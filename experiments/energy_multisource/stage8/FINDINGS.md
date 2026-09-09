# Stage 8 findings — 9 September 2026

## Technical summary

**Eight grid candidate/horizon cells clear both aggregate reference-baseline screens; none clears every clean-data regime screen.** The engineering result is an auditable shortlist with explicit failure boundaries, not a universally superior forecaster.

The frozen sweep covers 17 measured series, 23 observation-stress scenarios, three horizons per domain, two baselines, three candidates and three slices. It retains 1,173 prediction-array packets and 21,114 comparison records. Of those records, 3,219 are descriptive candidate-only screens, 4,914 show MAE regressions with sufficient support, 10,684 lack required support/coverage and 2,297 fail effect, tail or stability thresholds. These overlapping records are not independent successes or trials.

## Baselines change the decision

For California (CISO), the five-day median at a three-day horizon lowers clean-data MAE by **21.3593% versus persistence**, with p95 absolute error lower by 11.1769%, on 555 identical paired targets. Against the weekly seasonal baseline, the same candidate's MAE is **8.1788% worse**, and p95 error is 5.2827% worse. Its high-at-issue slice has only 21 pairs; its ramp slice has 46 pairs and 11.2300% worse MAE versus persistence. The favorable aggregate percentage cannot support promotion.

The eight clean-data cells passing both aggregate screens are: ISNE median at three days; ISNE blend at three and seven days; MISO blend at three days; NYIS median and blend at three days; PJM blend at three days; and TVA blend at three days. This is a post-screen descriptive shortlist, not a fresh validation set. The seven-day grid seasonal baseline and persistence use the same observation, so they are identical comparators at that horizon, not two independent benchmarks.

## Domain results retain the losses

| Clean data, all slice, versus persistence | Candidate-only | MAE regression | Other hold | Total |
|---|---:|---:|---:|---:|
| Grid | 12 | 47 | 13 | 72 |
| Marine | 0 | 45 | 0 | 45 |
| Geothermal | 0 | 34 | 2 | 36 |

Every tested clean marine candidate loses to persistence. In geothermal, the best clean MAE change among these candidates is only 2.5336% for the pump-rate blend at 60 minutes, while its p95 error worsens by 8.9208%. Earlier energy-lane models and interval methods are not reproduced as candidates in this sweep; these results neither replace nor invalidate their separate frozen experiments.

## Missing outcomes can hide behind high pair coverage

For NDBC station 44025 at one hour, only **4,406 of 8,760 scheduled targets (50.30%)** have a valid observed outcome. Median-versus-persistence pair coverage is 98.80% **conditional on those observed outcomes**. Those percentages answer different questions. Pair coverage is not end-to-end telemetry availability or prediction-service uptime. Station 46042/2025 remains a retained source hold, rather than being substituted or erased.

Under the first 30%-missingness seed, all 153 all-slice comparisons versus persistence are held for insufficient support/coverage. This is expected fail-closed behavior of the research screen. Across all other stress scenarios, potential improvements and regressions remain visible in the full packet; no single seed or favorable stress cell is presented as a general benefit.

## Experimental design and integrity

Calibration uses 2024 EIA data, 2023 marine data and the first 40% of the FORGE record's elapsed span. Evaluation uses the later available EIA daily record, the frozen 2025 marine records and the remaining FORGE span. Time bucketing uses right-closed means with no imputed future targets. The absent marine 2024 year remains empty; it is not silently compressed out of the timeline. Forecast targets use exact cadence offsets.

All models, horizons, stress rules, metrics and screen thresholds were fixed for this run. All data was already historically available to the lane. The first local freeze was `ddfef1f4`; a format-only revision was frozen at `aa452a36d7e441404120010fbc9a4429ff823e52`. Publication of code after historical outcomes is not prospective registration.

The first packet was correctly rejected after a consolidated JSON file was truncated. The replacement uses 1,173 metric shards, none larger than the enforced 2 MiB bound; the largest JSON artifact in the replacement is 271,224 bytes. The two runs' complete CSV bytes match: SHA-256 `f1951a90e229cd6f0d573f1e112fd848e174217c2ebdfd33acbdcfb14e919223`. The replacement result-manifest SHA-256 is `73ff9e4ca4fb27eea70b6e74180cf959217a38d2f8a4487f56ae280f99dec370`.

The verifier separately checks source authenticity, full normalization/prediction replay, scalar forecast spot checks, all metric recomputations, complete cell inventories and CSV/shard reconciliation. Consult `VERIFICATION.json` for the completed computational verification receipt. The selected research suite passes 176 tests and 13 subtests, including 60 Stage 8 edge/cache-contract tests. This is not a whole-repository CI or independent field-validation claim.

## Limitations and what to test next

The stress patterns and thresholds are synthetic engineering choices, not estimated frequencies or buyer requirements. Only two seeds are used for randomized missingness and noise; chronological quartiles provide descriptive stability checks rather than confidence intervals. Correlated horizons, sensors and seeds are not independent evidence. The three measured domains all relate to energy; the six other-sector contracts contain no measured performance.

Choose one of the eight grid shortlist cells with a buyer-owned incumbent and fixed unit/metric contract. Freeze a genuinely fresh evaluation window, publication-time receipts, adverse-regime support rules, accepted uncertainty method and an independent reviewer before opening outcomes. Measure the operational decision and costs separately before attempting any financial conversion. Source data ownership, accepted baselines and real decision utility remain unassigned.

Open questions: Does the candidate beat the actual incumbent on as-published inputs? Is performance maintained on rare ramps and high-demand days? How much missingness occurs in production? Does a forecast change improve a real decision after latency and implementation costs? These packets make those questions testable; they do not answer them by extrapolating an energy percentage to another sector.
