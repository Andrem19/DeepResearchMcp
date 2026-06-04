"""Citation management — stable citation ids for report references."""

from __future__ import annotations

from urllib.parse import urlparse

from app.models import Citation, RankedSource


def build_citations(ranked_sources: list[RankedSource]) -> list[Citation]:
    """Build citation list from ranked sources.

    Source IDs are already assigned by the ranker (starting at 1).
    Each citation gets title, url, and domain.
    """
    citations: list[Citation] = []

    for source in ranked_sources:
        citations.append(
            Citation(
                source_id=source.source_id,
                title=source.document.title or _domain_from_url(source.document.url),
                url=source.document.url,
                domain=_domain_from_url(source.document.url),
            )
        )

    return citations


def format_citation_source(citation: Citation) -> str:
    """Format a single citation for the Sources section.

    Format: [n] Title — domain — URL
    """
    title = citation.title or "Untitled"
    domain = citation.domain or "unknown"
    return f"[{citation.source_id}] {title} — {domain} — {citation.url}"


def validate_citations(body_text: str, citations: list[Citation]) -> list[str]:
    """Validate that all [n] references in body text exist in citations.

    Returns list of warnings for invalid references.
    """
    import re

    warnings: list[str] = []
    valid_ids = {c.source_id for c in citations}

    # Find all [n] patterns in body text
    refs = re.findall(r"\[(\d+)\]", body_text)
    for ref_str in refs:
        ref_id = int(ref_str)
        if ref_id not in valid_ids:
            warnings.append(f"Reference [{ref_id}] in body has no matching citation")

    return warnings


def _domain_from_url(url: str) -> str:
    """Extract domain from URL."""
    hostname = urlparse(url).hostname or ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname.lower()
