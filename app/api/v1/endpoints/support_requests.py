"""Super Admin support request management endpoints."""

import uuid

from fastapi import APIRouter, Depends, Path, Query, status

from app.dependencies.auth import get_current_super_admin
from app.dependencies.support_requests import get_support_request_service
from app.models.super_admin import SuperAdmin
from app.schemas.common import ErrorResponse
from app.schemas.support_request import (
    SupportRequestCloseResponse,
    SupportRequestListResponse,
    SupportRequestRespondRequest,
    SupportRequestResponse,
)
from app.services.support_request_service import SupportRequestService

router = APIRouter(prefix="/support-requests", tags=["support-requests"])
legacy_router = APIRouter(prefix="/support-requests", tags=["support-requests"])

_AUTH_ERROR_EXAMPLE = {
    "success": False,
    "message": "Authentication required.",
    "error": {"code": "AUTHENTICATION_FAILED", "details": None},
}
_FORBIDDEN_EXAMPLE = {
    "success": False,
    "message": "Super Admin role required.",
    "error": {"code": "AUTHORIZATION_FAILED", "details": None},
}
_NOT_FOUND_EXAMPLE = {
    "success": False,
    "message": "Support request not found.",
    "error": {"code": "SUPPORT_REQUEST_NOT_FOUND", "details": None},
}
_CLOSED_CONFLICT_EXAMPLE = {
    "success": False,
    "message": "Cannot respond to a closed support request.",
    "error": {"code": "SUPPORT_REQUEST_CLOSED", "details": {"status": "closed"}},
}
_VALIDATION_EXAMPLE = {
    "success": False,
    "message": "Validation error",
    "error": {
        "code": "VALIDATION_ERROR",
        "details": [{"field": "response", "message": "Response is required."}],
    },
}
_BAD_REQUEST_EXAMPLE = {
    "success": False,
    "message": "Request failed",
    "error": {"code": "BAD_REQUEST", "details": None},
}
_SERVER_ERROR_EXAMPLE = {
    "success": False,
    "message": "An unexpected error occurred.",
    "error": {"code": "INTERNAL_SERVER_ERROR", "details": None},
}

_PROTECTED_ERROR_RESPONSES = {
    400: {
        "description": "Malformed request.",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _BAD_REQUEST_EXAMPLE}},
    },
    401: {
        "description": "Missing, invalid, or expired JWT bearer token.",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _AUTH_ERROR_EXAMPLE}},
    },
    403: {
        "description": "Authenticated caller is not a Super Admin.",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _FORBIDDEN_EXAMPLE}},
    },
    422: {
        "description": (
            "Request validation error (field-level details in error.details)."
        ),
        "model": ErrorResponse,
        "content": {"application/json": {"example": _VALIDATION_EXAMPLE}},
    },
    500: {
        "description": "Internal server error.",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _SERVER_ERROR_EXAMPLE}},
    },
}

_LIST_DESCRIPTION = (
    "Return a paginated list of support requests for the Super Admin Support "
    "Requests Management screen. Each item includes Request ID (id), User Name "
    "(name/user_name), Date Submitted (submitted_at), Status, the original "
    "request text (request/description), and any Super Admin response. Newest "
    "requests appear first. Empty catalogs return success with data.items=[]. "
    "Requires Authorization: Bearer <JWT> from POST /api/login. Use page and "
    "page_size query parameters for list pagination."
)
_RESPOND_DESCRIPTION = (
    "Submit a Super Admin reply from the Response Text Area. POST identifies "
    "the target request in the body (id) because the path has no {id}. "
    "response is required and cannot be blank. Closed requests return 409 "
    "SUPPORT_REQUEST_CLOSED. Unknown id returns 404 SUPPORT_REQUEST_NOT_FOUND. "
    "Requires Super Admin JWT."
)
_CLOSE_DESCRIPTION = (
    "Close a support request after the UI confirmation modal. DELETE does not "
    "hard-delete the row; it sets status=closed so the request remains visible "
    "in the list. Successful close returns 200 with a confirmation message in "
    "message/description (not 204) so the frontend can show a success toast. "
    "Closing an already-closed request is idempotent. Requires Super Admin JWT."
)


async def _list_support_requests(
    page: int,
    page_size: int,
    service: SupportRequestService,
) -> SupportRequestListResponse:
    """Shared list handler for versioned and legacy routes."""
    return await service.list_support_requests(page=page, page_size=page_size)


