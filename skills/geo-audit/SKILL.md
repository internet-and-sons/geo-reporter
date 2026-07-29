---
name: geo-audit
description: Full website GEO+SEO audit with parallel subagent delegation. Orchestrates a comprehensive Generative Engine Optimization audit across AI citability, platform analysis, technical infrastructure, content quality, and schema markup. Produces a composite GEO Score (0-100) with prioritized action plan.
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash
  - WebFetch
  - Write
---

# GEO Audit Orchestration Skill

## Purpose

This skill performs a comprehensive Generative Engine Optimization (GEO) audit of any website. GEO is the practice of optimizing web content so that AI systems (ChatGPT, Claude, Perplexity, Gemini, etc.) can discover, understand, cite, and recommend it. This audit measures how well a site performs across all GEO dimensions and produces an actionable improvement plan.

## Report Contract (mandatory)

Before writing any output, read `"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/REPORT-CONTRACT.md"` and follow all 13 rules. In particular: the report leads with a ≤150-word TL;DR (score, top-3 actions with impact+effort, one-sentence posture); every status label comes from the contract's closed legend; every finding uses Finding/Evidence/Impact/Fix/Confidence; raw tables go to the appendix.

## Key Insight

Traditional SEO optimizes for search engine rankings. GEO optimizes for AI citation and recommendation. Sites that score high on GEO metrics see 30-115% more visibility in AI-generated responses (Georgia Tech / Princeton / IIT Delhi 2024 study). The two disciplines overlap but have distinct requirements.

---

## Audit Workflow

### Phase 1: Discovery and Reconnaissance

**Step 0: Ownership check (contract rule 13).** Establish whether this is the user's own site or a third party's. If third-party/competitor, run in External Observation mode: label the report "External Observation Only", cap the crawl at homepage + ≤20 pages, and present observations WITHOUT a /100 composite score. When ambiguous, ask "Is this your own site, or a competitor's / third party's?"

**Step 1: Fetch Homepage and Detect Business Type**

1. Run the structured page fetcher — **always use this, not `WebFetch`, for the target URL.** `WebFetch` converts HTML to markdown, strips `<head>`, drops JSON-LD, hides HTTP headers, and silently returns empty pages for JS-rendered SPAs. The packaged fetcher avoids all four problems:

   ```bash
   python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/fetch_page.py" <url> page
   ```

   The output is a single JSON object — use its fields directly rather than re-parsing the body:

   | Field | What's in it |
   |---|---|
   | `title`, `description`, `canonical` | page metadata |
   | `meta_tags` | full meta-tag dictionary (Open Graph, Twitter Card, robots, viewport, etc.) |
   | `h1_tags`, `heading_structure` | heading hierarchy with text |
   | `word_count`, `text_content` | body word count and extracted body text |
   | `internal_links`, `external_links`, `images` | with alt-text status on images |
   | `structured_data[]` | parsed JSON-LD blocks (Organization, LocalBusiness, Article, etc.) |
   | `headers`, `security_headers` | full HTTP response headers (CSP, HSTS, X-Frame-Options, etc.) |
   | `status_code`, `redirect_chain` | response status + redirect history |
   | `has_ssr_content` | **`false` = JS-rendered SPA with no server-side content**; AI crawlers will see an empty page. Flag as a critical issue if this is the case. |

**Multilingual detection (mandatory):** before crawling, determine whether the site is multilingual: look for hreflang link pairs, language path prefixes (`/en/`, `/he/`), and the `Content-Language` response header. If multilingual, run the audit **per language tree**: crawl each tree separately (use `--accept-language <lang>` on fetch_page.py for language-negotiating sites), give each tree its own category scores and findings, and structure the final report with one section per language (contract rule 7). Never average two languages into one score — a site can be dominant in one language and invisible in the other.

2. Extract these signals from the JSON (no re-fetch needed):
   - Page title, meta description, H1 heading (from `title`, `description`, `h1_tags`)
   - Navigation menu items and footer content (from `text_content` + link structure)
   - Schema.org markup on homepage (from `structured_data[]` — Organization, LocalBusiness, etc.)
   - Pricing page link (SaaS indicator)
   - Product listing patterns (E-commerce indicator)
   - Blog/resource section (Publisher indicator)
   - Service pages (Agency indicator)
   - Address/phone/Google Maps embed (Local business indicator)

