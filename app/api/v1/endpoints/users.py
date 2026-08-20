"""Super Admin user management endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.dependencies.auth import get_current_super_admin
from app.dependencies.users import get_user_service
from app.models.super_admin import SuperAdmin
from app.schemas.common import ErrorResponse
from app.schemas.user import (
    UserCreate,
    UserDeleteResponse,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
legacy_router = APIRouter(prefix="/users", tags=["users"])

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
_SELF_DELETE_EXAMPLE = {
    "success": False,
    "message": "You cannot remove your own account.",
    "error": {"code": "CANNOT_DELETE_OWN_ACCOUNT", "details": None},
}
_NOT_FOUND_EXAMPLE = {
    "success": False,
    "message": "User not found.",
    "error": {"code": "USER_NOT_FOUND", "details": None},
}
_ORG_NOT_FOUND_EXAMPLE = {
    "success": False,
    "message": "Organization not found.",
    "error": {
        "code": "ORGANIZATION_NOT_FOUND",
        "details": [
            {"field": "organization_id", "message": "Organization not found."}
        ],
    },
}
_EMAIL_CONFLICT_EXAMPLE = {
    "success": False,
    "message": "A user with this email already exists.",
    "error": {
        "code": "EMAIL_ALREADY_EXISTS",
        "details": [
            {"field": "email", "message": "A user with this email already exists."}
        ],
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
    "Return a paginated list of application users (coaches, players, and "
    "organization admins) for the Super Admin Manage Users screen. Each item "
    "includes Name (name/first_name/last_name), Role (role/roles), Email, and "
    "Status. Password is never returned. Empty catalogs return success with "
    "data.items=[]. Requires Authorization: Bearer <JWT> from POST /api/login. "
    "Use page and page_size for pagination."
)
_CREATE_DESCRIPTION = (
    "Create a coach, player, or organization admin from the Add User form. "
    "Required fields: email, password, role (or roles), and either "
    "first_name+last_name or name. Password must be at least 8 characters and "
    "include uppercase, lowercase, a number, and a special character. Duplicate "
    "email returns 409 EMAIL_ALREADY_EXISTS. Password is write-only and is never "
    "returned. Super Admins are not created here; they remain in super_admins. "
    "Requires Super Admin JWT."
)
_UPDATE_DESCRIPTION = (
    "Replace an existing user's details from the Edit User form. Fields: name "
    "or first_name+last_name, email, role or roles, optional password, and "
    "status. Unknown id returns 404 USER_NOT_FOUND. Duplicate email returns 409. "
    "Requires Super Admin JWT."
)
_DELETE_DESCRIPTION = (
    "Remove a user after the UI confirmation. Super Admin cannot remove their "
    "own account: DELETE /api/users/{jwt.sub} returns 403 CANNOT_DELETE_OWN_ACCOUNT. "
    "Successful removal returns 200 with a confirmation message (not 204) so the "
    "frontend can show a success toast. Requires Super Admin JWT."
)


async def _list_users(
    page: int,
    page_size: int,
    service: UserService,
) -> UserListResponse:
    """Shared list handler for versioned and legacy routes."""
    return await service.list_users(page=page, page_size=page_size)


async def _create_user(body: UserCreate, service: UserService) -> UserResponse:
    """Shared create handler for versioned and legacy routes."""
    return await service.create_user(body)


async def _update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    service: UserService,
) -> UserResponse:
    """Shared update handler for versioned and legacy routes."""
    return await service.update_user(user_id, body)


async def _delete_user(
    user_id: uuid.UUID,
    actor: SuperAdmin,
    service: UserService,
) -> UserDeleteResponse:
    """Shared delete handler for versioned and legacy routes."""
    return await service.delete_user(user_id, actor)


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description=_LIST_DESCRIPTION,
    operation_id="listUsersV1",
    responses={
        200: {"description": "Paginated user list.", "model": UserListResponse},
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def list_users_v1(
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
        description="Number of users per page.",
        examples=[20],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """Fetch a paginated list of users for Super Admin."""
    return await _list_users(page, page_size, service)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description=_CREATE_DESCRIPTION,
    operation_id="createUserV1",
    responses={
        201: {"description": "User created.", "model": UserResponse},
        409: {
            "description": "Duplicate email.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _EMAIL_CONFLICT_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
        422: {
            "description": (
                "Validation error, including unknown organization_id "
                "(ORGANIZATION_NOT_FOUND)."
            ),
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "validation": {
                            "summary": "VALIDATION_ERROR",
                            "value": _VALIDATION_EXAMPLE,
                        },
                        "unknown_organization": {
                            "summary": "ORGANIZATION_NOT_FOUND",
                            "value": _ORG_NOT_FOUND_EXAMPLE,
                        },
                    }
                }
            },
        },
    },
)
async def create_user_v1(
    body: UserCreate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Add a new user with validated details."""
    return await _create_user(body, service)


