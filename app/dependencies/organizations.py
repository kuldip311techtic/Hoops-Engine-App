"""Organization service dependency provider."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db
from app.repositories.organization_repository import OrganizationRepository
from app.services.organization_service import OrganizationService


def get_organization_service(
    session: AsyncSession = Depends(get_db),
) -> OrganizationService:
    """Provide an OrganizationService bound to the request-scoped session."""
    return OrganizationService(OrganizationRepository(session))
