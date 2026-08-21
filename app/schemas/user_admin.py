"""Admin user request and response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole
from app.schemas.auth import _validate_password_policy
from app.schemas.common import AdminSuccessResponse

_ROLE_ALIASES = {
    "coach": UserRole.COACH,
    "player": UserRole.PLAYER,
    "org_admin": UserRole.ORG_ADMIN,
    "organization_admin": UserRole.ORG_ADMIN,
    "organization admin": UserRole.ORG_ADMIN,
    "user": UserRole.USER,
    "viewer": UserRole.VIEWER,
}

_ROLE_LABELS = {
    UserRole.SUPER_ADMIN: "Super Admin",
    UserRole.USER: "User",
    UserRole.VIEWER: "Viewer",
    UserRole.COACH: "Coach",
    UserRole.PLAYER: "Player",
    UserRole.ORG_ADMIN: "Organization Admin",
}

_ADMIN_ASSIGNABLE_ROLES = {
    UserRole.USER,
    UserRole.VIEWER,
    UserRole.COACH,
    UserRole.PLAYER,
    UserRole.ORG_ADMIN,
}


def normalize_user_role(value: str | UserRole) -> UserRole:
    """Accept enum values or human-readable role labels (e.g. Coach)."""
    if isinstance(value, UserRole):
        role = value
    else:
        key = value.strip().lower().replace("-", "_")
        if key in _ROLE_ALIASES:
            role = _ROLE_ALIASES[key]
        else:
            try:
                role = UserRole(value.upper())
            except ValueError as exc:
                raise ValueError(
                    "role must be Coach, Player, Organization Admin, User, or Viewer"
                ) from exc
    if role == UserRole.SUPER_ADMIN:
        raise ValueError("SUPER_ADMIN cannot be assigned via the admin users API")
    if role not in _ADMIN_ASSIGNABLE_ROLES:
        raise ValueError(
            "role must be Coach, Player, Organization Admin, User, or Viewer"
        )
    return role


def user_role_label(role: UserRole) -> str:
    """Return a UI-friendly role label."""
    return _ROLE_LABELS[role]


def full_name(first_name: str, last_name: str) -> str:
    """Build the display name for Admin FE bindings."""
    parts = [part.strip() for part in (first_name, last_name) if part.strip()]
    return " ".join(parts)


class UserCreateRequest(BaseModel):
    """Payload for creating a user via Super Admin."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "password": "Securepass1!",
                "role": "Coach",
            }
        }
    )

    first_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User given name.",
        examples=["John"],
    )
    last_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="User family name.",
        examples=["Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Unique login email for the user.",
        examples=["john.doe@example.com"],
        max_length=255,
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=1024,
        description=(
            "Initial password meeting complexity rules. Never returned in responses."
        ),
        examples=["Securepass1!"],
    )
    role: str = Field(
        ...,
        description="Application role: Coach, Player, Organization Admin, User, or Viewer.",
        examples=["Coach"],
    )

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        """Validate password complexity."""
        return _validate_password_policy(value)

    @field_validator("role")
    @classmethod
    def role_value(cls, value: str) -> str:
        """Normalize and validate assignable roles."""
        normalize_user_role(value)
        return value.strip()


class UserUpdateRequest(BaseModel):
    """Partial update payload for a user."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "first_name": "Jane",
                "last_name": "Doe",
                "email": "jane.doe@example.com",
                "role": "Player",
            }
        }
    )

    first_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated given name.",
        examples=["Jane"],
    )
    last_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
        description="Updated family name.",
        examples=["Doe"],
    )
    email: EmailStr | None = Field(
        default=None,
        description="Updated login email.",
        examples=["jane.doe@example.com"],
        max_length=255,
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=1024,
        description="Optional replacement password meeting complexity rules.",
        examples=["NewSecure1!"],
    )
    role: str | None = Field(
        default=None,
        description="Updated role.",
        examples=["Player"],
    )

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str | None) -> str | None:
        """Validate password when provided."""
        if value is None:
            return None
        return _validate_password_policy(value)

    @field_validator("role")
    @classmethod
    def role_value(cls, value: str | None) -> str | None:
        """Normalize role when provided."""
        if value is None:
            return None
        normalize_user_role(value)
        return value.strip()


class UserResponse(BaseModel):
    """User returned to the Admin FE."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(
        ...,
        description="User primary key.",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    first_name: str = Field(..., description="Given name.", examples=["John"])
    last_name: str = Field(..., description="Family name.", examples=["Doe"])
    name: str = Field(
        ...,
        description="Full display name for Admin FE bindings.",
        examples=["John Doe"],
    )
    email: EmailStr = Field(
        ...,
        description="Login email address.",
        examples=["john.doe@example.com"],
    )
    role: str = Field(
        ...,
        description="Human-readable role label.",
        examples=["Coach"],
    )
    role_code: str = Field(
        ...,
        description="Stable role enum value.",
        examples=["COACH"],
    )
    is_active: bool = Field(
        ...,
        description="False when the account has been soft-removed.",
        examples=[True],
    )
    created_at: datetime = Field(
        ...,
        description="UTC timestamp when the account was created.",
    )
    updated_at: datetime = Field(
        ...,
        description="UTC timestamp when the account was last updated.",
    )


class UserListResponse(AdminSuccessResponse):
    """Paginated user list in the standard success envelope."""

    data: dict[str, object]
