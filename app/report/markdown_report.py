"""Markdown report renderer — builds the final research report."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.report.citations import format_citation_source

if TYPE_CHECKING:
    from app.models import ResearchReport


def render(report: ResearchReport, *, max_length: int = 15_000) -> str:
    """Render a ResearchReport to Markdown string.

    Args:
        report: The research report to render.
        max_length: Maximum output length in characters.

    Returns:
        Markdown string.
    """
    sections: list[str] = []

    # Header
    sections.append("# Deep Research Report")
    sections.append("")

    # Metadata
    sections.append(f"**Query:** {report.query}")
    sections.append(f"**Depth:** {report.depth}")
    sections.append(f"**Sources:** {report.source_count}")
    sections.append(f"**Generated:** {_format_datetime(report.generated_at)}")
    sections.append(f"**Duration:** {report.research_duration_seconds:.1f}s")
    sections.append("")

    # Summary
    if report.summary:
        sections.append("## Summary")
        sections.append("")
        sections.append(report.summary)
        sections.append("")

    # Key findings
    if report.findings:
        sections.append("## Key Findings")
        sections.append("")
        for i, finding in enumerate(report.findings, start=1):
            refs = " ".join(f"[{eid}]" for eid in finding.evidence_ids)
            sections.append(f"{i}. {finding.statement} {refs}")
        sections.append("")

    # Limitations
    if report.limitations:
        sections.append("## Limitations")
        sections.append("")
        for lim in report.limitations:
            sections.append(f"- {lim}")
        sections.append("")

    # Sources
    if report.citations:
        sections.append("## Sources")
        sections.append("")
        for citation in report.citations:
            sections.append(format_citation_source(citation))
        sections.append("")

    result = "\n".join(sections)

    # Trim if too long
    if len(result) > max_length:
        result = result[:max_length]
        truncation_notice = "\n\n---\n*Report truncated due to length limit.*\n"
        result = result[: max_length - len(truncation_notice)] + truncation_notice

    return result


def render_error(query: str, error: str) -> str:
    """Render an error as a user-friendly Markdown string."""
    return (
        f"# Deep Research Report\n\n"
        f"**Query:** {query}\n\n"
        f"## Error\n\n"
        f"Unable to complete research: {error}\n\n"
        f"This may be due to a temporary issue. Please try again later."
    )


def render_no_evidence(query: str) -> str:
    """Render a report when no sources were found."""
    return (
        f"# Deep Research Report\n\n"
        f"**Query:** {query}\n\n"
        f"## Summary\n\n"
        f"No relevant sources were found for this query.\n\n"
        f"## Limitations\n\n"
        f"- No sources available for analysis.\n"
        f"- Consider rephrasing the query or trying a different search depth.\n"
    )


def _format_datetime(dt: datetime) -> str:
    """Format datetime for display."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.strftime("%Y-%m-%d %H:%M UTC")
