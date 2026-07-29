"""Multilingual correctness tests (v0.4.0, gap analysis §2.8)."""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import fetch_page
from brand_scanner import check_wikipedia_presence, generate_brand_report


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


def test_cli_flag_without_url_prints_usage(tmp_path):
    """fetch_page.py --accept-language he (no URL) exits with usage, not a traceback."""
    import subprocess
    proc = subprocess.run(
        [sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts", "fetch_page.py"), "--accept-language", "he"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 1
    assert "Usage:" in proc.stdout


def _json_resp(payload):
    mock = MagicMock()
    mock.status_code = 200
    mock.json.return_value = payload
    return mock


def test_hebrew_wikipedia_presence_detected():
    """Brand with a he.wikipedia article and no en article must count as present."""
    def fake_get(url, **kwargs):
        if "he.wikipedia.org" in url:
            return _json_resp({"query": {"search": [{"title": "מותג בדיקה"}]}})
        if "en.wikipedia.org" in url:
            return _json_resp({"query": {"search": []}})
        return _json_resp({"search": []})  # wikidata

    with patch("brand_scanner.requests.get", side_effect=fake_get):
        result = check_wikipedia_presence("מותג בדיקה", languages=("en", "he"))
    assert result["has_wikipedia_page"] is True
    assert result["languages"]["he"]["found"] is True
    assert result["languages"]["en"]["found"] is False


def test_default_languages_include_en_and_he():
    with patch("brand_scanner.requests.get", return_value=_json_resp({"query": {"search": []}, "search": []})) as mock_get:
        check_wikipedia_presence("Some Brand")
    urls = [c.args[0] for c in mock_get.call_args_list]
    assert any("en.wikipedia.org" in u for u in urls)
    assert any("he.wikipedia.org" in u for u in urls)


def test_brand_report_passes_languages_through():
    with patch("brand_scanner.requests.get", return_value=_json_resp({"query": {"search": []}, "search": []})):
        report = generate_brand_report("Some Brand", languages=("en", "he"))
    assert "languages" in report["platforms"]["wikipedia"]


def test_wikimedia_calls_use_descriptive_ua():
    """Wikimedia 403s spoofed browser UAs (T400119) — API calls must self-identify."""
    with patch("brand_scanner.requests.get", return_value=_json_resp({"query": {"search": []}, "search": []})) as mock_get:
        check_wikipedia_presence("Some Brand")
    for call in mock_get.call_args_list:
        ua = call.kwargs["headers"]["User-Agent"]
        assert "GEO-Reporter" in ua
        assert "Chrome" not in ua
