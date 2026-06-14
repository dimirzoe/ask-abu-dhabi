"""SQLite-backed analytics for processed queries.

Every query the orchestrator handles is logged: timestamp, language, matched
attraction, persona, provider, off-topic flag, and KB status. The store is a
thin object (constructed via DI) wrapping the stdlib ``sqlite3`` module — no ORM.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.schema import AnalyticsRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS query_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT    NOT NULL,
    language    TEXT    NOT NULL,
    attraction  TEXT,
    persona     TEXT    NOT NULL,
    provider    TEXT    NOT NULL,
    off_topic   INTEGER NOT NULL DEFAULT 0,
    kb_status   TEXT    NOT NULL
);
"""


class AnalyticsStore:
    """A small SQLite wrapper for logging and summarising query analytics."""

    def __init__(self, db_path: str) -> None:
        """Initialise the store and ensure the schema exists.

        Args:
            db_path: Filesystem path to the SQLite database. Parent directories
                are created if necessary.
        """
        self._db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """Open a connection with row access by column name."""
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        """Create the analytics table if it does not already exist."""
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def log_query(
        self,
        *,
        language: str,
        attraction: Optional[str],
        persona: str,
        provider: str,
        off_topic: bool,
        kb_status: str,
    ) -> None:
        """Persist one analytics record.

        Args:
            language: Detected/forced response language code.
            attraction: Matched attraction id, or None.
            persona: Visitor persona value.
            provider: LLM provider name (or 'none' for off-topic).
            off_topic: Whether the query bypassed the LLM.
            kb_status: Knowledge-base freshness status at handling time.
        """
        record = AnalyticsRecord(
            timestamp=datetime.now(timezone.utc),
            language=language,
            attraction=attraction,
            persona=persona,
            provider=provider,
            off_topic=off_topic,
            kb_status=kb_status,
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO query_log
                    (timestamp, language, attraction, persona, provider,
                     off_topic, kb_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.timestamp.isoformat(),
                    record.language,
                    record.attraction,
                    record.persona,
                    record.provider,
                    int(record.off_topic),
                    record.kb_status,
                ),
            )

    def summary(self) -> dict[str, object]:
        """Return aggregate analytics for the ``/analytics`` endpoint.

        Returns:
            A dict with total counts and per-dimension breakdowns.
        """
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM query_log").fetchone()["c"]
            by_language = self._group(conn, "language")
            by_persona = self._group(conn, "persona")
            by_provider = self._group(conn, "provider")
            by_attraction = self._group(conn, "attraction")
            off_topic = conn.execute(
                "SELECT COUNT(*) AS c FROM query_log WHERE off_topic = 1"
            ).fetchone()["c"]
        return {
            "total_queries": total,
            "off_topic": off_topic,
            "by_language": by_language,
            "by_persona": by_persona,
            "by_provider": by_provider,
            "by_attraction": by_attraction,
        }

    @staticmethod
    def _group(conn: sqlite3.Connection, column: str) -> dict[str, int]:
        """Return a ``value -> count`` mapping grouped by ``column``."""
        rows = conn.execute(
            f"SELECT {column} AS k, COUNT(*) AS c FROM query_log "
            f"WHERE {column} IS NOT NULL GROUP BY {column} ORDER BY c DESC"
        ).fetchall()
        return {row["k"]: row["c"] for row in rows}
