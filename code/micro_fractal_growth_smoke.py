import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"
CONFIG = ROOT / "config"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    report = OUT / "micro_fractal_growth_report.json"
    audit = OUT / "micro_fractal_growth_audit.json"
    patch = CONFIG / "runtime_fractal_patch.json"

    missing = [str(p) for p in [report, audit, patch] if not p.exists()]
    if missing:
        print("[FRACTAL-SMOKE] missing files")
        for m in missing:
            print(f"  - {m}")
        return 1

    r = _load(report)
    a = _load(audit)
    p = _load(patch)

    miss_r = [k for k in ["timestamp_utc", "recommended_patch"] if k not in r]
    miss_a = [k for k in ["timestamp_utc", "inputs", "outputs", "applied"] if k not in a]
    miss_p = [k for k in ["micro_fractal_growth_active", "micro_fractal_growth_factor"] if k not in p]

    if miss_r or miss_a or miss_p:
        print("[FRACTAL-SMOKE] FAIL")
        print(f"  missing_report: {miss_r}")
        print(f"  missing_audit: {miss_a}")
        print(f"  missing_patch: {miss_p}")
        return 2

    print("[FRACTAL-SMOKE] PASS")
    print(f"  growth_factor: {p.get('micro_fractal_growth_factor')}")
    print(f"  pass_improvement: {p.get('micro_fractal_pass_improvement')}")
    print(f"  winner_pass: {p.get('micro_fractal_winner_pass')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
