"""Provider factory — selects a concrete :class:`LLMProvider` by settings.

Keeps construction logic in one place so the orchestrator and entry points stay
free of provider-specific imports and branching.
"""

from __future__ import annotations

from core.config import Settings
from core.exceptions import ConfigError
from providers.base import LLMProvider
from providers.gemini import GeminiProvider
from providers.openrouter import OpenRouterProvider

_REGISTRY: dict[str, type[LLMProvider]] = {
    "openrouter": OpenRouterProvider,
    "gemini": GeminiProvider,
}


def create_provider(settings: Settings) -> LLMProvider:
    """Instantiate the provider named by ``settings.llm_provider``.

    Args:
        settings: Application settings selecting the provider.

    Returns:
        A ready-to-use :class:`LLMProvider` instance.

    Raises:
        ConfigError: If the configured provider name is unknown.
    """
    provider_cls = _REGISTRY.get(settings.llm_provider)
    if provider_cls is None:
        raise ConfigError(
            f"Unknown LLM provider '{settings.llm_provider}'. "
            f"Supported: {', '.join(sorted(_REGISTRY))}."
        )
    return provider_cls()
