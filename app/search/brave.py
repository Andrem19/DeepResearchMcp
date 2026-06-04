"""Brave Search API provider."""

from __future__ import annotations

import httpx

from app.errors import SearchError
from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider


class BraveSearchProvider(SearchProvider):
    """Search provider using Brave Search API."""

    def __init__(self, api_key: str, *, base_url: str = "https://api.search.brave.com") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
        )

    @property
    def name(self) -> str:
        return "brave"

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        max_results: int = 20,
    ) -> list[SearchResult]:
        all_results: list[SearchResult] = []

        for query in queries:
            try:
                results = await self._search_single(query, max_results=max_results)
                all_results.extend(results)
            except httpx.TimeoutException:
                raise SearchError(f"Brave Search timeout for query: {query.query}") from None
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise SearchError("Brave Search rate limit exceeded") from None
                raise SearchError(f"Brave Search HTTP error: {e.response.status_code}") from None
            except httpx.HTTPError as e:
                raise SearchError(f"Brave Search error: {e}") from None

        return all_results[:max_results]

    async def _search_single(
        self,
        query: SearchQuery,
        *,
        max_results: int = 10,
    ) -> list[SearchResult]:
        response = await self._client.get(
            f"{self._base_url}/res/v1/web/search",
            params={
                "q": query.query,
                "count": min(max_results, 20),
            },
        )
        response.raise_for_status()
        data = response.json()

        results: list[SearchResult] = []
        web_results = data.get("web", {}).get("results", [])

        for i, item in enumerate(web_results):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", ""),
                    source_provider=self.name,
                    rank=i + 1,
                )
            )

        return results

    async def close(self) -> None:
        await self._client.aclose()
