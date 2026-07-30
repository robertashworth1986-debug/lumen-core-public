# Source-Native Benchmarking for Nature-Inspired Time-Series Families: A Fail-Closed Experimental Protocol

- Generated UTC: `2026-07-30T03:32:40+00:00`
- Status: `CURRENT_PUBLIC_SAFE_HUMAN_REVIEW_REQUIRED`
- Peer reviewed: `false`
- Independently validated: `false`
- External release authorized: `false`

> This technical note reports local software, custody, benchmark, and protocol states. It is not peer review, independent validation, a performance claim, field validation, trading alpha, realized savings, enterprise value, a patent opinion, or deployment authority.

## Abstract

LumenCore registers candidate computational families inspired by natural forms, but does not treat inspiration as evidence. This note reports a source-native benchmark ledger, the retrospective disposition of prior leads, a fixed-rule 12-pair retrospective market panel, and a frozen prospective protocol. The current ledger contains 140 registered families, 35 implementations, and 126 direct candidate-source-baseline comparisons. The market panel repairs the prior single-series bookkeeping bottleneck and contains one narrow exploratory Holm-positive comparison, but its candidate loses on mean to three other registered baselines. No candidate passes the promotion gate. The scientific contribution is therefore a reproducible comparison and falsification framework, not a performance champion.

## Research Question

Can a predeclared candidate family beat every accepted baseline for a specific source, series, cadence, and forecast horizon under prospective custody, clustered inference, an effect floor, and familywise error control?

## Current Evidence Snapshot

- Registered families: `140`
- Implementations present: `35`
- Missing implementations: `105`
- Candidate-source cards: `23`
- Direct comparisons: `126`
- Global Holm-positive comparisons: `0`
- Promoted champions: `0`
- Market-signal candidates: `4`
- Market-signal sources: `3`
- Market-signal comparisons: `48`
- Market-signal inferentially insufficient: `48`
- Kraken panel pairs: `12`
- Kraken panel comparisons: `16`
- Kraken panel exploratory Holm-positive comparisons: `1`
- Kraken panel all-baseline mean winners: `0`
- Kraken panel promotions: `0`

## Source-Native Method

- Comparison unit: Candidate-by-source cards evaluated against the baseline roster registered for that source, cadence, series, and horizon.
- Horizons: `[1, 3, 5]`
- Leakage control: Expanding history ends immediately before each forecast origin.
- Independence control: Inference clusters overlapping origins and horizons at the source-series level instead of treating every row as independent.
- Multiple-testing control: Global Holm correction across the candidate-source-baseline comparison family; prior subset leads receive no preference.
- Baselines:
  - `naive_last`
  - `drift`
  - `moving_average`
  - `exponential_smoothing`
  - `linear_trend`
  - `seasonal_naive_source_period`
  - `damped_holt_ets`
  - `autoregressive_ridge_source_lag`

## Retrospective Result

The former FRED and TWELVE_DATA subset leads are retired because they do not survive source-series clustering and the complete source-native baseline gauntlet. Four fixed market-signal families were also run against four registered baselines on each of Kraken, TwelveData, and AlphaVantage. All 48 market comparisons are inferentially insufficient because each source currently supplies one source-series cluster. A separate fixed-rule Kraken panel then evaluated the same four candidates against four baselines across 12 pre-scoring-selected pairs. One of 16 comparisons was positive after exploratory global Holm correction: beast_strategy_trend versus ridge_return_baseline, with mean unannualized risk-adjusted-score delta 0.061277644465, raw exact sign-test p 0.00634765625, and global Holm-adjusted p 0.04443359375. The same candidate lost on mean to buy-and-hold, moving-average-cross, and volatility-targeting baselines. Across the authoritative ledger and panel, zero candidate cards cleared the complete registered baseline set and zero candidates pass promotion.

## Frozen Prospective Protocol

- Protocol: `LUMENCORE_TS_SOURCE_NATIVE_20260729_V1`
- Status: `FROZEN_AWAITING_FUTURE_OBSERVATIONS`
- Decision: `WAITING_FOR_NEW_SOURCE_ROWS`
- Eligible future observations: `0`
- Candidate label: `fractal_brownian_surface`
- Scientific estimator: `hurst_conditioned_multiscale_increment_heuristic_v1`
- Metric: `relative_mean_absolute_error`
- Formula: `rMAE = MAE_candidate / MAE_baseline`
- Contrasts: `16`
- Correction: `one_sided_holm_familywise`
- Protocol SHA-256: `980ebaa821212965bffe04334df8c19f1a03e12acac7d9d04f38f21f03b0e1e5`

## Scientific Contribution

- A source-native baseline contract that prevents cross-source or cadence-mismatched promotion.
- A custody gate that binds exact source snapshots before benchmark acceptance.
- A clustered inference rule that avoids pseudoreplication from overlapping forecast origins and horizons.
- A full-family multiple-testing rule that prevents cherry-picking isolated wins.
- A future-only protocol with fixed endpoints, effect floor, sample gates, ablations, and falsification states.
- A cost-aware market-signal replay that uses identical timestamps, future-return rows, turnover costs, and source-specific baselines without granting a promotion from descriptive wins.
- A pre-scoring 12-pair Kraken panel that holds candidate, baseline, timing, and 10-basis-point turnover-cost rules fixed while retaining losses and a narrow exploratory positive result.
- A machine-readable claim boundary that keeps software proof separate from field, economic, or deployment claims.

## Limitations

- 105 of 140 registered families lack implementations.
- Only 3 lanes currently have executable direct measured adapters; the wider nature-inspired registry remains inventory, synthetic stress, or context until implemented.
- The original 48 market-signal comparisons remain inferentially insufficient under the predeclared five-cluster minimum because each source has one registered series.
- The 12-pair Kraken panel meets the exploratory pair-count floor, but pair-level signs share one exchange and overlapping market timestamps. Independence is therefore unconfirmed, and its one narrow Holm-positive comparison is not confirmatory alpha or edge.
- The panel's narrow trend-versus-ridge result is not a promotion: the same candidate loses on mean to the other three registered baselines, and no candidate clears the complete four-baseline set.
- The prospective protocol has zero eligible future observations and cannot yet support a prospective accuracy conclusion.
- No result establishes universal superiority, field performance, trading alpha, realized savings, customer acceptance, or deployment authority.

## Legacy Concept-Paper Disposition

The prior BioGeometry, scalar-field, bioresonance, cooling-savings, zero-point, weather-control, and wormhole-adjacent concept papers are preserved as historical speculative material and are blocked from upload or external scientific use.

## Receipt

- Whitepaper payload SHA-256: `df603bae68cc4d053f0956d44eda0a4997e5c2a2cf8b992cd7871e2cf424e3a2`
