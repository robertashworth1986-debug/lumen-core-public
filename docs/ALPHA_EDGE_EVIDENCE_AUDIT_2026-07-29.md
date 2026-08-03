# Alpha and Geometry Evidence Audit (2026-07-29)

## Decision

**No financial alpha is proven by the audited artifacts.**

None of the current trading artifacts satisfies the full chain required here for a proven result: a hypothesis and decision rule frozen before evaluation, causal features and execution timing, an untouched out-of-sample or prospective holdout, realistic after-cost returns, multiplicity control, capacity analysis, and independent reproduction.

The closest existing **causal after-cost replay** is `benchmark_beater.json`. It uses lagged signals and explicit fixed costs, but it is a retrospective, overlapping-window evaluation and its own verdict is `NO_ROBUST_EDGE` (`out/execution/benchmark_beater.json:9-33`; `code/execution/benchmark_beater.py:227-264`).

The closest existing **holdout-oriented research protocol** is the symbol-timing model. It selects hours on a chronological training segment and evaluates them on a test segment, but the current artifact has no selected BTC/USD hours, zero selected holdout samples, insufficient history, and a blocked production gate (`out/audit_only/symbol_timing_edge_20260719/symbol_timing_edge_latest.json:8630-8645`, `out/audit_only/symbol_timing_edge_20260719/symbol_timing_edge_latest.json:10012-10036`, `out/audit_only/symbol_timing_edge_20260719/symbol_timing_edge_latest.json:76053-76058`).

The Kuramoto cross-sector work is useful **negative evidence**, not alpha: zero of six sectors has a proven gain, zero has even a positive exploratory result, and trading remains disabled (`out/ops/kuramoto_cross_sector_benchmark_latest.json:137-152`, `out/ops/kuramoto_cross_sector_benchmark_latest.json:1830`). Its anchored EIA result is a protocol-frozen public-data forecast test, but Kuramoto loses to the best baseline by 184.091% on relative MAE and the artifact explicitly excludes trading-edge and savings claims (`out/ops/kuramoto_cross_sector_benchmark_latest.json:32-50`).

No live-trading recommendation is made.

## Audit Standard

For this audit, a result is called:

- **Proven OOS after-cost alpha** only if the model and primary metric were frozen before an untouched evaluation period, all signals are executable without same-bar or future information, returns include a defensible cost and capacity model, multiplicity is controlled, and the result survives independent or prospective replication.
- **Retrospective after-cost replay** if signal timing is causal and stated costs are deducted, but the rule, universe, windows, or evaluation were not protected by a preregistered untouched holdout.
- **Screen or proxy** if the output is a weighted score, ranking, synthetic benchmark, excursion label, or development search rather than an executable net-return series.
- **Invalid as alpha evidence** if same-bar/future leakage or selection on the reported test sample prevents a defensible performance interpretation.

Hashes, row counts, internal maturity labels, and generated holdouts can establish provenance or software reproducibility. They do not replace independent performance evidence.

## Artifact Classification

