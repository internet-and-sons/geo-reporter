---
name: geo-report
description: Generate a professional, client-facing GEO report combining all audit results into a single deliverable with scores, findings, and prioritized actions
version: 1.0.0
author: geo-reporter
tags: [geo, report, client-deliverable, executive-summary, action-plan]
allowed-tools: Read, Grep, Glob, Bash, WebFetch, Write
---

# GEO Client Report Generator

## Purpose

This skill aggregates outputs from all GEO audit skills into a single, professional report that can be delivered directly to a client or stakeholder. The report is written for **business owners and marketing leaders**, not developers — technical findings are translated into business impact and clear action items with priority levels.

## Report Contract (mandatory)

Before writing any output, read `"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/REPORT-CONTRACT.md"` and follow all 13 rules. In particular: the report leads with a ≤150-word TL;DR (score, top-3 actions with impact+effort, one-sentence posture); every status label comes from the contract's closed legend; every finding uses Finding/Evidence/Impact/Fix/Confidence; raw tables go to the appendix.

## How to Use This Skill

1. Run the following audits first (or use existing report data):
   - `geo-platform-optimizer` -> GEO-PLATFORM-OPTIMIZATION.md
   - `geo-schema` -> GEO-SCHEMA-REPORT.md
   - `geo-technical` -> GEO-TECHNICAL-AUDIT.md
   - `geo-content` -> GEO-CONTENT-ANALYSIS.md
   - (Optional) `geo-llmstxt` -> llms.txt assessment
   - (Optional) `geo-brand-mentions` -> brand authority data
2. Collect all scores and findings
3. Calculate the composite GEO Readiness Score
4. Generate the client report using the template below
5. Output: `GEO-CLIENT-REPORT-<DOMAIN-SLUG>.md` (see "Output" section for the slug rule)

---

## GEO Readiness Score Calculation

### Component Weights

| Component | Weight | Source Skill |
|---|---|---|
| AI Platform Readiness | 25% | geo-platform-optimizer |
| Content Quality & E-E-A-T | 25% | geo-content |
| Technical Foundation | 20% | geo-technical |
| Schema & Structured Data | 15% | geo-schema |
| Brand Authority & Entity Presence | 15% | geo-platform-optimizer (entity signals) |

### Score Formula
```
GEO Score = (Platform Score * 0.25) + (Content Score * 0.25) + (Technical Score * 0.20) + (Schema Score * 0.15) + (Brand Score * 0.15)
```

Round to the nearest integer. Cap at 100.

### Score Interpretation for Clients

| Score Range | Label | Client-Facing Description |
|---|---|---|
| 85-100 | Excellent | Your site is well-positioned for AI search. Focus on maintaining and expanding your advantage. |
| 70-84 | Good | Solid foundation with clear opportunities to improve AI visibility. Targeted optimizations will yield significant results. |
| 55-69 | Moderate | Your site has gaps in AI readiness that competitors may be exploiting. A structured optimization plan will close these gaps. |
| 40-54 | Below Average | Significant barriers to AI search visibility exist. Without action, your brand risks being invisible in AI-generated answers. |
| 0-39 | Needs Attention | Critical AI readiness issues require immediate action. Your competitors are likely capturing the AI search traffic your brand should own. |

---

## Report Template

The complete report follows this exact structure. Each section includes instructions on what to write and how.

Body sections carry findings in Finding/Evidence/Impact/Fix/Confidence form (contract rule 3). Enumerative tables belong in the Appendix (rule 8). The TL;DR and Score Breakdown are the two exceptions.

Every body finding renders in this shape:

```markdown
### [Finding title in plain language]
**Evidence:** [what was observed, quoted]
**Impact:** [reader terms; "no action needed" when true]
**Fix:** [paste-ready artifact, or task + owner + effort]
**Confidence:** [Confirmed | Likely | Hypothesis]
```

Omit **Fix** on no-action findings. Every status word inside Evidence comes from the contract's closed legend.

---

### Section 1: TL;DR

