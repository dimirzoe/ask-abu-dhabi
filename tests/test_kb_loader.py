"""Tests for the FRESH → STALE → BASELINE knowledge-base fallback chain."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from core.config import Settings
from core.exceptions import KnowledgeBaseError
from core.kb_loader import load_knowledge_base
from core.schema import KBStatus

BASELINE = Path(__file__).parents[1] / "data" / "baseline_knowledge_base.json"


def _write_kb(path: Path, generated_at: str) -> None:
    raw = json.loads(BASELINE.read_text(encoding="utf-8"))
    raw["generated_at"] = generated_at
    path.write_text(json.dumps(raw), encoding="utf-8")


def _settings(tmp_path: Path, kb_name: str = "kb.json") -> Settings:
    return Settings(
        kb_path=str(tmp_path / kb_name),
        kb_baseline_path=str(BASELINE),
        kb_stale_after_hours=168,
        analytics_db_path=str(tmp_path / "a.db"),
    )


def test_fresh_kb(tmp_path):
    settings = _settings(tmp_path)
    _write_kb(Path(settings.kb_path), datetime.now(timezone.utc).isoformat())
    attractions, status = load_knowledge_base(settings)
    assert status is KBStatus.FRESH
    assert len(attractions) == 12


def test_stale_kb(tmp_path):
    settings = _settings(tmp_path)
    old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    _write_kb(Path(settings.kb_path), old)
    _, status = load_knowledge_base(settings)
    assert status is KBStatus.STALE


def test_baseline_when_active_missing(tmp_path):
    settings = _settings(tmp_path)  # no active KB written
    attractions, status = load_knowledge_base(settings)
    assert status is KBStatus.BASELINE
    assert "zayed_mosque" in attractions


def test_baseline_when_active_corrupt(tmp_path):
    settings = _settings(tmp_path)
    Path(settings.kb_path).write_text("{ not valid json", encoding="utf-8")
    _, status = load_knowledge_base(settings)
    assert status is KBStatus.BASELINE


def test_failed_when_no_kb_available(tmp_path):
    settings = Settings(
        kb_path=str(tmp_path / "missing.json"),
        kb_baseline_path=str(tmp_path / "also_missing.json"),
        analytics_db_path=str(tmp_path / "a.db"),
    )
    with pytest.raises(KnowledgeBaseError):
        load_knowledge_base(settings)
