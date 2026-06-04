"""Unit tests for app.config — load_config, clamp_max_sources, ConfigError."""

from __future__ import annotations

import pytest

from app.config import AppConfig, ConfigError, clamp_max_sources, load_config

# ---------------------------------------------------------------------------
# load_config — defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_config_returns_appconfig():
    cfg = load_config(env={})
    assert isinstance(cfg, AppConfig)


@pytest.mark.unit
def test_load_config_defaults():
    cfg = load_config(env={})
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 8000
    assert cfg.mcp_path == "/mcp"
    assert cfg.bearer_token == ""
    assert cfg.search_provider == "fake"
    assert cfg.llm_provider == "extractive"
    assert cfg.max_sources_default == 8
    assert cfg.max_sources_hard_limit == 20
    assert cfg.fetch_timeout_seconds == 10.0
    assert cfg.total_research_timeout_seconds == 60.0
    assert cfg.max_fetch_bytes == 1_000_000
    assert cfg.max_report_length == 15_000
    assert cfg.cache_path == ".cache/deepresearch.sqlite3"
    assert cfg.log_level == "INFO"
    assert cfg.max_concurrent_requests == 10
    assert cfg.max_fetch_concurrency == 5
    assert cfg.max_search_queries_per_request == 10
    assert cfg.max_fetched_pages_per_request == 20
    assert cfg.max_source_chars_to_llm == 50_000
    assert cfg.request_size_limit == 10_000
    assert cfg.allowed_domains == []
    assert cfg.blocked_domains == []


# ---------------------------------------------------------------------------
# load_config — env overrides
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_config_env_overrides():
    env = {
        "MCP_HOST": "0.0.0.0",
        "MCP_PORT": "9000",
        "MCP_PATH": "/api/mcp",
        "SEARCH_PROVIDER": "brave",
        "LLM_PROVIDER": "openai",
        "BRAVE_API_KEY": "test-key-123",
        "MAX_SOURCES_DEFAULT": "5",
        "MAX_SOURCES_HARD_LIMIT": "50",
        "FETCH_TIMEOUT_SECONDS": "30.0",
        "TOTAL_RESEARCH_TIMEOUT_SECONDS": "120.0",
        "LOG_LEVEL": "DEBUG",
        "ALLOWED_DOMAINS": "example.com, test.org",
        "BLOCKED_DOMAINS": "spam.com",
    }
    cfg = load_config(env=env)
    assert cfg.host == "0.0.0.0"
    assert cfg.port == 9000
    assert cfg.mcp_path == "/api/mcp"
    assert cfg.search_provider == "brave"
    assert cfg.llm_provider == "openai"
    assert cfg.brave_api_key == "test-key-123"
    assert cfg.max_sources_default == 5
    assert cfg.max_sources_hard_limit == 50
    assert cfg.fetch_timeout_seconds == 30.0
    assert cfg.total_research_timeout_seconds == 120.0
    assert cfg.log_level == "DEBUG"
    assert cfg.allowed_domains == ["example.com", "test.org"]
    assert cfg.blocked_domains == ["spam.com"]


@pytest.mark.unit
def test_load_config_domains_are_lowered_and_stripped():
    env = {"ALLOWED_DOMAINS": "  Example.COM , Test.ORG  "}
    cfg = load_config(env=env)
    assert cfg.allowed_domains == ["example.com", "test.org"]


# ---------------------------------------------------------------------------
# load_config — invalid values
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_load_config_invalid_port():
    with pytest.raises(ConfigError, match="Invalid integer"):
        load_config(env={"MCP_PORT": "not-a-number"})


@pytest.mark.unit
def test_load_config_invalid_float():
    with pytest.raises(ConfigError, match="Invalid float"):
        load_config(env={"FETCH_TIMEOUT_SECONDS": "abc"})


@pytest.mark.unit
def test_load_config_unknown_search_provider():
    with pytest.raises(ConfigError, match="Unknown SEARCH_PROVIDER"):
        load_config(env={"SEARCH_PROVIDER": "google"})


@pytest.mark.unit
def test_load_config_unknown_llm_provider():
    with pytest.raises(ConfigError, match="Unknown LLM_PROVIDER"):
        load_config(env={"LLM_PROVIDER": "anthropic"})


# ---------------------------------------------------------------------------
# clamp_max_sources
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clamp_max_sources_within_range():
    cfg = load_config(env={})
    assert clamp_max_sources(10, cfg) == 10


@pytest.mark.unit
def test_clamp_max_sources_exceeds_hard_limit():
    cfg = load_config(env={"MAX_SOURCES_HARD_LIMIT": "20"})
    assert clamp_max_sources(100, cfg) == 20


@pytest.mark.unit
def test_clamp_max_sources_below_one():
    cfg = load_config(env={})
    assert clamp_max_sources(0, cfg) == 1
    assert clamp_max_sources(-5, cfg) == 1


@pytest.mark.unit
def test_clamp_max_sources_exactly_one():
    cfg = load_config(env={})
    assert clamp_max_sources(1, cfg) == 1


@pytest.mark.unit
def test_clamp_max_sources_exactly_hard_limit():
    cfg = load_config(env={"MAX_SOURCES_HARD_LIMIT": "15"})
    assert clamp_max_sources(15, cfg) == 15


# ---------------------------------------------------------------------------
# AppConfig is frozen
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_appconfig_is_frozen():
    cfg = load_config(env={})
    with pytest.raises(AttributeError):
        cfg.host = "0.0.0.0"  # type: ignore[misc]
