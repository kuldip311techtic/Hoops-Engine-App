"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DATABASE_URL_PREFIXES = ("DATABASE_URL=", "TEST_DATABASE_URL=")


def normalize_database_url(value: str | None) -> str | None:
    """Strip repeated accidental key prefixes from a database URL string."""
    if value is None or not isinstance(value, str):
        return value
    cleaned = value.strip()
    changed = True
    while changed:
        changed = False
        for prefix in _DATABASE_URL_PREFIXES:
            if cleaned.startswith(prefix):
                cleaned = cleaned.removeprefix(prefix)
                changed = True
    return cleaned


class Settings(BaseSettings):
    """Central application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        ...,
        description="Async PostgreSQL connection URL (postgresql+asyncpg://...).",
    )
    test_database_url: str | None = Field(
        default=None,
        description="Optional test database URL for integration tests.",
    )
    redis_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Redis connection URL for optional distributed services.",
    )
    environment: Literal["development", "staging", "production", "test"] = (
        "development"
    )
    secret_key: str = Field(..., min_length=16, description="General app secret key.")
    jwt_secret_key: str = Field(
        ...,
        min_length=32,
        description="Secret key used to sign JWT access tokens.",
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT signing algorithm.")
    access_token_expire_minutes: int = Field(
        default=30,
        ge=1,
        description="Access token lifetime in minutes.",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        ge=1,
        description="Refresh token lifetime in days (future use).",
    )
    auth_strategy: Literal["jwt"] = Field(
        default="jwt",
        description="Authentication strategy identifier.",
    )
    log_level: str = Field(default="INFO", description="Logging level.")
    cors_origins: str = Field(
        default="http://localhost:3000",
        description="Comma-separated list of allowed CORS origins.",
    )
    super_admin_email: str | None = Field(
        default=None,
        description="Optional bootstrap Super Admin email.",
    )
    super_admin_password: str | None = Field(
        default=None,
        description="Optional bootstrap Super Admin password.",
    )

    @field_validator("database_url", "test_database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str | None) -> str | None:
        """Strip accidental key prefixes and whitespace from database URLs."""
        return normalize_database_url(value)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: str | list[str]) -> str:
        """Normalize CORS origins input to a comma-separated string."""
        if isinstance(value, list):
            return ",".join(value)
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """Return parsed CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Return True when running in production."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
