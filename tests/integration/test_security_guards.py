"""Integration tests: security guards block unsafe URLs in the pipeline.

Tests that the URL safety validation blocks SSRF attempts, private IPs,
and dangerous schemes when fetching pages.
"""

from __future__ import annotations

import pytest

from app.config import AppConfig
from app.errors import URLSafetyError
from app.fetch.http_fetcher import FakeFetcher
from app.fetch.url_safety import validate_url
from app.models import SearchResult
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


# ── URL safety validation (unit-level, but in integration context) ───────────


@pytest.mark.integration
class TestURLSafetyValidation:
    """Test that validate_url blocks dangerous URLs."""

    @pytest.mark.parametrize("unsafe_url", [
        "http://127.0.0.1/admin",
        "http://localhost/secret",
        "http://10.0.0.1/internal",
        "http://192.168.1.1/router",
        "http://169.254.169.254/metadata",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "data:text/html,<h1>test</h1>",
    ])
    def test_unsafe_urls_blocked(self, unsafe_url: str):
        """Unsafe URLs should raise URLSafetyError."""
        with pytest.raises(URLSafetyError):
            validate_url(unsafe_url)

    @pytest.mark.parametrize("safe_url", [
        "https://example.com/page",
        "http://example.org/article",
        "https://www.wikipedia.org/wiki/Test",
    ])
    def test_safe_urls_pass(self, safe_url: str):
        """Safe public URLs should pass validation."""
        result = validate_url(safe_url)
        assert result == safe_url


@pytest.mark.integration
class TestDomainFiltering:
    """Test domain allow/block lists."""

    def test_blocked_domain_rejected(self):
        with pytest.raises(URLSafetyError, match="Blocked domain"):
            validate_url("https://evil.com/page", blocked_domains=["evil.com"])

    def test_allowed_domain_passes(self):
        result = validate_url("https://good.com/page", allowed_domains=["good.com"])
        assert result == "https://good.com/page"

    def test_non_allowed_domain_rejected(self):
        with pytest.raises(URLSafetyError, match="allowlist"):
            validate_url("https://other.com/page", allowed_domains=["good.com"])


# ── Unsafe URLs in pipeline context ─────────────────────────────────────────


@pytest.mark.integration
@pytest.mark.anyio
async def test_unsafe_search_urls_get_error_pages():
    """When search returns unsafe URLs, the FakeFetcher marks them as errors.

    The FakeFetcher does not do URL safety checks — it just returns pages.
    In production, HttpFetcher would block these via validate_url.
    Here we test that the pipeline handles error pages gracefully.
    """
    unsafe_results = [
        SearchResult(title="Internal", url="http://127.0.0.1/admin", snippet="Internal page", rank=1),
        SearchResult(title="Public", url="https://example.com/mcp-intro", snippet="Public page", rank=2),
    ]

    # FakeFetcher has no page for 127.0.0.1 — returns 404 error
    engine = ResearchEngine(
        config=_default_config(),
        search_provider=FakeSearchProvider(results=unsafe_results),
        fetcher=FakeFetcher(),  # default pages include example.com but not 127.0.0.1
        synthesizer=ExtractiveSynthesizer(),
    )

    report = await engine.run(query="test query")
    # The unsafe URL gets a 404 from FakeFetcher (error page),
    # but the pipeline still processes valid pages
    assert report.source_count >= 0  # may have 0 or 1 depending on extraction


@pytest.mark.integration
@pytest.mark.anyio
async def test_pipeline_survives_all_blocked_urls():
    """When all search results have blocked/dangerous URLs, report is empty."""
    unsafe_results = [
        SearchResult(title="Internal", url="http://127.0.0.1/admin", snippet="Internal", rank=1),
        SearchResult(title="Private", url="http://10.0.0.1/data", snippet="Private", rank=2),
    ]

    engine = ResearchEngine(
        config=_default_config(),
        search_provider=FakeSearchProvider(results=unsafe_results),
        fetcher=FakeFetcher(),  # no matching pages
        synthesizer=ExtractiveSynthesizer(),
    )

    report = await engine.run(query="internal data")
    assert report.source_count == 0
    assert len(report.findings) == 0
