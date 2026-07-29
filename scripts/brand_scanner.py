#!/usr/bin/env python3
"""
Brand Mention Scanner — Checks brand presence across AI-cited platforms.

Brand mentions correlate 3x more strongly with AI visibility than backlinks.
(Ahrefs December 2025 study of 75,000 brands)

Platform importance for AI citations:
1. YouTube mentions (~0.737 correlation - STRONGEST)
2. Reddit mentions (high)
3. Wikipedia presence (high)
4. LinkedIn presence (moderate)
5. Domain Rating/backlinks (~0.266 - weak)
"""

import sys
import json
import re
from urllib.parse import quote_plus, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Wikimedia rejects browser-spoofed UAs on its APIs (policy T400119).
# Their API etiquette requires a descriptive UA with contact info.
WIKIMEDIA_HEADERS = {
    "User-Agent": "GEO-Reporter/0.4 (https://github.com/internet-and-sons/geo-reporter; tal@internetandsons.com) python-requests",
    "Accept": "application/json",
}


def check_youtube_presence(brand_name: str) -> dict:
    """Check brand presence on YouTube."""
    result = {
        "platform": "YouTube",
        "correlation": 0.737,
        "weight": "25%",
        "has_channel": False,
        "mentioned_in_videos": False,
        "search_url": f"https://www.youtube.com/results?search_query={quote_plus(brand_name)}",
        "recommendations": [],
    }

    # Note: Actual YouTube API would be used in production
    # This provides the framework for Claude Code to use WebFetch
    result["check_instructions"] = [
        f"Search YouTube for '{brand_name}' and check:",
        "1. Does the brand have an official YouTube channel?",
        "2. Are there videos FROM the brand (tutorials, demos, thought leadership)?",
        "3. Are there videos ABOUT the brand from other creators?",
        "4. What's the view count on brand-related videos?",
        "5. Are there positive reviews or demonstrations?",
    ]

    result["recommendations"] = [
        "Create a YouTube channel if none exists",
        "Publish educational/tutorial content related to your niche",
        "Encourage customers to create review/demo videos",
        "Optimize video titles and descriptions with brand name",
        "Add timestamps and chapters to improve AI parseability",
        "Include transcripts (YouTube auto-generates, but review for accuracy)",
    ]

    return result


def check_reddit_presence(brand_name: str) -> dict:
    """Check brand presence on Reddit."""
    result = {
        "platform": "Reddit",
        "correlation": "High",
        "weight": "25%",
        "has_subreddit": False,
        "mentioned_in_discussions": False,
        "search_url": f"https://www.reddit.com/search/?q={quote_plus(brand_name)}",
        "recommendations": [],
    }

    result["check_instructions"] = [
        f"Search Reddit for '{brand_name}' and check:",
        "1. Does the brand have its own subreddit (r/brandname)?",
        "2. Is the brand discussed in relevant industry subreddits?",
        "3. What's the sentiment (positive, negative, neutral)?",
        "4. Are there recommendation threads mentioning the brand?",
        "5. Does the brand have an official Reddit presence?",
        "6. Are mentions recent (within last 6 months)?",
    ]

    result["recommendations"] = [
        "Monitor relevant subreddits for brand mentions",
        "Participate authentically in industry discussions (no spam)",
        "Create an official Reddit account for customer support",
        "Share valuable content (not just self-promotion)",
        "Respond to questions about your product/service category",
        "Reddit authenticity matters — don't use marketing speak",
    ]

    return result


