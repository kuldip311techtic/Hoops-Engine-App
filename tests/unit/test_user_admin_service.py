"""Unit tests for UserAdminService."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.exceptions.base import ConflictError, ForbiddenError, NotFoundError
from app.models.user import User, UserRole
from app.services.user_admin_service import UserAdminService
from tests.fakes import InMemoryUserRepository


@pytest.fixture
def users() -> InMemoryUserRepository:
    """Empty in-memory user repository."""
    return InMemoryUserRepository()


@pytest.fixture
def service(users: InMemoryUserRepository) -> UserAdminService:
    """UserAdminService bound to in-memory users."""
    return UserAdminService(users)


@pytest.fixture
def admin_actor(users: InMemoryUserRepository) -> User:
    """Super Admin actor for service calls."""
    now = datetime.now(UTC)
    return users.add(
        User(
            id=uuid4(),
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            password_hash="hash",
            role=UserRole.SUPER_ADMIN,
            token_version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.fixture
def coach_user(users: InMemoryUserRepository) -> User:
    """Seed a coach user."""
    now = datetime.now(UTC)
    return users.add(
        User(
            id=uuid4(),
            email="coach@test.com",
            first_name="John",
            last_name="Doe",
            password_hash="hash",
            role=UserRole.COACH,
            token_version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_create_user_success(service: UserAdminService) -> None:
    """Creating a user returns the expected response shape."""
    result = await service.create_user(
        first_name="Jane",
        last_name="Smith",
        email="jane@test.com",
        password="Securepass1!",
        role="Coach",
    )
    assert result.email == "jane@test.com"
    assert result.role == "Coach"
    assert result.roles == ["Coach"]
    assert result.name == "Jane Smith"


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises_conflict(
    service: UserAdminService,
    coach_user: User,
) -> None:
    """Duplicate email raises ConflictError."""
    with pytest.raises(ConflictError) as exc:
        await service.create_user(
            first_name="Other",
            last_name="User",
            email=coach_user.email,
            password="Securepass1!",
            role="Player",
        )
    assert exc.value.code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_user_invalid_role_raises_validation(
    service: UserAdminService,
) -> None:
    """Invalid role raises ValueError from normalize_user_role."""
    with pytest.raises(ValueError):
        await service.create_user(
            first_name="Bad",
            last_name="Role",
            email="bad@test.com",
            password="Securepass1!",
            role="SUPER_ADMIN",
        )


@pytest.mark.asyncio
async def test_deactivate_user_success(
    service: UserAdminService,
    coach_user: User,
    admin_actor: User,
) -> None:
    """Deactivating a user sets is_active to False."""
    result = await service.deactivate_user(coach_user.id, actor=admin_actor)
    assert result.is_active is False


@pytest.mark.asyncio
async def test_deactivate_self_raises_forbidden(
    service: UserAdminService,
    admin_actor: User,
) -> None:
    """Super Admin cannot remove their own account."""
    with pytest.raises(ForbiddenError) as exc:
        await service.deactivate_user(admin_actor.id, actor=admin_actor)
    assert exc.value.code == "CANNOT_REMOVE_SELF"


@pytest.mark.asyncio
async def test_deactivate_super_admin_raises_forbidden(
    service: UserAdminService,
    users: InMemoryUserRepository,
    admin_actor: User,
) -> None:
    """Cannot deactivate another Super Admin."""
    now = datetime.now(UTC)
    other_admin = users.add(
        User(
            id=uuid4(),
            email="other-admin@test.com",
            first_name="Other",
            last_name="Admin",
            password_hash="hash",
            role=UserRole.SUPER_ADMIN,
            token_version=1,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        await service.deactivate_user(other_admin.id, actor=admin_actor)
    assert exc.value.code == "FORBIDDEN"


@pytest.mark.asyncio
async def test_update_user_not_found_raises_not_found(
    service: UserAdminService,
) -> None:
    """Updating unknown user raises NotFoundError."""
    with pytest.raises(NotFoundError) as exc:
        await service.update_user(uuid4(), first_name="Missing")
    assert exc.value.code == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_list_users_pagination(
    service: UserAdminService,
    users: InMemoryUserRepository,
) -> None:
    """List users returns paginated results."""
    now = datetime.now(UTC)
    for index in range(3):
        users.add(
            User(
                id=uuid4(),
                email=f"user{index}@test.com",
                first_name=f"User{index}",
                last_name="Test",
                password_hash="hash",
                role=UserRole.USER,
                token_version=1,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
        )
    items, total, page, limit = await service.list_users(page=1, limit=2)
    assert len(items) == 2
    assert total == 3
    assert page == 1
    assert limit == 2
