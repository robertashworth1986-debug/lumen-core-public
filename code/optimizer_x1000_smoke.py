import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"
CONFIG = ROOT / "config"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    report = OUT / "optimizer_x1000_report.json"
    sim = OUT / "optimizer_x1000_simulation.json"
    patch = CONFIG / "runtime_optimized_patch.json"

    missing = [str(p) for p in [report, sim, patch] if not p.exists()]
    if missing:
        print("[X1000-SMOKE] missing files")
        for m in missing:
            print(f"  - {m}")
        return 1

    r = _load(report)
    s = _load(sim)
    p = _load(patch)

    req_report = ["timestamp_utc", "trials_total", "best", "recommended_patch"]
    req_patch = ["base_risk_fraction", "loop_seconds", "max_position_usd", "optimizer_x1000_active"]

    miss_r = [k for k in req_report if k not in r]
    miss_p = [k for k in req_patch if k not in p]

    if miss_r or miss_p:
        print("[X1000-SMOKE] FAIL")
        print(f"  missing_report_keys: {miss_r}")
        print(f"  missing_patch_keys: {miss_p}")
        return 2

    top_trials = s.get("top_trials", [])
    print("[X1000-SMOKE] PASS")
    print(f"  trials_total: {r.get('trials_total')}")
    print(f"  best_score: {r.get('best', {}).get('score')}")
    print(f"  recommended_loop_seconds: {p.get('loop_seconds')}")
    print(f"  top_trials_count: {len(top_trials)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
