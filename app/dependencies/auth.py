"""OAuth2 bearer dependencies for JWT authentication."""

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.db import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/super-admin/login")


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Build AuthService with a request-scoped user repository."""
    return AuthService(UserRepository(db))


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the authenticated user from the access token."""
    return await service.user_from_access_token(token)
