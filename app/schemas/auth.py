"""Authentication request and response schemas."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator

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
    """Credentials for Super Admin (or user) login."""

    email: EmailStr = Field(
        ...,
        description="Account email address",
        examples=["admin@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Account password",
        examples=["securepassword"],
    )


class RegisterRequest(BaseModel):
    """Registration payload. Password must meet the product policy."""

    email: EmailStr = Field(
        ...,
        description="Email to register",
        examples=["player@example.com"],
    )
    password: str = Field(
        ...,
        description="Password meeting complexity rules",
        examples=["Securepass1!"],
    )

    @field_validator("password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        """Validate password complexity."""
        return _validate_password_policy(value)


class ChangePasswordRequest(BaseModel):
    """Authenticated password change. Invalidates other sessions."""

    current_password: str = Field(
        ...,
        min_length=1,
        description="Existing password",
        examples=["Securepass1!"],
    )
    new_password: str = Field(
        ...,
        description="Replacement password meeting complexity rules",
        examples=["NewSecure1!"],
    )

    @field_validator("new_password")
    @classmethod
    def password_policy(cls, value: str) -> str:
        """Validate the new password complexity."""
        return _validate_password_policy(value)


class RefreshRequest(BaseModel):
    """Refresh-token grant."""

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Refresh JWT issued at login",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class TokenData(BaseModel):
    """OAuth2 bearer tokens plus SPA redirect hint and login UI fields."""

    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Always bearer")
    expires_in: int = Field(..., description="Access token lifetime in seconds")
    redirect_to: str = Field(
        ...,
        description="Path the SPA should navigate to after login (not an HTTP 302)",
        examples=["/dashboard"],
    )
    email: str = Field(
        ...,
        description="Authenticated Super Admin email",
        examples=["admin@example.com"],
    )
    description: str = Field(
        ...,
        description="Success copy for the Admin FE toast",
        examples=["Welcome back. Redirecting to the dashboard."],
    )


class TokenResponse(SuccessResponse):
    """Login success envelope. FE reads message, email, description, and data."""

    email: str = Field(
        ...,
        description="Authenticated Super Admin email (top-level for the login screen)",
        examples=["admin@example.com"],
    )
    description: str = Field(
        ...,
        description="Success toast copy",
        examples=["Welcome back. Redirecting to the dashboard."],
    )
    data: TokenData
