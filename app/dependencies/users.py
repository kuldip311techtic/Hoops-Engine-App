"""User service dependency provider."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db
from app.repositories.super_admin_repository import SuperAdminRepository
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


def get_user_service(session: AsyncSession = Depends(get_db)) -> UserService:
    """Provide a UserService bound to the request-scoped session."""
    return UserService(UserRepository(session), SuperAdminRepository(session))