This is the FIRST content section of the report — nothing goes above it. Keep it under 150 words total. The client should be able to read only this block and know the score, the posture, and what to do next.

```markdown
## TL;DR

**GEO Score: [X]/100 ([Rating])** [— up/down N since last audit]

[One plain-language sentence on overall posture.]

**Do these three things this week:**
1. [Action] — Impact: [High/Med/Low] · Effort: [minutes/hours/days] · Owner: [developer/content/marketing]
2. [Action] — Impact · Effort · Owner
3. [Action] — Impact · Effort · Owner
```

The three actions are the highest impact-per-effort items from the Prioritized Action Plan — not a separate list. Include the delta clause only when a prior audit for the same domain exists.

### Section 2: Executive Summary

Write exactly ONE paragraph (3-5 sentences) that **adds to** the TL;DR rather than restating it. Do not repeat the score, the rating label, or the three actions. Cover:
- What was analyzed (domain, number of pages, date of analysis)
- The single most impactful finding (positive or negative), with the observation that supports it
- One sentence on the business impact ("Addressing these recommendations could increase AI-driven traffic by an estimated XX%, representing approximately $X,XXX/month based on current traffic patterns")

**Tone**: Confident, direct, professional. No jargon. No hedging. Write as a consultant delivering findings, not as a tool generating a report.

### Section 3: GEO Readiness Score

Present the overall score prominently:

```
## GEO Readiness Score: XX/100 — [Label]
```

Then break down by component in a table:

```markdown
| Component | Score | Weight | Weighted Score |
|---|---|---|---|
| AI Platform Readiness | XX/100 | 25% | XX |
| Content Quality & E-E-A-T | XX/100 | 25% | XX |
| Technical Foundation | XX/100 | 20% | XX |
| Schema & Structured Data | XX/100 | 15% | XX |
| Brand Authority | XX/100 | 15% | XX |
| **Overall** | | | **XX/100** |
```

### Section 4: AI Visibility Dashboard

Open with one paragraph explaining what platform readiness means: "These scores reflect how likely your content is to be cited by each AI search platform. A score below 50 indicates significant barriers to citation on that platform."

Then write **one finding per platform that is materially weak or materially strong** — not one per platform on the list. The full five-platform readiness matrix goes to the Appendix.

```markdown
## AI Visibility Dashboard

[Paragraph: what these scores mean. Range across platforms: XX–XX/100.
Full per-platform matrix in Appendix → Raw Data Tables.]

### [Platform] cannot currently cite your product pages
**Evidence:** [Platform] readiness scored XX/100. [The specific observation that
drove it — e.g. "Perplexity favours pages with a dated, sourced summary block;
none of the 12 pages sampled carried a publication date."]
**Impact:** [Platform] is where [reader's audience] asks [category] questions.
At this score your pages are unlikely to surface in those answers.
**Fix:** [Specific action] — Owner: [content/developer/marketing] · Effort: [hours/days]
**Confidence:** [Confirmed | Likely | Hypothesis]

### [Platform] readiness is already strong
**Evidence:** [Platform] readiness scored XX/100; [observation supporting it].
**Impact:** No action needed — hold this position.
**Confidence:** Confirmed
```

### Section 5: AI Crawler Access Status

The **full per-crawler probe matrix lives in the Appendix**, with the closed legend printed directly beneath it. The body carries one finding per *distinct crawler posture* observed — not one row per bot.

**Every status word used anywhere — body or appendix — must come from the report contract's closed legend.** No free-text statuses, and never "Unverified". Opt-out tokens that are never fetched (Google-Extended, Applebot-Extended) render as `— Not tested (opt-out token — never fetches)`, not as a pass or fail.

