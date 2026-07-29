---
name: geo-agentready
description: Agent-readiness and AI-licensing surface check (non-scoring). Probes the emerging 2026 protocol surface — MCP server card, agents.json, RFC 9727 api-catalog, OAuth discovery (RFC 8414/9728), Web Bot Auth signature directory, NLWeb /ask + /mcp, RSL licensing (rsl.txt / License directive), and AIPREF Content-Usage — and reports which of these forward-looking signals a site publishes. Use when the user asks "is my site agent-ready", "can AI agents use my site", "do we support MCP / NLWeb", "check agent readiness", "AI licensing signals", or as the non-scoring agent-readiness appendix of a full audit. Absence of any signal is normal in 2026 and is NEVER penalized.
version: 1.0.0
author: geo-reporter
tags: [geo, agent-readiness, mcp, nlweb, rsl, web-bot-auth, emerging-specs]
allowed-tools: Read, Bash, Write
---

# GEO Agent Readiness — Emerging Protocol Surface Check

## Report Contract (mandatory)

Before writing any output, read `"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/REPORT-CONTRACT.md"` and follow all 11 rules. This skill's entire output is **informational** — contract rule 4 (evidence integrity) applies with special force: name each spec, state plainly that these are emerging standards, and never imply a site is deficient for lacking them.

## Purpose

Websites are growing a second interface: not pages for people, but endpoints and declarations for AI agents. In 2026 this surface is defined by a cluster of young specs — MCP server cards, NLWeb conversational endpoints, RFC 9727 API catalogs, OAuth discovery metadata, Web Bot Auth signature directories, and machine-readable licensing (RSL, AIPREF Content-Usage). Almost no site has all of these; most have none. This skill measures which of them a site publishes, so forward-leaning owners can see their position and everyone else learns the surface exists.

## Workflow

### Step 1 — Run the probe

```bash
python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/fetch_page.py" <url> agentready
```

The JSON output:

| Field | Meaning |
|---|---|
| `checks.<name>` | One entry per probe: `{path, spec, status, found}` |
| `homepage_headers` | `content_usage`, `content_signal`, `link` headers from the homepage |
| `summary.found_count` / `checked_count` | Roll-up |
| `errors[]` | Network failures — render as "not measured", never as absent |

Also run `fetch_page.py <url> robots` and read its `licensing` field: `license_urls` (RSL `License:` directives), `content_usage` (AIPREF rules), `content_signal` (Cloudflare Content Signals) declared in robots.txt.

### Step 2 — Render the report section

Group the results into three plain-language clusters:

**Agent endpoints** (can an AI agent interact with the site programmatically?):
- `mcp_server_card` (MCP SEP-1649), `agents_json`, `nlweb_ask` + `nlweb_mcp` (NLWeb), `api_catalog` (RFC 9727), `oauth_authorization_server` / `oauth_protected_resource` (RFC 8414/9728)

**Bot identity** (can the site verify who's crawling?):
- `web_bot_auth_directory` — Web Bot Auth (RFC 9421 HTTP Message Signatures; IETF WG backed by Cloudflare/OpenAI/Anthropic/Perplexity). Presence means the site can distinguish cryptographically-verified bots from spoofed UAs.

**Licensing declarations** (has the site stated its AI-usage terms machine-readably?):
- `rsl_txt` / `rsl_xml` + robots.txt `License:` directives (RSL 1.0, ~1,500 media orgs)
- robots.txt / header `Content-Usage` (IETF AIPREF draft)
- robots.txt / header `Content-Signal` (Cloudflare Content Signals, 3.8M+ domains)

**Hedge rule for generic paths:** `nlweb_ask` and `nlweb_mcp` probe `/ask` and `/mcp`, which ordinary sites may use for unrelated routes (an FAQ page answering GET /ask with 200 will register `found`). When only these two register and no other agent signal exists, render as "an endpoint responds at /ask (may be an unrelated route)" — never "NLWeb detected". Claim NLWeb only when the endpoint's response is machine-readable (JSON) or corroborated by another agent signal (e.g. an MCP server card).

Per finding, use the contract format. For a typical all-absent result, the whole section can be one finding:

> **Finding:** The site publishes none of the emerging agent-protocol signals — normal for 2026.
> **Evidence:** 10 well-known endpoints probed, 0 found; no licensing directives in robots.txt or headers.
> **Impact:** No action needed today. These specs matter when AI agents start transacting with sites directly; early adoption is a differentiator for developer-facing and commerce sites, not a requirement.
> **Confidence:** Confirmed.

When something IS found, name the spec, show the path, and say what it enables — e.g. an MCP server card means agent clients can discover the site's tools; RSL means the site has machine-readable licensing terms that AI companies can honor programmatically.

### Step 3 — Payment posture (cross-reference)

If the live probe (`geo-botaccess`) reported `payment_required_bots`, mention it here: HTTP 402 + licensing signals together describe the site's **monetization posture** toward AI. Render 402 per the contract legend: 💰 Payment required — a business decision, not a defect.

## Hard rules

1. **Non-scoring, always.** No numeric score. Never a Critical/High severity for absence.
2. **Date the specs.** Every mention carries its status: "RFC" (real standard), "IETF draft", "pre-standard". Do not upgrade a draft to a standard.
3. **Cloudflare context (time-sensitive):** from Sept 15, 2026, Cloudflare blocks AI training bots by default on new ad-supported domains. Sites adopting Cloudflare after that date may be blocking bots without knowing — when the live probe shows unexpected blocks on a recent Cloudflare site, raise this as the likely cause.
4. **Errors are "not measured."** A network failure on a well-known probe renders as "<check> not measured — <reason>", never as "absent".
