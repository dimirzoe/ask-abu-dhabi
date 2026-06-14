"""CLI entry point for the ETL pipeline.

Usage:
    python -m etl.run

Thin wrapper: builds settings + a Firecrawl client and invokes the pipeline,
translating the outcome into a process exit code (0 = published, 1 = aborted).
"""

from __future__ import annotations

import logging
import sys

from core.config import load_settings
from core.exceptions import AskAbuDhabiError
from etl.firecrawl_client import FirecrawlClient
from etl.pipeline import run_pipeline


def main() -> int:
    """Run the ETL pipeline once and return a shell exit code.

    Returns:
        0 if the knowledge base was published, 1 otherwise.
    """
    settings = load_settings()
    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger = logging.getLogger("etl.run")

    client = FirecrawlClient(settings)
    try:
        result = run_pipeline(settings, client)
    except AskAbuDhabiError as exc:
        logger.error("ETL run failed: %s", exc)
        return 1

    logger.info(
        "ETL complete: %d/%d sources valid, published=%s.",
        result.valid_count,
        result.total,
        result.published,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
