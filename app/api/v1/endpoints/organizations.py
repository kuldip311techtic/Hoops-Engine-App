"""Admin organization routes. Thin: validate DTO, call service, wrap envelope."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.admin import (
    get_current_super_admin,
    get_organization_service,
)
from app.models.user import User
from app.schemas.common import AdminSuccessResponse, openapi_error_map
from app.schemas.organization import (
    OrganizationCreateRequest,
    OrganizationListResponse,
    OrganizationUpdateRequest,
)
from app.services.organization_service import OrganizationService

router = APIRouter()
_errors = openapi_error_map()

_org_example = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Hoops Academy",
    "contact_email": "contact@example.com",
    "email": "contact@example.com",
    "phone_number": "1234567890",
    "phone": "1234567890",
    "address": "123 Main St",
    "description": "Youth basketball training organization.",
    "is_active": True,
    "is_published": True,
    "created_at": "2026-08-21T12:00:00+00:00",
    "updated_at": "2026-08-21T12:00:00+00:00",
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
    response_model=OrganizationListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_organizations",
    summary="List organizations",
    description=(
        "Super Admin only. Returns organizations for the admin table. By default "
        "all active and inactive organizations are returned so the admin UI can "
        "manage the full catalog. Set `active_only=true` to hide deactivated rows "
        "or `published_only=true` to return only published, active organizations "
        "— the same filter end users receive. Requires Bearer token for Super Admin."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Organizations retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Organizations retrieved",
                        "description": "Organizations retrieved successfully.",
                        "data": {"items": [_org_example]},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def list_organizations(
    active_only: bool = Query(
        default=False,
        description="When true, exclude soft-removed (inactive) organizations.",
    ),
    published_only: bool = Query(
        default=False,
        description=(
            "When true, return only published active organizations for end users."
        ),
    ),
    _admin: User = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> dict:
    """Return organizations for the Super Admin organizations table."""
    items = await service.list_organizations(
        active_only=active_only,
        published_only=published_only,
    )
    return {
        "success": True,
        "message": "Organizations retrieved",
        "description": "Organizations retrieved successfully.",
        "data": {"items": [item.model_dump(mode="json") for item in items]},
    }


@router.post(
    "",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_organization",
    summary="Create an organization",
    description=(
        "Super Admin only. Creates an organization with `name`, `contact_email`, "
        "`phone_number`, and `address`. Optional `description` and `is_published` "
        "may be supplied. Duplicate names return 409 ORGANIZATION_ALREADY_EXISTS. "
        "A best-effort welcome email is sent to the contact address when SES is "
        "configured. Requires Bearer token for Super Admin."
    ),
    tags=["admin"],
    responses={
        201: {
            "description": "Organization created.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Organization created",
                        "description": "The organization was added successfully.",
                        "data": {"organization": _org_example},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def create_organization(
    body: OrganizationCreateRequest,
    _admin: User = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> dict:
    """Add an organization to the catalog."""
    organization = await service.create_organization(
        name=body.name,
        contact_email=str(body.contact_email),
        phone_number=body.phone_number,
        address=body.address,
        description=body.description,
        is_published=body.is_published,
    )
    payload = organization.model_dump(mode="json")
    return {
        "success": True,
        "message": "Organization created",
        "description": "The organization was added successfully.",
        "data": {"organization": payload},
    }


@router.get(
    "/{organization_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_organization",
    summary="Get an organization",
    description=(
        "Super Admin only. Returns a single organization by id. Unknown or inactive "
        "ids return 404 ORGANIZATION_NOT_FOUND."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Organization retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Organization retrieved",
                        "description": "Organization retrieved successfully.",
                        "data": {"organization": _org_example},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def get_organization(
    organization_id: UUID,
    _admin: User = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> dict:
    """Return one organization."""
    organization = await service.get_organization(organization_id)
    return {
        "success": True,
        "message": "Organization retrieved",
        "description": "Organization retrieved successfully.",
        "data": {"organization": organization.model_dump(mode="json")},
    }


@router.put(
    "/{organization_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_organization",
    summary="Update an organization",
    description=(
        "Super Admin only. Partially updates an organization. All body fields are "
        "optional. Renaming to an existing organization name returns 409 "
        "ORGANIZATION_ALREADY_EXISTS. Unknown ids return 404."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Organization updated.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Organization updated",
                        "description": "The organization was updated successfully.",
                        "data": {"organization": _org_example},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def update_organization(
    organization_id: UUID,
    body: OrganizationUpdateRequest,
    _admin: User = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> dict:
    """Edit an existing organization."""
    organization = await service.update_organization(
        organization_id,
        name=body.name,
        contact_email=str(body.contact_email) if body.contact_email else None,
        phone_number=body.phone_number,
        address=body.address,
        description=body.description,
        is_published=body.is_published,
    )
    return {
        "success": True,
        "message": "Organization updated",
        "description": "The organization was updated successfully.",
        "data": {"organization": organization.model_dump(mode="json")},
    }


@router.delete(
    "/{organization_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="delete_organization",
    summary="Remove an organization",
    description=(
        "Super Admin only. Soft-removes an organization by setting `is_active` and "
        "`is_published` to false. Unknown or already removed ids return 404 "
        "ORGANIZATION_NOT_FOUND."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Organization removed.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Organization removed",
                        "description": "The organization was removed successfully.",
                        "data": {
                            "organization": {
                                **_org_example,
                                "is_active": False,
                                "is_published": False,
                            }
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def delete_organization(
    organization_id: UUID,
    _admin: User = Depends(get_current_super_admin),
    service: OrganizationService = Depends(get_organization_service),
) -> dict:
    """Remove an organization from the active catalog."""
    organization = await service.remove_organization(organization_id)
    return {
        "success": True,
        "message": "Organization removed",
        "description": "The organization was removed successfully.",
        "data": {"organization": organization.model_dump(mode="json")},
    }
