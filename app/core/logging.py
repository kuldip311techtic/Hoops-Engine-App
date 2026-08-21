"""Loguru configuration for stderr and rotating files."""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import get_settings

_CONFIGURED = False


def configure_logging() -> None:
    """Configure loguru sinks. Safe to call more than once."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    settings = get_settings()
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level)
    logs_dir = Path("logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        str(logs_dir / "app_{time:YYYY-MM-DD}.log"),
        rotation="1 day",
        retention="14 days",
        level=settings.log_level,
        enqueue=True,
    )
    _CONFIGURED = True


def redact_header(name: str, value: str) -> str:
    """Return a log-safe header value, redacting Authorization."""
    if name.lower() == "authorization":
        return "[REDACTED]"
    return value
