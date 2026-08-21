"""Auth middleware refresh-flow tests."""

import pytest

from app.core.security import create_access_token, create_refresh_token
from app.exceptions import UnauthorizedError
from app.middleware.auth import is_public_path, refresh_access_token
from app.middleware.logging import header_is_sensitive


def test_refresh_access_token_issues_new_access_token() -> None:
    """A valid refresh token yields a new access token for the same subject."""
    refresh = create_refresh_token("admin-id", extra_claims={"role": "super_admin"})
    access = refresh_access_token(refresh)
    from app.core.security import decode_access_token

    payload = decode_access_token(access)
    assert payload["sub"] == "admin-id"
    assert payload["type"] == "access"
    assert payload["role"] == "super_admin"


def test_refresh_rejects_access_token() -> None:
    """Access tokens cannot be used as refresh tokens."""
    access = create_access_token("admin-id")
    with pytest.raises(UnauthorizedError) as exc_info:
        refresh_access_token(access)
    assert exc_info.value.code == "INVALID_REFRESH_TOKEN"


def test_refresh_rejects_garbage() -> None:
    """Malformed refresh tokens raise UnauthorizedError."""
    with pytest.raises(UnauthorizedError):
        refresh_access_token("not-a-token")


def test_public_paths() -> None:
    """Docs and health are public."""
    assert is_public_path("/api/v1/health") is True
    assert is_public_path("/docs") is True
    assert is_public_path("/api/v1/auth/login") is True
    assert is_public_path("/api/auth/login") is True
    assert is_public_path("/api/v1/auth/change-password") is False


def test_sensitive_headers_redacted() -> None:
    """Authorization headers are treated as sensitive."""
    assert header_is_sensitive("Authorization") is True
    assert header_is_sensitive("Content-Type") is False
