from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\LumaTrader\INSTITUTIONAL_STACK_V2")
EXECUTION = ROOT / "code" / "execution"
CONFIG = ROOT / "config"
OUT = ROOT / "out"

LEGACY_RUNTIME_CONTROL = EXECUTION / "runtime_control.json"
RUNTIME_CONTROL = CONFIG / "runtime_control.json"
PAPER_RUNTIME = CONFIG / "paper_trader_runtime.json"
LIVE_ARM_CONFIRM = CONFIG / "live_arm.confirm"
PROOF_FILE = OUT / "paper_go_live_proof.json"

LIVE_ARM_PHRASE = "ARM_LIVE_SUPER_SNIPER"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def arm_live_mode() -> dict:
    raise RuntimeError(
        "RETIRED_LIVE_ARMING: repository policy permits live market data and "
        "paper execution only"
    )


def arm_paper_runtime() -> dict:
    runtime = load_json(PAPER_RUNTIME, {})
    runtime["generated_utc"] = now_iso()
    runtime["mode"] = "paper"
    runtime["paper_enabled"] = True
    runtime["allow_live_orders"] = False
    runtime["kill_switch"] = False
    runtime["gate_override_enabled"] = False
    runtime.setdefault("starting_capital_usd", 100000.0)
    runtime.setdefault("loop_seconds", 300)
    save_json(PAPER_RUNTIME, runtime)
    return {"path": str(PAPER_RUNTIME), "content": runtime}


def create_live_arm_confirm() -> dict:
    raise RuntimeError("RETIRED_LIVE_ARMING: confirmation files are not generated")


def write_proof(runtime_control: dict, paper_runtime: dict, confirm: dict) -> None:
    raise RuntimeError("RETIRED_LIVE_ARMING: live proof artifacts are not generated")


def main() -> int:
    print("REFUSED: legacy live arming script is retired.")
    print("It mixed paper and live flags, enabled gate overrides, and wrote a")
    print("confirmation file without validating heartbeats, balances, or risk.")
    print("Use the institutional live executor readiness workflow instead.")
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
