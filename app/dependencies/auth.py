"""Auth service and Super Admin identity dependency providers."""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import InvalidTokenError, decode_access_token
from app.dependencies.database import get_db
from app.exceptions.base import AuthenticationError, AuthorizationError
from app.models.super_admin import SuperAdmin
from app.repositories.super_admin_repository import SuperAdminRepository
from app.services.auth_service import AuthService

bearer_scheme = HTTPBearer(
    auto_error=False,
    description=(
        "JWT access token from POST /api/login or POST /api/v1/auth/login. "
        "Send as: Authorization: Bearer <token>"
    ),
)


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    """Provide an AuthService bound to the request-scoped database session."""
    return AuthService(SuperAdminRepository(session))


def get_super_admin_repository(
    session: AsyncSession = Depends(get_db),
) -> SuperAdminRepository:
    """Provide a SuperAdminRepository bound to the request-scoped session."""
    return SuperAdminRepository(session)


async def get_current_super_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    repository: SuperAdminRepository = Depends(get_super_admin_repository),
) -> SuperAdmin:
    """Return the authenticated Super Admin for protected dashboard routes.

    Raises AuthenticationError when the bearer token is missing, invalid,
    expired, or bound to an unknown/inactive account. Raises
    AuthorizationError when the JWT role is not super_admin.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.warning("Protected route called without a bearer token")
        raise AuthenticationError(
            message="Authentication required.",
            error_code="AUTHENTICATION_FAILED",
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        logger.warning("Protected route called with an invalid or expired token")
        raise AuthenticationError(
            message="Invalid or expired token.",
            error_code="AUTHENTICATION_FAILED",
        ) from exc

    role = payload.get("role")
    if role != "super_admin":
        logger.warning("Protected route called with non-super-admin role={}", role)
        raise AuthorizationError(
            message="Super Admin role required.",
            error_code="AUTHORIZATION_FAILED",
        )

    subject = payload.get("sub")
    try:
        admin_id = uuid.UUID(str(subject))
    except (TypeError, ValueError) as exc:
        logger.warning("Protected route token has an invalid subject claim")
        raise AuthenticationError(
            message="Invalid or expired token.",
            error_code="AUTHENTICATION_FAILED",
        ) from exc

    admin = await repository.get_by_id(admin_id)
    if admin is None or not admin.is_active:
        logger.warning("Protected route token did not match an active Super Admin")
        raise AuthenticationError(
            message="Invalid or expired token.",
            error_code="AUTHENTICATION_FAILED",
        )
    return admin
