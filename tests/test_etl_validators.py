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


def test_bare_numeric_hours_rejected():
    valid, reasons = validate_attraction(_make(hours="0-94"))
    assert not valid
    assert "hours not a real time" in reasons


def test_markup_artifacts_in_context_rejected():
    bad = "Visit us ![logo](http://x/l.png) and [book here](http://x/book) today now"
    valid, reasons = validate_attraction(_make(context=bad))
    assert not valid
    assert "context contains markup artifacts" in reasons


def test_context_without_prose_rejected():
    # Long enough to pass the length check, but no real words.
    digits = "12 34 56 78 90 11 22 33 44 55 66 77 88 99 00 12 34 56 78 90"
    valid, reasons = validate_attraction(_make(context=digits))
    assert not valid
    assert "context lacks prose" in reasons


def test_error_page_context_rejected():
    bad = "404 Page was not Found. The page you are trying to access does not exist here."
    valid, reasons = validate_attraction(_make(context=bad))
    assert not valid
    assert "context looks like an error/redirect page" in reasons


def test_real_clock_hours_accepted():
    assert is_valid(_make(hours="09:00 AM - 09:00 PM")) is True


def test_is_valid_convenience():
    assert is_valid(_make()) is True
