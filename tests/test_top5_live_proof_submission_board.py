from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_TOP5_LIVE_PROOF_SUBMISSION_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("top5_live_proof_submission_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_top5_board_starts_dice_and_keeps_dsip_action_gate_visible():
    module = load_module()
    board = module.build_board()

    assert board["schema"] == "top5_live_proof_submission_board_v1"
    assert board["source_posture"] == "LOCAL_READY_PORTAL_BLOCKED"
    assert board["active_start_package"]["package"] == "DICE"
    assert board["active_start_package"]["abstract_due_utc"] == "2026-06-30T18:00:00+00:00"
    assert "proposal-specific live-pulled replay" in board["active_start_package"]["reason"]

    action = board["closest_action_gate"]
    assert action["portal"] == "DSIP"
    assert action["deadline_utc"] == "2026-06-24T12:00:00+00:00"
    assert set(action["packages"]) == {"HarborSentinel", "MissionWeave", "NV065"}
    assert "not a captured final proposal due date" in action["boundary"]


def test_top5_board_requires_proposal_specific_live_proof_before_submit():
    module = load_module()
    board = module.build_board()
    packages = {row["package"]: row for row in board["packages"]}
    gate = board["global_live_proof_gate"]

    assert len(packages) == 5
    assert gate["proposal_specific_live_proof_count"] == 2
    assert gate["proposal_specific_live_proof_total"] == 5
    assert gate["packages_with_live_proof"] == ["DICE", "HarborSentinel"]
    assert set(gate["packages_missing_live_proof"]) == {"NSF Project Pitch", "MissionWeave", "NV065"}
    assert gate["all_five_have_proposal_specific_live_proof"] is False
    assert gate["ready_for_any_final_submit"] is False
    assert "No final grant submit" in gate["rule"]

    dice = packages["DICE"]["live_proof"]
    assert dice["proposal_specific_live_proof"] is True
    assert dice["primary_evidence_source"] == "frozen_live_pulled_rows"
    assert dice["source_count"] == 6
    assert dice["scenario_count"] == 14
    assert dice["ready_for_submit"] is False
    assert dice["blocked_claims"]["live_replay_proves_operational_performance"] is False
    assert "field validation" in dice["claim_boundary"]

    harbor = packages["HarborSentinel"]["live_proof"]
    assert harbor["proposal_specific_live_proof"] is True
    assert harbor["scenario_count"] == 20000
    assert "Recall lift vs speed-only" in "\n".join(harbor["evidence"])
    assert harbor["ready_for_submit"] is False
    assert harbor["blocked_claims"]["proves_field_performance"] is False
    assert "field validation" in harbor["claim_boundary"]

    for name in ["NSF Project Pitch", "MissionWeave", "NV065"]:
        assert packages[name]["live_proof"]["proposal_specific_live_proof"] is False
        assert packages[name]["live_proof"]["proof_status"] == "BLOCKED_MISSING_PROPOSAL_SPECIFIC_LIVE_PROOF"
        assert packages[name]["ready_for_final_submit"] is False


def test_top5_board_discards_hud_locally_without_cloud_delete_authority():
    module = load_module()
    board = module.build_board()
    rendered = module.render_markdown(board)

    discarded = board["discarded_workspaces"]
    assert discarded[0]["opportunity"] == "PDR-2600-DC-029Q"
    assert discarded[0]["workspace_id"] == "WS01676964"
    assert discarded[0]["status"] == "DISCARD_NO_SUBMIT"
    assert "Do not delete or withdraw" in discarded[0]["destructive_action_boundary"]

    geometry = board["geometry_live_breadth_gate"]
    assert geometry["live_breadth_backed_generated_lanes"] == 0
    assert geometry["ready_for_commit_push_as_live_benchmark"] is False
    assert geometry["kraken_live_execution_allowed"] is False

    assert "DISCARD_NO_SUBMIT" in rendered
    assert "Ready for any final submit: `False`" in rendered
    assert "Guaranteed funding" not in rendered
    assert "Guaranteed award" not in rendered
