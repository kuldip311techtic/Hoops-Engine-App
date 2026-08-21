"""Settings unit tests."""

import os
import secrets

from app.core.config import Settings, get_settings


def test_settings_reads_jwt_secret_alias() -> None:
    """JWT_SECRET is accepted as an alias for jwt_secret_key."""
    alias = os.environ.get("TEST_JWT_SECRET_ALIAS") or secrets.token_urlsafe(24)
    settings = Settings.model_validate({"JWT_SECRET": alias})
    assert settings.jwt_secret_key == alias


def test_test_database_url_present() -> None:
    """TEST_DATABASE_URL is exposed on settings."""
    settings = get_settings()
    assert "postgresql+asyncpg://" in settings.test_database_url
    assert "postgresql+asyncpg://" in settings.database_url


def test_cors_origin_list_splits_csv() -> None:
    """CORS_ORIGINS CSV is split into a list."""
    settings = Settings(cors_origins="http://a.com, http://b.com")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]