| Artifact | What it actually measures | Cost/OOS status | Audit classification |
|---|---|---|---|
| `top_system_strategy_baseline.json` | Best ranked flow/strategy/algo combination among 364 candidates | No cost term; same-bar leakage; winner selected on the reported test data | Invalid as alpha evidence |
| `benchmark_beater.json` | Fixed FBLH strategy versus six buy-and-hold benchmarks over nested trailing windows | Causal and fixed-cost, but retrospective and not an untouched preregistered holdout | After-cost replay; current result is negative |
| `alpha_burst_lab_summary.json` | Best of 2,592 threshold/hold/algorithm trials | Full-series normalization, same-bar entry, no costs, no train/test split | Invalid as alpha evidence |
| `mega_phase8_portfolio.json` | Sharpe-weighted top-eight phase-1 combinations | Signal is shifted and a 25 bps turnover fee is deducted, but selection and evaluation reuse the same data | Fee-adjusted in-sample ensemble |
| `kraken_institutional_alpha_gauntlet_latest.json` | Weighted liquidity, spread, stress, signal, and replay-readiness scores | No strategy return series or realized cost simulation | Screen/ranking proxy |
| `symbol_timing_edge_latest.json` | Train-selected UTC-hour labels and a chronological test diagnostic | Fixed 52 bps cost and a holdout structure, but no current candidate and insufficient history | Research protocol scaffold; no alpha result |
| `kuramoto_cross_sector_benchmark_latest.json` | One-step forecast error against frozen baselines across sectors | Stronger retrospective protocol plus a separate negative prospective EIA anchor; not trading P&L | Negative forecast evidence, not alpha |
| `branching_live_breadth_replay.json` | Synthetic constrained-flow proxy scenarios derived from two live-breadth source rows | Not operational topology, field data, or trading returns; baseline wins | Geometry proxy; negative promotion result |
| `geometry_confirmatory_promotion_audit_latest.json` | Generated paired trajectory/control score comparisons | Synthetic assumptions; no hardware or HIL | Strong internal control hypothesis, not financial alpha |

## Detailed Findings

### 1. Top system strategy baseline

The artifact reports a test Sharpe of 1.5244 and a positive test delta for the top candidate, but that candidate is the winner of a 364-candidate search (`out/execution/top_system_strategy_baseline.json:3-15`, `out/execution/top_system_strategy_baseline.json:17-30`). The sidecar builder does not recompute or validate the result; it copies the preexisting top-ten CSV and summary fields into JSON (`code/execution/build_top_strategy_baseline.py:113-148`).

The upstream suite has three decisive problems:

1. **The reported test set is used for model selection.** Every flow, strategy, and algorithm combination is evaluated, sorted by `institutional_score`, `test_sharpe`, and `test_vs_baseline`, and the first row is declared the winner (`code/execution/institutional_harmonic_suite.py:595-624`, `code/execution/institutional_harmonic_suite.py:663-678`). There is no untouched final holdout or correction for selecting the maximum of 364 candidates.
2. **The top flow and algorithm use current-bar returns to weight the same current-bar return.** `geom_gaussian` computes a rolling z-score that includes the current return (`code/execution/institutional_harmonic_suite.py:282-287`), and `confidence_weighted` does the same (`code/execution/institutional_harmonic_suite.py:490-493`). Those values are multiplied directly by the same `tr_ret` or `te_ret` (`code/execution/institutional_harmonic_suite.py:544-560`). This is same-bar leakage even if the underlying directional strategy is shifted.
3. **The return formula has no fee, spread, slippage, turnover, funding, borrow, or impact term.** The train and test P&L expressions are only signal times return times flow (`code/execution/institutional_harmonic_suite.py:550-564`).

The named source contains only 721 one-minute observations, from 03:32 to 15:32 UTC on one day, despite its `5000` filename (`data/kraken_live_5000.csv:1-2`, `data/kraken_live_5000.csv:722`). The suite annualizes with `sqrt(252)`, which is not a one-minute crypto annualization (`code/execution/institutional_harmonic_suite.py:13-16`, `code/execution/institutional_harmonic_suite.py:30-37`). This result is an exploratory and contaminated screen, not OOS alpha.

### 2. Benchmark beater

This is the most defensible trading replay in the reviewed set:

- The signal at bar `i` sees prices only through `i-1`, and the previous position earns bar `i` return (`code/execution/benchmark_beater.py:227-243`).
- Turnover costs and a closing cost are deducted; the artifact specifies 10 bps round trip plus 2 bps slippage per side (`code/execution/benchmark_beater.py:209-217`, `code/execution/benchmark_beater.py:227-250`; `out/execution/benchmark_beater.json:23-33`).
- Synthetic data is excluded from the headline (`out/execution/benchmark_beater.json:19-27`).

