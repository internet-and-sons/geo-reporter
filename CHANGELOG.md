# Changelog

All notable changes to GEO Reporter are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

GEO Reporter is a fork of, and is highly influenced by, [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude). Pre-fork history lives on the upstream repository; this changelog documents work as the project carries forward under its own line of development.

## [Unreleased]

## [0.4.0] — 2026-07-29

**Theme: truth refresh + report experience.** Corrects every factually-stale claim identified in the July 2026 gap analysis and introduces a mandatory report contract so audit output is readable and actionable for non-technical users.

### Added

- **Bilingual (English + Hebrew) citability scoring** in [`scripts/citability_scorer.py`](scripts/citability_scorer.py) (PR #26 by [@idoish](https://github.com/idoish)). Each passage is language-detected by Hebrew-character density; Hebrew passages are scored with a Hebrew-tuned engine (gazetteer-based named-entity detection for titles/acronyms/quoted names, Hebrew definition/source/transition/uniqueness pattern packs, `₪`/`ש"ח` currency and `אחוז` percentage detection, niqqud stripping, and a recalibrated 90–120 word optimal-length band). All non-Hebrew content keeps using the original English engine unchanged. Same public functions, five dimensions, weights, and A–F grade bands, so cross-language scores stay comparable.
- **`language` field on `score_passage()` output** and **`language_distribution` on `analyze_page_citability()` output**.
- **`tests/test_citability_scorer.py`** — 20 tests covering language detection, Hebrew normalisation, English-engine behaviour (unchanged), Hebrew named-entity/source/definition/currency/percentage/uniqueness signals, the recalibrated length band, and page-level `language_distribution`.
- **Report contract** (`skills/geo/REPORT-CONTRACT.md`) — 11 rules adopted by geo-audit, geo-report, geo-report-pdf, and all subagent output formats: TL;DR-first, closed status legend (no more "Unverified"), Finding/Evidence/Impact/Fix/Confidence, executable fixes with owner+effort, per-language sections, evidence integrity, before/after rewrites, high-risk gate, YMYL schema guard. Manual eval scenarios in `evals/report-contract-scenarios.md`.
- **2026 bot roster** — MistralAI-User, DuckAssistBot, Google-Agent, Google-CloudVertexBot, Google-NotebookLM, Google-GeminiNotebook (vendor renamed the NotebookLM fetcher; legacy token supported through Aug 2026), and Amazonbot added with vendor-verified UA tokens. New `status` field distinguishes active / retired (anthropic-ai, claude-web, FacebookBot) / opt-out tokens (Google-Extended, Applebot-Extended). Live probe covers active bots only and exposes `excluded_tokens`; robots parser derives from the same roster (split-brain fixed) and flags `stale_tokens`. DeepSeek/Grok honestly documented as unverifiable by UA.
- **Freshness extraction** — `fetch_page.py page` returns `freshness` (dates from JSON-LD `@graph`-aware walk / `<time datetime>` / `Last-Modified`; tiers fresh / aging / stale / very-stale / **future-dated** (markup defect, with ≤1-day skew tolerance for naive-timezone markup) / unknown); scored in geo-content with a per-tier treatment table.
- **Multilingual correctness** — brand_scanner checks Wikipedia/Wikidata in en+he by default (configurable per-language results); `--accept-language` flag on fetch_page (honored in `page` and `full` modes) so bilingual sites' non-English trees are auditable; geo-audit mandates per-language-tree audits with per-language scores.
- Schema templates: `comparison-page.json` (comparison content ≈ the highest-value AI-cited type), `video-object.json`.

### Changed

- **llms.txt downgraded to informational** (no measured citation impact — 97% of llms.txt files never fetched, SE Ranking 300k-domain study); AI Visibility reweighted to Citability 40 / Brand 30 / Crawler Access 30.
- **Platform guidance rewritten for the Google AI Mode era** — rank decoupling (only ~38% of AIO citations from top-10), query fan-out coverage check as the primary AIO lever, Google AI Mode as a distinct surface, Grok/DeepSeek platform notes, freshness (13-week window) as a universal action, 11–12% cross-platform citation overlap noted.
- **Schema guidance** — three guardrails in skill + agent: YMYL credential gate, JS-injected-schema caveat (no more false "no structured data" on CMS sites), platform-nuanced claims (causal-ish for Google grounding, correlational elsewhere).
- **E-E-A-T** — Sept 2025 Quality Rater Guidelines updates (AI-content assessment, YMYL expanded to Government/Civics); corrections/editorial-policy page scored for publishers.
- Citability grade cuts in agent docs aligned to the scorer (A≥80 / B≥65 / C≥50 / D≥35); breakdown key names corrected (`uniqueness_signals`).
- Stale "17 AI crawler" counts replaced with roster-derived phrasing across skills.

### Fixed

- **Wikimedia API calls were silently failing in production** — Wikimedia now returns 403 for browser-spoofed user agents (policy T400119), and both the Wikipedia and Wikidata checks swallowed the error, zeroing the 30-point Wikipedia brand signal for every brand. Now sends a descriptive `GEO-Reporter/0.4` UA.
- Recommended robots.txt no longer includes the retired `anthropic-ai` token; now covers Claude-SearchBot / Claude-User / Perplexity-User / MistralAI-User / DuckAssistBot / Amazonbot / Meta-ExternalAgent.
- `fetch_page.py` CLI no longer crashes with a traceback on malformed invocations (prints usage instead).

### Contributors

- [@idoish](https://github.com/idoish) — bilingual (Hebrew + English) citability scoring engine (PR #26)

## [0.3.5] — 2026-06-01

**Theme: the last three orphans.** Three more packaged scripts that the audit had been hand-doing in markdown for: llms.txt validation, brand mention scanning, and sitemap crawling. All now wired into the orchestrator and the AI Visibility subagent. Closes the orphaned-deep-check audit started in v0.3.2.

### Added

- **`score` field on `validate_llmstxt()` output** — 0 / 30 / 50 / 70 / 90 deterministically derived from boolean validity signals. Skill instructions consume this directly; no hand-scoring.
- **`total_score` field on `generate_brand_report()` output** — 0–100, weighted (Wikipedia 30 + Reddit 20 + YouTube 15 + LinkedIn 10 + Industry 25). API-verified Wikipedia/Wikidata signals populate automatically; the agent enriches the remaining platforms via WebFetch and recomputes the score.
- **`compute_brand_score(report)` helper** in `brand_scanner.py` so the agent can re-score after WebFetch enrichment without duplicating logic.
- **`tests/test_score_fields.py`** — 10 tests covering the canonical scale (0/30/50/70/90 for llms.txt; 0/30/65/100 combinations for brand). Locks in the contracts the skill instructions depend on.

### Changed

- **[`agents/geo-ai-visibility.md`](agents/geo-ai-visibility.md) Step 4 (llms.txt)** — invokes `llmstxt_generator.py <url> validate`; consumes `score`, `format_valid`, `has_title/description/sections/links`, `issues`, `suggestions`, `full_version.exists` by name. Docs corrected to match the actual flat schema (was previously documenting fictional nested fields).
- **[`agents/geo-ai-visibility.md`](agents/geo-ai-visibility.md) Step 5 (brand mentions)** — invokes `brand_scanner.py "<brand>" [domain]`. Documents the **two-pass flow** (Pass 1 = API-verified Wikipedia/Wikidata baseline; Pass 2 = WebFetch enrichment for YouTube/Reddit/LinkedIn/industry → recompute with `compute_brand_score`). No more hand-rolling the Wikipedia API check.
- **[`skills/geo-audit/SKILL.md`](skills/geo-audit/SKILL.md) Phase 1 Step 2 (sitemap crawl)** — invokes `fetch_page.py <url> sitemap` (uses the existing `crawl_sitemap()` which already handles sitemap-index recursion and the 50-page cap); falls back to `internal_links` from Step 1's page-mode output if no sitemap.

## [0.3.4] — 2026-06-01

**Theme: deterministic citability scoring.** Citability is the single largest weight in the GEO Score (25%). The audit was producing it by having Claude hand-score every block in markdown against the five-dimension rubric — non-deterministic, slow, and capped at whatever blocks Claude remembered to score. The packaged `scripts/citability_scorer.py` (`analyze_page_citability(url)`) implements the same rubric deterministically and scores every block ≥20 words. It was orphaned.

### Changed

- **[`agents/geo-ai-visibility.md`](agents/geo-ai-visibility.md) Step 2** — switched from in-markdown rubric to invoking `citability_scorer.py <url>`. Output JSON's `top_5_citable[]` / `bottom_5_citable[]` / `average_citability_score` / `grade_distribution` are consumed by field name; rewrite suggestions are now targeted at the weakest dimension per block (using the per-block `breakdown`).
- **[`skills/geo-citability/SKILL.md`](skills/geo-citability/SKILL.md)** — Analysis Procedure rewritten to invoke the scorer (Step 1) and produce rewrite suggestions from the per-dimension breakdown (Step 2). The rubric stays as reference documentation for what the numbers mean.

### Fixed

- **Non-deterministic citability scores** — two consecutive audits of the same URL now produce identical citability scores. (Hand-scored audits varied by 5–15 points across runs.)
- **Block-coverage gap** — the scorer processes every block ≥20 words. Previously Claude scored 5–10 blocks per page; sites with many shorter passages had most of their content invisible to the audit.

## [0.3.3] — 2026-06-01

**Theme: page-mode by default.** The audit orchestrator and every Phase-2 subagent were fetching the target URL with `WebFetch`, which converts HTML to markdown, strips `<head>` (losing JSON-LD, OG / Twitter Card, meta tags), discards HTTP headers, and silently returns empty pages for JS-rendered SPAs. The packaged `fetch_page.py <url> page` already returns a rich JSON with all of this — it was just orphaned outside `geo-schema`. This release wires it in everywhere.

### Changed

- **[`skills/geo-audit/SKILL.md`](skills/geo-audit/SKILL.md) Phase 1 Step 1** — switched from `WebFetch` to `fetch_page.py page`. Documents the full JSON schema (`title`, `meta_tags`, `heading_structure`, `structured_data[]`, `headers`, `security_headers`, `has_ssr_content`, …) so downstream subagents can consume by field name.
- **[`agents/geo-ai-visibility.md`](agents/geo-ai-visibility.md) Step 1** — page-mode fetch. Citability scoring now works against extracted `text_content` and `heading_structure` rather than re-parsing markdown.
- **[`agents/geo-content.md`](agents/geo-content.md) Step 1** — page-mode fetch. Author byline / publication date detection now prefers `structured_data[]` (`Article.author`, `Article.datePublished`) over text-pattern matching.
- **[`agents/geo-technical.md`](agents/geo-technical.md) Step 1** — page-mode fetch. **Biggest win here**: technical SEO checks were previously running against zero HTTP headers (because `WebFetch` discards them). Now `status_code`, `headers`, `redirect_chain`, and `security_headers` are all available.
- **[`agents/geo-platform-analysis.md`](agents/geo-platform-analysis.md)** — added Step 0 documenting that it should consume the orchestrator's Phase 1 fetch when run via `/geo audit`, or fetch with `fetch_page.py page` when standalone.

### Fixed

- **JS-rendered SPAs were silently misread as empty** — `WebFetch` doesn't execute JavaScript, so every subagent saw an empty page and reported "no content", "no schema", "no headings", etc. The packaged fetcher exposes a `has_ssr_content` flag (`false` = JS-rendered without SSR), so subagents now flag this as a critical AI-visibility issue rather than producing a false catastrophic audit.
- **OG / Twitter Card tags were systematically reported as missing** — they live in `<head>`, which `WebFetch` strips. Now read from `meta_tags`.
- **Security headers (CSP, HSTS, X-Frame-Options, …) and `Link:` headers were invisible** — `WebFetch` discards response headers. Now read from `headers` / `security_headers`.

## [0.3.2] — 2026-06-01

**Theme: live probe by default.** A real-world audit (`law.co.il`, fully permissive robots.txt) revealed that `/geo audit` was reporting every AI crawler as "⚠️ Unverified" — because the orchestrator was never invoking the live reachability probe, and the subagent doing AI Crawler Access was hand-rolling robots.txt parsing that mis-handled `User-agent: *` wildcards. Manual `curl -A "GPTBot/1.0" -I` confirmed every bot returned `200 OK`. This release closes the gap.

### Changed

- **`/geo audit` now invokes the live probe** ([`skills/geo-audit/SKILL.md`](skills/geo-audit/SKILL.md)) — Phase 2's AI Visibility subagent runs `fetch_page.py ... bots` (same engine as the standalone `geo-botaccess` skill) as the primary signal for crawler access. The static robots.txt analysis becomes a secondary "declared policy" signal used only to surface declared-vs-actual mismatches.
- **`geo-ai-visibility` Step 3 rewritten** ([`agents/geo-ai-visibility.md`](agents/geo-ai-visibility.md)) to (a) run the live probe first, (b) call the packaged `fetch_robots_txt()` parser via `fetch_page.py ... robots` rather than hand-rolling robots.txt parsing, and (c) reconcile the two signals into a table that flags declared-vs-actual mismatches (e.g. permissive robots.txt + Cloudflare 403 = critical WAF override). Output table now shows both Live and Declared columns.
- **`geo-crawlers` Step 0 added** ([`skills/geo-crawlers/SKILL.md`](skills/geo-crawlers/SKILL.md)) — live probe runs first, declared-policy parse second. Step 1 now mandates delegating to the packaged parser and explicitly documents that `ALLOWED_BY_DEFAULT` (wildcard-permitted) means "Allowed via wildcard", not "Unknown".
- **`geo-technical` no longer duplicates crawler access analysis** — that's now exclusively Subagent 1's job (avoids divergent verdicts in the final report).

### Fixed

- **False "Unverified" status on fully permissive robots.txt** — the previous skill instructions told Claude to classify any AI bot not explicitly named as "Unknown" / "Not mentioned" even when `User-agent: *` + empty `Disallow:` clearly permits everything. Now the parser's `ALLOWED_BY_DEFAULT` verdict is rendered as "Allowed (via wildcard)".
- **Missed WAF overrides** — sites with permissive robots.txt but a Cloudflare/WAF rule that 403s AI crawlers would previously pass the audit. The live probe surfaces this as a CRITICAL declared-vs-actual mismatch.

### Added

- **`tests/test_fetch_robots_txt.py`** — 8 tests covering wildcard inheritance (`ALLOWED_BY_DEFAULT`, `BLOCKED_BY_WILDCARD`), named-bot overrides, `NO_ROBOTS_TXT`, `NOT_MENTIONED`, and sitemap extraction. Locks in the parser behavior the skill instructions now depend on. (68/68 tests pass.)

## [0.3.1] — 2026-05-21

**Theme: plugin distribution.** The repo is now installable as a Claude Code plugin from a marketplace, and the README is rewritten for non-technical Claude Desktop users (Customize → Personal plugins → Create marketplace). The legacy `./install.sh` path is preserved for development and unusual setups.

(0.3.0 was a transient state — bumped in the manifests but never tagged. The post-review cleanup made up the difference; this is the first tagged 0.3.x release.)

### Added

- **Claude Code plugin support** — repo is installable as a plugin via `/plugin marketplace add https://github.com/internet-and-sons/geo-reporter` followed by `/plugin install geo-reporter`. Adds `.claude-plugin/plugin.json` (plugin manifest) and `.claude-plugin/marketplace.json` (marketplace descriptor).
- **`geo-reporter-setup` skill** — one-time `/geo-reporter:setup` command that installs Python dependencies after first install. Uses `python3 -m pip` to avoid interpreter-mismatch issues on macOS. Step 4 separately installs the Playwright Chromium browser binary (the Python package itself ships via `requirements.txt`).
- **Non-technical README rewrite** — leads with the Claude Desktop UI install flow; CLI shown as alternative. Developer reference (manual install, project layout, How it works, scoring methodology, data storage, uninstall, releases) moved to `CONTRIBUTING.md`.

### Changed

- **Main skill location** — `geo/SKILL.md` moved to `skills/geo/SKILL.md` to follow plugin layout convention. `install.sh`, `dev-link.sh`, and `dev-unlink.sh` updated accordingly.
- **Script paths in skills and agents** — `geo-botaccess`, `geo-schema`, `geo-technical`, `geo-report-pdf`, the main `geo` skill, and the `geo-schema` agent now reference Python scripts via `"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/..."`. The fallback preserves the legacy `./install.sh` path when running outside the plugin runtime.
- **Repo URL canonicalised** — `install.sh`, `install-win.sh`, `README.md`, `CONTRIBUTING.md`, and `CHANGELOG.md` link refs all point to `internet-and-sons/geo-reporter` (the active fork's actual remote) instead of stale `tzvister/geo-reporter` references.

### Fixed

- **`agents/geo-schema.md` stale script path** — the schema subagent in `/geo audit` still pointed at `~/.claude/skills/geo/scripts/fetch_page.py`, which doesn't exist under a plugin install. Updated to use the same `${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}` fallback.
- **Legacy `./install.sh` flow** — bare `${CLAUDE_PLUGIN_ROOT}` in skill bash blocks expanded to an empty string outside the plugin runtime, producing commands like `python "/scripts/fetch_page.py"`. All five affected skills now use the fallback pattern so both install paths work.
- **`dev-link.sh` / `dev-unlink.sh` sanity check** — both scripts looked for `geo/SKILL.md` at the repo root and exited with "Run this from the geo-reporter repo root" after the v0.3 directory move. Updated to `skills/geo/SKILL.md`.
- **`geo-reporter-setup` Playwright step** — Step 4 previously ran `pip install playwright` (already installed via `requirements.txt` in Step 2) before downloading the Chromium binary. The redundant `pip install` is removed; only the binary download remains.

## [0.2.0] — 2026-04-27

**Theme: community integration.** Every open contribution from upstream that's still useful has been ported in (with author attribution preserved on each commit), the project's contribution surface is now operational (CONTRIBUTING.md, CHANGELOG, automated review), and the workflow that runs Claude on PRs has been hardened through 4 iterations of empirical testing.

### Added

- **Content Signals check** ([#4](https://github.com/tzvister/geo-reporter/pull/4)) — non-scoring scan for `Content-Signal:` directives in robots.txt (IETF draft `draft-romm-aipref-contentsignals`). Surfaced in `geo-crawlers` Step 6 and `geo-ai-visibility` Step 3. Reuses the already-fetched robots.txt, no extra HTTP request. Ports work by [@an-morgan](https://github.com/an-morgan).
- **Agent-readiness signals in `geo-technical`** ([#4](https://github.com/tzvister/geo-reporter/pull/4)) — RFC 8288 `Link:` header parsing for `api-catalog` / `service-doc` / `mcp-server-card` rel types (no extra request, captured in the existing Step 1 fetch), plus an opt-in `Accept: text/markdown` content-negotiation probe (one extra request, non-penalising). Both are non-scoring.
- **`ai-input` recognised as a Content-Signal key** ([#7](https://github.com/tzvister/geo-reporter/pull/7)) — used in production by cloudflare.com alongside the IETF draft's keys. Empirically validated against the canonical reference site.
- **`CONTRIBUTING.md`** ([#6](https://github.com/tzvister/geo-reporter/pull/6)) — review-cadence SLA (~7 days), fork-and-PR flow, attribution policy for ported commits, MIT licensing note. Adapted from upstream PR #44 by [@ahernandez-developer](https://github.com/ahernandez-developer); commit author preserved.
- **Claude PR review workflow** ([#8](https://github.com/tzvister/geo-reporter/pull/8), iterated through #10–#13) — `.github/workflows/claude-review.yml` runs Claude on PRs labelled `needs-review`. Manual-trigger only (outside contributors cannot self-trigger), path-filtered to skip docs-only PRs, capped at 25 turns per review (~$0.20–0.50 per run, 2–5 min runtime). Posts inline comments via the GitHub MCP tool plus a summary comment. Uses Sonnet for code-review depth.
- **`needs-review` label** for opting PRs into the Claude review workflow.
- **Repo metadata** — Issues and Discussions enabled; About description, topics, and homepage URL refreshed.

### Changed

- **Report filenames now include the audited domain slug** ([#5](https://github.com/tzvister/geo-reporter/pull/5)) — `GEO-CLIENT-REPORT-<DOMAIN-SLUG>.md` and `GEO-REPORT-<DOMAIN-SLUG>.pdf` (e.g. `acme.com` → `ACME-COM`). Fixes silent overwrites when running multiple audits in the same directory. Convention propagated through `geo/SKILL.md`, `skills/geo-report/SKILL.md`, and `skills/geo-report-pdf/SKILL.md`.

### Fixed

- **Broken `geo-llms-txt` skill reference** ([#3](https://github.com/tzvister/geo-reporter/pull/3) — upstream PR [#50](https://github.com/zubair-trabzada/geo-seo-claude/pull/50) by [@xiaolai](https://github.com/xiaolai)) — `skills/geo-report/SKILL.md` referenced a non-existent skill, silently dropping llms.txt assessment from generated reports. Corrected to `geo-llmstxt`.
- **Pin `rich<14.0.0`** ([#3](https://github.com/tzvister/geo-reporter/pull/3) — upstream PR [#54](https://github.com/zubair-trabzada/geo-seo-claude/pull/54)) — the previous `<15.0.0` constraint allowed silent major-version bumps to rich 14.x.

### Security

- **Disable Flask debug mode by default** ([#3](https://github.com/tzvister/geo-reporter/pull/3) — upstream PR [#51](https://github.com/zubair-trabzada/geo-seo-claude/pull/51)) — `scripts/webapp/app.py` previously hardcoded `debug=True`, exposing the Werkzeug interactive debugger (RCE-equivalent if reachable). Now opt-in via `FLASK_DEBUG=true` env var.
- **Validate URL scheme in `fetch_page()`** ([#3](https://github.com/tzvister/geo-reporter/pull/3) — upstream PR [#52](https://github.com/zubair-trabzada/geo-seo-claude/pull/52)) — reject `file://` / `ftp://` / non-http schemes before any network call. Closes the SSRF vector when caller-supplied URLs reach `requests.get(allow_redirects=True)`.
- **Extend URL-scheme guard to `probe_ai_crawlers()`** ([#3](https://github.com/tzvister/geo-reporter/pull/3)) — same threat model as `fetch_page()`, same defence applied.
- **Domain-pin URLs in `llmstxt_generator`** ([#3](https://github.com/tzvister/geo-reporter/pull/3) — upstream PR [#53](https://github.com/zubair-trabzada/geo-seo-claude/pull/53)) — second-pass description fetcher previously trusted URLs discovered during crawl. Now skips cross-origin URLs (still emits the link in llms-full.txt, just doesn't fetch a description for it).
- **Bound stdin reads in `generate_pdf_report.py`** ([#3](https://github.com/tzvister/geo-reporter/pull/3) — upstream PR [#54](https://github.com/zubair-trabzada/geo-seo-claude/pull/54)) — 10 MB ceiling with overflow detection (`read(N+1)` pattern). Prevents OOM from oversized stdin pipes.

### Contributors

Upstream work ported with author attribution preserved on the commits:

- [@xiaolai](https://github.com/xiaolai) — five security/bug fixes via NLPM
- [@an-morgan](https://github.com/an-morgan) — Content Signals + agent-readiness checks
- [@ahernandez-developer](https://github.com/ahernandez-developer) — CONTRIBUTING.md scaffold

Plus the original [zubair-trabzada/geo-seo-claude](https://github.com/zubair-trabzada/geo-seo-claude) upstream, whose work this fork was built on.

## [0.1.0] — 2026-04-27

Inaugural release of GEO Reporter as a distinct project.

### Added

- **Live AI crawler reachability probe** (`geo-botaccess` skill, `bots` mode of `scripts/fetch_page.py`). Replays the homepage as each AI crawler user-agent, fingerprints the WAF/CDN, detects Cloudflare JS challenges with optional Playwright fallback, and surfaces declared-vs-actual mismatches as critical findings. Detects 16+ WAF/CDN products with product-specific remediation playbooks.
- **Bot-class taxonomy.** AI crawlers are now classified into four classes — `live-retrieval`, `search-index`, `traditional-search`, `training` — so the GEO impact of blocking can be scored accurately. Per-class scores plus a `HEALTHY_PUBLISHER` verdict so the canonical "block training, allow retrieval" publisher posture (NYT/WSJ/Reuters/BBC pattern) reads as healthy.
- **New AI crawler probes:** OAI-SearchBot, Claude-SearchBot, Claude-User, Perplexity-User. Bot count 13 → 17.
- `BOT_CLASSES` constant and `class` + `operator` fields on every probe in the JSON output.
- 8 new tests covering bot-class metadata, canonical class assignments, and verdict-logic across OPEN / HEALTHY_PUBLISHER / PARTIALLY_BLOCKED / MOSTLY_BLOCKED / BLOCKED postures (60 tests total, all passing).
- LICENSE: NOTICE-style preamble explaining the fork relationship; preserves Zubair Trabzada's original copyright (MIT requirement) and adds Tal Oron + contributors.
- README: "Highly influenced by" attribution block linking to the upstream project.
- This `CHANGELOG.md`.

### Changed

- **Project rename: `geo-seo-claude` → `geo-reporter`.** Install URLs, repository URL, banner alt text, sub-skill `author:` frontmatter, and rendered output strings all updated.
- Banner SVG: replaced the "SEO" block-letters row with a "REPORTER" wordmark in the same gradient.
- README description and architecture tree updated for the new project identity.
- `scripts/fetch_page.py`: `AI_CRAWLERS` restructured from `name -> ua` to `name -> {ua, class, operator}`. `AI_SEARCH_BOTS` retained as a derived back-compat alias.
- `scripts/fetch_page.py`: `probe_ai_crawlers()` now emits per-class scores, an overall score weighted `0.5·retrieval + 0.35·traditional + 0.15·training`, and a `verdict` field.
- `geo-botaccess/SKILL.md`: new "Bot classes" section explaining the four-class taxonomy and GEO-impact ranking; per-class report tables; explicit "do not recommend unblocking training" rule; edge-case notes on legacy `anthropic-ai` and signals-only `Google-Extended`/`Applebot-Extended`.
- `geo-technical/SKILL.md`: bot count and output-field references updated.
- User-facing strings in `scripts/generate_pdf_report.py`, `scripts/crm_dashboard.py`, `scripts/brand_scanner.py`, and `scripts/webapp/templates/*.html` rebranded.

### Removed

- Upstream-author Skool community funnel section in README, replaced with a neutral Contributing stub.
- `geo-seo-claude` branding from rendered output across CLI banners, PDF report headers, and webapp page titles.

[Unreleased]: https://github.com/internet-and-sons/geo-reporter/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.4.0
[0.3.5]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.3.5
[0.3.4]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.3.4
[0.3.3]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.3.3
[0.3.2]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.3.2
[0.3.1]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.3.1
[0.2.0]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.2.0
[0.1.0]: https://github.com/internet-and-sons/geo-reporter/releases/tag/v0.1.0
