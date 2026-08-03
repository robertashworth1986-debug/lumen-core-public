# Baseline Gauntlet Coverage

Generated UTC: `2026-07-29T08:11:03.613121+00:00`

Compatibility-gated baseline coverage audit only. EXECUTED means a requested baseline category maps to a comparison family in the current locked replay. REGISTERED means named in the benchmark registry but not run by the current adapter. Context-only manifest rows and incompatible tasks are excluded. Missing advanced adapters or IEEE cases must be added before those baselines can be claimed as tested. This is not field validation, superiority, or realized savings.

## Summary

- Requested baselines: `29`
- Requested categories executed in locked replay: `9`
- Distinct comparison families in locked replay: `21`
- Replay proxy ready from accepted-metric audit: `2`
- Registered but not adapter-executed: `2`
- Blocked by missing package/dataset: `0`
- Implementation needed: `15`
- Locked replay comparisons: `22`
- Locked replay candidate wins: `10`
- Locked replay estimated rows: `0`
- Locked replay numeric samples: `32608`
- Attribution scope: Executed-in-locked-replay counts only the 29 reviewer-requested categories that map to a current comparison family. Distinct baseline families counts every source-native or domain-native comparison family. Row exposure is repeated per baseline and must not be summed as unique global rows.
- SHA-256: `ce9c9a3f042ee94eb23b01b3eef7be47af5074a6bfbffb9982f1374bf7aac736`

## Package Status

- `filterpy`: `available`
- `lightgbm`: `available`
- `networkx`: `available`
- `numpy`: `available`
- `scipy`: `available`
- `sklearn`: `available`
- `statsmodels`: `available`
- `tensorflow`: `available`
- `xgboost`: `available`

## Requested Baselines

| Baseline | Status | Matched Replay Baselines | Route Comparisons | Candidate Wins | Row Exposure | Lanes | Missing Packages | Next Unlock |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| Persistence / last-value forecast | `EXECUTED_IN_LOCKED_REPLAY` | `naive_last` | `2` | `0` | `32548` | `time_series_model_routing, wave_resonance_timing` | `` |  |
| Rolling mean | `EXECUTED_IN_LOCKED_REPLAY` | `moving_average` | `1` | `1` | `17298` | `time_series_model_routing` | `` |  |
| Exponential smoothing / EWMA | `EXECUTED_IN_LOCKED_REPLAY` | `exponential_smoothing` | `1` | `1` | `17298` | `time_series_model_routing` | `` |  |
| ARIMA or SARIMAX | `REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED` | `arima` | `0` | `0` | `0` | `` | `` |  |
| Seasonal naive | `EXECUTED_IN_LOCKED_REPLAY` | `seasonal_naive_7, seasonal_naive_source_period` | `2` | `1` | `32548` | `time_series_model_routing, wave_resonance_timing` | `` |  |
| Holt-Winters / ETS | `EXECUTED_IN_LOCKED_REPLAY` | `damped_holt_ets` | `1` | `0` | `17298` | `time_series_model_routing` | `` |  |
| Kalman filter | `EXECUTED_IN_LOCKED_REPLAY` | `kalman_local_linear_trend` | `1` | `0` | `15250` | `wave_resonance_timing` | `` |  |
| Extended Kalman filter | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Unscented Kalman filter | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Particle filter | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Gaussian process regression | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Gradient boosting: XGBoost | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Gradient boosting: LightGBM | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Random forest regression | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| LSTM forecast | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| TCN forecast | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Small transformer forecast | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Model predictive control baseline | `REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED` | `model_predictive_control` | `0` | `0` | `0` | `` | `` |  |
| Dijkstra routing baseline | `EXECUTED_IN_LOCKED_REPLAY` | `dijkstra` | `1` | `1` | `42` | `branching_transport` | `` |  |
| A* routing baseline | `EXECUTED_IN_LOCKED_REPLAY` | `a_star` | `1` | `1` | `42` | `branching_transport` | `` |  |
| Min-cost flow routing baseline | `EXECUTED_IN_LOCKED_REPLAY` | `min_cost_flow` | `1` | `1` | `42` | `branching_transport` | `` |  |
| DC power-flow baseline | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| OPF baseline | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| IEEE 39-bus grid benchmark case | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| IEEE 118-bus grid benchmark case | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| IEEE 300-bus grid benchmark case | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Kuramoto order parameter | `REPLAY_PROXY_READY_FROM_ACCEPTED_METRIC_AUDIT` | `` | `0` | `0` | `0` | `` | `` | Run the same metric on IEEE 39/118/300 cases or a buyer-approved topology. |
| Kuramoto critical coupling threshold | `EXTERNAL_TOPOLOGY_REQUIRED` | `` | `0` | `0` | `0` | `` | `` | Obtain IEEE bus case adapter or buyer-supplied graph, natural frequencies, and acceptance metric. |
| Kuramoto phase-bound stress tests | `REPLAY_PROXY_READY_FROM_ACCEPTED_METRIC_AUDIT` | `` | `0` | `0` | `0` | `` | `` | Add instrumented phase logs, PMU-like traces, RF IQ captures, or accepted grid cases. |

## Interpretation

- Executed compatibility-gated coverage includes persistence, moving average, exponential smoothing, source-period seasonal naive, damped Holt/ETS, local-linear-trend Kalman, min-cost-flow, Dijkstra, and A* categories, plus additional source-native comparison families shown in the locked replay.
- ARIMA/SARIMAX, EKF/UKF/particle filters, Gaussian process, random forest, XGBoost, and LightGBM are not currently executed by this compatibility-gated adapter and must not be described as tested.
- Kuramoto order-parameter and phase-bound stress are now represented as accepted-metric replay proxies through the Kuramoto accepted metric audit; this improves reviewer language without claiming physical field validation.
- Routing/control baseline status is generated from the replay rows: executed `dijkstra, a_star`; registered but not executed `model_predictive_control`.
- LSTM/TCN/small-transformer forecasts, DC power-flow/OPF, IEEE 39/118/300 bus cases, and critical-coupling metrics still need adapters, accepted topology files, or buyer/agency-approved benchmark data.
- This strengthens the technical validation story, but it still does not authorize field-validation, realized-savings, trading-profit, safety, medical, or certification claims.
