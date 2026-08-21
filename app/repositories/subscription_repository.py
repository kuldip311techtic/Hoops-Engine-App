"""Subscription persistence."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription, SubscriptionStatus


class SubscriptionRepository:
    """All subscription table queries live here."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        """Return the subscription for ``user_id``, or None."""
        result = await self._session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        *,
        user_id: UUID,
        status: SubscriptionStatus,
        current_period_end: datetime,
        cancelled_at: datetime | None = None,
    ) -> Subscription:
        """Create or update the subscription row for ``user_id``."""
        existing = await self.get_by_user_id(user_id)
        if existing is None:
            existing = Subscription(
                user_id=user_id,
                status=status,
                current_period_end=current_period_end,
                cancelled_at=cancelled_at,
            )
            self._session.add(existing)
        else:
            existing.status = status
            existing.current_period_end = current_period_end
            existing.cancelled_at = cancelled_at
        await self._session.flush()
        return existing
