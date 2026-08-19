"""Unit tests for authentication service."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.exceptions.base import AuthenticationError
from app.models.super_admin import SuperAdmin
from app.services.auth_service import AuthService


@pytest.fixture
def mock_repository() -> AsyncMock:
    """Provide a mocked SuperAdminRepository."""
    return AsyncMock()


@pytest.fixture
def auth_service(mock_repository: AsyncMock) -> AuthService:
    """Provide an AuthService with a mocked repository."""
    return AuthService(mock_repository)


@pytest.fixture
def active_admin() -> SuperAdmin:
    """Provide an active Super Admin with a known bcrypt hash."""
    from app.core.security import hash_password

    admin = SuperAdmin(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    return admin


@pytest.mark.asyncio
async def test_login_super_admin_success(
    auth_service: AuthService,
    mock_repository: AsyncMock,
    active_admin: SuperAdmin,
) -> None:
    """Valid credentials should return a JWT token envelope."""
    mock_repository.get_by_email.return_value = active_admin
    response = await auth_service.login_super_admin(
        "admin@example.com",
        "password123",
    )
    assert response.success is True
    assert response.message == "Login successful."
    assert response.data.token
    assert response.data.token_type == "bearer"
    assert response.data.email == "admin@example.com"
    assert response.data.expires_in > 0
    assert response.description


@pytest.mark.asyncio
async def test_login_super_admin_invalid_password(
    auth_service: AuthService,
    mock_repository: AsyncMock,
    active_admin: SuperAdmin,
) -> None:
    """Wrong password should raise AuthenticationError."""
    mock_repository.get_by_email.return_value = active_admin
    with pytest.raises(AuthenticationError) as exc_info:
        await auth_service.login_super_admin("admin@example.com", "wrong-password")
    assert exc_info.value.message == "Invalid email or password."
    assert exc_info.value.error_code == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_login_super_admin_unknown_email(
    auth_service: AuthService,
    mock_repository: AsyncMock,
) -> None:
    """Unknown email should raise AuthenticationError."""
    mock_repository.get_by_email.return_value = None
    with pytest.raises(AuthenticationError):
        await auth_service.login_super_admin("unknown@example.com", "password123")


@pytest.mark.asyncio
async def test_login_super_admin_inactive_account(
    auth_service: AuthService,
    mock_repository: AsyncMock,
    active_admin: SuperAdmin,
) -> None:
    """Inactive accounts should not authenticate."""
    active_admin.is_active = False
    mock_repository.get_by_email.return_value = active_admin
    with pytest.raises(AuthenticationError):
        await auth_service.login_super_admin("admin@example.com", "password123")
