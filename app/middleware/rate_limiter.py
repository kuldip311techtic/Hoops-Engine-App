"""slowapi rate limiter configured from settings."""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

_settings = get_settings()

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[_settings.login_rate_limit],
    enabled=not _settings.is_test,
)


def get_limiter() -> Limiter:
    """Return the process-wide Limiter instance."""
    return limiter
