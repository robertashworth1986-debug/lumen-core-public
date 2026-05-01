# LUMENCORE X1000 Control Plane

This layer adds deeper optimization and safe orchestration on top of:
- `beast_mode.py`
- `lightning.py`
- `optimizer_x1000.py`
- `micro_fractal_growth.py`
- `time_travel_burst_engine.py`

## Components
- `optimizer_x1000.py`: Monte Carlo parameter search with constraints and patch emission
- `micro_fractal_growth.py`: momentum-aware micro-cell fractal compounding patcher
- `time_travel_burst_engine.py`: replay burst windows to simulate "time-travel" micro regimes
- `x1000_control_plane.py`: One-command stage runner (beast -> lightning -> optimizer -> fractal -> burst)
- `optimizer_x1000_smoke.py`: Output contract validation

## Key Outputs
- `out/execution/optimizer_x1000_report.json`
- `out/execution/optimizer_x1000_simulation.json`
- `config/runtime_optimized_patch.json`
- `out/execution/micro_fractal_growth_report.json`
- `config/runtime_fractal_patch.json`
- `out/execution/time_travel_burst_report.json`
- `out/execution/time_travel_burst_history.json` (when adaptive mutation is enabled)
- `config/runtime_time_travel_patch.json`
- `out/execution/x1000_control_plane_summary.json`

## Run
### Dry-run full pipeline
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/x1000_control_plane.py
```

### Dry-run full pipeline with two-pass optimizer (recommended)
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/x1000_control_plane.py --passes 2
```

### Apply mode (still subject to safety guards)
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/x1000_control_plane.py --apply
```

### Validate outputs
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/optimizer_x1000_smoke.py
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/micro_fractal_growth_smoke.py
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/time_travel_burst_smoke.py
```

### Run repeated evolutionary cycles (2 passes per cycle)
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/evolutionary_loop.py --cycles 2 --passes 2 --interval-sec 1
```

### Validate loop artifacts
```powershell
c:/LumaTrader/INSTITUTIONAL_STACK_V2/.venv/Scripts/python.exe code/evolutionary_loop_smoke.py
```

## Safety
- No guaranteed returns; optimizer maximizes objective under risk constraints.
- Direct runtime patch apply from optimizer is disabled by default in `config/optimizer_x1000.json`.
- To allow direct optimizer apply, explicitly enable policy + env var arming.

## Two-pass optimization behavior
- Pass 1: broad search over full parameter bounds.
- Pass 2: guided refinement around pass-1 winner with tighter bounds.
- Winner selection: pass with the higher constrained objective score.
- Report fields: `passes`, `winner_pass`, `pass_improvement`.

## Adaptive burst mutation
- Controlled in `config/time_travel_bursts.json` under `adaptive_mutation`.
- If `enabled=true`, each burst run can mutate `burst.window_sizes`, `burst.stride`, and `burst.max_windows`.
- Mutation stays bounded by policy keys:
	- `window_size_bounds`
	- `stride_bounds`
	- `max_windows_bounds`
- Hysteresis controls reduce overreaction:
	- `cooldown_runs_after_expand`, `cooldown_runs_after_contract`
	- `max_consecutive_expand`, `max_consecutive_contract`
	- `min_runs_before_mutation`, `min_windows_for_expand`
- Volatility shock brake can temporarily freeze mutation:
	- Config section: `adaptive_mutation.volatility_shock_brake`
	- Triggered by elevated short-horizon volatility (`std_ratio_trigger`, `std_abs_trigger_pct`, `mean_abs_trigger_pct`)
	- Applies `hold` mode with reason `volatility_shock_brake` and enforces `cooldown_runs_after_shock`
	- Optional self-tuning via `adaptive_mutation.volatility_shock_brake.autotune`:
		- Relaxes thresholds after repeated false positives
		- Tightens thresholds after repeated missed shocks
		- Always clamped to configured bounds (`ratio_bounds`, `abs_std_bounds`, `abs_mean_bounds`)
- Mutation modes:
	- `expand`: increases search breadth after strong score/win-rate with acceptable drawdown.
	- `contract`: tightens windows when drawdown rises or win-rate weakens.
	- `hold`: no change when performance is neutral.
- Persistence controls:
	- `persist_policy_updates=true` writes updated values back to `config/time_travel_bursts.json`.
	- `mutation_history_file` appends per-run mutation records.
- Burst report adds `mutation_enabled`, `mutation_mode`, and `mutated_burst` fields.
- Burst report also adds `mutation_reason` and `mutation_state` for explainability.
- Burst report/history also include `shock_brake` diagnostics (`triggered`, `reason`, `std_ratio`, windows used).
- Burst report/history include `shock_autotune` diagnostics (`feedback`, `action`, `tuned`, active thresholds).
