# Market-Signal Source-Native Benchmark

Protocol: `LUMENCORE_MARKET_SIGNAL_SOURCE_NATIVE_20260729_V1`
Generated UTC: `2026-07-29T13:48:55.612230+00:00`
Status: `EXPLORATORY_RETROSPECTIVE_NEGATIVE_OR_INSUFFICIENT_EVIDENCE`
Output payload SHA-256: `1b82e123b64969967022890c9d58c27754acf846e85829f88dbd9617240b8605`

## Decision

**No candidate is promoted.**

Exploratory retrospective paper/replay only. This sidecar does not establish alpha, edge, profit, value, field performance, prospective validity, execution quality, or live-trading authority. No external action is allowed.

## Fixed Scope

- Registered candidates: `4`
- Implemented candidates: `4`
- Missing candidate implementations: `0`
- Registered baselines: `4`
- Implemented baselines: `4`
- Sources: `3`
- Source series: `3`
- Strategy/source-series results: `24`
- Candidate/source/baseline comparisons: `48`
- Globally Holm-positive comparisons: `0`
- Candidates passing every source-native baseline: `0`

No parameter was selected or tuned on the evaluation observations. Every position applied to `return[t]` uses only information available through `t-1`.

## Input Custody

| Source | Registered snapshot | Rows | Series | Embedded SHA-256 verified |
|---|---|---:|---:|---|
| KRAKEN_PUBLIC | `data/live_measured/kraken_public/kraken_public_20260713T192646Z.json` | 250 | 1 | `true` |
| TWELVE_DATA | `data/live_measured/twelve_data/twelve_data_20260713T192646Z.json` | 250 | 1 | `true` |
| ALPHAVANTAGE | `data/live_measured/alphavantage/alphavantage_20260713T192646Z.json` | 100 | 1 | `true` |

The builder independently recomputes each snapshot's canonical embedded hash and requires an exact match to the snapshot reference in the qualified source wiring matrix.

## Implementations

| Role | Registered ID | Fixed implementation |
|---|---|---|
| candidate | `beast_strategy_trend` | `lagged_return_mean_cross_v1` |
| candidate | `beast_strategy_mean_revert` | `lagged_return_zscore_reversion_v1` |
| candidate | `beast_strategy_breakout` | `lagged_close_channel_breakout_v1` |
| candidate | `beast_strategy_regime_switch` | `lagged_volatility_regime_switch_v1` |
| baseline | `buy_and_hold` | `constant_long_v1` |
| baseline | `moving_average_cross` | `lagged_close_mean_cross_v1` |
| baseline | `ridge_return_baseline` | `fixed_history_ridge_return_sign_v1` |
| baseline | `volatility_targeting` | `lagged_long_volatility_target_v1` |

## Per-Source and Per-Series Results

