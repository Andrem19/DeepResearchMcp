"""Unit tests for app.planning.query_planner — plan_queries, normalize, variants."""

from __future__ import annotations

import pytest

from app.planning.query_planner import _build_variants, _normalize_query, plan_queries

# ---------------------------------------------------------------------------
# _normalize_query
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_normalize_query_basic():
    assert _normalize_query("  What   is   Python?  ") == "What is Python?"


@pytest.mark.unit
def test_normalize_query_removes_control_chars():
    result = _normalize_query("hello\x00world\x01")
    assert "\x00" not in result
    assert "\x01" not in result


@pytest.mark.unit
def test_normalize_query_empty():
    assert _normalize_query("") == ""


@pytest.mark.unit
def test_normalize_query_whitespace_only():
    assert _normalize_query("   \t\n  ") == ""


# ---------------------------------------------------------------------------
# _build_variants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_variants_returns_six():
    variants = _build_variants("Python programming")
    assert len(variants) == 6


@pytest.mark.unit
def test_build_variants_labels():
    variants = _build_variants("Python")
    labels = [v["label"] for v in variants]
    assert labels == ["exact", "overview", "recent", "criticism", "official", "analysis"]


@pytest.mark.unit
def test_build_variants_exact_is_original():
    variants = _build_variants("Python")
    assert variants[0]["query"] == "Python"
    assert variants[0]["label"] == "exact"


@pytest.mark.unit
def test_build_variants_overview_appends():
    variants = _build_variants("Python")
    assert "overview" in variants[1]["query"]


@pytest.mark.unit
def test_build_variants_recent_includes_years():
    variants = _build_variants("Python")
    assert "2024" in variants[2]["query"] or "2025" in variants[2]["query"]


# ---------------------------------------------------------------------------
# plan_queries — quick depth
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plan_queries_quick_returns_two():
    queries = plan_queries("Python", depth="quick")
    assert len(queries) == 2


@pytest.mark.unit
def test_plan_queries_quick_variants():
    queries = plan_queries("Python", depth="quick")
    labels = [q.variant for q in queries]
    assert "exact" in labels
    assert "overview" in labels


# ---------------------------------------------------------------------------
# plan_queries — standard depth
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plan_queries_standard_returns_four():
    queries = plan_queries("Python", depth="standard")
    assert len(queries) == 4


@pytest.mark.unit
def test_plan_queries_standard_original_query():
    queries = plan_queries("Python", depth="standard")
    for q in queries:
        assert q.original_query == "Python"


# ---------------------------------------------------------------------------
# plan_queries — deep depth
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plan_queries_deep_returns_six():
    queries = plan_queries("Python", depth="deep")
    assert len(queries) == 6


# ---------------------------------------------------------------------------
# plan_queries — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_plan_queries_empty_query():
    queries = plan_queries("")
    assert queries == []


@pytest.mark.unit
def test_plan_queries_whitespace_query():
    queries = plan_queries("   ")
    assert queries == []


@pytest.mark.unit
def test_plan_queries_unknown_depth_defaults_to_four():
    queries = plan_queries("Python", depth="unknown_depth")
    assert len(queries) == 4


@pytest.mark.unit
def test_plan_queries_normalizes_query():
    queries = plan_queries("  What   is   Python?  ")
    assert all(q.original_query == "What is Python?" for q in queries)


@pytest.mark.unit
def test_plan_queries_each_has_query_string():
    queries = plan_queries("Python", depth="deep")
    for q in queries:
        assert len(q.query) > 0
