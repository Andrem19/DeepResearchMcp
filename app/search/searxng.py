"""SearXNG search provider — self-hosted, no API key required."""

from __future__ import annotations

import httpx

from app.errors import SearchError
from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider


class SearXNGProvider(SearchProvider):
    """Search provider using a local SearXNG instance.

    No API key needed — just a running SearXNG server.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080",
        timeout: float = 15.0,
        max_results_per_query: int = 10,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_results = max_results_per_query
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    @property
    def name(self) -> str:
        return "searxng"

    async def search(
        self,
        queries: list[SearchQuery],
        max_results: int = 20,
    ) -> list[SearchResult]:
        """Search using SearXNG and return deduplicated results."""
        all_results: list[SearchResult] = []
        seen_urls: set[str] = set()

        for query in queries:
            try:
                results = await self._search_single(query.query, max_results)
                for r in results:
                    if r.url not in seen_urls:
                        seen_urls.add(r.url)
                        all_results.append(r)
            except Exception:
                # Continue with other queries if one fails
                continue

        return all_results[:max_results]

    async def _search_single(
        self,
        query: str,
        max_results: int,
    ) -> list[SearchResult]:
        """Execute a single search query against SearXNG."""
        try:
            response = await self._client.get(
                f"{self._base_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                    "language": "auto",
                },
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise SearchError(f"SearXNG timeout for query: {query[:50]}") from exc
        except httpx.HTTPStatusError as e:
            raise SearchError(f"SearXNG HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            raise SearchError(f"SearXNG request failed: {e}") from e

        data = response.json()
        items = data.get("results", [])

        results: list[SearchResult] = []
        for i, item in enumerate(items[:self._max_results]):
            url = item.get("url", "")
            title = item.get("title", "")
            snippet = item.get("content", "")

            if not url:
                continue

            try:
                results.append(
                    SearchResult(
                        title=title,
                        url=url,
                        snippet=snippet,
                        source_provider="searxng",
                        rank=i + 1,
                    )
                )
            except Exception:
                continue

        return results

    async def close(self) -> None:
        await self._client.aclose()
