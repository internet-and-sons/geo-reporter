"""
Roster integrity tests for AI_CRAWLERS (v0.4.0).

The roster is the single source of truth for BOTH the live probe and
the robots.txt parser. Every entry has a status:
  active        — real crawler, probed live
  retired       — legacy token; kept for declared-policy analysis and
                  stale-config detection, never probed
  opt-out-token — robots.txt signal only (Google-Extended etc.); the
                  operator never fetches with this UA, so probing it is
                  meaningless. Declared-policy analysis only.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import AI_CRAWLERS, BOT_CLASSES, active_crawlers, fetch_robots_txt


def test_every_entry_has_valid_status():
    for name, info in AI_CRAWLERS.items():
        assert info.get("status", "active") in ("active", "retired", "opt-out-token"), name


def test_retired_tokens_present_and_marked():
    for token in ("anthropic-ai", "claude-web", "FacebookBot"):
        assert token in AI_CRAWLERS, f"{token} must stay in roster for stale-config detection"
        assert AI_CRAWLERS[token]["status"] == "retired", token


def test_opt_out_tokens_marked():
    for token in ("Google-Extended", "Applebot-Extended"):
        assert AI_CRAWLERS[token]["status"] == "opt-out-token", token


def test_new_2026_bots_present_and_active():
    expected = {
        "MistralAI-User": ("live-retrieval", "Mistral"),
        "DuckAssistBot": ("search-index", "DuckDuckGo"),
        "Google-Agent": ("live-retrieval", "Google"),
        "Google-CloudVertexBot": ("training", "Google"),
        "Google-NotebookLM": ("live-retrieval", "Google"),
        "Amazonbot": ("search-index", "Amazon"),
    }
    for name, (cls, operator) in expected.items():
        assert name in AI_CRAWLERS, name
        assert AI_CRAWLERS[name]["class"] == cls, name
        assert AI_CRAWLERS[name]["operator"] == operator, name
        assert AI_CRAWLERS[name].get("status", "active") == "active", name


def test_every_class_is_known():
    for name, info in AI_CRAWLERS.items():
        assert info["class"] in BOT_CLASSES, name


def test_active_crawlers_helper_excludes_non_active():
    act = active_crawlers()
    assert "GPTBot" in act
    assert "anthropic-ai" not in act
    assert "Google-Extended" not in act
    assert "FacebookBot" not in act
    for name in act:
        assert AI_CRAWLERS[name].get("status", "active") == "active"


def _resp(status=200, text=""):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    return mock


def test_robots_parser_covers_entire_roster():
    """Declared-policy analysis covers ALL roster entries (incl. retired/opt-out)."""
    with patch("fetch_page.requests.get", return_value=_resp(200, "User-agent: *\nDisallow:\n")):
        result = fetch_robots_txt("https://example.com")
    assert set(result["ai_crawler_status"].keys()) == set(AI_CRAWLERS.keys())


def test_stale_tokens_flagged_when_present_in_robots():
    robots = (
        "User-agent: anthropic-ai\nAllow: /\n\n"
        "User-agent: GPTBot\nAllow: /\n"
    )
    with patch("fetch_page.requests.get", return_value=_resp(200, robots)):
        result = fetch_robots_txt("https://example.com")
    assert "anthropic-ai" in result["stale_tokens"]
    assert "GPTBot" not in result["stale_tokens"]


def test_stale_tokens_empty_when_none_present():
    with patch("fetch_page.requests.get", return_value=_resp(200, "User-agent: *\nDisallow:\n")):
        result = fetch_robots_txt("https://example.com")
    assert result["stale_tokens"] == []
