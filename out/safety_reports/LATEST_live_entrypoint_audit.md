# LumenCore Raw Live Entrypoint Audit

- Generated UTC: `2026-06-16T01:20:31.207426+00:00`
- Repo root: `C:\LumenCore_GitHub\lumen-core-public`

## Summary

- `files_with_raw_live_references`: `29`
- `files_with_safe_references`: `11`
- `total_files_with_hits`: `35`

## Meaning

- Raw live references are not automatically unsafe, but they must route through safe_live_executor/order_safety_gate before any live order path is trusted.
- Patch 5 only audits and creates a safe launcher; it does not rewrite every legacy script yet.
- No broker orders are submitted by this audit.

## Files With Hits

### `CHANGELOG.md`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 20 | YES | NO | `- **Live executor duplicate-child false positive** — Rewrote `_is_duplicate_child_executor()` in `live_executor.py`. Old PID-recycling edge case caused executor to self-block on launch. New logic uses env-marker + parent-PID + commandline triple-check.` |
| 22 | YES | NO | `- **Stale env var on executor relaunch** — `RUN_LIVE_COMPOUNDING_STACK.ps1` now clears `LUMA_LIVE_EXECUTOR_ROOT_PID` before each executor spawn.` |

### `execution_approval_queue.bak.json`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 95130 | YES | NO | `    "decision_reason": "approval_autofire_daemon",` |

### `reset_and_launch_all_engines.ps1`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 20 | YES | NO | `    'code/execution/live_executor.py',` |
| 23 | YES | NO | `    'code/execution/order_router.py',` |

### `truth_orchestrator_status.json`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 66 | YES | NO | `      "script": "C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code\\execution\\RUN_EXECUTION.ps1",` |
| 71 | YES | NO | `      "stderr_tail": "  File \"C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code\\execution\\RUN_EXECUTION.ps1\", line 1\n    cd C:\\LumaTrader\\INSTITUTIONAL_STACK_V2\\code\\execution\n       ^\nSyntaxError: invalid syntax\n"` |

### `code/FULL_TRUTH_ORCHESTRATOR.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 700 | YES | NO | `        for p in sorted(exec_dir.glob("RUN_EXECUTION*"), key=lambda x: x.name.lower()):` |

### `code/launch_unified_trading.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 14 | YES | NO | `  # Live mode is rejected. Use execution/live_executor.py after readiness gates.` |

### `code/multi_exchange_paper_ticker.py`

- Raw live references: `6`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 20 | YES | NO | `from execution.order_router import OrderRouter, RouteIntent` |
| 1747 | YES | NO | `    order_router = OrderRouter()` |
| 2018 | YES | NO | `        order_template = order_router.build_primary(route_intent, validate_only=True)` |
| 2019 | YES | NO | `        close_template = order_router.build_close_template(route_intent)` |
| 2472 | YES | NO | `        order_template = order_router.build_primary(route_intent, validate_only=True)` |
| 2473 | YES | NO | `        close_template = order_router.build_close_template(route_intent)` |

### `code/run_vps_growth_pipeline.py`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 14 | YES | NO | `CONTROLLER_SCRIPT = EXEC / "kraken_live_growth_controller.py"` |
| 87 | YES | NO | `    run_step(build_controller_cmd(args), "kraken_live_growth_controller")` |

### `code/unified_trade_executor.py`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 27 | YES | NO | `     Not implemented. Use execution/live_executor.py for real orders.` |
| 581 | YES | NO | `            "code/execution/live_executor.py after production readiness gates pass."` |

### `docs/PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 25 | YES | NO | `ticker, and symbol-awareness services. The large `live_executor.py` and` |

### `out/safety_reports/LATEST_safe_live_executor_smoke.json`

- Raw live references: `0`
- Safe references: `2`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 13 | NO | YES | `      "source": "safe_live_executor_smoke",` |
| 33 | NO | YES | `    "source": "safe_live_executor_smoke",` |

### `out/safety_reports/LATEST_safe_live_executor_smoke.md`

- Raw live references: `0`
- Safe references: `1`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 36 | NO | YES | `    "source": "safe_live_executor_smoke",` |

### `code/execution/approval_autofire_daemon.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 22 | YES | NO | `LOCK_FILE = OUT_EXEC / "approval_autofire_daemon.lock"` |

### `code/execution/audit_live_entrypoints.py`

- Raw live references: `8`
- Safe references: `4`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 14 | YES | NO | `    r"RUN_LIVE_COMPOUNDING_STACK",` |
| 15 | YES | NO | `    r"SUPERVISE_LIVE_COMPOUNDING_STACK",` |
| 16 | YES | NO | `    r"RUN_EXECUTION",` |
| 17 | YES | NO | `    r"LAUNCH_EVERYTHING",` |
| 18 | YES | NO | `    r"ARM_REAL_AUTOPILOT",` |
| 19 | YES | NO | `    r"approval_autofire_daemon",` |
| 20 | YES | NO | `    r"kraken_live_growth_controller",` |
| 21 | YES | NO | `    r"order_router",` |
| 25 | NO | YES | `    r"safe_live_executor",` |
| 26 | NO | YES | `    r"order_safety_gate",` |
| 27 | NO | YES | `    r"live_data_no_orders_gate",` |
| 102 | NO | YES | `            "Raw live references are not automatically unsafe, but they must route through safe_live_executor/order_safety_gate before any live order path is trusted.",` |

