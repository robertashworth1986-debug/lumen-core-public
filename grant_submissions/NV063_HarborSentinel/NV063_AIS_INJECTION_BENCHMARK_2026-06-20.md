# HarborSentinel Public AIS Controlled-Injection Benchmark

Generated UTC: 2026-06-20T22:43:53.044246+00:00

Posture: `PUBLIC_AIS_INJECTION_BENCHMARK_READY`

## Region And Split

- Region: New Orleans / Mississippi River Delta (`new_orleans_delta`)
- Development segments: 48624
- Validation segments: 48616
- Development CSV SHA-256: `128c42e103e722f8343af85e18c7b392953d2e48f46261705cf3e6f509149a46`
- Validation CSV SHA-256: `050f062ce913bc98b63573ba649c6022061e44dd9773dce48f520dd9006849e6`

## Frozen Thresholds

- Threshold source: development split only
- Threshold quantile: p99
- Max segment interval: 120.0 minutes

## Natural Candidate Rates

- Motion-consistency validation candidate rate: 0.0358
- Speed-only validation candidate rate: 0.0109
- Boundary: natural candidate rates are unlabeled review queues, not false-positive rates.

## Controlled Injection Result

- Total injected validation segments: 20000
- Motion-consistency recall: 1.0000
- Speed-only baseline recall: 0.2584
- Recall lift versus speed-only: 0.7416

## Stronger Single-Axis Baselines

- reported_speed_sog_p99: recall 0.2584; gap vs motion 0.7416
- derived_trajectory_speed_p99: recall 0.5053; gap vs motion 0.4947
- speed_gap_consistency_p99: recall 0.5068; gap vs motion 0.4932
- heading_rate_p99: recall 0.2575; gap vs motion 0.7425
- Best single-axis baseline: speed_gap_consistency_p99 (0.5068)
- Boundary: single-axis baseline recalls are controlled-injection checks, not precision or field-performance estimates.

## Family Recall

- speed_burst: motion 1.0000; speed-only 1.0000; n=5000
- position_jump: motion 1.0000; speed-only 0.0116; n=5000
- heading_snap: motion 1.0000; speed-only 0.0090; n=5000
- consistency_gap: motion 1.0000; speed-only 0.0128; n=5000

## Claim Boundary

This is a held-out public AIS controlled-injection benchmark. It demonstrates that a frozen development-threshold motion-consistency detector catches injected kinematic perturbations on validation AIS segments better than multiple single-axis frozen p99 baselines. It does not establish HarborSentinel operational detection performance, real adversary detection, multi-source fusion, ADS-B/radar validation, Navy/SSDS integration, field performance, or operational suitability.
