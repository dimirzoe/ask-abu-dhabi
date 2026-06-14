"""Shared pytest fixtures. Everything here is offline and deterministic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.analytics import AnalyticsStore
from core.config import Settings
from core.schema import Attraction
from providers.base import LLMProvider

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "firecrawl_responses"
BASELINE_KB = Path(__file__).parents[1] / "data" / "baseline_knowledge_base.json"


@pytest.fixture
def firecrawl_fixture():
    """Return a loader that reads a named Firecrawl response fixture."""

    def _load(name: str) -> dict:
        return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))

    return _load


@pytest.fixture
def baseline_attractions() -> dict[str, Attraction]:
    """Load the bundled baseline KB as validated Attraction models."""
    raw = json.loads(BASELINE_KB.read_text(encoding="utf-8"))
    return {
        key: Attraction.model_validate(value)
        for key, value in raw["attractions"].items()
    }


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Provide isolated settings pointing KB/analytics at a temp directory."""
    return Settings(
        llm_provider="openrouter",
        openrouter_api_key="test-key",
        gemini_api_key="test-key",
        firecrawl_api_key="test-key",
        kb_path=str(tmp_path / "knowledge_base.json"),
        kb_baseline_path=str(BASELINE_KB),
        analytics_db_path=str(tmp_path / "analytics.db"),
        etl_min_valid_sources=8,
    )


@pytest.fixture
def analytics(tmp_path: Path) -> AnalyticsStore:
    """Provide an isolated analytics store backed by a temp database."""
    return AnalyticsStore(str(tmp_path / "analytics.db"))


class StubProvider(LLMProvider):
    """A deterministic provider that records the last prompts it received."""

    name = "stub"

    def __init__(self, reply: str = "## 1. Direct Answer\nStub reply.") -> None:
        self.reply = reply
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None

    def generate(self, *, system_prompt: str, user_prompt: str, settings) -> str:
        """Record prompts and return the canned reply."""
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        return self.reply


@pytest.fixture
def stub_provider() -> StubProvider:
    """Provide a stub LLM provider."""
    return StubProvider()
