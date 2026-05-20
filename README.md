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

## What this does

GEO Reporter audits your website's visibility in AI search engines — ChatGPT, Claude, Perplexity, Google AI Overviews, and Bing Copilot — and gives you a client-ready report with concrete fixes.

You point it at a URL. It runs the audit. You get back a score (0–100), a prioritized action plan, and a PDF report you can hand to a client or your team.

No setup beyond installing the plugin once.

---

## Install

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

If you prefer the terminal:

```
/plugin marketplace add https://github.com/internet-and-sons/geo-reporter
/plugin install geo-reporter
/geo-reporter:setup
```

---

## What you can do

Once installed, open a Claude chat and type any of these:

```
/geo audit https://acme.com       # Full GEO + SEO audit with composite score
/geo quick https://acme.com       # 60-second visibility snapshot
/geo report-pdf                   # Generate a polished PDF you can send to a client
```

### All commands

| Command | What It Does |
|---------|-------------|
| `/geo audit <url>` | Full GEO + SEO audit with parallel analysis |
| `/geo quick <url>` | 60-second GEO visibility snapshot |
| `/geo citability <url>` | Score content for AI citation readiness |
| `/geo crawlers <url>` | Check which AI crawlers can access the site |
| `/geo llmstxt <url>` | Analyze or generate `llms.txt` |
| `/geo brands <url>` | Scan brand mentions across AI-cited platforms |
| `/geo platforms <url>` | Platform-specific optimization (ChatGPT, Perplexity, AIO) |
| `/geo schema <url>` | Structured data analysis & generation |
| `/geo technical <url>` | Technical SEO audit |
| `/geo content <url>` | Content quality & E-E-A-T assessment |
| `/geo report <url>` | Generate a client-ready markdown report |
| `/geo report-pdf` | Generate a professional PDF report with charts |

For agencies tracking pipelines: `/geo prospect`, `/geo proposal`, and `/geo compare` manage client lists, generate proposals, and produce month-over-month delta reports.

---

## What you'll get

- A **GEO Score** between 0 and 100 — a single number telling you how AI-search-ready the site is.
- A **prioritized action plan** — what to fix first, second, third, with the expected impact of each.
- A **client-ready PDF** with score gauges, bar charts, platform-readiness visualizations, and color-coded tables.

Everything is local. No data leaves your machine other than the page fetches the audit itself makes.

---

## Need help?

