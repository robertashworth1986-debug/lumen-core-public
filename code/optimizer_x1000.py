import argparse
import json
import math
import os
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"

RUNTIME_FILE = CONFIG / "runtime_control.json"
OPT_FILE = CONFIG / "optimizer_x1000.json"
TRADE_LOG_FILE = OUT / "trade_log.json"
HEALTH_FILE = OUT / "health_metrics.json"


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


def _safe_sample_pnl_pct(trade_log: List[Dict[str, Any]]) -> List[float]:
    vals: List[float] = []
    for t in trade_log:
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
        return {"mean": 0.0, "std": 0.0, "win_rate": 0.0, "sharpe": 0.0}
    mean = sum(values) / len(values)
    wins = sum(1 for x in values if x > 0)
    win_rate = wins / len(values)
    if len(values) > 1:
        var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    else:
        var = 0.0
    std = math.sqrt(max(var, 0.0))
    sharpe = (mean / std) if std > 1e-9 else 0.0
    return {"mean": mean, "std": std, "win_rate": win_rate, "sharpe": sharpe}


def _simulate_path(base_returns: List[float], n_steps: int, rng: random.Random) -> List[float]:
    if not base_returns:
        base_returns = [0.03, -0.02, 0.01, 0.0, 0.02, -0.01]
    return [rng.choice(base_returns) for _ in range(n_steps)]


def _max_drawdown_pct(path_returns_pct: List[float]) -> float:
    equity = 100.0
    peak = equity
    max_dd = 0.0
    for r in path_returns_pct:
        equity *= (1.0 + (r / 100.0))
        peak = max(peak, equity)
        if peak > 0:
            dd = ((peak - equity) / peak) * 100.0
            max_dd = max(max_dd, dd)
    return max_dd


def _score_candidate(
    candidate: Dict[str, float],
    sampled_returns: List[float],
    health: Dict[str, Any],
    weights: Dict[str, float],
) -> Dict[str, float]:
    risk_fraction = candidate["base_risk_fraction"]
    loop_seconds = candidate["loop_seconds"]
    pos_mult = candidate["max_position_usd_mult"]

    scaled = [r * risk_fraction * min(pos_mult, 2.0) for r in sampled_returns]
    st = _stats(scaled)
    drawdown = _max_drawdown_pct(scaled)

    latency_penalty = 0.0
    p95 = _f(health.get("latency_p95_ms"), 120.0)
    if p95 > 300:
        latency_penalty = min((p95 - 300.0) / 700.0, 1.0)

    cadence_penalty = 0.0
    if loop_seconds < 0.30 and p95 > 200:
        cadence_penalty = 0.25

    growth_signal = st["mean"] * 100.0
    sharpe_signal = st["sharpe"]
    stability_signal = max(0.0, 1.0 - ((_f(health.get("error_rate_pct"), 0.0) / 10.0) + latency_penalty + cadence_penalty))
    dd_penalty = min(drawdown / 25.0, 2.0)

    score = (
        weights["weight_growth"] * growth_signal
        + weights["weight_sharpe"] * sharpe_signal * 8.0
        + weights["weight_stability"] * stability_signal * 10.0
        - weights["weight_drawdown_penalty"] * dd_penalty * 12.0
    )

    return {
        "score": score,
        "sim_mean_pct": st["mean"],
        "sim_sharpe": st["sharpe"],
        "sim_win_rate": st["win_rate"],
        "sim_drawdown_pct": drawdown,
    }


