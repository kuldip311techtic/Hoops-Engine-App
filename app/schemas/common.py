"""Shared Pydantic envelopes used by every endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    """Machine-readable error payload nested under ``error``."""

    code: str = Field(
        ...,
        description="Stable machine-readable error code",
        examples=[
            "VALIDATION_ERROR",
            "UNAUTHORIZED",
            "INVALID_CREDENTIALS",
            "INTERNAL_SERVER_ERROR",
        ],
    )
    details: list[dict[str, Any]] | dict[str, Any] | None = Field(
        default=None,
        description="Optional field-level or structured error details",
        examples=[
            [
                {
                    "field": "email",
                    "message": "Field required",
                    "type": "missing",
                }
            ]
        ],
    )


class ErrorResponse(BaseModel):
    """Canonical error envelope returned by all failed requests."""

    success: Literal[False] = Field(default=False, description="Always false on errors")
    message: str = Field(
        ...,
        description="UI-safe human-readable message",
        examples=["Request validation failed"],
    )
    error: ErrorBody = Field(
        ...,
        description="Stable error code plus optional field details for the client",
    )


class SuccessResponse(BaseModel):
    """Canonical success envelope. ``data`` is endpoint-specific."""

    success: Literal[True] = Field(default=True, description="Always true on success")
    message: str = Field(
        ...,
        description="UI-safe human-readable message",
        examples=["Service is healthy"],
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Endpoint-specific payload",
        examples=[{"status": "ok"}],
    )


def _error_example(message: str, code: str, details: Any = None) -> dict[str, Any]:
    """Build a JSON example matching the project error envelope."""
    return {
        "success": False,
        "message": message,
        "error": {"code": code, "details": details},
    }


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "model": ErrorResponse,
        "description": "Bad request",
        "content": {
            "application/json": {
                "example": _error_example("Bad request", "BAD_REQUEST"),
            }
        },
    },
    401: {
        "model": ErrorResponse,
        "description": "Authentication required or invalid",
        "content": {
            "application/json": {
                "example": _error_example(
                    "Authentication required",
                    "UNAUTHORIZED",
                ),
            }
        },
    },
    403: {
        "model": ErrorResponse,
        "description": "Authenticated but not permitted",
        "content": {
            "application/json": {
                "example": _error_example(
                    "You do not have permission to perform this action",
                    "FORBIDDEN",
                ),
            }
        },
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource not found",
        "content": {
            "application/json": {
                "example": _error_example("Resource not found", "NOT_FOUND"),
            }
        },
    },
    409: {
        "model": ErrorResponse,
        "description": "Conflict with existing state",
        "content": {
            "application/json": {
                "example": _error_example(
                    "An account with this email already exists",
                    "EMAIL_ALREADY_EXISTS",
                ),
            }
        },
    },
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed",
        "content": {
            "application/json": {
                "example": _error_example(
                    "Request validation failed",
                    "VALIDATION_ERROR",
                    [
                        {
                            "field": "email",
                            "message": "Field required",
                            "type": "missing",
                        }
                    ],
                ),
            }
        },
    },
    429: {
        "model": ErrorResponse,
        "description": "Too many requests (login/refresh rate limit)",
        "content": {
            "application/json": {
                "example": _error_example(
                    "Too many requests. Please try again later.",
                    "RATE_LIMIT_EXCEEDED",
                ),
            }
        },
    },
    500: {
        "model": ErrorResponse,
        "description": "Unexpected server error (message never leaks internals)",
        "content": {
            "application/json": {
                "example": _error_example(
                    "An unexpected error occurred. Please try again later.",
                    "INTERNAL_SERVER_ERROR",
                ),
            }
        },
    },
    503: {
        "model": ErrorResponse,
        "description": "Dependency unavailable (database or webhook secret missing)",
        "content": {
            "application/json": {
                "example": _error_example(
                    "Database is unavailable",
                    "DATABASE_UNAVAILABLE",
                ),
            }
        },
    },
}
