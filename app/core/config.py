"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from the process environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    database_url: str = Field(
        ...,
        description="Async SQLAlchemy URL (postgresql+asyncpg://...)",
    )
    test_database_url: str = Field(
        ...,
        description="Async SQLAlchemy URL used by integration tests",
    )
    redis_url: str = Field(
        default="redis://127.0.0.1:6379/0",
        description="Redis URL for rate-limit storage",
    )
    environment: str = Field(default="development")
    secret_key: str = Field(...)
    jwt_secret_key: str = Field(
        ...,
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
        description="HMAC secret used to sign OAuth2/JWT tokens",
    )
    jwt_algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)
    refresh_token_expire_days: int = Field(default=7)
    auth_strategy: str = Field(default="jwt")
    login_rate_limit: str = Field(default="60/minute")
    log_level: str = Field(default="INFO")
    cors_origins: str = Field(default="http://localhost:3000")
    super_admin_email: str = Field(default="")
    super_admin_password: str = Field(default="")

    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    ses_from_email: str = Field(default="")
    ses_configuration_set: str = Field(default="")

    dashboard_path: str = Field(default="/dashboard")

    auth0_domain: str = Field(default="")
    auth0_client_id: str = Field(default="")
    auth0_client_secret: str = Field(default="")
    auth0_audience: str = Field(default="")
    auth0_webhook_secret: str = Field(default="")
    auth0_environment: str = Field(default="")

    stripe_secret_key: str = Field(default="")
    stripe_webhook_secret: str = Field(default="")
    billing_webhook_secret: str = Field(default="")

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        """Normalize log level to an uppercase logging name."""
        return value.upper()

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse CORS_ORIGINS as a comma-separated list of origins."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_test(self) -> bool:
        """Return True when running under the test environment."""
        return self.environment.lower() in {"test", "testing"}

    @property
    def ses_is_configured(self) -> bool:
        """Return True when SES credentials and a from-address are present."""
        return bool(
            self.aws_access_key_id
            and self.aws_secret_access_key
            and self.ses_from_email
        )

    @property
    def auth0_is_configured(self) -> bool:
        """Return True when Auth0 tenant credentials are present."""
        return bool(self.auth0_domain and self.auth0_client_id and self.auth0_client_secret)

    @property
    def auth0_runtime(self) -> str:
        """Sandbox vs production label for Auth0 (explicit env or app environment)."""
        if self.auth0_environment:
            return self.auth0_environment.lower()
        if self.environment.lower() in {"production", "prod"}:
            return "production"
        return "sandbox"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()
