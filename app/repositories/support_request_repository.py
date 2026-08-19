"""Support request data access layer."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support_request import SupportRequest


class SupportRequestRepository:
    """Repository for SupportRequest persistence operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize with an async database session."""
        self._session = session

    async def list_paginated(
        self,
        *,
        offset: int,
        limit: int,
    ) -> tuple[list[SupportRequest], int]:
        """Return a newest-first page of support requests and the total count."""
        count_stmt = select(func.count()).select_from(SupportRequest)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        stmt = (
            select(SupportRequest)
            .order_by(SupportRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def get_by_id(self, request_id: uuid.UUID) -> SupportRequest | None:
        """Return a support request by primary key, or None if missing."""
        stmt = select(SupportRequest).where(SupportRequest.id == request_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save(self, support_request: SupportRequest) -> SupportRequest:
        """Commit in-place updates and refresh the support request."""
        await self._session.commit()
        await self._session.refresh(support_request)
        return support_request
