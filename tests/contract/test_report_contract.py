"""Contract tests: Markdown report structure.

These tests verify that the rendered Markdown report always contains
the required sections and that citations are consistent.
"""

from __future__ import annotations

import re

import pytest

from app.config import AppConfig
from app.fetch.http_fetcher import FakeFetcher
from app.report.citations import validate_citations
from app.report.markdown_report import render, render_error, render_no_evidence
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


def _build_engine() -> ResearchEngine:
    cfg = _default_config()
    return ResearchEngine(
        config=cfg,
        search_provider=FakeSearchProvider(),
        fetcher=FakeFetcher(),
        synthesizer=ExtractiveSynthesizer(),
    )


# ── Required sections ───────────────────────────────────────────────────────


@pytest.mark.contract
@pytest.mark.anyio
async def test_report_has_summary_section():
    """The Markdown report contains a Summary section."""
    engine = _build_engine()
    md = await engine.run_markdown(query="MCP protocol")
    assert "## Summary" in md


@pytest.mark.contract
@pytest.mark.anyio
async def test_report_has_key_findings_section():
    """The Markdown report contains Key Findings section when sources are found."""
    engine = _build_engine()
    report = await engine.run(query="MCP protocol")
    md = render(report)

    if report.findings:
        assert "## Key Findings" in md
        # Each finding is numbered
        for i, _ in enumerate(report.findings, start=1):
            assert f"{i}." in md


@pytest.mark.contract
@pytest.mark.anyio
async def test_report_has_sources_section():
    """The Markdown report contains a Sources section when citations exist."""
    engine = _build_engine()
    report = await engine.run(query="MCP protocol")
    md = render(report)

    if report.citations:
        assert "## Sources" in md


@pytest.mark.contract
@pytest.mark.anyio
async def test_report_has_limitations_section():
    """The Markdown report always contains a Limitations section."""
    engine = _build_engine()
    md = await engine.run_markdown(query="MCP protocol")
    assert "## Limitations" in md


# ── Citation consistency ────────────────────────────────────────────────────


@pytest.mark.contract
@pytest.mark.anyio
async def test_every_bracket_ref_exists_in_sources():
    """Every [n] reference in the Markdown body exists in the Sources section."""
    engine = _build_engine()
    report = await engine.run(query="MCP protocol")
    md = render(report)

    if not report.citations:
        pytest.skip("No citations in report")

    # Extract all source IDs from the Sources section
    source_ids_in_section = set()
    for citation in report.citations:
        source_ids_in_section.add(citation.source_id)

    # Extract all [n] references from the Key Findings section
    refs_in_body = re.findall(r"\[(\d+)\]", md)

    for ref_str in refs_in_body:
        ref_id = int(ref_str)
        assert ref_id in source_ids_in_section, (
            f"Reference [{ref_id}] in body not found in Sources section"
        )


@pytest.mark.contract
@pytest.mark.anyio
async def test_every_source_is_referenced_in_body():
    """Every source listed in Sources should be referenced at least once in the body."""
    engine = _build_engine()
    report = await engine.run(query="MCP protocol")
    md = render(report)

    if not report.citations:
        pytest.skip("No citations in report")

    # Collect all [n] references from the full Markdown
    refs_in_body = {int(r) for r in re.findall(r"\[(\d+)\]", md)}

    for citation in report.citations:
        assert citation.source_id in refs_in_body, (
            f"Source [{citation.source_id}] listed in Sources but never referenced in body"
        )


# ── render_no_evidence contract ──────────────────────────────────────────────


@pytest.mark.contract
def test_render_no_evidence_has_required_sections():
    """render_no_evidence includes Summary and Limitations."""
    md = render_no_evidence("test query")
    assert "# Deep Research Report" in md
    assert "**Query:** test query" in md
    assert "## Summary" in md
    assert "## Limitations" in md


# ── render_error contract ────────────────────────────────────────────────────


@pytest.mark.contract
def test_render_error_has_error_section():
    """render_error includes an Error section."""
    md = render_error("test query", "Something went wrong")
    assert "# Deep Research Report" in md
    assert "**Query:** test query" in md
    assert "## Error" in md
    assert "Something went wrong" in md


# ── validate_citations utility ──────────────────────────────────────────────


@pytest.mark.contract
def test_validate_citations_detects_invalid_refs():
    """validate_citations returns warnings for invalid references."""
    from app.models import Citation

    citations = [
        Citation(source_id=1, title="Source 1", url="https://example.com/1", domain="example.com"),
        Citation(source_id=2, title="Source 2", url="https://example.com/2", domain="example.com"),
    ]
    body = "Some text [1] and [3] references."

    warnings = validate_citations(body, citations)
    assert len(warnings) == 1
    assert "[3]" in warnings[0]


@pytest.mark.contract
def test_validate_citations_no_warnings_for_valid_refs():
    """validate_citations returns no warnings when all references are valid."""
    from app.models import Citation

    citations = [
        Citation(source_id=1, title="Source 1", url="https://example.com/1", domain="example.com"),
        Citation(source_id=2, title="Source 2", url="https://example.com/2", domain="example.com"),
    ]
    body = "Some text [1] and [2] references."

    warnings = validate_citations(body, citations)
    assert len(warnings) == 0
