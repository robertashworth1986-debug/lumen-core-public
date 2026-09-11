# Denominator and paper-accounting assurance — 11 September 2026

## Scope

Two isolated offline audit modules and 59 synthetic tests. No forecast, frozen protocol, live source, production setting, order route or credential is modified. Stage 8 is inherited historical research, not a fresh independent holdout. The addition is based on main `3dc5205c759ab264e4e49cc78f59feb2846f005c`, and consumes research PR #216's packet at `6a58e9b5d7aecf8402354792ccd79add83cf748c` without merging that branch.

## Verification performed

The unchanged Stage 8 cached verifier passed locally: three source hashes, 17 normalizations, 1,173 full prediction-array replays, 275,655 scalar prediction checks, and all 21,114 metric records and CSV records reconciled. Elapsed time: 95.34 seconds in this environment. Full prediction replay shares original producer code; separate scalar checks do not make the full pipeline independently implemented.

Runtime: Python 3.13.5 and NumPy 2.3.5. Original reference Python: 3.11.9. This is additional-runtime diagnostic evidence, not exact pinned-runtime reproduction. Sixty existing Stage 8 tests and 59 new synthetic tests passed separately. No full-repository or remote-CI pass is asserted here.

## Coverage and comparison repair

`code/ops/audit_forecast_denominators.py` checks the exact hash-bound inventory before and after analysis. Every candidate is compared with both required baselines on one common target mask. Observed/scheduled, common-pair/observed and common-pair/scheduled denominators remain distinct. Identical baselines are flagged. Units, slices, horizons, losses and missing observations are retained.

The post-hoc diagnostic screen uses 100 pairs, at least 5% MAE improvement, non-worsening p95 error and three positive chronological quartiles, with at least 90% common-pair coverage of scheduled slice targets. It never authorizes promotion. This screen was designed after historical outcomes were examined and is not preregistration or confirmation.

Results: 10,557 candidate/slice audit cells. In 578 cells, at least 90% conditional coverage of observed outcomes hides less than 90% coverage of scheduled slice targets. These are dependent diagnostic cells, not independent incidents or customer losses. There are 371 descriptive screen-positive cells across reused stresses and slices, not 371 discoveries.

Clean/all-slice results: eight of 72 grid cells pass both reference-baseline screens; zero of 45 marine and zero of 36 geothermal cells pass. No clean candidate/horizon passes all three slice screens. All losses and holds remain recorded.

California median5 at three days: 555 common targets; MAE is 21.3593% better than persistence and 8.1788% worse than weekly seasonality. NDBC 44025 one-hour median5: 4,406 observed outcomes / 8,760 scheduled targets = 50.30%; 4,090 common pairs = 92.83% of observed outcomes but 46.69% of scheduled targets. The latter differs from the historical 98.80% single-baseline coverage because the new common mask also requires seasonality.

The three measured families are energy-related. Marine wave activity is not electrical production; FORGE source timezone and EIA as-published chronology remain unresolved. Six inherited other-sector contracts still have zero measured rows. No financial, emissions, uptime or plant-efficiency conversion is permitted.

## Paper accounting

`code/ops/audit_paper_accounting.py` checks a narrow, single-USD, long-only, fully funded in-memory paper ledger. It rejects live mode, unknown fields, duplicate IDs, invalid UTC chronology, unsupported events, shorts, unfunded fills, nondecimal amounts, cash mismatches and missing/stale/future marks. External deposits/withdrawals are not profit; declared fees are included.

The synthetic fixture has initial cash 1,000, a 500 deposit, two TEST units bought at 100 plus a 1 fee, one sold at 110 plus a 1 fee, and one remaining mark at 105. Cash is 1,408, equity is 1,513 and net paper P&L is 13, not 513. This is not Robert's account or reported earnings. No actual broker statement/current ledger was supplied, no broker reconciliation or profitability is established, and slippage/execution realism, leverage, derivatives and tax lots are outside this model. Existing trading holds remain unchanged.

## Reproduction

Run `python -m pytest -q tests/test_evidence_denominator_and_paper_audits.py`.

Run `python code/ops/audit_forecast_denominators.py --packet /path/to/extracted-stage8/results --expected-manifest-sha256 73ff9e4ca4fb27eea70b6e74180cf959217a38d2f8a4487f56ae280f99dec370 --out /path/to/new-audit-output`.

The original handoff ZIP digest is `897a89a06660642b4fa24932c8385c2872feb14f95ed9e89c2501609660e6b20`. Obtain it through the existing controlled handoff. Outputs cannot overwrite an existing path or be written inside the frozen result directory. The local download packet retains every audit cell, original and new test output, verifier receipt and hashes. Repository receipt: `evidence/assurance_20260911/receipt.json`.

Merge requires source review and repository CI. No deployment workflow or automatic mutation path is added. Independent reproduction, fresh source chronology, buyer-owned incumbents, adverse-regime support and willingness to pay remain separate gates.
