---
name: geo-crawlers
description: AI crawler access analysis. Checks robots.txt, meta tags, and HTTP headers to determine which AI crawlers can access the site. Provides a complete access map and recommendations for maximizing AI visibility while maintaining appropriate control.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebFetch
  - Write
---

# AI Crawler Access Analysis Skill

## Purpose

This skill analyzes a website's accessibility to AI crawlers -- the bots that AI companies use to discover, index, and train on web content. If AI crawlers are blocked, the site's content cannot appear in AI-generated responses regardless of its quality. Crawler access is the foundational technical requirement for GEO.

## Key Insight

As of early 2026, many websites inadvertently block AI crawlers through overly aggressive robots.txt rules, inherited from legacy SEO configurations. An Originality.ai 2025 study found that over 35% of the top 1,000 websites block at least one major AI crawler, and 5-10% block all AI crawlers. Blocking AI crawlers is the single fastest way to become invisible in AI-generated search results.

---

## Complete AI Crawler Reference

### Tier 1: Critical for AI Search Visibility (RECOMMEND: ALLOW)

These crawlers power the AI search products where users actively look for answers. Blocking them directly reduces your visibility in AI-generated responses.

#### GPTBot
- **Operator:** OpenAI
- **User-Agent:** `GPTBot`
- **Full User-Agent String:** `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; GPTBot/1.2; +https://openai.com/gptbot)`
- **Purpose:** Fetches content for ChatGPT's web browsing, plugins, and search features. Content accessed by GPTBot may be used to improve OpenAI models.
- **Impact of Blocking:** Content will NOT appear in ChatGPT Search results or be accessible when users ask ChatGPT to browse the web. This is the highest-impact AI crawler to allow.
- **Recommendation:** **ALLOW** -- ChatGPT has 300M+ weekly active users as of 2025. Blocking GPTBot removes your content from one of the largest AI search surfaces.

#### OAI-SearchBot
- **Operator:** OpenAI
- **User-Agent:** `OAI-SearchBot`
- **Full User-Agent String:** `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; OAI-SearchBot/1.0; +https://docs.openai.com/bots/overview)`
- **Purpose:** Specifically powers ChatGPT's search feature. Unlike GPTBot, content accessed by OAI-SearchBot is NOT used for model training -- only for live search results.
- **Impact of Blocking:** Content will not appear in ChatGPT's search results even if GPTBot is allowed.
- **Recommendation:** **ALLOW** -- This is a search-only crawler with no training implications. There is no strategic reason to block it.

#### ChatGPT-User
- **Operator:** OpenAI
- **User-Agent:** `ChatGPT-User`
- **Full User-Agent String:** `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; ChatGPT-User/1.0; +https://openai.com/bot)`
- **Purpose:** Used when a ChatGPT user explicitly asks the model to visit a specific URL. Acts like a browser agent on behalf of the user.
- **Impact of Blocking:** ChatGPT cannot visit your pages when users ask it to read or summarize them. This prevents direct user-initiated traffic.
- **Recommendation:** **ALLOW** -- Blocking this bot prevents users who are actively trying to engage with your content from accessing it through ChatGPT.

#### ClaudeBot
- **Operator:** Anthropic
- **User-Agent:** `ClaudeBot`
- **Full User-Agent String:** `ClaudeBot/1.0; +https://www.anthropic.com/claude-bot`
- **Purpose:** Fetches web content for Claude's features including web search, citations, and analysis tools.
- **Impact of Blocking:** Content will not be accessible to Claude for web search or when users ask Claude to analyze specific URLs.
- **Recommendation:** **ALLOW** -- Claude is a major AI assistant with growing market share. Blocking ClaudeBot reduces your AI search footprint.

#### PerplexityBot
- **Operator:** Perplexity AI
- **User-Agent:** `PerplexityBot`
- **Full User-Agent String:** `Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; PerplexityBot/1.0; +https://perplexity.ai/perplexitybot)`
- **Purpose:** Powers Perplexity's AI search engine, which provides sourced answers with direct citations and links back to source pages.
- **Impact of Blocking:** Content will not appear in Perplexity search results. Perplexity is one of the best referral traffic sources among AI search products because it always displays source links.
- **Recommendation:** **ALLOW** -- Perplexity drives actual referral traffic and always attributes sources. High-value AI crawler for publishers and businesses.

