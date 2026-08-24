"""Integration tests for Super Admin support request APIs (JAW-9605)."""

from uuid import uuid4

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_jaw_9605_list_support_requests_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Super Admin can list support requests."""
    response = await live_client.get(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] >= 2
    items = body["data"]["items"]
    assert len(items) >= 2
    first = items[0]
    assert "id" in first
    assert "status" in first
    assert "description" in first
    assert "request_id" in first


@pytest.mark.asyncio
async def test_jaw_9605_respond_to_support_request_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Super Admin can respond to a support request."""
    open_request = seed_support_request["open"]
    response = await live_client.post(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "request_id": str(open_request.id),
            "response": "Thank you for your inquiry!",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "RESPONDED"
    assert body["data"]["admin_response"] == "Thank you for your inquiry!"


@pytest.mark.asyncio
async def test_jaw_9605_close_support_request_success(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Super Admin can close a support request."""
    open_request = seed_support_request["open"]
    response = await live_client.put(
        f"/api/super-admin/support-requests/{open_request.id}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "CLOSED"
    assert body["data"]["closed_at"] is not None


@pytest.mark.asyncio
async def test_jaw_9605_respond_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Responding to unknown request returns 404."""
    response = await live_client.post(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "request_id": str(uuid4()),
            "response": "Thank you for your inquiry!",
        },
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9605_close_not_found_returns_404(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Closing unknown request returns 404."""
    response = await live_client.put(
        f"/api/super-admin/support-requests/{uuid4()}",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_jaw_9605_non_admin_returns_403(
    live_client: AsyncClient,
    user_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Non-admin users cannot access support request APIs."""
    response = await live_client.get(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {user_access_token}"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_jaw_9605_respond_to_closed_returns_400(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Cannot respond to an already closed support request."""
    closed_request = seed_support_request["closed"]
    response = await live_client.post(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={
            "request_id": str(closed_request.id),
            "response": "Too late",
        },
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "SUPPORT_REQUEST_CLOSED"

@pytest.mark.asyncio
async def test_jaw_9605_list_missing_token_returns_401(
    live_client: AsyncClient,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Missing Bearer token returns 401."""
    response = await live_client.get("/api/super-admin/support-requests")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9605_list_expired_token_returns_401(
    live_client: AsyncClient,
    expired_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Expired Bearer token returns 401."""
    response = await live_client.get(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {expired_access_token}"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_jaw_9605_list_filter_open_status(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Edge case: filter support requests by OPEN status."""
    response = await live_client.get(
        "/api/super-admin/support-requests?status=OPEN",
        headers={"Authorization": f"Bearer {admin_access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    for item in body["data"]["items"]:
        assert item["status"] == "OPEN"


@pytest.mark.asyncio
async def test_jaw_9605_respond_empty_response_returns_422(
    live_client: AsyncClient,
    admin_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Edge case: whitespace-only response returns 422."""
    open_request = seed_support_request["open"]
    response = await live_client.post(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {admin_access_token}"},
        json={"request_id": str(open_request.id), "response": "   "},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_jaw_9605_viewer_cannot_list_returns_403(
    live_client: AsyncClient,
    viewer_access_token: str,
    seed_support_request: dict[str, object],
) -> None:
    """[JAW-9605] Viewer role cannot access support request APIs."""
    response = await live_client.get(
        "/api/super-admin/support-requests",
        headers={"Authorization": f"Bearer {viewer_access_token}"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
