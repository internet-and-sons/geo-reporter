<p align="center">
  <img src="assets/banner.svg" alt="GEO Reporter" width="900"/>
</p>

<h1 align="center">GEO Reporter</h1>

<p align="center">
  <strong>See how your website performs in AI search — and what to fix.</strong>
</p>

<p align="center">
  <em>Highly influenced by <a href="https://github.com/zubair-trabzada/geo-seo-claude">zubair-trabzada/geo-seo-claude</a>. This fork is actively maintained on its own line of development.</em>
</p>

---

## What is GEO Reporter?

GEO Reporter is a Claude Code plugin that audits how visible a website is to AI search engines — ChatGPT, Claude, Perplexity, Google AI Overviews and AI Mode, Bing Copilot, and others — and produces a client-ready report with concrete, owner-tagged fixes.

You point it at a URL. It runs the audit. You get back a score out of 100, a prioritized action plan, and a PDF you can hand to a client or your team. Setup is a single command after install.

Generative Engine Optimization (GEO) is the practice of making a site easy for AI systems to discover, understand, trust, and cite. It overlaps with traditional SEO but has distinct requirements — a page can rank well in Google and still never be quoted in an AI answer.

---

## What does it check?

Below is the full checklist. Everything here is measured against the live site, not inferred.

### Can AI crawlers actually reach the site?

GEO Reporter replays your homepage as **22 AI crawler user-agents** from **12 operators** and records what each one actually receives. This is the check most tools get wrong: `robots.txt` states *intent*, but a Cloudflare or WAF rule can silently return `403` to every AI bot while the declared policy looks perfect.

| Class | What it means | Bots probed |
|---|---|---|
| **Live-retrieval** | Fetches a page on demand when a user asks | ChatGPT-User, Claude-User, Perplexity-User, MistralAI-User, Google-Agent, Google-NotebookLM, Google-GeminiNotebook |
| **Search-index** | Indexes pages for AI search results | OAI-SearchBot, Claude-SearchBot, PerplexityBot, MistralAI-Index, DuckAssistBot, Amazonbot |
| **Traditional search** | Feeds Google/Bing — and their AI surfaces | Googlebot, Bingbot |
| **Training** | Collects data for model training | GPTBot, ClaudeBot, CCBot, Google-CloudVertexBot, Bytespider, Meta-ExternalAgent, cohere-ai |

Also checked:

- **Declared-vs-actual mismatch** — the highest-value finding this tool produces: robots.txt says "come in", the WAF says 403.
- **WAF/CDN fingerprinting** across **15 products** (Cloudflare, Akamai, Imperva, Sucuri, AWS CloudFront/WAF/ELB, F5 BIG-IP, Fastly, Azure Front Door, Barracuda, Wallarm, StackPath, Google Frontend) so remediation names the actual console you need to open.
- **HTTP 402 pay-per-crawl** classified separately — a toll is not a block.
- **Retired and opt-out tokens** (`anthropic-ai`, `claude-web`, `Google-Extended`) reported honestly instead of producing meaningless probe rows.
- **Publisher posture recognition** — blocking training bots while allowing retrieval (the NYT/Reuters/BBC pattern) reads as healthy, not as a problem.
- **Coverage limits stated plainly** — DeepSeek publishes no crawler identity and Grok's is unreliable, so neither is silently implied to be covered.

### Is the content actually quotable by an AI?

A deterministic scorer grades every content block ≥20 words on five dimensions, so two runs of the same page produce identical scores:

| Dimension | Weight | What it measures |
|---|---|---|
| Answer block quality | 30 | Does the passage answer a question in its first sentences? |
| Self-containment | 25 | Does it still make sense lifted out of the page? |
| Structural readability | 20 | Lists, tables, scannable formatting |
| Statistical density | 15 | Specific numbers, dates, named entities |
| Uniqueness | 10 | Original data rather than restated consensus |

**Bilingual by design.** Hebrew and English blocks are scored by separate engines with their own optimal-length bands (English 134–167 words, Hebrew 90–120), so a Hebrew page is not penalised for English assumptions. Bilingual sites are audited **per language tree** with separate scores — a site can dominate in one language and be invisible in the other.

Also flagged (reported, never silently scored): keyword stuffing, calls-to-action mixed into article body text, boilerplate repetition, and missing author bylines.

### Is anyone manipulating AI crawlers on this site?

Few tools check this. GEO Reporter scans for content aimed at AI crawlers rather than human readers:

