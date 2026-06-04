"""Unit tests for app.models — Pydantic v2 models and validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models import (
    Citation,
    ExtractedDocument,
    FetchedPage,
    RankedSource,
    ResearchFinding,
    ResearchReport,
    ResearchRequest,
    SearchResult,
)

# ---------------------------------------------------------------------------
# ResearchRequest
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_research_request_valid():
    req = ResearchRequest(query="What is Python?")
    assert req.query == "What is Python?"
    assert req.depth == "standard"
    assert req.max_sources == 8
    assert req.output_format == "markdown"


@pytest.mark.unit
def test_research_request_strips_whitespace():
    req = ResearchRequest(query="  What is Python?  ")
    assert req.query == "What is Python?"


@pytest.mark.unit
def test_research_request_empty_query():
    with pytest.raises(ValidationError):
        ResearchRequest(query="")


@pytest.mark.unit
def test_research_request_whitespace_only_query():
    with pytest.raises(ValidationError):
        ResearchRequest(query="   ")


@pytest.mark.unit
def test_research_request_bad_depth():
    with pytest.raises(ValidationError):
        ResearchRequest(query="test", depth="ultra")


@pytest.mark.unit
def test_research_request_max_sources_too_low():
    with pytest.raises(ValidationError):
        ResearchRequest(query="test", max_sources=0)


@pytest.mark.unit
def test_research_request_max_sources_too_high():
    with pytest.raises(ValidationError):
        ResearchRequest(query="test", max_sources=101)


@pytest.mark.unit
def test_research_request_negative_recency_days():
    with pytest.raises(ValidationError):
        ResearchRequest(query="test", recency_days=-1)


@pytest.mark.unit
def test_research_request_strips_control_chars():
    req = ResearchRequest(query="hello\x00world\x01test")
    assert "\x00" not in req.query
    assert "\x01" not in req.query
    assert "hello" in req.query


@pytest.mark.unit
def test_research_request_all_depths():
    for depth in ("quick", "standard", "deep"):
        req = ResearchRequest(query="test", depth=depth)
        assert req.depth == depth


# ---------------------------------------------------------------------------
# SearchResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_search_result_valid():
    r = SearchResult(title="Test", url="https://example.com")
    assert r.url == "https://example.com"
    assert r.title == "Test"


@pytest.mark.unit
def test_search_result_empty_url():
    with pytest.raises(ValidationError):
        SearchResult(url="")


@pytest.mark.unit
def test_search_result_bad_scheme():
    with pytest.raises(ValidationError, match="http or https"):
        SearchResult(url="ftp://example.com")


@pytest.mark.unit
def test_search_result_no_hostname():
    with pytest.raises(ValidationError, match="hostname"):
        SearchResult(url="https://")


@pytest.mark.unit
def test_search_result_file_scheme():
    with pytest.raises(ValidationError):
        SearchResult(url="file:///etc/passwd")


# ---------------------------------------------------------------------------
# FetchedPage
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_fetched_page_is_success():
    page = FetchedPage(url="https://example.com", status_code=200, body=b"ok")
    assert page.is_success is True


@pytest.mark.unit
def test_fetched_page_is_failure_404():
    page = FetchedPage(url="https://example.com", status_code=404, body=b"not found")
    assert page.is_success is False


@pytest.mark.unit
def test_fetched_page_is_failure_error():
    page = FetchedPage(url="https://example.com", error="timeout")
    assert page.is_success is False


# ---------------------------------------------------------------------------
# ExtractedDocument
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extracted_document_defaults():
    doc = ExtractedDocument(url="https://example.com")
    assert doc.title == ""
    assert doc.text == ""
    assert doc.paragraphs == []
    assert doc.extraction_method == "html"


# ---------------------------------------------------------------------------
# RankedSource
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ranked_source_defaults():
    doc = ExtractedDocument(url="https://example.com")
    rs = RankedSource(document=doc)
    assert rs.score == 0.0
    assert rs.source_id == 0
    assert rs.score_breakdown == {}


# ---------------------------------------------------------------------------
# ResearchFinding
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_research_finding_defaults():
    f = ResearchFinding(statement="Test finding")
    assert f.evidence_ids == []
    assert f.confidence == 0.5
    assert f.limitations == []


@pytest.mark.unit
def test_research_finding_confidence_out_of_range():
    with pytest.raises(ValidationError):
        ResearchFinding(statement="Test", confidence=1.5)
    with pytest.raises(ValidationError):
        ResearchFinding(statement="Test", confidence=-0.1)


# ---------------------------------------------------------------------------
# Citation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_citation_source_id_must_be_positive():
    with pytest.raises(ValidationError):
        Citation(source_id=0)
    with pytest.raises(ValidationError):
        Citation(source_id=-1)


@pytest.mark.unit
def test_citation_source_id_valid():
    c = Citation(source_id=1, title="Test", url="https://example.com")
    assert c.source_id == 1


# ---------------------------------------------------------------------------
# ResearchReport — citation cross-validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_research_report_valid():
    report = ResearchReport(
        query="test",
        findings=[ResearchFinding(statement="s", evidence_ids=[1])],
        citations=[Citation(source_id=1, title="t", url="https://example.com")],
    )
    assert report.query == "test"


@pytest.mark.unit
def test_research_report_missing_citation():
    with pytest.raises(ValidationError, match="missing citation ids"):
        ResearchReport(
            query="test",
            findings=[ResearchFinding(statement="s", evidence_ids=[99])],
            citations=[Citation(source_id=1)],
        )


@pytest.mark.unit
def test_research_report_no_findings_is_valid():
    report = ResearchReport(query="test", findings=[], citations=[])
    assert report.findings == []


# ---------------------------------------------------------------------------
# Serialization round-trip
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_research_request_serialization():
    req = ResearchRequest(query="What is Python?", depth="deep", max_sources=10)
    data = req.model_dump()
    restored = ResearchRequest(**data)
    assert restored.query == req.query
    assert restored.depth == req.depth
    assert restored.max_sources == req.max_sources


@pytest.mark.unit
def test_search_result_serialization():
    r = SearchResult(title="Test", url="https://example.com", snippet="A snippet")
    data = r.model_dump()
    restored = SearchResult(**data)
    assert restored.title == r.title


@pytest.mark.unit
def test_research_report_serialization():
    report = ResearchReport(
        query="test query",
        summary="A summary",
        findings=[ResearchFinding(statement="fact", evidence_ids=[1])],
        citations=[Citation(source_id=1, title="src", url="https://example.com")],
    )
    data = report.model_dump()
    restored = ResearchReport(**data)
    assert restored.query == "test query"
    assert len(restored.findings) == 1
    assert len(restored.citations) == 1
