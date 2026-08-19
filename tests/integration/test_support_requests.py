"""Integration tests for Super Admin support request APIs."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.support_request import SupportRequest


def _auth_header(token: str) -> dict[str, str]:
    """Return an Authorization bearer header."""
    return {"Authorization": f"Bearer {token}"}


async def _seed_request(
    db_session: AsyncSession,
    **overrides: object,
) -> SupportRequest:
    """Insert a support request visible to subsequent API requests."""
    values: dict = {
        "user_id": uuid.uuid4(),
        "user_name": "Jane Player",
        "request": "I cannot log in to my player account.",
        "response": None,
        "status": "open",
    }
    values.update(overrides)
    row = SupportRequest(**values)
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


@pytest.mark.asyncio
async def test_list_support_requests_empty(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """GET /api/support-requests should return an empty paginated list."""
    response = await client.get(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Support requests retrieved."
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0
    assert "id" in body
    assert "name" in body
    assert "description" in body
    assert "status" in body
    assert body["error"] is None


@pytest.mark.asyncio
async def test_list_support_requests(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """List items should include Request ID, user name, date, and status."""
    row = await _seed_request(db_session)
    response = await client.get(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) == 1
    item = items[0]
    assert item["id"] == str(row.id)
    assert item["name"] == "Jane Player"
    assert item["user_name"] == "Jane Player"
    assert item["user_id"] == str(row.user_id)
    assert item["request"] == row.request
    assert item["description"] == row.request
    assert item["status"] == "open"
    assert item["submitted_at"]
    assert item["created_at"]


@pytest.mark.asyncio
async def test_respond_to_support_request(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """POST /api/support-requests should save the Super Admin response."""
    row = await _seed_request(db_session)
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "id": str(row.id),
            "response": "Please try resetting your password.",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Support request updated."
    assert body["description"]
    assert body["status"] == "responded"
    assert body["id"] == str(row.id)
    assert body["name"] == "Jane Player"
    assert body["support_request"]["response"] == (
        "Please try resetting your password."
    )
    assert body["data"]["status"] == "responded"
    assert body["error"] is None


@pytest.mark.asyncio
async def test_respond_invalid_empty_422(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """Blank or whitespace responses should return 422 VALIDATION_ERROR."""
    row = await _seed_request(db_session)
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={"id": str(row.id), "response": "   "},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


@pytest.mark.asyncio
async def test_respond_missing_response_422(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """Omitting the response field should return 422 with field details."""
    row = await _seed_request(db_session)
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={"id": str(row.id)},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_respond_unknown_id_404(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Responding to an unknown id should return 404."""
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "id": str(uuid.uuid4()),
            "response": "We are looking into this.",
        },
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_respond_to_closed_409(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """Responding to a closed request should return 409."""
    row = await _seed_request(db_session, status="closed")
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={"id": str(row.id), "response": "Too late."},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "SUPPORT_REQUEST_CLOSED"


@pytest.mark.asyncio
async def test_close_support_request_confirmation_message(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """DELETE should close the request and return a confirmation message."""
    row = await _seed_request(db_session)
    response = await client.delete(
        f"/api/support-requests/{row.id}",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Support request closed."
    assert body["description"]
    assert body["status"] == "closed"
    assert body["id"] == str(row.id)
    assert body["name"] == "Jane Player"
    assert body["data"]["status"] == "closed"
    listed = await client.get(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert listed.json()["data"]["items"][0]["status"] == "closed"


@pytest.mark.asyncio
async def test_close_unknown_id_404(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Closing an unknown id should return 404."""
    response = await client.delete(
        f"/api/support-requests/{uuid.uuid4()}",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SUPPORT_REQUEST_NOT_FOUND"


@pytest.mark.asyncio
async def test_support_requests_unauthenticated_401(client: AsyncClient) -> None:
    """Missing bearer token should return 401."""
    response = await client.get("/api/support-requests")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_legacy_and_v1_paths_both_work(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """Both /api/support-requests and /api/v1/support-requests should work."""
    await _seed_request(db_session, user_name="Alex Coach")
    headers = _auth_header(auth_tokens["admin"])
    v1 = await client.get("/api/v1/support-requests", headers=headers)
    legacy = await client.get("/api/support-requests", headers=headers)
    assert v1.status_code == 200
    assert legacy.status_code == 200
    assert v1.json()["data"]["total"] == 1
    assert legacy.json()["data"]["items"][0]["name"] == "Alex Coach"


@pytest.mark.asyncio
async def test_support_requests_openapi_documents_respond_body(
    client: AsyncClient,
) -> None:
    """OpenAPI should expose id and response on the respond POST body."""
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/api/support-requests" in schema["paths"]
    post = schema["paths"]["/api/support-requests"]["post"]
    request_body = post["requestBody"]["content"]["application/json"]["schema"]
    assert "$ref" in request_body
    model_name = request_body["$ref"].split("/")[-1]
    properties = schema["components"]["schemas"][model_name]["properties"]
    assert "id" in properties
    assert "response" in properties
    assert "delete" in schema["paths"]["/api/support-requests/{id}"]
