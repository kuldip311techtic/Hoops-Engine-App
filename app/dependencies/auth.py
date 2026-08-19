"""Auth service dependency provider."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db
from app.repositories.super_admin_repository import SuperAdminRepository
from app.services.auth_service import AuthService


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    """Provide an AuthService bound to the request-scoped database session."""
    return AuthService(SuperAdminRepository(session))
