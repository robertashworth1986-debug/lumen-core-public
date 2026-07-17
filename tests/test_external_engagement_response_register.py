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
    assert payload["summary"]["record_count"] == 11
    assert payload["summary"]["immediate_human_action_count"] == 2
    assert payload["summary"]["monitor_only_count"] == 7
    assert payload["summary"]["do_not_duplicate_send_count"] == 9
    assert payload["summary"]["email_action_reconciliation_status"] == (
        "NO_NEW_DEADLINE_CRITICAL_EMAIL_ACTION"
    )
    assert payload["summary"]["autonomous_external_send_allowed"] is False
    assert payload["summary"]["autonomous_final_portal_submission_allowed"] is False

    assert records["nashville_ec_takeoff_fall_2026"]["deadline"] == "2026-07-17"
    assert "six concise confirmation prompts" in records["nashville_ec_takeoff_fall_2026"]["action_gate"]
    assert records["nashville_ec_takeoff_fall_2026"]["response_artifact"].endswith(
        "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
    )
    assert records["nashville_ec_takeoff_fall_2026"]["private_fill_map_present"] is False
    assert records["nashville_ec_takeoff_fall_2026"]["private_fact_values_read_or_published"] is False
    assert any(
        path.endswith("CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py")
        for path in records["nashville_ec_takeoff_fall_2026"]["supporting_artifacts"]
    )
    assert "hidden-prompt private collector" in records["nashville_ec_takeoff_fall_2026"]["next_action"]
    assert payload["source_artifacts"]["nashville_human_fact_resolution"]["present"] is True
    assert payload["source_artifacts"]["nashville_private_collector"]["present"] is True
    assert payload["source_artifacts"]["nashville_private_workflow"]["present"] is True
    assert payload["source_artifacts"]["nashville_private_fill_map"]["present"] is False
    assert payload["source_artifacts"]["nashville_private_fill_map"]["bytes"] == 0
    assert payload["source_artifacts"]["nashville_private_fill_map"]["sha256"] is None
    assert payload["source_artifacts"]["nashville_private_fill_map"]["private_values_read_or_published"] is False
    launchtn = records["launchtn_3686_pitch_2026"]
    assert launchtn["deadline"] == "2026-08-13T23:59:00-05:00"
    assert launchtn["state"] == (
        "PORTAL_PACKET_QA_PASSED_HUMAN_FACTS_AND_FOUNDER_APPROVAL_REQUIRED"
    )
    assert launchtn["attachment_qa_passed_count"] == 2
    assert launchtn["attachment_required_count"] == 2
    assert launchtn["send_now"] is False
    assert "final rendered application" in launchtn["next_action"]
    assert payload["source_artifacts"]["launchtn_application_manifest"]["present"] is True
    assert payload["source_artifacts"]["launchtn_pitch_deck"]["present"] is True
    assert payload["source_artifacts"]["launchtn_financial_model"]["present"] is True
    assert records["epri_open_power_ai_mou"]["decision"] == "MONITOR_FOR_MOU_NO_DUPLICATE"
    assert records["epri_open_power_ai_mou"]["state"] == "OUTBOUND_SENT_MOU_PENDING"
    assert records["epri_open_power_ai_mou"]["do_not_duplicate_send"] is True
    assert records["epri_open_power_ai_mou"]["no_send_before"] == "2026-07-23"
    assert records["epri_open_power_ai_mou"]["latest_mailbox_event"] == (
        "AUTOMATIC_OUT_OF_OFFICE"
    )
    assert records["epri_open_power_ai_mou"]["out_of_office_through"] == (
        "2026-07-20"
    )
    assert records["georgia_patents_pro_bono_intake"]["state"] == (
        "OUTBOUND_SENT_INTAKE_RESPONSE_PENDING"
    )
    assert records["georgia_patents_pro_bono_intake"]["no_send_before"] == "2026-07-24"
    assert records["georgia_patents_pro_bono_intake"]["do_not_duplicate_send"] is True
    assert records["georgia_patents_pro_bono_intake"]["required_docket_role_count"] == 6
    assert records["georgia_patents_pro_bono_intake"]["captured_required_docket_role_count"] == 0
    assert records["georgia_patents_pro_bono_intake"]["docket_capture_complete"] is False
    assert any(
        path.endswith("PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md")
        for path in records["georgia_patents_pro_bono_intake"]["supporting_artifacts"]
    )
    assert payload["source_artifacts"]["georgia_patents_engagement_receipt"]["present"] is True
    assert payload["source_artifacts"]["patent_deadline_control"]["present"] is True
    assert payload["source_artifacts"]["patent_private_capture_workflow"]["present"] is True
    assert payload["source_artifacts"]["patent_practitioner_request_template"]["present"] is True
    assert payload["source_artifacts"]["epri_engagement_receipt"]["present"] is True
    assert records["lvlup_optional_paid_event"]["decision"] == (
        "DO_NOT_SPEND_OR_SEND_STALE_DRAFT"
    )
    assert records["lvlup_optional_paid_event"]["send_now"] is False
    assert records["sam_public_credential_rotation"]["state"] == (
        "ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED"
    )
    assert records["sam_public_credential_rotation"]["response_channel"] == (
        "ACCOUNT_ACTION"
    )
    assert records["sam_public_credential_rotation"]["send_now"] is False
    assert records["cdc_ai_acquisition_rfi"]["decision"] == "MONITOR_NO_REPLY_REQUIRED"
    assert records["lanl_vision_licensing_followup"]["no_send_before"] == "2026-07-23"
    assert records["terry_vynetic_followup"]["decision"] == (
        "MONITOR_NO_FURTHER_FOLLOWUP"
    )
    assert records["terry_vynetic_followup"]["outbound_followup_count"] == 2
    assert records["terry_vynetic_followup"]["outbound_spacing_seconds"] == 10
    assert records["terry_vynetic_followup"]["send_now"] is False
    assert records["terry_vynetic_followup"]["do_not_duplicate_send"] is True
    assert "Send nothing further" in records["terry_vynetic_followup"][
        "next_action"
    ]
    assert payload["source_artifacts"]["email_action_reconciliation"]["present"] is True
    assert records["nasa_data_center_rfi"]["do_not_duplicate_send"] is True
    assert records["army_aidp_draft_cfs_feedback"]["do_not_duplicate_send"] is True


