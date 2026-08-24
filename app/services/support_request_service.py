"""Support request admin use-cases."""

from uuid import UUID

from loguru import logger

from app.exceptions.base import AppError, NotFoundError
from app.models.support_request import SupportRequest, SupportRequestStatus
from app.models.user import User
from app.repositories.support_request_repository import SupportRequestRepository
from app.schemas.support_request import SupportRequestResponse


class SupportRequestService:
    """Super Admin operations on user support requests. No HTTP here."""

    def __init__(self, repository: SupportRequestRepository) -> None:
        """Inject the support request repository."""
        self._repository = repository

    @staticmethod
    def _to_response(request: SupportRequest) -> SupportRequestResponse:
        """Map an ORM row to the admin API response DTO."""
        submitter_email = request.submitter.email if request.submitter else None
        return SupportRequestResponse(
            id=request.id,
            request_id=request.id,
            subject=request.subject,
            description=request.message,
            message=request.message,
            status=request.status,
            submitter_email=submitter_email,
            admin_response=request.admin_response,
            created_at=request.created_at,
            updated_at=request.updated_at,
            responded_at=request.responded_at,
            closed_at=request.closed_at,
        )

    async def list_requests(
        self,
        *,
        status: SupportRequestStatus | None = None,
    ) -> tuple[list[SupportRequestResponse], int]:
        """Return all support requests for the admin table."""
        rows = await self._repository.list_all(status=status)
        items = [self._to_response(row) for row in rows]
        return items, len(items)

    async def respond(
        self,
        request_id: UUID,
        response: str,
        *,
        actor: User,
    ) -> SupportRequestResponse:
        """Attach an admin response to a support request."""
        request = await self._repository.get_by_id(request_id)
        if request is None:
            raise NotFoundError(
                "Support request not found",
                code="SUPPORT_REQUEST_NOT_FOUND",
            )
        if request.status == SupportRequestStatus.CLOSED:
            raise AppError(
                "Cannot respond to a closed support request",
                code="SUPPORT_REQUEST_CLOSED",
                status_code=400,
            )
        if (
            request.status == SupportRequestStatus.RESPONDED
            and request.admin_response == response
        ):
            logger.info(
                "support_request_respond_idempotent request_id={} actor_id={}",
                request_id,
                actor.id,
            )
            return self._to_response(request)
        updated = await self._repository.respond(request, response)
        logger.info(
            "support_request_responded request_id={} actor_id={}",
            request_id,
            actor.id,
        )
        return self._to_response(updated)

    async def close(
        self,
        request_id: UUID,
        *,
        actor: User,
    ) -> SupportRequestResponse:
        """Close a support request."""
        request = await self._repository.get_by_id(request_id)
        if request is None:
            raise NotFoundError(
                "Support request not found",
                code="SUPPORT_REQUEST_NOT_FOUND",
            )
        if request.status == SupportRequestStatus.CLOSED:
            logger.info(
                "support_request_close_idempotent request_id={} actor_id={}",
                request_id,
                actor.id,
            )
            return self._to_response(request)
        updated = await self._repository.close(request)
        logger.info(
            "support_request_closed request_id={} actor_id={}",
            request_id,
            actor.id,
        )
        return self._to_response(updated)