```markdown
## AI Crawler Access

[One-paragraph posture sentence: how many of the N crawlers probed reached your
site, and whether that matches what your robots.txt declares. Full probe matrix
in Appendix → Raw Data Tables.]

### ChatGPT's crawler is being turned away by your CDN
**Evidence:** GPTBot received `❌ Blocked by Cloudflare (mismatch — declared open)`
— HTTP 403 with a Cloudflare challenge body, while your robots.txt explicitly
allows it. Googlebot on the same path returned `✅ Confirmed (tested live)`.
**Impact:** ChatGPT cannot read the pages you intended to let it read. This is a
misconfiguration, not a policy choice — you are blocked without meaning to be.
**Fix:** Add GPTBot to the CDN bot-management allowlist. Owner: developer · Effort: minutes
**Confidence:** Confirmed

### Search and retrieval crawlers reach the site normally
**Evidence:** Googlebot, Bingbot and PerplexityBot each returned
`✅ Confirmed (tested live)` with bodies byte-identical to a browser fetch.
**Impact:** No action needed — the platforms that matter most can read you.
**Confidence:** Confirmed

### Training opt-out tokens are declared, and that is a deliberate posture
**Evidence:** Google-Extended and Applebot-Extended render as
`— Not tested (opt-out token — never fetches)`; robots.txt disallows both.
**Impact:** No action needed. Blocking training while allowing retrieval is the
standard publisher posture — it does not reduce your citation chances.
**Confidence:** Confirmed
```

**Translate for the client**: "Blocking AI crawlers is like closing your store during business hours. If a crawler cannot access your site, the AI platform it powers cannot cite your content. We recommend allowing all major AI crawlers unless you have a specific data licensing concern."

Per contract rule 10, if the fix involves editing robots.txt, describe the change and its consequences in plain language first, and only render the code block after the client confirms they want it.

### Section 6: Brand Authority Analysis

The **full platform-presence table goes to the Appendix**. The body carries findings for the entity gaps that actually move citation probability — highest-weight platforms first (Wikipedia and Reddit dominate ChatGPT and Perplexity citations respectively).

```markdown
## Brand Authority

[One paragraph: how many of the N authority platforms carry an accurate presence,
and which single gap costs the most. Full presence table in Appendix → Raw Data Tables.]

### Your brand has no machine-readable entity record
**Evidence:** No Wikidata item and no Wikipedia article resolve for "[Brand]".
The Organization schema on the homepage carries [N] `sameAs` links, none of
which point to an encyclopedic or registry source.
**Impact:** Wikipedia accounts for roughly 47.9% of ChatGPT's citations. Without
an anchored entity record, AI systems have no authoritative way to confirm your
brand is the entity being asked about, so they cite a competitor that does.
**Fix:** Create a Wikidata item with founding date, industry, and official URL,
then add it to `sameAs`. Owner: marketing · Effort: hours
**Confidence:** Confirmed

### Community presence is thin on the platform Perplexity trusts most
**Evidence:** [N] Reddit mentions of "[Brand]" across [subreddits sampled];
[characterization — e.g. "none in the last 12 months"].
**Impact:** Reddit accounts for roughly 46.7% of Perplexity's citations.
**Fix:** [Specific engagement plan] — Owner: marketing · Effort: weeks (ongoing)
**Confidence:** Likely

### Established profiles are consistent
**Evidence:** LinkedIn, YouTube and Crunchbase profiles all resolve and list the
same legal name, founding year and URL as the homepage schema.
**Impact:** No action needed — cross-platform consistency is already working for you.
**Confidence:** Confirmed
```

**Translate for the client**: "AI platforms build trust by cross-referencing your brand across multiple authoritative sources. Each platform where your brand has an accurate, consistent presence increases the likelihood of being cited in AI answers."

### Section 7: Citability Analysis

The **per-page citability score table goes to the Appendix**. The body carries findings about the *patterns* those scores reveal — a reader does not act on a list of twelve scores, they act on "your product pages all bury the answer".

Write one finding per pattern, covering both the strongest and weakest ends of the range. Because these are content rewrites, contract rule 6 applies: each rewrite finding shows the current passage, the rewritten citable version, and one line on why the rewrite wins.

