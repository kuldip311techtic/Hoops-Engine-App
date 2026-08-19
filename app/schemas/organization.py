"""Pydantic schemas for Super Admin organization management."""

import uuid
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.common import ErrorDetail

OrganizationStatus = Literal["active", "inactive"]


class OrganizationWrite(BaseModel):
    """Shared create/update payload for the Manage Organizations forms."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "Hoops Academy",
                "email": "ops@hoopsacademy.example",
                "contact_email": "ops@hoopsacademy.example",
                "phone_number": "+1-555-0100",
                "address": "123 Court Street, Springfield",
                "description": "Youth basketball training organization.",
                "status": "active",
            }
        }
    )

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Organization display name. Must be unique (case-insensitive).",
        examples=["Hoops Academy"],
    )
    email: EmailStr = Field(
        ...,
        description=(
            "Organization contact email used by the Manage Organizations UI. "
            "Must be unique (case-insensitive)."
        ),
        examples=["ops@hoopsacademy.example"],
    )
    contact_email: EmailStr | None = Field(
        default=None,
        description=(
            "Organization contact email (API field). Defaults to email when omitted."
        ),
        examples=["ops@hoopsacademy.example"],
    )
    phone_number: str = Field(
        ...,
        min_length=1,
        max_length=50,
        description="Primary contact phone number.",
        examples=["+1-555-0100"],
    )
    address: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Organization mailing or facility address.",
        examples=["123 Court Street, Springfield"],
    )
    description: str = Field(
        default="",
        max_length=2000,
        description="Optional organization description shown in the admin UI.",
        examples=["Youth basketball training organization."],
    )
    status: OrganizationStatus = Field(
        default="active",
        description=(
            "Lifecycle status. 'active' organizations are treated as in use and "
            "cannot be removed until set to 'inactive'."
        ),
        examples=["active"],
    )

    @model_validator(mode="after")
    def sync_contact_email(self) -> Self:
        """Normalize name/email and keep contact_email in sync with email."""
        resolved = str(self.contact_email or self.email).strip().lower()
        object.__setattr__(self, "contact_email", resolved)
        object.__setattr__(self, "email", resolved)
        object.__setattr__(self, "name", self.name.strip())
        object.__setattr__(self, "phone_number", self.phone_number.strip())
        object.__setattr__(self, "address", self.address.strip())
        object.__setattr__(self, "description", (self.description or "").strip())
        return self

    @property
    def is_active(self) -> bool:
        """Return True when status is active."""
        return self.status == "active"


class OrganizationCreate(OrganizationWrite):
    """Request body for POST /api/organizations."""


class OrganizationUpdate(OrganizationWrite):
    """Request body for PUT /api/organizations/{id}."""


class OrganizationRead(BaseModel):
    """Organization resource returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Organization identifier.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    name: str = Field(
        ..., description="Organization display name.", examples=["Hoops Academy"]
    )
    contact_email: str = Field(
        ...,
        description="Organization contact email.",
        examples=["ops@hoopsacademy.example"],
    )
    email: str = Field(
        ...,
        description="Frontend alias for contact_email.",
        examples=["ops@hoopsacademy.example"],
    )
    phone_number: str = Field(
        ...,
        description="Primary contact phone number.",
        examples=["+1-555-0100"],
    )
    address: str = Field(
        ...,
        description="Organization address.",
        examples=["123 Court Street, Springfield"],
    )
    description: str = Field(
        ...,
        description="Organization description.",
        examples=["Youth basketball training organization."],
    )
    status: OrganizationStatus = Field(
        ...,
        description="active or inactive. Active organizations are currently in use.",
        examples=["active"],
    )
    is_active: bool = Field(
        ...,
        description="True when status is active.",
        examples=[True],
    )


class OrganizationListData(BaseModel):
    """Paginated organization collection."""

    items: list[OrganizationRead] = Field(
        ...,
        description="Organizations for the requested page, sorted by name.",
    )
    total: int = Field(..., description="Total organization count.", examples=[1])
    page: int = Field(..., description="Current 1-based page number.", examples=[1])
    page_size: int = Field(
        ..., description="Page size used for this response.", examples=[20]
    )


