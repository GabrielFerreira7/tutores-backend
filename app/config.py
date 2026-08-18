from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Admin auth
    admin_api_key: str = "change-me-admin-key"

    # Used only to build the ready-to-copy <iframe> embed snippet returned to admins.
    frontend_base_url: str = "http://localhost:5173"

    # Persistence
    database_url: str = "sqlite:///./data/tutors.db"

    # LLM (provider selected by the "provider:model" prefix pydantic-ai expects,
    # e.g. "anthropic:claude-haiku-4-5-20251001" or "openai:gpt-4o-mini").
    # The actual API key is read by the provider SDK from its own standard env var
    # (ANTHROPIC_API_KEY / OPENAI_API_KEY), never handled directly by this app.
    llm_model: str = "anthropic:claude-haiku-4-5-20251001"
    llm_timeout_seconds: float = 30.0

    # Knowledge source fetching (agentic tool, not a vector store)
    max_source_fetch_bytes: int = 51_200
    source_fetch_timeout_seconds: float = 8.0
    source_cache_ttl_seconds: int = 3600

    # Conversation
    chat_history_limit: int = 20

    # CORS: comma-separated list of allowed origins, "*" for any (demo only)
    cors_allowed_origins: str = "*"

    # Rate limiting (slowapi syntax, e.g. "20/minute")
    chat_rate_limit: str = "20/minute"

    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        if self.cors_allowed_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
