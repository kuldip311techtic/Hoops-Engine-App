"""Frontend contract tests for Super Admin login API responses."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import ADMIN_LIVE_EMAIL, ADMIN_LIVE_PASSWORD

pytestmark = pytest.mark.usefixtures("seed_five_users")


@pytest.mark.asyncio
async def test_jaw_9606_fe_login_form_fields_in_openapi(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] OpenAPI documents email and password for the login form."""
    spec = (await live_client.get("/openapi.json")).json()
    login = spec["paths"]["/api/super-admin/login"]["post"]
    schema = login["requestBody"]["content"]["application/json"]["schema"]
    if "$ref" in schema:
        name = schema["$ref"].split("/")[-1]
        props = spec["components"]["schemas"][name]["properties"]
    else:
        props = schema["properties"]
    assert "email" in props
    assert "password" in props


@pytest.mark.asyncio
async def test_jaw_9606_fe_success_payload_has_ui_fields(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Success response includes message, email, description, and data tokens."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": ADMIN_LIVE_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    for key in ("success", "message", "email", "description", "data"):
        assert key in body
    data = body["data"]
    for key in (
        "access_token",
        "token",
        "refresh_token",
        "token_type",
        "expires_in",
        "redirect_to",
        "email",
        "description",
    ):
        assert key in data


@pytest.mark.asyncio
async def test_jaw_9606_fe_error_payload_is_parseable(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Error responses use the standard envelope for UI messaging."""
    response = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": "BadPass1!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert isinstance(body["message"], str)
    assert isinstance(body["description"], str)
    assert body["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_jaw_9606_fe_empty_fields_backend_validation(
    live_client: AsyncClient,
) -> None:
    """[JAW-9606] Backend enforces both fields (mirrors FE disabled-until-filled rule)."""
    empty_email = await live_client.post(
        "/api/super-admin/login",
        json={"email": "", "password": "SomePass1!"},
    )
    assert empty_email.status_code == 400

    empty_password = await live_client.post(
        "/api/super-admin/login",
        json={"email": ADMIN_LIVE_EMAIL, "password": ""},
    )
    assert empty_password.status_code == 400
