"""Health-check business logic."""

from loguru import logger

from app.exceptions import AppError
from app.repositories.health_repository import HealthRepository
from app.schemas.health import HealthData, HealthResponse


class HealthService:
    """Liveness and readiness checks."""

    def __init__(self, repository: HealthRepository | None = None) -> None:
        self._repository = repository

    def liveness(self) -> HealthResponse:
        """Process is up; does not touch the database."""
        return HealthResponse(
            success=True,
            message="Service is healthy",
            data=HealthData(status="ok"),
        )

    async def readiness(self) -> HealthResponse:
        """Process is up and the database accepts connections."""
        if self._repository is None:
            raise AppError(
                "Database is unavailable",
                status_code=503,
                code="DATABASE_UNAVAILABLE",
            )
        try:
            ok = await self._repository.ping()
        except Exception as exc:
            logger.opt(exception=exc).warning("database_ping_failed")
            raise AppError(
                "Database is unavailable",
                status_code=503,
                code="DATABASE_UNAVAILABLE",
            ) from exc
        if not ok:
            raise AppError(
                "Database is unavailable",
                status_code=503,
                code="DATABASE_UNAVAILABLE",
            )
        return HealthResponse(
            success=True,
            message="Service is ready",
            data=HealthData(status="ok"),
        )
