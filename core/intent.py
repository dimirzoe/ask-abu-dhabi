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

# Broad tourism / Abu Dhabi signal vocabulary. Lowercase EN + AR forms.
ON_TOPIC_TERMS: frozenset[str] = frozenset(
    {
        # English
        "abu dhabi", "uae", "emirate", "emirates", "mosque", "louvre", "museum",
        "palace", "beach", "corniche", "island", "yas", "saadiyat", "ferrari",
        "warner", "heritage", "fort", "hosn", "qasr", "attraction", "attractions",
        "visit", "tour", "tourist", "tourism", "ticket", "tickets", "fee", "fees",
        "price", "hours", "opening", "open", "location", "address", "transport",
        "metro", "bus", "taxi", "airport", "transfer", "visa", "etiquette",
        "dress", "culture", "things to do", "where", "how to get", "directions",
        "hotel", "restaurant", "family", "kids", "weekend", "itinerary",
        # Arabic
        "أبوظبي", "أبو ظبي", "الإمارات", "مسجد", "اللوفر", "متحف", "قصر",
        "شاطئ", "كورنيش", "جزيرة", "ياس", "السعديات", "تراث", "حصن",
        "زيارة", "جولة", "سياحة", "تذكرة", "رسوم", "سعر", "مواعيد", "موقع",
        "مواصلات", "حافلة", "مطار", "تأشيرة", "آداب", "ثقافة",
    }
)


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
    if any(term in lowered for term in ON_TOPIC_TERMS):
        return True
    return match_attraction(query, attractions) is not None