def _run_search_pass(
    runtime: Dict[str, Any],
    opt: Dict[str, Any],
    trade_log: List[Dict[str, Any]],
    health: Dict[str, Any],
    iterations: int,
    seed: int,
    center: Optional[Dict[str, float]] = None,
    tighten: float = 1.0,
) -> Dict[str, Any]:
    search = opt.get("search", {}) or {}
    weights = opt.get("objective", {}) or {}
    constraints = opt.get("constraints", {}) or {}

    rng = random.Random(seed)

    rf_min, rf_max = [float(x) for x in search.get("risk_fraction_bounds", [0.08, 0.95])]
    ls_min, ls_max = [float(x) for x in search.get("loop_seconds_bounds", [0.2, 1.5])]
    pm_min, pm_max = [float(x) for x in search.get("max_position_usd_multiplier_bounds", [0.6, 3.0])]
    gc_min, gc_max = [float(x) for x in search.get("gate_confidence_bounds", [0.52, 0.80])]
    ge_min, ge_max = [float(x) for x in search.get("gate_edge_bps_bounds", [6.0, 18.0])]
    py_min, py_max = [float(x) for x in search.get("pyramid_multiplier_bounds", [1.2, 4.0])]

    base_returns = _safe_sample_pnl_pct(trade_log)
    if len(base_returns) < 8:
        # sparse-data bootstrap distribution
        base_returns = [0.08, -0.05, 0.03, 0.01, -0.02, 0.12, -0.04, 0.02, 0.05, -0.01]

    current_max_pos = _f(runtime.get("max_position_usd"), 50.0)

    best = None
    trials: List[Dict[str, Any]] = []

    def _sample(low: float, high: float, key: str) -> float:
        if center is None:
            return rng.uniform(low, high)
        c = center.get(key, (low + high) / 2.0)
        span = max((high - low) * max(min(tighten, 1.0), 0.01), 1e-6)
        local_low = max(low, c - (span / 2.0))
        local_high = min(high, c + (span / 2.0))
        if local_low >= local_high:
            return max(min(c, high), low)
        return rng.uniform(local_low, local_high)

    for _ in range(iterations):
        cand = {
            "base_risk_fraction": _sample(rf_min, rf_max, "base_risk_fraction"),
            "loop_seconds": _sample(ls_min, ls_max, "loop_seconds"),
            "max_position_usd_mult": _sample(pm_min, pm_max, "max_position_usd_mult"),
            "gate_override_min_confidence": _sample(gc_min, gc_max, "gate_override_min_confidence"),
            "gate_override_min_edge_bps": _sample(ge_min, ge_max, "gate_override_min_edge_bps"),
            "pyramid_reinvestment_multiplier": _sample(py_min, py_max, "pyramid_reinvestment_multiplier"),
        }

        sim_path = _simulate_path(base_returns, n_steps=120, rng=rng)
        metrics = _score_candidate(cand, sim_path, health, weights)

        valid = (
            metrics["sim_drawdown_pct"] <= _f(constraints.get("max_simulated_drawdown_pct"), 18.0)
            and metrics["sim_win_rate"] >= _f(constraints.get("min_simulated_win_rate"), 0.45)
            and metrics["sim_sharpe"] >= _f(constraints.get("min_simulated_sharpe"), 0.25)
            and _f(health.get("error_rate_pct"), 0.0) <= _f(constraints.get("max_error_rate_pct"), 6.0)
        )

        row = {**cand, **metrics, "valid": valid}
        trials.append(row)
        if valid and (best is None or row["score"] > best["score"]):
            best = row

    if best is None and trials:
        best = max(trials, key=lambda x: x["score"])

    if best is None:
        best = {
            "base_risk_fraction": _f(runtime.get("base_risk_fraction"), 0.2),
            "loop_seconds": _f(runtime.get("loop_seconds"), 1.0),
            "max_position_usd_mult": 1.0,
            "gate_override_min_confidence": _f(runtime.get("gate_override_min_confidence"), 0.6),
            "gate_override_min_edge_bps": _f(runtime.get("gate_override_min_edge_bps"), 12.0),
            "pyramid_reinvestment_multiplier": _f(runtime.get("pyramid_reinvestment_multiplier"), 2.0),
            "score": 0.0,
            "sim_mean_pct": 0.0,
            "sim_sharpe": 0.0,
            "sim_win_rate": 0.0,
            "sim_drawdown_pct": 0.0,
            "valid": False,
        }

    patch = {
        "base_risk_fraction": round(best["base_risk_fraction"], 4),
        "loop_seconds": round(best["loop_seconds"], 3),
        "max_position_usd": round(current_max_pos * best["max_position_usd_mult"], 2),
        "gate_override_min_confidence": round(best["gate_override_min_confidence"], 4),
        "gate_override_min_edge_bps": round(best["gate_override_min_edge_bps"], 3),
        "pyramid_reinvestment_multiplier": round(best["pyramid_reinvestment_multiplier"], 3),
        "optimizer_x1000_active": True,
        "optimizer_x1000_last_run_utc": now_utc(),
        "optimizer_x1000_best_score": round(best["score"], 5),
    }

    return {
        "best": best,
        "patch": patch,
        "trials_sample": sorted(trials, key=lambda x: x["score"], reverse=True)[:25],
        "trials_total": len(trials),
        "base_returns_count": len(base_returns),
    }