def check_wikipedia_presence(brand_name: str, languages=("en", "he")) -> dict:
    """Check brand/entity presence on Wikipedia and Wikidata.

    Wikipedia is checked once per language in `languages`; a hit in ANY
    language counts as presence. Bilingual (e.g. Hebrew/English) brands with
    an article in only one language would otherwise be scored as absent.
    """
    primary_lang = languages[0] if languages else "en"
    result = {
        "platform": "Wikipedia",
        "correlation": "High",
        "weight": "20%",
        "has_wikipedia_page": False,
        "has_wikidata_entry": False,
        "cited_in_articles": False,
        "languages": {},
        "search_url": f"https://{primary_lang}.wikipedia.org/wiki/Special:Search?search={quote_plus(brand_name)}",
        "wikidata_url": f"https://www.wikidata.org/w/index.php?search={quote_plus(brand_name)}",
        "recommendations": [],
    }

    # Check the Wikipedia API once per language
    for lang in languages:
        lang_result = {"found": False, "title": None}
        try:
            api_url = (
                f"https://{lang}.wikipedia.org/w/api.php?action=query&list=search"
                f"&srsearch={quote_plus(brand_name)}&format=json"
            )
            response = requests.get(api_url, headers=WIKIMEDIA_HEADERS, timeout=15)
            if response.status_code == 200:
                search_results = response.json().get("query", {}).get("search", [])
                if search_results:
                    top_title = search_results[0].get("title", "")
                    if brand_name.lower() in top_title.lower():
                        lang_result["found"] = True
                        lang_result["title"] = top_title
                    result["wikipedia_search_results"] = len(search_results)
        except Exception:
            pass
        result["languages"][lang] = lang_result

    result["has_wikipedia_page"] = any(
        entry["found"] for entry in result["languages"].values()
    )

    # Check Wikidata — first language that returns a hit wins
    for lang in languages:
        try:
            wd_api_url = (
                f"https://www.wikidata.org/w/api.php?action=wbsearchentities"
                f"&search={quote_plus(brand_name)}&language={lang}&format=json"
            )
            response = requests.get(wd_api_url, headers=WIKIMEDIA_HEADERS, timeout=15)
            if response.status_code == 200:
                entities = response.json().get("search", [])
                if entities:
                    result["has_wikidata_entry"] = True
                    result["wikidata_id"] = entities[0].get("id", "")
                    result["wikidata_description"] = entities[0].get("description", "")
                    break
        except Exception:
            pass

    result["recommendations"] = [
        "If eligible, create a Wikipedia article (requires notability criteria)",
        "Ensure Wikidata entry exists with complete structured data",
        "Add sameAs links in schema markup pointing to Wikipedia/Wikidata",
        "Get cited in existing Wikipedia articles as a source",
        "Build notability through press coverage and independent reviews",
        "Note: Wikipedia has strict notability guidelines — PR coverage helps establish this",
    ]

    return result


_SAMEAS_PLATFORMS = (
    ("wikipedia", "Wikipedia"),
    ("wikidata", "Wikidata"),
    ("linkedin", "LinkedIn"),
    ("youtube", "YouTube"),
    ("twitter", "X/Twitter"),
    ("x.com", "X/Twitter"),
    ("facebook", "Facebook"),
    ("instagram", "Instagram"),
    ("github", "GitHub"),
    ("crunchbase", "Crunchbase"),
)


def _classify_sameas_platform(url: str) -> str:
    """Classify a sameAs URL to a known platform by its host."""
    host = (urlparse(url).hostname or "").lower()
    for needle, label in _SAMEAS_PLATFORMS:
        if needle in host:
            return label
    return "Other"


