"""Health check schemas."""

from pydantic import BaseModel, ConfigDict, Field


class HealthData(BaseModel):
    """Health check payload."""

    status: str = Field(..., description="Service health status.", examples=["healthy"])


class HealthResponse(BaseModel):
    """Health check success envelope."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Service is healthy.",
                "email": None,
                "token": None,
                "data": {"status": "healthy"},
            }
        }
    )

    success: bool = Field(default=True, description="Always true when service is healthy.")
    message: str = Field(
        default="Service is healthy.",
        description="Human-readable status message.",
        examples=["Service is healthy."],
    )
    email: str | None = Field(
        default=None,
        description="Not populated on health checks; present for consistent API envelope keys.",
    )
    token: str | None = Field(
        default=None,
        description="Not populated on health checks; present for consistent API envelope keys.",
    )
    data: HealthData = Field(..., description="Health details.")