def optimize(runtime: Dict[str, Any], opt: Dict[str, Any], trade_log: List[Dict[str, Any]], health: Dict[str, Any], passes: int = 1) -> Dict[str, Any]:
    search = opt.get("search", {}) or {}
    seed = int(search.get("seed", 42) or 42)
    iterations = int(search.get("iterations", 600) or 600)
    pass2_scale = float(search.get("pass2_iterations_scale", 0.65) or 0.65)
    pass2_tighten = float(search.get("pass2_tighten_factor", 0.35) or 0.35)

    pass1 = _run_search_pass(
        runtime=runtime,
        opt=opt,
        trade_log=trade_log,
        health=health,
        iterations=iterations,
        seed=seed,
        center=None,
        tighten=1.0,
    )

    if passes <= 1:
        return {
            "best": pass1["best"],
            "patch": pass1["patch"],
            "trials_sample": pass1["trials_sample"],
            "trials_total": pass1["trials_total"],
            "base_returns_count": pass1["base_returns_count"],
            "passes": 1,
            "pass1": pass1,
            "pass2": None,
            "pass_improvement": 0.0,
        }

    center = {
        "base_risk_fraction": float(pass1["best"].get("base_risk_fraction", 0.2)),
        "loop_seconds": float(pass1["best"].get("loop_seconds", 1.0)),
        "max_position_usd_mult": float(pass1["best"].get("max_position_usd_mult", 1.0)),
        "gate_override_min_confidence": float(pass1["best"].get("gate_override_min_confidence", 0.6)),
        "gate_override_min_edge_bps": float(pass1["best"].get("gate_override_min_edge_bps", 12.0)),
        "pyramid_reinvestment_multiplier": float(pass1["best"].get("pyramid_reinvestment_multiplier", 2.0)),
    }

    pass2 = _run_search_pass(
        runtime=runtime,
        opt=opt,
        trade_log=trade_log,
        health=health,
        iterations=max(int(iterations * pass2_scale), 100),
        seed=seed + 101,
        center=center,
        tighten=pass2_tighten,
    )

    use_pass2 = float(pass2["best"].get("score", 0.0)) >= float(pass1["best"].get("score", 0.0))
    winner = pass2 if use_pass2 else pass1
    improvement = float(pass2["best"].get("score", 0.0)) - float(pass1["best"].get("score", 0.0))

    return {
        "best": winner["best"],
        "patch": winner["patch"],
        "trials_sample": winner["trials_sample"],
        "trials_total": pass1["trials_total"] + pass2["trials_total"],
        "base_returns_count": winner["base_returns_count"],
        "passes": 2,
        "pass1": pass1,
        "pass2": pass2,
        "pass_improvement": round(improvement, 6),
        "winner_pass": "pass2" if use_pass2 else "pass1",
    }


