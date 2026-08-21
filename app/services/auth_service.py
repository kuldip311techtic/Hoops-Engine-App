"""Super Admin authentication and session (OAuth2 JWT)."""

import uuid
from typing import Any

from jose import JWTError
from loguru import logger

from app.core.config import Settings, get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.exceptions import ConflictError, UnauthorizedError
from app.models.super_admin import SuperAdmin
from app.repositories.super_admin_repository import SuperAdminRepository
from app.schemas.auth import LoginData, LoginResponse, SubscriptionAccessData
from app.services.billing_service import BillingService
from app.services.email_service import EmailService


class AuthService:
    """Authenticate Super Admins and issue OAuth2 access/refresh tokens.

    Identity is local JWT (AUTH_STRATEGY=jwt). Auth0 is not used on this path.
    """

    def __init__(
        self,
        repository: SuperAdminRepository,
        billing_service: BillingService,
        settings: Settings | None = None,
        email_service: EmailService | None = None,
    ) -> None:
        self._repository = repository
        self._billing_service = billing_service
        self._settings = settings or get_settings()
        self._email_service = email_service
        self._dummy_hash = hash_password("invalid-password-placeholder")

    def _token_claims(self, admin: SuperAdmin) -> dict[str, Any]:
        """JWT claims shared by access and refresh tokens."""
        return {
            "role": "super_admin",
            "token_version": int(admin.token_version),
            "email": admin.email,
        }

    def _build_response(self, admin: SuperAdmin, message: str) -> LoginResponse:
        """Assemble the frontend-friendly login envelope."""
        extra = self._token_claims(admin)
        access = create_access_token(subject=str(admin.id), extra_claims=extra)
        refresh = create_refresh_token(subject=str(admin.id), extra_claims=extra)
        description = "Redirect the Super Admin to the dashboard."
        data = LoginData(
            access_token=access,
            refresh_token=refresh,
            token_type="bearer",
            expires_in=self._settings.access_token_expire_minutes * 60,
            email=admin.email,
            description=description,
            message=message,
            error=None,
            redirect_to=self._settings.dashboard_path,
            subscription=self._billing_service.access_for_super_admin(),
        )
        return LoginResponse(success=True, message=message, data=data)

    async def login(self, email: str, password: str) -> LoginResponse:
        """Validate Super Admin credentials and create a session (JWT pair)."""
        admin = await self._repository.get_by_email(email)
        hashed = admin.hashed_password if admin is not None else self._dummy_hash
        password_ok = verify_password(password, hashed)
        if admin is None or not password_ok:
            logger.warning("super_admin_login_failed")
            raise UnauthorizedError(
                "Invalid email or password",
                code="INVALID_CREDENTIALS",
            )
        snapshot: SubscriptionAccessData = self._billing_service.access_for_super_admin()
        self._billing_service.ensure_access(snapshot)
        logger.info("super_admin_login_success admin_id={}", admin.id)
        self._maybe_notify_login(admin.email)
        return self._build_response(admin, "Login successful")

    async def refresh(self, refresh_token: str) -> LoginResponse:
        """Issue a new token pair from a valid refresh token."""
        try:
            payload = decode_refresh_token(refresh_token)
        except JWTError as exc:
            raise UnauthorizedError(
                "Invalid or expired refresh token",
                code="INVALID_REFRESH_TOKEN",
            ) from exc
        admin = await self._load_admin_from_payload(payload)
        return self._build_response(admin, "Session refreshed")

    async def change_password(
        self,
        admin: SuperAdmin,
        current_password: str,
        new_password: str,
    ) -> LoginResponse:
        """Update the password and revoke tokens on other devices."""
        if not verify_password(current_password, admin.hashed_password):
            raise UnauthorizedError(
                "Invalid email or password",
                code="INVALID_CREDENTIALS",
            )
        updated = await self._repository.update_password(admin, hash_password(new_password))
        logger.info("super_admin_password_changed admin_id={}", updated.id)
        return self._build_response(updated, "Password changed. Please use the new session.")

    async def register(self, email: str, password: str) -> SuperAdmin:
        """Create a Super Admin. Raises if the email is already in use."""
        existing = await self._repository.get_by_email(email)
        if existing is not None:
            raise ConflictError(
                "An account with this email already exists",
                code="EMAIL_ALREADY_EXISTS",
            )
        return await self._repository.create(
            email=email,
            hashed_password=hash_password(password),
        )

    async def get_by_token_payload(self, payload: dict[str, Any]) -> SuperAdmin:
        """Load the Super Admin for a decoded access token."""
        return await self._load_admin_from_payload(payload)

    async def _load_admin_from_payload(self, payload: dict[str, Any]) -> SuperAdmin:
        """Resolve ``sub`` + ``token_version`` or raise 401."""
        subject = payload.get("sub")
        try:
            admin_id = uuid.UUID(str(subject))
        except (ValueError, TypeError) as exc:
            raise UnauthorizedError(
                "Invalid or expired access token",
                code="INVALID_ACCESS_TOKEN",
            ) from exc
        admin = await self._repository.get_by_id(admin_id)
        if admin is None:
            raise UnauthorizedError(
                "Invalid or expired access token",
                code="INVALID_ACCESS_TOKEN",
            )
        claimed_version = int(payload.get("token_version", 0))
        if claimed_version != int(admin.token_version):
            raise UnauthorizedError(
                "Session expired. Please log in again.",
                code="SESSION_REVOKED",
            )
        return admin

    def _maybe_notify_login(self, email: str) -> None:
        """Best-effort login email via EmailService; never fails the login."""
        if self._email_service is None or not self._settings.ses_is_configured:
            return
        try:
            self._email_service.send_email(
                to_address=email,
                subject="New Hoops Engine login",
                html_body="<p>A new Super Admin session was created.</p>",
                text_body="A new Super Admin session was created.",
            )
        except Exception:
            logger.warning("login_notification_failed")
