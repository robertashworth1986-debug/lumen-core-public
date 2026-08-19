import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_LOCK = ROOT / "code" / "runtime_live_lock.py"
RISK_AUDIT = ROOT / "code" / "ops" / "BUILD_TRADING_CODE_RISK_AUDIT.py"
REBUILD = ROOT / "code" / "REBUILD_FULL_ADAPTIVE_LIVE_STACK.py"
DISCOVER = ROOT / "code" / "DISCOVER_AND_ROUTE_ALL_LIVE_KEYS.py"
ADAPTIVE = ROOT / "code" / "BUILD_ADAPTIVE_UNIVERSE_FROM_LIVE_KEYS.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def armed_runtime() -> dict:
    return {
        "mode": "live",
        "allow_live_orders": True,
        "paper_enabled": False,
        "kill_switch": False,
        "strict_live_only": True,
    }


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_strict_live_flags_are_not_authority_without_fresh_receipt(tmp_path):
    module = load_module("runtime_live_lock_missing_receipt", RUNTIME_LOCK)
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    runtime = armed_runtime()
    write_json(runtime_path, runtime)

    state = module.human_action_time_authority_state(
        runtime_control=runtime,
        runtime_path=runtime_path,
        receipt_path=receipt_path,
    )

    assert state["strict_live_requested"] is True
    assert state["authorized_strict_live_lock"] is False
    assert "action_receipt_missing" in state["reasons"]


def test_hash_bound_fresh_receipt_authorizes_read_only_live_preservation(tmp_path):
    module = load_module("runtime_live_lock_valid_receipt", RUNTIME_LOCK)
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    runtime = armed_runtime()
    write_json(runtime_path, runtime)
    runtime_sha = hashlib.sha256(runtime_path.read_bytes()).hexdigest()
    write_json(
        receipt_path,
        {
            "schema": "live_action_time_approval_receipt_v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "controller": "test-controller",
            "human_unlock_verified": True,
            "exact_action_time_phrase_verified": True,
            "authorization_scope": "single_live_stack_start",
            "reusable_for_restart": False,
            "runtime_control_path": "config/runtime_control.json",
            "armed_runtime_sha256": runtime_sha,
        },
    )

    state = module.human_action_time_authority_state(
        runtime_control=runtime,
        runtime_path=runtime_path,
        receipt_path=receipt_path,
    )

    assert state["authorized"] is True
    assert state["authorized_strict_live_lock"] is True


def test_rebuild_and_discovery_scripts_no_longer_write_live_arm_flags():
    audit = load_module("risk_audit_runtime_writers", RISK_AUDIT)

    for path in (REBUILD, DISCOVER, ADAPTIVE):
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        hits = audit.pattern_hits(source)
        assert "live_arm_write" not in hits, path.name
        assert "kill_switch_off_write" not in hits, path.name
        assert "human_action_time_authority_state" in source
        assert "live_runtime_preserved_read_only" in source


def test_separate_paper_runtime_remains_paper_even_during_live_preservation():
    rebuild = REBUILD.read_text(encoding="utf-8")

    assert 'paper_runtime["mode"] = "paper"' in rebuild
    assert 'paper_runtime["paper_enabled"] = True' in rebuild
    if DISCOVER.exists():
        discover = DISCOVER.read_text(encoding="utf-8")
        assert 'paper_runtime["paper_enabled"] = True' in discover
    if ADAPTIVE.exists():
        adaptive = ADAPTIVE.read_text(encoding="utf-8")
        assert 'paper["runtime_mode"] = "paper"' in adaptive
        assert 'paper["paper_enabled"] = True' in adaptive
