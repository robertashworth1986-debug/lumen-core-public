import json
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
OUT = ROOT / "out" / "execution"


def _load(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def main() -> int:
    decision = OUT / "super_sniper_decision.json"
    frozen = OUT / "frozen_deltas_super_sniper.json"

    if not decision.exists() or not frozen.exists():
        print("[SMOKE] missing files; run beast_mode.py first")
        return 1

    d = _load(decision)
    f = _load(frozen)

    required_decision = ["timestamp_utc", "sharp_value", "selected_symbol", "mode_after", "delta_count"]
    required_frozen = ["decision", "checksums", "delta"]

    missing_d = [k for k in required_decision if k not in d]
    missing_f = [k for k in required_frozen if k not in f]

    if missing_d or missing_f:
        print("[SMOKE] FAILED")
        print(f"  missing_decision_keys: {missing_d}")
        print(f"  missing_frozen_keys: {missing_f}")
        return 2

    print("[SMOKE] PASS")
    print(f"  sharp_value: {d.get('sharp_value')}")
    print(f"  selected_symbol: {d.get('selected_symbol')}")
    print(f"  mode_after: {d.get('mode_after')} | live: {d.get('live_after')}")
    print(f"  delta_count: {d.get('delta_count')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
