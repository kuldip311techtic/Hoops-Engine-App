"""Integration tests for Super Admin dashboard analytics API (JAW-9600)."""

import pytest
from httpx import AsyncClient

METRIC_KEYS = (
    "total_organizations",
    "total_coaches",
    "total_players",
    "total_sessions",
    "active_subscriptions",
    "revenue_overview",
    "links",
)


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600] Super Admin dashboard returns analytics data."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["description"]
    assert body["error"] is None
    data = body["data"]
    for key in METRIC_KEYS:
        assert key in data


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_metrics_keys(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600] Dashboard payload includes all metric fields."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    data = response.json()["data"]
    assert data["total_organizations"] >= 1
    assert data["total_coaches"] >= 1
    assert data["total_players"] >= 1
    assert data["active_subscriptions"] >= 1
    assert data["revenue_overview"] >= 49
    assert data["total_sessions"] == 0


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_reflects_seeded_counts(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600] Dashboard metrics reflect seeded platform data."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    data = response.json()["data"]
    assert data["total_organizations"] == 1
    assert data["total_coaches"] == 1
    assert data["total_players"] == 1
    assert data["active_subscriptions"] == 1
    assert data["revenue_overview"] == 49


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_includes_navigation_links(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600] Dashboard includes navigation links for core modules."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    links = response.json()["data"]["links"]
    assert len(links) == 4
    assert all("link" in item and "description" in item for item in links)
    link_paths = {item["link"] for item in links}
    assert "/organizations" in link_paths
    assert "/subscriptions" in link_paths


@pytest.mark.asyncio
async def test_jaw_9600_no_data_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    clean_dashboard_metrics: None,
) -> None:
    """[JAW-9600] Empty platform returns 404 when no dashboard data exists."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DASHBOARD_DATA_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_jaw_9600_unauthenticated_returns_401(
    live_client: AsyncClient,
    clean_dashboard_metrics: None,
) -> None:
    """[JAW-9600] Missing Bearer token returns 401."""
    response = await live_client.get("/api/super-admin/dashboard")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9600_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600] Non-admin users cannot access dashboard analytics."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"
