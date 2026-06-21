#!/usr/bin/env python3
"""
Citability Scorer (bilingual: English + Hebrew) — Analyzes content blocks for
AI citation readiness. Scores passages 0-100 based on how likely AI models are
to cite them.

Language dispatch:
  - Each passage is language-detected by Hebrew-character density.
  - Hebrew passages are scored with Hebrew-tuned patterns, gazetteer-based
    named-entity detection, and a recalibrated length band.
  - Everything else is scored with the ORIGINAL English logic, unchanged, so
    English behaviour is byte-for-byte identical to the upstream scorer.

The scoring dimensions, weights, and 0-100 grade bands are identical across
languages; only the pattern dictionaries, the named-entity detector, and the
optimal-length window differ. That keeps cross-language scores comparable.
"""

import sys
import json
import re
from typing import Optional

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Language detection + Hebrew normalisation
# ---------------------------------------------------------------------------

HEBREW_BLOCK = re.compile(r"[֐-׿]")
HEBREW_NIQQUD = re.compile(r"[֑-ׇ]")


def detect_language(text: str) -> str:
    """Return 'he' if the passage is predominantly Hebrew, else 'en'.

    We look at the ratio of Hebrew letters to all *alphabetic* characters
    (Hebrew + Latin). News pages often carry English names, URLs, and brand
    tokens inside Hebrew prose, so a simple "any Hebrew?" test over-triggers.
    A 30% Hebrew-letter share among letters is a robust threshold.
    """
    hebrew = len(HEBREW_BLOCK.findall(text))
    latin = len(re.findall(r"[A-Za-z]", text))
    total = hebrew + latin
    if total == 0:
        return "en"
    return "he" if (hebrew / total) >= 0.30 else "en"


def normalise_hebrew(text: str) -> str:
    """Strip niqqud and normalise gershayim/geresh so patterns match reliably."""
    text = HEBREW_NIQQUD.sub("", text)
    text = text.replace("״", '"').replace("׳", "'")  # ״ ׳ -> " '
    text = text.replace("“", '"').replace("”", '"')
    return text


# ===========================================================================
# ENGLISH SCORER — verbatim from the original plugin (do not modify)
# ===========================================================================

