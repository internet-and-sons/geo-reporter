#!/usr/bin/env python3
"""
Fetch and parse web pages for GEO analysis.
Extracts HTML, text content, meta tags, headers, and structured data.
"""

import sys
import json
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup, Comment
except ImportError:
    print("ERROR: Required packages not installed. Run: pip install -r requirements.txt")
    sys.exit(1)

# AI crawler user agents used for live probing.
#
# Each bot carries a "class" tag because the labs themselves split their
# fleets by purpose, and the GEO impact differs sharply by class. Mixing
# them in a single bucket — as earlier versions of this module did —
# produces misleading verdicts: a publisher that blocks training while
# allowing retrieval (NYT, WSJ, Reuters, BBC pattern) is doing the
# right thing for AI visibility, but flat scoring would call them
# "partially blocked".
#
# The four classes:
#
#   training       — bulk-collects content for foundation-model training
#                    (GPTBot, ClaudeBot, CCBot, Google-Extended, etc.).
#                    Lab docs explicitly state this content is not used
#                    in live answers. Blocking has near-zero GEO impact.
#   search-index   — indexes pages for AI search results
#                    (OAI-SearchBot, Claude-SearchBot, PerplexityBot).
#                    Blocking removes the site from AI search citations.
#   live-retrieval — fetched on demand when a user asks a question
#                    (ChatGPT-User, Claude-User, Perplexity-User).
#                    Blocking prevents user-triggered citations.
#   traditional-search — Googlebot, Bingbot. Power Google AI Overviews
#                    and Bing/Copilot. Blocking is almost always a
#                    misconfiguration and worth flagging loudly.
#
# Each entry also carries a "status" (defaulting to "active" when
# absent), because the roster is the single source of truth for BOTH
# the live probe and the robots.txt declared-policy parser:
#
#   active        — real, currently-operating crawler. Probed live.
#   retired       — legacy token the operator no longer fetches with
#                   (anthropic-ai, claude-web, FacebookBot). Kept so
#                   robots.txt analysis can spot stale configs; never
#                   probed, because a 403 for a UA nobody sends is noise.
#   opt-out-token — robots.txt signal only (Google-Extended,
#                   Applebot-Extended). The operator never fetches with
#                   this UA, so probing measures WAF UA-filtering and
#                   nothing else. Declared-policy analysis only.
#
# Use active_crawlers() for anything that hits the network.
#
# See OpenAI/Anthropic/Perplexity bot docs and the Cloudflare/Botify
# 2025 publisher-log analyses cited in the geo-botaccess SKILL.md.
AI_CRAWLERS = {
    # OpenAI
    "GPTBot": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.4; +https://openai.com/gptbot)",
        "class": "training",
        "operator": "OpenAI",
    },
    "OAI-SearchBot": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.4; +https://openai.com/searchbot)",
        "class": "search-index",
        "operator": "OpenAI",
    },
    "ChatGPT-User": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ChatGPT-User/1.0; +https://openai.com/bot)",
        "class": "live-retrieval",
        "operator": "OpenAI",
    },
    # Anthropic
    "ClaudeBot": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ClaudeBot/1.0; +https://www.anthropic.com/claude-bot)",
        "class": "training",
        "operator": "Anthropic",
    },
    "Claude-SearchBot": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-SearchBot/1.0; +https://www.anthropic.com/claudebot)",
        "class": "search-index",
        "operator": "Anthropic",
    },
    "Claude-User": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Claude-User/1.0; +https://www.anthropic.com/claudebot)",
        "class": "live-retrieval",
        "operator": "Anthropic",
    },
    # Perplexity
    "PerplexityBot": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)",
        "class": "search-index",
        "operator": "Perplexity",
    },
    "Perplexity-User": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Perplexity-User/1.0; +https://perplexity.ai/perplexity-user)",
        "class": "live-retrieval",
        "operator": "Perplexity",
    },
    # Mistral. Both tokens documented at https://docs.mistral.ai/robots/ and
    # both explicitly NOT used for generative AI training.
    "MistralAI-User": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; MistralAI-User/1.0; +https://docs.mistral.ai/robots)",
        "class": "live-retrieval",
        "operator": "Mistral",
    },
    "MistralAI-Index": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; MistralAI-Index/1.0; +https://docs.mistral.ai/robots)",
        "class": "search-index",
        "operator": "Mistral",
    },
    # DuckDuckGo
    "DuckAssistBot": {
        "ua": "Mozilla/5.0 (compatible; DuckAssistBot/1.2; +http://duckduckgo.com/duckassistbot.html)",
        "class": "search-index",
        "operator": "DuckDuckGo",
    },
    # Google agentic / grounding fetchers (Web Bot Auth signer; a plain
    # UA replay approximates WAF UA-filtering only, not signature checks)
    "Google-Agent": {
        "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko; compatible; Google-Agent; +https://developers.google.com/crawling/docs/crawlers-fetchers/google-agent) Chrome/138.0.0.0 Safari/537.36",
        "class": "live-retrieval",
        "operator": "Google",
    },
    "Google-CloudVertexBot": {
        "ua": "Mozilla/5.0 (compatible; Google-CloudVertexBot/1.0; +http://www.google.com/bot.html)",
        "class": "training",
        "operator": "Google",
    },
    # Google-NotebookLM is the LEGACY token for the Gemini Notebook
    # fetcher. Google renamed it to Google-GeminiNotebook and supports
    # the old spelling only through August 2026 — probe both until then,
    # then flip Google-NotebookLM to status "retired".
    "Google-NotebookLM": {
        "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 (compatible; Google-NotebookLM; +https://developers.google.com/crawling/docs/crawlers-fetchers/google-gemininotebook)",
        "class": "live-retrieval",
        "operator": "Google",
    },
    "Google-GeminiNotebook": {
        "ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36 (compatible; Google-GeminiNotebook; +https://developers.google.com/crawling/docs/crawlers-fetchers/google-gemininotebook)",
        "class": "live-retrieval",
        "operator": "Google",
    },
    # Amazon
    "Amazonbot": {
        "ua": "Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Amazonbot/0.1) Chrome/119.0.0.0 Safari/537.36",
        "class": "search-index",
        "operator": "Amazon",
    },
    # Google / Apple training opt-out tokens. These aren't real crawlers
    # — they're robots.txt signals that the operator honours separately.
    # Probing them tests only WAF-side UA filtering; treat results as
    # informational rather than diagnostic of real bot reachability.
    "Google-Extended": {
        "ua": "Mozilla/5.0 (compatible; Google-Extended/1.0; +http://www.google.com/bot.html)",
        "class": "training",
        "operator": "Google",
        "status": "opt-out-token",
    },
    "Applebot-Extended": {
        "ua": "Mozilla/5.0 (compatible; Applebot-Extended/1.0)",
        "class": "training",
        "operator": "Apple",
        "status": "opt-out-token",
    },
    # Traditional search bots (blocking these is usually a mistake).
    # Surface separately because Googlebot 403 also kills regular
    # Google Search indexing, not just AI Overviews.
    "GoogleBot": {
        "ua": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
        "class": "traditional-search",
        "operator": "Google",
    },
    "BingBot": {
        "ua": "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
        "class": "traditional-search",
        "operator": "Microsoft",
    },
    # Training-only crawlers. Often deliberately blocked by publishers
    # — that posture is GEO-healthy and the report should not penalise it.
    "CCBot": {
        "ua": "CCBot/2.0 (+https://commoncrawl.org/faq/)",
        "class": "training",
        "operator": "Common Crawl",
    },
    "Bytespider": {
        "ua": "Bytespider/1.0",
        "class": "training",
        "operator": "ByteDance",
    },
    "Meta-ExternalAgent": {
        "ua": "Meta-ExternalAgent/1.0 (+https://www.meta.com/)",
        "class": "training",
        "operator": "Meta",
    },
    "cohere-ai": {
        "ua": "cohere-ai/1.0",
        "class": "training",
        "operator": "Cohere",
    },
    # Retired legacy tokens — declared-policy analysis + stale-config
    # detection only; never probed live.
    "anthropic-ai": {
        "ua": "anthropic-ai/1.0",
        "class": "training",
        "operator": "Anthropic",
        "status": "retired",
    },
    "claude-web": {
        "ua": "claude-web/1.0",
        "class": "training",
        "operator": "Anthropic",
        "status": "retired",
    },
    "FacebookBot": {
        "ua": "FacebookBot/1.0 (+http://www.facebook.com/bot.html)",
        "class": "training",
        "operator": "Meta",
        "status": "retired",
    },
}

