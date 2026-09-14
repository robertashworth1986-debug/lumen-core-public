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

### Offline daily record report (`../institutional_daily_report.py`)

The September 14 correction retires the implicit credential/network/shared-file
refresh. A synthetic legacy probe with all readers replaced produced $100,000
starting capital, -$100,000 PnL, zero win rate, and -101% versus a one-day SPY
input from an empty account fixture. A future-dated record also counted in its
recent window. Those were report arithmetic defects, not account observations.

The replacement requires one explicit local JSON snapshot and a **new output
directory whose parent already exists**:

```powershell
python code/institutional_daily_report.py --snapshot review-input.json --output-dir review-result
```

Input contract (these values are a synthetic example):

```json
{
  "schema": "lumencore.daily_report_input.v1",
  "as_of_utc": "2026-09-14T08:00:00Z",
  "declared_mode": "synthetic",
  "declared_currency": "USD",
  "status": {},
  "state": {},
  "evidence": {},
  "ledger": []
}
```

The strict reader captures at most 16 MiB once, hashes those bytes, rejects
duplicate JSON members/non-finite literals, and requires at most 100,000 object
records. It does not authenticate the source, prove chronology/completeness or
make the file immutable. The supplied aware timestamp fixes the inclusive
60-minute window. Timestamps must use extended ISO form with seconds, an explicit
offset/Z, and at most six fractional digits; finer precision is rejected rather
than silently rounded into the window. Future, naive, invalid and older records have explicit counts.
Counts describe submitted records, never unique trades or actual executions.

Account, risk, performance, execution-flow and benchmark KPIs remain null.
Numeric declarations are kept separately as exact decimal strings, with no
fallback between sources; a real zero stays zero. Investment readiness, broker
reconciliation and live authority remain false. Optional recent-record notional
arithmetic requires complete nonnegative amounts, consistent declared mode/USD,
and no missing, conflicting or duplicate identities or invalid/future times.
This is not volume verification or account performance. Identity aliases
`event_id`, `id` and `trade_id`, when present together, must agree exactly.

Outputs are the existing report JSON, a diagnostic-only CSV, and a two-file hash
manifest inside the selected new directory. Validation/serialization precedes
directory creation, and existing directories/files are never overwritten.
An I/O failure during writing can leave a partial directory; a manifest is not
a transactional-publication or decompression/CPU-sandbox guarantee.

The old no-argument CLI exits 2. The canonical paper facade's implicit report and
evidence-pack subprocess paths are held without launches or repeated retries;
prior successful-refresh timestamps are retained and no success is claimed.
The facade binds this hold into the preserved loop, as it already binds the
exact-origin guards. Historical executor bytes and their order-safety policy
digest remain unchanged. Direct execution of the historical file is outside
this canonical facade correction and is not an approved invocation route.
The manual packager has the separate explicit-capture contract below.
`alpaca_paper_loop_builder.py` and historical shared reports remain legacy
paths requiring separate review. No original account, credentials, ledgers,
scheduled processes or execution controls were accessed or changed for these
synthetic tests. Caller tests execute an AST-isolated function with inert fakes.

### Explicit offline evidence pack

`code/build_investor_evidence_pack.py` no longer chooses runtime/account files,
creates a directory on import, or runs with no arguments. Provide an existing
plain source directory, a UTF-8 JSON list of 1 to 128 relative file paths, and a
new output directory under an existing plain parent. Example selection:

```json
["protocol.json", "results/report.json"]
```

```powershell
python code/build_investor_evidence_pack.py --source-root C:/review/captured --artifacts-json C:/review/selection.json --output-dir C:/review/new-pack
```

Every selected file must exist. Limits are 64 KiB for the selection, 16 MiB per
source and 64 MiB total source bytes. Observed links/reparse points, nonregular
files, traversal/drive paths, case collisions, reserved Windows names and path
components starting with spreadsheet-formula characters are rejected. Files are
captured once; the ledger, source hashes and ZIP use those same buffers. Observed
file identity/size/mtime changes during capture cause a hold. This is per-file
capture, not an atomic multi-file snapshot or exclusion of concurrent writers.

The new directory contains `artifact_hash_manifest.json`,
`artifact_hash_ledger.csv` and `institutional_evidence_pack.zip`; sources live
under `sources/` in the ZIP. The v2 manifest declares its exact self-hash rule.
The CLI receipt separately gives the SHA-256 of the final manifest bytes and
final archive bytes. Older v1 readers must not assume compatibility. All account
and performance fields are null, with `NOT_EVALUATED`, no broker reconciliation,
no investment readiness and no execution authority. Source contents are retained
as evidence bytes, not interpreted or certified. Review distribution rights and
contained claims before sharing; this tool does not redact source files.

Existing output is refused. Serialization occurs before creating output; a disk
error can still leave a partial new directory. Payload limits do not constitute
a hostile-filesystem, CPU or peak-memory sandbox. The elite optimizer's implicit
pack step remains HOLD, does not advertise old ZIPs, and now rejects failed
native steps. The original runtime was not activated for these corrections.

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
