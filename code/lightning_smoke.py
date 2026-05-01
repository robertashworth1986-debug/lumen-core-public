import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    fdelta = OUT / "lightning_frozen_delta.json"
    rem = OUT / "lightning_remediation.json"

    if not fdelta.exists() or not rem.exists():
        print("[LIGHTNING-SMOKE] missing files; run lightning.py first")
        return 1

    fd = _load(fdelta)
    rm = _load(rem)

    req_fd = ["timestamp_utc", "constraint_count", "delta_count", "mode_after", "live_after", "constraints"]
    req_rm = ["when", "where", "why", "what", "fix"]

    missing_fd = [k for k in req_fd if k not in fd]
    missing_rm = [k for k in req_rm if k not in rm]

    if missing_fd or missing_rm:
        print("[LIGHTNING-SMOKE] FAIL")
        print(f"  missing_frozen_delta: {missing_fd}")
        print(f"  missing_remediation: {missing_rm}")
        return 2

    print("[LIGHTNING-SMOKE] PASS")
    print(f"  constraints: {fd.get('constraint_count')}")
    print(f"  delta_count: {fd.get('delta_count')}")
    print(f"  mode_after: {fd.get('mode_after')} | live: {fd.get('live_after')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
