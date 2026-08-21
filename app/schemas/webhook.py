"""Webhook payload schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Auth0WebhookPayload(BaseModel):
    """Auth0 event callback body. Extra fields are ignored."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "example": {
                "event": "user.blocked",
                "user_email": "player@example.com",
                "environment": "sandbox",
            }
        },
    )

    event: str = Field(
        ...,
        min_length=1,
        description="Auth0 event name (for example user.blocked). Unknown events are acknowledged.",
        examples=["user.blocked"],
    )
    user_email: EmailStr | None = Field(
        default=None,
        description="Email of the affected user when present.",
        examples=["admin@example.com"],
    )
    environment: str | None = Field(
        default=None,
        description="sandbox or production. Used with AUTH0_SANDBOX_DOMAIN vs AUTH0_DOMAIN.",
        examples=["sandbox"],
    )


class BillingWebhookPayload(BaseModel):
    """Billing provider subscription update."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "user_email": "player@example.com",
                "status": "CANCELLED",
                "current_period_end": "2099-01-01T00:00:00Z",
            }
        }
    )

    user_email: EmailStr = Field(
        ...,
        description="User whose subscription changed.",
        examples=["player@example.com"],
    )
    status: str = Field(
        ...,
        min_length=1,
        description="ACTIVE, CANCELLED, or EXPIRED. Other values are stored as EXPIRED.",
        examples=["CANCELLED"],
    )
    current_period_end: datetime = Field(
        ...,
        description="End of the current billing period (UTC). Cancelled users retain access until this instant.",
        examples=["2099-01-01T00:00:00Z"],
    )
