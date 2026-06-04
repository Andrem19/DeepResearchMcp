"""HTML content extractor — extracts clean text from HTML pages."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from app.models import ExtractedDocument, FetchedPage

# Tags to completely remove (including content)
_REMOVE_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript"}

# Tags that are boilerplate indicators
_BOILERPLATE_TAGS = {"nav", "footer", "header", "aside", "form"}

# Maximum text length to extract (chars)
_MAX_TEXT_LENGTH = 100_000


def extract(page: FetchedPage) -> ExtractedDocument:
    """Extract clean text from a fetched HTML page.

    Returns ExtractedDocument with title, text, and paragraphs.
    """
    if not page.is_success:
        return ExtractedDocument(
            url=page.url,
            title="",
            text="",
            extraction_method="none",
        )

    html = page.body.decode("utf-8", errors="replace")

    title = _extract_title(html)
    text = _html_to_text(html)

    # Limit text length
    if len(text) > _MAX_TEXT_LENGTH:
        text = text[:_MAX_TEXT_LENGTH]

    paragraphs = _split_paragraphs(text)

    return ExtractedDocument(
        url=page.final_url or page.url,
        title=title,
        text=text,
        paragraphs=paragraphs,
        extraction_method="html",
        extracted_at=datetime.now(UTC),
    )


def _extract_title(html: str) -> str:
    """Extract <title> content from HTML."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return _clean_text(match.group(1))
    # Fallback: first <h1>
    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if match:
        return _clean_text(match.group(1))
    return ""


def _html_to_text(html: str) -> str:
    """Convert HTML to clean text by removing tags and normalizing whitespace."""
    # Remove unwanted tags and their content
    for tag in _REMOVE_TAGS:
        html = re.sub(rf"<{tag}[^>]*>.*?</{tag}>", "", html, flags=re.IGNORECASE | re.DOTALL)

    # Remove HTML comments
    html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)

    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", " ", html)

    # Decode common HTML entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")

    return _clean_text(text)


def _clean_text(text: str) -> str:
    """Normalize whitespace in text."""
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _split_paragraphs(text: str) -> list[str]:
    """Split text into non-empty paragraphs."""
    # Split on sentence-like boundaries (double spaces or more from tag removal)
    parts = re.split(r"\s{3,}", text)
    return [p.strip() for p in parts if p.strip()]