@router.put(
    "/{id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description=_UPDATE_DESCRIPTION,
    operation_id="updateUserV1",
    responses={
        200: {"description": "User updated.", "model": UserResponse},
        404: {
            "description": "User does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Duplicate email.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _EMAIL_CONFLICT_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def update_user_v1(
    id: Annotated[
        uuid.UUID,
        Path(
            description="User identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    body: UserUpdate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Edit an existing user's details."""
    return await _update_user(id, body, service)


@router.delete(
    "/{id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove user",
    description=_DELETE_DESCRIPTION,
    operation_id="deleteUserV1",
    responses={
        200: {
            "description": "User removed. Confirmation message is in message.",
            "model": UserDeleteResponse,
        },
        **_PROTECTED_ERROR_RESPONSES,
        403: {
            "description": (
                "Forbidden: Super Admin cannot remove their own account, "
                "or the caller is not a Super Admin."
            ),
            "model": ErrorResponse,
            "content": {"application/json": {"example": _SELF_DELETE_EXAMPLE}},
        },
        404: {
            "description": "User does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
    },
)
async def delete_user_v1(
    id: Annotated[
        uuid.UUID,
        Path(
            description="User identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserDeleteResponse:
    """Remove a user unless the caller targets their own account."""
    return await _delete_user(id, admin, service)


@legacy_router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List users",
    description=_LIST_DESCRIPTION + " Primary frontend path: GET /api/users.",
    operation_id="listUsers",
    responses={
        200: {"description": "Paginated user list.", "model": UserListResponse},
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def list_users_legacy(
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
        description="Number of users per page.",
        examples=[20],
    ),
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserListResponse:
    """Fetch a paginated list of users for Super Admin."""
    return await _list_users(page, page_size, service)


@legacy_router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
    description=_CREATE_DESCRIPTION + " Primary frontend path: POST /api/users.",
    operation_id="createUser",
    responses={
        201: {"description": "User created.", "model": UserResponse},
        409: {
            "description": "Duplicate email.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _EMAIL_CONFLICT_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
        422: {
            "description": (
                "Validation error, including unknown organization_id "
                "(ORGANIZATION_NOT_FOUND)."
            ),
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "examples": {
                        "validation": {
                            "summary": "VALIDATION_ERROR",
                            "value": _VALIDATION_EXAMPLE,
                        },
                        "unknown_organization": {
                            "summary": "ORGANIZATION_NOT_FOUND",
                            "value": _ORG_NOT_FOUND_EXAMPLE,
                        },
                    }
                }
            },
        },
    },
)
async def create_user_legacy(
    body: UserCreate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Add a new user with validated details."""
    return await _create_user(body, service)


@legacy_router.put(
    "/{id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user",
    description=_UPDATE_DESCRIPTION + " Primary frontend path: PUT /api/users/{id}.",
    operation_id="updateUser",
    responses={
        200: {"description": "User updated.", "model": UserResponse},
        404: {
            "description": "User does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
        409: {
            "description": "Duplicate email.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _EMAIL_CONFLICT_EXAMPLE}},
        },
        **_PROTECTED_ERROR_RESPONSES,
    },
)
async def update_user_legacy(
    id: Annotated[
        uuid.UUID,
        Path(
            description="User identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    body: UserUpdate,
    _admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserResponse:
    """Edit an existing user's details."""
    return await _update_user(id, body, service)


@legacy_router.delete(
    "/{id}",
    response_model=UserDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove user",
    description=_DELETE_DESCRIPTION + " Primary frontend path: DELETE /api/users/{id}.",
    operation_id="deleteUser",
    responses={
        200: {
            "description": "User removed. Confirmation message is in message.",
            "model": UserDeleteResponse,
        },
        **_PROTECTED_ERROR_RESPONSES,
        403: {
            "description": (
                "Forbidden: Super Admin cannot remove their own account, "
                "or the caller is not a Super Admin."
            ),
            "model": ErrorResponse,
            "content": {"application/json": {"example": _SELF_DELETE_EXAMPLE}},
        },
        404: {
            "description": "User does not exist.",
            "model": ErrorResponse,
            "content": {"application/json": {"example": _NOT_FOUND_EXAMPLE}},
        },
    },
)
async def delete_user_legacy(
    id: Annotated[
        uuid.UUID,
        Path(
            description="User identifier (UUID).",
            examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
        ),
    ],
    admin: SuperAdmin = Depends(get_current_super_admin),
    service: UserService = Depends(get_user_service),
) -> UserDeleteResponse:
    """Remove a user unless the caller targets their own account."""
    return await _delete_user(id, admin, service)
