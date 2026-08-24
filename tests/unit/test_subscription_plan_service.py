"""Unit tests for SubscriptionPlanService."""

from decimal import Decimal
from uuid import uuid4

import pytest

from app.exceptions.base import ConflictError, NotFoundError
from app.models.subscription_plan import BillingCycle
from app.services.subscription_plan_service import SubscriptionPlanService
from tests.fakes import InMemorySubscriptionPlanRepository


@pytest.fixture
def plans() -> InMemorySubscriptionPlanRepository:
    """Empty in-memory subscription plan repository."""
    return InMemorySubscriptionPlanRepository()


@pytest.fixture
def service(plans: InMemorySubscriptionPlanRepository) -> SubscriptionPlanService:
    """SubscriptionPlanService bound to in-memory plans."""
    return SubscriptionPlanService(plans)


@pytest.mark.asyncio
async def test_list_plans_success(
    service: SubscriptionPlanService,
    plans: InMemorySubscriptionPlanRepository,
) -> None:
    """Listing plans returns FE-friendly fields."""
    await plans.create(
        name="Basic Plan",
        price=Decimal("9.99"),
        billing_cycle=BillingCycle.MONTHLY,
        is_published=True,
    )
    items, total = await service.list_plans()
    assert total == 1
    plan = items[0]
    assert plan.name == "Basic Plan"
    assert plan.billing_cycle == "monthly"
    assert plan.duration == "monthly"
    assert plan.status == "published"


@pytest.mark.asyncio
async def test_create_plan_success(service: SubscriptionPlanService) -> None:
    """Creating a plan returns the expected response shape."""
    result = await service.create_plan(
        name="Basic Plan",
        price=Decimal("9.99"),
        billing_cycle="monthly",
        description="Entry tier",
        is_published=True,
    )
    assert result.name == "Basic Plan"
    assert result.price == Decimal("9.99")
    assert result.billing_cycle == "monthly"
    assert result.duration == "monthly"
    assert result.status == "published"
    assert result.description == "Entry tier"


@pytest.mark.asyncio
async def test_create_duplicate_name_raises_conflict(
    service: SubscriptionPlanService,
) -> None:
    """Duplicate plan names raise SUBSCRIPTION_PLAN_ALREADY_EXISTS."""
    await service.create_plan(
        name="Basic Plan",
        price=Decimal("9.99"),
        billing_cycle="monthly",
    )
    with pytest.raises(ConflictError) as exc_info:
        await service.create_plan(
            name="Basic Plan",
            price=Decimal("19.99"),
            billing_cycle="yearly",
        )
    assert exc_info.value.code == "SUBSCRIPTION_PLAN_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_plan_success(service: SubscriptionPlanService) -> None:
    """Updating a plan returns updated fields."""
    created = await service.create_plan(
        name="Basic Plan",
        price=Decimal("9.99"),
        billing_cycle="monthly",
    )
    result = await service.update_plan(
        created.id,
        price=Decimal("14.99"),
        billing_cycle="yearly",
    )
    assert result.price == Decimal("14.99")
    assert result.billing_cycle == "yearly"
    assert result.duration == "yearly"


@pytest.mark.asyncio
async def test_update_plan_not_found(service: SubscriptionPlanService) -> None:
    """Updating unknown plan raises SUBSCRIPTION_PLAN_NOT_FOUND."""
    with pytest.raises(NotFoundError) as exc_info:
        await service.update_plan(uuid4(), name="Missing")
    assert exc_info.value.code == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_remove_plan_unpublishes(service: SubscriptionPlanService) -> None:
    """Removing a plan unpublishes it."""
    created = await service.create_plan(
        name="Basic Plan",
        price=Decimal("9.99"),
        billing_cycle="monthly",
        is_published=True,
    )
    result = await service.remove_plan(created.id)
    assert result.is_published is False
    assert result.status == "unpublished"


@pytest.mark.asyncio
async def test_remove_plan_not_found(service: SubscriptionPlanService) -> None:
    """Removing unknown plan raises SUBSCRIPTION_PLAN_NOT_FOUND."""
    with pytest.raises(NotFoundError) as exc_info:
        await service.remove_plan(uuid4())
    assert exc_info.value.code == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_billing_cycle_normalization_monthly(
    service: SubscriptionPlanService,
) -> None:
    """Monthly aliases normalize to lowercase monthly in the response."""
    result = await service.create_plan(
        name="Monthly Plan",
        price=Decimal("9.99"),
        billing_cycle="Monthly",
    )
    assert result.billing_cycle == "monthly"


@pytest.mark.asyncio
async def test_billing_cycle_normalization_yearly(
    service: SubscriptionPlanService,
) -> None:
    """Yearly aliases normalize to lowercase yearly in the response."""
    result = await service.create_plan(
        name="Yearly Plan",
        price=Decimal("99.99"),
        billing_cycle="annual",
    )
    assert result.billing_cycle == "yearly"


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
    items, total = await service.list_plans(published_only=True)
    assert total == 1
    assert items[0].name == "Public Plan"
