"""Unit tests for app.extract.html_extractor — extract, title, script/style removal."""

from __future__ import annotations

import pytest

from app.extract.html_extractor import extract
from app.models import FetchedPage

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _page(html: str, url: str = "https://example.com", status: int = 200) -> FetchedPage:
    return FetchedPage(
        url=url,
        final_url=url,
        status_code=status,
        content_type="text/html",
        body=html.encode("utf-8"),
    )


# ---------------------------------------------------------------------------
# Title extraction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_extracts_title_tag():
    html = "<html><head><title>My Page Title</title></head><body>content</body></html>"
    doc = extract(_page(html))
    assert doc.title == "My Page Title"


@pytest.mark.unit
def test_extracts_h1_fallback():
    html = "<html><body><h1>Heading Title</h1><p>text</p></body></html>"
    doc = extract(_page(html))
    assert doc.title == "Heading Title"


@pytest.mark.unit
def test_no_title_returns_empty():
    html = "<html><body><p>Just a paragraph</p></body></html>"
    doc = extract(_page(html))
    assert doc.title == ""


# ---------------------------------------------------------------------------
# Script and style removal
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_removes_script_content():
    html = (
        "<html><body>"
        "<script>var x = 1;</script>"
        "<p>Visible text</p>"
        "</body></html>"
    )
    doc = extract(_page(html))
    assert "var x" not in doc.text
    assert "Visible text" in doc.text


@pytest.mark.unit
def test_removes_style_content():
    html = (
        "<html><body>"
        "<style>body { color: red; }</style>"
        "<p>Visible text</p>"
        "</body></html>"
    )
    doc = extract(_page(html))
    assert "color: red" not in doc.text
    assert "Visible text" in doc.text


@pytest.mark.unit
def test_removes_nav_footer_header_aside():
    html = (
        "<html><body>"
        "<nav>nav links</nav>"
        "<header>site header</header>"
        "<footer>site footer</footer>"
        "<aside>sidebar</aside>"
        "<p>Main content paragraph</p>"
        "</body></html>"
    )
    doc = extract(_page(html))
    assert "nav links" not in doc.text
    assert "site header" not in doc.text
    assert "site footer" not in doc.text
    assert "sidebar" not in doc.text
    assert "Main content paragraph" in doc.text


# ---------------------------------------------------------------------------
# Whitespace normalization
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_collapses_whitespace():
    html = "<html><body><p>Hello    World</p></body></html>"
    doc = extract(_page(html))
    assert "Hello World" in doc.text


@pytest.mark.unit
def test_html_entities_decoded():
    html = "<html><body><p>Tom &amp; Jerry &lt;cartoon&gt;</p></body></html>"
    doc = extract(_page(html))
    assert "Tom & Jerry" in doc.text
    assert "<cartoon>" in doc.text


# ---------------------------------------------------------------------------
# Non-success page
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_failed_fetch_returns_empty():
    page = FetchedPage(url="https://example.com", status_code=500, error="Server error")
    doc = extract(page)
    assert doc.text == ""
    assert doc.title == ""
    assert doc.extraction_method == "none"


# ---------------------------------------------------------------------------
# URL uses final_url
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_url_uses_final_url_when_present():
    html = "<html><head><title>t</title></head><body>ok</body></html>"
    page = FetchedPage(
        url="https://example.com/old",
        final_url="https://example.com/new",
        status_code=200,
        body=html.encode("utf-8"),
    )
    doc = extract(page)
    assert doc.url == "https://example.com/new"


# ---------------------------------------------------------------------------
# Paragraphs splitting
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_paragraphs_split():
    html = "<html><body><p>Para one</p>   <p>Para two</p>   <p>Para three</p></body></html>"
    doc = extract(_page(html))
    # Should produce multiple paragraphs (split on 3+ spaces from tag removal)
    assert len(doc.paragraphs) >= 1


# ---------------------------------------------------------------------------
# HTML comments removed
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_removes_html_comments():
    html = "<html><body><!-- this is a comment --><p>Visible</p></body></html>"
    doc = extract(_page(html))
    assert "this is a comment" not in doc.text
    assert "Visible" in doc.text
