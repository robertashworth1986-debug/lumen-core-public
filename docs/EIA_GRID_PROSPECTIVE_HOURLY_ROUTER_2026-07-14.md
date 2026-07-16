# EIA Grid Prospective Hourly Router

## Frozen Design

- Protocol: `config/eia_grid_prospective_hourly_router_protocol_v1.json`
- Protocol SHA256: `5398f17f57e02bdaadb1cef5b6dae20708146eaa0de534ebbe6ce36ab28952e5`
- Historical design receipt: `evidence/external_validation/eia_grid_hourly_router_design_benchmark_20260714.json`
- Historical design SHA256: `19698f1923f3fea9d0f2c4c3fef1088ee131163ed246f8aaa69894af9ddb06c9`
- Source rows: `86244`
- Training rows: `25151`
- Validation rows: `7549`
- First allowed UTC hour ending: `2026-07-15T14`
- Backfills: `false`
- Dynamic route overrides: `false`

## Frozen Authority Routes

| Authority | Candidate |
|---|---|
| CISO | xgboost_residual |
| ERCO | eia_official |
| ISNE | lightgbm_residual |
| MISO | lightgbm_residual |
| NYIS | xgboost_residual |
| PJM | lightgbm_residual |
| SWPP | ridge_residual |
| TVA | xgboost_residual |

## Scientific Boundary

The historical window selected the routes and is exploratory. Only targets sealed after the protocol freeze, before each interval starts, and before target actual demand appears can contribute prospective evidence.

A passing result would support bounded prospective public-data evidence for a frozen hourly specialist router. It does not establish patent validity or scope, utility control, realized savings, grid reliability improvement, production readiness, trading edge, or universal model superiority.

## Dated Public Snapshot

The public-safe runtime projection is [`eia_grid_prospective_hourly_runtime_projection_20260716.json`](../evidence/external_validation/eia_grid_prospective_hourly_runtime_projection_20260716.json). Its dated snapshot records 95 sealed predictions, 72 settlements, 0 common settled hours, and closed preliminary, confirmatory, durability, and promotion gates. The raw runtime ledgers remain outside the public repository; the projection preserves their hashes and terminal-chain receipts.

These incomplete-sample descriptive values do not support Level 4, external generalization, field performance, reliability, savings, production, or trading claims.

## Operations

- Core: `code/eia_grid_prospective_hourly_router.py`
- One-cycle wrapper: `tools/Run-EiaProspectiveHourlyRouterCycle.ps1`
- Scheduler registration: `tools/Register-EiaProspectiveHourlyRouterTask.ps1`
- Prediction ledger: `out/eia_grid_prospective_hourly_router/sealed_predictions.jsonl`
- Settlement ledger: `out/eia_grid_prospective_hourly_router/settlements.jsonl`
- Operational receipt chain: `out/eia_grid_prospective_hourly_router/operational_runs.jsonl`
- Status: `out/eia_grid_prospective_hourly_router/prospective_status_latest.json`

The runtime source cache and ledgers are operational artifacts, not repository fixtures. Each chain fails closed on a broken prior hash or record hash, and no credential is serialized.

## Publisher Sources

- [EIA Form EIA-930 hourly API dashboard](https://www.eia.gov/opendata/browser/electricity/rto/region-data)
- [EIA Open Data API documentation](https://www.eia.gov/opendata/documentation.php)

## Verification

```powershell
python code/ops/FREEZE_EIA_HOURLY_ROUTER_DESIGN.py --check
python code/ops/BUILD_EIA_HOURLY_RUNTIME_PROJECTION.py --check
python -m pytest -q tests/test_eia_grid_prospective_hourly_router.py tests/test_eia_prospective_source_timing_audit.py
powershell -NoProfile -ExecutionPolicy Bypass -File tools/Run-EiaProspectiveHourlyRouterCycle.ps1 -DryRun
```

Machine-readable freeze receipt: `evidence/external_validation/eia_grid_hourly_router_design_freeze_20260714.json`
