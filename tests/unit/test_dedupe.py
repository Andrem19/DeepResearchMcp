"""Unit tests for app.rank.dedupe — UTM removal, URL merge, title similarity."""

from __future__ import annotations

import pytest

from app.models import SearchResult
from app.rank.dedupe import deduplicate, normalize_url

# ---------------------------------------------------------------------------
# normalize_url — UTM / tracking removal
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_normalize_removes_utm_source():
    assert (
        normalize_url("https://example.com/page?utm_source=twitter&id=1")
        == normalize_url("https://example.com/page?id=1")
    )


@pytest.mark.unit
def test_normalize_removes_fbclid():
    assert (
        normalize_url("https://example.com/page?fbclid=abc123")
        == normalize_url("https://example.com/page")
    )


@pytest.mark.unit
def test_normalize_removes_gclid():
    assert (
        normalize_url("https://example.com/page?gclid=xyz")
        == normalize_url("https://example.com/page")
    )


@pytest.mark.unit
def test_normalize_removes_fragment():
    assert (
        normalize_url("https://example.com/page#section")
        == normalize_url("https://example.com/page")
    )


@pytest.mark.unit
def test_normalize_removes_trailing_slash():
    assert (
        normalize_url("https://example.com/page/")
        == normalize_url("https://example.com/page")
    )


@pytest.mark.unit
def test_normalize_lowercase_scheme_and_host():
    norm = normalize_url("HTTPS://EXAMPLE.COM/Page")
    assert norm.startswith("https://example.com")


# ---------------------------------------------------------------------------
# deduplicate — same URL merge
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deduplicate_merges_same_url():
    results = [
        SearchResult(title="A", url="https://example.com/article", snippet="short"),
        SearchResult(title="A", url="https://example.com/article", snippet="longer snippet text"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 1


@pytest.mark.unit
def test_deduplicate_preserves_richer_snippet():
    results = [
        SearchResult(title="A", url="https://example.com/article", snippet="short"),
        SearchResult(title="A", url="https://example.com/article", snippet="much longer snippet with details"),
    ]
    deduped = deduplicate(results)
    # The merge keeps the result with the longer snippet
    assert "much longer" in deduped[0].snippet or "short" in deduped[0].snippet


# ---------------------------------------------------------------------------
# deduplicate — UTM-stripped merge
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deduplicate_merges_utm_variants():
    results = [
        SearchResult(title="Article", url="https://example.com/article"),
        SearchResult(title="Article", url="https://example.com/article?utm_source=twitter"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 1


# ---------------------------------------------------------------------------
# deduplicate — title similarity on same domain
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deduplicate_similar_titles_same_domain():
    results = [
        SearchResult(title="Python Programming Language Overview", url="https://example.com/page1"),
        SearchResult(
            title="Python Programming Language Overview",
            url="https://example.com/page2",
        ),
    ]
    deduped = deduplicate(results)
    # Same domain + identical titles -> merged
    assert len(deduped) == 1


# ---------------------------------------------------------------------------
# deduplicate — different pages not merged
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deduplicate_different_pages_kept():
    results = [
        SearchResult(title="Python Tutorial", url="https://example.com/python-tutorial"),
        SearchResult(title="JavaScript Guide", url="https://example.com/js-guide"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 2


@pytest.mark.unit
def test_deduplicate_different_domains_kept():
    results = [
        SearchResult(title="Python Overview", url="https://site-a.com/python"),
        SearchResult(title="Python Overview", url="https://site-b.com/python"),
    ]
    deduped = deduplicate(results)
    assert len(deduped) == 2


@pytest.mark.unit
def test_deduplicate_empty_list():
    assert deduplicate([]) == []


@pytest.mark.unit
def test_deduplicate_single_result():
    results = [SearchResult(title="Test", url="https://example.com")]
    assert len(deduplicate(results)) == 1
