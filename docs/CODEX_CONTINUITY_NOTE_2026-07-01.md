# Codex Continuity Note - 2026-07-01

## Current Priority

Keep LumenCore focused on reviewer-safe live proof, grant submission readiness, and the first buyer-authorized field replay. Do not drift into new dashboards unless they consolidate the existing production boards.

## Commit Just Pushed

- Branch: `codex/live-domain-proof-feed-bundle`
- Commit: `a97ffbd`
- Message: `Harden live proof gates and grant evidence pipeline`
- Scope: 288 tracked files covering geometry proof gates, live source wiring, DICE/Harbor/NV065 grant evidence, dashboard feed hardening, continuity docs, and regression tests.

## Verification

- Full test suite before final cleanup: `345 passed, 4 warnings`.
- Focused post-cleanup verification: `23 passed`.
- Staged diff check: clean.
- Secret scan: no pasted plaintext API keys detected; only safe variable names and negative assertions appeared.

## Truth Gates

Keep these closed until an external buyer, agency, lab, or system owner approves the held-out operational data, baseline, acceptance metric, and economic conversion:

- Field validation claim.
- Realized savings claim.
- Fixed dollar value per frozen delta.
- Grant award certainty.
- Live/autonomous trading execution.
- Bulk outreach or sending without user review.

## Current Strongest Evidence

- Top replay cards: 5.
- Candidate live replays beating named baselines: 3.
- Strict rolling champions: 5.
- Total live-context rows evaluated in the current top replay summary: 150.
- Key champion lane: Kuramoto phase coupling, with source-conditioned holdout wins reported in the first-buyer board.
- Important boundary: this is internal, hash-backed, source-conditioned replay evidence, not field validation.

## First Buyer Lane

Recommended first buyer lane:

- EPRI AI for Power / Incubatenergy Labs.

Recommended first action:

- Send one manually reviewed inquiry through the official challenge/contact path.
- Ask for a paid evidence review or buyer-authorized field replay.

Do not auto-send. `dashboard/data/first_buyer_target_board.json` explicitly says:

- `manual_reviewed_outreach_allowed: true`
- `send_without_user_review_allowed: false`
- `bulk_email_allowed: false`

## Missing Source Families To Expand

Highest-value additions:

- Grid and ISO: PJM, MISO, ERCOT, CAISO, SPP, NYISO, ISO-NE, BPA, TVA.
- Energy and outage: DOE OE-417, FERC/EQR, EIA EBA, EIA nuclear outage/860/923.
- Weather and space weather: NOAA NCEI, NOAA SWPC, Open-Meteo fallback.
- Environment: EPA AQS, AirNow, OpenAQ.
- Harbor and maritime: MarineCadastre AIS, NOAA PORTS, USCG notices, validated paid AIS if available.
- Cyber and infrastructure: CISA KEV, NVD, Shodan/Censys only if used within terms.

## Next Best Move

Do not chase a giant dollar claim. The fastest credible revenue step is:

1. Pick one buyer lane.
2. Send one reviewed field-replay request.
3. Ask them to approve the baseline, held-out data, pass/fail metric, and dollar conversion.
4. Run the replay under those terms.
5. Convert the result into a pilot proposal.

