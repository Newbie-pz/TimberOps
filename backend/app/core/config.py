"""Environment-backed application configuration."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    app_name: str = Field(
        default="TimberOps backend",
        validation_alias="APP_NAME",
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")
    ai_enabled: bool = Field(default=False, validation_alias="AI_ENABLED")
    llm_provider: str = Field(default="doubao", validation_alias="LLM_PROVIDER")
    doubao_api_key: str | None = Field(
        default=None,
        validation_alias="DOUBAO_API_KEY",
    )
    doubao_base_url: str | None = Field(
        default=None,
        validation_alias="DOUBAO_BASE_URL",
    )
    doubao_model: str | None = Field(
        default=None,
        validation_alias="DOUBAO_MODEL",
    )
    ai_temperature: float = Field(
        default=0,
        ge=0,
        le=2,
        validation_alias="AI_TEMPERATURE",
    )
    llm_timeout_seconds: float = Field(
        default=25,
        gt=0,
        validation_alias="LLM_TIMEOUT_SECONDS",
    )
    llm_max_retries: int = Field(
        default=1,
        ge=0,
        le=1,
        validation_alias="LLM_MAX_RETRIES",
    )
    ai_agent_timeout_seconds: float = Field(
        default=30,
        gt=0,
        validation_alias="AI_AGENT_TIMEOUT_SECONDS",
    )
    mcp_host: str = Field(default="127.0.0.1", validation_alias="MCP_HOST")
    mcp_port: int = Field(default=8001, ge=1, le=65535, validation_alias="MCP_PORT")

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        frozen=True,
    )

    @model_validator(mode="after")
    def validate_ai_timeout_budget(self) -> "Settings":
        """Keep the provider deadline inside the Agent's overall deadline."""
        if self.llm_timeout_seconds >= self.ai_agent_timeout_seconds:
            raise ValueError(
                "LLM_TIMEOUT_SECONDS must be less than "
                "AI_AGENT_TIMEOUT_SECONDS"
            )
        return self

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
