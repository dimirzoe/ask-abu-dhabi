"""Extraction: pull structured fields out of a raw Firecrawl payload.

The extractor is intentionally tolerant — Firecrawl responses vary, and pages
rarely expose hours/fees in a machine-readable way. Anything not confidently
found is returned as an empty string and filled with a conservative default
during the transform step.
"""

from __future__ import annotations

import re

# Hours must look like a real clock-time range — at least one side carries a
# colon time (10:00) or an am/pm marker. This deliberately rejects bare numeric
# ranges such as "0-94" that leak from CSS/markup dimensions.
_HOURS_RE = re.compile(
    r"\b("
    r"\d{1,2}:\d{2}\s*(?:am|pm)?\s*(?:[-–—]|to)\s*\d{1,2}:\d{2}\s*(?:am|pm)?"
    r"|\d{1,2}\s*(?:am|pm)\s*(?:[-–—]|to)\s*\d{1,2}\s*(?:am|pm)"
    r")\b",
    re.IGNORECASE,
)
_FEE_RE = re.compile(
    r"(free admission|free entry|aed\s*\d+(?:\.\d+)?|\d+\s*aed|dhs?\s*\d+)",
    re.IGNORECASE,
)

# Markdown / HTML artifacts to strip out of scraped prose.
_IMAGE_RE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_URL_RE = re.compile(r"https?://\S+")
_MD_SYMBOLS_RE = re.compile(r"[#>*_`|~%+/\\]+")
_WS_RE = re.compile(r"\s+")
# Noise baked into inline SVG/icon exports (e.g. "Created with Sketch"). These
# multi-word phrases arrive glued to surrounding words ("ShapeCreated"), so no
# \b anchors. The standalone word "icon" is handled separately WITH a boundary
# so we never damage real words like "iconic".
_SVG_NOISE_RE = re.compile(
    r"(created with sketch|combined shape|check mark|clip path|fill rule"
    r"|icon compare)\.?",
    re.IGNORECASE,
)
_ICON_WORD_RE = re.compile(r"\bicon\b", re.IGNORECASE)

# Navigation / chrome phrases that carry no descriptive value.
_BOILERPLATE: tuple[str, ...] = (
    "skip to main content",
    "skip to content",
    "processing...",
    "loading...",
    "back to top",
    "cookie",
    "menu",
    "close",
    "search",
    "newsletter",
    "subscribe",
)


def _clean_text(markdown: str) -> str:
    """Strip markdown/HTML noise and boilerplate, returning readable prose.

    Removes images, link targets (keeping link text), bare URLs, markdown
    symbols, and common navigation phrases, then collapses whitespace.

    Args:
        markdown: Raw scraped markdown.

    Returns:
        Cleaned single-line prose (may be empty if the page was all chrome).
    """
    text = _IMAGE_RE.sub(" ", markdown)
    text = _LINK_RE.sub(r"\1", text)
    text = _URL_RE.sub(" ", text)
    text = _SVG_NOISE_RE.sub(" ", text)
    text = _ICON_WORD_RE.sub(" ", text)
    text = _MD_SYMBOLS_RE.sub(" ", text)
    lowered = text.lower()
    for phrase in _BOILERPLATE:
        if phrase in lowered:
            text = re.sub(re.escape(phrase), " ", text, flags=re.IGNORECASE)
    return _WS_RE.sub(" ", text).strip()


def _unwrap(payload: dict) -> dict:
    """Return the inner data object Firecrawl nests under ``data`` (if present)."""
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def extract_fields(payload: dict) -> dict[str, str]:
    """Extract candidate fields from a Firecrawl scrape payload.

    Args:
        payload: Raw Firecrawl response JSON for one page.

    Returns:
        A dict with keys ``title``, ``markdown`` (raw), ``text`` (cleaned prose),
        ``hours``, ``fee``, ``url``. Missing values are empty strings.
    """
    data = _unwrap(payload)
    metadata = data.get("metadata", {}) if isinstance(data.get("metadata"), dict) else {}
    markdown = data.get("markdown", "") or ""

    title = (metadata.get("title") or metadata.get("ogTitle") or "").strip()
    source_url = (metadata.get("sourceURL") or metadata.get("url") or "").strip()

    hours_match = _HOURS_RE.search(markdown)
    fee_match = _FEE_RE.search(markdown)

    return {
        "title": title,
        "markdown": markdown.strip(),
        "text": _clean_text(markdown),
        "hours": hours_match.group(1).strip() if hours_match else "",
        "fee": fee_match.group(1).strip() if fee_match else "",
        "url": source_url,
    }


def derive_keywords(text: str, limit: int = 8) -> list[str]:
    """Derive up to ``limit`` lowercase keyword tokens from text.

    A simple, dependency-free frequency heuristic over alphabetic tokens with a
    small stopword list. Deterministic for testability.

    Args:
        text: Source text (typically the page title plus context).
        limit: Maximum number of keywords to return.

    Returns:
        A list of distinct lowercase keywords, most frequent first.
    """
    stop = {
        "the", "and", "for", "with", "you", "your", "are", "this", "that",
        "from", "abu", "dhabi", "official", "website", "home", "page", "more",
        "our", "all", "about", "visit", "https", "http", "www", "com",
    }
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    counts: dict[str, int] = {}
    for tok in tokens:
        if tok in stop:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [word for word, _ in ranked[:limit]]
