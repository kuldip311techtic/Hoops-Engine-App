"""Integration tests for Super Admin subscription plan APIs (JAW-9604)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient

NEW_PLAN_NAME = "Pro Plan"
NEW_PLAN_PRICE = 29.99
UNICODE_PLAN_NAME = "プレミアム Plan"
MAX_LENGTH_NAME = "A" * 255


@pytest.mark.asyncio
async def test_jaw_9604_ac_view_subscription_plans(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] View subscription plans."""
    response = await live_client.get(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 2
    items = body["data"]["items"]
    assert len(items) >= 1
    first = items[0]
    for field in ("id", "name", "price", "billing_cycle", "duration", "status", "description"):
        assert field in first


@pytest.mark.asyncio
async def test_jaw_9604_ac_add_new_subscription_plan(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] Add new subscription plan."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": NEW_PLAN_NAME,
            "description": "Premium coaching access.",
            "price": NEW_PLAN_PRICE,
            "billing_cycle": "monthly",
            "is_published": True,
        },
    )
    assert response.status_code == 201
    plan = response.json()["data"]["subscription_plan"]
    assert plan["name"] == NEW_PLAN_NAME
    assert float(plan["price"]) == NEW_PLAN_PRICE
    assert plan["status"] == "published"


@pytest.mark.asyncio
async def test_jaw_9604_ac_edit_existing_subscription_plan(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] Edit existing subscription plan."""
    target = seed_subscription_plan["published"]
    response = await live_client.put(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "Updated Basic Plan",
            "price": 12.99,
            "billing_cycle": "yearly",
        },
    )
    assert response.status_code == 200
    plan = response.json()["data"]["subscription_plan"]
    assert plan["name"] == "Updated Basic Plan"
    assert float(plan["price"]) == 12.99
    assert plan["billing_cycle"] == "yearly"


@pytest.mark.asyncio
async def test_jaw_9604_ac_remove_subscription_plan(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] Remove subscription plan."""
    target = seed_subscription_plan["published"]
    response = await live_client.delete(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    plan = response.json()["data"]["subscription_plan"]
    assert plan["is_published"] is False
    assert plan["status"] == "unpublished"


@pytest.mark.asyncio
async def test_jaw_9604_ac_return_200_with_subscription_data(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] Return 200 status with subscription data on read/update/delete."""
    target = seed_subscription_plan["draft"]
    list_response = await live_client.get(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert list_response.status_code == 200
    assert list_response.json()["data"]["items"]

    update_response = await live_client.put(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"description": "Updated draft description."},
    )
    assert update_response.status_code == 200
    assert update_response.json()["data"]["subscription_plan"]["id"] == str(target.id)

    delete_response = await live_client.delete(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert delete_response.status_code == 200
    assert delete_response.json()["data"]["subscription_plan"]["status"] == "unpublished"


@pytest.mark.asyncio
async def test_jaw_9604_ac_return_400_for_invalid_subscription_data(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] Return 400/422 for invalid subscription data."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "",
            "price": -1,
            "billing_cycle": "weekly",
        },
    )
    assert response.status_code in (400, 422)
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] in ("VALIDATION_ERROR", "BAD_REQUEST")


@pytest.mark.asyncio
async def test_jaw_9604_ac_return_404_subscription_not_found(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """[JAW-9604 AC] Return 404 status for subscription not found."""
    missing_id = uuid4()
    for method, url, payload in (
        ("put", f"/api/super-admin/subscriptions/{missing_id}", {"name": "Ghost Plan"}),
        ("delete", f"/api/super-admin/subscriptions/{missing_id}", None),
    ):
        if method == "put":
            response = await live_client.put(
                url,
                headers={"Authorization": f"Bearer {admin_access_token}"},
                json=payload,
            )
        else:
            response = await live_client.delete(
                url,
                headers={"Authorization": f"Bearer {admin_access_token}"},
            )
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "SUBSCRIPTION_PLAN_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9604_create_unicode_name_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Edge case: unicode characters in plan name are accepted."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": UNICODE_PLAN_NAME,
            "price": 15.0,
            "billing_cycle": "monthly",
        },
    )
    assert response.status_code == 201
    assert response.json()["data"]["subscription_plan"]["name"] == UNICODE_PLAN_NAME


@pytest.mark.asyncio
async def test_jaw_9604_create_max_length_name_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Edge case: plan name at max length (255) is accepted."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": MAX_LENGTH_NAME,
            "price": 5.0,
            "billing_cycle": "yearly",
        },
    )
    assert response.status_code == 201
    assert len(response.json()["data"]["subscription_plan"]["name"]) == 255


@pytest.mark.asyncio
async def test_jaw_9604_create_whitespace_name_returns_validation_error(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Edge case: whitespace-only name fails validation."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "   ",
            "price": 9.99,
            "billing_cycle": "monthly",
        },
    )
    assert response.status_code in (400, 422)
    assert response.json()["success"] is False


@pytest.mark.asyncio
async def test_jaw_9604_create_duplicate_name_returns_409(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Error case: duplicate subscription plan name returns conflict."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "name": "Basic Plan",
            "price": 1.99,
            "billing_cycle": "monthly",
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUBSCRIPTION_PLAN_ALREADY_EXISTS"


@pytest.mark.asyncio
async def test_jaw_9604_update_billing_cycle_alias_annual(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Edge case: billing_cycle alias 'annual' maps to yearly."""
    target = seed_subscription_plan["published"]
    response = await live_client.put(
        f"/api/super-admin/subscriptions/{target.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"billing_cycle": "annual"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["subscription_plan"]["billing_cycle"] == "yearly"


@pytest.mark.asyncio
async def test_jaw_9604_published_only_filter(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Edge case: published_only=true excludes unpublished plans."""
    response = await live_client.get(
        "/api/super-admin/subscriptions?published_only=true",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(item["is_published"] is True for item in items)
    assert all(item["status"] == "published" for item in items)


@pytest.mark.asyncio
async def test_jaw_9604_list_unauthenticated_returns_401(
    live_client: AsyncClient,
    seed_subscription_plan: dict,
) -> None:
    """Auth: GET without Bearer token returns 401."""
    response = await live_client.get("/api/super-admin/subscriptions")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9604_create_unauthenticated_returns_401(
    live_client: AsyncClient,
    seed_subscription_plan: dict,
) -> None:
    """Auth: POST without Bearer token returns 401."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        json={"name": "No Auth Plan", "price": 1.0, "billing_cycle": "monthly"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9604_expired_token_returns_401(
    live_client: AsyncClient,
    expired_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Auth: expired JWT returns 401."""
    response = await live_client.get(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9604_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Auth: regular user cannot access subscription management."""
    response = await live_client.get(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_jaw_9604_viewer_returns_403(
    live_client: AsyncClient,
    viewer_access_token: str,
    seed_subscription_plan: dict,
) -> None:
    """Auth: viewer role cannot modify subscriptions."""
    response = await live_client.post(
        "/api/super-admin/subscriptions",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
        json={"name": "Viewer Plan", "price": 3.0, "billing_cycle": "monthly"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
