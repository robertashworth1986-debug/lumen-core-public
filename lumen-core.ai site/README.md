# lumen-core.ai Pipeline

Builds a web-ready status/data bundle from your institutional stack artifacts.

## What this pipeline does
- Reads runtime, execution, portfolio, trade, and audit artifacts from:
  - `config/runtime_control.json`
  - `out/execution_runtime.json`
  - `out/execution/adaptive_profile_state.json`
  - `out/execution/portfolio_summary.json`
  - `out/execution/trade_log.json`
  - `out/execution/execution_audit_chain.jsonl`
- Generates a deployable site bundle under:
  - `lumen-core.ai site/public/`
- Emits clean JSON endpoints and a live status dashboard page.

## Output structure
- `public/index.html`
- `public/data/health.json`
- `public/data/runtime.json`
- `public/data/profile.json`
- `public/data/portfolio.json`
- `public/data/trades_recent.json`
- `public/data/audit_recent.json`
- `public/data/build_info.json`

## Quick start (PowerShell)
```powershell
Set-Location "c:\LumaTrader\INSTITUTIONAL_STACK_V2\lumen-core.ai site"
python .\pipeline\build_site_bundle.py
python .\pipeline\smoke_test.py
```

## One-command run
```powershell
Set-Location "c:\LumaTrader\INSTITUTIONAL_STACK_V2\lumen-core.ai site"
.\pipeline\run_pipeline.ps1
```

## Deploy handoff
- Upload everything inside `lumen-core.ai site/public/` to your host/CDN for `lumen-core.ai`.
- Re-run the pipeline whenever new execution artifacts are produced.

## Notes
- The pipeline uses Python standard library only (no extra packages required).
- It is resilient to missing files and will still generate a valid site with fallback values.