3. **If `has_ssr_content == false`**, the site is JS-rendered without server-side rendering. This is a critical GEO finding — log it and continue with whatever data was extractable. For deeper JS-rendered analysis, the `geo-botaccess` skill's Playwright fallback can fetch a fully-rendered baseline; reference its output if available.

4. Classify the business type using these patterns:

| Business Type | Detection Signals |
|---|---|
| **SaaS** | Pricing page, "Sign up" / "Free trial" CTAs, app.domain.com subdomain, feature comparison tables, integration pages |
| **Local Business** | Physical address on homepage, Google Maps embed, "Near me" content, LocalBusiness schema, service area pages |
| **E-commerce** | Product listings, shopping cart, product schema, category pages, price displays, "Add to cart" buttons |
| **Publisher** | Blog-heavy navigation, article schema, author pages, date-based archives, RSS feeds, high content volume |
| **Agency/Services** | Case studies, portfolio, "Our Work" section, team page, client logos, service descriptions |
| **Hybrid** | Combination of above signals -- classify by dominant pattern |

**Step 2: Crawl Sitemap and Internal Links**

Use the packaged sitemap crawler — handles sitemap indexes recursively, respects the 50-page cap, and falls back gracefully if no sitemap is present:

```bash
python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/fetch_page.py" <url> sitemap
```

Returns `{pages: [...], count: N}`. The crawler already attempts `/sitemap.xml` and `/sitemap_index.xml`, follows nested sitemap indexes, and caps at 50 unique URLs.

If `count == 0`, no sitemap was discoverable. Fall back to internal-link crawling from the homepage's `internal_links` field (already collected in Step 1's `fetch_page.py page` output):
- Use the homepage's `internal_links` as the level-1 set
- Follow up to 2 levels deep, capped at 50 total URLs
- Prioritize pages linked from main navigation

For both paths: respect `robots.txt` (cross-reference with `fetch_page.py <url> robots`), skip pages disallowed for the default user-agent, and enforce a 30-second timeout per fetch.

Page prioritization within the 50-page cap:
- Homepage (always include)
- Top-level navigation pages
- High-value pages (pricing, about, contact, key service/product pages)
- Blog posts (sample 5–10 most recent)
- Category/landing pages

**Step 3: Collect Page-Level Data**

For each page in the crawl set, record:
- URL, title, meta description, canonical URL
- H1-H6 heading structure
- Word count of main content
- Schema.org types present
- Internal/external link counts
- Images with/without alt text
- Open Graph and Twitter Card meta tags
- Response status code
- Whether the page has structured data

---

### Phase 2: Parallel Subagent Delegation

Delegate analysis to 5 specialized subagents. Each subagent operates on the collected page data and produces a category score (0-100) plus findings.

**Subagent 1: AI Visibility Analysis (geo-ai-visibility)**
- Analyze content blocks for quotability by AI systems (citability scoring)
- **Run the live AI crawler reachability probe** (`fetch_page.py <url> bots`, same engine as the standalone `geo-botaccess` skill) to determine what each AI crawler actually receives from the origin — ground truth, robust against WAF rules that override robots.txt. Cross-reference against the declared robots.txt policy to surface declared-vs-actual mismatches as critical issues.
- Check llms.txt presence and validate format
- Scan brand presence across YouTube, Reddit, Wikipedia, LinkedIn
- Score brand authority signals that AI models use for entity recognition

**Subagent 2: Platform Optimization (geo-platform-analysis)**
- Assess readiness for Google AI Overviews, ChatGPT, Perplexity, Gemini, Bing Copilot
- Check platform-specific ranking factors and optimization opportunities

