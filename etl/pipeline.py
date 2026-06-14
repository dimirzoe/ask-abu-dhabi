"""ETL pipeline: scrape → extract → transform → validate → atomic publish.

For each :class:`~etl.sources.Source`:

1. ``firecrawl.scrape(url)``
2. ``extract_fields``
3. ``transform`` into an :class:`Attraction`
4. ``validate_attraction``

If at least ``settings.etl_min_valid_sources`` (default 8 of 12) entries
validate, the new knowledge base is written **atomically** (tmp file + rename),
replacing the active KB. Otherwise the existing JSON is preserved untouched and
an :class:`~core.exceptions.ETLError` is raised.
"""

from __future__ import annotations

import json
import logging
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.config import Settings
from core.exceptions import ETLError
from etl.extractors import extract_fields
from etl.firecrawl_client import FirecrawlClient
from etl.sources import SOURCES, Source
from etl.transformers import transform
from etl.validators import validate_attraction

logger = logging.getLogger(__name__)


class PipelineResult:
    """Outcome of an ETL run for logging and callers."""

    def __init__(
        self,
        *,
        valid_count: int,
        total: int,
        published: bool,
        failures: dict[str, list[str]],
        published_count: int = 0,
    ) -> None:
        """Capture run statistics.

        Args:
            valid_count: Number of sources that freshly scraped and validated.
            total: Total number of sources attempted.
            published: Whether the KB was written.
            failures: Mapping of source id to failure reasons.
            published_count: Total entries written (fresh + baseline-backfilled).
        """
        self.valid_count = valid_count
        self.total = total
        self.published = published
        self.failures = failures
        self.published_count = published_count

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return (
            f"PipelineResult(fresh={self.valid_count}/{self.total}, "
            f"published={self.published_count} entries)"
        )


def _process_source(
    source: Source, client: FirecrawlClient
) -> tuple[Optional[dict], list[str]]:
    """Scrape and transform one source into a serialisable attraction dict.

    Returns:
        ``(attraction_dict, reasons)``. On any failure ``attraction_dict`` is
        ``None`` and ``reasons`` explains why.
    """
    try:
        payload = client.scrape(source.url)
    except ETLError as exc:
        return None, [f"scrape error: {exc}"]

    fields = extract_fields(payload)
    try:
        attraction = transform(source, fields)
    except Exception as exc:  # noqa: BLE001 - schema/transform failure
        return None, [f"transform error: {exc}"]

    valid, reasons = validate_attraction(attraction)
    if not valid:
        return None, reasons
    return attraction.model_dump(), []


def _atomic_write(path: Path, document: dict) -> None:
    """Write ``document`` as JSON to ``path`` atomically (tmp file + rename).

    Args:
        path: Destination KB path.
        document: The full KB document to serialise.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)  # atomic on POSIX & Windows
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


def _load_baseline_attractions(path: Path) -> dict[str, dict]:
    """Load baseline attractions as raw dicts, used to backfill failed sources.

    Args:
        path: Path to the bundled baseline knowledge base.

    Returns:
        Mapping of attraction id to its raw dict, or ``{}`` if the baseline
        cannot be read (a missing baseline simply means no backfill).
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Baseline KB unreadable at %s; cannot backfill.", path)
        return {}
    attractions = raw.get("attractions", {})
    return attractions if isinstance(attractions, dict) else {}


def run_pipeline(
    settings: Settings,
    client: FirecrawlClient,
    sources: Optional[list[Source]] = None,
) -> PipelineResult:
    """Execute the full ETL run and conditionally publish the knowledge base.

    Args:
        settings: Application settings (paths, threshold).
        client: Firecrawl client (injected, mockable).
        sources: Sources to process; defaults to the canonical 12.

    Returns:
        A :class:`PipelineResult` describing the run.

    Raises:
        ETLError: If fewer than ``etl_min_valid_sources`` entries validate. The
            existing knowledge base is left untouched in that case.
    """
    sources = sources if sources is not None else SOURCES
    total = len(sources)
    attractions: dict[str, dict] = {}
    failures: dict[str, list[str]] = {}

    for source in sources:
        attraction_dict, reasons = _process_source(source, client)
        if attraction_dict is not None:
            attractions[source.attraction_id] = attraction_dict
        else:
            failures[source.attraction_id] = reasons
            logger.warning("Source '%s' failed: %s", source.attraction_id, reasons)

    valid_count = len(attractions)
    threshold = settings.etl_min_valid_sources

    if valid_count < threshold:
        logger.error(
            "ETL aborted: only %d/%d sources valid (need %d). Existing KB preserved.",
            valid_count,
            total,
            threshold,
        )
        raise ETLError(
            f"Only {valid_count}/{total} sources validated (minimum {threshold}). "
            f"Existing knowledge base preserved."
        )

    # Merge freshly scraped entries over the baseline so a partial run never
    # shrinks the knowledge base: fresh data wins, baseline backfills the rest.
    baseline = _load_baseline_attractions(Path(settings.kb_baseline_path))
    merged = {**baseline, **attractions}
    backfilled = len(merged) - valid_count

    document = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "attractions": merged,
    }
    _atomic_write(Path(settings.kb_path), document)
    logger.info(
        "ETL published KB to %s: %d/%d freshly scraped, %d baseline-backfilled, "
        "%d total entries.",
        settings.kb_path,
        valid_count,
        total,
        backfilled,
        len(merged),
    )
    return PipelineResult(
        valid_count=valid_count,
        total=total,
        published=True,
        failures=failures,
        published_count=len(merged),
    )