def test_all_transmitted_attachments_match_receipts():
    module = load_module()
    payload = module.build_payload("2026-07-16T23:59:00Z")

    assert payload["summary"]["verified_attachment_count"] == 6
    assert payload["summary"]["all_attachment_checks_pass"] is True
    for check in payload["attachment_checks"].values():
        assert check["present"] is True
        assert check["sha256_match"] is True
        assert check["bytes_match"] is True
    assert payload["attachment_checks"]["launchtn_pitch_deck"]["qa_status"] == (
        "QA_PASSED_FOUNDER_APPROVAL_REQUIRED"
    )
    assert payload["attachment_checks"]["launchtn_financial_model"]["qa_status"] == (
        "QA_PASSED_FOUNDER_APPROVAL_REQUIRED"
    )


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
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 52
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False
    destination = Path(receipt["destination_root"])
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        mirror = destination / source.name
        assert source.is_file(), artifact["source"]
        assert mirror.is_file(), str(mirror)
        assert source.stat().st_size == artifact["bytes"], artifact["source"]
        assert mirror.stat().st_size == artifact["bytes"], artifact["source"]
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert hashlib.sha256(mirror.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert {
        "code/ops/BUILD_NASHVILLE_EC_HUMAN_FACT_RESOLUTION.py",
        "code/ops/BUILD_NASHVILLE_EC_FALL_2026_APPLICATION.py",
        "tests/test_nashville_ec_human_fact_resolution.py",
        "tests/test_nashville_ec_fall_2026_application.py",
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md",
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json",
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md",
        "code/ops/BUILD_SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL.py",
        "tests/test_sam_public_credential_rotation_control.py",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.md",
        "grant_submissions/funding_sprint_20260709/EPRI_OPEN_POWER_AI_MOU_ENGAGEMENT_RECEIPT_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/GEORGIA_PATENTS_PRO_BONO_INTAKE_RESPONSE_2026-07-16.md",
        "grant_submissions/funding_sprint_20260709/GEORGIA_PATENTS_PRO_BONO_INTAKE_ENGAGEMENT_RECEIPT_2026-07-16.json",
        "tests/test_georgia_patents_pro_bono_intake.py",
        ".gitignore",
        "code/ops/CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py",
        "code/ops/VALIDATE_NASHVILLE_EC_PRIVATE_FACTS.py",
        "tests/test_capture_nashville_ec_private_facts.py",
        "tests/test_nashville_ec_private_facts.py",
        "config/nashville_ec_private_facts_template_v1.json",
        "grant_submissions/NASHVILLE_EC_FALL_2026/NASHVILLE_EC_PRIVATE_FACT_CAPTURE_WORKFLOW_2026-07-17.md",
        "code/ops/PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py",
        "tests/test_prepare_patent_center_private_capture.py",
        "grant_submissions/funding_sprint_20260709/PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md",
        "grant_submissions/funding_sprint_20260709/PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md",
        "code/ops/BUILD_EMAIL_ACTION_RECONCILIATION.py",
        "tests/test_email_action_reconciliation.py",
        "grant_submissions/funding_sprint_20260709/EMAIL_ACTION_RECONCILIATION_2026-07-17.json",
        "grant_submissions/funding_sprint_20260709/EMAIL_ACTION_RECONCILIATION_2026-07-17.md",
        "grant_submissions/funding_sprint_20260709/NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-17.md",
    }.issubset(mirrored_sources)

    assert "does not prove" in receipt["claim_boundary"]
