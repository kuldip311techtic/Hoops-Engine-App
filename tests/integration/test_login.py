"""Login HTTP tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_EMAIL, ADMIN_PASSWORD


@pytest.mark.asyncio
async def test_login_success_v1(client: AsyncClient) -> None:
    """POST /api/v1/auth/login returns tokens and redirect_to."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["redirect_to"] == "/dashboard"
    assert body["data"]["access_token"]
    assert body["email"] == ADMIN_EMAIL
    assert body["description"]
    assert body["message"]
    assert "error" not in body or body.get("error") is None
    assert ADMIN_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_login_success_legacy_api_auth_login(client: AsyncClient) -> None:
    """Ticket path POST /api/auth/login is an alias."""
    response = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_login_invalid_credentials_401(client: AsyncClient) -> None:
    """Wrong password is 401 INVALID_CREDENTIALS."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "WrongPass1!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Incorrect email or password"
    assert body["description"] == "Incorrect email or password"
    assert "error" in body


@pytest.mark.asyncio
async def test_login_invalid_email_422(client: AsyncClient) -> None:
    """Malformed email is 422."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "x"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_missing_fields_422(client: AsyncClient) -> None:
    """Missing fields (empty login form) is 422."""
    response = await client.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_openapi_documents_email_and_password(client: AsyncClient) -> None:
    """Swagger schema includes email and password for login."""
    spec = (await client.get("/openapi.json")).json()
    login = spec["paths"]["/api/v1/auth/login"]["post"]
    body = login["requestBody"]["content"]["application/json"]["schema"]
    # May be a $ref
    if "$ref" in body:
        name = body["$ref"].split("/")[-1]
        props = spec["components"]["schemas"][name]["properties"]
    else:
        props = body["properties"]
    assert "email" in props
    assert "password" in props


@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient) -> None:
    """Refresh returns a new access token."""
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    refresh = login.json()["data"]["refresh_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_refresh_invalid_401(client: AsyncClient) -> None:
    """Invalid refresh token is 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-valid"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_requires_auth(client: AsyncClient) -> None:
    """Change-password without a bearer token is 401."""
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "x", "new_password": "BrandNew1!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """Registering the admin email returns 409 EMAIL_ALREADY_EXISTS."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": ADMIN_EMAIL, "password": "Another1!"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_login_does_not_echo_password(client: AsyncClient) -> None:
    """Successful login responses do not include the submitted password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert ADMIN_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_login_frontend_contract_fields(client: AsyncClient) -> None:
    """Admin FE binds message, email, description on success and error on failure."""
    ok = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    body = ok.json()
    for key in ("message", "email", "description"):
        assert key in body
        assert body[key]
    assert "password" not in body
    assert "password" not in body["data"]
    assert body["data"]["email"] == ADMIN_EMAIL
    assert body["data"]["redirect_to"] == "/dashboard"

    bad = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": "nope"},
    )
    err = bad.json()
    assert err["error"]["code"] == "INVALID_CREDENTIALS"
    assert err["message"]
    assert err["description"]


@pytest.mark.asyncio
async def test_regular_user_cannot_use_super_admin_login(
    client: AsyncClient,
    users,
) -> None:
    """Non-admin credentials look like a failed login on this endpoint."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    users.add(
        User(
            email="player@example.com",
            password_hash=hash_password("Player1!"),
            role=UserRole.USER,
            token_version=1,
            is_active=True,
        )
    )
    response = await client.post(
        "/api/auth/login",
        json={"email": "player@example.com", "password": "Player1!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_empty_body_matches_disabled_button(client: AsyncClient) -> None:
    """Empty form (login button disabled until both fields filled) is 422."""
    response = await client.post("/api/auth/login", json={})
    assert response.status_code == 422
    details = response.json()["error"]["details"]
    fields = {item["field"] for item in details}
    assert "email" in fields
    assert "password" in fields