**Subagent 3: Technical GEO Infrastructure (geo-technical)**
- Verify meta tags, headers, and technical accessibility for AI systems
- Check page speed, server-side rendering, and Core Web Vitals
- Assess security headers and mobile optimization
- Run the agent-readiness probe (`fetch_page.py <url> agentready`) and include its non-scoring emerging-protocol block (see `geo-agentready` skill)
- (Crawler access is covered by Subagent 1's live probe — do not re-do static robots.txt parsing here.)

**Subagent 4: Content E-E-A-T Quality (geo-content)**
- Evaluate Experience, Expertise, Authoritativeness, Trustworthiness signals
- Check author bios, credentials, source citations
- Assess content freshness, depth, and originality
- Verify "About" page quality and team credentials
- Run the content-integrity scan (`fetch_page.py <url> integrity`) and surface any signals via the geo-integrity skill's framing (signal-not-verdict, max Confidence Likely)
- Surface the citability scorer's `negative_signals` (keyword stuffing, CTA-in-body, boilerplate, missing author) as informational findings — they do NOT change the score

**Subagent 5: Schema & Structured Data (geo-schema)**
- Validate all schema.org markup
- Check for GEO-critical schema types (FAQ, HowTo, Organization, Product, Article)
- Assess schema completeness and accuracy
- Identify missing schema opportunities

---

### Phase 3: Score Aggregation and Report Generation

#### Composite GEO Score Calculation

The overall GEO Score (0-100) is a weighted average of six category scores:

| Category | Weight | What It Measures |
|---|---|---|
| **AI Citability** | 25% | How quotable/extractable content is for AI systems |
| **Brand Authority** | 20% | Third-party mentions, entity recognition signals |
| **Content E-E-A-T** | 20% | Experience, Expertise, Authoritativeness, Trustworthiness |
| **Technical GEO** | 15% | AI crawler access, llms.txt, rendering, speed |
| **Schema & Structured Data** | 10% | Schema.org markup quality and completeness |
| **Platform Optimization** | 10% | Presence on platforms AI models train on and cite |

**Formula:**
```
GEO_Score = (Citability * 0.25) + (Brand * 0.20) + (EEAT * 0.20) + (Technical * 0.15) + (Schema * 0.10) + (Platform * 0.10)
```

#### Score Interpretation

| Score Range | Rating | Interpretation |
|---|---|---|
| 90-100 | Excellent | Top-tier GEO optimization; site is highly likely to be cited by AI |
| 75-89 | Good | Strong GEO foundation with room for improvement |
| 60-74 | Fair | Moderate GEO presence; significant optimization opportunities exist |
| 40-59 | Poor | Weak GEO signals; AI systems may struggle to cite or recommend |
| 0-39 | Critical | Minimal GEO optimization; site is largely invisible to AI systems |

#### Evaluator self-check (contract rule 12)

Before delivering, run the 8-point self-check from REPORT-CONTRACT.md rule 12 (evidence on every Critical/High, score matches findings, no fabricated metrics, no YMYL schema without credentials, no duplicate findings, scope respected, fixes name specific elements, high-risk code withheld). Fix any failure before output.

---

## Issue Severity Classification

Every issue found during the audit is classified by severity:

### Critical (Fix Immediately)
- All AI crawlers blocked in robots.txt
- No indexable content (JavaScript-rendered only with no SSR)
- Domain-level noindex directive
- Site returns 5xx errors on key pages
- Complete absence of any structured data
- Brand not recognized as an entity by any AI system

### High (Fix Within 1 Week)
- Key AI crawlers (GPTBot, ClaudeBot, PerplexityBot) blocked
- Zero question-answering content blocks on key pages
- Missing Organization or LocalBusiness schema
- No author attribution on content pages
- All content behind login/paywall with no preview

### Medium (Fix Within 1 Month)
- Partial AI crawler blocking (some allowed, some blocked)
- Content blocks average under 50 citability score
- Missing FAQ schema on pages with FAQ content
- Thin author bios without credentials
- No Wikipedia or Reddit brand presence
- Content undated or older than 13 weeks on key pages (AI engines measurably prefer fresh content)
- robots.txt carries rules for retired bot tokens (anthropic-ai, claude-web, FacebookBot) — dead weight, cleanup recommended

### Low (Optimize When Possible)
- Minor schema validation errors
- Some images missing alt text
- Content freshness issues on non-critical pages
- Missing Open Graph tags
- Suboptimal heading hierarchy on some pages
- LinkedIn company page exists but is incomplete
- No llms.txt file (informational: no measured citation impact; useful only for developer-facing sites serving coding agents)

---

## Output Format

Generate a file called `GEO-AUDIT-REPORT.md` with the following structure:

```markdown
# GEO Audit Report: [Site Name]

**Audit Date:** [Date] · **URL:** [URL] · **Business Type:** [Type] · **Pages Analyzed:** [Count] · **Languages:** [e.g. Hebrew + English]

## TL;DR

**GEO Score: [X]/100 ([Rating])** [— up/down N since last audit]

[One plain-language sentence on overall posture.]

**Do these three things this week:**
1. [Action] — Impact: [High/Med/Low] · Effort: [minutes/hours/days] · Owner: [developer/content/marketing]
2. [Action] — Impact · Effort · Owner
3. [Action] — Impact · Effort · Owner

## What changed since the last audit
[Only if a prior audit exists: Fixed / Regressed / New. Otherwise omit this section.]

## Findings

[Per language tree if multilingual. Each finding in contract format:]

### [Finding title in plain language]
**Evidence:** [what was observed, quoted]
**Impact:** [reader terms; say "no action needed" when true]
**Fix:** [paste-ready artifact, or task + owner + effort. For content fixes: proposed title, structure, and who currently wins the query]
**Confidence:** [Confirmed | Likely | Hypothesis]

## Score Breakdown

| Category | Score | Weight | Weighted |
|---|---|---|---|
| AI Citability | [X]/100 | 25% | [X] |
| Brand Authority | [X]/100 | 20% | [X] |
| Content E-E-A-T | [X]/100 | 20% | [X] |
| Technical GEO | [X]/100 | 15% | [X] |
| Schema & Structured Data | [X]/100 | 10% | [X] |
| Platform Optimization | [X]/100 | 10% | [X] |
| **Overall** | | | **[X]/100** |

## 30-Day Action Plan
[Week-by-week checkboxes, each item carrying owner + effort tags.]

## Appendix
[Raw tables: per-bot crawler matrix with the contract status legend printed above it, all-blocks citability scores, header dumps, pages analyzed, methodology, checks that did not run ("<metric> not measured — <how>").]
```

---

## Quality Gates

- **Page Limit:** Never crawl more than 50 pages per audit. Prioritize high-value pages.
- **Timeout:** 30-second maximum per page fetch. Skip pages that exceed this.
- **Robots.txt:** Always check and respect robots.txt before crawling. Note any AI-specific directives.
- **Rate Limiting:** Wait at least 1 second between page fetches to avoid overloading the server.
- **Error Handling:** Log failed fetches but continue the audit. Report fetch failures in the appendix.
- **Content Type:** Only analyze HTML pages. Skip PDFs, images, and other binary content.
- **Deduplication:** Canonicalize URLs before crawling. Skip duplicate content (e.g., HTTP vs HTTPS, www vs non-www, trailing slashes).

---

## Business-Type-Specific Audit Adjustments

### SaaS Sites
- Extra weight on: Feature comparison tables (high citability), integration pages, documentation quality
- Check for: API documentation structure, changelog pages, knowledge base organization
- Key schema: SoftwareApplication, FAQPage, HowTo

### Local Businesses
- Extra weight on: NAP consistency, Google Business Profile signals, local schema
- Check for: Service area pages, location-specific content, review markup
- Key schema: LocalBusiness, GeoCoordinates, OpeningHoursSpecification

### E-commerce Sites
- Extra weight on: Product descriptions (citability), comparison content, buying guides
- Check for: Product schema completeness, review aggregation, FAQ sections on product pages
- Key schema: Product, AggregateRating, Offer, BreadcrumbList

### Publishers
- Extra weight on: Article quality, author credentials, source citation practices
- Check for: Article schema, author pages, publication date freshness, original research
- Key schema: Article, NewsArticle, Person (author), ClaimReview

### Agency/Services
- Extra weight on: Case studies (citability), expertise demonstration, thought leadership
- Check for: Portfolio schema, team credentials, industry-specific expertise signals
- Key schema: Organization, Service, Person (team), Review
