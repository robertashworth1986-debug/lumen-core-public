# Stage 6 — uncertainty calibration and adverse-regime assurance

RESEARCH ONLY. Previously examined 2025 wave observations. No performance promotion, independent validation, production deployment, electricity gain or financial claim.

This pass keeps every point forecast fixed and compares four uncertainty-band methods. It asks whether the bands achieve their advertised coverage without becoming unnecessarily wide, especially when high activity is already visible at forecast issue time. The target remains WVHT squared times APD in m^2 s, not electricity or calibrated wave power.

## Registered design

Protocol commit: `65d45b1a7ef9f21a42c10c684cdcf38c5287d06f`.

Five stations, three forecast horizons, two inherited point forecasters, four interval methods and two feedback delays produce 240 interval metric records. Ninety method comparisons at the original 30-minute delay include descriptive 7-day and 14-day paired calendar-block bootstrap intervals. The 90-minute condition changes interval feedback only, not the timing of inherited point forecasts. The delays are assumed, not measured dissemination latencies.

The four methods are the legacy pooled absolute-residual band, activity-scaled symmetric band, activity-scaled signed/asymmetric band, and a clipped delayed-feedback adaptive band. The last method is ACI-inspired; clipping, delayed outcomes and daily batching mean that the original paper's theoretical guarantees are not claimed for this implementation.

References: Gibbs and Candes, Adaptive Conformal Inference Under Distribution Shift, https://arxiv.org/abs/2106.00170 ; interval-score definition, https://otexts.com/fpp3/distaccuracy.html . Standard statistical ingredients are not claimed as proprietary mathematical inventions.

## Interpret the results correctly

`summary.csv` and `interval_metrics.json` give coverage, width, interval score and adverse slices for every method. The interval score is width plus a penalty for truth outside the band; smaller is better. An improvement in that score is not an improvement in point-forecast MAE, energy production, plant efficiency or revenue.

`comparisons.json` retains all ninety descriptive comparisons. These intervals are not multiplicity-adjusted or familywise. Repeated and overlapping forecasts are dependent, and the 2025 record was already examined in earlier research stages. No winner can be promoted from this pass alone.

High-at-issue conditions use the contemporaneous observation and a threshold fixed from 2023. High-realized-target slices use the future outcome only for retrospective evaluation; they are not an operational detection rule. Coverage near 90% on average does not imply 90% coverage in either adverse slice, in every month or in a new deployment.

The legacy interval implementation must reproduce saved Stage 4 radii within 1e-10 tolerance before results are accepted. All methods and feedback-delay conditions use identical original target pairs. Missing future truth is never filled. The unavailable 46042 2025 source is not substituted.

## What the downloadable package contains

- Exact original Stage 4 source/result archive, SHA-256 `a0c693328a3a614ee7646731b81497f7d5f4b33b5338c9fab0595797d1017a2d`.
- All Stage 6 metrics, descriptive comparisons and per-issue interval arrays; NPZ arrays can be loaded with NumPy and `allow_pickle=False`.
- Source-code snapshot, registered protocol, unit-test log, input/output checksum manifest, and Git bundle of the executed checkpoint's complete reachable ancestry.

The packet is a versioned research backup, not a copy of every laptop/VPS file or every project. Release storage depends on retaining the repository and account. Domain `lumen-core.ai`, main, production, DNS and laptop/VPS contents are not changed by this workflow.

## Reproduce offline

Verify `SHA256SUMS.txt` and `CHECKPOINT_MANIFEST.json` in the download wrapper first. Extract the inner Stage 6 ZIP, then extract `research-code.zip` into a separate code folder. Use Python 3.11 and NumPy 2.3.5:

```sh
python -m pip install numpy==2.3.5
python -m unittest discover -s experiments/energy_multisource/stage6 -p 'test_*.py' -v
python experiments/energy_multisource/stage6/run_stage6.py --prior-zip ../inputs/energy-stage4-ci.zip --out ../reproduced-stage6
```

The input path above assumes the code folder is a direct child of the extracted packet folder. Raw sources and point forecasts are frozen. Compare numerical arrays and JSON results, not ZIP compression timestamps, when checking cross-environment reproduction.