# The four bot classes, in priority order for verdict logic. The
# overall score weights these as 0.5 (retrieval = live + search),
# 0.35 (traditional search), 0.15 (training) — see probe_ai_crawlers().
BOT_CLASSES = (
    "live-retrieval",
    "search-index",
    "traditional-search",
    "training",
)


def active_crawlers() -> dict:
    """Subset of AI_CRAWLERS that are real, currently-operating crawlers.

    The live probe uses ONLY this subset. Retired tokens and opt-out
    tokens stay in AI_CRAWLERS for declared-policy (robots.txt) analysis.
    """
    return {
        name: info
        for name, info in AI_CRAWLERS.items()
        if info.get("status", "active") == "active"
    }

# Back-compat alias for callers and tests that still reference the
# flat "AI search bots" set. New code should use AI_CRAWLERS[name]["class"].
AI_SEARCH_BOTS = {
    name for name, meta in AI_CRAWLERS.items()
    if meta["class"] in ("search-index", "live-retrieval", "traditional-search")
}

# Substrings that indicate a Cloudflare interstitial / challenge page
# rather than real site content. Used both on the browser baseline
# (to detect that we need a Playwright fallback) and on individual bot
# responses (to detect "200 OK" responses that are actually challenge
# pages disguised as success).
CF_CHALLENGE_MARKERS = (
    "cf-challenge",
    "cf-turnstile",
    "ray id",
    "checking your browser",
    "attention required",
    "just a moment",
    "enable javascript and cookies",
    "cf-chl-bypass",
    "challenge-platform",
)

# WAF / CDN fingerprints. Each entry is (product_name, predicate, evidence)
# where the predicate is called with two pre-normalised arguments:
#
#   headers_lower:  dict[str, str] of response headers, both keys and
#                   values lowercased for case-insensitive matching
#   cookies_blob:   one big lowercase string with all Set-Cookie values
#                   concatenated, for cheap "name in blob" cookie tests
#
# Identifying the specific product matters because remediation differs
# completely per product. "Allow GPTBot in Cloudflare" is a different
# procedure than "Allow GPTBot in Imperva" or "Allow GPTBot in AWS WAF".
# Skills that consume this data give product-specific dashboard paths
# in their recommendations, which is far more actionable than a generic
# "configure your WAF" suggestion.
#
# Multiple products can legitimately stack (e.g. Cloudflare in front of
# AWS ELB), so detect_waf() returns a list rather than a single value.
WAF_FINGERPRINTS = (
    ("Cloudflare", lambda h, c: "cf-ray" in h, "cf-ray header"),
    ("Cloudflare", lambda h, c: "cloudflare" in h.get("server", ""), "server: cloudflare"),
    ("Cloudflare", lambda h, c: any(n in c for n in ("__cf_bm", "cf_clearance", "__cfduid")), "cf_bm/cf_clearance cookie"),
    ("AWS CloudFront", lambda h, c: "x-amz-cf-id" in h, "x-amz-cf-id header"),
    ("AWS WAF", lambda h, c: "x-amzn-waf-action" in h, "x-amzn-waf-action header"),
    ("AWS ELB", lambda h, c: "awselb" in h.get("server", ""), "server: awselb"),
    ("Akamai", lambda h, c: "akamaighost" in h.get("server", "") or "akamai" in h.get("server", ""), "server: AkamaiGHost"),
    ("Akamai", lambda h, c: any(k.startswith("x-akamai") for k in h), "x-akamai-* header"),
    ("Akamai", lambda h, c: "akamai-grn" in h, "akamai-grn header"),
    ("Sucuri", lambda h, c: "sucuri" in h.get("server", ""), "server: sucuri/cloudproxy"),
    ("Sucuri", lambda h, c: "x-sucuri-id" in h or "x-sucuri-cache" in h, "x-sucuri-* header"),
    ("Imperva Incapsula", lambda h, c: "x-iinfo" in h, "x-iinfo header"),
    ("Imperva Incapsula", lambda h, c: "incapsula" in h.get("x-cdn", ""), "x-cdn: Incapsula"),
    ("Imperva Incapsula", lambda h, c: "incap_ses" in c or "visid_incap" in c, "incap_ses cookie"),
    ("F5 BIG-IP", lambda h, c: "big-ip" in h.get("server", "") or "bigip" in h.get("server", ""), "server: BIG-IP"),
    ("F5 BIG-IP", lambda h, c: "bigipserver" in c, "BIGipServer cookie"),
    ("F5 BIG-IP ASM", lambda h, c: "x-waf-event-info" in h, "x-waf-event-info header"),
    ("Fastly", lambda h, c: "x-fastly-request-id" in h, "x-fastly-request-id header"),
    ("Fastly", lambda h, c: "fastly" in h.get("server", ""), "server: fastly"),
    ("Barracuda WAF", lambda h, c: "barra_counter_session" in c, "barra_counter_session cookie"),
    ("Wallarm", lambda h, c: "nginx-wallarm" in h or "wallarm" in h.get("server", ""), "wallarm header"),
    ("Azure Front Door", lambda h, c: "x-azure-ref" in h, "x-azure-ref header"),
    ("StackPath", lambda h, c: any(k.startswith("x-sp-") for k in h), "x-sp-* header"),
    ("Google Frontend", lambda h, c: "google frontend" in h.get("server", ""), "server: Google Frontend"),
)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
}


FRESHNESS_TIERS = ((90, "fresh"), (365, "aging"), (730, "stale"))


def extract_freshness(structured_data, soup, headers) -> dict:
    """Best-effort content dates + freshness tier.

    Priority: JSON-LD dateModified > JSON-LD datePublished >
    <time datetime> > Last-Modified header. Freshness is a measured
    AI-citation signal (~50% of cited pages <13 weeks old, Ahrefs 2026);
    'unknown' means undated content — itself a finding, since AI engines
    can't verify recency without a machine-readable date.

    Tiers: fresh <90d, aging 90-365d, stale 365-730d, very-stale >730d,
    future-dated more than a day ahead of now, unknown when no date is
    discoverable. 'future-dated' is a markup defect, not fresh content —
    age_days stays negative as evidence rather than being clamped. Dates
    up to a day ahead stay 'fresh'; see the tolerance note below.
    """
    result = {
        "date_published": None,
        "date_modified": None,
        "last_modified_header": (headers or {}).get("Last-Modified"),
        "best_date": None,
        "age_days": None,
        "tier": "unknown",
        "source": None,
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

    for node in _walk(structured_data):
        if not result["date_published"] and node.get("datePublished"):
            result["date_published"] = str(node["datePublished"])
        if not result["date_modified"] and node.get("dateModified"):
            result["date_modified"] = str(node["dateModified"])

    candidates = [
        (result["date_modified"], "structured_data"),
        (result["date_published"], "structured_data"),
    ]
    if soup is not None:
        t = soup.find("time", attrs={"datetime": True})
        if t:
            candidates.append((t["datetime"], "time_tag"))
    candidates.append((result["last_modified_header"], "http_header"))

    for raw, source in candidates:
        if not raw:
            continue
        parsed = None
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = parsedate_to_datetime(str(raw))
            except (TypeError, ValueError):
                continue
        if parsed is None:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - parsed).days
        result["best_date"] = str(raw)
        result["age_days"] = age
        result["source"] = source
        # -1 tolerance, not 0: naive (offset-less) markup from a site ahead of
        # UTC parses as "future" here, since we stamp naive datetimes as UTC.
        # Worst legitimate case is UTC+14, which floors to age_days == -1, so
        # anything below that is a genuine defect (template-variable bugs,
        # dates months or years out) rather than timezone skew.
        if age < -1:
            result["tier"] = "future-dated"
        else:
            result["tier"] = next(
                (tier for limit, tier in FRESHNESS_TIERS if age < limit), "very-stale"
            )
        break

    return result