def run(apply_patch: bool, passes: int = 1) -> int:
    runtime = read_json(RUNTIME_FILE, {})
    opt = read_json(OPT_FILE, {})
    trade_log = read_json(TRADE_LOG_FILE, [])
    health = read_json(HEALTH_FILE, {})

    if not runtime or not opt:
        print("[X1000] missing runtime or optimizer config")
        return 1

    result = optimize(runtime, opt, trade_log, health, passes=max(1, passes))

    outputs = opt.get("outputs", {}) or {}
    report_path = ROOT / str(outputs.get("report_file", "out/execution/optimizer_x1000_report.json"))
    patch_path = ROOT / str(outputs.get("patch_file", "config/runtime_optimized_patch.json"))
    sim_path = ROOT / str(outputs.get("simulation_file", "out/execution/optimizer_x1000_simulation.json"))

    report = {
        "timestamp_utc": now_utc(),
        "passes": result.get("passes", 1),
        "winner_pass": result.get("winner_pass", "pass1"),
        "pass_improvement": result.get("pass_improvement", 0.0),
        "trials_total": result["trials_total"],
        "base_returns_count": result["base_returns_count"],
        "best": result["best"],
        "current_runtime_subset": {
            "base_risk_fraction": runtime.get("base_risk_fraction"),
            "loop_seconds": runtime.get("loop_seconds"),
            "max_position_usd": runtime.get("max_position_usd"),
            "gate_override_min_confidence": runtime.get("gate_override_min_confidence"),
            "gate_override_min_edge_bps": runtime.get("gate_override_min_edge_bps"),
            "pyramid_reinvestment_multiplier": runtime.get("pyramid_reinvestment_multiplier"),
        },
        "recommended_patch": result["patch"],
        "pass1_best": (result.get("pass1") or {}).get("best"),
        "pass2_best": (result.get("pass2") or {}).get("best"),
    }

    atomic_write_json(report_path, report, indent=2)
    atomic_write_json(patch_path, result["patch"], indent=2)
    atomic_write_json(
        sim_path,
        {
            "top_trials": result["trials_sample"],
            "pass1_top_trials": ((result.get("pass1") or {}).get("trials_sample") or [])[:10],
            "pass2_top_trials": ((result.get("pass2") or {}).get("trials_sample") or [])[:10],
        },
        indent=2,
    )

    applied = False
    apply_cfg = opt.get("apply", {}) or {}
    if apply_patch:
        allowed = bool(apply_cfg.get("allow_direct_runtime_patch", False))
        if bool(apply_cfg.get("require_env_var", True)):
            env_var = str(apply_cfg.get("env_var", "LUMENCORE_ARM_OPTIMIZER_APPLY"))
            env_val = str(apply_cfg.get("env_value", "YES_APPLY_OPTIMIZER_PATCH"))
            allowed = allowed and (os.environ.get(env_var, "") == env_val)

        if allowed:
            backup = RUNTIME_FILE.with_name(f"runtime_control.optimizer_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
            atomic_write_json(backup, runtime, indent=2)
            patched = dict(runtime)
            patched.update(result["patch"])
            atomic_write_json(RUNTIME_FILE, patched, indent=2)
            applied = True

    print("[X1000] optimization complete")
    print(f"  passes: {result.get('passes', 1)} | trials: {result['trials_total']} | returns_used: {result['base_returns_count']}")
    print(f"  best_score: {result['best']['score']:.5f}")
    print(f"  pass_improvement: {result.get('pass_improvement', 0.0)} | winner: {result.get('winner_pass', 'pass1')}")
    print(f"  report: {report_path}")
    print(f"  patch: {patch_path}")
    print(f"  applied_to_runtime: {applied}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="LUMENCORE X1000 optimizer")
    parser.add_argument("--apply", action="store_true", help="Attempt direct apply to runtime (requires arming)")
    parser.add_argument("--passes", type=int, default=1, help="Optimization passes (1 or 2)")
    args = parser.parse_args()
    return run(apply_patch=args.apply, passes=max(1, min(args.passes, 2)))


if __name__ == "__main__":
    raise SystemExit(main())
