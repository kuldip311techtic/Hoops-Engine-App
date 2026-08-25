"""Super Admin dashboard analytics use-cases."""

from loguru import logger

from app.exceptions.base import NotFoundError
from app.models.user import UserRole
from app.repositories.analytics_repository import AnalyticsRepository
from app.schemas.analytics import DashboardMetricsData, DashboardNavigationLink

# Coach session recording is not yet persisted; stub until that module ships.
_TOTAL_SESSIONS_STUB = 0

_DEFAULT_NAVIGATION_LINKS: tuple[DashboardNavigationLink, ...] = (
    DashboardNavigationLink(
        link="/organizations",
        description="Manage organizations",
    ),
    DashboardNavigationLink(
        link="/users?role=COACH",
        description="Manage coaches",
    ),
    DashboardNavigationLink(
        link="/users?role=PLAYER",
        description="Manage players",
    ),
    DashboardNavigationLink(
        link="/subscriptions",
        description="Manage subscription plans",
    ),
)


class AnalyticsService:
    """Aggregate platform metrics for the Super Admin dashboard. No HTTP here."""

    def __init__(self, analytics: AnalyticsRepository) -> None:
        """Inject the analytics repository."""
        self._analytics = analytics

    @staticmethod
    def _has_dashboard_data(metrics: DashboardMetricsData) -> bool:
        """Return True when at least one countable metric is non-zero."""
        return (
            metrics.total_organizations > 0
            or metrics.total_coaches > 0
            or metrics.total_players > 0
            or metrics.active_subscriptions > 0
            or metrics.revenue_overview > 0
        )

    async def get_dashboard_metrics(self) -> DashboardMetricsData:
        """Return aggregated dashboard metrics or raise when no data exists.

        Raises:
            NotFoundError: When all countable metrics are zero (empty platform).
        """
        total_organizations = await self._analytics.count_active_organizations()
        total_coaches = await self._analytics.count_users_by_role(UserRole.COACH)
        total_players = await self._analytics.count_users_by_role(UserRole.PLAYER)
        active_subscriptions = await self._analytics.count_active_subscriptions()
        revenue_sum = await self._analytics.sum_published_plan_prices()
        revenue_overview = int(revenue_sum)

        metrics = DashboardMetricsData(
            total_organizations=total_organizations,
            total_coaches=total_coaches,
            total_players=total_players,
            total_sessions=_TOTAL_SESSIONS_STUB,
            active_subscriptions=active_subscriptions,
            revenue_overview=revenue_overview,
            links=list(_DEFAULT_NAVIGATION_LINKS),
        )

        if not self._has_dashboard_data(metrics):
            raise NotFoundError(
                "No dashboard data is available",
                code="DASHBOARD_DATA_NOT_AVAILABLE",
            )

        logger.info(
            "dashboard_metrics_loaded organizations={} coaches={} players={} "
            "active_subscriptions={} revenue_overview={}",
            total_organizations,
            total_coaches,
            total_players,
            active_subscriptions,
            revenue_overview,
        )
        return metrics
