"""Webhook request bodies (Auth0 and billing)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Auth0WebhookRequest(BaseModel):
    """Auth0 event callback payload."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(
        ...,
        description="Auth0 event type",
        examples=["scim.user.updated"],
    )
    email: EmailStr | None = Field(
        default=None,
        description="User email when present on the event",
        examples=["admin@example.com"],
    )
    user_id: str | None = Field(
        default=None,
        description="Auth0 user id",
        examples=["auth0|abc123"],
    )
    description: str | None = Field(
        default=None,
        description="Optional event description",
        examples=["User password changed"],
    )


class BillingWebhookRequest(BaseModel):
    """Billing provider subscription event."""

    type: str = Field(
        ...,
        description="Event type from the billing provider",
        examples=["customer.subscription.deleted"],
    )
    email: EmailStr = Field(
        ...,
        description="Account email the subscription belongs to",
        examples=["coach@example.com"],
    )
    access_until: datetime | None = Field(
        default=None,
        description="When cancelled, access remains until this instant (end of billing cycle)",
        examples=["2026-09-01T00:00:00Z"],
    )
    description: str | None = Field(
        default=None,
        description="Optional event description",
        examples=["Subscription cancelled; access retained until period end"],
    )
    provider_ref: str | None = Field(
        default=None,
        description="Provider subscription id",
        examples=["sub_123"],
    )


class WebhookAckData(BaseModel):
    """Acknowledged webhook processing result."""

    accepted: bool = Field(default=True)
    type: str
    email: str | None = None
    description: str | None = None
    message: str
    error: None = None


class WebhookAckResponse(BaseModel):
    """Success envelope for webhook endpoints."""

    success: Literal[True] = True
    message: str
    data: WebhookAckData
