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

_BILLING_CYCLE_API_LABELS = {
    BillingCycle.MONTHLY: "monthly",
    BillingCycle.YEARLY: "yearly",
}


def normalize_billing_cycle(value: str | BillingCycle) -> BillingCycle:
    """Accept enum values or human-readable labels (e.g. monthly, Monthly)."""
    if isinstance(value, BillingCycle):
        return value
    key = value.strip().lower()
    if key in _BILLING_CYCLE_ALIASES:
        return _BILLING_CYCLE_ALIASES[key]
    try:
        return BillingCycle(value.upper())
    except ValueError as exc:
        raise ValueError(
            "billing_cycle must be monthly or yearly"
        ) from exc


def billing_cycle_api_label(cycle: BillingCycle) -> str:
    """Return the API-facing billing cycle label (lowercase)."""
    return _BILLING_CYCLE_API_LABELS[cycle]


def plan_status_label(is_published: bool) -> str:
    """Return a UI-friendly plan status for the admin table."""
    return "published" if is_published else "unpublished"


class SubscriptionPlanCreateRequest(BaseModel):
    """Payload for creating a subscription plan."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Basic Plan",
                "description": "Entry tier for small organizations.",
                "price": 9.99,
                "billing_cycle": "monthly",
                "is_published": True,
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique plan name shown in the admin UI.",
        examples=["Basic Plan"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional marketing or internal description for the plan.",
        examples=["Entry tier for small organizations."],
    )
    price: Decimal = Field(
        ...,
        gt=0,
        description="Plan price in USD.",
        examples=[9.99],
    )
    billing_cycle: str = Field(
        ...,
        description="Billing interval: monthly or yearly (aliases: annual, month, year).",
        examples=["monthly"],
        json_schema_extra={"enum": ["monthly", "yearly", "annual", "month", "year"]},
    )
    is_published: bool = Field(
        default=False,
        description=(
            "When true the plan is visible to end users. Defaults to false until "
            "explicitly published."
        ),
        examples=[True],
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Strip surrounding whitespace from the plan name."""
        return value.strip()

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
                "name": "Basic Plan Plus",
                "price": 14.99,
                "billing_cycle": "yearly",
                "is_published": True,
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated plan name. Must remain unique.",
        examples=["Basic Plan Plus"],
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
        examples=[14.99],
    )
    billing_cycle: str | None = Field(
        default=None,
        description="Updated billing interval: monthly or yearly (aliases: annual, month, year).",
        examples=["yearly"],
        json_schema_extra={"enum": ["monthly", "yearly", "annual", "month", "year"]},
    )
    is_published: bool | None = Field(
        default=None,
        description="Publish or unpublish the plan for end-user visibility.",
        examples=[True],
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        """Strip surrounding whitespace when provided."""
        if value is None:
            return None
        return value.strip()

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
        examples=["Basic Plan"],
    )
    description: str | None = Field(
        default=None,
        description="Optional plan description.",
        examples=["Entry tier for small organizations."],
    )
    price: Decimal = Field(
        ...,
        description="Plan price in USD.",
        examples=[9.99],
    )
    billing_cycle: str = Field(
        ...,
        description="Billing interval in lowercase (monthly or yearly).",
        examples=["monthly"],
    )
    duration: str = Field(
        ...,
        description="Alias of billing_cycle for Admin FE table bindings.",
        examples=["monthly"],
    )
    status: str = Field(
        ...,
        description="Plan visibility status: published or unpublished.",
        examples=["published"],
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


class SubscriptionPlanListData(BaseModel):
    """Subscription plan list payload."""

    items: list[SubscriptionPlanResponse] = Field(
        default_factory=list,
        description="Subscription plans ordered by name.",
    )
    total: int = Field(..., description="Total plans returned.", examples=[3])


class SubscriptionPlanActionData(BaseModel):
    """Single subscription plan returned from write operations."""

    subscription_plan: SubscriptionPlanResponse = Field(
        ...,
        description="Affected subscription plan record.",
    )


class SubscriptionPlanActionResponse(AdminSuccessResponse):
    """Success envelope for subscription plan write operations."""

    data: SubscriptionPlanActionData


class SubscriptionPlanListResponse(AdminSuccessResponse):
    """List of subscription plans in the standard success envelope."""

    data: SubscriptionPlanListData
