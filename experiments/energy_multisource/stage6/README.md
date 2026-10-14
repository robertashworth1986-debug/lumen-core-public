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