---

### Tier 2: Important for Broader AI Ecosystem (RECOMMEND: ALLOW)

These crawlers serve large AI platforms or search ecosystems. Allowing them increases your content's reach.

#### Google-Extended
- **Operator:** Google
- **User-Agent:** `Google-Extended`
- **Purpose:** Controls whether Google uses your content for Gemini model training and AI Overviews improvement. **CRITICAL NOTE:** Blocking Google-Extended does NOT affect your Google Search rankings or your appearance in Google Search results. That is controlled by the standard Googlebot.
- **Impact of Blocking:** Content may not be used for Gemini training or to improve AI Overviews. However, your content can still appear in AI Overviews based on standard search indexing.
- **Recommendation:** **ALLOW** -- Blocking provides minimal content protection upside while reducing your presence in Google's AI features. Since it does not affect standard search ranking, the only reason to block is philosophical objection to training data usage.

#### GoogleOther
- **Operator:** Google
- **User-Agent:** `GoogleOther`
- **Purpose:** Used by Google for various non-search-ranking purposes including research, one-off crawls, and AI-related data collection.
- **Impact of Blocking:** Minimal impact on search rankings. May reduce presence in Google's AI research and experimental features.
- **Recommendation:** **LEGACY / LOW-VALUE** -- No longer part of the recommended configuration. Harmless if already allowed; not worth adding.

#### Applebot-Extended
- **Operator:** Apple
- **User-Agent:** `Applebot-Extended`
- **Purpose:** Used by Apple to train and improve Apple Intelligence features, Siri, and Apple's AI products. Separate from standard Applebot (which powers Siri search and Spotlight Suggestions).
- **Impact of Blocking:** Content may not be used in Apple Intelligence features. Standard Siri and Spotlight functionality is unaffected (controlled by Applebot).
- **Recommendation:** **ALLOW** -- Apple Intelligence is integrated into all Apple devices (2B+ active devices). Presence in Apple's AI features has growing strategic value.

#### Amazonbot
- **Operator:** Amazon
- **User-Agent:** `Amazonbot`
- **Full User-Agent String:** `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/600.2.5 (KHTML, like Gecko) Version/8.0.2 Safari/600.2.5 (compatible; Amazonbot/0.1; +https://developer.amazon.com/support/amazonbot)`
- **Purpose:** Indexes content for Alexa answers and Amazon's AI features.
- **Impact of Blocking:** Content will not appear in Alexa voice responses or Amazon's AI-powered search features.
- **Recommendation:** **ALLOW** -- Relevant for voice search optimization. Lower priority than Tier 1 crawlers but no downside to allowing.

#### FacebookBot
- **Operator:** Meta
- **User-Agent:** `FacebookBot`
- **Purpose:** Legacy Meta token. Meta's current AI fetcher is `Meta-ExternalAgent`, which is what belongs in a recommended configuration.
- **Impact of Blocking:** None — Meta AI access is governed by `Meta-ExternalAgent`. Link previews are handled by a different crawler and are unaffected.
- **Recommendation:** **RETIRED token — see "Retired tokens" below.** Recommend `Meta-ExternalAgent` instead.

---

### Tier 3: Training-Only Crawlers (ALLOW or BLOCK Based on Strategy)

These crawlers are primarily used for AI model training rather than live search features. Blocking them does not affect AI search visibility.

#### CCBot
- **Operator:** Common Crawl (nonprofit)
- **User-Agent:** `CCBot`
- **Full User-Agent String:** `CCBot/2.0 (https://commoncrawl.org/faq/)`
- **Purpose:** Builds the Common Crawl dataset, which is used as training data by many AI companies (Google, Meta, Stability AI, and others).
- **Impact of Blocking:** Content will not appear in future Common Crawl datasets. Does NOT affect any live AI search product.
- **Recommendation:** **CONTEXT-DEPENDENT** -- Allow if you want maximum long-term AI training presence. Block if you want to control training data usage. No impact on search visibility.

#### anthropic-ai
- **Operator:** Anthropic
- **User-Agent:** `anthropic-ai`
- **Purpose:** Legacy token formerly used by Anthropic for training crawls. Anthropic's current fleet is ClaudeBot, Claude-SearchBot, and Claude-User.
- **Impact of Blocking:** None — no crawler ships this user-agent any more.
- **Recommendation:** **RETIRED token — see "Retired tokens" below.** Do not recommend allowing or blocking it. If a site's robots.txt still names it, report it as a cleanup item only.

