# Real Noise Promotion Sweep

Generated UTC: 2026-07-03T08:01:19.989751+00:00

## Boundary

Real-noise promotion sweep only. It hashes local/provider snapshots, measures noise and baseline-probe readiness, and identifies datasets ready for locked replay. It does not prove field validation, realized savings, fixed frozen-delta pricing, safety certification, medical efficacy, or autonomous live trading.

## Summary

- CSV snapshots scanned: 601
- Ready for locked replay: 206
- Strong real-noise candidates: 15
- Rows read: 34,450
- Numeric samples: 67,994
- Lanes with ready data: 6

## Strongest Ready Sources

| Provider | Lane | Rows | Numeric Samples | Signal | Best Baseline MAE | State |
|---|---:|---:|---:|---|---:|---|
| FRED_DGS10 | macro_rate_labor | 16049 | 16049 | value | 0.04312313 | strong_real_noise_replay_candidate |
| MER_T09_04 | energy_grid_proxy | 5704 | 15201 | Value | 0.10587843 | strong_real_noise_replay_candidate |
| KRAKEN_LIVE_5000 | market_noise | 721 | 5047 | volume | 1.71863247 | strong_real_noise_replay_candidate |
| FRED_CPIAUCSL | macro_rate_labor | 949 | 949 | value | 0.38400633 | strong_real_noise_replay_candidate |
| FRED_UNRATE | macro_rate_labor | 938 | 938 | value | 0.16275347 | strong_real_noise_replay_candidate |
| TREASURY_FISCAL_PUBLIC | macro_rate_labor | 100 | 800 | avg_interest_rate_amt | 1.07848316 | strong_real_noise_replay_candidate |
| 930-DATA-EXPORT_(2) | general_real_noise | 193 | 719 | Demand Forecast (MWh) | 8087.73162362 | strong_real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 100 | 700 | open | 208.47676768 | strong_real_noise_replay_candidate |
| TABLE14 | general_real_noise | 74 | 672 | Jan | 0.32009859 | real_noise_replay_candidate |
| TWELVE_DATA | market_noise | 100 | 500 | open | 3.44601161 | strong_real_noise_replay_candidate |
| ALPHAVANTAGE | market_noise | 100 | 400 | 4. close | 0.00334242 | strong_real_noise_replay_candidate |
| TREASURY_FISCAL_PUBLIC | macro_rate_labor | 50 | 400 | avg_interest_rate_amt | 1.04848231 | real_noise_replay_candidate |
| TREASURY_FISCAL_PUBLIC | macro_rate_labor | 50 | 400 | avg_interest_rate_amt | 1.04848231 | real_noise_replay_candidate |
| TREASURY_FISCAL_PUBLIC | macro_rate_labor | 50 | 400 | avg_interest_rate_amt | 1.04848231 | real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 50 | 350 | open | 162.87755102 | real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 50 | 350 | open | 187.0122449 | real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 50 | 350 | open | 187.0122449 | real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 50 | 350 | open | 188.82040816 | real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 50 | 350 | open | 165.36122449 | real_noise_replay_candidate |
| KRAKEN_PUBLIC | market_noise | 50 | 350 | open | 189.75510204 | real_noise_replay_candidate |

## Next Actions

1. Run the locked champion-vs-baseline replay on each ready source lane.
2. Freeze per-source replay outputs with hashes and negative-evidence notes.
3. Ask an external buyer/lab to approve held-out data, acceptance metric, and avoided-cost conversion.
4. Promote dollar claims only after the outside owner accepts the replay protocol and result interpretation.
