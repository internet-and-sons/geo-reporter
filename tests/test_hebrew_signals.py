"""Negative-signal heuristics must work on Hebrew, not only English.

Most sites this tool audits are Hebrew or Hebrew+English, but every
heuristic in _compute_negative_signals was written against English
vocabulary:

- _BYLINE_PATTERNS matched "by Foo" / "written by" / "author:", so
  missing_author flagged TRUE on every Hebrew article ever scored —
  including articles carrying a Person node in their JSON-LD.
- _CHROME_TERMS matched "share" / "copy link" / "subscribe", so a share
  widget reading "העתק קישור · שיתוף במייל · שיתוף בפייסבוק" scored as
  editorial prose and dragged the article average down.

Measured on zman.co.il: a share block and a 73-word donation appeal on
every article, scoring 18-30, pulled the sampled mean from 58.8 (content
only) to 50.9 — an 8-point error on the heaviest-weighted category.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from bs4 import BeautifulSoup  # noqa: E402

from citability_scorer import (  # noqa: E402
    _compute_negative_signals,
    _strip_chrome_elements,
)


def _blocks(*texts):
    return [{"heading": "", "content": t} for t in texts]


# Verbatim from https://www.zman.co.il/708456/
ZMAN_SHARE = (
    "העתק קישור שיתוף במייל שיתוף בטוויטר שיתוף בפייסבוק שיתוף בווצאפ "
    "הדפסת כתבה לכל תגובה ופוסט עמוד בזמן ישראל שניתן לשתף ישירות "
    "ברשתות החברתיות ולשלוח באימייל"
)
ZMAN_DONATION = (
    "ועכשיו אנו זקוקים לתמיכה שלך. עזרו לנו להמשיך ליצור עיתונות אמינה, "
    "מקצועית וליברלית. הצטרפו למעגל התומכים של זמן ישראל ותוכלו ליהנות "
    "מתכנים בלעדיים ומחוויית גלישה נקייה מפרסומות."
)
HEBREW_PROSE = (
    "ועדת וינוגרד, שהוקמה בספטמבר 2006 לחקור את מלחמת לבנון השנייה, "
    "פרסמה את מסקנותיה בשנים 2007-2008 ומצאה ליקויים עמוקים בהיערכות "
    "המדינה כלפי תושבי הגבול הצפוני."
)


class TestHebrewByline:
    def test_hebrew_byline_in_body_is_recognised(self):
        blocks = _blocks("מאת טל שניידר. " + HEBREW_PROSE)
        signals = _compute_negative_signals(blocks)
        assert signals["missing_author"]["flagged"] is False

    def test_structured_data_author_beats_text_heuristics(self):
        """The zman case — byline is in JSON-LD, not in the body prose."""
        structured = [{
            "@type": "NewsArticle",
            "author": [{"@type": "Person", "name": "יורם כץ"}],
        }]
        signals = _compute_negative_signals(
            _blocks(HEBREW_PROSE), structured_data=structured)
        assert signals["missing_author"]["flagged"] is False, (
            "an explicit Person author node is the strongest byline "
            "signal there is"
        )

    def test_genuinely_anonymous_hebrew_page_still_flags(self):
        """Guard against the fix turning into a whitewash."""
        signals = _compute_negative_signals(_blocks(HEBREW_PROSE))
        assert signals["missing_author"]["flagged"] is True

    def test_empty_author_node_does_not_count_as_a_byline(self):
        structured = [{"@type": "NewsArticle", "author": {"@type": "Person"}}]
        signals = _compute_negative_signals(
            _blocks(HEBREW_PROSE), structured_data=structured)
        assert signals["missing_author"]["flagged"] is True

    def test_english_byline_still_works(self):
        signals = _compute_negative_signals(
            _blocks("by Tal Schneider. The committee reported in 2007."))
        assert signals["missing_author"]["flagged"] is False


class TestHebrewChrome:
    def test_share_widget_is_detected_despite_being_59_words(self):
        signals = _compute_negative_signals(
            _blocks(ZMAN_SHARE, HEBREW_PROSE))
        assert signals["cta_chrome_ratio"]["value"] == 0.5

    def test_donation_appeal_is_detected(self):
        signals = _compute_negative_signals(
            _blocks(ZMAN_DONATION, HEBREW_PROSE))
        assert signals["cta_chrome_ratio"]["value"] == 0.5

    def test_hebrew_prose_is_not_mistaken_for_chrome(self):
        signals = _compute_negative_signals(_blocks(HEBREW_PROSE))
        assert signals["cta_chrome_ratio"]["value"] == 0.0

    def test_a_single_incidental_term_in_long_prose_is_not_chrome(self):
        """'שיתוף' appears in ordinary political writing — one mention in a
        long passage must not condemn the block."""
        prose = HEBREW_PROSE + " הסכם שיתוף הפעולה בין המפלגות נחתם ב-2019."
        signals = _compute_negative_signals(_blocks(prose))
        assert signals["cta_chrome_ratio"]["value"] == 0.0

    def test_english_chrome_still_detected(self):
        signals = _compute_negative_signals(
            _blocks("Share on Twitter. Copy link. Subscribe to our newsletter.",
                    "The committee reported its findings in 2008."))
        assert signals["cta_chrome_ratio"]["value"] == 0.5


class TestChromeElementStripping:
    """Widgets must be removed at the DOM level, not by dropping blocks.

    The share bar on zman.co.il sits inside the article element, so its
    button labels were concatenated onto the front of the article body.
    Dropping the resulting block would have discarded 383 words of
    journalism along with 59 words of buttons.
    """

    def test_share_widget_is_removed_but_the_article_survives(self):
        html = (
            "<article>"
            '<ul class="social">העתק קישור שיתוף במייל שיתוף בפייסבוק</ul>'
            f"<p>{HEBREW_PROSE}</p>"
            "</article>"
        )
        soup = BeautifulSoup(html, "lxml")
        assert _strip_chrome_elements(soup) == 1
        text = soup.get_text(strip=True)
        assert "העתק קישור" not in text
        assert "ועדת וינוגרד" in text

    def test_state_class_on_body_does_not_nuke_the_page(self):
        """zman.co.il ships <body class="hide-bottom-bar-join">.

        That matched the widget pattern and decomposed the whole
        document, leaving nothing to score.
        """
        html = (
            '<body class="hide-bottom-bar-join">'
            f"<article><p>{HEBREW_PROSE}</p></article>"
            "</body>"
        )
        soup = BeautifulSoup(html, "lxml")
        _strip_chrome_elements(soup)
        assert "ועדת וינוגרד" in soup.get_text(strip=True)

    def test_structural_tag_is_spared_even_when_it_is_a_small_share(self):
        """Isolates the structural guard from the text-share guard.

        A teaser <article class="...promo..."> on a listing page holds
        only a slice of the page text, so the share guard would happily
        decompose it. Structural tags carry the content by definition and
        must be spared on name alone.
        """
        html = (
            "<div>"
            f"<div><p>{HEBREW_PROSE * 8}</p></div>"
            f'<article class="promo-teaser"><p>{HEBREW_PROSE}</p></article>'
            "</div>"
        )
        soup = BeautifulSoup(html, "lxml")
        teaser = soup.find("article")
        share = len(teaser.get_text(strip=True)) / len(soup.get_text(strip=True))
        assert share < 0.4, "precondition: the share guard must not cover this"
        assert _strip_chrome_elements(soup) == 0
        assert soup.find("article") is not None

    def test_a_node_holding_most_of_the_page_is_never_chrome(self):
        """Whatever it calls itself, the bulk of the text is the article."""
        html = (
            "<div>"
            f'<div class="promo-wrapper"><p>{HEBREW_PROSE * 6}</p></div>'
            "<p>קצר</p>"
            "</div>"
        )
        soup = BeautifulSoup(html, "lxml")
        assert _strip_chrome_elements(soup) == 0
        assert "ועדת וינוגרד" in soup.get_text(strip=True)

    def test_support_bar_and_modal_are_removed(self):
        html = (
            "<div>"
            f"<article><p>{HEBREW_PROSE * 4}</p></article>"
            '<div class="bottom-bar-join-container"><p>עיתונות אמינה</p></div>'
            '<div class="popup-content"><p>לכל תגובה ופוסט</p></div>'
            "</div>"
        )
        soup = BeautifulSoup(html, "lxml")
        assert _strip_chrome_elements(soup) == 2
        text = soup.get_text(strip=True)
        assert "עיתונות אמינה" not in text
        assert "לכל תגובה" not in text
        assert "ועדת וינוגרד" in text
