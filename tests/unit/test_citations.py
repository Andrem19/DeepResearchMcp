"""Unit tests for app.report.citations — build, format, validate citations."""

from __future__ import annotations

import pytest

from app.models import Citation, ExtractedDocument, RankedSource
from app.report.citations import build_citations, format_citation_source, validate_citations

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ranked_source(source_id: int, url: str = "https://example.com", title: str = "Test") -> RankedSource:
    doc = ExtractedDocument(url=url, title=title, text="content")
    return RankedSource(document=doc, score=10.0, source_id=source_id)


# ---------------------------------------------------------------------------
# build_citations — ids start at 1, stable
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_citations_ids_start_at_1():
    sources = [
        _ranked_source(1, url="https://a.com"),
        _ranked_source(2, url="https://b.com"),
    ]
    citations = build_citations(sources)
    assert citations[0].source_id == 1
    assert citations[1].source_id == 2


@pytest.mark.unit
def test_build_citations_stable_order():
    sources = [
        _ranked_source(1, url="https://a.com", title="Alpha"),
        _ranked_source(2, url="https://b.com", title="Beta"),
    ]
    c1 = build_citations(sources)
    c2 = build_citations(sources)
    assert [c.source_id for c in c1] == [c.source_id for c in c2]


@pytest.mark.unit
def test_build_citations_extracts_domain():
    sources = [_ranked_source(1, url="https://www.example.com/page")]
    citations = build_citations(sources)
    assert citations[0].domain == "example.com"


@pytest.mark.unit
def test_build_citations_uses_title():
    sources = [_ranked_source(1, title="My Title")]
    citations = build_citations(sources)
    assert citations[0].title == "My Title"


@pytest.mark.unit
def test_build_citations_uses_domain_when_no_title():
    sources = [_ranked_source(1, url="https://www.example.com/page", title="")]
    citations = build_citations(sources)
    assert citations[0].title == "example.com"


@pytest.mark.unit
def test_build_citations_empty():
    assert build_citations([]) == []


# ---------------------------------------------------------------------------
# format_citation_source
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_format_citation_source_basic():
    c = Citation(source_id=1, title="My Article", url="https://example.com/article", domain="example.com")
    result = format_citation_source(c)
    assert result == "[1] My Article — example.com — https://example.com/article"


@pytest.mark.unit
def test_format_citation_source_untitled():
    c = Citation(source_id=2, title="", url="https://example.com", domain="example.com")
    result = format_citation_source(c)
    assert result.startswith("[2] Untitled")


@pytest.mark.unit
def test_format_citation_source_unknown_domain():
    c = Citation(source_id=3, title="Test", url="https://example.com", domain="")
    result = format_citation_source(c)
    assert "unknown" in result


# ---------------------------------------------------------------------------
# validate_citations
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_validate_citations_all_valid():
    citations = [Citation(source_id=1), Citation(source_id=2)]
    body = "Some text [1] and [2]."
    warnings = validate_citations(body, citations)
    assert warnings == []


@pytest.mark.unit
def test_validate_citations_missing_ref():
    citations = [Citation(source_id=1)]
    body = "Text with [1] and [99]."
    warnings = validate_citations(body, citations)
    assert len(warnings) == 1
    assert "99" in warnings[0]


@pytest.mark.unit
def test_validate_citations_no_refs_in_body():
    citations = [Citation(source_id=1)]
    body = "No citations here."
    warnings = validate_citations(body, citations)
    assert warnings == []


@pytest.mark.unit
def test_validate_citations_multiple_missing():
    citations = [Citation(source_id=1)]
    body = "Ref [5] and [10] are missing."
    warnings = validate_citations(body, citations)
    assert len(warnings) == 2
