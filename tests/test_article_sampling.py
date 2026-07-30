"""Child-article sampling tests (v0.4.4, "audit the citable unit").

classify_page_type() tells us a URL is a listing. That answer is only
useful if we can then name the articles beneath it — those are the units
AI engines cite, and they are what the audit should actually score.

sample_child_articles(page_data, limit=5, timeout=15) returns:

    {"candidates": [...urls...],       # heuristic, no network
     "sampled": [{"url","type","confidence"}...],   # verified articles
     "verified_count": int,
     "errors": [...strings...]}

Two properties matter beyond "it returns some URLs":

  * The sample is SPREAD across the candidate list, not the first N.
    Top-of-page items on a news section are the featured ones —
    systematically the freshest and best-edited — so a first-N sample
    biases every audit optimistically. A human analyst spreads.
  * Nothing unverified reaches `sampled`. A candidate that fails to
    fetch, or that turns out to be another listing, is recorded in
    `errors` with a reason and excluded — never guessed at.

Mocking style mirrors test_challenge_fallback.py: patch
``fetch_page.requests.get`` and route by URL.
"""

import os
import sys
from unittest.mock import MagicMock, patch

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import sample_child_articles  # noqa: E402


HOST = "https://www.example.com"
LISTING_URL = f"{HOST}/democracy/"


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

_FILLER = "<p>A genuine server-rendered sentence with several real words. </p>" * 40


def _article_html(headline="A story"):
    """A page that classify_page_type() calls an article: NewsArticle
    schema, exactly one h1, a machine-readable date."""
    return (
        "<!DOCTYPE html><html><head><title>%s</title>"
        '<script type="application/ld+json">'
        '{"@context":"https://schema.org","@type":"NewsArticle",'
        '"headline":"%s","datePublished":"2026-07-25T10:00:00+03:00"}'
        "</script></head><body><h1>%s</h1>%s</body></html>"
    ) % (headline, headline, headline, _FILLER)


def _listing_html():
    """A page that classify_page_type() calls a listing: no Article
    schema, many h1s, many article-shaped links."""
    headings = "".join(f"<h1>Headline {i}</h1>" for i in range(6))
    links = "".join(
        f'<a href="{HOST}/{810000 + i}/">Story {i}</a>' for i in range(14)
    )
    return (
        "<!DOCTYPE html><html><head><title>Section</title></head>"
        f"<body>{headings}{links}{_FILLER}</body></html>"
    )


def _resp(text, status=200, url=HOST + "/"):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = {}
    mock.history = []
    mock.url = url
    return mock


def _page(links, url=LISTING_URL):
    """A minimal fetch_page()-shaped dict for the listing being sampled."""
    return {
        "url": url,
        "h1_tags": ["Headline"] * 6,
        "structured_data": [],
        "freshness": {"tier": "unknown", "best_date": None},
        "internal_links": links,
        "word_count": 900,
    }


def _links(count, start=700000, host=HOST):
    return [
        {"url": f"{host}/{start + i}/", "text": f"Story {i}"} for i in range(count)
    ]


def _router(mapping, default=None):
    """requests.get side_effect: serve HTML by URL."""
    def _get(url, *args, **kwargs):
        if url in mapping:
            value = mapping[url]
            if isinstance(value, Exception):
                raise value
            return value
        if default is None:
            raise AssertionError(f"unexpected fetch of {url}")
        return default
    return _get


def _all_articles():
    """Every URL fetched comes back as a valid article."""
    def _get(url, *args, **kwargs):
        return _resp(_article_html(f"Story at {url}"), url=url)
    return _get


# ---------------------------------------------------------------------------
# 1. candidate extraction — heuristic, no network
# ---------------------------------------------------------------------------


def test_navigation_links_are_not_candidates():
    links = [
        {"url": f"{HOST}/tag/politics/", "text": "Politics"},
        {"url": f"{HOST}/about/", "text": "About"},
        {"url": f"{HOST}/author/37401/", "text": "A Writer"},
        # zman.co.il uses /writer/<id>/ — a numeric-ID byline page, which
        # the numeric-segment rule would otherwise read as an article.
        {"url": f"{HOST}/writer/37958/", "text": "Another Writer"},
        {"url": f"{HOST}/category/news/", "text": "News"},
        {"url": f"{HOST}/708066/", "text": "A real story"},
        {"url": f"{HOST}/a-hyphenated-story-slug/", "text": "Another story"},
    ]
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=5)

    assert result["candidates"] == [
        f"{HOST}/708066/",
        f"{HOST}/a-hyphenated-story-slug/",
    ]


def test_offsite_links_are_not_candidates():
    links = [
        {"url": "https://other.example.org/708066/", "text": "Elsewhere"},
        {"url": f"{HOST}/708067/", "text": "Here"},
    ]
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=5)

    assert result["candidates"] == [f"{HOST}/708067/"]


def test_the_page_itself_is_not_a_candidate():
    self_url = f"{HOST}/some-section-page/"
    links = [
        {"url": self_url, "text": "You are here"},
        {"url": f"{HOST}/708066/", "text": "A story"},
    ]
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links, url=self_url), limit=5)

    assert result["candidates"] == [f"{HOST}/708066/"]


def test_candidates_are_deduped_preserving_first_seen_order():
    links = [
        {"url": f"{HOST}/708066/", "text": "Headline"},
        {"url": f"{HOST}/708067/", "text": "Other"},
        {"url": f"{HOST}/708066/", "text": "Same story, image link"},
    ]
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=5)

    assert result["candidates"] == [f"{HOST}/708066/", f"{HOST}/708067/"]


