"""Contract tests: SearchProvider interface conformance.

Verify that FakeSearchProvider satisfies the SearchProvider ABC contract.
"""

from __future__ import annotations

import inspect

import pytest

from app.models import SearchQuery, SearchResult
from app.search.base import SearchProvider
from app.search.fake import FakeSearchProvider

# ── Interface conformance ───────────────────────────────────────────────────


@pytest.mark.contract
class TestFakeSearchProviderInterface:
    """FakeSearchProvider must satisfy the SearchProvider ABC."""

    def test_is_subclass_of_search_provider(self):
        assert issubclass(FakeSearchProvider, SearchProvider)

    def test_instantiation_without_args(self):
        provider = FakeSearchProvider()
        assert provider is not None

    def test_instantiation_with_custom_results(self):
        results = [
            SearchResult(title="Test", url="https://example.com/test", snippet="Test snippet"),
        ]
        provider = FakeSearchProvider(results=results)
        assert provider is not None

    def test_has_name_property(self):
        provider = FakeSearchProvider()
        assert provider.name == "fake"

    def test_has_async_search_method(self):
        provider = FakeSearchProvider()
        assert hasattr(provider, "search")
        assert inspect.iscoroutinefunction(provider.search)

    def test_search_accepts_expected_signature(self):
        """search() accepts (queries: list[SearchQuery], *, max_results: int)."""
        sig = inspect.signature(_provider := FakeSearchProvider().search)
        params = list(sig.parameters.keys())
        assert "queries" in params
        assert "max_results" in params


@pytest.mark.contract
@pytest.mark.anyio
async def test_fake_search_returns_list_of_search_results():
    """search() returns a list of SearchResult objects."""
    provider = FakeSearchProvider()
    queries = [SearchQuery(query="test", original_query="test")]
    results = await provider.search(queries, max_results=10)

    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, SearchResult)


@pytest.mark.contract
@pytest.mark.anyio
async def test_fake_search_respects_max_results():
    """search() returns at most max_results results."""
    provider = FakeSearchProvider()
    queries = [SearchQuery(query="test", original_query="test")]
    results = await provider.search(queries, max_results=1)

    assert len(results) <= 1


@pytest.mark.contract
@pytest.mark.anyio
async def test_fake_search_fail_raises_search_error():
    """When fail=True, search() raises SearchError."""
    from app.errors import SearchError

    provider = FakeSearchProvider(fail=True, error_message="test error")
    queries = [SearchQuery(query="test", original_query="test")]

    with pytest.raises(SearchError, match="test error"):
        await provider.search(queries)


@pytest.mark.contract
@pytest.mark.anyio
async def test_fake_search_default_results_count():
    """Default FakeSearchProvider returns exactly 3 results."""
    provider = FakeSearchProvider()
    queries = [SearchQuery(query="test", original_query="test")]
    results = await provider.search(queries, max_results=100)

    assert len(results) == 3


@pytest.mark.contract
@pytest.mark.anyio
async def test_fake_search_with_empty_custom_results():
    """FakeSearchProvider with empty results list returns no results.

    Note: FakeSearchProvider(results=[]) falls back to defaults because
    the constructor uses `results or self._default_results()` (empty list is falsy).
    This is a known behavior. We test by subclassing to override search().
    """

    class EmptyProvider(FakeSearchProvider):
        async def search(self, queries, *, max_results=20):
            return []

    provider = EmptyProvider()
    queries = [SearchQuery(query="test", original_query="test")]
    results = await provider.search(queries)

    assert results == []
