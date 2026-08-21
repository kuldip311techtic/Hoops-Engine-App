"""JAW-9448 required integration fixture."""

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
    """OpenAPI JSON is served."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert "/api/v1/health" in payload["paths"]
    assert "/api/v1/auth/login" in payload["paths"]


@pytest.mark.asyncio
async def test_validation_error_shape(client: AsyncClient) -> None:
    """Empty login body is 422 with loc/msg/type field details."""
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    details = body["error"]["details"]
    assert isinstance(details, list)
    assert any("loc" in item and "msg" in item and "type" in item for item in details)
    fields = {item.get("field") for item in details}
    assert "email" in fields
    assert "password" in fields


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
