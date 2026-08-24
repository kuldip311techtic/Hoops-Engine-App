"""Integration tests for project scaffold and health endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    """Liveness returns the success envelope with status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_openapi_available(client: AsyncClient) -> None:
    """OpenAPI JSON is served and documents the health route."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert "/api/v1/health" in payload["paths"]


@pytest.mark.asyncio
async def test_unhandled_error_does_not_leak_internal_message(
    client: AsyncClient,
) -> None:
    """Unknown protected paths return the envelope, never a stack trace."""
    response = await client.get("/api/v1/does-not-exist")
    assert response.status_code in (401, 404)
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] in ("UNAUTHORIZED", "NOT_FOUND")
    assert "Traceback" not in response.text
    assert "SELECT" not in response.text
