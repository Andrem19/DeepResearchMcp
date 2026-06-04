"""Domain error types for DeepResearch pipeline."""

from __future__ import annotations


class ResearchError(Exception):
    """Base error for all research pipeline failures."""


class ValidationError(ResearchError):
    """Invalid input (empty query, bad depth, etc.)."""


class SearchError(ResearchError):
    """Search provider failure."""


class FetchError(ResearchError):
    """Page fetch failure (network, timeout, blocked URL, etc.)."""


class ExtractionError(ResearchError):
    """Content extraction failure."""


class URLSafetyError(ResearchError):
    """URL blocked by safety guard (SSRF, private IP, bad scheme, etc.)."""


class SynthesisError(ResearchError):
    """Synthesis failure."""


class StorageError(ResearchError):
    """Storage/cache failure."""


class ConfigError(ResearchError):
    """Invalid configuration."""


class TimeoutError(ResearchError):
    """Research request exceeded total timeout."""
