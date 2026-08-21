"""Subscription plan admin service unit tests (JAW-9465)."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.exceptions.base import ConflictError, NotFoundError
from app.models.subscription_plan import BillingCycle
from app.services.subscription_plan_service import SubscriptionPlanService
from tests.fakes import InMemorySubscriptionPlanRepository


@pytest.fixture
def plans() -> InMemorySubscriptionPlanRepository:
    """Empty in-memory plan repository."""
    return InMemorySubscriptionPlanRepository()


@pytest.fixture
def service(plans: InMemorySubscriptionPlanRepository) -> SubscriptionPlanService:
    """SubscriptionPlanService bound to in-memory plans."""
    return SubscriptionPlanService(plans)


@pytest.mark.asyncio
async def test_create_plan_success(service: SubscriptionPlanService) -> None:
    """Creating a plan returns the mapped response."""
    result = await service.create_plan(
        name="Starter",
        price=Decimal("19.99"),
        billing_cycle="Monthly",
        description="Entry tier",
        is_published=True,
    )
    assert result.name == "Starter"
    assert result.price == Decimal("19.99")
    assert result.billing_cycle == "Monthly"
    assert result.is_published is True
    assert result.description == "Entry tier"


@pytest.mark.asyncio
async def test_create_plan_duplicate_name_conflict(
    service: SubscriptionPlanService,
) -> None:
    """Duplicate plan names raise SUBSCRIPTION_PLAN_ALREADY_EXISTS."""
    await service.create_plan(
        name="Starter",
        price=Decimal("19.99"),
        billing_cycle="Monthly",
    )
    with pytest.raises(ConflictError) as exc:
        await service.create_plan(
            name="Starter",
            price=Decimal("29.99"),
            billing_cycle="Yearly",
        )
    assert exc.value.code == "SUBSCRIPTION_PLAN_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_plan_not_found(service: SubscriptionPlanService) -> None:
    """Updating a missing plan raises SUBSCRIPTION_PLAN_NOT_FOUND."""
    with pytest.raises(NotFoundError) as exc:
        await service.update_plan(uuid4(), name="Missing")
    assert exc.value.code == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_plan_sets_unpublished(
    service: SubscriptionPlanService,
) -> None:
    """Removing a plan unpublishes it."""
    created = await service.create_plan(
        name="Pro",
        price=Decimal("29.99"),
        billing_cycle="Monthly",
        is_published=True,
    )
    removed = await service.remove_plan(created.id)
    assert removed.is_published is False


@pytest.mark.asyncio
async def test_list_plans_published_only_filter(
    service: SubscriptionPlanService,
    plans: InMemorySubscriptionPlanRepository,
) -> None:
    """published_only returns only published catalog rows."""
    await plans.create(
        name="Public Plan",
        price=Decimal("10.00"),
        billing_cycle=BillingCycle.MONTHLY,
        is_published=True,
    )
    await plans.create(
        name="Draft Plan",
        price=Decimal("20.00"),
        billing_cycle=BillingCycle.YEARLY,
        is_published=False,
    )
    published = await service.list_plans(published_only=True)
    assert len(published) == 1
    assert published[0].name == "Public Plan"
