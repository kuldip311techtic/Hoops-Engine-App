"""Super Admin organization management endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.dependencies.auth import get_current_super_admin
from app.dependencies.organizations import get_organization_service
from app.models.super_admin import SuperAdmin
from app.schemas.common import ErrorResponse
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationDeleteResponse,
    OrganizationListResponse,
    OrganizationResponse,
    OrganizationUpdate,
)
from app.services.organization_service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])
legacy_router = APIRouter(prefix="/organizations", tags=["organizations"])

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
    "message": "Organization not found.",
    "error": {"code": "ORGANIZATION_NOT_FOUND", "details": None},
}
_NAME_CONFLICT_EXAMPLE = {
    "success": False,
    "message": "An organization with this name already exists.",
    "error": {
        "code": "ORGANIZATION_NAME_EXISTS",
        "details": [
            {
                "field": "name",
                "message": "An organization with this name already exists.",
            }
        ],
    },
}
_EMAIL_CONFLICT_EXAMPLE = {
    "success": False,
    "message": "An organization with this email already exists.",
    "error": {
        "code": "EMAIL_ALREADY_EXISTS",
        "details": [
            {
                "field": "email",
                "message": "An organization with this email already exists.",
            }
        ],
    },
}
_IN_USE_EXAMPLE = {
    "success": False,
    "message": (
        "This organization is currently in use and cannot be removed. "
        "Set status to inactive first."
    ),
    "error": {
        "code": "ORGANIZATION_IN_USE",
        "details": {"in_use": True, "status": "active"},
    },
}
_VALIDATION_EXAMPLE = {
    "success": False,
    "message": "Validation error",
    "error": {
        "code": "VALIDATION_ERROR",
        "details": [
            {"field": "email", "message": "value is not a valid email address"}
        ],
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
    "Return a paginated list of organizations for the Super Admin Manage Organizations "
    "screen. Each item includes id, name, email/contact_email, phone_number, address, "
    "description, and status (active or inactive). Active organizations are treated as "
    "currently in use. Requires Authorization: Bearer <JWT> from POST /api/login. "
    "Use page and page_size query parameters for list pagination."
)
_CREATE_DESCRIPTION = (
    "Create a new organization from the Add Organization form. Requires a unique name "
    "and unique contact email (case-insensitive). Send email (frontend) and optionally "
    "contact_email (API alias), plus phone_number, address, description, and status. "
    "Duplicate name returns 409 ORGANIZATION_NAME_EXISTS. Duplicate email returns 409 "
    "EMAIL_ALREADY_EXISTS. Requires Super Admin JWT."
)
_UPDATE_DESCRIPTION = (
    "Replace an existing organization's details from the Edit Organization form. "
    "All form fields are submitted. Name and email must remain unique. Unknown id "
    "returns 404 ORGANIZATION_NOT_FOUND. Requires Super Admin JWT."
)
_DELETE_DESCRIPTION = (
    "Remove an organization after the UI confirmation prompt. Active organizations "
    "are currently in use: DELETE returns 409 ORGANIZATION_IN_USE with a warning "
    "message so the UI can display it. Deactivate via PUT (status=inactive) first, "
    "then DELETE. Successful removal returns 200 with a confirmation message "
    "(not 204) so the frontend can show a success toast. Requires Super Admin JWT."
)


async def _list_organizations(
    page: int,
    page_size: int,
    service: OrganizationService,
) -> OrganizationListResponse:
    """Shared list handler for versioned and legacy routes."""
    return await service.list_organizations(page=page, page_size=page_size)


async def _create_organization(
    body: OrganizationCreate,
    service: OrganizationService,
) -> OrganizationResponse:
    """Shared create handler for versioned and legacy routes."""
    return await service.create_organization(body)


async def _update_organization(
    organization_id: uuid.UUID,
    body: OrganizationUpdate,
    service: OrganizationService,
) -> OrganizationResponse:
    """Shared update handler for versioned and legacy routes."""
    return await service.update_organization(organization_id, body)


async def _delete_organization(
    organization_id: uuid.UUID,
    service: OrganizationService,
) -> OrganizationDeleteResponse:
    """Shared delete handler for versioned and legacy routes."""
    return await service.delete_organization(organization_id)


@router.get(
    "",
    response_model=OrganizationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List organizations",
    description=_LIST_DESCRIPTION,
    operation_id="listOrganizationsV1",
    responses={
        200: {
            "description": "Paginated organization list.",
            "model": OrganizationListResponse,
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def list_organizations_v1(
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
        description="Number of organizations per page.",
        examples=[20],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationListResponse:
    """Fetch a paginated list of organizations for Super Admin."""
    return await _list_organizations(page, page_size, service)


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description=_CREATE_DESCRIPTION,
    operation_id="createOrganizationV1",
    responses={
        201: {
            "description": "Organization created.",
            "model": OrganizationResponse,
        },
        409: {
            "description": "Duplicate organization name or email.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "name_conflict": {
                            "summary": "ORGANIZATION_NAME_EXISTS",
                            "value": _NAME_CONFLICT_EXAMPLE,
                        },
                        "email_conflict": {
                            "summary": "EMAIL_ALREADY_EXISTS",
                            "value": _EMAIL_CONFLICT_EXAMPLE,
                        },
                    }
                }
            },
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def create_organization_v1(
    body: OrganizationCreate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Add a new organization with validated details."""
    return await _create_organization(body, service)