# Schema.org @types that mark a page as a standalone content unit — the
# thing an AI engine actually cites. Everything else (WebSite,
# CollectionPage, NewsMediaOrganization, ...) describes a wrapper.
ARTICLE_SCHEMA_TYPES = frozenset(
    {"article", "newsarticle", "blogposting", "report"}
)

# First path segment values that mark a navigation surface rather than a
# content unit. A /tag/politics/ or /writer/37401/ link is how humans
# browse; it is not the citable article.
NAVIGATION_PATH_PREFIXES = frozenset(
    {
        "about", "archive", "archives", "author", "authors", "cart",
        "categories", "category", "contact", "faq", "feed", "help",
        "login", "page", "person", "press", "privacy", "rss", "search",
        "section", "sections", "tag", "tags", "terms", "topic", "topics",
        "wp-admin", "wp-content", "wp-json",
    }
)

_NUMERIC_ID_SEGMENT = re.compile(r"^\d{4,}$")
_DATE_PATH = re.compile(r"/(19|20)\d{2}/\d{1,2}(/|$)")
_HYPHENATED_SLUG = re.compile(r"^[^/]*[a-z0-9]+(-[a-z0-9]+){1,}[^/]*$", re.IGNORECASE)

# Listing thresholds. Both are deliberately loose: this is a routing hint,
# not a score, and the cost of a false "listing" is one extra sampling
# pass while the cost of a false "article" is auditing the wrapper.
LISTING_MIN_H1S = 4          # "> 3" — a content unit has one h1
LISTING_MIN_ARTICLE_LINKS = 10


def _looks_like_article_url(link_url: str, host: str) -> bool:
    """Heuristic: is this same-host link a content unit or navigation?

    Content-shaped: a numeric ID segment of 4+ digits (/708066/), a date
    segment (/2026/07/...), or a multi-word hyphenated slug. Navigation:
    /about/, /tag/politics/, /writer/37401/ and friends.
    """
    if not link_url or not isinstance(link_url, str):
        return False
    try:
        parsed = urlparse(link_url)
    except ValueError:
        return False
    if parsed.netloc and host and parsed.netloc.lower() != host.lower():
        return False
    path = parsed.path or ""
    segments = [seg for seg in path.split("/") if seg]
    if not segments:
        return False
    if segments[0].lower() in NAVIGATION_PATH_PREFIXES:
        return False
    if any(_NUMERIC_ID_SEGMENT.match(seg) for seg in segments):
        return True
    if _DATE_PATH.search(path):
        return True
    last = segments[-1]
    # Strip a trailing file extension before slug-testing (/a-b-c.html).
    last = re.sub(r"\.(html?|php|aspx?)$", "", last, flags=re.IGNORECASE)
    if "-" in last and len(last) > 8 and _HYPHENATED_SLUG.match(last):
        return True
    return False


def _iter_schema_nodes(structured_data):
    """Yield every dict node in a JSON-LD blob, descending into @graph."""
    stack = list(structured_data or [])
    seen = 0
    while stack and seen < 500:
        node = stack.pop()
        seen += 1
        if isinstance(node, dict):
            yield node
            for value in node.values():
                if isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(node, list):
            stack.extend(node)


def _article_schema_types(structured_data) -> list:
    """Article-family @type values present in the page's JSON-LD."""
    found = []
    for node in _iter_schema_nodes(structured_data):
        raw = node.get("@type")
        values = raw if isinstance(raw, list) else [raw]
        for value in values:
            if not isinstance(value, str):
                continue
            name = value.rsplit("/", 1)[-1].strip()
            if name.lower() in ARTICLE_SCHEMA_TYPES and name not in found:
                found.append(name)
    return found


def classify_page_type(page_data: dict) -> dict:
    """Decide whether a fetched page is the citable unit or a wrapper.

    Pure function over an existing fetch_page() result — no network. A
    news section page (zman.co.il/democracy) is a human navigation
    surface; the units AI engines cite are the articles beneath it.
    Auditing the wrapper produces recommendations about the wrapper's
    19 h1s and boilerplate description, none of which govern citation.

    Returns {"type": "article"|"listing"|"homepage"|"other",
             "confidence": "high"|"medium"|"low",
             "signals": [human-readable evidence strings]}.
    The signals are quoted verbatim as Evidence in the report, so they
    are written for a client reading them, not for a debugger.
    """
    page_data = page_data or {}
    url = page_data.get("url") or ""
    h1_tags = page_data.get("h1_tags") or []
    structured_data = page_data.get("structured_data") or []
    freshness = page_data.get("freshness") or {}
    internal_links = page_data.get("internal_links") or []

    h1_count = len(h1_tags)
    tier = freshness.get("tier") or "unknown"
    freshness_resolved = tier != "unknown"

    try:
        parsed_url = urlparse(url)
    except ValueError:
        parsed_url = None
    host = parsed_url.netloc if parsed_url else ""
    path = (parsed_url.path if parsed_url else "") or ""

    # --- homepage: checked first, it outranks every other signal -------
    if path in ("", "/"):
        return {
            "type": "homepage",
            "confidence": "high",
            "signals": ["URL is the site root (no path segment)"],
        }

    # --- gather evidence ----------------------------------------------
    article_types = _article_schema_types(structured_data)

    article_link_urls = set()
    for link in internal_links:
        if isinstance(link, dict):
            link_url = link.get("url")
        elif isinstance(link, str):
            link_url = link
        else:
            continue
        if _looks_like_article_url(link_url, host):
            article_link_urls.add(link_url)
    article_link_count = len(article_link_urls)

    signals = []

    # --- article -------------------------------------------------------
    if article_types:
        signals.append(f"{'/'.join(article_types)} schema present")
        if h1_count == 1:
            signals.append("exactly 1 h1 element")
        elif h1_count:
            signals.append(f"{h1_count} h1 elements")
        else:
            signals.append("no h1 element")
        if freshness_resolved:
            signals.append(f"freshness resolved ({tier})")
        else:
            signals.append("freshness unresolved (no machine-readable date)")
        confidence = "high" if (h1_count == 1 and freshness_resolved) else "medium"
        return {"type": "article", "confidence": confidence, "signals": signals}

    # --- listing -------------------------------------------------------
    many_h1s = h1_count > LISTING_MIN_H1S - 1
    many_article_links = article_link_count >= LISTING_MIN_ARTICLE_LINKS
    if (many_h1s or many_article_links) and not freshness_resolved:
        signals.append("no Article-family schema")
        if many_h1s:
            signals.append(f"{h1_count} h1 elements")
        if many_article_links:
            signals.append(f"{article_link_count} article-shaped internal links")
        signals.append("freshness unresolved (no machine-readable date)")
        confidence = "high" if (many_h1s and many_article_links) else "medium"
        return {"type": "listing", "confidence": confidence, "signals": signals}

    # --- other ---------------------------------------------------------
    signals.append("no Article-family schema")
    signals.append(f"{h1_count} h1 element{'' if h1_count == 1 else 's'}")
    signals.append(f"{article_link_count} article-shaped internal links")
    if freshness_resolved:
        signals.append(f"freshness resolved ({tier})")
    else:
        signals.append("freshness unresolved (no machine-readable date)")
    return {"type": "other", "confidence": "low", "signals": signals}


