"""Multilingual correctness tests (v0.4.0, gap analysis §2.8)."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import fetch_page


def _resp(status=200, text="<html><head><title>t</title></head><body><p>hello world content</p></body></html>"):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = {}
    mock.history = []
    return mock


def test_fetch_page_accept_language_override():
    with patch("fetch_page.requests.get", return_value=_resp()) as mock_get:
        fetch_page("https://example.com", accept_language="he")
    sent_headers = mock_get.call_args.kwargs["headers"]
    assert sent_headers["Accept-Language"].startswith("he")


def test_fetch_page_default_language_unchanged():
    with patch("fetch_page.requests.get", return_value=_resp()) as mock_get:
        fetch_page("https://example.com")
    sent_headers = mock_get.call_args.kwargs["headers"]
    assert sent_headers["Accept-Language"].startswith("en")
