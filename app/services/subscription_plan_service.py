"""Admin subscription plan catalog use-cases."""

from decimal import Decimal
from uuid import UUID

from loguru import logger

from app.exceptions.base import ConflictError, NotFoundError
from app.models.subscription_plan import SubscriptionPlan
from app.repositories.subscription_plan_repository import SubscriptionPlanRepository
from app.schemas.subscription_plan import (
    SubscriptionPlanResponse,
    billing_cycle_api_label,
    normalize_billing_cycle,
    plan_status_label,
)


class SubscriptionPlanService:
    """CRUD operations for the subscription plan catalog. No HTTP here."""

    def __init__(self, plans: SubscriptionPlanRepository) -> None:
        """Inject the subscription plan repository."""
        self._plans = plans

    @staticmethod
    def _to_response(plan: SubscriptionPlan) -> SubscriptionPlanResponse:
        """Map an ORM row to the admin API response DTO."""
        cycle = billing_cycle_api_label(plan.billing_cycle)
        status = plan_status_label(plan.is_published)
        return SubscriptionPlanResponse(
            id=plan.id,
            name=plan.name,
            description=plan.description,
            price=plan.price,
            billing_cycle=cycle,
            duration=cycle,
            status=status,
            is_published=plan.is_published,
            created_at=plan.created_at,
            updated_at=plan.updated_at,
        )

    async def list_plans(
        self,
        *,
        published_only: bool = False,
    ) -> tuple[list[SubscriptionPlanResponse], int]:
        """Return subscription plans for the admin table."""
        rows = await self._plans.list_all(published_only=published_only)
        items = [self._to_response(row) for row in rows]
        return items, len(items)

    async def create_plan(
        self,
        *,
        name: str,
        price: Decimal,
        billing_cycle: str,
        description: str | None = None,
        is_published: bool = False,
    ) -> SubscriptionPlanResponse:
        """Create a plan after verifying the name is unique."""
        existing = await self._plans.get_by_name(name)
        if existing is not None:
            raise ConflictError(
                "A subscription plan with this name already exists",
                code="SUBSCRIPTION_PLAN_ALREADY_EXISTS",
            )
        cycle = normalize_billing_cycle(billing_cycle)
        plan = await self._plans.create(
            name=name,
            description=description,
            price=price,
            billing_cycle=cycle,
            is_published=is_published,
        )
        logger.info(
            "subscription_plan_created plan_id={} name={}",
            plan.id,
            plan.name,
        )
        return self._to_response(plan)

    async def update_plan(
        self,
        plan_id: UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        price: Decimal | None = None,
        billing_cycle: str | None = None,
        is_published: bool | None = None,
    ) -> SubscriptionPlanResponse:
        """Update an existing plan."""
        plan = await self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError(
                "Subscription plan not found",
                code="SUBSCRIPTION_PLAN_NOT_FOUND",
            )
        if name is not None and name != plan.name:
            conflict = await self._plans.get_by_name(name)
            if conflict is not None:
                raise ConflictError(
                    "A subscription plan with this name already exists",
                    code="SUBSCRIPTION_PLAN_ALREADY_EXISTS",
                )
        cycle = normalize_billing_cycle(billing_cycle) if billing_cycle else None
        updated = await self._plans.update(
            plan,
            name=name,
            description=description,
            price=price,
            billing_cycle=cycle,
            is_published=is_published,
        )
        logger.info("subscription_plan_updated plan_id={}", updated.id)
        return self._to_response(updated)

    async def remove_plan(self, plan_id: UUID) -> SubscriptionPlanResponse:
        """Soft-remove a plan by unpublishing it."""
        plan = await self._plans.get_by_id(plan_id)
        if plan is None:
            raise NotFoundError(
                "Subscription plan not found",
                code="SUBSCRIPTION_PLAN_NOT_FOUND",
            )
        updated = await self._plans.unpublish(plan)
        logger.info("subscription_plan_removed plan_id={}", updated.id)
        return self._to_response(updated)
