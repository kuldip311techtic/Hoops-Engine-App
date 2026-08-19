"""Pydantic schemas for Super Admin user management."""

import uuid
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.common import ErrorDetail

UserRole = Literal["coach", "player", "organization_admin"]
UserStatus = Literal["active", "inactive"]


def _display_name(first_name: str, last_name: str) -> str:
    """Return the combined name shown in the Manage Users list."""
    return f"{first_name} {last_name}".strip()


class UserCreate(BaseModel):
    """Request body for POST /api/users (Add User form)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Coach",
                "name": "Jane Coach",
                "email": "jane.coach@example.com",
                "role": "coach",
                "roles": ["coach"],
                "password": "SecurePass1!",
                "status": "active",
            }
        }
    )

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Given name. Required unless name is provided.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Family name. Required unless name is provided.",
        examples=["Coach"],
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=201,
        description="Frontend combined name. Splits into first_name and last_name.",
        examples=["Jane Coach"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique user email address (case-insensitive).",
        examples=["jane.coach@example.com"],
    )
    role: UserRole | None = Field(
        default=None,
        description="User role. One of coach, player, organization_admin.",
        examples=["coach"],
    )
    roles: list[UserRole] | None = Field(
        default=None,
        description="Frontend roles list. First entry is used when role is omitted.",
        examples=[["coach"]],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description=(
            "Account password. Write-only. Must include uppercase, lowercase, "
            "a number, and a special character."
        ),
        examples=["SecurePass1!"],
    )
    status: UserStatus = Field(
        default="active",
        description="Account status shown in the user list.",
        examples=["active"],
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        description="Optional organization this user belongs to.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )

    @model_validator(mode="after")
    def normalize_identity(self) -> Self:
        """Resolve name/role aliases and normalize email."""
        object.__setattr__(self, "email", str(self.email).strip().lower())
        first = (self.first_name or "").strip()
        last = (self.last_name or "").strip()
        combined = (self.name or "").strip()
        if first and last:
            object.__setattr__(self, "first_name", first)
            object.__setattr__(self, "last_name", last)
            object.__setattr__(self, "name", _display_name(first, last))
        elif combined:
            parts = combined.split(None, 1)
            object.__setattr__(self, "first_name", parts[0])
            object.__setattr__(
                self, "last_name", parts[1] if len(parts) > 1 else parts[0]
            )
            object.__setattr__(
                self, "name", _display_name(self.first_name, self.last_name)
            )
        else:
            raise ValueError("first_name and last_name, or name, is required")
        resolved_role = self.role
        if resolved_role is None and self.roles:
            resolved_role = self.roles[0]
        if resolved_role is None:
            raise ValueError("role or roles is required")
        object.__setattr__(self, "role", resolved_role)
        object.__setattr__(self, "roles", [resolved_role])
        return self

    @property
    def is_active(self) -> bool:
        """Return True when status is active."""
        return self.status == "active"


class UserUpdate(BaseModel):
    """Request body for PUT /api/users/{id} (Edit User form)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Coach",
                "name": "Jane Coach",
                "email": "jane.coach@example.com",
                "role": "coach",
                "roles": ["coach"],
                "status": "active",
            }
        }
    )

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Given name. Required unless name is provided.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Family name. Required unless name is provided.",
        examples=["Coach"],
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=201,
        description="Frontend combined name. Splits into first_name and last_name.",
        examples=["Jane Coach"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique user email address (case-insensitive).",
        examples=["jane.coach@example.com"],
    )
    role: UserRole | None = Field(
        default=None,
        description="User role. One of coach, player, organization_admin.",
        examples=["coach"],
    )
    roles: list[UserRole] | None = Field(
        default=None,
        description="Frontend roles list. First entry is used when role is omitted.",
        examples=[["coach"]],
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
        description=(
            "Optional new password. Write-only; omitted leaves the hash unchanged."
        ),
        examples=["SecurePass1!"],
    )
    status: UserStatus | None = Field(
        default=None,
        description=(
            "Account status. Omit to leave unchanged. Send active or inactive "
            "to update the list Status column."
        ),
        examples=["active"],
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        description=(
            "Optional organization this user belongs to. Omit to leave unchanged."
        ),
    )

    @model_validator(mode="after")
    def normalize_identity(self) -> Self:
        """Resolve name/role aliases and normalize email."""
        object.__setattr__(self, "email", str(self.email).strip().lower())
        first = (self.first_name or "").strip()
        last = (self.last_name or "").strip()
        combined = (self.name or "").strip()
        if first and last:
            object.__setattr__(self, "first_name", first)
            object.__setattr__(self, "last_name", last)
            object.__setattr__(self, "name", _display_name(first, last))
        elif combined:
            parts = combined.split(None, 1)
            object.__setattr__(self, "first_name", parts[0])
            object.__setattr__(
                self, "last_name", parts[1] if len(parts) > 1 else parts[0]
            )
            object.__setattr__(
                self, "name", _display_name(self.first_name, self.last_name)
            )
        else:
            raise ValueError("first_name and last_name, or name, is required")
        resolved_role = self.role
        if resolved_role is None and self.roles:
            resolved_role = self.roles[0]
        if resolved_role is None:
            raise ValueError("role or roles is required")
        object.__setattr__(self, "role", resolved_role)
        object.__setattr__(self, "roles", [resolved_role])
        return self

    @property
    def is_active(self) -> bool | None:
        """Return True/False when status is set; None means leave unchanged."""
        if self.status is None:
            return None
        return self.status == "active"


