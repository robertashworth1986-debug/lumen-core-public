from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PROOF_TO_PILOT_CONTROL_ROOM.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "proof_to_pilot_control_room", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_control_room_reports_protocol_review_not_pilot_readiness():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "proof_to_pilot_control_room_v2"
    assert summary["family_count"] == 140
    assert summary["natural_path_family_count"] >= 50
    assert summary["natural_path_target_met"] is True
    assert summary["repeat_confirmation_eligible_count"] == 0
    assert summary["robust_candidate_count"] == 0
    assert summary["protocol_review_packet_count"] == 2
    assert summary["field_replay_candidate_count"] == 0
    assert summary["pilot_ready_count"] == 0
    assert summary["manual_outreach_ready_count"] == 0
    assert summary["current_commercial_stage"] == (
        "paid_protocol_review_scoping_ready_draft_only_no_recipient"
    )
    assert summary["top_family_ids"] == [
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
    ]
    assert len(summary["control_room_chain_sha256"]) == 64


def test_protocol_review_cards_preserve_failures_and_no_send_gate():
    module = load_module()
    payload = module.build_payload()
    cards = {
        row["family_id"]: row for row in payload["protocol_review_cards"]
    }

    assert set(cards) == {
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
    }
    brach = cards["brachistochrone_descent"]
    assert brach["evidence_stage"] == (
        "blocked_no_compatible_direct_measured_replay"
    )
    assert brach["field_replay_status"] == "blocked"
    assert "Protocol Review" in brach["title"]

    kuramoto = cards["kuramoto_phase_coupling"]
    assert kuramoto["evidence_stage"] == (
        "direct_measured_source_specific_baseline_gate_failed"
    )
    assert kuramoto["field_replay_status"] == "blocked"
    assert kuramoto["measured_reference"]["candidate"] == (
        "kuramoto_phase_coupling"
    )
    assert kuramoto["measured_reference"]["holdout_count"] == 1525
    assert kuramoto["measured_reference"]["wins_vs_named_baseline"] == 482
    assert kuramoto["measured_reference"][
        "mean_delta_vs_named_baseline"
    ] == -0.508190706
    assert kuramoto["measured_reference"]["all_baseline_gate_passed"] is False

    for card in cards.values():
        assert len(card["reviewer_roles"]) >= 3
        assert len(card["source_and_baseline_controls"]["data_checklist"]) >= 5
        assert len(card["source_and_baseline_controls"]["baseline_controls"]) >= 5
        assert len(card["data_room_artifacts"]) >= 5
        assert len(card["deliverables"]) >= 6
        assert len(card["next_actions"]) >= 5
        assert len(card["card_sha256"]) == 64
        gate = card["claim_gate"]
        assert gate["paid_protocol_review_scoping_allowed"] is True
        assert gate["pilot_ready"] is False
        assert gate["field_replay_request_allowed"] is False
        assert gate["manual_outreach_allowed"] is False
        assert gate["send_allowed"] is False
        assert gate["exact_action_time_approval_required"] is True


def test_control_room_keeps_all_external_claim_gates_closed():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    text = json.dumps(payload).lower()

    assert summary["internal_performance_champion_present"] is False
    assert summary["paid_protocol_review_scoping_allowed"] is True
    assert summary["manual_reviewed_outreach_allowed"] is False
    assert summary["paid_evaluation_offer_allowed"] is True
    assert summary["buyer_authorized_pilot_scoping_ready"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["bulk_email_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert summary["enterprise_valuation_asserted"] is False
    assert "fixed-dollar frozen-delta value" in text
    assert "award certainty" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text


def test_control_room_artifact_health_and_markdown_are_reviewer_safe():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert payload["summary"]["all_chain_docs_present"] is True
    assert len(payload["artifact_health"]) == 6
    assert all(row["exists"] for row in payload["artifact_health"])
    assert all(len(row["sha256"]) == 64 for row in payload["artifact_health"])

    assert "Proof To Protocol Review Control Room" in rendered
    assert "No current candidate is pilot-ready" in rendered
    assert "Repeat-eligible candidates: `0`" in rendered
    assert "Robust candidates: `0`" in rendered
    assert "Field-replay candidates: `0`" in rendered
    assert "Pilot-ready candidates: `0`" in rendered
    assert "Manual outreach ready: `0`" in rendered
    assert "Paid protocol-review scoping allowed: `true`" in rendered
    assert "Manual reviewed outreach allowed: `false`" in rendered
    assert "Field-validation claim allowed: `false`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "482" in rendered
    assert "-0.508190706" in rendered
    assert "24/24" not in rendered
    assert "manual paid-pilot outreach" not in lowered