## Continuation

Cumulative review remains PR #215; the owner-assigned tracker is issue #214. This pass does not close the scientific or merge gates. Use the Stage 6 closeout in `evidence/energy_continuity/` when available for exact execution, publication and mirror receipts. Select a clearly specified interval method only for a fresh registered evaluation, then obtain independent technical review before making a deployment or commercial-benefit claim.

## Replay and regime assurance continuation

`verify_stage6.py` checks the exact result inventory through the package verifier, binds primitive arrays to the SHA-pinned original Stage 4 archive, replays all interval bounds and feedback metadata with the retained implementation, and recomputes all 240 metric records and 90 comparisons. Duplicate JSON members, missing or repeated cells, invalid Boolean gates, malformed CSV columns, altered intervals, and inconsistent metric claims are rejected. `package_stage6.py` now requires this check before Git/archive side effects and only packages the exact declared result files into fresh output directories.

This is deterministic replay and numerical consistency, not validation by an independent implementation or evaluator. It does not establish a fresh holdout, a physical benefit, or algorithmic novelty. Numeric replay uses absolute and relative tolerance 1e-10; identities, masks and discrete metadata are exact.

Against the published Stage 6 packet, all 15 `adaptive_scaled_28d` / `delayed_blend_v01` / 30-minute-delay high-at-issue slices fall below nominal 90% empirical coverage (46.30% to 87.67%). The 100-row reporting floor is descriptive, not an effective independent sample size or inferential guarantee. These slices are dependent and use the same examined 2025 record. The verifier retains all methods, delays, months and insufficient slices; it does not select a favorable subset.

Run this continuation from the current review code against an extracted original packet. The output path must not already exist:

```sh
python experiments/energy_multisource/stage6/verify_stage6.py --results /path/to/packet/results --output /path/to/new-assurance.json
```

The default frozen source is `/path/to/packet/inputs/energy-stage4-ci.zip`. Use `--source-zip` only to select another location for the exact same SHA-pinned bytes. The older release's embedded code does not contain this continuation; retain the reviewed continuation commit and receipt alongside the immutable original download.

## Fresh evaluation design

`FRESH_EVALUATION_DRAFT.json` selects one candidate for review: the existing `adaptive_scaled_28d` wrapper around `delayed_blend_v01`, applied to all five stations and all three horizons. It compares that candidate with the legacy wrapper and the same activity scaling without adaptive feedback. This advances the existing external-evaluation outcome. The draft has **not been frozen or executed**; prospective execution and promotion remain false.

The future decision must require useful interval scores and high-activity coverage in every declared cell. A favorable aggregate cannot erase a regime failure. For example, the preserved 46237 / one-hour / blend result contains 219 misses among 601 high-activity issues, versus 1,597 misses among 16,867 ordinary issues: miss rates of 36.44% and 9.47%. Overall coverage of 89.60% hides this 3.85-fold descriptive difference. These are dependent observations in the already examined record, not additional independent evidence.

Starting today, using a new download, or labeling data "2026" does not establish a fresh test. The draft requires a consumed-data inventory, actual retrieval and durable prediction timestamps, a source-revision rule, a fixed future window, and exact code/state/environment bindings. The evaluator, independent timestamp receipt, dates, sample-support floors, material-effect thresholds and confirmatory inference implementation remain explicitly unassigned. Insufficient high-activity evidence yields a hold; the window cannot be extended after seeing a result.

[Original adaptive conformal inference](https://proceedings.neurips.cc/paper/2021/hash/0d441de75945e5acbc865406fc9a2559-Abstract.html) concerns an exact update and long-time coverage, while [later distribution-shift work](https://www.jmlr.org/papers/v25/22-1218.html) studies local regret and adaptive step sizes. Neither source confers its guarantee on this clipped, delayed, batched heuristic. [Sequential forecast-comparison methods](https://arxiv.org/abs/2110.00115) offer a route to appropriate monitoring, but require a reviewed score, information boundary and treatment of delayed/overlapping outcomes. The current diagnostic bootstrap remains descriptive.
