"""Text cleaner — normalizes and cleans extracted text."""

from __future__ import annotations

import re


def clean_text(text: str) -> str:
    """Clean and normalize text content.

    - Collapse whitespace
    - Remove boilerplate patterns
    - Normalize unicode
    """
    if not text:
        return ""

    # Remove common boilerplate patterns
    text = _remove_boilerplate(text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def remove_boilerplate_paragraphs(paragraphs: list[str]) -> list[str]:
    """Remove paragraphs that look like boilerplate."""
    return [p for p in paragraphs if not _is_boilerplate(p)]


def _remove_boilerplate(text: str) -> str:
    """Remove common boilerplate patterns from text."""
    # Cookie notices
    text = re.sub(
        r"(?i)this\s+site\s+uses\s+cookies.*?\.",
        "",
        text,
    )
    # Newsletter signup
    text = re.sub(
        r"(?i)subscribe\s+to\s+(?:our\s+)?newsletter.*?\.",
        "",
        text,
    )
    # Social media prompts
    text = re.sub(
        r"(?i)(?:follow\s+us|share\s+this)\s+on\s+\w+.*?\.",
        "",
        text,
    )
    return text


def _is_boilerplate(paragraph: str) -> bool:
    """Check if a paragraph is boilerplate."""
    lower = paragraph.lower().strip()
    if len(lower) < 20:
        return True

    boilerplate_indicators = [
        "cookie",
        "javascript is required",
        "enable javascript",
        "subscribe to our newsletter",
        "sign up for",
        "log in to",
        "click here to",
        "all rights reserved",
        "copyright ©",
    ]
    return any(indicator in lower for indicator in boilerplate_indicators)
