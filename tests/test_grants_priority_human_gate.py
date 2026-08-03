from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"
PRIORITY_LANES = (
    "launchtn_3686_pitch_2026",
    "erdc_sovereign_cloud_cso",
    "state_pax_silica_ai_assistance",
)


def test_grant_factory_loads_current_priority_sources_fail_closed() -> None:
    html = (DASHBOARD / "grants.html").read_text(encoding="utf-8")

    assert 'id="priority-action-queue"' in html
    assert "near_deadline_submission_command_board.json" in html
    assert "human_action_docket.json" in html
    assert "Current source-bound queue unavailable. No lane is shown as ready." in html
    assert "final action human-gated" in html
    assert 'target="_blank" rel="noopener">Official source</a>' in html
    for lane_id in PRIORITY_LANES:
        assert lane_id in html


def test_priority_lanes_match_current_source_bound_human_gates() -> None:
    command_board = json.loads(
        (DASHBOARD / "data" / "near_deadline_submission_command_board.json").read_text(
            encoding="utf-8"
        )
    )
    docket = json.loads(
        (DASHBOARD / "data" / "human_action_docket.json").read_text(encoding="utf-8")
    )

    assert command_board["summary"]["final_submit_allowed_without_human"] is False
    assert command_board["summary"]["external_send_allowed_without_human"] is False
    lanes = {row["lane_id"]: row for row in command_board["lanes"]}
    docket_items = {row["lane_id"]: row for row in docket["docket_items"]}

    for lane_id in PRIORITY_LANES:
        assert lanes[lane_id]["submission_ready"] is False
        assert lanes[lane_id]["official_url"].startswith("https://")
        assert lanes[lane_id]["official_deadline_text"]
        assert docket_items[lane_id]["human_gate"].startswith("Human action required:")
        assert "Human approval is required" in docket_items[lane_id]["no_final_action_rule"]

    launchtn = lanes["launchtn_3686_pitch_2026"]
    launchtn_manifest = json.loads(
        (
            ROOT
            / "grant_submissions"
            / "LAUNCHTN_3686_PITCH_2026"
            / "LAUNCHTN_3686_APPLICATION_MANIFEST_2026-08-02.json"
        ).read_text(encoding="utf-8")
    )
    manifest_summary = launchtn_manifest["summary"]
    assert launchtn["human_or_private_fact_gate_count"] == manifest_summary[
        "human_or_private_fact_gates"
    ]
    assert launchtn["required_attachments_present"] == manifest_summary[
        "required_attachments_present"
    ]
    assert launchtn["required_attachments_final_qa_passed"] == manifest_summary[
        "required_attachments_qa_passed"
    ]
    assert launchtn["safe_upload_count"] == len(
        launchtn_manifest["safe_upload_set"]
    )
