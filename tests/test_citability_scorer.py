"""
Tests for the bilingual (English + Hebrew) citability scorer.

The scorer language-detects each passage and routes Hebrew to a Hebrew-tuned
engine, while all other content keeps using the original English logic. These
tests lock in:

  - English behaviour is unchanged (routing + the five scoring dimensions).
  - Hebrew passages route to the Hebrew engine and earn credit for the signals
    the English engine cannot see (gazetteer named entities, Hebrew source /
    definition / uniqueness cues, ₪ / ש"ח currency, אחוז percentages, and the
    recalibrated 90-120 word optimal length band).
  - Page-level analysis reports a language_distribution.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from citability_scorer import (  # noqa: E402
    detect_language,
    normalise_hebrew,
    score_passage,
    analyze_page_citability,
    _he_named_entities,
)


def _resp(status=200, text=""):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.raise_for_status = MagicMock()
    return mock


# A rich Hebrew passage that exercises every Hebrew dimension: definition cue
# (מהווה), source cues (לפי / מסר), named entities (בג"ץ, ח"כ, השר), a percentage
# via אחוז, currency, first-hand research (מצאנו), and a question heading.
HE_RICH = (
    'אבטלה מבנית מהווה מצב שבו עובדים מתקשים למצוא עבודה. לפי נתוני הלמ"ס, '
    'שיעור האבטלה עמד על 4 אחוז בשנת 2024. ח"כ פלוני מסר כי בג"ץ דן בעתירה '
    'בנושא, והשר אלמוני הגיב. מצאנו כי כ-12 אלף משתמשים הושפעו, בעלות של '
    '500 ש"ח לאדם.'
)

EN_RICH = (
    "Customer churn is a metric that measures how many users leave a service. "
    "According to Gartner, 23% of SaaS companies lose 5,000 customers per year. "
    "We found that retention improves with onboarding, for example a guided tour."
)


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

def test_detect_language_english():
    assert detect_language("This is a plain English sentence.") == "en"


def test_detect_language_hebrew():
    assert detect_language("זהו משפט פשוט בעברית לבדיקה.") == "he"


def test_detect_language_empty_defaults_to_english():
    assert detect_language("") == "en"
    assert detect_language("12345 !!! ???") == "en"


def test_detect_language_mixed_below_threshold_is_english():
    """Hebrew prose with a few brand tokens stays Hebrew; mostly-Latin is English."""
    mostly_latin = "The company OpenAI launched a tool. בינה"
    assert detect_language(mostly_latin) == "en"


# ---------------------------------------------------------------------------
# Hebrew normalisation helper
# ---------------------------------------------------------------------------

def test_normalise_hebrew_strips_niqqud_and_normalises_quotes():
    # שָׁלוֹם carries niqqud; ״ and ׳ are gershayim/geresh.
    out = normalise_hebrew("שָׁלוֹם ״טקסט״ ׳")
    assert "ְ" not in out and "ֹ" not in out  # niqqud removed
    assert "״" not in out and "׳" not in out  # gershayim/geresh normalised
    assert '"' in out and "'" in out


# ---------------------------------------------------------------------------
# English routing & behaviour (must stay unchanged)
# ---------------------------------------------------------------------------

def test_english_passage_routes_to_english_engine():
    result = score_passage(EN_RICH, "What is churn?")
    assert result["language"] == "en"


def test_english_result_has_all_fields():
    result = score_passage(EN_RICH, "What is churn?")
    for key in ("language", "heading", "word_count", "total_score",
                "grade", "label", "breakdown", "preview"):
        assert key in result
    assert result["heading"] == "What is churn?"
    assert set(result["breakdown"]) == {
        "answer_block_quality", "self_containment", "structural_readability",
        "statistical_density", "uniqueness_signals",
    }


def test_english_dimensions_credited():
    """English engine still credits its native signals."""
    r = score_passage(EN_RICH, "What is churn?")
    b = r["breakdown"]
    assert b["answer_block_quality"] > 0   # "is a" definition + "according to"
    assert b["statistical_density"] > 0    # 23% and $-style numbers
    assert b["uniqueness_signals"] > 0     # "we found" / "for example"
    assert 0 <= r["total_score"] <= 100


def test_english_named_entities_credited_via_capitalisation():
    """Proper-noun heuristic still fires on English capitalised names."""
    r = score_passage(
        "Gartner and Forrester both published reports. Microsoft and Google agreed.",
    )
    assert r["language"] == "en"
    assert r["breakdown"]["self_containment"] > 0


# ---------------------------------------------------------------------------
# Hebrew routing & behaviour
# ---------------------------------------------------------------------------

def test_hebrew_passage_routes_to_hebrew_engine():
    r = score_passage(HE_RICH, "מהי אבטלה מבנית?")
    assert r["language"] == "he"
    assert r["heading"] == "מהי אבטלה מבנית?"


def test_hebrew_named_entity_detection():
    """Gazetteer NER counts titles, gershayim acronyms, and quoted names."""
    text = 'בג"ץ דן בעתירה. ח"כ פלוני הגיב. השר אלמוני נכח בדיון.'
    assert _he_named_entities(text) >= 3


def test_hebrew_entities_credited_in_self_containment():
    """Entity-rich Hebrew scores self-containment above entity-free Hebrew."""
    rich = score_passage('בג"ץ, ח"כ פלוני והשר אלמוני נכחו בדיון החשוב.')
    bare = score_passage("הדיון היה חשוב מאוד והנושא עלה שוב ושוב בישיבה.")
    assert rich["language"] == bare["language"] == "he"
    assert rich["breakdown"]["self_containment"] > bare["breakdown"]["self_containment"]


def test_hebrew_definition_and_source_cues_credited():
    r = score_passage(HE_RICH, "מהי אבטלה מבנית?")
    # מהווה (definition) + early-answer + question heading + לפי/מסר (source)
    assert r["breakdown"]["answer_block_quality"] > 0


def test_hebrew_statistical_density_credits_percent_and_currency():
    """אחוז percentages and ₪ / ש"ח currency feed statistical density."""
    pct = score_passage("שיעור ההצלחה עמד על 80 אחוז במהלך השנה האחרונה כולה.")
    money = score_passage('המחיר היה 500 ש"ח ועלה ל-₪ 700 תוך חודש ימים בלבד.')
    assert pct["breakdown"]["statistical_density"] > 0
    assert money["breakdown"]["statistical_density"] > 0


