"""Loguru logging configuration."""

import logging
import sys
from pathlib import Path

from loguru import logger

from app.core.config import Settings


class InterceptHandler(logging.Handler):
    """Forward standard-library logging records to loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a stdlib log record through loguru."""
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1
        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def configure_logging(settings: Settings | None = None) -> None:
    """Configure loguru sinks for stderr and rotating files."""
    from app.core.config import get_settings

    resolved = settings or get_settings()
    logger.remove()
    logger.add(
        sys.stderr,
        level=resolved.log_level,
        backtrace=False,
        diagnose=False,
    )
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    logger.add(
        logs_dir / "app_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="14 days",
        level=resolved.log_level,
        backtrace=False,
        diagnose=False,
    )
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        logging.getLogger(name).handlers = [InterceptHandler()]