```markdown
## Citability Analysis

[One paragraph: citability range across the N pages scored, and the single
pattern that separates the top from the bottom. Per-page scores in
Appendix → Raw Data Tables.]

### Your highest-value pages bury the answer below the fold
**Evidence:** [N] of [N] product pages open with brand narrative; the first
direct answer to the page's own title question appears at paragraph [N].
On `/[path]` the opening line reads: "[quoted current passage]".
**Impact:** AI systems extract answers from the first self-contained passage
they can lift. Pages that make them read 400 words first get skipped in favour
of a competitor who answered in the first sentence.
**Fix:** Lead each page with a 40–60 word direct answer.

*Current:* "[quoted current passage]"
*Rewritten:* "[the citable version — direct, self-contained, specific]"
*Why it wins:* Answers the title question in one liftable sentence, with a
concrete figure an AI system can attribute.

Owner: content · Effort: days
**Confidence:** Confirmed

### Your guide pages are already highly citable
**Evidence:** `/[path]` scored XX/100 — question-form H2s, dated, bylined to a
named author with credentials, and each section answers in its first sentence.
**Impact:** No action needed. This page is your template — apply its structure
to the pages above.
**Confidence:** Confirmed
```

**Business impact framing**: "Your most citable pages are your best candidates for appearing in AI-generated answers. Improving the least citable pages represents the highest-ROI content investment you can make for AI visibility."

### Section 8: Technical Health Summary

The **full technical checklist goes to the Appendix**. The body carries a finding for each area that needs work, plus one consolidated no-action finding for the areas that are already healthy. Order by severity — rendering first, then anything blocking crawl, then performance.

Per contract rule 4: any check that did not run renders as "[metric] not measured — [what would measure it]". Never a guessed value.

```markdown
## Technical Health

[One paragraph: how many of the N technical checks passed, and the one that
matters most. Full checklist in Appendix → Raw Data Tables.]

### AI crawlers see an empty page
**Evidence:** The server HTML for `/[path]` contains [N] words of body copy; the
same URL rendered with JavaScript contains [N]. Product copy, headings and
schema all appear only after JS execution.
**Impact:** This is the single most impactful technical issue for AI search
visibility. Most AI platforms do not execute JavaScript, so they receive a shell
with nothing to cite. Until this is resolved they cannot cite your content at all.
**Fix:** Enable server-side rendering or static pre-rendering for all indexable
routes. Owner: developer · Effort: days
**Confidence:** Confirmed

### Pages load slowly enough to affect ranking and crawl budget
**Evidence:** LCP [X.X]s and INP [XXX]ms on [page], measured via [tool] on [date]
— above the [2.5s / 200ms] thresholds.
**Impact:** [Reader-terms consequence.]
**Fix:** [Named change — e.g. "compress the four hero images on /"] —
Owner: developer · Effort: hours
**Confidence:** Confirmed

### HTTPS, mobile rendering and security headers are all sound
**Evidence:** Valid certificate, HSTS present, responsive viewport declared, and
mobile and desktop HTML match.
**Impact:** No action needed.
**Confidence:** Confirmed
```

### Section 9: Schema & Structured Data

The **complete schema inventory goes to the Appendix**. The body carries a finding per missing or broken schema, each shipping the paste-ready JSON-LD as its Fix (contract rule 5).

Two guards apply. Contract rule 11: never recommend `LegalService`, `MedicalWebPage`, `Physician`, `MedicalClinic` or `FinancialProduct` unless the report verifies the site displays the matching real-world credential — otherwise recommend `Organization` / `ProfessionalService` and say why. And if `structured_data` came back empty but the page shows CMS markers, report "no server-rendered structured data; client-side injection possible", not "no structured data".

