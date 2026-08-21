"""Live PostgreSQL integration tests for admin organizations (JAW-9457)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def clear_organizations(postgres_schema: None) -> None:
    """Ensure each test starts with an empty organizations table."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE organizations RESTART IDENTITY CASCADE")
        )
        await session.commit()


async def _create_org(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Central Hoops",
    published: bool = True,
) -> dict:
    """Helper: create an organization and return parsed JSON."""
    response = await client.post(
        "/api/v1/organizations",
        headers=headers,
        json={
            "name": name,
            "contact_email": f"{name.replace(' ', '').lower()}@example.com",
            "phone_number": "5551234567",
            "address": "100 Court St",
            "description": "Integration test org",
            "is_published": published,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- JAW-9457 acceptance criteria ---


@pytest.mark.asyncio
async def test_jaw_9457_view_organizations(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9457] View list of organizations."""
    await _create_org(db_client, admin_headers, name="List Org")
    response = await db_client.get("/api/v1/organizations", headers=admin_headers)
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "List Org"


@pytest.mark.asyncio
async def test_jaw_9457_add_organization(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9457] Add new organization."""
    body = await _create_org(db_client, admin_headers, name="New Org")
    org = body["data"]["organization"]
    assert org["email"] == org["contact_email"]
    assert org["phone"] == org["phone_number"]


@pytest.mark.asyncio
async def test_jaw_9457_edit_organization(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9457] Edit existing organization."""
    created = await _create_org(db_client, admin_headers, name="Edit Org")
    org_id = created["data"]["organization"]["id"]
    update = await db_client.put(
        f"/api/v1/organizations/{org_id}",
        headers=admin_headers,
        json={"name": "Edit Org Updated", "address": "200 Lane"},
    )
    assert update.status_code == 200
    assert update.json()["data"]["organization"]["name"] == "Edit Org Updated"


@pytest.mark.asyncio
async def test_jaw_9457_remove_organization(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9457] Remove organization (soft-deactivate)."""
    created = await _create_org(db_client, admin_headers, name="Remove Org")
    org_id = created["data"]["organization"]["id"]
    delete = await db_client.delete(
        f"/api/v1/organizations/{org_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["data"]["organization"]["is_active"] is False


@pytest.mark.asyncio
async def test_jaw_9457_published_only_active_published_orgs(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9457] published_only returns only published active organizations."""
    await _create_org(db_client, admin_headers, name="Published Org", published=True)
    await _create_org(db_client, admin_headers, name="Draft Org", published=False)
    response = await db_client.get(
        "/api/v1/organizations?published_only=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    names = [row["name"] for row in response.json()["data"]["items"]]
    assert names == ["Published Org"]


@pytest.mark.asyncio
async def test_jaw_9457_openapi_documents_organizations(
    db_client: AsyncClient,
) -> None:
    """[JAW-9457] OpenAPI includes organization operations."""
    response = await db_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/organizations" in paths
    assert "delete" in paths["/api/v1/organizations/{organization_id}"]


# --- Auth ---


@pytest.mark.asyncio
async def test_organizations_missing_token_401(
    db_client: AsyncClient,
    missing_auth_headers: dict[str, str],
) -> None:
    response = await db_client.get(
        "/api/v1/organizations",
        headers=missing_auth_headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_organizations_user_role_forbidden(
    db_client: AsyncClient,
    user_headers: dict[str, str],
) -> None:
    response = await db_client.get("/api/v1/organizations", headers=user_headers)
    assert response.status_code == 403


# --- Edge cases ---


@pytest.mark.asyncio
async def test_create_org_invalid_phone_returns_422(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={
            "name": "Bad Phone",
            "contact_email": "bad@example.com",
            "phone_number": "abc!!!",
            "address": "1 St",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_org_empty_address_returns_422(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={
            "name": "No Address",
            "contact_email": "noaddr@example.com",
            "phone_number": "5551112222",
            "address": "",
        },
    )
    assert response.status_code == 422


# --- Error cases ---


@pytest.mark.asyncio
async def test_get_organization_not_found(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.get(
        f"/api/v1/organizations/{uuid4()}",
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_duplicate_org_name_conflict(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    payload = {
        "name": "Unique Org",
        "contact_email": "a@example.com",
        "phone_number": "5554443333",
        "address": "3 Rd",
    }
    assert (
        await db_client.post(
            "/api/v1/organizations", headers=admin_headers, json=payload
        )
    ).status_code == 201
    dup = await db_client.post(
        "/api/v1/organizations",
        headers=admin_headers,
        json={**payload, "contact_email": "b@example.com"},
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_organizations_alias_path(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    response = await db_client.get("/api/organizations", headers=admin_headers)
    assert response.status_code == 200