def fetch_page(url: str, timeout: int = 30, accept_language: str = None) -> dict:
    """Fetch a page and return structured analysis data.

    accept_language overrides the default Accept-Language header so the
    non-default language tree of a bilingual site can be audited.
    """
    result = {
        "url": url,
        "status_code": None,
        "redirect_chain": [],
        "headers": {},
        "meta_tags": {},
        "title": None,
        "description": None,
        "canonical": None,
        "h1_tags": [],
        "heading_structure": [],
        "word_count": 0,
        "text_content": "",
        "internal_links": [],
        "external_links": [],
        "images": [],
        "structured_data": [],
        "freshness": {},
        "has_ssr_content": True,
        "security_headers": {},
        "fetch_method": "default",
        "challenge_detected": False,
        "errors": [],
    }

    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        result["errors"].append(f"Unsupported URL scheme: {parsed_url.scheme!r}. Only http and https are allowed.")
        return result

    try:
        request_headers = dict(DEFAULT_HEADERS)
        if accept_language:
            request_headers["Accept-Language"] = f"{accept_language},{accept_language};q=0.9,en;q=0.5"
        response = requests.get(
            url,
            headers=request_headers,
            timeout=timeout,
            allow_redirects=True,
        )

        # WAF/CDN challenge fallback. Cloudflare and friends serve an
        # interstitial to generic scripted user-agents — sometimes with a
        # 200 status — and parsing that block page as if it were the site
        # would silently corrupt every downstream analysis. Retry ONCE with
        # the GPTBot user-agent, which sites that challenge scripted
        # browsers commonly allowlist. One retry only: no retry storms, and
        # nothing happens at all unless the body actually looks like a
        # challenge (an ordinary 403/404/500 is left alone).
        if is_challenge_page(response.text, response.status_code):
            result["challenge_detected"] = True
            bot_headers = dict(request_headers)
            bot_headers["User-Agent"] = AI_CRAWLERS["GPTBot"]["ua"]
            bot_response = requests.get(
                url,
                headers=bot_headers,
                timeout=timeout,
                allow_redirects=True,
            )
            if not is_challenge_page(bot_response.text, bot_response.status_code):
                # The bot UA got through — everything downstream parses the
                # retry response instead of the challenge page.
                response = bot_response
                result["fetch_method"] = "bot_ua_fallback"
            else:
                # Challenged both ways. Keep the original response for a
                # best-effort parse and flag the result as unreliable.
                result["errors"].append(
                    "Page returned a WAF/CDN challenge to both a browser "
                    "user-agent and a bot user-agent; content analysis may "
                    "be unreliable."
                )

        # Track redirects
        if response.history:
            result["redirect_chain"] = [
                {"url": r.url, "status": r.status_code} for r in response.history
            ]

        result["status_code"] = response.status_code
        result["headers"] = dict(response.headers)

        # Security headers check
        security_headers = [
            "Strict-Transport-Security",
            "Content-Security-Policy",
            "X-Frame-Options",
            "X-Content-Type-Options",
            "Referrer-Policy",
            "Permissions-Policy",
        ]
        for header in security_headers:
            result["security_headers"][header] = response.headers.get(header, None)

        # Parse HTML
        soup = BeautifulSoup(response.text, "lxml")

        # Title
        title_tag = soup.find("title")
        result["title"] = title_tag.get_text(strip=True) if title_tag else None

        # Meta tags
        for meta in soup.find_all("meta"):
            name = meta.get("name", meta.get("property", ""))
            content = meta.get("content", "")
            if name and content:
                result["meta_tags"][name.lower()] = content
                if name.lower() == "description":
                    result["description"] = content

        # Canonical
        canonical = soup.find("link", rel="canonical")
        result["canonical"] = canonical.get("href") if canonical else None

        # Headings
        for level in range(1, 7):
            for heading in soup.find_all(f"h{level}"):
                text = heading.get_text(strip=True)
                result["heading_structure"].append({"level": level, "text": text})
                if level == 1:
                    result["h1_tags"].append(text)

        # Structured data (JSON-LD) — extract before decompose() mutates the tree
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string)
                result["structured_data"].append(data)
            except (json.JSONDecodeError, TypeError):
                result["errors"].append("Invalid JSON-LD detected")

        result["freshness"] = extract_freshness(
            result["structured_data"], soup, result["headers"]
        )

        # SSR check — must run BEFORE decompose() mutates the tree
        js_app_roots = soup.find_all(
            id=re.compile(r"(app|root|__next|__nuxt)", re.I)
        )

        # Check SSR by measuring content inside framework root divs
        # before decompose() strips elements from the tree
        ssr_check_results = []
        for root_el in js_app_roots:
            inner_text = root_el.get_text(strip=True)
            ssr_check_results.append({
                "id": root_el.get("id", "unknown"),
                "text_length": len(inner_text),
            })

        # Text content — decompose non-content elements (destructive)
        for element in soup.find_all(["script", "style", "nav", "footer", "header"]):
            element.decompose()
        text = soup.get_text(separator=" ", strip=True)
        result["text_content"] = text
        result["word_count"] = len(text.split())

        # Links
        parsed_url = urlparse(url)
        base_domain = parsed_url.netloc
        for link in soup.find_all("a", href=True):
            href = urljoin(url, link["href"])
            link_text = link.get_text(strip=True)
            parsed_href = urlparse(href)
            if parsed_href.netloc == base_domain:
                result["internal_links"].append({"url": href, "text": link_text})
            elif parsed_href.scheme in ("http", "https"):
                result["external_links"].append({"url": href, "text": link_text})

        # Images
        for img in soup.find_all("img"):
            img_data = {
                "src": img.get("src", ""),
                "alt": img.get("alt", ""),
                "width": img.get("width"),
                "height": img.get("height"),
                "loading": img.get("loading"),
            }
            result["images"].append(img_data)

        # SSR assessment — use pre-decompose measurements + overall content
        if js_app_roots:
            for check in ssr_check_results:
                # Only flag as client-rendered if both the root div has
                # minimal content AND the overall page has little text.
                # Sites using SSR/prerendering (WordPress, LiteSpeed Cache,
                # Prerender.io) will have substantial text despite having
                # framework-style root divs.
                if check["text_length"] < 50 and result["word_count"] < 200:
                    result["has_ssr_content"] = False
                    result["errors"].append(
                        f"Possible client-side only rendering detected: "
                        f"#{check['id']} has minimal server-rendered content "
                        f"({result['word_count']} words on page)"
                    )

    except requests.exceptions.Timeout:
        result["errors"].append(f"Timeout after {timeout} seconds")
    except requests.exceptions.ConnectionError as e:
        result["errors"].append(f"Connection error: {str(e)}")
    except Exception as e:
        result["errors"].append(f"Unexpected error: {str(e)}")

    return result


