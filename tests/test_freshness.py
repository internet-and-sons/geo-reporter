"""Freshness extraction tests (v0.4.0, gap analysis §1.4).

~Half of AI-cited pages were published/updated within the prior 13 weeks
(Ahrefs 2026). fetch_page now extracts dates and assigns a tier:
  fresh < 90d, aging 90-365d, stale 365-730d, very-stale > 730d,
  unknown when no date is discoverable.
Tests generate dates relative to now so they never go stale.
"""

import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from bs4 import BeautifulSoup
from fetch_page import extract_freshness


def _days_ago(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def test_jsonld_date_modified_preferred_and_tier_fresh():
    sd = [{"@type": "Article", "datePublished": _days_ago(400), "dateModified": _days_ago(10)}]
    result = extract_freshness(sd, None, {})
    assert result["source"] == "structured_data"
    assert result["tier"] == "fresh"
    assert result["age_days"] <= 11


def test_jsonld_published_only_tier_aging():
    sd = [{"@type": "Article", "datePublished": _days_ago(180)}]
    result = extract_freshness(sd, None, {})
    assert result["tier"] == "aging"


def test_time_tag_fallback():
    html = f'<html><body><time datetime="{_days_ago(30)}">last month</time></body></html>'
    soup = BeautifulSoup(html, "lxml")
    result = extract_freshness([], soup, {})
    assert result["source"] == "time_tag"
    assert result["tier"] == "fresh"


def test_last_modified_header_fallback():
    dt = datetime.now(timezone.utc) - timedelta(days=800)
    header = dt.strftime("%a, %d %b %Y %H:%M:%S GMT")
    result = extract_freshness([], None, {"Last-Modified": header})
    assert result["source"] == "http_header"
    assert result["tier"] == "very-stale"


def test_no_date_is_unknown():
    result = extract_freshness([], None, {})
    assert result["tier"] == "unknown"
    assert result["age_days"] is None


def test_unparseable_date_is_unknown_not_crash():
    sd = [{"@type": "Article", "datePublished": "not a date"}]
    result = extract_freshness(sd, None, {})
    assert result["tier"] == "unknown"
