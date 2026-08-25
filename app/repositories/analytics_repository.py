"""Analytics aggregate queries for the Super Admin dashboard."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.organization import Organization
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.subscription_plan import SubscriptionPlan
from app.models.user import User, UserRole


class AnalyticsRepository:
    """Read-only COUNT/SUM queries for dashboard metrics."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def count_active_organizations(self) -> int:
        """Return the number of active organizations."""
        stmt = (
            select(func.count())
            .select_from(Organization)
            .where(Organization.is_active.is_(True))
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_users_by_role(self, role: UserRole) -> int:
        """Return active users with the given role."""
        stmt = (
            select(func.count())
            .select_from(User)
            .where(User.role == role, User.is_active.is_(True))
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def count_active_subscriptions(self) -> int:
        """Return the number of active user billing subscriptions."""
        stmt = (
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.status == SubscriptionStatus.ACTIVE)
        )
        return int((await self._session.execute(stmt)).scalar_one())

    async def sum_published_plan_prices(self) -> Decimal:
        """Return the sum of prices for published subscription plans."""
        stmt = select(func.coalesce(func.sum(SubscriptionPlan.price), 0)).where(
            SubscriptionPlan.is_published.is_(True)
        )
        value = (await self._session.execute(stmt)).scalar_one()
        return Decimal(str(value))
