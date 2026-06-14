"""Extraction: pull structured fields out of a raw Firecrawl payload.

The extractor is intentionally tolerant — Firecrawl responses vary, and pages
rarely expose hours/fees in a machine-readable way. Anything not confidently
found is returned as an empty string and filled with a conservative default
during the transform step.
"""

from __future__ import annotations

import re

# Loose patterns to opportunistically surface common facts from page text.
_HOURS_RE = re.compile(
    r"(\d{1,2}(:\d{2})?\s*(am|pm)?\s*[-–to]+\s*\d{1,2}(:\d{2})?\s*(am|pm)?)",
    re.IGNORECASE,
)
_FEE_RE = re.compile(
    r"(free admission|free entry|aed\s*\d+(\.\d+)?|\d+\s*aed|dhs?\s*\d+)",
    re.IGNORECASE,
)


def _unwrap(payload: dict) -> dict:
    """Return the inner data object Firecrawl nests under ``data`` (if present)."""
    data = payload.get("data")
    return data if isinstance(data, dict) else payload


def extract_fields(payload: dict) -> dict[str, str]:
    """Extract candidate fields from a Firecrawl scrape payload.

    Args:
        payload: Raw Firecrawl response JSON for one page.

    Returns:
        A dict with keys ``title``, ``markdown``, ``hours``, ``fee``, ``url``.
        Missing values are empty strings.
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