It still is not protected OOS evidence. The fixed formula is evaluated retrospectively on six assets and four nested trailing windows (`code/execution/benchmark_beater.py:300-309`, `code/execution/benchmark_beater.py:400-420`). The 90-day sample is contained in the 365-day sample, so the 12 headline observations are neither independent trials nor a prospective holdout. There is no family-wise or false-discovery correction, confidence interval for net alpha, capacity limit, order-book impact model, or evidence that the formula was frozen independently before these prices were inspected. The artifact itself reports only 6 of 12 headline windows beating, a 50% positive-Sharpe rate, and `NO_ROBUST_EDGE` (`out/execution/benchmark_beater.json:9-21`). Preserve this as a useful negative benchmark, not as a claim of edge.

### 3. Alpha burst lab

The headline result is not economically interpretable. The artifact reports 2,592 trials, a 100% win rate, 49,900% return, Sharpe 3.8756, and zero drawdown, but the baseline return is exactly the same 49,900% and all three proof-of-savings fields are zero (`out/execution/alpha_burst_lab_summary.json:11-35`, `out/execution/alpha_burst_lab_summary.json:37-56`).

The code explains the pathology:

- `normalize` divides every observation by a denominator computed over the full series, importing future information into earlier signals (`code/execution/alpha_harmonic_burst_lab.py:390-396`).
- `harmonic_envelope` uses current return `r` to construct current signal `s` (`code/execution/alpha_harmonic_burst_lab.py:416-425`).
- The backtest opens when that same `s` crosses the threshold and immediately earns the same-bar return `r` (`code/execution/alpha_harmonic_burst_lab.py:493-523`).
- Every entry, exit, hold, algorithm, and series combination is scored on the same sample and globally sorted; there is no split or multiplicity correction (`code/execution/alpha_harmonic_burst_lab.py:544-620`, `code/execution/alpha_harmonic_burst_lab.py:830-857`).
- The P&L loop contains no transaction-cost or execution model (`code/execution/alpha_harmonic_burst_lab.py:510-540`).

This artifact should not be cited as alpha, savings, win-rate, or performance evidence.

### 4. Mega phase-8 portfolio

The underlying per-pair return calculation is causally shifted and deducts a 25 bps turnover fee (`code/mega_backtest_deep.py:26-31`). That is better than the two leaked screens above. The portfolio result is nevertheless selected and measured on the same cached data:

- Phase 1 tests every strategy/algo combination on the full available sample and ranks by Sharpe (`code/mega_backtest.py:118-145`).
- Phase 8 reads the first eight phase-1 rows, derives weights from their same-sample Sharpes, and re-evaluates them on the same OHLC cache (`code/mega_backtest_deep.py:88-110`).
- Returns from different pairs are concatenated end to end and then compounded as though simultaneous markets were sequential investments (`code/mega_backtest_deep.py:111-117`; `code/mega_backtest.py:101-113`). The reported cumulative return is therefore not a time-aligned portfolio return.
- Four positive-weight members are variants of the same `harmonic_consensus` strategy, so the output does not demonstrate independent diversification (`out/backtest/mega_phase8_portfolio.json:2-52`).

The JSON contains only members, weights, Sharpe, cumulative return, and win rate, with no generation time, input receipts, sample dates, notional, turnover, or cost declaration (`out/backtest/mega_phase8_portfolio.json:1-56`). Its 25 bps fee is not a capacity model and omits spread, slippage, market impact, funding/borrow, latency, and venue constraints. Classify it as a fee-adjusted in-sample ensemble.

The phase-2 code also labels pooled slices "walk-forward," but no training slice is used to choose or fit each combination; all combinations are precomputed and then ranked over all later blocks (`code/mega_backtest.py:148-179`). That is a rolling-origin comparison, not a protected final holdout.

### 5. Kraken institutional alpha gauntlet

