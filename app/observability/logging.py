"""Structured logging for DeepResearch pipeline."""

from __future__ import annotations

import logging
import re
from typing import Any

# Patterns to redact from logs
_REDACT_PATTERNS = [
    re.compile(r"(Bearer\s+)\S+", re.IGNORECASE),
    re.compile(r"(api[_-]?key[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"(token[=:]\s*)\S+", re.IGNORECASE),
    re.compile(r"(Authorization[=:]\s*)\S+", re.IGNORECASE),
]

logger = logging.getLogger("deepresearch")


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def log_stage(
    stage: str,
    *,
    correlation_id: str = "",
    duration_ms: float = 0,
    count: int = 0,
    provider: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a pipeline stage event."""
    msg = f"[{stage}]"
    if correlation_id:
        msg += f" cid={correlation_id}"
    if duration_ms:
        msg += f" duration={duration_ms:.0f}ms"
    if count:
        msg += f" count={count}"
    if provider:
        msg += f" provider={provider}"

    if extra:
        for k, v in extra.items():
            msg += f" {k}={v}"

    logger.info(msg)


def log_warning(
    stage: str,
    message: str,
    *,
    correlation_id: str = "",
    extra: dict[str, Any] | None = None,
) -> None:
    """Log a pipeline warning."""
    msg = f"[{stage}] WARNING: {message}"
    if correlation_id:
        msg += f" cid={correlation_id}"
    if extra:
        for k, v in extra.items():
            msg += f" {k}={v}"
    logger.warning(msg)


def redact_secrets(text: str) -> str:
    """Remove API keys and tokens from text for safe logging."""
    for pattern in _REDACT_PATTERNS:
        text = pattern.sub(r"\1[REDACTED]", text)
    return text
