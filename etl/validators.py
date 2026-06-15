"""Validation: decide whether a transformed Attraction is fit for publication.

An entry is valid when it parses against the schema AND carries enough signal to
be useful (real title, official URL, non-trivial context, and keywords). The
pipeline counts valid entries to enforce the 8-of-12 publication threshold.
"""

from __future__ import annotations

import re

from core.schema import Attraction

_MIN_CONTEXT_CHARS = 40
_MIN_CONTEXT_WORDS = 8
_MIN_KEYWORDS = 3

# A bare numeric range like "0-94" — never a real opening-hours value.
_BARE_NUMERIC_RANGE_RE = re.compile(r"^\d+\s*[-–—]\s*\d+$")
# Leftover markdown/HTML artifacts that mean the context wasn't cleaned.
_ARTIFACT_MARKERS: tuple[str, ...] = ("](", "![", "http://", "https://", "skip to")
# Phrases that reveal the scrape hit a 404 / redirect / error stub rather than
# real attraction content. Such entries must be rejected (and backfilled from
# the baseline) instead of publishing "page not found" as an attraction blurb.
_ERROR_PAGE_MARKERS: tuple[str, ...] = (
    "page not found",
    "page was not found",
    "404",
    "no longer exists",
    "does not exist",
    "the mirage you",
    "you might interested",
)


def validate_attraction(attraction: Attraction) -> tuple[bool, list[str]]:
    """Validate a single attraction.

    Beyond the basic presence checks, this rejects entries whose scraped fields
    are clearly junk: bare numeric "hours" (e.g. ``0-94``) and context blocks
    that are too short, too sparse, or still contain markdown/HTML artifacts.

    Args:
        attraction: The transformed attraction to check.

    Returns:
        A tuple ``(is_valid, reasons)`` where ``reasons`` lists failed checks
        (empty when valid).
    """
    reasons: list[str] = []

    if not attraction.title.strip():
        reasons.append("missing title")
    if not attraction.url.startswith(("http://", "https://")):
        reasons.append("invalid url")
    if not attraction.nudge.strip():
        reasons.append("missing nudge")
    if len(attraction.keywords) < _MIN_KEYWORDS:
        reasons.append("too few keywords")

    context = attraction.context.strip()
    context_lower = context.lower()
    if len(context) < _MIN_CONTEXT_CHARS:
        reasons.append("context too short")
    elif len(re.findall(r"[A-Za-z]{2,}", context)) < _MIN_CONTEXT_WORDS:
        reasons.append("context lacks prose")
    elif any(marker in context_lower for marker in _ARTIFACT_MARKERS):
        reasons.append("context contains markup artifacts")
    elif any(marker in context_lower for marker in _ERROR_PAGE_MARKERS):
        reasons.append("context looks like an error/redirect page")

    hours = attraction.hours.strip()
    if _BARE_NUMERIC_RANGE_RE.match(hours):
        reasons.append("hours not a real time")

    return (len(reasons) == 0, reasons)


def is_valid(attraction: Attraction) -> bool:
    """Convenience boolean wrapper around :func:`validate_attraction`."""
    valid, _ = validate_attraction(attraction)
    return valid
