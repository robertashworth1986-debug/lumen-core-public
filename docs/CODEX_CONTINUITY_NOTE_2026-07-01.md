# Codex Continuity Note - 2026-07-01

## Current Priority

Keep LumenCore focused on reviewer-safe live proof, grant submission readiness, and the first buyer-authorized field replay. Do not drift into new dashboards unless they consolidate the existing production boards.

## Current Verified State

- Live domain proof feeds are publicly hash-verified: `12/12` required reviewer feeds match the local bundle.
- `dashboard/data/champion_metric_gauntlet.json` now reports `live_domain_reviewer_ready: true`.
- Champion gauntlet status: `11/13` gates pass. The two remaining blockers are external field validation and realized dollar savings.
- This clears the public proof-feed gate for a reviewed buyer outreach message. It does not clear field-validation, realized-savings, grant-award, live-trading, medical, or autonomous-control claims.

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

- Current internal champion: Kuramoto phase coupling.
- Named baseline: Kalman filter.
- Source-conditioned holdout result: `24/24` wins.
- Estimated rows replayed: about `2.5M`.
- Broader mapped live-source universe: `17` measured providers, `23` enabled providers, `186` mapped source files/feeds, and `313` manifest rows ready for benchmark promotion.
- Important boundary: this is internal, hash-backed, source-conditioned replay evidence, not field validation or realized savings.

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

## Working Rule For Future Passes

Use the existing master boards and feeds first:

- `mission_control.html`
- `grants.html`
- `quant_lab.html`
- `dashboard/data/champion_metric_gauntlet.json`
- `dashboard/data/live_domain_deployment_feed.json`
- `dashboard/data/first_buyer_target_board.json`
- `dashboard/data/field_validated_dollar_claim_ladder.json`

Do not create another parallel dashboard unless it replaces or consolidates an existing one. The platform wins by getting cleaner, more verifiable, and easier for a reviewer or buyer to trust.