### `code/execution/kraken_live_growth_controller.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 283 | YES | NO | `        "schema": "kraken_live_growth_controller_v1",` |

### `code/execution/live_data_no_orders_gate.py`

- Raw live references: `0`
- Safe references: `4`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 232 | NO | YES | `    json_path = out_dir / f"live_data_no_orders_gate_{stamp}.json"` |
| 233 | NO | YES | `    latest_json = out_dir / "LATEST_live_data_no_orders_gate.json"` |
| 234 | NO | YES | `    md_path = out_dir / "LATEST_live_data_no_orders_gate.md"` |
| 304 | NO | YES | `    print(f"LIVE_DATA_NO_ORDERS_GATE={report['stage_status']}")` |

### `code/execution/live_executor.py`

- Raw live references: `7`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 28 | YES | NO | `from order_router import OrderRouter, RouteIntent` |
| 259 | YES | NO | `    # is actually still running live_executor.py (guards against PID recycling / stale markers).` |
| 279 | YES | NO | `        # Verify the parent is actually live_executor.py and not a recycled PID.` |
| 281 | YES | NO | `        if "code/execution/live_executor.py" in root_cmd:` |
| 1183 | YES | NO | `        self.order_router = OrderRouter()` |
| 8906 | YES | NO | `        order_template = self.order_router.build_primary(route_intent, validate_only=False)` |
| 8907 | YES | NO | `        close_template = self.order_router.build_close_template(route_intent)` |

### `code/execution/order_router.py`

- Raw live references: `2`
- Safe references: `3`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 7 | NO | YES | `Every order intent must pass order_safety_gate before any downstream executor` |
| 19 | NO | YES | `    from order_safety_gate import OrderIntent, decide_order_permission` |
| 21 | NO | YES | `    from .order_safety_gate import OrderIntent, decide_order_permission` |
| 50 | YES | NO | `        source=str(order.get("source") or "order_router"),` |
| 147 | YES | NO | `        "source": "order_router_smoke",` |

### `code/execution/order_safety_gate.py`

- Raw live references: `0`
- Safe references: `4`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 11 | NO | YES | `    from live_data_no_orders_gate import evaluate as evaluate_live_stage` |
| 13 | NO | YES | `    from .live_data_no_orders_gate import evaluate as evaluate_live_stage` |
| 152 | NO | YES | `    ledger = out_dir / "order_safety_gate_ledger.jsonl"` |
| 234 | NO | YES | `        source="order_safety_gate_smoke",` |

### `code/execution/RUN_LIVE_COMPOUNDING_STACK.ps1`

- Raw live references: `6`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 29 | YES | NO | `$daemonScript = Join-Path $execDir "approval_autofire_daemon.py"` |
| 38 | YES | NO | `$executorScript = Join-Path $execDir "live_executor.py"` |
| 74 | YES | NO | `    $running = Get-ProcsByPattern "*approval_autofire_daemon.py*" \| Select-Object -First 1` |
| 85 | YES | NO | `        $running = Get-ProcsByPattern "*approval_autofire_daemon.py*" \| Select-Object -First 1` |
| 96 | YES | NO | `    $running = Get-ProcsByPattern "*live_executor.py*" \| Select-Object -First 1` |
| 115 | YES | NO | `        $running = Get-ProcsByPattern "*live_executor.py*" \| Select-Object -First 1` |

### `code/execution/RUN_LIVE_DATA_NO_ORDERS_GATE.ps1`

- Raw live references: `0`
- Safe references: `3`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 15 | NO | YES | `    py -3 .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot` |
| 17 | NO | YES | `    python .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot` |
| 21 | NO | YES | `Write-Host "$RepoRoot\out\safety_reports\LATEST_live_data_no_orders_gate.md" -ForegroundColor Green` |

### `code/execution/RUN_LIVE_STACK_SAFE_NO_ORDERS.ps1`

- Raw live references: `2`
- Safe references: `6`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 15 | NO | YES | `    py -3 .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot` |
| 17 | NO | YES | `    python .\code\execution\live_data_no_orders_gate.py --stage live-data-no-orders --root $RepoRoot` |
| 22 | YES | YES | `    py -3 .\code\execution\safe_live_executor.py` |
| 24 | YES | YES | `    python .\code\execution\safe_live_executor.py` |
| 36 | NO | YES | `Write-Host "$RepoRoot\out\safety_reports\LATEST_live_data_no_orders_gate.md" -ForegroundColor Green` |
| 37 | NO | YES | `Write-Host "$RepoRoot\out\safety_reports\LATEST_safe_live_executor_smoke.md" -ForegroundColor Green` |

