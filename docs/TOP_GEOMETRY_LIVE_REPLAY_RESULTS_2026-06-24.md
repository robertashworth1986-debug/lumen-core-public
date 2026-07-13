# Top Geometry Live Replay Results

Generated UTC: `2026-07-13T19:42:25.988474+00:00`

## Summary

- Replay cards: 5
- Adapter replays run: 5
- Source-context-only cards: 0
- Candidate beats named baseline count: 4
- Cards with paired inference: 5
- Positive after Holm correction: 0
- Registered baseline comparisons: 21
- Registered baseline mean-score wins: 19
- Registered baseline wins after global Holm: 2
- Cards beating every registered baseline by mean: 4
- Cards beating every registered baseline after global Holm: 0
- Time-series measured sources accepted: 5
- Time-series measured series accepted: 8
- Live-context rows evaluated: 4874
- Unique snapshot hashes: 16
- Snapshot chain SHA-256: `851c1c807028ed20497b08220e77648e5c7bc315a2d87558a7dc5360403bd47e`
- Strict rolling champions: `5`
- Triple-source candidate replays: `0`
- Single-run candidate replays: `0`
- Ready for live geometry claim: `false`
- Ready for real-dollar claim: `false`

## Replay Cards

| Rank | Lane | Candidate | Named Baseline | Adapter | Mean Delta | 95% Bootstrap CI | Holm p | Best Geometry | Status |
| ---: | --- | --- | --- | --- | ---: | --- | ---: | --- | --- |
| 1 | `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | `live_context_replay_ran` | 0.081332 | [0.0669164, 0.0912468] | 0.25 | `brachistochrone_descent` | `false` |
| 2 | `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | `live_context_replay_ran` | 0.154018 | [0.0994196, 0.198197] | 0.25 | `kuramoto_phase_coupling` | `false` |
| 3 | `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | `live_context_replay_ran` | 0.019447 | [-0.052843, 0.145357] | 1.0 | `crack_propagation_paths` | `false` |
| 4 | `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | `live_context_replay_ran` | 0.113841 | [0.102252, 0.12543] | 1.0 | `thermal_plume_convection` | `false` |
| 5 | `time_series_model_routing` | `fractal_brownian_surface` | `naive_last` | `live_measured_walk_forward_ran` | -0.014244 | [-0.02830713, -0.00121097] | 0.0411052495 | `fractal_brownian_surface` | `false` |

## Registered Baseline Gauntlet

These are internally registered software baselines, not externally approved standards.

| Lane | Candidate | Baseline | Mean Delta | Pairs | 95% Bootstrap CI | Global Holm p | Status |
| --- | --- | --- | ---: | ---: | --- | ---: | --- |
| `optimal_curve_transport` | `brachistochrone_descent` | `cubic_spline` | 0.070196 | 5 | [0.0555354, 0.0801108] | 1.0 | `false` |
| `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | 0.081332 | 5 | [0.0669164, 0.0912468] | 1.0 | `false` |
| `optimal_curve_transport` | `brachistochrone_descent` | `straight_line` | 0.084932 | 5 | [0.0702714, 0.0948468] | 1.0 | `false` |
| `optimal_curve_transport` | `brachistochrone_descent` | `rrt_star` | 0.134804 | 5 | [0.1201434, 0.1447188] | 1.0 | `false` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | 0.154018 | 5 | [0.0994196, 0.198197] | 1.0 | `false` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `phase_locked_loop` | 0.164483 | 5 | [0.1062464, 0.2121812] | 1.0 | `false` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `fft_filter` | 0.260076 | 5 | [0.1774232, 0.3334316] | 1.0 | `false` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `arima` | 0.264044 | 5 | [0.1990766, 0.3157832] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `steiner_approximation` | 0.016469 | 4 | [-0.0552575, 0.142844] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | 0.019447 | 4 | [-0.052843, 0.145357] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `min_cost_flow` | 0.066974 | 4 | [0.02043575, 0.150391] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `dijkstra` | 0.086843 | 4 | [0.029754, 0.192342] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `a_star` | 0.091373 | 4 | [0.0361145, 0.194593] | 1.0 | `false` |
| `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | 0.113841 | 2 | [0.102252, 0.12543] | 1.0 | `false` |
| `thermal_ventilation` | `thermal_plume_convection` | `cfd_reference` | 0.115776 | 2 | [0.112336, 0.119216] | 1.0 | `false` |
| `thermal_ventilation` | `thermal_plume_convection` | `conventional_hvac_network` | 0.136235 | 2 | [0.11762, 0.154851] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `naive_last` | -0.014244 | 786 | [-0.02830713, -0.00121097] | 0.1479788982 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `drift` | -0.011038 | 786 | [-0.02370114, 0.00170789] | 0.1137813708 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `linear_trend` | 0.004836 | 786 | [-0.00916532, 0.01797489] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `exponential_smoothing` | 0.046916 | 786 | [0.02845499, 0.06552959] | 0.004686924 | `true` |
| `time_series_model_routing` | `fractal_brownian_surface` | `moving_average` | 0.076194 | 786 | [0.05643173, 0.09584382] | 2.1e-09 | `true` |

## Claim Boundary

Live-context replay only. Frozen measured source snapshots are used to derive deterministic scenario stress parameters for existing software benchmarks. This is stronger than synthetic-only benchmarking, but it is not field validation, not realized savings, not a real-dollar claim, not grant award certainty, and not permission for live trading.

Holm correction across five preselected top replay cards only, not the full geometry registry.

Separate Holm correction across every candidate-versus-registered-baseline comparison exposed by the five executable adapters; baselines are internal registrations, not externally approved standards.

## Next Gate

Promote no card to live geometry or dollar claims until the replay is repeated on larger frozen windows, uncertainty intervals are reported, multiple-comparison control is applied across the registry, and a real operational/field validation source is attached.