class UserRead(BaseModel):
    """User resource returned to the frontend. Password is never populated."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(..., description="User identifier.")
    first_name: str = Field(..., description="Given name.", examples=["Jane"])
    last_name: str = Field(..., description="Family name.", examples=["Coach"])
    name: str = Field(
        ..., description="Combined display name.", examples=["Jane Coach"]
    )
    email: str = Field(
        ..., description="User email.", examples=["jane.coach@example.com"]
    )
    role: UserRole = Field(..., description="Primary role.", examples=["coach"])
    roles: list[UserRole] = Field(
        ...,
        description="Roles list for the frontend (single primary role).",
        examples=[["coach"]],
    )
    status: UserStatus = Field(
        ..., description="active or inactive.", examples=["active"]
    )
    is_active: bool = Field(..., description="True when status is active.")
    description: str = Field(
        default="",
        description="Optional user description; empty when not set.",
    )
    password: str | None = Field(
        default=None,
        description="Always null in responses. Password is write-only.",
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        description="Optional organization this user belongs to.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )


class UserListData(BaseModel):
    """Paginated user collection."""

    items: list[UserRead] = Field(..., description="Users for the requested page.")
    total: int = Field(..., description="Total user count.", examples=[1])
    page: int = Field(..., description="Current 1-based page number.", examples=[1])
    page_size: int = Field(
        ..., description="Page size used for this response.", examples=[20]
    )


class UserResponse(BaseModel):
    """Success envelope for a single user (create/update)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "User created.",
                "description": "User added successfully.",
                "email": "jane.coach@example.com",
                "token": None,
                "password": None,
                "user": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "first_name": "Jane",
                    "last_name": "Coach",
                    "name": "Jane Coach",
                    "email": "jane.coach@example.com",
                    "role": "coach",
                    "roles": ["coach"],
                    "status": "active",
                    "is_active": True,
                    "description": "",
                    "password": None,
                    "organization_id": None,
                },
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Jane Coach",
                "role": "coach",
                "roles": ["coach"],
                "status": "active",
                "error": None,
                "data": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "first_name": "Jane",
                    "last_name": "Coach",
                    "name": "Jane Coach",
                    "email": "jane.coach@example.com",
                    "role": "coach",
                    "roles": ["coach"],
                    "status": "active",
                    "is_active": True,
                    "description": "",
                    "password": None,
                    "organization_id": None,
                },
            }
        }
    )

    success: bool = Field(default=True, description="Always true on success.")
    message: str = Field(..., description="UI-safe success message for toasts.")
    description: str = Field(..., description="Longer outcome description for UI copy.")
    email: str | None = Field(
        default=None, description="User email for single-item responses."
    )
    token: str | None = Field(default=None, description="Not populated on user routes.")
    password: str | None = Field(
        default=None,
        description="Always null. Password is write-only and never returned.",
    )
    user: UserRead | None = Field(default=None, description="User resource.")
    id: uuid.UUID | None = Field(
        default=None, description="User id for single-item responses."
    )
    name: str | None = Field(
        default=None, description="Display name for single-item responses."
    )
    role: UserRole | None = Field(default=None, description="Primary role.")
    roles: list[UserRole] | None = Field(default=None, description="Roles list.")
    status: UserStatus | None = Field(default=None, description="Account status.")
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: UserRead = Field(..., description="User resource.")


