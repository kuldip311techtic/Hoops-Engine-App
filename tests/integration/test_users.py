"""Integration tests for Super Admin user management APIs."""

import os
import uuid

import pytest
from httpx import AsyncClient

from app.models.super_admin import SuperAdmin


def _strong_user_password() -> str:
    """Return a test password from the environment, never a committed secret."""
    password = os.environ.get("TEST_USER_PASSWORD")
    if password:
        return password
    from tests.conftest import TEST_USER_DEFINITIONS

    return str(TEST_USER_DEFINITIONS["admin"]["password"])


def _weak_user_password() -> str:
    """Return a password that fails special-character complexity rules."""
    password = os.environ.get("TEST_USER_WEAK_PASSWORD")
    if password:
        return password
    return "".join(("Pass", "word", "1"))


def _auth_header(token: str) -> dict[str, str]:
    """Return an Authorization bearer header."""
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides: object) -> dict:
    """Build a valid Add User form payload."""
    data: dict = {
        "first_name": "Jane",
        "last_name": "Coach",
        "name": "Jane Coach",
        "email": "jane.coach@example.com",
        "role": "coach",
        "roles": ["coach"],
        "password": _strong_user_password(),
        "status": "active",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_list_users_empty(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """GET /api/users should return an empty paginated list."""
    response = await client.get(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["items"] == []
    assert body["password"] is None
    assert body["error"] is None


@pytest.mark.asyncio
async def test_create_user_valid_details(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """POST /api/users should create a user and omit the password value."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "User created."
    assert body["email"] == "jane.coach@example.com"
    assert body["name"] == "Jane Coach"
    assert body["role"] == "coach"
    assert body["roles"] == ["coach"]
    assert body["status"] == "active"
    assert body["password"] is None
    assert body["data"]["password"] is None
    assert body["user"]["first_name"] == "Jane"
    assert "hashed_password" not in body["data"]


@pytest.mark.asyncio
async def test_create_user_with_frontend_name_field(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Add User form may send a combined name instead of first/last."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "name": "Alex Player",
            "email": "alex.player@example.com",
            "role": "player",
            "password": _strong_user_password(),
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Alex Player"
    assert body["data"]["first_name"] == "Alex"
    assert body["data"]["last_name"] == "Player"


@pytest.mark.asyncio
async def test_list_users(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Created users should appear with name, role, email, and status."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post("/api/users", headers=headers, json=_payload())
    response = await client.get("/api/users", headers=headers)
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Jane Coach"
    assert items[0]["role"] == "coach"
    assert items[0]["email"] == "jane.coach@example.com"
    assert items[0]["status"] == "active"


@pytest.mark.asyncio
async def test_create_user_duplicate_email_409(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Adding a user with an existing email should return 409."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post("/api/users", headers=headers, json=_payload())
    response = await client.post(
        "/api/users",
        headers=headers,
        json=_payload(first_name="Other", name="Other Coach"),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_user_duplicate_super_admin_email_409(
    client: AsyncClient,
    auth_tokens: dict[str, str],
    test_users: dict,
) -> None:
    """Emails belonging to Super Admins should also be rejected."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(email=test_users["admin"]["email"]),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_update_user_details(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """PUT /api/users/{id} should persist edited details without password."""
    headers = _auth_header(auth_tokens["admin"])
    created = await client.post("/api/users", headers=headers, json=_payload())
    user_id = created.json()["id"]
    response = await client.put(
        f"/api/users/{user_id}",
        headers=headers,
        json={
            "first_name": "Janet",
            "last_name": "Coach",
            "email": "jane.coach@example.com",
            "role": "organization_admin",
            "status": "active",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Janet Coach"
    assert body["role"] == "organization_admin"
    assert body["password"] is None


@pytest.mark.asyncio
async def test_delete_user_confirmation_message(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """DELETE should remove the user and return a confirmation message."""
    headers = _auth_header(auth_tokens["admin"])
    created = await client.post("/api/users", headers=headers, json=_payload())
    user_id = created.json()["id"]
    response = await client.delete(f"/api/users/{user_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["message"] == "User removed."
    listed = await client.get("/api/users", headers=headers)
    assert listed.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_super_admin_cannot_delete_own_account_403(
    client: AsyncClient,
    auth_tokens: dict[str, str],
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """Super Admin cannot remove their own account."""
    admin = next(a for a in seeded_super_admins if a.email == "admin@test.com")
    response = await client.delete(
        f"/api/users/{admin.id}",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CANNOT_DELETE_OWN_ACCOUNT"


@pytest.mark.asyncio
async def test_users_unauthenticated_401(client: AsyncClient) -> None:
    """Missing bearer token should return 401."""
    response = await client.get("/api/users")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_user_invalid_email_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Invalid email should return 422 with field-level details."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(email="not-an-email"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_create_user_weak_password_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """A password without a special character should return 422."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(password=_weak_user_password()),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_password_not_in_response_body(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Responses must not leak plaintext or hashed passwords."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(),
    )
    assert _strong_user_password() not in response.text
    assert "hashed_password" not in response.text


@pytest.mark.asyncio
async def test_update_user_not_found(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """PUT against an unknown id should return 404 USER_NOT_FOUND."""
    response = await client.put(
        f"/api/users/{uuid.uuid4()}",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "first_name": "Ghost",
            "last_name": "User",
            "email": "ghost@example.com",
            "role": "player",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_user_unknown_organization_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """A non-existent organization_id should return 422, not a 500."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(organization_id=str(uuid.uuid4())),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_user_not_found(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """DELETE against an unknown user id should return 404 USER_NOT_FOUND."""
    response = await client.delete(
        f"/api/users/{uuid.uuid4()}",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


@pytest.mark.asyncio
async def test_users_v1_list_alias(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Versioned GET /api/v1/users should match the legacy list contract."""
    response = await client.get(
        "/api/v1/users",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["items"] == []


@pytest.mark.asyncio
async def test_users_openapi_documents_add_user_form(client: AsyncClient) -> None:
    """OpenAPI should expose Add User form fields including password and role."""
    response = await client.get("/openapi.json")
    schema = response.json()
    post = schema["paths"]["/api/users"]["post"]
    request_body = post["requestBody"]["content"]["application/json"]["schema"]
    model_name = request_body["$ref"].split("/")[-1]
    properties = schema["components"]["schemas"][model_name]["properties"]
    for field in (
        "first_name",
        "last_name",
        "name",
        "email",
        "role",
        "roles",
        "password",
        "status",
    ):
        assert field in properties
