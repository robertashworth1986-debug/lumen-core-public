# Execution Optimization Tools

This folder contains research and offline reporting utilities. Their presence or
successful execution does not establish profitability or investment readiness.

## 1) Runtime threshold optimizer (`runtime_optimizer_optuna.py`)

Optimizes a key entry-quality threshold (`min_gate_score_for_entry`) using `optuna` and historical closed trades.

### Runtime Optimizer Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/runtime_optimizer_optuna.py --trials 120 --min-kept 5
```

### Runtime Optimizer Output

- `out/execution/runtime_optimizer_recommendation.json`

---

## 2) Reported trade diagnostics (`investor_performance_report.py`)

The existing filename now emits `lumencore.reported_trade_diagnostics.v2`.
It reads one byte-bound, SHA-256-identified JSON snapshot, reports record and
field coverage, and computes descriptive arithmetic only when every included
record supplies a complete compatible basis. It never promotes a sample to
institutional quality based on its row count.

Input is at most 16 MiB and 100,000 objects. Duplicate JSON keys and non-finite
JSON numbers are rejected. Closed records require an explicit `CLOSED` status;
duplicate IDs/content, unknown statuses, or missing/mixed mode hold aggregates.
USD aggregates additionally require `currency: USD` on every closed record.
Amounts must be finite, at most 1e15 in absolute value, and have at most 12
decimal places. JSON decimals retain their decimal representation before
aggregation; monetary totals are exact decimal strings, not binary floats.
Both identity aliases must agree when present. Conflicting aliases or incomplete coverage hold the whole
affected metric. Labels and arithmetic are not source authentication.

Sharpe, Sortino, Calmar, equity, drawdown, portfolio percentage return and
unique executed-trade counts remain JSON `null`. Trade-event rows do not
supply initial equity, external cash flows, regular return intervals, or
broker reconciliation. The old 100,000 USD starting-capital fallback and
252/365-per-trade annualization are removed. The dashboard entry point reuses
this report and displays reported PnL per record, with no fabricated equity.
Loaded source rows retain their original missing-field distinctions; changing
the display frame requires reloading the source before reusing its receipt.
The plot is optional; exact supplied fields remain in the record table.

Compatibility: old consumers must honor the new schema and nulls, rather than
coercing unknowns to zero. The legacy institutional scorecard now explicitly
holds investment-readiness promotion and leaves its account KPIs unknown.
Malformed object shapes are recorded as holds. Enabled status requires an
actual boolean, declared row presence is separate from validated measurement,
and non-finite numbers cannot escape into its JSON output. Legacy opportunity
declarations are retained separately without becoming realized dollar effects.
Other archived/legacy analytics, including the DuckDB pipeline below, are not
upgraded or validated by this correction. Historical generated outputs remain
unchanged and must not be treated as current v2 diagnostics.

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