class UserListResponse(BaseModel):
    """Success envelope for GET /api/users."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Users retrieved.",
                "description": "User list loaded.",
                "email": None,
                "token": None,
                "password": None,
                "user": None,
                "id": None,
                "name": None,
                "role": None,
                "roles": None,
                "status": None,
                "error": None,
                "data": {"items": [], "total": 0, "page": 1, "page_size": 20},
            }
        }
    )

    success: bool = Field(default=True, description="Always true on success.")
    message: str = Field(..., description="UI-safe success message.")
    description: str = Field(..., description="Longer outcome description for UI copy.")
    email: str | None = Field(
        default=None, description="Not populated on list responses."
    )
    token: str | None = Field(default=None, description="Not populated on user routes.")
    password: str | None = Field(
        default=None, description="Always null. Password is write-only."
    )
    user: UserRead | None = Field(
        default=None,
        description="Not populated on list responses; items are in data.items.",
    )
    id: uuid.UUID | None = Field(
        default=None, description="Not populated on list responses."
    )
    name: str | None = Field(
        default=None, description="Not populated on list responses."
    )
    role: UserRole | None = Field(
        default=None, description="Not populated on list responses."
    )
    roles: list[UserRole] | None = Field(
        default=None,
        description="Not populated on list responses; each item has roles.",
    )
    status: UserStatus | None = Field(
        default=None,
        description="Not populated on list responses; each item has status.",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: UserListData = Field(..., description="Paginated user collection.")


class UserDeleteResponse(BaseModel):
    """Success envelope for DELETE /api/users/{id} confirmation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "User removed.",
                "description": "The user was removed successfully.",
                "email": "jane.coach@example.com",
                "token": None,
                "password": None,
                "user": None,
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Jane Coach",
                "role": "coach",
                "roles": ["coach"],
                "status": "inactive",
                "error": None,
                "data": {},
            }
        }
    )

    success: bool = Field(default=True, description="Always true on success.")
    message: str = Field(..., description="Confirmation message for the remove toast.")
    description: str = Field(..., description="Longer confirmation copy for the UI.")
    email: str | None = Field(default=None, description="Email of the removed user.")
    token: str | None = Field(default=None, description="Not populated on user routes.")
    password: str | None = Field(default=None, description="Always null.")
    user: UserRead | None = Field(
        default=None, description="Null after successful removal."
    )
    id: uuid.UUID | None = Field(..., description="Identifier of the removed user.")
    name: str | None = Field(..., description="Display name of the removed user.")
    role: UserRole | None = Field(default=None, description="Role of the removed user.")
    roles: list[UserRole] | None = Field(
        default=None, description="Roles of the removed user."
    )
    status: UserStatus | None = Field(
        default="inactive",
        description="Status after removal.",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: dict = Field(default_factory=dict, description="Empty object after deletion.")
