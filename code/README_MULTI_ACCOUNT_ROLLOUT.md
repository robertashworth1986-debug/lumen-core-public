# Multi-Account Universe Rollout

This layer discovers all **key-backed execution accounts** from `config/luma_live_keys.env`, maps the full universe into each account (executable + shadow), and emits policy-gated deployment plans.

## Important
- It can deploy across existing key-backed accounts.
- It does **not** auto-create brokerage/exchange accounts (KYC/compliance requirement).

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

### Request live arming (still policy-gated)
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/multi_account_universe_rollout.py --apply --arm-live
```

### Validate outputs
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/multi_account_rollout_smoke.py
```

## Live gating
Even with `--arm-live`, live activation only occurs if policy guards pass:
1. `allow_live=true` in `config/multi_account_policy.json`
2. env var `LUMENCORE_ARM_MULTI_LIVE=YES_ARM_MULTI_ACCOUNT_LIVE`
3. file `config/multi_live_arm.confirm` contains `ARM_MULTI_ACCOUNT_LIVE`

## Strategy mapping model
- `KRAKEN` accounts execute crypto symbols and shadow equities.
- `ALPACA` accounts execute equities and shadow crypto.
- Unsupported assets become shadow universe for ongoing evolutionary scoring.
