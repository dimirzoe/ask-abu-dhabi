"""Tests for LLM providers and the factory. All HTTP is mocked."""

from __future__ import annotations

import pytest

from core.exceptions import ConfigError, LLMError
from providers.factory import create_provider
from providers.gemini import GeminiProvider
from providers.openrouter import OpenRouterProvider


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.exceptions.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


def test_factory_selects_openrouter(settings):
    settings.llm_provider = "openrouter"
    assert isinstance(create_provider(settings), OpenRouterProvider)


def test_factory_selects_gemini(settings):
    settings.llm_provider = "gemini"
    assert isinstance(create_provider(settings), GeminiProvider)


def test_factory_unknown_provider_raises(settings):
    settings.llm_provider = "nope"  # type: ignore[assignment]
    with pytest.raises(ConfigError):
        create_provider(settings)


def test_openrouter_generate_success(settings, mocker):
    payload = {"choices": [{"message": {"content": "Hello from OpenRouter"}}]}
    mocker.patch("providers.openrouter.requests.post", return_value=_FakeResponse(payload))
    provider = OpenRouterProvider()
    result = provider.generate(
        system_prompt="sys", user_prompt="usr", settings=settings
    )
    assert result == "Hello from OpenRouter"


def test_openrouter_missing_key_raises(settings):
    settings.openrouter_api_key = ""
    with pytest.raises(LLMError):
        OpenRouterProvider().generate(system_prompt="s", user_prompt="u", settings=settings)


def test_openrouter_bad_shape_raises(settings, mocker):
    mocker.patch(
        "providers.openrouter.requests.post",
        return_value=_FakeResponse({"unexpected": True}),
    )
    with pytest.raises(LLMError):
        OpenRouterProvider().generate(system_prompt="s", user_prompt="u", settings=settings)


def test_gemini_generate_success(settings, mocker):
    payload = {"candidates": [{"content": {"parts": [{"text": "Hi from Gemini"}]}}]}
    mocker.patch("providers.gemini.requests.post", return_value=_FakeResponse(payload))
    result = GeminiProvider().generate(
        system_prompt="sys", user_prompt="usr", settings=settings
    )
    assert result == "Hi from Gemini"


def test_gemini_empty_completion_raises(settings, mocker):
    payload = {"candidates": [{"content": {"parts": [{"text": ""}]}}]}
    mocker.patch("providers.gemini.requests.post", return_value=_FakeResponse(payload))
    with pytest.raises(LLMError):
        GeminiProvider().generate(system_prompt="s", user_prompt="u", settings=settings)
