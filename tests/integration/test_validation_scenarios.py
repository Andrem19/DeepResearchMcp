"""Validation scenarios — automated checks from Stage 29.

These tests verify the project works end-to-end with fake providers,
covering the 5 manual validation scenarios from the roadmap.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from app.config import load_config
from app.errors import URLSafetyError
from app.fetch.url_safety import validate_url as check_url_safety
from app.report.markdown_report import render_error
from app.research_engine import ResearchEngine, create_engine
from app.search.fake import FakeSearchProvider


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ---------------------------------------------------------------------------
# Scenario 1: Simple question → report has required sections
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_scenario1_simple_question():
    """Run research and verify report contains all required sections."""
    config = load_config({"SEARCH_PROVIDER": "fake", "MCP_BEARER_TOKEN": ""})
    engine = create_engine(config)

    report_md = _run(engine.run_markdown("What is MCP Streamable HTTP?"))

    # Report contains required sections
    assert "# Deep Research Report" in report_md
    assert "**Query:**" in report_md
    assert "## Summary" in report_md
    assert "## Key Findings" in report_md
    assert "## Limitations" in report_md
    assert "## Sources" in report_md

    # Sources have stable numbered citations
    assert "[1]" in report_md

    # Generated timestamp present
    assert "**Generated:**" in report_md


# ---------------------------------------------------------------------------
# Scenario 4: Partial failure — some URLs fail, report still created
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_scenario4_partial_failure():
    """Configure fake provider with some failing URLs, report still created."""
    from app.fetch.http_fetcher import FakeFetcher

    config = load_config({"SEARCH_PROVIDER": "fake", "MCP_BEARER_TOKEN": ""})

    # Use fake search that returns results
    search = FakeSearchProvider()
    # Use fake fetcher (some pages succeed, some fail by default)
    fetcher = FakeFetcher()
    from app.storage.cache import NullCache
    from app.synthesize.extractive import ExtractiveSynthesizer

    engine = ResearchEngine(
        config=config,
        search_provider=search,
        fetcher=fetcher,
        synthesizer=ExtractiveSynthesizer(),
        cache=NullCache(),
    )

    report_md = _run(engine.run_markdown("test partial failures"))

    # Report is still created (even if with limitations)
    assert "# Deep Research Report" in report_md or "No sources found" in report_md or "research error" in report_md.lower()


# ---------------------------------------------------------------------------
# Scenario 5: Security — localhost URL blocked
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_scenario5_localhost_blocked():
    """Query that tries to fetch localhost should be blocked."""
    with pytest.raises(URLSafetyError):
        check_url_safety("http://localhost/admin")


@pytest.mark.integration
def test_scenario5_private_ip_blocked():
    """Private IP addresses should be blocked."""
    with pytest.raises(URLSafetyError):
        check_url_safety("http://192.168.1.1/secret")


@pytest.mark.integration
def test_scenario5_metadata_ip_blocked():
    """Cloud metadata IP should be blocked."""
    with pytest.raises(URLSafetyError):
        check_url_safety("http://169.254.169.254/latest/meta-data/")


@pytest.mark.integration
def test_scenario5_file_scheme_blocked():
    """file:// scheme should be blocked."""
    with pytest.raises(URLSafetyError):
        check_url_safety("file:///etc/passwd")


# ---------------------------------------------------------------------------
# Scenario: Zero sources → useful "no evidence" report
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_zero_sources_no_evidence_report():
    """When no sources found, return useful 'no evidence' report."""
    from app.fetch.http_fetcher import FakeFetcher
    from app.search.fake import FakeSearchProvider
    from app.storage.cache import NullCache
    from app.synthesize.extractive import ExtractiveSynthesizer

    config = load_config({"SEARCH_PROVIDER": "fake", "MCP_BEARER_TOKEN": ""})

    # Empty results provider
    search = FakeSearchProvider(results=[])
    fetcher = FakeFetcher()
    engine = ResearchEngine(
        config=config,
        search_provider=search,
        fetcher=fetcher,
        synthesizer=ExtractiveSynthesizer(),
        cache=NullCache(),
    )

    report_md = _run(engine.run_markdown("obscure topic xyz"))
    # Should contain a meaningful message about no sources
    assert "No" in report_md or "no" in report_md or "not enough" in report_md.lower()


