"""Research Engine — central orchestrator for the deep research pipeline.

All dependencies are injected via constructor for testability.
The engine coordinates: planning -> search -> dedupe -> fetch -> extract -> rank -> synthesize -> report.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

from app.config import AppConfig, clamp_max_sources
from app.errors import ResearchError, ValidationError
from app.errors import TimeoutError as ResearchTimeoutError
from app.extract.html_extractor import extract as extract_content
from app.extract.text_cleaner import remove_boilerplate_paragraphs
from app.fetch.http_fetcher import HttpFetcher
from app.models import (
    ExtractedDocument,
    FetchedPage,
    RankedSource,
    ResearchReport,
)
from app.observability.logging import log_stage
from app.observability.metrics import metrics
from app.planning.query_planner import plan_queries
from app.rank.dedupe import deduplicate
from app.rank.source_ranker import rank as rank_sources
from app.report.citations import build_citations
from app.report.markdown_report import render, render_error, render_no_evidence
from app.storage.cache import NullCache, ResearchCache

if TYPE_CHECKING:
    from app.search.base import SearchProvider
    from app.synthesize.base import Synthesizer


class _Fetcher(Protocol):
    async def fetch(self, url: str) -> FetchedPage: ...
    async def fetch_many(self, urls: list[str], *, max_concurrency: int = 5) -> list[FetchedPage]: ...
    async def close(self) -> None: ...


class ResearchEngine:
    """Orchestrates the full research pipeline.

    Dependencies are injected via constructor.
    Use create_engine() factory for production setup.
    """

    def __init__(
        self,
        config: AppConfig,
        search_provider: SearchProvider,
        fetcher: _Fetcher,
        synthesizer: Synthesizer,
        cache: ResearchCache | None = None,
    ) -> None:
        self._config = config
        self._search = search_provider
        self._fetcher = fetcher
        self._synthesizer = synthesizer
        self._cache = cache or NullCache()

    async def run(self, query: str, depth: str = "standard", max_sources: int = 8,
                  recency_days: int | None = None) -> ResearchReport:
        """Run the full research pipeline.

        Args:
            query: User research query.
            depth: "quick", "standard", or "deep".
            max_sources: Max sources to include (clamped by server).
            recency_days: Optional recency filter.

        Returns:
            ResearchReport with findings, citations, and limitations.
        """
        correlation_id = uuid.uuid4().hex[:8]
        start_time = time.monotonic()

        # Validate
        if not query or not query.strip():
            raise ValidationError("Query must not be empty")

        clamped = clamp_max_sources(max_sources, self._config)
        log_stage("start", correlation_id=correlation_id, extra={"query": query[:100], "depth": depth})

        try:
            return await asyncio.wait_for(
                self._run_pipeline(query, depth, clamped, recency_days, correlation_id, start_time),
                timeout=self._config.total_research_timeout_seconds,
            )
        except TimeoutError:
            raise ResearchTimeoutError(
                f"Research timed out after {self._config.total_research_timeout_seconds}s"
            ) from None

    async def _run_pipeline(
        self,
        query: str,
        depth: str,
        max_sources: int,
        recency_days: int | None,
        correlation_id: str,
        start_time: float,
    ) -> ResearchReport:
        """Execute all pipeline stages."""

        # 1. Plan search queries
        t0 = time.monotonic()
        queries = plan_queries(query, depth)
        log_stage("planning", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(queries))

        # 2. Search
        t0 = time.monotonic()
        search_results = await self._search.search(queries, max_results=max_sources * 3)
        log_stage("search", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(search_results), provider=self._search.name)
        metrics.increment("search.results", len(search_results))

        # 3. Deduplicate
        t0 = time.monotonic()
        deduped = deduplicate(search_results)
        log_stage("dedupe", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(deduped))

        if not deduped:
            return self._empty_report(query, depth, start_time)

        # 4. Fetch pages
        t0 = time.monotonic()
        urls = [r.url for r in deduped[:max_sources * 2]]
        pages = await self._fetcher.fetch_many(
            urls, max_concurrency=self._config.max_fetch_concurrency
        )
        successful_pages = [p for p in pages if p.is_success]
        failed_count = len(pages) - len(successful_pages)
        log_stage("fetch", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(successful_pages), extra={"failed": str(failed_count)})
        metrics.increment("fetch.pages", len(successful_pages))

        # 5. Extract content
        t0 = time.monotonic()
        documents: list[ExtractedDocument] = []
        for page in successful_pages:
            doc = extract_content(page)
            if doc.text:
                # Clean boilerplate paragraphs
                doc.paragraphs = remove_boilerplate_paragraphs(doc.paragraphs)
                documents.append(doc)
        log_stage("extract", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(documents))

        if not documents:
            return self._empty_report(query, depth, start_time)

        # 6. Rank
        t0 = time.monotonic()
        ranked = rank_sources(documents, query, max_results=max_sources, recency_days=recency_days)
        log_stage("rank", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(ranked))

        # 7. Synthesize
        t0 = time.monotonic()
        findings = await self._synthesizer.synthesize(query, ranked)
        log_stage("synthesize", correlation_id=correlation_id, duration_ms=(time.monotonic() - t0) * 1000,
                   count=len(findings))

        # 8. Build citations
        citations = build_citations(ranked)

        # 9. Build report
        limitations = self._build_limitations(findings, ranked, failed_count, recency_days)
        duration = time.monotonic() - start_time

        report = ResearchReport(
            query=query,
            depth=depth,
            summary=self._build_summary(findings, ranked),
            findings=findings,
            citations=citations,
            limitations=limitations,
            source_count=len(ranked),
            generated_at=datetime.now(UTC),
            research_duration_seconds=duration,
        )

        log_stage("complete", correlation_id=correlation_id, duration_ms=duration * 1000,
                   count=len(ranked))
        metrics.increment("research.completed")

        return report

    async def run_markdown(self, query: str, depth: str = "standard", max_sources: int = 8,
                           recency_days: int | None = None) -> str:
        """Run research and return Markdown string. Used by MCP adapter."""
        try:
            report = await self.run(query, depth, max_sources, recency_days)

            if report.source_count == 0:
                return render_no_evidence(query)

            return render(report, max_length=self._config.max_report_length)

        except ValidationError as e:
            return render_error(query, f"Invalid input: {e}")
        except ResearchTimeoutError as e:
            return render_error(query, str(e))
        except ResearchError as e:
            return render_error(query, f"Research error: {e}")

    def _empty_report(self, query: str, depth: str, start_time: float) -> ResearchReport:
        """Create a report for when no sources were found."""
        return ResearchReport(
            query=query,
            depth=depth,
            summary="No relevant sources were found.",
            findings=[],
            citations=[],
            limitations=["No sources found. Try rephrasing the query or using a different depth."],
            source_count=0,
            generated_at=datetime.now(UTC),
            research_duration_seconds=time.monotonic() - start_time,
        )

    def _build_summary(self, findings, ranked: list[RankedSource]) -> str:
        """Build a brief summary from findings."""
        if not findings:
            return "No findings could be extracted from available sources."
        # Take the first finding as summary basis
        return findings[0].statement[:500]

    def _build_limitations(
        self,
        findings,
        ranked: list[RankedSource],
        failed_fetches: int,
        recency_days: int | None,
    ) -> list[str]:
        """Build limitations section content."""
        limitations: list[str] = []

        if len(ranked) < 3:
            limitations.append(
                f"Only {len(ranked)} source(s) found — conclusions may not be comprehensive."
            )

        if failed_fetches > 0:
            limitations.append(
                f"{failed_fetches} source(s) could not be fetched and were excluded."
            )

        if recency_days:
            limitations.append(
                f"Results filtered to sources from the last {recency_days} day(s)."
            )

        low_conf = [f for f in findings if f.confidence < 0.4]
        if low_conf:
            limitations.append(
                f"{len(low_conf)} finding(s) have low confidence due to weak evidence."
            )

        if not limitations:
            limitations.append("This report is based on available sources and may not cover all perspectives.")

        return limitations


def create_engine(config: AppConfig) -> ResearchEngine:
    """Factory: create a ResearchEngine with configured providers."""
    search_provider = _create_search_provider(config)
    fetcher = _create_fetcher(config)
    synthesizer = _create_synthesizer(config)
    cache = _create_cache(config)

    return ResearchEngine(
        config=config,
        search_provider=search_provider,
        fetcher=fetcher,
        synthesizer=synthesizer,
        cache=cache,
    )


def _create_search_provider(config: AppConfig) -> SearchProvider:
    """Create the configured search provider."""
    if config.search_provider == "fake":
        from app.search.fake import FakeSearchProvider
        return FakeSearchProvider()

    if config.search_provider == "duckduckgo":
        from app.search.duckduckgo import DuckDuckGoProvider
        return DuckDuckGoProvider()

    if config.search_provider == "searxng":
        from app.search.searxng import SearXNGProvider
        return SearXNGProvider(base_url=config.searxng_url)

    if config.search_provider == "brave" and config.brave_api_key:
        from app.search.brave import BraveSearchProvider
        return BraveSearchProvider(api_key=config.brave_api_key)

    if config.search_provider == "tavily" and config.tavily_api_key:
        from app.search.tavily import TavilySearchProvider
        return TavilySearchProvider(api_key=config.tavily_api_key)

    if config.search_provider == "serper" and config.serper_api_key:
        from app.search.serper import SerperSearchProvider
        return SerperSearchProvider(api_key=config.serper_api_key)

    # Fallback to fake
    from app.search.fake import FakeSearchProvider
    return FakeSearchProvider()


def _create_fetcher(config: AppConfig) -> _Fetcher:
    """Create the appropriate fetcher based on config."""
    if config.search_provider == "fake":
        from app.fetch.http_fetcher import FakeFetcher

        return FakeFetcher()
    return HttpFetcher(config)


def _create_synthesizer(config: AppConfig) -> Synthesizer:
    """Create the configured synthesizer."""
    if config.llm_provider == "openai" and config.llm_api_key:
        from app.synthesize.llm import LLMSynthesizer

        return LLMSynthesizer(
            api_key=config.llm_api_key,
            api_base=config.llm_api_base or "https://api.openai.com/v1",
            model=config.llm_model or "gpt-4o-mini",
            max_input_chars=config.max_source_chars_to_llm,
        )

    from app.synthesize.extractive import ExtractiveSynthesizer

    return ExtractiveSynthesizer()


def _create_cache(config: AppConfig) -> ResearchCache | None:
    """Create cache if storage is configured."""
    try:
        from app.storage.cache import ResearchCache
        from app.storage.sqlite_store import SQLiteStore
        store = SQLiteStore(config.cache_path)
        return ResearchCache(store)
    except Exception:
        return None
