"""Request/response access logging."""

import time

from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import redact_header


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, and duration. Redact Authorization."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Emit an access log line after the response is produced."""
        started = time.perf_counter()
        auth = request.headers.get("authorization", "")
        redact_header("authorization", auth)
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - started) * 1000
            logger.exception(
                "http_request_failed method={} path={} duration_ms={:.2f}",
                request.method,
                request.url.path,
                duration_ms,
            )
            raise
        duration_ms = (time.perf_counter() - started) * 1000
        client = request.client.host if request.client else "-"
        logger.info(
            "http_request method={} path={} status={} duration_ms={:.2f} client={}",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            client,
        )
        return response
