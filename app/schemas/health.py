"""Health-check request/response schemas."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthData(BaseModel):
    """Liveness/readiness payload nested under ``data``.

    Includes the Admin FE login-screen field names (email, password,
    description, error, message) so Figma flatteners can read the same keys
    on every JSON response. ``password`` is always empty — never a secret.
    """

    status: str = Field(
        ...,
        description="Probe status. ``ok`` when the check passed.",
        examples=["ok"],
    )
    email: str = Field(
        default="",
        description="No authenticated user on a public probe; empty string.",
        examples=[""],
    )
    password: str = Field(
        default="",
        description="Always empty. Passwords are never returned by this API.",
        examples=[""],
    )
    description: str = Field(
        default="Public health probe",
        description="UI copy describing this probe",
        examples=["Public health probe"],
    )
    message: str = Field(
        default="Service is healthy",
        description="UI-safe status message (mirrors the envelope message)",
        examples=["Service is healthy"],
    )
    error: None = Field(
        default=None,
        description="Always null on success; failures use the error envelope",
        examples=[None],
    )


class HealthResponse(BaseModel):
    """Successful health-check envelope."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "message": "Service is healthy",
                    "data": {
                        "status": "ok",
                        "email": "",
                        "password": "",
                        "description": "Public health probe",
                        "message": "Service is healthy",
                        "error": None,
                    },
                }
            ]
        }
    )

    success: Literal[True] = Field(
        default=True,
        description="Always true on success",
        examples=[True],
    )
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
