"""Liveness and readiness HTTP endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.middleware.rate_limiter import limiter
from app.repositories.health_repository import HealthRepository
from app.schemas.common import ERROR_RESPONSES
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter(tags=["health"])


def get_liveness_service() -> HealthService:
    """Liveness does not query the database."""
    return HealthService(repository=None)


def get_readiness_service(
    session: AsyncSession = Depends(get_db),
) -> HealthService:
    """Readiness probes PostgreSQL through the repository layer."""
    return HealthService(repository=HealthRepository(session))


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description=(
        "Returns whether this API process is running. Does not check the "
        "database. Public; no authentication required."
    ),
    responses={
        200: {
            "description": "Process is up",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Service is healthy",
                        "data": {"status": "ok"},
                    }
                }
            },
        },
        500: ERROR_RESPONSES[500],
    },
)
@limiter.exempt
async def health_check(
    request: Request,
    service: HealthService = Depends(get_liveness_service),
) -> HealthResponse:
    """Return process liveness."""
    return service.liveness()


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description=(
        "Returns whether this API can serve traffic, including a PostgreSQL "
        "``SELECT 1`` ping. Public; no authentication required."
    ),
    responses={
        200: {
            "description": "Process and database are ready",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Service is ready",
                        "data": {"status": "ok"},
                    }
                }
            },
        },
        500: ERROR_RESPONSES[500],
        503: ERROR_RESPONSES[503],
    },
)
@limiter.exempt
async def health_ready(
    request: Request,
    service: HealthService = Depends(get_readiness_service),
) -> HealthResponse:
    """Return process + database readiness."""
    return await service.readiness()
