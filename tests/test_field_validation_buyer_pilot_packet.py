from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_FIELD_VALIDATION_BUYER_PILOT_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("field_validation_buyer_pilot_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_buyer_pilot_packet_builds_two_manual_outreach_tracks():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    by_family = {row["family_id"]: row for row in payload["packets"]}

    assert payload["schema"] == "field_validation_buyer_pilot_packet_v1"
    assert summary["packet_count"] == 2
    assert summary["manual_outreach_ready_count"] == 2
    assert len(summary["packet_chain_sha256"]) == 64
    assert "brachistochrone_descent" in by_family
    assert "kuramoto_phase_coupling" in by_family

    brach = by_family["brachistochrone_descent"]
    assert brach["lane"] == "optimal_curve_transport"
    assert "Director of Grid Analytics" in brach["priority_buyer_titles"]
    assert "Port Operations Analytics Lead" in brach["priority_buyer_titles"]
    assert "Constrained Transport" in brach["pilot_name"]

    kuramoto = by_family["kuramoto_phase_coupling"]
    assert kuramoto["lane"] == "wave_resonance_timing"
    assert "Energy Forecasting Lead" in kuramoto["priority_buyer_titles"]
    assert "Sensor Fusion Program Manager" in kuramoto["priority_buyer_titles"]
    assert "Resonance Timing" in kuramoto["pilot_name"]
    assert kuramoto["field_replay_request"]["minimum_holdout_windows"] == 20
    assert kuramoto["field_replay_request"]["current_status"] == "ready_to_request_field_replay_not_yet_field_validated"


def test_buyer_pilot_packet_contains_sow_data_room_and_pilot_questions():
    module = load_module()
    payload = module.build_payload()

    for packet in payload["packets"]:
        assert packet["paid_offer"]["offer_type"] == "paid technical evaluation or buyer-authorized pilot scoping"
        assert packet["paid_offer"]["pricing_status"] == "quote_after_fit_call_and_data_scope"
        assert "not sale of guaranteed-value frozen deltas" in packet["paid_offer"]["safe_positioning"]
        assert len(packet["deliverables"]) >= 6
        assert len(packet["data_room_artifacts"]) >= 5
        assert "docs/GEOMETRY_REPEAT_UNCERTAINTY_REPORT_2026-06-25.md" in packet["data_room_artifacts"]
        assert "docs/GEOMETRY_FIELD_VALIDATION_PROTOCOL_2026-06-25.md" in packet["data_room_artifacts"]
        assert "docs/KURAMOTO_HOLDOUT_EXPANSION_2026-06-26.md" in packet["data_room_artifacts"]
        assert len(packet["buyer_data_checklist"]) >= 5
        assert len(packet["baseline_controls"]) >= 5
        assert len(packet["primary_kpis"]) >= 4
        assert len(packet["pre_call_questions"]) >= 6
        assert len(packet["sow_outline"]) >= 5
        assert len(packet["packet_sha256"]) == 64


def test_buyer_pilot_packet_surfaces_kuramoto_holdout_without_overclaiming():
    module = load_module()
    payload = module.build_payload()
    by_family = {row["family_id"]: row for row in payload["packets"]}
    summary = payload["summary"]
    kuramoto = by_family["kuramoto_phase_coupling"]
    holdout = kuramoto["latest_holdout_evidence"]

    assert summary["kuramoto_holdout_ready_for_field_replay_request"] is True
    assert summary["kuramoto_holdout_count"] >= 20
    assert summary["kuramoto_holdout_wins_vs_kalman"] >= 16
    assert len(summary["kuramoto_holdout_chain_sha256"]) == 64

    assert holdout["candidate"] == "kuramoto_phase_coupling"
    assert holdout["named_baseline"] == "kalman_filter"
    assert holdout["holdout_count"] >= 20
    assert holdout["wins_vs_kalman"] >= 16
    assert holdout["passes_internal_20_holdout_gate"] is True
    assert holdout["ready_for_buyer_authorized_field_replay_request"] is True
    assert holdout["estimated_rows_replayed"] > 0
    assert len(holdout["holdout_chain_sha256"]) == 64
    assert "not field validation" in holdout["claim_boundary"].lower()


def test_buyer_pilot_packet_blocks_overclaim_and_bulk_outreach():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]
    text = json.dumps(payload).lower()

    assert summary["bulk_email_allowed"] is False
    assert summary["fixed_dollar_delta_claim_allowed"] is False
    assert summary["field_validation_claim_allowed"] is False
    assert summary["realized_savings_claim_allowed"] is False
    assert summary["live_trading_or_autonomous_execution_allowed"] is False
    assert "fixed-dollar frozen-delta claim" in text
    assert "bulk email" in text
    assert "live_order_placement" not in text
    assert ("api" + "_key") not in text

    for packet in payload["packets"]:
        gate = packet["claim_gate"]
        assert gate["send_manually_to_reviewed_contacts"] is True
        assert gate["bulk_email_allowed"] is False
        assert gate["fixed_dollar_delta_claim_allowed"] is False
        assert gate["field_validation_claim_allowed"] is False
        assert gate["realized_savings_claim_allowed"] is False
        assert gate["live_trading_or_autonomous_execution_allowed"] is False
        assert "guaranteed savings" in packet["no_send_phrases"]
        assert "$10k per frozen delta" in packet["no_send_phrases"]


def test_buyer_pilot_markdown_is_actionable_and_compliant():
    module = load_module()
    rendered = module.render_markdown(module.build_payload())

    assert "Field Validation Buyer Pilot Packet" in rendered
    assert "Manual outreach ready: `2`" in rendered
    assert "Bulk email allowed: `false`" in rendered
    assert "Fixed-dollar delta claim allowed: `false`" in rendered
    assert "`brachistochrone_descent`" in rendered
    assert "`kuramoto_phase_coupling`" in rendered
    assert "To stop further outreach, reply \"remove.\"" in rendered
    assert "Do not run bulk outreach" in rendered
    assert "Expanded internal holdout evidence" in rendered
    assert "Kuramoto holdout wins vs Kalman" in rendered
    assert "not field validation or a dollar claim" in rendered
