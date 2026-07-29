"""
v0.4.2 tests: sameAs liveness + @id extraction for the entity-graph audit.

``check_sameas_liveness`` walks parsed JSON-LD (structured_data), extracts
every ``sameAs`` URL and ``@id`` value, then HEAD-checks each sameAs URL for
liveness. Broken sameAs links (``href="#"``, 404s, dead profiles) are a real,
common entity-graph defect — a finding, not a score change.

Network is always mocked: ``brand_scanner.requests.head`` (and ``.get`` for the
405 / HEAD-rejected fallback path). Degenerate URLs (``#``, ``""``) are guarded
and must never hit the network.
"""

import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from brand_scanner import check_sameas_liveness  # noqa: E402


def _resp(status):
    m = MagicMock()
    m.status_code = status
    return m


# --- extraction -----------------------------------------------------------


def test_sameas_list_across_organization_node():
    sd = [
        {
            "@type": "Organization",
            "@id": "https://example.com/#org",
            "sameAs": [
                "https://en.wikipedia.org/wiki/Example",
                "https://www.linkedin.com/company/example",
                "https://x.com/example",
            ],
        }
    ]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    assert result["sameas_urls"] == [
        "https://en.wikipedia.org/wiki/Example",
        "https://www.linkedin.com/company/example",
        "https://x.com/example",
    ]
    assert result["live_count"] == 3
    assert result["broken"] == []


def test_sameas_dedupe_preserves_first_seen_order():
    sd = [
        {"sameAs": ["https://a.example/x", "https://b.example/y", "https://a.example/x"]},
    ]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    assert result["sameas_urls"] == ["https://a.example/x", "https://b.example/y"]


def test_sameas_nested_in_graph():
    sd = [
        {
            "@graph": [
                {"@type": "WebSite", "@id": "https://example.com/#website"},
                {
                    "@type": "Person",
                    "@id": "https://example.com/#person",
                    "sameAs": ["https://en.wikipedia.org/wiki/Jane"],
                },
            ]
        }
    ]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    assert result["sameas_urls"] == ["https://en.wikipedia.org/wiki/Jane"]
    assert set(result["at_ids"]) == {
        "https://example.com/#website",
        "https://example.com/#person",
    }


def test_sameas_single_string_not_list():
    sd = [{"@type": "Organization", "sameAs": "https://x.com/onlyone"}]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    assert result["sameas_urls"] == ["https://x.com/onlyone"]


def test_sameas_ignores_non_string_entries():
    sd = [{"sameAs": ["https://good.example/ok", 123, None, {"@id": "x"}]}]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    assert result["sameas_urls"] == ["https://good.example/ok"]


# --- @id extraction -------------------------------------------------------


def test_at_id_extraction_and_present_flag():
    sd = [{"@type": "Organization", "@id": "https://example.com/#org", "sameAs": []}]
    result = check_sameas_liveness(sd)
    assert result["at_ids"] == ["https://example.com/#org"]
    assert result["at_id_present"] is True


def test_at_id_absent_flag():
    sd = [{"@type": "Organization", "name": "Example"}]
    result = check_sameas_liveness(sd)
    assert result["at_ids"] == []
    assert result["at_id_present"] is False


# --- guarded degenerate URLs (no network) ---------------------------------


def test_degenerate_urls_are_guarded_no_request():
    sd = [{"sameAs": ["#", ""]}]
    with patch("brand_scanner.requests.head") as mock_head, patch(
        "brand_scanner.requests.get"
    ) as mock_get:
        result = check_sameas_liveness(sd)
    mock_head.assert_not_called()
    mock_get.assert_not_called()
    assert result["sameas_urls"] == ["#", ""]
    assert result["live_count"] == 0
    for check in result["checks"]:
        assert check["status"] is None
        assert check["live"] is False
    assert set(result["broken"]) == {"#", ""}


# --- liveness -------------------------------------------------------------


def test_live_200():
    sd = [{"sameAs": ["https://live.example/ok"]}]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    check = result["checks"][0]
    assert check["status"] == 200
    assert check["live"] is True
    assert result["live_count"] == 1
    assert result["broken"] == []


def test_broken_404():
    sd = [{"sameAs": ["https://dead.example/gone"]}]
    with patch("brand_scanner.requests.head", return_value=_resp(404)):
        result = check_sameas_liveness(sd)
    check = result["checks"][0]
    assert check["status"] == 404
    assert check["live"] is False
    assert result["broken"] == ["https://dead.example/gone"]


def test_head_raises_then_get_fallback_live():
    sd = [{"sameAs": ["https://picky.example/nohead"]}]
    with patch(
        "brand_scanner.requests.head", side_effect=requests_exc()
    ) as mock_head, patch(
        "brand_scanner.requests.get", return_value=_resp(200)
    ) as mock_get:
        result = check_sameas_liveness(sd)
    mock_head.assert_called_once()
    mock_get.assert_called_once()
    assert result["checks"][0]["status"] == 200
    assert result["checks"][0]["live"] is True


def test_head_405_then_get_fallback_live():
    sd = [{"sameAs": ["https://picky.example/405"]}]
    with patch(
        "brand_scanner.requests.head", return_value=_resp(405)
    ) as mock_head, patch(
        "brand_scanner.requests.get", return_value=_resp(200)
    ) as mock_get:
        result = check_sameas_liveness(sd)
    mock_head.assert_called_once()
    mock_get.assert_called_once()
    assert result["checks"][0]["status"] == 200
    assert result["checks"][0]["live"] is True


def test_head_and_get_both_fail_status_none():
    sd = [{"sameAs": ["https://down.example/x"]}]
    with patch(
        "brand_scanner.requests.head", side_effect=requests_exc()
    ), patch("brand_scanner.requests.get", side_effect=requests_exc()):
        result = check_sameas_liveness(sd)
    check = result["checks"][0]
    assert check["status"] is None
    assert check["live"] is False
    assert result["broken"] == ["https://down.example/x"]


# --- platform classification ----------------------------------------------


def test_platform_classification():
    sd = [
        {
            "sameAs": [
                "https://en.wikipedia.org/wiki/Example",
                "https://www.linkedin.com/company/example",
                "https://x.com/example",
                "https://example.org/blog",
            ]
        }
    ]
    with patch("brand_scanner.requests.head", return_value=_resp(200)):
        result = check_sameas_liveness(sd)
    by_url = {c["url"]: c["platform"] for c in result["checks"]}
    assert by_url["https://en.wikipedia.org/wiki/Example"] == "Wikipedia"
    assert by_url["https://www.linkedin.com/company/example"] == "LinkedIn"
    assert by_url["https://x.com/example"] == "X/Twitter"
    assert by_url["https://example.org/blog"] == "Other"


def requests_exc():
    """A RequestException instance (imported lazily to mirror brand_scanner)."""
    import requests

    return requests.RequestException("boom")
