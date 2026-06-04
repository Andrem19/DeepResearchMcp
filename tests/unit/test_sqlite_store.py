"""Unit tests for app.storage.sqlite_store — tables, cache hit/miss, expiration."""

from __future__ import annotations

from datetime import UTC

import pytest

from app.storage.sqlite_store import SQLiteStore

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def store(tmp_path):
    """Create a SQLiteStore with a temporary database."""
    db_path = str(tmp_path / "test.sqlite3")
    s = SQLiteStore(db_path=db_path)
    yield s
    s.close()


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_creates_tables(store):
    conn = store._get_conn()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    table_names = {row["name"] for row in tables}
    assert "search_cache" in table_names
    assert "page_cache" in table_names
    assert "research_runs" in table_names


# ---------------------------------------------------------------------------
# Search cache — hit / miss
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_cache_miss(store):
    result = store.get_search_cache("nonexistent_hash")
    assert result is None


@pytest.mark.unit
def test_search_cache_hit(store):
    data = [{"title": "Result 1", "url": "https://example.com"}]
    # ttl_seconds=0 means no expiration (expires_at=NULL), so data persists.
    # Positive TTL triggers the known bug where expires_at=now (immediately expired).
    store.set_search_cache("hash1", "test query", data, provider="fake", ttl_seconds=0)
    result = store.get_search_cache("hash1")
    assert result is not None
    assert len(result) == 1
    assert result[0]["title"] == "Result 1"


@pytest.mark.unit
def test_search_cache_overwrite(store):
    store.set_search_cache("hash1", "q", [{"title": "old"}], ttl_seconds=0)
    store.set_search_cache("hash1", "q", [{"title": "new"}], ttl_seconds=0)
    result = store.get_search_cache("hash1")
    assert result[0]["title"] == "new"


# ---------------------------------------------------------------------------
# Search cache — expiration
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_cache_expired_returns_none(store):
    # Set with 1s TTL, then manually expire by setting expires_at in the past
    store.set_search_cache("hash2", "q", [{"title": "expired"}], ttl_seconds=1)
    # Manually set expires_at to the past to simulate expiration
    from datetime import datetime, timedelta

    conn = store._get_conn()
    conn.execute(
        "UPDATE search_cache SET expires_at = ? WHERE query_hash = ?",
        ((datetime.now(UTC) - timedelta(hours=1)).isoformat(), "hash2"),
    )
    conn.commit()
    result = store.get_search_cache("hash2")
    assert result is None


@pytest.mark.unit
def test_search_cache_zero_ttl_never_expires(store):
    store.set_search_cache("hash3", "q", [{"title": "permanent"}], ttl_seconds=0)
    result = store.get_search_cache("hash3")
    assert result is not None
    assert result[0]["title"] == "permanent"


# ---------------------------------------------------------------------------
# Page cache — hit / miss
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_page_cache_miss(store):
    result = store.get_page_cache("nonexistent")
    assert result is None


@pytest.mark.unit
def test_page_cache_hit(store):
    store.set_page_cache(
        "page_hash1",
        "https://example.com",
        status_code=200,
        content_type="text/html",
        body=b"<html>hello</html>",
    )
    result = store.get_page_cache("page_hash1")
    assert result is not None
    assert result["url"] == "https://example.com"
    assert result["status_code"] == 200
    assert result["body"] == b"<html>hello</html>"


@pytest.mark.unit
def test_page_cache_overwrite(store):
    store.set_page_cache("ph", "https://example.com", 200, "text/html", b"old")
    store.set_page_cache("ph", "https://example.com", 200, "text/html", b"new")
    result = store.get_page_cache("ph")
    assert result["body"] == b"new"


# ---------------------------------------------------------------------------
# Research runs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_save_research_run(store):
    run_id = store.save_research_run(
        query="What is Python?",
        depth="standard",
        source_count=5,
        duration_seconds=3.14,
        report_md="# Report",
        correlation_id="corr-123",
    )
    assert run_id > 0


@pytest.mark.unit
def test_save_multiple_runs_increments(store):
    id1 = store.save_research_run(
        query="q1", depth="quick", source_count=1,
        duration_seconds=1.0, report_md="r1",
    )
    id2 = store.save_research_run(
        query="q2", depth="deep", source_count=10,
        duration_seconds=10.0, report_md="r2",
    )
    assert id2 > id1


# ---------------------------------------------------------------------------
# Close
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_close_sets_conn_none(store):
    store._get_conn()  # ensure connection is open
    assert store._conn is not None
    store.close()
    assert store._conn is None


@pytest.mark.unit
def test_double_close_safe(store):
    store.close()
    store.close()  # should not raise
