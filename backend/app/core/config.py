"""Application configuration via environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """AgentForge application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # --- App ---
    app_name: str = "AgentForge"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"
    api_prefix: str = "/api/v1"

    # --- Database ---
    database_url: str = "postgresql+asyncpg://agentforge:agentforge@localhost:5432/agentforge"
    database_echo: bool = False

    # --- Redis ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Auth / JWT ---
    jwt_secret_key: str = "change-me-in-production-use-a-real-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # --- OAuth ---
    github_client_id: str = ""
    github_client_secret: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    oauth_redirect_base_url: str = "http://localhost:3000"  # Frontend URL for OAuth redirects

    # --- LLM Providers ---
    openai_api_key: str = ""
    openai_base_url: str = ""  # Custom base URL for OpenAI-compatible APIs (e.g., Ollama)
    anthropic_api_key: str = ""
    google_api_key: str = ""

    # --- Storage (MinIO / S3) ---
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "agentforge"
    s3_region: str = "us-east-1"

    # --- Observability ---
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "http://localhost:3001"
    otlp_endpoint: str = ""

    # --- CORS ---
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    # --- Rate Limiting ---
    rate_limit_per_minute: int = 300


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
