# Geometry Field Validation Protocol

Generated UTC: `2026-07-01T05:24:39.719558+00:00`

This protocol converts robust repeat-window candidates into buyer- or agency-authorized validation plans. It does not itself prove field validation, realized savings, procurement value, or trading edge.

## Summary

- Protocols generated: `2`
- Pilot-scoping ready: `2`
- Top family: `brachistochrone_descent`
- Top lane: `optimal_curve_transport`
- Ready for field-validation claim: `false`
- Ready for real-dollar claim: `false`
- Ready for bulk sales claim: `false`
- Protocol chain SHA-256: `7402dfd38c1263308005751070deca96613279d44dcdc930f9f349e29997b2c2`

## Protocols

### 1. `brachistochrone_descent`

- Lane: `optimal_curve_transport`
- Pilot: Constrained Transport / Routing Replay Pilot
- Evidence stage: `ready_for_buyer_authorized_pilot_scoping`
- Evidence: 12/12 repeat windows, min delta `0.067174`, lower 95 delta `0.074954`, minimum sources `5`.
- Evidence strength score: `194.939`
- Buyer data required:
  - timestamped constraint windows with obstacles, limits, or route/path decisions
  - the incumbent route/path or dispatch decision used at the time
  - measured outcome such as latency, energy, loss, exposure, or recovery time
  - cost or risk conversion factors supplied by the buyer
  - holdout windows selected before model scoring
- Acceptance gate:
  - At least `20` pre-registered holdout windows, `3` independent sources/sensors, candidate win rate >= `0.6`, Wilson lower win rate >= `0.5`, lower 95 delta > `0.0`.
### 2. `kuramoto_phase_coupling`

- Lane: `wave_resonance_timing`
- Pilot: Wave / Resonance Timing Forecast Pilot
- Evidence stage: `ready_for_buyer_authorized_pilot_scoping`
- Evidence: 5/5 repeat windows, min delta `0.107803`, lower 95 delta `0.113548`, minimum sources `5`.
- Evidence strength score: `180.562`
- Buyer data required:
  - timestamped oscillatory or cyclic measurements
  - incumbent forecast, filter, or timing-control baseline
  - measured downstream outcome such as error, drift, outage lead time, or intervention cost
  - known exogenous event markers where available
  - holdout windows selected before model scoring
- Acceptance gate:
  - At least `20` pre-registered holdout windows, `3` independent sources/sensors, candidate win rate >= `0.6`, Wilson lower win rate >= `0.5`, lower 95 delta > `0.0`.

## Claim Boundary

- The current proof supports paid evaluation and pilot scoping.
- Real-dollar claims require buyer-approved economic conversion factors and a completed field-data pilot.
- Bulk frozen-delta sales claims remain blocked.
- Live trading or autonomous operational execution remains blocked.
