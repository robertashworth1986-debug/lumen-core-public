import argparse
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"

RUNTIME_FILE = CONFIG / "runtime_control.json"
TRADE_LOG_FILE = OUT / "trade_log.json"
X1000_FILE = OUT / "optimizer_x1000_report.json"
FRACTAL_FILE = OUT / "micro_fractal_growth_report.json"
BURST_POLICY_FILE = CONFIG / "time_travel_bursts.json"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def atomic_write_json(path: Path, payload: Any, indent: int = 2) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=indent)
    os.replace(tmp, path)


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _extract_returns(trades: List[Dict[str, Any]]) -> List[float]:
    vals: List[float] = []
    for t in trades:
        if t.get("pnl_pct") is not None:
            vals.append(_f(t.get("pnl_pct"), 0.0))
        else:
            entry = _f(t.get("entry_price"), 0.0)
            exit_px = _f(t.get("exit_price"), entry)
            if entry > 0:
                vals.append(((exit_px - entry) / entry) * 100.0)
    return vals


def _stats(values: List[float]) -> Dict[str, float]:
    if not values:
        return {"mean": 0.0, "std": 0.0, "win_rate": 0.0, "sharpe": 0.0, "drawdown": 0.0}

    mean = sum(values) / len(values)
    wins = sum(1 for v in values if v > 0)
    win_rate = wins / len(values)
    if len(values) > 1:
        var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    else:
        var = 0.0
    std = math.sqrt(max(var, 0.0))
    sharpe = (mean / std) if std > 1e-9 else 0.0

    equity = 100.0
    peak = equity
    dd = 0.0
    for r in values:
        equity *= (1.0 + (r / 100.0))
        peak = max(peak, equity)
        if peak > 0:
            dd = max(dd, ((peak - equity) / peak) * 100.0)

    return {"mean": mean, "std": std, "win_rate": win_rate, "sharpe": sharpe, "drawdown": dd}


def _burst_windows(returns: List[float], window_sizes: List[int], stride: int, max_windows: int) -> List[List[float]]:
    out: List[List[float]] = []
    n = len(returns)
    stride = max(1, stride)

    for w in window_sizes:
        w = max(2, int(w))
        if n < w:
            continue
        for i in range(0, n - w + 1, stride):
            out.append(returns[i:i + w])
            if len(out) >= max_windows:
                return out
    return out


def _clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def _clamp_float(value: float, low: float, high: float) -> float:
    return max(low, min(high, float(value)))


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(max(var, 0.0))


def _volatility_shock_metrics(returns: List[float], cfg: Dict[str, Any]) -> Dict[str, Any]:
    recent_window = max(2, int(cfg.get("recent_window", 16) or 16))
    baseline_window = max(recent_window + 1, int(cfg.get("baseline_window", 80) or 80))
    min_recent_window = max(2, int(cfg.get("min_recent_window", 8) or 8))
    min_baseline_window = max(min_recent_window + 1, int(cfg.get("min_baseline_window", 24) or 24))

    recent = returns[-recent_window:] if len(returns) >= recent_window else returns[-min_recent_window:]
    baseline = returns[-baseline_window:] if len(returns) >= baseline_window else returns[-min_baseline_window:]

    recent_std = _std(recent)
    baseline_std = _std(baseline)
    ratio = (recent_std / baseline_std) if baseline_std > 1e-9 else 0.0
    recent_abs_mean = (sum(abs(x) for x in recent) / len(recent)) if recent else 0.0

    ratio_trigger = _f(cfg.get("std_ratio_trigger", 2.2), 2.2)
    std_abs_trigger = _f(cfg.get("std_abs_trigger_pct", 0.22), 0.22)
    abs_mean_trigger = _f(cfg.get("mean_abs_trigger_pct", 0.12), 0.12)

    triggered = False
    reason = "none"
    if len(recent) < min_recent_window or len(baseline) < min_baseline_window:
        reason = "insufficient_data"
    elif ratio >= ratio_trigger:
        triggered = True
        reason = "std_ratio"
    elif recent_std >= std_abs_trigger:
        triggered = True
        reason = "std_absolute"
    elif recent_abs_mean >= abs_mean_trigger:
        triggered = True
        reason = "abs_mean"

    return {
        "enabled": bool(cfg.get("enabled", True)),
        "triggered": triggered,
        "reason": reason,
        "recent_window_used": len(recent),
        "baseline_window_used": len(baseline),
        "recent_std": round(recent_std, 8),
        "baseline_std": round(baseline_std, 8),
        "std_ratio": round(ratio, 8),
        "recent_abs_mean": round(recent_abs_mean, 8),
        "thresholds": {
            "std_ratio_trigger": ratio_trigger,
            "std_abs_trigger_pct": std_abs_trigger,
            "mean_abs_trigger_pct": abs_mean_trigger,
        },
    }


