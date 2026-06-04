"""SQLite storage for research runs and cached data."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class SQLiteStore:
    """Simple SQLite storage for cache and research metadata."""

    def __init__(self, db_path: str = ".cache/deepresearch.sqlite3") -> None:
        self._db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(self._db_path)
            self._conn.row_factory = sqlite3.Row
            self._init_tables()
        return self._conn

    def _init_tables(self) -> None:
        """Create tables if they don't exist."""
        conn = self._get_conn()
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS search_cache (
                query_hash TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                results TEXT NOT NULL,
                provider TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS page_cache (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                status_code INTEGER,
                content_type TEXT,
                body BLOB,
                fetched_at TEXT NOT NULL,
                expires_at TEXT
            );

            CREATE TABLE IF NOT EXISTS research_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                depth TEXT NOT NULL DEFAULT 'standard',
                source_count INTEGER DEFAULT 0,
                duration_seconds REAL DEFAULT 0,
                report_md TEXT,
                created_at TEXT NOT NULL,
                correlation_id TEXT
            );
            """
        )
        conn.commit()

    # --- Search Cache ---

    def get_search_cache(self, query_hash: str) -> dict[str, Any] | None:
        """Get cached search results."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT results, expires_at FROM search_cache WHERE query_hash = ?",
            (query_hash,),
        ).fetchone()
        if row is None:
            return None
        # Check expiration
        if row["expires_at"]:
            expires = datetime.fromisoformat(row["expires_at"])
            if datetime.now(UTC) > expires:
                conn.execute("DELETE FROM search_cache WHERE query_hash = ?", (query_hash,))
                conn.commit()
                return None
        return json.loads(row["results"])

    def set_search_cache(
        self,
        query_hash: str,
        query: str,
        results: list[dict[str, Any]],
        provider: str = "",
        ttl_seconds: int = 3600,
    ) -> None:
        """Cache search results."""
        from datetime import timedelta

        conn = self._get_conn()
        now = datetime.now(UTC)
        expires = (now + timedelta(seconds=ttl_seconds)).isoformat() if ttl_seconds > 0 else None
        conn.execute(
            """INSERT OR REPLACE INTO search_cache
               (query_hash, query, results, provider, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (query_hash, query, json.dumps(results), provider, now.isoformat(), expires),
        )
        conn.commit()

    # --- Page Cache ---

    def get_page_cache(self, url_hash: str) -> dict[str, Any] | None:
        """Get cached page."""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT url, status_code, content_type, body, fetched_at FROM page_cache WHERE url_hash = ?",
            (url_hash,),
        ).fetchone()
        if row is None:
            return None
        return {
            "url": row["url"],
            "status_code": row["status_code"],
            "content_type": row["content_type"],
            "body": row["body"],
            "fetched_at": row["fetched_at"],
        }

    def set_page_cache(
        self,
        url_hash: str,
        url: str,
        status_code: int,
        content_type: str,
        body: bytes,
        ttl_seconds: int = 3600,
    ) -> None:
        """Cache a fetched page."""
        conn = self._get_conn()
        now = datetime.now(UTC)
        conn.execute(
            """INSERT OR REPLACE INTO page_cache
               (url_hash, url, status_code, content_type, body, fetched_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (url_hash, url, status_code, content_type, body, now.isoformat(), None),
        )
        conn.commit()

    # --- Research Runs ---

    def save_research_run(
        self,
        *,
        query: str,
        depth: str,
        source_count: int,
        duration_seconds: float,
        report_md: str,
        correlation_id: str = "",
    ) -> int:
        """Save a research run record."""
        conn = self._get_conn()
        now = datetime.now(UTC)
        cursor = conn.execute(
            """INSERT INTO research_runs
               (query, depth, source_count, duration_seconds, report_md, created_at, correlation_id)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (query, depth, source_count, duration_seconds, report_md, now.isoformat(), correlation_id),
        )
        conn.commit()
        return cursor.lastrowid or 0

    def close(self) -> None:
        """Close the database connection."""
        if self._conn is not None:
            self._conn.close()
            self._conn = None
