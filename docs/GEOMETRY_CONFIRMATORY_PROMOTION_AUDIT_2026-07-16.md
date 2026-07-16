# Geometry Confirmatory Promotion Audit

Generated UTC: `2026-07-16T00:35:56.881467+00:00`
Audit SHA-256: `fad00c628fb9644014588dc99fd4a80f62f2a61d3dad6a3e213bcdb17e7990f1`

## Boundary

Internal confirmatory audit of generated software benchmarks. LumenGrade is an internal evidence-maturity label, not FAA, DoD, Air Force, laboratory, investor, or third-party certification. No result establishes airworthiness, operational safety, field validation, universal superiority, realized savings, or trading alpha.

## Summary

- Executed geometry families audited: `22`.
- Development-preselected confirmatory candidates: `4`.
- Internal confirmatory passes: `2`.
- Confirmatory non-promotions: `2`.
- Descriptive-only family results: `18`.
- All source manifests valid: `true`.
- LumenGrade is an internal evidence-maturity label and never an external certification.

## Lane Decisions

| Lane | Validation Scenarios | Selected Geometry | Selected Baseline | Decision | LumenGrade |
| --- | ---: | --- | --- | --- | --- |
| `branching_transport` | 1000 | `leaf_veins` | `minimum_spanning_tree` | `NOT_PROMOTED_CONFIRMATORY_GATE_FAILED` | `LG2` |
| `optimal_curve_transport` | 1000 | `brachistochrone_descent` | `minimum_jerk_curve` | `NOT_PROMOTED_CONFIRMATORY_GATE_FAILED` | `LG2` |
| `thermal_ventilation` | 1000 | `thermal_plume_convection` | `straight_duct` | `INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED` | `LG2` |
| `wave_resonance_timing` | 1000 | `kuramoto_phase_coupling` | `kalman_filter` | `INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED` | `LG2` |

## Family Comparisons

| Lane | Family | Baseline | Score Delta | CI95 | Minimum Condition Delta | Decision |
| --- | --- | --- | ---: | --- | ---: | --- |
| `branching_transport` | `crack_propagation_paths` | `minimum_spanning_tree` | 0.005874 | `[0.001184, 0.010564]` | -0.034099 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `leaf_veins` | `minimum_spanning_tree` | 0.007201 | `[0.002, 0.012402]` | -0.044612 | `NOT_PROMOTED_CONFIRMATORY_GATE_FAILED` |
| `branching_transport` | `river_deltas` | `minimum_spanning_tree` | -0.05489 | `[-0.059094, -0.050687]` | -0.091222 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `vascular_lung_branching` | `minimum_spanning_tree` | 0.001868 | `[-0.000558, 0.004295]` | 0.000702 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `murray_law_branching` | `minimum_spanning_tree` | -0.070953 | `[-0.073904, -0.068002]` | -0.082966 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `neural_dendritic_arbors` | `minimum_spanning_tree` | 0.001661 | `[-0.000734, 0.004057]` | -0.000136 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `root_gravitropism_paths` | `minimum_spanning_tree` | -0.070951 | `[-0.073902, -0.068]` | -0.082959 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `lightning_laplacian_paths` | `minimum_spanning_tree` | -0.070968 | `[-0.07392, -0.068017]` | -0.083045 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `branching_transport` | `kidney_nephron_filtration` | `minimum_spanning_tree` | -0.002098 | `[-0.005912, 0.001715]` | -0.033418 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `optimal_curve_transport` | `brachistochrone_descent` | `minimum_jerk_curve` | 0.179587 | `[0.177893, 0.181281]` | 0.147522 | `NOT_PROMOTED_CONFIRMATORY_GATE_FAILED` |
| `optimal_curve_transport` | `catenary_minimum_energy` | `minimum_jerk_curve` | 0.036948 | `[0.036463, 0.037434]` | 0.031395 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `optimal_curve_transport` | `cycloid_rolling_paths` | `minimum_jerk_curve` | 0.075638 | `[0.073133, 0.078142]` | 0.007717 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `optimal_curve_transport` | `logarithmic_spiral_growth` | `minimum_jerk_curve` | -0.041024 | `[-0.04215, -0.039897]` | -0.048852 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `optimal_curve_transport` | `minimum_action_path` | `minimum_jerk_curve` | 0.077371 | `[0.075504, 0.079238]` | 0.028537 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `thermal_ventilation` | `rayleigh_benard_cells` | `straight_duct` | 0.046963 | `[0.046468, 0.047458]` | 0.039576 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `thermal_ventilation` | `termite_mound_ventilation` | `straight_duct` | 0.07635 | `[0.075218, 0.077481]` | 0.046273 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `thermal_ventilation` | `thermal_plume_convection` | `straight_duct` | 0.097337 | `[0.096531, 0.098143]` | 0.081614 | `INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED` |
| `wave_resonance_timing` | `firefly_synchronization` | `kalman_filter` | 0.033325 | `[0.032324, 0.034326]` | 0.009283 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `wave_resonance_timing` | `heart_rate_variability_control` | `kalman_filter` | 0.037028 | `[0.035778, 0.038278]` | 0.012721 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `wave_resonance_timing` | `kuramoto_phase_coupling` | `kalman_filter` | 0.117904 | `[0.115205, 0.120603]` | 0.050049 | `INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED` |
| `wave_resonance_timing` | `chladni_nodal_patterns` | `kalman_filter` | 0.062699 | `[0.059662, 0.065735]` | 0.005956 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
| `wave_resonance_timing` | `lissajous_phase_paths` | `kalman_filter` | 0.10763 | `[0.104367, 0.110892]` | 0.033174 | `DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED` |
