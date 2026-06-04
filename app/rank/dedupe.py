"""URL deduplication and source normalization."""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlencode, urlparse

if TYPE_CHECKING:
    from app.models import SearchResult

# Tracking parameters to remove
_TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "msclkid", "mc_eid", "dclid",
    "ref", "referrer", "source", "s_cid",
}

# Maximum similarity ratio for title dedup (0.0-1.0)
_TITLE_SIMILARITY_THRESHOLD = 0.85


def deduplicate(results: list[SearchResult]) -> list[SearchResult]:
    """Deduplicate search results by normalized URL and similar titles.

    Returns deduplicated list preserving first occurrence and merging metadata.
    """
    seen_urls: dict[str, int] = {}  # normalized_url -> index in output
    output: list[SearchResult] = []

    for result in results:
        norm_url = normalize_url(result.url)

        # Check exact URL match
        if norm_url in seen_urls:
            idx = seen_urls[norm_url]
            # Merge: keep the one with more info
            existing = output[idx]
            output[idx] = _merge(existing, result)
            continue

        # Check title similarity against all seen results
        is_dup = False
        for existing in output:
            # Same domain + similar title = duplicate
            if (
                _title_similarity(existing.title, result.title) >= _TITLE_SIMILARITY_THRESHOLD
                and _same_domain(existing.url, result.url)
            ):
                is_dup = True
                break

        if not is_dup:
            seen_urls[norm_url] = len(output)
            output.append(result)

    return output


def normalize_url(url: str) -> str:
    """Normalize a URL for comparison.

    - Lowercase scheme and host
    - Remove tracking parameters
    - Remove fragment/anchor
    - Remove trailing slashes
    """
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower() if parsed.hostname else ""

    # Remove tracking parameters
    params = parse_qs(parsed.query, keep_blank_values=True)
    cleaned_params = {k: v for k, v in params.items() if k.lower() not in _TRACKING_PARAMS}

    # Rebuild query string (sorted for consistency)
    query = urlencode(sorted(cleaned_params.items()), doseq=True)

    # Remove fragment, normalize path
    path = parsed.path.rstrip("/") or "/"

    # Rebuild port
    port = parsed.port
    port_str = f":{port}" if port else ""

    return f"{scheme}://{host}{port_str}{path}" + (f"?{query}" if query else "")


def _merge(a: SearchResult, b: SearchResult) -> SearchResult:
    """Merge two duplicate results, keeping the richer one."""
    # Keep the one with longer snippet
    if len(b.snippet) > len(a.snippet):
        return b.model_copy(update={"snippet": a.snippet or b.snippet})
    return a


def _title_similarity(a: str, b: str) -> float:
    """Simple word-overlap similarity between two titles."""
    if not a or not b:
        return 0.0

    words_a = set(a.lower().split())
    words_b = set(b.lower().split())

    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union)


def _same_domain(url_a: str, url_b: str) -> bool:
    """Check if two URLs share the same domain."""
    host_a = urlparse(url_a).hostname or ""
    host_b = urlparse(url_b).hostname or ""
    return host_a.lower() == host_b.lower()
