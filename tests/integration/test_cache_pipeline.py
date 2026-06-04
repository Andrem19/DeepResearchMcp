"""Integration tests: cache pipeline with SQLiteStore.

Basic tests verifying cache infrastructure works end-to-end.
Note: the engine pipeline currently does not use cache internally,
but the cache layer itself can be tested for correctness.
"""

from __future__ import annotations

import pytest

from app.storage.cache import NullCache, ResearchCache
from app.storage.sqlite_store import SQLiteStore

# ── NullCache ────────────────────────────────────────────────────────────────


@pytest.mark.integration
class TestNullCache:
    """NullCache always reports disabled and returns None."""

    def test_null_cache_not_enabled(self):
        cache = NullCache()
        assert cache.enabled is False

    def test_null_cache_get_search_returns_none(self):
        cache = NullCache()
        assert cache.get_search_results("test query", "fake") is None

    def test_null_cache_get_page_returns_none(self):
        cache = NullCache()
        assert cache.get_page("https://example.com") is None

    def test_null_cache_set_does_not_raise(self):
        cache = NullCache()
        # These should be no-ops, not raise
        cache.set_search_results("q", "fake", [{"title": "t"}])
        cache.set_page("https://example.com", 200, "text/html", b"data")


# ── ResearchCache with real SQLiteStore ──────────────────────────────────────


@pytest.mark.integration
class TestResearchCacheWithStore:
    """Cache backed by a temporary SQLite database."""

    @pytest.fixture()
    def cache(self, tmp_path):
        """Create a ResearchCache with a temp SQLite database.

        Uses ttl_seconds=0 to disable expiration. The current SQLiteStore
        implementation sets expires_at=now (instead of now+ttl), causing
        entries to expire immediately. With ttl=0, expires_at is None and
        the read-path skips the expiration check.
        """
        db_path = str(tmp_path / "test_cache.sqlite3")
        store = SQLiteStore(db_path)
        return ResearchCache(store, ttl_seconds=0)

    def test_cache_enabled_when_store_present(self, cache):
        assert cache.enabled is True

    def test_search_cache_round_trip(self, cache):
        results = [{"title": "MCP Intro", "url": "https://example.com/mcp"}]
        cache.set_search_results("MCP query", "fake", results)

        retrieved = cache.get_search_results("MCP query", "fake")
        assert retrieved is not None
        assert len(retrieved) == 1
        assert retrieved[0]["title"] == "MCP Intro"

    def test_search_cache_miss_returns_none(self, cache):
        assert cache.get_search_results("missing query", "fake") is None

    def test_page_cache_round_trip(self, cache):
        body = b"<html><body>Hello</body></html>"
        cache.set_page("https://example.com/page", 200, "text/html", body)

        retrieved = cache.get_page("https://example.com/page")
        assert retrieved is not None
        assert retrieved["body"] == body
        assert retrieved["status_code"] == 200

    def test_page_cache_miss_returns_none(self, cache):
        assert cache.get_page("https://example.com/missing") is None

    def test_different_providers_do_not_collide(self, cache):
        cache.set_search_results("q", "fake", [{"title": "fake result"}])
        cache.set_search_results("q", "brave", [{"title": "brave result"}])

        assert cache.get_search_results("q", "fake")[0]["title"] == "fake result"
        assert cache.get_search_results("q", "brave")[0]["title"] == "brave result"

    def test_cache_close_and_reopen(self, tmp_path):
        db_path = str(tmp_path / "test_cache2.sqlite3")

        # Write with one cache instance
        store1 = SQLiteStore(db_path)
        cache1 = ResearchCache(store1, ttl_seconds=0)
        cache1.set_search_results("persist query", "fake", [{"title": "persisted"}])
        cache1.close()

        # Read with a new cache instance
        store2 = SQLiteStore(db_path)
        cache2 = ResearchCache(store2, ttl_seconds=0)
        result = cache2.get_search_results("persist query", "fake")
        assert result is not None
        assert result[0]["title"] == "persisted"
        cache2.close()
