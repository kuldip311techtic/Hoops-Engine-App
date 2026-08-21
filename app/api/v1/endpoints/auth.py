"""Authentication routes. Thin: validate DTO, call AuthService, wrap envelope."""

from fastapi import APIRouter, Depends, Request, status

from app.core.config import get_settings
from app.dependencies.auth import get_auth_service, get_current_user
from app.middleware.rate_limiter import get_limiter
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
)
from app.schemas.common import SuccessResponse, openapi_error_map
from app.services.auth_service import AuthService

router = APIRouter()
limiter = get_limiter()
_errors = openapi_error_map()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Super Admin / user login",
    description=(
        "Public OAuth2 password login. Accepts JSON `email` and `password`, "
        "validates credentials, and returns bearer access and refresh tokens "
        "in `data`. Top-level `email`, `message`, and `description` are included "
        "for the Admin login screen (success toast + redirect). The SPA must "
        "store the tokens and navigate to `data.redirect_to` (dashboard). "
        "This endpoint never issues HTTP 302 and never echoes `password`. "
        "Only Super Admin accounts may use this route; other roles receive the "
        "same 401 as a bad password. Empty or invalid fields return 422."
    ),
    tags=["auth"],
    responses={
        200: {
            "description": "Authenticated. Frontend should redirect to data.redirect_to.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Login successful",
                        "email": "admin@example.com",
                        "description": "Welcome back. Redirecting to the dashboard.",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "redirect_to": "/dashboard",
                            "email": "admin@example.com",
                            "description": "Welcome back. Redirecting to the dashboard.",
                        },
                    }
                }
            },
        },
        400: _errors[400],
        401: _errors[401],
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
        422: _errors[422],
        500: _errors[500],
    },
)
@limiter.limit(get_settings().login_rate_limit)
async def login(
    request: Request,
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Authenticate Super Admin and return bearer tokens."""
    tokens = await service.login(
        body.email,
        body.password,
        require_super_admin=True,
    )
    payload = tokens.model_dump()
    return {
        "success": True,
        "message": "Login successful",
        "email": tokens.email,
        "description": tokens.description,
        "data": payload,
    }


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Creates a USER account. Returns 409 EMAIL_ALREADY_EXISTS when the "
        "email is already registered. Password must be at least 8 characters "
        "with upper, lower, number, and special character."
    ),
    tags=["auth"],
    responses={
        201: {
            "description": "Account created",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Registration successful",
                        "data": {
                            "access_token": "eyJ...",
                            "refresh_token": "eyJ...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "redirect_to": "/dashboard",
                        },
                    }
                }
            },
        },
        409: _errors[409],
        422: _errors[422],
        500: _errors[500],
    },
)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Register a user and return bearer tokens."""
    tokens = await service.register(body.email, body.password)
    payload = tokens.model_dump()
    return {
        "success": True,
        "message": "Registration successful",
        "email": tokens.email,
        "description": tokens.description,
        "data": payload,
    }


@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
    description=(
        "Exchange a refresh token for a new access/refresh pair. Rejects "
        "access tokens, garbage, and tokens whose version no longer matches "
        "the user (for example after a password change on another device)."
    ),
    tags=["auth"],
    responses={
        200: {"description": "New tokens issued"},
        401: _errors[401],
        422: _errors[422],
        500: _errors[500],
    },
)
async def refresh(
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Rotate tokens from a refresh JWT."""
    tokens = await service.refresh(body.refresh_token)
    payload = tokens.model_dump()
    return {
        "success": True,
        "message": "Token refreshed",
        "email": tokens.email,
        "description": tokens.description,
        "data": payload,
    }


@router.post(
    "/change-password",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Change password and revoke other sessions",
    description=(
        "Requires a Bearer access token. Verifies `current_password`, stores "
        "a new hash, and increments `token_version` so JWTs issued to other "
        "devices are rejected until those devices log in again."
    ),
    tags=["auth"],
    responses={
        200: {
            "description": "Password updated",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Password updated",
                        "data": {},
                    }
                }
            },
        },
        401: _errors[401],
        422: _errors[422],
        500: _errors[500],
    },
)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Change password for the authenticated user."""
    await service.change_password(
        current_user,
        body.current_password,
        body.new_password,
    )
    return {"success": True, "message": "Password updated", "data": {}}
