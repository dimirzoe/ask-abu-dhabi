"""Tests for language detection and on-topic gating."""

from __future__ import annotations

from core.intent import detect_language, is_on_topic
from core.knowledge_base import match_attraction
from core.schema import Language


def test_detect_language_english(baseline_attractions):
    assert detect_language("What are the opening hours of the Louvre?") is Language.EN


def test_detect_language_arabic():
    assert detect_language("ما هي مواعيد متحف اللوفر؟") is Language.AR


def test_detect_language_forced_overrides_script():
    assert detect_language("ما هي المواعيد؟", forced=Language.EN) is Language.EN


def test_on_topic_via_keyword(baseline_attractions):
    assert is_on_topic("Tell me about the grand mosque", baseline_attractions)


def test_on_topic_via_attraction_match(baseline_attractions):
    assert is_on_topic("louvre tickets please", baseline_attractions)


def test_on_topic_arabic(baseline_attractions):
    assert is_on_topic("أين يقع المسجد؟", baseline_attractions)


def test_off_topic_query(baseline_attractions):
    assert not is_on_topic("Write me a python sorting function", baseline_attractions)


def test_off_topic_general_knowledge(baseline_attractions):
    assert not is_on_topic("What is the capital of France?", baseline_attractions)


def test_partial_keyword_token_does_not_match(baseline_attractions):
    # "world" alone must NOT pull in Yas Island via the "ferrari world" keyword.
    query = "Who won the football World Cup last year?"
    assert match_attraction(query, baseline_attractions) is None
    assert not is_on_topic(query, baseline_attractions)


def test_arabic_query_matches_specific_attraction(baseline_attractions):
    match = match_attraction("ما هي مواعيد مسجد الشيخ زايد الكبير؟", baseline_attractions)
    assert match is not None
    assert match[0] == "zayed_mosque"


def test_arabic_louvre_matches(baseline_attractions):
    match = match_attraction("كم سعر تذكرة متحف اللوفر؟", baseline_attractions)
    assert match is not None
    assert match[0] == "louvre"
