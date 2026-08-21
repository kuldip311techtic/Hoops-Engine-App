"""User admin service unit tests (JAW-9460)."""

import secrets
from uuid import uuid4

import pytest

from app.exceptions.base import ConflictError, ForbiddenError
from app.models.user import User, UserRole
from app.services.user_admin_service import UserAdminService
from tests.conftest import LIVE_NEW_EMAIL
from tests.fakes import InMemoryUserRepository


def _test_password(*, prefix: str = "Unit") -> str:
    """Return a unique password that satisfies the app's complexity policy."""
    return f"{prefix}{secrets.token_hex(8)}!1"


@pytest.fixture
def users() -> InMemoryUserRepository:
    """Empty in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def service(users: InMemoryUserRepository) -> UserAdminService:
    """UserAdminService without email."""
    return UserAdminService(users, email_service=None)


def _admin() -> User:
    """Build a super admin actor for deactivate tests."""
    return User(
        id=uuid4(),
        email="actor@example.com",
        first_name="Super",
        last_name="Admin",
        password_hash="hash",
        role=UserRole.SUPER_ADMIN,
        token_version=1,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_create_user_success(service: UserAdminService) -> None:
    """Creating a user returns FE-friendly name and role fields."""
    result = await service.create_user(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        password=_test_password(),
        role="Coach",
    )
    assert result.name == "John Doe"
    assert result.role == "Coach"
    assert result.role_code == "COACH"
    assert result.email == "john.doe@example.com"


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises_conflict(
    service: UserAdminService,
) -> None:
    """Duplicate emails raise EMAIL_ALREADY_EXISTS."""
    password = _test_password()
    await service.create_user(
        first_name="John",
        last_name="Doe",
        email=LIVE_NEW_EMAIL,
        password=password,
        role="Coach",
    )
    with pytest.raises(ConflictError) as exc:
        await service.create_user(
            first_name="Jane",
            last_name="Doe",
            email=LIVE_NEW_EMAIL,
            password=_test_password(prefix="Other"),
            role="Player",
        )
    assert exc.value.code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_user_bumps_token_version_on_password_change(
    service: UserAdminService,
    users: InMemoryUserRepository,
) -> None:
    """Password changes invalidate existing sessions."""
    created = await service.create_user(
        first_name="Pat",
        last_name="Smith",
        email="pat@example.com",
        password=_test_password(prefix="Initial"),
        role="User",
    )
    user = await users.get_by_id(created.id)
    assert user is not None
    assert user.token_version == 1
    await service.update_user(
        created.id,
        password=_test_password(prefix="Updated"),
    )
    assert user.token_version == 2


@pytest.mark.asyncio
async def test_deactivate_user_sets_is_active_false(
    service: UserAdminService,
) -> None:
    """Removing a user soft-deactivates the account."""
    created = await service.create_user(
        first_name="Rem",
        last_name="Ove",
        email="remove@example.com",
        password=_test_password(),
        role="Viewer",
    )
    removed = await service.deactivate_user(created.id, actor=_admin())
    assert removed.is_active is False


@pytest.mark.asyncio
async def test_deactivate_self_raises_forbidden(
    service: UserAdminService,
    users: InMemoryUserRepository,
) -> None:
    """Super Admin cannot remove their own account."""
    actor = await users.create(
        email="admin@example.com",
        password_hash="hash",
        role=UserRole.SUPER_ADMIN,
        first_name="Super",
        last_name="Admin",
    )
    with pytest.raises(ForbiddenError) as exc:
        await service.deactivate_user(actor.id, actor=actor)
    assert exc.value.code == "CANNOT_REMOVE_SELF"


@pytest.mark.asyncio
async def test_list_users_excludes_inactive_when_requested(
    service: UserAdminService,
    users: InMemoryUserRepository,
) -> None:
    """active_only excludes deactivated accounts."""
    active = await users.create(
        email="active@example.com",
        password_hash="hash",
        role=UserRole.COACH,
        first_name="Active",
        last_name="User",
    )
    inactive = await users.create(
        email="inactive@example.com",
        password_hash="hash",
        role=UserRole.PLAYER,
        first_name="Inactive",
        last_name="User",
    )
    inactive.is_active = False
    items, total, page, limit = await service.list_users(active_only=True)
    assert total == 1
    assert items[0].id == active.id
    assert page == 1
    assert limit == 50
