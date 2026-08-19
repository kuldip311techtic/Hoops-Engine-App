"""End-to-end Super Admin login tests against a real PostgreSQL test database."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
)
from app.models.super_admin import SuperAdmin


class TestLoginHappyPath:
    """Successful authentication scenarios."""

    @pytest.mark.asyncio
    async def test_super_admin_login_via_api_login(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """JAW-9419: Super Admin can log in with email and password (POST /api/login)."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"], "password": admin["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["message"] == "Login successful."
        assert body["data"]["token"]
        assert body["data"]["email"] == admin["email"]
        assert body["data"]["token_type"] == "bearer"
        assert body["data"]["expires_in"] > 0

    @pytest.mark.asyncio
    async def test_super_admin_login_via_v1_route(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Login succeeds on versioned route POST /api/v1/auth/login."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": admin["email"], "password": admin["password"]},
        )
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert "token" in response.json()["data"]

    @pytest.mark.asyncio
    async def test_login_response_includes_dashboard_redirect_description(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """JAW-9419: Success payload supports FE dashboard redirect (description + token)."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"], "password": admin["password"]},
        )
        body = response.json()
        assert "dashboard" in body["description"].lower()
        assert body["data"]["token"]

    @pytest.mark.asyncio
    async def test_secondary_super_admin_can_login(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """A second active Super Admin account can authenticate."""
        user = test_users["user"]
        response = await client.post(
            "/api/login",
            json={"email": user["email"], "password": user["password"]},
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == user["email"]


class TestLoginEdgeCases:
    """Boundary and normalization behavior."""

    @pytest.mark.asyncio
    async def test_login_email_case_insensitive(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Email lookup is case-insensitive."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"].upper(), "password": admin["password"]},
        )
        assert response.status_code == 200
        assert response.json()["data"]["email"] == admin["email"]

    @pytest.mark.asyncio
    async def test_login_password_with_special_characters(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Passwords with special characters verify correctly."""
        viewer = test_users["viewer"]
        response = await client.post(
            "/api/login",
            json={"email": viewer["email"], "password": viewer["password"]},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_login_email_with_leading_trailing_whitespace_normalized(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Repository strips whitespace from submitted email."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={
                "email": f"  {admin['email']}  ",
                "password": admin["password"],
            },
        )
        assert response.status_code == 200


class TestLoginErrorCases:
    """Failure responses with frontend-friendly envelopes."""

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """JAW-9419: Incorrect credentials return UI-safe error message."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"], "password": "WrongPassword!"},
        )
        assert response.status_code == 401
        body = response.json()
        assert body["success"] is False
        assert body["message"] == "Invalid email or password."
        assert body["error"]["code"] == "AUTHENTICATION_FAILED"

    @pytest.mark.asyncio
    async def test_login_unknown_email_returns_401(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Unknown email returns same generic error (no enumeration)."""
        new_user = test_users["new"]
        response = await client.post(
            "/api/login",
            json={"email": new_user["email"], "password": new_user["password"]},
        )
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "AUTHENTICATION_FAILED"

    @pytest.mark.asyncio
    async def test_login_inactive_super_admin_returns_401(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Inactive Super Admin cannot authenticate."""
        inactive = test_users["inactive"]
        response = await client.post(
            "/api/login",
            json={"email": inactive["email"], "password": inactive["password"]},
        )
        assert response.status_code == 401
        assert response.json()["message"] == "Invalid email or password."

    @pytest.mark.asyncio
    async def test_login_empty_password_returns_422(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """JAW-9419: Login requires valid password (empty rejected)."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"], "password": ""},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["details"]

    @pytest.mark.asyncio
    async def test_login_invalid_email_format_returns_422(
        self, client: AsyncClient
    ) -> None:
        """JAW-9419: Login requires valid email format."""
        response = await client.post(
            "/api/login",
            json={"email": "not-an-email", "password": "password123"},
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    @pytest.mark.asyncio
    async def test_login_missing_password_field_returns_422(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Missing password field triggers validation error."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"]},
        )
        assert response.status_code == 422


class TestJwtAuth:
    """JWT issuance and validation behavior (JAW-9404 auth skeleton)."""

    @pytest.mark.asyncio
    async def test_login_jwt_contains_super_admin_role(
        self, client: AsyncClient, test_users: dict
    ) -> None:
        """Issued JWT includes role=super_admin claim."""
        admin = test_users["admin"]
        response = await client.post(
            "/api/login",
            json={"email": admin["email"], "password": admin["password"]},
        )
        token = response.json()["data"]["token"]
        payload = decode_access_token(token)
        assert payload["role"] == "super_admin"
        assert payload["email"] == admin["email"]
        assert "sub" in payload

    @pytest.mark.asyncio
    async def test_expired_jwt_token_is_rejected(self, test_users: dict) -> None:
        """Expired tokens raise InvalidTokenError on decode."""
        admin = test_users["admin"]
        token = create_access_token(
            subject="test-subject",
            claims={"email": admin["email"], "role": "super_admin"},
            expires_delta=timedelta(seconds=-1),
        )
        with pytest.raises(InvalidTokenError):
            decode_access_token(token)

    @pytest.mark.asyncio
    async def test_tampered_jwt_token_is_rejected(self, auth_tokens: dict) -> None:
        """Tampered JWT signature is rejected."""
        token = auth_tokens["admin"]
        tampered = token[:-6] + "xxxxxx"
        with pytest.raises(InvalidTokenError):
            decode_access_token(tampered)

    @pytest.mark.asyncio
    async def test_auth_token_fixture_matches_login(
        self, client: AsyncClient, test_users: dict, auth_tokens: dict
    ) -> None:
        """Auth token fixture produces decodable JWT for admin user."""
        payload = decode_access_token(auth_tokens["admin"])
        assert payload["email"] == test_users["admin"]["email"]


class TestDataIntegrity:
    """Database constraint and persistence checks."""

    @pytest.mark.asyncio
    async def test_duplicate_super_admin_email_rejected(
        self, db_session, test_users: dict
    ) -> None:
        """Unique email constraint prevents duplicate Super Admin rows."""
        from sqlalchemy.exc import IntegrityError

        from app.core.security import hash_password

        duplicate = SuperAdmin(
            email=test_users["admin"]["email"],
            hashed_password=hash_password("AnotherPass123!"),
            is_active=True,
        )
        db_session.add(duplicate)
        with pytest.raises(IntegrityError):
            await db_session.commit()
        await db_session.rollback()
