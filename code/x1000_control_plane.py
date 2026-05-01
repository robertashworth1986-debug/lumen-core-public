import argparse
from datetime import datetime, timezone
from pathlib import Path

from beast_mode import run as run_beast
from lightning import run as run_lightning
from optimizer_x1000 import run as run_optimizer
from micro_fractal_growth import run as run_fractal
from time_travel_burst_engine import run as run_burst

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_summary(payload):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "x1000_control_plane_summary.json"
    path.write_text(__import__("json").dumps(payload, indent=2), encoding="utf-8")
    return path


def run_all(apply: bool, passes: int = 2) -> int:
    summary = {
        "timestamp_utc": now_utc(),
        "apply": apply,
        "passes": passes,
        "stages": [],
    }

    # Stage 1: Beast mode tuning
    rc1 = run_beast(dry_run=not apply)
    summary["stages"].append({"stage": "beast_mode", "return_code": rc1})
    if rc1 != 0:
        summary["status"] = "failed"
        summary["failed_stage"] = "beast_mode"
        write_summary(summary)
        return rc1

    # Stage 2: Lightning guardrail enforcement
    rc2 = run_lightning(dry_run=not apply)
    summary["stages"].append({"stage": "lightning", "return_code": rc2})
    if rc2 != 0:
        summary["status"] = "failed"
        summary["failed_stage"] = "lightning"
        write_summary(summary)
        return rc2

    # Stage 3: X1000 optimization pass
    rc3 = run_optimizer(apply_patch=apply, passes=max(1, min(passes, 2)))
    summary["stages"].append({"stage": "optimizer_x1000", "return_code": rc3})
    if rc3 != 0:
        summary["status"] = "failed"
        summary["failed_stage"] = "optimizer_x1000"
        write_summary(summary)
        return rc3

    # Stage 4: Micro-fractal growth pass
    rc4 = run_fractal(apply_patch=apply)
    summary["stages"].append({"stage": "micro_fractal_growth", "return_code": rc4})
    if rc4 != 0:
        summary["status"] = "failed"
        summary["failed_stage"] = "micro_fractal_growth"
        write_summary(summary)
        return rc4

    # Stage 5: Time-travel burst replay pass
    rc5 = run_burst(apply_patch=apply)
    summary["stages"].append({"stage": "time_travel_burst", "return_code": rc5})
    if rc5 != 0:
        summary["status"] = "failed"
        summary["failed_stage"] = "time_travel_burst"
        write_summary(summary)
        return rc5

    summary["status"] = "ok"
    summary_path = write_summary(summary)
    print("[X1000-CONTROL-PLANE] complete")
    print(f"  apply: {apply}")
    print(f"  summary: {summary_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run beast + lightning + x1000 optimizer pipeline")
    parser.add_argument("--apply", action="store_true", help="Apply changes where allowed by each stage")
    parser.add_argument("--passes", type=int, default=2, help="Optimizer passes per cycle (recommended: 2)")
    args = parser.parse_args()
    return run_all(apply=args.apply, passes=max(1, min(args.passes, 2)))


if __name__ == "__main__":
    raise SystemExit(main())
