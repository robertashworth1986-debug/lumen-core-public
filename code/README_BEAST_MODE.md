# LUMENCORE Beast Mode (Super Sniper)

`beast_mode.py` is a **runtime control tuner** for aggressive, high-cadence candidate hunting with auditable delta-freeze outputs.

It does **not place orders directly**. It updates `config/runtime_control.json` and the existing orchestrator enforces execution + risk controls.

## Files
- Config: `config/super_sniper.json`
- Runtime target: `config/runtime_control.json`
- Engine: `code/beast_mode.py`
- Smoke test: `code/beast_mode_smoke.py`
- Outputs:
  - `out/execution/super_sniper_decision.json`
  - `out/execution/frozen_deltas_super_sniper.json`

## Features
- Sharp-triggered candidate activation (`sharp_trigger` default `2.0`)
- Lineage-based winner selection from `trade_log.json`
- Capital boost policy (`target_multiplier` default `10x`)
- Cadence/pyramiding burst tuning
- Delta freeze + checksum audit output
- Live-arming guardrails:
  - env var gate
  - manual confirm file phrase
  - explicit `allow_live_switch`

## Run
### 1) Dry run (safe, default)
```powershell
python code/beast_mode.py
```

### 2) Apply runtime changes
```powershell
python code/beast_mode.py --apply
```

### 3) Smoke verify outputs
```powershell
python code/beast_mode_smoke.py
```

## Live arming (explicit only)
By default, config keeps live disabled:
- `live_arming.allow_live_switch = false`
- runtime is forced to paper mode.

To arm live intentionally, all must pass:
1. Set `allow_live_switch` to `true` in `config/super_sniper.json`
2. Create `config/live_arm.confirm` containing `ARM_LIVE_SUPER_SNIPER`
3. Set environment variable:
```powershell
$env:LUMENCORE_ARM_LIVE = "YES_I_ACCEPT_REAL_CAPITAL_RISK"
```
4. Run apply:
```powershell
python code/beast_mode.py --apply
```

## Notes
- A backup of runtime config is saved automatically on apply.
- `futures_mode` stays disabled by default in super sniper config.
- Use paper mode to validate candidate quality before live arming.
