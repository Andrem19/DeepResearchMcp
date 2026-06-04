"""Fake search provider for testing. Returns fixture data or constructor-injected results."""

from __future__ import annotations

from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider


class FakeSearchProvider(SearchProvider):
    """Search provider that returns pre-configured results for testing."""

    def __init__(
        self,
        results: list[SearchResult] | None = None,
        *,
        fail: bool = False,
        error_message: str = "Fake search provider error",
    ) -> None:
        self._results = results if results is not None else self._default_results()
        self._fail = fail
        self._error_message = error_message

    @property
    def name(self) -> str:
        return "fake"

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        max_results: int = 20,
    ) -> list[SearchResult]:
        if self._fail:
            from app.errors import SearchError

            raise SearchError(self._error_message)

        return self._results[:max_results]

    @staticmethod
    def _default_results() -> list[SearchResult]:
        """Provide sensible default fake results."""
        return [
            SearchResult(
                title="Introduction to MCP Protocol",
                url="https://example.com/mcp-intro",
                snippet="Model Context Protocol enables communication between AI models and tools.",
                source_provider="fake",
                rank=1,
            ),
            SearchResult(
                title="MCP Streamable HTTP Transport",
                url="https://example.com/mcp-streamable-http",
                snippet="Streamable HTTP transport for MCP allows stateless server deployments.",
                source_provider="fake",
                rank=2,
            ),
            SearchResult(
                title="FastMCP Documentation",
                url="https://example.com/fastmcp-docs",
                snippet="FastMCP is a Python framework for building MCP servers quickly.",
                source_provider="fake",
                rank=3,
            ),
        ]
