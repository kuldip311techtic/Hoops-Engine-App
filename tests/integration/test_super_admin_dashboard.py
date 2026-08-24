"""Integration tests for Super Admin dashboard analytics API (JAW-9600)."""

import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_LIVE_EMAIL, ADMIN_LIVE_PASSWORD

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
async def test_jaw_9600_ac_dashboard_loads_after_login(
    live_client: AsyncClient,
    seed_dashboard_metrics: dict,
    seed_five_users: dict,
) -> None:
    """[JAW-9600 AC] Dashboard loads successfully after login."""
    login = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": ADMIN_LIVE_PASSWORD},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    assert login.json()["data"]["redirect_to"] == "/dashboard"

    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    for key in METRIC_KEYS:
        assert key in body["data"]


@pytest.mark.asyncio
async def test_jaw_9600_ac_key_metrics_displayed_accurately(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600 AC] All key metrics are displayed accurately."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_organizations"] == 1
    assert data["total_coaches"] == 1
    assert data["total_players"] == 1
    assert data["active_subscriptions"] == 1
    assert data["revenue_overview"] == 49
    assert data["total_sessions"] == 0


@pytest.mark.asyncio
async def test_jaw_9600_ac_navigate_to_core_modules(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600 AC] Super Admin can navigate to core modules from the dashboard."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    links = response.json()["data"]["links"]
    assert len(links) == 4
    link_paths = {item["link"] for item in links}
    assert "/organizations" in link_paths
    assert "/users?role=COACH" in link_paths
    assert "/users?role=PLAYER" in link_paths
    assert "/subscriptions" in link_paths
    assert all("description" in item for item in links)


@pytest.mark.asyncio
async def test_jaw_9600_ac_return_200_with_analytics_data(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """[JAW-9600 AC] Return 200 status with analytics data."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["message"] == "Dashboard analytics retrieved"
    for key in METRIC_KEYS:
        assert key in body["data"]


@pytest.mark.asyncio
async def test_jaw_9600_ac_return_404_when_no_data(
    live_client: AsyncClient,
    admin_access_token: str,
    clean_dashboard_metrics: None,
) -> None:
    """[JAW-9600 AC] Return 404 status if no data is available."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DASHBOARD_DATA_NOT_AVAILABLE"


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_unauthenticated_returns_401(
    live_client: AsyncClient,
    clean_dashboard_metrics: None,
) -> None:
    """Auth: missing Bearer token returns 401."""
    response = await live_client.get("/api/super-admin/dashboard")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_expired_token_returns_401(
    live_client: AsyncClient,
    expired_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """Auth: expired JWT returns 401."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """Auth: non-admin user cannot access dashboard analytics."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_jaw_9600_dashboard_viewer_returns_403(
    live_client: AsyncClient,
    viewer_access_token: str,
    seed_dashboard_metrics: dict,
) -> None:
    """Auth: viewer role cannot access Super Admin dashboard."""
    response = await live_client.get(
        "/api/super-admin/dashboard",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
