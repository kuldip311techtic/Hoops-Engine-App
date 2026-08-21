"""Health-check data access."""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class HealthRepository:
    """Database probes used by the health service."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> bool:
        """Return True when the database answers ``SELECT 1``."""
        result = await self._session.execute(text("SELECT 1"))
        return result.scalar_one() == 1
