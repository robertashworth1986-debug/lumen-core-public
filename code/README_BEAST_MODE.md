# LUMENCORE Beast Mode (Super Sniper)

`beast_mode.py` is a **runtime control tuner** for aggressive, high-cadence candidate hunting with auditable delta-freeze outputs.

It does **not place orders or arm live mode**. It can apply paper-safe tuning to `config/runtime_control.json`; the existing orchestrator enforces execution and risk controls.

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
- Legacy live-arm settings are retained only as diagnostic inputs.
- A strict-live runtime is immutable to this tuner so its hash-bound authority cannot be invalidated.

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

## Live boundary
`beast_mode.py` cannot transition a runtime to live. Live execution belongs to the canonical action-time authority path, which requires a fresh hash-bound human receipt and execution-layer validation. If the current runtime is already strict-live, this tuner writes its analysis artifacts but leaves that runtime file unchanged.

## Notes
- A backup of runtime config is saved automatically on apply.
- `futures_mode` stays disabled by default in super sniper config.
- Use paper mode to evaluate candidate quality; this tuner is not a live-arming tool.
