"""Health-check request/response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthData(BaseModel):
    """Liveness/readiness payload nested under ``data``."""

    status: str = Field(
        ...,
        description="Probe status. ``ok`` when the check passed.",
        examples=["ok"],
    )


class HealthResponse(BaseModel):
    """Successful health-check envelope."""

    success: Literal[True] = Field(default=True, description="Always true on success")
    message: str = Field(
        ...,
        description="UI-safe status message",
        examples=["Service is healthy"],
    )
    data: HealthData = Field(
        ...,
        description="Probe details",
        examples=[{"status": "ok"}],
    )
