"""Unit tests for SupportRequestService."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.exceptions.base import AppError, NotFoundError
from app.models.support_request import SupportRequest, SupportRequestStatus
from app.models.user import User, UserRole
from app.services.support_request_service import SupportRequestService
from tests.fakes import InMemorySupportRequestRepository


@pytest.fixture
def support_requests() -> InMemorySupportRequestRepository:
    """Empty in-memory support request repository."""
    return InMemorySupportRequestRepository()


@pytest.fixture
def service(support_requests: InMemorySupportRequestRepository) -> SupportRequestService:
    """SupportRequestService bound to in-memory repository."""
    return SupportRequestService(support_requests)


@pytest.fixture
def admin_actor() -> User:
    """Super Admin actor for service calls."""
    return User(
        email="admin@test.com",
        password_hash="hash",
        role=UserRole.SUPER_ADMIN,
        token_version=1,
        is_active=True,
    )


@pytest.fixture
def open_request(support_requests: InMemorySupportRequestRepository) -> SupportRequest:
    """Seed an OPEN support request."""
    now = datetime.now(UTC)
    return support_requests.add(
        SupportRequest(
            id=uuid4(),
            subject="Help",
            message="Need assistance",
            status=SupportRequestStatus.OPEN,
            created_at=now,
            updated_at=now,
        )
    )


@pytest.mark.asyncio
async def test_list_requests_empty(service: SupportRequestService) -> None:
    """Empty repository returns an empty list."""
    items, total = await service.list_requests()
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_respond_to_open_request(
    service: SupportRequestService,
    open_request: SupportRequest,
    admin_actor: User,
) -> None:
    """Responding to an OPEN request sets RESPONDED status."""
    result = await service.respond(
        open_request.id,
        "Thank you for your inquiry!",
        actor=admin_actor,
    )
    assert result.status == SupportRequestStatus.RESPONDED
    assert result.admin_response == "Thank you for your inquiry!"
    assert result.responded_at is not None


@pytest.mark.asyncio
async def test_respond_not_found_raises_not_found(
    service: SupportRequestService,
    admin_actor: User,
) -> None:
    """Missing request raises NotFoundError."""
    with pytest.raises(NotFoundError) as exc:
        await service.respond(uuid4(), "Hello", actor=admin_actor)
    assert exc.value.code == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_respond_to_closed_raises_bad_request(
    service: SupportRequestService,
    support_requests: InMemorySupportRequestRepository,
    admin_actor: User,
) -> None:
    """Cannot respond to a CLOSED request."""
    now = datetime.now(UTC)
    closed = support_requests.add(
        SupportRequest(
            id=uuid4(),
            subject="Closed",
            message="Done",
            status=SupportRequestStatus.CLOSED,
            created_at=now,
            updated_at=now,
            closed_at=now,
        )
    )
    with pytest.raises(AppError) as exc:
        await service.respond(closed.id, "Too late", actor=admin_actor)
    assert exc.value.code == "SUPPORT_REQUEST_CLOSED"
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_close_open_request(
    service: SupportRequestService,
    open_request: SupportRequest,
    admin_actor: User,
) -> None:
    """Closing an OPEN request sets CLOSED status."""
    result = await service.close(open_request.id, actor=admin_actor)
    assert result.status == SupportRequestStatus.CLOSED
    assert result.closed_at is not None


@pytest.mark.asyncio
async def test_close_not_found_raises_not_found(
    service: SupportRequestService,
    admin_actor: User,
) -> None:
    """Missing request on close raises NotFoundError."""
    with pytest.raises(NotFoundError) as exc:
        await service.close(uuid4(), actor=admin_actor)
    assert exc.value.code == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_close_already_closed_is_idempotent(
    service: SupportRequestService,
    support_requests: InMemorySupportRequestRepository,
    admin_actor: User,
) -> None:
    """Closing an already CLOSED request returns the same row."""
    now = datetime.now(UTC)
    closed = support_requests.add(
        SupportRequest(
            id=uuid4(),
            subject="Closed",
            message="Done",
            status=SupportRequestStatus.CLOSED,
            created_at=now,
            updated_at=now,
            closed_at=now,
        )
    )
    result = await service.close(closed.id, actor=admin_actor)
    assert result.status == SupportRequestStatus.CLOSED
