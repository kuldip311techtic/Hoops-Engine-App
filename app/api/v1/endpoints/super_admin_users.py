"""Super Admin user management routes."""

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
    "roles": ["Coach"],
    "role_code": "COACH",
    "is_active": True,
    "created_at": "2026-08-24T12:00:00+00:00",
    "updated_at": "2026-08-24T12:00:00+00:00",
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
        "Super Admin only. Returns paginated users for the Manage Users table. "
        "Each item includes `id`, `name`, `email`, `role`, `roles`, and `role_code`. "
        "Set `active_only=true` to exclude deactivated accounts. Supports `page` "
        "and `limit` query parameters (max 100 per page). Requires Bearer JWT "
        "for a Super Admin account."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "Users retrieved.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Users retrieved",
                        "description": "Users retrieved successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
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
        "email": None,
        "token": None,
        "error": None,
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
        "Password must meet complexity rules (8+ chars, upper, lower, digit, special). "
        "Duplicate emails return 409 EMAIL_ALREADY_EXISTS. SUPER_ADMIN cannot be "
        "assigned. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        201: {
            "description": "User created.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User created",
                        "description": "The user was added successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
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
        "email": None,
        "token": None,
        "error": None,
        "data": {"user": user.model_dump(mode="json")},
    }


@router.put(
    "/{user_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="update_user",
    summary="Update a user",
    description=(
        "Super Admin only. Partially updates a user identified by `{user_id}`. "
        "Password or role changes invalidate existing JWTs. Super Admin accounts "
        "cannot be edited. Duplicate emails return 409 EMAIL_ALREADY_EXISTS. "
        "Unknown ids return 404 USER_NOT_FOUND. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "User updated.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User updated",
                        "description": "The user was updated successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
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
        "email": None,
        "token": None,
        "error": None,
        "data": {"user": user.model_dump(mode="json")},
    }


@router.delete(
    "/{user_id}",
    response_model=AdminSuccessResponse,
    status_code=status.HTTP_200_OK,
    operation_id="delete_user",
    summary="Remove a user",
    description=(
        "Super Admin only. Soft-removes a user by setting `is_active` to false. "
        "The acting Super Admin cannot remove their own account (403 CANNOT_REMOVE_SELF). "
        "Super Admin target accounts cannot be removed. Unknown ids return 404 "
        "USER_NOT_FOUND. Requires Bearer JWT for Super Admin."
    ),
    tags=["super-admin"],
    responses={
        200: {
            "description": "User removed.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "User removed",
                        "description": "The user was removed successfully.",
                        "email": None,
                        "token": None,
                        "error": None,
                        "data": {
                            "user": {**_user_example, "is_active": False},
                        },
                    }
                }
            },
        },
        403: {
            "description": "Forbidden, including self-removal.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "You cannot remove your own account",
                        "description": "You cannot remove your own account",
                        "error": {"code": "CANNOT_REMOVE_SELF", "details": None},
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
    """Remove a user account from the active roster."""
    user = await service.deactivate_user(user_id, actor=admin)
    return {
        "success": True,
        "message": "User removed",
        "description": "The user was removed successfully.",
        "email": None,
        "token": None,
        "error": None,
        "data": {"user": user.model_dump(mode="json")},
    }
