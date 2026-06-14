"""Tests for the ETL pipeline: atomic publish and abort-preserves-existing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.exceptions import ETLError
from etl.pipeline import run_pipeline
from etl.sources import SOURCES


class FakeClient:
    """Firecrawl client stub driven by a per-id behaviour map."""

    def __init__(self, valid_payload: dict, failing_ids: set[str]) -> None:
        self._valid = valid_payload
        self._failing = failing_ids
        self._id_by_url = {s.url: s.attraction_id for s in SOURCES}

    def scrape(self, url: str) -> dict:
        attraction_id = self._id_by_url.get(url, "")
        if attraction_id in self._failing:
            raise ETLError(f"simulated scrape failure for {attraction_id}")
        return self._valid


@pytest.fixture
def valid_payload(firecrawl_fixture):
    return firecrawl_fixture("zayed_mosque_valid.json")


def test_pipeline_publishes_when_enough_valid(settings, valid_payload):
    client = FakeClient(valid_payload, failing_ids=set())
    result = run_pipeline(settings, client)
    assert result.published is True
    assert result.valid_count == 12

    kb = json.loads(Path(settings.kb_path).read_text(encoding="utf-8"))
    assert len(kb["attractions"]) == 12
    assert "generated_at" in kb


def test_pipeline_meets_threshold_with_some_failures(settings, valid_payload):
    # 4 failing → 8 valid, exactly meets the threshold of 8.
    failing = {s.attraction_id for s in SOURCES[:4]}
    client = FakeClient(valid_payload, failing_ids=failing)
    result = run_pipeline(settings, client)
    assert result.published is True
    assert result.valid_count == 8


def test_pipeline_aborts_and_preserves_existing(settings, valid_payload):
    # Pre-seed an existing KB that must NOT be overwritten on abort.
    existing = {"generated_at": "2020-01-01T00:00:00+00:00", "attractions": {"old": 1}}
    Path(settings.kb_path).write_text(json.dumps(existing), encoding="utf-8")

    failing = {s.attraction_id for s in SOURCES[:5]}  # only 7 valid < 8
    client = FakeClient(valid_payload, failing_ids=failing)

    with pytest.raises(ETLError):
        run_pipeline(settings, client)

    preserved = json.loads(Path(settings.kb_path).read_text(encoding="utf-8"))
    assert preserved == existing  # untouched


def test_pipeline_atomic_no_tmp_left_behind(settings, valid_payload):
    client = FakeClient(valid_payload, failing_ids=set())
    run_pipeline(settings, client)
    leftovers = list(Path(settings.kb_path).parent.glob("*.tmp"))
    assert leftovers == []


def test_partial_run_backfills_from_baseline(settings, valid_payload):
    # 2 sources fail (like the real u.ae timeouts) -> still 10 fresh, but the
    # published KB must contain all 12 entries via baseline backfill.
    failing = {"visa_info", "culture_etiquette"}
    client = FakeClient(valid_payload, failing_ids=failing)
    result = run_pipeline(settings, client)

    assert result.valid_count == 10
    assert result.published_count == 12

    kb = json.loads(Path(settings.kb_path).read_text(encoding="utf-8"))
    assert set(kb["attractions"]) >= {"visa_info", "culture_etiquette"}
    assert len(kb["attractions"]) == 12


def test_backfilled_entry_keeps_baseline_data(settings, valid_payload):
    failing = {"visa_info"}
    client = FakeClient(valid_payload, failing_ids=failing)
    run_pipeline(settings, client)

    kb = json.loads(Path(settings.kb_path).read_text(encoding="utf-8"))
    baseline = json.loads(Path(settings.kb_baseline_path).read_text(encoding="utf-8"))
    # The failed source's published entry equals its baseline entry.
    assert kb["attractions"]["visa_info"] == baseline["attractions"]["visa_info"]
