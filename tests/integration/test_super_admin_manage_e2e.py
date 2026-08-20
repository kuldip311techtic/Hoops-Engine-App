"""Gap-filling e2e tests for Super Admin org, support, and user APIs.

Covers edge cases (unicode, max length, empty input), extra auth (expired JWT,
wrong role), and data-integrity paths not already asserted in the primary
integration modules. Uses the shared PostgreSQL fixtures in tests/conftest.py.
"""

from datetime import timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token
from app.models.super_admin import SuperAdmin
from app.models.support_request import SupportRequest
from tests.conftest import TEST_USER_DEFINITIONS


def _auth_header(token: str) -> dict[str, str]:
    """Return an Authorization bearer header."""
    return {"Authorization": f"Bearer {token}"}


def _user_password() -> str:
    """Reuse the seeded admin persona password (env-overridable)."""
    import os

    return os.environ.get("TEST_USER_PASSWORD") or str(
        TEST_USER_DEFINITIONS["admin"]["password"]
    )


def _org_payload(**overrides: object) -> dict:
    """Build a valid organization write payload."""
    data: dict = {
        "name": "Edge Academy",
        "email": "edge@academy.example",
        "phone_number": "+1-555-0200",
        "address": "1 Main Street",
        "description": "Edge-case organization.",
        "status": "active",
    }
    data.update(overrides)
    return data


async def _seed_support(
    db_session: AsyncSession,
    **overrides: object,
) -> SupportRequest:
    """Insert a support request for subsequent HTTP calls."""
    values: dict = {
        "user_id": uuid4(),
        "user_name": "Edge Player",
        "request": "Need help with my drills.",
        "response": None,
        "status": "open",
    }
    values.update(overrides)
    row = SupportRequest(**values)
    db_session.add(row)
    await db_session.commit()
    await db_session.refresh(row)
    return row


