"""Shared API response envelope and OpenAPI helpers."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str = Field(..., description="Stable error code", examples=["VALIDATION_ERROR"])
    details: Any = Field(
        default=None,
        description="Optional field-level or structured details.",
    )


class SuccessResponse(BaseModel):
    """Standard success envelope."""

    success: bool = Field(default=True, description="Always true for success.")
    message: str = Field(..., description="UI-safe summary of the result.")
    data: dict[str, Any] = Field(default_factory=dict, description="Response payload.")


class ErrorResponse(BaseModel):
    """Standard error envelope. Includes ``description`` for the Admin login UI."""

    success: bool = Field(default=False, description="Always false for errors.")
    message: str = Field(..., description="UI-safe error message (inline + toast).")
    description: str = Field(
        ...,
        description="Same UI-safe copy as message; Admin FE reads this key.",
    )
    error: ErrorDetail


def success_body(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a success envelope dict."""
    return {"success": True, "message": message, "data": data or {}}


def error_body(message: str, code: str, details: Any = None) -> dict[str, Any]:
    """Build an error envelope dict.

    ``description`` duplicates ``message`` so the Admin login screen can bind
    either key. ``password`` is never returned.
    """
    return {
        "success": False,
        "message": message,
        "description": message,
        "error": {"code": code, "details": details},
    }


def openapi_error(status: int, code: str, message: str) -> dict[str, Any]:
    """Return an OpenAPI response fragment for an error envelope."""
    return {
        "description": message,
        "content": {
            "application/json": {
                "example": error_body(message, code, None),
                "schema": ErrorResponse.model_json_schema(),
            }
        },
    }


def openapi_error_map() -> dict[int | str, dict[str, Any]]:
    """Common error responses documented on every endpoint."""
    return {
        400: openapi_error(400, "BAD_REQUEST", "Bad request"),
        401: openapi_error(401, "UNAUTHORIZED", "Not authenticated"),
        403: openapi_error(403, "FORBIDDEN", "Access denied"),
        404: openapi_error(404, "NOT_FOUND", "Resource not found"),
        409: openapi_error(409, "CONFLICT", "Resource already exists"),
        422: {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "example": error_body(
                        "Request validation failed",
                        "VALIDATION_ERROR",
                        [
                            {
                                "loc": ["body", "email"],
                                "msg": "Field required",
                                "type": "missing",
                                "field": "email",
                                "message": "Field required",
                            }
                        ],
                    )
                }
            },
        },
        500: openapi_error(500, "INTERNAL_ERROR", "Internal server error"),
    }
