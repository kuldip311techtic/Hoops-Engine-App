"""Health endpoint integration tests."""

from unittest.mock import AsyncMock

from app.api.v1.endpoints.health import get_readiness_service
from app.exceptions import AppError
from app.schemas.health import HealthData, HealthResponse
from app.services.health_service import HealthService


async def test_health_check_status_ok(client) -> None:
    """Liveness returns 200 with status ok."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"


async def test_health_is_public(client) -> None:
    """Health does not require an Authorization header."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert "www-authenticate" not in {k.lower() for k in response.headers}


async def test_health_ready_success(app, client) -> None:
    """Readiness returns 200 when the health service reports ready."""
    service = HealthService(repository=AsyncMock())
    service.readiness = AsyncMock(
        return_value=HealthResponse(
            success=True,
            message="Service is ready",
            data=HealthData(status="ok"),
        )
    )

    app.dependency_overrides[get_readiness_service] = lambda: service
    try:
        response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["success"] is True


async def test_health_ready_database_unavailable(app, client) -> None:
    """Readiness returns 503 with DATABASE_UNAVAILABLE when the DB is down."""

    async def _failing_service() -> HealthService:
        class _Boom(HealthService):
            async def readiness(self):
                raise AppError(
                    "Database is unavailable",
                    status_code=503,
                    code="DATABASE_UNAVAILABLE",
                )

        return _Boom(repository=AsyncMock())

    app.dependency_overrides[get_readiness_service] = _failing_service
    try:
        response = await client.get("/api/v1/health/ready")
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "DATABASE_UNAVAILABLE"
