"""
Tests for the structured TL;DR block on the PDF cover (v0.4.3).

Since v0.4.0 the report contract requires `executive_summary` to carry a TL;DR:
a bold score line, a one-sentence posture, and three numbered actions tagged
with impact / effort / owner. Rendering that as one flat Paragraph flattens all
the structure into an unreadable prose blob, so `render_tldr_flowables()` splits
it into separate flowables.

Pre-v0.4.0 audit JSON carries plain prose in the same field; that must keep
rendering exactly as it did before (a single Paragraph).
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from reportlab.platypus import Paragraph  # noqa: E402

from generate_pdf_report import build_styles, render_tldr_flowables  # noqa: E402


STRUCTURED = (
    "**GEO Score: 58/100 — Moderate**\n"
    "The site is reachable by every live-retrieval crawler but publishes no "
    "structured data, so AI engines can read it and still fail to attribute it.\n"
    "1. Publish Organization schema with sameAs — Impact: High | Effort: Low | Owner: Dev\n"
    "2. Add author bylines and last-updated dates — Impact: High | Effort: Medium | Owner: Content\n"
    "3. Create llms.txt pointing at the 12 money pages — Impact: Medium | Effort: Low | Owner: Dev\n"
)

UNSTRUCTURED = (
    "This report presents the findings of a comprehensive GEO audit conducted on "
    "Example Company. The site achieved an overall GEO Readiness Score of 58/100, "
    "placing it in the Moderate tier. Implementing schema markup, allowing AI "
    "crawlers, and optimizing content structure could raise the score to roughly "
    "78/100 within 90 days."
)


@pytest.fixture
def styles():
    return build_styles()


def _texts(flowables):
    return [f.text for f in flowables if isinstance(f, Paragraph)]


# ------------------------------------------------------------------
# Empty / missing input
# ------------------------------------------------------------------

@pytest.mark.parametrize("value", ["", "   \n  ", None])
def test_empty_summary_returns_empty_list(value, styles):
    assert render_tldr_flowables(value, styles) == []


# ------------------------------------------------------------------
# Unstructured prose — backwards compatibility
# ------------------------------------------------------------------

def test_unstructured_returns_exactly_one_paragraph(styles):
    out = render_tldr_flowables(UNSTRUCTURED, styles)
    assert len(out) == 1
    assert isinstance(out[0], Paragraph)


def test_unstructured_text_is_passed_through_unchanged(styles):
    out = render_tldr_flowables(UNSTRUCTURED, styles)
    assert out[0].text == UNSTRUCTURED


def test_unstructured_uses_the_original_body_style(styles):
    out = render_tldr_flowables(UNSTRUCTURED, styles)
    assert out[0].style.name == styles["BodyText_Custom"].name


# ------------------------------------------------------------------
# Structured TL;DR
# ------------------------------------------------------------------

def test_structured_returns_multiple_flowables(styles):
    out = render_tldr_flowables(STRUCTURED, styles)
    # lead + posture + 3 actions
    assert len(out) >= 5


def test_bold_span_becomes_reportlab_inline_markup(styles):
    lead = _texts(render_tldr_flowables(STRUCTURED, styles))[0]
    assert "<b>GEO Score: 58/100 — Moderate</b>" in lead
    assert "**" not in lead


def test_posture_sentence_is_its_own_flowable(styles):
    texts = _texts(render_tldr_flowables(STRUCTURED, styles))
    posture = [t for t in texts if t.startswith("The site is reachable")]
    assert len(posture) == 1
    # the posture must not have been glued onto the score line
    assert "GEO Score" not in posture[0]


def test_each_numbered_action_is_its_own_paragraph(styles):
    texts = _texts(render_tldr_flowables(STRUCTURED, styles))
    actions = [t for t in texts if t.lstrip().startswith(("1.", "2.", "3."))]
    assert len(actions) == 3
    assert "Organization schema" in actions[0]
    assert "author bylines" in actions[1]
    assert "llms.txt" in actions[2]


def test_numbered_actions_are_indented(styles):
    out = render_tldr_flowables(STRUCTURED, styles)
    actions = [f for f in out
               if isinstance(f, Paragraph) and f.text.lstrip().startswith(("1.", "2.", "3."))]
    assert actions, "expected numbered action paragraphs"
    for para in actions:
        assert para.style.leftIndent > 0


def test_numbered_list_without_bold_is_still_structured(styles):
    text = "1. Fix robots.txt\n2. Add schema\n3. Ship llms.txt"
    out = render_tldr_flowables(text, styles)
    assert len(out) == 3


def test_bold_only_summary_is_structured(styles):
    text = "**GEO Score: 71/100 — Good**\nThe site is broadly AI-legible."
    out = render_tldr_flowables(text, styles)
    assert len(out) == 2
    assert "<b>GEO Score: 71/100 — Good</b>" in out[0].text


# ------------------------------------------------------------------
# Escaping — client text must not break the ReportLab parser
# ------------------------------------------------------------------

def test_ampersand_and_angle_brackets_are_escaped_before_markup(styles):
    text = (
        "**Score: 44/100 — Smith & Sons <Holdings>**\n"
        "1. Fix robots.txt for Bloom & Co — Impact: High | Effort: Low | Owner: Dev"
    )
    texts = _texts(render_tldr_flowables(text, styles))
    joined = "\n".join(texts)
    assert "&amp;" in joined
    assert "&lt;Holdings&gt;" in joined
    # the bold markup we inserted must survive escaping
    assert "<b>Score: 44/100 — Smith &amp; Sons &lt;Holdings&gt;</b>" in texts[0]
    # ...and no raw, unescaped ampersand is left behind
    assert " & " not in joined


def test_structured_flowables_actually_render(styles):
    """A Paragraph parses its markup lazily on wrap(); bad markup raises there."""
    text = (
        "**Score: 44/100 — Smith & Sons**\n"
        "Entity coverage is thin & inconsistent.\n"
        "1. Fix <robots.txt> — Impact: High | Effort: Low | Owner: Dev"
    )
    for flowable in render_tldr_flowables(text, styles):
        flowable.wrap(400, 800)
