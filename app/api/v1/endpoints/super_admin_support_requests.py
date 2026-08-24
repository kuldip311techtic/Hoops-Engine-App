"""Super Admin support request management routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.admin import get_current_super_admin, get_support_request_service
from app.models.support_request import SupportRequestStatus
from app.models.user import User
from app.schemas.common import openapi_error_map
from app.schemas.support_request import (
    SupportRequestActionResponse,
    SupportRequestListResponse,
    SupportRequestRespondRequest,
)
from app.services.support_request_service import SupportRequestService

router = APIRouter()
_errors = openapi_error_map()

_request_example = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "subject": "Cannot access practice plans",
    "description": "I am unable to view practice plans after logging in.",
    "message": "I am unable to view practice plans after logging in.",
    "status": "OPEN",
    "submitter_email": "user@example.com",
    "admin_response": None,
    "created_at": "2026-08-24T12:00:00+00:00",
    "updated_at": "2026-08-24T12:00:00+00:00",
    "responded_at": None,
    "closed_at": None,
}

_common_responses = {
    400: _errors[400],
    401: _errors[401],
    403: _errors[403],
    404: _errors[404],
    409: _errors[409],
    422: _errors[422],
    500: _errors[500],
}


@router.get(
    "",
    response_model=SupportRequestListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_support_requests",
    summary="List support requests",
    description=(
        "Super Admin only. Returns all user-submitted support requests for the "
        "Support Requests Management table. Each item includes `id`, `request_id`, "
        "`subject`, `description` (user inquiry text), `status`, `submitter_email`, "
        "`admin_response`, and timestamps. Optional `status` query filter accepts "
        "OPEN, RESPONDED, or CLOSED. Requires Bearer JWT for a Super Admin account."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Support requests retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Support requests retrieved",
                        "description": "Support requests retrieved successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {
                            "items": [_request_example],
                            "total": 1,
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def list_support_requests(
    status_filter: SupportRequestStatus | None = Query(
        default=None,
        alias="status",
        description="Optional filter by support request status.",
    ),
    _admin: User = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> dict:
    """Return support requests for the Super Admin dashboard."""
    items, total = await service.list_requests(status=status_filter)
    return {
        "success": True,
        "message": "Support requests retrieved",
        "description": "Support requests retrieved successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": {
            "items": [item.model_dump(mode="json") for item in items],
            "total": total,
        },
    }


@router.post(
    "",
    response_model=SupportRequestActionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="respond_support_request",
    summary="Respond to a support request",
    description=(
        "Super Admin only. Records an admin response for an existing support "
        "request identified by `request_id` in the JSON body. Sets status to "
        "RESPONDED and stores `response` as `admin_response`. Returns 404 when "
        "the request does not exist. Returns 400 when the request is already "
        "CLOSED. Re-submitting the same response on an already RESPONDED request "
        "is idempotent and returns 200. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Response recorded.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Support request updated",
                        "description": "Your response was saved successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {
                            **_request_example,
                            "status": "RESPONDED",
                            "admin_response": "Thank you for your inquiry!",
                            "responded_at": "2026-08-24T12:05:00+00:00",
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def respond_support_request(
    body: SupportRequestRespondRequest,
    admin: User = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> dict:
    """Respond to a user support request."""
    result = await service.respond(
        body.request_id,
        body.response,
        actor=admin,
    )
    return {
        "success": True,
        "message": "Support request updated",
        "description": "Your response was saved successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": result.model_dump(mode="json"),
    }


@router.put(
    "/{request_id}",
    response_model=SupportRequestActionResponse,
    status_code=status.HTTP_200_OK,
    operation_id="close_support_request",
    summary="Close a support request",
    description=(
        "Super Admin only. Marks the support request identified by `{request_id}` "
        "as CLOSED. Returns 404 when the request does not exist. Closing an "
        "already CLOSED request is idempotent and returns 200. Requires Bearer "
        "JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Support request closed.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Support request closed",
                        "description": "The support request was closed successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {
                            **_request_example,
                            "status": "CLOSED",
                            "closed_at": "2026-08-24T12:10:00+00:00",
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def close_support_request(
    request_id: UUID,
    admin: User = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> dict:
    """Close a support request."""
    result = await service.close(request_id, actor=admin)
    return {
        "success": True,
        "message": "Support request closed",
        "description": "The support request was closed successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": result.model_dump(mode="json"),
    }
