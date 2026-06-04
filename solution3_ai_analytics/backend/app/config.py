"""Application settings, loaded from environment / .env via pydantic-settings."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default LLM mode when no X-LLM-Mode header is present on a request.
    LLM_MODE: str = "FAKE"

    # Demo tenant (mock auth for now). The pipeline injects this sponsor_id into
    # every query. Second tenant meridian_pharmaceuticals exists for isolation tests.
    DEMO_SPONSOR: str = "helix_therapeutics"

    # Azure OpenAI — only needed for LIVE mode (office laptop). Blank locally.
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_API_VERSION: str = "2024-08-01-preview"
    AZURE_OPENAI_CHAT_DEPLOYMENT: str = "gpt-4.1-mini"
    AZURE_OPENAI_EMBED_DEPLOYMENT: str = "text-embedding-3-small"

    # Database — privileged + read-only roles (see docker-compose init SQL).
    DATABASE_URL: str = (
        "postgresql+asyncpg://solution3_app:app_pw@localhost:55432/solution3"
    )
    APP_READONLY_DATABASE_URL: str = (
        "postgresql+asyncpg://app_readonly:readonly_pw@localhost:55432/solution3"
    )


settings = Settings()
