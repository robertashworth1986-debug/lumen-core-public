# Execution Optimization Tools

This folder now includes two utility scripts for improving net profitability and investor reporting.

## 1) Runtime threshold optimizer (`runtime_optimizer_optuna.py`)

Optimizes a key entry-quality threshold (`min_gate_score_for_entry`) using `optuna` and historical closed trades.

### Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/runtime_optimizer_optuna.py --trials 120 --min-kept 5
```

### Output

- `out/execution/runtime_optimizer_recommendation.json`

---

## 2) Investor performance report (`investor_performance_report.py`)

Builds investor-facing metrics from `trade_log.json`, including Sharpe/Sortino/Calmar/max drawdown and fee drag.

### Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/investor_performance_report.py
```

### Outputs

- `out/execution/investor_performance_report.json`
- `out/execution/investor_performance_report.md`

---

## 3) DuckDB + Parquet investor pipeline (`trade_log_duckdb_pipeline.py`)

Builds normalized Parquet from `trade_log.json`, then computes KPI metrics via DuckDB.

### Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/trade_log_duckdb_pipeline.py
```

### Outputs

- `out/execution/analytics/trade_log.parquet`
- `out/execution/analytics/luma_analytics.duckdb`
- `out/execution/analytics/investor_kpi_duckdb.json`
- `out/execution/analytics/investor_kpi_duckdb.md`