def check_sameas_liveness(structured_data, timeout=10) -> dict:
    """Extract sameAs URLs + @id values from JSON-LD and HEAD-check liveness.

    Walks structured_data recursively (dicts, @graph lists, nested
    dicts/lists — mirrors extract_freshness in fetch_page.py). Every
    ``sameAs`` value (string or list of strings) is collected and deduped
    preserving first-seen order; every ``@id`` is collected distinctly.

    Each sameAs URL is HEAD-checked. Servers that reject HEAD (raise, or
    return 405) get one GET retry with stream=True. Degenerate URLs
    (``#``, ``""``, anything not http(s)) are guarded — never requested —
    and recorded as status None / live False.

    Non-scoring: a broken sameAs link is a *finding* for human review, not
    a score change. The entity graph AI engines walk to confirm identity
    is only as trustworthy as its links resolve.
    """
    result = {
        "sameas_urls": [],
        "at_ids": [],
        "at_id_present": False,
        "checks": [],
        "live_count": 0,
        "broken": [],
    }

    def _walk(nodes):
        for node in nodes or []:
            if isinstance(node, dict):
                yield node
                for v in node.values():
                    if isinstance(v, dict):
                        yield from _walk([v])
                    elif isinstance(v, list):
                        yield from _walk(v)

    seen_urls = set()
    seen_ids = set()
    for node in _walk(structured_data):
        same = node.get("sameAs")
        if isinstance(same, str):
            same = [same]
        if isinstance(same, list):
            for entry in same:
                if isinstance(entry, str) and entry not in seen_urls:
                    seen_urls.add(entry)
                    result["sameas_urls"].append(entry)
        node_id = node.get("@id")
        if isinstance(node_id, str) and node_id not in seen_ids:
            seen_ids.add(node_id)
            result["at_ids"].append(node_id)

    result["at_id_present"] = bool(result["at_ids"])

    for url in result["sameas_urls"]:
        status = None
        if url.startswith("http://") or url.startswith("https://"):
            status = _probe_liveness(url, timeout)
        live = status is not None and status < 400
        result["checks"].append(
            {
                "url": url,
                "platform": _classify_sameas_platform(url),
                "status": status,
                "live": live,
            }
        )
        if live:
            result["live_count"] += 1
        else:
            result["broken"].append(url)

    return result


def _probe_liveness(url: str, timeout) -> "int | None":
    """HEAD-check a URL; retry once with GET on exception or 405.

    Returns the final HTTP status code, or None if both attempts fail.
    """
    try:
        resp = requests.head(
            url, headers=DEFAULT_HEADERS, allow_redirects=True, timeout=timeout
        )
        status = resp.status_code
    except requests.RequestException:
        status = None

    if status is None or status == 405:
        try:
            resp = requests.get(
                url,
                headers=DEFAULT_HEADERS,
                allow_redirects=True,
                timeout=timeout,
                stream=True,
            )
            status = resp.status_code
        except requests.RequestException:
            status = None

    return status


def check_linkedin_presence(brand_name: str) -> dict:
    """Check brand presence on LinkedIn."""
    result = {
        "platform": "LinkedIn",
        "correlation": "Moderate",
        "weight": "15%",
        "has_company_page": False,
        "employee_thought_leadership": False,
        "search_url": f"https://www.linkedin.com/search/results/companies/?keywords={quote_plus(brand_name)}",
        "recommendations": [],
    }

    result["check_instructions"] = [
        f"Search LinkedIn for '{brand_name}' and check:",
        "1. Does the company have a LinkedIn page?",
        "2. How many followers?",
        "3. Is the page active with recent posts?",
        "4. Do employees post thought leadership content?",
        "5. Are there LinkedIn articles about the brand?",
        "6. Is there engagement on posts (likes, comments, shares)?",
    ]

    result["recommendations"] = [
        "Create/optimize LinkedIn company page",
        "Post regular thought leadership content",
        "Encourage employees to share company content",
        "Publish long-form LinkedIn articles",
        "Engage with industry discussions and comments",
        "Add company LinkedIn URL to schema sameAs property",
    ]

    return result


def check_other_platforms(brand_name: str) -> dict:
    """Check brand presence on additional platforms."""
    result = {
        "platform": "Other Platforms",
        "weight": "15%",
        "platforms_checked": {},
        "recommendations": [],
    }

    platforms = {
        "Quora": f"https://www.quora.com/search?q={quote_plus(brand_name)}",
        "Stack Overflow": f"https://stackoverflow.com/search?q={quote_plus(brand_name)}",
        "GitHub": f"https://github.com/search?q={quote_plus(brand_name)}",
        "Crunchbase": f"https://www.crunchbase.com/textsearch?q={quote_plus(brand_name)}",
        "Product Hunt": f"https://www.producthunt.com/search?q={quote_plus(brand_name)}",
        "G2": f"https://www.g2.com/search?utf8=&query={quote_plus(brand_name)}",
        "Trustpilot": f"https://www.trustpilot.com/search?query={quote_plus(brand_name)}",
    }

    result["platforms_checked"] = {
        name: {
            "search_url": url,
            "check_instruction": f"Search for '{brand_name}' on {name}",
        }
        for name, url in platforms.items()
    }

    result["recommendations"] = [
        "Maintain profiles on industry-relevant platforms",
        "Respond to questions on Quora and Stack Overflow",
        "Encourage customer reviews on G2 and Trustpilot",
        "Keep Crunchbase profile updated (important for B2B)",
        "Open-source contributions on GitHub boost developer brand authority",
        "Product Hunt launch can generate significant initial buzz",
    ]

    return result