def _score_passage_en(text: str, heading: Optional[str] = None) -> dict:
    """Score a single passage for AI citability (0-100) — English."""
    words = text.split()
    word_count = len(words)

    scores = {
        "answer_block_quality": 0,
        "self_containment": 0,
        "structural_readability": 0,
        "statistical_density": 0,
        "uniqueness_signals": 0,
    }

    # === 1. Answer Block Quality (30%) ===
    abq_score = 0
    definition_patterns = [
        r"\b\w+\s+is\s+(?:a|an|the)\s",
        r"\b\w+\s+refers?\s+to\s",
        r"\b\w+\s+means?\s",
        r"\b\w+\s+(?:can be |are )?defined\s+as\s",
        r"\bin\s+(?:simple|other)\s+(?:terms|words)\s*,",
    ]
    for pattern in definition_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            abq_score += 15
            break

    first_60_words = " ".join(words[:60])
    if any(
        re.search(p, first_60_words, re.IGNORECASE)
        for p in [
            r"\b(?:is|are|was|were|means?|refers?)\b",
            r"\d+%",
            r"\$[\d,]+",
            r"\d+\s+(?:million|billion|thousand)",
        ]
    ):
        abq_score += 15

    if heading and heading.endswith("?"):
        abq_score += 10

    sentences = re.split(r"[.!?]+", text)
    short_clear_sentences = sum(1 for s in sentences if 5 <= len(s.split()) <= 25)
    if sentences:
        clarity_ratio = short_clear_sentences / len(sentences)
        abq_score += int(clarity_ratio * 10)

    if re.search(
        r"(?:according to|research shows|studies? (?:show|indicate|suggest|found)|data (?:shows|indicates|suggests))",
        text,
        re.IGNORECASE,
    ):
        abq_score += 10

    scores["answer_block_quality"] = min(abq_score, 30)

    # === 2. Self-Containment (25%) ===
    sc_score = 0
    if 134 <= word_count <= 167:
        sc_score += 10
    elif 100 <= word_count <= 200:
        sc_score += 7
    elif 80 <= word_count <= 250:
        sc_score += 4
    elif word_count < 30 or word_count > 400:
        sc_score += 0
    else:
        sc_score += 2

    pronoun_count = len(
        re.findall(
            r"\b(?:it|they|them|their|this|that|these|those|he|she|his|her)\b",
            text,
            re.IGNORECASE,
        )
    )
    if word_count > 0:
        pronoun_ratio = pronoun_count / word_count
        if pronoun_ratio < 0.02:
            sc_score += 8
        elif pronoun_ratio < 0.04:
            sc_score += 5
        elif pronoun_ratio < 0.06:
            sc_score += 3

    proper_nouns = len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b", text))
    if proper_nouns >= 3:
        sc_score += 7
    elif proper_nouns >= 1:
        sc_score += 4

    scores["self_containment"] = min(sc_score, 25)

    # === 3. Structural Readability (20%) ===
    sr_score = 0
    if sentences:
        avg_sentence_length = word_count / len(sentences)
        if 10 <= avg_sentence_length <= 20:
            sr_score += 8
        elif 8 <= avg_sentence_length <= 25:
            sr_score += 5
        else:
            sr_score += 2

    if re.search(r"(?:first|second|third|finally|additionally|moreover|furthermore)", text, re.IGNORECASE):
        sr_score += 4
    if re.search(r"(?:\d+[\.\)]\s|\b(?:step|tip|point)\s+\d+)", text, re.IGNORECASE):
        sr_score += 4
    if "\n" in text:
        sr_score += 4
    scores["structural_readability"] = min(sr_score, 20)

    # === 4. Statistical Density (15%) ===
    sd_score = 0
    pct_count = len(re.findall(r"\d+(?:\.\d+)?%", text))
    sd_score += min(pct_count * 3, 6)
    dollar_count = len(re.findall(r"\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|M|B|K))?", text))
    sd_score += min(dollar_count * 3, 5)
    number_count = len(re.findall(r"\b\d+(?:,\d{3})*(?:\.\d+)?\s+(?:users|customers|pages|sites|companies|businesses|people|percent|times|x\b)", text, re.IGNORECASE))
    sd_score += min(number_count * 2, 4)
    year_count = len(re.findall(r"\b20(?:2[3-6]|1\d)\b", text))
    if year_count > 0:
        sd_score += 2
    source_patterns = [
        r"(?:according to|per|from|by)\s+[A-Z]",
        r"(?:Gartner|Forrester|McKinsey|Harvard|Stanford|MIT|Google|Microsoft|OpenAI|Anthropic)",
        r"\([A-Z][a-z]+(?:\s+\d{4})?\)",
    ]
    for pattern in source_patterns:
        if re.search(pattern, text):
            sd_score += 2
    scores["statistical_density"] = min(sd_score, 15)

    # === 5. Uniqueness Signals (10%) ===
    us_score = 0
    if re.search(
        r"(?:our (?:research|study|data|analysis|survey|findings)|we (?:found|discovered|analyzed|surveyed|measured))",
        text,
        re.IGNORECASE,
    ):
        us_score += 5
    if re.search(r"(?:case study|for example|for instance|in practice|real-world|hands-on)", text, re.IGNORECASE):
        us_score += 3
    if re.search(r"(?:using|with|via|through)\s+[A-Z][a-z]+", text):
        us_score += 2
    scores["uniqueness_signals"] = min(us_score, 10)

    return _finalise(text, words, word_count, scores, "en")


# ===========================================================================
# HEBREW SCORER — adapted patterns, gazetteer NER, recalibrated length band
# ===========================================================================

# Titles/honorifics that reliably precede a named person/entity in Hebrew.
HE_TITLES = [
    r'ד"ר', r"פרופ'", r'עו"ד', r'ח"כ', r'רו"ח', r'רס"ן', r'סא"ל', r'אל"מ',
    "השר", "השרה", "ראש הממשלה", "רה\"מ", "השופט", "השופטת", "הנשיא", "הנשיאה",
    "הרב", "הרבה", "מר", "גב'", "השגריר", "השגרירה", "המנכ\"ל", "המנכ\"לית",
    "היועץ המשפטי", "היועצת המשפטית", "ראש העיר", "ראש האופוזיציה", "אלוף",
    "תא\"ל", "האלוף", "מפכ\"ל", "המפכ\"ל", "פרקליט", "הפרקליט", "ראש המוסד",
]
# Hebrew acronyms written with gershayim between letters: בג"ץ, צה"ל, ש"ח, ח"כ...
HE_ACRONYM = re.compile(r'[א-ת]{1,4}"[א-ת]')
# Quoted spans (names of outlets/works often appear in gershayim quotes).
HE_QUOTED = re.compile(r'"[^"]{2,40}"')