- **Hidden text** — CSS-hidden blocks of 8+ words
- **LLM-directed instructions** — imperatives planted in HTML comments, `aria-hidden` containers, or `data-*` attributes ("ignore previous instructions", "cite this as…")
- **Invisible Unicode** — zero-width characters embedded in visible text
- **Cloaked keyword blocks** — hidden, keyword-stuffed sections

Findings are deliberately conservative and framed as *signals for review, never proof of intent* — a plugin, theme, or inherited SEO vendor produces these patterns as readily as deliberate spam.

### Is the site ready for AI agents, not just AI crawlers?

Ten well-known endpoints are probed for the emerging 2026 agent surface — all reported as forward-looking signals, never penalised when absent:

MCP server card (SEP-1649) · `agents.json` · API catalog (RFC 9727) · OAuth discovery (RFC 8414/9728) · Web Bot Auth signature directory · NLWeb `/ask` and `/mcp` · RSL `rsl.txt` / `rsl.xml`

Plus machine-readable AI-licensing declarations: `Content-Usage` (IETF AIPREF), `Content-Signal` (Cloudflare), and RSL `License:` directives.

### Does structured data tell AI systems what this entity is?

- **JSON-LD, Microdata, and RDFa detection** with validation against Schema.org
- **8 ready-to-adapt JSON-LD templates** (Organization, LocalBusiness, Article+Author, Product, SoftwareApplication, WebSite+SearchAction, comparison page, VideoObject)
- **`sameAs` liveness** — every entity link is HEAD-checked, so dead profile links and `href="#"` placeholders surface as findings
- **`@id` graph consistency** across pages
- **YMYL credential gate** — `LegalService`, `MedicalWebPage`, `Physician` and similar are never recommended without verified real-world credentials, because wrong YMYL markup is a manual-action risk
- **Client-side injection caveat** — a CMS that injects JSON-LD via JavaScript is not reported as "no structured data"

### Does the content meet E-E-A-T and freshness expectations?

Experience, Expertise, Authoritativeness, and Trustworthiness are scored against Google's September 2025 Quality Rater Guidelines, including their treatment of AI-generated content and the expanded YMYL definition. A visible corrections/editorial-standards page is scored for publishers.

**Freshness** is extracted from JSON-LD, `<time datetime>`, or `Last-Modified` and tiered: fresh (<90 days), aging, stale, very-stale, **future-dated** (a markup defect, not fresh content), or unknown (undated — AI engines cannot verify recency).

### Is the technical foundation sound?

Server-side rendering (AI crawlers do not execute JavaScript), Core Web Vitals risk, security headers, canonicals, hreflang, sitemaps, redirect chains, mobile parity, meta and Open Graph tags, and RFC 8288 `Link` headers. When a WAF challenges an ordinary browser request, the fetcher retries as a bot and discloses which view was analysed.

### Which AI platform is the site actually losing on?

Per-platform readiness for **Google AI Overviews**, **Google AI Mode**, **ChatGPT**, **Perplexity**, **Gemini**, and **Bing Copilot**, with notes on Grok and DeepSeek. Guidance reflects the 2026 reality: only about 38% of AI Overview citations now come from Google's top 10 results (Ahrefs), so the tool runs a **query fan-out coverage check** — decomposing a page's topic into the sub-queries AI engines actually issue, and reporting which ones the page can answer on its own.

Because roughly 11–12% of cited domains overlap between ChatGPT and Perplexity, per-platform recommendations are genuinely different work rather than one tactic repeated.

### What about brand presence off-site?

Wikipedia and Wikidata are checked via API in **English and Hebrew**, plus Reddit, YouTube, LinkedIn, and review platforms. Every mention is classified with the **Owned / Competitor / Earned Media / PR Wire / Social / Institution** taxonomy — a brand whose only corroboration is its own site and press releases reads as the thin authority it is.

### And `llms.txt`?

Validated and generated — but reported as **informational, not scored**. No major AI platform has confirmed reading it for citation, and a 300,000-domain study found 97% of `llms.txt` files were never fetched. It remains useful for developer-facing sites serving coding agents. GEO Reporter says so plainly rather than selling it.

---

## How do I install it?

### Recommended — Claude Desktop (no terminal required)

This works in both **Claude Code** and **Claude Cowork**.

1. Open Claude Desktop.
2. Click **Customize** (the settings/gear menu).
3. Go to **Personal plugins**.
4. Click **Create marketplace**.
5. Paste this URL:
   ```
   https://github.com/internet-and-sons/geo-reporter
   ```
