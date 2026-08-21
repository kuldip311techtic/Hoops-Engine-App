"""Subscription data access."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription import Subscription


class SubscriptionRepository:
    """All subscription SQL lives here."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_email(self, email: str) -> Subscription | None:
        """Return the subscription for this email, if any."""
        stmt = select(Subscription).where(func.lower(Subscription.email) == email.lower())
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_cancelled(
        self,
        *,
        email: str,
        access_until: datetime | None,
        provider_ref: str | None,
        cancelled_at: datetime,
    ) -> Subscription:
        """Mark a subscription cancelled while retaining access until ``access_until``."""
        existing = await self.get_by_email(email)
        if existing is None:
            existing = Subscription(
                email=email.lower(),
                status="cancelled",
                access_until=access_until,
                cancelled_at=cancelled_at,
                provider_ref=provider_ref,
            )
            self._session.add(existing)
        else:
            existing.status = "cancelled"
            existing.access_until = access_until
            existing.cancelled_at = cancelled_at
            if provider_ref:
                existing.provider_ref = provider_ref
        await self._session.flush()
        await self._session.refresh(existing)
        return existing
