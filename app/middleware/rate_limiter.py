"""slowapi rate limiter configured from settings."""

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.schemas.common import ErrorBody, ErrorResponse


def _storage_uri() -> str:
    """Use in-memory storage in tests; Redis otherwise."""
    settings = get_settings()
    if settings.is_test:
        return "memory://"
    return settings.redis_url or "memory://"


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=_storage_uri(),
    headers_enabled=True,
)


async def rate_limit_exceeded_handler(
    _request: Request,
    _exc: RateLimitExceeded,
) -> JSONResponse:
    """Return the project error envelope for HTTP 429."""
    body = ErrorResponse(
        success=False,
        message="Too many requests. Please try again later.",
        error=ErrorBody(code="RATE_LIMIT_EXCEEDED", details=None),
    )
    return JSONResponse(status_code=429, content=body.model_dump())
