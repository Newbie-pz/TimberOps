"""Environment-backed application configuration."""

from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings loaded from environment variables or a local .env file."""

    database_url: str | None = Field(default=None, validation_alias="DATABASE_URL")
    app_env: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias="APP_ENV",
    )
    app_name: str = Field(
        default="TimberOps backend",
        validation_alias="APP_NAME",
    )
    debug: bool = Field(default=False, validation_alias="DEBUG")
    enable_api_docs: bool = Field(
        default=True,
        validation_alias="ENABLE_API_DOCS",
    )
    cors_allowed_origins: str = Field(
        default="",
        validation_alias="CORS_ALLOWED_ORIGINS",
    )
    jwt_secret_key: SecretStr | None = Field(
        default=None,
        validation_alias="JWT_SECRET_KEY",
    )
    jwt_access_token_expire_minutes: int = Field(
        default=60,
        gt=0,
        validation_alias="JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    )
    public_registration_enabled: bool = Field(
        default=False,
        validation_alias="PUBLIC_REGISTRATION_ENABLED",
    )
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
    def validate_runtime_security(self) -> "Settings":
        """Reject unsafe cross-origin and production-only configurations."""
        if self.llm_timeout_seconds >= self.ai_agent_timeout_seconds:
            raise ValueError(
                "LLM_TIMEOUT_SECONDS must be less than "
                "AI_AGENT_TIMEOUT_SECONDS"
            )
        origins = self.get_cors_allowed_origins()
        if "*" in origins:
            raise ValueError("CORS_ALLOWED_ORIGINS must not contain a wildcard")
        for origin in origins:
            parsed = urlsplit(origin)
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path not in {"", "/"}
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must contain only HTTP(S) origins"
                )
        if self.app_env == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if self.database_url:
                hostname = urlsplit(self.database_url).hostname
                if hostname in {"localhost", "127.0.0.1", "::1"}:
                    raise ValueError(
                        "Production DATABASE_URL must use a network service host"
                    )
            if any(
                urlsplit(origin).hostname in {"localhost", "127.0.0.1", "::1"}
                for origin in origins
            ):
                raise ValueError(
                    "Production CORS origins must not use loopback hosts"
                )
        return self

    def get_cors_allowed_origins(self) -> list[str]:
        """Return normalized exact origins; an empty value means same-origin only."""
        configured = [
            origin.strip().rstrip("/")
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]
        if configured or self.app_env != "development":
            return configured
        return ["http://localhost:5173", "http://127.0.0.1:5173"]

    def require_database_url(self) -> str:
        """Return the configured database URL or fail with an actionable error."""
        if not self.database_url:
            raise RuntimeError(
                "DATABASE_URL is required for database operations. "
                "Copy .env.example to .env and configure it first."
            )
        return self.database_url

    def require_jwt_secret_key(self) -> str:
        """Return a non-placeholder JWT key suitable for signing tokens."""
        if self.jwt_secret_key is None:
            raise RuntimeError("JWT_SECRET_KEY is required for authentication")
        secret = self.jwt_secret_key.get_secret_value()
        normalized = secret.strip().lower()
        if (
            len(secret) < 32
            or normalized.startswith(("replace_", "change_me", "your_"))
            or normalized in {"secret", "changeme", "development"}
        ):
            raise RuntimeError(
                "JWT_SECRET_KEY must be replaced with at least 32 random characters"
            )
        return secret


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide immutable settings instance."""
    return Settings()
