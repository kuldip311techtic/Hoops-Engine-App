"""Super Admin authorization and admin service factories."""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies.auth import get_current_user
from app.dependencies.db import get_db
from app.exceptions.base import ForbiddenError
from app.models.user import User, UserRole
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.subscription_plan_repository import SubscriptionPlanRepository
from app.repositories.support_request_repository import SupportRequestRepository
from app.repositories.user_repository import UserRepository
from app.services.analytics_service import AnalyticsService
from app.services.organization_service import OrganizationService
from app.services.subscription_plan_service import SubscriptionPlanService
from app.services.support_request_service import SupportRequestService
from app.services.user_admin_service import UserAdminService


async def get_current_super_admin(
    user: User = Depends(get_current_user),
) -> User:
    """Require an authenticated Super Admin principal."""
    if user.role != UserRole.SUPER_ADMIN:
        raise ForbiddenError("Access denied", code="FORBIDDEN")
    return user


def get_support_request_service(
    db: AsyncSession = Depends(get_db),
) -> SupportRequestService:
    """Build SupportRequestService with a request-scoped repository."""
    return SupportRequestService(SupportRequestRepository(db))


def get_user_admin_service(
    db: AsyncSession = Depends(get_db),
) -> UserAdminService:
    """Build UserAdminService with a request-scoped repository."""
    return UserAdminService(UserRepository(db))


def get_organization_service(
    db: AsyncSession = Depends(get_db),
) -> OrganizationService:
    """Build OrganizationService with a request-scoped repository."""
    return OrganizationService(OrganizationRepository(db))


def get_subscription_plan_service(
    db: AsyncSession = Depends(get_db),
) -> SubscriptionPlanService:
    """Build SubscriptionPlanService with a request-scoped repository."""
    return SubscriptionPlanService(SubscriptionPlanRepository(db))


def get_analytics_service(
    db: AsyncSession = Depends(get_db),
) -> AnalyticsService:
    """Build AnalyticsService with a request-scoped repository."""
    return AnalyticsService(AnalyticsRepository(db))