#### Bytespider
- **Operator:** ByteDance
- **User-Agent:** `Bytespider`
- **Purpose:** Used by ByteDance for various AI products including TikTok's AI features and Doubao (their ChatGPT competitor in China).
- **Impact of Blocking:** Content will not be used for ByteDance AI products. Minimal impact for Western-market businesses.
- **Recommendation:** **BLOCK** for most Western businesses (aggressive crawling behavior reported, minimal search visibility benefit). **ALLOW** if targeting Chinese/Asian markets.

#### cohere-ai
- **Operator:** Cohere
- **User-Agent:** `cohere-ai`
- **Purpose:** Used by Cohere for model training. Cohere powers enterprise AI solutions and the Coral chat product.
- **Impact of Blocking:** Content will not be used for Cohere model training. Minimal direct consumer-facing impact.
- **Recommendation:** **CONTEXT-DEPENDENT** -- Low priority. Allow or block based on general training data stance.

---

## Recommendation Matrix Summary

| Crawler | Tier | Recommendation | Reason |
|---|---|---|---|
| GPTBot | 1 | **ALLOW** | Powers ChatGPT Search (300M+ users) |
| OAI-SearchBot | 1 | **ALLOW** | Search-only, no training use |
| ChatGPT-User | 1 | **ALLOW** | User-initiated browsing |
| ClaudeBot | 1 | **ALLOW** | Claude web search and analysis |
| PerplexityBot | 1 | **ALLOW** | Best referral traffic AI search |
| Google-Extended | 2 | **ALLOW** | Gemini features; no search rank impact |
| GoogleOther | 2 | Legacy / low-value | Dropped from the recommended config |
| Applebot-Extended | 2 | **ALLOW** | Apple Intelligence (2B+ devices) |
| Amazonbot | 2 | **ALLOW** | Alexa and Amazon AI |
| FacebookBot | 2 | RETIRED token — see "Retired tokens" below | Superseded by Meta-ExternalAgent |
| CCBot | 3 | Context | Training data only |
| anthropic-ai | 3 | RETIRED token — see "Retired tokens" below | No crawler ships this UA; cleanup item only |
| Bytespider | 3 | **BLOCK** | Aggressive crawler, low benefit |
| cohere-ai | 3 | Context | Training data only |

### Maximum AI Visibility Configuration (robots.txt)

For sites wanting maximum AI search visibility:

```
# AI Crawlers - ALLOWED for AI search visibility
User-agent: GPTBot
Allow: /

User-agent: OAI-SearchBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: Claude-SearchBot
Allow: /

User-agent: Claude-User
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Perplexity-User
Allow: /

User-agent: MistralAI-User
Allow: /

User-agent: DuckAssistBot
Allow: /

User-agent: Amazonbot
Allow: /

User-agent: Meta-ExternalAgent
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: Applebot-Extended
Allow: /

# AI Crawlers - BLOCKED (aggressive/low value)
User-agent: Bytespider
Disallow: /

User-agent: CCBot
Disallow: /
```

Gone from previous versions of this recommendation: anthropic-ai (retired token), GoogleOther and FacebookBot (legacy/low-value).

### Retired tokens — flag, don't recommend

`anthropic-ai`, `claude-web`, and `FacebookBot` are retired legacy tokens. Never include them in recommended configurations. When a site's robots.txt still carries rules for them (surfaced in the `stale_tokens` field of `fetch_page.py <url> robots` output), report it as an informational cleanup item: the rules are dead weight and signal an unmaintained robots.txt.

### Opt-out tokens are not crawlers

`Google-Extended` and `Applebot-Extended` never fetch pages — they are robots.txt signals the operators honour separately. They belong in robots.txt recommendations (above) but have no meaningful live-probe result; the probe excludes them (see `excluded_tokens`).

### Fetchers that ignore robots.txt

`Google-Agent` (user-triggered agent fetches) generally does not consult robots.txt. Its declared status in a robots.txt table is close to meaningless — the live probe (`geo-botaccess`) is the only signal that matters for it. Never recommend a robots.txt rule as a way to control it; WAF-level rules are the real lever.

---

## Analysis Procedure

### Step 0: Run the live reachability probe (ground truth)

