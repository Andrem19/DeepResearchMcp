"""Integration tests: MCP tool contract via engine.run_markdown().

FastMCP in-process tool testing is complex, so we test the same code path
that the MCP tool handler uses: engine.run_markdown().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.config import AppConfig
from app.fetch.http_fetcher import FakeFetcher
from app.research_engine import ResearchEngine
from app.search.fake import FakeSearchProvider
from app.synthesize.extractive import ExtractiveSynthesizer

if TYPE_CHECKING:
    from app.models import SearchResult


def _default_config() -> AppConfig:
    return AppConfig(
        total_research_timeout_seconds=60.0,
        max_sources_hard_limit=20,
        max_fetch_concurrency=5,
        max_report_length=15_000,
    )


def _build_engine(
    *,
    search_results: list[SearchResult] | None = None,
    search_fail: bool = False,
) -> ResearchEngine:
    cfg = _default_config()
    search = FakeSearchProvider(results=search_results, fail=search_fail)
    fetcher = FakeFetcher()
    synthesizer = ExtractiveSynthesizer()
    return ResearchEngine(config=cfg, search_provider=search, fetcher=fetcher, synthesizer=synthesizer)


class _EmptyFakeSearchProvider(FakeSearchProvider):
    """Search provider that always returns zero results."""

    async def search(self, queries, *, max_results=20):
        if self._fail:
            from app.errors import SearchError
            raise SearchError(self._error_message)
        return []


def _build_empty_engine() -> ResearchEngine:
    """Build an engine whose search provider always returns zero results."""
    cfg = _default_config()
    search = _EmptyFakeSearchProvider()
    fetcher = FakeFetcher()
    synthesizer = ExtractiveSynthesizer()
    return ResearchEngine(config=cfg, search_provider=search, fetcher=fetcher, synthesizer=synthesizer)


# ── Markdown output ─────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_deep_research_returns_markdown_string():
    """The engine.run_markdown() call (same path as MCP tool) returns a Markdown string."""
    engine = _build_engine()
    result = await engine.run_markdown(query="MCP protocol")

    assert isinstance(result, str)
    assert len(result) > 0
    assert result.startswith("# Deep Research Report")


@pytest.mark.integration
@pytest.mark.anyio
async def test_markdown_output_has_required_sections():
    """The Markdown output contains all required top-level sections."""
    engine = _build_engine()
    result = await engine.run_markdown(query="MCP protocol")

    assert "## Summary" in result
    assert "## Sources" in result
    assert "## Limitations" in result


@pytest.mark.integration
@pytest.mark.anyio
async def test_markdown_output_has_query_metadata():
    """The Markdown output includes query metadata."""
    engine = _build_engine()
    result = await engine.run_markdown(query="MCP protocol", depth="deep")

    assert "**Query:** MCP protocol" in result
    assert "**Depth:** deep" in result
    assert "**Sources:**" in result


# ── Error handling returns error Markdown ────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_error_handling_returns_error_markdown():
    """When search fails, run_markdown returns a Markdown error message."""
    engine = _build_engine(search_fail=True)
    result = await engine.run_markdown(query="anything")

    assert isinstance(result, str)
    assert "# Deep Research Report" in result
    assert "## Error" in result
    assert "Unable to complete research" in result


@pytest.mark.integration
@pytest.mark.anyio
async def test_no_evidence_returns_no_evidence_markdown():
    """When no sources are found, run_markdown returns the no-evidence Markdown."""
    engine = _build_empty_engine()
    result = await engine.run_markdown(query="xyzzy nothing")

    assert isinstance(result, str)
    assert "# Deep Research Report" in result
    assert "No relevant sources were found" in result
