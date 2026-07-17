from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_ENGAGEMENT_RESPONSE_CONTROL_E_DRIVE_SYNC_RECEIPT_2026-07-16.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("external_engagement_response_register", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_register_routes_current_actions_without_duplicate_sends():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")
    records = {row["lane_id"]: row for row in payload["records"]}

    assert payload["schema"] == "lumencore.external_engagement_response_register.v1"
    assert payload["summary"]["record_count"] == 6
    assert payload["summary"]["immediate_human_action_count"] == 1
    assert payload["summary"]["monitor_only_count"] == 5
    assert payload["summary"]["do_not_duplicate_send_count"] == 5
    assert payload["summary"]["autonomous_external_send_allowed"] is False
    assert payload["summary"]["autonomous_final_portal_submission_allowed"] is False

    assert records["nashville_ec_takeoff_fall_2026"]["deadline"] == "2026-07-17"
    assert "six concise confirmation prompts" in records["nashville_ec_takeoff_fall_2026"]["action_gate"]
    assert records["nashville_ec_takeoff_fall_2026"]["response_artifact"].endswith(
        "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
    )
    assert payload["source_artifacts"]["nashville_human_fact_resolution"]["present"] is True
    assert records["epri_open_power_ai_mou"]["decision"] == "MONITOR_FOR_MOU_NO_DUPLICATE"
    assert records["epri_open_power_ai_mou"]["state"] == "OUTBOUND_SENT_MOU_PENDING"
    assert records["epri_open_power_ai_mou"]["do_not_duplicate_send"] is True
    assert records["epri_open_power_ai_mou"]["no_send_before"] == "2026-07-23"
    assert payload["source_artifacts"]["epri_engagement_receipt"]["present"] is True
    assert records["cdc_ai_acquisition_rfi"]["decision"] == "MONITOR_NO_REPLY_REQUIRED"
    assert records["lanl_vision_licensing_followup"]["no_send_before"] == "2026-07-23"
    assert records["nasa_data_center_rfi"]["do_not_duplicate_send"] is True
    assert records["army_aidp_draft_cfs_feedback"]["do_not_duplicate_send"] is True


def test_all_transmitted_attachments_match_receipts():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")

    assert payload["summary"]["verified_attachment_count"] == 4
    assert payload["summary"]["all_attachment_checks_pass"] is True
    for check in payload["attachment_checks"].values():
        assert check["present"] is True
        assert check["sha256_match"] is True
        assert check["bytes_match"] is True


def test_register_preserves_claim_and_privacy_boundaries():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "duplicate sends would reduce credibility" in payload["direct_answer"]
    assert "do not resend" in lowered
    assert "MOU-routing information only" in rendered
    assert "does not prove" in payload["claim_boundary"]
    assert "do_not_treat_as_official_sam_notice" in lowered
    assert "full legal name:" not in lowered
    assert "signatory email:" not in lowered
    assert "signatory telephone:" not in lowered
    assert "meeting id" not in lowered
    assert "passcode" not in lowered
    assert "zoom.us" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered


def test_lanl_followup_is_held_and_bounded():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")
    lanl = next(row for row in payload["records"] if row["lane_id"] == "lanl_vision_licensing_followup")
    body = lanl["follow_up_template"]["body"]

    assert lanl["send_now"] is False
    assert lanl["do_not_duplicate_send"] is True
    assert "Stage 0 diligence session" in body
    assert "not asserting a license" in body
    assert "field validation" in body
    assert "production readiness" in body


def test_mirror_receipt_matches_every_bounded_source():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 30
    assert receipt["all_sha256_matched_after_copy"] is True
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        assert source.is_file(), artifact["source"]
        assert source.stat().st_size == artifact["bytes"], artifact["source"]
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == artifact["sha256"]

    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert {
        "code/ops/BUILD_NASHVILLE_EC_HUMAN_FACT_RESOLUTION.py",
        "tests/test_nashville_ec_human_fact_resolution.py",
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json",
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md",
        "code/ops/BUILD_SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL.py",
        "tests/test_sam_public_credential_rotation_control.py",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.md",
        "grant_submissions/funding_sprint_20260709/EPRI_OPEN_POWER_AI_MOU_ENGAGEMENT_RECEIPT_2026-07-16.json",
    }.issubset(mirrored_sources)

    assert "does not prove" in receipt["claim_boundary"]
