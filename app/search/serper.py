"""Serper (Google Search) API provider."""

from __future__ import annotations

import httpx

from app.errors import SearchError
from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider


class SerperSearchProvider(SearchProvider):
    """Search provider using Serper.dev Google Search API."""

    def __init__(self, api_key: str, *, base_url: str = "https://google.serper.dev") -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(10.0),
            headers={"X-API-KEY": api_key},
        )

    @property
    def name(self) -> str:
        return "serper"

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
                raise SearchError(f"Serper timeout for query: {query.query}") from None
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    raise SearchError("Serper rate limit exceeded") from None
                raise SearchError(f"Serper HTTP error: {e.response.status_code}") from None
            except httpx.HTTPError as e:
                raise SearchError(f"Serper error: {e}") from None

        return all_results[:max_results]

    async def _search_single(
        self,
        query: SearchQuery,
        *,
        max_results: int = 10,
    ) -> list[SearchResult]:
        response = await self._client.post(
            f"{self._base_url}/search",
            json={"q": query.query, "num": min(max_results, 10)},
        )
        response.raise_for_status()
        data = response.json()

        results: list[SearchResult] = []
        for i, item in enumerate(data.get("organic", [])):
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("link", ""),
                    snippet=item.get("snippet", ""),
                    source_provider=self.name,
                    rank=i + 1,
                )
            )

        return results

    async def close(self) -> None:
        await self._client.aclose()
