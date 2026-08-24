"""Support request admin request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.support_request import SupportRequestStatus
from app.schemas.common import AdminSuccessResponse


class SupportRequestRespondRequest(BaseModel):
    """Payload for responding to an existing support request."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "response": "Thank you for your inquiry!",
            }
        }
    )

    request_id: UUID = Field(
        ...,
        description="UUID of the support request to respond to.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    response: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Admin response text sent to the user.",
        examples=["Thank you for your inquiry!"],
    )

    @field_validator("response")
    @classmethod
    def strip_response(cls, value: str) -> str:
        """Reject whitespace-only responses."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("response must not be empty")
        return stripped


class SupportRequestResponse(BaseModel):
    """Single support request row for the Super Admin UI."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Support request primary key.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    request_id: UUID = Field(
        ...,
        description="Alias of id for FE bindings that read request_id.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    subject: str = Field(
        ...,
        description="Short summary of the user's inquiry.",
        examples=["Cannot access practice plans"],
    )
    description: str = Field(
        ...,
        description="Full user inquiry text shown in the detail panel.",
        examples=["I am unable to view practice plans after logging in."],
    )
    message: str = Field(
        ...,
        description="Same inquiry text as description (legacy key).",
        examples=["I am unable to view practice plans after logging in."],
    )
    status: SupportRequestStatus = Field(
        ...,
        description="Current lifecycle status: OPEN, RESPONDED, or CLOSED.",
        examples=["OPEN"],
    )
    submitter_email: str | None = Field(
        default=None,
        description="Email of the user who submitted the request, when known.",
        examples=["user@example.com"],
    )
    admin_response: str | None = Field(
        default=None,
        description="Latest admin response text, when provided.",
        examples=["Thank you for your inquiry!"],
    )
    created_at: datetime = Field(
        ...,
        description="When the request was submitted.",
    )
    updated_at: datetime = Field(
        ...,
        description="When the request was last modified.",
    )
    responded_at: datetime | None = Field(
        default=None,
        description="When an admin response was first or last recorded.",
    )
    closed_at: datetime | None = Field(
        default=None,
        description="When the request was closed.",
    )


class SupportRequestListData(BaseModel):
    """List payload for the support requests table."""

    items: list[SupportRequestResponse] = Field(
        default_factory=list,
        description="Support requests ordered by created_at descending.",
    )
    total: int = Field(
        ...,
        description="Total number of support requests returned.",
        examples=[2],
    )


class SupportRequestListResponse(AdminSuccessResponse):
    """Success envelope for GET /api/super-admin/support-requests."""

    data: SupportRequestListData


class SupportRequestActionResponse(AdminSuccessResponse):
    """Success envelope for respond/close actions."""

    data: SupportRequestResponse
