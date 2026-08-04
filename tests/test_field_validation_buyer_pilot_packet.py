from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT
    / "code"
    / "ops"
    / "BUILD_FIELD_VALIDATION_BUYER_PILOT_PACKET.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "field_validation_buyer_pilot_packet", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_packet_builds_two_protocol_reviews_and_zero_outreach_tracks():
    payload = load_module().build_payload()
    info = payload["summary"]
    by_family = {row["family_id"]: row for row in payload["packets"]}

    assert payload["schema"] == "field_validation_buyer_pilot_packet_v2"
    assert info["packet_count"] == 2
    assert info["protocol_review_packet_count"] == 2
    assert info["manual_outreach_ready_count"] == 0
    assert info["field_replay_candidate_count"] == 0
    assert info["internal_performance_champion_count"] == 0
    assert len(info["packet_chain_sha256"]) == 64
    assert set(by_family) == {
        "brachistochrone_descent",
        "kuramoto_phase_coupling",
    }

    brach = by_family["brachistochrone_descent"]
    assert brach["evidence_stage"] == "blocked_no_compatible_direct_measured_replay"
    assert brach["field_replay_request"]["current_status"] == "blocked"
    assert brach["latest_repeat_evidence"]["repeat_live_win_count"] == 0

    kuramoto = by_family["kuramoto_phase_coupling"]
    assert (
        kuramoto["evidence_stage"]
        == "direct_measured_source_specific_baseline_gate_failed"
    )
    assert kuramoto["field_replay_request"]["current_status"] == "blocked"


def test_protocol_packets_have_bounded_service_scope_and_review_outputs():
    payload = load_module().build_payload()

    for packet in payload["packets"]:
        offer = packet["paid_offer"]
        assert (
            offer["offer_type"]
            == "paid source-native benchmark and evidence protocol review"
        )
        assert offer["price_range_usd"] == {"low": 3500, "high": 3500}
        assert offer["duration_business_days"] == 10
        assert offer["fee_status"] == "candidate_not_committed"
        assert offer["founder_approved"] is False
        assert offer["buyer_accepted"] is False
        assert "Do not sell a winning candidate" in offer["safe_positioning"]
        assert len(packet["deliverables"]) >= 6
        assert len(packet["data_room_artifacts"]) >= 5
        assert len(packet["buyer_data_checklist"]) >= 5
        assert len(packet["baseline_controls"]) >= 5
        assert len(packet["primary_kpis"]) >= 4
        assert len(packet["pre_call_questions"]) >= 6
        assert len(packet["sow_outline"]) >= 5
        assert len(packet["packet_sha256"]) == 64


def test_kuramoto_negative_result_is_preserved_without_field_request():
    payload = load_module().build_payload()
    info = payload["summary"]
    kuramoto = next(
        row
        for row in payload["packets"]
        if row["family_id"] == "kuramoto_phase_coupling"
    )
    holdout = kuramoto["latest_holdout_evidence"]

    assert info["kuramoto_holdout_ready_for_field_replay_request"] is False
    assert info["kuramoto_holdout_count"] >= 1_500
    assert (
        info["kuramoto_holdout_wins_vs_kalman"]
        < info["kuramoto_holdout_count"] / 2
    )
    assert info["kuramoto_holdout_mean_delta_vs_kalman"] < 0
    assert len(info["kuramoto_holdout_chain_sha256"]) == 64

    assert holdout["candidate"] == "kuramoto_phase_coupling"
    assert holdout["development_selected_candidate"] == "lissajous_phase_paths"
    assert holdout["candidate_was_protocol_selected"] is False
    assert holdout["named_baseline"] == "kalman_local_linear_trend"
    assert holdout["registered_baseline_mean_win_count"] == 0
    assert (
        holdout["candidate_beats_all_registered_baselines_after_holm"] is False
    )
    assert holdout["ready_for_buyer_authorized_field_replay_request"] is False


def test_packet_blocks_outreach_performance_and_money_overclaims():
    payload = load_module().build_payload()
    info = payload["summary"]
    text = json.dumps(payload).lower()

    assert info["bulk_email_allowed"] is False
    assert info["fixed_dollar_delta_claim_allowed"] is False
    assert info["field_validation_claim_allowed"] is False
    assert info["realized_savings_claim_allowed"] is False
    assert info["live_trading_or_autonomous_execution_allowed"] is False
    assert "bulk email" in text
    assert "current performance champion" in text

    for packet in payload["packets"]:
        gate = packet["claim_gate"]
        assert gate["send_manually_to_reviewed_contacts"] is False
        assert gate["exact_action_time_approval_required"] is True
        assert gate["performance_champion_claim_allowed"] is False
        assert gate["bulk_email_allowed"] is False
        assert gate["field_validation_claim_allowed"] is False


def test_protocol_packet_markdown_is_actionable_and_compliant():
    module = load_module()
    rendered = module.render_markdown(module.build_payload())

    assert "Field Validation Buyer Pilot Packet" in rendered
    assert "Manual outreach ready: `0`" in rendered
    assert "Field-replay candidates: `0`" in rendered
    assert "Internal performance champions: `0`" in rendered
    assert "Kuramoto field-replay request ready: `false`" in rendered
    assert "Do not run bulk outreach" in rendered
    assert "current performance champion" in rendered
