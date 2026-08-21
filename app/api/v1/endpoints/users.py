"""Admin user management routes. Thin: validate DTO, call service, wrap envelope."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from app.dependencies.admin import get_current_super_admin, get_user_admin_service
from app.models.user import User
from app.schemas.common import AdminSuccessResponse, openapi_error_map
from app.schemas.user_admin import (
    UserCreateRequest,
    UserListResponse,
    UserUpdateRequest,
)
from app.services.user_admin_service import UserAdminService

router = APIRouter()
_errors = openapi_error_map()

_user_example = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "first_name": "John",
    "last_name": "Doe",
    "name": "John Doe",
    "email": "john.doe@example.com",
    "role": "Coach",
    "role_code": "COACH",
    "is_active": True,
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
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    operation_id="list_users",
    summary="List users",
    description=(
        "Super Admin only. Returns paginated users for the admin table. By default "
        "all active and inactive users are returned. Set `active_only=true` to "
        "exclude deactivated accounts — the same filter end users receive. "
        "Requires Bearer token for Super Admin."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "Users retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Users retrieved",
                        "description": "Users retrieved successfully.",
                        "data": {
                            "items": [_user_example],
                            "page": 1,
                            "limit": 50,
                            "total": 1,
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def list_users(
    active_only: bool = Query(
        default=False,
        description="When true, return only active user accounts.",
    ),
    page: int = Query(default=1, ge=1, description="1-based page number."),
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
        description="Maximum users per page (max 100).",
    ),
    _admin: User = Depends(get_current_super_admin),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """Return users for the Super Admin manage-users screen."""
    items, total, safe_page, safe_limit = await service.list_users(
        active_only=active_only,
        page=page,
        limit=limit,
    )
    return {
        "success": True,
        "message": "Users retrieved",
        "description": "Users retrieved successfully.",
        "data": {
            "items": [item.model_dump(mode="json") for item in items],
            "page": safe_page,
            "limit": safe_limit,
            "total": total,
        },
    }


@router.post(
    "",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_user",
    summary="Create a user",
    description=(
        "Super Admin only. Creates a user with `first_name`, `last_name`, `email`, "
        "`password`, and `role` (Coach, Player, Organization Admin, User, or Viewer). "
        "Duplicate emails return 409 EMAIL_ALREADY_EXISTS. SUPER_ADMIN cannot be "
        "assigned. A best-effort welcome email is sent when SES is configured."
    ),
    tags=["admin"],
    responses={
        201: {
            "description": "User created.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User created",
                        "description": "The user was added successfully.",
                        "data": {"user": _user_example},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def create_user(
    body: UserCreateRequest,
    _admin: User = Depends(get_current_super_admin),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """Add a user account."""
    user = await service.create_user(
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email),
        password=body.password,
        role=body.role,
    )
    return {
        "success": True,
        "message": "User created",
        "description": "The user was added successfully.",
        "data": {"user": user.model_dump(mode="json")},
    }


@router.get(
    "/{user_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="get_user",
    summary="Get user by ID",
    description="Retrieve a user by their unique ID. Requires Super Admin authorization.",
    tags=["admin"],
    responses={
        200: {
            "description": "User retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User retrieved",
                        "description": "User retrieved successfully.",
                        "data": {"user": _user_example},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def get_user(
    user_id: UUID,
    _admin: User = Depends(get_current_super_admin),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """Retrieve a user by their unique ID."""
    user = await service.get_user(user_id)
    return {
        "success": True,
        "message": "User retrieved",
        "description": "User retrieved successfully.",
        "data": {"user": user.model_dump(mode="json")},
    }


@router.put(
    "/{user_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_user",
    summary="Update a user",
    description=(
        "Super Admin only. Partially updates a user account. All body fields are "
        "optional. Duplicate emails return 409 EMAIL_ALREADY_EXISTS. Super Admin "
        "accounts cannot be modified. Unknown or inactive ids return 404."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "User updated.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User updated",
                        "description": "The user was updated successfully.",
                        "data": {"user": _user_example},
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def update_user(
    user_id: UUID,
    body: UserUpdateRequest,
    _admin: User = Depends(get_current_super_admin),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """Edit an existing user account."""
    user = await service.update_user(
        user_id,
        first_name=body.first_name,
        last_name=body.last_name,
        email=str(body.email) if body.email else None,
        password=body.password,
        role=body.role,
    )
    return {
        "success": True,
        "message": "User updated",
        "description": "The user was updated successfully.",
        "data": {"user": user.model_dump(mode="json")},
    }


@router.delete(
    "/{user_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="delete_user",
    summary="Remove a user",
    description=(
        "Super Admin only. Soft-removes a user by deactivating the account. The "
        "acting Super Admin cannot remove themselves. Unknown or already removed "
        "ids return 404 USER_NOT_FOUND."
    ),
    tags=["admin"],
    responses={
        200: {
            "description": "User removed.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User removed",
                        "description": "The user was removed successfully.",
                        "data": {
                            "user": {**_user_example, "is_active": False},
                        },
                    }
                }
            },
        },
        **_common_responses,
    },
)
async def delete_user(
    user_id: UUID,
    admin: User = Depends(get_current_super_admin),
    service: UserAdminService = Depends(get_user_admin_service),
) -> dict:
    """Remove a user from the active catalog."""
    user = await service.deactivate_user(user_id, actor=admin)
    return {
        "success": True,
        "message": "User removed",
        "description": "The user was removed successfully.",
        "data": {"user": user.model_dump(mode="json")},
    }
