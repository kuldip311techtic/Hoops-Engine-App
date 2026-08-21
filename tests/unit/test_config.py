"""Settings unit tests."""

from app.core.config import Settings, get_settings


def test_settings_reads_jwt_secret_alias() -> None:
    """JWT_SECRET is accepted as an alias for jwt_secret_key."""
    settings = Settings(JWT_SECRET="alias-secret-value")  # type: ignore[call-arg]
    assert settings.jwt_secret_key == "alias-secret-value"


def test_test_database_url_present() -> None:
    """TEST_DATABASE_URL is exposed on settings."""
    settings = get_settings()
    assert "postgresql+asyncpg://" in settings.test_database_url
    assert "postgresql+asyncpg://" in settings.database_url


def test_cors_origin_list_splits_csv() -> None:
    """CORS_ORIGINS CSV is split into a list."""
    settings = Settings(cors_origins="http://a.com, http://b.com")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]
