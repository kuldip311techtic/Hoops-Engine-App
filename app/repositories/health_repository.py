"""Database ping used by the readiness probe."""

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepository:
    """Runs a trivial query to confirm PostgreSQL is reachable."""

    def __init__(self, session: AsyncSession) -> None:
        """Store the async session."""
        self._session = session

    async def ping(self) -> bool:
        """Return True when ``SELECT 1`` succeeds."""
        try:
            await self._session.execute(text("SELECT 1"))
            return True
        except Exception:
            logger.exception("db_ping_failed")
            return False
