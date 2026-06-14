"""Prompt construction for EN/AR responses and the static off-topic redirect.

Every LLM answer must follow a strict 4-section Markdown structure so the UI can
render it predictably and the closing nudge is delivered verbatim:

1. Direct Answer
2. Key Info (Hours · Fee · Location · Duration)
3. Official Link
4. What's Next  (the attraction's ``nudge``, verbatim)

EN and AR share the structure but use translated section headers.
"""

from __future__ import annotations

from core.schema import Attraction, Language, Persona

# --- Section headers per language --------------------------------------------
_HEADERS: dict[Language, list[str]] = {
    Language.EN: [
        "1. Direct Answer",
        "2. Key Info (Hours · Fee · Location · Duration)",
        "3. Official Link",
        "4. What's Next",
    ],
    Language.AR: [
        "١. الإجابة المباشرة",
        "٢. معلومات أساسية (المواعيد · الرسوم · الموقع · المدة)",
        "٣. الرابط الرسمي",
        "٤. الخطوة التالية",
    ],
}

# --- Persona tone guidance ----------------------------------------------------
_PERSONA_TONE: dict[Persona, str] = {
    Persona.FIRST_TIME: (
        "The visitor is in Abu Dhabi for the first time. Be welcoming and "
        "orienting; briefly explain context a newcomer would not know."
    ),
    Persona.FAMILY: (
        "The visitor is travelling with family/children. Highlight kid-friendly "
        "aspects, facilities, and practical comfort notes."
    ),
    Persona.BUSINESS: (
        "The visitor is on a business trip with limited time. Be concise and "
        "efficiency-focused; emphasise proximity, timing, and quick visits."
    ),
}

_LANG_INSTRUCTION: dict[Language, str] = {
    Language.EN: "Respond in clear, professional English.",
    Language.AR: "أجب باللغة العربية الفصحى الواضحة والمهنية.",
}


def build_system_prompt(language: Language) -> str:
    """Return the system prompt enforcing the 4-section structure.

    Args:
        language: Target response language.

    Returns:
        A system prompt string in the requested language.
    """
    headers = _HEADERS[language]
    if language == Language.AR:
        return (
            "أنت «اسأل أبوظبي»، مساعد سياحي خبير بإمارة أبوظبي. "
            "استخدم فقط الحقائق الواردة في سياق المعرفة المقدَّم. "
            "إن لم تتوفر المعلومة، انصح بزيارة الموقع الرسمي. "
            "يجب أن يتبع ردك هذا الهيكل بالماركداون وبأربعة أقسام بالضبط:\n"
            f"## {headers[0]}\n## {headers[1]}\n## {headers[2]}\n## {headers[3]}\n"
            "اجعل القسم الرابع مطابقًا تمامًا لنص الدعوة المقدَّم دون تغيير."
        )
    return (
        "You are 'Ask Abu Dhabi', an expert tourism assistant for the Emirate of "
        "Abu Dhabi. Use ONLY the facts in the provided knowledge context. If a "
        "detail is unknown, advise checking the official site. Your reply MUST "
        "follow this exact 4-section Markdown structure:\n"
        f"## {headers[0]}\n## {headers[1]}\n## {headers[2]}\n## {headers[3]}\n"
        "Section 4 must reproduce the provided nudge text verbatim, unchanged."
    )


def _format_context(attraction: Attraction | None) -> str:
    """Render the knowledge context block for the prompt."""
    if attraction is None:
        return "No specific attraction matched. Answer generally about Abu Dhabi."
    return (
        f"Title: {attraction.title}\n"
        f"Category: {attraction.category}\n"
        f"Location: {attraction.location}\n"
        f"Hours: {attraction.hours}\n"
        f"Fee: {attraction.fee}\n"
        f"Typical duration: {attraction.duration}\n"
        f"Official URL: {attraction.url}\n"
        f"Context: {attraction.context}\n"
        f"Nudge (use VERBATIM in section 4): {attraction.nudge}"
    )


def build_user_prompt(
    query: str,
    attraction: Attraction | None,
    language: Language,
    persona: Persona,
) -> str:
    """Build the user-turn prompt combining query, persona, and KB context.

    Args:
        query: The raw user query.
        attraction: Matched attraction, or None for a general answer.
        language: Target response language.
        persona: Visitor persona controlling tone and emphasis.

    Returns:
        The fully assembled user prompt string.
    """
    return (
        f"{_LANG_INSTRUCTION[language]}\n"
        f"Persona guidance: {_PERSONA_TONE[persona]}\n\n"
        f"--- Knowledge context ---\n{_format_context(attraction)}\n"
        f"--- End context ---\n\n"
        f"User question: {query}"
    )


def off_topic_message(language: Language) -> str:
    """Return the static redirect shown for off-topic queries (no LLM call).

    Args:
        language: Target response language.

    Returns:
        A polite, fixed redirect message scoped to Abu Dhabi tourism.
    """
    if language == Language.AR:
        return (
            "أنا «اسأل أبوظبي» وأساعدك في السياحة والمعالم داخل إمارة أبوظبي فقط — "
            "مثل المساجد والمتاحف والشواطئ والمواصلات والتأشيرات. "
            "اطرح سؤالاً متعلقًا بزيارة أبوظبي وسأكون سعيدًا بمساعدتك."
        )
    return (
        "I'm 'Ask Abu Dhabi', and I only help with tourism and attractions within "
        "the Emirate of Abu Dhabi — things like mosques, museums, beaches, "
        "transport, and visas. Please ask something about visiting Abu Dhabi and "
        "I'll be glad to help."
    )
