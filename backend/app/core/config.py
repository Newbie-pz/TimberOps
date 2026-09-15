"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    app_name: str = Field(
        default="TimberOps backend",
        validation_alias="APP_NAME",
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        frozen=True,
    )

    def require_database_url(self) -> str:
        """Return the configured database URL or fail with an actionable error."""
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL is required for database operations. "
                "Copy .env.example to .env and configure it first."
            )
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()
