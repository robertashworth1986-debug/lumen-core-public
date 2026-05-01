import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"
CONFIG = ROOT / "config"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    report = OUT / "time_travel_burst_report.json"
    audit = OUT / "time_travel_burst_audit.json"
    patch = CONFIG / "runtime_time_travel_patch.json"
    policy = CONFIG / "time_travel_bursts.json"

    policy_data = _load(policy) if policy.exists() else {}
    mutation_cfg = (policy_data or {}).get("adaptive_mutation", {}) or {}
    mutation_enabled = bool(mutation_cfg.get("enabled", False))
    history_file = ROOT / str(mutation_cfg.get("mutation_history_file", "out/execution/time_travel_burst_history.json"))

    missing = [str(p) for p in [report, audit, patch] if not p.exists()]
    if mutation_enabled and not history_file.exists():
        missing.append(str(history_file))
    if missing:
        print("[BURST-SMOKE] missing files")
        for m in missing:
            print(f"  - {m}")
        return 1

    r = _load(report)
    a = _load(audit)
    p = _load(patch)
    h = _load(history_file) if mutation_enabled else {"runs": []}

    miss_r = [k for k in ["timestamp_utc", "windows_total", "best", "recommended_patch"] if k not in r]
    miss_a = [k for k in ["timestamp_utc", "inputs", "outputs", "applied"] if k not in a]
    miss_p = [k for k in ["time_travel_burst_active", "time_travel_burst_best_score"] if k not in p]
    miss_h = [k for k in ["runs"] if k not in h] if mutation_enabled else []

    if mutation_enabled:
        miss_r.extend([k for k in ["mutation_enabled", "mutation_mode", "mutation_reason", "shock_brake", "shock_autotune", "mutation_state", "mutated_burst"] if k not in r])
        if not isinstance(h.get("runs", []), list) or len(h.get("runs", [])) == 0:
            miss_h.append("runs_non_empty")
        else:
            last = h.get("runs", [])[-1]
            miss_h.extend([k for k in ["mutation_mode", "mutation_reason", "shock_brake", "shock_autotune", "mutation_state"] if k not in last])

    if miss_r or miss_a or miss_p or miss_h:
        print("[BURST-SMOKE] FAIL")
        print(f"  missing_report: {miss_r}")
        print(f"  missing_audit: {miss_a}")
        print(f"  missing_patch: {miss_p}")
        print(f"  missing_history: {miss_h}")
        return 2

    print("[BURST-SMOKE] PASS")
    print(f"  windows_total: {r.get('windows_total')}")
    print(f"  best_score: {p.get('time_travel_burst_best_score')}")
    print(f"  best_win_rate: {p.get('time_travel_burst_best_win_rate')}")
    if mutation_enabled:
        print(f"  mutation_mode: {r.get('mutation_mode')}")
        print(f"  mutation_reason: {r.get('mutation_reason')}")
        print(f"  shock_triggered: {(r.get('shock_brake') or {}).get('triggered')}")
        print(f"  shock_autotune_action: {(r.get('shock_autotune') or {}).get('action')}")
        print(f"  mutation_runs: {len(h.get('runs', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
