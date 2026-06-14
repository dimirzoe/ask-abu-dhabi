"""Abstract LLM provider interface.

Concrete providers (OpenRouter, Gemini) implement :class:`LLMProvider`. The
orchestrator depends only on this abstraction, never on a concrete provider.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.config import Settings


class LLMProvider(ABC):
    """Contract every LLM provider must satisfy."""

    #: Human-readable provider name, used in responses and analytics.
    name: str = "base"

    @abstractmethod
    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: Settings,
    ) -> str:
        """Generate a completion for the given prompts.

        Args:
            system_prompt: System-role instructions.
            user_prompt: User-role content including KB context and the query.
            settings: Application settings (model, temperature, timeout, etc.).

        Returns:
            The model's text completion.

        Raises:
            LLMError: If the request fails or the response cannot be parsed.
        """
        raise NotImplementedError
