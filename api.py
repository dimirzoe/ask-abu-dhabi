"""FastAPI entry point — thin HTTP layer over the orchestrator.

Endpoints:
    POST /ask          — process a query and return an AskResponse.
    GET  /health       — liveness + KB/provider status.
    GET  /attractions  — list the loaded knowledge-base attractions.
    GET  /analytics    — aggregate query analytics.

All logic lives in ``core`` / ``providers``. Dependencies (settings, provider,
attractions, analytics) are wired via FastAPI's dependency-injection system; no
module-level global state is mutated at request time.
"""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from core.analytics import AnalyticsStore
from core.config import Settings, get_settings
from core.exceptions import AskAbuDhabiError, KnowledgeBaseError, LLMError
from core.kb_loader import load_knowledge_base
from core.orchestrator import process_query
from core.schema import Attraction, AskRequest, AskResponse, KBStatus
from providers.base import LLMProvider
from providers.factory import create_provider

app = FastAPI(title="Ask Abu Dhabi API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Dependency providers (cached at process scope, injected per request) -----
@lru_cache(maxsize=1)
def _settings_singleton() -> Settings:
    """Return the cached application settings."""
    return get_settings()


@lru_cache(maxsize=1)
def _analytics_singleton() -> AnalyticsStore:
    """Return the cached analytics store."""
    return AnalyticsStore(_settings_singleton().analytics_db_path)


def get_settings_dep() -> Settings:
    """FastAPI dependency: application settings."""
    return _settings_singleton()


def get_provider_dep(
    settings: Settings = Depends(get_settings_dep),
) -> LLMProvider:
    """FastAPI dependency: the configured LLM provider."""
    return create_provider(settings)


def get_kb_dep(
    settings: Settings = Depends(get_settings_dep),
) -> tuple[dict[str, Attraction], KBStatus]:
    """FastAPI dependency: loaded attractions and KB status."""
    try:
        return load_knowledge_base(settings)
    except KnowledgeBaseError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def get_analytics_dep() -> AnalyticsStore:
    """FastAPI dependency: the analytics store."""
    return _analytics_singleton()


# --- Endpoints ----------------------------------------------------------------
@app.post("/ask", response_model=AskResponse)
def ask(
    request: AskRequest,
    settings: Settings = Depends(get_settings_dep),
    provider: LLMProvider = Depends(get_provider_dep),
    kb: tuple[dict[str, Attraction], KBStatus] = Depends(get_kb_dep),
    analytics: AnalyticsStore = Depends(get_analytics_dep),
) -> AskResponse:
    """Process a user query and return a structured answer."""
    attractions, kb_status = kb
    try:
        return process_query(
            request,
            provider=provider,
            settings=settings,
            attractions=attractions,
            kb_status=kb_status,
            analytics=analytics,
        )
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AskAbuDhabiError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/health")
def health(
    settings: Settings = Depends(get_settings_dep),
    kb: tuple[dict[str, Attraction], KBStatus] = Depends(get_kb_dep),
) -> dict[str, object]:
    """Return liveness and basic operational status."""
    attractions, kb_status = kb
    return {
        "status": "ok",
        "provider": settings.llm_provider,
        "kb_status": kb_status.value,
        "attractions_loaded": len(attractions),
    }


@app.get("/attractions")
def attractions_endpoint(
    kb: tuple[dict[str, Attraction], KBStatus] = Depends(get_kb_dep),
) -> dict[str, object]:
    """Return the loaded knowledge-base attractions."""
    attractions, kb_status = kb
    return {
        "kb_status": kb_status.value,
        "count": len(attractions),
        "attractions": {k: v.model_dump() for k, v in attractions.items()},
    }


@app.get("/analytics")
def analytics_endpoint(
    analytics: AnalyticsStore = Depends(get_analytics_dep),
) -> dict[str, object]:
    """Return aggregate query analytics."""
    return analytics.summary()
