"""Loguru logging configuration."""

import sys

from loguru import logger

from app.core.config import get_settings

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging() -> None:
    """Configure application logging sinks."""
    settings = get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level.upper(),
        format=LOG_FORMAT,
        enqueue=True,
    )
    logger.add(
        "logs/app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="14 days",
        level=settings.log_level.upper(),
        format=LOG_FORMAT,
        enqueue=True,
    )


__all__ = ["logger", "setup_logging"]