HE_PRONOUNS = re.compile(
    r"(?:^|\s)(?:הוא|היא|הם|הן|זה|זו|זאת|אלה|אלו|הללו|שלו|שלה|שלהם|שלהן|"
    r"אותו|אותה|אותם|אותן|עליו|עליה|עליהם|בו|בה|בהם)(?=\s|$|[.,;:])"
)

HE_DEFINITION = [
    r"\bמהווה\b", r"\bנחשב(?:ת|ים|ות)?\s+ל", r"\bמוגדר(?:ת|ים|ות)?\s+כ",
    r"\bפירוש(?:ו|ה)\b", r"\bמשמעות(?:ו|ה)\b", r"\bכלומר\b",
    r"\bבמילים אחרות\b", r"\bהיינו\b", r"ה(?:וא|יא)\s+\S+",  # הוא/היא + word (copula)
    r"\s[—\-]\s",  # em-dash / hyphen definition ( X — Y )
]
HE_EARLY_ANSWER = [
    r"\b(?:הוא|היא|היה|הייתה|הינו|הינה|מהווה|נחשב)\b",
    r"\d+%", r"\b\d+\s*אחוז", r"[₪]\s*[\d,]+", r"[\d,]+\s*ש\"ח",
    r"\d+\s*(?:מיליון|מיליארד|אלף)",
]
HE_QUESTION_WORDS = re.compile(r"^\s*(?:האם|מדוע|כיצד|מה |מי |למה|איך|מתי|היכן|לאן|כמה)")
HE_SOURCES = [
    r"(?:לפי|על[\- ]פי|לדברי|כפי ש|נמסר|דיווח(?:ה|ו)?|מסר(?:ה|ו)?|לפי נתוני|לפי דו\"ח)",
    r"(?:הלמ\"ס|בנק ישראל|בג\"ץ|הכנסת|מבקר המדינה|הפרקליטות|משטרת ישראל|"
    r"בית המשפט|המכון הישראלי|אוניברסיטת)",
    r"\([א-ת][^)]{0,30}\d{4}\)",  # (source 2024)
]
HE_TRANSITIONS = re.compile(
    r"(?:ראשית|שנית|שלישית|לבסוף|בנוסף|כמו כן|יתרה מכך|זאת ועוד|לסיכום|"
    r"מצד אחד|מצד שני|לעומת זאת|בהמשך)"
)
HE_LIST = re.compile(r"(?:\d+[\.\)]\s|\b(?:שלב|טיפ|נקודה|סעיף)\s+\d+)")
HE_UNIQUE_RESEARCH = re.compile(
    r"(?:המחקר שלנו|הסקר שלנו|הניתוח שלנו|הנתונים שלנו|מצאנו|גילינו|"
    r"ניתחנו|בדקנו|סקרנו|מדדנו|חשפנו)"
)
HE_UNIQUE_EXAMPLE = re.compile(r"(?:מקרה בוחן|לדוגמה|למשל|הלכה למעשה|בפועל|דוגמה לכך)")
HE_NUM_CONTEXT = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s*(?:משתמשים|לקוחות|אנשים|תושבים|חברות|עסקים|"
    r"שקל|שקלים|פעמים|מקרים|ימים|שנים|חודשים|מיליון|מיליארד|אלף)"
)


def _he_named_entities(text: str) -> int:
    """Approximate named-entity count for Hebrew (no capitalisation signal).

    Combines three reliable surface cues: honorific/title prefixes, gershayim
    acronyms (בג\"ץ, צה\"ל…), and quoted outlet/work names. This replaces the
    English [A-Z][a-z]+ proper-noun heuristic, which scores ~0 on Hebrew.
    """
    count = 0
    for title in HE_TITLES:
        count += len(re.findall(title, text))
    count += len(HE_ACRONYM.findall(text))
    count += len(HE_QUOTED.findall(text))
    return count


