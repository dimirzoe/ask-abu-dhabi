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
from core.knowledge_base import rank_attractions
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
    Role,
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

    # Build a short context window (recent user turns + current query) so that
    # follow-ups like "i am from russia" inherit the topic of the prior question
    # for both on-topic gating and attraction matching.
    recent_user_turns = [m.content for m in request.history if m.role == Role.USER]
    context_query = " ".join([*recent_user_turns[-2:], request.query]).strip()

    # Resolve the topic from the NEAREST query that matches: try the current
    # query first, then progressively widen to include one or two prior user
    # turns, stopping at the first window that matches. This prevents a stale
    # earlier topic (e.g. a mosque question) from out-ranking the current one
    # (e.g. a visa follow-up) and mislabelling the official link.
    ranked: list[tuple[str, Attraction, int]] = []
    for text in (
        request.query,
        " ".join([*recent_user_turns[-1:], request.query]),
        " ".join([*recent_user_turns[-2:], request.query]),
    ):
        ranked = rank_attractions(text, attractions)
        if ranked:
            break

    attraction_id = ranked[0][0] if ranked else None
    attraction = ranked[0][1] if ranked else None
    # Primary topic plus one strong secondary (phrase-level match, score >= 3)
    # so cross-topic questions — e.g. "bus to the mosque" — carry both the
    # destination and the transport facts.
    context_attractions = [a for _id, a, _score in ranked[:1]]
    context_attractions += [a for _id, a, score in ranked[1:2] if score >= 3]

    on_topic = is_on_topic(context_query, attractions)

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

    system_prompt = build_system_prompt(
        language, allow_general_knowledge=settings.llm_allow_general_knowledge
    )
    user_prompt = build_user_prompt(
        query=request.query,
        attractions=context_attractions,
        language=language,
        persona=request.persona,
        history=request.history,
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
