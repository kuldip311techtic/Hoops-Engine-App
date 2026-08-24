"""FastAPI exception handlers that emit the standard error envelope."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.responses import Response

from app.exceptions.base import AppError
from app.schemas.common import error_body


def _status_code_to_default(status_code: int) -> tuple[str, str]:
    """Map an HTTP status to a default (code, message) pair."""
    mapping = {
        400: ("BAD_REQUEST", "Bad request"),
        401: ("UNAUTHORIZED", "Not authenticated"),
        403: ("FORBIDDEN", "Access denied"),
        404: ("NOT_FOUND", "Resource not found"),
        409: ("CONFLICT", "Resource already exists"),
        422: ("VALIDATION_ERROR", "Request validation failed"),
        429: ("RATE_LIMITED", "Too many requests"),
        500: ("INTERNAL_ERROR", "Internal server error"),
        503: ("SERVICE_UNAVAILABLE", "Service unavailable"),
    }
    return mapping.get(status_code, ("APP_ERROR", "Request failed"))


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Serialize an ``AppError`` into the standard error envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.message, exc.code, exc.details),
    )


async def http_exception_handler(_request: Request, exc: HTTPException) -> Response:
    """Serialize FastAPI/Starlette HTTPException into the envelope."""
    code, default_message = _status_code_to_default(exc.status_code)
    message = default_message
    if isinstance(exc.detail, str) and exc.detail:
        message = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(message, code, None),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """Return 422 with field-level details for the UI."""
    details = []
    for err in exc.errors():
        loc = list(err.get("loc", []))
        field = ".".join(str(part) for part in loc if part != "body")
        msg = err.get("msg", "Invalid value")
        details.append(
            {
                "field": field or "body",
                "message": msg,
                "msg": msg,
                "type": err.get("type", "value_error"),
                "loc": loc,
            }
        )
    return JSONResponse(
        status_code=422,
        content=error_body(
            "Request validation failed",
            "VALIDATION_ERROR",
            details,
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected errors and return a generic 500 that does not leak internals."""
    logger.exception(
        "unhandled_exception path={} method={}",
        request.url.path,
        request.method,
    )
    return JSONResponse(
        status_code=500,
        content=error_body("Internal server error", "INTERNAL_ERROR", None),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach application exception handlers to ``app``."""
    app.add_exception_handler(AppError, app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(HTTPException, http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
