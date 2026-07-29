# EIA Grid Wave Champion Benchmark

Generated UTC: `2026-07-26T23:00:11.159720+00:00`

## Decision

Development-selected wave candidate: `lissajous_phase_paths`.
Protocol-grade internal champion: `false`.

The candidate identity was selected on development dates only. The fixed 2026 holdout was not used for selection or substitution.

## Protocol Receipt

- Protocol id: `EIA_GRID_WAVE_CHAMPION_20260713`
- Protocol SHA-256: `273eb823b0be4b2d403d0aaa591673c2e470e3d7f30abb166a43fe6e311a1c3d`
- Protocol frozen commit: `5b4ddbaef438e8f1d7c7d294a451d59280175b35`
- Panel row-chain SHA-256: `594684318e85e3440e385cff3e30c5d095930410572c6c4b39472814ae4655dd`
- Authorities: `8`
- Minimum common holdout days per authority: `184`

## Development Leaderboard

| Rank | Strategy | Kind | Mean seasonal MASE | Mean absolute error MWh |
|---:|---|---|---:|---:|
| 1 | `eia_day_ahead_forecast` | `official_baseline` | 0.384082 | 25286.302 |
| 2 | `autoregressive_ridge_p14` | `algorithmic_baseline` | 0.635361 | 47480.329 |
| 3 | `kalman_local_linear_trend` | `algorithmic_baseline` | 0.798064 | 62655.415 |
| 4 | `naive_last` | `algorithmic_baseline` | 0.919528 | 68747.060 |
| 5 | `seasonal_naive_7` | `algorithmic_baseline` | 1.077341 | 84668.201 |
| 6 | `fft_extrapolation_top5` | `algorithmic_baseline` | 1.256829 | 99893.930 |
| 7 | `lissajous_phase_paths` | `wave_candidate` | 1.299236 | 103005.141 |
| 8 | `kuramoto_phase_coupling` | `wave_candidate` | 1.299792 | 103055.263 |
| 9 | `firefly_synchronization` | `wave_candidate` | 1.300378 | 103066.629 |
| 10 | `chladni_nodal_patterns` | `wave_candidate` | 1.342432 | 106473.865 |

## Untouched Holdout Leaderboard

| Rank | Strategy | Kind | Mean seasonal MASE | Mean absolute error MWh | Direction accuracy |
|---:|---|---|---:|---:|---:|
| 1 | `autoregressive_ridge_p14` | `algorithmic_baseline` | 0.479459 | 36327.755 | 0.6695 |
| 2 | `naive_last` | `algorithmic_baseline` | 0.560535 | 43570.967 | 0.0105 |
| 3 | `eia_day_ahead_forecast` | `official_baseline` | 0.569405 | 36714.302 | 0.7849 |
| 4 | `kalman_local_linear_trend` | `algorithmic_baseline` | 0.745318 | 59524.286 | 0.5154 |
| 5 | `fft_extrapolation_top5` | `algorithmic_baseline` | 0.952753 | 77178.922 | 0.5587 |
| 6 | `seasonal_naive_7` | `algorithmic_baseline` | 1.035013 | 84798.032 | 0.5980 |
| 7 | `chladni_nodal_patterns` | `wave_candidate` | 1.247616 | 102765.924 | 0.5816 |
| 8 | `lissajous_phase_paths` | `wave_candidate` | 1.253218 | 103176.623 | 0.5784 |
| 9 | `kuramoto_phase_coupling` | `wave_candidate` | 1.253509 | 103203.940 | 0.5777 |
| 10 | `firefly_synchronization` | `wave_candidate` | 1.253944 | 103208.467 | 0.5797 |

## Baseline Gauntlet

Positive skill means the baseline seasonal-MASE minus candidate seasonal-MASE is positive.

| Baseline | Mean skill | Cluster CI95 | Holm p | Authority wins | Month win rate | Pass |
|---|---:|---|---:|---:|---:|---|
| `eia_day_ahead_forecast` | -0.741921 | [-1.188030, -0.226840] | 1.6135e-05 | 2/8 | 0.1964 | `false` |
| `seasonal_naive_7` | -0.219159 | [-0.318988, -0.113970] | 0.0440465 | 1/8 | 0.3571 | `false` |
| `naive_last` | -0.743539 | [-0.901304, -0.580698] | 7.91034e-15 | 0/8 | 0.0179 | `false` |
| `kalman_local_linear_trend` | -0.529867 | [-0.675282, -0.375676] | 4.68117e-10 | 0/8 | 0.0893 | `false` |
| `autoregressive_ridge_p14` | -0.829408 | [-0.992000, -0.674714] | 1.66533e-16 | 0/8 | 0.0000 | `false` |
| `fft_extrapolation_top5` | -0.347027 | [-0.561495, -0.132535] | 0.00912307 | 2/8 | 0.3036 | `false` |

## Gate

- Coverage pass: `true`
- Every baseline comparison pass: `false`
- External replication complete: `false`
- Realized-savings claim allowed: `false`
- Unbeatable claim allowed: `false`

## Boundary

The prior coefficient-driven wave benchmark is synthetic scenario software and is not evidence that an implemented Kuramoto model beats Kalman on measured grid demand.

> Measured public EIA-930 software forecast benchmark in native MWh only. It does not establish field control, grid reliability improvement, realized savings, procurement acceptance, safety, external validation, trading edge, or an unbeatable claim.
