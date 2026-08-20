"""User management business logic."""

import re
import uuid
from typing import NoReturn, cast

from sqlalchemy.exc import IntegrityError

from app.core.logging import logger
from app.core.security import hash_password
from app.exceptions.base import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.models.super_admin import SuperAdmin
from app.models.user import User
from app.repositories.super_admin_repository import SuperAdminRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import (
    UserCreate,
    UserDeleteResponse,
    UserListData,
    UserListResponse,
    UserRead,
    UserResponse,
    UserRole,
    UserStatus,
    UserUpdate,
)

_PASSWORD_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def _is_foreign_key_violation(exc: IntegrityError) -> bool:
    """Return True when IntegrityError is an organization FK failure."""
    orig = getattr(exc, "orig", None)
    combined = f"{type(orig).__name__ if orig is not None else ''} {orig}".lower()
    return "foreign" in combined or "foreignkeyviolation" in combined


def validate_password_strength(password: str) -> None:
    """Raise ValidationAppError when a password fails complexity rules.

    Rules: at least 8 characters, one uppercase, one lowercase, one digit,
    and one special character.
    """
    issues: list[str] = []
    if len(password) < 8:
        issues.append("at least 8 characters")
    if not any(char.islower() for char in password):
        issues.append("one lowercase letter")
    if not any(char.isupper() for char in password):
        issues.append("one uppercase letter")
    if not any(char.isdigit() for char in password):
        issues.append("one number")
    if not _PASSWORD_SPECIAL.search(password):
        issues.append("one special character")
    if issues:
        message = "Password must include " + ", ".join(issues) + "."
        raise ValidationAppError(
            message=message,
            error_code="VALIDATION_ERROR",
            details=[{"field": "password", "message": message}],
        )


def _to_read(user: User) -> UserRead:
    """Map a User ORM instance to the public read schema."""
    role = cast(UserRole, user.role)
    status: UserStatus = "active" if user.is_active else "inactive"
    name = f"{user.first_name} {user.last_name}".strip()
    return UserRead(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        name=name,
        email=user.email,
        role=role,
        roles=[role],
        status=status,
        is_active=user.is_active,
        description="",
        password=None,
        organization_id=user.organization_id,
    )


def _single_response(user: User, message: str, description: str) -> UserResponse:
    """Build the frontend-facing single-user success envelope."""
    payload = _to_read(user)
    return UserResponse(
        success=True,
        message=message,
        description=description,
        email=payload.email,
        token=None,
        password=None,
        user=payload,
        id=payload.id,
        name=payload.name,
        role=payload.role,
        roles=payload.roles,
        status=payload.status,
        error=None,
        data=payload,
    )


