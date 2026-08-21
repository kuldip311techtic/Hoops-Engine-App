"""Admin subscription plan request and response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.subscription_plan import BillingCycle
from app.schemas.common import AdminSuccessResponse

_BILLING_CYCLE_ALIASES = {
    "monthly": BillingCycle.MONTHLY,
    "yearly": BillingCycle.YEARLY,
    "annual": BillingCycle.YEARLY,
    "month": BillingCycle.MONTHLY,
    "year": BillingCycle.YEARLY,
}

_BILLING_CYCLE_LABELS = {
    BillingCycle.MONTHLY: "Monthly",
    BillingCycle.YEARLY: "Yearly",
}


def normalize_billing_cycle(value: str | BillingCycle) -> BillingCycle:
    """Accept enum values or human-readable labels (e.g. Monthly)."""
    if isinstance(value, BillingCycle):
        return value
    key = value.strip().lower()
    if key in _BILLING_CYCLE_ALIASES:
        return _BILLING_CYCLE_ALIASES[key]
    try:
        return BillingCycle(value.upper())
    except ValueError as exc:
        raise ValueError(
            "billing_cycle must be Monthly or Yearly"
        ) from exc


class SubscriptionPlanCreateRequest(BaseModel):
    """Payload for creating a subscription plan."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Pro Coach",
                "description": "Full access for coaching teams.",
                "price": 29.99,
                "billing_cycle": "Monthly",
                "is_published": True,
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique plan name shown in the admin UI.",
        examples=["Pro Coach"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional marketing or internal description for the plan.",
        examples=["Full access for coaching teams."],
    )
    price: Decimal = Field(
        ...,
        gt=0,
        description="Plan price in USD.",
        examples=[29.99],
    )
    billing_cycle: str = Field(
        ...,
        description="Billing interval: Monthly or Yearly.",
        examples=["Monthly"],
    )
    is_published: bool = Field(
        default=False,
        description=(
            "When true the plan is visible to end users. Defaults to false until "
            "explicitly published."
        ),
        examples=[True],
    )

    @field_validator("billing_cycle")
    @classmethod
    def validate_billing_cycle(cls, value: str) -> str:
        """Normalize billing cycle input."""
        normalize_billing_cycle(value)
        return value.strip()


class SubscriptionPlanUpdateRequest(BaseModel):
    """Partial update payload for a subscription plan."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Pro Coach Plus",
                "price": 39.99,
                "billing_cycle": "Yearly",
                "is_published": True,
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated plan name. Must remain unique.",
        examples=["Pro Coach Plus"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated plan description.",
        examples=["Annual billing with premium support."],
    )
    price: Decimal | None = Field(
        default=None,
        gt=0,
        description="Updated plan price in USD.",
        examples=[39.99],
    )
    billing_cycle: str | None = Field(
        default=None,
        description="Updated billing interval: Monthly or Yearly.",
        examples=["Yearly"],
    )
    is_published: bool | None = Field(
        default=None,
        description="Publish or unpublish the plan for end-user visibility.",
        examples=[True],
    )

    @field_validator("billing_cycle")
    @classmethod
    def validate_billing_cycle(cls, value: str | None) -> str | None:
        """Normalize billing cycle when provided."""
        if value is None:
            return None
        normalize_billing_cycle(value)
        return value.strip()


class SubscriptionPlanResponse(BaseModel):
    """Subscription plan returned to the Admin FE."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Plan primary key.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    name: str = Field(
        ...,
        description="Plan display name.",
        examples=["Pro Coach"],
    )
    description: str | None = Field(
        default=None,
        description="Optional plan description.",
        examples=["Full access for coaching teams."],
    )
    price: Decimal = Field(
        ...,
        description="Plan price in USD.",
        examples=[29.99],
    )
    billing_cycle: str = Field(
        ...,
        description="Human-readable billing interval.",
        examples=["Monthly"],
    )
    is_published: bool = Field(
        ...,
        description="True when the plan is visible to end users.",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the plan was created.",
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp when the plan was last updated.",
    )


class SubscriptionPlanListResponse(AdminSuccessResponse):
    """List of subscription plans in the standard success envelope."""

    data: dict[str, list[SubscriptionPlanResponse]]


def billing_cycle_label(cycle: BillingCycle) -> str:
    """Return a UI-friendly billing cycle label."""
    return _BILLING_CYCLE_LABELS[cycle]
