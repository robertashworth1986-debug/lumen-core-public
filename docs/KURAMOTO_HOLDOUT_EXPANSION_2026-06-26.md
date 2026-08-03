# Kuramoto Holdout Expansion

Generated UTC: `2026-07-29T05:42:17.621148+00:00`

This artifact supersedes the legacy generic source-conditioned Kuramoto holdout claim. It evaluates kuramoto_phase_coupling on the frozen measured EIA-930 demand/forecast panel using chronological development and holdout windows, native MWh errors, seasonal-MASE-7, and every source-specific registered EIA baseline. Kuramoto was not the development-selected wave candidate and did not beat any registered baseline on mean holdout skill. This is an internal measured-software benchmark, not external replication, field validation, grid-control evidence, realized savings, procurement acceptance, or a live execution signal.

## Measured Result

- Evidence mode: `direct_measured_replay`
- Source: `EIA_GRID_VALIDATION`
- Panel rows: `14704`
- Authorities: `8`
- Candidate: `kuramoto_phase_coupling`
- Development-selected wave candidate: `lissajous_phase_paths`
- Kuramoto selected by frozen protocol: `false`
- Kuramoto holdout rank: `9`
- Kuramoto mean seasonal-MASE-7: `1.253509`
- Named baseline: `kalman_local_linear_trend`
- Daily paired wins/losses-or-ties vs Kalman: `482` / `1043`
- Daily win rate vs Kalman: `0.316066`
- Mean skill delta vs Kalman: `-0.508190706`
- Best registered baseline: `autoregressive_ridge_p14`
- Mean skill delta vs best baseline: `-0.774049311`
- Registered baselines beaten on mean: `0 / 6`
- All-baseline protocol gate passed: `false`
- Protocol-grade internal champion: `false`
- Holdout chain SHA-256: `ffb3e4448ad393027791e3c582b2c8d0dde1e6cf0685fafd630727bb2477a9cb`

## Source-Specific Baseline Gauntlet

| Baseline | Daily pairs | Wins | Losses | Mean skill | Month skill | Holm p | Gate pass |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `eia_day_ahead_forecast` | `1525` | `395` | `1130` | `-0.684103462` | `-0.742136` | `1.613495433044898e-05` | `false` |
| `seasonal_naive_7` | `1525` | `622` | `903` | `-0.218495669` | `-0.219373` | `0.04404654610215078` | `false` |
| `naive_last` | `1525` | `355` | `1170` | `-0.692974101` | `-0.743753` | `7.91033905045424e-15` | `false` |
| `kalman_local_linear_trend` | `1525` | `482` | `1043` | `-0.508190706` | `-0.530082` | `4.681169896159076e-10` | `false` |
| `autoregressive_ridge_p14` | `1525` | `307` | `1218` | `-0.774049311` | `-0.829623` | `1.6653345369377348e-16` | `false` |
| `fft_extrapolation_top5` | `1525` | `581` | `944` | `-0.30075575` | `-0.347242` | `0.00912306549281644` | `false` |

## Reviewer-Safe Interpretation

The earlier multi-source conditioned replay cannot be used as a direct performance result. On the frozen measured EIA holdout, Kuramoto is a negative result: it was not selected on development data and it loses to every registered source-specific baseline on mean skill. That result is scientifically useful because it closes an unproductive route without inflating the evidence boundary.

## Closed Claim Gates

- field_validation_claim_allowed: `false`
- real_dollar_savings_claim_allowed: `false`
- fixed_dollar_delta_sale_claim_allowed: `false`
- live_trading_or_autonomous_execution_allowed: `false`
- buyer_authorized_field_replay_request_ready: `false`

## Next Research Actions

- Do not promote Kuramoto from this EIA lane; preserve it as a measured negative result.
- Retain lissajous_phase_paths as the frozen development-selected wave candidate, while recording that it also failed the holdout promotion gate.
- Search new wave-family structure only on development windows, then freeze one candidate before rerunning the untouched holdout protocol.
- Require every future family to beat the official EIA forecast, seasonal naive, naive last, Kalman, autoregressive ridge, and FFT baselines under the same source-native metric.
- Request external replay only after a candidate clears the internal all-baseline and multiplicity gates.
