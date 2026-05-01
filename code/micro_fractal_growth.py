import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
CONFIG = ROOT / "config"
OUT = ROOT / "out" / "execution"

RUNTIME_FILE = CONFIG / "runtime_control.json"
X1000_REPORT_FILE = OUT / "optimizer_x1000_report.json"
LIGHTNING_FILE = OUT / "lightning_frozen_delta.json"
FRACTAL_FILE = CONFIG / "micro_fractal_growth.json"


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


def build_fractal_patch(runtime: Dict[str, Any], x1000: Dict[str, Any], lightning: Dict[str, Any], fractal: Dict[str, Any]) -> Dict[str, Any]:
    micro = fractal.get("micro_cells", {}) or {}
    momentum = fractal.get("momentum", {}) or {}
    safety = fractal.get("safety", {}) or {}

    pass_improvement = _f(x1000.get("pass_improvement", 0.0), 0.0)
    winner_pass = str(x1000.get("winner_pass", "pass1"))
    best = x1000.get("best", {}) or {}
    constraints = int(lightning.get("constraint_count", 0) or 0)

    base_growth_step = _f(micro.get("base_growth_step_pct", 1.8), 1.8)
    max_growth_step = _f(micro.get("max_growth_step_pct", 6.0), 6.0)
    drawdown_brake = _f(micro.get("drawdown_brake_step_pct", 0.8), 0.8)

    growth_factor = 1.0 + min(max(base_growth_step / 100.0, 0.0), max_growth_step / 100.0)
    if pass_improvement >= _f(momentum.get("improvement_floor", 0.05), 0.05):
        growth_factor *= 1.08
    if bool(momentum.get("boost_if_pass2_wins", True)) and winner_pass == "pass2":
        growth_factor *= _f(momentum.get("boost_multiplier", 1.15), 1.15)
    if bool(momentum.get("cooldown_if_stability_weak", True)) and constraints > 0:
        growth_factor *= max(0.80, 1.0 - (drawdown_brake / 10.0))

    base_risk_fraction = _f(best.get("base_risk_fraction"), _f(runtime.get("base_risk_fraction"), 0.2))
    loop_seconds = _f(best.get("loop_seconds"), _f(runtime.get("loop_seconds"), 1.0))

    current_max_position = _f(runtime.get("max_position_usd"), 50.0)
    position_mult = min(growth_factor, _f(safety.get("max_position_usd_multiplier", 1.60), 1.60))
    new_max_position = current_max_position * position_mult

    safe_risk = min(
        _f(safety.get("max_base_risk_fraction", 0.92), 0.92),
        max(0.05, base_risk_fraction * min(growth_factor, 1.12))
    )

    min_loop = _f(safety.get("min_loop_seconds", 0.20), 0.20)
    max_loop = _f(safety.get("max_loop_seconds", 2.50), 2.50)
    safe_loop = min(max(loop_seconds * (0.95 if constraints == 0 else 1.12), min_loop), max_loop)

    daily_loss = _f(runtime.get("max_daily_loss_usd"), 50.0)
    daily_mult = _f(safety.get("max_daily_loss_usd_multiplier", 1.25), 1.25)
    safe_daily_loss = daily_loss * min(growth_factor, daily_mult)

    force_paper = bool(safety.get("force_paper_on_high_constraints", True)) and constraints >= 2

    patch = {
        "base_risk_fraction": round(safe_risk, 4),
        "loop_seconds": round(safe_loop, 3),
        "max_position_usd": round(new_max_position, 2),
        "max_daily_loss_usd": round(safe_daily_loss, 2),
        "micro_fractal_growth_active": True,
        "micro_fractal_growth_last_run_utc": now_utc(),
        "micro_fractal_growth_factor": round(growth_factor, 6),
        "micro_fractal_pass_improvement": round(pass_improvement, 6),
        "micro_fractal_winner_pass": winner_pass,
        "micro_fractal_constraints": constraints,
    }

    if force_paper:
        patch["mode"] = "paper"
        patch["allow_live_orders"] = False

    return patch


def run(apply_patch: bool) -> int:
    runtime = read_json(RUNTIME_FILE, {})
    x1000 = read_json(X1000_REPORT_FILE, {})
    lightning = read_json(LIGHTNING_FILE, {})
    fractal = read_json(FRACTAL_FILE, {})

    if not runtime or not fractal:
        print("[FRACTAL] missing runtime or fractal policy")
        return 1

    outputs = fractal.get("outputs", {}) or {}
    report_path = ROOT / str(outputs.get("report_file", "out/execution/micro_fractal_growth_report.json"))
    patch_path = ROOT / str(outputs.get("patch_file", "config/runtime_fractal_patch.json"))
    audit_path = ROOT / str(outputs.get("audit_file", "out/execution/micro_fractal_growth_audit.json"))

    patch = build_fractal_patch(runtime, x1000, lightning, fractal)

    report = {
        "timestamp_utc": now_utc(),
        "x1000_winner_pass": x1000.get("winner_pass"),
        "x1000_pass_improvement": x1000.get("pass_improvement"),
        "lightning_constraint_count": lightning.get("constraint_count", 0),
        "recommended_patch": patch,
    }

    audit = {
        "timestamp_utc": now_utc(),
        "inputs": {
            "runtime_file": str(RUNTIME_FILE),
            "x1000_file": str(X1000_REPORT_FILE),
            "lightning_file": str(LIGHTNING_FILE),
            "fractal_policy": str(FRACTAL_FILE),
        },
        "outputs": {
            "report_file": str(report_path),
            "patch_file": str(patch_path),
            "audit_file": str(audit_path),
        },
        "applied": False,
    }

    atomic_write_json(report_path, report, indent=2)
    atomic_write_json(patch_path, patch, indent=2)

    if apply_patch:
        merged = dict(runtime)
        merged.update(patch)
        backup = RUNTIME_FILE.with_name(f"runtime_control.fractal_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        atomic_write_json(backup, runtime, indent=2)
        atomic_write_json(RUNTIME_FILE, merged, indent=2)
        audit["applied"] = True
        audit["runtime_backup"] = str(backup)

    atomic_write_json(audit_path, audit, indent=2)

    print("[FRACTAL] complete")
    print(f"  apply_patch: {apply_patch}")
    print(f"  growth_factor: {patch.get('micro_fractal_growth_factor')}")
    print(f"  pass_improvement: {patch.get('micro_fractal_pass_improvement')}")
    print(f"  report: {report_path}")
    print(f"  patch: {patch_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Micro-fractal growth pass")
    parser.add_argument("--apply", action="store_true", help="Apply fractal patch to runtime config")
    args = parser.parse_args()
    return run(apply_patch=args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