### `code/execution/RUN_ORDER_ROUTER_SAFETY_SMOKE.ps1`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 13 | YES | NO | `    py -3 .\code\execution\order_router.py` |
| 15 | YES | NO | `    python .\code\execution\order_router.py` |

### `code/execution/RUN_ORDER_SAFETY_GATE_SMOKE.ps1`

- Raw live references: `0`
- Safe references: `3`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 13 | NO | YES | `    py -3 .\code\execution\order_safety_gate.py` |
| 15 | NO | YES | `    python .\code\execution\order_safety_gate.py` |
| 19 | NO | YES | `Write-Host "$RepoRoot\out\safety_reports\order_safety_gate_ledger.jsonl" -ForegroundColor Green` |

### `code/execution/RUN_SAFE_LIVE_EXECUTOR_SMOKE.ps1`

- Raw live references: `2`
- Safe references: `3`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 13 | YES | YES | `    py -3 .\code\execution\safe_live_executor.py` |
| 15 | YES | YES | `    python .\code\execution\safe_live_executor.py` |
| 19 | NO | YES | `Write-Host "$RepoRoot\out\safety_reports\LATEST_safe_live_executor_smoke.md" -ForegroundColor Green` |

### `code/execution/safe_live_executor.py`

- Raw live references: `1`
- Safe references: `7`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 7 | YES | NO | `- Provide one safe entry point before anything reaches live_executor.py.` |
| 10 | NO | YES | `  central order_safety_gate approves the intent.` |
| 24 | NO | YES | `    from order_safety_gate import OrderIntent, decide_order_permission` |
| 26 | NO | YES | `    from .order_safety_gate import OrderIntent, decide_order_permission` |
| 114 | NO | YES | `        source=str(order.get("source") or "safe_live_executor"),` |
| 190 | NO | YES | `    json_path = out_dir / "LATEST_safe_live_executor_smoke.json"` |
| 191 | NO | YES | `    md_path = out_dir / "LATEST_safe_live_executor_smoke.md"` |
| 227 | NO | YES | `        "source": "safe_live_executor_smoke",` |

### `code/execution/SUPERVISE_LIVE_COMPOUNDING_STACK.ps1`

- Raw live references: `3`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 13 | YES | NO | `$launcher = Join-Path $execDir "RUN_LIVE_COMPOUNDING_STACK.ps1"` |
| 128 | YES | NO | `        $daemonCount = Get-ProcessCount "*approval_autofire_daemon.py*"` |
| 129 | YES | NO | `        $executorCount = Get-ProcessCount "*live_executor.py*"` |

### `code/execution/universe_audit_runner.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 41 | YES | NO | `    "order_router",` |

### `code/ops/ANALYZE_TRADER_BLEED.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 210 | YES | NO | `            "fix": "Add per-pair stop-loss and a daily loss cutoff in live_executor.py.",` |

### `code/ops/build_enterprise_value_hardening_pack.py`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 176 | YES | NO | `            "execution": "python INSTITUTIONAL_STACK_V2/code/execution/kraken_live_growth_controller.py --cached --controller Robert",` |

### `code/ops/BUILD_GRANT_KRAKEN_ACTION_BRIEF.py`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 173 | YES | NO | `                "command": "python code/execution/kraken_live_growth_controller.py --cached --controller Robert",` |
| 204 | YES | NO | `                "command": "python code/execution/kraken_live_growth_controller.py --cached --controller Robert",` |

### `code/ops/BUILD_UNIVERSE_INDEX_PACK.ps1`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 165 | YES | NO | `            $isExec = ($scriptExt -contains $ext) -and ($lp -match "execution_orchestrator\|live_executor\|order_router\|liquidity_guard\|risk_kernel\|rl_policy\|signal_gate\|rolling_capital\|harmonic_signal_connector\|runtime_control")` |

### `code/ops/RUN_BOOTH_WARROOM_REFRESH.ps1`

- Raw live references: `1`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 18 | YES | NO | `$autopilotScript = Join-Path $stackRoot 'ARM_REAL_AUTOPILOT.ps1'` |

### `code/ops/RUN_GRANT_DASHBOARD_AUTO_REFRESH.ps1`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 43 | YES | NO | `$growthController = Join-Path $stackRoot 'code\execution\kraken_live_growth_controller.py'` |
| 152 | YES | NO | `                throw "kraken_live_growth_controller failed with exit code $LASTEXITCODE"` |

### `code/ops/STACK_RUNTIME_MANAGER.ps1`

- Raw live references: `2`
- Safe references: `0`

| Line | Raw | Safe | Text |
|---:|---|---|---|
| 189 | YES | NO | `        Arguments = @('live_executor.py')` |
| 190 | YES | NO | `        MatchNeedle = 'live_executor.py'` |
