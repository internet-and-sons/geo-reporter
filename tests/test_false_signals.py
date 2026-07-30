"""
v0.4.4 tests: three false-signal bugs found on a live Cloudflare-fronted audit.

All three shared one failure mode — a WAF's refusal was read as a *finding*
about the client's site rather than as "we could not tell". Each produced a
confidently wrong statement in a real client report:

  (a) ``check_agent_readiness`` treated any non-404 as "endpoint found", so a
      Cloudflare-strict host (403 on every path) was reported as running the
      NLWeb ``/ask`` and ``/mcp`` endpoints.
  (b) ``check_sameas_liveness`` probed with a spoofed Chrome UA. Wikimedia
      refuses that per policy T400119 (403) and Facebook answers 400, so two
      perfectly good sameAs links were reported to the client as broken.
  (c) ``llmstxt_generator.generate_llmstxt`` did a bare ``requests.get`` with
      no challenge fallback, so it would build an llms.txt out of a Cloudflare
      interstitial.

These tests are written to prove the FALSE CASE IS GONE, not merely that the
happy path still works: an all-403 host must yield zero found and ten
inconclusive; a 403 sameAs must land in ``inconclusive`` and NOT in ``broken``.
``broken`` is what a client is told to go fix, so it must mean genuinely
broken — 404/410/DNS failure — and nothing else.
"""

import sys
import os
from unittest.mock import patch, MagicMock

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from fetch_page import check_agent_readiness, is_challenge_page  # noqa: E402
from fetch_page import AI_CRAWLERS  # noqa: E402
from brand_scanner import check_sameas_liveness  # noqa: E402
from llmstxt_generator import generate_llmstxt  # noqa: E402


AGENT_CHECK_COUNT = 10

# A real Cloudflare interstitial body. Asserted against is_challenge_page()
# below so the fixture cannot silently drift out of the detector's reach.
CHALLENGE_HTML = (
    "<!DOCTYPE html><html><head><title>Just a moment...</title></head>"
    "<body><div class='cf-challenge'>Checking your browser before accessing "
    "the site. Ray ID: 8f0e1a2b3c4d</div></body></html>"
)

REAL_HTML = (
    "<!DOCTYPE html><html><head><title>Zman News | Israel</title>"
    "<meta name='description' content='Daily news coverage.'></head>"
    "<body><h1>Zman News</h1><p>Real server-rendered content.</p></body></html>"
)


def _resp(status=200, text="", headers=None):
    mock = MagicMock()
    mock.status_code = status
    mock.text = text
    mock.headers = headers or {}
    mock.history = []
    return mock


def test_challenge_fixture_actually_trips_the_detector():
    """Guard: if this fails every challenge assertion below is vacuous."""
    assert is_challenge_page(CHALLENGE_HTML, 200) is True
    assert is_challenge_page(REAL_HTML, 200) is False


# ---------------------------------------------------------------------------
# (a) agent readiness — a WAF 403 is inconclusive, never "endpoint found"
# ---------------------------------------------------------------------------


