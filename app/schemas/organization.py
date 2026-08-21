"""Admin organization request and response schemas."""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import AdminSuccessResponse

_PHONE_PATTERN = re.compile(r"^[0-9+\-\s()]{7,20}$")


def validate_phone_number(value: str) -> str:
    """Ensure phone numbers contain only allowed characters and length."""
    cleaned = value.strip()
    if not _PHONE_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "phone_number must be 7-20 characters and contain only digits, "
            "spaces, +, -, or parentheses"
        )
    return cleaned


class OrganizationCreateRequest(BaseModel):
    """Payload for creating an organization."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Hoops Academy",
                "contact_email": "contact@example.com",
                "phone_number": "1234567890",
                "address": "123 Main St",
                "description": "Youth basketball training organization.",
                "is_published": True,
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique organization name.",
        examples=["Hoops Academy"],
    )
    contact_email: EmailStr = Field(
        ...,
        description="Primary contact email for the organization.",
        examples=["contact@example.com"],
        max_length=255,
    )
    phone_number: str = Field(
        ...,
        description="Organization phone number (7-20 digits/symbols).",
        examples=["1234567890"],
        max_length=32,
    )
    address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Organization street address.",
        examples=["123 Main St"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Optional internal or display description.",
        examples=["Youth basketball training organization."],
    )
    is_published: bool = Field(
        default=False,
        description=(
            "When true the organization is visible to end users. Defaults to false."
        ),
        examples=[True],
    )

    @field_validator("phone_number")
    @classmethod
    def phone_number_format(cls, value: str) -> str:
        """Validate phone number format."""
        return validate_phone_number(value)


class OrganizationUpdateRequest(BaseModel):
    """Partial update payload for an organization."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Hoops Academy West",
                "contact_email": "west@example.com",
                "phone_number": "9876543210",
                "address": "456 Oak Ave",
            }
        }
    )

    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Updated organization name.",
        examples=["Hoops Academy West"],
    )
    contact_email: EmailStr | None = Field(
        default=None,
        description="Updated contact email.",
        examples=["west@example.com"],
        max_length=255,
    )
    phone_number: str | None = Field(
        default=None,
        description="Updated phone number.",
        examples=["9876543210"],
        max_length=32,
    )
    address: str | None = Field(
        default=None,
        min_length=1,
        max_length=500,
        description="Updated address.",
        examples=["456 Oak Ave"],
    )
    description: str | None = Field(
        default=None,
        max_length=500,
        description="Updated description.",
        examples=["Regional training hub."],
    )
    is_published: bool | None = Field(
        default=None,
        description="Publish or unpublish the organization for end users.",
        examples=[True],
    )

    @field_validator("phone_number")
    @classmethod
    def phone_number_format(cls, value: str | None) -> str | None:
        """Validate phone number when provided."""
        if value is None:
            return None
        return validate_phone_number(value)


class OrganizationResponse(BaseModel):
    """Organization returned to the Admin FE."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="Organization primary key.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    name: str = Field(
        ...,
        description="Organization display name.",
        examples=["Hoops Academy"],
    )
    contact_email: EmailStr = Field(
        ...,
        description="Primary contact email stored for the organization.",
        examples=["contact@example.com"],
    )
    email: EmailStr = Field(
        ...,
        description="Alias of contact_email for Admin FE bindings.",
        examples=["contact@example.com"],
    )
    phone_number: str = Field(
        ...,
        description="Organization phone number.",
        examples=["1234567890"],
    )
    phone: str = Field(
        ...,
        description="Alias of phone_number for Admin FE bindings.",
        examples=["1234567890"],
    )
    address: str = Field(
        ...,
        description="Organization street address.",
        examples=["123 Main St"],
    )
    description: str | None = Field(
        default=None,
        description="Optional organization description.",
        examples=["Youth basketball training organization."],
    )
    is_active: bool = Field(
        ...,
        description="False when the organization has been soft-removed.",
        examples=[True],
    )
    is_published: bool = Field(
        ...,
        description="True when visible to end users.",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the organization was created.",
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp when the organization was last updated.",
    )


class OrganizationListResponse(AdminSuccessResponse):
    """List of organizations in the standard success envelope."""

    data: dict[str, list[OrganizationResponse]]
