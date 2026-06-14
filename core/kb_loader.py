"""Knowledge-base loading with a 3-tier freshness fallback chain.

Resolution order:

1. **FRESH**   — the active KB at ``settings.kb_path`` parses and is recent.
2. **STALE**   — the active KB parses but is older than ``kb_stale_after_hours``.
3. **BASELINE** — the bundled baseline KB is used.

If none of these can be loaded, a :class:`~core.exceptions.KnowledgeBaseError`
is raised (the orchestrator surfaces this as a FAILED state).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from core.config import Settings
from core.exceptions import KnowledgeBaseError
from core.schema import Attraction, KBStatus

logger = logging.getLogger(__name__)


def _parse_kb_file(path: Path) -> tuple[dict[str, Attraction], datetime | None]:
    """Parse a KB JSON file into validated attractions and its generation time.

    Args:
        path: Path to a knowledge-base JSON document.

    Returns:
        A tuple of (attractions mapping, generated_at datetime or None).

    Raises:
        KnowledgeBaseError: If the file is missing, invalid JSON, or fails
            schema validation.
    """
    if not path.exists():
        raise KnowledgeBaseError(f"Knowledge base file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeBaseError(f"Could not read KB at {path}: {exc}") from exc

    raw_attractions = raw.get("attractions", raw)
    if not isinstance(raw_attractions, dict) or not raw_attractions:
        raise KnowledgeBaseError(f"KB at {path} contains no attractions.")

    try:
        attractions = {
            key: Attraction.model_validate(value)
            for key, value in raw_attractions.items()
        }
    except Exception as exc:  # pydantic ValidationError and friends
        raise KnowledgeBaseError(f"KB at {path} failed validation: {exc}") from exc

    generated_at = _parse_timestamp(raw.get("generated_at"))
    return attractions, generated_at


def _parse_timestamp(value: object) -> datetime | None:
    """Best-effort parse of an ISO-8601 timestamp string into aware UTC."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _is_stale(generated_at: datetime | None, stale_after_hours: int) -> bool:
    """Return True when ``generated_at`` is older than the staleness window."""
    if generated_at is None:
        return True
    age_hours = (datetime.now(timezone.utc) - generated_at).total_seconds() / 3600
    return age_hours > stale_after_hours


def load_knowledge_base(
    settings: Settings,
) -> tuple[dict[str, Attraction], KBStatus]:
    """Load attractions using the FRESH → STALE → BASELINE fallback chain.

    Args:
        settings: Application settings providing KB paths and staleness window.

    Returns:
        A tuple of (attractions mapping, :class:`KBStatus`).

    Raises:
        KnowledgeBaseError: If neither the active KB nor the baseline can load.
    """
    active_path = Path(settings.kb_path)

    # --- Tier 1 & 2: active KB (FRESH or STALE) ---
    try:
        attractions, generated_at = _parse_kb_file(active_path)
    except KnowledgeBaseError as exc:
        logger.warning("Active KB unavailable (%s); falling back to baseline.", exc)
    else:
        if _is_stale(generated_at, settings.kb_stale_after_hours):
            logger.warning(
                "Active KB at %s is STALE (generated_at=%s). Serving anyway.",
                active_path,
                generated_at,
            )
            return attractions, KBStatus.STALE
        return attractions, KBStatus.FRESH

    # --- Tier 3: bundled baseline ---
    baseline_path = Path(settings.kb_baseline_path)
    try:
        attractions, _ = _parse_kb_file(baseline_path)
    except KnowledgeBaseError as exc:
        raise KnowledgeBaseError(
            f"Could not load active KB or baseline KB at {baseline_path}: {exc}"
        ) from exc

    logger.warning("Serving BASELINE knowledge base from %s.", baseline_path)
    return attractions, KBStatus.BASELINE