def test_hebrew_uniqueness_first_hand_research_credited():
    r = score_passage("מצאנו כי התופעה נפוצה. ניתחנו את הנתונים וגילינו דפוס ברור.")
    assert r["language"] == "he"
    assert r["breakdown"]["uniqueness_signals"] >= 5  # research cue worth 5


def test_hebrew_question_heading_bonus_via_question_word():
    """A Hebrew heading opening with a question word earns the heading bonus."""
    with_q = score_passage(HE_RICH, "כיצד נמדדת אבטלה?")
    without_q = score_passage(HE_RICH, "אבטלה")
    assert with_q["breakdown"]["answer_block_quality"] >= without_q["breakdown"]["answer_block_quality"]


def test_hebrew_optimal_length_band():
    """A ~100-word Hebrew passage lands in the 90-120 optimal band (top length credit)."""
    long_passage = " ".join(["מילה"] * 100)
    r = score_passage(long_passage)
    assert r["language"] == "he"
    assert r["word_count"] == 100
    # 10 points is the max length credit; entity/pronoun bonuses may add more,
    # so assert self_containment cleared the optimal-band threshold.
    assert r["breakdown"]["self_containment"] >= 10


def test_hebrew_rich_passage_grades_well():
    r = score_passage(HE_RICH, "מהי אבטלה מבנית?")
    assert r["total_score"] >= 50  # at least Moderate Citability
    assert r["grade"] in {"A", "B", "C"}


# ---------------------------------------------------------------------------
# Page-level analysis
# ---------------------------------------------------------------------------

_HE_HTML = """
<html><body>
<h2>מהי אבטלה מבנית?</h2>
<p>אבטלה מבנית מהווה מצב שבו עובדים מתקשים למצוא עבודה ההולמת את כישוריהם.
לפי נתוני הלמ"ס שיעור האבטלה עמד על 4 אחוז בשנת 2024 ובג"ץ דן בעתירה בנושא.
מצאנו כי כ-12 אלף משתמשים הושפעו מן השינוי הזה במהלך התקופה הנבדקת.</p>
<h2>About inflation</h2>
<p>Inflation is a sustained rise in prices. According to the central bank,
prices rose 3% in 2024. We found that wages lagged behind consumer costs.</p>
</body></html>
"""


def test_page_analysis_reports_language_distribution():
    with patch("citability_scorer.requests.get", return_value=_resp(200, _HE_HTML)):
        result = analyze_page_citability("https://example.com")
    assert "language_distribution" in result
    dist = result["language_distribution"]
    assert dist["he"] >= 1  # the Hebrew block
    assert dist["en"] >= 1  # the English block
    assert result["total_blocks_analyzed"] == dist["he"] + dist["en"]


def test_page_analysis_handles_fetch_error():
    with patch("citability_scorer.requests.get", side_effect=Exception("boom")):
        result = analyze_page_citability("https://example.com")
    assert "error" in result
