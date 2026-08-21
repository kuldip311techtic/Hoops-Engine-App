"""Settings loading from environment."""

from app.core.config import Settings, get_settings


def test_settings_reads_jwt_secret_key_alias(monkeypatch) -> None:
    """JWT_SECRET is accepted when JWT_SECRET_KEY is absent."""
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "alias-secret")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://u:p@localhost/db",
    )
    monkeypatch.setenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://u:p@localhost/db_test",
    )
    monkeypatch.setenv("SECRET_KEY", "s")
    get_settings.cache_clear()
    settings = Settings()
    assert settings.jwt_secret_key == "alias-secret"
    get_settings.cache_clear()


def test_cors_origin_list_splits_csv() -> None:
    """CORS_ORIGINS is parsed as a list of origins."""
    settings = Settings(
        database_url="postgresql+asyncpg://u:p@localhost/db",
        test_database_url="postgresql+asyncpg://u:p@localhost/db_test",
        secret_key="s",
        jwt_secret_key="k",
        cors_origins="http://localhost:3000, https://app.example.com",
    )
    assert settings.cors_origin_list == [
        "http://localhost:3000",
        "https://app.example.com",
    ]


def test_test_database_url_present(settings) -> None:
    """TEST_DATABASE_URL is required on Settings."""
    assert settings.test_database_url.startswith("postgresql+asyncpg://")
