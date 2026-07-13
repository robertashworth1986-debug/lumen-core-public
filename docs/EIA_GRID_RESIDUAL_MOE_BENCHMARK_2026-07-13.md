# EIA Grid Residual Mixture-of-Experts Benchmark

Generated UTC: `2026-07-13T21:06:28.728467+00:00`

## Verdict

- Selected on development only: `xgboost_residual`
- Protocol-grade internal champion: `false`
- Allowed claim: No protocol-grade internal champion; retain the incumbent and report the result.
- External replication complete: `false`
- Field validation complete: `false`

This test asks whether residual correction can improve a strong incumbent. It does not assume that a new geometry or machine-learning model should replace the official forecast. The router is allowed to abstain to the incumbent when its component models disagree.

## Frozen Evidence

- Protocol commit: `9fdde5f0d9836e3bdc995df22b04b8c3b72188cd`
- Protocol SHA-256: `79b4e6f92fb9dbd51eaa349ffebbc9b944bc95f7587bf26617e241dafa5380b8`
- Frozen panel SHA-256: `8b480ec4923c17d3782eacd428ee5ea599525145ce2a0772ba934aba0a40da59`
- Frozen panel row-chain SHA-256: `594684318e85e3440e385cff3e30c5d095930410572c6c4b39472814ae4655dd`
- Official EIA panel rows: `14704`
- Feature rows: `5949`
- Feature contract SHA-256: `294613987812825c8d02adafc1ccb718abfb960e7816d68e946c7d2c4bd6032d`
- Artifact chain SHA-256: `df9ef66f4069e0fa46ad08c0b733ffacacb485c87a41582ed9fbe7430aa98e19`

## Development Selection

| Rank | Candidate | Mean MASE | Mean absolute error MWh | Abstention rate |
| ---: | --- | ---: | ---: | ---: |
| 1 | `xgboost_residual` | 0.179285 | 13528.601 | 0.000 |
| 2 | `median_residual_ensemble` | 0.181042 | 13584.148 | 0.000 |
| 3 | `lightgbm_residual` | 0.187874 | 13962.406 | 0.000 |
| 4 | `agreement_gated_residual_moe` | 0.194878 | 14325.125 | 0.013 |
| 5 | `ridge_residual` | 0.212179 | 15800.183 | 0.000 |
| 6 | `half_median_residual_ensemble` | 0.276151 | 19060.170 | 0.000 |
| 7 | `official_ar_blend_75_25` | 0.371296 | 24704.648 | 0.000 |

## Untouched Holdout

| Rank | Strategy | Kind | Mean MASE | Mean absolute error MWh | Direction accuracy |
| ---: | --- | --- | ---: | ---: | ---: |
| 1 | `xgboost_residual` | `residual_candidate` | 0.212112 | 16082.490 | 0.872 |
| 2 | `direct_lightgbm_stack` | `baseline` | 0.235871 | 17874.172 | 0.858 |
| 3 | `direct_xgboost_stack` | `baseline` | 0.264246 | 20117.152 | 0.848 |
| 4 | `official_ar_equal_blend` | `baseline` | 0.425171 | 28852.556 | 0.798 |
| 5 | `autoregressive_ridge_p14` | `baseline` | 0.491378 | 37149.773 | 0.668 |
| 6 | `eia_day_ahead_forecast` | `baseline` | 0.579383 | 36568.783 | 0.796 |
| 7 | `seasonal_naive_7` | `baseline` | 1.066175 | 88617.236 | 0.595 |

## Selected Candidate Versus Baselines

Positive skill means baseline MASE minus selected-candidate MASE is positive.

| Baseline | Mean skill | CI95 | Month win rate | Authority wins | Holm p | Pass |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| `eia_day_ahead_forecast` | 0.373227 | [0.092357, 0.736906] | 0.865 | 8 | 2.09214e-07 | `true` |
| `autoregressive_ridge_p14` | 0.263498 | [0.146682, 0.373489] | 0.904 | 7 | 5.13929e-09 | `false` |
| `seasonal_naive_7` | 0.882051 | [0.711456, 1.037321] | 0.962 | 8 | 3.67439e-12 | `true` |
| `official_ar_equal_blend` | 0.204418 | [0.117863, 0.329423] | 0.942 | 8 | 5.21339e-11 | `true` |
| `direct_xgboost_stack` | 0.053757 | [0.027528, 0.079821] | 0.827 | 7 | 4.07554e-06 | `true` |
| `direct_lightgbm_stack` | 0.027746 | [0.001906, 0.050010] | 0.808 | 6 | 9.06327e-06 | `true` |

## Interpretation

- A win must survive every predeclared baseline and every robustness gate. Beating only seasonal naive or only one tree model is not enough.
- A loss is retained as evidence that the incumbent should remain in this lane.
- Development error correlations are stored in the JSON report so ensemble value can be distinguished from redundant model voting.

## Claim Boundary

This protocol can produce measured public EIA-930 software forecast evidence in native MWh. It cannot by itself establish field control, grid reliability improvement, realized savings, procurement acceptance, safety, external validation, trading edge, or an unbeatable claim.