The gauntlet is correctly bounded by its own artifact: it ranks paper-research candidates, makes no profit claim, allows no live order, and says external capacity evidence is missing (`out/ops/kraken_institutional_alpha_gauntlet_latest.json:2-23`). It currently has zero institutional research candidates and zero large-fund-ready candidates (`out/ops/kraken_institutional_alpha_gauntlet_latest.json:373-388`).

The `institutional_alpha_score` is not alpha. It is a weighted blend of signal quality, execution, log turnover, stress, and a replay-readiness score (`code/ops/BUILD_KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET.py:192-239`). Replay readiness receives 80 points merely when the in-sample best buy and sell hours differ (`code/ops/BUILD_KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET.py:138-145`). The upstream `alpha_edge_score` is likewise a heuristic weighted sum of recent returns, liquidity, volatility, and spread (`code/ops/build_kraken_multi_tf_alpha_map.py:368-438`), while buy/sell hours are selected from the same observed hourly curve (`code/ops/build_kraken_multi_tf_alpha_map.py:603-652`).

Its "capacity" is a capped paper-notional heuristic, explicitly not large-fund capacity proof (`code/ops/BUILD_KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET.py:148-164`). Keep this as a screening and safety-control surface only.

### 6. Symbol timing edge

This code has the strongest starting protocol for a new trading test:

- It deducts a declared 52 bps round-trip cost from forward excursion and close-return labels (`code/ops/build_symbol_timing_edge_model.py:213-252`; `out/audit_only/symbol_timing_edge_20260719/symbol_timing_edge_latest.json:6-26`).
- It performs a chronological 70/30 split, selects hours only from training data, and evaluates those hours on the test segment (`code/ops/build_symbol_timing_edge_model.py:469-513`).
- It requires minimum history, selected holdout samples, positive holdout lift, and a positive median holdout close return (`code/ops/build_symbol_timing_edge_model.py:550-595`).

The current result is still a null result. The longest cited BTC/USD series has only 721 hourly bars or 4.29 weeks, is marked `insufficient_history`, and has no train candidate (`out/audit_only/symbol_timing_edge_20260719/symbol_timing_edge_latest.json:8630-8645`). Its selected holdout contains zero samples (`out/audit_only/symbol_timing_edge_20260719/symbol_timing_edge_latest.json:10012-10036`).

Before preregistration, four weaknesses need correction:

1. Purge or embargo at least the 24-hour forecast horizon around the train/test boundary. Current forward labels overlap adjacent origins and the split is made directly on the resulting samples (`code/ops/build_symbol_timing_edge_model.py:223-250`, `code/ops/build_symbol_timing_edge_model.py:469-477`).
2. Use executable close-to-close or predeclared exit returns as the primary metric. `net_mfe_pct` uses the maximum future high inside the horizon, which is an oracle excursion rather than a realizable exit (`code/ops/build_symbol_timing_edge_model.py:228-249`).
3. Treat completed-day low/high labels as research labels only, as the code itself warns (`code/ops/build_symbol_timing_edge_model.py:228-244`, `code/ops/build_symbol_timing_edge_model.py:634-639`).
4. Control multiplicity across 53 symbols, 24 UTC hours, and exploratory weekday-hour cells. A single-symbol primary test or hierarchical/FDR-controlled family must be frozen before the holdout opens.

### 7. Kuramoto cross-sector benchmark

This is the strongest statistical implementation in the audited set, but it supports a negative conclusion. The runner uses rolling one-step origins with history only, paired loss deltas, deterministic block-bootstrap intervals, and Holm correction (`code/ops/BUILD_KURAMOTO_CROSS_SECTOR_BENCHMARK.py:1-6`, `code/ops/BUILD_KURAMOTO_CROSS_SECTOR_BENCHMARK.py:345-435`, `code/ops/BUILD_KURAMOTO_CROSS_SECTOR_BENCHMARK.py:559-620`). It also marks retrospective sources as not untouched and blocks sector, savings, and trading claims pending prospective external replay (`code/ops/BUILD_KURAMOTO_CROSS_SECTOR_BENCHMARK.py:434-436`, `code/ops/BUILD_KURAMOTO_CROSS_SECTOR_BENCHMARK.py:651-678`).

