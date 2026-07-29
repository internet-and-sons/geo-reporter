"""
Tests for the WAF/CDN challenge fallback inside ``fetch_page()``.

``is_challenge_page`` and the Playwright baseline were previously wired
only into ``probe_ai_crawlers``. ``fetch_page()`` — which every
content/technical/schema analysis depends on — parsed Cloudflare block
pages as if they were the site's real content.

Contract covered here:
  - normal page          -> fetch_method "default", challenge_detected False, ONE GET
  - challenge then rescue -> retry with the GPTBot UA, parse the retry body,
                             fetch_method "bot_ua_fallback", TWO GETs
  - challenge both times  -> best-effort parse, challenge_detected True,
                             fetch_method "default", explanatory error
  - ordinary 403/404/500  -> NO retry (guard against retry storms)

Mocking style mirrors test_fetch_page_bots.py / test_agent_readiness.py:
patch ``fetch_page.requests.get`` and feed responses via ``side_effect``.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import AI_CRAWLERS, fetch_page, is_challenge_page  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(status=200, text="<html><body>content</body></html>", headers=None):
    """Build a minimal mock requests.Response for fetch_page()."""
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = headers or {}
    mock.history = []
    mock.url = "https://example.com/"
    return mock


REAL_HTML = (
    "<!DOCTYPE html><html><head><title>Real Article</title>"
    '<meta name="description" content="A real page">'
    "</head><body><h1>Real article heading</h1>"
    + ("<p>Genuine server-rendered sentence with several real words here. </p>" * 30)
    + "</body></html>"
)

# 503 + "Just a moment..." is the canonical Cloudflare interstitial.
CHALLENGE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body><div class=\"cf-challenge\">Checking your browser before accessing.</div>"
    "<div id=\"cf-turnstile\"></div></body></html>"
)

# A second, distinguishable challenge body for the both-challenged case.
CHALLENGE_HTML_2 = (
    "<!DOCTYPE html><html><head><title>Attention Required</title></head>"
    "<body><div class=\"cf-challenge\">Enable JavaScript and cookies to continue</div>"
    "</body></html>"
)

# An ordinary application 403 — no Cloudflare/WAF markers anywhere.
PLAIN_403_HTML = (
    "<!DOCTYPE html><html><head><title>Forbidden</title></head>"
    "<body><h1>403 Forbidden</h1><p>You do not have permission to view "
    "this directory or page.</p></body></html>"
)


# ---------------------------------------------------------------------------
# Fixture sanity — the fixtures must actually trip / not trip the detector
# ---------------------------------------------------------------------------

def test_fixtures_match_detector_expectations():
    assert is_challenge_page(CHALLENGE_HTML, 503) is True
    assert is_challenge_page(CHALLENGE_HTML_2, 403) is True
    assert is_challenge_page(REAL_HTML, 200) is False
    assert is_challenge_page(PLAIN_403_HTML, 403) is False


# ---------------------------------------------------------------------------
# Default (non-challenged) path must be unchanged
# ---------------------------------------------------------------------------

def test_normal_page_uses_default_method_and_one_request():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [_resp(200, REAL_HTML)]
        result = fetch_page("https://example.com/")

    assert mock_get.call_count == 1
    assert result["fetch_method"] == "default"
    assert result["challenge_detected"] is False
    assert result["status_code"] == 200
    assert result["title"] == "Real Article"
    assert result["word_count"] > 0


def test_normal_page_does_not_send_a_bot_user_agent():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [_resp(200, REAL_HTML)]
        fetch_page("https://example.com/")

    sent_ua = mock_get.call_args_list[0].kwargs["headers"]["User-Agent"]
    assert sent_ua != AI_CRAWLERS["GPTBot"]["ua"]


# ---------------------------------------------------------------------------
# Challenged, then rescued by the bot user-agent
# ---------------------------------------------------------------------------

def test_challenge_then_success_uses_retry_body():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [
            _resp(503, CHALLENGE_HTML, {"Server": "cloudflare"}),
            _resp(200, REAL_HTML, {"Server": "cloudflare"}),
        ]
        result = fetch_page("https://example.com/")

    assert mock_get.call_count == 2
    assert result["challenge_detected"] is True
    assert result["fetch_method"] == "bot_ua_fallback"
    # Everything downstream must reflect the RETRY response.
    assert result["status_code"] == 200
    assert result["title"] == "Real Article"
    assert result["h1_tags"] == ["Real article heading"]
    assert result["word_count"] > 50
    assert "Genuine server-rendered sentence" in result["text_content"]


def test_retry_sends_the_gptbot_user_agent():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [
            _resp(503, CHALLENGE_HTML),
            _resp(200, REAL_HTML),
        ]
        fetch_page("https://example.com/")

    retry_headers = mock_get.call_args_list[1].kwargs["headers"]
    assert retry_headers["User-Agent"] == AI_CRAWLERS["GPTBot"]["ua"]


def test_retry_preserves_other_request_headers():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [
            _resp(503, CHALLENGE_HTML),
            _resp(200, REAL_HTML),
        ]
        fetch_page("https://example.com/", accept_language="he")

    first_headers = mock_get.call_args_list[0].kwargs["headers"]
    retry_headers = mock_get.call_args_list[1].kwargs["headers"]
    assert retry_headers["Accept-Language"].startswith("he")
    # The first call's recorded headers must not be mutated by the retry.
    assert first_headers["User-Agent"] != AI_CRAWLERS["GPTBot"]["ua"]


def test_disguised_200_challenge_also_triggers_fallback():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [
            _resp(200, CHALLENGE_HTML),
            _resp(200, REAL_HTML),
        ]
        result = fetch_page("https://example.com/")

    assert mock_get.call_count == 2
    assert result["challenge_detected"] is True
    assert result["fetch_method"] == "bot_ua_fallback"
    assert result["title"] == "Real Article"


# ---------------------------------------------------------------------------
# Challenged both times
# ---------------------------------------------------------------------------

def test_both_responses_challenged_reports_error_and_best_effort_parse():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [
            _resp(503, CHALLENGE_HTML),
            _resp(403, CHALLENGE_HTML_2),
        ]
        result = fetch_page("https://example.com/")

    assert mock_get.call_count == 2
    assert result["challenge_detected"] is True
    assert result["fetch_method"] == "default"
    # Best-effort parse of the original response.
    assert result["status_code"] == 503
    assert result["title"] == "Just a moment..."
    assert any("challenge" in e.lower() for e in result["errors"])


def test_only_one_retry_is_ever_attempted():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [
            _resp(503, CHALLENGE_HTML),
            _resp(503, CHALLENGE_HTML),
            _resp(200, REAL_HTML),
        ]
        fetch_page("https://example.com/")

    assert mock_get.call_count == 2


# ---------------------------------------------------------------------------
# Non-challenge failures must NOT trigger a retry
# ---------------------------------------------------------------------------

def test_plain_403_does_not_retry():
    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = [_resp(403, PLAIN_403_HTML)]
        result = fetch_page("https://example.com/")

    assert mock_get.call_count == 1
    assert result["fetch_method"] == "default"
    assert result["challenge_detected"] is False
    assert result["status_code"] == 403


def test_plain_404_and_500_do_not_retry():
    for status in (404, 500):
        with patch("fetch_page.requests.get") as mock_get:
            mock_get.side_effect = [
                _resp(status, "<html><head><title>Oops</title></head><body>gone</body></html>")
            ]
            result = fetch_page("https://example.com/")

        assert mock_get.call_count == 1, f"status {status} triggered a retry"
        assert result["fetch_method"] == "default"
        assert result["challenge_detected"] is False


# ---------------------------------------------------------------------------
# Fields are always present, even on hard failures
# ---------------------------------------------------------------------------

def test_new_fields_present_on_connection_error():
    import requests as _requests

    with patch("fetch_page.requests.get") as mock_get:
        mock_get.side_effect = _requests.exceptions.ConnectionError("boom")
        result = fetch_page("https://example.com/")

    assert result["fetch_method"] == "default"
    assert result["challenge_detected"] is False
    assert result["errors"]


def test_new_fields_present_on_bad_scheme():
    result = fetch_page("ftp://example.com/")
    assert result["fetch_method"] == "default"
    assert result["challenge_detected"] is False
