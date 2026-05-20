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

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the developer guide, manual install instructions, architecture, scoring methodology, and uninstall steps.

---

## License

MIT License — see [LICENSE](LICENSE) for the full text and the upstream attribution notice.

---

Built for the AI search era.
