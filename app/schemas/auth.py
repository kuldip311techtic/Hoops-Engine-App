"""Authentication request and response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.schemas.common import SuccessResponse


class LoginRequest(BaseModel):
    """Credentials for the Super Admin login screen (email + password only)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "admin@example.com",
                "password": "password123",
            }
        }
    )

    email: str = Field(
        ...,
        description="Super Admin email address shown on the Admin login screen.",
        examples=["admin@example.com"],
        max_length=255,
    )
    password: str = Field(
        ...,
        max_length=1024,
        description="Account password. Never returned in responses.",
        examples=["password123"],
    )

    @field_validator("email", "password")
    @classmethod
    def strip_fields(cls, value: str) -> str:
        """Strip surrounding whitespace before route-level validation."""
        return value.strip()


class TokenData(BaseModel):
    """Bearer token payload returned after successful login."""

    access_token: str = Field(
        ...,
        description="JWT access token for Authorization: Bearer headers.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token: str = Field(
        ...,
        description="Alias of access_token for frontend clients that read `token`.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for session renewal.",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="OAuth2 token type.",
        examples=["bearer"],
    )
    expires_in: int = Field(
        ...,
        description="Access token lifetime in seconds.",
        examples=[1800],
    )
    redirect_to: str = Field(
        ...,
        description="SPA route the frontend should navigate to after login.",
        examples=["/dashboard"],
    )
    email: EmailStr = Field(
        ...,
        description="Authenticated Super Admin email.",
        examples=["admin@example.com"],
    )
    description: str = Field(
        ...,
        description="UI-safe success copy for toast or inline messaging.",
        examples=["Welcome back. Redirecting to the dashboard."],
    )


class LoginResponse(SuccessResponse):
    """Success envelope for Super Admin login."""

    message: str = Field(
        ...,
        description="UI-safe login success summary.",
        examples=["Login successful"],
    )
    email: EmailStr = Field(
        ...,
        description="Authenticated Super Admin email (top-level for the login UI).",
        examples=["admin@example.com"],
    )
    description: str = Field(
        ...,
        description="UI-safe success copy duplicated at the top level for the login UI.",
        examples=["Welcome back. Redirecting to the dashboard."],
    )
    data: TokenData
