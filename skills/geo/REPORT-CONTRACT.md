# GEO Reporter — Report Contract

Every user-facing audit output (geo-audit, geo-report, geo-report-pdf, and each
subagent's report section) MUST follow these rules. The reader is assumed
non-technical. The report is the product.

## 1. Lead with the decision

The report opens with a TL;DR of at most 150 words:
- Composite score, plus delta vs. the previous audit if one exists.
- The top 3 actions, each with expected impact (High/Medium/Low) and effort
  (minutes/hours/days).
- One sentence of overall posture in plain language.

A reader who stops after the TL;DR must still know what to do this week.

## 2. Closed status vocabulary

Every status label comes from this legend, printed with the table that uses it.
No other status labels are permitted. "Unverified" is banned.

| Label | Meaning |
|---|---|
| ✅ Confirmed (tested live) | We made the request and observed success |
| ❌ Blocked by <product> (mismatch — declared open) | robots.txt permits the bot but the WAF/CDN rejects it. CRITICAL |
| ❌ Blocked (declared, intentional) | robots.txt blocks it; fine when it matches a stated posture |
| 💰 Payment required (HTTP 402 — site monetizes AI access) | The site demands payment per crawl (e.g. Cloudflare pay-per-crawl). Not a block and not a misconfiguration — report as a monetization posture |
| ⚠️ Content differs for bots | Bot receives a different body than a browser does |
| — Not tested (<reason>) | e.g. "opt-out token — never fetches", "probe unavailable" |

## 3. Finding format (mandatory)

Every finding renders as:
**Finding** — one sentence, plain language.
**Evidence** — what was actually observed, quoted ("GPTBot received HTTP 200,
byte-identical to Chrome").
**Impact** — why the reader should care, in reader terms, including "no action
needed" when that is the truth.
**Fix** — see rule 5. Omit for no-action findings.
**Confidence** — Confirmed | Likely | Hypothesis.

## 4. Evidence integrity

No claim without a named check that ran. If a check did not run, render
"<metric> not measured — <what would measure it>" — never a guessed value,
never an ominous blank.

## 5. Executable fixes

Every Critical/High fix ships as either:
- a paste-ready artifact (robots.txt block, JSON-LD snippet, llms.txt file), or
- a delegatable task with owner-type (developer | content | marketing) and
  effort tag (minutes | hours | days).
Content fixes include a brief: proposed title, structure, and who currently
wins that query (displacement evidence).

## 6. Before/after demonstration

Every content-rewrite recommendation shows: the current passage, the rewritten
citable version, one line on why the rewrite wins.

## 7. Per-language sections

Bilingual/multilingual sites get separate scores, findings, and action lists
per language tree. Never blend languages into one score.

## 8. Progressive disclosure

Main body is narrative. Raw tables (per-bot matrices, all-blocks scores,
header dumps) go to appendices. PDF mirrors the same hierarchy.

## 9. Delta-first on repeat audits

If a previous audit exists, the report leads with what changed:
Fixed / Regressed / New — before restating standing findings.

## 10. High-risk gate

Changes to robots.txt, noindex, canonicals, or redirects are described in
plain language with consequences BEFORE any code block is shown, and the code
is only rendered after the user confirms they want it.

## 11. YMYL schema guard

Never recommend LegalService, MedicalWebPage, Physician, MedicalClinic, or
FinancialProduct schema unless the report also verifies the site displays the
corresponding real-world credentials. When unverified, recommend the generic
parent type (Organization / ProfessionalService) and say why.

## 12. Evaluator self-check before delivery

Before delivering any report, run this 8-point self-check and fix any failure first:
1. Every Critical/High finding has Evidence quoting a real observation.
2. The composite score matches the findings distribution (no "72/100" over a wall of Criticals).
3. No fabricated or guessed metric — anything not measured says "not measured".
4. No YMYL schema (LegalService/Medical*/FinancialProduct) recommended without a credential check (rule 11).
5. No duplicate findings.
6. Scope respected — the report answers what was asked, no unrequested rewrites.
7. Every fix names a specific element / file / rule, not "improve your content".
8. High-risk code (robots.txt, noindex, redirects, canonicals) is described before it is shown, and withheld pending confirmation (rule 10).

## 13. Internal vs. external mode

Determine whose site this is before scoring:
- **Internal** (the user owns it): full scored audit, full crawl, Execute-mode fixes.
- **External** (a competitor or third-party URL): label the report **"External Observation Only"**, cap the crawl at homepage + ≤20 pages, and present **no /100 score** — you cannot credibly score a site whose context, goals, and constraints you don't have. Surface observations and opportunities, not a grade.

When it is ambiguous, ask: "Is this your own site, or a competitor's / third party's?" A prospect's site being audited before engagement is **External** until they are a client.
