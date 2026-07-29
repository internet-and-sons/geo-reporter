"""
Doc/roster sync tests for skills/geo-crawlers/SKILL.md.

AI_CRAWLERS in scripts/fetch_page.py is the single source of truth for bot
identity. The geo-crawlers skill documents a human-readable subset of the same
bots, including verbatim "Full User-Agent String" values that readers copy into
WAF allowlist rules. When the two drift, we ship a reference doc that disagrees
with our own probe and hand users rules that never match.

This drifted twice in v0.4.3 alone: the roster UA-version bump left the doc on
GPTBot/1.2 and OAI-SearchBot/1.0, and a subsequent sweep found three older
pre-existing drifts (ClaudeBot documented as a bare token with no Mozilla
wrapper, Amazonbot documented with an entirely different legacy UA, CCBot
missing the '+' before its URL). A convention note in the doc is not enough —
these tests make the invariant enforceable.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import AI_CRAWLERS

SKILL_PATH = os.path.join(
    os.path.dirname(__file__), "..", "skills", "geo-crawlers", "SKILL.md"
)

# Bots documented in geo-crawlers that legitimately have no AI_CRAWLERS entry.
# Each exemption must name a reason; do not add to this set to silence a real
# drift.
#
#   GoogleOther — documented only to tell readers it is legacy/low-value and has
#   been dropped from the recommended robots.txt config. It is not an AI search
#   crawler, so the live probe has no reason to carry it. The doc entry exists
#   purely so a reader who finds GoogleOther in their robots.txt learns they can
#   ignore it.
DOCUMENTED_BUT_NOT_IN_ROSTER = {"GoogleOther"}


def _skill_text():
    with open(SKILL_PATH, encoding="utf-8") as fh:
        return fh.read()


def _reference_section(text):
    """The '## Complete AI Crawler Reference' section, where bots are documented.

    Scoped so that '####' headings elsewhere in the file (report templates and
    the like) can never be mistaken for bot entries.
    """
    start = text.index("## Complete AI Crawler Reference")
    end = text.index("## Recommendation Matrix Summary", start)
    return text[start:end]


def _documented_uas(text):
    """[(bot_name, ua)] for every documented Full User-Agent String.

    The UA line belongs to the nearest preceding '#### <bot>' heading.
    """
    section = _reference_section(text)
    pairs = []
    current = None
    for line in section.splitlines():
        heading = re.match(r"^####\s+(\S+)", line)
        if heading:
            current = heading.group(1)
            continue
        ua = re.match(r"^-\s+\*\*Full User-Agent String:\*\*\s+`(.+)`\s*$", line)
        if ua:
            pairs.append((current, ua.group(1)))
    return pairs


def _documented_bots(text):
    return re.findall(r"^####\s+(\S+)", _reference_section(text), flags=re.MULTILINE)


def test_documented_uas_match_roster_verbatim():
    """Every documented UA string must be some roster entry's `ua`, byte-for-byte."""
    pairs = _documented_uas(_skill_text())
    assert pairs, "no Full User-Agent String entries found — did the doc format change?"

    for bot, documented in pairs:
        expected = AI_CRAWLERS.get(bot, {}).get("ua")
        assert expected is not None, (
            f"{bot} documents a Full User-Agent String but has no AI_CRAWLERS entry. "
            f"Add it to the roster in scripts/fetch_page.py, or drop the UA line."
        )
        assert documented == expected, (
            f"UA drift for {bot} — skills/geo-crawlers/SKILL.md disagrees with the "
            f"AI_CRAWLERS roster (the roster is the source of truth).\n"
            f"  doc:    {documented}\n"
            f"  roster: {expected}\n"
            f"Fix: copy the roster value verbatim into the doc's "
            f"'**Full User-Agent String:**' line for {bot}."
        )


def test_documented_ua_bots_are_unique():
    """Guards the parser: two UA lines under one heading would mask a drift."""
    bots = [bot for bot, _ in _documented_uas(_skill_text())]
    dupes = {b for b in bots if bots.count(b) > 1}
    assert not dupes, f"duplicate Full User-Agent String entries for: {sorted(dupes)}"


def test_documented_bots_exist_in_roster():
    """Population check: documented bots exist in the roster, save named exemptions."""
    missing = {
        bot
        for bot in _documented_bots(_skill_text())
        if bot not in AI_CRAWLERS and bot not in DOCUMENTED_BUT_NOT_IN_ROSTER
    }
    assert not missing, (
        f"documented in skills/geo-crawlers/SKILL.md but absent from AI_CRAWLERS: "
        f"{sorted(missing)}. Either add the bot to the roster in "
        f"scripts/fetch_page.py, or add it to DOCUMENTED_BUT_NOT_IN_ROSTER with a "
        f"comment explaining why it is exempt."
    )


def test_exemptions_are_still_needed():
    """A stale exemption is a silently weakened assertion — fail when one is."""
    documented = set(_documented_bots(_skill_text()))
    for bot in DOCUMENTED_BUT_NOT_IN_ROSTER:
        assert bot in documented, (
            f"{bot} is exempted in DOCUMENTED_BUT_NOT_IN_ROSTER but is no longer "
            f"documented in the skill — remove the stale exemption."
        )
        assert bot not in AI_CRAWLERS, (
            f"{bot} is exempted in DOCUMENTED_BUT_NOT_IN_ROSTER but now HAS a roster "
            f"entry — remove the exemption so the bot is checked like the rest."
        )
