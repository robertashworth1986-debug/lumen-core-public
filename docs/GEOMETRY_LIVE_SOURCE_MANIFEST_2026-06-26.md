# Geometry Live Source Manifest

Generated UTC: `2026-07-29T04:31:38.674260+00:00`

Geometry live source manifest only. It maps local/uploaded/live snapshot files to candidate benchmark lanes. A row in this manifest is not a validated result, not field validation, not a clinical claim, not a trading signal, and not a real-dollar savings claim.

## Summary

- Manifest rows: `500`
- Discovered source-lane routes: `562`
- Manifest rows truncated: `true`
- Omitted source-lane routes: `62`
- Ready-for-benchmark rows: `358`
- Unclassified rows: `19`
- Mapped lanes: `10`
- Unique source files: `204`
- Unique source estimated rows: `2837288`
- Estimated mapped rows: `7375785`
- Note: mapped rows are source-lane routes and may count the same source once per benchmark lane.
- Field validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`
- Live trading/autonomous execution allowed: `false`
- Medical/addiction-treatment claim allowed: `false`
- Manifest SHA-256: `7eb9f46cf61e454b9417cc02cb6d3e3e4afdded3eeaf44d52c8fe65bf653f234`
- Full discovered-row-set SHA-256: `f8ac16fc06cb80b1d07ae55378904aa3e09eff3b5faaf4b54e0df1eaa5fc185d`

## Lane Summary

| Lane | Candidate | Baseline | Sources | Rows | Ready Rows |
| --- | --- | --- | --- | --- | --- |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `171` | `2455556` | `171` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `167` | `2455555` | `167` |
| `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | `10` | `2795` | `10` |
| `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | `9` | `408` | `9` |
| `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | `1` | `2047` | `1` |
| `market_signal_geometry` | `fractal_brownian_surface` | `autoregressive_baseline` | `170` | `2455187` | `0` |
| `unclassified` | `` | `` | `19` | `378399` | `0` |
| `field_guided_control` | `atmospheric_jet_stream_paths` | `potential_field_baseline` | `9` | `2086` | `0` |
| `multi_agent_coordination` | `role_coherence_routing` | `centralized_dispatch_baseline` | `1` | `904` | `0` |
| `resource_aware_scheduling` | `cicada_prime_cycles` | `fifo_or_round_robin_scheduler` | `1` | `904` | `0` |
| `mission_network_routing` | `slime_mold_routing` | `dijkstra_shortest_path` | `4` | `343` | `0` |

## Top Manifest Rows

| Rank | System | Lane | Candidate | Baseline | Rows |
| --- | --- | --- | --- | --- | --- |
| `1` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `249999` |
| `2` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `249999` |
| `3` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `249999` |
| `4` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `249999` |
| `5` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `6` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `7` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `8` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `9` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `10` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `11` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `12` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `13` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `14` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `15` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `16` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `17` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `18` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `19` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `20` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `21` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `22` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |
| `23` | `macro_rates_labor` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `16044` |
| `24` | `macro_rates_labor` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `16044` |

## Boundaries

- This manifest is a benchmark routing map, not a result.
- Unclassified rows must be manually mapped or archived before use.
- Mapped rows still need frozen source manifests, identical-baseline replay, and claim-gate review.
- No field, medical, live-trading, fixed-dollar, or realized-savings claim is allowed from this manifest alone.
