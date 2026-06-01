"""
Tests for the deterministic score fields added in v0.3.5:
  - validate_llmstxt() now returns a `score` (0-100)
  - generate_brand_report() / compute_brand_score() return a `total_score` (0-100)

Locks in the canonical scoring scales the skill instructions now depend on.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from llmstxt_generator import validate_llmstxt  # noqa: E402
from brand_scanner import compute_brand_score  # noqa: E402


def _resp(status=200, text=""):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    return mock


# ---------------------------------------------------------------------------
# llms.txt score
# ---------------------------------------------------------------------------

def test_llmstxt_score_zero_when_absent():
    with patch("llmstxt_generator.requests.get", return_value=_resp(404, "")):
        result = validate_llmstxt("https://example.com")
    assert result["exists"] is False
    assert result["score"] == 0


def test_llmstxt_score_30_when_malformed():
    """File exists but missing required elements → 30."""
    malformed = "Just some random text\nwith no structure\n"
    # First call = /llms.txt (200, malformed); second = /llms-full.txt (404)
    with patch("llmstxt_generator.requests.get",
               side_effect=[_resp(200, malformed), _resp(404, "")]):
        result = validate_llmstxt("https://example.com")
    assert result["exists"] is True
    assert result["format_valid"] is False
    assert result["score"] == 30


def test_llmstxt_score_50_when_valid_but_minimal():
    """Valid format but <5 links and <2 sections → 50."""
    minimal = (
        "# Example Site\n"
        "> A brief description of the site.\n\n"
        "## Main\n"
        "- [Home](https://example.com): Homepage\n"
    )
    with patch("llmstxt_generator.requests.get",
               side_effect=[_resp(200, minimal), _resp(404, "")]):
        result = validate_llmstxt("https://example.com")
    assert result["format_valid"] is True
    assert result["score"] == 50


def test_llmstxt_score_70_when_valid_and_substantial():
    """Valid + ≥5 links + ≥2 sections, no llms-full.txt → 70."""
    full = (
        "# Example Site\n"
        "> A description.\n\n"
        "## Section A\n"
        "- [P1](https://example.com/1): desc\n"
        "- [P2](https://example.com/2): desc\n"
        "- [P3](https://example.com/3): desc\n\n"
        "## Section B\n"
        "- [P4](https://example.com/4): desc\n"
        "- [P5](https://example.com/5): desc\n"
    )
    with patch("llmstxt_generator.requests.get",
               side_effect=[_resp(200, full), _resp(404, "")]):
        result = validate_llmstxt("https://example.com")
    assert result["score"] == 70


def test_llmstxt_score_90_when_full_version_also_present():
    """Substantial + llms-full.txt → 90."""
    full = (
        "# Example Site\n"
        "> A description.\n\n"
        "## Section A\n"
        "- [P1](https://example.com/1): desc\n"
        "- [P2](https://example.com/2): desc\n"
        "- [P3](https://example.com/3): desc\n\n"
        "## Section B\n"
        "- [P4](https://example.com/4): desc\n"
        "- [P5](https://example.com/5): desc\n"
    )
    # llms.txt 200 + llms-full.txt 200
    with patch("llmstxt_generator.requests.get",
               side_effect=[_resp(200, full), _resp(200, "full content here")]):
        result = validate_llmstxt("https://example.com")
    assert result["full_version"]["exists"] is True
    assert result["score"] == 90


# ---------------------------------------------------------------------------
# Brand score
# ---------------------------------------------------------------------------

def test_brand_score_zero_with_no_signals():
    report = {"platforms": {
        "wikipedia": {"has_wikipedia_page": False, "has_wikidata_entry": False},
        "reddit": {"has_subreddit": False, "mentioned_in_discussions": False},
        "youtube": {"has_channel": False, "mentioned_in_videos": False},
        "linkedin": {"has_company_page": False},
        "other": {"platforms_checked": {}},
    }}
    assert compute_brand_score(report) == 0


def test_brand_score_wikipedia_only():
    """Wikipedia presence alone = 30."""
    report = {"platforms": {
        "wikipedia": {"has_wikipedia_page": True, "has_wikidata_entry": False},
        "reddit": {}, "youtube": {}, "linkedin": {},
        "other": {"platforms_checked": {}},
    }}
    assert compute_brand_score(report) == 30


def test_brand_score_full_house_caps_at_100():
    """All platforms confirmed → 30+20+15+10+25 = 100."""
    report = {"platforms": {
        "wikipedia": {"has_wikipedia_page": True, "has_wikidata_entry": True},
        "reddit": {"has_subreddit": True, "mentioned_in_discussions": True},
        "youtube": {"has_channel": True, "mentioned_in_videos": True},
        "linkedin": {"has_company_page": True},
        "other": {"platforms_checked": {
            "G2": {"confirmed": True},
            "Crunchbase": {"confirmed": True},
        }},
    }}
    assert compute_brand_score(report) == 100


def test_brand_score_partial_combo():
    """Wikipedia + LinkedIn + Industry = 30 + 10 + 25 = 65."""
    report = {"platforms": {
        "wikipedia": {"has_wikipedia_page": True},
        "reddit": {},
        "youtube": {},
        "linkedin": {"has_company_page": True},
        "other": {"platforms_checked": {"Trustpilot": {"confirmed": True}}},
    }}
    assert compute_brand_score(report) == 65


def test_brand_report_includes_total_score():
    """generate_brand_report() returns a top-level total_score field."""
    from brand_scanner import generate_brand_report
    # Suppress real network calls — Wikipedia/Wikidata API hits inside
    # check_wikipedia_presence. We don't care about the value, only that
    # the field exists and is in range.
    with patch("brand_scanner.requests.get",
               return_value=_resp(200, '{"query":{"search":[]},"search":[]}')):
        report = generate_brand_report("Some Test Brand")
    assert "total_score" in report
    assert 0 <= report["total_score"] <= 100