Current evidence:

- 786 evaluation origins, six sectors, zero positive exploratory sectors, and zero proven sector gains (`out/ops/kuramoto_cross_sector_benchmark_latest.json:137-152`).
- In the separately anchored EIA public-data result, `kuramoto_phase_coupling` has MAE 103,203.94 MWh versus 36,327.76 for autoregressive ridge and a relative MAE change of -184.091% (`out/ops/kuramoto_cross_sector_benchmark_latest.json:6-30`, `out/ops/kuramoto_cross_sector_benchmark_latest.json:45-50`).
- The artifact forbids converting forecast error into dollars without a buyer-approved native-unit cost rule (`out/ops/kuramoto_cross_sector_benchmark_latest.json:110-134`).

This is scientifically valuable falsification. Do not spend a new test budget on the current Kuramoto candidate unless a materially new, mechanistically justified formulation is frozen before a never-before-scored window.

### 8. Branching live-breadth replay

This artifact is a deterministic synthetic proxy, not a live topology replay. Its own boundary says that it is not raw operational topology, field validation, realized savings, government savings, or trading performance (`dashboard/data/branching_live_breadth_replay.json:909-925`; `code/ops/BUILD_BRANCHING_LIVE_BREADTH_REPLAY.py:42-50`).

The generator converts estimated loss/value/gain fields into grid dimensions and synthetic risk, demand, failure, and obstacle parameters (`code/ops/BUILD_BRANCHING_LIVE_BREADTH_REPLAY.py:156-178`). Development and validation use the same two live source rows with different deterministic seeds (`code/ops/BUILD_BRANCHING_LIVE_BREADTH_REPLAY.py:367-383`). In validation, minimum spanning tree scores 0.405403 versus 0.399775 for the best geometry, a -0.005628 delta, so the baseline still leads (`dashboard/data/branching_live_breadth_replay.json:1003-1037`). It is useful for software and experimental-design work, not alpha or field-efficiency claims.

## Brachistochrone Descent Versus Motor Phase Locking

These are different layers and should not be treated as competing algorithms:

- `brachistochrone_descent` is an **outer-loop path or trajectory-shaping hypothesis**. It proposes how a commanded state should move through space/time under a fastest-descent objective.
- A motor PLL/observer plus field-oriented control (FOC) is an **inner-loop electromechanical synchronization and actuation system**. It estimates or locks electrical phase and regulates current/torque so the motor follows commanded references.

A trajectory generator can feed position, speed, acceleration, or torque references into a PLL/FOC inner loop. A positive path-planning score does not by itself show phase-lock quality, torque control, inverter efficiency, motor robustness, or hardware safety.

The exact current internal evidence is strong but bounded:

- `brachistochrone_descent` was development-preselected against `minimum_jerk_curve`; all five condition-level guardrails pass (`out/ops/geometry_confirmatory_promotion_audit_latest.json:814-857`).
- The aggregate paired score delta is **0.179587**, with paired-normal CI95 **[0.177893, 0.181281]** over **1,000 generated scenarios** (`out/ops/geometry_confirmatory_promotion_audit_latest.json:909-917`).
- Travel time, energy proxy, and constraint-violation guardrails pass (`out/ops/geometry_confirmatory_promotion_audit_latest.json:867-897`).
- Promotion fails only `all_metric_noninferiority` because smoothness is **0.0884** versus **0.0452** for minimum jerk, where lower is better (`out/ops/geometry_confirmatory_promotion_audit_latest.json:815-820`, `out/ops/geometry_confirmatory_promotion_audit_latest.json:859-906`).

