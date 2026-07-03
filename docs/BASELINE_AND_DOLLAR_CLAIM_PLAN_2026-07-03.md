# Baseline And Dollar Claim Plan

Generated local date: `2026-07-03`

This note keeps LumenCore's economic story strong without drifting into claims the evidence cannot yet support.

## Current Honest Position

LumenCore is strong as an internal measurement and replay platform:

- `140` registered geometry/model families across `12` lanes.
- `207` real-noise datasets ready for locked replay.
- `604` CSV/provider snapshots scanned in the latest real-noise sweep.
- `68,274` numeric samples identified in the latest sweep.
- `24` currently measured live-source adapters out of `29` enabled.
- Current internal champion: `kuramoto_phase_coupling` in the `wave_resonance_timing` lane.
- Current champion result: `24/24` source-conditioned holdout wins against a Kalman-filter baseline.

This is not yet field validation, realized savings, or a fixed buyer price. The correct next milestone is buyer-authorized field replay.

## What Kalman Means

A Kalman filter is a classical recursive estimator used to track the hidden state of a noisy dynamic system. It is common in controls, navigation, aerospace, signal processing, and grid-style state estimation.

Beating a Kalman baseline in an internal replay is meaningful because Kalman is not a toy baseline. It says the candidate handled a noisy timing/signal problem better than a respected control-estimation method under the local replay assumptions.

It does not prove that the method will beat every grid, RF, PLL, defense, medical, or trading system. It means the result deserves stronger locked replay and external validation.

## Baselines To Add Next

High priority:

- Persistence / last-value forecast
- Rolling mean
- Exponential smoothing / EWMA
- ARIMA or SARIMAX
- Holt-Winters / ETS
- Extended Kalman filter
- Unscented Kalman filter
- Particle filter
- Gaussian process regression
- Gradient boosting: XGBoost or LightGBM
- Random forest regression
- LSTM / TCN / small transformer forecast
- Model predictive control baseline
- Dijkstra / A* / min-cost flow for routing lanes
- DC power-flow / OPF baselines for grid lanes
- IEEE 39-bus, 118-bus, and 300-bus grid benchmark cases
- Kuramoto order parameter, critical coupling threshold, and phase-bound stress tests

## Dollar Claim Ladder

Safe today:

> LumenCore has internal benchmark winners and a growing real-noise replay queue. It is ready for buyer-authorized field replay.

Pilot scoping language:

> For a $1B/year value stream, each `0.001%` improvement equals about `$10,000/year`, each `0.01%` improvement equals about `$100,000/year`, each `0.1%` improvement equals about `$1,000,000/year`, and each `1%` improvement equals about `$10,000,000/year`.

Use this only as sensitivity math, not as a realized savings claim.

## Planning-Only Improvement Bands

These are planning targets for conversations with buyers. They are not field-validated claims.

| Lane | Conservative Pilot Target | On $1B/year Value Stream | What Must Validate It |
| --- | ---: | ---: | --- |
| Grid/energy timing and outage replay | `0.001%` to `0.05%` | `$10k` to `$500k/year` | Utility or lab holdout data, incumbent baseline, accepted reliability/cost metric |
| Forecasting and operational scheduling | `0.005%` to `0.1%` | `$50k` to `$1M/year` | Owner-approved forecast horizon, cost of error, replay window |
| Air/weather/water stress routing | `0.001%` to `0.03%` | `$10k` to `$300k/year` | Public agency or operator-approved impact conversion |
| Federal opportunity/grant/capture triage | productivity model only | not sector savings | Time saved, deadlines caught, submission quality, award pipeline |
| Market/trading replay | no money claim | no live claim | Independent paper/live audit, risk controls, drawdown limits, broker/exchange evidence |

## What Makes It Field Validated

Field validation starts when an external owner, lab, agency, buyer, or accepted benchmark authority supplies or approves:

- held-out operational data
- incumbent baseline
- acceptance metric
- replay window
- stress/failure cases
- economic conversion formula
- who signs off on the result

Until those exist, LumenCore should sell a paid validation pilot, not a realized savings guarantee.

## Buyer Pitch In One Sentence

> Give LumenCore your held-out data, incumbent baseline, and cost-of-error rule; we will replay our candidate families against your real constraints, freeze the evidence, and show what improved, what failed, and what can honestly be priced.

