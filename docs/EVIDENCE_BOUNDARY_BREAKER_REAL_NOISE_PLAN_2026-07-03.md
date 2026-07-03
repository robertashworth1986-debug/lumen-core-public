# Evidence Boundary Breaker Real Noise Plan

Generated local date: `2026-07-03`

Purpose: move LumenCore from synthetic oscillatory-signal evidence toward real-world replay evidence without breaking claim discipline.

## Current Boundary

The synthetic evidence boundary is correct:

> Generated oscillatory-signal software benchmark only. Phase drift, noise, dropout, shock, multimode interference, forecast horizon, and stability metrics are synthetic assumptions. Results do not establish grid, PLL hardware, RF, medical, defense, field, safety, certification, trading, or real-dollar performance.

This boundary protects the platform. We do not remove it. We outgrow it by adding real-noise lanes with locked baselines and promotion gates.

## What Counts As Real Noise

Real noise is not just randomness. Real noise is measured uncertainty from a real source system:

- market microstructure noise from Kraken/Coinbase/Alpaca/market feeds
- energy load, generation, outage, and forecast residuals from EIA/NOAA/NWS/FRED style sources
- air-quality drift and environmental sensor variability from AirNow/EPA-style feeds
- macro revision noise from labor, rates, treasury, and economic series
- sports-market pricing noise only as a non-operational probabilistic market benchmark
- buyer-owned grid, RF, PLL, maritime, or industrial telemetry after external approval

## What Trading Data Can Prove

Trading data is full of real noise and is useful for stress-testing timing, drift, outliers, missing ticks, liquidity gaps, and regime shifts.

Trading data can support:

- real-noise replay robustness
- latency and update-cadence tests
- directional prediction under noisy conditions
- benchmark comparisons against naive, Kalman, ARIMA-style, moving-average, and persistence baselines
- risk-control and fail-closed behavior

Trading data cannot support yet:

- institutional trading readiness
- profitable live execution claims
- autonomous live trading permission
- guaranteed alpha
- agency or utility field validation

The right wording is:

> LumenCore uses market data as a high-noise real-world benchmark lane for timing and robustness. It is not being presented as a live trading product or profit claim.

## Promotion Gates

Each real-noise lane must pass these gates before it upgrades the evidence boundary:

1. Source identity recorded.
2. Source timestamp window locked.
3. Raw input hash frozen.
4. Schema adapter documented.
5. Baseline named before the run.
6. Candidate and baseline share the same input window.
7. Metric named before the run.
8. No post-hoc tuning on the holdout window.
9. Negative results logged.
10. Output hash and manifest frozen.

To become field validation, add:

11. External owner or lab approves the held-out data.
12. External owner or lab approves the incumbent baseline.
13. External owner or lab approves the acceptance metric.
14. Economic conversion is agreed before scoring.
15. Result is signed, accepted, or reproducibly rerun by the external owner/lab.

## Immediate Real-Noise Lanes

### Lane 1: Market Noise Replay

Source examples:

- Kraken public/live feed
- Coinbase public feed
- Alpaca market data
- FRED rates
- Treasury yields

Metrics:

- MAE/RMSE against next-window value
- directional accuracy
- phase proxy error
- drawdown risk proxy
- dropout robustness
- shock recovery
- latency budget

Claim stage if passed:

> real-noise internal replay benchmark

Not allowed:

> trading profit, institutional alpha, autonomous execution readiness

### Lane 2: Energy Forecast And Grid Proxy Replay

Source examples:

- EIA generation/load/outage feeds
- NOAA/NWS weather
- FRED macro and energy-adjacent pressure variables
- AirNow/EPA environmental stress variables

Metrics:

- forecast error reduction
- drift lead time
- false alarm rate
- phase/timing coherence
- source ablation
- rolling-window stability

Claim stage if passed:

> grid/energy proxy replay benchmark

Not allowed:

> utility field validation, avoided outage savings, operational control readiness

### Lane 3: External Buyer Field Replay

Source examples:

- EPRI/Incubatenergy utility-provided data
- EPB/ORNL historical grid or microgrid data
- TVA/Spark partner data
- lab-provided PLL/RF bench data

Metrics:

- chosen by the owner before replay
- incumbent baseline locked by owner
- economic conversion locked only after technical acceptance terms are defined

Claim stage if passed:

> buyer-authorized field replay

Allowed only after acceptance:

> field-validated result for that specific system, metric, and window

## Outreach Approval Status

Robert approved sending the staged outreach emails in chat on `2026-07-03`.

Staged messages:

- EPRI / Incubatenergy Labs reply
- Black Dog / Scott Kelly follow-up
- EPB field replay routing request
- Baker Donelson patent/legal intake request

Operational note: the Gmail connector token was expired and the browser automation surfaces were not reachable at the time of staging. Compose URLs were opened and bodies were copied to clipboard for manual send/review. Confirm sent status manually before marking any outreach item as sent.

## Next Technical Build Target

Build or run a `real_noise_promotion_sweep` that creates one frozen result per lane:

- `market_noise_replay`
- `energy_grid_proxy_replay`
- `air_environmental_noise_replay`
- `macro_revision_noise_replay`

Each output must include:

- source system
- row count
- time window
- raw hash
- baseline
- candidate family
- metric
- result
- pass/fail
- next claim stage

The goal is not to make the boundary disappear. The goal is to replace synthetic-only language with a stronger, truthful ladder:

1. synthetic stress benchmark
2. real-noise internal replay benchmark
3. source-conditioned holdout benchmark
4. buyer-authorized field replay
5. externally accepted field result
6. bounded avoided-cost estimate
7. contracted or realized savings