def fetch_robots_txt(url: str, timeout: int = 15) -> dict:
    """Fetch and parse robots.txt for AI crawler directives."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

    # Declared-policy analysis covers the ENTIRE roster — including retired
    # and opt-out-token entries. A site can still carry rules for a token the
    # operator no longer honours, and that's worth reporting.
    ai_crawlers = list(AI_CRAWLERS.keys())

    result = {
        "url": robots_url,
        "exists": False,
        "content": "",
        "ai_crawler_status": {},
        "stale_tokens": [],
        "sitemaps": [],
        "licensing": {"license_urls": [], "content_usage": [], "content_signal": []},
        "errors": [],
    }

    try:
        response = requests.get(robots_url, headers=DEFAULT_HEADERS, timeout=timeout)

        if response.status_code == 200:
            result["exists"] = True
            result["content"] = response.text

            # Parse for each AI crawler
            lines = response.text.split("\n")
            current_agent = None
            agent_rules = {}

            for line in lines:
                line = line.strip()
                if line.lower().startswith("user-agent:"):
                    current_agent = line.split(":", 1)[1].strip()
                    if current_agent not in agent_rules:
                        agent_rules[current_agent] = []
                elif line.lower().startswith("disallow:") and current_agent:
                    path = line.split(":", 1)[1].strip()
                    agent_rules[current_agent].append(
                        {"directive": "Disallow", "path": path}
                    )
                elif line.lower().startswith("allow:") and current_agent:
                    path = line.split(":", 1)[1].strip()
                    agent_rules[current_agent].append(
                        {"directive": "Allow", "path": path}
                    )
                elif line.lower().startswith("sitemap:"):
                    sitemap_url = line.split(":", 1)[1].strip()
                    # Handle case where "Sitemap:" splits off the "http"
                    if not sitemap_url.startswith("http"):
                        sitemap_url = "http" + sitemap_url
                    result["sitemaps"].append(sitemap_url)
                # Machine-readable AI-licensing directives (non-scoring —
                # pure extraction; the skill layer renders presence as info).
                # `split(":", 1)` keeps everything after the FIRST colon, so
                # URLs with their own colons survive intact.
                elif line.lower().startswith("license:"):
                    result["licensing"]["license_urls"].append(
                        line.split(":", 1)[1].strip()
                    )
                elif line.lower().startswith("content-usage:"):
                    result["licensing"]["content_usage"].append(
                        line.split(":", 1)[1].strip()
                    )
                elif line.lower().startswith("content-signal:"):
                    result["licensing"]["content_signal"].append(
                        line.split(":", 1)[1].strip()
                    )

            # Determine status for each AI crawler
            for crawler in ai_crawlers:
                if crawler in agent_rules:
                    rules = agent_rules[crawler]
                    if any(
                        r["directive"] == "Disallow" and r["path"] == "/"
                        for r in rules
                    ):
                        result["ai_crawler_status"][crawler] = "BLOCKED"
                    elif any(
                        r["directive"] == "Disallow" and r["path"] for r in rules
                    ):
                        result["ai_crawler_status"][crawler] = "PARTIALLY_BLOCKED"
                    else:
                        result["ai_crawler_status"][crawler] = "ALLOWED"
                elif "*" in agent_rules:
                    wildcard_rules = agent_rules["*"]
                    if any(
                        r["directive"] == "Disallow" and r["path"] == "/"
                        for r in wildcard_rules
                    ):
                        result["ai_crawler_status"][crawler] = "BLOCKED_BY_WILDCARD"
                    else:
                        result["ai_crawler_status"][crawler] = "ALLOWED_BY_DEFAULT"
                else:
                    result["ai_crawler_status"][crawler] = "NOT_MENTIONED"

            # Flag retired tokens that the site still carries rules for —
            # dead weight worth a cleanup recommendation (informational).
            result["stale_tokens"] = [
                name
                for name, info in AI_CRAWLERS.items()
                if info.get("status") == "retired" and name in agent_rules
            ]

        elif response.status_code == 404:
            result["errors"].append("No robots.txt found (404)")
            for crawler in ai_crawlers:
                result["ai_crawler_status"][crawler] = "NO_ROBOTS_TXT"
        else:
            result["errors"].append(
                f"Unexpected status code: {response.status_code}"
            )

    except Exception as e:
        result["errors"].append(f"Error fetching robots.txt: {str(e)}")

    return result


def fetch_llms_txt(url: str, timeout: int = 15) -> dict:
    """Check for llms.txt file."""
    parsed = urlparse(url)
    llms_url = f"{parsed.scheme}://{parsed.netloc}/llms.txt"
    llms_full_url = f"{parsed.scheme}://{parsed.netloc}/llms-full.txt"

    result = {
        "llms_txt": {"url": llms_url, "exists": False, "content": ""},
        "llms_full_txt": {"url": llms_full_url, "exists": False, "content": ""},
        "errors": [],
    }

    for key, check_url in [("llms_txt", llms_url), ("llms_full_txt", llms_full_url)]:
        try:
            response = requests.get(
                check_url, headers=DEFAULT_HEADERS, timeout=timeout
            )
            if response.status_code == 200:
                result[key]["exists"] = True
                result[key]["content"] = response.text
        except Exception as e:
            result["errors"].append(f"Error checking {check_url}: {str(e)}")

    return result


def extract_content_blocks(html: str) -> list:
    """Extract content blocks for citability analysis."""
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for element in soup.find_all(
        ["script", "style", "nav", "footer", "header", "aside"]
    ):
        element.decompose()

    blocks = []
    # Extract content sections (between headings)
    current_heading = None
    current_content = []

    for element in soup.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "table", "blockquote"]
    ):
        tag = element.name

        if tag.startswith("h"):
            # Save previous block
            if current_content:
                text = " ".join(current_content)
                word_count = len(text.split())
                blocks.append(
                    {
                        "heading": current_heading,
                        "content": text,
                        "word_count": word_count,
                        "tag_types": list(
                            set(
                                [
                                    e.name
                                    for e in element.find_all_previous(
                                        ["p", "ul", "ol", "table"]
                                    )
                                ]
                            )
                        ),
                    }
                )
            current_heading = element.get_text(strip=True)
            current_content = []
        else:
            text = element.get_text(strip=True)
            if text:
                current_content.append(text)

    # Don't forget the last block
    if current_content:
        text = " ".join(current_content)
        blocks.append(
            {
                "heading": current_heading,
                "content": text,
                "word_count": len(text.split()),
            }
        )

    return blocks


def is_challenge_page(html: str, status_code: int) -> bool:
    """Detect a Cloudflare interstitial / WAF block page disguised as content.

    Cloudflare and similar products serve HTML challenge pages that look
    like real responses (sometimes even with a 200 status). The body
    contains characteristic markers like ``cf-challenge`` or
    "Checking your browser". We check the first 8 KB only because the
    markers always appear early in the document and bounding the check
    keeps it cheap on large pages.
    """
    head = (html or "")[:8000].lower()
    if status_code in (403, 503):
        if any(m in head for m in CF_CHALLENGE_MARKERS):
            return True
        # Cloudflare's own error pages are clearly branded — treat any
        # 403/503 served from Cloudflare as a challenge for the purposes
        # of "did this bot reach the real content".
        if "cloudflare" in head:
            return True
    if status_code == 200:
        if any(m in head for m in CF_CHALLENGE_MARKERS):
            return True
    return False


def detect_waf(response) -> list:
    """Fingerprint WAF/CDN products from response headers and cookies.

    Returns a list of ``{"product": str, "evidence": str}`` dicts. Multiple
    products may stack legitimately (e.g. Cloudflare in front of an AWS
    ELB), so the function never short-circuits — it walks the full
    fingerprint table and de-duplicates by product name, keeping the
    first piece of evidence found for each.

    Pure function over the headers, so it's trivial to unit-test by
    constructing a fake response object.
    """
    headers_lower = {k.lower(): str(v).lower() for k, v in response.headers.items()}

    # Some servers send Set-Cookie multiple times. requests exposes them
    # via the underlying response.raw object or via response.cookies, but
    # the cleanest cross-version path is to flatten the headers we already
    # have. We just need a string for substring matching.
    cookie_blob = headers_lower.get("set-cookie", "")

    seen = set()
    detected = []
    for product, predicate, evidence in WAF_FINGERPRINTS:
        if product in seen:
            continue
        try:
            if predicate(headers_lower, cookie_blob):
                detected.append({"product": product, "evidence": evidence})
                seen.add(product)
        except Exception:
            # A broken fingerprint should never break the whole scan.
            # Swallow and continue so a single bad predicate doesn't
            # take out detection for every other product.
            pass
    return detected


def _playwright_baseline(url: str, timeout_ms: int = 30000):
    """Fetch ``url`` with a real headless browser, for JS-challenged sites.

    Returns ``(status, html)`` on success or ``None`` if Playwright isn't
    installed or the fetch fails. We import inside the function so the
    rest of fetch_page.py keeps working when Playwright is missing —
    Playwright is in requirements.txt but graceful degradation matters
    for users on minimal installs.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(user_agent=DEFAULT_HEADERS["User-Agent"])
            page = ctx.new_page()
            resp = page.goto(url, wait_until="networkidle", timeout=timeout_ms)
            status = resp.status if resp else 200
            html = page.content()
            browser.close()
            return status, html
    except Exception:
        return None


def _content_similarity(a: str, b: str) -> float:
    """Cheap text-similarity score in [0, 1] for the first 10 KB of two pages.

    Used to catch the case where a bot receives HTTP 200 with a totally
    different (often stripped or generic) body than the browser baseline.
    SequenceMatcher is good enough here — we don't need linguistic
    analysis, just "are these obviously the same page". The 10 KB cap
    keeps the comparison constant-time on long articles.
    """
    def normalise(text: str) -> str:
        return re.sub(r"\s+", " ", (text or "")[:10000]).strip().lower()
    return SequenceMatcher(None, normalise(a), normalise(b)).ratio()


