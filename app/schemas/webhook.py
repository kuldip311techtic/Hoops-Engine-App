"""Webhook request bodies (Auth0 and billing)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Auth0WebhookRequest(BaseModel):
    """Auth0 event callback payload."""

    model_config = ConfigDict(
        extra="allow",
        json_schema_extra={
            "examples": [
                {
                    "type": "scim.user.updated",
                    "email": "admin@example.com",
                    "user_id": "auth0|abc123",
                    "description": "User password changed",
                }
            ]
        },
    )

    type: str = Field(
        ...,
        description="Auth0 event type",
        examples=["scim.user.updated"],
        min_length=1,
        max_length=128,
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
        max_length=255,
    )
    description: str | None = Field(
        default=None,
        description="Optional event description",
        examples=["User password changed"],
        max_length=1024,
    )


class BillingWebhookRequest(BaseModel):
    """Billing provider subscription event."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "type": "customer.subscription.deleted",
                    "email": "coach@example.com",
                    "access_until": "2026-09-01T00:00:00Z",
                    "description": (
                        "Subscription cancelled; access retained until period end"
                    ),
                    "provider_ref": "sub_123",
                }
            ]
        }
    )

    type: str = Field(
        ...,
        description="Event type from the billing provider",
        examples=["customer.subscription.deleted"],
        min_length=1,
        max_length=128,
    )
    email: EmailStr = Field(
        ...,
        description="Account email the subscription belongs to",
        examples=["coach@example.com"],
    )
    access_until: datetime | None = Field(
        default=None,
        description=(
            "When cancelled, access remains until this instant "
            "(end of the billing cycle)"
        ),
        examples=["2026-09-01T00:00:00Z"],
    )
    description: str | None = Field(
        default=None,
        description="Optional event description",
        examples=["Subscription cancelled; access retained until period end"],
        max_length=1024,
    )
    provider_ref: str | None = Field(
        default=None,
        description="Provider subscription id",
        examples=["sub_123"],
        max_length=255,
    )


class WebhookAckData(BaseModel):
    """Acknowledged webhook processing result."""

    accepted: bool = Field(
        default=True,
        description="True when the event was verified and accepted",
        examples=[True],
    )
    type: str = Field(
        ...,
        description="Echo of the inbound event type",
        examples=["customer.subscription.deleted"],
    )
    email: str | None = Field(
        default=None,
        description="Account email from the payload when present",
        examples=["coach@example.com"],
    )
    description: str | None = Field(
        default=None,
        description="Human-readable processing note for operators",
        examples=[
            "Subscription cancelled; access retained until the end of the billing cycle"
        ],
    )
    message: str = Field(
        ...,
        description="UI-safe acknowledgement message",
        examples=["Billing event accepted"],
    )
    error: None = Field(
        default=None,
        description="Always null on success; failures use the error envelope",
        examples=[None],
    )
    password: str = Field(
        default="",
        description="Always empty. Passwords are never returned by this API.",
        examples=[""],
    )


class WebhookAckResponse(BaseModel):
    """Success envelope for webhook endpoints."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "message": "Billing event accepted",
                    "data": {
                        "accepted": True,
                        "type": "customer.subscription.deleted",
                        "email": "coach@example.com",
                        "description": (
                            "Subscription cancelled; access retained until "
                            "the end of the billing cycle"
                        ),
                        "message": "Billing event accepted",
                        "error": None,
                    },
                }
            ]
        }
    )

    success: Literal[True] = Field(
        default=True,
        description="Always true on success",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="UI-safe acknowledgement message",
        examples=["Billing event accepted"],
    )
    data: WebhookAckData = Field(
        ...,
        description="Accepted event echo (type, email, description)",
    )
