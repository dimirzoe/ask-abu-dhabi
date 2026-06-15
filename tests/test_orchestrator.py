"""Tests for the orchestrator pipeline, including the off-topic LLM bypass."""

from __future__ import annotations

from core.orchestrator import process_query
from core.schema import AskRequest, KBStatus, Language, Message, Persona, Role


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


def test_followup_inherits_topic_from_history(
    settings, baseline_attractions, stub_provider
):
    # "i am from russia" alone is off-topic, but as a follow-up to a visa
    # question it must continue the thread (provider is called, not bypassed).
    history = [
        Message(role=Role.USER, content="Do I need a visa to visit the UAE?"),
        Message(role=Role.ASSISTANT, content="Many nationalities get visa on arrival…"),
    ]
    request = AskRequest(query="i am from russia", history=history)
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
        kb_status=KBStatus.FRESH,
    )
    assert response.off_topic is False
    assert response.attraction_id == "visa_info"
    assert stub_provider.last_user_prompt is not None
    assert "russia" in stub_provider.last_user_prompt.lower()
    # Prior turns are included for context.
    assert "Conversation so far" in stub_provider.last_user_prompt


def test_followup_without_topic_history_still_off_topic(
    settings, baseline_attractions, stub_provider
):
    # A contextless off-topic message with unrelated history stays off-topic.
    history = [Message(role=Role.USER, content="i am from russia")]
    request = AskRequest(query="write me a python function", history=history)
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
    )
    assert response.off_topic is True
    assert stub_provider.last_user_prompt is None


def test_followup_link_follows_current_topic_not_stale(
    settings, baseline_attractions, stub_provider
):
    # After a mosque conversation, a visa follow-up must link to the visa page,
    # not the (keyword-heavy) mosque from earlier turns.
    history = [
        Message(role=Role.USER, content="how can i reach sheikh zayed mosque"),
        Message(role=Role.ASSISTANT, content="The mosque is on Sheikh Rashid St."),
        Message(role=Role.USER, content="Do I need a visa?"),
        Message(role=Role.ASSISTANT, content="Visa requirements vary by nationality."),
    ]
    request = AskRequest(
        query="How long can I stay if i am from russia?", history=history
    )
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
    )
    assert response.attraction_id == "visa_info"
    assert response.official_url == baseline_attractions["visa_info"].url


def test_cross_topic_pulls_in_transport_context(
    settings, baseline_attractions, stub_provider
):
    # "bus to the mosque" should keep the mosque as primary but also surface a
    # transport entry so the model has the facts to answer the bus question.
    request = AskRequest(query="can I take a bus to reach Sheikh Zayed Grand Mosque?")
    response = process_query(
        request,
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
    )
    assert response.attraction_id == "zayed_mosque"
    prompt = stub_provider.last_user_prompt
    assert "PRIMARY topic" in prompt and "RELATED topic" in prompt
    assert "Transport" in prompt  # a transport entry was pulled in


def test_fallback_flag_reaches_system_prompt(
    settings, baseline_attractions, stub_provider
):
    settings.llm_allow_general_knowledge = True
    process_query(
        AskRequest(query="Do I need a visa?"),
        provider=stub_provider,
        settings=settings,
        attractions=baseline_attractions,
    )
    assert "general knowledge" in stub_provider.last_system_prompt.lower()


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
