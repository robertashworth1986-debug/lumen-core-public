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
    runtime = load_json(RUNTIME_CONTROL, {})
    runtime["generated_utc"] = now_iso()
    runtime["mode"] = "live"
    runtime["allow_live_orders"] = True
    runtime["kill_switch"] = False
    runtime["gate_override_enabled"] = True
    runtime.setdefault("initial_capital", 219.0)
    save_json(RUNTIME_CONTROL, runtime)

    # Maintain backward compatibility for legacy execution-only runtime files.
    legacy_runtime = load_json(LEGACY_RUNTIME_CONTROL, {})
    legacy_runtime.update({
        "generated_utc": runtime["generated_utc"],
        "mode": runtime["mode"],
        "allow_live_orders": runtime["allow_live_orders"],
        "kill_switch": runtime["kill_switch"],
        "gate_override_enabled": runtime["gate_override_enabled"],
    })
    if "initial_capital" not in legacy_runtime:
        legacy_runtime["initial_capital"] = runtime["initial_capital"]
    save_json(LEGACY_RUNTIME_CONTROL, legacy_runtime)

    return {"path": str(RUNTIME_CONTROL), "content": runtime}


def arm_paper_runtime() -> dict:
    runtime = load_json(PAPER_RUNTIME, {})
    runtime["generated_utc"] = now_iso()
    runtime["mode"] = "live"
    runtime["paper_enabled"] = True
    runtime["allow_live_orders"] = True
    runtime["kill_switch"] = False
    runtime.setdefault("starting_capital_usd", 100000.0)
    runtime.setdefault("loop_seconds", 300)
    save_json(PAPER_RUNTIME, runtime)
    return {"path": str(PAPER_RUNTIME), "content": runtime}


def create_live_arm_confirm() -> dict:
    save_text(LIVE_ARM_CONFIRM, f"{LIVE_ARM_PHRASE}\n")
    return {"path": str(LIVE_ARM_CONFIRM), "phrase": LIVE_ARM_PHRASE}


def write_proof(runtime_control: dict, paper_runtime: dict, confirm: dict) -> None:
    proof = {
        "generated_utc": now_iso(),
        "runtime_control": runtime_control,
        "paper_runtime": paper_runtime,
        "live_arm_confirm": confirm,
        "status": "live_configured",
        "note": "Runtime flags set to live and allow_live_orders enabled. This file is a bootstrapped live-arm proof artifact.",
    }
    save_json(PROOF_FILE, proof)


def main() -> int:
    runtime_control = arm_live_mode()
    paper_runtime = arm_paper_runtime()
    confirm = create_live_arm_confirm()
    write_proof(runtime_control, paper_runtime, confirm)

    print("=== LIVE PAPER TRADER ARMING COMPLETE ===")
    print(f"Runtime control updated: {runtime_control['path']}")
    print(f"Paper runtime updated: {paper_runtime['path']}")
    print(f"Live arm confirm file: {confirm['path']}")
    print(f"Proof artifact: {PROOF_FILE}")
    print("")
    print("Next step: run RUN_ALPACA_PAPER_247.ps1 to start the live paper loop.")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
