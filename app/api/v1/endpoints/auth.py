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
_public = {"security": []}


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    operation_id="login_super_admin",
    summary="Authenticate Super Admin",
    description=(
        "Public OAuth2 password login for the Admin Super Admin screen. "
        "Accepts JSON `email` and `password` (the only fields on the Figma login "
        "form). Validates credentials against a Super Admin account and returns "
        "bearer `access_token` and `refresh_token` in `data`. "
        "Top-level `email`, `message`, and `description` are included so the SPA "
        "can show a success toast and redirect. The SPA must store the tokens "
        "and navigate to `data.redirect_to` (dashboard). This endpoint never "
        "issues HTTP 302 and never echoes `password`. "
        "Non-Super-Admin roles, unknown emails, wrong passwords, and inactive "
        "accounts all return 401 INVALID_CREDENTIALS with the same message so "
        "callers cannot enumerate accounts. Empty or invalid fields return 422 "
        "VALIDATION_ERROR. Login is rate-limited (429 RATE_LIMITED) per settings. "
        "The unused FastAPI `Request` parameter is required by slowapi and is "
        "not part of the JSON body."
    ),
    tags=["auth"],
    openapi_extra=_public,
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
        401: {
            "description": "Incorrect email or password (or non-Super-Admin role).",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Incorrect email or password",
                        "description": "Incorrect email or password",
                        "error": {"code": "INVALID_CREDENTIALS", "details": None},
                    }
                }
            },
        },
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
        422: _errors[422],
        429: _errors[429],
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
    operation_id="register_user",
    summary="Register a new user",
    description=(
        "Public registration. Creates a USER-role account from JSON `email` and "
        "`password`. Password must be at least 8 characters with upper, lower, "
        "number, and special character. Duplicate emails return 409 "
        "EMAIL_ALREADY_EXISTS with a clear message for the UI. On success the "
        "same token envelope as login is returned (including `email` and "
        "`description`) so the SPA can store tokens and navigate to "
        "`data.redirect_to`. This route does not require a Bearer token."
    ),
    tags=["auth"],
    openapi_extra=_public,
    responses={
        201: {
            "description": "Account created. Store tokens and navigate to data.redirect_to.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Registration successful",
                        "email": "player@example.com",
                        "description": "Account created. Redirecting to the dashboard.",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "redirect_to": "/dashboard",
                            "email": "player@example.com",
                            "description": "Account created. Redirecting to the dashboard.",
                        },
                    }
                }
            },
        },
        400: _errors[400],
        401: _errors[401],
        403: _errors[403],
        404: _errors[404],
        409: {
            "description": "Email already registered.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Email already in use",
                        "description": "Email already in use",
                        "error": {"code": "EMAIL_ALREADY_EXISTS", "details": None},
                    }
                }
            },
        },
        422: _errors[422],
        429: _errors[429],
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
    operation_id="refresh_tokens",
    summary="Refresh access token",
    description=(
        "Public refresh-token grant. Exchange a refresh JWT for a new "
        "access/refresh pair. Rejects access tokens, malformed values, unknown "
        "subjects, and tokens whose `ver` no longer matches the user "
        "(for example after a password change on another device). "
        "Send JSON `{refresh_token}` only; do not send a Bearer header. "
        "Success uses the same envelope as login so the SPA can replace stored tokens."
    ),
    tags=["auth"],
    openapi_extra=_public,
    responses={
        200: {
            "description": "New tokens issued.",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Token refreshed",
                        "email": "admin@example.com",
                        "description": "Your session was renewed.",
                        "data": {
                            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                            "token_type": "bearer",
                            "expires_in": 1800,
                            "redirect_to": "/dashboard",
                            "email": "admin@example.com",
                            "description": "Your session was renewed.",
                        },
                    }
                }
            },
        },
        400: _errors[400],
        401: {
            "description": "Refresh token is invalid, expired, or revoked.",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "message": "Invalid refresh token",
                        "description": "Invalid refresh token",
                        "error": {"code": "UNAUTHORIZED", "details": None},
                    }
                }
            },
        },
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
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
    operation_id="change_password",
    summary="Change password and revoke other sessions",
    description=(
        "Authenticated. Requires `Authorization: Bearer <access_token>`. "
        "Verifies `current_password`, stores a new hash that meets the password "
        "policy, and increments `token_version` so JWTs issued to other devices "
        "are rejected until those devices log in again. Wrong current password "
        "returns 401 INVALID_CREDENTIALS. Missing or expired Bearer token "
        "returns 401 UNAUTHORIZED."
    ),
    tags=["auth"],
    responses={
        200: {
            "description": "Password updated; other sessions are revoked.",
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
        400: _errors[400],
        401: _errors[401],
        403: _errors[403],
        404: _errors[404],
        409: _errors[409],
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
