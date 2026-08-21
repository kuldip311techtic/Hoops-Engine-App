"""Live PostgreSQL integration tests for Super Admin login and session APIs (JAW-9470)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from jose import jwt
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import ForbiddenError
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.services.auth_service import AuthService
from tests.conftest import (
    LIVE_ADMIN_EMAIL,
    LIVE_ADMIN_PASSWORD,
    LIVE_INACTIVE_EMAIL,
    LIVE_INACTIVE_PASSWORD,
    LIVE_NEW_EMAIL,
    LIVE_NEW_PASSWORD,
    LIVE_USER_EMAIL,
    LIVE_USER_PASSWORD,
    LIVE_VIEWER_EMAIL,
    LIVE_VIEWER_PASSWORD,
)


@pytest.mark.asyncio
async def test_super_admin_can_login_with_email_and_password(
    db_client: AsyncClient,
) -> None:
    """JAW-9470: Super Admin logs in with email and password against real rows."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": LIVE_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["email"] == LIVE_ADMIN_EMAIL
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]
    assert body["data"]["refresh_token"]
    assert LIVE_ADMIN_PASSWORD not in response.text


@pytest.mark.asyncio
async def test_super_admin_login_alias_path(db_client: AsyncClient) -> None:
    """Ticket path POST /api/auth/login authenticates the seeded Super Admin."""
    response = await db_client.post(
        "/api/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": LIVE_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_login_redirects_spa_to_dashboard(db_client: AsyncClient) -> None:
    """JAW-9470: success returns redirect_to dashboard, never HTTP 302."""
    response = await db_client.post(
        "/api/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": LIVE_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    assert response.status_code != 302
    assert response.json()["data"]["redirect_to"] == "/dashboard"
    assert "Redirecting to the dashboard" in response.json()["description"]


@pytest.mark.asyncio
async def test_incorrect_credentials_return_generic_error(
    db_client: AsyncClient,
) -> None:
    """JAW-9470: wrong password returns INVALID_CREDENTIALS without leaking which field."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": "WrongPass1!"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_CREDENTIALS"
    assert body["message"] == "Incorrect email or password"
    assert body["description"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_unknown_email_uses_same_error(db_client: AsyncClient) -> None:
    """Unknown email must not be distinguishable from a bad password."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@test.com", "password": LIVE_ADMIN_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_requires_valid_email_and_password(db_client: AsyncClient) -> None:
    """JAW-9470: malformed email is 422 VALIDATION_ERROR."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "not-an-email", "password": "x"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert any("email" in str(item.get("field")) for item in body["error"]["details"])


@pytest.mark.asyncio
async def test_empty_login_body_matches_disabled_button(db_client: AsyncClient) -> None:
    """JAW-9470: empty form (button disabled until both fields filled) is 422."""
    response = await db_client.post("/api/auth/login", json={})
    assert response.status_code == 422
    fields = {item["field"] for item in response.json()["error"]["details"]}
    assert "email" in fields
    assert "password" in fields


@pytest.mark.asyncio
async def test_login_empty_string_password(db_client: AsyncClient) -> None:
    """Empty password is rejected by schema validation."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": ""},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_login_unicode_email_local_part(db_client: AsyncClient) -> None:
    """Unicode local-part that is not a valid email is 422."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": "админ@test.com", "password": LIVE_ADMIN_PASSWORD},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_max_length_password_still_unauthorized(
    db_client: AsyncClient,
) -> None:
    """Oversized wrong password is still a credentials error, not a 500."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": "Aa1!" + ("x" * 4000)},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_regular_user_cannot_use_super_admin_login(
    db_client: AsyncClient,
) -> None:
    """USER role is rejected with the same 401 as a bad password."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_USER_EMAIL, "password": LIVE_USER_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_viewer_cannot_use_super_admin_login(db_client: AsyncClient) -> None:
    """VIEWER role cannot authenticate on the Super Admin login route."""
    response = await db_client.post(
        "/api/auth/login",
        json={"email": LIVE_VIEWER_EMAIL, "password": LIVE_VIEWER_PASSWORD},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(db_client: AsyncClient) -> None:
    """Deactivated account cannot log in on the Super Admin route."""
    response = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_INACTIVE_EMAIL, "password": LIVE_INACTIVE_PASSWORD},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_change_password_missing_token_401(db_client: AsyncClient) -> None:
    """Protected change-password without Authorization is 401."""
    response = await db_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": LIVE_ADMIN_PASSWORD, "new_password": "BrandNew1!"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["error"]["code"] in ("UNAUTHORIZED",)


@pytest.mark.asyncio
async def test_change_password_revokes_other_device_refresh(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
    seeded_users: dict[str, User],
) -> None:
    """JAW-9470: password change increments token_version; old refresh is rejected."""
    login = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": LIVE_ADMIN_PASSWORD},
    )
    old_refresh = login.json()["data"]["refresh_token"]
    changed = await db_client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={
            "current_password": LIVE_ADMIN_PASSWORD,
            "new_password": "BrandNew1!",
        },
    )
    assert changed.status_code == 200
    assert changed.json()["success"] is True
    stale = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_refresh},
    )
    assert stale.status_code == 401
    again = await db_client.post(
        "/api/v1/auth/login",
        json={"email": LIVE_ADMIN_EMAIL, "password": "BrandNew1!"},
    )
    assert again.status_code == 200
    assert again.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_change_password_wrong_current(
    db_client: AsyncClient,
    admin_headers: dict[str, str],
) -> None:
    """Wrong current_password is 401 INVALID_CREDENTIALS."""
    response = await db_client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"current_password": "NopeNope1!", "new_password": "BrandNew1!"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_register_duplicate_email_clear_error(db_client: AsyncClient) -> None:
    """JAW-9470: registering an existing email returns 409 EMAIL_ALREADY_EXISTS."""
    response = await db_client.post(
        "/api/v1/auth/register",
        json={"email": LIVE_ADMIN_EMAIL, "password": LIVE_NEW_PASSWORD},
    )
    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "EMAIL_ALREADY_EXISTS"
    assert "already" in body["message"].lower() or "in use" in body["message"].lower()


@pytest.mark.asyncio
async def test_register_new_user_not_yet_in_database(db_client: AsyncClient) -> None:
    """New user persona can register and receive bearer tokens."""
    response = await db_client.post(
        "/api/v1/auth/register",
        json={"email": LIVE_NEW_EMAIL, "password": LIVE_NEW_PASSWORD},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["email"] == LIVE_NEW_EMAIL
    assert body["data"]["access_token"]
    assert body["data"]["redirect_to"] == "/dashboard"


@pytest.mark.asyncio
async def test_register_weak_password_rejected(db_client: AsyncClient) -> None:
    """Password policy rejects a lowercase-only secret."""
    response = await db_client.post(
        "/api/v1/auth/register",
        json={"email": "weakpass@test.com", "password": "short"},
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_register_empty_email(db_client: AsyncClient) -> None:
    """Empty email on register is 422."""
    response = await db_client.post(
        "/api/v1/auth/register",
        json={"email": "", "password": LIVE_NEW_PASSWORD},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_refresh_garbage_token(db_client: AsyncClient) -> None:
    """Non-JWT refresh payload is 401."""
    response = await db_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not-valid"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_expired_access_token_rejected(
    db_client: AsyncClient,
    seeded_users: dict[str, User],
) -> None:
    """Expired access JWT cannot call change-password."""
    settings = get_settings()
    token = jwt.encode(
        {
            "sub": str(seeded_users["admin"].id),
            "type": "access",
            "ver": seeded_users["admin"].token_version,
            "exp": datetime.now(UTC) - timedelta(minutes=5),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    response = await db_client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_password": LIVE_ADMIN_PASSWORD, "new_password": "BrandNew1!"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_cancelled_subscription_retains_access_until_period_end(
    seeded_users: dict[str, User],
) -> None:
    """JAW-9470: CANCELLED subscription still allows access before current_period_end."""
    user = seeded_users["user"]
    async with AsyncSessionLocal() as session:
        session.add(
            Subscription(
                id=uuid4(),
                user_id=user.id,
                status=SubscriptionStatus.CANCELLED,
                current_period_end=datetime.now(UTC) + timedelta(days=5),
                cancelled_at=datetime.now(UTC),
            )
        )
        await session.commit()
        bound = await session.get(User, user.id)
        from app.repositories.subscription_repository import SubscriptionRepository
        from app.repositories.user_repository import UserRepository

        service = AuthService(UserRepository(session), SubscriptionRepository(session))
        assert bound is not None
        assert await service.has_access(bound) is True
        tokens = await service.login(
            LIVE_USER_EMAIL, LIVE_USER_PASSWORD, require_super_admin=False
        )
        assert tokens.access_token
        assert tokens.redirect_to == "/dashboard"


@pytest.mark.asyncio
async def test_cancelled_subscription_denies_access_after_period_end(
    seeded_users: dict[str, User],
) -> None:
    """Cancelled subscription past current_period_end is denied."""
    user = seeded_users["user"]
    async with AsyncSessionLocal() as session:
        session.add(
            Subscription(
                id=uuid4(),
                user_id=user.id,
                status=SubscriptionStatus.CANCELLED,
                current_period_end=datetime.now(UTC) - timedelta(days=1),
                cancelled_at=datetime.now(UTC) - timedelta(days=10),
            )
        )
        await session.commit()
        from app.repositories.subscription_repository import SubscriptionRepository
        from app.repositories.user_repository import UserRepository

        service = AuthService(UserRepository(session), SubscriptionRepository(session))
        bound = await session.get(User, user.id)
        assert bound is not None
        assert await service.has_access(bound) is False
        with pytest.raises(ForbiddenError) as exc:
            await service.login(
                LIVE_USER_EMAIL, LIVE_USER_PASSWORD, require_super_admin=False
            )
        assert exc.value.code == "SUBSCRIPTION_INACTIVE"


@pytest.mark.asyncio
async def test_duplicate_email_unique_constraint(seeded_users: dict[str, User]) -> None:
    """Second insert of the same email raises IntegrityError."""
    async with AsyncSessionLocal() as session:
        session.add(
            User(
                email=LIVE_ADMIN_EMAIL,
                password_hash=hash_password("OtherPass1!"),
                role=UserRole.USER,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_subscription_fk_rejects_unknown_user(
    seeded_users: dict[str, User],
) -> None:
    """Subscription.user_id must reference users.id."""
    async with AsyncSessionLocal() as session:
        session.add(
            Subscription(
                user_id=uuid4(),
                status=SubscriptionStatus.ACTIVE,
                current_period_end=datetime.now(UTC) + timedelta(days=1),
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


@pytest.mark.asyncio
async def test_subscription_cascade_on_user_delete(
    seeded_users: dict[str, User],
) -> None:
    """Deleting a user removes their subscription row."""
    user = seeded_users["viewer"]
    async with AsyncSessionLocal() as session:
        session.add(
            Subscription(
                user_id=user.id,
                status=SubscriptionStatus.ACTIVE,
                current_period_end=datetime.now(UTC) + timedelta(days=30),
            )
        )
        await session.commit()
        await session.execute(text("DELETE FROM users WHERE email = :e"), {"e": user.email})
        await session.commit()
        remaining = await session.execute(
            text("SELECT count(*) FROM subscriptions WHERE user_id = :id"),
            {"id": user.id},
        )
        assert remaining.scalar_one() == 0


@pytest.mark.asyncio
async def test_seeded_personas_exist_in_postgres(
    seeded_users: dict[str, User],
) -> None:
    """Admin, user, viewer, and inactive are real rows; newuser is absent."""
    assert seeded_users["admin"].role == UserRole.SUPER_ADMIN
    assert seeded_users["user"].role == UserRole.USER
    assert seeded_users["viewer"].role == UserRole.VIEWER
    assert seeded_users["inactive"].is_active is False
    async with AsyncSessionLocal() as session:
        found = await session.execute(
            text("SELECT email FROM users ORDER BY email")
        )
        emails = {row[0] for row in found}
    assert LIVE_ADMIN_EMAIL in emails
    assert LIVE_USER_EMAIL in emails
    assert LIVE_VIEWER_EMAIL in emails
    assert LIVE_INACTIVE_EMAIL in emails
    assert LIVE_NEW_EMAIL not in emails
