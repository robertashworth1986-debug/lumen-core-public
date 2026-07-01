# Champion Phase Proxy Diagnostics

Generated UTC: `2026-07-01T11:27:21.118005+00:00`
Phase proxy SHA-256: `40e0d8f507da064652404d3f70721b6994848ee5b3f80006a9c615b71b7d07e1`

## Truth Line

The champion now has replay-data phase proxy diagnostics across the current holdout set. These metrics support mechanism triage for the wave-resonance lane, but they do not prove hardware PLL behavior or external field validation.

## Summary

- Champion: `kuramoto_phase_coupling`
- Named baseline: `kalman_filter`
- Usable numeric holdouts: `23/24`
- Mean phase coherence proxy: `0.515292`
- Mean circular phase error proxy: `0.484708`
- Mean phase slip proxy rate: `0.007775`
- Mean spectral concentration proxy: `0.351751`
- Mean absolute residual lag-1 autocorrelation proxy: `0.242831`
- Hardware phase-lock claim allowed: `false`

## Source Summary

| Source | Holdouts | Usable | Phase Coherence | Slip Rate | Spectral Concentration | Abs Residual Lag1 |
|---|---:|---:|---:|---:|---:|---:|
| `energy_grid` | 2 | 2 | 0.996039 | 0.002335 | 0.031406 | 0.500002 |
| `macro_rates_labor` | 1 | 1 | 0.077596 | 0.000489 | 0.51083 | 0.219651 |
| `market_data` | 20 | 20 | 0.489102 | 0.008683 | 0.375831 | 0.218273 |
| `sports_market` | 1 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Boundary

Replay phase-proxy diagnostics for the current internal champion. These metrics are computed from source-conditioned holdout data and are useful for mechanism triage. They are not hardware PLL measurements, not field validation, not realized savings, and not proof of live trading edge.
