# Market-Signal Kraken Panel Benchmark

Protocol: `LUMENCORE_MARKET_SIGNAL_KRAKEN_PANEL_20260729_V1`
Generated UTC: `2026-07-29T20:17:04.550427+00:00`
Status: `RETROSPECTIVE_PANEL_SCREEN_NO_PROMOTION`
Payload SHA-256: `d74f8f09b2e552c45df0175b1d6676279fb3511fa0628a9c79fb28200548a404`

## Decision

**No candidate is promoted.**

Exploratory retrospective paper/replay only. The turnover-ranked panel was frozen before candidate scoring, but it was not prospectively protected and the pairs share a common exchange and market regime. No alpha, edge, profit, value, field-performance, independence, execution-quality, or live-trading claim is allowed.

## What Changed

- The earlier source-native sidecar had one series per source. This panel applies the same four candidates and four baselines to 12 pre-scoring Kraken pairs.
- Pair selection used public 24-hour turnover with legacy alpha priority disabled, then removed stablecoin/fiat bases and duplicate quote variants.
- Every pair has 720 hourly prices and [660] post-warmup scoring observations.

## Exact Scope

- Registered candidates: `4`
- Registered baselines: `4`
- Panel pairs: `12`
- Strategy/pair results: `96`
- Candidate-baseline comparisons: `16`
- Mean-positive comparisons: `3`
- Exploratory global-Holm positives: `1`
- Promotions: `0`

## Candidate Diagnostics

| Candidate | Mean wins / 4 | Holm positives / 4 | All-baseline mean win | All-baseline Holm win | Promotion |
|---|---:|---:|---|---|---|
| `beast_strategy_trend` | 1 | 1 | no | no | `BLOCKED` |
| `beast_strategy_mean_revert` | 0 | 0 | no | no | `BLOCKED` |
| `beast_strategy_breakout` | 1 | 0 | no | no | `BLOCKED` |
| `beast_strategy_regime_switch` | 1 | 0 | no | no | `BLOCKED` |

## Panel Custody

| Pair | Rows | 24h turnover at selection | SHA-256 |
|---|---:|---:|---|
| `BTC/USD` | 720 | $77,329,585.52 | `094ddf65624d105817d33d0c3bc2bc2b09b26bbc357a355547d1840812eda8c5` |
| `ETH/USD` | 720 | $31,514,905.17 | `27add38811efc4b2289e46c7a6036b9482b604a4ac96ea51fd1f3fa1d6180b9b` |
| `SOL/USD` | 720 | $13,149,769.76 | `97de4210de9faba97c685276f12c434365238241a06726e73ea97080e8c5ba78` |
| `XRP/USD` | 720 | $12,708,145.04 | `e8bd1260dac9f7e9dc1b1b82a65d48c28a157237cbc05a6d468570264e724758` |
| `ADA/USD` | 720 | $9,587,420.30 | `8c64b379e47b005a6f47fde5f27651bd8a24b387ee2c3f379b7e1e940b06b88d` |
| `HYPE/USD` | 720 | $4,133,959.20 | `6e1a2f31817f07e5e01ffde77c3f36beacd4703d9e4ed04348489ac0daa35b1f` |
| `SUI/USD` | 720 | $3,971,845.21 | `ee46394824a5a74b66de427c80ea78df7e405da6a1d707199cfc8d7e9b5cf7ae` |
| `XMR/USD` | 720 | $3,961,686.32 | `4ba0d8d6ab1302bc20fad49890b62843c05f17840748de0947c147ffff486350` |
| `LTC/USD` | 720 | $3,342,632.50 | `ed3219eb7975dcaf822356ca382d03d183b78e03f23c8447446b7badc632ddcf` |
| `DOGE/USD` | 720 | $2,832,183.33 | `59ac3045c4c7a74a0975f43b01b725d891de049be9d5e7c587ddeb7743634357` |
| `ZEC/USD` | 720 | $2,501,911.28 | `4e49854ff7bb190e51fd6ab92ba5c41c3565eb89d05ebe62b4ce9ef7204c4927` |
| `TAO/USD` | 720 | $2,014,708.28 | `4ce9859793b7df8d0652f4d15c6ce0fc49c5b2ff17acd781ca85aa0c749f6c4c` |

## Limits

- This is retrospective development evidence, not a prospective test.
- Pairs share an exchange, timestamps, and a broad crypto market factor.
- The fixed 10 bps turnover cost proxy excludes funding, borrow, latency, queue position, and market impact.
- The panel-selection rule did not use these candidate or baseline scores, but turnover selection can still create universe-selection effects.
- Any future challenger must be frozen before untouched or prospective scoring.

## Safest Next Action

Use this panel only to choose a small challenger set and freeze it before collecting future bars. Keep the existing prospective time-series protocol unchanged.
