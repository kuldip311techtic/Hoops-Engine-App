"""Auth request/response schemas for Super Admin login and session."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Super Admin login form consumed by the Admin FE login screen.

    Ticket/Figma fields: ``email`` and ``password``. Both are required; the
    frontend disables the login button until they are filled.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "email": "admin@example.com",
                    "password": "securepassword",
                }
            ]
        }
    )

    email: EmailStr = Field(
        ...,
        description="Super Admin email address from the login form",
        examples=["admin@example.com"],
        max_length=255,
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Super Admin password (write-only; never returned)",
        examples=["securepassword"],
    )


class RefreshRequest(BaseModel):
    """Refresh the access token using a refresh token."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"}
            ]
        }
    )

    refresh_token: str = Field(
        ...,
        min_length=1,
        description="Refresh JWT issued at login (must have type=refresh)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"],
    )


class ChangePasswordRequest(BaseModel):
    """Change the Super Admin password and revoke other sessions."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "current_password": "securepassword",
                    "new_password": "NewSecure1!",
                }
            ]
        }
    )

    current_password: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Current password",
        examples=["securepassword"],
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=1024,
        description="New password (min 8 characters). Bumps token_version.",
        examples=["NewSecure1!"],
    )


class SubscriptionAccessData(BaseModel):
    """Billing access snapshot nested in login data."""

    status: str = Field(
        ...,
        description=(
            "Subscription status: active, cancelled, expired, or "
            "not_applicable for Super Admin"
        ),
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

    access_token: str = Field(
        ...,
        description="OAuth2 JWT access token (store in memory / secure storage)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access"],
    )
    refresh_token: str = Field(
        ...,
        description="OAuth2 JWT refresh token used with POST /auth/refresh",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"],
    )
    token_type: Literal["bearer"] = Field(
        default="bearer",
        description="OAuth2 token type; send as ``Authorization: Bearer <token>``",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token lifetime in seconds",
        examples=[1800],
    )
    email: EmailStr = Field(
        ...,
        description="Authenticated Super Admin email",
        examples=["admin@example.com"],
    )
    password: str = Field(
        default="",
        description=(
            "Always empty. The login form sends password; this API never "
            "echoes the secret back."
        ),
        examples=[""],
    )
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
        examples=[None],
    )
    redirect_to: str = Field(
        ...,
        description=(
            "Client-side path to navigate after storing tokens. This API "
            "returns HTTP 200, not 302."
        ),
        examples=["/dashboard"],
    )
    subscription: SubscriptionAccessData = Field(
        ...,
        description="Billing access snapshot (Super Admin is not_applicable)",
        examples=[
            {
                "status": "not_applicable",
                "has_access": True,
                "access_until": None,
            }
        ],
    )


class LoginResponse(BaseModel):
    """Success envelope for login, refresh, and change-password."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "message": "Login successful",
                    "data": {
                        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
                        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
                        "token_type": "bearer",
                        "expires_in": 1800,
                        "email": "admin@example.com",
                        "password": "",
                        "description": "Redirect the Super Admin to the dashboard.",
                        "message": "Login successful",
                        "error": None,
                        "redirect_to": "/dashboard",
                        "subscription": {
                            "status": "not_applicable",
                            "has_access": True,
                            "access_until": None,
                        },
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
        description="UI-safe human-readable message for the login screen",
        examples=["Login successful"],
    )
    data: LoginData = Field(
        ...,
        description="Tokens plus FE redirect and subscription snapshot",
    )
