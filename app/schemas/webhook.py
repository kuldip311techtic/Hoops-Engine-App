"""Webhook payload schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Auth0WebhookPayload(BaseModel):
    """Auth0 event callback body. Extra fields are ignored."""

    model_config = ConfigDict(extra="allow")

    event: str = Field(
        ...,
        description="Auth0 event name",
        examples=["user.blocked"],
    )
    user_email: EmailStr | None = Field(
        default=None,
        description="Email of the affected user when present",
        examples=["admin@example.com"],
    )
    environment: str | None = Field(
        default=None,
        description="sandbox or production",
        examples=["sandbox"],
    )


class BillingWebhookPayload(BaseModel):
    """Billing provider subscription update."""

    user_email: EmailStr = Field(
        ...,
        description="User whose subscription changed",
        examples=["player@example.com"],
    )
    status: str = Field(
        ...,
        description="ACTIVE, CANCELLED, or EXPIRED",
        examples=["CANCELLED"],
    )
    current_period_end: datetime = Field(
        ...,
        description="End of the current billing period (UTC)",
    )
