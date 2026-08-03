# Geometry Synthetic/Live Coverage Audit

Generated UTC: `2026-07-29T10:49:30.189532+00:00`

## Policy

**Synthetic discovers. Direct measured replay tests. Field validation proves operational value.**

- Synthetic: Controlled benchmarks, failure cases, cheap ranking, and candidate discovery.
- Live: Frozen measured data replay with matched baselines, hashes, timestamps, holdouts, and uncertainty; still not field validation.
- Field validation: External partner, agency, or independent validation before real-dollar or operational-performance claims.
- Source context: Measured-source availability, direct task compatibility, source-conditioned synthetic stress, family execution, and field validation are separate gates.
- Comparison: Only lane-compatible families and named baselines may share a frozen source adapter, constraints, seeds, metrics, holdout, and multiple-comparison gate.

## Current Truth

- Registered families accounted for: `140`
- Registered lanes: `12`
- Implementations present: `35`
- Implementations still required: `105`
- Current frozen generated-benchmark executions: `30`
- Source-conditioned replay receipts: `4` families
- Qualified direct-source links: `10`
- Qualified conditioning-source links: `12`
- Context-only measured-source links: `46`
- Direct-source replay build-ready lanes: `3`
- Source-conditioned simulation build-ready lanes: `4`
- Development-preselected candidates: `4`
- Internal confirmatory passes: `2`
- Confirmatory non-promotions retained: `2`
- Proof-priority candidate families: `0`
- Test-spec-ready but no result yet: `105`
- Registered but missing a first test: `0`
- Field-validated families: `0`
- Natural-logic families registered / implemented / executed: `140` / `35` / `30`
- Family/source/baseline protocol cards: `140`

## Answer

No. 140 families are registered, 35 have implementations, 30 have current frozen generated-benchmark execution, 4 were development-preselected, 2 passed internal confirmatory gates, 2 were retained as confirmatory non-promotions, and 0 are field validated. Registry or source coverage must not be described as testing.

## Natural-Form Sentinels

- `mycelium_network` (mission_network_routing): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.
- `slime_mold_routing` (mission_network_routing): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.
- `ant_trails` (mission_network_routing): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.
- `bee_foraging_paths` (mission_network_routing): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.
- `bird_v_formation_flocking` (multi_agent_coordination): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.
- `boids_swarm_flocking` (multi_agent_coordination): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.
- `wolf_pack_pursuit_paths` (multi_agent_coordination): implementation `true`, frozen execution `true`, stage `synthetic_benchmark_result_present`.

## Requested Universe Coverage

- Requested candidates tracked in this audit: `129`
- Covered by registry family: `54`
- Covered as baseline: `7`
- Not yet in registry: `68`

## Top Next Live Replay Queue

- `mycelium_network` (mission_network_routing): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `delivery_rate_minus_cost_and_recovery_penalty`
- `slime_mold_routing` (mission_network_routing): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `delivery_rate_after_edge_dropout`
- `bee_foraging_paths` (mission_network_routing): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `time_to_profitable_target`
- `bird_v_formation_flocking` (multi_agent_coordination): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `energy_proxy_at_completion`
- `wolf_pack_pursuit_paths` (multi_agent_coordination): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `capture_time_with_collision_penalty`
- `ant_trails` (mission_network_routing): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `cost_per_delivery_with_recovery`
- `river_deltas` (branching_transport): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `delivered_flow_per_material`
- `leaf_veins` (branching_transport): synthetic_benchmark_result_present -> source_conditioned_replay_present; metric `delivered_flow_after_random_cut`
- `vascular_lung_branching` (branching_transport): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `flow_uniformity_per_material`
- `termite_mound_ventilation` (thermal_ventilation): synthetic_benchmark_result_present -> measured_source_available_not_replayed; metric `temperature_uniformity_per_energy`

## Top Next Synthetic Benchmark Queue

- `beast_algo_echo_stack` (time_series_model_routing): test_spec_ready_no_result; first test `full_beast_algorithm_lane_replay_v1`
- `markov_blanket_boundaries` (stability_diagnostic): test_spec_ready_no_result; first test `markov_blanket_diagnostic_v1`
- `beast_algo_cross_asset_resonance` (wave_resonance_timing): test_spec_ready_no_result; first test `full_beast_algorithm_lane_replay_v1`
- `beast_algo_curvature_pressure` (optimal_curve_transport): test_spec_ready_no_result; first test `full_beast_algorithm_lane_replay_v1`
- `cicada_prime_cycles` (resource_aware_scheduling): test_spec_ready_no_result; first test `prime_cycle_wake_v1`
- `atmospheric_jet_stream_paths` (field_guided_control): test_spec_ready_no_result; first test `jetstream_corridor_v1`
- `fractal_brownian_surface` (time_series_model_routing): implementation_present_no_frozen_result; first test `fbm_signal_features_v1`
- `beast_algo_multi_timeframe_stack` (time_series_model_routing): test_spec_ready_no_result; first test `full_beast_algorithm_lane_replay_v1`
- `beast_algo_multi_timescale_interference` (time_series_model_routing): test_spec_ready_no_result; first test `full_beast_algorithm_lane_replay_v1`
- `beast_algo_resonant_pressure` (time_series_model_routing): test_spec_ready_no_result; first test `full_beast_algorithm_lane_replay_v1`

## Missing From Registry

- bidirectional A*
- traveling-salesman heuristics
- vehicle-routing heuristics
- RRT/RRT*
- probabilistic roadmaps
- contraction hierarchies
- landmark routing
- hierarchical pathfinding
- dynamic replanning / D* Lite
- predator-prey pursuit/evasion
- electric field lines
- harmonic potential fields
- vortex fields
- gradient-flow paths
- Laplacian smoothing paths

## Do Not Overclaim

This audit does not create field validation, realized savings, trading profit, award certainty, or universal superiority claims.
