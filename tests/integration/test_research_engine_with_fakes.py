"""Integration tests: full ResearchEngine pipeline using fake providers.

All tests are offline — no network, no API keys.
"""

from __future__ import annotations

import asyncio

import pytest

from app.config import AppConfig
from app.errors import SearchError
from app.errors import TimeoutError as ResearchTimeoutError
from app.fetch.http_fetcher import FakeFetcher
from app.models import ResearchReport, SearchResult
from app.research_engine import ResearchEngine
from app.search.fake import FakeSearchProvider
from app.synthesize.extractive import ExtractiveSynthesizer


def _default_config(**overrides) -> AppConfig:
    """Create a test AppConfig with sensible defaults."""
    defaults = dict(
        total_research_timeout_seconds=60.0,
        max_sources_hard_limit=20,
        max_fetch_concurrency=5,
        max_report_length=15_000,
        blocked_domains=[],
        allowed_domains=[],
    )
    defaults.update(overrides)
    return AppConfig(**defaults)


def _build_engine(
    *,
    config: AppConfig | None = None,
    search_results: list[SearchResult] | None = None,
    search_fail: bool = False,
    fail_urls: set[str] | None = None,
    pages: dict[str, bytes] | None = None,
) -> ResearchEngine:
    """Build a ResearchEngine with fake providers for testing.

    Note: FakeSearchProvider(results=[]) falls back to default results because
    the constructor uses `results or self._default_results()` (empty list is falsy).
    To get zero results, we must pass results=[None] and override, or use a subclass.
    Instead, use _build_empty_search_engine() for zero-source tests.
    """
    cfg = config or _default_config()
    search = FakeSearchProvider(results=search_results, fail=search_fail)
    fetcher = FakeFetcher(pages=pages, fail_urls=fail_urls)
    synthesizer = ExtractiveSynthesizer()
    return ResearchEngine(
        config=cfg,
        search_provider=search,
        fetcher=fetcher,
        synthesizer=synthesizer,
    )


class _EmptyFakeSearchProvider(FakeSearchProvider):
    """Search provider that always returns zero results (overrides default fallback)."""

    async def search(self, queries, *, max_results=20):
        if self._fail:
            from app.errors import SearchError
            raise SearchError(self._error_message)
        return []


def _build_empty_search_engine(
    *,
    config: AppConfig | None = None,
) -> ResearchEngine:
    """Build an engine whose search provider always returns zero results."""
    cfg = config or _default_config()
    search = _EmptyFakeSearchProvider()
    fetcher = FakeFetcher()
    synthesizer = ExtractiveSynthesizer()
    return ResearchEngine(
        config=cfg,
        search_provider=search,
        fetcher=fetcher,
        synthesizer=synthesizer,
    )


# ── Happy path ──────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_happy_path_full_report():
    """FakeSearchProvider + FakeFetcher + ExtractiveSynthesizer produces a report with findings and citations."""
    engine = _build_engine()
    report = await engine.run(query="MCP protocol overview")

    assert isinstance(report, ResearchReport)
    assert report.query == "MCP protocol overview"
    assert report.depth == "standard"
    assert report.source_count > 0
    assert len(report.findings) > 0
    assert len(report.citations) > 0
    assert report.summary
    assert report.research_duration_seconds >= 0


@pytest.mark.integration
@pytest.mark.anyio
async def test_happy_path_run_markdown():
    """run_markdown returns a non-empty Markdown string with expected sections."""
    engine = _build_engine()
    md = await engine.run_markdown(query="MCP protocol")

    assert isinstance(md, str)
    assert "# Deep Research Report" in md
    assert "**Query:** MCP protocol" in md
    assert "## Summary" in md
    assert "## Sources" in md


# ── Search provider failure ─────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_search_provider_failure_returns_error_markdown():
    """When the search provider fails, run_markdown returns an error Markdown string."""
    engine = _build_engine(search_fail=True)
    md = await engine.run_markdown(query="anything")

    assert isinstance(md, str)
    assert "# Deep Research Report" in md
    assert "## Error" in md


@pytest.mark.integration
@pytest.mark.anyio
async def test_search_provider_failure_run_raises():
    """When the search provider fails, run() raises SearchError."""
    engine = _build_engine(search_fail=True)
    with pytest.raises(SearchError):
        await engine.run(query="anything")


# ── Zero sources ────────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_zero_sources_returns_no_evidence_report():
    """When search returns zero results, report has source_count=0 and 'not enough evidence' output."""
    engine = _build_empty_search_engine()
    report = await engine.run(query="obscure non-existent topic xyzzy")

    assert isinstance(report, ResearchReport)
    assert report.source_count == 0
    assert len(report.findings) == 0
    assert len(report.citations) == 0
    assert "No relevant sources" in report.summary or "No sources" in report.summary


@pytest.mark.integration
@pytest.mark.anyio
async def test_zero_sources_run_markdown_returns_no_evidence():
    """run_markdown returns the no-evidence Markdown when no sources are found."""
    engine = _build_empty_search_engine()
    md = await engine.run_markdown(query="obscure topic xyzzy")

    assert "# Deep Research Report" in md
    assert "No relevant sources were found" in md


# ── max_sources respected ──────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_max_sources_is_respected():
    """The report should not cite more sources than max_sources."""
    engine = _build_engine()
    report = await engine.run(query="MCP protocol", max_sources=2)

    assert report.source_count <= 2
    assert len(report.citations) <= 2


@pytest.mark.integration
@pytest.mark.anyio
async def test_max_sources_clamped_by_config():
    """max_sources is clamped by config.max_sources_hard_limit."""
    config = _default_config(max_sources_hard_limit=1)
    engine = _build_engine(config=config)
    report = await engine.run(query="MCP protocol", max_sources=100)

    assert report.source_count <= 1
    assert len(report.citations) <= 1


# ── Timeout (mocked) ────────────────────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_timeout_returns_error_markdown():
    """When the pipeline times out, run_markdown returns an error Markdown string.

    We simulate timeout by patching _run_pipeline to hang and setting a tiny timeout.
    """
    config = _default_config(total_research_timeout_seconds=0.01)
    engine = _build_engine(config=config)

    # Patch the search provider to sleep longer than the timeout
    original_search = engine._search.search

    async def _slow_search(queries, *, max_results=20):
        await asyncio.sleep(10)  # sleep far longer than timeout
        return await original_search(queries, max_results=max_results)

    engine._search.search = _slow_search

    md = await engine.run_markdown(query="slow query")
    assert "# Deep Research Report" in md
    assert "## Error" in md


@pytest.mark.integration
@pytest.mark.anyio
async def test_timeout_run_raises():
    """When the pipeline times out, run() raises TimeoutError."""
    config = _default_config(total_research_timeout_seconds=0.01)
    engine = _build_engine(config=config)

    original_search = engine._search.search

    async def _slow_search(queries, *, max_results=20):
        await asyncio.sleep(10)
        return await original_search(queries, max_results=max_results)

    engine._search.search = _slow_search

    with pytest.raises(ResearchTimeoutError):
        await engine.run(query="slow query")
