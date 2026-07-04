# Baseline Gauntlet Coverage

Generated UTC: `2026-07-04T02:11:24.641020+00:00`

Baseline coverage audit only. EXECUTED means present in the locked source-conditioned replay feed. REGISTERED means named in the benchmark registry but not run by the current adapter. Per-baseline comparison and win counts come from route-level comparison rows where available. Missing advanced adapters or IEEE cases must be added before those baselines can be claimed as tested. This is not field validation or realized savings.

## Summary

- Requested baselines: `29`
- Executed in locked replay: `15`
- Replay proxy ready from accepted-metric audit: `2`
- Registered but not adapter-executed: `3`
- Blocked by missing package/dataset: `0`
- Implementation needed: `8`
- Locked replay comparisons: `1969`
- Locked replay candidate wins: `1355`
- Locked replay estimated rows: `7152253`
- Locked replay numeric samples: `92056`
- Attribution scope: Per-baseline comparisons and candidate wins are counted from route-level comparison rows. Rows replayed are per-baseline exposure counts and should not be summed as unique global rows.
- SHA-256: `700209ca1a12852a36b69c325f0518bd1d00a0a6c00f9329f4cbc5826d61a4d3`

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
| Persistence / last-value forecast | `EXECUTED_IN_LOCKED_REPLAY` | `persistence` | `82` | `64` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Rolling mean | `EXECUTED_IN_LOCKED_REPLAY` | `rolling_mean` | `82` | `51` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Exponential smoothing / EWMA | `EXECUTED_IN_LOCKED_REPLAY` | `ewma` | `82` | `36` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| ARIMA or SARIMAX | `EXECUTED_IN_LOCKED_REPLAY` | `arima` | `147` | `147` | `2880400` | `wave_resonance_timing` | `` |  |
| Seasonal naive | `EXECUTED_IN_LOCKED_REPLAY` | `seasonal_naive` | `82` | `51` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Holt-Winters / ETS | `EXECUTED_IN_LOCKED_REPLAY` | `holt_winters_ets` | `82` | `49` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Kalman filter | `EXECUTED_IN_LOCKED_REPLAY` | `kalman_filter, scalar_kalman_filter` | `229` | `175` | `5595647` | `energy_price_pressure_proxy, wave_resonance_timing` | `` |  |
| Extended Kalman filter | `EXECUTED_IN_LOCKED_REPLAY` | `extended_kalman_filter` | `82` | `26` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Unscented Kalman filter | `EXECUTED_IN_LOCKED_REPLAY` | `unscented_kalman_filter` | `82` | `30` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Particle filter | `EXECUTED_IN_LOCKED_REPLAY` | `particle_filter` | `82` | `71` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Gaussian process regression | `EXECUTED_IN_LOCKED_REPLAY` | `gaussian_process_regression` | `82` | `47` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Gradient boosting: XGBoost | `EXECUTED_IN_LOCKED_REPLAY` | `xgboost` | `82` | `46` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Gradient boosting: LightGBM | `EXECUTED_IN_LOCKED_REPLAY` | `lightgbm` | `82` | `46` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| Random forest regression | `EXECUTED_IN_LOCKED_REPLAY` | `random_forest_regression` | `82` | `47` | `2715247` | `energy_price_pressure_proxy` | `` |  |
| LSTM forecast | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| TCN forecast | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Small transformer forecast | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Model predictive control baseline | `REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED` | `model_predictive_control` | `0` | `0` | `0` | `` | `` |  |
| Dijkstra routing baseline | `REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED` | `dijkstra` | `0` | `0` | `0` | `` | `` |  |
| A* routing baseline | `REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED` | `a_star` | `0` | `0` | `0` | `` | `` |  |
| Min-cost flow routing baseline | `EXECUTED_IN_LOCKED_REPLAY` | `min_cost_flow` | `11` | `8` | `695728` | `branching_transport` | `` |  |
| DC power-flow baseline | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| OPF baseline | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| IEEE 39-bus grid benchmark case | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| IEEE 118-bus grid benchmark case | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| IEEE 300-bus grid benchmark case | `IMPLEMENTATION_NEEDED` | `` | `0` | `0` | `0` | `` | `` |  |
| Kuramoto order parameter | `REPLAY_PROXY_READY_FROM_ACCEPTED_METRIC_AUDIT` | `` | `0` | `0` | `0` | `` | `` | Run the same metric on IEEE 39/118/300 cases or a buyer-approved topology. |
| Kuramoto critical coupling threshold | `EXTERNAL_TOPOLOGY_REQUIRED` | `` | `0` | `0` | `0` | `` | `` | Obtain IEEE bus case adapter or buyer-supplied graph, natural frequencies, and acceptance metric. |
| Kuramoto phase-bound stress tests | `REPLAY_PROXY_READY_FROM_ACCEPTED_METRIC_AUDIT` | `` | `0` | `0` | `0` | `` | `` | Add instrumented phase logs, PMU-like traces, RF IQ captures, or accepted grid cases. |

## Interpretation

- Executed locked replay coverage now includes classical forecast baselines, ETS/Holt-Winters, ARIMA, scalar/standard Kalman plus EKF/UKF/particle filters, Gaussian process, random forest, XGBoost, LightGBM, and min-cost-flow routing.
- Kuramoto order-parameter and phase-bound stress are now represented as accepted-metric replay proxies through the Kuramoto accepted metric audit; this improves reviewer language without claiming physical field validation.
- MPC, Dijkstra, and A* are registered in the geometry registry but are not executed by this locked replay adapter yet.
- LSTM/TCN/small-transformer forecasts, DC power-flow/OPF, IEEE 39/118/300 bus cases, and critical-coupling metrics still need adapters, accepted topology files, or buyer/agency-approved benchmark data.
- This strengthens the technical validation story, but it still does not authorize field-validation, realized-savings, trading-profit, safety, medical, or certification claims.
