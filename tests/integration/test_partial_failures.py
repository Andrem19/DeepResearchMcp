"""Integration tests: partial failures in the pipeline.

Some URLs fail to fetch, but the report is still generated with limitations.
"""

from __future__ import annotations

import pytest

from app.config import AppConfig
from app.fetch.http_fetcher import FakeFetcher
from app.models import ResearchReport, SearchResult
from app.research_engine import ResearchEngine
from app.search.fake import FakeSearchProvider
from app.synthesize.extractive import ExtractiveSynthesizer


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
    fail_urls: set[str] | None = None,
    pages: dict[str, bytes] | None = None,
) -> ResearchEngine:
    cfg = _default_config()
    search = FakeSearchProvider(results=search_results)
    fetcher = FakeFetcher(pages=pages, fail_urls=fail_urls)
    synthesizer = ExtractiveSynthesizer()
    return ResearchEngine(config=cfg, search_provider=search, fetcher=fetcher, synthesizer=synthesizer)


# ── Partial fetch failures ──────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_some_urls_fail_report_still_generated():
    """When some URLs fail to fetch, the report is still generated."""
    # Use default 3 results, but fail one URL
    engine = _build_engine(fail_urls={"https://example.com/mcp-intro"})
    report = await engine.run(query="MCP protocol")

    assert isinstance(report, ResearchReport)
    assert report.source_count > 0
    assert len(report.findings) > 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_some_urls_fail_limitations_mentioned():
    """When fetch failures occur, limitations mention failed sources."""
    engine = _build_engine(fail_urls={"https://example.com/mcp-intro"})
    report = await engine.run(query="MCP protocol")

    # The pipeline tracks failed fetches and adds to limitations
    assert any("could not be fetched" in lim or "source(s)" in lim.lower() for lim in report.limitations)


@pytest.mark.integration
@pytest.mark.anyio
async def test_all_urls_fail_returns_empty_report():
    """When all URLs fail, the report has source_count=0."""
    engine = _build_engine(
        fail_urls={
            "https://example.com/mcp-intro",
            "https://example.com/mcp-streamable-http",
            "https://example.com/fastmcp-docs",
        }
    )
    report = await engine.run(query="MCP protocol")

    assert report.source_count == 0
    assert len(report.findings) == 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_partial_failure_markdown_still_valid():
    """run_markdown returns a valid report even with partial fetch failures."""
    engine = _build_engine(fail_urls={"https://example.com/mcp-intro"})
    md = await engine.run_markdown(query="MCP protocol")

    assert "# Deep Research Report" in md
    assert "## Summary" in md


@pytest.mark.integration
@pytest.mark.anyio
async def test_custom_pages_with_some_failures():
    """Engine works with custom page content and partial failures."""
    custom_results = [
        SearchResult(title="Page A", url="https://example.com/a", snippet="Page A content", rank=1),
        SearchResult(title="Page B", url="https://example.com/b", snippet="Page B content", rank=2),
        SearchResult(title="Page C", url="https://example.com/c", snippet="Page C content", rank=3),
    ]
    custom_pages = {
        "https://example.com/a": b"<html><body><p>Content for page A about research.</p></body></html>",
        "https://example.com/b": b"<html><body><p>Content for page B about analysis.</p></body></html>",
        # Page C has no page content — will get 404
    }
    engine = _build_engine(
        search_results=custom_results,
        pages=custom_pages,
    )
    report = await engine.run(query="research analysis")

    assert report.source_count > 0
    # At least one source should be from A or B
    assert any("example.com" in c.url for c in report.citations)