def probe_ai_crawlers(url: str, timeout: int = 15) -> dict:
    """Live-probe a URL with AI crawler user-agents to detect WAF blocking.

    This is the empirical complement to ``fetch_robots_txt``. Static
    robots.txt analysis tells you what a site *declares*; this function
    tells you what AI bots *actually* receive. The two often disagree:
    a site can have a permissive robots.txt while a Cloudflare bot
    management rule silently returns 403 to GPTBot, ClaudeBot, and
    Googlebot. The declared policy looks fine; the live reality is
    that AI search products see nothing.

    Workflow:

      1. Fetch a browser baseline so we know what real content looks
         like (size, body, headers).
      2. Detect Cloudflare JS challenges on that baseline. If found,
         try a Playwright headless fallback so we have a usable
         reference for similarity comparison. If Playwright is missing,
         we degrade gracefully and rely on status-code / challenge-body
         detection alone.
      3. Fingerprint WAF/CDN products from the baseline headers — this
         drives product-specific remediation in downstream skills.
      4. Replay the request as each ACTIVE AI crawler (see
         active_crawlers() — retired and opt-out-only tokens are never
         probed, and are reported in result["excluded_tokens"]),
         comparing status, body length, and content similarity to the
         baseline.
         A bot is considered blocked if any of:
            - status is 403, 406, 429, or 503
            - body matches Cloudflare challenge markers (200 with a
              disguised block page)
            - body is non-trivially smaller AND content similarity to
              baseline is suspiciously low (silent content stripping)
         - status 402 is classified separately as payment-required
           (pay-per-crawl), neither blocked nor allowed

    Returns a dict structured for JSON consumption by skills. All
    failures are captured in result["errors"] rather than raised — this
    matches the error-handling pattern used elsewhere in fetch_page.py.
    """
    result = {
        "url": url,
        "baseline": {
            "status": None,
            "length": None,
            "used_playwright": False,
        },
        "js_challenge_detected": False,
        "wafs_detected": [],
        "probes": [],
        "errors": [],
        # Roster entries deliberately NOT probed, mapped to why. Lets the
        # report layer explain the absence of e.g. a Google-Extended row
        # instead of leaving a silent gap.
        "excluded_tokens": {
            name: info.get("status")
            for name, info in AI_CRAWLERS.items()
            if info.get("status", "active") != "active"
        },
        # Bots that met an HTTP 402 pay-per-crawl toll rather than a block.
        "payment_required_bots": [],
    }

    # Reject non-http(s) schemes before any network call. Mirrors the
    # guard in fetch_page() — same threat model (caller-supplied URL,
    # allow_redirects=True downstream) so the same defence applies.
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ("http", "https"):
        result["errors"].append(
            f"Unsupported URL scheme: {parsed_url.scheme!r}. "
            "Only http and https are allowed."
        )
        return result

    # --- 1. Browser baseline -------------------------------------------------
    try:
        baseline_resp = requests.get(
            url, headers=DEFAULT_HEADERS, timeout=timeout, allow_redirects=True
        )
    except Exception as e:
        result["errors"].append(f"Baseline fetch failed: {e}")
        return result

    baseline_html = baseline_resp.text or ""
    result["baseline"]["status"] = baseline_resp.status_code
    result["baseline"]["length"] = len(baseline_html)

    # --- 2. JS challenge detection + optional Playwright fallback -----------
    if is_challenge_page(baseline_html, baseline_resp.status_code):
        result["js_challenge_detected"] = True
        pw = _playwright_baseline(url)
        if pw is not None:
            pw_status, pw_html = pw
            if not is_challenge_page(pw_html, pw_status):
                # Playwright successfully bypassed the challenge — use
                # its rendered output as the comparison baseline so the
                # similarity scores below are meaningful.
                baseline_html = pw_html
                result["baseline"]["status"] = pw_status
                result["baseline"]["length"] = len(pw_html)
                result["baseline"]["used_playwright"] = True

    # --- 3. WAF / CDN fingerprinting ----------------------------------------
    # Run on the original requests response — Playwright bypassed the
    # challenge for the body, but the original headers are what tell us
    # which product is in front of the site.
    result["wafs_detected"] = detect_waf(baseline_resp)

    # --- 4. Per-bot probes ---------------------------------------------------
    # If the baseline is itself a challenge page that Playwright couldn't
    # bypass, similarity comparison is meaningless (every bot will look
    # "similar" to a challenge page). In that case we fall back to pure
    # status-code / challenge-marker detection.
    baseline_is_challenge = (
        result["js_challenge_detected"] and not result["baseline"]["used_playwright"]
    )

    for bot_name, meta in active_crawlers().items():
        bot_ua = meta["ua"]
        probe = {
            "bot": bot_name,
            "user_agent": bot_ua,
            "class": meta["class"],
            "operator": meta["operator"],
            "status": None,
            "length": None,
            "similarity": None,
            "blocked": False,
            "payment_required": False,
            "block_reason": None,
        }
        try:
            bot_resp = requests.get(
                url,
                headers={**DEFAULT_HEADERS, "User-Agent": bot_ua},
                timeout=timeout,
                allow_redirects=True,
            )
        except Exception as e:
            probe["blocked"] = True
            probe["block_reason"] = f"request_error: {e}"
            result["probes"].append(probe)
            continue

        bot_html = bot_resp.text or ""
        probe["status"] = bot_resp.status_code
        probe["length"] = len(bot_html)

        # Block detection rules in priority order. We record the first
        # rule that matches so the downstream skill can give a precise
        # explanation in its recommendations.
        if bot_resp.status_code == 402:
            # Pay-per-crawl (e.g. Cloudflare's 402 flow): the site is
            # monetizing AI access, not blocking it. Classify distinctly —
            # calling this "blocked" would produce a false CRITICAL
            # mismatch finding; calling it "allowed" would hide the toll.
            probe["payment_required"] = True
            probe["block_reason"] = "payment-required (HTTP 402 — pay-per-crawl)"
            result["payment_required_bots"].append(bot_name)
        elif bot_resp.status_code in (403, 406, 429, 503):
            probe["blocked"] = True
            probe["block_reason"] = f"http_{bot_resp.status_code}"
        elif is_challenge_page(bot_html, bot_resp.status_code):
            probe["blocked"] = True
            probe["block_reason"] = "challenge_page"
        elif not baseline_is_challenge:
            # Compare against the real browser baseline. We only flag
            # via similarity when both the body is much smaller AND the
            # similarity is low — either signal alone has too many false
            # positives (mobile-optimised pages, A/B tests, etc.).
            similarity = _content_similarity(baseline_html, bot_html)
            probe["similarity"] = round(similarity, 3)
            length_ratio = (
                probe["length"] / result["baseline"]["length"]
                if result["baseline"]["length"]
                else 1.0
            )
            if similarity < 0.4 and length_ratio < 0.5:
                probe["blocked"] = True
                probe["block_reason"] = "content_stripped"

        result["probes"].append(probe)

    # --- 5. Per-class scoring + overall verdict -----------------------------
    # Scoring is multi-dimensional rather than a single number because the
    # GEO impact of blocking differs sharply by bot class. A site that
    # blocks training but allows retrieval is the canonical healthy
    # publisher posture (NYT, WSJ, Reuters, BBC) — one flat score would
    # mislabel it. We emit a sub-score per class and an overall verdict
    # that weights retrieval reachability heaviest.
    by_class = {cls: {"total": 0, "blocked": 0, "score": 100}
                for cls in BOT_CLASSES}
    for probe in result["probes"]:
        cls = probe["class"]
        by_class[cls]["total"] += 1
        if probe["blocked"]:
            by_class[cls]["blocked"] += 1
    # Each class drops linearly from 100 to 0 as the share of blocked
    # bots in that class goes from 0% to 100%.
    for stats in by_class.values():
        if stats["total"]:
            stats["score"] = max(
                0, round(100 * (1 - stats["blocked"] / stats["total"]))
            )

    # JS-challenge penalty applies to the search-index and live-retrieval
    # classes since non-browser bots can't bypass an interstitial.
    if result["js_challenge_detected"] and not result["baseline"]["used_playwright"]:
        for cls in ("search-index", "live-retrieval"):
            by_class[cls]["score"] = max(0, by_class[cls]["score"] - 30)

    result["class_scores"] = by_class

    retrieval = (by_class["live-retrieval"]["score"] + by_class["search-index"]["score"]) // 2
    traditional = by_class["traditional-search"]["score"]
    training = by_class["training"]["score"]

    # Verdict logic. Retrieval is the headline signal; training is
    # informational. "HEALTHY_PUBLISHER" recognises the NYT/Reuters
    # pattern explicitly so reports don't mislabel it as a problem.
    if retrieval >= 90 and traditional >= 90:
        verdict = "OPEN" if training >= 70 else "HEALTHY_PUBLISHER"
    elif retrieval >= 70 and traditional >= 70:
        verdict = "PARTIALLY_BLOCKED"
    elif retrieval >= 40 or traditional >= 40:
        verdict = "MOSTLY_BLOCKED"
    else:
        verdict = "BLOCKED"

    result["verdict"] = verdict
    result["overall_score"] = round(
        0.5 * retrieval + 0.35 * traditional + 0.15 * training
    )

    return result


