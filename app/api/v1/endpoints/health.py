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
        "running. No Authorization header is required."
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
        400: _errors[400],
        401: _errors[401],
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
        422: _errors[422],
        500: _errors[500],
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
        400: _errors[400],
        401: _errors[401],
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
        422: _errors[422],
        500: _errors[500],
        503: {
            "description": "Database unavailable.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Database unavailable",
                        "description": "Database unavailable",
                        "error": {"code": "SERVICE_UNAVAILABLE", "details": None},
                    }
                }
            },
        },
    },
)
async def health_ready(db: AsyncSession = Depends(get_db)) -> dict:
    """Return readiness after a database ping."""
    data = await HealthService(HealthRepository(db)).readiness()
    return {"success": True, "message": "Service is ready", "data": data}
