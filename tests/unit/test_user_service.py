"""Unit tests for user management service."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.core.security import verify_password
from app.exceptions.base import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.models.super_admin import SuperAdmin
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService, validate_password_strength


def _payload(**overrides: object) -> UserCreate:
    """Build a valid user create payload."""
    data: dict = {
        "first_name": "Jane",
        "last_name": "Coach",
        "email": "jane.coach@example.com",
        "role": "coach",
        "password": "SecurePass1!",
        "status": "active",
    }
    data.update(overrides)
    return UserCreate.model_validate(data)


def _user(**overrides: object) -> User:
    """Build a User ORM instance."""
    values: dict = {
        "id": uuid.uuid4(),
        "first_name": "Jane",
        "last_name": "Coach",
        "email": "jane.coach@example.com",
        "role": "coach",
        "hashed_password": "hashed",
        "is_active": True,
        "organization_id": None,
    }
    values.update(overrides)
    return User(**values)


def _admin() -> SuperAdmin:
    """Build an actor Super Admin."""
    return SuperAdmin(
        id=uuid.uuid4(),
        email="admin@test.com",
        hashed_password="hash",
        is_active=True,
    )


@pytest.fixture
def user_repository() -> AsyncMock:
    """Provide a mocked UserRepository."""
    return AsyncMock()


@pytest.fixture
def admin_repository() -> AsyncMock:
    """Provide a mocked SuperAdminRepository."""
    return AsyncMock()


@pytest.fixture
def service(user_repository: AsyncMock, admin_repository: AsyncMock) -> UserService:
    """Provide a UserService with mocked repositories."""
    return UserService(user_repository, admin_repository)


def test_validate_password_strength_rejects_weak_password() -> None:
    """Passwords missing complexity rules should raise ValidationAppError."""
    with pytest.raises(ValidationAppError) as exc_info:
        validate_password_strength("short")
    assert exc_info.value.error_code == "VALIDATION_ERROR"
    assert exc_info.value.details[0]["field"] == "password"


def test_validate_password_strength_accepts_complex_password() -> None:
    """A password meeting SOW rules should not raise."""
    validate_password_strength("SecurePass1!")


@pytest.mark.asyncio
async def test_create_user_success_hashes_password(
    service: UserService,
    user_repository: AsyncMock,
    admin_repository: AsyncMock,
) -> None:
    """Valid details should persist a hashed password, never plaintext."""
    created = _user()
    user_repository.get_by_email_ci.return_value = None
    admin_repository.get_by_email.return_value = None

    async def _create(user: User) -> User:
        assert user.hashed_password != "SecurePass1!"
        assert verify_password("SecurePass1!", user.hashed_password)
        created.hashed_password = user.hashed_password
        return created

    user_repository.create.side_effect = _create
    response = await service.create_user(_payload())
    assert response.success is True
    assert response.password is None
    assert response.data.password is None
    assert response.email == "jane.coach@example.com"
    assert response.role == "coach"
    assert response.roles == ["coach"]
    assert response.name == "Jane Coach"


@pytest.mark.asyncio
async def test_create_user_duplicate_email_conflict(
    service: UserService,
    user_repository: AsyncMock,
    admin_repository: AsyncMock,
) -> None:
    """Duplicate emails should raise EMAIL_ALREADY_EXISTS."""
    user_repository.get_by_email_ci.return_value = _user()
    admin_repository.get_by_email.return_value = None
    with pytest.raises(ConflictError) as exc_info:
        await service.create_user(_payload())
    assert exc_info.value.error_code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_user_duplicate_super_admin_email_conflict(
    service: UserService,
    user_repository: AsyncMock,
    admin_repository: AsyncMock,
) -> None:
    """Emails already used by Super Admins should also conflict."""
    user_repository.get_by_email_ci.return_value = None
    admin_repository.get_by_email.return_value = _admin()
    with pytest.raises(ConflictError) as exc_info:
        await service.create_user(_payload(email="admin@test.com"))
    assert exc_info.value.error_code == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_user_weak_password_validation_error(
    service: UserService,
    user_repository: AsyncMock,
) -> None:
    """Weak passwords should raise ValidationAppError before persist."""
    with pytest.raises(ValidationAppError):
        await service.create_user(_payload(password="Password1"))
    user_repository.create.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_self_raises_authorization(
    service: UserService,
    user_repository: AsyncMock,
) -> None:
    """Super Admin cannot remove their own account."""
    actor = _admin()
    with pytest.raises(AuthorizationError) as exc_info:
        await service.delete_user(actor.id, actor)
    assert exc_info.value.error_code == "CANNOT_DELETE_OWN_ACCOUNT"
    user_repository.delete.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user_other_success(
    service: UserService,
    user_repository: AsyncMock,
) -> None:
    """Removing another user should return a confirmation envelope."""
    actor = _admin()
    target = _user()
    user_repository.get_by_id.return_value = target
    response = await service.delete_user(target.id, actor)
    assert response.success is True
    assert response.message == "User removed."
    assert response.id == target.id
    user_repository.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_update_user_not_found(
    service: UserService,
    user_repository: AsyncMock,
) -> None:
    """Updating a missing user should raise USER_NOT_FOUND."""
    user_repository.get_by_id.return_value = None
    with pytest.raises(NotFoundError) as exc_info:
        await service.update_user(
            uuid.uuid4(),
            UserUpdate.model_validate(
                {
                    "first_name": "A",
                    "last_name": "B",
                    "email": "ab@example.com",
                    "role": "player",
                }
            ),
        )
    assert exc_info.value.error_code == "USER_NOT_FOUND"
