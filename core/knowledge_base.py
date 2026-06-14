"""Attraction matching against the in-memory knowledge base.

Pure, side-effect-free helpers that map a free-text query to a known attraction.
Matching is deliberately simple and deterministic (keyword / title overlap) to
keep behaviour explainable and fully testable offline.
"""

from __future__ import annotations

import re
from typing import Optional

from core.schema import Attraction

_TOKEN_RE = re.compile(r"[a-zA-Z؀-ۿ]+")


def _tokenize(text: str) -> set[str]:
    """Lowercase a string and split it into alphabetic / Arabic tokens."""
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _score(query_tokens: set[str], attraction: Attraction) -> int:
    """Score how well an attraction matches a tokenized query.

    A keyword scores only when **all** of its tokens are present in the query
    (whole-phrase match). This avoids false positives where a single shared
    token — e.g. "world" in "World Cup" overlapping the "ferrari world" keyword —
    would otherwise pull in an unrelated attraction. Title-word overlap adds a
    weaker secondary signal so a bare attraction name still matches.
    """
    score = 0
    for kw in attraction.keywords:
        # Keywords may be multi-word phrases; require the full phrase to match.
        kw_tokens = _tokenize(kw)
        if kw_tokens and kw_tokens.issubset(query_tokens):
            score += 3
    score += len(_tokenize(attraction.title) & query_tokens)
    return score


def match_attraction(
    query: str, attractions: dict[str, Attraction]
) -> Optional[tuple[str, Attraction]]:
    """Return the best-matching ``(id, attraction)`` for ``query`` if any.

    Args:
        query: Raw user query text.
        attractions: Mapping of attraction id to :class:`Attraction`.

    Returns:
        The highest-scoring ``(id, attraction)`` pair, or ``None`` when no
        attraction shares any signal with the query.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return None

    best_id: Optional[str] = None
    best_attraction: Optional[Attraction] = None
    best_score = 0

    for attraction_id, attraction in attractions.items():
        score = _score(query_tokens, attraction)
        if score > best_score:
            best_score = score
            best_id = attraction_id
            best_attraction = attraction

    if best_id is None or best_attraction is None:
        return None
    return best_id, best_attraction
