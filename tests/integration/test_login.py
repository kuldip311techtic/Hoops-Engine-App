"""HTTP tests for Super Admin login and session."""

import uuid
from unittest.mock import MagicMock

from app.api.v1.endpoints.auth import get_auth_service
from app.core.security import hash_password
from app.models.super_admin import SuperAdmin
from app.schemas.auth import SubscriptionAccessData
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService


def _admin(password: str = "securepassword") -> SuperAdmin:
    return SuperAdmin(
        id=uuid.uuid4(),
        email="admin@example.com",
        hashed_password=hash_password(password),
        token_version=0,
    )


class _FakeRepo:
    def __init__(self, admin: SuperAdmin | None) -> None:
        self.admin = admin

    async def get_by_email(self, email: str) -> SuperAdmin | None:
        if self.admin and email.lower() == self.admin.email.lower():
            return self.admin
        return None

    async def get_by_id(self, admin_id):
        if self.admin and self.admin.id == admin_id:
            return self.admin
        return None

    async def update_password(self, admin: SuperAdmin, hashed_password: str) -> SuperAdmin:
        admin.hashed_password = hashed_password
        admin.token_version += 1
        return admin


def _build_service(admin: SuperAdmin | None) -> AuthService:
    billing = MagicMock(spec=BillingService)
    billing.access_for_super_admin.return_value = SubscriptionAccessData(
        status="not_applicable",
        has_access=True,
        access_until=None,
    )
    billing.ensure_access.return_value = None
    from app.core.config import get_settings

    return AuthService(
        repository=_FakeRepo(admin),
        billing_service=billing,
        settings=get_settings(),
    )


async def test_login_success_v1(app, client) -> None:
    """POST /api/v1/auth/login returns tokens and FE fields."""
    app.dependency_overrides[get_auth_service] = lambda: _build_service(_admin())
    try:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "securepassword"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful"
    data = body["data"]
    assert data["email"] == "admin@example.com"
    assert data["error"] is None
    assert data["description"]
    assert data["redirect_to"] == "/dashboard"
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert "password" not in data


async def test_login_success_legacy_api_auth_login(app, client) -> None:
    """Frontend path POST /api/auth/login is mounted."""
    app.dependency_overrides[get_auth_service] = lambda: _build_service(_admin())
    try:
        response = await client.post(
            "/api/auth/login",
            json={"email": "admin@example.com", "password": "securepassword"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["success"] is True


async def test_login_invalid_credentials_401(app, client) -> None:
    """Wrong password returns INVALID_CREDENTIALS."""
    app.dependency_overrides[get_auth_service] = lambda: _build_service(_admin())
    try:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Invalid email or password"


async def test_login_invalid_email_422(client) -> None:
    """Invalid email format is a validation error on the email field."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "securepassword"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    fields = {item["field"] for item in body["error"]["details"]}
    assert "email" in fields


async def test_login_missing_fields_422(client) -> None:
    """Both email and password are required."""
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    fields = {item["field"] for item in response.json()["error"]["details"]}
    assert "email" in fields
    assert "password" in fields


async def test_refresh_success(app, client) -> None:
    """Refresh returns a new token pair."""
    service = _build_service(_admin())
    login = await service.login("admin@example.com", "securepassword")
    app.dependency_overrides[get_auth_service] = lambda: service
    try:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": login.data.refresh_token},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


async def test_refresh_invalid_401(app, client) -> None:
    """Garbage refresh tokens are 401."""
    app.dependency_overrides[get_auth_service] = lambda: _build_service(_admin())
    try:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "not-a-token"},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 401


async def test_login_openapi_documents_email_and_password(client) -> None:
    """Swagger includes email and password on the login request body."""
    spec = (await client.get("/openapi.json")).json()
    schema = spec["components"]["schemas"]["LoginRequest"]
    assert "email" in schema["properties"]
    assert "password" in schema["properties"]
    assert "/api/v1/auth/login" in spec["paths"]
    assert "/api/auth/login" in spec["paths"]


async def test_change_password_requires_auth(client) -> None:
    """Change-password is not public."""
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "securepassword", "new_password": "NewSecure1!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] in {"UNAUTHORIZED", "INVALID_ACCESS_TOKEN"}
