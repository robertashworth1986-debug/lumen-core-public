# FAA SDR Frozen 10,000-Scenario Benchmark

Generated UTC: `2026-07-14T02:47:47.741993+00:00`

## Result

- Independent frozen holdout reports: `10,000`.
- Strategies scored per report: `8`.
- Scenario-model evaluations: `80,000`.
- Holdout unique keys: `10,000`; development overlap: `0`.
- Strongest approved baseline: `hist_gradient_boosting`.
- Candidate promoted: `false`.

## Holdout Leaderboard

| Model | Candidate | Macro F1 | Log loss | Top-3 accuracy | ECE |
|---|---|---:|---:|---:|---:|
| hybrid_router_candidate | true | 0.142170 | 1.891384 | 0.706900 | 0.058071 |
| hist_gradient_boosting | false | 0.139775 | 1.888001 | 0.707700 | 0.058055 |
| lightgbm | false | 0.138739 | 1.884366 | 0.720800 | 0.064922 |
| xgboost | false | 0.127083 | 1.863826 | 0.713500 | 0.045719 |
| random_forest | false | 0.118650 | 1.936833 | 0.709100 | 0.022116 |
| linear_logistic_sgd | false | 0.111160 | 1.884105 | 0.719400 | 0.035968 |
| aircraft_make_frequency | false | 0.035745 | 2.278677 | 0.617800 | 0.049227 |
| training_majority | false | 0.015395 | 11.174908 | 0.362700 | 0.645499 |

## Promotion Gate

- Exact unique 10,000 holdout: `true`.
- Multiplicity-adjusted primary improvement: `false`.
- Log-loss noninferiority: `true`.
- Supported aircraft-make guardrail: `true`.
- Final candidate promotion: `false`.

Every non-win remains part of the evidence record; run volume does not override the declared gates.

## Rolls-Royce Exploratory Slice

The frozen holdout contains `28` rows matching the transparent Rolls-Royce-family rule. This count is descriptive and is not a confirmatory OEM or engine-health study.

## Reproducibility

- Protocol SHA-256: `3af7dcfce210600eb83935e2840855e192469a7253d3996e186cda39079a1895`.
- Holdout ID-set SHA-256: `9886c8c168601c47081a51919d19387cbabd899b5a70d7961e1619c1654df71f`.
- Prediction file SHA-256: `ca53fc2f573955dba8a6714569b2cdef518be740af6674cf9edce5817f545516`.
- Receipt SHA-256: `9d2144dc1fce6c5be74851f7748c6aa7fb5250ed6329abcf6e95a5b6921e565a`.

## Claim Boundary

This benchmark evaluates report-level JASC maintenance triage on public FAA SDR records. It is not an FAA or OEM evaluation, an airworthiness determination, a failure-rate estimate, an engine-health monitor, an operational decision aid, field validation, or proof of economic savings. The Rolls-Royce-family slice is descriptive only and does not imply a relationship with or validation by Rolls-Royce.
