"""Pydantic schemas for Super Admin support request management."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.common import ErrorDetail

SupportRequestStatus = Literal["open", "responded", "closed"]


class SupportRequestRespondRequest(BaseModel):
    """Request body for POST /api/support-requests (respond form)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "response": "Please try resetting your password from the login screen.",
            }
        }
    )

    id: uuid.UUID = Field(
        ...,
        description="Identifier of the support request being answered.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    response: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="Super Admin reply shown in the Response Text Area.",
        examples=["Please try resetting your password from the login screen."],
    )

    @field_validator("response")
    @classmethod
    def response_not_blank(cls, value: str) -> str:
        """Reject whitespace-only responses before they reach the service."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("Response is required.")
        return stripped


class SupportRequestRead(BaseModel):
    """Support request resource returned to the frontend."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Request ID shown in the support requests list.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    user_id: uuid.UUID = Field(
        ...,
        description="Identifier of the user who submitted the request.",
        examples=["7c9e6679-7425-40de-944b-e07fc1f90ae7"],
    )
    name: str = Field(
        ...,
        description="User name shown in the list (frontend field).",
        examples=["Jane Player"],
    )
    user_name: str = Field(
        ...,
        description="User name alias matching the list column.",
        examples=["Jane Player"],
    )
    request: str = Field(
        ...,
        description="Original support inquiry text.",
        examples=["I cannot log in to my player account."],
    )
    description: str = Field(
        ...,
        description="Frontend alias for the original request text.",
        examples=["I cannot log in to my player account."],
    )
    response: str | None = Field(
        default=None,
        description="Super Admin reply, if one has been submitted.",
        examples=["Please try resetting your password from the login screen."],
    )
    status: SupportRequestStatus = Field(
        ...,
        description="open, responded, or closed.",
        examples=["open"],
    )
    submitted_at: datetime = Field(
        ...,
        description="Date submitted (created_at) for the list column.",
    )
    created_at: datetime = Field(
        ...,
        description="Timestamp when the request was submitted.",
    )


class SupportRequestListData(BaseModel):
    """Paginated support request collection."""

    items: list[SupportRequestRead] = Field(
        ...,
        description="Support requests for the requested page, newest first.",
    )
    total: int = Field(..., description="Total support request count.", examples=[1])
    page: int = Field(..., description="Current 1-based page number.", examples=[1])
    page_size: int = Field(
        ...,
        description="Page size used for this response.",
        examples=[20],
    )


class SupportRequestResponse(BaseModel):
    """Success envelope for a single support request (respond)."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Support request updated.",
                "description": "Your response was saved.",
                "email": None,
                "token": None,
                "support_request": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    "name": "Jane Player",
                    "user_name": "Jane Player",
                    "request": "I cannot log in to my player account.",
                    "description": "I cannot log in to my player account.",
                    "response": "Please try resetting your password.",
                    "status": "responded",
                    "submitted_at": "2026-08-19T12:00:00Z",
                    "created_at": "2026-08-19T12:00:00Z",
                },
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Jane Player",
                "status": "responded",
                "error": None,
                "data": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    "name": "Jane Player",
                    "user_name": "Jane Player",
                    "request": "I cannot log in to my player account.",
                    "description": "I cannot log in to my player account.",
                    "response": "Please try resetting your password.",
                    "status": "responded",
                    "submitted_at": "2026-08-19T12:00:00Z",
                    "created_at": "2026-08-19T12:00:00Z",
                },
            }
        }
    )

    success: bool = Field(default=True, description="Always true on success.")
    message: str = Field(..., description="UI-safe success message for toasts.")
    description: str = Field(..., description="Longer outcome description for UI copy.")
    email: str | None = Field(
        default=None,
        description="Not populated on support-request routes.",
    )
    token: str | None = Field(
        default=None,
        description="Not populated on support-request routes.",
    )
    support_request: SupportRequestRead | None = Field(
        default=None,
        description="Updated support request resource.",
    )
    id: uuid.UUID | None = Field(
        default=None,
        description="Support request id for single-item responses.",
    )
    name: str | None = Field(
        default=None,
        description="Submitter name for single-item responses.",
    )
    status: SupportRequestStatus | None = Field(
        default=None,
        description="Status after the operation.",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: SupportRequestRead = Field(..., description="Support request resource.")


class SupportRequestListResponse(BaseModel):
    """Success envelope for GET /api/support-requests."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Support requests retrieved.",
                "description": "Support request list loaded.",
                "email": None,
                "token": None,
                "support_request": None,
                "id": None,
                "name": None,
                "status": None,
                "error": None,
                "data": {
                    "items": [],
                    "total": 0,
                    "page": 1,
                    "page_size": 20,
                },
            }
        }
    )

    success: bool = Field(default=True, description="Always true on success.")
    message: str = Field(..., description="UI-safe success message.")
    description: str = Field(..., description="Longer outcome description for UI copy.")
    email: str | None = Field(
        default=None, description="Not populated on list responses."
    )
    token: str | None = Field(
        default=None,
        description="Not populated on support-request routes.",
    )
    support_request: SupportRequestRead | None = Field(
        default=None,
        description="Not populated on list responses; items are in data.items.",
    )
    id: uuid.UUID | None = Field(
        default=None,
        description="Not populated on list responses.",
    )
    name: str | None = Field(
        default=None, description="Not populated on list responses."
    )
    status: SupportRequestStatus | None = Field(
        default=None,
        description="Not populated on list responses; each item has its own status.",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: SupportRequestListData = Field(
        ...,
        description="Paginated support request collection.",
    )


class SupportRequestCloseResponse(BaseModel):
    """Success envelope for DELETE /api/support-requests/{id} confirmation."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Support request closed.",
                "description": "The support request was closed successfully.",
                "email": None,
                "token": None,
                "support_request": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    "name": "Jane Player",
                    "user_name": "Jane Player",
                    "request": "I cannot log in to my player account.",
                    "description": "I cannot log in to my player account.",
                    "response": None,
                    "status": "closed",
                    "submitted_at": "2026-08-19T12:00:00Z",
                    "created_at": "2026-08-19T12:00:00Z",
                },
                "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "name": "Jane Player",
                "status": "closed",
                "error": None,
                "data": {
                    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                    "user_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                    "name": "Jane Player",
                    "user_name": "Jane Player",
                    "request": "I cannot log in to my player account.",
                    "description": "I cannot log in to my player account.",
                    "response": None,
                    "status": "closed",
                    "submitted_at": "2026-08-19T12:00:00Z",
                    "created_at": "2026-08-19T12:00:00Z",
                },
            }
        }
    )

    success: bool = Field(default=True, description="Always true on success.")
    message: str = Field(
        ...,
        description="Confirmation message for the close toast.",
        examples=["Support request closed."],
    )
    description: str = Field(
        ...,
        description="Longer confirmation copy for the UI.",
        examples=["The support request was closed successfully."],
    )
    email: str | None = Field(default=None, description="Not populated after close.")
    token: str | None = Field(
        default=None,
        description="Not populated on support-request routes.",
    )
    support_request: SupportRequestRead | None = Field(
        default=None,
        description="Closed support request resource.",
    )
    id: uuid.UUID | None = Field(..., description="Identifier of the closed request.")
    name: str | None = Field(..., description="Submitter name of the closed request.")
    status: SupportRequestStatus | None = Field(
        default="closed",
        description="Status after close (always closed).",
    )
    error: ErrorDetail | None = Field(
        default=None, description="Always null on success."
    )
    data: SupportRequestRead = Field(
        ..., description="Closed support request resource."
    )
