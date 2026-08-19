"""End-to-end platform tests for health, OpenAPI, and error handling."""

from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, decode_access_token


class TestHealthEndpoint:
    """Health check and uptime probes (JAW-9404)."""

    @pytest.mark.asyncio
    async def test_health_check_returns_200(self, client: AsyncClient) -> None:
        """JAW-9404: Health endpoint returns healthy envelope."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"
        assert body["message"] == "Service is healthy."

    @pytest.mark.asyncio
    async def test_health_endpoint_requires_no_auth(self, client: AsyncClient) -> None:
        """Health check is public (no Authorization header needed)."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200


class TestOpenApi:
    """Swagger/OpenAPI documentation (JAW-9404)."""

    @pytest.mark.asyncio
    async def test_openapi_json_available(self, client: AsyncClient) -> None:
        """JAW-9404: OpenAPI schema is exposed for Swagger UI."""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == "Hoops Engine API"
        assert "/api/v1/health" in schema["paths"]
        assert "/api/login" in schema["paths"]

    @pytest.mark.asyncio
    async def test_openapi_login_documents_email_and_password(
        self, client: AsyncClient
    ) -> None:
        """Login request body exposes email and password for Swagger Try it out."""
        response = await client.get("/openapi.json")
        schema = response.json()
        login_post = schema["paths"]["/api/login"]["post"]
        ref = login_post["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        model_name = ref.split("/")[-1]
        props = schema["components"]["schemas"][model_name]["properties"]
        assert "email" in props
        assert "password" in props


class TestErrorHandling:
    """Global exception handlers and validation envelopes (JAW-9404)."""

    @pytest.mark.asyncio
    async def test_validation_error_returns_structured_envelope(
        self, client: AsyncClient
    ) -> None:
        """JAW-9404: Validation errors return field-level details in error envelope."""
        response = await client.post(
            "/api/login",
            json={"email": "bad-email", "password": ""},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "Validation error"
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert isinstance(body["error"]["details"], list)
        assert any(item.get("field") for item in body["error"]["details"])

    @pytest.mark.asyncio
    async def test_login_failure_error_envelope_for_frontend(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """JAW-9419: FE can render error below form using message + error.code."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"], "password": "wrong"},
        )
        body = response.json()
        assert body["success"] is False
        assert "message" in body
        assert "error" in body
        assert body["error"]["code"] == "AUTHENTICATION_FAILED"


class TestJwtUtility:
    """JWT utility functions (JAW-9404 auth skeleton)."""

    def test_create_and_decode_access_token_roundtrip(self) -> None:
        """JAW-9404: JWT utility creates decodable tokens."""
        token = create_access_token(
            subject="user-uuid",
            claims={"email": "admin@test.com", "role": "super_admin"},
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "user-uuid"
        assert payload["email"] == "admin@test.com"
        assert "exp" in payload


class TestExternalServiceMocks:
    """Ensure tests remain isolated from third-party services."""

    @pytest.mark.asyncio
    async def test_redis_not_called_during_login(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Login flow does not require live Redis (mock if referenced)."""
        admin = test_users["admin"]
        with patch("redis.asyncio.from_url") as mock_redis:
            mock_redis.return_value.ping.side_effect = AssertionError(
                "Redis should not be contacted during login tests"
            )
            response = await client.post(
                "/api/login",
                json={"email": admin["email"], "password": admin["password"]},
            )
        assert response.status_code == 200


class TestDatabaseConnectivity:
    """Database configuration smoke tests (JAW-9404)."""

    @pytest.mark.asyncio
    async def test_database_session_can_query_super_admins(
        self, db_session, seeded_super_admins: list
    ) -> None:
        """JAW-9404: Test database is reachable and seeded Super Admins exist."""
        from sqlalchemy import func, select

        result = await db_session.scalar(
            select(func.count()).select_from(SuperAdmin)
        )
        assert result == len(seeded_super_admins)


from app.models.super_admin import SuperAdmin
