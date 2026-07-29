# Report-Contract Eval Scenarios (manual)

Run these after any change to geo-audit, geo-report, geo-report-pdf, or agent
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

## Scenario 2 — TL;DR standalone test

Command: `/geo audit <any site>`
- [ ] Report opens with TL;DR ≤150 words containing: score, exactly 3 actions, each with impact + effort + owner
- [ ] Reading ONLY the TL;DR, a non-technical person can say what to do this week
- [ ] No table longer than 6 rows appears before the appendix

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
