# LUMENCORE Lightning Supervisor

`lightning.py` adds a second hardening layer on top of `beast_mode.py` with **10 extra robustness upgrades** focused on safety, constraint tagging, and remediation.

## Files
- Policy: `config/lightning_guardrails.json`
- Engine: `code/lightning.py`
- Smoke: `code/lightning_smoke.py`
- Outputs:
  - `out/execution/lightning_frozen_delta.json`
  - `out/execution/lightning_remediation.json`

## 10 Upgrades Included
1. Volatility circuit breaker
2. Latency drift guard (p95/p99 thresholds)
3. Stability guard (error rate + order success)
4. Sector concentration cap framework
5. Slippage guard framework
6. Data freshness guard
7. Capital preservation floor
8. Adaptive cadence controller
9. Shadow simulation hook
10. Auto-remediation playbook (when/where/why/what/fix)

## Run
### 1) Dry run (safe)
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/lightning.py
```

### 2) Apply patch
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/lightning.py --apply
```

### 3) Validate outputs
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/lightning_smoke.py
```

## Safety Notes
- No guaranteed returns; performance is market-dependent.
- `lightning` defaults to paper unless explicit live arming guards pass.
- It writes frozen delta and remediation guidance for audit-grade traceability.

## Suggested sequence
1. Run `beast_mode.py --apply`
2. Run `lightning.py --apply`
3. Start execution orchestrator in paper mode
4. Review constraints/remediation outputs before any live arming
