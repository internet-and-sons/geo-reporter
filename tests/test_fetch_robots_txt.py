"""
Tests for fetch_robots_txt — locks in wildcard inheritance behavior.

The skills (geo-ai-visibility, geo-crawlers) now delegate robots.txt parsing
to this function instead of hand-rolling it, after past bugs where a fully
permissive `User-agent: *` + empty `Disallow:` got mis-rendered as "Unknown"
or "Unverified". These tests pin the contract those skills depend on.

Mocking style mirrors test_fetch_page_ssr.py / test_fetch_page_bots.py —
patch ``fetch_page.requests.get`` with a MagicMock.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import fetch_robots_txt  # noqa: E402


def _resp(status=200, text=""):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = {}
    return mock


# ---------------------------------------------------------------------------
# Wildcard inheritance — the law.co.il case
# ---------------------------------------------------------------------------

def test_fully_permissive_wildcard_allows_every_ai_bot_by_default():
    """User-agent: * + empty Disallow: → every unnamed AI bot is ALLOWED_BY_DEFAULT."""
    robots_text = "User-agent: *\nDisallow:\n"
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    assert result["exists"] is True
    statuses = result["ai_crawler_status"]
    for bot in ("GPTBot", "ClaudeBot", "PerplexityBot", "OAI-SearchBot",
                "ChatGPT-User", "Google-Extended", "Applebot-Extended"):
        assert statuses[bot] == "ALLOWED_BY_DEFAULT", (
            f"{bot} should be ALLOWED_BY_DEFAULT under wildcard, got {statuses[bot]}"
        )


def test_wildcard_disallow_root_blocks_every_unnamed_bot():
    """User-agent: * + Disallow: / → every unnamed bot is BLOCKED_BY_WILDCARD."""
    robots_text = "User-agent: *\nDisallow: /\n"
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    statuses = result["ai_crawler_status"]
    for bot in ("GPTBot", "ClaudeBot", "PerplexityBot"):
        assert statuses[bot] == "BLOCKED_BY_WILDCARD"


def test_named_bot_overrides_wildcard_block():
    """A bot with its own permissive block beats a restrictive wildcard."""
    robots_text = (
        "User-agent: *\nDisallow: /\n\n"
        "User-agent: GPTBot\nDisallow:\n"
    )
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    assert result["ai_crawler_status"]["GPTBot"] == "ALLOWED"
    # Other bots still inherit the wildcard block
    assert result["ai_crawler_status"]["ClaudeBot"] == "BLOCKED_BY_WILDCARD"


def test_named_bot_with_root_disallow_is_blocked():
    robots_text = "User-agent: GPTBot\nDisallow: /\n"
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    assert result["ai_crawler_status"]["GPTBot"] == "BLOCKED"


def test_named_bot_with_path_disallow_is_partially_blocked():
    robots_text = "User-agent: GPTBot\nDisallow: /private/\n"
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    assert result["ai_crawler_status"]["GPTBot"] == "PARTIALLY_BLOCKED"


def test_no_robots_txt_marks_every_bot_as_no_robots_txt():
    """A 404 on robots.txt → every bot reported as NO_ROBOTS_TXT (implicitly permitted)."""
    with patch("fetch_page.requests.get", return_value=_resp(404, "")):
        result = fetch_robots_txt("https://example.com")

    assert result["exists"] is False
    for bot in ("GPTBot", "ClaudeBot", "PerplexityBot"):
        assert result["ai_crawler_status"][bot] == "NO_ROBOTS_TXT"


def test_bot_unmentioned_and_no_wildcard_is_not_mentioned():
    """Only specific bots named, no wildcard → unnamed bots are NOT_MENTIONED."""
    robots_text = "User-agent: Googlebot\nDisallow:\n"
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    assert result["ai_crawler_status"]["GPTBot"] == "NOT_MENTIONED"
    assert result["ai_crawler_status"]["ClaudeBot"] == "NOT_MENTIONED"


def test_sitemap_directive_captured():
    robots_text = (
        "User-agent: *\nDisallow:\n"
        "Sitemap: https://example.com/sitemap.xml\n"
    )
    with patch("fetch_page.requests.get", return_value=_resp(200, robots_text)):
        result = fetch_robots_txt("https://example.com")

    assert "https://example.com/sitemap.xml" in result["sitemaps"]