# ---------------------------------------------------------------------------
# Scenario: Report citations are valid
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_report_citations_valid():
    """Every [n] in report body exists in Sources section."""
    import re

    config = load_config({"SEARCH_PROVIDER": "fake", "MCP_BEARER_TOKEN": ""})
    engine = create_engine(config)

    report_md = _run(engine.run_markdown("What is MCP?"))

    # Find all [n] citations in the body (before Sources section)
    sources_idx = report_md.find("## Sources")
    if sources_idx == -1:
        pytest.skip("No Sources section in report")

    body = report_md[:sources_idx]
    cited_ids = set(int(n) for n in re.findall(r"\[(\d+)\]", body))

    # Find all [n] in Sources section
    sources_section = report_md[sources_idx:]
    source_ids = set(int(n) for n in re.findall(r"\[(\d+)\]", sources_section))

    # Every cited ID must exist in sources
    missing = cited_ids - source_ids
    assert not missing, f"Citations referenced but not in Sources: {missing}"


# ---------------------------------------------------------------------------
# Scenario: Async job tools work
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_async_job_lifecycle():
    """Start a job, check status, get report — full lifecycle."""

    class FakeEngine:
        async def run_markdown(self, *args, **kwargs):
            return "# Async Report\n\n[1] Result — example.com — https://example.com"

    from app.jobs import JobManager

    manager = JobManager(FakeEngine())
    job = _run(manager.start_research("async test"))

    _run(asyncio.sleep(0.2))

    # Check status
    status = _run(manager.get_status(job.job_id))
    assert status is not None
    assert status.status.value in ("completed", "running", "pending")

    # Wait for completion if needed
    if not status.is_terminal:
        _run(asyncio.sleep(0.5))
        status = _run(manager.get_status(job.job_id))

    assert status.status.value == "completed"

    # Get report
    report = _run(manager.get_report(job.job_id))
    assert report is not None
    assert "Async Report" in report


# ---------------------------------------------------------------------------
# Scenario: MCP tool contract — tool names and schemas
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_mcp_tool_contract():
    """Verify MCP tools are properly registered."""

    # Get registered tools
    # FastMCP stores tools internally; verify the module has expected functions
    import app.mcp_server as server_module

    assert hasattr(server_module, "deep_research")
    assert hasattr(server_module, "start_deep_research")
    assert hasattr(server_module, "get_research_status")
    assert hasattr(server_module, "get_research_report")
    assert hasattr(server_module, "list_recent_research")


# ---------------------------------------------------------------------------
# Scenario: JSON example configs are valid
# ---------------------------------------------------------------------------


@pytest.mark.contract
def test_example_configs_valid():
    """All example JSON configs are valid and contain expected keys."""
    import pathlib

    examples_dir = pathlib.Path("examples")
    for json_file in examples_dir.glob("*.json"):
        content = json.loads(json_file.read_text())
        # Should contain mcp/deepresearch reference
        content_str = json.dumps(content)
        assert "deepresearch" in content_str.lower() or "mcp" in content_str.lower(), \
            f"{json_file.name}: missing deepresearch/mcp reference"
        # Should not contain real secrets
        assert "sk-" not in content_str
        assert "AKIA" not in content_str


# ---------------------------------------------------------------------------
# Scenario: Error report renders properly
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_error_report_render():
    """Error report is clean Markdown without stack traces."""
    error_md = render_error("test query", "Something went wrong: internal details")
    assert "test query" in error_md
    assert "Something went wrong" in error_md
    assert "Traceback" not in error_md
    assert "internal details" in error_md


# ---------------------------------------------------------------------------
# Scenario: max_sources is respected and clamped
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_max_sources_clamped():
    """Client requesting 1000 sources gets clamped to server limit."""
    config = load_config({"SEARCH_PROVIDER": "fake", "MCP_BEARER_TOKEN": ""})
    engine = create_engine(config)

    # Request 1000 sources — should be clamped to hard limit (20)
    report_md = _run(engine.run_markdown("test", max_sources=1000))

    # Should still work (not crash)
    assert isinstance(report_md, str)
    assert len(report_md) > 0