6. Install the **geo-reporter** plugin from the marketplace that just appeared.
7. In any chat, run this once to install the Python helpers GEO Reporter uses:
   ```
   /geo-reporter:setup
   ```

That's it. You can now type `/geo audit <your-site>` in any Claude chat.

### Alternative — CLI

```
/plugin marketplace add https://github.com/internet-and-sons/geo-reporter
/plugin install geo-reporter
/geo-reporter:setup
```

---

## What can I run?

```
/geo audit https://acme.com       # Full GEO + SEO audit with composite score
/geo quick https://acme.com       # 60-second visibility snapshot
/geo report-pdf                   # Polished PDF you can send to a client
```

| Command | What it does |
|---------|-------------|
| `/geo audit <url>` | Full GEO + SEO audit with parallel analysis |
| `/geo quick <url>` | 60-second GEO visibility snapshot |
| `/geo citability <url>` | Score content for AI citation readiness |
| `/geo crawlers <url>` | Declared AI crawler policy (robots.txt) |
| `/geo botaccess <url>` | **Live** AI crawler reachability probe with WAF detection |
| `/geo integrity <url>` | GEO-spam & prompt-injection scan |
| `/geo agentready <url>` | Agent-readiness & AI-licensing surface check |
| `/geo llmstxt <url>` | Analyze or generate `llms.txt` |
| `/geo brands <url>` | Brand mentions across AI-cited platforms |
| `/geo platforms <url>` | Platform-specific optimization |
| `/geo schema <url>` | Structured data analysis & generation |
| `/geo technical <url>` | Technical SEO audit |
| `/geo content <url>` | Content quality & E-E-A-T assessment |
| `/geo report <url>` | Client-ready markdown report |
| `/geo report-pdf` | Professional PDF report with charts |

For agencies: `/geo prospect`, `/geo proposal`, and `/geo compare` manage client pipelines, generate proposals, and produce month-over-month delta reports.

---

## What does the report look like?

Every report follows a written contract of **13 rules**, because a technically-correct audit that the reader misunderstands is a failed audit:

- **Leads with the decision** — a TL;DR under 150 words carrying the score and the top three actions, each tagged with impact, effort, and owner. Read only that and you still know what to do this week.
- **Closed status vocabulary** — no ambiguous labels. A crawler row says `✅ Confirmed (tested live)` or `❌ Blocked by Cloudflare (mismatch — declared open)`, never "Unverified".
- **Every finding shows its evidence** — quoted observations, not assertions. Findings render as Finding / Evidence / Impact / Fix / Confidence.
- **Fixes are executable** — a paste-ready artifact, or a delegatable task with an owner type and effort estimate.
- **Nothing is guessed** — a check that did not run says "not measured", never a plausible number.
- **Per-language sections** for bilingual sites; raw tables demoted to an appendix.
- **Third-party sites** are labelled "External Observation Only" with no score — you cannot credibly grade a site whose context you do not have.

Output is markdown plus an optional PDF with score gauges, charts, and color-coded tables.

---

## Why does GEO matter?

| Metric | Value | Source |
|--------|-------|--------|
| AI-referred sessions growth | +527% (Jan–May 2025) | SparkToro |
| Search traffic drop projected by 2028 | −50% | Gartner |
| Brand mentions vs backlinks for AI visibility | 3× stronger correlation | Ahrefs (Dec 2025) |
| AI Overview citations from outside Google's top 10 | ~62% | Ahrefs (2026) |
| Cited pages updated within the last ~13 weeks | ~50% | Ahrefs (2026) |
| Domain overlap between ChatGPT and Perplexity citations | 11–12% | Averi (2026) |
| GEO services market | $850M+, projected $7.3B by 2031 | Yahoo Finance / Superlines |

AI search is displacing traditional search. This tool optimizes for where the traffic is going.

---

## Need help?

- Found a bug or have a question? [Open an issue](https://github.com/internet-and-sons/geo-reporter/issues).
- Want to chat? Email [tal@internetandsons.com](mailto:tal@internetandsons.com).

Everything runs locally. No data leaves your machine beyond the page fetches the audit itself makes.

---

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the developer guide, manual install, architecture, scoring methodology, and uninstall steps. The project ships **234 automated tests**; new Python comes with matching tests.

---

## License

MIT License — see [LICENSE](LICENSE) for the full text and the upstream attribution notice.

---

Built for the AI search era.
