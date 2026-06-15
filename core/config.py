"""Application configuration via pydantic-settings.

A single :class:`Settings` object is the only source of truth for configuration.
It is constructed once at the edge (entry points / DI containers) and passed
explicitly into the functions that need it. Never call ``os.getenv`` elsewhere.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from core.exceptions import ConfigError

ProviderName = Literal["openrouter", "gemini"]


class Settings(BaseSettings):
    """Strongly-typed application settings loaded from environment / ``.env``.

    Attributes mirror the keys documented in ``.env.example``. Validation
    failures are surfaced as :class:`~core.exceptions.ConfigError` via
    :func:`load_settings`.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Provider selection ---
    llm_provider: ProviderName = "openrouter"

    # --- OpenRouter ---
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # --- Gemini ---
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"

    # --- Generation parameters ---
    llm_temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    llm_max_tokens: int = Field(default=1024, gt=0, le=8192)
    llm_timeout_seconds: int = Field(default=30, gt=0, le=300)
    llm_max_retries: int = Field(default=3, ge=0, le=6)
    # KB-first + AI fallback: when True, the model may supplement missing KB
    # details from its general knowledge (with a "verify on official site" note).
    # When False, answers are strictly limited to the knowledge base.
    llm_allow_general_knowledge: bool = True

    # --- Knowledge base ---
    kb_path: str = "data/knowledge_base.json"
    kb_baseline_path: str = "data/baseline_knowledge_base.json"
    kb_stale_after_hours: int = Field(default=168, gt=0)

    # --- Analytics ---
    analytics_db_path: str = "data/analytics.db"

    # --- ETL / Firecrawl ---
    firecrawl_api_key: str = ""
    firecrawl_base_url: str = "https://api.firecrawl.dev/v1"
    firecrawl_timeout_seconds: int = Field(default=60, gt=0, le=600)
    etl_min_valid_sources: int = Field(default=8, ge=1, le=12)

    # --- App metadata ---
    app_name: str = "Ask Abu Dhabi"
    log_level: str = "INFO"

    def require_provider_key(self) -> str:
        """Return the API key for the currently selected provider.

        Raises:
            ConfigError: If the selected provider has no API key configured.
        """
        key = (
            self.openrouter_api_key
            if self.llm_provider == "openrouter"
            else self.gemini_api_key
        )
        if not key:
            raise ConfigError(
                f"No API key configured for provider '{self.llm_provider}'. "
                f"Set the corresponding *_API_KEY in your .env file."
            )
        return key


def load_settings() -> Settings:
    """Construct a :class:`Settings` instance, translating validation errors.

    Returns:
        A fully validated settings object.

    Raises:
        ConfigError: If environment values fail validation.
    """
    try:
        return Settings()
    except ValidationError as exc:  # pragma: no cover - defensive
        raise ConfigError(f"Invalid configuration: {exc}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached settings instance.

    Cached purely to avoid re-parsing ``.env`` on every request; the object is
    immutable in practice and is still passed explicitly into business logic.
    """
    return load_settings()
