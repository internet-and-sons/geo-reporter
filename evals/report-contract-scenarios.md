# Report-Contract Eval Scenarios (manual)

Run these after any change to geo-audit, geo-report, or agent
output formats. Each scenario: run the command, then check every assertion.
A scenario fails if ANY assertion fails. Record results in the PR description.

## How to run

Use a fixture site with known properties (https://example.com works for 1–2;
a real bilingual site is needed for 3; any prior-audit site for 5).

## Scenario 1 — Status vocabulary (the "Unverified" regression)

Command: `/geo crawlers <fully-permissive site>`
- [ ] No status label outside the contract legend appears (grep the output for "Unverified" — must be absent)
- [ ] The legend is printed with the crawler table
- [ ] Opt-out tokens (Google-Extended, Applebot-Extended) render as "— Not tested (opt-out token …)", not as blocked/allowed
- [ ] A permissive wildcard robots.txt renders as Allowed-family status, never "Unknown"
- [ ] Retired tokens present in the site's robots.txt surface as an informational cleanup item (stale_tokens)
- [ ] If any bot received HTTP 402, it renders as "💰 Payment required", never as blocked or as a mismatch

## Scenario 2 — TL;DR standalone test

Command: `/geo audit <any site>`
- [ ] Report opens with TL;DR ≤150 words containing: score, exactly 3 actions, each with impact + effort + owner
- [ ] Reading ONLY the TL;DR, a non-technical person can say what to do this week
- [ ] No table longer than 6 rows appears before the appendix (template-mandated tables — e.g. the 7-row Score Breakdown — are exempt)

## Scenario 3 — Bilingual site

Command: `/geo audit <bilingual he/en site>`
- [ ] Report contains one findings section per language
- [ ] No blended cross-language score is presented as the site's score without per-language breakdown
- [ ] Brand/Wikipedia findings state per-language presence

## Scenario 4 — YMYL schema gate

Command: `/geo schema <law-firm or medical site without visible credentials>`
- [ ] No LegalService/Medical*/FinancialProduct recommendation appears without a credential-verification note
- [ ] The fallback (Organization/ProfessionalService) is offered instead

## Scenario 5 — Evidence integrity + delta

Command: `/geo audit <site with a prior audit>`, with network blocked for one check (e.g. temporarily pass an invalid URL to one probe)
- [ ] The failed check renders "not measured — <how to measure>", not a guessed value
- [ ] The report leads with Fixed / Regressed / New versus the prior audit
- [ ] Every Critical/High finding has Evidence quoting an observation and a Fix with owner + effort

## Scenario 6 — Integrity signal framing

Command: `/geo integrity <clean site>` then `/geo integrity <site with a hidden-text block>`
- [ ] Clean site: reports "no content-integrity signals", Confidence Confirmed, no false accusation
- [ ] Flagged site: each finding quotes the actual offending text (evidence) and its location
- [ ] Every flagged finding is framed as "review this / signal, not proof", never "you are spamming"
- [ ] Max Confidence on any flagged finding is "Likely" — never "Confirmed" (we confirmed the pattern exists, not the intent)
- [ ] The section carries no numeric score (integrity is non-scoring)
- [ ] Innocent explanations (plugin, theme, inherited SEO vendor) are named

## Scenario 7 — External / competitor observation mode

Command: `/geo audit <a competitor or third-party URL>` (answer "competitor" if asked whose site it is)
- [ ] The report is labeled "External Observation Only"
- [ ] No /100 composite score is presented for the third-party site
- [ ] The crawl is capped (homepage + ≤20 pages), and the methodology says so
- [ ] Output is framed as observations/opportunities, not a graded verdict
- [ ] If ownership was ambiguous, the tool asked "your own site, or a competitor's / third party's?"

## Scenario 8 — Right-unit selection

Command: `/geo audit <a section / category / tag URL on a publisher site>`
- [ ] The report states which unit was audited and why (listing → the articles beneath it)
- [ ] Findings are about the sampled articles, NOT the listing's H1 count, meta description, or teaser citability
- [ ] Recurring findings are written as canonical fixes, each labelled **domain** / **template** / **editorial**
- [ ] The listing page is assessed only as a discovery path (crawlable, links its articles, links resolve)
- [ ] Articles excluded from the sample are named with a reason (failed to fetch, or cross-language-tree), never silently dropped or estimated
- [ ] On a multilingual site, samples are per language tree — never pooled into one score

## Scenario 9 — Inconclusive is not absent

Command: `/geo agentready <a Cloudflare-fronted site>` and `/geo brands <a site with Wikipedia + Facebook sameAs links>`
- [ ] agentready: checks the site refused (401/403/429) render as "— Not measured", never as absent
- [ ] agentready: the report distinguishes "no agent endpoints found" from "could not determine from outside"
- [ ] brands: only genuinely-failing links (404/410/DNS) appear as broken-link findings
- [ ] brands: links the platform refused to answer appear as a note, not a finding — a live Wikidata or Facebook link is never reported as broken
- [ ] citability: when `fetch_method` is `bot_ua_fallback`, the methodology says scores reflect the AI-crawler view

## Scenario 10 — An expected refusal is not a block

Command: `/geo crawlers <any site>` and `/geo audit <a healthy publisher: blocks training, allows retrieval>`
- [ ] Googlebot, Bingbot and the `Google-*` agents render as `— Not tested (validated by network address)` — never `❌ Blocked`
- [ ] `traditional-search` reports as **not measured**, never as `0/100`, when every member is address-verified
- [ ] The composite crawler score does not fall because of an off-network 403 from Google or Bing
- [ ] A site that blocks CCBot/Bytespider/Meta/cohere while serving every retrieval and search crawler reads as `HEALTHY_PUBLISHER`, not `MOSTLY_BLOCKED`
- [ ] The report points the reader at Google Search Console / Bing Webmaster Tools as the only way to confirm real Google/Bing access
- [ ] Genuine retrieval blocks still score badly — the exclusion never whitewashes a real problem

## Scenario 11 — The scorer speaks Hebrew

Command: `/geo citability <a Hebrew article on a publisher template>`
- [ ] `missing_author` is NOT flagged on an article carrying a visible Hebrew byline or a `Person` node in its JSON-LD
- [ ] Share bars, comment-system explainers and reader-support pitches do not appear among the scored passages
- [ ] The reported score is the content-only average; the all-blocks figure appears only when explaining a change vs a previous audit
- [ ] Optimal-length counts use the Hebrew band (90–120 words), not the English one
- [ ] Ordinary Hebrew prose that happens to contain a word like "שיתוף" (cooperation) is not classified as chrome
