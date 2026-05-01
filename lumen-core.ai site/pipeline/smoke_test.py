import json
from pathlib import Path


SITE_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = SITE_ROOT / "public"
DATA_DIR = PUBLIC_DIR / "data"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    required_files = [
        PUBLIC_DIR / "index.html",
        DATA_DIR / "health.json",
        DATA_DIR / "runtime.json",
        DATA_DIR / "profile.json",
        DATA_DIR / "portfolio.json",
        DATA_DIR / "trades_recent.json",
        DATA_DIR / "audit_recent.json",
        DATA_DIR / "build_info.json",
    ]

    missing = [str(path) for path in required_files if not path.exists()]
    if missing:
        raise SystemExit(f"❌ Missing required output files:\n- " + "\n- ".join(missing))

    health = _read_json(DATA_DIR / "health.json")
    runtime = _read_json(DATA_DIR / "runtime.json")
    trades_recent = _read_json(DATA_DIR / "trades_recent.json")
    audit_recent = _read_json(DATA_DIR / "audit_recent.json")

    assert "runtime_mode" in health, "health.json missing runtime_mode"
    assert "allow_live_orders" in health, "health.json missing allow_live_orders"
    assert isinstance(trades_recent.get("items", []), list), "trades_recent.items must be list"
    assert isinstance(audit_recent.get("items", []), list), "audit_recent.items must be list"
    assert "execution_runtime" in runtime, "runtime.json missing execution_runtime"

    print("✅ Smoke test passed")
    print(f"   Verified files: {len(required_files)}")
    print(f"   Runtime mode:   {health.get('runtime_mode')}")
    print(f"   Recent trades:  {len(trades_recent.get('items', []))}")
    print(f"   Recent events:  {len(audit_recent.get('items', []))}")


if __name__ == "__main__":
    main()
