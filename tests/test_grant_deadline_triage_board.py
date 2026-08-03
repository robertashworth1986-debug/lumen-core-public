from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_GRANT_DEADLINE_TRIAGE_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("grant_deadline_triage_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_deadline_triage_uses_official_dice_and_dsip_dates():
    module = load_module()
    board = module.build_board()

    assert board["schema"] == "grant_deadline_triage_board_v1"
    assert board["source_posture"] == "CURRENT_COMMAND_BOARD_OVERLAY_APPLIED"
    assert board["legacy_source_posture"] == "LOCAL_READY_PORTAL_BLOCKED"
    assert board["readiness_summary"]["local_blockers"] == 0
    assert board["readiness_summary"]["portal_user_blockers"] > 0

    dice = board["official_deadlines"]["dice"]
    assert dice["funding_opportunity_number"] == "HR001126S0010"
    assert dice["abstract_due"]["utc_iso"] == "2026-06-30T18:00:00+00:00"
    assert dice["proposal_due"]["utc_iso"] == "2026-08-25T18:00:00+00:00"
    assert dice["submission_channel"] == "DARPA BAAT"
    assert "BAAT" in dice["channel_boundary"]
    assert dice["historical_deadline_record_only"] is True
    assert dice["current_route_status"] == (
        "FULL_PROPOSAL_DISCOURAGED_ROUTE_CLOSED"
    )
    assert dice["full_proposal_allowed"] is False
    assert dice["reply_required"] is False
    assert dice["do_not_duplicate"] is True
    assert "Do not reply" in dice["immediate_action"]

    topics = {
        row["topic_code"]: row
        for row in board["official_deadlines"]["dsip"]["selected_topics"]
    }
    assert set(topics) == {"DON26BZ03-NV063", "DON26BZ03-NV065", "DLA26BZ03-NV011"}
    assert topics["DON26BZ03-NV063"]["topic_status"] == "Pre-Release"
    assert topics["DON26BZ03-NV063"]["cmmc_level"] == "Level 2 (Self)"
    assert topics["DON26BZ03-NV063"]["tpoc_qa_end_utc"] == "2026-06-24T12:00:00+00:00"
    assert topics["DON26BZ03-NV065"]["tpoc_qa_end_utc"] == "2026-06-24T12:00:00+00:00"
    assert topics["DLA26BZ03-NV011"]["tpoc_qa_end_utc"] == "2026-06-24T12:00:00+00:00"
    assert "historical" in board["official_deadlines"]["dsip"][
        "proposal_window_boundary"
    ].lower()

    overlay = board["current_command_board"]
    source_board = module.read_json(module.CURRENT_COMMAND_BOARD_JSON)
    source_stage_numbers = {
        row["opportunity_number"] for row in source_board.get("stage_now", [])
    }
    assert overlay["available"] is True
    assert overlay["stage_candidate_count"] == source_board["summary"][
        "stage_candidate_count"
    ]
    assert overlay["stage_candidate_count"] == len(overlay["stage_lanes"])
    assert overlay["stage_ready_count"] == 0
    assert overlay["all_final_actions_blocked_without_human"] is True
    overlay_stage_numbers = {
        row["opportunity_number"] for row in overlay["stage_lanes"]
    }
    assert overlay_stage_numbers == source_stage_numbers
    assert all(
        row["submission_ready"] is False for row in overlay["stage_lanes"]
    )


def test_deadline_triage_preserves_submit_and_evidence_boundaries():
    module = load_module()
    board = module.build_board()
    rendered = module.render_markdown(board)

    assert board["submit_gate"]["ready_for_submit"] is False
    assert "I approve this exact upload/submit action now." in board["submit_gate"]["required_user_phrase"]
    assert any("No upload" in item for item in board["safety_boundaries"])
    assert any("Dollar-value" in item for item in board["safety_boundaries"])

    geometry = board["evidence_to_use"]["geometry_championship"]
    assert geometry["generated_lane_benchmark_count"] >= 2
    assert geometry["generated_champion_family"] == "brachistochrone_descent"
    assert geometry["claim_gate_passed"] is False
    assert geometry["kraken_live_execution_allowed"] is False
    assert "field validation" in geometry["boundary"]
    assert "dollar-value proof" in geometry["boundary"]

    live_gate = board["live_proof_submission_gate"]
    assert live_gate["available"] is True
    assert live_gate["status"] == (
        "HISTORICAL_ACTIVE_START_SUPERSEDED_BY_OFFICIAL_CLOSURE"
    )
    assert live_gate["active_start_package"] == ""
    assert live_gate["active_start_deadline_utc"] == ""
    assert live_gate["legacy_active_start_package"] == "DICE"
    assert live_gate["legacy_active_start_deadline_utc"] == (
        "2026-06-30T18:00:00+00:00"
    )
    assert live_gate["closest_action_gate_portal"] == ""
    assert live_gate["closest_action_gate_utc"] == ""
    assert live_gate["proposal_specific_live_proof_count"] == 2
    assert live_gate["proposal_specific_live_proof_total"] == 5
    assert set(live_gate["packages_missing_live_proof"]) == {"NSF Project Pitch", "MissionWeave", "NV065"}
    assert live_gate["ready_for_any_final_submit"] is False
    assert board["discarded_workspaces"][0]["status"] == "DISCARD_NO_SUBMIT"

    assert "DICE is not a Grants.gov submit path" in rendered
    assert "official feedback discouraged a full proposal" in rendered
    assert "Historical capture: TPOC Q&A closed June 24, 2026" in rendered
    assert "Ready for submit: `False`" in rendered
    assert "Live-Proof Submission Gate" in rendered
    assert "Ready for any final submit: `False`" in rendered
    assert "DISCARD_NO_SUBMIT" in rendered
    assert "## Current Action Order" in rendered
    assert "Inside BAAT" not in rendered
    assert "Inside DSIP" not in rendered
    assert "Guaranteed award" not in rendered
    assert "Guaranteed funding" not in rendered


def test_deadline_triage_fails_closed_without_current_command_board(tmp_path):
    module = load_module()
    module.CURRENT_COMMAND_BOARD_JSON = tmp_path / "missing-current-board.json"

    board = module.build_board()
    overlay = board["current_command_board"]

    assert board["source_posture"] == (
        "CURRENT_COMMAND_BOARD_MISSING_REVERIFY_REQUIRED"
    )
    assert overlay["available"] is False
    assert overlay["stage_ready_count"] == 0
    assert overlay["all_final_actions_blocked_without_human"] is True
    assert board["submit_gate"]["ready_for_submit"] is False
    assert any(
        "Rebuild and verify" in action for action in board["tonight_action_order"]
    )
