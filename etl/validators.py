"""Validation: decide whether a transformed Attraction is fit for publication.

An entry is valid when it parses against the schema AND carries enough signal to
be useful (real title, official URL, non-trivial context, and keywords). The
pipeline counts valid entries to enforce the 8-of-12 publication threshold.
"""

from __future__ import annotations

from core.schema import Attraction

_MIN_CONTEXT_CHARS = 20
_MIN_KEYWORDS = 3


def validate_attraction(attraction: Attraction) -> tuple[bool, list[str]]:
    """Validate a single attraction.

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
    if len(attraction.context.strip()) < _MIN_CONTEXT_CHARS:
        reasons.append("context too short")
    if len(attraction.keywords) < _MIN_KEYWORDS:
        reasons.append("too few keywords")
    if not attraction.nudge.strip():
        reasons.append("missing nudge")

    return (len(reasons) == 0, reasons)


def is_valid(attraction: Attraction) -> bool:
    """Convenience boolean wrapper around :func:`validate_attraction`."""
    valid, _ = validate_attraction(attraction)
    return valid
