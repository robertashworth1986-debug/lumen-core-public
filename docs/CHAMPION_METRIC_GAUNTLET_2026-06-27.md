# Champion Metric Gauntlet

Generated UTC: `2026-07-29T05:52:38.173184+00:00`

## What To Ask Me

Ask questions that force evidence, gates, and next actions:

1. What is proven right now, and what is only promising?
2. Which geometry family is the current champion, and what named baseline did it beat?
3. How many holdouts, rows, source systems, and hashes back the claim?
4. Which claim is safe for a grant reviewer today?
5. What exactly blocks field validation and real dollar savings?
6. What is the next test that would increase valuation the most?
7. What should be shown on the live domain before a reviewer sees it?
8. What should never be said because it overclaims the evidence?

## Current Answer

No current geometry family is an internal performance champion. Kuramoto phase coupling was audited on 1525 paired measured EIA holdout days; it won 482 pairs against kalman_local_linear_trend but had a negative mean skill delta of -0.508191 and did not clear any complete source-specific all-baseline promotion gate. The broader source inventory is research capacity only, not performance evidence. The safe commercial ask is a paid protocol or evidence review, not a performance or savings claim.

## Strongest Current Candidate

- Family: `kuramoto_phase_coupling`
- Label: `Kuramoto phase coupling`
- Lane: `wave_resonance_timing`
- Named baseline: `kalman_local_linear_trend`
- Holdout wins: `482/1525`
- Mean delta vs baseline: `-0.508191`
- Min delta vs baseline: `0.0`
- Source systems: `1`
- Broader measured providers: `25/29`
- Manifest unique sources: `204`
- Manifest ready benchmark rows: `358`
- Estimated rows replayed: `15250`
- Sign-test p-value: `1.0`
- Wilson lower 95% win-rate bound: `0.293217`
- Holdout chain SHA-256: `ffb3e4448ad393027791e3c582b2c8d0dde1e6cf0685fafd630727bb2477a9cb`

## Safe Claim State