def generate_brand_report(brand_name: str, domain: str = None, languages=("en", "he")) -> dict:
    """Generate a comprehensive brand mention report."""
    report = {
        "brand_name": brand_name,
        "domain": domain,
        "analysis_date": "Generated by GEO Reporter",
        "key_insight": "Brand mentions correlate 3x more strongly with AI visibility than backlinks (Ahrefs Dec 2025, 75K brands)",
        "platforms": {},
        "overall_recommendations": [],
    }

    # Check all platforms
    report["platforms"]["youtube"] = check_youtube_presence(brand_name)
    report["platforms"]["reddit"] = check_reddit_presence(brand_name)
    report["platforms"]["wikipedia"] = check_wikipedia_presence(brand_name, languages=languages)
    report["platforms"]["linkedin"] = check_linkedin_presence(brand_name)
    report["platforms"]["other"] = check_other_platforms(brand_name)

    # Overall recommendations
    report["overall_recommendations"] = [
        "Priority 1: YouTube — highest correlation (0.737) with AI citations. Create educational content.",
        "Priority 2: Reddit — build authentic presence in industry subreddits. No marketing speak.",
        "Priority 3: Wikipedia — establish notability through press coverage, then create/improve entry.",
        "Priority 4: LinkedIn — thought leadership content from founders and employees.",
        "Priority 5: Review platforms — G2, Trustpilot, Capterra for social proof signals.",
        "Cross-platform: Ensure consistent NAP (Name, Address, Phone) across all platforms.",
        "Schema markup: Add sameAs property linking to ALL platform profiles.",
        "Monitor: Set up brand mention alerts across all platforms.",
    ]

    # Compute baseline total_score (0-100) from API-verifiable signals only.
    # Wikipedia + Wikidata are checked via API and produce real booleans;
    # YouTube/Reddit/LinkedIn return check_instructions for the caller to
    # follow up on via WebFetch. After the caller enriches the per-platform
    # has_* fields, they can call compute_brand_score(report) to re-score.
    report["total_score"] = compute_brand_score(report)

    return report


def compute_brand_score(report: dict) -> int:
    """Score 0-100 from per-platform boolean signals.

    Weights mirror the audit rubric:
      Wikipedia presence:   30
      Reddit presence:      20
      YouTube presence:     15
      LinkedIn presence:    10
      Industry sources:     25 (Crunchbase, G2, Trustpilot, etc.)
    """
    p = report.get("platforms", {})
    score = 0

    wiki = p.get("wikipedia", {})
    if wiki.get("has_wikipedia_page") or wiki.get("has_wikidata_entry"):
        score += 30

    reddit = p.get("reddit", {})
    if reddit.get("has_subreddit") or reddit.get("mentioned_in_discussions"):
        score += 20

    youtube = p.get("youtube", {})
    if youtube.get("has_channel") or youtube.get("mentioned_in_videos"):
        score += 15

    linkedin = p.get("linkedin", {})
    if linkedin.get("has_company_page"):
        score += 10

    # Industry sources — credit if ANY of the bundled platforms shows confirmed presence
    other = p.get("other", {}).get("platforms_checked", {})
    if any(v.get("confirmed", False) for v in other.values()):
        score += 25

    return min(score, 100)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python brand_scanner.py <brand_name> [domain] [langs]")
        print("Example: python brand_scanner.py 'Acme Corp' acmecorp.com en,he")
        sys.exit(1)

    brand = sys.argv[1]
    domain = sys.argv[2] if len(sys.argv) > 2 else None
    langs = tuple(sys.argv[3].split(",")) if len(sys.argv) > 3 else ("en", "he")

    result = generate_brand_report(brand, domain, languages=langs)
    print(json.dumps(result, indent=2, default=str))
