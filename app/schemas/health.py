"""Health check schemas."""

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    """Health check payload."""

    status: str = Field(..., description="Service health status.", examples=["healthy"])


class HealthResponse(BaseModel):
    """Health check success envelope."""

    success: bool = Field(default=True, description="Always true when service is healthy.")
    message: str = Field(default="Service is healthy.", description="Human-readable status message.")
    data: HealthData = Field(..., description="Health details.")
