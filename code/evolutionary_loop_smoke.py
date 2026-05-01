import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    loop_file = OUT / "evolutionary_loop_history.json"
    report_file = OUT / "optimizer_x1000_report.json"

    if not loop_file.exists() or not report_file.exists():
        print("[EVO-SMOKE] missing outputs; run evolutionary_loop.py first")
        return 1

    loop = _load(loop_file)
    report = _load(report_file)

    missing_loop = [k for k in ["started_utc", "cycles", "status"] if k not in loop]
    missing_report = [k for k in ["passes", "winner_pass", "pass_improvement", "best"] if k not in report]

    if missing_loop or missing_report:
        print("[EVO-SMOKE] FAIL")
        print(f"  missing_loop: {missing_loop}")
        print(f"  missing_report: {missing_report}")
        return 2

    cycles = loop.get("cycles", [])
    print("[EVO-SMOKE] PASS")
    print(f"  cycles_recorded: {len(cycles)}")
    print(f"  loop_status: {loop.get('status')}")
    print(f"  winner_pass: {report.get('winner_pass')}")
    print(f"  pass_improvement: {report.get('pass_improvement')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
