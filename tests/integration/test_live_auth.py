"""Live PostgreSQL integration tests for Super Admin login (JAW-9470)."""

from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import create_access_token
from app.exceptions import ConflictError
from app.models.super_admin import SuperAdmin
from app.repositories.subscription_repository import SubscriptionRepository
from app.repositories.super_admin_repository import SuperAdminRepository
from app.services.auth_service import AuthService
from app.services.billing_service import BillingService
from tests.conftest import (
    ADMIN_EMAIL,
    ADMIN_PASSWORD,
    INACTIVE_EMAIL,
    INACTIVE_PASSWORD,
    NEW_USER_EMAIL,
    NEW_USER_PASSWORD,
    USER_EMAIL,
    USER_PASSWORD,
    VIEWER_EMAIL,
    VIEWER_PASSWORD,
)


async def test_super_admin_login_with_email_and_password(client) -> None:
    """JAW-9470: Super Admin can log in with email and password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Login successful"
    data = body["data"]
    assert data["email"] == ADMIN_EMAIL
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["error"] is None
    assert data["subscription"]["has_access"] is True


async def test_legacy_login_path_returns_tokens(client) -> None:
    """Frontend alias POST /api/auth/login hits the same handler."""
    response = await client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


async def test_login_returns_dashboard_redirect(client, settings) -> None:
    """JAW-9470: successful login tells the FE to go to the dashboard."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["redirect_to"] == settings.dashboard_path
    assert data["redirect_to"] == "/dashboard"
    assert "dashboard" in data["description"].lower()
    assert response.status_code != 302


async def test_login_incorrect_credentials_error(client) -> None:
    """JAW-9470: wrong password returns a generic INVALID_CREDENTIALS error."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "WrongPass1!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Invalid email or password"
    assert ADMIN_EMAIL not in body["message"]


async def test_login_unknown_email_same_message(client) -> None:
    """Unknown email uses the same 401 copy (no account enumeration)."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": NEW_USER_EMAIL, "password": NEW_USER_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_requires_valid_email_and_password(client) -> None:
    """JAW-9470: invalid email format is a 422 on the email field."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    fields = {item["field"] for item in body["error"]["details"]}
    assert "email" in fields


async def test_login_empty_body_matches_disabled_button(client) -> None:
    """JAW-9470: empty form is rejected (FE disables the button until filled)."""
    response = await client.post("/api/v1/auth/login", json={})
    assert response.status_code == 422
    fields = {item["field"] for item in response.json()["error"]["details"]}
    assert "email" in fields
    assert "password" in fields


async def test_login_empty_string_password(client) -> None:
    """Empty password is a validation error."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ""},
    )
    assert response.status_code == 422
    fields = {item["field"] for item in response.json()["error"]["details"]}
    assert "password" in fields


async def test_login_plus_tag_email_does_not_match_admin(client) -> None:
    """Plus-tagged email is valid format but is a different account."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin+tag@test.com", "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_login_max_length_password_rejected(client) -> None:
    """Oversized wrong password still returns INVALID_CREDENTIALS, not 500."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": "x" * 512},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_login_does_not_echo_password(client) -> None:
    """Successful login payload never includes the password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    dumped = response.text.lower()
    assert ADMIN_PASSWORD.lower() not in dumped
    assert "hashed_password" not in dumped


async def test_regular_user_login(client) -> None:
    """Second Super Admin (regular fixture) can authenticate."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": USER_EMAIL, "password": USER_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == USER_EMAIL


async def test_viewer_user_login(client) -> None:
    """Viewer fixture is a Super Admin row and can log in."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": VIEWER_EMAIL, "password": VIEWER_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == VIEWER_EMAIL


async def test_inactive_user_password_login_succeeds(client) -> None:
    """No is_active column: inactive fixture can still log in with password."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": INACTIVE_EMAIL, "password": INACTIVE_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == INACTIVE_EMAIL


async def test_new_user_cannot_login(client, new_user) -> None:
    """New user is not in the database and cannot log in."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": new_user["email"], "password": new_user["password"]},
    )
    assert response.status_code == 401


async def test_refresh_success(client, admin_login) -> None:
    """A valid refresh token issues a new access token."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": admin_login["refresh_token"]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]
    assert response.json()["data"]["email"] == ADMIN_EMAIL


