"""Integration tests required by the project-setup ticket."""

from pydantic import BaseModel, Field


async def test_health_returns_ok(client) -> None:
    """GET /api/v1/health returns the success envelope."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert "message" in body


async def test_openapi_available(client) -> None:
    """OpenAPI documents the health route."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "/api/v1/health" in spec["paths"]
    health = spec["paths"]["/api/v1/health"]["get"]
    assert health["summary"] == "Liveness probe"
    assert "health" in health["tags"]


async def test_validation_error_shape(app) -> None:
    """Validation failures use the project error envelope with field details."""
    from httpx import ASGITransport, AsyncClient

    class SampleBody(BaseModel):
        field_name: str = Field(..., description="Required example field")

    @app.post("/api/v1/_validation-sample")
    async def _validation_sample(body: SampleBody) -> dict:
        return {"received": body.field_name}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/_validation-sample", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)
    fields = {item["field"] for item in body["error"]["details"]}
    assert "field_name" in fields


async def test_unhandled_error_does_not_leak_internal_message(app) -> None:
    """500 responses never include exception text or stack traces."""
    from httpx import ASGITransport, AsyncClient

    internal_marker = "internal-db-trace-must-not-appear"

    @app.get("/api/v1/_boom")
    async def _boom() -> dict:
        raise RuntimeError(internal_marker)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/_boom")
    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert internal_marker not in body["message"]
    assert internal_marker not in response.text
