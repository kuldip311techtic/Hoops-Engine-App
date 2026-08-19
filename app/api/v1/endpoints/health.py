"""Health check endpoint."""

from fastapi import APIRouter, status

from app.schemas.common import ErrorResponse
from app.schemas.health import HealthData, HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description=(
        "Returns the current health status of the API service. "
        "Use this endpoint for load balancer probes and uptime monitoring. "
        "No authentication is required."
    ),
    tags=["health"],
    responses={
        200: {
            "description": "Service is healthy.",
            "model": HealthResponse,
        },
        422: {
            "description": "Validation error.",
            "model": ErrorResponse,
        },
        429: {
            "description": "Rate limit exceeded.",
            "model": ErrorResponse,
        },
        500: {
            "description": "Internal server error.",
            "model": ErrorResponse,
        },
    },
)
async def health_check() -> HealthResponse:
    """Verify that the API is running and responsive."""
    return HealthResponse(
        success=True,
        message="Service is healthy.",
        data=HealthData(status="healthy"),
    )
