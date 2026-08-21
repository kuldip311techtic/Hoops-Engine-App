"""Live health, docs, and error-envelope integration tests."""

async def test_health_liveness_ok(client) -> None:
    """GET /api/v1/health returns the success envelope without auth."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert "message" in body


async def test_health_ready_hits_postgres(client) -> None:
    """GET /api/v1/health/ready runs SELECT 1 against the test database."""
    response = await client.get("/api/v1/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["message"] == "Service is ready"


async def test_docs_available(client) -> None:
    """Swagger UI is served."""
    response = await client.get("/docs")
    assert response.status_code == 200


async def test_validation_error_shape_on_login(client) -> None:
    """Validation failures use {success, message, error.details}."""
    response = await client.post("/api/v1/auth/login", json={"email": "x"})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert isinstance(body["error"]["details"], list)


async def test_unhandled_500_does_not_leak(app) -> None:
    """Global 500 handler never returns exception text."""
    from httpx import ASGITransport, AsyncClient

    marker = "internal-db-trace-must-not-appear"

    @app.get("/api/v1/_boom")
    async def _boom() -> dict:
        raise RuntimeError(marker)

    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/_boom")
    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert marker not in body["message"]
    assert marker not in response.text


async def test_login_openapi_documents_email_and_password(client) -> None:
    """Swagger includes email and password on LoginRequest."""
    spec = (await client.get("/openapi.json")).json()
    schema = spec["components"]["schemas"]["LoginRequest"]
    assert "email" in schema["properties"]
    assert "password" in schema["properties"]
    assert "/api/v1/auth/login" in spec["paths"]
    assert "/api/auth/login" in spec["paths"]
