"""Unit tests for support request management service."""

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.exceptions.base import ConflictError, NotFoundError, ValidationAppError
from app.models.support_request import SupportRequest
from app.schemas.support_request import SupportRequestRespondRequest
from app.services.support_request_service import SupportRequestService


def _row(**overrides: object) -> SupportRequest:
    """Build a SupportRequest ORM instance."""
    values: dict = {
        "id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "user_name": "Jane Player",
        "request": "I cannot log in to my player account.",
        "response": None,
        "status": "open",
        "created_at": datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
        "updated_at": datetime(2026, 8, 19, 12, 0, tzinfo=UTC),
    }
    values.update(overrides)
    return SupportRequest(**values)


@pytest.fixture
def repository() -> AsyncMock:
    """Provide a mocked SupportRequestRepository."""
    return AsyncMock()


@pytest.fixture
def service(repository: AsyncMock) -> SupportRequestService:
    """Provide a SupportRequestService with a mocked repository."""
    return SupportRequestService(repository)


@pytest.mark.asyncio
async def test_list_support_requests(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """List should map rows into the frontend envelope including name and status."""
    row = _row()
    repository.list_paginated.return_value = ([row], 1)
    response = await service.list_support_requests(page=1, page_size=20)
    assert response.success is True
    assert response.data.total == 1
    assert response.data.items[0].id == row.id
    assert response.data.items[0].name == "Jane Player"
    assert response.data.items[0].description == row.request
    assert response.data.items[0].status == "open"
    assert response.error is None


@pytest.mark.asyncio
async def test_list_support_requests_empty(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """An empty catalog should still return a success envelope."""
    repository.list_paginated.return_value = ([], 0)
    response = await service.list_support_requests(page=1, page_size=20)
    assert response.data.items == []
    assert response.data.total == 0


@pytest.mark.asyncio
async def test_respond_success(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """A valid response should set status to responded."""
    row = _row()
    repository.get_by_id.return_value = row
    repository.save.return_value = row
    payload = SupportRequestRespondRequest(
        id=row.id,
        response="Please try resetting your password.",
    )
    response = await service.respond_to_support_request(payload)
    assert response.success is True
    assert response.status == "responded"
    assert response.data.response == "Please try resetting your password."
    assert row.status == "responded"
    repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_respond_empty_raises_validation(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """Whitespace-only responses should raise ValidationAppError."""
    payload = SupportRequestRespondRequest.model_construct(
        id=uuid.uuid4(),
        response="   ",
    )
    with pytest.raises(ValidationAppError) as exc_info:
        await service.respond_to_support_request(payload)
    assert exc_info.value.error_code == "VALIDATION_ERROR"
    repository.save.assert_not_called()


@pytest.mark.asyncio
async def test_respond_not_found(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """Responding to a missing request should raise NotFoundError."""
    repository.get_by_id.return_value = None
    payload = SupportRequestRespondRequest(
        id=uuid.uuid4(),
        response="We are looking into this.",
    )
    with pytest.raises(NotFoundError) as exc_info:
        await service.respond_to_support_request(payload)
    assert exc_info.value.error_code == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_respond_to_closed_conflict(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """Responding to a closed request should raise ConflictError."""
    row = _row(status="closed")
    repository.get_by_id.return_value = row
    payload = SupportRequestRespondRequest(
        id=row.id,
        response="Too late to reply.",
    )
    with pytest.raises(ConflictError) as exc_info:
        await service.respond_to_support_request(payload)
    assert exc_info.value.error_code == "SUPPORT_REQUEST_CLOSED"
    repository.save.assert_not_called()


@pytest.mark.asyncio
async def test_close_sets_status_and_confirmation_message(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """Close should set status=closed and return a confirmation message."""
    row = _row(status="open")
    repository.get_by_id.return_value = row
    repository.save.return_value = row
    response = await service.close_support_request(row.id)
    assert response.success is True
    assert response.message == "Support request closed."
    assert response.description
    assert response.status == "closed"
    assert response.id == row.id
    assert response.name == "Jane Player"
    repository.save.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_already_closed_is_idempotent(
    service: SupportRequestService,
    repository: AsyncMock,
) -> None:
    """Closing an already-closed request should still confirm success."""
    row = _row(status="closed")
    repository.get_by_id.return_value = row
    response = await service.close_support_request(row.id)
    assert response.message == "Support request closed."
    assert response.status == "closed"
    repository.save.assert_not_called()
