"""Unit tests for app.synthesize.extractive — ExtractiveSynthesizer."""

from __future__ import annotations

import asyncio

import pytest

from app.models import ExtractedDocument, RankedSource
from app.synthesize.extractive import ExtractiveSynthesizer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _source(
    source_id: int = 1,
    score: float = 40.0,
    text: str = "Python is a versatile programming language used for web development and data science.",
    url: str = "https://example.com",
) -> RankedSource:
    doc = ExtractedDocument(url=url, title="Test Document", text=text)
    return RankedSource(document=doc, score=score, source_id=source_id)


def _run_synthesize(synthesizer, query, sources):
    """Run async synthesize in a synchronous test."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(
        synthesizer.synthesize(query, sources)
    )


# ---------------------------------------------------------------------------
# Creates findings from high-relevance sources
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_creates_findings_from_high_relevance():
    synth = ExtractiveSynthesizer()
    sources = [
        _source(source_id=1, score=50.0, text="Python is a versatile programming language for web development."),
        _source(source_id=2, score=35.0, text="Python supports data science and machine learning libraries."),
    ]
    findings = _run_synthesize(synth, "Python programming", sources)
    assert len(findings) >= 1
    for f in findings:
        assert f.statement
        assert len(f.evidence_ids) >= 1


# ---------------------------------------------------------------------------
# Confidence is capped
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_confidence_capped():
    synth = ExtractiveSynthesizer()
    sources = [_source(source_id=1, score=100.0, text="Python is a high-level programming language.")]
    findings = _run_synthesize(synth, "Python", sources)
    for f in findings:
        assert f.confidence <= 1.0


# ---------------------------------------------------------------------------
# Limitations added when few sources
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_limitations_when_few_sources():
    synth = ExtractiveSynthesizer()
    sources = [
        _source(source_id=1, score=40.0, text="Python is a programming language for data science and web development projects."),
    ]
    findings = _run_synthesize(synth, "Python", sources)
    assert len(sources) < 3
    for f in findings:
        assert any("Limited sources" in lim for lim in f.limitations)


# ---------------------------------------------------------------------------
# No sources -> empty findings
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_no_sources_returns_empty():
    synth = ExtractiveSynthesizer()
    findings = _run_synthesize(synth, "Python", [])
    assert findings == []


# ---------------------------------------------------------------------------
# Medium-relevance sources used when few high
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_medium_relevance_fallback():
    synth = ExtractiveSynthesizer()
    sources = [
        _source(source_id=1, score=15.0, text="Python programming language is used for building web applications and APIs."),
    ]
    findings = _run_synthesize(synth, "Python", sources)
    # Should still create a finding from medium-relevance source
    assert len(findings) >= 1


# ---------------------------------------------------------------------------
# Generic finding when no relevant sentences
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_generic_finding_for_low_relevance():
    synth = ExtractiveSynthesizer()
    sources = [
        _source(
            source_id=1,
            score=5.0,
            text="This text has absolutely nothing related to the query terms at all.",
        ),
    ]
    findings = _run_synthesize(synth, "quantum computing entanglement", sources)
    # Should create generic findings with limitations
    if findings:
        for f in findings:
            assert f.confidence <= 0.3
