"""Query orchestration — the composition root of the request pipeline.

:func:`process_query` is a (near-)pure function: all collaborators are injected.
It performs no I/O of its own beyond delegating to the provided provider and the
optional analytics store.

Pipeline:
    detect_language → match_attraction → log analytics → if off-topic return a
    static response (LLM bypassed) → else build prompt → provider.generate →
    return :class:`AskResponse`.
"""

from __future__ import annotations

from typing import Optional

from core.analytics import AnalyticsStore
from core.config import Settings
from core.intent import detect_language, is_on_topic
from core.knowledge_base import match_attraction
from core.prompts import (
    build_system_prompt,
    build_user_prompt,
    off_topic_message,
)
from core.schema import (
    Attraction,
    AskRequest,
    AskResponse,
    KBStatus,
)
from providers.base import LLMProvider


def process_query(
    request: AskRequest,
    provider: LLMProvider,
    settings: Settings,
    attractions: dict[str, Attraction],
    *,
    kb_status: KBStatus = KBStatus.FRESH,
    analytics: Optional[AnalyticsStore] = None,
) -> AskResponse:
    """Process a single user request end-to-end.

    Args:
        request: The validated inbound request.
        provider: The LLM provider to use for on-topic generation (injected).
        settings: Application settings (injected).
        attractions: Loaded knowledge-base attractions (injected).
        kb_status: Freshness status of the loaded KB, for analytics/response.
        analytics: Optional analytics store; every query is logged when present.

    Returns:
        An :class:`AskResponse`. Off-topic queries bypass the LLM and return a
        static redirect message.

    Raises:
        LLMError: Propagated from the provider when generation fails.
    """
    language = detect_language(request.query, forced=request.language)
    match = match_attraction(request.query, attractions)
    attraction_id = match[0] if match else None
    attraction = match[1] if match else None

    on_topic = is_on_topic(request.query, attractions)

    # --- Off-topic short-circuit: never touch the LLM ---
    if not on_topic:
        if analytics is not None:
            analytics.log_query(
                language=language.value,
                attraction=None,
                persona=request.persona.value,
                provider="none",
                off_topic=True,
                kb_status=kb_status.value,
            )
        return AskResponse(
            answer=off_topic_message(language),
            language=language,
            attraction_id=None,
            attraction_title=None,
            official_url=None,
            persona=request.persona,
            provider="none",
            off_topic=True,
            kb_status=kb_status,
        )

    # --- On-topic: build prompt and call the provider ---
    if analytics is not None:
        analytics.log_query(
            language=language.value,
            attraction=attraction_id,
            persona=request.persona.value,
            provider=provider.name,
            off_topic=False,
            kb_status=kb_status.value,
        )

    system_prompt = build_system_prompt(language)
    user_prompt = build_user_prompt(
        query=request.query,
        attraction=attraction,
        language=language,
        persona=request.persona,
    )
    answer = provider.generate(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        settings=settings,
    )

    return AskResponse(
        answer=answer,
        language=language,
        attraction_id=attraction_id,
        attraction_title=attraction.title if attraction else None,
        official_url=attraction.url if attraction else None,
        persona=request.persona,
        provider=provider.name,
        off_topic=False,
        kb_status=kb_status,
    )