```markdown
## Schema & Structured Data

[One paragraph: which schema types are present and valid, which are missing.
Full inventory in Appendix → Raw Data Tables.]

### Your Organization schema does not link out to any other profile
**Evidence:** The homepage Organization block is valid JSON-LD and server-rendered,
but carries no `sameAs` property. [N] verified profiles exist off-site.
**Impact:** `sameAs` is how an AI system confirms the company on your site is the
same company it has seen on LinkedIn, Wikidata and Crunchbase. Without it, each
mention is a separate unverified entity and none of them accumulate trust.
**Fix:** Add to the existing Organization block in `<head>`:

```json
"sameAs": [
  "https://www.linkedin.com/company/...",
  "https://www.wikidata.org/wiki/Q..."
]
```

Owner: developer · Effort: minutes
**Confidence:** Confirmed

### Articles carry no author entity
**Evidence:** [N] of [N] blog posts have Article schema; none include a `author`
Person node with `sameAs` or `knowsAbout`.
**Impact:** Author credentials are the strongest E-E-A-T signal available to AI
systems. Anonymous articles are discounted against bylined competitors.
**Fix:** [Paste-ready Person node, adapted from the `article-author` template.]
Owner: developer · Effort: hours
**Confidence:** Confirmed
```

Where a schema is missing entirely, adapt the matching bundled template from `schema/` (see geo-schema) and paste the filled result into the Fix — never a template with `REPLACE:` markers or `YOURDOMAIN.com` left in it.

### Section 10: llms.txt Status

```markdown
## llms.txt — AI Content Guide

### No AI content guide is published
**Evidence:** `https://[domain]/llms.txt` and `/llms-full.txt` both return HTTP 404.
**Impact:** llms.txt is an emerging standard, not yet universally read, so its
absence costs nothing today — but publishing one is cheap and puts you ahead of
competitors as adoption grows.
**Fix:** [Paste-ready llms.txt, generated from the site's own structure — title,
one-line description, and the 10–20 pages you most want cited.]
Owner: developer · Effort: minutes
**Confidence:** Confirmed
```

**Translate for the client**: "llms.txt is an emerging standard (similar to robots.txt) that tells AI systems what your site is about and which pages are most important. While not universally adopted yet, implementing it positions your brand ahead of competitors and provides direct guidance to AI platforms."

### Section 11: Prioritized Action Plan

This is the most important section of the report. Organize actions by timeline and impact.

```markdown
## Prioritized Action Plan

### Quick Wins (This Week)
*High impact, low effort — can be implemented immediately*

| # | Action | Impact | Effort | Platforms Affected |
|---|---|---|---|---|
| 1 | [Specific action] | [High/Med] | [Hours estimate] | [Which AI platforms] |
| 2 | [Specific action] | [High/Med] | [Hours estimate] | [Which AI platforms] |
```

**Quick Win criteria**: Can be done in < 4 hours by one person. Examples:
- Unblock AI crawlers in robots.txt
- Add publication dates to existing content
- Add author bylines with credentials
- Fix broken meta descriptions
- Add sameAs properties to existing Organization schema
- Create/claim llms.txt file

```markdown
### Medium-Term Improvements (This Month)
*Significant impact, moderate effort — requires content or technical changes*

| # | Action | Impact | Effort | Platforms Affected |
|---|---|---|---|---|
| 1 | [Specific action] | [High/Med] | [Days estimate] | [Which AI platforms] |
```

**Medium-Term criteria**: 1-5 days of work. Examples:
- Restructure top 10 pages with question-based headings and direct answers
- Implement comprehensive Schema.org markup
- Create author pages with credentials and sameAs links
- Optimize Core Web Vitals (image compression, code splitting)
- Register and configure Bing Webmaster Tools
- Implement IndexNow protocol

```markdown
### Strategic Initiatives (This Quarter)
*Long-term competitive advantage, requires ongoing investment*