def _score_passage_he(text: str, heading: Optional[str] = None) -> dict:
    """Score a single passage for AI citability (0-100) — Hebrew."""
    text = normalise_hebrew(text)
    heading = normalise_hebrew(heading) if heading else heading
    words = text.split()
    word_count = len(words)

    scores = {
        "answer_block_quality": 0,
        "self_containment": 0,
        "structural_readability": 0,
        "statistical_density": 0,
        "uniqueness_signals": 0,
    }

    # === 1. Answer Block Quality (30%) ===
    abq_score = 0
    for pattern in HE_DEFINITION:
        if re.search(pattern, text):
            abq_score += 15
            break

    first_60 = " ".join(words[:60])
    if any(re.search(p, first_60) for p in HE_EARLY_ANSWER):
        abq_score += 15

    if (heading and (heading.endswith("?") or HE_QUESTION_WORDS.search(heading))):
        abq_score += 10

    sentences = re.split(r"[.!?]+", text)
    short_clear = sum(1 for s in sentences if 4 <= len(s.split()) <= 22)
    if sentences:
        abq_score += int((short_clear / len(sentences)) * 10)

    if any(re.search(p, text) for p in HE_SOURCES):
        abq_score += 10

    scores["answer_block_quality"] = min(abq_score, 30)

    # === 2. Self-Containment (25%) — recalibrated length band for Hebrew ===
    sc_score = 0
    if 90 <= word_count <= 120:
        sc_score += 10
    elif 70 <= word_count <= 150:
        sc_score += 7
    elif 55 <= word_count <= 180:
        sc_score += 4
    elif word_count < 20 or word_count > 300:
        sc_score += 0
    else:
        sc_score += 2

    pronoun_count = len(HE_PRONOUNS.findall(text))
    if word_count > 0:
        pronoun_ratio = pronoun_count / word_count
        if pronoun_ratio < 0.02:
            sc_score += 8
        elif pronoun_ratio < 0.04:
            sc_score += 5
        elif pronoun_ratio < 0.06:
            sc_score += 3

    entities = _he_named_entities(text)
    if entities >= 3:
        sc_score += 7
    elif entities >= 1:
        sc_score += 4

    scores["self_containment"] = min(sc_score, 25)

    # === 3. Structural Readability (20%) ===
    sr_score = 0
    if sentences:
        avg_len = word_count / len(sentences)
        # Hebrew sentences pack more meaning per token; allow a slightly lower band.
        if 8 <= avg_len <= 18:
            sr_score += 8
        elif 6 <= avg_len <= 23:
            sr_score += 5
        else:
            sr_score += 2
    if HE_TRANSITIONS.search(text):
        sr_score += 4
    if HE_LIST.search(text):
        sr_score += 4
    if "\n" in text:
        sr_score += 4
    scores["structural_readability"] = min(sr_score, 20)

    # === 4. Statistical Density (15%) ===
    sd_score = 0
    pct_count = len(re.findall(r"\d+(?:\.\d+)?%", text)) + len(re.findall(r"\d+\s*אחוז", text))
    sd_score += min(pct_count * 3, 6)
    money_count = len(re.findall(r"[₪]\s*[\d,]+", text)) + len(re.findall(r"[\d,]+\s*ש\"ח", text))
    sd_score += min(money_count * 3, 5)
    sd_score += min(len(HE_NUM_CONTEXT.findall(text)) * 2, 4)
    if re.search(r"\b20(?:2[3-6]|1\d)\b", text):
        sd_score += 2
    for pattern in HE_SOURCES:
        if re.search(pattern, text):
            sd_score += 2
            break
    scores["statistical_density"] = min(sd_score, 15)

    # === 5. Uniqueness Signals (10%) ===
    us_score = 0
    if HE_UNIQUE_RESEARCH.search(text):
        us_score += 5
    if HE_UNIQUE_EXAMPLE.search(text):
        us_score += 3
    if entities >= 1:  # concrete named actors signal first-hand specificity
        us_score += 2
    scores["uniqueness_signals"] = min(us_score, 10)

    return _finalise(text, words, word_count, scores, "he")


