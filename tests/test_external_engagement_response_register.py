from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER.py"
LVLUP_REVIEW_CONFIRMATION = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "LVLUP_INDEPENDENT_REVIEW_CONFIRMATION_2026-07-17.json"
)
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_ENGAGEMENT_RESPONSE_CONTROL_E_DRIVE_SYNC_RECEIPT_2026-07-16.json"
)
CURRENT_STATE_MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "EXTERNAL_RESPONSE_STATE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
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
    assert payload["summary"]["record_count"] == 13
    assert payload["summary"]["immediate_human_action_count"] == 1
    assert payload["summary"]["monitor_only_count"] == 9
    assert payload["summary"]["do_not_duplicate_send_count"] == 12
    assert payload["summary"]["email_action_reconciliation_status"] == (
        "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
    )
    assert payload["summary"]["autonomous_external_send_allowed"] is False
    assert payload["summary"]["autonomous_final_portal_submission_allowed"] is False

    assert records["nashville_ec_takeoff_fall_2026"]["deadline"] == (
        "2026-07-17T23:59:00-05:00"
    )
    assert "rolling review result through August 3" in records[
        "nashville_ec_takeoff_fall_2026"
    ]["action_gate"]
    nashville = records["nashville_ec_takeoff_fall_2026"]
    assert nashville["state"] == "PORTAL_SUBMISSION_CONFIRMED"
    assert nashville["decision"] == "MONITOR_REVIEW_RESULT_NO_DUPLICATE"
    assert nashville["do_not_duplicate_send"] is True
    assert nashville["deadline_support_sent_utc"] == "2026-07-17T12:05:34Z"
    assert nashville["deadline_support_email_is_application"] is False
    assert nashville["response_artifact"].endswith(
        "NASHVILLE_EC_SUBMISSION_RECEIPT_2026-07-17.json"
    )
    assert nashville["official_close_time_confirmed"] is True
    assert nashville["deadline_timezone_explicit_in_message"] is False
    assert nashville["operational_timezone"] == "America/Chicago"
    private_fill_map_present = module.NASHVILLE_PRIVATE_FILL_MAP.is_file()
    assert nashville["private_fill_map_present"] is private_fill_map_present
    assert nashville["private_fact_values_read_or_published"] is False
    assert nashville["portal_submission_verified"] is True
    assert nashville["expected_next_steps_by"] == "2026-08-03"
    assert any(
        path.endswith("CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py")
        for path in nashville["supporting_artifacts"]
    )
    assert any(
        path.endswith("NASHVILLE_EC_DEADLINE_PRESERVATION_RESPONSE_CONTROL_2026-07-17.md")
        for path in nashville["supporting_artifacts"]
    )
    assert "Do not resubmit" in nashville["next_action"]
    assert "do not describe the application as accepted" in nashville["next_action"]
    assert payload["source_artifacts"]["nashville_human_fact_resolution"]["present"] is True
    assert payload["source_artifacts"]["nashville_private_collector"]["present"] is True
    assert payload["source_artifacts"]["nashville_private_workflow"]["present"] is True
    assert payload["source_artifacts"]["nashville_private_fill_map"][
        "present"
    ] is private_fill_map_present
    assert payload["source_artifacts"]["nashville_private_fill_map"]["bytes"] == 0
    assert payload["source_artifacts"]["nashville_private_fill_map"]["sha256"] is None
    assert payload["source_artifacts"]["nashville_private_fill_map"]["private_values_read_or_published"] is False
    assert payload["source_artifacts"]["nashville_deadline_preservation_receipt"]["present"] is True
    assert payload["source_artifacts"]["nashville_deadline_response_control"]["present"] is True
    assert payload["source_artifacts"]["nashville_official_deadline_confirmation"]["present"] is True
    assert payload["source_artifacts"]["nashville_submission_receipt"]["present"] is True
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
        "SERVICE_NOT_OFFERED_FOR_ALREADY_FILED_APPLICATION"
    )
    assert records["georgia_patents_pro_bono_intake"]["decision"] == (
        "CLOSE_SERVICE_SCOPE_NO_GO_NO_DUPLICATE"
    )
    assert records["georgia_patents_pro_bono_intake"]["no_send_before"] is None
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
    lvlup = records["lvlup_optional_paid_event"]
    assert lvlup["state"] == (
        "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    )
    assert lvlup["decision"] == "MONITOR_INDEPENDENT_REVIEW_NO_DUPLICATE"
    assert lvlup["written_independent_review_confirmation"] is True
    assert lvlup["paid_sponsor_purchase_required_for_separate_review"] is False
    assert lvlup["send_now"] is False
    assert payload["source_artifacts"]["lvlup_independent_review_confirmation"]["present"] is True
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
    darpa = records["darpa_sn_26_97_low_resource_computing_rfi"]
    assert darpa["state"] == (
        "FORMAL_RFI_PACKAGE_SENT_AGENCY_RESPONSE_RECEIVED_MONITOR_ONLY"
    )
    assert darpa["decision"] == "MONITOR_FORMAL_PACKAGE_NO_DUPLICATE"
    assert darpa["attachment_count"] == 2
    assert darpa["timely_submission_claimed"] is False
    assert darpa["do_not_duplicate_send"] is True
    assert payload["source_artifacts"]["darpa_sn_26_97_public_submission_receipt"][
        "present"
    ] is True
    fhwa = records["fhwa_tsmo_qualified_partner_outreach"]
    assert fhwa["state"] == (
        "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
    )
    assert fhwa["decision"] == "CLOSE_NO_GO_TEAM_SET_NO_DUPLICATE"
    assert fhwa["qualified_partner_evidence_present"] is False
    assert fhwa["delivery_failure_count"] == 1
    assert fhwa["replacement_send_count"] == 1
    assert fhwa["threaded_acknowledgment_send_count"] == 1
    assert fhwa["confirmed_delivery_count"] == 1
    assert fhwa["inbound_response_count"] == 2
    assert fhwa["qualified_response_lead_referral_count"] == 1
    assert fhwa["fit_check_confirmed_count"] == 0
    assert fhwa["team_set_decline_count"] == 1
    assert fhwa["last_outbound_status"] == (
        "THREADED_REFERRAL_ACKNOWLEDGMENT_SENT_FIT_CHECK_PENDING"
    )
    assert fhwa["active_route_status"] == "NO_GO_TEAM_SET_NO_ADDITIONAL_PARTNERS"
    assert fhwa["no_send_before"] is None
    assert fhwa["send_now"] is False
    assert fhwa["do_not_duplicate_send"] is True
    assert len(fhwa["message_id_sha256"]) == 64
    assert payload["source_artifacts"]["fhwa_partner_outreach_control"]["present"] is True
    assert payload["source_artifacts"]["fhwa_partner_response_control"]["present"] is True
    assert any(
        path.endswith("FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md")
        for path in fhwa["supporting_artifacts"]
    )
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
    assert "portal displayed a submission confirmation" in payload["direct_answer"]
    assert "without resubmitting or implying selection" in payload["direct_answer"]
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


def test_lvlup_confirmation_sentence_is_hashed_and_bounded():
    receipt = json.loads(LVLUP_REVIEW_CONFIRMATION.read_text(encoding="utf-8"))
    confirmation = receipt["confirmation"]
    sentence = confirmation["bounded_exact_sentence"]

    assert receipt["schema"] == "lumencore.lvlup_independent_review_confirmation.v1"
    assert receipt["status"] == (
        "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    )
    assert hashlib.sha256(sentence.encode("utf-8")).hexdigest() == confirmation[
        "bounded_exact_sentence_sha256"
    ]
    assert confirmation["sender_stated_independent_review_continues"] is True
    assert confirmation["funding_or_selection_confirmed"] is False
    assert receipt["response_state"]["reply_required"] is False
    assert receipt["response_state"]["duplicate_reply_allowed"] is False
    assert "does not prove" in receipt["claim_boundary"].lower()


def test_historical_response_state_mirror_remains_intact_on_e_drive():
    receipt = json.loads(CURRENT_STATE_MIRROR_RECEIPT.read_text(encoding="utf-8"))
    destination = Path(receipt["destination_root"])

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"])
    assert receipt["artifact_count"] >= 29
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["private_founder_values_mirrored"] is False
    for artifact in receipt["artifacts"]:
        mirror = destination / Path(artifact["source"]).name
        expected = artifact["sha256"]

        assert mirror.is_file(), str(mirror)
        assert mirror.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(mirror.read_bytes()).hexdigest().upper() == expected
        assert artifact["copy_sha256_matched"] is True

    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert {
        "code/ops/BUILD_EXTERNAL_RESPONSE_STATE_E_DRIVE_SYNC_RECEIPT.py",
        "code/ops/BUILD_DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT.py",
        "code/ops/BUILD_TRACTION_OPPORTUNITY_INTAKE_LEDGER.py",
        "code/ops/BUILD_TRACTION_FOLLOWUP_PACKET.py",
        "code/ops/BUILD_EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET.py",
        "code/ops/BUILD_REVIEWER_CONCIERGE_PACKET.py",
        "code/ops/BUILD_AGENCY_SUBMISSION_ASSEMBLY_GATE.py",
        "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.json",
        "assets/hardware/flowform_curved_motherboard_honeycomb_battery_v3_concept.png",
        "grant_submissions/funding_sprint_20260709/DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.json",
        "grant_submissions/funding_sprint_20260709/DARPA_SN_26_97_PUBLIC_SUBMISSION_RECEIPT_2026-07-17.md",
        "out/ops/traction_opportunity_intake_ledger_latest.json",
        "out/ops/traction_followup_packet_latest.json",
        "out/ops/evtit_technical_sprint_scope_packet_latest.json",
        "out/ops/reviewer_concierge_packet_latest.json",
        "out/ops/human_action_docket_latest.json",
        "out/ops/reviewer_decision_brief_latest.json",
        "out/ops/customer_commercialization_packet_latest.json",
        "out/ops/reviewer_investor_fast_lane_router_latest.json",
        "out/ops/agency_submission_assembly_gate_latest.json",
        "grant_submissions/DLA26BZ03_NV011_MissionWeave/MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json",
    }.issubset(mirrored_sources)
    assert len({Path(source).name.casefold() for source in mirrored_sources}) == len(
        mirrored_sources
    )

    assert "does not prove" in receipt["claim_boundary"].lower()


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
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 63
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False
    destination = Path(receipt["destination_root"])
    for artifact in receipt["artifacts"]:
        source_path = Path(artifact["source"])
        mirror = destination / source_path.name
        assert source_path.is_absolute() is False
        assert ".." not in source_path.parts
        assert mirror.is_file(), str(mirror)
        assert mirror.stat().st_size == artifact["bytes"], artifact["source"]
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
        "code/ops/BUILD_FHWA_TSMO_PARTNER_OUTREACH_CONTROL.py",
        "tests/test_fhwa_tsmo_partner_outreach_control.py",
        "grant_submissions/funding_sprint_20260709/FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json",
        "grant_submissions/funding_sprint_20260709/FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.md",
        "code/ops/BUILD_NEAR_DEADLINE_PACKAGE_DECISION_GATE.py",
        "tests/test_near_deadline_package_decision_gate.py",
        "grant_submissions/funding_sprint_20260709/NEAR_DEADLINE_PACKAGE_DECISION_GATE_2026-07-16.md",
        "out/ops/near_deadline_package_decision_gate_latest.json",
        "grant_submissions/funding_sprint_20260709/FHWA_TSMO_QUALIFIED_TEAMING_REQUEST_2026-07-16.md",
        "out/ops/external_engagement_response_register_latest.json",
        "dashboard/data/external_engagement_response_register.json",
    }.issubset(mirrored_sources)

    assert "does not prove" in receipt["claim_boundary"]
