"""Support request service dependency provider."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.database import get_db
from app.repositories.support_request_repository import SupportRequestRepository
from app.services.support_request_service import SupportRequestService


def get_support_request_service(
    session: AsyncSession = Depends(get_db),
) -> SupportRequestService:
    """Provide a SupportRequestService bound to the request-scoped session."""
    return SupportRequestService(SupportRequestRepository(session))
