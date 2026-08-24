"""Authentication use-cases: Super Admin login and token resolution."""

from uuid import UUID

from jose import JWTError
from loguru import logger

from app.core.config import Settings, get_settings
from app.core.security import (
    TOKEN_TYPE_ACCESS,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.exceptions.base import UnauthorizedError
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenData

LOGIN_SUCCESS_DESCRIPTION = "Welcome back. Redirecting to the dashboard."
_INVALID_CREDENTIALS = "Incorrect email or password"


class AuthService:
    """Credential verification and token issuance. No HTTP here."""

    def __init__(
        self,
        users: UserRepository,
        settings: Settings | None = None,
    ) -> None:
        """Inject repositories and settings."""
        self._users = users
        self._settings = settings or get_settings()

    def _tokens(self, user: User, description: str) -> TokenData:
        """Issue a fresh access/refresh pair for ``user``."""
        access = create_access_token(user.id, user.token_version)
        return TokenData(
            access_token=access,
            token=access,
            refresh_token=create_refresh_token(user.id, user.token_version),
            token_type="bearer",
            expires_in=self._settings.access_token_expire_minutes * 60,
            redirect_to=self._settings.dashboard_path,
            email=user.email,
            description=description,
        )

    async def login(
        self,
        email: str,
        password: str,
        *,
        require_super_admin: bool = False,
    ) -> TokenData:
        """Authenticate with email/password and return bearer tokens.

        Unknown email, wrong password, inactive accounts, and (when
        ``require_super_admin``) non-admin roles share the same error so
        callers cannot enumerate accounts.
        """
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            logger.info("login_failed email={}", email.lower())
            raise UnauthorizedError(
                _INVALID_CREDENTIALS,
                code="INVALID_CREDENTIALS",
            )
        if require_super_admin and user.role != UserRole.SUPER_ADMIN:
            logger.info("login_rejected_not_super_admin email={}", email.lower())
            raise UnauthorizedError(
                _INVALID_CREDENTIALS,
                code="INVALID_CREDENTIALS",
            )
        if not user.is_active:
            raise UnauthorizedError(
                _INVALID_CREDENTIALS,
                code="INVALID_CREDENTIALS",
            )
        logger.info("login_success user_id={}", user.id)
        return self._tokens(user, LOGIN_SUCCESS_DESCRIPTION)

    async def user_from_access_token(self, token: str) -> User:
        """Resolve a User from a bearer access token."""
        try:
            payload = decode_token(token)
        except JWTError as exc:
            raise UnauthorizedError("Not authenticated") from exc
        if payload.get("type") != TOKEN_TYPE_ACCESS:
            raise UnauthorizedError("Not authenticated")
        try:
            user_id = UUID(str(payload["sub"]))
        except (KeyError, ValueError) as exc:
            raise UnauthorizedError("Not authenticated") from exc
        user = await self._users.get_by_id(user_id)
        if user is None or int(payload.get("ver", 0)) != user.token_version:
            raise UnauthorizedError("Not authenticated")
        return user
