"""Pydantic v2 models for data crossing module boundaries.

These models form the contract between layers (API ↔ orchestrator ↔ providers ↔
knowledge base). Any structure passed between packages should be defined here.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Language(str, Enum):
    """Supported response languages."""

    EN = "en"
    AR = "ar"


class Persona(str, Enum):
    """Visitor persona used to tune prompt tone and the closing nudge."""

    FIRST_TIME = "first_time"
    FAMILY = "family"
    BUSINESS = "business"


class KBStatus(str, Enum):
    """Freshness tier of the loaded knowledge base."""

    FRESH = "FRESH"
    STALE = "STALE"
    BASELINE = "BASELINE"
    FAILED = "FAILED"


class Attraction(BaseModel):
    """A single knowledge-base entry describing an attraction or topic."""

    title: str
    category: str
    url: str
    location: str
    hours: str
    fee: str
    duration: str
    context: str
    nudge: str
    keywords: list[str] = Field(min_length=1)
    source_url: str
    last_updated: str

    @field_validator("keywords")
    @classmethod
    def _normalise_keywords(cls, value: list[str]) -> list[str]:
        """Lowercase and strip keywords; drop empties."""
        return [k.strip().lower() for k in value if k and k.strip()]


class KnowledgeBase(BaseModel):
    """Container for the full set of attractions plus generation metadata."""

    generated_at: str
    attractions: dict[str, Attraction]


class AskRequest(BaseModel):
    """Inbound user request handled by the orchestrator."""

    query: str = Field(min_length=1, max_length=2000)
    persona: Persona = Persona.FIRST_TIME
    language: Optional[Language] = Field(
        default=None,
        description="Force a response language; None means auto-detect.",
    )


class AskResponse(BaseModel):
    """Outbound answer returned to API / UI callers."""

    answer: str
    language: Language
    attraction_id: Optional[str] = None
    attraction_title: Optional[str] = None
    official_url: Optional[str] = None
    persona: Persona
    provider: str
    off_topic: bool = False
    kb_status: KBStatus


class AnalyticsRecord(BaseModel):
    """A single analytics row describing one processed query."""

    timestamp: datetime
    language: str
    attraction: Optional[str]
    persona: str
    provider: str
    off_topic: bool
    kb_status: str
