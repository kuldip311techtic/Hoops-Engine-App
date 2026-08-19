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
    data: HealthData = Field(..., description="Health details.")
