"""Tests for ETL extraction and transformation against fixtures."""

from __future__ import annotations

from core.schema import Attraction
from etl.extractors import _clean_text, derive_keywords, extract_fields
from etl.sources import SOURCES_BY_ID
from etl.transformers import transform
from etl.validators import validate_attraction


def test_extract_fields_valid(firecrawl_fixture):
    fields = extract_fields(firecrawl_fixture("zayed_mosque_valid.json"))
    assert fields["title"] == "Sheikh Zayed Grand Mosque — Official Site"
    assert fields["url"] == "https://www.szgmc.gov.ae/en/"
    assert fields["fee"]  # "free admission" surfaced
    assert "mosque" in fields["markdown"].lower()


def test_extract_fields_corrupted(firecrawl_fixture):
    fields = extract_fields(firecrawl_fixture("corrupted.json"))
    assert fields["title"] == ""
    assert fields["markdown"] == ""


def test_extract_hours_from_louvre(firecrawl_fixture):
    fields = extract_fields(firecrawl_fixture("louvre_valid.json"))
    assert fields["hours"]  # a time range was detected


def test_derive_keywords_deterministic():
    kws = derive_keywords("Mosque mosque museum museum museum gallery", limit=3)
    assert kws[0] == "museum"  # highest frequency first
    assert len(kws) <= 3


def test_transform_produces_valid_attraction(firecrawl_fixture):
    fields = extract_fields(firecrawl_fixture("louvre_valid.json"))
    attraction = transform(SOURCES_BY_ID["louvre"], fields)
    assert isinstance(attraction, Attraction)
    assert attraction.title == "Louvre Abu Dhabi"
    assert attraction.nudge == SOURCES_BY_ID["louvre"].nudge
    assert len(attraction.keywords) >= 1


def test_transform_uses_defaults_for_missing(firecrawl_fixture):
    fields = extract_fields(firecrawl_fixture("corrupted.json"))
    attraction = transform(SOURCES_BY_ID["zayed_mosque"], fields)
    assert attraction.location == "Check official site for current details"
    assert attraction.duration == "Check official site for current details"


def test_clean_text_strips_markup():
    raw = "[Skip to main content](http://x) ![logo](http://y/l.png) See https://z here"
    cleaned = _clean_text(raw)
    assert "http" not in cleaned
    assert "![" not in cleaned
    assert "](" not in cleaned
    assert "logo" not in cleaned  # image alt text dropped
    assert "skip to main content" not in cleaned.lower()  # boilerplate dropped


def test_noisy_page_yields_no_fake_hours(firecrawl_fixture):
    # The bare "0-94" in the page must NOT be extracted as opening hours.
    fields = extract_fields(firecrawl_fixture("louvre_noisy.json"))
    assert fields["hours"] == ""


def test_noisy_page_fails_validation(firecrawl_fixture):
    # A page that is all navigation chrome must not produce a publishable entry.
    fields = extract_fields(firecrawl_fixture("louvre_noisy.json"))
    attraction = transform(SOURCES_BY_ID["louvre"], fields)
    valid, reasons = validate_attraction(attraction)
    assert valid is False
    assert reasons  # explains why it was rejected
