"""Health liveness and readiness use-cases."""

from app.exceptions.base import ServiceUnavailableError
from app.repositories.health_repository import HealthRepository


class HealthService:
    """Probes used by load balancers and orchestrators."""

    def __init__(self, repository: HealthRepository | None = None) -> None:
        """Optionally inject a repository for the readiness probe."""
        self._repository = repository

    async def liveness(self) -> dict[str, str]:
        """Return process liveness without touching the database."""
        return {"status": "ok"}

    async def readiness(self) -> dict[str, str]:
        """Return readiness after a database ping.

        Raises:
            ServiceUnavailableError: When the database is unreachable.
        """
        if self._repository is None:
            raise ServiceUnavailableError("Database unavailable")
        ok = await self._repository.ping()
        if not ok:
            raise ServiceUnavailableError("Database unavailable")
        return {"status": "ok"}