def _mutate_policy(
    policy: Dict[str, Any],
    best: Dict[str, Any],
    mutation_cfg: Dict[str, Any],
    history_runs: int,
    windows_total: int,
    shock_metrics: Dict[str, Any],
) -> Dict[str, Any]:
    out = json.loads(json.dumps(policy))
    burst = out.get("burst", {}) or {}
    adaptive = out.setdefault("adaptive_mutation", {})
    state = adaptive.get("mutation_state", {}) or {}

    window_sizes = [int(x) for x in burst.get("window_sizes", [8, 12, 20])]
    stride = int(burst.get("stride", 2) or 2)
    max_windows = int(burst.get("max_windows", 60) or 60)

    w_low, w_high = [int(x) for x in mutation_cfg.get("window_size_bounds", [6, 60])]
    s_low, s_high = [int(x) for x in mutation_cfg.get("stride_bounds", [1, 6])]
    mw_low, mw_high = [int(x) for x in mutation_cfg.get("max_windows_bounds", [20, 240])]

    improve_th = _f(mutation_cfg.get("score_improve_threshold", 0.25), 0.25)
    win_target = _f(mutation_cfg.get("win_rate_target", 0.60), 0.60)
    dd_target = _f(mutation_cfg.get("drawdown_target_pct", 8.0), 8.0)

    score = _f(best.get("score", 0.0), 0.0)
    win_rate = _f(best.get("win_rate", 0.0), 0.0)
    drawdown = _f(best.get("drawdown", 0.0), 0.0)

    expand_w = int(mutation_cfg.get("window_expand_step", 2) or 2)
    contract_w = int(mutation_cfg.get("window_contract_step", 2) or 2)
    expand_mw = int(mutation_cfg.get("max_windows_expand_step", 10) or 10)
    contract_mw = int(mutation_cfg.get("max_windows_contract_step", 10) or 10)

    min_runs_before_mutation = int(mutation_cfg.get("min_runs_before_mutation", 1) or 1)
    min_windows_for_expand = int(mutation_cfg.get("min_windows_for_expand", 2) or 2)
    max_consecutive_expand = int(mutation_cfg.get("max_consecutive_expand", 3) or 3)
    max_consecutive_contract = int(mutation_cfg.get("max_consecutive_contract", 2) or 2)
    cooldown_after_expand = int(mutation_cfg.get("cooldown_runs_after_expand", 1) or 1)
    cooldown_after_contract = int(mutation_cfg.get("cooldown_runs_after_contract", 1) or 1)
    shock_cfg = mutation_cfg.get("volatility_shock_brake", {}) or {}
    shock_cfg_out = adaptive.setdefault("volatility_shock_brake", {}) or {}
    if not shock_cfg_out:
        shock_cfg_out.update(shock_cfg)
    cooldown_after_shock = int(shock_cfg.get("cooldown_runs_after_shock", 2) or 2)

    cooldown_remaining = max(0, int(state.get("cooldown_remaining", 0) or 0))
    consecutive_expand = max(0, int(state.get("consecutive_expand", 0) or 0))
    consecutive_contract = max(0, int(state.get("consecutive_contract", 0) or 0))

    mutation_mode = "hold"
    mutation_reason = "neutral_conditions"

    shock_active = bool(shock_metrics.get("enabled", False)) and bool(shock_metrics.get("triggered", False))

    autotune = shock_cfg_out.get("autotune", {}) or {}
    autotune_enabled = bool(autotune.get("enabled", True))
    min_runs_between_tunes = int(autotune.get("min_runs_between_tunes", 2) or 2)
    fp_streak_to_relax = int(autotune.get("false_positive_streak_to_relax", 2) or 2)
    miss_streak_to_tighten = int(autotune.get("missed_shock_streak_to_tighten", 2) or 2)

    relax_ratio_step = _f(autotune.get("relax_ratio_step", 0.08), 0.08)
    tighten_ratio_step = _f(autotune.get("tighten_ratio_step", 0.06), 0.06)
    relax_abs_step = _f(autotune.get("relax_abs_step_pct", 0.015), 0.015)
    tighten_abs_step = _f(autotune.get("tighten_abs_step_pct", 0.01), 0.01)

    ratio_low, ratio_high = [float(x) for x in autotune.get("ratio_bounds", [1.4, 4.0])]
    abs_low, abs_high = [float(x) for x in autotune.get("abs_std_bounds", [0.08, 0.8])]
    mean_low, mean_high = [float(x) for x in autotune.get("abs_mean_bounds", [0.05, 0.5])]

    std_ratio_trigger = _f(shock_cfg_out.get("std_ratio_trigger", shock_cfg.get("std_ratio_trigger", 2.2)), 2.2)
    std_abs_trigger = _f(shock_cfg_out.get("std_abs_trigger_pct", shock_cfg.get("std_abs_trigger_pct", 0.22)), 0.22)
    mean_abs_trigger = _f(shock_cfg_out.get("mean_abs_trigger_pct", shock_cfg.get("mean_abs_trigger_pct", 0.12)), 0.12)

    fp_streak = int(state.get("shock_false_positive_streak", 0) or 0)
    miss_streak = int(state.get("shock_missed_streak", 0) or 0)
    last_tune_run = int(state.get("shock_last_tune_run", 0) or 0)
    run_idx = int(max(history_runs, int(state.get("runs_seen", 0) or 0)) + 1)

    if shock_active:
        mutation_mode = "hold"
        mutation_reason = "volatility_shock_brake"
        cooldown_remaining = max(cooldown_remaining, cooldown_after_shock)
    elif history_runs < min_runs_before_mutation:
        mutation_mode = "hold"
        mutation_reason = "warmup"
    elif cooldown_remaining > 0:
        mutation_mode = "hold"
        mutation_reason = "cooldown"
        cooldown_remaining = max(0, cooldown_remaining - 1)
    else:
        preferred_mode = "hold"
        if score >= improve_th and win_rate >= win_target and drawdown <= dd_target:
            preferred_mode = "expand"
        elif drawdown > dd_target or win_rate < max(0.35, win_target - 0.12):
            preferred_mode = "contract"

        if preferred_mode == "expand" and windows_total < min_windows_for_expand:
            mutation_mode = "hold"
            mutation_reason = "insufficient_windows"
        elif preferred_mode == "expand" and consecutive_expand >= max_consecutive_expand:
            mutation_mode = "hold"
            mutation_reason = "expand_streak_cap"
        elif preferred_mode == "contract" and consecutive_contract >= max_consecutive_contract:
            mutation_mode = "hold"
            mutation_reason = "contract_streak_cap"
        else:
            mutation_mode = preferred_mode
            mutation_reason = "threshold_signal" if preferred_mode != "hold" else "neutral_conditions"

    strong_good = (score >= improve_th) and (win_rate >= win_target) and (drawdown <= dd_target)
    stressed_bad = (drawdown > (dd_target * 1.25)) or (win_rate < max(0.30, win_target - 0.20))

    if shock_active and strong_good:
        fp_streak += 1
        miss_streak = 0
        shock_feedback = "false_positive"
    elif (not shock_active) and stressed_bad:
        miss_streak += 1
        fp_streak = 0
        shock_feedback = "missed_shock"
    else:
        fp_streak = 0
        miss_streak = 0
        shock_feedback = "neutral"

    tuned = False
    tune_action = "hold"
    if autotune_enabled and (run_idx - last_tune_run) >= max(1, min_runs_between_tunes):
        if fp_streak >= max(1, fp_streak_to_relax):
            std_ratio_trigger = _clamp_float(std_ratio_trigger * (1.0 + relax_ratio_step), ratio_low, ratio_high)
            std_abs_trigger = _clamp_float(std_abs_trigger + relax_abs_step, abs_low, abs_high)
            mean_abs_trigger = _clamp_float(mean_abs_trigger + relax_abs_step, mean_low, mean_high)
            tuned = True
            tune_action = "relax"
            last_tune_run = run_idx
            fp_streak = 0
        elif miss_streak >= max(1, miss_streak_to_tighten):
            std_ratio_trigger = _clamp_float(std_ratio_trigger * (1.0 - tighten_ratio_step), ratio_low, ratio_high)
            std_abs_trigger = _clamp_float(std_abs_trigger - tighten_abs_step, abs_low, abs_high)
            mean_abs_trigger = _clamp_float(mean_abs_trigger - tighten_abs_step, mean_low, mean_high)
            tuned = True
            tune_action = "tighten"
            last_tune_run = run_idx
            miss_streak = 0

    shock_cfg_out["std_ratio_trigger"] = round(std_ratio_trigger, 8)
    shock_cfg_out["std_abs_trigger_pct"] = round(std_abs_trigger, 8)
    shock_cfg_out["mean_abs_trigger_pct"] = round(mean_abs_trigger, 8)

    if mutation_mode == "expand":
        window_sizes = [_clamp_int(w + expand_w, w_low, w_high) for w in window_sizes]
        max_windows = _clamp_int(max_windows + expand_mw, mw_low, mw_high)
        stride = _clamp_int(stride + 1, s_low, s_high)
        consecutive_expand += 1
        consecutive_contract = 0
        cooldown_remaining = max(0, cooldown_after_expand)
    elif mutation_mode == "contract":
        window_sizes = [_clamp_int(w - contract_w, w_low, w_high) for w in window_sizes]
        max_windows = _clamp_int(max_windows - contract_mw, mw_low, mw_high)
        stride = _clamp_int(stride - 1, s_low, s_high)
        consecutive_contract += 1
        consecutive_expand = 0
        cooldown_remaining = max(0, cooldown_after_contract)
    else:
        consecutive_expand = 0
        consecutive_contract = 0

    window_sizes = sorted(list(dict.fromkeys(window_sizes)))
    burst["window_sizes"] = window_sizes
    burst["stride"] = stride
    burst["max_windows"] = max_windows
    out["burst"] = burst
    adaptive["last_mode"] = mutation_mode
    adaptive["last_reason"] = mutation_reason
    adaptive["last_updated_utc"] = now_utc()
    adaptive["last_shock_brake"] = {
        "triggered": bool(shock_metrics.get("triggered", False)),
        "reason": shock_metrics.get("reason", "none"),
        "std_ratio": shock_metrics.get("std_ratio"),
        "recent_std": shock_metrics.get("recent_std"),
    }
    adaptive["last_shock_autotune"] = {
        "enabled": autotune_enabled,
        "feedback": shock_feedback,
        "action": tune_action,
        "tuned": tuned,
        "run_index": run_idx,
        "thresholds": {
            "std_ratio_trigger": shock_cfg_out.get("std_ratio_trigger"),
            "std_abs_trigger_pct": shock_cfg_out.get("std_abs_trigger_pct"),
            "mean_abs_trigger_pct": shock_cfg_out.get("mean_abs_trigger_pct"),
        },
    }
    adaptive["mutation_state"] = {
        "cooldown_remaining": int(cooldown_remaining),
        "consecutive_expand": int(consecutive_expand),
        "consecutive_contract": int(consecutive_contract),
        "runs_seen": run_idx,
        "total_mutations": int(state.get("total_mutations", 0) or 0) + (1 if mutation_mode in ("expand", "contract") else 0),
        "shock_false_positive_streak": int(fp_streak),
        "shock_missed_streak": int(miss_streak),
        "shock_last_tune_run": int(last_tune_run),
    }
    return out


