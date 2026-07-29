"""Tests for informational (non-scoring) negative signals in the citability
scorer.

These signals are a diagnostic overlay attached to the page-level result under
``negative_signals``. They must NEVER move ``total_score``, grade cuts,
``average_citability_score`` or ``grade_distribution`` — that determinism is
guarded by tests/test_score_fields.py and tests/test_citability_scorer.py,
which stay byte-for-byte untouched. This file only asserts the new field.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from citability_scorer import analyze_page_citability  # noqa: E402


def _resp(status=200, text=""):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.raise_for_status = MagicMock()
    return mock


def _analyze(html):
    with patch("citability_scorer.requests.get", return_value=_resp(200, html)):
        return analyze_page_citability("https://example.com")


# --- Fixtures ---------------------------------------------------------------

# Clean article: byline present, varied vocabulary, long prose paragraphs
# (> 40 words so no chrome gate), no duplicates.
CLEAN_HTML = """
<html><body>
<h1>Understanding Customer Retention</h1>
<p>By Jane Smith, published on Tuesday. Retention describes whether people
continue paying for a subscription over successive billing periods, and it
reflects genuine satisfaction across the entire lifecycle from onboarding
through renewal decisions made months later by finance teams.</p>
<h2>Why Onboarding Matters</h2>
<p>Early guidance reduces confusion during the first sessions, when new
members explore dashboards, connect integrations, and configure alerts.
Thoughtful walkthroughs shorten the path toward habitual weekly usage and
measurably improve downstream loyalty among cohorts observed quarterly.</p>
<h2>Measuring Progress Fairly</h2>
<p>Analysts compare cohorts against baselines, adjusting expectations for
seasonality, promotional discounts, and pricing experiments. Honest reporting
acknowledges variance instead of celebrating noise, which keeps stakeholders
aligned around durable trends rather than transient spikes appearing weekly.</p>
</body></html>
"""

# Keyword-stuffed body: one token dominates well beyond 6%.
STUFFED_HTML = """
<html><body>
<h1>Widget Guide</h1>
<p>Widget widget widget really matters because widget shoppers compare widget
listings before widget checkout, and widget reviews mention widget durability
plus widget pricing whenever widget buyers evaluate widget alternatives online
today near widget season.</p>
</body></html>
"""

# Mostly CTA / share / subscribe chrome blocks.
CHROME_HTML = """
<html><body>
<h1>News Story</h1>
<p>Share this article now please everyone. Subscribe to our newsletter today.
Sign up and log in now. Copy link, print, and follow us always.</p>
<h2>More options</h2>
<p>Please subscribe and share again. Follow us on every network. Sign up for
the newsletter. Copy link, print this, log in now.</p>
<h2>The actual story</h2>
<p>Regulators approved the merger after reviewing competitive concerns raised
by smaller rivals during a lengthy consultation that examined pricing power,
data portability, and long term consumer welfare across regional markets.</p>
</body></html>
"""

# A repeated boilerplate paragraph appearing under two headings.
BOILERPLATE_BLOCK = (
    "This proprietary content is protected under international copyright law "
    "and may not be reproduced, redistributed, or transmitted without prior "
    "written permission from the publisher and its licensing partners."
)
BOILERPLATE_HTML = f"""
<html><body>
<h1>Report</h1>
<p>{BOILERPLATE_BLOCK}</p>
<h2>Section Two</h2>
<p>{BOILERPLATE_BLOCK}</p>
<h2>Original Analysis</h2>
<p>Independent modelling suggests demand will soften modestly next quarter as
interest rates plateau, with regional variation driven by employment trends,
housing affordability, and shifting consumer confidence across metropolitan
areas surveyed recently.</p>
</body></html>
"""

# Same clean prose but WITHOUT any byline.
NO_BYLINE_HTML = """
<html><body>
<h1>Understanding Customer Retention</h1>
<p>Retention describes whether people continue paying for a subscription over
successive billing periods, reflecting genuine satisfaction across the entire
lifecycle from onboarding through renewal decisions made months later by the
finance teams involved.</p>
<h2>Measuring Progress</h2>
<p>Analysts compare cohorts against baselines, adjusting expectations for
seasonality, promotional discounts, and pricing experiments while reporting
variance honestly so stakeholders stay aligned around durable trends rather
than transient noise.</p>
</body></html>
"""

EMPTY_HTML = "<html><body><p>Too short.</p></body></html>"


# --- Shape --------------------------------------------------------------------

def _assert_shape(neg):
    assert set(neg.keys()) == {
        "keyword_stuffing", "cta_chrome_ratio", "boilerplate_ratio",
        "missing_author",
    }
    for key, sig in neg.items():
        assert set(sig.keys()) == {"value", "flagged", "note"}, key
        assert isinstance(sig["flagged"], bool), key
        assert isinstance(sig["note"], str) and sig["note"], key


def test_negative_signals_always_present_and_shaped():
    result = _analyze(CLEAN_HTML)
    assert "negative_signals" in result
    _assert_shape(result["negative_signals"])


def test_negative_signals_do_not_disturb_existing_fields():
    result = _analyze(CLEAN_HTML)
    # The core scoring outputs still exist and negative_signals is purely additive.
    for field in (
        "average_citability_score", "grade_distribution", "total_blocks_analyzed",
        "top_5_citable", "bottom_5_citable", "all_blocks",
    ):
        assert field in result


# --- Clean article: nothing flagged ------------------------------------------

def test_clean_article_flags_nothing():
    neg = _analyze(CLEAN_HTML)["negative_signals"]
    assert neg["keyword_stuffing"]["flagged"] is False
    assert neg["cta_chrome_ratio"]["flagged"] is False
    assert neg["boilerplate_ratio"]["flagged"] is False
    assert neg["missing_author"]["flagged"] is False
    assert neg["missing_author"]["value"] is False


# --- Keyword stuffing --------------------------------------------------------

def test_keyword_stuffing_flagged():
    neg = _analyze(STUFFED_HTML)["negative_signals"]
    assert neg["keyword_stuffing"]["value"] > 0.06
    assert neg["keyword_stuffing"]["flagged"] is True
    assert "Princeton KDD-2024" in neg["keyword_stuffing"]["note"]


# --- CTA / chrome ------------------------------------------------------------

def test_cta_chrome_ratio_flagged():
    neg = _analyze(CHROME_HTML)["negative_signals"]
    assert neg["cta_chrome_ratio"]["value"] > 0.30
    assert neg["cta_chrome_ratio"]["flagged"] is True


# --- Boilerplate -------------------------------------------------------------

def test_boilerplate_ratio_flagged():
    neg = _analyze(BOILERPLATE_HTML)["negative_signals"]
    assert neg["boilerplate_ratio"]["value"] > 0.25
    assert neg["boilerplate_ratio"]["flagged"] is True


# --- Missing author ----------------------------------------------------------

def test_missing_author_flagged_when_no_byline():
    neg = _analyze(NO_BYLINE_HTML)["negative_signals"]
    assert neg["missing_author"]["value"] is True
    assert neg["missing_author"]["flagged"] is True
    assert "Person schema" in neg["missing_author"]["note"]


def test_missing_author_false_with_byline():
    neg = _analyze(CLEAN_HTML)["negative_signals"]
    assert neg["missing_author"]["value"] is False
    assert neg["missing_author"]["flagged"] is False


# --- Empty page --------------------------------------------------------------

def test_empty_page_yields_zeroed_signals():
    result = _analyze(EMPTY_HTML)
    assert result["total_blocks_analyzed"] == 0
    neg = result["negative_signals"]
    _assert_shape(neg)
    assert neg["keyword_stuffing"]["value"] == 0.0
    assert neg["cta_chrome_ratio"]["value"] == 0.0
    assert neg["boilerplate_ratio"]["value"] == 0.0
    assert neg["missing_author"]["value"] is False
    for sig in neg.values():
        assert sig["flagged"] is False
        assert sig["note"] == "insufficient content to assess"