# ---------------------------------------------------------------------------
# Shared finalisation (grade bands identical across languages)
# ---------------------------------------------------------------------------

def _finalise(text, words, word_count, scores, lang) -> dict:
    total = sum(scores.values())
    if total >= 80:
        grade, label = "A", "Highly Citable"
    elif total >= 65:
        grade, label = "B", "Good Citability"
    elif total >= 50:
        grade, label = "C", "Moderate Citability"
    elif total >= 35:
        grade, label = "D", "Low Citability"
    else:
        grade, label = "F", "Poor Citability"
    return {
        "language": lang,
        "heading": None,
        "word_count": word_count,
        "total_score": total,
        "grade": grade,
        "label": label,
        "breakdown": scores,
        "preview": " ".join(words[:30]) + ("..." if word_count > 30 else ""),
    }


def score_passage(text: str, heading: Optional[str] = None) -> dict:
    """Language-dispatching entry point. Hebrew -> Hebrew scorer, else English."""
    lang = detect_language(text)
    result = (_score_passage_he if lang == "he" else _score_passage_en)(text, heading)
    result["heading"] = heading
    return result


# ---------------------------------------------------------------------------
# Page-level analysis (unchanged interface)
# ---------------------------------------------------------------------------

def analyze_page_citability(url: str) -> dict:
    """Analyze all content blocks on a page for citability."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            timeout=30,
        )
        response.raise_for_status()
    except Exception as e:
        return {"error": f"Failed to fetch page: {str(e)}"}

    soup = BeautifulSoup(response.text, "lxml")
    for element in soup.find_all(["script", "style", "nav", "footer", "header", "aside", "form"]):
        element.decompose()

    blocks = []
    current_heading = "Introduction"
    current_paragraphs = []
    for element in soup.find_all(["h1", "h2", "h3", "h4", "p", "ul", "ol", "table"]):
        if element.name.startswith("h"):
            if current_paragraphs:
                combined = " ".join(current_paragraphs)
                if len(combined.split()) >= 20:
                    blocks.append({"heading": current_heading, "content": combined})
            current_heading = element.get_text(strip=True)
            current_paragraphs = []
        else:
            text = element.get_text(strip=True)
            if text and len(text.split()) >= 5:
                current_paragraphs.append(text)
    if current_paragraphs:
        combined = " ".join(current_paragraphs)
        if len(combined.split()) >= 20:
            blocks.append({"heading": current_heading, "content": combined})

    scored_blocks = [score_passage(b["content"], b["heading"]) for b in blocks]

    if scored_blocks:
        avg_score = sum(b["total_score"] for b in scored_blocks) / len(scored_blocks)
        top_blocks = sorted(scored_blocks, key=lambda x: x["total_score"], reverse=True)[:5]
        bottom_blocks = sorted(scored_blocks, key=lambda x: x["total_score"])[:5]
        # Optimal length depends on the dominant language of the block.
        optimal_count = sum(
            1 for b in scored_blocks
            if (90 <= b["word_count"] <= 120 if b.get("language") == "he"
                else 134 <= b["word_count"] <= 167)
        )
    else:
        avg_score, top_blocks, bottom_blocks, optimal_count = 0, [], [], 0

    grade_dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0}
    for block in scored_blocks:
        grade_dist[block["grade"]] += 1

    lang_dist = {"he": 0, "en": 0}
    for block in scored_blocks:
        lang_dist[block.get("language", "en")] += 1

    return {
        "url": url,
        "language_distribution": lang_dist,
        "total_blocks_analyzed": len(scored_blocks),
        "average_citability_score": round(avg_score, 1),
        "optimal_length_passages": optimal_count,
        "grade_distribution": grade_dist,
        "top_5_citable": top_blocks,
        "bottom_5_citable": bottom_blocks,
        "all_blocks": scored_blocks,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python citability_scorer.py <url>")
        print("Returns JSON with citability analysis for all content blocks.")
        print("Hebrew passages are scored with the Hebrew engine; all others with the English engine.")
        sys.exit(1)
    result = analyze_page_citability(sys.argv[1])
    print(json.dumps(result, indent=2, default=str, ensure_ascii=False))
