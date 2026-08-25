"""Subscription plan catalog persistence."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.subscription_plan import BillingCycle, SubscriptionPlan


class SubscriptionPlanRepository:
    """All subscription_plans table queries live here."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def list_all(
        self,
        *,
        published_only: bool = False,
    ) -> list[SubscriptionPlan]:
        """Return plans ordered by name, optionally filtered to published only."""
        stmt = select(SubscriptionPlan).order_by(SubscriptionPlan.name)
        if published_only:
            stmt = stmt.where(SubscriptionPlan.is_published.is_(True))
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        """Return the plan with this id, or None."""
        result = await self._session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def get_by_name(self, name: str) -> SubscriptionPlan | None:
        """Return the plan with this name, or None."""
        result = await self._session.execute(
            select(SubscriptionPlan).where(SubscriptionPlan.name == name)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        name: str,
        price,
        billing_cycle: BillingCycle,
        description: str | None = None,
        is_published: bool = False,
    ) -> SubscriptionPlan:
        """Insert a new subscription plan and flush so the PK is available."""
        plan = SubscriptionPlan(
            name=name,
            description=description,
            price=price,
            billing_cycle=billing_cycle,
            is_published=is_published,
        )
        self._session.add(plan)
        await self._session.flush()
        await self._session.refresh(plan)
        return plan

    async def update(
        self,
        plan: SubscriptionPlan,
        *,
        name: str | None = None,
        description: str | None = None,
        price=None,
        billing_cycle: BillingCycle | None = None,
        is_published: bool | None = None,
    ) -> SubscriptionPlan:
        """Apply partial updates to an existing plan."""
        if name is not None:
            plan.name = name
        if description is not None:
            plan.description = description
        if price is not None:
            plan.price = price
        if billing_cycle is not None:
            plan.billing_cycle = billing_cycle
        if is_published is not None:
            plan.is_published = is_published
        plan.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(plan)
        return plan

    async def unpublish(self, plan: SubscriptionPlan) -> SubscriptionPlan:
        """Soft-remove a plan by marking it unpublished."""
        plan.is_published = False
        plan.updated_at = datetime.now(UTC)
        await self._session.flush()
        await self._session.refresh(plan)
        return plan
