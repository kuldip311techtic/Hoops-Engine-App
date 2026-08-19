"""Super Admin authentication endpoints."""

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import get_auth_service
from app.middleware.rate_limiter import limiter
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.common import ErrorResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
legacy_router = APIRouter(tags=["auth"])

_LOGIN_SUCCESS_EXAMPLE = {
    "success": True,
    "message": "Login successful.",
    "description": "Super Admin authenticated. Redirect to dashboard.",
    "data": {
        "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIuLi.",
        "token_type": "bearer",
        "expires_in": 1800,
        "email": "admin@example.com",
    },
}

_LOGIN_AUTH_ERROR_EXAMPLE = {
    "success": False,
    "message": "Invalid email or password.",
    "error": {"code": "AUTHENTICATION_FAILED", "details": None},
}

_LOGIN_VALIDATION_ERROR_EXAMPLE = {
    "success": False,
    "message": "Validation error",
    "error": {
        "code": "VALIDATION_ERROR",
        "details": [
            {"field": "password", "message": "String should have at least 1 character"}
        ],
    },
}

_LOGIN_RATE_LIMIT_EXAMPLE = {
    "success": False,
    "message": "Too many requests. Please try again later.",
    "error": {"code": "RATE_LIMIT_EXCEEDED", "details": {"retry_after": "10/minute"}},
}

_LOGIN_SERVER_ERROR_EXAMPLE = {
    "success": False,
    "message": "An unexpected error occurred.",
    "error": {"code": "INTERNAL_SERVER_ERROR", "details": None},
}

_LOGIN_OPENAPI_RESPONSES = {
    200: {
        "description": "Super Admin authenticated successfully. Returns JWT for dashboard access.",
        "model": LoginResponse,
        "content": {"application/json": {"example": _LOGIN_SUCCESS_EXAMPLE}},
    },
    401: {
        "description": "Invalid email or password. Same message for unknown email and wrong password (no user enumeration).",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _LOGIN_AUTH_ERROR_EXAMPLE}},
    },
    422: {
        "description": "Validation error (missing/invalid email or empty password).",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _LOGIN_VALIDATION_ERROR_EXAMPLE}},
    },
    429: {
        "description": "Too many login attempts (rate limit: 10 requests per minute per client IP).",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _LOGIN_RATE_LIMIT_EXAMPLE}},
    },
    500: {
        "description": "Internal server error.",
        "model": ErrorResponse,
        "content": {"application/json": {"example": _LOGIN_SERVER_ERROR_EXAMPLE}},
    },
}

_LOGIN_DESCRIPTION = (
    "Authenticate a Super Admin using email and password from the login screen. "
    "On success, returns a JWT access token in data.token for subsequent Authorization: Bearer requests. "
    "The response includes message and description fields for UI feedback and dashboard redirect. "
    "Failed attempts return a generic 401 message without revealing whether the email exists. "
    "Rate limited to 10 requests per minute per IP. "
    "This endpoint is public — no Authorization header is required."
)


async def _login(
    body: LoginRequest,
    auth_service: AuthService,
) -> LoginResponse:
    """Shared login handler for versioned and legacy routes."""
    return await auth_service.login_super_admin(body.email, body.password)


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Super Admin login (v1)",
    description=_LOGIN_DESCRIPTION,
    operation_id="loginSuperAdminV1",
    responses=_LOGIN_OPENAPI_RESPONSES,
    openapi_extra={"security": []},
)
@limiter.limit("10/minute")
async def login_super_admin_v1(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate Super Admin credentials and issue a JWT access token."""
    return await _login(body, auth_service)


@legacy_router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Super Admin login",
    description=(
        _LOGIN_DESCRIPTION
        + " Primary endpoint for the Super Admin login screen (POST /api/login)."
    ),
    operation_id="loginSuperAdminLegacy",
    responses=_LOGIN_OPENAPI_RESPONSES,
    openapi_extra={"security": []},
)
@limiter.limit("10/minute")
async def login_super_admin_legacy(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Legacy /api/login route for frontend integration."""
    return await _login(body, auth_service)
