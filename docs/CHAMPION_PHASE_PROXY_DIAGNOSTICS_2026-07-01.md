# Champion Phase Proxy Diagnostics

Generated UTC: `2026-07-01T10:59:26.177513+00:00`
Phase proxy SHA-256: `cf2bd7e07665801b26ab7521fd6c41e55965bc10c08b140f2dc92ee61d861f63`

## Truth Line

The champion now has replay-data phase proxy diagnostics across the current holdout set. These metrics support mechanism triage for the wave-resonance lane, but they do not prove hardware PLL behavior or external field validation.

## Summary

- Champion: `kuramoto_phase_coupling`
- Named baseline: `kalman_filter`
- Usable numeric holdouts: `22/24`
- Mean phase coherence proxy: `0.535187`
- Mean circular phase error proxy: `0.464813`
- Mean phase slip proxy rate: `0.008106`
- Mean spectral concentration proxy: `0.34452`
- Mean absolute residual lag-1 autocorrelation proxy: `0.243884`
- Hardware phase-lock claim allowed: `false`

## Source Summary

| Source | Holdouts | Usable | Phase Coherence | Slip Rate | Spectral Concentration | Abs Residual Lag1 |
|---|---:|---:|---:|---:|---:|---:|
| `energy_grid` | 2 | 2 | 0.996039 | 0.002335 | 0.031406 | 0.500002 |
| `macro_rates_labor` | 1 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |
| `market_data` | 20 | 20 | 0.489102 | 0.008683 | 0.375831 | 0.218273 |
| `sports_market` | 1 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Boundary

Replay phase-proxy diagnostics for the current internal champion. These metrics are computed from source-conditioned holdout data and are useful for mechanism triage. They are not hardware PLL measurements, not field validation, not realized savings, and not proof of live trading edge.
