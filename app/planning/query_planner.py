"""Deterministic query planner — generates search queries from user input.

No LLM required. Uses templates and heuristics to create diverse queries.
"""

from __future__ import annotations

import re

from app.models import SearchQuery

# Number of queries per depth level
_DEPTH_QUERY_COUNT = {
    "quick": 2,
    "standard": 4,
    "deep": 6,
}


def plan_queries(
    query: str,
    depth: str = "standard",
) -> list[SearchQuery]:
    """Generate search queries from a user query and depth setting.

    Args:
        query: Original user research query.
        depth: "quick", "standard", or "deep".

    Returns:
        List of SearchQuery objects for the search provider.
    """
    normalized = _normalize_query(query)
    if not normalized:
        return []

    count = _DEPTH_QUERY_COUNT.get(depth, 4)
    variants = _build_variants(normalized)

    # Take up to `count` variants
    selected = variants[:count]

    return [
        SearchQuery(
            query=v["query"],
            variant=v["label"],
            original_query=normalized,
        )
        for v in selected
    ]


def _normalize_query(query: str) -> str:
    """Clean and normalize a query string."""
    # Remove dangerous control characters
    cleaned = "".join(ch for ch in query if ch >= " " or ch in ("\n", "\t"))
    # Collapse whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _build_variants(query: str) -> list[dict[str, str]]:
    """Build query variant templates."""
    variants: list[dict[str, str]] = []

    # 1. Exact query
    variants.append({"query": query, "label": "exact"})

    # 2. Overview / introduction
    variants.append({"query": f"{query} overview", "label": "overview"})

    # 3. Recent / current state
    variants.append({"query": f"{query} latest developments 2024 2025", "label": "recent"})

    # 4. Criticism / limitations / alternatives
    variants.append({"query": f"{query} criticism limitations problems", "label": "criticism"})

    # 5. Official / primary sources
    variants.append({"query": f"{query} official documentation specification", "label": "official"})

    # 6. Comparison / analysis
    variants.append({"query": f"{query} comparison analysis", "label": "analysis"})

    # Filter out empty variants (shouldn't happen, but safe)
    return [v for v in variants if v["query"].strip()]
