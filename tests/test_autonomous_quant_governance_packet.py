from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_AUTONOMOUS_QUANT_GOVERNANCE_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("autonomous_quant_governance_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_autonomous_quant_governance_packet_is_ready_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "autonomous_quant_governance_packet_v1"
    assert payload["status"] == "AUTONOMOUS_QUANT_GOVERNANCE_READY_HUMAN_RUNTIME_REQUIRED"
    assert summary["reviewer_gate_clear"] is True
    assert summary["unsafe_sensitive_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert summary["all_final_actions_blocked_without_human"] is True
    assert summary["global_runtime_paper"] is True
    assert summary["global_live_orders_disabled"] is True
    assert summary["execution_status_paper"] is True
    assert summary["account_live_orders_disabled"] is True
    assert summary["all_agents_require_approval"] is True
    assert summary["auto_fire_enabled_count"] == 0
    assert summary["capital_movement_allowed"] is False
    assert summary["order_placement_allowed"] is False


def test_runtime_snapshot_captures_accounts_agents_and_markers():
    module = load_module()
    payload = module.build_payload()
    snapshot = payload["runtime_snapshot"]

    assert snapshot["global_runtime"]["mode"] == "paper"
    assert snapshot["global_runtime"]["allow_live_orders"] is False
    assert snapshot["execution_status"]["execution_mode"] == "paper"
    assert snapshot["execution_status"]["live_arm"].upper() == "OFF"
    assert len(snapshot["account_runtimes"]) >= 2
    assert all(not bool(row.get("allow_live_orders")) for row in snapshot["account_runtimes"])
    assert len(snapshot["agent_registry"]) >= 5
    assert all(row["requires_approval"] for row in snapshot["agent_registry"])
    assert all(not row["auto_fire"] for row in snapshot["agent_registry"])
    assert len(snapshot["runtime_markers"]) >= 3
    assert payload["summary"]["runtime_marker_reconciliation_count"] >= 0


def test_autonomous_quant_packet_evidence_sources_are_present_and_hashed():
    module = load_module()
    payload = module.build_payload()
    evidence_by_name = {Path(row["path"]).name: row for row in payload["evidence_status"]}

    for name in [
        "AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
        "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "HUMAN_ACTION_DOCKET_2026-07-09.md",
        "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        "runtime_control.json",
        "execution_status.json",
        "autonomous_agent_manifest.py",
    ]:
        assert name in evidence_by_name
        assert evidence_by_name[name]["present"] is True
        assert evidence_by_name[name]["bytes"] > 0
        assert len(evidence_by_name[name]["sha256"]) == 64


def test_rendered_packet_keeps_risky_public_claims_out():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "capital movement allowed: `false`" in lowered
    assert "order placement allowed: `false`" in lowered
    assert "external system action without human: `false`" in lowered
    for phrase in [
        "live profit",
        "guaranteed returns",
        "risk-free",
        "autonomous trading system ready",
        "field validated",
        "realized savings",
    ]:
        assert phrase not in lowered
    for marker in [
        "zoom.us",
        "meeting id",
        "password",
        "one tap mobile",
        "private key",
        "refresh_token",
        "client_secret",
        "api_key",
    ]:
        assert marker not in lowered
