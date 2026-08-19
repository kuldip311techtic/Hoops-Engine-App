"""Global exception handlers producing frontend-friendly envelopes."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.logging import logger
from app.exceptions.base import AppException
from app.schemas.common import ErrorDetail, ErrorResponse


def _error_response(
    *,
    status_code: int,
    message: str,
    code: str,
    details: Any = None,
) -> JSONResponse:
    """Build a standardized error JSON response."""
    body = ErrorResponse(
        success=False,
        message=message,
        error=ErrorDetail(code=code, details=details),
    )
    return JSONResponse(status_code=status_code, content=body.model_dump())


async def app_exception_handler(_request: Request, exc: AppException) -> JSONResponse:
    """Handle project-specific AppException instances."""
    logger.warning("AppException: {} ({})", exc.message, exc.error_code)
    return _error_response(
        status_code=exc.status_code,
        message=exc.message,
        code=exc.error_code,
        details=exc.details,
    )


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Handle Pydantic/FastAPI request validation errors."""
    field_errors = []
    for error in exc.errors():
        loc = error.get("loc", ())
        field = ".".join(str(part) for part in loc if part != "body") or "body"
        field_errors.append({"field": field, "message": error.get("msg", "Invalid value")})
    return _error_response(
        status_code=422,
        message="Validation error",
        code="VALIDATION_ERROR",
        details=field_errors,
    )


async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Handle Starlette/FastAPI HTTP exceptions."""
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_SERVER_ERROR",
    }
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return _error_response(
        status_code=exc.status_code,
        message=message,
        code=code_map.get(exc.status_code, "HTTP_ERROR"),
        details=None,
    )


async def rate_limit_exception_handler(
    _request: Request,
    exc: RateLimitExceeded,
) -> JSONResponse:
    """Handle slowapi rate limit violations."""
    return _error_response(
        status_code=429,
        message="Too many requests. Please try again later.",
        code="RATE_LIMIT_EXCEEDED",
        details={"retry_after": exc.detail},
    )


async def unhandled_exception_handler(
    _request: Request,
    exc: Exception,
) -> JSONResponse:
    """Handle unexpected exceptions without leaking internals in production."""
    settings = get_settings()
    logger.exception("Unhandled exception: {}", exc)
    message = (
        "An unexpected error occurred."
        if settings.is_production
        else "An unexpected error occurred."
    )
    details = None if settings.is_production else {"type": exc.__class__.__name__}
    return _error_response(
        status_code=500,
        message=message,
        code="INTERNAL_SERVER_ERROR",
        details=details,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RateLimitExceeded, rate_limit_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
