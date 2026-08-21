"""AuthService unit tests."""

import pytest

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.exceptions.base import ConflictError, UnauthorizedError
from app.models.user import User
from app.services.auth_service import AuthService
from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD
from tests.fakes import InMemorySubscriptionRepository, InMemoryUserRepository


@pytest.mark.asyncio
async def test_login_success_returns_bearer_tokens(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Successful login returns access and refresh tokens plus redirect_to."""
    tokens = await auth_service.login(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert tokens.token_type == "bearer"
    assert tokens.redirect_to == "/dashboard"
    assert tokens.email == ADMIN_EMAIL
    assert tokens.description
    assert decode_token(tokens.access_token)["sub"] == str(admin_user.id)


@pytest.mark.asyncio
async def test_login_unknown_email_raises_unauthorized(
    auth_service: AuthService,
) -> None:
    """Unknown emails raise the generic credentials error."""
    with pytest.raises(UnauthorizedError, match="Incorrect email or password"):
        await auth_service.login("nobody@example.com", ADMIN_PASSWORD)


@pytest.mark.asyncio
async def test_login_wrong_password_raises_unauthorized(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Wrong passwords raise the generic credentials error."""
    with pytest.raises(UnauthorizedError, match="Incorrect email or password"):
        await auth_service.login(ADMIN_EMAIL, "WrongPass1!")


@pytest.mark.asyncio
async def test_login_error_message_does_not_reveal_which_field(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Unknown email and bad password share the same message."""
    with pytest.raises(UnauthorizedError) as unknown:
        await auth_service.login("missing@example.com", ADMIN_PASSWORD)
    with pytest.raises(UnauthorizedError) as bad:
        await auth_service.login(ADMIN_EMAIL, "nope")
    assert unknown.value.message == bad.value.message
    assert unknown.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_register_duplicate_email(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Registering an existing email raises EMAIL_ALREADY_EXISTS."""
    with pytest.raises(ConflictError) as exc:
        await auth_service.register(ADMIN_EMAIL, "Another1!")
    assert exc.value.code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_change_password_revokes_other_sessions(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Changing password increments token_version so old refresh tokens fail."""
    old_refresh = create_refresh_token(admin_user.id, admin_user.token_version)
    await auth_service.change_password(admin_user, ADMIN_PASSWORD, "BrandNew1!")
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(old_refresh)
    new_tokens = await auth_service.login(ADMIN_EMAIL, "BrandNew1!")
    assert decode_token(new_tokens.access_token)["ver"] == admin_user.token_version


@pytest.mark.asyncio
async def test_refresh_rejects_access_token(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Access tokens are not valid for refresh."""
    access = create_access_token(admin_user.id, admin_user.token_version)
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(access)


@pytest.mark.asyncio
async def test_refresh_rejects_stale_token_version(
    auth_service: AuthService,
    admin_user: User,
) -> None:
    """Refresh tokens with an old version are rejected."""
    stale = create_refresh_token(admin_user.id, token_version=0)
    with pytest.raises(UnauthorizedError):
        await auth_service.refresh(stale)


@pytest.mark.asyncio
async def test_register_new_user(
    users: InMemoryUserRepository,
    subscriptions: InMemorySubscriptionRepository,
) -> None:
    """A new email can register and then log in."""
    service = AuthService(users, subscriptions)
    tokens = await service.register("fresh@example.com", "FreshPass1!")
    assert tokens.access_token
    assert tokens.email == "fresh@example.com"
    again = await service.login("fresh@example.com", "FreshPass1!")
    assert again.access_token


@pytest.mark.asyncio
async def test_require_super_admin_rejects_user_role(
    users: InMemoryUserRepository,
    subscriptions: InMemorySubscriptionRepository,
) -> None:
    """Admin login endpoint must not admit USER accounts."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    service = AuthService(users, subscriptions)
    users.add(
        User(
            email="player@example.com",
            password_hash=hash_password("Player1!"),
            role=UserRole.USER,
            token_version=1,
            is_active=True,
        )
    )
    with pytest.raises(UnauthorizedError) as exc:
        await service.login(
            "player@example.com",
            "Player1!",
            require_super_admin=True,
        )
    assert exc.value.code == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_still_succeeds_when_email_fails(
    auth_service: AuthService,
    admin_user: User,
    users: InMemoryUserRepository,
    subscriptions: InMemorySubscriptionRepository,
) -> None:
    """SES failures must not block Super Admin login."""
    from unittest.mock import MagicMock

    from app.exceptions.base import AppError

    mail = MagicMock()
    mail.send_email.side_effect = AppError("Failed to send email", code="EMAIL_SEND_FAILED")
    service = AuthService(users, subscriptions, email_service=mail)
    tokens = await service.login(ADMIN_EMAIL, ADMIN_PASSWORD, require_super_admin=True)
    assert tokens.access_token
    mail.send_email.assert_called_once()
