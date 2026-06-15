"""Tests for prompt construction and the off-topic redirect."""

from __future__ import annotations

from core.prompts import (
    build_system_prompt,
    build_user_prompt,
    off_topic_message,
)
from core.schema import Language, Persona


def test_system_prompt_en_uses_narrative_plus_table():
    prompt = build_system_prompt(Language.EN)
    assert "| Feature | Details |" in prompt
    assert "Entry Fee" in prompt
    assert "Do NOT repeat" in prompt  # no fact duplication in narrative
    assert "button below the table" in prompt
    # The old rigid numbered headers must be gone.
    assert "## 1. Direct Answer" not in prompt


def test_system_prompt_ar_uses_narrative_plus_table():
    prompt = build_system_prompt(Language.AR)
    assert "اسأل أبوظبي" in prompt
    assert "| الميزة | التفاصيل |" in prompt
    assert "رسوم الدخول" in prompt


def test_user_prompt_includes_nudge_verbatim(baseline_attractions):
    attraction = baseline_attractions["zayed_mosque"]
    prompt = build_user_prompt(
        "When does it open?",
        [attraction],
        Language.EN,
        Persona.FAMILY,
    )
    assert attraction.nudge in prompt
    assert "family" in prompt.lower()


def test_user_prompt_with_two_attractions(baseline_attractions):
    primary = baseline_attractions["zayed_mosque"]
    related = baseline_attractions["public_transport"]
    prompt = build_user_prompt(
        "can I take a bus to the mosque?",
        [primary, related],
        Language.EN,
        Persona.FIRST_TIME,
    )
    assert "PRIMARY topic" in prompt
    assert "RELATED topic" in prompt
    assert related.title in prompt  # transport facts available to the model


def test_user_prompt_without_attraction(baseline_attractions):
    prompt = build_user_prompt("general question", [], Language.EN, Persona.BUSINESS)
    assert "No specific attraction matched" in prompt


def test_off_topic_message_languages():
    assert "Abu Dhabi" in off_topic_message(Language.EN)
    assert "أبوظبي" in off_topic_message(Language.AR)
