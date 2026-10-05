# High-activity interval diagnostic — October 5, 2026

**Verdict: retain for review; no performance promotion. Fourteen of fifteen mandatory cells still miss 90% empirical high-activity coverage.**

One interval overlay was specified, tested and hash-recorded before one retrospective run. The underlying 2025 observations had already been examined; this is not a fresh holdout. No point forecast, original baseline, source threshold or scoring mask changed.

The overlay calibrates high-issue residuals using only outcomes whose target plus the assumed 30-minute delay falls strictly before the UTC update. At least 32 high-regime residuals in the past 28 days are required. This floor was fixed before execution, not selected to improve the result. It is not a power calculation or independence guarantee. Ordinary-issue intervals remain exactly unchanged.

## What happened

- Median high-activity coverage: **64.49% → 76.20%** across the same fifteen cells.
- Cells meeting the 90% high-activity target: **0 → 1 of 15**.
- Median overall interval score: **0.675% lower**; eleven cells improve, four worsen. Lower is better.
- Median overall interval width: **3.289% larger**.
- Calibration support: **3,518 of 5,754 high-issue rows (61.14%)**; the other 2,236 fall back to the unchanged baseline. These are dependent station/horizon rows, not independent storms.
- One scored execution; eleven new software tests passed, including future-outcome mutation, strict boundary exclusion, missing truth, expired history, fallback and ordinary-issue preservation.

Wider bands are expected to cover more outcomes. The useful question is whether that coverage justifies the score and width costs in every required regime. This candidate does not resolve the adverse-regime failure and is not promoted. Sparse high-activity calibration remains an observed limitation; the result does not prove it is the sole cause of undercoverage.

## Every mandatory cell

| Station | Horizon | High rows | Coverage before | Coverage after | Overall score change* | Width change |
|---|---:|---:|---:|---:|---:|---:|
| 41002 | 60 min | 555 | 51.17% | 67.21% | -2.089% | +12.612% |
| 41002 | 180 min | 557 | 55.66% | 70.02% | +0.534% | +16.038% |
| 41002 | 360 min | 558 | 61.29% | 70.61% | +3.170% | +14.718% |
| 42001 | 60 min | 108 | 46.30% | 64.81% | -1.920% | +1.825% |
| 42001 | 180 min | 108 | 51.85% | 68.52% | -0.675% | +1.618% |
| 42001 | 360 min | 107 | 64.49% | 65.42% | +0.069% | +0.163% |
| 44025 | 60 min | 353 | 62.04% | 68.27% | -2.159% | +3.289% |
| 44025 | 180 min | 353 | 69.69% | 76.20% | +0.044% | +3.232% |
| 44025 | 360 min | 352 | 74.15% | 76.99% | -0.541% | +0.985% |
| 46050 | 60 min | 300 | 70.33% | 87.00% | -1.516% | +4.871% |
| 46050 | 180 min | 300 | 81.33% | 89.67% | -0.440% | +1.579% |
| 46050 | 360 min | 300 | 87.67% | 95.00% | -0.500% | +0.839% |
| 46237 | 60 min | 601 | 63.56% | 79.03% | -3.755% | +5.165% |
| 46237 | 180 min | 602 | 68.60% | 82.06% | -2.315% | +4.848% |
| 46237 | 360 min | 600 | 72.33% | 84.83% | -2.033% | +4.023% |

*Negative score change is an improvement. All twelve months, including empty slices, are retained in result.json; overall and high-regime metrics are reported separately.

## What remains

The original prospective draft is unchanged, with 37 null fields and an unassigned independent evaluator. Actual observation retrieval time, forecast seals before targets, initial-state identity, a fixed future window, use-case thresholds and a reviewed dependence-aware inference method remain necessary. The phase rules also need an explicit definition: the final independent-execution receipt belongs after the run it attests; any required pre-run rehearsal must have a separately named receipt. Independent acceptance remains a promotion gate. The protocol digest must use an external immutable envelope or a precisely declared canonical self-field exclusion. These are design corrections, not an implemented prospective preflight or permission to execute.

The 30-minute lag is assumed; it is not evidence of historical publication availability. No finite-sample conditional coverage guarantee, independent validation, electricity or geothermal gain, cost savings, operational safety or deployment authority follows. No second candidate or threshold change was attempted after seeing this outcome.

## Identity

- Protocol SHA-256: `5475e492267303cf502b52f6071ba9e5296deb219037264aeb769d4e09828e3a`
- Runner SHA-256: `20644b7d109bfcc9f48c596e629f0c5c30cb5575def4e097159b61be1ce006c7`
- Source archive SHA-256: `a0c693328a3a614ee7646731b81497f7d5f4b33b5338c9fab0595797d1017a2d`
- Result SHA-256: `dcfc2dd87a9626f0e278a7d3a8df50556a6003a083664e4862e008cc972e5079`
- Existing historical source commit: `2c06c8315c667dec6bed426b533024ecb8300f59`.
- Runtime: Python 3.12.14 / NumPy 2.3.5; measured execution 1.637 seconds.

This advances the existing external-review lane and creates no new commercial product.


## Reproduce

Use the original hash-verified Stage 6 download packet. This run uses its unchanged `inputs/energy-stage4-ci.zip` and `results/` directory. Do not substitute current data or relabel the examined 2025 record as fresh.

```sh
python -m unittest discover -s experiments/energy_multisource/stage6/high_activity_diagnostic_20261005 -p "test_*.py" -v
python experiments/energy_multisource/stage6/high_activity_diagnostic_20261005/run_diagnostic.py --packet /path/to/extracted/stage6 --out /path/to/new/results
```

The executed NumPy version is 2.3.5. The original download is 77,535,338 bytes, SHA-256 `7e04e7d7ce0b1a0754cbb2859a9dec11a9a957f5a49b7df31dd3598e82e72ebd`. Its inner packet SHA-256 is `77e7cfdb6ae5e77840b81d2e93905735679600ebbc729c09207ca3a4290bf629`. Full candidate interval arrays and their manifest are retained in the companion diagnostic receipt bundle. Publication/review of these records is not authorization for another search or prospective execution.
