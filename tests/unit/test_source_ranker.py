"""Unit tests for app.rank.source_ranker — scoring, bonuses, penalties, determinism."""

from __future__ import annotations

import pytest

from app.models import ExtractedDocument
from app.rank.source_ranker import rank

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _doc(
    url: str = "https://example.com",
    title: str = "Test Document",
    text: str = "This is a test document with some content about Python programming.",
) -> ExtractedDocument:
    return ExtractedDocument(url=url, title=title, text=text)


# ---------------------------------------------------------------------------
# Exact match ranks higher
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_exact_title_match_ranks_higher():
    query = "Python programming"
    docs = [
        _doc(title="Python programming tutorial", text="Some text about Python programming."),
        _doc(title="Unrelated topic", text="This has nothing to do with the query."),
    ]
    ranked = rank(docs, query, max_results=10)
    assert ranked[0].document.title == "Python programming tutorial"
    assert ranked[0].score > ranked[1].score


# ---------------------------------------------------------------------------
# Official / reputable source bonus
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_reputable_domain_gets_bonus():
    query = "Python"
    docs = [
        _doc(url="https://docs.python.org/3/tutorial/", title="Python Tutorial"),
        _doc(url="https://random-blog.com/post", title="Python Tutorial"),
    ]
    ranked = rank(docs, query, max_results=10)
    # The docs.python.org result should rank higher due to domain bonus
    assert ranked[0].document.url.startswith("https://docs.python.org")
    pythondoc = ranked[0]
    blog = ranked[1]
    assert pythondoc.score_breakdown["domain_quality"] == 15.0
    assert blog.score_breakdown["domain_quality"] == 0.0


# ---------------------------------------------------------------------------
# Thin content penalty
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_thin_content_penalty():
    query = "test"
    docs = [
        _doc(text="Short"),  # Under 100 chars -> thin penalty
        _doc(text="A" * 500),  # Full content length score
    ]
    ranked = rank(docs, query, max_results=10)
    thin = next(r for r in ranked if len(r.document.text) < 100)
    full = next(r for r in ranked if len(r.document.text) >= 100)
    assert thin.score_breakdown["thin_content_penalty"] == -20.0
    assert full.score_breakdown["thin_content_penalty"] == 0.0


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ranking_is_deterministic():
    query = "Python"
    docs = [
        _doc(url="https://a.com", title="Python A"),
        _doc(url="https://b.com", title="Python B"),
        _doc(url="https://c.com", title="Python C"),
    ]
    run1 = rank(docs, query, max_results=10)
    run2 = rank(docs, query, max_results=10)
    for r1, r2 in zip(run1, run2, strict=False):
        assert r1.document.url == r2.document.url
        assert r1.score == r2.score


# ---------------------------------------------------------------------------
# source_id starts at 1
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_source_ids_start_at_one():
    docs = [_doc(), _doc(url="https://other.com")]
    ranked = rank(docs, "test", max_results=10)
    assert ranked[0].source_id == 1
    assert ranked[1].source_id == 2


# ---------------------------------------------------------------------------
# max_results limits output
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_max_results_limits_output():
    docs = [_doc(url=f"https://site{i}.com", title=f"Doc {i}") for i in range(10)]
    ranked = rank(docs, "test", max_results=3)
    assert len(ranked) == 3


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_rank_empty_input():
    ranked = rank([], "test")
    assert ranked == []


# ---------------------------------------------------------------------------
# Aggregator penalty
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_aggregator_penalty():
    query = "test"
    docs = [
        _doc(url="https://pinterest.com/something", title="Test"),
        _doc(url="https://example.com/page", title="Test"),
    ]
    ranked = rank(docs, query, max_results=10)
    pinterest = next(r for r in ranked if "pinterest" in r.document.url)
    assert pinterest.score_breakdown["aggregator_penalty"] == -10.0


# ---------------------------------------------------------------------------
# Score never negative
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_score_never_negative():
    docs = [_doc(url="https://pinterest.com/x", title="X", text="Short")]
    ranked = rank(docs, "completely unrelated query xyz", max_results=10)
    for r in ranked:
        assert r.score >= 0.0
