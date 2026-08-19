"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient) -> None:
    """Health endpoint should return 200 with healthy status envelope."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "healthy"
    assert "email" in body
    assert "token" in body


@pytest.mark.asyncio
async def test_openapi_docs_available(client: AsyncClient) -> None:
    """OpenAPI schema should be exposed for Swagger UI."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "Hoops Engine API"
    assert "/api/v1/health" in schema["paths"]
