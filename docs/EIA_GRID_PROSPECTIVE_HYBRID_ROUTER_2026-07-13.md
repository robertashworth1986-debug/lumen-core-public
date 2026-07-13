# EIA Grid Prospective Hybrid Router

Prepared UTC: `2026-07-13T21:34:19.768039+00:00`

## Purpose

This lane tests whether a frozen authority-specific specialist router can outperform the best fixed specialist on future EIA-930 demand targets. It is the prospective test of the routing and orchestration hypothesis; it is not a retrospective champion claim.

## Frozen Design

- Protocol: `config/eia_grid_prospective_hybrid_router_protocol_v1.json`
- Protocol commit: `3130a9bb1632eab25a64e388b92263ac833a729e`
- Protocol SHA-256: `77a67f201884f70110c840d4d6b98b4194dca6f32a34c63c4a09c9dd786afb86`
- Historical design cutoff: `2026-07-12`
- First allowed target: `2026-07-14`
- Backfilled predictions: prohibited
- Dynamic route overrides: prohibited
- Primary comparator: the best fixed specialist over the same prospective common-intersection window

The frozen route map is:

| Authority | Selected specialist |
| --- | --- |
| `CISO` | `xgboost_residual` |
| `ERCO` | `xgboost_residual` |
| `ISNE` | `xgboost_residual` |
| `MISO` | `xgboost_residual` |
| `NYIS` | `direct_lightgbm_stack` |
| `PJM` | `xgboost_residual` |
| `SWPP` | `autoregressive_ridge_p14` |
| `TVA` | `xgboost_residual` |

## Historical Design Evidence

The frozen route map was selected after examining the historical window, so the following figures are exploratory only:

- Routed mean MASE: `0.1968729349`
- Best fixed specialist mean MASE: `0.2121118633`
- Relative improvement: `7.184382886%`

These values motivate the prospective experiment. They do not confirm the routing hypothesis.

## Live Preflight

The live EIA dry-run read `14,711` source-panel rows and produced zero sealed predictions. Every candidate was skipped because the target actual was already present. This is a passing timing-control result: the implementation refused to convert observed targets into retrospective predictions.

- Source panel row-chain SHA-256: `704b8a76cdc8af5be8a1c07555b6a0261a9852c13353a34404a5317cbd6ce8a3`
- Existing prediction count: `0`
- Sealed record count: `0`
- Authorities skipped: `CISO`, `ERCO`, `ISNE`, `MISO`, `NYIS`, `PJM`, `SWPP`, `TVA`

## Audit Controls

- The target actual must be absent when a prediction is sealed.
- The prediction must be sealed before target-local midnight.
- Source responses, protocol identity, specialist outputs, route selection, and model receipts are recorded.
- Prediction and settlement ledgers are append-only SHA-256 chains.
- Settlement can occur only after a valid prediction record exists.
- Tests cover protocol validation, target leakage exclusion, timing eligibility, future-target selection, and chain tamper detection.

Focused verification on 2026-07-13: `15 passed` across the prospective router, residual benchmark, wave benchmark, and NASA response renderer suites.

## Evidence Gates

- Preliminary: 30 common prospective days per authority
- Confirmatory: 90 common prospective days per authority plus all statistical and robustness gates
- Durability: 180 common prospective days per authority plus external partner replication

Until those gates are reached, the correct status is `prospective collection pending`.

## Claim Boundary

A future passing result would support prospective public-data evidence for a frozen hybrid forecast router. This lane does not establish patent validity or scope, utility field control, realized savings, grid reliability improvement, production readiness, trading edge, or universal model superiority.
