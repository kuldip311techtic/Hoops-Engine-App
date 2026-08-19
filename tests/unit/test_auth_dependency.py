"""Unit tests for Super Admin JWT dependency."""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.security import create_access_token
from app.dependencies.auth import get_current_super_admin
from app.exceptions.base import AuthenticationError, AuthorizationError
from app.models.super_admin import SuperAdmin


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    """Build HTTP Bearer credentials for dependency tests."""
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


@pytest.mark.asyncio
async def test_get_current_super_admin_missing_credentials() -> None:
    """Missing Authorization header should raise AuthenticationError."""
    repository = AsyncMock()
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_super_admin(credentials=None, repository=repository)
    assert exc_info.value.error_code == "AUTHENTICATION_FAILED"
    assert exc_info.value.message == "Authentication required."
    repository.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_super_admin_invalid_token() -> None:
    """Tampered tokens should raise AuthenticationError."""
    repository = AsyncMock()
    with pytest.raises(AuthenticationError) as exc_info:
        await get_current_super_admin(
            credentials=_bearer("not-a-jwt"),
            repository=repository,
        )
    assert exc_info.value.message == "Invalid or expired token."


@pytest.mark.asyncio
async def test_get_current_super_admin_wrong_role() -> None:
    """Non-super-admin JWT role should raise AuthorizationError."""
    repository = AsyncMock()
    token = create_access_token(
        subject=str(uuid.uuid4()),
        claims={"email": "coach@example.com", "role": "coach"},
    )
    with pytest.raises(AuthorizationError) as exc_info:
        await get_current_super_admin(
            credentials=_bearer(token),
            repository=repository,
        )
    assert exc_info.value.error_code == "AUTHORIZATION_FAILED"


@pytest.mark.asyncio
async def test_get_current_super_admin_inactive_account() -> None:
    """Inactive Super Admin tokens should not authenticate."""
    admin_id = uuid.uuid4()
    repository = AsyncMock()
    repository.get_by_id.return_value = SuperAdmin(
        id=admin_id,
        email="inactive@example.com",
        hashed_password="hash",
        is_active=False,
    )
    token = create_access_token(
        subject=str(admin_id),
        claims={"email": "inactive@example.com", "role": "super_admin"},
    )
    with pytest.raises(AuthenticationError):
        await get_current_super_admin(
            credentials=_bearer(token),
            repository=repository,
        )


@pytest.mark.asyncio
async def test_get_current_super_admin_invalid_subject() -> None:
    """A token whose sub is not a UUID should raise AuthenticationError."""
    repository = AsyncMock()
    token = create_access_token(
        subject="not-a-uuid",
        claims={"email": "admin@example.com", "role": "super_admin"},
    )
    with pytest.raises(AuthenticationError):
        await get_current_super_admin(
            credentials=_bearer(token),
            repository=repository,
        )
    repository.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_get_current_super_admin_success() -> None:
    """A valid Super Admin token should return the matching account."""
    admin_id = uuid.uuid4()
    admin = SuperAdmin(
        id=admin_id,
        email="admin@example.com",
        hashed_password="hash",
        is_active=True,
    )
    repository = AsyncMock()
    repository.get_by_id.return_value = admin
    token = create_access_token(
        subject=str(admin_id),
        claims={"email": admin.email, "role": "super_admin"},
    )
    result = await get_current_super_admin(
        credentials=_bearer(token),
        repository=repository,
    )
    assert result.id == admin_id
    repository.get_by_id.assert_awaited_once_with(admin_id)