async def _respond_to_support_request(
    body: SupportRequestRespondRequest,
    service: SupportRequestService,
) -> SupportRequestResponse:
    """Shared respond handler for versioned and legacy routes."""
    return await service.respond_to_support_request(body)


async def _close_support_request(
    request_id: uuid.UUID,
    service: SupportRequestService,
) -> SupportRequestCloseResponse:
    """Shared close handler for versioned and legacy routes."""
    return await service.close_support_request(request_id)


@router.get(
    "",
    response_model=SupportRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List support requests",
    description=_LIST_DESCRIPTION,
    operation_id="listSupportRequestsV1",
    responses={
        200: {
            "description": "Paginated support request list.",
            "model": SupportRequestListResponse,
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def list_support_requests_v1(
    page: int = Query(
        1,
        ge=1,
        description="1-based page number.",
        examples=[1],
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of support requests per page.",
        examples=[20],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> SupportRequestListResponse:
    """Fetch a paginated list of support requests for Super Admin."""
    return await _list_support_requests(page, page_size, service)


@router.post(
    "",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Respond to a support request",
    description=_RESPOND_DESCRIPTION,
    operation_id="respondToSupportRequestV1",
    responses={
        200: {
            "description": "Support request updated with the Super Admin response.",
            "model": SupportRequestResponse,
        },
        404: {
            "description": "Support request does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Support request is already closed.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _CLOSED_CONFLICT_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def respond_to_support_request_v1(
    body: SupportRequestRespondRequest,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> SupportRequestResponse:
    """Save a Super Admin response on a support request."""
    return await _respond_to_support_request(body, service)


@router.delete(
    "/{id}",
    response_model=SupportRequestCloseResponse,
    status_code=status.HTTP_200_OK,
    summary="Close a support request",
    description=_CLOSE_DESCRIPTION,
    operation_id="closeSupportRequestV1",
    responses={
        200: {
            "description": "Support request closed. Confirmation is in message.",
            "model": SupportRequestCloseResponse,
        },
        404: {
            "description": "Support request does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def close_support_request_v1(
    id: uuid.UUID = Path(
        ...,
        description="Support request identifier (UUID).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> SupportRequestCloseResponse:
    """Close a support request after UI confirmation."""
    return await _close_support_request(id, service)


@legacy_router.get(
    "",
    response_model=SupportRequestListResponse,
    status_code=status.HTTP_200_OK,
    summary="List support requests",
    description=_LIST_DESCRIPTION
    + " Primary frontend path: GET /api/support-requests.",
    operation_id="listSupportRequests",
    responses={
        200: {
            "description": "Paginated support request list.",
            "model": SupportRequestListResponse,
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def list_support_requests_legacy(
    page: int = Query(
        1,
        ge=1,
        description="1-based page number.",
        examples=[1],
    ),
    page_size: int = Query(
        20,
        ge=1,
        le=100,
        description="Number of support requests per page.",
        examples=[20],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> SupportRequestListResponse:
    """Fetch a paginated list of support requests for Super Admin."""
    return await _list_support_requests(page, page_size, service)


@legacy_router.post(
    "",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Respond to a support request",
    description=(
        _RESPOND_DESCRIPTION + " Primary frontend path: POST /api/support-requests."
    ),
    operation_id="respondToSupportRequest",
    responses={
        200: {
            "description": "Support request updated with the Super Admin response.",
            "model": SupportRequestResponse,
        },
        404: {
            "description": "Support request does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Support request is already closed.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _CLOSED_CONFLICT_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def respond_to_support_request_legacy(
    body: SupportRequestRespondRequest,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> SupportRequestResponse:
    """Save a Super Admin response on a support request."""
    return await _respond_to_support_request(body, service)


@legacy_router.delete(
    "/{id}",
    response_model=SupportRequestCloseResponse,
    status_code=status.HTTP_200_OK,
    summary="Close a support request",
    description=(
        _CLOSE_DESCRIPTION
        + " Primary frontend path: DELETE /api/support-requests/{id}."
    ),
    operation_id="closeSupportRequest",
    responses={
        200: {
            "description": "Support request closed. Confirmation is in message.",
            "model": SupportRequestCloseResponse,
        },
        404: {
            "description": "Support request does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def close_support_request_legacy(
    id: uuid.UUID = Path(
        ...,
        description="Support request identifier (UUID).",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: SupportRequestService = Depends(get_support_request_service),
) -> SupportRequestCloseResponse:
    """Close a support request after UI confirmation."""
    return await _close_support_request(id, service)
