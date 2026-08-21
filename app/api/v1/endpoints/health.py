"""Health endpoints. Thin: call HealthService and wrap the envelope."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.repositories.health_repository import HealthRepository
from app.schemas.common import openapi_error_map
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description=(
        "Returns process liveness without querying PostgreSQL. "
        "Use this for load-balancer health checks. The payload is wrapped in "
        "the standard success envelope; `data.status` is `ok` when the process "
        "is running."
    ),
    tags=["health"],
    responses={
        200: {
            "description": "Service is healthy",
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
        **{k: v for k, v in openapi_error_map().items() if k in (500,)},
    },
)
async def health_check() -> dict:
    """Return liveness status."""
    data = await HealthService().liveness()
    return {"success": True, "message": "Service is healthy", "data": data}


@router.get(
    "/health/ready",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness probe",
    description=(
        "Confirms the API can reach PostgreSQL (`SELECT 1`). Returns 503 with "
        "code SERVICE_UNAVAILABLE when the database is down."
    ),
    tags=["health"],
    responses={
        200: {
            "description": "Database is reachable",
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
        503: {
            "description": "Database unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Database unavailable",
                        "error": {"code": "SERVICE_UNAVAILABLE", "details": None},
                    }
                }
            },
        },
        **{k: v for k, v in openapi_error_map().items() if k in (500,)},
    },
)
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict:
    """Return readiness after a database ping."""
    data = await HealthService(HealthRepository(db)).readiness()
    return {"success": True, "message": "Service is ready", "data": data}
