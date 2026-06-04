"""Deterministic source ranker — scores sources by relevance signals."""

from __future__ import annotations

from urllib.parse import urlparse

from app.models import ExtractedDocument, RankedSource

# Known high-quality domains (score bonus)
_REPUTABLE_DOMAINS = {
    "wikipedia.org", "github.com", "stackoverflow.com",
    "docs.python.org", "developer.mozilla.org",
    "arxiv.org", "nature.com", "sciencedirect.com",
    "ietf.org", "w3.org", "spec.whatwg.org",
}

# SEO aggregator penalty domains
_AGGREGATOR_PENALTY_DOMAINS = {
    "pinterest.com", "reddit.com", "quora.com",
    "medium.com", "buzzfeed.com",
}


def rank(
    documents: list[ExtractedDocument],
    query: str,
    *,
    max_results: int = 8,
    recency_days: int | None = None,
) -> list[RankedSource]:
    """Rank extracted documents by relevance to query.

    Args:
        documents: Documents to rank.
        query: Original search query.
        max_results: Maximum number of results.
        recency_days: If set, boost fresher content.

    Returns:
        Sorted list of RankedSource with scores.
    """
    scored: list[RankedSource] = []

    for doc in documents:
        score, breakdown = _score_document(doc, query, recency_days)
        scored.append(
            RankedSource(
                document=doc,
                score=score,
                score_breakdown=breakdown,
            )
        )

    # Sort by score descending
    scored.sort(key=lambda s: s.score, reverse=True)

    # Assign source_ids starting at 1
    for i, source in enumerate(scored[:max_results], start=1):
        source.source_id = i

    return scored[:max_results]


def _score_document(
    doc: ExtractedDocument,
    query: str,
    recency_days: int | None,
) -> tuple[float, dict[str, float]]:
    """Score a single document. Returns (total_score, breakdown)."""
    breakdown: dict[str, float] = {}

    # 1. Query-word overlap in title (0-40 points)
    title_score = _word_overlap(query, doc.title) * 40.0
    breakdown["title_match"] = title_score

    # 2. Query-word overlap in text (0-30 points)
    text_score = _word_overlap(query, doc.text) * 30.0
    breakdown["text_match"] = text_score

    # 3. Reputable domain bonus (0-15 points)
    domain = _get_domain(doc.url)
    domain_score = 15.0 if domain in _REPUTABLE_DOMAINS else 0.0
    breakdown["domain_quality"] = domain_score

    # 4. Content length bonus — penalize thin content (0-10 points)
    length_score = min(len(doc.text) / 500.0, 1.0) * 10.0
    breakdown["content_length"] = length_score

    # 5. Aggregator penalty (-10 points)
    agg_penalty = -10.0 if domain in _AGGREGATOR_PENALTY_DOMAINS else 0.0
    breakdown["aggregator_penalty"] = agg_penalty

    # 6. Boilerplate penalty — penalize if text is mostly whitespace/short
    if len(doc.text.strip()) < 100:
        breakdown["thin_content_penalty"] = -20.0
    else:
        breakdown["thin_content_penalty"] = 0.0

    total = sum(breakdown.values())
    return max(0.0, total), breakdown


def _word_overlap(query: str, text: str) -> float:
    """Fraction of query words found in text."""
    query_words = set(query.lower().split())
    if not query_words:
        return 0.0
    text_lower = text.lower()
    found = sum(1 for w in query_words if w in text_lower)
    return found / len(query_words)


def _get_domain(url: str) -> str:
    """Extract domain from URL, stripping www prefix."""
    hostname = urlparse(url).hostname or ""
    # Remove www. prefix
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname.lower()
