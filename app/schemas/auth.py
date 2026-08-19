"""Authentication request and response schemas."""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Super Admin login credentials."""

    email: EmailStr = Field(
        ...,
        description="Registered Super Admin email address.",
        examples=["admin@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        description="Super Admin account password.",
        examples=["password123"],
    )


class LoginData(BaseModel):
    """Authenticated session payload returned after successful login."""

    token: str = Field(
        ...,
        description="JWT access token. Include as Authorization: Bearer <token>.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Token type for Authorization header.",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token lifetime in seconds.",
        examples=[1800],
    )
    email: str = Field(
        ...,
        description="Authenticated Super Admin email address.",
        examples=["admin@example.com"],
    )


class LoginResponse(BaseModel):
    """Successful login response envelope."""

    success: bool = Field(
        default=True,
        description="Indicates the login attempt succeeded.",
    )
    message: str = Field(
        ...,
        description="UI-safe success message.",
        examples=["Login successful."],
    )
    description: str = Field(
        ...,
        description="Detailed outcome description for UI display or logging.",
        examples=["Super Admin authenticated. Redirect to dashboard."],
    )
    data: LoginData = Field(..., description="Authentication payload.")
