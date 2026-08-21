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

_HEALTH_ERRORS = {
    400: ERROR_RESPONSES[400],
    401: ERROR_RESPONSES[401],
    403: ERROR_RESPONSES[403],
    404: ERROR_RESPONSES[404],
    409: ERROR_RESPONSES[409],
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
}


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
    operation_id="health_liveness",
    description=(
        "Returns whether this API process is running. Does not check the "
        "database. Used by orchestrators as a liveness probe. Public; no "
        "authentication required. Exempt from rate limiting."
    ),
    responses={
        200: {
            "model": HealthResponse,
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
        **_HEALTH_ERRORS,
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
    operation_id="health_readiness",
    description=(
        "Returns whether this API can serve traffic, including a PostgreSQL "
        "``SELECT 1`` ping through the repository layer. Public; no "
        "authentication required. Returns 503 DATABASE_UNAVAILABLE when the "
        "database cannot be reached. Exempt from rate limiting."
    ),
    responses={
        200: {
            "model": HealthResponse,
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
        **_HEALTH_ERRORS,
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
