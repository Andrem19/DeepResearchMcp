"""Cache layer wrapping SQLiteStore with hash-based keys."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.storage.sqlite_store import SQLiteStore


class ResearchCache:
    """High-level cache for research pipeline data."""

    def __init__(self, store: SQLiteStore | None = None, *, ttl_seconds: int = 3600) -> None:
        self._store = store
        self._ttl = ttl_seconds

    @property
    def enabled(self) -> bool:
        return self._store is not None

    def get_search_results(self, query: str, provider: str) -> list[dict[str, Any]] | None:
        """Get cached search results for a query."""
        if not self._store:
            return None
        key = _hash_key(f"search:{provider}:{query}")
        data = self._store.get_search_cache(key)
        if data and isinstance(data, list):
            return data
        return None

    def set_search_results(
        self, query: str, provider: str, results: list[dict[str, Any]]
    ) -> None:
        """Cache search results."""
        if not self._store:
            return
        key = _hash_key(f"search:{provider}:{query}")
        self._store.set_search_cache(key, query, results, provider, self._ttl)

    def get_page(self, url: str) -> dict[str, Any] | None:
        """Get cached page."""
        if not self._store:
            return None
        key = _hash_key(f"page:{url}")
        return self._store.get_page_cache(key)

    def set_page(self, url: str, status_code: int, content_type: str, body: bytes) -> None:
        """Cache a fetched page."""
        if not self._store:
            return
        key = _hash_key(f"page:{url}")
        self._store.set_page_cache(key, url, status_code, content_type, body, self._ttl)

    def close(self) -> None:
        """Close underlying store."""
        if self._store:
            self._store.close()


class NullCache(ResearchCache):
    """Disabled cache — all operations are no-ops."""

    def __init__(self) -> None:
        super().__init__(store=None)

    @property
    def enabled(self) -> bool:
        return False


def _hash_key(s: str) -> str:
    """Create a stable hash key."""
    return hashlib.sha256(s.encode()).hexdigest()[:32]
