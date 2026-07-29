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

from fetch_page import (  # noqa: E402
    active_crawlers,
    check_agent_readiness,
    probe_ai_crawlers,
)


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


AGENT_ENDPOINTS = {
    "api_catalog": "/.well-known/api-catalog",
    "oauth_authorization_server": "/.well-known/oauth-authorization-server",
    "oauth_protected_resource": "/.well-known/oauth-protected-resource",
    "mcp_server_card": "/.well-known/mcp/server-card.json",
    "agents_json": "/.well-known/agents.json",
    "web_bot_auth_directory": "/.well-known/http-message-signatures-directory",
    "rsl_txt": "/rsl.txt",
    "rsl_xml": "/rsl.xml",
    "nlweb_ask": "/ask",
    "nlweb_mcp": "/mcp",
}


class TestAgentReadiness:
    def test_all_absent(self):
        with patch("fetch_page.requests.get", return_value=_resp(404, text="not found")):
            result = check_agent_readiness("https://example.com")
        assert set(result["checks"].keys()) == set(AGENT_ENDPOINTS.keys())
        for name, check in result["checks"].items():
            assert check["found"] is False, name
        assert result["summary"]["found_count"] == 0
        assert result["summary"]["checked_count"] == len(AGENT_ENDPOINTS)

    def test_mcp_server_card_found(self):
        def fake_get(url, **kwargs):
            if url.endswith("/.well-known/mcp/server-card.json"):
                return _resp(200, text='{"name": "example-mcp"}',
                             headers={"Content-Type": "application/json"})
            return _resp(404, text="not found")
        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://example.com")
        assert result["checks"]["mcp_server_card"]["found"] is True
        assert result["checks"]["mcp_server_card"]["status"] == 200
        assert result["summary"]["found_count"] == 1

    def test_nlweb_405_counts_as_endpoint_exists(self):
        """NLWeb /ask and /mcp are POST endpoints; a GET may return 405 —
        that still proves the endpoint exists (a missing route returns 404)."""
        def fake_get(url, **kwargs):
            if url.endswith("/ask") or url.endswith("/mcp"):
                return _resp(405, text="method not allowed")
            return _resp(404, text="not found")
        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://example.com")
        assert result["checks"]["nlweb_ask"]["found"] is True
        assert result["checks"]["nlweb_mcp"]["found"] is True

    def test_html_200_on_wellknown_is_not_found(self):
        """SPAs that return their index.html for every path must not count as
        having agent endpoints: a 200 whose body looks like HTML is a soft-404."""
        def fake_get(url, **kwargs):
            return _resp(200, text="<!DOCTYPE html><html><body>app</body></html>",
                         headers={"Content-Type": "text/html"})
        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://example.com")
        for name in ("api_catalog", "mcp_server_card", "agents_json",
                     "web_bot_auth_directory", "rsl_txt", "rsl_xml"):
            assert result["checks"][name]["found"] is False, name

    def test_homepage_headers_captured(self):
        def fake_get(url, **kwargs):
            if url.rstrip("/") == "https://example.com":
                return _resp(200, headers={
                    "Content-Usage": "train-ai=n",
                    "Link": '</api-catalog>; rel="api-catalog"',
                })
            return _resp(404, text="not found")
        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://example.com")
        assert result["homepage_headers"]["content_usage"] == "train-ai=n"
        assert "api-catalog" in result["homepage_headers"]["link"]

    def test_network_error_recorded_not_raised(self):
        with patch("fetch_page.requests.get", side_effect=Exception("boom")):
            result = check_agent_readiness("https://example.com")
        assert result["summary"]["found_count"] == 0
        assert result["errors"]
