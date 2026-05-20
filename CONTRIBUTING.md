# Contributing to GEO Reporter

Thanks for considering a contribution. Bug reports, fixes, new schema templates, platform-readiness updates, and lab-bot reclassifications as the AI search landscape evolves are all in scope and welcome.

## Review cadence

PRs are reviewed within ~7 days. If a week passes without a response, ping the PR — I may have missed the notification.

## How to contribute

### Reporting bugs
- Search [existing issues](https://github.com/internet-and-sons/geo-reporter/issues) first.
- If yours is new, open one with a clear title, a reproducer, and what behaviour you expected vs. what happened. Include the OS, Python version, and Claude Code version when relevant.

### Suggesting features
- Open a feature request issue. A short rationale ("I want this because…") makes triage faster than a long spec.
- For larger ideas, a [Discussion](https://github.com/internet-and-sons/geo-reporter/discussions) is lower-friction than an issue.

### Pull requests
The standard fork-and-PR flow:

1. Fork `internet-and-sons/geo-reporter`, create a topic branch off `main`.
2. Make your change. Keep PRs focused — one logical change per PR.
3. Add or update tests where applicable. Run `python -m pytest tests/` locally.
4. If your change is user-visible, add an entry under `## [Unreleased]` in `CHANGELOG.md`.
5. Open the PR against `main`. Reference any related issue.

## Local development

To iterate on a skill or test someone else's PR without re-installing on every change, use **dev mode**:

```bash
./dev-link.sh
```

This replaces the installed copies under `~/.claude/skills/` with symlinks pointing back into your repo working tree. Edits in the repo (or branch checkouts) are immediately live in Claude Code with no copy step.

**Workflow for testing a PR locally:**

```bash
git fetch origin pull/<N>/head:pr-<N>
git checkout pr-<N>
# /geo commands in Claude Code now run the PR's code.
# Edit, save, re-run /geo — instant feedback.

git checkout main         # back to v0.x main, still live via symlinks
./dev-unlink.sh           # exit dev mode entirely, frozen install
```

Caveats:

- **Whatever branch you have checked out is what Claude Code runs.** Don't run `/geo` audits on real client work while a WIP branch is checked out.
- Your local-only skills (e.g. anything in `~/.claude/skills/` that isn't part of GEO Reporter) stay untouched by `dev-link.sh` / `dev-unlink.sh`.
- For testing multiple PRs in parallel, use `git worktree add ../geo-reporter-pr-<N> pr-<N>`, then run `dev-link.sh` from whichever worktree you want active.

When you're done testing, `./dev-unlink.sh` removes the symlinks and re-installs proper copies via `install.sh` (so your installed skill is frozen at the current branch's state).

## Style guidelines

### Commit messages
- Imperative mood, present tense: "Add X", not "Added X" / "Adds X"
- First line ≤72 chars; blank line; longer body if needed
- Reference issues/PRs in the body, not the subject

### Code
- Match surrounding style. Prefer small, obvious changes over clever ones.
- Don't add abstractions for hypothetical future requirements.

### Skill changes (`skills/*/SKILL.md` and `agents/*.md`)
- Keep the front-matter `name`, `description`, `version`, `allowed-tools` accurate.
- If you're adding scoring logic, document the rubric in the same file.

## Attribution policy

When porting commits from another fork or merging cherry-picks, original authorship is preserved on the commit (`Author:` header). If you're picking up someone else's stalled work, mention them in the PR body so they get credit and a notification.

## Licensing

By submitting a PR, you agree your contribution is licensed under the project's MIT license. The original `zubair-trabzada/geo-seo-claude` upstream copyright is preserved in `LICENSE`; new work is added to that copyright line.

## Manual install (without the plugin marketplace)

The plugin marketplace is the recommended path for users (see [README.md](README.md)). For development or unusual setups, the legacy installer still works.

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

## Project layout

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
├── CONTRIBUTING.md               # This file
└── LICENSE                       # MIT (with upstream attribution)
```

## How it works

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

## Notable subsystems

- **Live AI Crawler Reachability Probe** (`geo-botaccess`) — replays the homepage as each AI crawler user-agent, fingerprints the WAF/CDN (Cloudflare, AWS WAF, Imperva, Akamai, and 13 others), detects Cloudflare JS challenges with optional Playwright fallback, and surfaces declared-vs-actual mismatches as critical findings.
- **AI Crawler Classification** — 17 AI crawlers classified into `training`, `search-index`, `live-retrieval`, `traditional-search`. The "block training, allow retrieval" publisher posture (NYT/WSJ/Reuters/BBC pattern) reads as healthy, not as "partially blocked".
- **Content Signals & Agent-Readiness** — Detects [IETF Content Signals](https://contentsignals.org/), RFC 8288 `Link:` headers (`api-catalog`, `service-doc`, `mcp-server-card`), and Markdown content negotiation (`Accept: text/markdown`).
- **Citability Scoring** — Analyzes content blocks for AI citation readiness. Optimal AI-cited passages are 134–167 words, self-contained, fact-rich.

## Data storage

The CRM and reporting skills (`/geo prospect`, `/geo proposal`, `/geo compare`) store runtime data outside the Claude Code directory:

```
~/.geo-prospects/
├── prospects.json              # Client/prospect pipeline data
├── proposals/                  # Generated proposal documents
└── reports/                    # Monthly delta reports
```

This directory is **not removed** by the uninstaller — delete it manually if you no longer need your prospect data.

## Uninstall

```bash
./uninstall.sh
```

Or manually:

```bash
rm -rf ~/.claude/skills/geo ~/.claude/skills/geo-* ~/.claude/agents/geo-*.md
```

## Versioning & releases

GEO Reporter follows [Semantic Versioning](https://semver.org/). Tagged releases are published on GitHub with notes covering each change.

- [Latest release](https://github.com/internet-and-sons/geo-reporter/releases/latest)
- [All releases](https://github.com/internet-and-sons/geo-reporter/releases)
- [CHANGELOG.md](CHANGELOG.md) — running record in [Keep a Changelog](https://keepachangelog.com/) format

## Questions?

Open a Discussion or email the maintainer (see `git log`).
