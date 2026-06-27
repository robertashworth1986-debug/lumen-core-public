# Champion Metric Gauntlet

Generated UTC: `2026-06-27T21:08:03.287584+00:00`

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

Kuramoto phase coupling is the current internal champion because it beat kalman_filter on 24/24 source-conditioned holdouts across 4 source systems. That is strong enough to request a buyer-authorized field replay, but it is not field validation or realized dollar savings yet.

## Strongest Current Candidate

- Family: `kuramoto_phase_coupling`
- Label: `Kuramoto phase coupling`
- Lane: `wave_resonance_timing`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Mean delta vs baseline: `0.139875`
- Min delta vs baseline: `0.044697`
- Source systems: `4`
- Estimated rows replayed: `2506267`
- Sign-test p-value: `6e-08`
- Wilson lower 95% win-rate bound: `0.862024`
- Holdout chain SHA-256: `b723b3cf65d3971b0492e41cc27fc82e1fba57a5e0d672a67e9818348313f2e6`

## Safe Claim State

- Reviewer-safe internal claim allowed: `true`
- Buyer-authorized field replay request ready: `true`
- Bounded estimated value claim allowed: `true`
- Paid pilot scoping allowed: `true`
- Field-validation claim allowed: `false`
- Real-dollar savings claim allowed: `false`
- Live trading or autonomous execution allowed: `false`
- Safe estimated hourly value surface: `$4,520.00`
- Safe estimated annual value surface: `$39,595,200.00`

## Metric Gates

- `holdout_depth`: `PASS` | actual `24` | threshold `>= 20 source-conditioned holdouts`
- `baseline_win_count`: `PASS` | actual `24/24` | threshold `>= 16/20 and preferably all positive`
- `baseline_win_rate`: `PASS` | actual `1.0` | threshold `>= 0.80`
- `minimum_delta_positive`: `PASS` | actual `0.044697` | threshold `> 0`
- `sign_test_strength`: `PASS` | actual `6e-08` | threshold `<= 0.001`
- `wilson_lower_bound`: `PASS` | actual `0.862024` | threshold `>= 0.75`
- `source_system_diversity`: `PASS` | actual `4` | threshold `>= 3 source systems`
- `row_replay_depth`: `PASS` | actual `2506267` | threshold `>= 1,000,000 estimated rows replayed`
- `hash_chain_present`: `PASS` | actual `b723b3cf65d3...` | threshold `64 hex characters`
- `vault_hashes_verified`: `PASS` | actual `True` | threshold `true`
- `all_families_live_benchmarked`: `BLOCKED` | actual `False` | threshold `true before broad all-family claims`
- `live_domain_feed_routed`: `PASS` | actual `True` | threshold `true before hosted reviewer proof claim`
- `field_validation`: `BLOCKED` | actual `False` | threshold `true before field validated language`

## Blockers

- `all_families_live_benchmarked`: Broad all-family language remains blocked.
- `field_validation`: Field-validation and realized-savings language remains blocked.

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

Champion metric gauntlet only. This artifact explains the current internal winner, the tests it has passed, the tests it has not passed, and the safest claim language. It does not create field validation, realized savings, trading profit, medical efficacy, award certainty, or a fixed dollar price for frozen deltas.

Gauntlet SHA-256: `3908fad094c311285c22ce981c411657e23e411045bc059acece27f851926415`
