import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PAPER_EXECUTOR = ROOT / "code" / "execution" / "alpaca_paper_executor.py"
LIVE_GUARD = ROOT / "code" / "execution" / "live_runtime_guard.py"
LIVE_LAUNCHER = ROOT / "code" / "execution" / "RUN_LIVE_COMPOUNDING_STACK.ps1"
LIVE_SUPERVISOR = ROOT / "code" / "execution" / "SUPERVISE_LIVE_COMPOUNDING_STACK.ps1"
LEGACY_RUNTIME = ROOT / "code" / "execution" / "runtime_control.json"
LIVE_AUTHORITY = ROOT / "code" / "execution" / "live_action_authority.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_alpaca_paper_client_pins_canonical_hosts():
    module = load_module("alpaca_paper_executor_boundary", PAPER_EXECUTOR)

    client = module.AlpacaPaperClient("key", "secret")
    assert client.trading_base == "https://paper-api.alpaca.markets"
    assert client.data_base == "https://data.alpaca.markets"

    with pytest.raises(ValueError, match="paper-api.alpaca.markets"):
        module.AlpacaPaperClient(
            "key",
            "secret",
            trading_base="https://api.alpaca.markets",
        )

    with pytest.raises(ValueError, match="data.alpaca.markets"):
        module.AlpacaPaperClient(
            "key",
            "secret",
            data_base="https://example.invalid",
        )


def test_live_launcher_requires_fresh_bound_human_unlock_before_mutation():
    text = LIVE_LAUNCHER.read_text(encoding="utf-8")
    lowered = text.lower()

    guard_at = lowered.index("assert-liveexecutionhumanunlock")
    mutation_at = lowered.index('$runtime.mode = "live"')
    assert guard_at < mutation_at
    assert "luma_human_unlock_token" in lowered
    assert "arm lumencore live compounding" in lowered
    assert "expectedruntimesha256" in lowered
    assert "trading_stack_safety_audit_latest.json" in lowered
    assert 'safetyaudit.posture -cne "paper_ok"' in lowered
    assert "safetyaudit.blockers" in lowered
    assert "safetyauditageseconds -gt 300" in lowered
    assert "safety_audit_sha256" in lowered
    assert "single_live_stack_start" in lowered
    assert "reusable_for_restart = $false" in lowered


def test_live_supervisor_disarms_and_refuses_approval_reuse():
    text = LIVE_SUPERVISOR.read_text(encoding="utf-8").lower()

    assert '$actiontimeapproval = ""' in text
    assert '$expectedruntimesha256 = ""' in text
    assert "set-runtimefailclosed" in text
    assert "fresh_action_time_approval_required_for_restart" in text
    assert "automatic restart is blocked" in text


def test_legacy_runtime_copy_is_explicitly_non_authoritative_and_disarmed():
    runtime = json.loads(LEGACY_RUNTIME.read_text(encoding="utf-8"))

    assert runtime["authoritative"] is False
    assert runtime["canonical_runtime_path"] == "config/runtime_control.json"
    assert runtime["mode"] == "paper"
    assert runtime["allow_live_orders"] is False
    assert runtime["paper_enabled"] is True
    assert runtime["kill_switch"] is True
    assert runtime["gate_override_enabled"] is False


def test_live_runtime_guard_rejects_every_partial_arm_state():
    module = load_module("live_runtime_guard_boundary", LIVE_GUARD)
    guard = module.LiveRuntimeGuard(ROOT)
    safe_metrics = {
        "realized_pnl_total": 0.0,
        "portfolio_heat": 0.0,
        "open_positions": 0,
    }

    cases = [
        ({"mode": "paper", "allow_live_orders": False, "paper_enabled": True, "kill_switch": False}, "live_orders_not_armed"),
        ({"mode": "live", "allow_live_orders": False, "paper_enabled": False, "kill_switch": False}, "live_orders_not_armed"),
        ({"mode": "live", "allow_live_orders": True, "paper_enabled": True, "kill_switch": False}, "paper_mode_conflict"),
        ({"mode": "live", "allow_live_orders": True, "paper_enabled": False, "kill_switch": True}, "kill_switch_enabled"),
    ]
    for runtime, expected_reason in cases:
        allowed, reason = guard.can_place_live_order(runtime, **safe_metrics)
        assert allowed is False
        assert reason == expected_reason


def test_fully_armed_runtime_still_requires_fresh_hash_bound_action_receipt(tmp_path):
    guard_module = load_module("live_runtime_guard_receipt_boundary", LIVE_GUARD)
    authority_module = load_module("live_action_authority_receipt_boundary", LIVE_AUTHORITY)
    root = tmp_path / "stack"
    runtime_path = root / "config" / "runtime_control.json"
    runtime_path.parent.mkdir(parents=True, exist_ok=True)
    runtime_path.write_text(
        json.dumps(
            {
                "mode": "live",
                "allow_live_orders": True,
                "paper_enabled": False,
                "kill_switch": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    guard = guard_module.LiveRuntimeGuard(root)
    runtime = guard.load()
    metrics = {"realized_pnl_total": 0.0, "portfolio_heat": 0.0, "open_positions": 0}

    allowed, reason = guard.can_place_live_order(runtime, **metrics)

    assert allowed is False
    assert reason == "action_time_authority_required:action_receipt_missing"

    guard.action_receipt_file.parent.mkdir(parents=True, exist_ok=True)
    guard.action_receipt_file.write_text(
        json.dumps(
            {
                "schema": "live_action_time_approval_receipt_v1",
                "generated_utc": datetime.now(timezone.utc).isoformat(),
                "controller": "Robert",
                "human_unlock_verified": True,
                "exact_action_time_phrase_verified": True,
                "armed_runtime_sha256": authority_module.sha256_file(runtime_path),
                "runtime_control_path": "config/runtime_control.json",
                "authorization_scope": "single_live_stack_start",
                "reusable_for_restart": False,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    allowed, reason = guard.can_place_live_order(runtime, **metrics)

    assert allowed is True
    assert reason == "live_orders_armed"