| # | Action | Impact | Effort | Platforms Affected |
|---|---|---|---|---|
| 1 | [Specific action] | [High/Med] | [Weeks estimate] | [Which AI platforms] |
```

**Strategic criteria**: Ongoing effort over weeks/months. Examples:
- Build Wikipedia/Wikidata entity presence
- Develop active Reddit community engagement strategy
- Create YouTube content strategy aligned with search queries
- Implement server-side rendering (if currently client-rendered)
- Build topical authority through comprehensive content strategy
- Establish original research/data publication program

### Estimated Impact
After the action plan, include an impact estimate:

"Based on industry benchmarks and the specific gaps identified in this audit:
- **Quick Wins alone** could improve your GEO score by approximately [X-Y] points
- **Full implementation** of this action plan could improve your GEO score to approximately [XX]/100
- At current traffic levels and conversion rates, improved AI visibility represents an estimated **$X,XXX - $XX,XXX per month** in additional organic value"

Use conservative estimates. Base the dollar figure on:
- Current estimated organic traffic value (from analytics if available, or estimate from industry benchmarks)
- AI search is projected to drive 25-40% of organic discovery by end of 2026
- A 10-point GEO score improvement typically correlates with a 15-25% increase in AI citation frequency

### Section 12: Competitor Comparison (if competitor URLs provided)

If competitor URLs were analyzed alongside the primary domain. Per contract rule 13, competitor sites are **External Observation Only** — present observations, never a /100 grade for a site you do not own. The **full side-by-side metric matrix goes to the Appendix**; the body carries findings on the gaps that matter.

```markdown
## Competitor Comparison

[One paragraph: who was compared and on what basis. Full matrix in
Appendix → Raw Data Tables. Competitor observations are external-only — no scores.]

### A competitor owns the entity record you are missing
**Evidence:** [Competitor] resolves to a Wikidata item and a Google Knowledge
Panel; [Brand] resolves to neither.
**Impact:** When an AI system is asked "who are the leading [category] providers",
[Competitor] is a confirmable entity and you are an unconfirmed string.
**Fix:** [Named action] — Owner: marketing · Effort: [hours/weeks]
**Confidence:** Confirmed

### You lead on crawler access
**Evidence:** All [N] probed AI crawlers returned `✅ Confirmed (tested live)` on
[Brand]; [Competitor] returned `❌ Blocked (declared, intentional)` for GPTBot
and PerplexityBot.
**Impact:** No action needed — this is a real, defensible advantage. Hold it.
**Confidence:** Confirmed
```

### Section 13: Appendix

```markdown
## Appendix

### Raw Data Tables

Every enumerative table lives here — the body sections above reference these by
name rather than reproducing them. Reproduce each table in full; the body is
narrative, the appendix is the record. Status labels stay inside the contract's
closed legend here too.

#### A1. AI Platform Readiness Matrix
| AI Platform | Readiness Score | Key Gap | Priority Action |
|---|---|---|---|
| Google AI Overviews | XX/100 | [One-line gap] | [One-line action] |
| ChatGPT Web Search | XX/100 | [One-line gap] | [One-line action] |
| Perplexity AI | XX/100 | [One-line gap] | [One-line action] |
| Google Gemini | XX/100 | [One-line gap] | [One-line action] |
| Bing Copilot | XX/100 | [One-line gap] | [One-line action] |

#### A2. AI Crawler Probe Results
| AI Crawler | Platform | Status | Impact | Recommendation |
|---|---|---|---|---|
| Googlebot | Google Search + AIO | ✅ Confirmed (tested live) | Critical | [Action] |
| GPTBot | ChatGPT / OpenAI | ❌ Blocked by <product> (mismatch — declared open) | High | [Action] |
| Bingbot | Bing + Copilot + ChatGPT | ✅ Confirmed (tested live) | High | [Action] |
| PerplexityBot | Perplexity AI | ❌ Blocked (declared, intentional) | Medium | [Action] |
| Google-Extended | Gemini Training | — Not tested (opt-out token — never fetches) | Medium | [Action] |
| ClaudeBot | Anthropic Claude | ⚠️ Content differs for bots | Medium | [Action] |
| Applebot-Extended | Apple Intelligence | — Not tested (opt-out token — never fetches) | Medium | [Action] |

Print the report contract's status legend directly beneath this table so the
client can decode every label without leaving the page.

