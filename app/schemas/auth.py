"""Authentication request and response schemas."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    """Super Admin login credentials submitted from the login screen."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"email": "admin@example.com", "password": "password123"}
        }
    )

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

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Login successful.",
                "description": "Super Admin authenticated. Redirect to dashboard.",
                "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "email": "admin@example.com",
                "data": {
                    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                    "token_type": "bearer",
                    "expires_in": 1800,
                    "email": "admin@example.com",
                },
            }
        }
    )

    success: bool = Field(
        default=True,
        description="Indicates the login attempt succeeded.",
    )
    message: str = Field(
        ...,
        description="UI-safe success message for the login screen.",
        examples=["Login successful."],
    )
    description: str = Field(
        ...,
        description="Detailed outcome description for UI display or logging.",
        examples=["Super Admin authenticated. Redirect to dashboard."],
    )
    token: str = Field(
        ...,
        description="JWT access token for Authorization: Bearer header (mirrors data.token).",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    email: str = Field(
        ...,
        description="Authenticated Super Admin email (mirrors data.email).",
        examples=["admin@example.com"],
    )
    data: LoginData = Field(..., description="Authentication payload including JWT token.")
