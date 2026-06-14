"""OpenRouter LLM provider (OpenAI-compatible chat completions API)."""

from __future__ import annotations

import requests

from core.config import Settings
from core.exceptions import LLMError
from providers.base import LLMProvider
from providers.retry import post_with_retries


class OpenRouterProvider(LLMProvider):
    """Provider backed by the OpenRouter chat-completions endpoint."""

    name = "openrouter"

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: Settings,
    ) -> str:
        """Call OpenRouter and return the assistant message content.

        Args:
            system_prompt: System-role instructions.
            user_prompt: User-role content.
            settings: Application settings supplying key, model, and limits.

        Returns:
            The generated completion text.

        Raises:
            LLMError: On HTTP errors, timeouts, or malformed responses.
        """
        api_key = settings.openrouter_api_key
        if not api_key:
            raise LLMError("OPENROUTER_API_KEY is not configured.")

        url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://ask-abu-dhabi.local",
            "X-Title": settings.app_name,
        }
        payload = {
            "model": settings.openrouter_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.llm_temperature,
            "max_tokens": settings.llm_max_tokens,
        }

        def _post() -> requests.Response:
            return requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=settings.llm_timeout_seconds,
            )

        try:
            response = post_with_retries(_post, max_retries=settings.llm_max_retries)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"OpenRouter request failed: {exc}") from exc
        except ValueError as exc:  # JSON decode
            raise LLMError(f"OpenRouter returned invalid JSON: {exc}") from exc

        return self._extract_content(data)

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Extract the message content from an OpenRouter response payload."""
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected OpenRouter response shape: {data}") from exc
        if not isinstance(content, str) or not content.strip():
            raise LLMError("OpenRouter returned an empty completion.")
        return content.strip()
