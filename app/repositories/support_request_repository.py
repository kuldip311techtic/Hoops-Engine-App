"""Support request persistence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.support_request import SupportRequest, SupportRequestStatus


class SupportRequestRepository:
    """All support_requests table queries live here."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def list_all(
        self,
        *,
        status: SupportRequestStatus | None = None,
    ) -> list[SupportRequest]:
        """Return support requests ordered by created_at descending."""
        stmt = (
            select(SupportRequest)
            .options(selectinload(SupportRequest.submitter))
            .order_by(SupportRequest.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(SupportRequest.status == status)
        result = await self._session.execute(stmt)
        return list(result.scalars().unique().all())

    async def count_all(self, *, status: SupportRequestStatus | None = None) -> int:
        """Return the number of support requests."""
        stmt = select(func.count()).select_from(SupportRequest)
        if status is not None:
            stmt = stmt.where(SupportRequest.status == status)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def get_by_id(self, request_id: UUID) -> SupportRequest | None:
        """Return the support request with this id, or None."""
        stmt = (
            select(SupportRequest)
            .options(selectinload(SupportRequest.submitter))
            .where(SupportRequest.id == request_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        subject: str,
        message: str,
        submitter_user_id: UUID | None = None,
        status: SupportRequestStatus = SupportRequestStatus.OPEN,
    ) -> SupportRequest:
        """Insert a support request row and flush so the PK is available."""
        row = SupportRequest(
            subject=subject,
            message=message,
            submitter_user_id=submitter_user_id,
            status=status,
        )
        self._session.add(row)
        await self._session.flush()
        await self._session.refresh(row)
        return row

    async def respond(self, request: SupportRequest, admin_response: str) -> SupportRequest:
        """Record an admin response and mark the request as RESPONDED."""
        now = datetime.now(UTC)
        request.admin_response = admin_response
        request.status = SupportRequestStatus.RESPONDED
        request.responded_at = now
        request.updated_at = now
        await self._session.flush()
        await self._session.refresh(request)
        return request

    async def close(self, request: SupportRequest) -> SupportRequest:
        """Mark the support request as CLOSED."""
        now = datetime.now(UTC)
        request.status = SupportRequestStatus.CLOSED
        request.closed_at = now
        request.updated_at = now
        await self._session.flush()
        await self._session.refresh(request)
        return request