class TestAgentReadinessWafBlindSpot:
    def test_all_403_host_finds_nothing_and_says_so(self):
        """The zman.co.il case: every path 403s, so we know nothing at all.

        Previously ``found = status != 404`` made both NLWeb endpoints
        register as present on a host that simply refuses scripted clients.
        """
        with patch("fetch_page.requests.get",
                   return_value=_resp(403, text=CHALLENGE_HTML)):
            result = check_agent_readiness("https://waf.example")

        assert result["summary"]["found_count"] == 0
        assert result["summary"]["inconclusive_count"] == AGENT_CHECK_COUNT
        assert result["checks"]["nlweb_ask"]["found"] is False
        assert result["checks"]["nlweb_ask"]["inconclusive"] is True
        assert result["checks"]["nlweb_mcp"]["found"] is False
        assert result["checks"]["nlweb_mcp"]["inconclusive"] is True
        # json/text checks are inconclusive on a 403 too, not "absent".
        assert result["checks"]["api_catalog"]["inconclusive"] is True
        assert result["checks"]["api_catalog"]["found"] is False

    def test_405_on_ask_still_proves_the_route_exists(self):
        """The genuine NLWeb signal must survive the fix.

        ``/ask`` is a POST endpoint; a GET returning 405 means the route is
        registered. That is the whole point of the endpoint check.
        """
        def fake_get(url, **kwargs):
            if url.endswith("/ask") or url.endswith("/mcp"):
                return _resp(405, text="method not allowed")
            return _resp(404, text="not found")

        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://nlweb.example")

        assert result["checks"]["nlweb_ask"]["found"] is True
        assert result["checks"]["nlweb_ask"]["inconclusive"] is False
        assert result["checks"]["nlweb_mcp"]["found"] is True
        assert result["summary"]["found_count"] == 2
        assert result["summary"]["inconclusive_count"] == 0

    def test_200_on_ask_is_found(self):
        """A 2xx on an endpoint path is a live route."""
        def fake_get(url, **kwargs):
            if url.endswith("/ask"):
                return _resp(200, text='{"ok": true}')
            return _resp(404, text="not found")

        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://nlweb.example")

        assert result["checks"]["nlweb_ask"]["found"] is True
        assert result["checks"]["nlweb_ask"]["inconclusive"] is False

    def test_404_is_absent_not_inconclusive(self):
        """Genuinely absent must stay distinguishable from blocked."""
        with patch("fetch_page.requests.get",
                   return_value=_resp(404, text="not found")):
            result = check_agent_readiness("https://plain.example")

        for name, check in result["checks"].items():
            assert check["found"] is False, name
            assert check["inconclusive"] is False, name
        assert result["summary"]["found_count"] == 0
        assert result["summary"]["inconclusive_count"] == 0

    def test_500_is_inconclusive_only_via_error_not_status(self):
        """A 5xx is neither found nor a claim of absence for endpoints."""
        def fake_get(url, **kwargs):
            if url.endswith("/ask"):
                return _resp(500, text="server error")
            return _resp(404, text="not found")

        with patch("fetch_page.requests.get", side_effect=fake_get):
            result = check_agent_readiness("https://broken.example")

        assert result["checks"]["nlweb_ask"]["found"] is False

    def test_429_is_inconclusive(self):
        with patch("fetch_page.requests.get",
                   return_value=_resp(429, text="slow down")):
            result = check_agent_readiness("https://ratelimited.example")

        assert result["summary"]["inconclusive_count"] == AGENT_CHECK_COUNT
        assert result["summary"]["found_count"] == 0

    def test_request_error_is_inconclusive(self):
        """A transport failure tells us nothing about the endpoint."""
        with patch("fetch_page.requests.get", side_effect=Exception("boom")):
            result = check_agent_readiness("https://down.example")

        assert result["summary"]["found_count"] == 0
        assert result["summary"]["inconclusive_count"] == AGENT_CHECK_COUNT
        assert result["checks"]["nlweb_ask"]["inconclusive"] is True
        assert result["errors"]


# ---------------------------------------------------------------------------
# (b) sameAs liveness — an honest UA, and 403 != broken
# ---------------------------------------------------------------------------


class TestSameAsFalseBrokenLinks:
    def test_403_wikidata_is_inconclusive_not_broken(self):
        """The reported-to-client bug: Wikidata 403 became "broken link"."""
        sd = [{"sameAs": ["https://www.wikidata.org/wiki/Q12345"]}]
        with patch("brand_scanner.requests.head", return_value=_resp(403)):
            result = check_sameas_liveness(sd)

        assert result["inconclusive"] == ["https://www.wikidata.org/wiki/Q12345"]
        assert result["broken"] == []
        check = result["checks"][0]
        assert check["inconclusive"] is True
        assert check["live"] is False
        assert result["live_count"] == 0

    def test_404_is_genuinely_broken(self):
        """``broken`` must still catch a real dead link."""
        sd = [{"sameAs": ["https://dead.example/gone"]}]
        with patch("brand_scanner.requests.head", return_value=_resp(404)):
            result = check_sameas_liveness(sd)

        assert result["broken"] == ["https://dead.example/gone"]
        assert result["inconclusive"] == []
        assert result["checks"][0]["inconclusive"] is False

    def test_410_is_genuinely_broken(self):
        sd = [{"sameAs": ["https://dead.example/gone-forever"]}]
        with patch("brand_scanner.requests.head", return_value=_resp(410)):
            result = check_sameas_liveness(sd)

        assert result["broken"] == ["https://dead.example/gone-forever"]
        assert result["inconclusive"] == []

    def test_dns_failure_is_genuinely_broken(self):
        sd = [{"sameAs": ["https://nosuchhost.invalid/x"]}]
        with patch("brand_scanner.requests.head",
                   side_effect=requests.RequestException("dns")), \
             patch("brand_scanner.requests.get",
                   side_effect=requests.RequestException("dns")):
            result = check_sameas_liveness(sd)

        assert result["broken"] == ["https://nosuchhost.invalid/x"]
        assert result["inconclusive"] == []

    def test_429_is_inconclusive(self):
        sd = [{"sameAs": ["https://ratelimited.example/profile"]}]
        with patch("brand_scanner.requests.head", return_value=_resp(429)):
            result = check_sameas_liveness(sd)

        assert result["inconclusive"] == ["https://ratelimited.example/profile"]
        assert result["broken"] == []

    def test_401_is_inconclusive(self):
        sd = [{"sameAs": ["https://gated.example/profile"]}]
        with patch("brand_scanner.requests.head", return_value=_resp(401)):
            result = check_sameas_liveness(sd)

        assert result["inconclusive"] == ["https://gated.example/profile"]
        assert result["broken"] == []

    def test_wikimedia_host_gets_the_descriptive_ua(self):
        """Wikimedia policy T400119 refuses browser-spoofed UAs outright."""
        sd = [{"sameAs": ["https://en.wikipedia.org/wiki/Example"]}]
        with patch("brand_scanner.requests.head",
                   return_value=_resp(200)) as mock_head:
            check_sameas_liveness(sd)

        ua = mock_head.call_args.kwargs["headers"]["User-Agent"]
        assert "Chrome" not in ua
        assert "Mozilla" not in ua
        assert "GEO-Reporter" in ua

    def test_wikidata_host_gets_the_descriptive_ua(self):
        sd = [{"sameAs": ["https://www.wikidata.org/wiki/Q42"]}]
        with patch("brand_scanner.requests.head",
                   return_value=_resp(200)) as mock_head:
            check_sameas_liveness(sd)

        ua = mock_head.call_args.kwargs["headers"]["User-Agent"]
        assert "Chrome" not in ua
        assert "GEO-Reporter" in ua

    def test_non_wikimedia_host_also_gets_a_descriptive_ua(self):
        """Facebook answered 400 to the spoofed Chrome UA; be honest everywhere."""
        sd = [{"sameAs": ["https://www.facebook.com/example"]}]
        with patch("brand_scanner.requests.head",
                   return_value=_resp(200)) as mock_head:
            check_sameas_liveness(sd)

        ua = mock_head.call_args.kwargs["headers"]["User-Agent"]
        assert "Chrome" not in ua
        assert "GEO-Reporter" in ua

    def test_get_fallback_also_carries_the_descriptive_ua(self):
        """The 405 HEAD-reject retry must not fall back to the spoofed UA."""
        sd = [{"sameAs": ["https://en.wikipedia.org/wiki/Example"]}]
        with patch("brand_scanner.requests.head", return_value=_resp(405)), \
             patch("brand_scanner.requests.get",
                   return_value=_resp(200)) as mock_get:
            check_sameas_liveness(sd)

        ua = mock_get.call_args.kwargs["headers"]["User-Agent"]
        assert "Chrome" not in ua
        assert "GEO-Reporter" in ua

    def test_mixed_bag_partitions_correctly(self):
        """live / inconclusive / broken are three disjoint buckets."""
        sd = [{"sameAs": [
            "https://ok.example/live",
            "https://waf.example/blocked",
            "https://dead.example/gone",
        ]}]

        def fake_head(url, **kwargs):
            if "blocked" in url:
                return _resp(403)
            if "gone" in url:
                return _resp(404)
            return _resp(200)

        with patch("brand_scanner.requests.head", side_effect=fake_head):
            result = check_sameas_liveness(sd)

        assert result["live_count"] == 1
        assert result["inconclusive"] == ["https://waf.example/blocked"]
        assert result["broken"] == ["https://dead.example/gone"]


