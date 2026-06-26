# Geometry Live Source Manifest

Generated UTC: `2026-06-26T01:14:43.851157+00:00`

Geometry live source manifest only. It maps local/uploaded/live snapshot files to candidate benchmark lanes. A row in this manifest is not a validated result, not field validation, not a clinical claim, not a trading signal, and not a real-dollar savings claim.

## Summary

- Manifest rows: `490`
- Ready-for-benchmark rows: `309`
- Unclassified rows: `26`
- Mapped lanes: `8`
- Unique source files: `183`
- Unique source estimated rows: `3751192`
- Estimated mapped rows: `9850384`
- Note: mapped rows are source-lane routes and may count the same source once per benchmark lane.
- Field validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`
- Live trading/autonomous execution allowed: `false`
- Medical/addiction-treatment claim allowed: `false`
- Manifest SHA-256: `1569670ff4da808ba77594e82ff1ef3c55e5f18e38036883420533414e89c5b3`

## Lane Summary

| Lane | Candidate | Baseline | Sources | Rows | Ready Rows |
| --- | --- | --- | --- | --- | --- |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `145` | `2882071` | `145` |
| `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `142` | `2882071` | `142` |
| `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | `11` | `695728` | `11` |
| `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | `8` | `441538` | `8` |
| `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | `3` | `254187` | `3` |
| `market_signal_geometry` | `fractal_brownian_surface` | `autoregressive_baseline` | `143` | `2440566` | `0` |
| `unclassified` | `` | `` | `26` | `614898` | `0` |
| `field_guided_control` | `atmospheric_jet_stream_paths` | `potential_field_baseline` | `9` | `254220` | `0` |
| `mission_network_routing` | `slime_mold_routing` | `dijkstra_shortest_path` | `3` | `3` | `0` |

## Top Manifest Rows

| Rank | System | Lane | Candidate | Baseline | Rows |
| --- | --- | --- | --- | --- | --- |
| `1` | `maritime_ais` | `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | `249999` |
| `2` | `energy_grid` | `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | `249999` |
| `3` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `249999` |
| `4` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `249999` |
| `5` | `energy_grid` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `249999` |
| `6` | `maritime_ais` | `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | `249999` |
| `7` | `energy_grid` | `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | `249999` |
| `8` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `249999` |
| `9` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `249999` |
| `10` | `energy_grid` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `249999` |
| `11` | `energy_grid` | `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | `191506` |
| `12` | `energy_grid` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `191506` |
| `13` | `energy_grid` | `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | `191506` |
| `14` | `energy_grid` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `191506` |
| `15` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `16` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `17` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `18` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `19` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `20` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `21` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `22` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `23` | `market_data` | `energy_price_pressure_proxy` | `phase_locked_residual_corrector` | `best_named_forecast_baseline` | `160080` |
| `24` | `market_data` | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `160080` |

## Boundaries

- This manifest is a benchmark routing map, not a result.
- Unclassified rows must be manually mapped or archived before use.
- Mapped rows still need frozen source manifests, identical-baseline replay, and claim-gate review.
- No field, medical, live-trading, fixed-dollar, or realized-savings claim is allowed from this manifest alone.
