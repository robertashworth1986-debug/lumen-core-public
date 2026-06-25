from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py"


def load_module():
    spec = importlib.util.spec_from_file_location("proof_to_pilot_control_room", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_control_room_aggregates_full_proof_to_pilot_chain():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "proof_to_pilot_control_room_v1"
    assert summary["family_count"] >= 140
    assert summary["natural_path_family_count"] >= 50
    assert summary["natural_path_target_met"] is True
    assert summary["robust_candidate_count"] == 2
    assert summary["pilot_packet_count"] == 2
    assert summary["manual_outreach_ready_count"] == 2
    assert summary["current_commercial_stage"] == "paid_evaluation_scoping_ready_not_field_validated"
    assert summary["top_family_ids"] == ["brachistochrone_descent", "kuramoto_phase_coupling"]
    assert len(summary["control_room_chain_sha256"]) == 64


def test_control_room_cards_have_actionable_pilot_wiring():
    module = load_module()
    payload = module.build_payload()
    cards = {row["family_id"]: row for row in payload["top_cards"]}

    assert set(cards) == {"brachistochrone_descent", "kuramoto_phase_coupling"}
    brach = cards["brachistochrone_descent"]
    assert brach["lane"] == "optimal_curve_transport"
    assert brach["commercial_stage"] == "manual_paid_pilot_outreach_ready"
    assert brach["repeat_window_evidence"]["wins"] == 6
    assert brach["repeat_window_evidence"]["windows"] == 6
    assert brach["repeat_window_evidence"]["min_source_count"] >= 5
    assert "Constrained Transport" in brach["email_subject"]

    kuramoto = cards["kuramoto_phase_coupling"]
    assert kuramoto["lane"] == "wave_resonance_timing"
    assert kuramoto["repeat_window_evidence"]["wins"] == 6
    assert kuramoto["repeat_window_evidence"]["windows"] == 6
    assert kuramoto["repeat_window_evidence"]["min_source_count"] >= 4
    assert "Resonance Timing" in kuramoto["email_subject"]

    for card in cards.values():
        assert len(card["buyer_targets"]) >= 5
        assert len(card["data_room_artifacts"]) >= 5
        assert len(card["next_actions"]) >= 5
        assert len(card["unlock_conditions"]) >= 5
        assert len(card["card_sha256"]) == 64


def test_control_room_keeps_claim_gates_closed_except_manual_pilot_outreach():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    text = json.dumps(payload).lower()

    assert summary["manual_reviewed_outreach_allowed"] is True
    assert summary["paid_evaluation_offer_allowed"] is True
    assert summary["buyer_authorized_pilot_scoping_ready"] is True
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert "fixed-dollar frozen-delta value" in text
    assert "award certainty" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text

    for card in payload["top_cards"]:
        gate = card["claim_gate"]
        assert gate["manual_outreach_allowed"] is True
        assert gate["paid_evaluation_offer_allowed"] is True
        assert gate["field_validation_claim_allowed"] is False
        assert gate["realized_savings_claim_allowed"] is False
        assert gate["fixed_dollar_delta_claim_allowed"] is False
        assert gate["bulk_email_allowed"] is False
        assert gate["live_trading_or_autonomous_execution_allowed"] is False


def test_control_room_artifact_health_and_markdown_are_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)

    assert payload["summary"]["all_chain_docs_present"] is True
    assert len(payload["artifact_health"]) >= 6
    assert all(row["exists"] for row in payload["artifact_health"])
    assert all(len(row["sha256"]) == 64 for row in payload["artifact_health"])

    assert "Proof To Pilot Control Room" in rendered
    assert "Manual reviewed outreach allowed: `true`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "Fixed-dollar delta claim allowed: `false`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "Real-dollar claims remain blocked" in rendered