def score_windows(windows: List[List[float]], objective: Dict[str, float], constraints: Dict[str, float]) -> Dict[str, Any]:
    best = None
    scored: List[Dict[str, Any]] = []

    for idx, win in enumerate(windows):
        st = _stats(win)
        valid = (
            st["win_rate"] >= _f(constraints.get("min_win_rate"), 0.45)
            and st["drawdown"] <= _f(constraints.get("max_drawdown_pct"), 16.0)
            and st["sharpe"] >= _f(constraints.get("min_sharpe"), 0.10)
        )

        score = (
            _f(objective.get("weight_growth"), 0.45) * (st["mean"] * 100.0)
            + _f(objective.get("weight_win_rate"), 0.20) * (st["win_rate"] * 100.0)
            + _f(objective.get("weight_sharpe"), 0.20) * (st["sharpe"] * 8.0)
            - _f(objective.get("weight_drawdown_penalty"), 0.15) * (st["drawdown"] * 1.5)
        )

        row = {
            "window_index": idx,
            "window_len": len(win),
            "score": score,
            "valid": valid,
            "mean": st["mean"],
            "win_rate": st["win_rate"],
            "sharpe": st["sharpe"],
            "drawdown": st["drawdown"],
        }
        scored.append(row)

        if valid and (best is None or row["score"] > best["score"]):
            best = row

    if best is None and scored:
        best = max(scored, key=lambda x: x["score"])

    return {
        "best": best,
        "top": sorted(scored, key=lambda x: x["score"], reverse=True)[:20],
        "total": len(scored),
    }


