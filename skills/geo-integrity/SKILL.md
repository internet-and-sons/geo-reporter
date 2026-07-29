---
name: geo-integrity
description: Content-integrity scan (non-scoring) — detects GEO-spam and prompt-injection aimed at AI crawlers: hidden text, LLM-directed instructions in comments/aria-hidden/data attributes, invisible zero-width characters, and cloaked keyword-stuffed blocks. Use when the user asks "is my site clean", "check for AI spam / prompt injection", "did someone inject instructions", "content integrity", "hidden text check", or as the integrity appendix of a full audit. Every result is a SIGNAL for review, never proof of intent.
version: 1.0.0
author: geo-reporter
tags: [geo, integrity, prompt-injection, geo-spam, hidden-text, security]
allowed-tools: Read, Bash, Write
---

# GEO Content Integrity — GEO-Spam & Prompt-Injection Scan

## Report Contract (mandatory)

Before writing any output, read `"${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/REPORT-CONTRACT.md"` and follow all rules. This scan is **non-scoring** and every finding is a *signal for review*, never an accusation — contract rule 4 (evidence integrity) and the framing rule below are load-bearing.

## Purpose

Some sites carry content designed to manipulate AI crawlers rather than inform human readers: text hidden with CSS, instructions to the model buried in HTML comments or `aria-hidden` blocks, invisible zero-width characters, keyword-stuffed cloaked sections. This may be deliberate (an SEO/GEO-spam vendor), accidental (a plugin injecting junk), or a false positive (a legitimate edge case). This scan surfaces the signals; a human decides what they mean.

## Workflow

### Step 1 — Run the scan

```bash
python "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/geo}/scripts/fetch_page.py" <url> integrity
```

Output:

| Field | Meaning |
|---|---|
| `findings[]` | Each: `{type, severity, evidence, location}` — the quoted offending text and where it sits |
| `counts` | Per-type roll-up (hidden_text, llm_instruction, zero_width, cloaked_keywords) |
| `summary` | One-line plain-language roll-up |

Finding types: **hidden_text** (high — CSS-hidden text of 8+ words), **llm_instruction** (high — imperative text aimed at models, in comments / aria-hidden / data-attributes), **zero_width** (medium — invisible Unicode inside visible text), **cloaked_keywords** (medium — hidden keyword-stuffed block).

### Step 2 — Render, under the framing rule

**The framing rule (non-negotiable):** every finding is presented as "review this — static analysis cannot prove intent." Never write "your site is spamming" or "you are manipulating AI." Use the contract's Finding/Evidence/Impact/Fix/Confidence format, with **Confidence: Likely** at most (never Confirmed — we confirmed the pattern exists, not that it is malicious).

Example rendering of a clean result (the common case):

> **Finding:** No content-integrity signals detected.
> **Evidence:** Scanned for hidden text, model-directed instructions, invisible characters, and cloaked keyword blocks — none found.
> **Impact:** No action needed.
> **Confidence:** Confirmed. (A clean scan IS confirmable; a flagged one is only "Likely" a problem.)

Example rendering of a flagged result:

> **Finding:** A hidden text block and an instruction aimed at AI models were found — worth reviewing.
> **Evidence:** `<p style="display:none">…</p>` containing "[quoted evidence]"; an HTML comment reading "[quoted evidence]".
> **Impact:** If deliberate, this is the kind of manipulation that gets a site demoted or distrusted by AI search once detected. If it came from a plugin or template, it is still worth removing. We cannot tell which from the markup alone.
> **Fix:** Review the two elements at [location]. If you did not intentionally place them, remove them and check what generated them (a plugin, a theme, a prior SEO vendor). Developer task, minutes.
> **Confidence:** Likely.

### Step 3 — Cross-reference

If run inside a full audit, the integrity block sits in the Content or a dedicated Integrity section. A clean scan is a small positive trust signal worth stating; flagged signals are their own findings.

## Hard rules

1. **Non-scoring.** No number. A flagged site is not "lower quality" by score — it has signals to review.
2. **Signal, not verdict.** Maximum Confidence on any flagged finding is **Likely**. Static HTML analysis cannot read intent.
3. **Always quote evidence.** Every flagged finding shows the actual offending text/attribute and its location — the reader must be able to find and judge it themselves.
4. **Name the innocent explanations.** Plugins, themes, inherited SEO vendors, and legitimate edge cases all produce these patterns. Say so.
