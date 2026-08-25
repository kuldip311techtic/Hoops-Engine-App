"""Unit tests for AuthService.login."""

import pytest

from app.core.security import hash_password
from app.exceptions.base import UnauthorizedError
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from tests.fakes import InMemoryUserRepository


@pytest.fixture
def users() -> InMemoryUserRepository:
    """Empty in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def service(users: InMemoryUserRepository) -> AuthService:
    """AuthService bound to in-memory users."""
    return AuthService(users)


@pytest.mark.asyncio
async def test_login_success_super_admin(service: AuthService, users: InMemoryUserRepository) -> None:
    """Super Admin receives access and refresh tokens."""
    users.add(
        User(
            email="admin@example.com",
            password_hash=hash_password("Securepass1!"),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
    )
    tokens = await service.login(
        "admin@example.com",
        "Securepass1!",
        require_super_admin=True,
    )
    assert tokens.access_token
    assert tokens.token == tokens.access_token
    assert tokens.refresh_token
    assert tokens.redirect_to == "/dashboard"


@pytest.mark.asyncio
async def test_login_wrong_password_raises_unauthorized(
    service: AuthService,
    users: InMemoryUserRepository,
) -> None:
    """Wrong password raises INVALID_CREDENTIALS."""
    users.add(
        User(
            email="admin@example.com",
            password_hash=hash_password("Securepass1!"),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
        )
    )
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login(
            "admin@example.com",
            "WrongPass1!",
            require_super_admin=True,
        )
    assert exc_info.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_non_super_admin_same_error_as_wrong_password(
    service: AuthService,
    users: InMemoryUserRepository,
) -> None:
    """Non-Super-Admin role returns the same 401 as wrong password."""
    users.add(
        User(
            email="user@example.com",
            password_hash=hash_password("Securepass1!"),
            role=UserRole.USER,
            is_active=True,
        )
    )
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login(
            "user@example.com",
            "Securepass1!",
            require_super_admin=True,
        )
    assert exc_info.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_inactive_user_raises_unauthorized(
    service: AuthService,
    users: InMemoryUserRepository,
) -> None:
    """Inactive accounts cannot log in."""
    users.add(
        User(
            email="admin@example.com",
            password_hash=hash_password("Securepass1!"),
            role=UserRole.SUPER_ADMIN,
            is_active=False,
        )
    )
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login(
            "admin@example.com",
            "Securepass1!",
            require_super_admin=True,
        )
    assert exc_info.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_user_from_access_token_inactive_raises_unauthorized(
    service: AuthService,
    users: InMemoryUserRepository,
) -> None:
    """Inactive accounts cannot use bearer tokens on protected routes."""
    from app.core.security import create_access_token

    user = users.add(
        User(
            email="admin@example.com",
            password_hash=hash_password("Securepass1!"),
            role=UserRole.SUPER_ADMIN,
            is_active=False,
        )
    )
    token = create_access_token(user.id, user.token_version)
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.user_from_access_token(token)
    assert exc_info.value.code == "UNAUTHORIZED"
