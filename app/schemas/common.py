"""Shared Pydantic envelopes used by every endpoint."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    """Machine-readable error payload nested under ``error``."""

    code: str = Field(
        ...,
        description="Stable machine-readable error code",
        examples=["VALIDATION_ERROR", "UNAUTHORIZED", "INTERNAL_SERVER_ERROR"],
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
    error: ErrorBody


class SuccessResponse(BaseModel):
    """Canonical success envelope. ``data`` is endpoint-specific."""

    success: Literal[True] = Field(default=True, description="Always true on success")
    message: str = Field(
        ...,
        description="UI-safe human-readable message",
        examples=["Service is healthy"],
    )
    data: dict[str, Any] = Field(default_factory=dict)


ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {
        "model": ErrorResponse,
        "description": "Bad request",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Bad request",
                    "error": {"code": "BAD_REQUEST", "details": None},
                }
            }
        },
    },
    401: {
        "model": ErrorResponse,
        "description": "Authentication required or invalid",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Authentication required",
                    "error": {"code": "UNAUTHORIZED", "details": None},
                }
            }
        },
    },
    403: {
        "model": ErrorResponse,
        "description": "Authenticated but not permitted",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "You do not have permission to perform this action",
                    "error": {"code": "FORBIDDEN", "details": None},
                }
            }
        },
    },
    404: {
        "model": ErrorResponse,
        "description": "Resource not found",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Resource not found",
                    "error": {"code": "NOT_FOUND", "details": None},
                }
            }
        },
    },
    409: {
        "model": ErrorResponse,
        "description": "Conflict with existing state",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Resource already exists",
                    "error": {"code": "CONFLICT", "details": None},
                }
            }
        },
    },
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Request validation failed",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "details": [
                            {
                                "field": "field_name",
                                "message": "Field required",
                                "type": "missing",
                            }
                        ],
                    },
                }
            }
        },
    },
    500: {
        "model": ErrorResponse,
        "description": "Unexpected server error (message never leaks internals)",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "An unexpected error occurred. Please try again later.",
                    "error": {"code": "INTERNAL_SERVER_ERROR", "details": None},
                }
            }
        },
    },
    503: {
        "model": ErrorResponse,
        "description": "Dependency unavailable",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Database is unavailable",
                    "error": {"code": "DATABASE_UNAVAILABLE", "details": None},
                }
            }
        },
    },
}
