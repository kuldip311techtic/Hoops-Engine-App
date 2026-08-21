"""Request/response logging middleware."""

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_REDACTED_HEADERS = {"authorization", "cookie", "set-cookie", "x-api-key"}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration without sensitive headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Log a single HTTP request/response cycle."""
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        logger.info(
            "http_request method={} path={} status={} duration_ms={} client={}",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request.client.host if request.client else None,
        )
        return response


def header_is_sensitive(name: str) -> bool:
    """Return True if a header must not be written to logs."""
    return name.lower() in _REDACTED_HEADERS
