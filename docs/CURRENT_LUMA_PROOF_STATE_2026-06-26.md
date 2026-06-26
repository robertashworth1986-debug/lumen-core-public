# Current Luma Proof State

Generated UTC: `2026-06-26T04:24:27.282473+00:00`

Current proof-state checkpoint generated from authoritative local artifacts. It ranks the strongest geometry candidates and proposal targets, but it does not grant field-validation, realized-savings, fixed-dollar frozen-delta, clinical, live-trading, or award-certainty claims.

## Hard Numbers

- Registered geometry families: `140`
- Natural-path families: `137`
- Benchmark-specified families: `137`
- Ready-for-benchmark manifest routes: `309`
- Unique source files in manifest: `183`
- Manifest estimated rows: `3751192`
- Current source-conditioned replay routes: `10`
- Current source-conditioned wins/losses: `7` / `3`
- Current replay estimated rows: `2324511`
- Numeric samples read: `37070`
- Mean replay delta vs named baselines: `0.094602`
- Strongest current delta: `0.198179` from `kuramoto_phase_coupling`

## Champion Ranking

| Rank | Family | Lane | Stage | Score | Main Claim |
| --- | --- | --- | --- | ---: | --- |
| 1 | `brachistochrone_descent` | `optimal_curve_transport` | `robust_repeat_plus_current_replay` | 140.41 | brachistochrone_descent is a robust repeat-window benchmark candidate on optimal_curve_transport; this supports paid technical evaluation scoping, not field validation or realized savings. |
| 2 | `kuramoto_phase_coupling` | `wave_resonance_timing` | `source_conditioned_multi_replay_winner_not_field_validated` | 129.497 | kuramoto_phase_coupling is the strongest current source-conditioned replay candidate on wave_resonance_timing; it needs more holdout windows, buyer-authorized baselines, and field validation before dollar claims. |
| 3 | `thermal_plume_convection` | `thermal_ventilation` | `source_conditioned_candidate_needs_repeat` | 113.239 | thermal_plume_convection remains a research candidate until it wins frozen replays against named baselines. |
| 4 | `leaf_veins` | `branching_transport` | `negative_current_replay_demote` | 93.147 | leaf_veins lost or tied in the current source-conditioned replay and should be rerouted or demoted. |

## Money State

- Strongest current commercial claim: `bounded_estimated_value_signal_and_paid_pilot_scoping`
- Safe estimated hourly value signal: `$4,520`
- Safe estimated annual value signal: `$39,595,200`
- Blocked context annual surface: `$52,288,496,940`
- The blocked context surface is not a realized savings claim.

## First Proposal Target

- Target: Energy Forecasting / Grid Reliability Paid Technical Evaluation
- Buyer role: Energy Forecasting Lead, Grid Reliability Analytics Lead, or National Lab validation lead
- Ask: 20-minute technical fit call, then a paid evidence review or buyer-authorized field replay.
- Acceptance metric: forecast residual, phase/timing error, drift-detection lead time, false positives, and missed-event rate versus incumbent baseline.

## Claim Gates

- field_validation_claim_allowed: `false`
- real_dollar_savings_claim_allowed: `false`
- fixed_dollar_delta_sale_claim_allowed: `false`
- live_trading_or_autonomous_execution_allowed: `false`
- paid_technical_evaluation_scoping_allowed: `true`
- all_registered_families_live_benchmarked: `false`
- natural_path_registry_target_met: `true`

## Next Actions

- Lead with brachistochrone_descent only in bounded benchmark language.
- Run Kuramoto phase-coupling on at least 20 more EIA/FRED/NOAA/NASA holdout windows.
- Pull ISO/RTO LMP or accepted electricity-price settlement data before any real-dollar energy claim.
- Move leaf-vein branching out of winner language until it beats minimum-spanning-tree on fresh source-conditioned routes.
- Attach the current proof-state JSON hash to grant and buyer packets so reviewers can reproduce the evidence boundary.

## Inputs

- registry: `config\geometry_championship_v1_registry.json`
- ready_source_replay: `out\ops\geometry_ready_source_replay_latest.json`
- source_manifest: `out\ops\geometry_live_source_manifest_latest.json`
- repeat_validation: `out\ops\geometry_repeat_proof_validation_latest.json`
- uncertainty: `out\ops\geometry_repeat_uncertainty_report_latest.json`
- valuation: `out\ops\valuation_proposal_target_packet_latest.json`
- Proof-state SHA-256: `324a092c456e0c6e6a5ec93aa2c654594c27a8b0afcb6a6165d37c9a05e107cb`
