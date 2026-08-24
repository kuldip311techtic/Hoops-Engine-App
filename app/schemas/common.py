"""Shared API response envelope and OpenAPI helpers."""

from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Machine-readable error payload."""

    code: str = Field(
        ...,
        description="Stable error code the client can switch on.",
        examples=["VALIDATION_ERROR"],
    )
    details: Any = Field(
        default=None,
        description="Optional field-level or structured details.",
        examples=[
            [
                {
                    "field": "password",
                    "message": "Field required",
                    "msg": "Field required",
                    "type": "missing",
                    "loc": ["body", "password"],
                }
            ]
        ],
    )


class SuccessResponse(BaseModel):
    """Standard success envelope."""

    success: bool = Field(
        default=True,
        description="Always true for success.",
        examples=[True],
    )
    message: str = Field(
        ...,
        description="UI-safe summary of the result.",
        examples=["Service is healthy"],
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Response payload.",
        examples=[{"status": "ok"}],
    )


class ErrorResponse(BaseModel):
    """Standard error envelope."""

    success: bool = Field(
        default=False,
        description="Always false for errors.",
        examples=[False],
    )
    message: str = Field(
        ...,
        description="UI-safe error message.",
        examples=["Request validation failed"],
    )
    description: str = Field(
        ...,
        description="Same UI-safe copy as message.",
        examples=["Request validation failed"],
    )
    error: ErrorDetail


def success_body(message: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build a success envelope dict."""
    return {"success": True, "message": message, "data": data or {}}


def error_body(message: str, code: str, details: Any = None) -> dict[str, Any]:
    """Build an error envelope dict."""
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
                                "field": "password",
                                "message": "Field required",
                                "msg": "Field required",
                                "type": "missing",
                                "loc": ["body", "password"],
                            }
                        ],
                    ),
                    "schema": ErrorResponse.model_json_schema(),
                }
            },
        },
        429: openapi_error(429, "RATE_LIMITED", "Too many requests"),
        500: openapi_error(500, "INTERNAL_ERROR", "Internal server error"),
        503: openapi_error(503, "SERVICE_UNAVAILABLE", "Service unavailable"),
    }
