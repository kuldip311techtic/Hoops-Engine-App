"""Health endpoints. Thin: call HealthService and wrap the envelope."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.repositories.health_repository import HealthRepository
from app.schemas.common import openapi_error_map
from app.schemas.health import HealthResponse
from app.services.health_service import HealthService

router = APIRouter()
_errors = openapi_error_map()
_public = {"security": []}

_health_errors = {
    500: _errors[500],
}

_readiness_errors = {
    500: _errors[500],
    503: _errors[503],
}


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    operation_id="health_liveness",
    summary="Liveness probe",
    description=(
        "Public liveness probe for the Hoops Engine API. Returns process "
        "liveness without querying PostgreSQL. The payload uses the standard "
        "success envelope with `data.status` set to `ok` when the process is "
        "running. No Authorization header is required. Returns 500 only on "
        "unexpected server failure."
    ),
    tags=["health"],
    openapi_extra=_public,
    responses={
        200: {
            "description": "Service is healthy.",
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
        **_health_errors,
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
    operation_id="health_readiness",
    summary="Readiness probe",
    description=(
        "Public readiness probe. Confirms the API can reach PostgreSQL with "
        "`SELECT 1`. Returns 200 with `data.status=ok` when the database "
        "accepts connections. Returns 503 SERVICE_UNAVAILABLE when the "
        "database is down. No Authorization header is required."
    ),
    tags=["health"],
    openapi_extra=_public,
    responses={
        200: {
            "description": "Database is reachable.",
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
        **_readiness_errors,
    },
)
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict:
    """Return readiness after a database ping."""
    data = await HealthService(HealthRepository(db)).readiness()
    return {"success": True, "message": "Service is ready", "data": data}
