"""Health check schemas."""

from pydantic import BaseModel, Field

from app.schemas.common import SuccessResponse


class HealthData(BaseModel):
    """Liveness/readiness payload."""

    status: str = Field(
        ...,
        description="ok when the probe succeeded.",
        examples=["ok"],
    )


class HealthResponse(SuccessResponse):
    """Envelope wrapping health data."""

    message: str = Field(
        ...,
        description="UI-safe summary of the probe result.",
        examples=["Service is healthy"],
    )
    data: HealthData
