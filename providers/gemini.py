"""Google Gemini LLM provider (generateContent REST API)."""

from __future__ import annotations

import requests

from core.config import Settings
from core.exceptions import LLMError
from providers.base import LLMProvider
from providers.retry import post_with_retries


class GeminiProvider(LLMProvider):
    """Provider backed by the Gemini ``generateContent`` endpoint."""

    name = "gemini"

    def generate(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        settings: Settings,
    ) -> str:
        """Call Gemini and return the generated text.

        Args:
            system_prompt: System-role instructions (sent via systemInstruction).
            user_prompt: User-role content.
            settings: Application settings supplying key, model, and limits.

        Returns:
            The generated completion text.

        Raises:
            LLMError: On HTTP errors, timeouts, or malformed responses.
        """
        api_key = settings.gemini_api_key
        if not api_key:
            raise LLMError("GEMINI_API_KEY is not configured.")

        base = settings.gemini_base_url.rstrip("/")
        url = f"{base}/models/{settings.gemini_model}:generateContent"
        params = {"key": api_key}
        payload = {
            "systemInstruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": settings.llm_temperature,
                "maxOutputTokens": settings.llm_max_tokens,
            },
        }

        def _post() -> requests.Response:
            return requests.post(
                url,
                params=params,
                json=payload,
                timeout=settings.llm_timeout_seconds,
            )

        try:
            response = post_with_retries(_post, max_retries=settings.llm_max_retries)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as exc:
            raise LLMError(f"Gemini request failed: {exc}") from exc
        except ValueError as exc:  # JSON decode
            raise LLMError(f"Gemini returned invalid JSON: {exc}") from exc

        return self._extract_content(data)

    @staticmethod
    def _extract_content(data: dict) -> str:
        """Extract the text from a Gemini ``generateContent`` payload."""
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected Gemini response shape: {data}") from exc
        if not text.strip():
            raise LLMError("Gemini returned an empty completion.")
        return text.strip()
