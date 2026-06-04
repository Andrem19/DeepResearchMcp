# Configuration

All settings are loaded from environment variables with safe defaults. No CLI argument parsing.

## Server Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_HOST` | `127.0.0.1` | Server bind address |
| `MCP_PORT` | `8000` | Server port |
| `MCP_PATH` | `/mcp` | MCP endpoint path |
| `MCP_BEARER_TOKEN` | *(empty)* | Auth token. Required for production, optional for local dev |

## Search Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `SEARCH_PROVIDER` | `fake` | Provider: `fake`, `brave`, `tavily`, `serper` |
| `BRAVE_API_KEY` | *(empty)* | Brave Search API key |
| `TAVILY_API_KEY` | *(empty)* | Tavily API key |
| `SERPER_API_KEY` | *(empty)* | Serper.dev API key |

## LLM Provider

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `extractive` | `extractive` (no LLM) or `openai` |
| `LLM_API_KEY` | *(empty)* | OpenAI-compatible API key |
| `LLM_API_BASE` | *(empty)* | Custom API endpoint (e.g., LM Studio) |
| `LLM_MODEL` | *(empty)* | Model name |

## Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `MAX_SOURCES_DEFAULT` | `8` | Default max sources |
| `MAX_SOURCES_HARD_LIMIT` | `20` | Server-side hard limit (cannot be exceeded) |
| `FETCH_TIMEOUT_SECONDS` | `10` | Per-page fetch timeout |
| `TOTAL_RESEARCH_TIMEOUT_SECONDS` | `60` | Total research timeout |
| `MAX_FETCH_BYTES` | `1000000` | Max page size (1 MB) |
| `MAX_REPORT_LENGTH` | `15000` | Max report length in chars |

## Cache

| Variable | Default | Description |
|----------|---------|-------------|
| `CACHE_PATH` | `.cache/deepresearch.sqlite3` | SQLite database path |

## Logging

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |

## Example .env

See `.env.example` in the project root. Never commit real API keys.
