"""Super Admin login, refresh, and change-password endpoints."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.dependencies.auth import get_current_super_admin
from app.dependencies.db import get_db
from app.middleware.rate_limiter import limiter
from app.models.super_admin import SuperAdmin
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.super_admin_repository import SuperAdminRepository
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
)
from app.schemas.common import ERROR_RESPONSES
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])

_LOGIN_ERRORS = {
    400: ERROR_RESPONSES[400],
    401: {
        "model": ERROR_RESPONSES[401]["model"],
        "description": "Invalid credentials",
        "content": {
            "application/json": {
                "example": {
                    "success": False,
                    "message": "Invalid email or password",
                    "error": {"code": "INVALID_CREDENTIALS", "details": None},
                }
            }
        },
    },
    403: ERROR_RESPONSES[403],
    404: ERROR_RESPONSES[404],
    409: ERROR_RESPONSES[409],
    422: ERROR_RESPONSES[422],
    500: ERROR_RESPONSES[500],
}


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    """Compose AuthService with repositories and billing (no vendor SDKs)."""
    return AuthService(
        repository=SuperAdminRepository(session),
        billing_service=BillingService(SubscriptionRepository(session)),
        settings=get_settings(),
        email_service=EmailService(),
    )


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Super Admin login",
    description=(
        "Public OAuth2 password login for Super Admin. Validates ``email`` and "
        "``password``, then returns bearer access and refresh tokens. The "
        "frontend stores the tokens and redirects to ``data.redirect_to`` "
        "(dashboard). Failed attempts return INVALID_CREDENTIALS without "
        "revealing whether the email exists. No authentication header required."
    ),
    responses=_LOGIN_ERRORS,
)
@limiter.limit(get_settings().login_rate_limit)
async def login(
    request: Request,
    body: LoginRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Authenticate Super Admin and create a JWT session."""
    return await service.login(str(body.email), body.password)


@router.post(
    "/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh Super Admin session",
    description=(
        "Public endpoint. Exchange a valid refresh token for a new access and "
        "refresh token pair. Rejects access tokens and revoked sessions "
        "(token_version mismatch after password change)."
    ),
    responses=_LOGIN_ERRORS,
)
@limiter.limit(get_settings().login_rate_limit)
async def refresh(
    request: Request,
    body: RefreshRequest,
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Rotate the Super Admin session from a refresh token."""
    return await service.refresh(body.refresh_token)


@router.post(
    "/change-password",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Change Super Admin password",
    description=(
        "Requires a valid access token. Updates the password and increments "
        "``token_version`` so other devices must log in again. Returns a fresh "
        "token pair for the current device."
    ),
    responses={
        **_LOGIN_ERRORS,
        401: ERROR_RESPONSES[401],
    },
)
async def change_password(
    body: ChangePasswordRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Change password and revoke other sessions."""
    return await service.change_password(admin, body.current_password, body.new_password)
