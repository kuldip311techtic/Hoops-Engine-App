"""Health check endpoint."""

from fastapi import APIRouter, status

from app.schemas.common import ErrorResponse
from app.schemas.health import HealthData, HealthResponse

router = APIRouter()

_HEALTH_SUCCESS_EXAMPLE = {
    "success": True,
    "message": "Service is healthy.",
    "data": {"status": "healthy"},
}

_HEALTH_RATE_LIMIT_EXAMPLE = {
    "success": False,
    "message": "Too many requests. Please try again later.",
    "error": {"code": "RATE_LIMIT_EXCEEDED", "details": {"retry_after": "200/minute"}},
}

_HEALTH_SERVER_ERROR_EXAMPLE = {
    "success": False,
    "message": "An unexpected error occurred.",
    "error": {"code": "INTERNAL_SERVER_ERROR", "details": None},
}


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description=(
        "Returns the current health status of the API service for load balancer probes "
        "and uptime monitoring. Does not query downstream dependencies. "
        "This endpoint is public — no Authorization header is required."
    ),
    tags=["health"],
    operation_id="getHealthStatus",
    responses={
        200: {
            "description": "Service is healthy.",
            "model": HealthResponse,
            "content": {"application/json": {"example": _HEALTH_SUCCESS_EXAMPLE}},
        },
        429: {
            "description": "Rate limit exceeded.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _HEALTH_RATE_LIMIT_EXAMPLE}},
        },
        500: {
            "description": "Internal server error.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _HEALTH_SERVER_ERROR_EXAMPLE}},
        },
    },
    openapi_extra={"security": []},
)
async def health_check() -> HealthResponse:
    """Verify that the API is running and responsive."""
    return HealthResponse(
        success=True,
        message="Service is healthy.",
        data=HealthData(status="healthy"),
    )