async def test_refresh_invalid_token(client) -> None:
    """Garbage refresh tokens are 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-a-token"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] in {
        "INVALID_REFRESH_TOKEN",
        "UNAUTHORIZED",
    }


async def test_refresh_rejects_access_token(client, admin_login) -> None:
    """Access tokens cannot be used on the refresh endpoint."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": admin_login["access_token"]},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_REFRESH_TOKEN"


async def test_change_password_missing_bearer_401(client) -> None:
    """Change-password requires a Bearer access token."""
    response = await client.post(
        "/api/v1/auth/change-password",
        json={"current_password": ADMIN_PASSWORD, "new_password": "NewSecure1!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] in {
        "UNAUTHORIZED",
        "INVALID_ACCESS_TOKEN",
    }


async def test_change_password_wrong_current(client, admin_headers) -> None:
    """Wrong current password is INVALID_CREDENTIALS."""
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"current_password": "NopeNope1!", "new_password": "NewSecure1!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


async def test_change_password_short_new_422(client, admin_headers) -> None:
    """New password shorter than 8 characters is a validation error."""
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"current_password": ADMIN_PASSWORD, "new_password": "short"},
    )
    assert response.status_code == 422
    fields = {item["field"] for item in response.json()["error"]["details"]}
    assert "new_password" in fields


async def test_change_password_revokes_other_devices(client, admin_login) -> None:
    """JAW-9470: password change bumps token_version; old refresh is revoked."""
    old_refresh = admin_login["refresh_token"]
    response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {admin_login['access_token']}"},
        json={"current_password": ADMIN_PASSWORD, "new_password": "NewSecure1!"},
    )
    assert response.status_code == 200
    new_data = response.json()["data"]
    assert new_data["access_token"]
    assert new_data["access_token"] != admin_login["access_token"]

    stale = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert stale.status_code == 401
    assert stale.json()["error"]["code"] == "SESSION_REVOKED"

    fresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": new_data["refresh_token"]},
    )
    assert fresh.status_code == 200


async def test_expired_access_token_rejected(client, db_session) -> None:
    """Expired JWT on change-password is 401."""
    result = await db_session.execute(
        select(SuperAdmin).where(SuperAdmin.email == ADMIN_EMAIL)
    )
    admin = result.scalar_one()
    settings = get_settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(admin.id),
            "type": "access",
            "token_version": int(admin.token_version),
            "role": "super_admin",
            "email": admin.email,
            "iat": int((now - timedelta(hours=2)).timestamp()),
            "exp": int((now - timedelta(hours=1)).timestamp()),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": ADMIN_PASSWORD, "new_password": "NewSecure1!"},
    )
    assert response.status_code == 401


async def test_stale_token_version_rejected(client, db_session) -> None:
    """Access token with token_version 0 is rejected for inactive fixture."""
    result = await db_session.execute(
        select(SuperAdmin).where(SuperAdmin.email == INACTIVE_EMAIL)
    )
    admin = result.scalar_one()
    token = create_access_token(
        str(admin.id),
        extra_claims={
            "role": "super_admin",
            "token_version": 0,
            "email": admin.email,
        },
    )
    response = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "current_password": INACTIVE_PASSWORD,
            "new_password": "NewSecure1!",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "SESSION_REVOKED"


async def test_register_duplicate_email(db_session) -> None:
    """JAW-9470: registering an existing email raises EMAIL_ALREADY_EXISTS."""
    service = AuthService(
        repository=SuperAdminRepository(db_session),
        billing_service=BillingService(SubscriptionRepository(db_session)),
        settings=get_settings(),
    )
    with pytest.raises(ConflictError) as exc_info:
        await service.register(ADMIN_EMAIL, ADMIN_PASSWORD)
    assert exc_info.value.code == "EMAIL_ALREADY_EXISTS"
    assert exc_info.value.status_code == 409
    assert "already exists" in exc_info.value.message.lower()


async def test_register_new_user_then_login(client, db_session, new_user) -> None:
    """A new email can be registered in the service layer then log in."""
    service = AuthService(
        repository=SuperAdminRepository(db_session),
        billing_service=BillingService(SubscriptionRepository(db_session)),
        settings=get_settings(),
    )
    created = await service.register(new_user["email"], new_user["password"])
    await db_session.commit()
    assert str(created.email) == NEW_USER_EMAIL
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": new_user["email"], "password": new_user["password"]},
    )
    assert response.status_code == 200
    assert response.json()["data"]["email"] == NEW_USER_EMAIL
