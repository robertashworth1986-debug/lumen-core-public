import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from x1000_control_plane import run_all

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"
REPORT_FILE = OUT / "optimizer_x1000_report.json"
LOOP_FILE = OUT / "evolutionary_loop_history.json"


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
    tmp.replace(path)


def run_loop(cycles: int, interval_sec: float, apply: bool, passes: int) -> int:
    history: Dict[str, Any] = {
        "started_utc": now_utc(),
        "apply": apply,
        "passes": passes,
        "cycles_requested": cycles,
        "interval_sec": interval_sec,
        "cycles": [],
    }

    previous_score = None
    for idx in range(1, cycles + 1):
        t0 = time.time()
        rc = run_all(apply=apply, passes=passes)
        report = read_json(REPORT_FILE, {})

        best_score = float((report.get("best") or {}).get("score", 0.0) or 0.0)
        pass_improvement = float(report.get("pass_improvement", 0.0) or 0.0)
        winner_pass = str(report.get("winner_pass", "pass1"))

        delta_vs_prev = None
        if previous_score is not None:
            delta_vs_prev = best_score - previous_score
        previous_score = best_score

        elapsed = time.time() - t0
        cycle_row = {
            "cycle": idx,
            "timestamp_utc": now_utc(),
            "return_code": rc,
            "best_score": best_score,
            "winner_pass": winner_pass,
            "pass_improvement": pass_improvement,
            "delta_vs_prev_cycle": delta_vs_prev,
            "elapsed_sec": round(elapsed, 3),
            "status": "ok" if rc == 0 else "failed",
        }
        history["cycles"].append(cycle_row)

        atomic_write_json(LOOP_FILE, history, indent=2)

        print(f"[EVOLUTIONARY-LOOP] cycle={idx}/{cycles} rc={rc} best_score={best_score:.5f} winner={winner_pass} pass_impr={pass_improvement}")

        if rc != 0:
            history["ended_utc"] = now_utc()
            history["status"] = "failed"
            atomic_write_json(LOOP_FILE, history, indent=2)
            return rc

        if idx < cycles and interval_sec > 0:
            time.sleep(interval_sec)

    history["ended_utc"] = now_utc()
    history["status"] = "ok"
    atomic_write_json(LOOP_FILE, history, indent=2)
    print(f"[EVOLUTIONARY-LOOP] complete | history={LOOP_FILE}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repeated two-pass optimization cycles")
    parser.add_argument("--cycles", type=int, default=2, help="Number of optimization cycles")
    parser.add_argument("--interval-sec", type=float, default=1.0, help="Sleep interval between cycles")
    parser.add_argument("--apply", action="store_true", help="Apply mode (subject to all stage guardrails)")
    parser.add_argument("--passes", type=int, default=2, help="Optimizer passes per cycle (recommended 2)")
    args = parser.parse_args()

    cycles = max(1, args.cycles)
    passes = max(1, min(args.passes, 2))
    return run_loop(cycles=cycles, interval_sec=max(0.0, args.interval_sec), apply=args.apply, passes=passes)


if __name__ == "__main__":
    raise SystemExit(main())