| Source | Series | Strategy | Role | Obs | Cost bps | Turnover | Assumed cost | Max drawdown | Risk-adjusted score | Net paper return |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| KRAKEN_PUBLIC | `XXBTZUSD` | `beast_strategy_trend` | candidate | 190 | 10.00 | 89.000000 | 0.089000 | 0.143374 | -0.163675 | -0.121880 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `beast_strategy_mean_revert` | candidate | 190 | 10.00 | 86.000000 | 0.086000 | 0.096105 | -0.175833 | -0.095177 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `beast_strategy_breakout` | candidate | 190 | 10.00 | 48.000000 | 0.048000 | 0.051296 | -0.058165 | -0.024448 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `beast_strategy_regime_switch` | candidate | 190 | 10.00 | 73.000000 | 0.073000 | 0.059766 | -0.072280 | -0.045925 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `buy_and_hold` | baseline | 190 | 10.00 | 1.000000 | 0.001000 | 0.043543 | -0.021587 | -0.017958 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `moving_average_cross` | baseline | 190 | 10.00 | 21.000000 | 0.021000 | 0.136619 | -0.150053 | -0.110524 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `ridge_return_baseline` | baseline | 190 | 10.00 | 123.000000 | 0.123000 | 0.169522 | -0.225386 | -0.159494 |
| KRAKEN_PUBLIC | `XXBTZUSD` | `volatility_targeting` | baseline | 190 | 10.00 | 3.629089 | 0.003629 | 0.018915 | -0.049409 | -0.012146 |
| TWELVE_DATA | `AAPL` | `beast_strategy_trend` | candidate | 190 | 5.00 | 59.000000 | 0.029500 | 0.137248 | 0.043211 | 0.107686 |
| TWELVE_DATA | `AAPL` | `beast_strategy_mean_revert` | candidate | 190 | 5.00 | 92.000000 | 0.046000 | 0.171480 | -0.071211 | -0.118297 |
| TWELVE_DATA | `AAPL` | `beast_strategy_breakout` | candidate | 190 | 5.00 | 56.000000 | 0.028000 | 0.122415 | -0.030799 | -0.042153 |
| TWELVE_DATA | `AAPL` | `beast_strategy_regime_switch` | candidate | 190 | 5.00 | 86.000000 | 0.043000 | 0.153594 | -0.016986 | -0.049452 |
| TWELVE_DATA | `AAPL` | `buy_and_hold` | baseline | 190 | 5.00 | 1.000000 | 0.000500 | 0.138230 | 0.081063 | 0.234687 |
| TWELVE_DATA | `AAPL` | `moving_average_cross` | baseline | 190 | 5.00 | 13.000000 | 0.006500 | 0.174809 | 0.025264 | 0.052299 |
| TWELVE_DATA | `AAPL` | `ridge_return_baseline` | baseline | 190 | 5.00 | 189.000000 | 0.094500 | 0.251873 | -0.035917 | -0.117680 |
| TWELVE_DATA | `AAPL` | `volatility_targeting` | baseline | 190 | 5.00 | 4.392647 | 0.002196 | 0.119410 | 0.032047 | 0.040194 |
| ALPHAVANTAGE | `EURUSD` | `beast_strategy_trend` | candidate | 40 | 2.00 | 11.000000 | 0.002200 | 0.010587 | 0.035951 | 0.004063 |
| ALPHAVANTAGE | `EURUSD` | `beast_strategy_mean_revert` | candidate | 40 | 2.00 | 18.000000 | 0.003600 | 0.005657 | 0.106372 | 0.004430 |
| ALPHAVANTAGE | `EURUSD` | `beast_strategy_breakout` | candidate | 40 | 2.00 | 14.000000 | 0.002800 | 0.012542 | -0.110016 | -0.005653 |
| ALPHAVANTAGE | `EURUSD` | `beast_strategy_regime_switch` | candidate | 40 | 2.00 | 22.000000 | 0.004400 | 0.007103 | 0.227699 | 0.013772 |
| ALPHAVANTAGE | `EURUSD` | `buy_and_hold` | baseline | 40 | 2.00 | 1.000000 | 0.000200 | 0.025903 | -0.156258 | -0.018432 |
| ALPHAVANTAGE | `EURUSD` | `moving_average_cross` | baseline | 40 | 2.00 | 3.000000 | 0.000600 | 0.007604 | 0.195507 | 0.022878 |
| ALPHAVANTAGE | `EURUSD` | `ridge_return_baseline` | baseline | 40 | 2.00 | 37.000000 | 0.007400 | 0.010628 | 0.087621 | 0.010189 |
| ALPHAVANTAGE | `EURUSD` | `volatility_targeting` | baseline | 40 | 2.00 | 1.000000 | 0.000200 | 0.025903 | -0.156258 | -0.018432 |

These are bounded retrospective paper/replay measurements, not realized or expected trading outcomes.

## Clustered Inference and Global Correction

- Paired unit: `source_series`
- Test: `two_sided_exact_sign_test_on_source_series_risk_adjusted_score_deltas`
- Multiple-comparison control: `holm`
- Familywise alpha: `0.05`
- Inferentially insufficient comparisons: `48`
- Global Holm positives: `0`

No candidate is promoted. Current snapshots contain one series per source, so every candidate-source-baseline comparison is inferentially insufficient under the predeclared source-series cluster rule.

Time observations inside one source series are deliberately not counted as independent inferential units. The three current sources each contain only one series, so raw p-values are forced to `1.0` under the predeclared single-cluster rule.

## Limitations

- The snapshots are retrospective and were not prospectively protected for this sidecar.
- There is one series per source, below the five-cluster inferential minimum.
- Costs are fixed research proxies, not executable venue quotes.
- Funding, borrow, latency, queue position, spread variation, taxes, rollover, and market impact are not fully modeled.
- Candidate inclusion comes from the existing registry and is not evidence of merit.
- A mean score difference is descriptive only; no comparison survives the global promotion gate.

## Claim Controls

- Alpha claim allowed: `false`
- Edge claim allowed: `false`
- Profit claim allowed: `false`
- Value claim allowed: `false`
- Field-performance claim allowed: `false`
- Prospective-validation claim allowed: `false`
- Live trading allowed: `false`
- External action allowed: `false`

## Reproduction

```powershell
python code/ops/BUILD_MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK.py --generated-utc 2026-07-29T13:48:55.612230+00:00
python -m pytest -q tests/test_market_signal_source_native_benchmark.py
```