#### A3. Brand Presence by Platform
| Platform | Presence | Status | Impact on AI Visibility |
|---|---|---|---|
| Wikipedia | Yes/No | [Detail] | Very High — 47.9% of ChatGPT citations are Wikipedia |
| Wikidata | Yes/No | [Detail] | High — machine-readable entity data |
| LinkedIn | Yes/No | [Detail] | High — Bing Copilot and ChatGPT signal |
| YouTube | Yes/No | [Detail] | High — Gemini and Perplexity signal |
| Reddit | Yes/No | [Detail] | Very High — 46.7% of Perplexity citations are Reddit |
| Google Knowledge Panel | Yes/No | [Detail] | High — Gemini entity recognition |
| Crunchbase | Yes/No | [Detail] | Medium — entity validation |
| GitHub | Yes/No | [Detail] | Medium — tech brand signal |

#### A4. Per-Page Citability Scores
| URL | Citability | Strongest signal | Weakest signal |
|---|---|---|---|
| [absolute URL] | XX/100 | [signal] | [signal] |

List every page scored, ranked high to low.

#### A5. Technical Checklist
| Area | Status | Business Impact |
|---|---|---|
| Core Web Vitals | Good/Needs Work/Poor | [Impact on user experience and rankings] |
| Server-Side Rendering | Yes/Partial/No | [Impact on AI crawler visibility] |
| Mobile Optimization | Good/Needs Work/Poor | [Impact on Google's mobile-first indexing] |
| Security (HTTPS + Headers) | Good/Needs Work/Poor | [Impact on trust signals] |
| Page Speed | Fast/Average/Slow | [Impact on user experience and crawl budget] |
| IndexNow Protocol | Implemented/Not | [Impact on Bing/ChatGPT indexing speed] |

Any check that did not run renders as "[metric] not measured — [what would
measure it]" (contract rule 4).

#### A6. Schema Inventory
| Schema Type | Present | Status | AI Impact |
|---|---|---|---|
| Organization | Yes/No | [Valid/Issues] | Critical — entity recognition |
| Article + Author | Yes/No | [Valid/Issues] | High — E-E-A-T signal |
| sameAs (entity links) | Yes/No | [Count] links | Critical — cross-platform entity graph |
| [Business-specific] | Yes/No | [Valid/Issues] | [Impact] |
| WebSite + SearchAction | Yes/No | [Valid/Issues] | Medium — sitelinks |
| BreadcrumbList | Yes/No | [Valid/Issues] | Low-Medium — navigation context |

#### A7. llms.txt Status
| File | Status | Recommendation |
|---|---|---|
| /llms.txt | Present/Missing | [Action] |
| /llms-full.txt | Present/Missing | [Action] |

#### A8. Competitor Matrix *(only if competitor URLs were analyzed)*
| Metric | [Your Brand] | [Competitor 1] | [Competitor 2] |
|---|---|---|---|
| Google AIO Readiness | XX/100 | [observation] | [observation] |
| ChatGPT Readiness | XX/100 | [observation] | [observation] |
| Perplexity Readiness | XX/100 | [observation] | [observation] |
| Schema Coverage | [Detail] | [Detail] | [Detail] |
| Wikipedia Presence | Yes/No | Yes/No | Yes/No |
| Reddit Authority | [Detail] | [Detail] | [Detail] |
| SSR Status | Yes/No | Yes/No | Yes/No |

Competitor columns carry observations, not /100 scores (contract rule 13).

### Methodology
This GEO audit was conducted using the following methodology:
- **Pages analyzed**: [List of specific URLs audited]
- **Platforms assessed**: Google AI Overviews, ChatGPT, Perplexity AI, Google Gemini, Bing Copilot
- **Technical checks**: HTTP headers, robots.txt, HTML source analysis, structured data validation
- **Content assessment**: E-E-A-T framework (Experience, Expertise, Authoritativeness, Trustworthiness) per Google's December 2025 Quality Rater Guidelines
- **Schema validation**: JSON-LD parsing and Schema.org specification compliance
- **Date of analysis**: [Date]

