# Cross-Sector Intelligence Pipeline

This pipeline freezes high-integrity cross-sector drift/failure deltas and writes grant-ready audit artifacts.

## What it does

- Captures immutable delta records in `out/infra_frozen_deltas.jsonl`
- Writes failure predictions to `out/cross_sector_failure_predictions.jsonl`
- Appends an audit event to `out/infra_audit_ledger.jsonl`
- Produces summary evidence in `out/investor_and_grant_evidence.json`
- Updates chain-of-custody hashes in `out/infra_chain_of_custody_sha256.json`

## Run

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/run_cross_sector_intel.py
```

## Build federal brief

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/run_federal_brief.py
```

Outputs:

- `out/federal_brief.json`
- `out/federal_brief.md`

## Optimization artifacts

Each cross-sector run now emits bounded optimization simulation artifacts:

- `out/cross_sector_optimization_report.json`
- `out/cross_sector_optimization_matrix.csv`
- `out/cross_sector_optimization_report.md`

## Run 24/7 federal brief daemon

```powershell
pwsh -NoProfile -ExecutionPolicy Bypass -File c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/RUN_FEDERAL_BRIEF_247.ps1
```

Daemon outputs:

- `out/federal_brief_run_ledger.jsonl`
- `out/federal_brief_daemon_heartbeat.json`

## Build Nobel-tier dashboard and deck pack

```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe c:/LumaTrader/INSTITUTIONAL_STACK_V2/code/execution/run_nobel_tier_assets.py
```

Generated outputs:

- `dashboard/nobel_tier_command_center.html`
- `out/INSTITUTIONAL_REVIEW_BUNDLE/nobel_tier_slides.json`
- `out/INSTITUTIONAL_REVIEW_BUNDLE/nobel_tier_powerpoint_slides.md`
- `out/INSTITUTIONAL_REVIEW_BUNDLE/nobel_tier_executive_summary.json`

## Runtime configuration

Optional runtime config:

- `config/cross_sector_intel_runtime.json`

Supported keys:

- `lumen_detection_efficiency` (default `0.72`)
- `mitigation_multiplier` (default `0.86`)
- `trust_tier` (default `gov_audit_ready`)
- `program_alignment` (default `DARPA/DOE/DOD/NSF/NASA`)