def build_patch(runtime: Dict[str, Any], x1000: Dict[str, Any], fractal: Dict[str, Any], best: Dict[str, Any], safety: Dict[str, Any]) -> Dict[str, Any]:
    xpatch = (x1000.get("recommended_patch") or {})
    fpatch = (fractal.get("recommended_patch") or {})

    base_risk = max(_f(xpatch.get("base_risk_fraction"), _f(runtime.get("base_risk_fraction"), 0.2)), _f(fpatch.get("base_risk_fraction"), 0.2))
    loop_sec = min(_f(xpatch.get("loop_seconds"), _f(runtime.get("loop_seconds"), 1.0)), _f(fpatch.get("loop_seconds"), 1.0))
    max_pos = max(_f(xpatch.get("max_position_usd"), _f(runtime.get("max_position_usd"), 50.0)), _f(fpatch.get("max_position_usd"), 50.0))

    confidence_gain = 1.0 + min(max(_f(best.get("win_rate"), 0.5) - 0.5, 0.0), 0.20)
    drawdown_brake = max(0.65, 1.0 - (_f(best.get("drawdown"), 0.0) / 100.0))
    scalar = confidence_gain * drawdown_brake

    safe_risk = min(base_risk * scalar, _f(safety.get("max_base_risk_fraction"), 0.90))
    safe_loop = min(max(loop_sec / max(scalar, 0.75), _f(safety.get("min_loop_seconds"), 0.20)), _f(safety.get("max_loop_seconds"), 2.00))
    safe_max_pos = min(max_pos * scalar, _f(runtime.get("max_position_usd"), 50.0) * _f(safety.get("max_position_multiplier"), 1.45))

    patch = {
        "base_risk_fraction": round(safe_risk, 4),
        "loop_seconds": round(safe_loop, 3),
        "max_position_usd": round(safe_max_pos, 2),
        "time_travel_burst_active": True,
        "time_travel_burst_last_run_utc": now_utc(),
        "time_travel_burst_best_score": round(_f(best.get("score"), 0.0), 6),
        "time_travel_burst_best_win_rate": round(_f(best.get("win_rate"), 0.0), 6),
        "time_travel_burst_best_sharpe": round(_f(best.get("sharpe"), 0.0), 6),
        "time_travel_burst_best_drawdown": round(_f(best.get("drawdown"), 0.0), 6),
    }

    if bool(safety.get("force_paper", True)):
        patch["mode"] = "paper"
        patch["allow_live_orders"] = False

    return patch


