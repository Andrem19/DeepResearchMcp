"""DuckDuckGo search provider — no API key required, fully self-contained."""

from __future__ import annotations

from ddgs import DDGS

from app.errors import SearchError
from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider


class DuckDuckGoProvider(SearchProvider):
    """Search provider using DuckDuckGo. No API key needed.

    Uses the ddgs library which queries DDG HTML interface
    directly. Fully self-contained — no external services to configure.
    """

    @property
    def name(self) -> str:
        return "duckduckgo"

    async def search(
        self,
        queries: list[SearchQuery],
        max_results: int = 20,
    ) -> list[SearchResult]:
        """Search DuckDuckGo for each query and return deduplicated results."""
        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in queries:
            try:
                results = self._search_sync(query.query, max_results=max_results)
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r)
            except Exception:
                # Continue with other queries if one fails
                continue

        return all_results[:max_results]

    def _search_sync(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[SearchResult]:
        """Execute a synchronous DDG search."""
        try:
            with DDGS() as ddgs:
                items = list(ddgs.text(query, max_results=max_results))
        except Exception as exc:
            raise SearchError(f"DuckDuckGo search failed: {exc}") from exc

        results: list[SearchResult] = []
        for i, item in enumerate(items):
            url = item.get("href", "") or item.get("link", "")
            title = item.get("title", "")
            snippet = item.get("body", "") or item.get("snippet", "")

            if not url:
                continue

            try:
                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source_provider="duckduckgo",
                        rank=i + 1,
                    )
                )
            except Exception:
                continue

        return results