This is a **strong control/trajectory hypothesis, not financial alpha**. It is also not yet motor evidence. The benchmark uses generated scenarios and formula-based path metrics (`code/geometry_optimal_curve_transport_benchmark.py:108-164`); minimum jerk and brachistochrone are implemented as fixed planning-factor analogues (`code/geometry_optimal_curve_transport_benchmark.py:205-230`, `code/geometry_optimal_curve_transport_benchmark.py:282-311`). The audit explicitly says generated software evidence does not establish field validation or trading alpha (`out/ops/geometry_confirmatory_promotion_audit_latest.json:3-10`).

The plausible next candidate is:

> A constrained brachistochrone objective with an explicit minimum-jerk regularizer, producing references for an otherwise unchanged PLL/observer plus FOC motor inner loop.

The decisive test should be hardware-in-the-loop (HIL), not another synthetic leaderboard. Compare it against minimum-jerk trajectory plus the identical PLL/FOC stack, plant model, inverter limits, loads, and disturbances. Freeze one primary objective before testing, plus noninferiority gates for smoothness, tracking error, peak current, torque ripple, current THD, DC-bus energy, thermal proxy, settling time, and constraint violations. Include sensor noise, phase-estimation error, load steps, saturation, latency, and dropout scenarios. Any later physical claim requires bench or field replication after HIL.

## Ranked Preregistered Tests

Only these three hypotheses are worth a new protected test on present evidence.

### 1. Purged BTC/USD UTC-hour timing holdout

**Hypothesis:** A single development-selected UTC entry window improves 24-hour executable close-to-close BTC/USD return after all stated costs versus all-hour and matched random-hour baselines on a future untouched holdout.

Freeze one symbol, one data vendor/venue, one selection rule, one primary net-return metric, the 52 bps minimum cost plus a timestamped spread/slippage schedule, a 24-hour purge/embargo, nonoverlapping positions, minimum sample size, and a capacity/participation cap. Open the holdout only after at least 26 weeks of development history and collect a new prospective interval without retuning. Report the null if development again selects no hour.

**Why ranked first:** the existing implementation already separates train from test and correctly blocks promotion when evidence is absent. It needs stronger data and statistics, not a favorable reinterpretation of the current null.

### 2. Frozen FBLH prospective replay

**Hypothesis:** The exact current FBLH formula and thresholds produce positive net excess return versus buy-and-hold on a future, date-locked multi-asset panel after venue-appropriate spread, slippage, turnover, borrow/funding, and impact costs.

Freeze the formula at `code/execution/benchmark_beater.py:122-169`, one primary aggregate statistic, the asset panel, weighting rule, start/end timestamps, missing-data rule, and family-wise error procedure. Do not use nested trailing windows as separate confirmations. A single future panel should be the confirmatory test; no threshold, component weight, asset, or window may be changed after opening it.

**Why ranked second:** it is the only audited trading candidate with clearly lagged signals and explicit costs, but the present retrospective result is negative. One decisive prospective test is justified; repeated retrospective searches are not.

### 3. Regularized brachistochrone-to-PLL/FOC HIL test

**Hypothesis:** A brachistochrone trajectory objective with a preregistered minimum-jerk regularizer improves the primary HIL mission metric versus minimum-jerk planning while remaining noninferior on smoothness and motor-control guardrails, with the same PLL/FOC implementation.

Freeze the regularization weight before HIL, or select it on a development bench and then lock it before a separate confirmatory scenario set. Use paired scenarios and preserve the smoothness failure as a hard gate. This test may establish control-system evidence; it cannot establish trading alpha.

## Do Not Promote

Do not allocate a new confirmatory budget to the current `alpha_burst_lab`, `top_system_strategy_baseline`, or `mega_phase8` headline results until their leakage, selection, and portfolio-accounting defects are removed. Do not promote the current Kraken gauntlet score as a return metric. Do not market Kuramoto or branching efficiency gains while their current baselines lead.

The fastest credible path is not another large search. It is one frozen causal rule, one untouched outcome interval, one realistic cost/capacity contract, one primary metric, and an independent evaluator who receives the protocol before the outcomes exist.
