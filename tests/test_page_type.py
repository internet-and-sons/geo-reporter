"""Page-type classification tests (v0.4.4, "audit the citable unit").

A news section listing page is a human navigation surface. The units AI
engines actually cite are the articles beneath it. classify_page_type()
reads an existing fetch_page() result dict — no network — and says which
kind of page it is, so the audit can target the right unit.

Every fixture here is a plain dict shaped like a fetch_page() result.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import classify_page_type


# --------------------------------------------------------------------------
# fixture builders
# --------------------------------------------------------------------------


def _page(**overrides):
    """A minimal fetch_page()-shaped dict; override the keys under test."""
    page = {
        "url": "https://example.com/some-page/",
        "h1_tags": ["A heading"],
        "structured_data": [],
        "freshness": {"tier": "unknown", "best_date": None},
        "internal_links": [],
        "word_count": 500,
    }
    page.update(overrides)
    return page


def _numeric_links(count, host="https://www.zman.co.il"):
    """Article-shaped links: bare numeric-ID paths, as zman.co.il uses."""
    return [
        {"url": f"{host}/{700000 + i}/", "text": f"Story {i}"} for i in range(count)
    ]


NEWSARTICLE_SCHEMA = [
    {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": "A story",
        "datePublished": "2026-07-29T12:05:57+03:00",
    }
]


# --------------------------------------------------------------------------
# 1. real article shape
# --------------------------------------------------------------------------


def test_newsarticle_schema_one_h1_and_resolved_freshness_is_high_confidence_article():
    result = classify_page_type(
        _page(
            url="https://www.zman.co.il/708066/",
            h1_tags=["הפסקת התנדבות איננה סרבנות"],
            structured_data=NEWSARTICLE_SCHEMA,
            freshness={"tier": "fresh", "best_date": "2026-07-29T12:05:57+03:00"},
            internal_links=_numeric_links(3),
            word_count=1863,
        )
    )
    assert result["type"] == "article"
    assert result["confidence"] == "high"
    assert any("NewsArticle" in s for s in result["signals"])


def test_article_family_types_all_recognised():
    for schema_type in ("Article", "NewsArticle", "BlogPosting", "Report"):
        result = classify_page_type(
            _page(
                url="https://example.com/2026/07/a-long-form-story/",
                h1_tags=["A story"],
                structured_data=[{"@type": schema_type}],
                freshness={"tier": "aging", "best_date": "2026-01-02"},
            )
        )
        assert result["type"] == "article", schema_type
        assert result["confidence"] == "high", schema_type


def test_article_schema_nested_in_graph_is_found():
    result = classify_page_type(
        _page(
            url="https://example.com/2026/07/a-long-form-story/",
            h1_tags=["A story"],
            structured_data=[
                {
                    "@context": "https://schema.org",
                    "@graph": [
                        {"@type": "WebSite"},
                        {"@type": ["BlogPosting", "CreativeWork"]},
                    ],
                }
            ],
            freshness={"tier": "fresh", "best_date": "2026-07-01"},
        )
    )
    assert result["type"] == "article"


# --------------------------------------------------------------------------
# 2. the zman /democracy/ listing shape
# --------------------------------------------------------------------------


def test_zman_democracy_section_shape_is_high_confidence_listing():
    result = classify_page_type(
        _page(
            url="https://www.zman.co.il/democracy/",
            h1_tags=[f"Headline {i}" for i in range(19)],
            structured_data=[
                {"@type": "NewsMediaOrganization", "name": "זמן ישראל"},
                {"@type": "WebSite"},
            ],
            freshness={"tier": "unknown", "best_date": None},
            internal_links=_numeric_links(38),
            word_count=6131,
        )
    )
    assert result["type"] == "listing"
    assert result["confidence"] == "high"
    joined = " | ".join(result["signals"])
    assert "19" in joined
    assert "38" in joined
    assert "no Article-family schema" in joined


def test_listing_on_h1_count_alone_still_classifies_as_listing():
    result = classify_page_type(
        _page(
            url="https://example.com/news/",
            h1_tags=[f"Headline {i}" for i in range(8)],
            structured_data=[{"@type": "WebSite"}],
            freshness={"tier": "unknown", "best_date": None},
            internal_links=[{"url": "https://example.com/about/", "text": "About"}],
        )
    )
    assert result["type"] == "listing"
    assert result["confidence"] == "medium"


def test_listing_on_article_shaped_links_alone_still_classifies_as_listing():
    result = classify_page_type(
        _page(
            url="https://example.com/news/",
            h1_tags=["Latest news"],
            structured_data=[],
            freshness={"tier": "unknown", "best_date": None},
            internal_links=[
                {"url": f"https://example.com/2026/07/story-number-{i}/", "text": "s"}
                for i in range(14)
            ],
        )
    )
    assert result["type"] == "listing"
    assert result["confidence"] == "medium"


def test_navigation_links_are_not_article_shaped():
    """/about/, /tag/politics/ etc. must not push a page into listing."""
    result = classify_page_type(
        _page(
            url="https://example.com/help/",
            h1_tags=["Help"],
            structured_data=[],
            freshness={"tier": "unknown", "best_date": None},
            internal_links=[
                {"url": f"https://example.com/tag/topic{i}/", "text": "t"}
                for i in range(12)
            ]
            + [
                {"url": "https://example.com/about/", "text": "About"},
                {"url": "https://example.com/contact/", "text": "Contact"},
            ],
        )
    )
    assert result["type"] == "other"


def test_resolved_freshness_blocks_listing_classification():
    """A dated page is a content unit, not a navigation surface."""
    result = classify_page_type(
        _page(
            url="https://example.com/news/",
            h1_tags=[f"Headline {i}" for i in range(9)],
            structured_data=[],
            freshness={"tier": "fresh", "best_date": "2026-07-20"},
            internal_links=_numeric_links(20, host="https://example.com"),
        )
    )
    assert result["type"] != "listing"


# --------------------------------------------------------------------------
# 3. homepage wins over everything
# --------------------------------------------------------------------------


def test_root_path_is_homepage_even_with_listing_signals():
    result = classify_page_type(
        _page(
            url="https://www.zman.co.il/",
            h1_tags=[f"Headline {i}" for i in range(19)],
            structured_data=[{"@type": "WebSite"}],
            freshness={"tier": "unknown", "best_date": None},
            internal_links=_numeric_links(38),
        )
    )
    assert result["type"] == "homepage"


def test_empty_path_is_homepage():
    result = classify_page_type(_page(url="https://example.com", h1_tags=["Welcome"]))
    assert result["type"] == "homepage"


def test_homepage_wins_over_article_schema():
    result = classify_page_type(
        _page(
            url="https://example.com/",
            h1_tags=["Welcome"],
            structured_data=NEWSARTICLE_SCHEMA,
            freshness={"tier": "fresh", "best_date": "2026-07-29"},
        )
    )
    assert result["type"] == "homepage"


# --------------------------------------------------------------------------
# 4. about page — not a listing
# --------------------------------------------------------------------------


def test_about_page_is_other_not_listing():
    result = classify_page_type(
        _page(
            url="https://example.com/about/",
            h1_tags=["About us"],
            structured_data=[{"@type": "Organization", "name": "Example"}],
            freshness={"tier": "unknown", "best_date": None},
            internal_links=[
                {"url": "https://example.com/contact/", "text": "Contact"},
                {"url": "https://example.com/careers/", "text": "Careers"},
                {"url": "https://example.com/press/", "text": "Press"},
            ],
            word_count=420,
        )
    )
    assert result["type"] == "other"


# --------------------------------------------------------------------------
# 5. ambiguous — article schema but multiple h1s
# --------------------------------------------------------------------------


def test_article_schema_with_five_h1s_is_medium_confidence_article():
    result = classify_page_type(
        _page(
            url="https://example.com/2026/07/a-story/",
            h1_tags=[f"Heading {i}" for i in range(5)],
            structured_data=NEWSARTICLE_SCHEMA,
            freshness={"tier": "fresh", "best_date": "2026-07-29"},
        )
    )
    assert result["type"] == "article"
    assert result["confidence"] == "medium"


def test_article_schema_with_unknown_freshness_is_medium_confidence_article():
    result = classify_page_type(
        _page(
            url="https://example.com/2026/07/a-story/",
            h1_tags=["A story"],
            structured_data=NEWSARTICLE_SCHEMA,
            freshness={"tier": "unknown", "best_date": None},
        )
    )
    assert result["type"] == "article"
    assert result["confidence"] == "medium"
    assert any("freshness unresolved" in s for s in result["signals"])


# --------------------------------------------------------------------------
# 6. contract: shape of every result
# --------------------------------------------------------------------------


ALL_FIXTURES = [
    _page(
        url="https://www.zman.co.il/708066/",
        structured_data=NEWSARTICLE_SCHEMA,
        freshness={"tier": "fresh", "best_date": "2026-07-29"},
    ),
    _page(
        url="https://www.zman.co.il/democracy/",
        h1_tags=[f"H{i}" for i in range(19)],
        internal_links=_numeric_links(38),
    ),
    _page(url="https://example.com/"),
    _page(url="https://example.com/about/"),
    _page(url="https://example.com/x/", h1_tags=[], structured_data=None),
    _page(url="https://example.com/y/", internal_links=None, freshness=None),
]


def test_every_result_has_the_full_contract():
    for fixture in ALL_FIXTURES:
        result = classify_page_type(fixture)
        assert set(result) >= {"type", "confidence", "signals"}, result
        assert result["type"] in ("article", "listing", "homepage", "other"), result
        assert result["confidence"] in ("high", "medium", "low"), result
        assert isinstance(result["signals"], list)
        assert result["signals"], f"empty signals for {fixture['url']}"
        assert all(isinstance(s, str) and s for s in result["signals"])


def test_bare_string_internal_links_are_tolerated():
    result = classify_page_type(
        _page(
            url="https://example.com/news/",
            h1_tags=[f"H{i}" for i in range(6)],
            internal_links=[f"https://example.com/{700000 + i}/" for i in range(15)],
        )
    )
    assert result["type"] == "listing"
    assert result["confidence"] == "high"


def test_classification_does_not_mutate_input():
    fixture = _page(url="https://example.com/about/")
    before = dict(fixture)
    classify_page_type(fixture)
    assert fixture == before


def test_missing_keys_do_not_raise():
    result = classify_page_type({"url": "https://example.com/thing/"})
    assert result["type"] == "other"
    assert result["signals"]
