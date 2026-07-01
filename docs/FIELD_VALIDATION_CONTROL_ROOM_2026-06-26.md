# Field Validation Control Room

Generated UTC: `2026-06-29T20:45:59.130802+00:00`

One reviewer/buyer control surface for the strongest geometry evidence, current claim gates, field-validation blockers, and next validation actions.

## Current Truth

- Strongest current family: `kuramoto_phase_coupling`
- Lane: `wave_resonance_timing`
- Asset score: `332.412`
- Status: `ready_to_request_field_replay_not_yet_field_validated`
- Internal wins vs Kalman: `24/24`
- Estimated rows replayed: `2506267`
- Source systems: `4`
- Best secondary buyer-pilot family: `brachistochrone_descent`

## Claim Gates

- Manual outreach ready: `true`
- Bulk email allowed: `false`
- External validation unlock packet ready: `true`
- External approval received: `false`
- Grid/RF/PLL protocols ready: `true`
- Broader measured providers: `17`
- Manifest unique sources: `183`
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

## External Validation Unlock

- Status: `go_to_request_external_replay_not_go_to_field_claim`
- External approval received: `false`
- Allowed language: We are ready to run a buyer-authorized replay against your held-out data, incumbent baseline, acceptance metric, and agreed economic conversion.
- Blocked language: We have already field validated this, realized savings, or established a fixed dollar value per frozen delta.

Required external inputs before field-validation or dollar claims:

- `held_out_operational_data` from `buyer, agency, lab, utility, or system owner`: Prevents tuning to self-selected examples. Status: `missing_external_owner_supply_or_approval`
- `incumbent_baseline` from `external system owner`: Defines what must be beaten under equal constraints. Status: `missing_external_owner_supply_or_approval`
- `acceptance_metric` from `external technical reviewer or operator`: Pre-registers what counts as a win before replay. Status: `missing_external_owner_supply_or_approval`
- `economic_conversion_factor` from `buyer finance, operations, or program office`: Converts technical delta into an allowed dollar estimate. Status: `missing_external_owner_supply_or_approval`
- `data_rights_and_publication_boundary` from `buyer legal/security/data owner`: Determines what can be stored, sold, published, or cited. Status: `missing_external_owner_supply_or_approval`
- `signed_or_logged_result_acceptance` from `external lab, buyer, agency, or system owner`: Turns internal replay into externally traceable validation evidence. Status: `missing_external_owner_supply_or_approval`

Minimum acceptance protocol:

- `holdout_windows`: 20 or more pre-registered windows unless the buyer defines a stricter domain standard
- `baseline_execution`: candidate and incumbent run on identical inputs, clocks, missingness rules, and guardrails
- `failure_handling`: failed, tied, missing, and adverse windows remain in the ledger
- `hashing`: hash raw input pointers, normalized inputs, configs, outputs, logs, and interpretation memo
- `review`: external owner confirms whether the acceptance metric was met

## Grid/RF/PLL Validation Tracks

Grid, RF, and PLL hardware validation can be designed now, but it becomes field validation only after an external lab, buyer, utility, or authorized operator runs or accepts a locked protocol on their instrumented data or test bench.

### Grid Validation

Required inputs:
- PMU or frequency/load telemetry
- ISO/RTO or utility event windows
- forecast and incumbent baseline outputs
- accepted cost factors such as imbalance, outage, congestion, or analyst review cost
- operator-approved holdout period

Acceptance metrics:
- forecast error reduction
- phase/frequency drift early-warning lead time
- false positive and false negative rate
- latency under operational cadence
- dollar conversion agreed before replay

### Rf Validation

Required inputs:
- SDR or spectrum analyzer captures
- signal generator or channel emulator settings
- noise, jammer, fading, or interference profiles
- baseline receiver or classifier outputs
- timestamped lab notebook and calibration records

Acceptance metrics:
- SNR or SINR improvement
- EVM and BER reduction
- lock or reacquisition time
- classification/detection lift
- latency and compute budget

### Pll Validation

Required inputs:
- reference oscillator and PLL configuration
- signal generator jitter/drift injection profile
- oscilloscope, phase-noise analyzer, or timestamp counter logs
- temperature/load perturbation profile
- baseline loop filter or Kalman/PLL controller result

Acceptance metrics:
- lock time
- cycle-slip count
- phase error distribution
- jitter transfer and peaking
- phase noise or Allan deviation
- recovery time after perturbation

## Top Assets

### `kuramoto_phase_coupling`

- Lane: `wave_resonance_timing`
- Asset score: `332.412`
- Evidence status: `expanded_source_conditioned_holdout_winner_not_field_validated`
- Claim stage: `buyer_authorized_field_replay_request_ready_not_field_validated`
- Benchmark hypothesis: Test phase-locking features for oscillatory datasets.

### `brachistochrone_descent`

- Lane: `optimal_curve_transport`
- Asset score: `272.058`
- Evidence status: `rolling_champion_repeat_live_context_not_field_validated`
- Claim stage: `rolling_champion_not_field_validated`
- Benchmark hypothesis: Test fastest constrained descent versus straight/spline/minimum-jerk routes.

### `thermal_plume_convection`

- Lane: `thermal_ventilation`
- Asset score: `187.193`
- Evidence status: `rolling_champion_repeat_live_context_not_field_validated`
- Claim stage: `rolling_champion_not_field_validated`
- Benchmark hypothesis: Test passive heat evacuation under hotspots.

### `leaf_veins`

- Lane: `branching_transport`
- Asset score: `147.0`
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
4. Ask the owner to approve the exact acceptance metric and economic conversion before any scoring.
5. Freeze the buyer baseline, metrics, pass/fail threshold, and forbidden tuning rules.
6. Run candidate and incumbent under identical constraints.
7. Hash inputs, logs, outputs, and the interpretation memo.
8. Record failures as first-class evidence rather than deleting them.
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

Control room SHA-256: `b5a744bb004d3763733b52fc95a1c304ae6876f1cd451165f11148120b35ef56`
