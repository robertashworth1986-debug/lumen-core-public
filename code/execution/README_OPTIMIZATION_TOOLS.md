# Execution Optimization Tools

This folder includes utility scripts for improving net profitability and investor reporting.

## 1) Runtime threshold optimizer (`runtime_optimizer_optuna.py`)

Optimizes a key entry-quality threshold (`min_gate_score_for_entry`) using `optuna` and historical closed trades.

### Runtime Optimizer Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/runtime_optimizer_optuna.py --trials 120 --min-kept 5
```

### Runtime Optimizer Output

- `out/execution/runtime_optimizer_recommendation.json`

---

## 2) Investor performance report (`investor_performance_report.py`)

Builds investor-facing metrics from `trade_log.json`, including Sharpe/Sortino/Calmar/max drawdown and fee drag.

### Investor Report Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/investor_performance_report.py
```

### Investor Report Outputs

- `out/execution/investor_performance_report.json`
- `out/execution/investor_performance_report.md`

---

## 3) DuckDB + Parquet investor pipeline (`trade_log_duckdb_pipeline.py`)

Builds normalized Parquet from `trade_log.json`, then computes KPI metrics via DuckDB.

### DuckDB Pipeline Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/trade_log_duckdb_pipeline.py
```

### DuckDB Pipeline Outputs

- `out/execution/analytics/trade_log.parquet`
- `out/execution/analytics/luma_analytics.duckdb`
- `out/execution/analytics/investor_kpi_duckdb.json`
- `out/execution/analytics/investor_kpi_duckdb.md`

---

## 4) Harmonic vs Backprop proof-pack (`harmonic_backprop_proofpack.py`)

Runs an apples-to-apples benchmark on any local CSV, then emits a hash-verifiable proof pack and appends a chain entry to the frozen ledger.

### Harmonic Proof-Pack Run

```powershell
c:/LumaTrader/venv3.11/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/harmonic_backprop_proofpack.py --input-csv c:/LumaTrader/clean_data/alpaca_spy.csv
```

VS Code task label: `Run harmonic backprop proof-pack`

### Harmonic Proof-Pack Outputs

- `out/execution/harmonic_backprop_proofpack/<run_id>/cleaned_input.csv`
- `out/execution/harmonic_backprop_proofpack/<run_id>/holdout_predictions.csv`
- `out/execution/harmonic_backprop_proofpack/<run_id>/metrics.csv`
- `out/execution/harmonic_backprop_proofpack/<run_id>/summary.json`
- `out/execution/harmonic_backprop_proofpack/<run_id>/manifest.sha256.json`
- `out/execution/harmonic_backprop_proofpack/latest.json` (pointer to most recent run for dashboards)
- `out/frozen_delta_ledger.jsonl` (new entry appended with `entry_sha256`)
