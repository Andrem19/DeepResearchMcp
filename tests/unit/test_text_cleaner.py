"""Unit tests for app.extract.text_cleaner — clean_text, remove_boilerplate_paragraphs."""

from __future__ import annotations

import pytest

from app.extract.text_cleaner import clean_text, remove_boilerplate_paragraphs

# ---------------------------------------------------------------------------
# clean_text
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_clean_text_collapse_whitespace():
    assert clean_text("hello   world") == "hello world"


@pytest.mark.unit
def test_clean_text_strips():
    assert clean_text("  hello  ") == "hello"


@pytest.mark.unit
def test_clean_text_empty():
    assert clean_text("") == ""


@pytest.mark.unit
def test_clean_text_removes_cookie_notice():
    text = "This site uses cookies to improve your experience. Some content here."
    result = clean_text(text)
    assert "This site uses cookies" not in result
    assert "Some content here." in result


@pytest.mark.unit
def test_clean_text_removes_newsletter():
    text = "Subscribe to our newsletter for updates. Real content follows."
    result = clean_text(text)
    assert "Subscribe to our newsletter" not in result


@pytest.mark.unit
def test_clean_text_removes_social_prompt():
    text = "Follow us on Twitter for more. Real content follows."
    result = clean_text(text)
    assert "Follow us on Twitter" not in result


@pytest.mark.unit
def test_clean_text_leaves_normal_text():
    text = "Python is a programming language."
    assert clean_text(text) == "Python is a programming language."


# ---------------------------------------------------------------------------
# remove_boilerplate_paragraphs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_removes_short_paragraphs():
    paragraphs = ["ok", "This is a longer paragraph that is not boilerplate text."]
    result = remove_boilerplate_paragraphs(paragraphs)
    assert len(result) == 1
    assert "longer paragraph" in result[0]


@pytest.mark.unit
def test_removes_cookie_paragraph():
    paragraphs = ["This website uses cookies for a better experience and tracking."]
    result = remove_boilerplate_paragraphs(paragraphs)
    assert len(result) == 0


@pytest.mark.unit
def test_removes_javascript_required():
    paragraphs = ["JavaScript is required to view this page properly."]
    result = remove_boilerplate_paragraphs(paragraphs)
    assert len(result) == 0


@pytest.mark.unit
def test_removes_copyright():
    paragraphs = ["All rights reserved. Copyright 2024 Example Corp."]
    result = remove_boilerplate_paragraphs(paragraphs)
    assert len(result) == 0


@pytest.mark.unit
def test_keeps_normal_paragraphs():
    paragraphs = [
        "Python is a versatile programming language used in web development.",
        "Machine learning models require large datasets for training.",
    ]
    result = remove_boilerplate_paragraphs(paragraphs)
    assert len(result) == 2


@pytest.mark.unit
def test_empty_list():
    assert remove_boilerplate_paragraphs([]) == []
