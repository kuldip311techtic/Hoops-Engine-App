"""Auth request/response schemas for Super Admin login and session."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Super Admin login form (email + password)."""

    email: EmailStr = Field(
        ...,
        description="Super Admin email address",
        examples=["admin@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Super Admin password (write-only; never returned)",
        examples=["securepassword"],
    )


class RefreshRequest(BaseModel):
    """Refresh the access token using a refresh token."""

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Refresh token issued at login",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"],
    )


class ChangePasswordRequest(BaseModel):
    """Change the Super Admin password and revoke other sessions."""

    current_password: str = Field(
        ...,
        min_length=1,
        description="Current password",
        examples=["securepassword"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        description="New password (min 8 characters)",
        examples=["NewSecure1!"],
    )


class SubscriptionAccessData(BaseModel):
    """Billing access snapshot nested in login data."""

    status: str = Field(
        ...,
        description="active, cancelled, expired, or not_applicable for Super Admin",
        examples=["not_applicable"],
    )
    has_access: bool = Field(
        ...,
        description="Whether the account may use the product right now",
        examples=[True],
    )
    access_until: str | None = Field(
        default=None,
        description="ISO-8601 instant access remains valid after cancellation",
        examples=[None],
    )


class LoginData(BaseModel):
    """Successful login payload consumed by the Super Admin login screen."""

    access_token: str = Field(..., description="OAuth2 JWT access token")
    refresh_token: str = Field(..., description="OAuth2 JWT refresh token")
    token_type: Literal["bearer"] = Field(default="bearer", description="OAuth2 token type")
    expires_in: int = Field(..., description="Access token lifetime in seconds", examples=[1800])
    email: EmailStr = Field(..., description="Authenticated Super Admin email")
    description: str = Field(
        ...,
        description="UI copy describing the next step after login",
        examples=["Redirect the Super Admin to the dashboard."],
    )
    message: str = Field(
        ...,
        description="UI-safe success message (also present on the envelope)",
        examples=["Login successful"],
    )
    error: None = Field(
        default=None,
        description="Always null on success; errors use the top-level error object",
    )
    redirect_to: str = Field(
        ...,
        description="Client-side path to navigate after storing tokens",
        examples=["/dashboard"],
    )
    subscription: SubscriptionAccessData


class LoginResponse(BaseModel):
    """Success envelope for login, refresh, and change-password."""

    success: Literal[True] = Field(default=True)
    message: str = Field(..., examples=["Login successful"])
    data: LoginData
