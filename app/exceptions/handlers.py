"""Exception handlers that emit the project error envelope."""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions.base import AppError
from app.schemas.common import ErrorBody, ErrorResponse

_STATUS_CODES: dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMIT_EXCEEDED",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
}


def _error_payload(
    *,
    message: str,
    code: str,
    details: list[dict] | dict | None = None,
) -> dict:
    """Build the canonical error envelope."""
    body = ErrorResponse(
        success=False,
        message=message,
        error=ErrorBody(code=code, details=details),
    )
    return body.model_dump()


def _loc_to_field(loc: tuple | list) -> str:
    """Turn a Pydantic ``loc`` tuple into a dotted field path."""
    parts = [str(item) for item in loc if item != "body"]
    return ".".join(parts) if parts else "body"


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Serialize ``AppError`` into the project error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(
            message=exc.message,
            code=exc.code,
            details=exc.details,
        ),
    )


async def validation_error_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return field-level validation details without leaking internals."""
    details = []
    for error in exc.errors():
        details.append(
            {
                "field": _loc_to_field(error.get("loc", ())),
                "message": error.get("msg", "Invalid value"),
                "type": error.get("type", "value_error"),
            }
        )
    return JSONResponse(
        status_code=422,
        content=_error_payload(
            message="Request validation failed",
            code="VALIDATION_ERROR",
            details=details,
        ),
    )


async def http_exception_handler(
    _request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """Normalize Starlette/FastAPI HTTPException to the project envelope."""
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    details = None if isinstance(exc.detail, str) else exc.detail
    code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_payload(message=message, code=code, details=details),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected errors and return a UI-safe 500 — never str(exc)."""
    logger.opt(exception=exc).error(
        "Unhandled exception on {} {}",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content=_error_payload(
            message="An unexpected error occurred. Please try again later.",
            code="INTERNAL_SERVER_ERROR",
            details=None,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all exception handlers to ``app``."""
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
