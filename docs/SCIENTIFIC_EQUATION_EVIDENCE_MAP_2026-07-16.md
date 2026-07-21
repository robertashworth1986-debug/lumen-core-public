# Scientific Equation Evidence Map

Generated UTC: `2026-07-21T13:52:27.019439+00:00`
Registry SHA-256: `2c8efd1535cef14ede2c11782db0ff43332b269797243c8ea1a4e712be2cea75`
Builder SHA-256: `1077dd04512caeda698a661df3c822322972e8953e11ee71b16d2e83c6baf736`
Terminal chain SHA-256: `c0b8783ac029d673008e0926ac1e6900d9abacdc420f64bed2a56e5500c8db4c`

## Truth Line

This map distinguishes exact standard methods, operational definitions, heuristic analogues, and exploratory heuristics. It is an internal traceability artifact, not patentability, agency acceptance, independent validation, field validation, or performance certification.

## Maturity Wall

- Registered entries: `25`
- Registered files: `26`
- Registry files current: `true`
- Registry hash drift count: `0`
- Independently reproduced entries: `0`
- Field or acceptance validated entries: `0`
- Patentability determined: `false`
- External validation claim allowed: `false`
- Field validation claim allowed: `false`

## Equation And Algorithm Ledger

| ID | Name | Class | Evidence | Claim ceiling | Source | Allowed now |
| --- | --- | --- | --- | --- | --- | --- |
| `FREQ-001` | Harmonic design matrix | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/frequency_cluster_truth_gauntlet.py:552::harmonic_design` | The frozen gauntlet implements a standard sine/cosine harmonic basis. |
| `FREQ-002` | Least-squares harmonic prediction with nonnegative clip | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/frequency_cluster_truth_gauntlet.py:562::fit_harmonic_predict` | The frozen candidate uses ordinary least squares over registered harmonic features and clips negative outputs. |
| `FREQ-003` | Discovery partial R-squared | `OPERATIONAL_DEFINITION` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/frequency_cluster_truth_gauntlet.py:574::partial_r2` | Frequency discovery ranks registered periods using a transparent nonnegative R-squared diagnostic on the discovery split only. |
| `FREQ-004` | EWMA half-life recursion | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/frequency_cluster_truth_gauntlet.py:644::ewma_predictions` | The benchmark includes a standard half-life-parameterized EWMA baseline component. |
| `FREQ-005` | Moving-block bootstrap sampler | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/frequency_cluster_truth_gauntlet.py:670::moving_block_indices` | The frozen inference layer preserves local dependence with a moving-block bootstrap. |
| `FREQ-006` | Holm familywise p-value adjustment | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/frequency_cluster_truth_gauntlet.py:694::holm_adjust` | The gauntlet applies the standard monotone Holm adjustment across the registered test family. |
| `EIA-D-001` | Robust center and scale contract | `OPERATIONAL_DEFINITION` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_residual_moe_benchmark.py:121::stable_scale` | The EIA benchmark uses a declared robust normalization contract. |
| `EIA-D-002` | Seven-day seasonal MASE scale | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_residual_moe_benchmark.py:128::seasonal_mase_scale` | The daily EIA lane reports error relative to a seven-day seasonal-naive scale. |
| `EIA-D-003` | Autoregressive ridge baseline | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_residual_moe_benchmark.py:138::forecast_autoregressive_ridge` | The frozen EIA lane includes a transparent autoregressive ridge baseline. |
| `EIA-D-004` | Daily forecast metric row | `OPERATIONAL_DEFINITION` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_residual_moe_benchmark.py:463::metric_row` | Daily holdout rows expose declared error and direction metrics with units. |
| `EIA-D-005` | Exact two-sided sign test | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_residual_moe_benchmark.py:591::exact_two_sided_sign_test` | The paired comparison layer includes an exact two-sided sign test. |
| `EIA-H-001` | Hourly weekly-difference target scale | `OPERATIONAL_DEFINITION` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_prospective_hourly_router.py:340::target_scale` | The prospective hourly protocol uses a declared median weekly-difference normalization scale. |
| `EIA-H-002` | Leakage-controlled hourly feature vector | `OPERATIONAL_DEFINITION` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_prospective_hourly_router.py:351::build_feature_row` | The sealed-forecast feature contract excludes the target actual and uses declared lags and cyclic bases. |
| `EIA-H-003` | Append-only canonical SHA-256 chain | `EXACT_STANDARD_METHOD` | `E2_FROZEN_INTERNAL_OR_SOURCE_AUTHENTIC` | `C2_FROZEN_INTERNAL_EVIDENCE` | `code/eia_grid_prospective_hourly_router.py:646::append_chain_record` | Prospective records are appended to a tamper-evident canonical SHA-256 chain. |
| `DICE-001` | Normalized strategy entropy | `EXACT_STANDARD_METHOD` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/dice_constraint_contract_benchmark.py:260::_strategy_entropy` | The generated benchmark reports normalized Shannon entropy across eight modeled strategies. |
| `DICE-002` | Constraint-contract development objective | `OPERATIONAL_DEFINITION` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/dice_constraint_contract_benchmark.py:399::_objective` | A declared weighted objective selects contract margins on generated development conditions. |
| `NV065-001` | Expected sensor contribution heuristic | `EXPLORATORY_HEURISTIC` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/nv065_sensor_tasking_benchmark.py:281::expected_contribution` | A deterministic nonnegative heuristic ranks generated sensor-track assignments in the NV065 software benchmark. |
| `MW-001` | MissionWeave priority score | `EXPLORATORY_HEURISTIC` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/missionweave_benchmark.py:228::_priority` | A declared weighted heuristic ranks eligible generated workflow cases. |
| `MW-002` | Gini dispersion metric | `EXACT_STANDARD_METHOD` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/missionweave_benchmark.py:279::_gini` | The generated workflow benchmark reports a standard Gini dispersion statistic. |
| `GEO-WAVE-001` | Kuramoto-labeled phase-coupling analogue | `HEURISTIC_ANALOGUE` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/geometry_wave_resonance_timing_benchmark.py:285::strategy_kuramoto_phase_coupling` | A bounded Kuramoto-inspired analogue was evaluated in a generated wave-timing benchmark. |
| `GEO-CURVE-001` | Brachistochrone-labeled descent analogue | `HEURISTIC_ANALOGUE` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/geometry_optimal_curve_transport_benchmark.py:217::strategy_brachistochrone_descent` | A bounded brachistochrone-inspired analogue was evaluated and failed its internal confirmatory promotion gate. |
| `GEO-THERMAL-001` | Thermal-plume ventilation analogue | `HEURISTIC_ANALOGUE` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/geometry_thermal_ventilation_benchmark.py:279::strategy_thermal_plume_convection` | A bounded thermal-plume-inspired cooling proxy passed an internal generated confirmatory benchmark. |
| `GEO-GRAPH-001` | Dijkstra shortest-path search | `EXACT_STANDARD_METHOD` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/geometry_branching_transport_benchmark.py:199::dijkstra_path` | The generated branching benchmark includes a standard Dijkstra path baseline over its registered graph costs. |
| `UH-001` | Phi-resonance additive bonus | `EXPLORATORY_HEURISTIC` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/universal_harmonic_edge_core.py:157::phi_resonance_bonus` | An implemented bounded phi-proximity bonus exists as exploratory scoring code. |
| `UH-002` | Universal harmonic composite score | `EXPLORATORY_HEURISTIC` | `E1_INTERNAL_IMPLEMENTATION` | `C1_INTERNAL_IMPLEMENTATION` | `code/universal_harmonic_edge_core.py:204::score_signal` | A deterministic bounded cross-domain composite score is implemented for exploratory ranking. |

## Interpretation Rules

- `EXACT_STANDARD_METHOD` means the implementation follows a named standard method; it is not claimed as novel by itself.
- `OPERATIONAL_DEFINITION` means the formula is a transparent project-specific metric, scale, feature, or gate.
- `HEURISTIC_ANALOGUE` means the name is inspiration only; it is not a numerical solution of the governing equation.
- `EXPLORATORY_HEURISTIC` means implemented code exists, but empirical promotion and external validation remain blocked.
- E2 may support a frozen internal or source-authentic implementation claim. It does not imply independent endorsement.
- No entry in this release reaches E3 independent reproduction or E4 field/acceptance validation.

## Patent Boundary

Standard equations and algorithms are prior art and are not asserted as novel alone. Any protectable position would require counsel to assess the specific system combination, routing, controls, data contracts, and claimed implementation details against prior art. This map is technical provenance, not a patentability opinion.
