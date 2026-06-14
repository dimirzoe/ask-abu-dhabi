"""Tests for the orchestrator pipeline, including the off-topic LLM bypass."""

from __future__ import annotations

from core.orchestrator import process_query
from core.schema import AskRequest, KBStatus, Language, Persona


def test_on_topic_calls_provider(settings, baseline_attractions, stub_provider, analytics):
    request = AskRequest(query="What are the hours of the grand mosque?")
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
        kb_status=KBStatus.FRESH,
        analytics=analytics,
    )
    assert response.off_topic is False
    assert response.provider == "stub"
    assert response.attraction_id == "zayed_mosque"
    assert response.official_url == baseline_attractions["zayed_mosque"].url
    assert stub_provider.last_user_prompt is not None  # provider was invoked


def test_off_topic_bypasses_provider(settings, baseline_attractions, stub_provider, analytics):
    request = AskRequest(query="Write me a python sorting function")
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
        kb_status=KBStatus.FRESH,
        analytics=analytics,
    )
    assert response.off_topic is True
    assert response.provider == "none"
    assert response.official_url is None
    # The LLM must NOT have been touched.
    assert stub_provider.last_user_prompt is None


def test_arabic_query_returns_arabic(settings, baseline_attractions, stub_provider):
    request = AskRequest(query="ما هي مواعيد المسجد؟")
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
        kb_status=KBStatus.FRESH,
    )
    assert response.language is Language.AR


def test_persona_propagates(settings, baseline_attractions, stub_provider):
    request = AskRequest(query="louvre tickets", persona=Persona.BUSINESS)
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
        kb_status=KBStatus.BASELINE,
    )
    assert response.persona is Persona.BUSINESS
    assert response.kb_status is KBStatus.BASELINE


def test_analytics_logged(settings, baseline_attractions, stub_provider, analytics):
    request = AskRequest(query="corniche walk")
    process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
        analytics=analytics,
    )
    summary = analytics.summary()
    assert summary["total_queries"] == 1
    assert summary["by_provider"].get("stub") == 1
