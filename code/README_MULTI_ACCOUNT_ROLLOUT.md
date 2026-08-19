# Multi-Account Universe Rollout

This layer discovers locally configured account records from `config/luma_live_keys.env`, maps the full universe into each account (paper-executable + shadow), and emits masked, paper-only deployment plans.

## Important
- It can write paper-only runtime plans for existing configured accounts.
- It does **not** auto-create brokerage/exchange accounts (KYC/compliance requirement).
- It never writes raw credentials into its registry or output plans.

## Files
- Policy: `config/multi_account_policy.json`
- Engine: `code/multi_account_universe_rollout.py`
- Smoke: `code/multi_account_rollout_smoke.py`
- Outputs:
  - `config/live_account_registry.json`
  - `out/execution/multi_account_rollout_plan.json`
  - `out/execution/multi_account_constraint_tags.json`
  - `out/execution/multi_account_remediation.json`

## Run
### Dry-run planning
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/multi_account_universe_rollout.py
```

### Apply per-account runtime configs
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/multi_account_universe_rollout.py --apply
```

### Record a blocked legacy live request
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/multi_account_universe_rollout.py --apply --arm-live
```

### Validate outputs
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/multi_account_rollout_smoke.py
```

## Live boundary
`--arm-live` is retained for backward-compatible diagnostics, but it records a blocked constraint and all generated account runtimes remain paper-only. Multi-account live authorization must not be inferred from local key presence, an environment variable, or a confirmation file.

## Strategy mapping model
- `KRAKEN` accounts execute crypto symbols and shadow equities.
- `ALPACA` accounts execute equities and shadow crypto.
- Unsupported assets become shadow universe for ongoing evolutionary scoring.
