# Architecture

## Overview

DeepResearch MCP Server follows a **thin adapter** pattern:

- The MCP layer (`app/mcp_server.py`) is a minimal adapter that exposes one tool.
- All business logic lives in `app/research_engine.py` and its sub-modules.
- External dependencies (search, fetch, LLM) are injected via interfaces.

## Pipeline Flow

```text
User Query
    |
    v
[MCP Adapter]  ← app/mcp_server.py (thin)
    |
    v
[Research Engine]  ← app/research_engine.py (orchestrator)
    |
    +-- [Query Planner]  ← app/planning/query_planner.py
    |       Generates search queries from user input
    |
    +-- [Search Provider]  ← app/search/
    |       Searches the web (Brave, Tavily, Serper, or Fake)
    |
    +-- [Deduplicator]  ← app/rank/dedupe.py
    |       Removes duplicate URLs and similar results
    |
    +-- [Page Fetcher]  ← app/fetch/
    |       Fetches pages with URL safety guard (SSRF protection)
    |
    +-- [Content Extractor]  ← app/extract/
    |       Extracts clean text from HTML
    |
    +-- [Source Ranker]  ← app/rank/source_ranker.py
    |       Scores and ranks sources by relevance
    |
    +-- [Synthesizer]  ← app/synthesize/
    |       Builds findings from evidence (extractive or LLM)
    |
    +-- [Report Renderer]  ← app/report/
    |       Generates Markdown report with citations
    |
    +-- [Storage/Cache]  ← app/storage/
    |       SQLite cache for search results and pages
    |
    +-- [Observability]  ← app/observability/
            Structured logging and metrics
```

## Key Design Decisions

1. **One MCP tool**: `deep_research` is the only public tool. Complexity is internal.
2. **Dependency injection**: All components are injected via constructor for testability.
3. **Fake providers first**: Everything works offline with fake/mock implementations.
4. **Deterministic fallback**: The extractive synthesizer works without LLM.
5. **SSRF protection**: URL Safety Guard blocks private IPs, localhost, and dangerous schemes.

## Module Dependencies

```text
mcp_server → research_engine → {planning, search, fetch, extract, rank, synthesize, report, storage}
```

No circular imports. Models are in `app/models.py` and imported by all modules.