# ---------------------------------------------------------------------------
# JAW-9414 organizations — edge / error / auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_org_unicode_name_and_address(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Unicode name and address should persist on create and list."""
    headers = _auth_header(auth_tokens["admin"])
    response = await client.post(
        "/api/organizations",
        headers=headers,
        json=_org_payload(
            name="Hoops 篮球 Academy é",
            email="unicode-org@example.com",
            address="Calle José 12, São Paulo",
        ),
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Hoops 篮球 Academy é"
    listed = await client.get("/api/organizations", headers=headers)
    assert listed.json()["data"]["items"][0]["address"] == "Calle José 12, São Paulo"


@pytest.mark.asyncio
async def test_org_name_at_max_length_255(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """A 255-character organization name is accepted."""
    name = "A" * 255
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_org_payload(name=name, email="maxlen@example.com"),
    )
    assert response.status_code == 201
    assert response.json()["name"] == name


@pytest.mark.asyncio
async def test_org_name_over_max_length_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """A 256-character organization name returns 422 VALIDATION_ERROR."""
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_org_payload(name="A" * 256, email="toolong@example.com"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_org_empty_name_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Empty name is rejected with field-level validation details."""
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_org_payload(name=""),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    fields = [item["field"] for item in response.json()["error"]["details"]]
    assert any("name" in field for field in fields)


@pytest.mark.asyncio
async def test_org_phone_over_max_length_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Phone numbers longer than 50 characters return 422."""
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_org_payload(phone_number="1" * 51),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_org_address_over_max_length_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Addresses longer than 500 characters return 422."""
    response = await client.post(
        "/api/organizations",
        headers=_auth_header(auth_tokens["admin"]),
        json=_org_payload(address="x" * 501),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_org_pagination_page_size(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """page_size=1 should return one item and total=2."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post(
        "/api/organizations",
        headers=headers,
        json=_org_payload(name="Alpha Org", email="alpha@example.com"),
    )
    await client.post(
        "/api/organizations",
        headers=headers,
        json=_org_payload(name="Beta Org", email="beta@example.com"),
    )
    response = await client.get(
        "/api/organizations",
        headers=headers,
        params={"page": 1, "page_size": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["page"] == 1
    assert body["data"]["page_size"] == 1
    assert body["data"]["total"] == 2
    assert len(body["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_org_delete_not_found_404(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """DELETE against an unknown organization id returns 404."""
    response = await client.delete(
        f"/api/organizations/{uuid4()}",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORGANIZATION_NOT_FOUND"


@pytest.mark.asyncio
async def test_org_expired_token_401(
    client: AsyncClient,
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """An expired JWT must not list organizations."""
    admin = next(a for a in seeded_super_admins if a.email == "admin@test.com")
    token = create_access_token(
        subject=str(admin.id),
        claims={"email": admin.email, "role": "super_admin"},
        expires_delta=timedelta(seconds=-30),
    )
    response = await client.get(
        "/api/organizations",
        headers=_auth_header(token),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_org_viewer_persona_can_list(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Viewer persona is a Super Admin and can read organizations."""
    response = await client.get(
        "/api/organizations",
        headers=_auth_header(auth_tokens["viewer"]),
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


# ---------------------------------------------------------------------------
# JAW-9417 support requests — edge / error / auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_support_unicode_user_name_and_request(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """List should return unicode user names and request text."""
    await _seed_support(
        db_session,
        user_name="José 李",
        request="Não consigo entrar — 登录失败",
    )
    response = await client.get(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
    )
    assert response.status_code == 200
    item = response.json()["data"]["items"][0]
    assert item["name"] == "José 李"
    assert "登录失败" in item["request"]


@pytest.mark.asyncio
async def test_support_response_at_max_length_4000(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """A 4000-character response is accepted."""
    row = await _seed_support(db_session)
    reply = "R" * 4000
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={"id": str(row.id), "response": reply},
    )
    assert response.status_code == 200
    assert len(response.json()["support_request"]["response"]) == 4000


@pytest.mark.asyncio
async def test_support_response_over_max_length_422(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """A 4001-character response returns 422 VALIDATION_ERROR."""
    row = await _seed_support(db_session)
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={"id": str(row.id), "response": "R" * 4001},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_support_empty_response_string_422(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_tokens: dict[str, str],
) -> None:
    """An empty response string is invalid."""
    row = await _seed_support(db_session)
    response = await client.post(
        "/api/support-requests",
        headers=_auth_header(auth_tokens["admin"]),
        json={"id": str(row.id), "response": ""},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_support_expired_token_401(
    client: AsyncClient,
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """Expired JWT cannot list support requests."""
    admin = next(a for a in seeded_super_admins if a.email == "admin@test.com")
    token = create_access_token(
        subject=str(admin.id),
        claims={"email": admin.email, "role": "super_admin"},
        expires_delta=timedelta(seconds=-30),
    )
    response = await client.get(
        "/api/support-requests",
        headers=_auth_header(token),
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_support_inactive_admin_401(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Inactive Super Admin cannot close support requests."""
    response = await client.delete(
        f"/api/support-requests/{uuid4()}",
        headers=_auth_header(auth_tokens["inactive"]),
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_support_wrong_role_403(
    client: AsyncClient,
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """A coach-role JWT cannot list support requests."""
    admin = seeded_super_admins[0]
    token = create_access_token(
        subject=str(admin.id),
        claims={"email": admin.email, "role": "coach"},
    )
    response = await client.get(
        "/api/support-requests",
        headers=_auth_header(token),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_FAILED"


# ---------------------------------------------------------------------------
# JAW-9415 users — edge / error / auth
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_user_unicode_name(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Unicode first/last names should round-trip on create."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "first_name": "José",
            "last_name": "García",
            "email": "jose.garcia@example.com",
            "role": "player",
            "password": _user_password(),
        },
    )
    assert response.status_code == 201
    assert response.json()["name"] == "José García"
    assert response.json()["data"]["first_name"] == "José"


@pytest.mark.asyncio
async def test_user_first_name_over_max_length_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """first_name longer than 100 characters returns 422."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "first_name": "J" * 101,
            "last_name": "Coach",
            "email": "longname@example.com",
            "role": "coach",
            "password": _user_password(),
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_user_invalid_role_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Roles outside coach/player/organization_admin return 422."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "first_name": "Pat",
            "last_name": "Admin",
            "email": "pat.admin@example.com",
            "role": "super_admin",
            "password": _user_password(),
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_user_missing_name_fields_422(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Create without first_name/last_name or name returns 422."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["admin"]),
        json={
            "email": "noname@example.com",
            "role": "coach",
            "password": _user_password(),
        },
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_user_pagination_page_size(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """User list pagination should honor page_size."""
    headers = _auth_header(auth_tokens["admin"])
    await client.post(
        "/api/users",
        headers=headers,
        json={
            "name": "Alpha Coach",
            "email": "alpha.coach@example.com",
            "role": "coach",
            "password": _user_password(),
        },
    )
    await client.post(
        "/api/users",
        headers=headers,
        json={
            "name": "Beta Player",
            "email": "beta.player@example.com",
            "role": "player",
            "password": _user_password(),
        },
    )
    response = await client.get(
        "/api/users",
        headers=headers,
        params={"page": 1, "page_size": 1},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] == 2
    assert body["data"]["page_size"] == 1
    assert len(body["data"]["items"]) == 1


@pytest.mark.asyncio
async def test_user_expired_token_401(
    client: AsyncClient,
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """Expired JWT cannot list users."""
    admin = next(a for a in seeded_super_admins if a.email == "admin@test.com")
    token = create_access_token(
        subject=str(admin.id),
        claims={"email": admin.email, "role": "super_admin"},
        expires_delta=timedelta(seconds=-30),
    )
    response = await client.get("/api/users", headers=_auth_header(token))
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"


@pytest.mark.asyncio
async def test_user_wrong_role_403(
    client: AsyncClient,
    seeded_super_admins: list[SuperAdmin],
) -> None:
    """A player-role JWT cannot create users."""
    admin = seeded_super_admins[0]
    token = create_access_token(
        subject=str(admin.id),
        claims={"email": admin.email, "role": "player"},
    )
    response = await client.post(
        "/api/users",
        headers=_auth_header(token),
        json={
            "name": "Blocked User",
            "email": "blocked@example.com",
            "role": "coach",
            "password": _user_password(),
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_FAILED"


@pytest.mark.asyncio
async def test_regular_persona_can_create_user(
    client: AsyncClient,
    auth_tokens: dict[str, str],
) -> None:
    """Secondary Super Admin persona (user) can add a coach."""
    response = await client.post(
        "/api/users",
        headers=_auth_header(auth_tokens["user"]),
        json={
            "name": "Casey Coach",
            "email": "casey.coach@example.com",
            "role": "coach",
            "password": _user_password(),
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "casey.coach@example.com"
