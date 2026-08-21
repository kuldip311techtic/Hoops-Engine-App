"""Admin user account management use-cases."""

from uuid import UUID

from loguru import logger

from app.core.security import hash_password
from app.exceptions.base import ConflictError, ForbiddenError, NotFoundError
from app.models.user import User, UserRole
from app.repositories.user_repository import UserRepository
from app.schemas.user_admin import (
    UserResponse,
    full_name,
    normalize_user_role,
    user_role_label,
)
from app.services.email_service import EmailService


class UserAdminService:
    """Super Admin CRUD for user accounts. No HTTP here."""

    def __init__(
        self,
        users: UserRepository,
        email_service: EmailService | None = None,
    ) -> None:
        """Inject repository and optional email adapter."""
        self._users = users
        self._email = email_service

    @staticmethod
    def _to_response(user: User) -> UserResponse:
        """Map an ORM row to the admin API response DTO."""
        return UserResponse(
            id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            name=full_name(user.first_name, user.last_name),
            email=user.email,
            role=user_role_label(user.role),
            role_code=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _notify_created(self, user: User) -> None:
        """Best-effort account-created email. Never fails the admin request."""
        if self._email is None:
            return
        try:
            self._email.send_email(
                to_address=user.email,
                subject="Your Hoops Engine account",
                body_text=(
                    f"Hello {full_name(user.first_name, user.last_name)}, "
                    "your Hoops Engine account was created by an administrator."
                ),
            )
        except Exception:
            logger.warning("user_welcome_email_skipped user_id={}", user.id)

    async def list_users(
        self,
        *,
        active_only: bool = False,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[list[UserResponse], int, int, int]:
        """Return paginated users for the admin table."""
        safe_page = max(page, 1)
        safe_limit = min(max(limit, 1), 100)
        offset = (safe_page - 1) * safe_limit
        rows, total = await self._users.list_all(
            active_only=active_only,
            offset=offset,
            limit=safe_limit,
        )
        return (
            [self._to_response(row) for row in rows],
            total,
            safe_page,
            safe_limit,
        )

    async def get_user(self, user_id: UUID) -> UserResponse:
        """Return a single user or raise NotFoundError."""
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        return self._to_response(user)

    async def create_user(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        role: str,
    ) -> UserResponse:
        """Create a user after verifying email uniqueness."""
        existing = await self._users.get_by_email(email)
        if existing is not None:
            raise ConflictError(
                "Email already in use",
                code="EMAIL_ALREADY_EXISTS",
            )
        role_enum = normalize_user_role(role)
        user = await self._users.create(
            email=email,
            password_hash=hash_password(password),
            role=role_enum,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
        )
        logger.info("admin_user_created user_id={} role={}", user.id, role_enum.value)
        self._notify_created(user)
        return self._to_response(user)

    async def update_user(
        self,
        user_id: UUID,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        password: str | None = None,
        role: str | None = None,
    ) -> UserResponse:
        """Update an existing user account."""
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        if user.role == UserRole.SUPER_ADMIN:
            raise ForbiddenError(
                "Super Admin accounts cannot be modified via this API",
                code="FORBIDDEN",
            )
        if email is not None and email.lower() != user.email:
            conflict = await self._users.get_by_email(email)
            if conflict is not None:
                raise ConflictError(
                    "Email already in use",
                    code="EMAIL_ALREADY_EXISTS",
                )
        role_enum = normalize_user_role(role) if role is not None else None
        password_hash = hash_password(password) if password is not None else None
        should_revoke_tokens = password_hash is not None or (
            role_enum is not None and role_enum != user.role
        )
        updated = await self._users.update(
            user,
            email=email,
            password_hash=password_hash,
            role=role_enum,
            first_name=first_name.strip() if first_name is not None else None,
            last_name=last_name.strip() if last_name is not None else None,
        )
        if should_revoke_tokens:
            await self._users.increment_token_version(updated)
        logger.info("admin_user_updated user_id={}", updated.id)
        return self._to_response(updated)

    async def deactivate_user(
        self,
        user_id: UUID,
        *,
        actor: User,
    ) -> UserResponse:
        """Soft-remove a user. The acting Super Admin cannot remove themselves."""
        if actor.id == user_id:
            raise ForbiddenError(
                "You cannot remove your own account",
                code="CANNOT_REMOVE_SELF",
            )
        user = await self._users.get_by_id(user_id)
        if user is None or not user.is_active:
            raise NotFoundError("User not found", code="USER_NOT_FOUND")
        if user.role == UserRole.SUPER_ADMIN:
            raise ForbiddenError(
                "Super Admin accounts cannot be removed via this API",
                code="FORBIDDEN",
            )
        updated = await self._users.deactivate(user)
        await self._users.increment_token_version(updated)
        logger.info("admin_user_deactivated user_id={}", updated.id)
        return self._to_response(updated)
