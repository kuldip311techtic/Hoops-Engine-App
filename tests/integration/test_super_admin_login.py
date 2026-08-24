"""HTTP tests for POST /api/super-admin/login."""

import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_login_success_returns_token_and_redirect_to(client: AsyncClient) -> None:
    """Successful login returns JWT, redirect_to, and top-level UI fields."""
    response = await client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful"
    assert body["email"] == ADMIN_EMAIL
    assert body["description"]
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["redirect_to"] == "/dashboard"
    assert body["data"]["access_token"]
    assert body["data"]["token"] == body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert ADMIN_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_login_invalid_credentials_401(client: AsyncClient) -> None:
    """Wrong password is 401 INVALID_CREDENTIALS."""
    response = await client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_EMAIL, "password": "WrongPass1!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Incorrect email or password"
    assert body["description"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_empty_email_400(client: AsyncClient) -> None:
    """Whitespace-only email is 400 BAD_REQUEST."""
    response = await client.post(
        "/api/super-admin/login",
        json={"email": "   ", "password": "password123"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_login_empty_password_400(client: AsyncClient) -> None:
    """Whitespace-only password is 400 BAD_REQUEST."""
    response = await client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_EMAIL, "password": "   "},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "BAD_REQUEST"


@pytest.mark.asyncio
async def test_login_malformed_email_422(client: AsyncClient) -> None:
    """Malformed email is 422 VALIDATION_ERROR."""
    response = await client.post(
        "/api/super-admin/login",
        json={"email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_missing_password_422(client: AsyncClient) -> None:
    """Missing password field is 422."""
    response = await client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_EMAIL},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_openapi_documents_email_and_password(client: AsyncClient) -> None:
    """Swagger schema includes email and password for login."""
    spec = (await client.get("/openapi.json")).json()
    login = spec["paths"]["/api/super-admin/login"]["post"]
    body = login["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in body:
        name = body["$ref"].split("/")[-1]
        props = spec["components"]["schemas"][name]["properties"]
    else:
        props = body["properties"]
    assert "email" in props
    assert "password" in props


@pytest.mark.asyncio
async def test_login_never_echoes_password(client: AsyncClient) -> None:
    """Successful and failed responses never include the submitted password."""
    for payload in (
        {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        {"email": ADMIN_EMAIL, "password": "WrongPass1!"},
    ):
        response = await client.post("/api/super-admin/login", json=payload)
        assert payload["password"] not in response.text
