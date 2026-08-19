import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "execution" / "approval_autofire_daemon.py"


def load_module():
    spec = importlib.util.spec_from_file_location("approval_autofire_authority", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def live_runtime() -> dict:
    return {
        "mode": "live",
        "allow_live_orders": True,
        "paper_enabled": False,
        "kill_switch": False,
    }


def valid_receipt(module, runtime_path: Path, generated_utc: str) -> dict:
    return {
        "schema": "live_action_time_approval_receipt_v1",
        "generated_utc": generated_utc,
        "controller": "Robert",
        "human_unlock_verified": True,
        "exact_action_time_phrase_verified": True,
        "armed_runtime_sha256": module.sha256_file(runtime_path),
        "runtime_control_path": "config/runtime_control.json",
        "authorization_scope": "single_live_stack_start",
        "reusable_for_restart": False,
    }


def test_paper_runtime_and_missing_receipt_fail_closed(tmp_path):
    module = load_module()
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    write_json(
        runtime_path,
        {
            "mode": "paper",
            "allow_live_orders": False,
            "paper_enabled": True,
            "kill_switch": True,
        },
    )

    authority = module.autofire_authority_state(runtime_path, receipt_path, "Robert")

    assert authority["authorized"] is False
    assert "runtime_mode_not_live" in authority["reasons"]
    assert "live_orders_not_armed" in authority["reasons"]
    assert "paper_mode_conflict" in authority["reasons"]
    assert "kill_switch_enabled" in authority["reasons"]
    assert "action_receipt_missing" in authority["reasons"]


def test_fresh_hash_bound_one_time_receipt_is_authorized(tmp_path):
    module = load_module()
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    now = datetime(2026, 8, 19, 18, 0, tzinfo=timezone.utc)
    write_json(runtime_path, live_runtime())
    write_json(receipt_path, valid_receipt(module, runtime_path, (now - timedelta(seconds=10)).isoformat()))

    authority = module.autofire_authority_state(
        runtime_path,
        receipt_path,
        "Robert",
        ttl_seconds=300,
        now=now,
    )

    assert authority["authorized"] is True
    assert authority["reasons"] == []
    assert authority["receipt_age_sec"] == 10.0


def test_stale_receipt_is_rejected(tmp_path):
    module = load_module()
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    now = datetime(2026, 8, 19, 18, 0, tzinfo=timezone.utc)
    write_json(runtime_path, live_runtime())
    write_json(receipt_path, valid_receipt(module, runtime_path, (now - timedelta(seconds=301)).isoformat()))

    authority = module.autofire_authority_state(
        runtime_path,
        receipt_path,
        "Robert",
        ttl_seconds=300,
        now=now,
    )

    assert authority["authorized"] is False
    assert "action_receipt_expired" in authority["reasons"]


def test_receipt_cannot_be_reused_after_runtime_changes(tmp_path):
    module = load_module()
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    now = datetime(2026, 8, 19, 18, 0, tzinfo=timezone.utc)
    write_json(runtime_path, live_runtime())
    receipt = valid_receipt(module, runtime_path, now.isoformat())
    write_json(receipt_path, receipt)
    changed = live_runtime()
    changed["max_notional_per_trade_usd"] = 1.0
    write_json(runtime_path, changed)

    authority = module.autofire_authority_state(runtime_path, receipt_path, "Robert", now=now)

    assert authority["authorized"] is False
    assert "action_receipt_runtime_hash_mismatch" in authority["reasons"]


def test_reusable_or_wrong_controller_receipt_is_rejected(tmp_path):
    module = load_module()
    runtime_path = tmp_path / "config" / "runtime_control.json"
    receipt_path = tmp_path / "out" / "execution" / "receipt.json"
    now = datetime(2026, 8, 19, 18, 0, tzinfo=timezone.utc)
    write_json(runtime_path, live_runtime())
    receipt = valid_receipt(module, runtime_path, now.isoformat())
    receipt["reusable_for_restart"] = True
    receipt["controller"] = "AnotherOperator"
    write_json(receipt_path, receipt)

    authority = module.autofire_authority_state(runtime_path, receipt_path, "Robert", now=now)

    assert authority["authorized"] is False
    assert "action_receipt_reusable_or_unspecified" in authority["reasons"]
    assert "action_receipt_controller_mismatch" in authority["reasons"]


def test_authority_gate_precedes_every_gateway_read_in_main():
    main_source = SCRIPT.read_text(encoding="utf-8").split("def main()", maxsplit=1)[1]

    gate_at = main_source.index("authority = autofire_authority_state")
    disarmed_continue_at = main_source.index("continue", gate_at)
    first_queue_read_at = main_source.index("queue_payload = request_json")
    decision_gate_at = main_source.index("decision_authority = autofire_authority_state")
    approval_post_at = main_source.index('f"{gateway_url}/api/master/approval/decide"')

    assert gate_at < disarmed_continue_at < first_queue_read_at
    assert decision_gate_at < approval_post_at
