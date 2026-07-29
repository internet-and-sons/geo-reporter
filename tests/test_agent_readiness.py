"""
v0.4.1 tests: HTTP 402 pay-per-crawl classification, agent-readiness
well-known probes, and licensing-signal extraction.

Mocking style mirrors test_fetch_page_bots.py: patch
``fetch_page.requests.get`` and feed responses via side_effect (one
baseline response followed by one response per active crawler).
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import active_crawlers, probe_ai_crawlers  # noqa: E402


BASELINE_HTML = (
    "<!DOCTYPE html><html><head><title>Example</title></head>"
    "<body><h1>Example article</h1>"
    + ("<p>Real server-rendered content paragraph with plenty of words. </p>" * 40)
    + "</body></html>"
)


def _resp(status=200, text=BASELINE_HTML, headers=None):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = headers or {}
    mock.history = []
    mock.url = "https://example.com/"
    return mock


class TestPaymentRequired:
    def test_402_is_payment_required_not_blocked_not_allowed(self):
        """A 402 is a payment demand — distinct from both blocked and allowed."""
        responses = [_resp(200)] + [_resp(402, text="payment required")
                                    for _ in active_crawlers()]
        with patch("fetch_page.requests.get", side_effect=responses):
            result = probe_ai_crawlers("https://example.com")
        for p in result["probes"]:
            assert p["payment_required"] is True, p["bot"]
            assert p["blocked"] is False, p["bot"]
            assert p["block_reason"] == "payment-required (HTTP 402 — pay-per-crawl)", p["bot"]

    def test_payment_required_bots_summary_field(self):
        responses = [_resp(200)] + [_resp(402, text="payment required")
                                    for _ in active_crawlers()]
        with patch("fetch_page.requests.get", side_effect=responses):
            result = probe_ai_crawlers("https://example.com")
        assert set(result["payment_required_bots"]) == set(active_crawlers().keys())

    def test_mixed_402_and_200(self):
        """402 only for some bots: those are payment_required, the rest allowed."""
        bots = list(active_crawlers().keys())
        responses = [_resp(200)]
        for name in bots:
            responses.append(_resp(402, text="x") if name == "GPTBot" else _resp(200))
        with patch("fetch_page.requests.get", side_effect=responses):
            result = probe_ai_crawlers("https://example.com")
        by_bot = {p["bot"]: p for p in result["probes"]}
        assert by_bot["GPTBot"]["payment_required"] is True
        assert by_bot["ClaudeBot"]["payment_required"] is False
        assert result["payment_required_bots"] == ["GPTBot"]

    def test_ordinary_403_still_blocked_not_payment(self):
        responses = [_resp(200)] + [_resp(403, text="forbidden")
                                    for _ in active_crawlers()]
        with patch("fetch_page.requests.get", side_effect=responses):
            result = probe_ai_crawlers("https://example.com")
        for p in result["probes"]:
            assert p["blocked"] is True
            assert p["payment_required"] is False
        assert result["payment_required_bots"] == []