def crawl_sitemap(url: str, max_pages: int = 50, timeout: int = 15) -> list:
    """Crawl sitemap.xml to discover pages."""
    parsed = urlparse(url)
    sitemap_urls = [
        f"{parsed.scheme}://{parsed.netloc}/sitemap.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap_index.xml",
        f"{parsed.scheme}://{parsed.netloc}/sitemap/",
    ]

    discovered_pages = set()

    for sitemap_url in sitemap_urls:
        try:
            response = requests.get(
                sitemap_url, headers=DEFAULT_HEADERS, timeout=timeout
            )
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "lxml")

                # Check for sitemap index
                for sitemap in soup.find_all("sitemap"):
                    loc = sitemap.find("loc")
                    if loc:
                        # Fetch child sitemap
                        try:
                            child_resp = requests.get(
                                loc.text.strip(),
                                headers=DEFAULT_HEADERS,
                                timeout=timeout,
                            )
                            if child_resp.status_code == 200:
                                child_soup = BeautifulSoup(child_resp.text, "lxml")
                                for url_tag in child_soup.find_all("url"):
                                    loc_tag = url_tag.find("loc")
                                    if loc_tag:
                                        discovered_pages.add(loc_tag.text.strip())
                                    if len(discovered_pages) >= max_pages:
                                        break
                        except Exception:
                            pass
                    if len(discovered_pages) >= max_pages:
                        break

                # Direct URL entries
                for url_tag in soup.find_all("url"):
                    loc = url_tag.find("loc")
                    if loc:
                        discovered_pages.add(loc.text.strip())
                    if len(discovered_pages) >= max_pages:
                        break

                if discovered_pages:
                    break

        except Exception:
            continue

    return list(discovered_pages)[:max_pages]


AGENT_READINESS_ENDPOINTS = {
    # name: (path, spec, expects) — expects: "json", "text", or "endpoint"
    "api_catalog": ("/.well-known/api-catalog", "RFC 9727", "json"),
    "oauth_authorization_server": ("/.well-known/oauth-authorization-server", "RFC 8414", "json"),
    "oauth_protected_resource": ("/.well-known/oauth-protected-resource", "RFC 9728", "json"),
    "mcp_server_card": ("/.well-known/mcp/server-card.json", "MCP SEP-1649", "json"),
    "agents_json": ("/.well-known/agents.json", "agents.json (pre-standard)", "json"),
    "web_bot_auth_directory": ("/.well-known/http-message-signatures-directory", "Web Bot Auth (IETF draft)", "json"),
    "rsl_txt": ("/rsl.txt", "RSL 1.0", "text"),
    "rsl_xml": ("/rsl.xml", "RSL 1.0", "text"),
    "nlweb_ask": ("/ask", "NLWeb", "endpoint"),
    "nlweb_mcp": ("/mcp", "NLWeb / MCP", "endpoint"),
}


