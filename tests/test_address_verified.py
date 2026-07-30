"""Address-verified crawlers must not be scored as blocked.

Google and Microsoft verify their crawlers by network address (reverse
DNS / published IP ranges), so a request carrying their user-agent from
any other network is *supposed* to be refused. That 403 is correct
anti-impersonation behaviour and carries no information about how the
real crawler is treated.

v0.4.3 taught the *report* to render these as "— Not tested (validated by
network address)", but the scoring engine never learned the distinction:
`class_scores` counted every one of those expected 403s as a block. On a
healthy publisher that dragged traditional-search to 0/100 and turned a
HEALTHY_PUBLISHER posture into "MOSTLY_BLOCKED" — the exact Googlebot
false alarm the v0.4.3 changelog warned about.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from fetch_page import (  # noqa: E402
    AI_CRAWLERS,
    address_verified_crawlers,
    score_probe_results,
)


ADDRESS_VERIFIED = (
    "GoogleBot",
    "BingBot",
    "Google-Agent",
    "Google-NotebookLM",
    "Google-GeminiNotebook",
    "Google-CloudVertexBot",
)


def _probe(bot, blocked, status=200):
    meta = AI_CRAWLERS[bot]
    return {
        "bot": bot,
        "class": meta["class"],
        "operator": meta["operator"],
        "status": status,
        "blocked": blocked,
        "payment_required": False,
    }


class TestRosterFlag:
    def test_every_google_and_bing_crawler_is_flagged(self):
        for bot in ADDRESS_VERIFIED:
            assert AI_CRAWLERS[bot].get("address_verified") is True, (
                f"{bot} verifies by network address and must be flagged"
            )

    def test_no_other_crawler_is_flagged(self):
        for name, meta in AI_CRAWLERS.items():
            if name not in ADDRESS_VERIFIED:
                assert not meta.get("address_verified"), (
                    f"{name} is not address-verified; flagging it would "
                    f"silently drop a real block from the score"
                )

    def test_helper_returns_exactly_the_flagged_set(self):
        assert set(address_verified_crawlers()) == set(ADDRESS_VERIFIED)


class TestScoringExcludesThem:
    def test_expected_403_does_not_lower_its_class_score(self):
        """The zman case: all AI bots pass, Google/Bing 403 as designed."""
        probes = [
            _probe("ChatGPT-User", False),
            _probe("Claude-User", False),
            _probe("Perplexity-User", False),
            _probe("MistralAI-User", False),
            # Address-verified — expected refusals, not blocks.
            _probe("Google-Agent", True, 403),
            _probe("Google-NotebookLM", True, 403),
            _probe("Google-GeminiNotebook", True, 403),
        ]
        scores = score_probe_results(probes)["class_scores"]
        live = scores["live-retrieval"]
        assert live["score"] == 100, (
            "4 of 4 testable retrieval bots were reachable; the three "
            "Google 403s are anti-impersonation responses, not blocks"
        )
        assert live["testable"] == 4
        assert live["excluded_address_verified"] == 3

    def test_class_with_no_testable_bots_scores_none_not_zero(self):
        """traditional-search is Googlebot + Bingbot — both address-verified.

        Off-network there is nothing testable in the class. Scoring it 0
        asserts "blocked", which is a claim we have no evidence for.
        """
        probes = [_probe("GoogleBot", True, 403), _probe("BingBot", True, 403)]
        trad = score_probe_results(probes)["class_scores"]["traditional-search"]
        assert trad["score"] is None
        assert trad["testable"] == 0

    def test_real_blocks_in_a_mixed_class_still_count(self):
        """Excluding Google must not mask genuine training blocks."""
        probes = [
            _probe("GPTBot", False),
            _probe("ClaudeBot", False),
            _probe("CCBot", True, 403),
            _probe("Bytespider", True, 403),
            _probe("Meta-ExternalAgent", True, 403),
            _probe("cohere-ai", True, 403),
            _probe("Google-CloudVertexBot", True, 403),
        ]
        training = score_probe_results(probes)["class_scores"]["training"]
        assert training["testable"] == 6
        assert training["blocked"] == 4
        assert training["score"] == 33


class TestVerdictAndOverall:
    def _zman(self):
        return [
            _probe(b, False) for b in (
                "ChatGPT-User", "Claude-User", "Perplexity-User",
                "MistralAI-User", "OAI-SearchBot", "Claude-SearchBot",
                "PerplexityBot", "MistralAI-Index", "DuckAssistBot",
                "Amazonbot", "GPTBot", "ClaudeBot",
            )
        ] + [
            _probe(b, True, 403) for b in (
                "CCBot", "Bytespider", "Meta-ExternalAgent", "cohere-ai",
                "GoogleBot", "BingBot", "Google-Agent", "Google-NotebookLM",
                "Google-GeminiNotebook", "Google-CloudVertexBot",
            )
        ]

    def test_healthy_publisher_is_not_called_mostly_blocked(self):
        result = score_probe_results(self._zman())
        assert result["verdict"] == "HEALTHY_PUBLISHER", (
            "blocks training scrapers, allows every retrieval and search "
            "crawler — the canonical NYT/Reuters posture"
        )

    def test_overall_score_renormalises_over_testable_classes(self):
        """With traditional-search untestable its 0.35 weight must be
        redistributed, not counted as zero."""
        result = score_probe_results(self._zman())
        # retrieval 100 (weight .5) + training 33 (weight .15),
        # renormalised over the 0.65 of weight that is testable.
        assert result["overall_score"] == 85
        assert result["untestable_classes"] == ["traditional-search"]

    def test_a_genuine_retrieval_block_still_scores_badly(self):
        """Guard against the fix turning into a whitewash."""
        probes = [
            _probe("ChatGPT-User", True, 403),
            _probe("Claude-User", True, 403),
            _probe("Perplexity-User", True, 403),
            _probe("MistralAI-User", True, 403),
            _probe("OAI-SearchBot", True, 403),
            _probe("GoogleBot", True, 403),
        ]
        result = score_probe_results(probes)
        assert result["class_scores"]["live-retrieval"]["score"] == 0
        assert result["verdict"] in ("BLOCKED", "MOSTLY_BLOCKED")
