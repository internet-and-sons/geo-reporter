"""
Tests for the WAF/CDN challenge fallback inside ``analyze_page_citability()``.

v0.4.3 taught ``fetch_page()`` to retry a Cloudflare-challenged fetch with the
GPTBot user-agent. The citability scorer kept doing its own bare
``requests.get`` + ``raise_for_status()``, so on a challenge-fronted site it
returned ``{"error": "Failed to fetch page: 403 Client Error: Forbidden"}`` and
scored nothing — silently dropping the single largest component (25%) of the
composite GEO score.

Contract covered here, mirroring tests/test_challenge_fallback.py:
  - normal page           -> fetch_method "default", challenge_detected False, ONE GET
  - challenge then rescue -> retry with the GPTBot UA, score the RETRY body,
                             fetch_method "bot_ua_fallback", challenge_detected
                             True, TWO GETs, real blocks scored
  - challenged both times  -> existing {"error": ...} shape, message names the
                             challenge, challenge_detected discoverable
  - ordinary 403 body     -> NO retry (guard against retry storms), existing
                             {"error": ...} shape

Mocking style mirrors tests/test_citability_scorer.py: patch
``citability_scorer.requests.get`` and feed responses via ``side_effect``.
"""

import sys
import os
from unittest.mock import patch, MagicMock

import pytest
import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from citability_scorer import analyze_page_citability  # noqa: E402
from fetch_page import AI_CRAWLERS, is_challenge_page  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(status=200, text="", raises=None):
    """Build a minimal mock requests.Response for the citability scorer."""
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.raise_for_status = MagicMock(side_effect=raises)
    return mock


def _article_html(title, heading, marker):
    """Real-looking prose with enough words to clear the block extractor.

    The extractor keeps <p> elements of >= 5 words and emits a block only when
    the combined paragraphs under a heading total >= 20 words. Fixtures must
    clear both thresholds or a "rescued" assertion would pass vacuously with
    zero blocks scored.
    """
    paragraphs = "".join(
        f"<p>{marker} Paragraph {i} records the measured finding in plain "
        f"language, with a concrete figure of {i * 7} percent and enough "
        f"genuine words to clear the extractor threshold comfortably.</p>"
        for i in range(1, 7)
    )
    return (
        f"<!DOCTYPE html><html><head><title>{title}</title></head><body>"
        f"<h1>{heading}</h1>{paragraphs}"
        f"<h2>{heading} continued</h2>{paragraphs}"
        "</body></html>"
    )


REAL_HTML = _article_html(
    "Real Article", "Rescued Content Heading", "RESCUEDBODY"
)

# 503 + "Just a moment..." is the canonical Cloudflare interstitial, and the
# body also carries the cf-challenge / cf-turnstile markers.
CHALLENGE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    '<body><div class="cf-challenge">Checking your browser before accessing.'
    '</div><div id="cf-turnstile"></div></body></html>'
)

# A second, distinguishable challenge body for the both-challenged case.
BOT_CHALLENGE_HTML = (
    "<!DOCTYPE html><html><head><title>Attention Required!</title></head>"
    '<body><div id="challenge-platform">Please enable JavaScript and cookies '
    "to continue.</div></body></html>"
)

# An ordinary 403: no Cloudflare markers, no "cloudflare" string anywhere.
PLAIN_403_HTML = (
    "<!DOCTYPE html><html><head><title>Forbidden</title></head><body>"
    "<h1>Forbidden</h1><p>You do not have permission to access this "
    "resource on this server.</p></body></html>"
)


def test_fixtures_are_recognised_by_the_shared_detector():
    """Guard the fixtures themselves: they must trip the real detector."""
    assert is_challenge_page(CHALLENGE_HTML, 503) is True
    assert is_challenge_page(BOT_CHALLENGE_HTML, 403) is True
    assert is_challenge_page(PLAIN_403_HTML, 403) is False
    assert is_challenge_page(REAL_HTML, 200) is False


# ---------------------------------------------------------------------------
# 1. Normal page — no challenge, no retry
# ---------------------------------------------------------------------------

