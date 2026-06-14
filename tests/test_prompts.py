"""Tests for prompt construction and the off-topic redirect."""

from __future__ import annotations

from core.prompts import (
    build_system_prompt,
    build_user_prompt,
    off_topic_message,
)
from core.schema import Language, Persona


def test_system_prompt_en_has_four_sections():
    prompt = build_system_prompt(Language.EN)
    assert "1. Direct Answer" in prompt
    assert "2. Key Info (Hours · Fee · Location · Duration)" in prompt
    assert "3. Official Link" in prompt
    assert "4. What's Next" in prompt


def test_system_prompt_ar_is_arabic():
    prompt = build_system_prompt(Language.AR)
    assert "الإجابة المباشرة" in prompt


def test_user_prompt_includes_nudge_verbatim(baseline_attractions):
    attraction = baseline_attractions["zayed_mosque"]
    prompt = build_user_prompt(
        "When does it open?",
        attraction,
        Language.EN,
        Persona.FAMILY,
    )
    assert attraction.nudge in prompt
    assert "family" in prompt.lower()


def test_user_prompt_without_attraction(baseline_attractions):
    prompt = build_user_prompt("general question", None, Language.EN, Persona.BUSINESS)
    assert "No specific attraction matched" in prompt


def test_off_topic_message_languages():
    assert "Abu Dhabi" in off_topic_message(Language.EN)
    assert "أبوظبي" in off_topic_message(Language.AR)
