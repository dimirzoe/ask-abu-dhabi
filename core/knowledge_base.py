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

# Stopwords excluded from title-overlap scoring so generic words (especially
# "in"/"the"/"abu"/"dhabi", which appear in many titles) cannot spuriously match
# unrelated queries (e.g. "weather in Tokyo" hitting "...Etiquette in Abu Dhabi").
_TITLE_STOPWORDS: frozenset[str] = frozenset(
    {"in", "the", "and", "of", "a", "to", "at", "on", "for", "abu", "dhabi"}
)


def _tokenize(text: str) -> set[str]:
    """Lowercase a string and split it into alphabetic / Arabic tokens."""
    return {t.lower() for t in _TOKEN_RE.findall(text)}


def _score(query_tokens: set[str], attraction: Attraction) -> int:
    """Score how well an attraction matches a tokenized query.

    A keyword scores only when **all** of its tokens are present in the query
    (whole-phrase match). This avoids false positives where a single shared
    token — e.g. "world" in "World Cup" overlapping the "ferrari world" keyword —
    would otherwise pull in an unrelated attraction. Significant title words
    (stopwords removed) add a weaker secondary signal so a bare attraction name
    still matches.
    """
    score = 0
    for kw in attraction.keywords:
        # Keywords may be multi-word phrases; require the full phrase to match.
        kw_tokens = _tokenize(kw)
        if kw_tokens and kw_tokens.issubset(query_tokens):
            score += 3
    title_tokens = _tokenize(attraction.title) - _TITLE_STOPWORDS
    score += len(title_tokens & query_tokens)
    return score


def rank_attractions(
    query: str, attractions: dict[str, Attraction]
) -> list[tuple[str, Attraction, int]]:
    """Rank attractions by relevance to ``query``.

    Args:
        query: Raw user query text.
        attractions: Mapping of attraction id to :class:`Attraction`.

    Returns:
        ``(id, attraction, score)`` tuples with score > 0, highest first.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    scored = [
        (attraction_id, attraction, _score(query_tokens, attraction))
        for attraction_id, attraction in attractions.items()
    ]
    ranked = [t for t in scored if t[2] > 0]
    ranked.sort(key=lambda t: t[2], reverse=True)
    return ranked


def match_attraction(
    query: str, attractions: dict[str, Attraction]
) -> Optional[tuple[str, Attraction]]:
    """Return the single best-matching ``(id, attraction)`` for ``query``.

    Args:
        query: Raw user query text.
        attractions: Mapping of attraction id to :class:`Attraction`.

    Returns:
        The highest-scoring ``(id, attraction)`` pair, or ``None`` when no
        attraction shares any signal with the query.
    """
    ranked = rank_attractions(query, attractions)
    if not ranked:
        return None
    best_id, best_attraction, _ = ranked[0]
    return best_id, best_attraction
