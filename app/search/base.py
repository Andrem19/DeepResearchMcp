"""Abstract search provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import SearchQuery, SearchResult


class SearchProvider(ABC):
    """Interface for search providers.

    Implementations must not fetch pages or do synthesis.
    They return search results (title, url, snippet) only.
    """

    @abstractmethod
    async def search(
        self,
        queries: list[SearchQuery],
        *,
        max_results: int = 20,
    ) -> list[SearchResult]:
        """Execute search queries and return deduplicated results.

        Args:
            queries: Search queries to execute.
            max_results: Maximum number of results to return.

        Returns:
            List of SearchResult objects.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name for logging."""
