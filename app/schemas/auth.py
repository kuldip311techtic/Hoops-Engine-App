"""Authentication request and response schemas."""

import re

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import SuccessResponse

_PASSWORD_SPECIAL = re.compile(r"[^A-Za-z0-9]")


def _validate_password_policy(value: str) -> str:
    """Enforce the product password policy (8+, upper, lower, digit, special)."""
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must include an uppercase letter")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must include a lowercase letter")
    if not re.search(r"[0-9]", value):
        raise ValueError("Password must include a number")
    if not _PASSWORD_SPECIAL.search(value):
        raise ValueError("Password must include a special character")
    return value


class LoginRequest(BaseModel):
    """Credentials for the Super Admin login screen (email + password only)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "admin@example.com",
                "password": "securepassword",
            }
        }
    )

    email: EmailStr = Field(
        ...,
        description="Super Admin email address shown on the Admin login screen.",
        examples=["admin@example.com"],
        max_length=255,
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Account password. Never returned in responses.",
        examples=["securepassword"],
    )


class RegisterRequest(BaseModel):
    """Registration payload. Password must meet the product policy."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "player@example.com",
                "password": "Securepass1!",
            }
        }
    )

    email: EmailStr = Field(
        ...,
        description="Email to register. Stored lowercase; must be unique.",
        examples=["player@example.com"],
        max_length=255,
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=1024,
        description=(
            "Password meeting complexity rules: 8+ characters with upper, "
            "lower, number, and special character."
        ),
        examples=["Securepass1!"],
    )

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        """Validate password complexity."""
        return _validate_password_policy(value)


class ChangePasswordRequest(BaseModel):
    """Authenticated password change. Invalidates other sessions."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "current_password": "Securepass1!",
                "new_password": "NewSecure1!",
            }
        }
    )

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Existing password for the authenticated user.",
        examples=["Securepass1!"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=1024,
        description="Replacement password meeting complexity rules.",
        examples=["NewSecure1!"],
    )

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        """Validate the new password complexity."""
        return _validate_password_policy(value)


class RefreshRequest(BaseModel):
    """Refresh-token grant."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            }
        }
    )

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Refresh JWT issued at login. Access tokens are rejected.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class TokenData(BaseModel):
    """OAuth2 bearer tokens plus SPA redirect hint and login UI fields."""

    access_token: str = Field(
        ...,
        description="JWT access token (type=access). Send as Authorization: Bearer.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token (type=refresh) for POST /auth/refresh.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Always bearer.",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token lifetime in seconds.",
        examples=[1800],
        ge=1,
    )
    redirect_to: str = Field(
        ...,
        description="Path the SPA should navigate to after login (not an HTTP 302).",
        examples=["/dashboard"],
    )
    email: str = Field(
        ...,
        description="Authenticated account email (also duplicated at envelope top level).",
        examples=["admin@example.com"],
    )
    description: str = Field(
        ...,
        description="Success copy for the Admin FE toast.",
        examples=["Welcome back. Redirecting to the dashboard."],
    )


class TokenResponse(SuccessResponse):
    """Login success envelope. FE reads message, email, description, and data."""

    email: str = Field(
        ...,
        description="Authenticated Super Admin email (top-level for the login screen).",
        examples=["admin@example.com"],
    )
    description: str = Field(
        ...,
        description="Success toast copy for the Admin login screen.",
        examples=["Welcome back. Redirecting to the dashboard."],
    )
    data: TokenData
