"""Tests for the transient-error retry helper and provider integration."""

from __future__ import annotations

import pytest
import requests

from core.exceptions import LLMError
from providers.gemini import GeminiProvider
from providers.openrouter import OpenRouterProvider
from providers.retry import post_with_retries


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


def test_retry_recovers_after_transient(monkeypatch):
    calls = {"n": 0}

    def do_post():
        calls["n"] += 1
        return _Resp(503) if calls["n"] < 3 else _Resp(200, {"ok": True})

    resp = post_with_retries(do_post, max_retries=3, sleep=lambda _: None)
    assert resp.status_code == 200
    assert calls["n"] == 3  # two 503s, then success


def test_retry_gives_up_and_returns_last(monkeypatch):
    def do_post():
        return _Resp(503)

    resp = post_with_retries(do_post, max_retries=2, sleep=lambda _: None)
    assert resp.status_code == 503  # exhausted retries, returns last response


def test_openrouter_retries_then_succeeds(settings, mocker):
    settings.llm_max_retries = 3
    payload = {"choices": [{"message": {"content": "Recovered"}}]}
    responses = [_Resp(503), _Resp(200, payload)]
    mocker.patch("providers.openrouter.requests.post", side_effect=responses)
    mocker.patch("providers.retry.time.sleep", lambda _: None)

    result = OpenRouterProvider().generate(
        system_prompt="s", user_prompt="u", settings=settings
    )
    assert result == "Recovered"


def test_gemini_persistent_503_raises_llm_error(settings, mocker):
    settings.llm_max_retries = 2
    mocker.patch("providers.gemini.requests.post", return_value=_Resp(503))
    mocker.patch("providers.retry.time.sleep", lambda _: None)

    with pytest.raises(LLMError):
        GeminiProvider().generate(system_prompt="s", user_prompt="u", settings=settings)
