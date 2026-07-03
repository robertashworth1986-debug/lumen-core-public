# Champion Source Ablation

Generated UTC: `2026-07-03T02:04:58.077252+00:00`
Source ablation SHA-256: `c2c4b855f6869e076a4936f7f7a5a39d1c97e8850121dfc92dc819ab96979753`

## Truth Line

The champion is not being carried by a single current source system: each leave-one-source-out slice remains positive against the named Kalman baseline. This strengthens internal robustness and buyer-replay readiness, while still stopping short of field validation or realized dollars.

## Summary

- Champion: `kuramoto_phase_coupling`
- Lane: `wave_resonance_timing`
- Named baseline: `kalman_filter`
- Holdout wins: `24/24`
- Source systems: `4`
- Leave-one-source-out passes: `4/4`
- All leave-one-source-out passed: `true`
- Mean delta vs named baseline: `0.140668`
- Minimum delta vs named baseline: `0.044697`
- Estimated rows replayed: `2506267`
- Numeric samples read: `66690`
- Field-validation claim allowed: `false`

## Leave-One-Source-Out Table

| Withheld Source | Kept Holdouts | Kept Wins | Min Delta | Mean Delta | Pass |
|---|---:|---:|---:|---:|---|
| `energy_grid` | 22 | 22 | 0.044697 | 0.136581 | `true` |
| `macro_rates_labor` | 23 | 23 | 0.044697 | 0.139839 | `true` |
| `market_data` | 4 | 4 | 0.068539 | 0.149882 | `true` |
| `sports_market` | 23 | 23 | 0.044697 | 0.143804 | `true` |

## Source System Cards

| Source | Holdouts | Wins | Rows | Samples | Mean Delta | Min Delta |
|---|---:|---:|---:|---:|---:|---:|
| `energy_grid` | 2 | 2 | 441505 | 3690 | 0.185622 | 0.168155 |
| `macro_rates_labor` | 1 | 1 | 16044 | 3000 | 0.159744 | 0.159744 |
| `market_data` | 20 | 20 | 2048718 | 60000 | 0.138825 | 0.044697 |
| `sports_market` | 1 | 1 | 0 | 0 | 0.068539 | 0.068539 |

## Boundary

Champion source ablation. This artifact tests whether the current internal champion remains positive when each source system is withheld from the current holdout replay. It is internal source-conditioned evidence only. It is not field validation, not realized savings, not hardware validation, not a fixed dollar claim, and not live trading evidence.