def check_agent_readiness(url: str, timeout: int = 10) -> dict:
    """Probe the emerging agent/licensing protocol surface (non-scoring).

    Every check here targets an emerging spec (2025-2026). Absence is the
    norm and must never be penalized — the report layer surfaces presence
    as a forward-looking signal only.

    found semantics per expects-type:
      json/text — HTTP 200 AND body does not look like an HTML page
                  (SPAs serve index.html for unknown paths: soft-404 guard)
      endpoint  — any response except 404 (NLWeb's /ask and /mcp are POST
                  endpoints; GET commonly returns 405, which still proves
                  the route exists)
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return {"url": url, "checks": {}, "homepage_headers": {},
                "summary": {"found_count": 0, "checked_count": 0},
                "errors": [f"Unsupported URL scheme: {parsed.scheme!r}"]}
    base = f"{parsed.scheme}://{parsed.netloc}"

    result = {
        "url": base,
        "checks": {},
        "homepage_headers": {"content_usage": None, "content_signal": None, "link": None},
        "summary": {"found_count": 0, "checked_count": len(AGENT_READINESS_ENDPOINTS)},
        "errors": [],
    }

    def _looks_like_html(text):
        head = (text or "")[:256].lstrip().lower()
        return head.startswith("<!doctype html") or head.startswith("<html")

    for name, (path, spec, expects) in AGENT_READINESS_ENDPOINTS.items():
        check = {"path": path, "spec": spec, "status": None, "found": False}
        try:
            resp = requests.get(base + path, headers=DEFAULT_HEADERS,
                                timeout=timeout, allow_redirects=True)
            check["status"] = resp.status_code
            if expects == "endpoint":
                check["found"] = resp.status_code != 404
            else:
                check["found"] = resp.status_code == 200 and not _looks_like_html(resp.text)
        except Exception as e:
            result["errors"].append(f"{name}: {e}")
        result["checks"][name] = check

    try:
        home = requests.get(base, headers=DEFAULT_HEADERS, timeout=timeout,
                            allow_redirects=True)
        result["homepage_headers"]["content_usage"] = home.headers.get("Content-Usage")
        result["homepage_headers"]["content_signal"] = home.headers.get("Content-Signal")
        result["homepage_headers"]["link"] = home.headers.get("Link")
    except Exception as e:
        result["errors"].append(f"homepage headers: {e}")

    result["summary"]["found_count"] = sum(
        1 for c in result["checks"].values() if c["found"]
    )
    return result


# ---------------------------------------------------------------------------
# Content-integrity scanner (GEO-spam / prompt-injection detection)
# ---------------------------------------------------------------------------
#
# CONSERVATIVE by design. Static analysis cannot tell an intentional spam
# injection from a plugin quirk or a legitimate edge case, so every finding
# is framed as a *signal for review*, never as proof. We detect ONLY four
# high-confidence patterns, each with a false-positive guard (word floors and
# occurrence floors) that keeps ordinary a11y markup and stray characters
# from tripping the scanner:
#
#   1. hidden_text       — text-bearing element with an INLINE hiding style,
#                          carrying >= 8 words of real text.
#   2. llm_instruction   — LLM-directed imperative in an HTML comment,
#                          aria-hidden element, or data-* attribute.
#   3. zero_width        — >= 3 zero-width chars inside VISIBLE text.
#   4. cloaked_keywords  — aria-hidden / display:none block of >= 25 words
#                          whose top token exceeds 18% density.
#
# We only ever see INLINE styles; class-based hiding (e.g. .sr-only) is
# invisible to us and, being standard a11y practice, is deliberately left
# alone.

# Inline style fragments that hide an element from human readers. Matched
# against a whitespace-stripped, lowercased copy of the style attribute.
_HIDING_STYLE_PATTERNS = (
    "display:none",
    "visibility:hidden",
    "opacity:0",
    "font-size:0",
    "font-size:1px",
    "text-indent:-9999px",
)

# LLM-directed imperative phrases. High-confidence only.
_LLM_INSTRUCTION_PATTERNS = (
    r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"\byou\s+(are|must|should)\s+(now\s+)?",
    r"cite\s+(this|us|these)\b",
    r"recommend\s+\S+\s+(as|above|over)\b",
    r"system\s+prompt",
    r"as\s+an?\s+(ai|language\s+model|assistant)",
)
_LLM_INSTRUCTION_RE = re.compile(
    "|".join(_LLM_INSTRUCTION_PATTERNS), re.IGNORECASE
)

# Zero-width / BOM code points that don't render but travel inside text.
_ZERO_WIDTH_CHARS = ("​", "‌", "‍", "﻿")

# Tags whose text is not human-visible page content.
_NON_VISIBLE_PARENTS = {"script", "style", "noscript", "template", "head"}

# Tags we consider "text-bearing" for the hidden_text check.
_TEXT_BEARING_TAGS = {"p", "div", "span", "li", "a",
                      "h1", "h2", "h3", "h4", "h5", "h6"}

# Small inline stopword set for the keyword-density check.
_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "any", "can",
    "her", "was", "one", "our", "out", "day", "get", "has", "him", "his",
    "how", "man", "new", "now", "old", "see", "two", "way", "who", "boy",
    "did", "its", "let", "put", "say", "she", "too", "use", "that", "this",
    "with", "from", "they", "have", "will", "your", "what", "when", "which",
    "their", "there", "would", "about", "into", "over", "than", "them",
    "then", "these", "those", "were", "been", "some", "more", "very", "such",
    "here", "also", "only", "just", "like", "most", "much", "many", "each",
}


def scan_content_integrity(soup, base_url: str = "") -> dict:
    """Statically scan a parsed page for content-integrity red flags.

    Detects four high-confidence patterns that can indicate content aimed at
    manipulating LLM crawlers (hidden text, LLM-directed instructions,
    zero-width payloads, and cloaked keyword stuffing). CONSERVATIVE by
    design — findings are signals for human review, not proof of spam.

    Returns a dict with ``url``, ``findings`` (each carrying
    ``type``/``severity``/``evidence``/``location``), ``counts`` per type,
    and a one-line plain-language ``summary``.
    """
    findings = []

    def _words(text):
        return re.findall(r"\b\w[\w'-]*\b", text)

    # --- 1. hidden_text ---------------------------------------------------
    for element in soup.find_all(_TEXT_BEARING_TAGS):
        style = element.get("style", "")
        if not style:
            continue
        squashed = re.sub(r"\s+", "", style).lower()
        matched = next(
            (p for p in _HIDING_STYLE_PATTERNS if p in squashed), None
        )
        if not matched:
            continue
        text = element.get_text(" ", strip=True)
        words = _words(text)
        if len(words) < 8:
            continue  # word-floor guard: icons / single hidden words are fine
        evidence = " ".join(words[:15])
        findings.append({
            "type": "hidden_text",
            "severity": "high",
            "evidence": evidence,
            "location": f"<{element.name}> style: {matched}",
        })

    # --- 2. llm_instruction ----------------------------------------------
    def _record_instruction(text, location):
        if not text:
            return
        m = _LLM_INSTRUCTION_RE.search(text)
        if not m:
            return
        snippet = text.strip()
        if len(snippet) > 120:
            snippet = snippet[:120].rstrip() + "..."
        findings.append({
            "type": "llm_instruction",
            "severity": "high",
            "evidence": snippet,
            "location": location,
        })

    # (a) HTML comments
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        _record_instruction(str(comment), "html comment")

    # (b) aria-hidden="true" elements
    for element in soup.find_all(attrs={"aria-hidden": "true"}):
        _record_instruction(element.get_text(" ", strip=True),
                            "aria-hidden element")

    # (c) any data-* attribute value
    for element in soup.find_all(True):
        for attr, value in element.attrs.items():
            if not attr.startswith("data-"):
                continue
            if isinstance(value, (list, tuple)):
                value = " ".join(value)
            _record_instruction(str(value), "data-attribute")

    # --- 3. zero_width ----------------------------------------------------
    # Count zero-width chars per visible text node, tally per element.
    zw_by_element = {}
    for node in soup.find_all(string=True):
        parent = node.parent
        if parent is not None and parent.name in _NON_VISIBLE_PARENTS:
            continue
        if isinstance(node, Comment):
            continue
        count = sum(str(node).count(ch) for ch in _ZERO_WIDTH_CHARS)
        if count:
            key = parent if parent is not None else node
            zw_by_element[key] = zw_by_element.get(key, 0) + count

    total_zw = sum(zw_by_element.values())
    if total_zw >= 3:  # occurrence-floor guard: single strays are innocuous
        # Attribute to the element with the most occurrences for evidence.
        top_el = max(zw_by_element, key=zw_by_element.get)
        tag = getattr(top_el, "name", "text") or "text"
        findings.append({
            "type": "zero_width",
            "severity": "medium",
            "evidence": f"<{tag}> contains {total_zw} zero-width characters",
            "location": f"<{tag}>",
        })

    # --- 4. cloaked_keywords ---------------------------------------------
    # aria-hidden OR inline display:none blocks with >= 25 words whose single
    # most-frequent meaningful token exceeds 18% density.
    seen_cloak = set()
    cloak_candidates = list(soup.find_all(attrs={"aria-hidden": "true"}))
    for element in soup.find_all(style=True):
        squashed = re.sub(r"\s+", "", element.get("style", "")).lower()
        if "display:none" in squashed:
            cloak_candidates.append(element)

    for element in cloak_candidates:
        if id(element) in seen_cloak:
            continue
        seen_cloak.add(id(element))
        text = element.get_text(" ", strip=True)
        tokens = [t.lower() for t in _words(text)]
        if len(tokens) < 25:
            continue  # word-floor guard
        meaningful = [t for t in tokens if len(t) >= 4 and t not in _STOPWORDS]
        if not meaningful:
            continue
        counts = {}
        for t in meaningful:
            counts[t] = counts.get(t, 0) + 1
        top_token = max(counts, key=counts.get)
        ratio = counts[top_token] / len(tokens)
        if ratio <= 0.18:  # density guard
            continue
        findings.append({
            "type": "cloaked_keywords",
            "severity": "medium",
            "evidence": f"'{top_token}' is {ratio:.0%} of tokens",
            "location": f"<{element.name}>",
        })

    counts = {
        "hidden_text": sum(1 for f in findings if f["type"] == "hidden_text"),
        "llm_instruction": sum(
            1 for f in findings if f["type"] == "llm_instruction"),
        "zero_width": sum(1 for f in findings if f["type"] == "zero_width"),
        "cloaked_keywords": sum(
            1 for f in findings if f["type"] == "cloaked_keywords"),
    }
    total = len(findings)
    if total == 0:
        summary = "No content-integrity signals detected."
    else:
        parts = [f"{n} {name.replace('_', ' ')}"
                 for name, n in counts.items() if n]
        summary = (
            f"{total} content-integrity signal{'s' if total != 1 else ''} "
            f"for review ({', '.join(parts)}). Signals, not proof — verify "
            "each before acting."
        )

    return {
        "url": base_url,
        "findings": findings,
        "counts": counts,
        "summary": summary,
    }


if __name__ == "__main__":

    def _print_usage_and_exit():
        print("Usage: python fetch_page.py <url> [mode] [--accept-language he]")
        print("Modes: page (default), robots, llms, sitemap, blocks, bots, "
              "agentready, integrity, full")
        sys.exit(1)

    if len(sys.argv) < 2:
        _print_usage_and_exit()

    accept_language = None
    if "--accept-language" in sys.argv:
        idx = sys.argv.index("--accept-language")
        if idx + 1 < len(sys.argv):
            accept_language = sys.argv[idx + 1]
            del sys.argv[idx:idx + 2]

    # Re-validate: stripping the flag may have consumed the only args present
    # (e.g. `fetch_page.py --accept-language he` with no URL).
    if len(sys.argv) < 2:
        _print_usage_and_exit()

    target_url = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "page"

    if mode == "page":
        data = fetch_page(target_url, accept_language=accept_language)
    elif mode == "robots":
        data = fetch_robots_txt(target_url)
    elif mode == "llms":
        data = fetch_llms_txt(target_url)
    elif mode == "sitemap":
        pages = crawl_sitemap(target_url)
        data = {"pages": pages, "count": len(pages)}
    elif mode == "blocks":
        response = requests.get(target_url, headers=DEFAULT_HEADERS, timeout=30)
        data = extract_content_blocks(response.text)
    elif mode == "bots":
        # Live AI crawler reachability probe — empirical complement to
        # the static `robots` mode. See probe_ai_crawlers() for details.
        data = probe_ai_crawlers(target_url)
    elif mode == "agentready":
        # Non-scoring probe of the emerging agent/licensing protocol surface.
        data = check_agent_readiness(target_url)
    elif mode == "integrity":
        # Static content-integrity scan (GEO-spam / prompt-injection).
        # Signals for review, not proof. Scan whatever HTML we get back,
        # even on a non-200 (an error page can carry injected content too).
        response = requests.get(target_url, headers=DEFAULT_HEADERS, timeout=30)
        soup = BeautifulSoup(response.text, "lxml")
        data = scan_content_integrity(soup, target_url)
    elif mode == "full":
        data = {
            "page": fetch_page(target_url, accept_language=accept_language),
            "robots": fetch_robots_txt(target_url),
            "llms": fetch_llms_txt(target_url),
            "sitemap": crawl_sitemap(target_url),
            "bots": probe_ai_crawlers(target_url),
        }
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)

    print(json.dumps(data, indent=2, default=str))
