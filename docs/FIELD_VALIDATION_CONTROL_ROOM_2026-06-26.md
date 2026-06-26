# Field Validation Control Room

Generated UTC: `2026-06-26T21:14:20.785664+00:00`

One reviewer/buyer control surface for the strongest geometry evidence, current claim gates, field-validation blockers, and next validation actions.

## Current Truth

- Strongest current family: `kuramoto_phase_coupling`
- Lane: `wave_resonance_timing`
- Asset score: `336.069`
- Status: `ready_to_request_field_replay_not_yet_field_validated`
- Internal wins vs Kalman: `24/24`
- Estimated rows replayed: `2506267`
- Source systems: `4`
- Best secondary buyer-pilot family: `brachistochrone_descent`

## Claim Gates

- Manual outreach ready: `true`
- Bulk email allowed: `false`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`
- Fixed-dollar delta claim allowed: `false`
- Live autonomous execution allowed: `false`

## Strongest Proof Bridge

- Candidate: `kuramoto_phase_coupling`
- Baseline: `kalman_filter`
- Holdout result: `24/24`
- Mean delta: `0.139875`
- Wilson lower 95%: `0.862024`
- Chain SHA-256: `b723b3cf65d3971b0492e41cc27fc82e1fba57a5e0d672a67e9818348313f2e6`

This supports a field-replay request. It does not establish field validation or a realized-dollar claim.

## Top Assets

### `kuramoto_phase_coupling`

- Lane: `wave_resonance_timing`
- Asset score: `336.069`
- Evidence status: `expanded_source_conditioned_holdout_winner_not_field_validated`
- Claim stage: `buyer_authorized_field_replay_request_ready_not_field_validated`
- Benchmark hypothesis: Test phase-locking features for oscillatory datasets.

### `brachistochrone_descent`

- Lane: `optimal_curve_transport`
- Asset score: `273.826`
- Evidence status: `rolling_champion_repeat_live_context_not_field_validated`
- Claim stage: `rolling_champion_not_field_validated`
- Benchmark hypothesis: Test fastest constrained descent versus straight/spline/minimum-jerk routes.

### `thermal_plume_convection`

- Lane: `thermal_ventilation`
- Asset score: `188.846`
- Evidence status: `rolling_champion_repeat_live_context_not_field_validated`
- Claim stage: `rolling_champion_not_field_validated`
- Benchmark hypothesis: Test passive heat evacuation under hotspots.

### `leaf_veins`

- Lane: `branching_transport`
- Asset score: `151.3`
- Evidence status: `triple_source_live_candidate_needs_repeat_run`
- Claim stage: `live_replay_candidate_needs_repeat`
- Benchmark hypothesis: Test transport under random vein failures.

### `beast_algo_echo_stack`

- Lane: `time_series_model_routing`
- Asset score: `115.0`
- Evidence status: `proof_value_candidate_not_performance_claim`
- Claim stage: `live_replay_ready_not_field_validated`
- Benchmark hypothesis: Test whether echo_stack improves its assigned lane versus frozen baselines under live/public replay. Registry inclusion is not evidence of alpha.

## Claim Ladder

- `internal_live_replay`: `passed`
  Evidence: 24/24 wins vs Kalman; 2506267 estimated rows replayed
  Claim allowed: `internal source-conditioned replay winner`
- `buyer_authorized_field_replay_request`: `ready`
  Evidence: request packet built with buyer data checklist, baselines, KPIs, acceptance gates, and manual email copy
  Claim allowed: `ready to request buyer-authorized field replay`
- `field_validation`: `blocked_until_external_owner_replay`
  Evidence: missing buyer or agency controlled replay and result interpretation
  Claim allowed: `False`
- `real_dollar_claim`: `blocked_until_buyer_approved_economics`
  Evidence: missing buyer-approved cost factors and signed conversion from technical improvement to dollars
  Claim allowed: `False`
- `live_execution_or_trading`: `blocked`
  Evidence: research and buyer-pilot assets are not live autonomous execution authorization
  Claim allowed: `False`

## Next 10 Actions

1. Use the Kuramoto field replay request as the primary buyer-facing validation ask.
2. Select one energy/grid, forecasting, sensor-fusion, or industrial-stability owner with real holdout data.
3. Ask for 20 pre-registered windows and their accepted incumbent baseline before any replay.
4. Freeze the buyer baseline, metrics, pass/fail threshold, and forbidden tuning rules.
5. Run candidate and incumbent under identical constraints.
6. Hash inputs, logs, outputs, and the interpretation memo.
7. Record failures as first-class evidence rather than deleting them.
8. Only convert to dollars after the buyer supplies accepted economic conversion factors.
9. Keep brachistochrone as the second paid-pilot lane for constrained transport/routing.
10. Do not use field-validation or fixed-dollar language until the external replay passes.

## Dashboard Cards

- Strongest Current Asset: `24/24`
  Kuramoto wins vs Kalman on internal source-conditioned holdouts (`request-field-replay`)
- Claim Gate: `not field validated`
  External owner-controlled replay still required (`blocked-until-buyer-replay`)
- Rows Replayed: `2506267`
  Estimated internal replay rows across measured source systems (`internal-evidence`)
- Next Commercial Step: `paid pilot`
  Manual outreach to one qualified owner, not bulk claims (`manual-outreach-only`)

## Blocked Claims

- `field validation already proven`
- `realized dollar savings`
- `fixed dollar value per frozen delta`
- `guaranteed trading or institutional profit`
- `medical or addiction treatment claims`
- `bulk outreach`

Control room SHA-256: `3055af8b1e97545cd074aa31a42f46035dac7855bd874eefae0628cf159811d6`