### Data Sources
- Google Search Quality Rater Guidelines (December 2025 update)
- Schema.org full type hierarchy
- Industry citation studies (Zyppy, Authoritas, Semrush AI search research, 2025-2026)
- Core Web Vitals thresholds (web.dev, 2026 standards)
- AI crawler user-agent documentation (per-platform official docs)

### Glossary

| Term | Definition |
|---|---|
| GEO | Generative Engine Optimization — optimizing content to be cited by AI search platforms |
| AIO | AI Overviews — Google's AI-generated answer boxes at the top of search results |
| E-E-A-T | Experience, Expertise, Authoritativeness, Trustworthiness — Google's content quality framework |
| SSR | Server-Side Rendering — generating HTML on the server so crawlers can read content without JavaScript |
| CWV | Core Web Vitals — Google's page experience metrics (LCP, INP, CLS) |
| LCP | Largest Contentful Paint — time to render the largest visible element |
| INP | Interaction to Next Paint — responsiveness metric (replaced FID in March 2024) |
| CLS | Cumulative Layout Shift — visual stability metric |
| JSON-LD | JavaScript Object Notation for Linked Data — preferred structured data format |
| sameAs | Schema.org property linking an entity to its profiles on other platforms |
| IndexNow | Protocol for instantly notifying search engines of content changes |
| llms.txt | Proposed standard file for guiding AI systems about a site's content |
| YMYL | Your Money or Your Life — topics requiring highest E-E-A-T standards |
| SERP | Search Engine Results Page |
| Topical Authority | The depth and breadth of a site's coverage of its core topic area |
```

---

## Formatting and Tone Guidelines

### Formatting
- Move enumerative tables to the appendix; the body carries findings in Finding/Evidence/Impact/Fix/Confidence format. The TL;DR and the Score Breakdown are the only body blocks exempt from this.
- Use clean markdown throughout: tables, headers (H2/H3), bullet points, bold for emphasis
- Tables for data, bullets for recommendations, bold for key terms
- One blank line between sections for readability
- Use horizontal rules (---) to separate major sections
- All URLs should be absolute (not relative)

### Tone
- **Professional but accessible** — written for a business owner, not a developer
- **Confident and direct** — state findings as conclusions, not possibilities
- **Action-oriented** — every finding should connect to a specific action
- **Business-impact focused** — translate technical issues into business outcomes
- Avoid: jargon without explanation, hedging language, passive voice, excessive caveats
- Use: "Your site [does/does not]...", "We recommend...", "This impacts..."

### Dollar-Value Framing
Where possible, connect recommendations to business value:
- "Improving your Google AIO readiness from 35 to 70 could increase your presence in AI Overviews by an estimated 50%, which at current search volumes represents approximately 2,000 additional monthly visitors"
- "Server-side rendering would make your content accessible to ChatGPT, Perplexity, and other AI platforms — collectively representing an audience your competitors are already reaching"
- "The investment in Schema.org markup (estimated 8-16 hours of developer time) could increase your entity recognition score from 20 to 75, significantly improving citation probability"

Be conservative with estimates. State assumptions clearly. Never guarantee specific results.

---

## Output

Generate **`GEO-CLIENT-REPORT-<DOMAIN-SLUG>.md`** using the complete template above, filled with actual audit data — where `<DOMAIN-SLUG>` is the audited domain with `www.` stripped, dots replaced by hyphens, and uppercased to match the rest of the filename (e.g. `example.co.uk` → `EXAMPLE-CO-UK`, so the file becomes `GEO-CLIENT-REPORT-EXAMPLE-CO-UK.md`). This keeps reports for multiple clients distinguishable in the same directory and visually consistent with the rest of the filename. The report should be:
- 40-80 pages equivalent in detail (3,000-6,000 words)
- Ready to send to a client without editing
- Self-contained (no references to other report files — all relevant data is included)
- Printable and presentable (clean markdown formatting)
