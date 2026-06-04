"""Application configuration loaded from env vars with safe defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class AppConfig:
    """All application settings. Created via load_config()."""

    # Server
    host: str = "127.0.0.1"
    port: int = 8000
    mcp_path: str = "/mcp"
    mcp_transport: str = "streamable-http"
    bearer_token: str = ""

    # Providers
    search_provider: Literal["fake", "brave", "tavily", "serper"] = "fake"
    llm_provider: Literal["extractive", "openai"] = "extractive"

    # API Keys (empty = not configured)
    brave_api_key: str = ""
    tavily_api_key: str = ""
    serper_api_key: str = ""
    llm_api_key: str = ""
    llm_api_base: str = ""
    llm_model: str = ""

    # Limits
    max_sources_default: int = 8
    max_sources_hard_limit: int = 20
    fetch_timeout_seconds: float = 10.0
    total_research_timeout_seconds: float = 60.0
    max_fetch_bytes: int = 1_000_000
    max_report_length: int = 15_000

    # Cache
    cache_path: str = ".cache/deepresearch.sqlite3"

    # Logging
    log_level: str = "INFO"

    # Security
    max_concurrent_requests: int = 10
    max_fetch_concurrency: int = 5
    max_search_queries_per_request: int = 10
    max_fetched_pages_per_request: int = 20
    max_source_chars_to_llm: int = 50_000
    request_size_limit: int = 10_000

    # Allowed domains (empty = allow all except blocked)
    allowed_domains: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)


def load_config(env: dict[str, str] | None = None) -> AppConfig:
    """Load configuration from environment variables with safe defaults.

    Args:
        env: Optional dict to read from instead of os.environ (for testing).

    Returns:
        Fully initialized AppConfig.
    """
    source = env if env is not None else dict(os.environ)

    def _get(key: str, default: str = "") -> str:
        return source.get(key, default)

    def _get_int(key: str, default: int) -> int:
        raw = _get(key)
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            raise ConfigError(f"Invalid integer for {key}: {raw!r}") from None

    def _get_float(key: str, default: float) -> float:
        raw = _get(key)
        if not raw:
            return default
        try:
            return float(raw)
        except ValueError:
            raise ConfigError(f"Invalid float for {key}: {raw!r}") from None

    def _get_list(key: str) -> list[str]:
        raw = _get(key)
        if not raw:
            return []
        return [d.strip().lower() for d in raw.split(",") if d.strip()]

    search_provider = _get("SEARCH_PROVIDER", "fake")
    if search_provider not in ("fake", "brave", "tavily", "serper"):
        raise ConfigError(f"Unknown SEARCH_PROVIDER: {search_provider!r}")

    llm_provider = _get("LLM_PROVIDER", "extractive")
    if llm_provider not in ("extractive", "openai"):
        raise ConfigError(f"Unknown LLM_PROVIDER: {llm_provider!r}")

    mcp_transport = _get("MCP_TRANSPORT", "streamable-http")
    if mcp_transport not in ("streamable-http", "stdio"):
        raise ConfigError(f"Unknown MCP_TRANSPORT: {mcp_transport!r}. Use 'streamable-http' or 'stdio'.")

    return AppConfig(
        host=_get("MCP_HOST", "127.0.0.1"),
        port=_get_int("MCP_PORT", 8000),
        mcp_path=_get("MCP_PATH", "/mcp"),
        mcp_transport=mcp_transport,
        bearer_token=_get("MCP_BEARER_TOKEN", ""),
        search_provider=search_provider,
        llm_provider=llm_provider,
        brave_api_key=_get("BRAVE_API_KEY"),
        tavily_api_key=_get("TAVILY_API_KEY"),
        serper_api_key=_get("SERPER_API_KEY"),
        llm_api_key=_get("LLM_API_KEY"),
        llm_api_base=_get("LLM_API_BASE"),
        llm_model=_get("LLM_MODEL"),
        max_sources_default=_get_int("MAX_SOURCES_DEFAULT", 8),
        max_sources_hard_limit=_get_int("MAX_SOURCES_HARD_LIMIT", 20),
        fetch_timeout_seconds=_get_float("FETCH_TIMEOUT_SECONDS", 10.0),
        total_research_timeout_seconds=_get_float("TOTAL_RESEARCH_TIMEOUT_SECONDS", 60.0),
        max_fetch_bytes=_get_int("MAX_FETCH_BYTES", 1_000_000),
        max_report_length=_get_int("MAX_REPORT_LENGTH", 15_000),
        cache_path=_get("CACHE_PATH", ".cache/deepresearch.sqlite3"),
        log_level=_get("LOG_LEVEL", "INFO"),
        max_concurrent_requests=_get_int("MAX_CONCURRENT_REQUESTS", 10),
        max_fetch_concurrency=_get_int("MAX_FETCH_CONCURRENCY", 5),
        max_search_queries_per_request=_get_int("MAX_SEARCH_QUERIES_PER_REQUEST", 10),
        max_fetched_pages_per_request=_get_int("MAX_FETCHED_PAGES_PER_REQUEST", 20),
        max_source_chars_to_llm=_get_int("MAX_SOURCE_CHARS_TO_LLM", 50_000),
        request_size_limit=_get_int("REQUEST_SIZE_LIMIT", 10_000),
        allowed_domains=_get_list("ALLOWED_DOMAINS"),
        blocked_domains=_get_list("BLOCKED_DOMAINS"),
    )


def clamp_max_sources(requested: int, config: AppConfig) -> int:
    """Clamp requested max_sources to the server hard limit."""
    return max(1, min(requested, config.max_sources_hard_limit))


class ConfigError(Exception):
    """Raised when configuration values are invalid."""
