"""Support request management business logic."""

import uuid
from typing import cast

from app.core.logging import logger
from app.exceptions.base import ConflictError, NotFoundError, ValidationAppError
from app.models.support_request import SupportRequest
from app.repositories.support_request_repository import SupportRequestRepository
from app.schemas.support_request import (
    SupportRequestCloseResponse,
    SupportRequestListData,
    SupportRequestListResponse,
    SupportRequestRead,
    SupportRequestRespondRequest,
    SupportRequestResponse,
    SupportRequestStatus,
)


def _to_read(row: SupportRequest) -> SupportRequestRead:
    """Map a SupportRequest ORM instance to the public read schema."""
    status = cast(
        SupportRequestStatus,
        row.status if row.status in ("open", "responded", "closed") else "open",
    )
    return SupportRequestRead(
        id=row.id,
        user_id=row.user_id,
        name=row.user_name,
        user_name=row.user_name,
        request=row.request,
        description=row.request,
        response=row.response,
        status=status,
        submitted_at=row.created_at,
        created_at=row.created_at,
    )


def _item_envelope(
    row: SupportRequest,
    message: str,
    description: str,
) -> SupportRequestResponse:
    """Build the frontend-facing single-item success envelope."""
    payload = _to_read(row)
    return SupportRequestResponse(
        success=True,
        message=message,
        description=description,
        email=None,
        token=None,
        support_request=payload,
        id=payload.id,
        name=payload.name,
        status=payload.status,
        error=None,
        data=payload,
    )


class SupportRequestService:
    """Service for Super Admin support request workflows."""

    def __init__(self, repository: SupportRequestRepository) -> None:
        """Initialize with a SupportRequest repository."""
        self._repository = repository

    async def list_support_requests(
        self,
        *,
        page: int,
        page_size: int,
    ) -> SupportRequestListResponse:
        """Return a paginated list of support requests, newest first."""
        offset = (page - 1) * page_size
        rows, total = await self._repository.list_paginated(
            offset=offset,
            limit=page_size,
        )
        items = [_to_read(row) for row in rows]
        return SupportRequestListResponse(
            success=True,
            message="Support requests retrieved.",
            description="Support request list loaded.",
            email=None,
            token=None,
            support_request=None,
            id=None,
            name=None,
            status=None,
            error=None,
            data=SupportRequestListData(
                items=items,
                total=total,
                page=page,
                page_size=page_size,
            ),
        )

    async def respond_to_support_request(
        self,
        payload: SupportRequestRespondRequest,
    ) -> SupportRequestResponse:
        """Save a Super Admin response on an open or previously answered request."""
        response_text = payload.response.strip()
        if not response_text:
            logger.warning("Rejected empty support request response")
            raise ValidationAppError(
                message="Response is required.",
                error_code="VALIDATION_ERROR",
                details=[
                    {
                        "field": "response",
                        "message": "Response is required.",
                    }
                ],
            )
        row = await self._get_or_404(payload.id)
        if row.status == "closed":
            logger.warning(
                "Attempted to respond to closed support request id={}",
                row.id,
            )
            raise ConflictError(
                message="Cannot respond to a closed support request.",
                error_code="SUPPORT_REQUEST_CLOSED",
                details={"status": "closed"},
            )
        row.response = response_text
        row.status = "responded"
        saved = await self._repository.save(row)
        logger.info("Support request responded id={}", saved.id)
        return _item_envelope(
            saved,
            message="Support request updated.",
            description="Your response was saved.",
        )

    async def close_support_request(
        self,
        request_id: uuid.UUID,
    ) -> SupportRequestCloseResponse:
        """Mark a support request closed and return a confirmation envelope."""
        row = await self._get_or_404(request_id)
        if row.status != "closed":
            row.status = "closed"
            row = await self._repository.save(row)
        else:
            logger.info("Support request already closed id={}", row.id)
        logger.info("Support request closed id={}", row.id)
        payload = _to_read(row)
        return SupportRequestCloseResponse(
            success=True,
            message="Support request closed.",
            description="The support request was closed successfully.",
            email=None,
            token=None,
            support_request=payload,
            id=payload.id,
            name=payload.name,
            status="closed",
            error=None,
            data=payload,
        )

    async def _get_or_404(self, request_id: uuid.UUID) -> SupportRequest:
        """Load a support request or raise NotFoundError."""
        row = await self._repository.get_by_id(request_id)
        if row is None:
            raise NotFoundError(
                message="Support request not found.",
                error_code="SUPPORT_REQUEST_NOT_FOUND",
            )
        return row
