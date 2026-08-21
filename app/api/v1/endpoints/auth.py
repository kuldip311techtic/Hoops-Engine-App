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

_LOGIN_SUCCESS_EXAMPLE = {
    "success": True,
    "message": "Login successful",
    "data": {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.access",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh",
        "token_type": "bearer",
        "expires_in": 1800,
        "email": "admin@example.com",
        "description": "Redirect the Super Admin to the dashboard.",
        "message": "Login successful",
        "error": None,
        "redirect_to": "/dashboard",
        "subscription": {
            "status": "not_applicable",
            "has_access": True,
            "access_until": None,
        },
    },
}

_LOGIN_ERRORS = {
    400: ERROR_RESPONSES[400],
    401: {
        "model": ERROR_RESPONSES[401]["model"],
        "description": (
            "Invalid credentials. Always INVALID_CREDENTIALS — does not reveal "
            "whether the email exists."
        ),
        "content": {
            "application/json": {
                "examples": {
                    "invalid_credentials": {
                        "summary": "Wrong email or password",
                        "value": {
                            "success": False,
                            "message": "Invalid email or password",
                            "error": {
                                "code": "INVALID_CREDENTIALS",
                                "details": None,
                            },
                        },
                    }
                }
            }
        },
    },
    403: ERROR_RESPONSES[403],
    404: ERROR_RESPONSES[404],
    409: ERROR_RESPONSES[409],
    422: ERROR_RESPONSES[422],
    429: ERROR_RESPONSES[429],
    500: ERROR_RESPONSES[500],
}

_REFRESH_ERRORS = {
    **_LOGIN_ERRORS,
    401: {
        "model": ERROR_RESPONSES[401]["model"],
        "description": "Refresh token missing, expired, wrong type, or revoked",
        "content": {
            "application/json": {
                "examples": {
                    "invalid_refresh": {
                        "summary": "Not a valid refresh JWT",
                        "value": {
                            "success": False,
                            "message": "Invalid or expired refresh token",
                            "error": {
                                "code": "INVALID_REFRESH_TOKEN",
                                "details": None,
                            },
                        },
                    },
                    "session_revoked": {
                        "summary": "Password changed on another device",
                        "value": {
                            "success": False,
                            "message": "Session expired. Please log in again.",
                            "error": {
                                "code": "SESSION_REVOKED",
                                "details": None,
                            },
                        },
                    },
                }
            }
        },
    },
}

_CHANGE_PASSWORD_ERRORS = {
    **_LOGIN_ERRORS,
    401: {
        "model": ERROR_RESPONSES[401]["model"],
        "description": (
            "Missing/invalid Bearer access token, SESSION_REVOKED after another "
            "device changed the password, or INVALID_CREDENTIALS for the current "
            "password."
        ),
        "content": {
            "application/json": {
                "examples": {
                    "missing_bearer": {
                        "summary": "No Authorization header",
                        "value": {
                            "success": False,
                            "message": "Authentication required",
                            "error": {"code": "UNAUTHORIZED", "details": None},
                        },
                    },
                    "invalid_access": {
                        "summary": "Expired or malformed access token",
                        "value": {
                            "success": False,
                            "message": "Invalid or expired access token",
                            "error": {
                                "code": "INVALID_ACCESS_TOKEN",
                                "details": None,
                            },
                        },
                    },
                    "session_revoked": {
                        "summary": "token_version mismatch",
                        "value": {
                            "success": False,
                            "message": "Session expired. Please log in again.",
                            "error": {
                                "code": "SESSION_REVOKED",
                                "details": None,
                            },
                        },
                    },
                    "wrong_current": {
                        "summary": "Current password is incorrect",
                        "value": {
                            "success": False,
                            "message": "Invalid email or password",
                            "error": {
                                "code": "INVALID_CREDENTIALS",
                                "details": None,
                            },
                        },
                    },
                }
            }
        },
    },
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
        "Public OAuth2 password login for Super Admin. The Admin FE login "
        "screen submits ``email`` and ``password`` (both required). On success "
        "this returns HTTP 200 with bearer ``access_token`` and "
        "``refresh_token`` in ``data``. The frontend stores the tokens and "
        "navigates to ``data.redirect_to`` (dashboard, default ``/dashboard``). "
        "This API does not issue HTTP 302. Failed attempts return 401 "
        "INVALID_CREDENTIALS without revealing whether the email exists. "
        "Rate limited per LOGIN_RATE_LIMIT. No authentication header required."
    ),
    responses={
        200: {
            "model": LoginResponse,
            "description": "Authenticated; FE should store tokens and redirect",
            "content": {
                "application/json": {"example": _LOGIN_SUCCESS_EXAMPLE},
            },
        },
        **_LOGIN_ERRORS,
    },
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
        "refresh token pair. Rejects access tokens (INVALID_REFRESH_TOKEN) and "
        "revoked sessions whose ``token_version`` no longer matches after a "
        "password change (SESSION_REVOKED). Rate limited per LOGIN_RATE_LIMIT. "
        "No authentication header required."
    ),
    responses={
        200: {
            "model": LoginResponse,
            "description": "New token pair issued",
            "content": {
                "application/json": {
                    "example": {
                        **_LOGIN_SUCCESS_EXAMPLE,
                        "message": "Session refreshed",
                    }
                },
            },
        },
        **_REFRESH_ERRORS,
    },
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
        "Requires a valid Bearer access token (OAuth2PasswordBearer). Updates "
        "the password after verifying ``current_password``, then increments "
        "``token_version`` so other devices must log in again. Returns a fresh "
        "token pair for the current device. Wrong current password is 401 "
        "INVALID_CREDENTIALS; short ``new_password`` is 422 VALIDATION_ERROR."
    ),
    responses={
        200: {
            "model": LoginResponse,
            "description": "Password updated; new session issued for this device",
            "content": {
                "application/json": {
                    "example": {
                        **_LOGIN_SUCCESS_EXAMPLE,
                        "message": (
                            "Password changed. Please use the new session."
                        ),
                    }
                },
            },
        },
        **_CHANGE_PASSWORD_ERRORS,
    },
)
async def change_password(
    body: ChangePasswordRequest,
    admin: SuperAdmin = Depends(get_current_super_admin),
    service: AuthService = Depends(get_auth_service),
) -> LoginResponse:
    """Change password and revoke other sessions."""
    return await service.change_password(
        admin, body.current_password, body.new_password
    )
