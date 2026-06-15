"""Transformation: merge extracted fields + source metadata into an Attraction.

Applies conservative defaults ("Check official site for current details") wherever
the extractor could not confidently find a value, and stamps ``last_updated``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from core.schema import Attraction
from etl.extractors import derive_keywords
from etl.sources import Source

_CHECK_OFFICIAL = "Check official site for current details"


def _context_snippet(markdown: str, fallback: str, max_chars: int = 600) -> str:
    """Build a short context blurb from scraped markdown, falling back if empty."""
    cleaned = " ".join(markdown.split())
    if not cleaned:
        return fallback
    return cleaned[:max_chars].rstrip()


def transform(source: Source, fields: dict[str, str]) -> Attraction:
    """Combine a :class:`Source` with extracted fields into an :class:`Attraction`.

    Args:
        source: The static source definition (id, title, category, nudge).
        fields: Output of :func:`etl.extractors.extract_fields`.

    Returns:
        A fully-populated, schema-valid :class:`Attraction`.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = source.title  # Trust curated title over scraped metadata.
    # Use the cleaned prose ("text"), falling back to raw markdown for older
    # callers/fixtures that only provide it.
    context = _context_snippet(
        fields.get("text") or fields.get("markdown", ""),
        fallback=f"{title} — {_CHECK_OFFICIAL}.",
    )
    keyword_seed = f"{title} {source.category} {context}"
    keywords = derive_keywords(keyword_seed) or [title.lower()]

    return Attraction(
        title=title,
        category=source.category,
        url=source.url,
        location=_CHECK_OFFICIAL,
        hours=fields.get("hours") or _CHECK_OFFICIAL,
        fee=fields.get("fee") or _CHECK_OFFICIAL,
        duration=_CHECK_OFFICIAL,
        context=context,
        nudge=source.nudge,
        keywords=keywords,
        source_url=fields.get("url") or source.url,
        last_updated=now,
    )
