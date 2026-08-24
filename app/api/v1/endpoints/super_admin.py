"""Super Admin authentication routes."""

from email_validator import EmailNotValidError, validate_email
from fastapi import APIRouter, Depends, Request, status

from app.core.config import get_settings
from app.dependencies.auth import get_auth_service
from app.exceptions.base import AppError
from app.middleware.rate_limiter import get_limiter
from app.schemas.auth import LoginRequest, LoginResponse
from app.schemas.common import openapi_error_map
from app.services.auth_service import AuthService

router = APIRouter()
limiter = get_limiter()
_errors = openapi_error_map()
_public = {"security": []}


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    operation_id="super_admin_login",
    summary="Authenticate Super Admin",
    description=(
        "Public login for the Super Admin dashboard. Accepts JSON `email` and "
        "`password` from the login form. On success returns bearer JWT tokens "
        "in `data` (`access_token`, `token`, `refresh_token`), plus top-level "
        "`email`, `message`, and `description` for the UI. The SPA must store "
        "the token and navigate to `data.redirect_to` (typically `/dashboard`). "
        "This endpoint never issues HTTP 302 and never echoes `password`. "
        "Empty email or password returns 400 BAD_REQUEST. Wrong credentials "
        "return 401 INVALID_CREDENTIALS with a generic message. Malformed "
        "requests return 422 VALIDATION_ERROR with field details."
    ),
    tags=["super-admin"],
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
                            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
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
            "description": "Incorrect email or password.",
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
async def super_admin_login(
    request: Request,
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> dict:
    """Authenticate Super Admin and return bearer tokens."""
    email_value = body.email
    password_value = body.password
    if not email_value or not password_value:
        raise AppError(
            "Email and password are required",
            code="BAD_REQUEST",
            status_code=400,
        )
    try:
        validate_email(email_value, check_deliverability=False)
    except EmailNotValidError as exc:
        raise AppError(
            "Invalid email address",
            code="VALIDATION_ERROR",
            status_code=422,
        ) from exc
    tokens = await service.login(
        email_value,
        password_value,
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
