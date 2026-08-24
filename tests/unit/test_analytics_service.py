"""Unit tests for AnalyticsService."""

from decimal import Decimal

import pytest

from app.exceptions.base import NotFoundError
from app.services.analytics_service import AnalyticsService
from tests.fakes import InMemoryAnalyticsRepository


@pytest.fixture
def analytics_repo() -> InMemoryAnalyticsRepository:
    """Analytics repository with sample counts."""
    return InMemoryAnalyticsRepository(
        total_organizations=2,
        total_coaches=3,
        total_players=5,
        active_subscriptions=1,
        revenue_overview=Decimal("49.99"),
    )


@pytest.fixture
def service(analytics_repo: InMemoryAnalyticsRepository) -> AnalyticsService:
    """AnalyticsService bound to in-memory analytics."""
    return AnalyticsService(analytics_repo)


@pytest.mark.asyncio
async def test_get_dashboard_metrics_success(service: AnalyticsService) -> None:
    """Dashboard metrics include all required fields and navigation links."""
    metrics = await service.get_dashboard_metrics()
    assert metrics.total_organizations == 2
    assert metrics.total_coaches == 3
    assert metrics.total_players == 5
    assert metrics.total_sessions == 0
    assert metrics.active_subscriptions == 1
    assert metrics.revenue_overview == 49
    assert len(metrics.links) == 4
    assert metrics.links[0].link == "/organizations"
    assert metrics.links[0].description


@pytest.mark.asyncio
async def test_get_dashboard_metrics_zero_raises_not_found() -> None:
    """Empty platform metrics raise DASHBOARD_DATA_NOT_AVAILABLE."""
    service = AnalyticsService(InMemoryAnalyticsRepository())
    with pytest.raises(NotFoundError) as exc_info:
        await service.get_dashboard_metrics()
    assert exc_info.value.code == "DASHBOARD_DATA_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_revenue_overview_sums_published_plan_prices() -> None:
    """Revenue overview converts published plan price sum to whole dollars."""
    service = AnalyticsService(
        InMemoryAnalyticsRepository(revenue_overview=Decimal("5000.50"))
    )
    metrics = await service.get_dashboard_metrics()
    assert metrics.revenue_overview == 5000


@pytest.mark.asyncio
async def test_total_sessions_always_zero_stub(service: AnalyticsService) -> None:
    """Sessions remain stubbed at zero until Coach module exists."""
    metrics = await service.get_dashboard_metrics()
    assert metrics.total_sessions == 0
