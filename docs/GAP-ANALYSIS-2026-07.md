# GEO Reporter — Deep Gap Analysis (July 2026)

**Baseline:** v0.3.5 (2026-06-01)
**Date:** 2026-07-29
**Method:** three parallel research streams — (1) exhaustive read of [mykpono/ultimate-seo-geo](https://github.com/mykpono/ultimate-seo-geo) v1.9.0 including its 35 scripts, 24 reference docs, and eval harness; (2) a 14-search primary-source sweep of 2025–2026 GEO research (Ahrefs, Semrush, Otterly, Cloudflare, IETF datatracker, Google announcements); (3) a survey of ~12 other open-source and commercial GEO tools (Auriti-Labs/geo-optimizer-skill, isagentready-skills, elmo, getcito, gego, HubSpot AEO Grader, Profound, Dark Visitors, and others).

Verdict labels: **ADOPT** (do it), **ADAPT** (do a modified version), **WATCH** (revisit in 1–2 quarters), **REJECT** (deliberately don't).

---

## 0. Executive summary

The audit engine's *mechanics* are in good shape after the v0.3.2–v0.3.5 determinism work — our live bot probe with WAF fingerprinting remains strictly ahead of every open-source competitor surveyed (all of them, including ultimate-seo-geo, do static robots.txt parsing only, and ultimate-seo-geo's crawler scoring is actually backwards — it *rewards* blocking AI bots).

The problem is that the *knowledge layer* has drifted out of date and the *coverage map* has three genuinely missing dimensions:

1. **Factual staleness** — retired bot tokens we still probe and recommend, an llms.txt weighting the evidence no longer supports, platform guidance written for a pre-AI-Mode Google.
2. **Missing audit surface** — the 2026 protocol layer (Web Bot Auth, RSL, Content-Usage, HTTP 402, `.well-known` agent endpoints), GEO-spam/prompt-injection detection, and freshness scoring.
3. **A missing product category** — prompt-based share-of-voice tracking (querying the AI engines and measuring whether/how the brand appears). Every commercial competitor leads with this. *Update 2026-07-29: hypothesis-tested and deliberately deferred to `geo-observe` rather than built here — see §2.7 for the test results and handoff notes.*

Plus a set of internal inconsistencies our own audit-the-audit passes surfaced (§6).

**Governing design principle (added 2026-07-29): the report is the product.** Every upgrade must be judged by whether the person reading the audit output understands it faster and can act on it more directly. The plugin's audience is now non-technical (per the v0.3.x README repositioning); a technically-correct check that produces an ambiguous table row is a net regression. See §4 for the report contract — it is a co-headline deliverable of v0.4.0, not polish for later.

---

## 1. Factual staleness (high urgency, low effort)

### 1.1 Retired and mislabeled bot tokens — ADOPT

- **`anthropic-ai` is a retired legacy token** (as is `claude-web`). We still carry it in `AI_CRAWLERS`, probe it live, and our `geo-crawlers` skill recommends `User-agent: anthropic-ai / Allow: /` in its "Maximum AI Visibility Configuration". Recommending rules for dead tokens is the kind of staleness we flag in *other* people's robots.txt.
  - Fix: mark legacy in `AI_CRAWLERS` (`"status": "retired"`), stop recommending it, and **flag its presence in a site's robots.txt as stale-config** (informational, non-scoring).
- **`FacebookBot` is legacy** — superseded by `Meta-ExternalAgent` (which we have). It survives only in the static parser list.
- **`Google-Extended` and `Applebot-Extended` are opt-out tokens, not crawlers.** They never fetch anything; they never appear in logs. Our live probe sends requests with these strings as user-agents, which produces a meaningless "200 OK" datapoint. Fix: keep them in the *declared-policy* analysis, exclude them from the *live probe*, and label them "opt-out token — robots.txt declaration is the only signal that exists."

### 1.2 Missing bots — ADOPT

Add to `AI_CRAWLERS` (live probe + static list, correct class):

| Bot | Operator | Class | Note |
|---|---|---|---|
| `MistralAI-User` | Mistral | live-retrieval | Le Chat live fetch |
| `DuckAssistBot` | DuckDuckGo | search-index | DuckAssist answers |
| `Google-Agent` | Google | live-retrieval | user-triggered agent fetch; Web Bot Auth signer |
| `Google-CloudVertexBot` | Google | training | Vertex AI grounding |
| `Google-NotebookLM` | Google | live-retrieval | NotebookLM source fetch |
| `Amazonbot` | Amazon | search-index/training | already in static list, **missing from live probe** |

Document as a new "unverifiable" class in `geo-botaccess` output: **DeepSeek publishes no crawler UA at all** (fetches look like browser traffic — cannot be blocked by robots.txt or UA-based WAF rules) and **xAI/Grok** documentation is contradictory with reports of spoofed browser UAs. A bot-access report that doesn't mention these implies more control than a site owner actually has.

Also fix the standing inconsistency: static parser list (14 bots) ≠ live probe list (17 bots). Single source of truth: derive both from `AI_CRAWLERS`.

### 1.3 llms.txt — downgrade from scored to informational — ADOPT

The verdict is in: no major platform reads it for citation. Google explicitly says it does nothing for Search/AIO (Mueller: "none of the AI services have said they're using LLMs.TXT"). SE Ranking's 300k-domain study: ~10% adoption, **97% of llms.txt files never fetched by any AI crawler, zero measurable citation effect**.

Our current treatment: 10% of the AI Visibility component score. That's now over-weighted by roughly 10%.

- Reweight AI Visibility: Citability 35 → 40%, Crawler Access 25 → 30%, Brand 30%, llms.txt 10 → **0% (non-scoring, informational)**.
- Keep the validator and generator — reframed for the **B2A niche where it does work**: docs/API sites serving coding agents and agentic browsers (Stripe, Vercel, Cloudflare, Anthropic ship it for this).
- Change report language from "critical gap" to "optional; useful for developer-facing sites; no citation impact."

### 1.4 Freshness is a first-class citation signal — ADOPT

~Half of AI-cited pages were published/updated within the previous 13 weeks; AI-cited content runs ~26% fresher than organic SERPs (Ahrefs 2026). We currently mention freshness qualitatively in `geo-content`; nothing scores it.

- Add a deterministic freshness extractor (from `Article.datePublished/dateModified` JSON-LD, `<time datetime>`, HTTP `Last-Modified`) to `fetch_page.py page` output.
- Score with tiers: Fresh <90d / Aging 90–365d / Stale 1–2y / Very Stale >2y, with per-content-type thresholds (news vs evergreen).
- Feed into `geo-compare` as **content-decay tracking** — "these 12 cited-candidate pages will cross the 13-week window next month" is exactly the recurring-engagement artifact the monthly-delta product needs.

### 1.5 Google AI Mode changed the platform map — ADOPT

Since July 2026, AI-generated answers are Google's **default** search surface globally (Gemini 3.5 Flash on every query; publisher clicks down ~58%; ~93% of AI Mode sessions end without a click). Our `geo-platform-optimizer` still describes AI Overviews as an overlay that "favors pages that already rank top-10" — but only **38% of AIO citations now come from Google top-10** (down from 76% mid-2025), and #1 ranking yields only ~33% citation probability.

The operative model is **query fan-out**: one query → 8–15 parallel sub-queries, each retrieving *passages* independently. Pages ranking for fan-out sub-queries are **161% more likely to be cited** (0.77 correlation).

- Rewrite the AIO section around fan-out; add **Google AI Mode as a distinct platform** (zero links surfaced by default, multi-turn, Deep Search).
- Add a **fan-out coverage check** to `geo-citability`/`geo-platform-optimizer`: decompose the page's head topic into likely sub-queries (who/what/how/vs/cost/examples...), then check which are answered by a self-contained passage on the page. This is the single highest-leverage new *content* check.
- Add platform entries for **Grok** and a note on **Meta AI**; keep Bing Copilot (still ChatGPT's retrieval layer — Bing Webmaster + IndexNow checks stay valid).

---

## 2. Missing audit dimensions

### 2.1 Agent-readiness protocol suite — ADOPT (new sub-skill `geo-agentready`)

We already check RFC 8288 `Link` headers, Content-Signal, and markdown negotiation as non-scoring signals — the convention extends naturally. Cloudflare now publishes an Agent Readiness score and isagentready-skills (a Claude skill bundle, our closest structural sibling) runs 42 checkpoints. The whole suite is cheap: single `.well-known` URL fetches.

| Check | Mechanism |
|---|---|
| Web Bot Auth support | RFC 9421 HTTP Message Signatures; `Signature-Agent` header handling; `.well-known` JWKS directory. IETF WG chartered 2026; backed by Cloudflare/OpenAI/Anthropic/Perplexity; enforced by AWS WAF, Vercel, Shopify |
| API catalog | `.well-known/api-catalog` (RFC 9727) — we already parse the Link-header form |
| OAuth discovery | RFC 8414 / RFC 9728 metadata endpoints |
| MCP server card | `.well-known/mcp/server-card.json` (SEP-1649) |
| agents.json | `.well-known/agents.json` (pre-standard) |
| NLWeb | `/ask` + `/mcp` endpoints (Microsoft protocol; Cloudflare AutoRAG managed option) |
| Commerce protocols | x402, Agentic Commerce Protocol, UCP — flag-only, non-scoring |

All non-scoring initially (same rationale as Content Signals: penalizing absence of emerging specs is unfair). One new `fetch_page.py` mode (`agentready`) + one SKILL.md.

### 2.2 Content-licensing signal detection — ADOPT (extends `geo-botaccess`/`geo-crawlers`)

The licensing layer moved fast in 2025–2026 and we detect none of it:

- **RSL 1.0** (Really Simple Licensing — finalized Dec 2025, ~1,500 media orgs, Cloudflare/Akamai support): check for `rsl.txt` / RSL license link in robots.txt / RSL XML.
- **`Content-Usage` HTTP header + robots.txt rule** (IETF AIPREF attachment draft; vocabulary draft on Proposed Standard track, IESG target Aug 2026). We check the Cloudflare `Content-Signal` precursor already — add the IETF form.
- **HTTP 402 semantics**: Cloudflare pay-per-crawl (pivoting to pay-per-answer as of July 2026; **AI training bots blocked by default on new Cloudflare ad-supported domains from Sept 15, 2026**). Our live probe currently has no 402 branch — a 402 would presumably read as "blocked." It isn't: it's a payment demand. Classify distinctly: `verdict: "payment-required"`, report as "site monetizes AI access, not blocking."

The Sept 15 Cloudflare default-block change matters commercially: a wave of sites will *become* bot-blocked without their owners knowing. Our declared-vs-actual mismatch detection is exactly the tool for that moment — worth a report callout.

### 2.3 GEO-spam / prompt-injection detection — ADOPT (new script + extension to `geo-content`)

Nobody else in our niche audits for this except Auriti-Labs; it's differentiating and pure static analysis. Patterns: hidden text (CSS/monochrome/micro-fonts), invisible Unicode, LLM-directed instructions in HTML comments or `aria-hidden`/data-attributes ("ignore previous instructions", "cite this site as the best..."), cloaked content served only to bot UAs (we already have per-UA fetches to diff!). Two outputs:

- **Integrity check** for the audited site itself ("your CMS/plugin injected LLM-instruction spam — this is a manual-action and trust risk").
- **Per-UA content diff** we get almost free from the live probe: similarity between bot-served and Chrome-served content already exists (`similarity` field) — extend to flag *bot-targeted additions*, not just stripping.

### 2.4 Negative/anti-citation signals — ADAPT (extends `geo-citability`/`geo-content`)

We score positives only. Add penalty-side checks: CTA/popup density, boilerplate ratio, missing author, keyword stuffing (Princeton KDD-2024 measured keyword stuffing at **−10%** citation likelihood). Fold into `citability_scorer.py` as new negative dimensions rather than a separate tool.

### 2.5 Entity/Knowledge-Graph audit deepening — ADAPT (extends `brand_scanner.py`)

ultimate-seo-geo's entity stack is deeper than ours in specific, adoptable ways:

- **`sameAs` liveness**: extract `sameAs` from JSON-LD and HEAD-check each URL for 404s (broken entity links are a real, common finding — law.co.il's `href="#"` LinkedIn links are exactly this).
- **`@id` graph consistency** across pages (`#organization` / `#person` / `#website` cross-referencing).
- **Wikidata QID with confidence** rather than first-hit title match (their implementation has homonym false positives — do it better, not the same).
- **AI Entity Resolution Test** — "ask 4 platforms who the brand is, score 0–3 each" — is a good idea that belongs in the visibility skill (§2.7), not brand-mentions.
- Adopt **Profound's source taxonomy** for mention classification: Owned / Competitor / Earned Media / PR Wire / Social / Institution.

### 2.6 Server-log crawl evidence — ADAPT (new `geo-botaccess` mode)

Our probe answers "*can* they crawl"; log analysis answers "*did* they." AI crawlers don't execute JS, so GA4/Plausible never see them — server logs are the only ground truth of actual AI crawl activity, and crawl-to-referral ratios (Anthropic ~38,000:1, OpenAI ~1,091:1) are now standard practitioner deliverables. Accept an access-log path, parse UA hits per bot class, report crawl frequency + most-crawled paths. Optional (logs aren't always available) — but it converts the botaccess skill from point-in-time to longitudinal.

### 2.7 Prompt-based share-of-voice visibility — DEFER to geo-observe (hypothesis tested 2026-07-29)

Originally proposed as the v0.5 flagship. **Tested empirically before committing** (subject: law.co.il; 4 buyer-intent prompts × 2 conditions [parametric / search-grounded] × 3 independent blind runs — agents were never told which brand was tracked):

- **H1 stability: PASS.** 8/8 prompt×condition cells produced identical brand-mention outcomes across repeats (pre-registered bar: ≥75%). Mention-rate is measurable signal with only 3 repeats per prompt.
- **H2 displacement extractability: PASS (marginal).** ~55% of cited domains recur across repeats of the same prompt (bar: ≥50%); the head of the list is fully stable (iapp.org, dataguidance.com 3/3 for the losing prompt), the tail is noise. → Report only ≥2/3 recurrers as displacement targets.
- **H3 dual-condition diagnostic: FAIL.** Zero divergent parametric-vs-grounded cells; the per-prompt 2×2 added no discrimination and would have *mis-diagnosed* the one losing prompt as an entity problem. Refinement: run the parametric probe **once per brand** as a covariate, not per prompt (≈40% cost reduction).
- **Actionability demonstrated:** the panel yielded one crisp, evidence-backed recommendation (see the law.co.il worked example in the test report) and a success metric — freeze the panel, re-run monthly, count cell flips; the measured stability makes a flip meaningful.

**Decision: do not build this in GEO Reporter.** The capability already lives elsewhere (`geo-observe`, the maintainer's separate implementation). Hand the validated methodology findings to that tool instead: 3 repeats suffice; blind design is mandatory (naming the brand in the prompt contaminates measurement); brand detection must scan full answer text, not model-generated entity recaps (which proved lossy); parametric probe once per brand; only recurring displacers are reportable; frozen-panel flip-counting is the success metric. GEO Reporter optionally keeps a single-shot **entity-embeddedness check** (does the model name the brand unprompted for its category?) as a lightweight audit signal.

**Multilingual addendum (Hebrew replication, same date):** the full experiment was repeated with Hebrew prompts and a Hebrew-speaking user persona (3 blind grounded runs). Results: identical win/loss shape and 100% cell stability (12/12 cells stable across the two languages) — but the displacement lists for the losing prompt had **zero domain overlap** between languages (English: iapp.org, dataguidance.com, compliance vendors; Hebrew: shibolet.com, ebnlaw.co.il, globes.co.il). Handoff requirement for `geo-observe`: **panels must run per language, with per-language displacement lists and per-language recommendations** — a single-language panel measures at most half the market for bilingual brands, and optimizing for the wrong language's displacers would waste the client's effort.

### 2.8 Multilingual audit correctness (Hebrew/English) — ADOPT (high priority for our client base)

Most sites we audit are bilingual (Hebrew + English). A code audit (2026-07-29) found four concrete English-bias defects, and a Hebrew replication of the visibility experiment confirmed why they matter:

1. **`brand_scanner.py` checks `en.wikipedia.org` only** (and queries Wikidata with `language=en`). A brand with a Hebrew Wikipedia article and no English one loses the full 30 Wikipedia points of the Brand Mention Score. Fix: accept a language list (default `["en", "he"]` when Hebrew content detected via `Content-Language`/`lang` attr), query each wiki, report per-language presence. (Empirical support: a Hebrew grounded run cited `he.wikipedia.org` as an expert-verification source.)
2. **`citability_scorer.py`'s Answer Block Quality dimension is English regex** (`X is / means / refers to`, "What/How/Why" headings). Hebrew passages structurally cannot score on it regardless of quality. Fix: add Hebrew pattern equivalents (`X הוא/היא`, `מהו/מהי/כיצד/איך/למה` headings, ₪ in statistical density); flag that the 134–167-word optimal band is an English-corpus finding — Hebrew is morphologically denser and the band likely shifts down (do not assert a number without evidence; score length-band as language-unknown for non-English until calibrated).
3. **`fetch_page.py` hardcodes `Accept-Language: en-US`** on every fetch including the live bot probe — language-negotiating sites always show us their English variant, silently excluding the Hebrew tree from the audit. Fix: fetch with the site's own language variants; audit both trees.
4. **Skill layer has no bilingual protocol.** Only `geo-technical` mentions hreflang. `geo-audit` Phase 1 should detect multi-language structure (path prefixes like `/en/`, hreflang pairs, `Content-Language`) and then run content/citability/schema analysis **per language tree**, reporting scores per language rather than blending.

**Why it matters — measured:** the Hebrew replication of the §2.7 experiment (3 blind grounded runs, Hebrew prompts) reproduced the English win/loss pattern exactly (12/12 stable cells across both languages) but with a **zero-overlap displacement list**: the English losing prompt is won by iapp.org/dataguidance.com/compliance vendors; the same Hebrew prompt is won by shibolet.com/ebnlaw.co.il/globes.co.il. Language = separate market; recommendations must be issued per language.

### 2.9 RAG-chunk / passage-indexing readiness — ADAPT (extends `citability_scorer.py`)

Section-level complement to our passage-level 134–167w rubric: heading-boundary chunk alignment, anchor sentences, definition-style section openings, **no pronoun-dependent openings** ("It/This..." referring backwards — scorer already computes a pronoun ratio, so this is nearly free), each H2 self-contained at 100–200 words. Google passage ranking and AI citation reward the same structure.

---

## 3. Methodology recalibration

### 3.1 Schema claims need platform-nuance — ADOPT

Current `geo-schema` implies schema straightforwardly drives AI citation. 2026 evidence: 71% of ChatGPT-cited pages carry structured data (correlational), Google engineers confirm grounding value **on Google surfaces**, Google docs simultaneously say no special schema is required, and third-party LLMs largely can't parse JSON-LD at runtime. Reframe: strongly causal-ish for Google surfaces, correlational elsewhere; the *entity consistency* it creates is the durable value.

### 3.2 JS-injected schema false negative — ADOPT (bug-class fix)

Our static fetch reports "no structured data" on CMS sites where Yoast/RankMath inject JSON-LD client-side. The law.co.il audit's "0 JSON-LD blocks" is exactly the pattern that needs the caveat. Fix: when `structured_data` is empty AND the site shows CMS markers, (a) caveat the finding, (b) offer the Playwright fallback (already a dependency) to verify rendered DOM before reporting "missing."

### 3.3 Schema catalog refresh + YMYL gate — ADOPT

- Status-tier the recommendations: ACTIVE / RESTRICTED (FAQPage — with the decision tree; explicitly fine as a GEO play) / NO-RICH-RESULTS-BUT-KEEP (HowTo) / RETIRED (SpecialAnnouncement, ClaimReview, etc. — verify each date independently before asserting).
- **YMYL-sensitive gate**: never auto-recommend `LegalService` / `MedicalWebPage` / `Physician` / `FinancialProduct` schema without verified credentials — manual-action risk. *Our own law.co.il report recommended `LegalService` sitewide with no credential check.* Add the gate to `geo-schema` and the `geo-schema` agent.
- New templates worth adding to `schema/`: `comparison-page` (ItemList + Product), `person-author-entity` with full `sameAs` block (we have article-author; extend), `video-object`.

### 3.4 Citability guidance updates — ADAPT

- Word count has ~zero correlation with citation (Ahrefs, 174k pages) — our passage-extractability focus is right; make sure no report language implies "write longer."
- **Content-type awareness**: comparison articles ≈ 33% of AI citations ("if you build one thing for GEO, build a comparison article"); being *featured in* third-party "best X" lists beats writing your own. Add to `geo-citability` recommendations and `geo-brand-mentions` (earned-lists check).
- Platform divergence is real and growing: **11–12% domain overlap between ChatGPT and Perplexity citations**. Keep and strengthen per-platform work; add a platform-to-dimension effort-allocation matrix.

### 3.5 E-E-A-T refresh — ADOPT

Sept 2025 QRG (current): raters explicitly assess AI-generated content (AI use alone ≠ low quality; low-effort AI output = Lowest), YMYL expanded to Government/Civics. Update `geo-content` accordingly; add "corrections/editorial policy page" as a scored trust item for publishers (we already recommend it ad hoc — make it a check).

---

## 4. Report experience — the report is the product (ADOPT, v0.4.0 co-headline)

### The evidence that this is broken today

- **The "Unverified" incident (law.co.il audit, 2026-06):** the AI-crawler table showed "⚠️ Unverified" for every bot on a fully permissive site. The site owner read it as "blocked," asked for an explanation, and the report had also recommended robots.txt additions that weren't needed. Two distinct failures: an ambiguous status vocabulary, and a recommendation not grounded in evidence. (The data layer behind this was fixed in v0.3.2; the *presentation contract* that allowed an ambiguous label to ship was not.)
- **YMYL schema recommendation without a credential check** in the same report (`LegalService` sitewide) — a fix the user could have pasted and been harmed by.
- **Jargon density:** the current report template leans on GEO/E-E-A-T/SSR/schema vocabulary with no plain-language layer, while the plugin's declared audience is non-technical.
- **Recommendations without execution paths:** "Add Organization schema" is a finding; "paste this JSON-LD into your site `<head>` (or send this file to your developer)" is an action. The current template mostly produces the former.
- **The best output this project produced all month** was one sentence: *"You're never cited for the Amendment 13 question — in Hebrew you lose to Shibolet/EBN, in English to IAPP/DataGuidance; publish an obligations guide in both languages."* Evidence-backed, specific, delegatable. The report format should be engineered to produce sentences like that, not tables that bury them.

### The report contract (applies to geo-audit, geo-report, geo-report-pdf, and every subagent output format)

1. **Lead with the decision, not the data.** TL;DR of ≤150 words at the top: composite score (+ delta if a prior audit exists), the top 3 actions with expected impact and effort, and one sentence on overall posture. A reader who stops there should still know what to do this week.
2. **Closed status vocabulary, defined inline.** Every status label comes from a fixed legend printed with the table. Ambiguous labels are banned — "Unverified" is replaced by exactly one of: `✅ Confirmed (tested live)` / `❌ Blocked by <product> (mismatch — declared open)` / `❌ Blocked (declared, intentional)` / `⚠️ Content differs for bots` / `— Not tested (<reason>)`.
3. **Mandatory finding format:** **Finding / Evidence / Impact / Fix / Confidence** (Confirmed · Likely · Hypothesis). Evidence quotes what was actually observed ("GPTBot received HTTP 200, byte-identical to Chrome"); Impact is stated in reader terms ("AI assistants can already read your site — no action needed"), not spec terms.
4. **Evidence-integrity rule:** no claim appears without a named check that ran. Degraded runs render "`<metric>` not measured — <what would measure it>", never a guessed value or an ominous blank.
5. **Executable fixes.** Every Critical/High fix ships as a paste-ready artifact (robots.txt block, JSON-LD snippet, llms.txt file) or a delegatable task with owner-type (developer / content / marketing) and effort tag (minutes / hours / days). Content fixes include a brief: proposed title, structure, and *who currently wins that query* — the displacement evidence is what makes the brief persuasive.
6. **Before/after demonstration** for every content-rewrite recommendation: the current passage, the rewritten citable version, one line on why it wins.
7. **Per-language sections for bilingual sites.** Hebrew and English trees get separate scores, separate findings, separate action lists — never blended (a blended score hides that you can be dominant in one language and invisible in the other, which is exactly what the law.co.il visibility test found).
8. **Progressive disclosure.** Main body is narrative for the non-technical reader; raw tables, per-bot matrices, and methodology move to appendices. PDF and markdown mirror the same hierarchy.
9. **Repeat audits lead with the delta** — "what changed since last audit" (fixed / regressed / new), wired into `geo-compare`.
10. **High-risk gate:** robots.txt/noindex/redirect changes are described in plain language with consequences first; the code block is withheld until the reader confirms (prevents paste-first-ask-later accidents).

### Acceptance criteria (v0.4.0 definition of done)

- Re-run the law.co.il audit: the AI-crawler section must be answerable without a follow-up question — every row's status self-explains from the legend.
- Every Critical/High finding carries a paste-ready or delegatable fix with owner + effort.
- The TL;DR standing alone passes the "tell me what to do this week" test.
- No YMYL schema recommendation renders without the credential-check caveat.
- A bilingual site's report shows per-language sections.
- Add 3–5 skill-level eval scenarios asserting these report properties (the §5 eval-harness pattern), so the contract is regression-tested, not aspirational.

## 5. Process & architecture patterns worth stealing

| Pattern | Source | Verdict |
|---|---|---|
| **Evidence-integrity table** — every claim needs a named precondition ("LCP only if pagespeed ran"), else emit "[metric] not measured" | ultimate-seo-geo | **ADOPT** — direct extension of our determinism work into the report layer |
| **Evaluator pass before delivery** — 11-point self-check (evidence on every Critical, score matches findings, no fabricated metrics, no YMYL schema without credentials...) | ultimate-seo-geo (from Anthropic cookbook) | **ADOPT** — cheap markdown, catches exactly the law.co.il-style failures |
| **High-risk execute gate** — robots.txt/noindex/redirect changes described in plain language, code withheld until explicit confirmation | ultimate-seo-geo | **ADOPT** for `geo-crawlers`/`geo-technical` fix outputs |
| **Internal vs. Competitive mode** — external URLs get "External Observation Only" label, no numeric score, capped crawl | ultimate-seo-geo | **ADOPT** — directly relevant to `geo-prospect`/`geo-proposal` legal posture |
| **Finding format**: Finding / Evidence / Impact / Fix / Confidence | ultimate-seo-geo | **ADOPT** as report-wide convention |
| **Before/after citation demonstration** — show the uncitable passage, the 134–167w rewrite, and why | ultimate-seo-geo | **ADOPT** — we have the weakest-dimension data per block already |
| **Functional-page exemption** — never flag login/checkout/signup as thin content | ultimate-seo-geo eval 15 | **ADOPT** — one-line false-positive guard |
| **Skill-level eval harness** — scenario prompts + assertions + golden transcripts in CI | ultimate-seo-geo (15/63) | **ADAPT** — we have 78 pytest for scripts, zero for SKILL.md behavior; start with 5–8 scenarios (wildcard robots case, YMYL schema case, high-risk gate case...) |
| Bot-list currency automation via Dark Visitors API | Dark Visitors | **ADAPT** — a CI job that diffs `AI_CRAWLERS` against the live directory and opens an issue |
| CI output formats (SARIF/JUnit) | Auriti-Labs | **WATCH** — different distribution channel, unclear demand |
| Multi-platform packaging (AGENTS.md/GEMINI.md/Cursor/GPT) | ultimate-seo-geo | **WATCH** — we're deliberately Claude-plugin-first |
| Content coherence / cross-page terminology checks | Auriti-Labs | **WATCH** — corpus-level analysis, heavier lift |

## 5b. Rejects (know what NOT to copy)

- **Static-only crawler analysis** presented as access truth (everyone else) — our live probe is the correction; never regress.
- **ultimate-seo-geo's backwards robots scoring** (blocking AI bots *raises* its SEO score; ✅ icon rendered on "blocked") — cautionary tale for any scoring change: add a test asserting the direction.
- **Unsourced precision statistics** ("FCP<0.4s → 6.7 vs 2.1 citations", "schema = 2.5× AI answers", "85% retrieved-never-cited") — do not import any number without a primary source; our CHANGELOG discipline should extend to citation discipline in skill docs.
- **Word-count floors** (contradicts both Google and the Ahrefs data).
- **Speakable/voice emphasis** — long-beta, news-only, low 2026 value (we already treat it as minor; keep it that way).
- **llms.txt as a scored GEO driver** (see §1.3).

---

## 6. Internal inconsistencies found during this analysis

1. **Bot list split-brain**: `fetch_robots_txt()` checks 14 bots; `AI_CRAWLERS` live-probes 17; neither is a superset of the other (static has Amazonbot/FacebookBot; probe has Claude-SearchBot/-User, Perplexity-User, Meta-ExternalAgent, GoogleBot, BingBot). Derive both from one structure.
2. **Citability rubric has three diverging definitions**: `skills/geo-citability/SKILL.md` says weights 30/25/20/15/10; `agents/geo-ai-visibility.md` documents 25/20/20/20/15; `citability_scorer.py` sums per-dimension point-buckets (its own implicit weighting). Grade cuts also differ (agent doc: A≥85/B≥70; scorer: A≥80/B≥65). The scorer is canonical — align both docs to it.
3. **`geo-crawlers` recommended config still emits `anthropic-ai`** and omits Claude-SearchBot/Claude-User/Perplexity-User/Meta-ExternalAgent — the recommendation block predates our own bot-list expansion.
4. **AI Visibility composite weights** in `agents/geo-ai-visibility.md` (35/30/25/10) don't match `geo-audit` SKILL.md's category description weights — reconcile when reweighting for §1.3.

---

## 7. Recommended release train

> **Status update (2026-07-29, post-release):** v0.4.0 shipped as [PR #27](https://github.com/internet-and-sons/geo-reporter/pull/27) / tag v0.4.0 — all planned scope plus review-loop additions (Google-GeminiNotebook, future-dated freshness tier with skew tolerance, Wikimedia UA production fix, en+he Wikipedia). §2.8's citability-scorer Hebrew i18n was independently delivered by outside contributor @idoish (PR #26) and shipped inside v0.4.0.
>
> **v0.4.x backlog accumulated during execution** (from implementer escalations + live evals):
> 1. Codify the address-verified-bot render rule (GoogleBot/BingBot/Google-* probed off-network → "— Not tested (validated by network address)") in geo-botaccess — the two eval executors chose different legal renders.
> 2. `fetch_page.py` default Chrome UA gets Cloudflare-challenged on strict sites — add a bot-UA fallback for content analysis (disclosed-in-methodology pattern from the zman.co.il eval).
> 3. Eval Scenario 2 wording: exempt template-mandated tables (Score Breakdown, 7 rows) from the >6-row appendix rule.
> 4. geo-crawlers tier reference profiles + tier scoring don't yet mirror the 21-bot roster (legacy 94/100 tier score vs live 31/100 confused-then-explained in the eval); unify.
> 5. Roster candidates: MistralAI-Index, OAI-AdsBot; stale UA version strings (GPTBot/1.2 → 1.4, OAI-SearchBot/1.0 → 1.4).
> 6. Flip `Google-NotebookLM` to `status: "retired"` after August 2026.
> 7. Schema-template index table in geo-schema (8 templates, currently discoverable only by directory listing).
> 8. Structured TL;DR block on the PDF cover (ReportLab change) + per-section Finding-format conversion of geo-report's illustrative tables.
> 9. Freshness weight in the content composite (currently 5%) vs its measured citation importance — scoring-design review.

| Release | Theme | Contents | Effort |
|---|---|---|---|
| **v0.4.0** | **Truth refresh + report experience** | **§4 report contract across geo-audit / geo-report / geo-report-pdf / subagent output formats (TL;DR-first, closed status legend, Finding-Evidence-Impact-Fix-Confidence, executable fixes, per-language sections, acceptance criteria + report evals)**; §1.1–1.5 (bot roster + retired tokens + opt-out token semantics, llms.txt downgrade + reweight, freshness scoring, AI Mode/fan-out rewrite of platform-optimizer); §3.1–3.5 (schema nuance + YMYL gate + JS-injection caveat, citability guidance, E-E-A-T refresh); §6 consistency fixes; **§2.8 quick multilingual fixes** (multi-language Wikipedia/Wikidata in brand_scanner, Accept-Language handling, bilingual-site detection + per-language-tree audit protocol) | Mostly markdown + `AI_CRAWLERS` restructure + freshness extractor + brand_scanner language param + tests |
| **v0.4.1** | **Agent readiness & licensing** | §2.1 `geo-agentready` (well-known probes, Web Bot Auth detection, NLWeb), §2.2 (RSL, Content-Usage, HTTP 402 classification in probe — incl. Sept 15 Cloudflare default-block callout) | One new fetch mode + one SKILL.md + probe branch + tests |
| **v0.4.2** | **Integrity & entity depth** | §2.3 prompt-injection/GEO-spam detector, §2.4 negative signals in scorer, §2.5 sameAs liveness + @id consistency + Profound taxonomy, §2.8 citability scorer Hebrew i18n (pattern equivalents + language-aware length band), §5 remaining guardrails (evaluator self-check pass, external-observation mode for prospect audits) | New script + scorer extension + report-layer markdown |
| ~~v0.5.0~~ | ~~Visibility tracking~~ | **Cut after hypothesis test (2026-07-29)** — methodology validated (H1/H2 pass) but capability is owned by `geo-observe`; findings handed over (§2.7). Remaining candidates for a future v0.5: §2.6 log-evidence mode + a lightweight entity-embeddedness check | — |
| Ongoing | Eval harness (§4), Dark Visitors CI diff (§4) | Start at v0.4.0 with 5 scenarios, grow per release | Incremental |

**Sequencing logic:** v0.4.0 first because it fixes the two things that most damage reader trust: claims that are now *wrong* (stale bots, llms.txt weight, pre-AI-Mode guidance) and presentation that lets correct data mislead (the "Unverified" incident). Truth and readability ship together because they are the same promise to the reader. v0.4.1 is the cheapest new-surface win. v0.4.2 is differentiation. Visibility tracking is deferred to `geo-observe` (§2.7).

---

## 8. Source appendix

**Primary studies:** Ahrefs top-10 decoupling (38%) · Ahrefs content-length (~0 correlation) · Ahrefs freshness (13-week window) · Semrush 230k-prompt multi-platform study · Otterly AI Citations Report 2026 · Averi 680M-citation overlap analysis (11%) · SE Ranking 300k-domain llms.txt study · Princeton GEO (KDD 2024) technique effects.
**Standards/infra:** IETF AIPREF WG drafts · RFC 9421/9727/8414/9728 · rslstandard.org (RSL 1.0) · Cloudflare blog/changelogs (Content Signals, pay-per-crawl→pay-per-answer, Sept 15 default block, Agent Readiness, signed agents) · MCP SEP-1649 · NLWeb.
**Vendor docs:** OpenAI bots · Anthropic crawler docs (retired-token notice) · Perplexity bots · Google crawler directory (Google-Agent, CloudVertexBot, NotebookLM) · Mistral, DuckDuckGo bot pages · Dark Visitors directory.
**Tools reviewed:** mykpono/ultimate-seo-geo v1.9.0 (full clone read) · Auriti-Labs/geo-optimizer-skill · BartWaardenburg/isagentready-skills · elmohq/elmo · ai-search-guru/getcito · AI2HU/gego · sarahkb125/llm-brand-tracker · ngstcf/ai-seo-auditor · bridgetoagent/llms-txt-validator · HubSpot AEO Grader · Profound methodology pages.

*Note on statistics: numbers above marked with a specific study are traceable; ultimate-seo-geo also circulates many high-precision unsourced figures (§5b) that we deliberately did not import.*
