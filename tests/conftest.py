"""Shared pytest fixtures and configuration for DeepResearch tests."""

from __future__ import annotations


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "integration: integration tests (offline, no network)")
    config.addinivalue_line("markers", "contract: contract tests verifying interface conformance")
