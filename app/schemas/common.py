"""Shared Pydantic schemas for API responses."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str = Field(
        ...,
        description="Stable machine-readable error code for client handling.",
        examples=["VALIDATION_ERROR", "AUTHENTICATION_FAILED", "RATE_LIMIT_EXCEEDED"],
    )
    details: Any = Field(
        default=None,
        description="Optional structured details (e.g. field errors or retry_after).",
        examples=[None, [{"field": "email", "message": "value is not a valid email address"}]],
    )


class ErrorResponse(BaseModel):
    """Standard error response envelope."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": False,
                "message": "Invalid email or password.",
                "error": {"code": "AUTHENTICATION_FAILED", "details": None},
            }
        }
    )

    success: bool = Field(default=False, description="Always false for errors.")
    message: str = Field(
        ...,
        description="UI-safe human-readable message.",
        examples=["Invalid email or password.", "Validation error"],
    )
    error: ErrorDetail = Field(..., description="Structured error information.")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success response envelope."""

    model_config = ConfigDict(json_schema_extra={"example": {"success": True, "message": "OK", "data": {}}})

    success: bool = Field(default=True, description="Always true for successful responses.")
    message: str = Field(..., description="Human-readable success message.")
    data: T = Field(..., description="Response payload.")


class ErrorEnvelope(BaseModel):
    """Alias schema used internally by exception handlers."""

    success: bool = False
    message: str
    error: ErrorDetail
