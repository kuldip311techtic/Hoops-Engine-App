"""AuthService unit tests with a fake repository."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.config import Settings
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.exceptions import ConflictError, UnauthorizedError
from app.models.super_admin import SuperAdmin
from app.schemas.auth import SubscriptionAccessData
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService


def _settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        test_database_url="postgresql+asyncpg://u:p@localhost/db_test",
        secret_key="s",
        jwt_secret_key="unit-test-jwt-secret-key-value",
        access_token_expire_minutes=30,
        dashboard_path="/dashboard",
    )


def _admin(*, token_version: int = 0, password: str = "securepassword") -> SuperAdmin:
    return SuperAdmin(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password(password),
        token_version=token_version,
    )


def _service(repo) -> AuthService:
    billing = MagicMock(spec=BillingService)
    billing.access_for_super_admin.return_value = SubscriptionAccessData(
        status="not_applicable",
        has_access=True,
        access_until=None,
    )
    billing.ensure_access.return_value = None
    return AuthService(repository=repo, billing_service=billing, settings=_settings())


@pytest.mark.asyncio
async def test_login_success_returns_bearer_tokens() -> None:
    """Valid credentials return access and refresh tokens plus FE fields."""
    admin = _admin()
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=admin)
    service = _service(repo)
    result = await service.login("admin@example.com", "securepassword")
    assert result.success is True
    assert result.data.token_type == "bearer"
    assert result.data.email == "admin@example.com"
    assert result.data.redirect_to == "/dashboard"
    assert result.data.error is None
    assert result.data.description
    assert result.message == "Login successful"
    assert result.data.access_token
    assert result.data.refresh_token


@pytest.mark.asyncio
async def test_login_unknown_email_raises_unauthorized() -> None:
    """Unknown email is a generic invalid-credentials error."""
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    service = _service(repo)
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login("missing@example.com", "securepassword")
    assert exc_info.value.code == "INVALID_CREDENTIALS"
    assert "missing@example.com" not in exc_info.value.message


@pytest.mark.asyncio
async def test_login_wrong_password_raises_unauthorized() -> None:
    """Wrong password uses the same error as unknown email."""
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=_admin())
    service = _service(repo)
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login("admin@example.com", "nope")
    assert exc_info.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_error_message_does_not_reveal_which_field() -> None:
    """Failure copy does not say whether email or password was wrong."""
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=None)
    service = _service(repo)
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.login("admin@example.com", "wrong")
    assert exc_info.value.message == "Invalid email or password"


@pytest.mark.asyncio
async def test_refresh_rejects_access_token() -> None:
    """Access tokens cannot be refreshed."""
    admin = _admin()
    access = create_access_token(str(admin.id), extra_claims={"token_version": 0})
    repo = AsyncMock()
    service = _service(repo)
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.refresh(access)
    assert exc_info.value.code == "INVALID_REFRESH_TOKEN"


@pytest.mark.asyncio
async def test_refresh_rejects_stale_token_version() -> None:
    """Refresh fails after password change (token_version bump)."""
    admin = _admin(token_version=2)
    refresh = create_refresh_token(
        str(admin.id),
        extra_claims={"role": "super_admin", "token_version": 0, "email": admin.email},
    )
    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=admin)
    service = _service(repo)
    with pytest.raises(UnauthorizedError) as exc_info:
        await service.refresh(refresh)
    assert exc_info.value.code == "SESSION_REVOKED"


@pytest.mark.asyncio
async def test_register_duplicate_email() -> None:
    """Registering an existing email raises EMAIL_ALREADY_EXISTS."""
    repo = AsyncMock()
    repo.get_by_email = AsyncMock(return_value=_admin())
    service = _service(repo)
    with pytest.raises(ConflictError) as exc_info:
        await service.register("admin@example.com", "securepassword")
    assert exc_info.value.code == "EMAIL_ALREADY_EXISTS"
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions() -> None:
    """Password change bumps token_version via the repository."""
    admin = _admin()
    updated = _admin(token_version=1)
    updated.id = admin.id
    repo = AsyncMock()
    repo.update_password = AsyncMock(return_value=updated)
    service = _service(repo)
    result = await service.change_password(admin, "securepassword", "NewSecure1!")
    assert result.success is True
    repo.update_password.assert_awaited()