class OrganizationResponse(BaseModel):
    """Success envelope for a single organization (create/update)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Organization created.",
                "description": "Organization added successfully.",
                "email": "ops@hoopsacademy.example",
                "token": None,
                "organization": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "name": "Hoops Academy",
                    "contact_email": "ops@hoopsacademy.example",
                    "email": "ops@hoopsacademy.example",
                    "phone_number": "+1-555-0100",
                    "address": "123 Court Street, Springfield",
                    "description": "Youth basketball training organization.",
                    "status": "active",
                    "is_active": True,
                },
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Hoops Academy",
                "status": "active",
                "error": None,
                "data": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "name": "Hoops Academy",
                    "contact_email": "ops@hoopsacademy.example",
                    "email": "ops@hoopsacademy.example",
                    "phone_number": "+1-555-0100",
                    "address": "123 Court Street, Springfield",
                    "description": "Youth basketball training organization.",
                    "status": "active",
                    "is_active": True,
                },
            }
        }
    )

    success: bool = Field(
        default=True, description="Always true for successful responses."
    )
    message: str = Field(..., description="UI-safe success message for toasts.")
    description: str = Field(..., description="Longer outcome description for UI copy.")
    email: str | None = Field(
        default=None,
        description="Organization contact email; null when not applicable.",
    )
    token: str | None = Field(
        default=None,
        description=(
            "Not populated on organization routes; present for envelope consistency."
        ),
    )
    organization: OrganizationRead | None = Field(
        default=None,
        description="Organization resource for single-item responses.",
    )
    id: uuid.UUID | None = Field(
        default=None, description="Organization id for single-item responses."
    )
    name: str | None = Field(
        default=None, description="Organization name for single-item responses."
    )
    status: OrganizationStatus | None = Field(
        default=None,
        description="Organization status for single-item responses.",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: OrganizationRead = Field(..., description="Organization resource.")


class OrganizationListResponse(BaseModel):
    """Success envelope for GET /api/organizations."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Organizations retrieved.",
                "description": "Organization list loaded.",
                "email": None,
                "token": None,
                "organization": None,
                "id": None,
                "name": None,
                "status": None,
                "error": None,
                "data": {
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "page_size": 20,
                },
            }
        }
    )

    success: bool = Field(
        default=True, description="Always true for successful responses."
    )
    message: str = Field(..., description="UI-safe success message.")
    description: str = Field(..., description="Longer outcome description for UI copy.")
    email: str | None = Field(
        default=None, description="Not populated on list responses."
    )
    token: str | None = Field(
        default=None, description="Not populated on organization routes."
    )
    organization: OrganizationRead | None = Field(
        default=None,
        description="Not populated on list responses; each item is in data.items.",
    )
    id: uuid.UUID | None = Field(
        default=None, description="Not populated on list responses."
    )
    name: str | None = Field(
        default=None, description="Not populated on list responses."
    )
    status: OrganizationStatus | None = Field(
        default=None,
        description="Not populated on list responses; each item has its own status.",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: OrganizationListData = Field(
        ..., description="Paginated organization collection."
    )


class OrganizationDeleteResponse(BaseModel):
    """Success envelope for DELETE /api/organizations/{id} confirmation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Organization removed.",
                "description": "The organization was removed successfully.",
                "email": None,
                "token": None,
                "organization": None,
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Hoops Academy",
                "status": "inactive",
                "error": None,
                "data": {},
            }
        }
    )

    success: bool = Field(
        default=True, description="Always true for successful responses."
    )
    message: str = Field(..., description="Confirmation message for the remove toast.")
    description: str = Field(..., description="Longer confirmation copy for the UI.")
    email: str | None = Field(default=None, description="Not populated after deletion.")
    token: str | None = Field(
        default=None, description="Not populated on organization routes."
    )
    organization: OrganizationRead | None = Field(
        default=None,
        description="Null after successful removal.",
    )
    id: uuid.UUID | None = Field(
        ..., description="Identifier of the removed organization."
    )
    name: str | None = Field(..., description="Name of the removed organization.")
    status: OrganizationStatus | None = Field(
        default="inactive",
        description="Status at the time of removal (always inactive).",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: dict = Field(default_factory=dict, description="Empty object after deletion.")
