"""Super Admin authentication endpoints."""

from fastapi import APIRouter, Depends, Request, status

from app.dependencies.auth import get_auth_service
from app.middleware.rate_limiter import limiter
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.common import ErrorResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])
legacy_router = APIRouter(tags=["auth"])

_LOGIN_OPENAPI_RESPONSES = {
    200: {
        "description": "Super Admin authenticated successfully.",
        "model": LoginResponse,
    },
    401: {
        "description": "Invalid email or password.",
        "model": ErrorResponse,
    },
    422: {
        "description": "Validation error (missing or invalid email/password).",
        "model": ErrorResponse,
    },
    429: {
        "description": "Too many login attempts.",
        "model": ErrorResponse,
    },
    500: {
        "description": "Internal server error.",
        "model": ErrorResponse,
    },
}


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
    description=(
        "Authenticate a Super Admin using email and password. "
        "Returns a JWT access token on success for dashboard access. "
        "No authentication is required to call this endpoint."
    ),
    responses=_LOGIN_OPENAPI_RESPONSES,
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
        "Authenticate a Super Admin using email and password. "
        "Returns a JWT access token on success. This is the primary login "
        "endpoint consumed by the Super Admin login screen (POST /api/login). "
        "No authentication is required."
    ),
    responses=_LOGIN_OPENAPI_RESPONSES,
)
@limiter.limit("10/minute")
async def login_super_admin_legacy(
    request: Request,
    body: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Legacy /api/login route for frontend integration."""
    return await _login(body, auth_service)
