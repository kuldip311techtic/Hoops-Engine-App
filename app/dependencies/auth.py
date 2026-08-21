"""OAuth2 bearer-token dependencies."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.dependencies.db import get_db
from app.exceptions import UnauthorizedError
from app.models.super_admin import SuperAdmin
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.super_admin_repository import SuperAdminRepository
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/v1/auth/login",
    auto_error=False,
    scheme_name="OAuth2PasswordBearer",
)


async def get_current_token_payload(
    token: str | None = Depends(oauth2_scheme),
) -> dict:
    """Decode the access token or raise ``UnauthorizedError``."""
    if not token:
        raise UnauthorizedError()
    try:
        return decode_access_token(token)
    except JWTError as exc:
        raise UnauthorizedError(
            "Invalid or expired access token",
            code="INVALID_ACCESS_TOKEN",
        ) from exc


async def get_current_super_admin(
    payload: dict = Depends(get_current_token_payload),
    session: AsyncSession = Depends(get_db),
) -> SuperAdmin:
    """Load the Super Admin for the Bearer token and enforce token_version."""
    service = AuthService(
        repository=SuperAdminRepository(session),
        billing_service=BillingService(SubscriptionRepository(session)),
        settings=get_settings(),
    )
    return await service.get_by_token_payload(payload)


async def get_db_session(
    session: AsyncSession = Depends(get_db),
) -> AsyncSession:
    """Alias kept so auth-aware routes can pull a session alongside the token."""
    return session
