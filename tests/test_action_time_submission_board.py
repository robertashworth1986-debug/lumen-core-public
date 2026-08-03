from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ACTION_TIME_SUBMISSION_BOARD.py"


def load_module():
    spec = importlib.util.spec_from_file_location("action_time_submission_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_action_time_board_prioritizes_dice_and_harbor_without_submit_claims():
    module = load_module()
    board = module.build_board()

    assert board["schema"] == "action_time_submission_board_v1"
    assert board["source_posture"] == "LOCAL_READY_PORTAL_BLOCKED"
    assert board["summary"]["local_blockers"] == 0
    assert board["summary"]["portal_user_blockers"] > 0

    cards = {card["package"]: card for card in board["cards"]}
    assert board["cards"][0]["package"] == "DICE"
    assert board["cards"][1]["package"] == "HarborSentinel"
    assert cards["DICE"]["ready_to_submit"] is False
    assert cards["HarborSentinel"]["ready_to_submit"] is False
    assert board["package_freeze"]["available"] is True
    assert len(board["package_freeze"]["signature_sha256"]) == 64
    assert board["portal_preview_runbook"]["available"] is True
    assert board["support_outreach_pack"]["available"] is True
    assert board["support_outreach_pack"]["official_support_lanes"] >= 4
    assert "DARPA BAAT" in board["support_outreach_pack"]["sign_in_targets"]
    assert "PIEE / SPRS" in board["support_outreach_pack"]["sign_in_targets"]
    assert board["reviewer_red_team_gate"]["available"] is True
    assert board["reviewer_red_team_gate"]["packages_reviewed"] >= 2
    assert board["reviewer_red_team_gate"]["ready_for_upload_count"] == 0
    assert any("DICE frozen live-breadth replay ready" in fact for fact in cards["DICE"]["verified_strengths"])
    assert any(task["gate"] == "BAAT authority" for task in cards["DICE"]["next_capture_tasks"])
    assert any(task["gate"] == "DSIP authority" for task in cards["HarborSentinel"]["next_capture_tasks"])
    assert any(task["gate"] == "Action-time approval" for task in cards["HarborSentinel"]["next_capture_tasks"])


def test_action_time_board_preserves_harbor_evidence_boundaries():
    module = load_module()
    board = module.build_board()
    harbor = next(card for card in board["cards"] if card["package"] == "HarborSentinel")
    rendered = module.render_markdown(board)

    assert any("controlled-injection benchmark ready" in fact for fact in harbor["verified_strengths"])
    assert any("AIS review-burden profile ready" in fact for fact in harbor["verified_strengths"])
    assert "speed-only baseline recall 0.25835" in "\n".join(harbor["verified_strengths"])
    assert "p95 candidates/hour" in "\n".join(harbor["verified_strengths"])
    assert "No submit/certify/upload" not in rendered
    assert "Do not upload, certify, consent, sign, submit" in rendered
    assert "TOP_SUBMISSION_PACKAGE_FREEZE_2026-06-20.md" in rendered
    assert "PORTAL_PREVIEW_RUNBOOK_2026-06-20.md" in rendered
    assert "GRANT_SUPPORT_OUTREACH_PACK_2026-06-20.md" in rendered
    assert "REVIEWER_RED_TEAM_GATE_2026-06-20.md" in rendered
    assert "legal representation" in rendered
    assert "field-performance claims" in rendered
    assert "Guaranteed funding" not in rendered
    assert "SQY2XW71ZM51" not in rendered
    assert "14TM8" not in rendered