**Always run this first.** robots.txt declares *intent*; the live probe measures what actually happens. A site can have a fully permissive robots.txt while a WAF/CDN rule silently 403s every AI crawler.

```bash
python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/fetch_page.py" <url> bots
```

Use the resulting `probes[]` array as the per-bot status in the output table, the `wafs_detected` array to surface any WAF/CDN in front of the site, and the `verdict` field (`OPEN` / `HEALTHY_PUBLISHER` / `PARTIALLY_BLOCKED` / `MOSTLY_BLOCKED` / `BLOCKED`) as the overall posture. See `geo-botaccess` for the full output schema. If the probe fails (network error), fall back to Step 1 alone and note the degradation.

### Step 1: Fetch and parse the declared policy

Use the parser bundled with this repo — **do not hand-roll robots.txt parsing**. The packaged parser correctly handles `User-agent: *` wildcard inheritance, including the common "fully permissive" case (`User-agent: *` + empty `Disallow:`).

```bash
python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/fetch_page.py" <url> robots
```

The `ai_crawler_status` field returns one of these per crawler — interpret each as written, including the wildcard case:

| Status | Meaning |
|---|---|
| `ALLOWED` | Bot has its own block, no `Disallow: /` |
| `BLOCKED` | Bot has its own block with `Disallow: /` |
| `PARTIALLY_BLOCKED` | Bot has its own block with specific path disallows but not root |
| `ALLOWED_BY_DEFAULT` | Bot is not named; wildcard `User-agent: *` is present and does not block root. **Permissive — render as "Allowed (via wildcard)" in the table, not "Unknown" or "Unverified".** |
| `BLOCKED_BY_WILDCARD` | Bot is not named; wildcard has `Disallow: /` |
| `NOT_MENTIONED` | Neither bot-specific nor wildcard rules present |
| `NO_ROBOTS_TXT` | 404 — bot is implicitly permitted |

Also note any `Crawl-delay` directives (may slow AI crawler access) and `Sitemap` references (AI crawlers use these for discovery — both surface as `sitemaps[]` in the JSON output).

### Step 2: Check Meta Robots Tags

1. For a sample of 5-10 key pages, fetch the HTML and check for:
   - `<meta name="robots" content="noindex">` -- blocks all bots
   - `<meta name="robots" content="nofollow">` -- prevents link following
   - `<meta name="robots" content="noai">` -- emerging tag to block AI use
   - `<meta name="robots" content="noimageai">` -- blocks AI image training
   - Bot-specific meta tags: `<meta name="GPTBot" content="noindex">`
2. Record any page-level overrides of the robots.txt directives.

### Step 3: Check HTTP Headers

1. For the same sample pages, check response headers for:
   - `X-Robots-Tag: noindex` -- HTTP header equivalent of meta noindex
   - `X-Robots-Tag: noai` -- HTTP header to block AI use
   - `X-Robots-Tag: noimageai` -- blocks AI image training
   - Bot-specific headers: `X-Robots-Tag: GPTBot: noindex`
2. Note that HTTP headers override meta tags and apply to non-HTML resources too.

### Step 4: Check for AI-Specific Files

1. Check for `/llms.txt` (emerging standard for AI crawler guidance).
2. Check for `/.well-known/ai-plugin.json` (OpenAI plugin manifest).
3. Check for `/ai.txt` (proposed standard, similar to ads.txt for AI).
4. Record presence/absence and quality of each file.

### Step 5: Assess JavaScript Rendering Requirements

1. Check if the site is a Single Page Application (SPA) or heavily JavaScript-rendered.
2. AI crawlers vary in their JavaScript rendering capabilities:
   - GPTBot: Limited JS rendering
   - ClaudeBot: Limited JS rendering
   - PerplexityBot: Limited JS rendering
   - Googlebot: Full JS rendering (but Google-Extended inherits this)
3. If critical content requires JS rendering, flag this as a potential issue.
4. Check for Server-Side Rendering (SSR) or Static Site Generation (SSG) as mitigations.

### Step 6: Parse Content Signals

Using the already-fetched robots.txt from Step 1, scan for `Content-Signal:` directives (IETF draft `draft-romm-aipref-contentsignals`).

