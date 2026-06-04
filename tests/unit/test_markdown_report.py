"""Unit tests for app.report.markdown_report — render, render_error, render_no_evidence."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models import Citation, ResearchFinding, ResearchReport
from app.report.markdown_report import render, render_error, render_no_evidence

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _report(**overrides) -> ResearchReport:
    defaults = {
        "query": "What is Python?",
        "depth": "standard",
        "summary": "Python is a programming language.",
        "findings": [
            ResearchFinding(
                statement="Python is widely used.",
                evidence_ids=[1],
                confidence=0.9,
            ),
        ],
        "citations": [
            Citation(source_id=1, title="Python Docs", url="https://docs.python.org", domain="docs.python.org"),
        ],
        "limitations": ["Limited to web sources."],
        "source_count": 1,
        "generated_at": datetime(2025, 1, 15, 12, 0, tzinfo=UTC),
        "research_duration_seconds": 3.5,
    }
    defaults.update(overrides)
    return ResearchReport(**defaults)


# ---------------------------------------------------------------------------
# render — required sections
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_contains_header():
    report = _report()
    md = render(report)
    assert "# Deep Research Report" in md


@pytest.mark.unit
def test_render_contains_query():
    report = _report()
    md = render(report)
    assert "**Query:** What is Python?" in md


@pytest.mark.unit
def test_render_contains_depth():
    report = _report()
    md = render(report)
    assert "**Depth:** standard" in md


@pytest.mark.unit
def test_render_contains_sources_count():
    report = _report()
    md = render(report)
    assert "**Sources:** 1" in md


@pytest.mark.unit
def test_render_contains_summary():
    report = _report()
    md = render(report)
    assert "## Summary" in md
    assert "Python is a programming language." in md


@pytest.mark.unit
def test_render_contains_findings():
    report = _report()
    md = render(report)
    assert "## Key Findings" in md
    assert "Python is widely used." in md


@pytest.mark.unit
def test_render_contains_limitations():
    report = _report()
    md = render(report)
    assert "## Limitations" in md
    assert "Limited to web sources." in md


@pytest.mark.unit
def test_render_contains_sources_section():
    report = _report()
    md = render(report)
    assert "## Sources" in md
    assert "[1] Python Docs" in md


@pytest.mark.unit
def test_render_contains_duration():
    report = _report()
    md = render(report)
    assert "**Duration:** 3.5s" in md


# ---------------------------------------------------------------------------
# render — max length truncation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_max_length():
    # Create a report with a very long summary
    long_summary = "Word " * 20_000
    report = _report(summary=long_summary)
    md = render(report, max_length=500)
    assert len(md) <= 500
    assert "truncated" in md.lower()


# ---------------------------------------------------------------------------
# render — empty sections omitted
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_no_summary():
    report = _report(summary="")
    md = render(report)
    assert "## Summary" not in md


@pytest.mark.unit
def test_render_no_findings():
    report = _report(findings=[], citations=[])
    md = render(report)
    assert "## Key Findings" not in md


# ---------------------------------------------------------------------------
# render_error
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_error_contains_query():
    md = render_error("test query", "something went wrong")
    assert "test query" in md
    assert "## Error" in md
    assert "something went wrong" in md


@pytest.mark.unit
def test_render_error_has_header():
    md = render_error("q", "e")
    assert "# Deep Research Report" in md


# ---------------------------------------------------------------------------
# render_no_evidence
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_render_no_evidence_contains_query():
    md = render_no_evidence("test query")
    assert "test query" in md


@pytest.mark.unit
def test_render_no_evidence_has_summary():
    md = render_no_evidence("q")
    assert "## Summary" in md
    assert "No relevant sources" in md


@pytest.mark.unit
def test_render_no_evidence_has_limitations():
    md = render_no_evidence("q")
    assert "## Limitations" in md
    assert "No sources available" in md
