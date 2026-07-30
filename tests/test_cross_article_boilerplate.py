"""Boilerplate recurring across sampled articles is not journalism.

`boilerplate_ratio` only ever compared blocks *within* one page, so a
standing editor's note or membership pitch that appears once per article
was invisible to it by construction — it is not a duplicate on any single
page, only across the set.

v0.4.4 gave the audit a verified sample of child articles, which is
exactly the input this needs. Class-name heuristics (_CHROME_SELECTOR)
are brittle across sites; "this identical passage appears on every
article we sampled" is site-agnostic and near-impossible to trip
accidentally.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from citability_scorer import detect_cross_article_boilerplate  # noqa: E402


PITCH = (
    "עיתונות אמינה, מקצועית וליברלית היא יסוד הכרחי לחברה חופשית ובריאה. "
    "הצטרפו למעגל התומכים של זמן ישראל."
)
NOTE = "This article is part of our ongoing coverage of the 2026 election."


def _article(*texts):
    return [{"heading": "", "content": t} for t in texts]


class TestDetection:
    def test_passage_on_every_article_is_boilerplate(self):
        articles = [
            _article("Unique reporting about the northern border.", PITCH),
            _article("Unique reporting about the judicial committee.", PITCH),
            _article("Unique reporting about coalition arithmetic.", PITCH),
        ]
        found = detect_cross_article_boilerplate(articles)
        assert len(found) == 1
        assert PITCH in found

    def test_unique_prose_is_never_boilerplate(self):
        articles = [
            _article("Unique reporting about the northern border."),
            _article("Unique reporting about the judicial committee."),
            _article("Unique reporting about coalition arithmetic."),
        ]
        assert detect_cross_article_boilerplate(articles) == set()

    def test_near_identical_passages_still_count(self):
        """Publishers vary a word or a date in a standing note."""
        articles = [
            _article("Real reporting one.", NOTE),
            _article("Real reporting two.", NOTE.replace("2026", "2027")),
            _article("Real reporting three.", NOTE),
        ]
        assert len(detect_cross_article_boilerplate(articles)) >= 1

    def test_appearing_on_a_minority_of_articles_is_not_boilerplate(self):
        """A passage on 2 of 5 is a topic, not furniture."""
        articles = [
            _article("Reporting one.", NOTE),
            _article("Reporting two.", NOTE),
            _article("Reporting three."),
            _article("Reporting four."),
            _article("Reporting five."),
        ]
        assert detect_cross_article_boilerplate(articles) == set()

    def test_threshold_is_configurable(self):
        # NOTE is on 2 of 4 articles — exactly 0.5.
        articles = [
            _article("Reporting one.", NOTE),
            _article("Reporting two.", NOTE),
            _article("Reporting three."),
            _article("Reporting four."),
        ]
        assert detect_cross_article_boilerplate(articles, min_share=0.6) == set()
        assert NOTE in detect_cross_article_boilerplate(articles, min_share=0.5)


class TestGuards:
    def test_a_single_article_yields_nothing(self):
        """With one sample there is no such thing as 'recurring'.

        Returning its blocks as boilerplate would empty the only article
        we have.
        """
        assert detect_cross_article_boilerplate([_article("A.", PITCH)]) == set()

    def test_empty_input_is_safe(self):
        assert detect_cross_article_boilerplate([]) == set()

    def test_repetition_within_one_article_does_not_count(self):
        """Cross-article means across articles — an intra-page duplicate is
        boilerplate_ratio's job, and counting it here would let a single
        repetitive page define boilerplate for the whole sample."""
        articles = [
            _article(PITCH, PITCH, PITCH),
            _article("Unique reporting about the border."),
        ]
        assert detect_cross_article_boilerplate(articles) == set()