- Found a bug or have a question? [Open an issue](https://github.com/internet-and-sons/geo-reporter/issues).
- Want to chat? Email [tal@internetandsons.com](mailto:tal@internetandsons.com).

---

## Why GEO matters

| Metric | Value |
|--------|-------|
| GEO services market | $850M+ (projected $7.3B by 2031) |
| AI-referred traffic growth | +527% year-over-year |
| AI traffic conversion rate vs organic | 4.4x higher |
| Gartner: search traffic drop by 2028 | -50% |
| Brand mentions vs backlinks for AI | 3x stronger correlation |
| Marketers investing in GEO | Only 23% |

AI search is eating traditional search. This tool optimizes for where traffic is going, not where it was.

---

## For developers

The rest of this document is reference material for contributors and anyone installing without the plugin marketplace.

### Manual install (without the plugin system)

One-command install (macOS/Linux):

```bash
curl -fsSL https://raw.githubusercontent.com/internet-and-sons/geo-reporter/main/install.sh | bash
```

Manual install:

```bash
git clone https://github.com/internet-and-sons/geo-reporter.git
cd geo-reporter
./install.sh
```

Windows (Git Bash — not PowerShell/CMD):

```bash
# One-command install
curl -fsSL https://raw.githubusercontent.com/internet-and-sons/geo-reporter/main/install-win.sh | bash

# Or manual
git clone https://github.com/internet-and-sons/geo-reporter.git
cd geo-reporter
./install-win.sh
```

Requirements: Python 3.8+, Claude Code CLI, Git. Optional: Playwright (for screenshots).

### Architecture

```
geo-reporter/
├── .claude-plugin/
│   ├── plugin.json               # Plugin manifest
│   └── marketplace.json          # Marketplace descriptor
├── skills/                       # 16 skills (main + 15 specialized)
│   ├── geo/                      # Main skill orchestrator
│   ├── geo-reporter-setup/       # First-run Python deps installer
│   ├── geo-audit/                # Full audit orchestration & scoring
│   ├── geo-botaccess/            # Live AI crawler reachability probe
│   ├── geo-citability/           # AI citation readiness scoring
│   ├── geo-crawlers/             # AI crawler access + Content Signals
│   ├── geo-llmstxt/              # llms.txt analysis & generation
│   ├── geo-brand-mentions/       # Brand presence on AI-cited platforms
│   ├── geo-platform-optimizer/   # Platform-specific optimization
│   ├── geo-schema/               # Structured data
│   ├── geo-technical/            # Technical SEO + agent-readiness
│   ├── geo-content/              # Content quality & E-E-A-T
│   ├── geo-report/               # Markdown report generation
│   ├── geo-report-pdf/           # PDF report with charts
│   ├── geo-prospect/             # CRM-lite prospect pipeline
│   ├── geo-proposal/             # Auto-generate client proposals
│   └── geo-compare/              # Monthly delta tracking
├── agents/                       # 5 parallel subagents
├── scripts/                      # Python utilities
├── schema/                       # JSON-LD templates
├── tests/                        # pytest suite (60 tests)
├── .github/workflows/            # Claude PR review automation
├── install.sh                    # Legacy installer
├── uninstall.sh                  # Uninstaller
├── requirements.txt              # Python dependencies
├── CHANGELOG.md                  # Release history (Keep a Changelog)
├── CONTRIBUTING.md               # Contribution guidelines
└── LICENSE                       # MIT (with upstream attribution)
```

### How it works

**Full audit flow** — when you run `/geo audit https://example.com`:

1. **Discovery** — Fetches homepage, detects business type, crawls sitemap.
2. **Parallel analysis** — Launches 5 subagents simultaneously:
   - AI Visibility (citability, crawlers, llms.txt, brand mentions)
   - Platform Analysis (ChatGPT, Perplexity, Google AIO readiness)
   - Technical SEO (Core Web Vitals, SSR, security, mobile)
   - Content Quality (E-E-A-T, readability, freshness)
   - Schema Markup (detection, validation, generation)
3. **Synthesis** — Aggregates scores into a composite GEO Score (0–100).
4. **Report** — Outputs a prioritized action plan with quick wins.

**Scoring methodology**:

| Category | Weight |
|----------|--------|
| AI Citability & Visibility | 25% |
| Brand Authority Signals | 20% |
| Content Quality & E-E-A-T | 20% |
| Technical Foundations | 15% |
| Structured Data | 10% |
| Platform Optimization | 10% |

### Notable subsystems

- **Live AI Crawler Reachability Probe** (`geo-botaccess`) — replays the homepage as each AI crawler user-agent, fingerprints the WAF/CDN (Cloudflare, AWS WAF, Imperva, Akamai, and 13 others), detects Cloudflare JS challenges with optional Playwright fallback, and surfaces declared-vs-actual mismatches as critical findings.
- **AI Crawler Classification** — 17 AI crawlers classified into `training`, `search-index`, `live-retrieval`, `traditional-search`. The "block training, allow retrieval" publisher posture (NYT/WSJ/Reuters/BBC pattern) reads as healthy, not as "partially blocked".
- **Content Signals & Agent-Readiness** — Detects [IETF Content Signals](https://contentsignals.org/), RFC 8288 `Link:` headers (`api-catalog`, `service-doc`, `mcp-server-card`), and Markdown content negotiation (`Accept: text/markdown`).
- **Citability Scoring** — Analyzes content blocks for AI citation readiness. Optimal AI-cited passages are 134–167 words, self-contained, fact-rich.

### Data storage

The CRM and reporting skills (`/geo prospect`, `/geo proposal`, `/geo compare`) store runtime data outside the Claude Code directory:

```
~/.geo-prospects/
├── prospects.json              # Client/prospect pipeline data
├── proposals/                  # Generated proposal documents
└── reports/                    # Monthly delta reports
```

This directory is **not removed** by the uninstaller — delete it manually if you no longer need your prospect data.

### Uninstall

```bash
./uninstall.sh
```

Or manually:

```bash
rm -rf ~/.claude/skills/geo ~/.claude/skills/geo-* ~/.claude/agents/geo-*.md
```

### Versioning & releases

GEO Reporter follows [Semantic Versioning](https://semver.org/). Tagged releases are published on GitHub with notes covering each change.

- [Latest release](https://github.com/internet-and-sons/geo-reporter/releases/latest)
- [All releases](https://github.com/internet-and-sons/geo-reporter/releases)
- [CHANGELOG.md](CHANGELOG.md) — running record in [Keep a Changelog](https://keepachangelog.com/) format

### Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). Bug reports, new bot-class definitions as labs publish them, schema additions, and platform-readiness updates are all in scope.

---

## License

MIT License — see [LICENSE](LICENSE) for the full text and the upstream attribution notice.

---

Built for the AI search era.
