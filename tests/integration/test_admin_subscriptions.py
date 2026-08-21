"""Live PostgreSQL integration tests for admin subscription plans (JAW-9465)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import AsyncSessionLocal


@pytest.fixture(autouse=True)
async def clear_subscription_plans(postgres_schema: None) -> None:
    """Ensure each test starts with an empty plan catalog."""
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("TRUNCATE TABLE subscription_plans RESTART IDENTITY CASCADE")
        )
        await session.commit()


async def _create_plan(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Team Plan",
    published: bool = True,
    price: float = 49.99,
    billing_cycle: str = "Monthly",
) -> dict:
    """Helper: create a plan and return parsed JSON body."""
    response = await client.post(
        "/api/v1/subscriptions",
        headers=headers,
        json={
            "name": name,
            "description": "Integration test plan",
            "price": price,
            "billing_cycle": billing_cycle,
            "is_published": published,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- JAW-9465 acceptance criteria ---


@pytest.mark.asyncio
async def test_jaw_9465_view_subscription_plans(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9465] View subscription plans."""
    await _create_plan(db_client, admin_headers, name="Listed Plan")
    response = await db_client.get("/api/v1/subscriptions", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    items = body["data"]["items"]
    assert len(items) == 1
    assert items[0]["name"] == "Listed Plan"


@pytest.mark.asyncio
async def test_jaw_9465_add_subscription_plan(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9465] Add new subscription plan."""
    body = await _create_plan(db_client, admin_headers, name="New Plan", price=19.99)
    assert body["data"]["name"] == "New Plan"
    assert float(body["data"]["price"]) == 19.99
    assert body["data"]["billing_cycle"] == "Monthly"


@pytest.mark.asyncio
async def test_jaw_9465_edit_subscription_plan(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9465] Edit existing subscription plan."""
    created = await _create_plan(db_client, admin_headers, name="Editable")
    plan_id = created["data"]["id"]
    update = await db_client.put(
        f"/api/v1/subscriptions/{plan_id}",
        headers=admin_headers,
        json={"price": 99.99, "billing_cycle": "Yearly"},
    )
    assert update.status_code == 200
    data = update.json()["data"]
    assert float(data["price"]) == 99.99
    assert data["billing_cycle"] == "Yearly"


@pytest.mark.asyncio
async def test_jaw_9465_remove_subscription_plan(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9465] Remove subscription plan (soft-unpublish)."""
    created = await _create_plan(db_client, admin_headers, name="Removable")
    plan_id = created["data"]["id"]
    delete = await db_client.delete(
        f"/api/v1/subscriptions/{plan_id}",
        headers=admin_headers,
    )
    assert delete.status_code == 200
    assert delete.json()["data"]["is_published"] is False


@pytest.mark.asyncio
async def test_jaw_9465_published_only_returns_active_catalog(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """[JAW-9465] Only published plans returned when published_only=true."""
    await _create_plan(db_client, admin_headers, name="Public Plan", published=True)
    await _create_plan(db_client, admin_headers, name="Draft Plan", published=False)
    response = await db_client.get(
        "/api/v1/subscriptions?published_only=true",
        headers=admin_headers,
    )
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["data"]["items"]]
    assert names == ["Public Plan"]


@pytest.mark.asyncio
async def test_jaw_9465_openapi_documents_subscriptions(
    db_client: AsyncClient,
) -> None:
    """[JAW-9465] API documentation includes subscription plan operations."""
    response = await db_client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/subscriptions" in paths
    assert "get" in paths["/api/v1/subscriptions"]
    assert "post" in paths["/api/v1/subscriptions"]
    assert "/api/subscriptions" in paths


# --- Auth tests ---


@pytest.mark.asyncio
async def test_subscriptions_missing_token_returns_401(
    db_client: AsyncClient,
    missing_auth_headers: dict[str, str],
) -> None:
    """Missing bearer token is rejected."""
    response = await db_client.get(
        "/api/v1/subscriptions",
        headers=missing_auth_headers,
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_subscriptions_regular_user_forbidden(
    db_client: AsyncClient,
    user_headers: dict[str, str],
) -> None:
    """Non Super Admin receives 403."""
    response = await db_client.get("/api/v1/subscriptions", headers=user_headers)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_subscriptions_viewer_forbidden(
    db_client: AsyncClient,
    viewer_headers: dict[str, str],
) -> None:
    """Viewer role cannot manage subscriptions."""
    response = await db_client.post(
        "/api/v1/subscriptions",
        headers=viewer_headers,
        json={
            "name": "Blocked",
            "price": 1.0,
            "billing_cycle": "Monthly",
        },
    )
    assert response.status_code == 403


# --- Edge cases ---


@pytest.mark.asyncio
async def test_create_plan_unicode_name(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Unicode characters in plan name are accepted."""
    body = await _create_plan(
        db_client,
        admin_headers,
        name="Pro Coach — Elite",
    )
    assert "—" in body["data"]["name"]


@pytest.mark.asyncio
async def test_create_plan_max_length_name(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Name at max length (255) is accepted."""
    name = "P" * 255
    body = await _create_plan(db_client, admin_headers, name=name)
    assert len(body["data"]["name"]) == 255


@pytest.mark.asyncio
async def test_create_plan_name_too_long_returns_422(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Name exceeding 255 chars returns validation error."""
    response = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json={
            "name": "X" * 256,
            "price": 9.99,
            "billing_cycle": "Monthly",
        },
    )
    assert response.status_code == 422


# --- Error cases ---


@pytest.mark.asyncio
async def test_get_plan_not_found(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Unknown plan id returns 404."""
    response = await db_client.get(
        f"/api/v1/subscriptions/{uuid4()}",
        headers=admin_headers,
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_duplicate_name_conflict(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Duplicate plan name returns 409."""
    payload = {"name": "Dup Plan", "price": 12.0, "billing_cycle": "Monthly"}
    assert (
        await db_client.post(
            "/api/v1/subscriptions", headers=admin_headers, json=payload
        )
    ).status_code == 201
    dup = await db_client.post(
        "/api/v1/subscriptions", headers=admin_headers, json=payload
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "SUBSCRIPTION_PLAN_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_create_plan_invalid_price_returns_422(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Non-positive price fails validation."""
    response = await db_client.post(
        "/api/v1/subscriptions",
        headers=admin_headers,
        json={"name": "Bad Price", "price": -1, "billing_cycle": "Monthly"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_subscriptions_alias_path(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """GET /api/subscriptions alias works."""
    response = await db_client.get("/api/subscriptions", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
