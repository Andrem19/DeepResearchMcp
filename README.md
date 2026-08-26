# DeepResearch MCP Server

A lightweight Model Context Protocol server for deep web research. It accepts a compact research request, searches and reads sources, compares evidence, and returns a structured Markdown report with citations.

## Why It Exists

Small local models and coding agents often perform poorly when they must coordinate many low-level search and browsing tools. DeepResearch MCP exposes a single high-level tool — `deep_research` — and keeps the retrieval, reading, comparison, and report-building workflow inside the server.

## Highlights

- One high-level MCP tool instead of a large low-level tool surface.
- Multi-source research with configurable depth and recency.
- Structured Markdown reports with citations.
- Provider abstraction for search backends.
- SSRF protection, bearer-token authentication, limits, and timeouts.
- Offline test coverage that does not require paid API access.
- Designed to reduce orchestration burden for smaller local models.

## Quick Start

```bash
conda create -n dr1 python=3.12 -y
conda activate dr1
pip install -e ".[dev]"
python -m app.mcp_server
```

Run with a real search provider:

```bash
SEARCH_PROVIDER=brave BRAVE_API_KEY=your-key python -m app.mcp_server
```

## MCP Tool

```text
deep_research(
    query: str,
    depth: "quick" | "standard" | "deep" = "standard",
    max_sources: int = 8,
    recency_days: int | None = None,
    output_format: "markdown" = "markdown"
) -> str
```

## Client Configuration

### OpenCode

```json
{
  "mcp": {
    "deepresearch": {
      "type": "remote",
      "url": "http://127.0.0.1:8000/mcp",
      "enabled": true,
      "headers": {
        "Authorization": "Bearer YOUR_SECRET_TOKEN"
      },
      "timeout": 120000
    }
  }
}
```

### LM Studio

```json
{
  "mcpServers": {
    "deepresearch": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer YOUR_SECRET_TOKEN"
      }
    }
  }
}
```

## Engineering Principles

- **Small public interface** — the client delegates research rather than micromanaging internal steps.
- **Report-oriented output** — callers receive a finished sourced report instead of raw retrieval results.
- **Safety boundaries** — outbound requests are constrained by SSRF protection, authentication, timeouts, and limits.
- **Deterministic development path** — tests can run offline without external API keys.

## Development

```bash
conda activate dr1
ruff check .
python -m pytest
```

Static typing is configured for incremental use, but it is not yet a CI gate for the full legacy test suite.

## License

MIT
