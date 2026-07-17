from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_ENGAGEMENT_CLOCK_GATE.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_ENGAGEMENT_CLOCK_GATE_E_DRIVE_SYNC_RECEIPT_2026-07-16.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("external_engagement_clock_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_clock_gate_identifies_only_the_immediate_human_fact_lane():
    module = load_module()
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
    )
    controls = {row["lane_id"]: row for row in payload["controls"]}

    assert payload["schema"] == "lumencore.external_engagement_clock_gate.v1"
    assert payload["status"] == "HUMAN_ACTION_DUE_NO_AUTONOMOUS_SEND"
    assert payload["summary"]["lane_count"] == 7
    assert payload["summary"]["immediate_human_action_count"] == 1
    assert payload["summary"]["date_only_deadline_count"] == 1
    assert payload["summary"]["duplicate_send_block_count"] == 6
    assert payload["summary"]["active_follow_up_hold_count"] == 3
    assert payload["summary"]["autonomous_external_send_allowed"] is False
    assert payload["summary"]["autonomous_final_submit_allowed"] is False
    assert payload["summary"]["browser_navigation_performed"] is False

    nashville = controls["nashville_ec_takeoff_fall_2026"]
    assert nashville["priority"] == "P0_HUMAN_FACTS_NOW"
    assert nashville["human_action_required_now"] is True
    assert nashville["deadline_precision"] == "DATE_ONLY_CLOSE_TIME_NOT_RECORDED"
    assert nashville["deadline_state"] == "DUE_NEXT_LOCAL_DAY_TIME_UNVERIFIED"
    assert nashville["hours_remaining"] is None


def test_clock_gate_blocks_duplicate_outreach_and_preserves_holds():
    module = load_module()
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
    )
    controls = {row["lane_id"]: row for row in payload["controls"]}

    for lane_id in (
        "epri_open_power_ai_mou",
        "georgia_patents_pro_bono_intake",
        "cdc_ai_acquisition_rfi",
        "lanl_vision_licensing_followup",
        "nasa_data_center_rfi",
        "army_aidp_draft_cfs_feedback",
    ):
        row = controls[lane_id]
        assert row["duplicate_send_control"] == "BLOCKED_DO_NOT_DUPLICATE"
        assert row["autonomous_external_send_allowed"] is False
        assert row["autonomous_final_submit_allowed"] is False

    for lane_id in (
        "epri_open_power_ai_mou",
        "georgia_patents_pro_bono_intake",
        "lanl_vision_licensing_followup",
    ):
        assert controls[lane_id]["follow_up_hold_state"] == "FOLLOW_UP_HOLD_ACTIVE"

    assert controls["nasa_data_center_rfi"]["deadline_state"] == "UNDER_24_HOURS"
    assert controls["nasa_data_center_rfi"]["priority"] == "P2_MONITOR_NO_DUPLICATE"


def test_clock_gate_verifies_source_and_record_hashes():
    module = load_module()
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
    )

    assert payload["summary"]["source_register_hash_valid"] is True
    assert payload["summary"]["all_record_hashes_valid"] is True
    assert payload["summary"]["verified_record_hash_count"] == 7
    assert len(payload["source"]["sha256"]) == 64
    assert len(payload["gate_sha256"]) == 64
    for row in payload["controls"]:
        assert row["record_hash_valid"] is True
        assert len(row["control_sha256"]) == 64


def test_rendered_gate_is_public_safe_and_claim_bounded():
    module = load_module()
    payload = module.build_payload(
        as_of_utc="2026-07-17T04:57:00Z",
        generated_utc="2026-07-17T04:57:00Z",
    )
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    module.ensure_public_safe(rendered)
    assert "only immediate human-fact action" in lowered
    assert "no exact closing hour is claimed" in lowered
    assert "session-browser navigation performed: `false`" in lowered
    assert "does not establish" in lowered
    for marker in module.PRIVATE_MARKERS:
        assert marker not in lowered


def test_bounded_e_drive_mirror_matches_every_clock_gate_artifact():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8-sig"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 6
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        mirror = Path(artifact["destination"])
        assert source.is_file(), artifact["source"]
        assert mirror.is_file(), artifact["destination"]
        assert source.stat().st_size == mirror.stat().st_size == artifact["bytes"]
        source_hash = hashlib.sha256(source.read_bytes()).hexdigest().upper()
        mirror_hash = hashlib.sha256(mirror.read_bytes()).hexdigest().upper()
        assert source_hash == mirror_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert "does not prove email transmission" in receipt["claim_boundary"]