class UserService:
    """Service for Super Admin user CRUD workflows."""

    def __init__(
        self,
        repository: UserRepository,
        super_admin_repository: SuperAdminRepository,
    ) -> None:
        """Initialize with user and Super Admin repositories."""
        self._repository = repository
        self._super_admin_repository = super_admin_repository

    async def list_users(self, *, page: int, page_size: int) -> UserListResponse:
        """Return a paginated list of users sorted by name."""
        offset = (page - 1) * page_size
        rows, total = await self._repository.list_paginated(
            offset=offset,
            limit=page_size,
        )
        items = [_to_read(row) for row in rows]
        return UserListResponse(
            success=True,
            message="Users retrieved.",
            description="User list loaded.",
            email=None,
            token=None,
            password=None,
            user=None,
            id=None,
            name=None,
            role=None,
            roles=None,
            status=None,
            error=None,
            data=UserListData(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            ),
        )

    async def create_user(self, payload: UserCreate) -> UserResponse:
        """Create a user, hashing the password and rejecting duplicate emails."""
        validate_password_strength(payload.password)
        await self._assert_unique_email(payload.email)
        user = User(
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
            email=payload.email,
            role=payload.role or "coach",
            hashed_password=hash_password(payload.password),
            is_active=payload.is_active,
            organization_id=payload.organization_id,
        )
        try:
            saved = await self._repository.create(user)
        except IntegrityError as exc:
            logger.warning("User create violated a database constraint")
            await self._raise_integrity_error(payload.email, cause=exc)
        logger.info("User created id={} email={}", saved.id, saved.email)
        return _single_response(
            saved,
            message="User created.",
            description="User added successfully.",
        )

    async def update_user(
        self,
        user_id: uuid.UUID,
        payload: UserUpdate,
    ) -> UserResponse:
        """Update an existing user, rejecting duplicate emails."""
        user = await self._get_or_404(user_id)
        await self._assert_unique_email(payload.email, exclude_id=user.id)
        if payload.password:
            validate_password_strength(payload.password)
            user.hashed_password = hash_password(payload.password)
        user.first_name = payload.first_name or user.first_name
        user.last_name = payload.last_name or user.last_name
        user.email = payload.email
        user.role = payload.role or user.role
        if payload.status is not None:
            user.is_active = payload.is_active is True
        if "organization_id" in payload.model_fields_set:
            user.organization_id = payload.organization_id
        try:
            saved = await self._repository.save(user)
        except IntegrityError as exc:
            logger.warning("User update violated a database constraint id={}", user_id)
            await self._raise_integrity_error(
                payload.email,
                cause=exc,
                exclude_id=user_id,
            )
        logger.info("User updated id={} email={}", saved.id, saved.email)
        return _single_response(
            saved,
            message="User updated.",
            description="User details saved.",
        )

    async def delete_user(
        self,
        user_id: uuid.UUID,
        actor: SuperAdmin,
    ) -> UserDeleteResponse:
        """Remove a user unless the Super Admin targets their own account."""
        if user_id == actor.id:
            logger.warning(
                "Super Admin attempted to remove own account id={}",
                actor.id,
            )
            raise AuthorizationError(
                message="You cannot remove your own account.",
                error_code="CANNOT_DELETE_OWN_ACCOUNT",
            )
        user = await self._get_or_404(user_id)
        removed_id = user.id
        removed_name = f"{user.first_name} {user.last_name}".strip()
        removed_email = user.email
        removed_role = cast(UserRole, user.role)
        await self._repository.delete(user)
        logger.info("User removed id={} email={}", removed_id, removed_email)
        return UserDeleteResponse(
            success=True,
            message="User removed.",
            description="The user was removed successfully.",
            email=removed_email,
            token=None,
            password=None,
            user=None,
            id=removed_id,
            name=removed_name,
            role=removed_role,
            roles=[removed_role],
            status="inactive",
            error=None,
            data={},
        )

    async def _get_or_404(self, user_id: uuid.UUID) -> User:
        """Load a user or raise NotFoundError."""
        user = await self._repository.get_by_id(user_id)
        if user is None:
            raise NotFoundError(
                message="User not found.",
                error_code="USER_NOT_FOUND",
            )
        return user

    async def _assert_unique_email(
        self,
        email: str,
        *,
        exclude_id: uuid.UUID | None = None,
    ) -> None:
        """Raise ConflictError when email is already used by a user or Super Admin."""
        existing_user = await self._repository.get_by_email_ci(
            email,
            exclude_id=exclude_id,
        )
        existing_admin = await self._super_admin_repository.get_by_email(email)
        if existing_user is not None or existing_admin is not None:
            logger.warning("Duplicate user email={}", email)
            raise ConflictError(
                message="A user with this email already exists.",
                error_code="EMAIL_ALREADY_EXISTS",
                details=[
                    {
                        "field": "email",
                        "message": "A user with this email already exists.",
                    }
                ],
            )

    async def _raise_integrity_error(
        self,
        email: str,
        *,
        cause: IntegrityError,
        exclude_id: uuid.UUID | None = None,
    ) -> NoReturn:
        """Map IntegrityError to EMAIL_ALREADY_EXISTS or ORGANIZATION_NOT_FOUND."""
        if _is_foreign_key_violation(cause):
            raise ValidationAppError(
                message="Organization not found.",
                error_code="ORGANIZATION_NOT_FOUND",
                details=[
                    {
                        "field": "organization_id",
                        "message": "Organization not found.",
                    }
                ],
            ) from cause
        await self._assert_unique_email(email, exclude_id=exclude_id)
        raise ConflictError(
            message="A user with this email already exists.",
            error_code="EMAIL_ALREADY_EXISTS",
        ) from cause
