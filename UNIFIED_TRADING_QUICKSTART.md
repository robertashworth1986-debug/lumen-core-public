# LumenCore trading research and evidence map

Updated September 13, 2026. This supersedes the earlier launch-oriented quickstart. It advances the existing external-review / paid-pilot outcome by making the built trading lane inspectable.

## Start with the connected views

- [Mission Control](https://lumen-core.ai/mission_control.html): build and source breadth.
- [Quant Lab](https://lumen-core.ai/quant_lab.html): candidate research and later gates.
- [Kraken research](https://lumen-core.ai/kraken_execution_dashboard.html): historical order records and accounting boundary.
- [Grant Factory](https://lumen-core.ai/grants.html): turn bounded evidence into reviewable application work.

These URLs show the connected review views only after the separate public release. Source changes and tests do not prove deployment. The complete August 8 operator interfaces remain in Git history at `987e37ea47858c9c7dcc03f179f859f78fc9e995`; their private runtime is not reconnected by this change.

## What has actually been recovered

| Evidence | Result | Interpretation |
| --- | --- | --- |
| `investor_txids/trade_log.json` | Five distinct April 5 order IDs across SOLUSD, ADAUSD and SPXUSD | Historical first-party rows labeled LIVE/CLOSED. Missing closing-fill and fee joins prevent a strategy-level net-profit claim. |
| `runtime_env_hydration_proof.json` | April 4 smoke output contains an order ID and a validate=false payload under a VALIDATE_ONLY label | Historical mode-label conflict. Do not rerun this receipt as a smoke test. Current `code/kraken_execution.py` explicitly forces validate=True in the validation helper. |
| `dashboard/level3_truth_dashboard.json` | 1,872 input rows; 17 selected champions | Selection output, not 17 externally validated strategies. |
| `dashboard/level4_live_summary.json` | Five HYPE/PAXG/XRP/FET candidates; test MC Sharpes 4.142–6.006 | Historical research. The LIVE_ALLOCATION_READY label does not authorize trading. |
| `dashboard/level6_paper_guardrail.json` | Zero approved winners, zero observed paper events, paper_ready_for_live=false | The later gate held all five; four follow-on Sharpe values are negative. |
| `gen4_real/champion.json` | USDC/USD mean reversion, reported Sharpe 8.501 | Recover costs, sampling interval and source window before interpreting this stablecoin result. |
| `gen4_validate_scale/validated_champion.json` | ZEC/USD trend, reported Sharpe 1.782 | Candidate-specific historical result. |
| `gen5_output/gen5_champion.json` | ZEC stress windows have mixed results | Does not establish stable performance across periods. |
| `gen6_5/gen6_5_state.json` | 41 trades, reported PnL -6.21 | State-file units and exchange attribution require reconciliation. |
| `gen7/state.json` | Three trades, reported PnL +3,079.687 | Mode and venue reconciliation are not established in the summary; not verified cash profit. |
| `gen7_clean/best.json` | Shadow XRP/USD, 126 trades, PnL -19.41 | Explicit shadow result. |
| `credible_top10.json` | Repeated 721-row Kraken input entries, test Sharpe 5.082 | Deduplicate dataset references and recover metric units, costs and baseline definition. |
| `adaptive_champion.json` | Sharpe 15.058; vs_baseline -0.117 | High Sharpe does not establish improvement over the incumbent. |
| `rolling_performance.json` | Paper source, zero trades and paper PnL zero | Fictional/paper accounting, not realized exchange PnL. |
| `config/accounts/KRAKEN_PRIMARY/runtime_control.json` | Paper mode, live orders disabled | Committed configuration; current server state must be checked separately by an authorized operator. |

Historical measurements are preserved. No current market edge, fixed daily return, five-day proof rule or blanket “all generations live-tested” claim is established by this recovered set.

## The research stack

| Family | Existing implementation | How it connects |
| --- | --- | --- |
| Broad strategy search | `code/backtest_all_strategies.py`, `code/universe_backtest.py`, `code/universe_backtest_multi.py`, `code/mega_backtest.py`, `code/mega_backtest_deep.py` | Candidate generation and baselines; retain the complete selection universe. |
| Walk-forward research | `code/backtest_walkforward_engine.py` | Sequential train/test scaffolding; its example is synthetic and is not production evidence. |
| Unified signals | `code/unified_alpha_engine.py`, `code/adaptive_engine.py`, `code/universal_harmonic_edge_core.py` | Signal/ranking architecture, distinct from realized execution. |
| Pair and timeframe screening | `code/ops/build_kraken_multi_tf_alpha_map.py` | Spread, trend, recent movement and ranked pair diagnostics. An alpha score is a heuristic. |
| Move clustering | `code/ops/build_kraken_6m_move_clusters.py` | Movement by time-of-day/weekday with observed history coverage. A six-month target does not prove six months were obtained. |
| Timing holdouts | `code/ops/build_symbol_timing_edge_model.py`, `code/ops/collect_kraken_hourly_history.py` | Chronological selection, holdout diagnostics and a default 52-bps round-trip cost; review history support and overlap. |
| Spike and swing research | `code/backtest_spike_hunter.py`, `code/kraken_dislocation_scan.py`, `code/kraken_followup_review.py` | Event-specific research; do not infer net profit from alerts. |
| Edge quality | `code/edge_truth_guard.py` | Baseline-relative quality, extreme Sharpe and sample checks. Preserve fail/hold verdicts. |
| Cross-sector prioritization | `code/ops/BUILD_ALPHA_EDGE_LOCK_ENGINE.py` | Heuristic scoring and seeded Gaussian confidence simulations. These are not an empirical probability of trading profit. |
| Allocation and regime | `code/execution/crypto_allocator.py`, `code/execution/crypto_regime_controller.py` | Allocation decisions remain downstream of data and authorization gates. |
| Execution | `code/kraken_execution.py`, `code/unified_trade_executor.py`, `code/execution/kraken_live_growth_controller.py` | Order integration and safeguards; no order action is part of the review build. |
| Accounting and proof | `code/ops/ANALYZE_TRADER_BLEED.py`, `code/build_kraken_positive_proof.py` | Join fills, cost basis, fees and strategy attribution. The bleed helper's gross-price comparisons alone do not establish net results. |
| Dashboard and review | `code/ops/build_research_review_surfaces.py`, `dashboard/assets/luma_command_fabric.js` | Eight connected static review pages, public health only, source links and archived full-interface links. |

## Read-only verification

From the repository root:

```sh
python code/ops/build_research_review_surfaces.py --check
python code/ops/ensure_dashboard_command_fabric.py --strict
python -m pytest tests/test_kraken_evidence_accounting.py tests/test_public_legacy_route_holds.py tests/test_public_offer_consistency.py
```

The evidence builder reads local artifacts and writes a report; it never calls Kraken. Unknown PnL is null. A measured zero requires complete accounting provenance. Paper and shadow reports are never eligible for the realized field.

For a first-party reconciled result, the input must explicitly provide: mode=live, finite realized_net_pnl, quote_currency, start/end UTC window, and a reconciliation record with status=MATCHED, fees_included=true, cost_basis_complete=true, positive closed_trade_count and fills_source. This is reported reconciliation, not independent verification. Preserve the underlying fill export privately.

## Remaining research gates

1. Recover the exact original input files, symbols, dates, strategy versions and parameter selection history.
2. Freeze the baseline, train/holdout split, overlap/embargo policy and market-cost assumptions.
3. Compare all selected candidates on untouched data; keep losing and held results.
4. Join existing historical order IDs to fills, fees, closing cost basis and strategy decisions.
5. Confirm paper operation and source health separately from historical research. Runtime changes, live orders, withdrawals and deployment remain separate actions.

Private Gmail receipts, account details, screenshots and notebook material belong in the private review estate. They must not be copied into this public repository.
