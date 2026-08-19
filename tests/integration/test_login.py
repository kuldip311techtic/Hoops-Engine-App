"""Integration tests for Super Admin login endpoints."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import hash_password
from app.dependencies.auth import get_auth_service
from app.main import create_app
from app.models.super_admin import SuperAdmin
from app.repositories.super_admin_repository import SuperAdminRepository
from app.services.auth_service import AuthService


@pytest.fixture
def seeded_admin() -> SuperAdmin:
    """Provide a seeded Super Admin entity."""
    admin = SuperAdmin(
        email="admin@example.com",
        hashed_password=hash_password("password123"),
        is_active=True,
    )
    return admin


@pytest.fixture
async def login_client(seeded_admin: SuperAdmin) -> AsyncIterator[AsyncClient]:
    """HTTP client with auth service backed by a mocked repository."""
    mock_repo = AsyncMock(spec=SuperAdminRepository)
    mock_repo.get_by_email.return_value = seeded_admin
    auth_service = AuthService(mock_repo)

    application = create_app()

    async def override_auth_service() -> AuthService:
        return auth_service

    application.dependency_overrides[get_auth_service] = override_auth_service

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    application.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_post_api_login_success(login_client: AsyncClient) -> None:
    """POST /api/login should return JWT token on valid credentials."""
    response = await login_client.post(
        "/api/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful."
    assert body["description"]
    assert body["data"]["token"]
    assert body["data"]["email"] == "admin@example.com"
    assert body["data"]["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_post_api_v1_auth_login_success(login_client: AsyncClient) -> None:
    """POST /api/v1/auth/login should return JWT token on valid credentials."""
    response = await login_client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token"]


@pytest.mark.asyncio
async def test_login_invalid_credentials_returns_401(login_client: AsyncClient) -> None:
    """Invalid credentials should return 401 with error envelope."""
    response = await login_client.post(
        "/api/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Invalid email or password."
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_login_validation_error_empty_password(login_client: AsyncClient) -> None:
    """Empty password should return 422 validation error."""
    response = await login_client.post(
        "/api/login",
        json={"email": "admin@example.com", "password": ""},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


@pytest.mark.asyncio
async def test_login_validation_error_invalid_email(login_client: AsyncClient) -> None:
    """Invalid email format should return 422 validation error."""
    response = await login_client.post(
        "/api/login",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_openapi_documents_request_body(login_client: AsyncClient) -> None:
    """OpenAPI schema should expose email and password fields for login."""
    response = await login_client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    login_path = schema["paths"]["/api/login"]["post"]
    request_body = login_path["requestBody"]["content"]["application/json"]["schema"]
    assert "$ref" in request_body
    model_name = request_body["$ref"].split("/")[-1]
    login_schema = schema["components"]["schemas"][model_name]
    assert "email" in login_schema["properties"]
    assert "password" in login_schema["properties"]
