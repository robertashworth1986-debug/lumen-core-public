# Top Geometry Live Replay Results

Generated UTC: `2026-07-29T13:49:18.738458+00:00`

## Summary

- Replay cards: 5
- Adapter replays run: 4
- Direct measured replays run: 2
- Source-conditioned synthetic stress runs: 2
- Cards with no compatible replay input: 1
- Context-only source rows excluded: 20
- Candidate beats named baseline count: 1
- Cards with paired inference: 4
- Positive after Holm correction: 0
- Registered baseline comparisons: 22
- Registered baseline mean-score wins: 10
- Registered baseline wins after global Holm: 0
- Cards beating every registered baseline by mean: 1
- Cards beating every registered baseline after global Holm: 0
- Time-series measured sources accepted: 6
- Time-series measured series accepted: 16
- Compatibility-gated performance rows evaluated: 34133
- Unique snapshot hashes: 9
- Snapshot chain SHA-256: `f51dcd96203fda99b0ad55b1d052fefaf7e4157d7cb3ea9686bd62dccc665b80`
- Strict rolling champions: `0`
- Triple-source candidate replays: `0`
- Single-run candidate replays: `0`
- Ready for live geometry claim: `false`
- Ready for real-dollar claim: `false`

## Replay Cards

| Rank | Lane | Registered Candidate | Evaluated Candidate | Named Baseline | Adapter | Mean Delta | 95% Bootstrap CI | Holm p | Status |
| ---: | --- | --- | --- | --- | ---: | --- | ---: | --- | --- |
| 1 | `optimal_curve_transport` | `brachistochrone_descent` | `brachistochrone_descent` | `` | `no_compatible_replay_input` | n/a | n/a | n/a | `false` |
| 2 | `wave_resonance_timing` | `kuramoto_phase_coupling` | `lissajous_phase_paths` | `autoregressive_ridge_p14` | `direct_measured_eia_grid_wave_replay_ran` | -0.773758 | [-0.82047036, -0.72619308] | 3.7888659488e-127 | `false` |
| 3 | `branching_transport` | `leaf_veins` | `leaf_veins` | `minimum_spanning_tree` | `source_conditioned_synthetic_stress_ran` | -0.053173 | [-0.06915, -0.038573] | 0.75 | `false` |
| 4 | `thermal_ventilation` | `thermal_plume_convection` | `thermal_plume_convection` | `straight_duct` | `source_conditioned_synthetic_stress_ran` | 0.122835 | [0.114333, 0.128742] | 0.75 | `false` |
| 5 | `time_series_model_routing` | `fractal_brownian_surface` | `fractal_brownian_surface` | `autoregressive_ridge_source_lag` | `live_measured_walk_forward_ran` | -0.01962 | [-0.03910863, 0.05026084] | 0.803619384766 | `false` |

## Registered Baseline Gauntlet

These are internally registered software baselines, not externally approved standards.

| Lane | Candidate | Baseline | Mean Delta | Pairs | 95% Bootstrap CI | Global Holm p | Status |
| --- | --- | --- | ---: | ---: | --- | ---: | --- |
| `wave_resonance_timing` | `lissajous_phase_paths` | `autoregressive_ridge_p14` | -0.773758 | 1525 | [-0.82047036, -0.72619308] | 2.08387627184e-126 | `false` |
| `wave_resonance_timing` | `lissajous_phase_paths` | `naive_last` | -0.692683 | 1525 | [-0.74313761, -0.64230227] | 2.95317797639e-100 | `false` |
| `wave_resonance_timing` | `lissajous_phase_paths` | `eia_day_ahead_forecast` | -0.683812 | 1525 | [-0.74362547, -0.62333777] | 2.47331578522e-80 | `false` |
| `wave_resonance_timing` | `lissajous_phase_paths` | `kalman_local_linear_trend` | -0.5079 | 1525 | [-0.56091588, -0.45591429] | 2.02370435002e-46 | `false` |
| `wave_resonance_timing` | `lissajous_phase_paths` | `fft_extrapolation_top5` | -0.300465 | 1525 | [-0.35082514, -0.24850973] | 3.61706453807e-19 | `false` |
| `wave_resonance_timing` | `lissajous_phase_paths` | `seasonal_naive_7` | -0.218205 | 1525 | [-0.27424074, -0.16351208] | 1.10096599574e-11 | `false` |
| `branching_transport` | `leaf_veins` | `steiner_approximation` | -0.057502 | 3 | [-0.071872, -0.047251] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | -0.053173 | 3 | [-0.06915, -0.038573] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `min_cost_flow` | 0.005933 | 3 | [-0.026961, 0.026599] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `dijkstra` | 0.029996 | 3 | [0.010611, 0.042514] | 1.0 | `false` |
| `branching_transport` | `leaf_veins` | `a_star` | 0.03391 | 3 | [0.020335, 0.044495] | 1.0 | `false` |
| `thermal_ventilation` | `thermal_plume_convection` | `cfd_reference` | 0.121347 | 3 | [0.119216, 0.124624] | 1.0 | `false` |
| `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | 0.122835 | 3 | [0.114333, 0.128742] | 1.0 | `false` |
| `thermal_ventilation` | `thermal_plume_convection` | `conventional_hvac_network` | 0.14887 | 3 | [0.138134, 0.154851] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `autoregressive_ridge_source_lag` | -0.01962 | 16 | [-0.03910863, 0.05026084] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `naive_last` | -0.017397 | 16 | [-0.02676554, -0.00745818] | 0.319061279296 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `drift` | -0.01573 | 16 | [-0.02259226, 0.00675582] | 0.0668945312499 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `damped_holt_ets` | -0.00564 | 16 | [-0.01165858, 0.01276537] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `linear_trend` | 0.002219 | 16 | [-0.00450353, 0.01643337] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `exponential_smoothing` | 0.005914 | 16 | [-0.01002399, 0.03678739] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `moving_average` | 0.023367 | 16 | [0.00197032, 0.05887596] | 1.0 | `false` |
| `time_series_model_routing` | `fractal_brownian_surface` | `seasonal_naive_source_period` | 0.063171 | 16 | [0.0284779, 0.12516925] | 1.0 | `false` |

## Claim Boundary

Compatibility-gated evidence only. Direct measured replay uses task-compatible chronological observations and source-specific accepted baselines. Source-conditioned synthetic stress uses measured inputs only to set synthetic conditions. Context-only sources are excluded from performance calculations. Neither mode is field validation, realized savings, a real-dollar claim, award certainty, or permission for live trading.

Holm correction across five preselected top replay cards only, not the full geometry registry.

Separate Holm correction across every candidate-versus-registered-baseline comparison exposed by the five executable adapters; baselines are internal registrations, not externally approved standards.

## Next Gate

Promote no card to live geometry or dollar claims until the replay is repeated on larger frozen windows, uncertainty intervals are reported, multiple-comparison control is applied across the registry, and a real operational/field validation source is attached.
