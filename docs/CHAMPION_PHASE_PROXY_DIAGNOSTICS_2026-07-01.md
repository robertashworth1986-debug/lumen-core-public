# Champion Phase Proxy Diagnostics

Generated UTC: `2026-07-01T16:28:22.438111+00:00`
Phase proxy SHA-256: `8e077551c6309e2106611dfffa858066f7f2c0ddb272260c5dcedabcd666c357`

## Truth Line

The champion now has replay-data phase proxy diagnostics across the current holdout set. Flat or low-variance numeric files are explicitly marked as degenerate so they cannot inflate the source-level phase means. These metrics support mechanism triage for the wave-resonance lane, but they do not prove hardware PLL behavior or external field validation.

## Summary

- Champion: `kuramoto_phase_coupling`
- Named baseline: `kalman_filter`
- Usable numeric holdouts: `23/24`
- Non-degenerate numeric holdouts: `15`
- Degenerate numeric holdouts excluded from source means: `8`
- Mean phase coherence proxy: `0.515292`
- Mean circular phase error proxy: `0.484708`
- Mean phase slip proxy rate: `0.007775`
- Mean spectral concentration proxy: `0.351751`
- Mean absolute residual lag-1 autocorrelation proxy: `0.242831`
- Hardware phase-lock claim allowed: `false`

## Source Summary

| Source | Holdouts | Usable | Non-Degenerate | Degenerate | Phase Coherence | Slip Rate | Spectral Concentration | Abs Residual Lag1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `energy_grid` | 2 | 2 | 2 | 0 | 0.996039 | 0.002335 | 0.031406 | 0.500002 |
| `macro_rates_labor` | 1 | 1 | 1 | 0 | 0.077596 | 0.000489 | 0.51083 | 0.219651 |
| `market_data` | 20 | 20 | 12 | 8 | 0.216035 | 0.014472 | 0.57398 | 0.354651 |
| `sports_market` | 1 | 0 | 0 | 0 | 0.0 | 0.0 | 0.0 | 0.0 |

## Boundary

Replay phase-proxy diagnostics for the current internal champion. These metrics are computed from source-conditioned holdout data and are useful for mechanism triage. They are not hardware PLL measurements, not field validation, not realized savings, and not proof of live trading edge.