@router.put(
    "/{id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update organization",
    description=_UPDATE_DESCRIPTION,
    operation_id="updateOrganizationV1",
    responses={
        200: {
            "description": "Organization updated.",
            "model": OrganizationResponse,
        },
        404: {
            "description": "Organization does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Duplicate organization name or email.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "name_conflict": {
                            "summary": "ORGANIZATION_NAME_EXISTS",
                            "value": _NAME_CONFLICT_EXAMPLE,
                        },
                        "email_conflict": {
                            "summary": "EMAIL_ALREADY_EXISTS",
                            "value": _EMAIL_CONFLICT_EXAMPLE,
                        },
                    }
                }
            },
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def update_organization_v1(
    id: Annotated[
        uuid.UUID,
        Path(
            description="Organization identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    body: OrganizationUpdate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Edit an existing organization's details."""
    return await _update_organization(id, body, service)


@router.delete(
    "/{id}",
    response_model=OrganizationDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove organization",
    description=_DELETE_DESCRIPTION,
    operation_id="deleteOrganizationV1",
    responses={
        200: {
            "description": "Organization removed. Confirmation message is in message.",
            "model": OrganizationDeleteResponse,
        },
        404: {
            "description": "Organization does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": (
                "Organization is currently in use (active) and cannot be removed."
            ),
            "model": ErrorResponse,
            "content": {"application/json": {"example": _IN_USE_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def delete_organization_v1(
    id: Annotated[
        uuid.UUID,
        Path(
            description="Organization identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationDeleteResponse:
    """Remove an inactive organization after UI confirmation."""
    return await _delete_organization(id, service)


@legacy_router.get(
    "",
    response_model=OrganizationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List organizations",
    description=_LIST_DESCRIPTION + " Primary frontend path: GET /api/organizations.",
    operation_id="listOrganizations",
    responses={
        200: {
            "description": "Paginated organization list.",
            "model": OrganizationListResponse,
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def list_organizations_legacy(
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
        description="Number of organizations per page.",
        examples=[20],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationListResponse:
    """Fetch a paginated list of organizations for Super Admin."""
    return await _list_organizations(page, page_size, service)


@legacy_router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create organization",
    description=_CREATE_DESCRIPTION
    + " Primary frontend path: POST /api/organizations.",
    operation_id="createOrganization",
    responses={
        201: {
            "description": "Organization created.",
            "model": OrganizationResponse,
        },
        409: {
            "description": "Duplicate organization name or email.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "name_conflict": {
                            "summary": "ORGANIZATION_NAME_EXISTS",
                            "value": _NAME_CONFLICT_EXAMPLE,
                        },
                        "email_conflict": {
                            "summary": "EMAIL_ALREADY_EXISTS",
                            "value": _EMAIL_CONFLICT_EXAMPLE,
                        },
                    }
                }
            },
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def create_organization_legacy(
    body: OrganizationCreate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Add a new organization with validated details."""
    return await _create_organization(body, service)


@legacy_router.put(
    "/{id}",
    response_model=OrganizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update organization",
    description=_UPDATE_DESCRIPTION
    + " Primary frontend path: PUT /api/organizations/{id}.",
    operation_id="updateOrganization",
    responses={
        200: {
            "description": "Organization updated.",
            "model": OrganizationResponse,
        },
        404: {
            "description": "Organization does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Duplicate organization name or email.",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "name_conflict": {
                            "summary": "ORGANIZATION_NAME_EXISTS",
                            "value": _NAME_CONFLICT_EXAMPLE,
                        },
                        "email_conflict": {
                            "summary": "EMAIL_ALREADY_EXISTS",
                            "value": _EMAIL_CONFLICT_EXAMPLE,
                        },
                    }
                }
            },
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def update_organization_legacy(
    id: Annotated[
        uuid.UUID,
        Path(
            description="Organization identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    body: OrganizationUpdate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationResponse:
    """Edit an existing organization's details."""
    return await _update_organization(id, body, service)


@legacy_router.delete(
    "/{id}",
    response_model=OrganizationDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove organization",
    description=(
        _DELETE_DESCRIPTION + " Primary frontend path: DELETE /api/organizations/{id}."
    ),
    operation_id="deleteOrganization",
    responses={
        200: {
            "description": "Organization removed. Confirmation message is in message.",
            "model": OrganizationDeleteResponse,
        },
        404: {
            "description": "Organization does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": (
                "Organization is currently in use (active) and cannot be removed."
            ),
            "model": ErrorResponse,
            "content": {"application/json": {"example": _IN_USE_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def delete_organization_legacy(
    id: Annotated[
        uuid.UUID,
        Path(
            description="Organization identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> OrganizationDeleteResponse:
    """Remove an inactive organization after UI confirmation."""
    return await _delete_organization(id, service)