def run(apply_patch: bool) -> int:
    runtime = read_json(RUNTIME_FILE, {})
    trades = read_json(TRADE_LOG_FILE, [])
    x1000 = read_json(X1000_FILE, {})
    fractal = read_json(FRACTAL_FILE, {})
    policy = read_json(BURST_POLICY_FILE, {})

    if not runtime or not policy:
        print("[BURST] missing runtime or burst policy")
        return 1

    burst_cfg = policy.get("burst", {}) or {}
    objective = policy.get("objective", {}) or {}
    constraints = policy.get("constraints", {}) or {}
    safety = policy.get("safety", {}) or {}
    mutation_cfg = policy.get("adaptive_mutation", {}) or {}
    outputs = policy.get("outputs", {}) or {}

    returns = _extract_returns(trades)
    lookback = int(burst_cfg.get("lookback_trades", 400) or 400)
    returns = returns[-max(lookback, 1):]
    if len(returns) < 6:
        returns = [0.08, -0.04, 0.03, 0.02, -0.01, 0.01, 0.06, -0.03, 0.04, 0.0]

    windows = _burst_windows(
        returns,
        window_sizes=[int(x) for x in burst_cfg.get("window_sizes", [8, 12, 20])],
        stride=int(burst_cfg.get("stride", 2) or 2),
        max_windows=int(burst_cfg.get("max_windows", 60) or 60),
    )

    scored = score_windows(windows, objective, constraints)
    best = scored.get("best") or {
        "score": 0.0,
        "win_rate": 0.0,
        "sharpe": 0.0,
        "drawdown": 0.0,
    }

    patch = build_patch(runtime, x1000, fractal, best, safety)

    report_path = ROOT / str(outputs.get("report_file", "out/execution/time_travel_burst_report.json"))
    patch_path = ROOT / str(outputs.get("patch_file", "config/runtime_time_travel_patch.json"))
    audit_path = ROOT / str(outputs.get("audit_file", "out/execution/time_travel_burst_audit.json"))

    report = {
        "timestamp_utc": now_utc(),
        "windows_total": scored.get("total", 0),
        "best": best,
        "recommended_patch": patch,
        "x1000_pass_improvement": x1000.get("pass_improvement"),
        "fractal_growth_factor": (fractal.get("recommended_patch") or {}).get("micro_fractal_growth_factor"),
        "mutation_enabled": bool(mutation_cfg.get("enabled", False)),
    }

    audit = {
        "timestamp_utc": now_utc(),
        "applied": False,
        "inputs": {
            "runtime": str(RUNTIME_FILE),
            "trades": str(TRADE_LOG_FILE),
            "x1000": str(X1000_FILE),
            "fractal": str(FRACTAL_FILE),
            "policy": str(BURST_POLICY_FILE),
        },
        "outputs": {
            "report": str(report_path),
            "patch": str(patch_path),
            "audit": str(audit_path),
        },
    }

    atomic_write_json(report_path, report, indent=2)
    atomic_write_json(patch_path, patch, indent=2)

    if bool(mutation_cfg.get("enabled", False)) and bool(mutation_cfg.get("persist_policy_updates", True)):
        shock_cfg = mutation_cfg.get("volatility_shock_brake", {}) or {}
        shock_metrics = _volatility_shock_metrics(returns, shock_cfg)
        hist_file = ROOT / str(mutation_cfg.get("mutation_history_file", "out/execution/time_travel_burst_history.json"))
        history = read_json(hist_file, {"runs": []})
        if not isinstance(history, dict):
            history = {"runs": []}
        if "runs" not in history or not isinstance(history.get("runs"), list):
            history["runs"] = []

        updated_policy = _mutate_policy(
            policy=policy,
            best=best,
            mutation_cfg=mutation_cfg,
            history_runs=len(history.get("runs", [])),
            windows_total=int(scored.get("total", 0) or 0),
            shock_metrics=shock_metrics,
        )
        atomic_write_json(BURST_POLICY_FILE, updated_policy, indent=2)
        mutation_state = (updated_policy.get("adaptive_mutation") or {}).get("mutation_state", {}) or {}
        shock_autotune = (updated_policy.get("adaptive_mutation") or {}).get("last_shock_autotune", {}) or {}
        history["runs"].append(
            {
                "timestamp_utc": now_utc(),
                "best_score": best.get("score"),
                "best_win_rate": best.get("win_rate"),
                "best_drawdown": best.get("drawdown"),
                "new_window_sizes": (updated_policy.get("burst") or {}).get("window_sizes"),
                "new_stride": (updated_policy.get("burst") or {}).get("stride"),
                "new_max_windows": (updated_policy.get("burst") or {}).get("max_windows"),
                "mutation_mode": (updated_policy.get("adaptive_mutation") or {}).get("last_mode"),
                "mutation_reason": (updated_policy.get("adaptive_mutation") or {}).get("last_reason"),
                "shock_brake": shock_metrics,
                "shock_autotune": shock_autotune,
                "mutation_state": mutation_state,
            }
        )
        history["runs"] = history["runs"][-200:]
        atomic_write_json(hist_file, history, indent=2)
        report["mutation_mode"] = (updated_policy.get("adaptive_mutation") or {}).get("last_mode")
        report["mutation_reason"] = (updated_policy.get("adaptive_mutation") or {}).get("last_reason")
        report["shock_brake"] = shock_metrics
        report["shock_autotune"] = shock_autotune
        report["mutation_state"] = mutation_state
        report["mutated_burst"] = updated_policy.get("burst")
        atomic_write_json(report_path, report, indent=2)

    if apply_patch:
        merged = dict(runtime)
        merged.update(patch)
        backup = RUNTIME_FILE.with_name(f"runtime_control.burst_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        atomic_write_json(backup, runtime, indent=2)
        atomic_write_json(RUNTIME_FILE, merged, indent=2)
        audit["applied"] = True
        audit["runtime_backup"] = str(backup)

    atomic_write_json(audit_path, audit, indent=2)

    print("[BURST] complete")
    print(f"  apply_patch: {apply_patch}")
    print(f"  windows_total: {scored.get('total', 0)}")
    print(f"  best_score: {best.get('score')}")
    if report.get("mutation_mode"):
        print(f"  mutation_mode: {report.get('mutation_mode')} ({report.get('mutation_reason')}) | burst: {report.get('mutated_burst')}")
    print(f"  report: {report_path}")
    print(f"  patch: {patch_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Time-travel burst replay engine")
    parser.add_argument("--apply", action="store_true", help="Apply burst patch to runtime")
    args = parser.parse_args()
    return run(apply_patch=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