def test_bare_string_links_are_handled():
    links = [f"{HOST}/708066/", {"url": f"{HOST}/708067/", "text": "Two"}, None, 42]
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=5)

    assert result["candidates"] == [f"{HOST}/708066/", f"{HOST}/708067/"]


# ---------------------------------------------------------------------------
# 2. the sample is spread, not the first N
# ---------------------------------------------------------------------------


def test_sample_is_spread_across_candidates_not_first_n():
    links = _links(40)
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=5)

    picked = [entry["url"] for entry in result["sampled"]]
    # Evenly spaced across the 40 candidates: indices 0, 9, 19, 29, 39.
    assert picked == [
        f"{HOST}/700000/",
        f"{HOST}/700009/",
        f"{HOST}/700019/",
        f"{HOST}/700029/",
        f"{HOST}/700039/",
    ]
    # And explicitly NOT the first five.
    assert picked != [f"{HOST}/{700000 + i}/" for i in range(5)]
    assert result["verified_count"] == 5


def test_sample_is_capped_at_limit_fetches():
    links = _links(40)
    fake_get = MagicMock(side_effect=_all_articles())
    with patch("fetch_page.requests.get", fake_get):
        result = sample_child_articles(_page(links), limit=3)

    assert len(result["candidates"]) == 40
    assert fake_get.call_count == 3
    assert len(result["sampled"]) == 3


def test_fewer_candidates_than_limit_samples_all_of_them():
    links = _links(2)
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=5)

    assert [entry["url"] for entry in result["sampled"]] == [
        f"{HOST}/700000/",
        f"{HOST}/700001/",
    ]


def test_sampling_is_deterministic_across_runs():
    links = _links(37)
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        first = sample_child_articles(_page(links), limit=5)
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        second = sample_child_articles(_page(links), limit=5)

    assert first["sampled"] == second["sampled"]
    assert first["candidates"] == second["candidates"]


# ---------------------------------------------------------------------------
# 3. verification — only confirmed articles are counted
# ---------------------------------------------------------------------------


def test_verification_records_type_and_confidence():
    links = _links(3)
    with patch("fetch_page.requests.get", side_effect=_all_articles()):
        result = sample_child_articles(_page(links), limit=3)

    assert result["verified_count"] == 3
    for entry in result["sampled"]:
        assert entry["type"] == "article"
        assert entry["confidence"] == "high"
    assert result["errors"] == []


def test_candidate_that_classifies_as_listing_is_excluded_with_a_reason():
    links = _links(3)
    mapping = {
        f"{HOST}/700000/": _resp(_article_html(), url=f"{HOST}/700000/"),
        f"{HOST}/700001/": _resp(_listing_html(), url=f"{HOST}/700001/"),
        f"{HOST}/700002/": _resp(_article_html(), url=f"{HOST}/700002/"),
    }
    with patch("fetch_page.requests.get", side_effect=_router(mapping)):
        result = sample_child_articles(_page(links), limit=3)

    sampled_urls = [entry["url"] for entry in result["sampled"]]
    assert sampled_urls == [f"{HOST}/700000/", f"{HOST}/700002/"]
    assert result["verified_count"] == 2
    assert len(result["errors"]) == 1
    assert f"{HOST}/700001/" in result["errors"][0]
    assert "listing" in result["errors"][0]


def test_fetch_failure_is_recorded_and_never_sampled():
    links = _links(3)
    mapping = {
        f"{HOST}/700000/": _resp(_article_html(), url=f"{HOST}/700000/"),
        f"{HOST}/700001/": requests.exceptions.ConnectionError("boom"),
        f"{HOST}/700002/": _resp(_article_html(), url=f"{HOST}/700002/"),
    }
    with patch("fetch_page.requests.get", side_effect=_router(mapping)):
        result = sample_child_articles(_page(links), limit=3)

    sampled_urls = [entry["url"] for entry in result["sampled"]]
    assert f"{HOST}/700001/" not in sampled_urls
    assert result["verified_count"] == 2
    assert any(f"{HOST}/700001/" in err for err in result["errors"])


def test_http_error_status_is_recorded_and_never_sampled():
    links = _links(2)
    mapping = {
        f"{HOST}/700000/": _resp("<html><body>gone</body></html>", status=404,
                                 url=f"{HOST}/700000/"),
        f"{HOST}/700001/": _resp(_article_html(), url=f"{HOST}/700001/"),
    }
    with patch("fetch_page.requests.get", side_effect=_router(mapping)):
        result = sample_child_articles(_page(links), limit=2)

    assert [entry["url"] for entry in result["sampled"]] == [f"{HOST}/700001/"]
    assert result["verified_count"] == 1
    assert any("404" in err for err in result["errors"])


# ---------------------------------------------------------------------------
# 4. degenerate input
# ---------------------------------------------------------------------------


def test_empty_internal_links_returns_an_empty_result_without_fetching():
    fake_get = MagicMock()
    with patch("fetch_page.requests.get", fake_get):
        result = sample_child_articles(_page([]), limit=5)

    assert result == {
        "candidates": [],
        "sampled": [],
        "verified_count": 0,
        "errors": [],
    }
    assert fake_get.call_count == 0


def test_missing_internal_links_key_does_not_crash():
    fake_get = MagicMock()
    with patch("fetch_page.requests.get", fake_get):
        result = sample_child_articles({"url": LISTING_URL}, limit=5)

    assert result["candidates"] == []
    assert result["verified_count"] == 0
    assert fake_get.call_count == 0


def test_none_page_data_does_not_crash():
    fake_get = MagicMock()
    with patch("fetch_page.requests.get", fake_get):
        result = sample_child_articles(None)

    assert result["candidates"] == []
    assert result["sampled"] == []
    assert fake_get.call_count == 0
