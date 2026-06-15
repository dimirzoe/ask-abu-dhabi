"""Intent / language detection used to gate the LLM.

Two responsibilities, both pure and offline:

* :func:`detect_language` — heuristically choose EN vs AR for the reply.
* :func:`is_on_topic` — decide whether a query is about Abu Dhabi tourism. When
  it is not, the orchestrator must bypass the LLM entirely and return a static
  redirect message.

A query is considered on-topic if it matches a known attraction OR contains any
of a curated set of tourism signal terms (EN + AR).
"""

from __future__ import annotations

import re

from core.knowledge_base import match_attraction
from core.schema import Attraction, Language

_ARABIC_RE = re.compile(r"[؀-ۿ]")

# Abu Dhabi tourism signal vocabulary. Lowercase EN + AR forms. Deliberately
# excludes over-generic standalone words (where/open/price/fee/hotel/family/kids/
# address/restaurant/weekend) that would fire on unrelated queries — a real
# Abu Dhabi query carries an attraction name or a domain term ("visa", "abu
# dhabi", "tourism"), or matches an attraction directly.
ON_TOPIC_TERMS: frozenset[str] = frozenset(
    {
        # English
        "abu dhabi", "uae", "emirate", "emirates", "mosque", "louvre", "museum",
        "palace", "beach", "corniche", "island", "yas", "saadiyat", "ferrari",
        "warner", "heritage", "fort", "hosn", "qasr", "attraction", "attractions",
        "visit", "tour", "tourist", "tourism", "ticket", "tickets",
        "sightseeing", "transport", "metro", "taxi", "airport", "transfer",
        "visa", "etiquette", "dress code", "culture", "things to do",
        "how to get", "directions", "itinerary", "hafilat",
        # Arabic
        "أبوظبي", "أبو ظبي", "الإمارات", "مسجد", "اللوفر", "متحف", "قصر",
        "شاطئ", "كورنيش", "جزيرة", "ياس", "السعديات", "تراث", "حصن",
        "زيارة", "جولة", "سياحة", "تذكرة", "رسوم", "سعر", "مواعيد", "موقع",
        "مواصلات", "حافلة", "مطار", "تأشيرة", "آداب", "ثقافة",
    }
)

_WORD_RE = re.compile(r"[a-z]+")


def _term_matches(term: str, lowered: str, words: set[str]) -> bool:
    """Whole-word (EN) / phrase / substring (AR) match for an on-topic term.

    Single ASCII words match only as whole words (so "fee" does not fire on
    "coffee"); multi-word phrases and Arabic terms use substring matching.
    """
    if " " in term:
        return term in lowered
    if term.isascii():
        return term in words
    return term in lowered


def detect_language(text: str, forced: Language | None = None) -> Language:
    """Detect the response language for a query.

    Args:
        text: The raw user query.
        forced: If provided, overrides detection (used by the UI language hint).

    Returns:
        :attr:`Language.AR` when Arabic script is present (and not overridden),
        otherwise :attr:`Language.EN`.
    """
    if forced is not None:
        return forced
    return Language.AR if _ARABIC_RE.search(text) else Language.EN


def is_on_topic(query: str, attractions: dict[str, Attraction]) -> bool:
    """Return True if the query is about Abu Dhabi tourism.

    Args:
        query: Raw user query.
        attractions: Knowledge-base attractions (used for direct matches).

    Returns:
        Whether the query should be answered by the LLM (``True``) or handled by
        the static off-topic redirect (``False``).
    """
    lowered = query.lower()
    words = set(_WORD_RE.findall(lowered))
    if any(_term_matches(term, lowered, words) for term in ON_TOPIC_TERMS):
        return True
    return match_attraction(query, attractions) is not None
