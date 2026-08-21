"""Health HTTP tests."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check_status_ok(client: AsyncClient) -> None:
    """GET /api/v1/health is 200 with data.status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_is_public(client: AsyncClient) -> None:
    """Health does not require Authorization."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert "Not authenticated" not in response.text


@pytest.mark.asyncio
async def test_health_ready_success(client: AsyncClient) -> None:
    """Readiness succeeds when ping returns True."""
    with patch(
        "app.repositories.health_repository.HealthRepository.ping",
        new=AsyncMock(return_value=True),
    ):
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_health_ready_database_unavailable(client: AsyncClient) -> None:
    """Readiness returns 503 when ping fails."""
    with patch(
        "app.repositories.health_repository.HealthRepository.ping",
        new=AsyncMock(return_value=False),
    ):
        response = await client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