def test_normal_page_scores_with_a_single_get():
    with patch("citability_scorer.requests.get",
               return_value=_resp(200, REAL_HTML)) as mock_get:
        result = analyze_page_citability("https://example.com/article")

    assert "error" not in result
    assert mock_get.call_count == 1
    assert result["fetch_method"] == "default"
    assert result["challenge_detected"] is False
    assert result["total_blocks_analyzed"] > 0
    assert result["average_citability_score"] > 0


# ---------------------------------------------------------------------------
# 2. Challenged, then rescued by the GPTBot UA
# ---------------------------------------------------------------------------

def test_challenge_then_rescue_scores_the_retry_body():
    with patch("citability_scorer.requests.get",
               side_effect=[_resp(503, CHALLENGE_HTML),
                            _resp(200, REAL_HTML)]) as mock_get:
        result = analyze_page_citability("https://example.com/article")

    assert "error" not in result
    assert mock_get.call_count == 2
    assert result["fetch_method"] == "bot_ua_fallback"
    assert result["challenge_detected"] is True

    # Not vacuous: real blocks came out of the RETRY body.
    assert result["total_blocks_analyzed"] > 0
    assert result["average_citability_score"] > 0
    all_content = " ".join(
        f"{b.get('heading') or ''} {b.get('preview', '')}"
        for b in result["all_blocks"]
    )
    assert "RESCUEDBODY" in all_content
    assert "Rescued Content Heading" in all_content
    assert "Checking your browser" not in all_content


def test_retry_uses_the_gptbot_user_agent():
    with patch("citability_scorer.requests.get",
               side_effect=[_resp(503, CHALLENGE_HTML),
                            _resp(200, REAL_HTML)]) as mock_get:
        analyze_page_citability("https://example.com/article")

    retry_headers = mock_get.call_args_list[1].kwargs["headers"]
    assert retry_headers["User-Agent"] == AI_CRAWLERS["GPTBot"]["ua"]
    assert "GPTBot" in retry_headers["User-Agent"]

    # The first attempt must NOT use a bot UA — it's the browser view.
    first_headers = mock_get.call_args_list[0].kwargs["headers"]
    assert "GPTBot" not in first_headers["User-Agent"]
    # And it must be a complete browser UA, not a truncated one.
    assert first_headers["User-Agent"].startswith("Mozilla/5.0")
    assert "Safari/537.36" in first_headers["User-Agent"]


# ---------------------------------------------------------------------------
# 3. Challenged both ways — error contract preserved, challenge disclosed
# ---------------------------------------------------------------------------

def test_challenged_both_ways_returns_error_naming_the_challenge():
    with patch("citability_scorer.requests.get",
               side_effect=[_resp(503, CHALLENGE_HTML),
                            _resp(403, BOT_CHALLENGE_HTML)]) as mock_get:
        result = analyze_page_citability("https://example.com/article")

    assert mock_get.call_count == 2
    # Existing error contract: an "error" key holding a string.
    assert "error" in result
    assert isinstance(result["error"], str)
    assert result["error"].startswith("Failed to fetch page")
    assert "challenge" in result["error"].lower()
    # The challenge must still be discoverable by the skill layer.
    assert result["challenge_detected"] is True
    # Nothing was scored.
    assert "average_citability_score" not in result


# ---------------------------------------------------------------------------
# 4. Ordinary 403 — no retry storm
# ---------------------------------------------------------------------------

def test_plain_403_does_not_retry():
    http_error = requests.exceptions.HTTPError(
        "403 Client Error: Forbidden for url: https://example.com/article"
    )
    with patch("citability_scorer.requests.get",
               return_value=_resp(403, PLAIN_403_HTML,
                                  raises=http_error)) as mock_get:
        result = analyze_page_citability("https://example.com/article")

    assert mock_get.call_count == 1
    assert "error" in result
    assert result["error"].startswith("Failed to fetch page")
    assert "403" in result["error"]


def test_network_exception_keeps_the_error_shape():
    with patch("citability_scorer.requests.get",
               side_effect=Exception("boom")) as mock_get:
        result = analyze_page_citability("https://example.com/article")

    assert mock_get.call_count == 1
    assert result["error"] == "Failed to fetch page: boom"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