- Reviewer-safe internal claim allowed: `false`
- Buyer-authorized field replay request ready: `false`
- Bounded estimated value claim allowed: `false`
- Paid pilot scoping allowed: `true`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`
- Live trading or autonomous execution allowed: `false`
- Safe estimated hourly value surface: `$0.00`
- Safe estimated annual value surface: `$0.00`

## Source Breadth Correction

The direct measured candidate source count and the broader live-source universe are intentionally not the same metric. The candidate count covers the frozen EIA holdout only. The broader universe counts providers, local/live files, and legacy manifest rows available for future compatibility work; those counts are not performance evidence and do not imply a champion.

- Champion replay source systems: `1`
- Champion replay source names: `EIA_GRID_VALIDATION`
- Fresh measured providers: `25` of `29`
- Fresh measured rows in latest bounded pull: `2580`
- Measured provider names: `AIRNOW, ALPACA, ALPHAVANTAGE, BEA, BLS, CENSUS, COINBASE_PUBLIC, COINGECKO_PUBLIC, EIA, FINNHUB, FRED, GRANTS_GOV, KRAKEN, KRAKEN_PUBLIC, MASSIVE, NASA, NOAA_NCEI, NWS_PUBLIC, OPEN_METEO_PUBLIC, SEC_PUBLIC, TREASURY_FISCAL_PUBLIC, TWELVE_DATA, USGS_WATER, WEBHOOK, WORLD_BANK_PUBLIC`
- Failed or thin provider names: `BINANCE_PUBLIC, EPA_AQS, NREL, THE_ODDS_API`
- Manifest unique source count: `204`
- Manifest ready-for-benchmark row count: `358`
- Manifest estimated rows mapped: `7375785`

## Grid/RF/PLL Hardware Validation Gate

Grid, RF, and PLL hardware validation can be designed now, but it becomes field validation only after an external lab, buyer, utility, or authorized operator runs or accepts a locked protocol on their instrumented data or test bench.

A fixed dollar or realized-savings claim stays blocked until a buyer, lab, utility, or authorized operator accepts the test protocol, baseline, holdout window, and dollar conversion before the replay.

### What API Keys Are For

- Pull fresh measured rows from many live systems.
- Create timestamped, hashable source snapshots.
- Populate benchmarks and dashboards with current evidence.
- Support buyer discovery by showing where a repeatable anomaly or lift exists.
- They do not by themselves create realized savings; the acceptance protocol does that.

### Fixed-Dollar Claim Blockers

- No buyer-authorized before/after deployment or accepted field replay yet.
- No pre-agreed economic conversion factor for each sector and use case.
- No signed acceptance criteria from the system owner or external lab.
- No proof that the measured lift survived external holdouts controlled by the buyer.
- No contract term that prices a frozen delta as a deliverable or paid diagnostic artifact.

## Metric Gates

- `holdout_depth`: `PASS` | actual `1525` | threshold `>= 1,000 paired measured holdout days`
- `development_selection_frozen`: `BLOCKED` | actual `False` | threshold `true`
- `baseline_win_rate`: `NEEDS_WORK` | actual `0.316066` | threshold `> 0.50 with positive mean skill`
- `mean_skill_positive`: `NEEDS_WORK` | actual `-0.508191` | threshold `> 0`
- `all_source_specific_baselines_global_holm`: `BLOCKED` | actual `False` | threshold `true`
- `authority_coverage`: `PASS` | actual `8` | threshold `>= 8 EIA balancing authorities`
- `row_replay_depth`: `PASS` | actual `15250` | threshold `>= 10,000 evaluated strategy rows`
- `hash_chain_present`: `PASS` | actual `ffb3e4448ad3...` | threshold `64 hex characters`
- `vault_hashes_verified`: `PASS` | actual `True` | threshold `true`
- `all_families_live_benchmarked`: `BLOCKED` | actual `False` | threshold `true before broad all-family claims`
- `live_domain_feed_routed`: `BLOCKED` | actual `9/14 required hosted hashes match; 5 stale/missing` | threshold `all required hosted hashes match before hosted reviewer proof claim`
- `field_validation`: `BLOCKED` | actual `False` | threshold `true before field validated language`

## Blockers

- `development_selection_frozen`: Kuramoto remains a post-selection audit, not the protocol candidate.
- `all_source_specific_baselines_global_holm`: No internal performance champion is allowed.
- `all_families_live_benchmarked`: Broad all-family language remains blocked.
- `live_domain_feed_routed`: Hosted reviewer proof language is allowed once all required feed hashes match.
- `field_validation`: Field-validation and realized-savings language remains blocked.

## Metric Expansion Suite

This is the next flex layer: every promoted champion should be pressure-tested across error, phase, robustness, source-generalization, decision quality, runtime, economics, provenance, field replay, and all-family competition. Status labels preserve the difference between proven, ready-to-run, and externally blocked.

### `forecast_error_and_residuals`

- Status: `EVIDENCED_CORE_READY_TO_EXPAND`
- Question: Does the champion reduce error against a named incumbent baseline?
- Metrics: `MAE, RMSE, MAPE_or_SMAPE, WAPE, residual_bias, residual_autocorrelation`
- Current evidence: 482/1525 holdout wins vs kalman_local_linear_trend with minimum delta 0.0 and 15,250 estimated rows replayed.
- Next action: Add per-source residual health tables before promoting more live-breadth providers into the champion replay.
- Claim gate: Internal champion claim allowed; field-performance language remains blocked.

### `phase_lock_and_timing`

- Status: `EVIDENCED_CORE_NEEDS_DIRECT_PHASE_DIAGNOSTICS`
- Question: Is the win specifically a phase/timing advantage rather than generic smoothing?
- Metrics: `circular_phase_error, phase_slip_count, lock_duration, recovery_time, coherence, spectral_concentration`
- Current evidence: Champion lane is wave_resonance_timing with sign-test p-value 1.0; direct phase diagnostics are still the next strongest proof upgrade.
- Next action: Run a dedicated phase-error distribution report for grid/EIA, market, macro, and sports-market source slices.
- Claim gate: Phase-lock language is allowed as a hypothesis-backed internal finding, not as hardware or field validation.

### `robustness_and_stress`

- Status: `READY_FOR_NEXT_RUN`
- Question: Does the champion survive missingness, spikes, drift, and delayed samples?
- Metrics: `dropout_sensitivity, outlier_sensitivity, regime_split_delta, rolling_window_stability, bootstrap_ci`
- Current evidence: Current gauntlet passes minimum-positive-delta and Wilson lower-bound gates; explicit perturbation stress is the next layer.
- Next action: Replay the champion under frozen perturbation seeds and publish pass/fail by source system.
- Claim gate: Robustness language waits for perturbation artifacts and frozen seeds.

### `source_generalization`

- Status: `READY_FOR_LIVE_BREADTH_PROMOTION`
- Question: Does the champion generalize beyond the current four promoted replay systems?
- Metrics: `leave_one_source_out, source_group_holdout, provider_promotion_rate, schema_normalization_success`
- Current evidence: Current champion replay uses 1 promoted source systems; broader live breadth has 25/29 measured providers and 358 ready-for-benchmark manifest rows.
- Next action: Promote one provider at a time only after a named baseline, schema adapter, and acceptance metric exist.
- Claim gate: Broad live-breadth claims remain blocked until promoted sources pass locked benchmarks.

### `decision_detection_quality`

- Status: `READY_FOR_DOMAIN_SPECIFIC_RUN`
- Question: Would the champion improve a buyer decision, not just a numerical score?
- Metrics: `precision, recall, F1, false_alarm_rate, miss_rate, lead_time, precision_recall_auc`
- Current evidence: Harbor/DICE/MissionWeave style artifacts provide separate decision lanes; the Kuramoto champion needs domain-specific decision mapping.
- Next action: Map one grid or maritime event dataset to a binary or ranked decision task with a locked baseline.
- Claim gate: Decision-lift language waits for task-specific labels or accepted event windows.

### `operational_runtime_budget`

- Status: `READY_FOR_NEXT_RUN`
- Question: Can the champion run fast enough for a real operator cadence?
- Metrics: `runtime_p50, runtime_p95, memory_mb, throughput_rows_per_second, update_latency, fail_closed_rate`
- Current evidence: Current proof establishes replay strength, not operational latency or deployment budget.
- Next action: Add timed benchmark wrappers around the champion replay and publish runtime budgets by source size.
- Claim gate: Operational-readiness language waits for latency and fail-closed evidence.

### `economic_conversion`

- Status: `BLOCKED_REQUIRES_EXTERNAL_OWNER`
- Question: How does a metric improvement convert into dollars for a named system?
- Metrics: `avoided_outage_minutes, energy_waste_reduction, review_burden_reduction, imbalance_or_congestion_cost, false_alarm_cost`
- Current evidence: Current system has bounded opportunity surfaces, not accepted realized savings.
- Next action: Ask OpenPOWER AI/EPRI/utility/lab owner to approve baseline, metric, and cost conversion before replay.
- Claim gate: Real-dollar savings and fixed-dollar frozen-delta claims remain blocked.

### `provenance_and_reproducibility`

- Status: `EVIDENCED_CORE_READY_TO_EXPAND`
- Question: Can a reviewer reproduce the evidence chain?
- Metrics: `input_hash, config_hash, output_hash, code_commit, manifest_sha256, domain_hash_match`
- Current evidence: Champion hash chain exists and dashboard feeds are local-ready; live-domain feed status is LOCAL_READY_DOMAIN_NOT_VERIFIED.
- Next action: Keep regenerating feed manifests after each run and verify live-domain hashes before public claims.
- Claim gate: Hash-verified proof language is allowed only for feeds whose local and hosted hashes match.

### `external_field_replay`

- Status: `BLOCKED_REQUIRES_BUYER_OR_LAB`
- Question: Will an external owner reproduce the win on their held-out data and baseline?
- Metrics: `locked_holdout_window, incumbent_baseline, acceptance_metric, forbidden_tuning_rules, signed_result`
- Current evidence: Current evidence is a direct measured nonpromotion result and is not ready for a performance replay request.
- Next action: Use the next research cycle to freeze a development-selected candidate before any external performance ask.
- Claim gate: Field-validation language remains blocked until an internally promoted candidate and an external owner accept the protocol.

### `all_family_championship`

- Status: `BLOCKED_REQUIRES_FULL_REGISTRY_RUN`
- Question: Can any development-selected wave family clear every source-specific baseline under the same metric budget?
- Metrics: `family_count_tested, baseline_count, matched_budget, winner_by_lane, negative_results_logged`
- Current evidence: No current wave family cleared the measured EIA promotion gate; all-family live championship remains explicitly blocked.
- Next action: Search families on development data, freeze one candidate per lane, then publish the untouched holdout result and losers.
- Claim gate: Universal geometry-superiority language remains blocked.


## Next 10 Tests

- `amplitude_error_check`: Phase-locking can win timing while hiding amplitude mistakes. Output: MAE/RMSE/MAPE by holdout and by source system.
- `phase_error_distribution`: The strongest claim is phase behavior; measure it directly. Output: Circular error, phase slip count, and phase-lock duration.
- `directional_accuracy`: Buyers care whether the system moves action in the right direction. Output: Up/down or risk/no-risk confusion matrix.
- `residual_autocorrelation`: A model that leaves structured residuals has not captured the system. Output: Ljung-Box style residual health by holdout.
- `ablation_against_neighbor_geometries`: Proves Kuramoto is not just inheriting a general wave-family boost. Output: Kuramoto vs PLL, Lissajous, harmonic potential, and Kalman variants.
- `drift_and_outlier_stress`: Field systems break under drift, missingness, and spikes. Output: Performance under dropouts, jumps, and delayed samples.
- `latency_and_cost_budget`: Operational buyers need to know if it runs fast enough. Output: Runtime, memory, and update cadence per source.
- `buyer_economic_conversion_dry_run`: Dollar claims need accepted conversion factors. Output: Scenario table only, with field-validation gates still closed.
- `hosted_hash_verification`: The live domain should serve the same proof hashes as the local packet. Output: VPS/domain feed manifest with matching SHA-256 values.
- `authorized_field_replay_protocol`: This is the bridge from internal proof to a field validation claim. Output: Signed or logged buyer replay packet with locked baseline and acceptance criteria.

## Boundary

Measured candidate metric gauntlet only. This artifact records the current direct measured result, the tests it passed, the tests it failed, and the safest claim language. No current family is an internal performance champion. It does not create field validation, realized savings, trading profit, medical efficacy, award certainty, or a fixed dollar price for frozen deltas.

Gauntlet SHA-256: `913e152acca0efc2bf37027113e3e10e6e77d53c8a5eb70343a5c3e403787a8d`
