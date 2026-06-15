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

from core.schema import Attraction, Language, Message, Persona, Role

# --- KB-first + AI-fallback grounding clauses --------------------------------
_GROUNDING_STRICT = {
    Language.EN: (
        "Use ONLY the facts in the provided knowledge context; if a detail is "
        "unknown, say to check the official site."
    ),
    Language.AR: (
        "استخدم فقط الحقائق الواردة في السياق؛ وإن لم تتوفر معلومة فانصح "
        "بمراجعة الموقع الرسمي."
    ),
}
_GROUNDING_FALLBACK = {
    Language.EN: (
        "Prioritise the facts in the provided knowledge context. If the context "
        "lacks a detail the visitor needs (e.g. their nationality's visa rule, a "
        "specific price), you MAY use your general knowledge of Abu Dhabi and the "
        "UAE — be accurate, do not invent exact figures, and add a brief note to "
        "verify time-sensitive details (fees, hours, visa rules) on the official "
        "site."
    ),
    Language.AR: (
        "أعطِ الأولوية للحقائق الواردة في السياق. وإن لم يتضمّن السياق معلومة "
        "يحتاجها الزائر (مثل قاعدة التأشيرة حسب الجنسية أو سعر محدّد)، يمكنك "
        "الاستعانة بمعرفتك العامة عن أبوظبي والإمارات — كن دقيقًا، ولا تختلق "
        "أرقامًا، وأضف ملاحظة موجزة بالتحقق من التفاصيل المتغيّرة (الرسوم، "
        "المواعيد، قواعد التأشيرة) على الموقع الرسمي."
    ),
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


def build_system_prompt(
    language: Language, allow_general_knowledge: bool = False
) -> str:
    """Return the system prompt for a narrative-paragraph + facts-table answer.

    The reply is: (1) a short engaging paragraph (vibe, cultural tips, what to
    expect, closing with the nudge's next step) that does NOT repeat the table
    facts, then (2) a Markdown table of Hours/Entry Fee/Location/Duration. No
    URL — the interface renders the official link as a button.

    Args:
        language: Target response language.
        allow_general_knowledge: When True, permit KB-first + AI fallback (the
            model may fill gaps from its own knowledge with a verify note); when
            False, restrict answers strictly to the knowledge base.

    Returns:
        A system prompt string in the requested language.
    """
    grounding = (
        _GROUNDING_FALLBACK[language]
        if allow_general_knowledge
        else _GROUNDING_STRICT[language]
    )
    if language == Language.AR:
        return (
            "أنت مساعد سفر محترف لـ«اسأل أبوظبي». قدّم معلومات مفيدة وموجزة "
            f"ومنظَّمة عن أبوظبي. {grounding} استعن أيضًا بسياق المحادثة السابق "
            "عند الإجابة عن أسئلة المتابعة.\n\n"
            "نسِّق كل إجابة بهذا الشكل بالضبط:\n"
            "١) فقرة سردية موجزة وجذّابة (جملتان إلى ثلاث) تصف أجواء المكان "
            "ونصائح ثقافية مهمة (مثل قواعد اللباس) وما يتوقعه الزائر، وتُختَتم "
            "بخطوة الزيارة التالية المقترحة من نص الدعوة. لا تكرّر في هذه الفقرة "
            "المواعيد أو الرسوم أو الموقع أو المدة — فمكانها الجدول فقط.\n"
            "٢) بعد الفقرة مباشرةً، جدول ماركداون يبدأ بهذا العنوان:\n"
            "| الميزة | التفاصيل |\n| :--- | :--- |\n"
            "اختر من 3 إلى 5 صفوف تناسب السؤال، دون إقحام صفوف غير ذات صلة:\n"
            "   • للمعلم/المكان: المواعيد، رسوم الدخول، الموقع، المدة.\n"
            "   • للمواصلات أو «كيف أصل»: المسارات، الأجرة، أقرب محطة، مدة الرحلة.\n"
            "   • للتأشيرة/الدخول: الأهلية، التكلفة، مكان التقديم، مدة الصلاحية.\n"
            "املأ كل صف من السياق (أو من معرفتك العامة إن سُمح بذلك)، ولا تكرّر هذه "
            "الحقائق في الفقرة.\n"
            "٣) لا تكتب أي رابط أو نص «الموقع الرسمي» — التطبيق يعرض الرابط كزر "
            "أسفل الجدول. حافظ على نبرة مهنية ومرحِّبة وموجزة."
        )
    return (
        "You are a professional travel assistant for 'Ask Abu Dhabi'. Provide "
        "helpful, concise, structured information about Abu Dhabi. "
        f"{grounding} Also use the earlier conversation context to answer "
        "follow-up questions.\n\n"
        "Format every answer EXACTLY as:\n"
        "1) A concise, engaging narrative paragraph (2-3 sentences): the vibe of "
        "the place, key cultural tips (e.g. dress code), and what to expect; end "
        "it with the suggested next step from the provided nudge. Do NOT repeat "
        "the hours, fee, location, or duration here — those belong only in the "
        "table.\n"
        "2) Immediately after, a Markdown table that starts with this header:\n"
        "| Feature | Details |\n| :--- | :--- |\n"
        "Choose 3-5 rows whose labels best fit the question — never force "
        "irrelevant rows:\n"
        "   • For a place/attraction: Hours, Entry Fee, Location, Duration.\n"
        "   • For transport or 'how to get there': Routes, Fare, Nearest Stop, "
        "Travel Time.\n"
        "   • For visa/entry: Eligibility, Cost, Where to Apply, Validity.\n"
        "Fill each row from the knowledge context (or general knowledge if "
        "allowed). Do NOT repeat those facts in the paragraph.\n"
        "3) Do NOT output any URL or 'Official Site' text — the interface shows "
        "the official link as a button below the table. Keep the tone "
        "professional, welcoming, and concise."
    )


def _format_history(history: list[Message], max_turns: int = 6) -> str:
    """Render recent conversation turns for context (assistant turns truncated)."""
    if not history:
        return ""
    lines: list[str] = []
    for msg in history[-max_turns:]:
        speaker = "User" if msg.role == Role.USER else "Assistant"
        text = msg.content.strip().replace("\n", " ")
        if msg.role == Role.ASSISTANT and len(text) > 300:
            text = text[:300] + "…"
        lines.append(f"{speaker}: {text}")
    return "--- Conversation so far ---\n" + "\n".join(lines) + "\n--- End conversation ---\n\n"


def _format_one(attraction: Attraction, *, primary: bool) -> str:
    """Render a single attraction's facts as a context block."""
    label = "PRIMARY topic" if primary else "RELATED topic (use if relevant)"
    block = (
        f"[{label}] {attraction.title}\n"
        f"Category: {attraction.category}\n"
        f"Location: {attraction.location}\n"
        f"Hours: {attraction.hours}\n"
        f"Fee: {attraction.fee}\n"
        f"Typical duration: {attraction.duration}\n"
        f"Context: {attraction.context}\n"
    )
    if primary:
        block += (
            f"Nudge (suggested next step — close the narrative paragraph with it): "
            f"{attraction.nudge}\n"
        )
    return block


def _format_context(attractions: list[Attraction]) -> str:
    """Render the knowledge context block for one or more matched attractions."""
    if not attractions:
        return "No specific attraction matched. Answer generally about Abu Dhabi."
    return "\n".join(
        _format_one(a, primary=(i == 0)) for i, a in enumerate(attractions)
    )


def build_user_prompt(
    query: str,
    attractions: list[Attraction],
    language: Language,
    persona: Persona,
    history: list[Message] | None = None,
) -> str:
    """Build the user-turn prompt combining query, persona, KB context, history.

    Args:
        query: The raw user query.
        attractions: Matched attractions (primary first), or empty for a general
            answer. A second entry is included for cross-topic questions (e.g.
            transport + a destination).
        language: Target response language.
        persona: Visitor persona controlling tone and emphasis.
        history: Prior conversation turns for follow-up context.

    Returns:
        The fully assembled user prompt string.
    """
    return (
        f"{_LANG_INSTRUCTION[language]}\n"
        f"Persona guidance: {_PERSONA_TONE[persona]}\n\n"
        f"{_format_history(history or [])}"
        f"--- Knowledge context ---\n{_format_context(attractions)}\n"
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