# ---------------------------------------------------------------------------
# (c) llms.txt generate-mode — the same WAF blind spot fetch_page fixed
# ---------------------------------------------------------------------------


class TestLlmstxtGenerateChallengeFallback:
    def test_challenge_then_retry_with_gptbot_ua(self):
        """A challenged homepage must be retried once with the GPTBot UA."""
        with patch("llmstxt_generator.requests.get",
                   side_effect=[_resp(200, text=CHALLENGE_HTML),
                                _resp(200, text=REAL_HTML)]) as mock_get:
            result = generate_llmstxt("https://waf.example")

        assert mock_get.call_count == 2
        retry_ua = mock_get.call_args_list[1].kwargs["headers"]["User-Agent"]
        assert retry_ua == AI_CRAWLERS["GPTBot"]["ua"]

        # Generation proceeded off the REAL body, not the interstitial.
        assert "error" not in result
        assert "Zman News" in result["generated_llmstxt"]
        assert "Just a moment" not in result["generated_llmstxt"]

    def test_normal_page_is_fetched_once(self):
        """No challenge => no retry storm."""
        with patch("llmstxt_generator.requests.get",
                   return_value=_resp(200, text=REAL_HTML)) as mock_get:
            result = generate_llmstxt("https://clean.example")

        assert mock_get.call_count == 1
        assert "Zman News" in result["generated_llmstxt"]

    def test_challenged_both_times_reports_an_error(self):
        """Never build an llms.txt out of an interstitial."""
        with patch("llmstxt_generator.requests.get",
                   side_effect=[_resp(403, text=CHALLENGE_HTML),
                                _resp(403, text=CHALLENGE_HTML)]) as mock_get:
            result = generate_llmstxt("https://hostile.example")

        assert mock_get.call_count == 2
        assert "error" in result
        assert "challenge" in result["error"].lower()
        assert result["generated_llmstxt"] == ""

    def test_ordinary_403_does_not_trigger_a_retry(self):
        """A plain 403 body is not a challenge — one request only."""
        with patch("llmstxt_generator.requests.get",
                   return_value=_resp(403, text="<h1>Forbidden</h1>")) as mock_get:
            generate_llmstxt("https://forbidden.example")

        assert mock_get.call_count == 1
