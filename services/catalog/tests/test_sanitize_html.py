"""Dish / prep HTML sanitizer — XSS hardening."""

from app.ingredients import sanitize_html


def test_strips_script_and_handlers():
    out = sanitize_html('<p onclick="x">Hi<script>alert(1)</script></p>')
    assert "<script" not in out.lower()
    assert "onclick" not in out.lower()
    assert "Hi" in out


def test_blocks_javascript_href():
    out = sanitize_html('<a href="javascript:alert(1)">x</a>')
    assert "javascript:" not in out.lower()


def test_allows_https_links():
    out = sanitize_html('<a href="https://ok.example/path">x</a>')
    assert 'href="https://ok.example/path"' in out
    assert 'rel="noopener noreferrer"' in out
