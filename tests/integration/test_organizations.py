"""Integration tests for Super Admin organization management APIs."""

import uuid

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.super_admin import SuperAdmin


def _auth_header(token: str) -> dict[str, str]:
    """Return an Authorization bearer header."""
    return {"Authorization": f"Bearer {token}"}


def _payload(**overrides: object) -> dict:
    """Build a valid organization write payload."""
    data: dict = {
        "name": "Hoops Academy",
        "email": "ops@hoopsacademy.example",
        "contact_email": "ops@hoopsacademy.example",
        "phone_number": "+1-555-0100",
        "address": "123 Court Street, Springfield",
        "description": "Youth basketball training organization.",
        "status": "active",
    }
    data.update(overrides)
    return data


@pytest.mark.asyncio
async def test_list_organizations_empty(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """GET /api/organizations should return an empty paginated list."""
    response = await client.get(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Organizations retrieved."
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0
    assert body["data"]["page"] == 1
    assert "email" in body
    assert "organization" in body
    assert "status" in body
    assert body["error"] is None


@pytest.mark.asyncio
async def test_create_organization_valid_details(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """POST /api/organizations should create an organization and return FE fields."""
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Organization created."
    assert body["description"]
    assert body["email"] == "ops@hoopsacademy.example"
    assert body["organization"]["name"] == "Hoops Academy"
    assert body["organization"]["email"] == body["email"]
    assert body["organization"]["contact_email"] == body["email"]
    assert body["id"] == body["organization"]["id"]
    assert body["name"] == "Hoops Academy"
    assert body["status"] == "active"
    assert body["data"]["phone_number"] == "+1-555-0100"
    assert body["error"] is None


@pytest.mark.asyncio
async def test_list_organizations_success(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Created organizations should appear in the list with status and email."""
    await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(),
    )
    response = await client.get(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Hoops Academy"
    assert items[0]["email"] == "ops@hoopsacademy.example"
    assert items[0]["status"] == "active"


@pytest.mark.asyncio
async def test_create_organization_duplicate_name_409(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Adding an organization with an existing name should return 409."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post("/api/organizations", headers=headers, json=_payload())
    response = await client.post(
        "/api/organizations",
        headers=headers,
        json=_payload(email="other@example.com", contact_email="other@example.com"),
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ORGANIZATION_NAME_EXISTS"
    assert "already exists" in body["message"]


@pytest.mark.asyncio
async def test_create_organization_duplicate_email_409(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Adding an organization with an existing email should return 409."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post("/api/organizations", headers=headers, json=_payload())
    response = await client.post(
        "/api/organizations",
        headers=headers,
        json=_payload(name="Other Academy"),
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    assert body["error"]["details"][0]["field"] == "email"


@pytest.mark.asyncio
async def test_create_organization_duplicate_name_case_insensitive(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Name uniqueness should ignore case."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post("/api/organizations", headers=headers, json=_payload())
    response = await client.post(
        "/api/organizations",
        headers=headers,
        json=_payload(
            name="hoops academy",
            email="unique@example.com",
            contact_email="unique@example.com",
        ),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORGANIZATION_NAME_EXISTS"


@pytest.mark.asyncio
async def test_update_organization_details(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """PUT /api/organizations/{id} should persist edited details."""
    headers = _auth_header(auth_tokens["admin"])
    created = await client.post(
        "/api/organizations",
        headers=headers,
        json=_payload(),
    )
    org_id = created.json()["id"]
    response = await client.put(
        f"/api/organizations/{org_id}",
        headers=headers,
        json=_payload(
            name="Hoops Academy East",
            phone_number="+1-555-0199",
            status="active",
        ),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Hoops Academy East"
    assert body["organization"]["phone_number"] == "+1-555-0199"
    assert body["message"] == "Organization updated."


@pytest.mark.asyncio
async def test_update_organization_not_found(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """PUT against an unknown id should return 404 ORGANIZATION_NOT_FOUND."""
    response = await client.put(
        f"/api/organizations/{uuid.uuid4()}",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(name="Ghost Org", email="ghost@example.com"),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_organization_in_use_warning_409(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Removing an active organization should return an in-use warning."""
    headers = _auth_header(auth_tokens["admin"])
    created = await client.post(
        "/api/organizations",
        headers=headers,
        json=_payload(),
    )
    org_id = created.json()["id"]
    response = await client.delete(
        f"/api/organizations/{org_id}",
        headers=headers,
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "ORGANIZATION_IN_USE"
    assert "currently in use" in body["message"]
    assert body["error"]["details"]["in_use"] is True


@pytest.mark.asyncio
async def test_delete_organization_confirmation_message(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Inactive organizations can be removed; response includes confirmation."""
    headers = _auth_header(auth_tokens["admin"])
    created = await client.post(
        "/api/organizations",
        headers=headers,
        json=_payload(),
    )
    org_id = created.json()["id"]
    await client.put(
        f"/api/organizations/{org_id}",
        headers=headers,
        json=_payload(status="inactive"),
    )
    response = await client.delete(
        f"/api/organizations/{org_id}",
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Organization removed."
    assert body["description"]
    assert body["id"] == org_id
    assert body["name"] == "Hoops Academy"
    listed = await client.get("/api/organizations", headers=headers)
    assert listed.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_organizations_unauthenticated_401(client: AsyncClient) -> None:
    """Missing bearer token should return 401 with AUTHENTICATION_FAILED."""
    response = await client.get("/api/organizations")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_organizations_invalid_token_401(client: AsyncClient) -> None:
    """An invalid JWT should return 401."""
    response = await client.get(
        "/api/organizations",
        headers=_auth_header("not-a-valid-token"),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_organizations_inactive_admin_401(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Inactive Super Admin tokens should not access organization APIs."""
    response = await client.get(
        "/api/organizations",
        headers=_auth_header(auth_tokens["inactive"]),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_organizations_non_super_admin_403(
    client: AsyncClient,
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """A JWT without super_admin role should return 403."""
    admin = seeded_super_admins[0]
    token = create_access_token(
        subject=str(admin.id),
        claims={"email": admin.email, "role": "coach"},
    )
    response = await client.get(
        "/api/organizations",
        headers=_auth_header(token),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_FAILED"


@pytest.mark.asyncio
async def test_create_organization_validation_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Invalid email should return 422 with field-level details."""
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_payload(email="not-an-email", contact_email="not-an-email"),
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


@pytest.mark.asyncio
async def test_legacy_and_v1_paths_both_work(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Both /api/organizations and /api/v1/organizations should be available."""
    headers = _auth_header(auth_tokens["admin"])
    created = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json=_payload(name="V1 Academy", email="v1@example.com"),
    )
    assert created.status_code == 201
    listed = await client.get("/api/organizations", headers=headers)
    assert listed.status_code == 200
    names = [item["name"] for item in listed.json()["data"]["items"]]
    assert "V1 Academy" in names


@pytest.mark.asyncio
async def test_organizations_openapi_documents_request_body(
    client: AsyncClient,
) -> None:
    """OpenAPI should expose Add Organization form fields including email and name."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/api/organizations" in schema["paths"]
    post = schema["paths"]["/api/organizations"]["post"]
    request_body = post["requestBody"]["content"]["application/json"]["schema"]
    assert "$ref" in request_body
    model_name = request_body["$ref"].split("/")[-1]
    properties = schema["components"]["schemas"][model_name]["properties"]
    for field in (
        "name",
        "email",
        "contact_email",
        "phone_number",
        "address",
        "description",
        "status",
    ):
        assert field in properties
    assert "security" not in post or post.get("security") != []
