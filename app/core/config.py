"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration. Secrets must come from the environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/hoopsengine",
        description="Async SQLAlchemy URL using the asyncpg driver.",
    )
    test_database_url: str = Field(
        default="postgresql+asyncpg://user:password@localhost:5432/hoopsengine_test",
        description="Async SQLAlchemy URL for the test database.",
    )
    jwt_secret_key: str = Field(
        default="change-me-to-a-long-random-secret",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
        description="HMAC secret used to sign JWTs.",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    cors_origins: str = Field(default="http://localhost:3000")
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    login_rate_limit: str = Field(default="60/minute")
    dashboard_path: str = Field(default="/dashboard")
    super_admin_email: str | None = Field(default=None)
    super_admin_password: str | None = Field(default=None)
    auth0_domain: str = Field(default="")
    auth0_client_id: str = Field(default="")
    auth0_client_secret: str = Field(default="")
    auth0_webhook_secret: str = Field(default="")
    auth0_sandbox_domain: str = Field(default="")
    billing_webhook_secret: str = Field(default="")
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    ses_from_email: str = Field(default="")

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origin_list(self) -> list[str]:
        """Return CORS origins as a list split from the CSV setting."""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        """Return True when ENVIRONMENT is production."""
        return self.environment.lower() == "production"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_test(self) -> bool:
        """Return True when ENVIRONMENT is test."""
        return self.environment.lower() == "test"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
