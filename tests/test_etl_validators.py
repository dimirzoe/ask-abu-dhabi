"""Tests for ETL validation rules."""

from __future__ import annotations

from core.schema import Attraction
from etl.validators import is_valid, validate_attraction


def _make(**overrides) -> Attraction:
    base = dict(
        title="Louvre Abu Dhabi",
        category="Museum",
        url="https://www.louvreabudhabi.ae/en",
        location="Saadiyat Island",
        hours="10:00 - 18:30",
        fee="AED 63",
        duration="2 hours",
        context="A universal museum on Saadiyat Island with a famous dome.",
        nudge="Pair your visit with neighbouring museums.",
        keywords=["louvre", "museum", "art", "saadiyat"],
        source_url="https://www.louvreabudhabi.ae/en",
        last_updated="2026-01-01",
    )
    base.update(overrides)
    return Attraction.model_validate(base)


def test_valid_attraction_passes():
    valid, reasons = validate_attraction(_make())
    assert valid is True
    assert reasons == []


def test_invalid_url_fails():
    valid, reasons = validate_attraction(_make(url="ftp://nope"))
    assert valid is False
    assert "invalid url" in reasons


def test_short_context_fails():
    valid, reasons = validate_attraction(_make(context="short"))
    assert not valid
    assert "context too short" in reasons


def test_too_few_keywords_fails():
    valid, reasons = validate_attraction(_make(keywords=["one", "two"]))
    assert not valid
    assert "too few keywords" in reasons


def test_is_valid_convenience():
    assert is_valid(_make()) is True