1. Scan every line for a line starting with `Content-Signal:` (case-insensitive).
2. If found:
   - Parse all key=value pairs (split on `,` then on `=`).
   - Validate keys against the known set: `ai-train`, `search`, `ai-personalization`, `ai-retrieval`, `ai-input`. (`ai-input` is used in production by cloudflare.com and appears alongside the IETF draft's keys; keep both until the spec settles.)
   - Validate values: only `yes` and `no` are valid.
   - Flag any unknown keys or invalid values as a warning — the spec is still an IETF draft.
   - Record the result as **Pass** and surface parsed values with plain-English meaning.
3. If absent: record as **Recommendation** — the site has not declared AI usage preferences.

No additional HTTP request is needed. robots.txt is already fetched in Step 1.

---

## Output Format

Generate a file called `GEO-CRAWLER-ACCESS.md`:

```markdown
# AI Crawler Access Report: [Domain]

**Analysis Date:** [Date]
**Domain:** [Domain]
**robots.txt Status:** [Found/Not Found/Error]

---

## Crawler Access Summary

| Crawler | Operator | Tier | Status | Impact |
|---|---|---|---|---|
| GPTBot | OpenAI | 1 | [Allowed/Blocked/Not Mentioned] | [Impact description] |
| OAI-SearchBot | OpenAI | 1 | [Status] | [Impact] |
| ChatGPT-User | OpenAI | 1 | [Status] | [Impact] |
| ClaudeBot | Anthropic | 1 | [Status] | [Impact] |
| PerplexityBot | Perplexity | 1 | [Status] | [Impact] |
| Google-Extended | Google | 2 | [Status] | [Impact] |
| GoogleOther | Google | 2 | [Status] | [Impact] |
| Applebot-Extended | Apple | 2 | [Status] | [Impact] |
| Amazonbot | Amazon | 2 | [Status] | [Impact] |
| Meta-ExternalAgent | Meta | 2 | [Status] | [Impact] |
| CCBot | Common Crawl | 3 | [Status] | [Impact] |
| Bytespider | ByteDance | 3 | [Status] | [Impact] |
| cohere-ai | Cohere | 3 | [Status] | [Impact] |

**Retired tokens still present:** [list any tokens from the `stale_tokens` field — cleanup item, not an access status. Write "None" if the field is empty.]

## Crawler Access Score: [overall_score]/100 (measured — live probe)

**Per-class:** Live-retrieval [X] · Search-index [X] · Traditional-search [X] · Training [X]
**Verdict:** [OPEN / HEALTHY_PUBLISHER / PARTIALLY_BLOCKED / MOSTLY_BLOCKED / BLOCKED]

<!-- Numbers come from the Step 0 probe's `overall_score` / `class_scores` / `verdict`.
     Do not compute a score from the tier counts in this skill — see
     "Crawler access score — use the measured one" below. -->

---

## Critical Issues

[List any Tier 1 crawlers that are blocked]

## Recommendations

### Immediate Actions
[Specific robots.txt changes needed]

### robots.txt Recommendation
```
[Complete recommended robots.txt content for AI crawlers]
```

### Additional Technical Findings
- **Meta Robots Tags:** [Findings]
- **X-Robots-Tag Headers:** [Findings]
- **JavaScript Rendering:** [Assessment]
- **llms.txt:** [Present/Absent]
- **Sitemap Accessibility:** [Assessment]

### Content Signals (IETF Draft)

**Status:** Present / Absent

<!-- If present: -->
| Signal Key | Value | Meaning |
|---|---|---|
| ai-train | no | Opted out of AI model training |
| search | yes | Permits use in AI-powered search results |

<!-- If absent: -->
**Recommendation:** Add a `Content-Signal:` directive to robots.txt to declare AI usage preferences explicitly. Example:

`Content-Signal: ai-train=no, search=yes, ai-retrieval=yes`

See https://contentsignals.org/ for the full specification.
```

---

## Crawler access score — use the measured one

This skill reports **declared policy** (what robots.txt says). The score comes from **measured reachability** — the live probe's `overall_score` and `class_scores` (see the `geo-botaccess` skill).

Do not compute a second score from tier counts. A site with a permissive robots.txt and a blocking WAF is exactly the case this tool exists to catch, and a declared-policy score would read ~94/100 while reality reads ~31/100. Two scores that disagree force the reader to reconcile them; report one number, from the probe, and use this skill's tier tables to explain *what each bot does* rather than to compute anything.
