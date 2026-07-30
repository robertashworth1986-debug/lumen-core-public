from __future__ import annotations

import importlib.util
import hashlib
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py"
SCAN_DATE = date(2026, 7, 16)
BOARD_AS_OF = "2026-07-18T16:00:00Z"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
MISSIONWEAVE_ACTION_GATE = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location("near_deadline_submission_command_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def build_test_payload(module, scan_date: date = SCAN_DATE):
    return module.build_payload(
        scan_date=scan_date,
        generated_utc=BOARD_AS_OF,
        as_of_utc=BOARD_AS_OF,
    )


def test_near_deadline_board_identifies_stage_now_and_human_gates():
    module = load_module()
    payload = build_test_payload(module)

    assert payload["schema"] == "near_deadline_submission_command_board_v5"
    assert payload["status"] == (
        "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_FAIL_CLOSED_FRESHNESS_BLOCKERS"
    )
    assert payload["summary"]["lane_count"] == 23
    assert payload["summary"]["curated_navy_lane_count"] == 3
    assert payload["summary"]["stage_now_count"] == 4
    assert payload["summary"]["stage_candidate_count"] == 4
    assert payload["summary"]["stage_ready_count"] == 0
    assert payload["summary"]["sent_verified_count"] == 5
    assert payload["summary"]["emergency_eligibility_gate_count"] == 0
    assert payload["summary"]["no_bid_or_partner_only_count"] == 6
    assert payload["summary"]["expired_without_verified_send_count"] == 1
    assert payload["summary"]["human_gated_count"] == 17
    assert payload["summary"]["freshness_blocked_lane_count"] == 13
    assert payload["summary"]["sam_zero_row_inconclusive_blocker"] is True
    assert payload["summary"]["final_submit_allowed_without_human"] is False
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_human"] is False
    assert payload["summary"]["legal_certification_allowed_without_human"] is False
    assert "SAM.gov public credential rotation" in payload["summary"]["critical_same_day_infrastructure_action"]
    sam_rotation = payload["operational_controls"]["sam_public_key_rotation"]
    assert sam_rotation["status"] == "ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED"
    assert sam_rotation["deadline_state"] == "PAST_DUE"
    assert sam_rotation["aliases_consistent"] is False
    assert sam_rotation["replacement_installation_detected"] is False
    assert sam_rotation["rotation_verified"] is False
    assert sam_rotation["human_action_required"] is True
    assert sam_rotation["browser_navigation_performed"] is False
    assert sam_rotation["private_installer"] == "code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py"
    assert "became overdue" in payload["summary"]["critical_same_day_infrastructure_action"]
    patent_control = payload["operational_controls"]["patent_deadline_evidence"]
    assert patent_control["status"] == (
        "PAYMENT_ACKNOWLEDGEMENT_ONLY_OFFICIAL_DOCKET_REQUIRED"
    )
    assert patent_control["payment_acknowledgement_found"] is True
    assert patent_control["filing_receipt_found"] is False
    assert patent_control["official_correspondence_found"] is False
    assert patent_control["official_status_record_found"] is False
    assert patent_control["required_docket_role_count"] == 6
    assert patent_control["captured_required_docket_role_count"] == 0
    assert patent_control["docket_capture_complete"] is False
    assert len(patent_control["missing_required_docket_roles"]) == 6
    assert patent_control["private_capture_workflow"].endswith(
        "PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md"
    )
    assert patent_control["us_prosecution_deadline"] == (
        "UNVERIFIED_REQUIRES_NEWEST_OFFICIAL_NOTICE"
    )
    assert "TIME_SENSITIVE" in patent_control["foreign_pct_priority"]
    assert patent_control["human_action_required"] is True
    assert patent_control["browser_navigation_performed"] is False

    stage_ids = {row["opportunity_number"] for row in payload["stage_now"]}
    assert "80TECH26RFI0020" not in stage_ids
    assert "ACCAPGAIDPRFI4" not in stage_ids
    assert "693JJ326R000012" not in stage_ids
    assert "26-510" in stage_ids
    assert "W912HZ26SC005" not in stage_ids
    assert "NASHVILLE-EC-FALL-2026" not in stage_ids
    assert "OPENAI-BUILD-WEEK-2026" in stage_ids
    assert "DLA26BZ03-NV011" in stage_ids
    assert "LAUNCHTN-3686-2026" in stage_ids

    sent_ids = {row["opportunity_number"] for row in payload["sent_verified"]}
    assert sent_ids == {
        "80TECH26RFI0020",
        "ACCAPGAIDPRFI4",
        "75D301-26-RFI-73483",
        "NASHVILLE-EC-FALL-2026",
        "DARPA-SN-26-97",
    }

    assert "HHS-2026-ACL-NIDILRR-REGE-0212" in payload["summary"]["closest_deadline_lane"]
    assert payload["summary"]["closest_stage_ready_lane"] == (
        "No open lane is currently supported by the board."
    )
    assert payload["stage_ready"] == []
    assert "5/10" in payload["summary"]["strongest_today_action"]
    assert "5 open" in payload["summary"]["strongest_today_action"]
    assert "Nashville EC is portal-confirmed" in payload["summary"][
        "strongest_today_action"
    ]
    assert "5/10 gates pass" in payload["summary"]["fastest_low_friction_lane"]

    nsf = next(row for row in payload["lanes"] if row["opportunity_number"] == "26-510")
    assert nsf["deadline_date"] == "2026-11-04"
    assert nsf["deadline_utc"] is None
    assert nsf["project_pitch_due_date"] is None
    assert nsf["listed_full_proposal_deadline_dates"] == [
        "2026-07-27",
        "2026-11-04",
        "2027-03-04",
        "2027-07-07",
    ]
    assert nsf["past_listed_full_proposal_deadline_dates"] == ["2026-07-27"]
    assert nsf["future_listed_full_proposal_deadline_dates"] == [
        "2026-11-04",
        "2027-03-04",
        "2027-07-07",
    ]
    assert nsf["nearest_listed_full_proposal_deadline_date"] == "2026-11-04"
    assert nsf["nearest_listed_deadline_reachable"] is False
    assert nsf["full_proposal_planning_deadline_date"] == "2026-11-04"
    assert nsf["full_proposal_submission_allowed"] is False
    assert nsf["invitation_verified"] is False
    assert nsf["deadline_semantics"] == (
        "PROJECT_PITCH_GATE_ROLLING_FULL_PROPOSAL_INVITATION_REQUIRED"
    )
    assert "July 27, 2026 is past" in nsf["official_deadline_text"]
    assert "November 4, 2026" in nsf["official_deadline_text"]
    assert "remains unreachable" in nsf["official_deadline_text"]
    assert "26-510" in payload["summary"]["best_grants_lane"]
    assert "next rolling Project Pitch route" in payload["summary"][
        "best_grants_lane"
    ]
    fhwa = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "693JJ326R000012"
    )
    assert fhwa["command"] == "NO_SOLO_SUBMIT_PARTNER_ONLY"
    assert fhwa["eligibility_state"] == (
        "TEAM_SET_NO_ADDITIONAL_PARTNERS_ROUTE_CLOSED"
    )
    assert fhwa["partner_outreach_status"] == (
        "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
    )
    assert fhwa["partner_outreach_delivery_failure_count"] == 1
    assert fhwa["partner_outreach_replacement_send_count"] == 1
    assert fhwa["partner_outreach_confirmed_delivery_count"] == 1
    assert fhwa["partner_outreach_inbound_response_count"] == 2
    assert fhwa["partner_outreach_referral_count"] == 1
    assert fhwa["partner_outreach_acknowledgment_send_count"] == 1
    assert fhwa["partner_outreach_fit_check_confirmed_count"] == 0
    assert fhwa["partner_outreach_team_set_decline_count"] == 1
    assert fhwa["qualified_partner_evidence_present"] is False
    assert fhwa["no_follow_up_before"] is None
    assert any("Close the Cambridge Systematics route" in row for row in fhwa["today_work"])
    assert any(
        path.endswith("FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md")
        for path in fhwa["package_files"]
    )
    assert "no solo bid" in payload["summary"]["best_contract_lane"].lower()
    assert "route is closed" in payload["summary"]["best_contract_lane"].lower()
    rendered = module.render_markdown(payload)
    assert "INVITATION_CONTINGENT_PLANNING_TARGET" in rendered

    ec = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "NASHVILLE-EC-FALL-2026"
    )
    assert ec["command"] == "SENT_VERIFIED"
    assert ec["pre_send_command"] == "STAGE_APPLICATION"
    assert ec["submission_status"] == "PORTAL_SUBMISSION_CONFIRMED"
    assert ec["sent_utc"] == "2026-07-18T04:54:52.709214Z"
    assert ec["receipt_path"].endswith(
        "NASHVILLE_EC_SUBMISSION_RECEIPT_2026-07-17.json"
    )
    assert ec["verification_scope"] == "PORTAL_CONFIRMATION_PAGE_OBSERVED"
    assert ec["deadline_date"] == "2026-07-17"
    assert ec["deadline_utc"] == "2026-07-18T04:59:00Z"
    assert ec["deadline_semantics"] == (
        "OFFICIAL_REPLY_CONFIRMED_TIME_TIMEZONE_INFERRED_SUBMIT_EARLY"
    )
    assert "TAKEOFF" in ec["fit_state"]
    assert "11:59 p.m. on July 17" in ec["official_deadline_text"]
    assert "America/Chicago" in ec["official_deadline_text"]
    assert any("Monitor the existing email account" in row for row in ec["today_work"])
    assert any(
        path.endswith("NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json")
        for path in ec["package_files"]
    )
    assert any(
        path.endswith("NASHVILLE_EC_DEADLINE_PRESERVATION_ENGAGEMENT_RECEIPT_2026-07-17.json")
        for path in ec["package_files"]
    )
    assert any(
        path.endswith("NASHVILLE_EC_DEADLINE_PRESERVATION_RESPONSE_CONTROL_2026-07-17.md")
        for path in ec["package_files"]
    )
    assert any(
        path.endswith("NASHVILLE_EC_OFFICIAL_DEADLINE_CONFIRMATION_2026-07-17.json")
        for path in ec["package_files"]
    )
    assert any(
        path.endswith("NASHVILLE_EC_SUBMISSION_RECEIPT_2026-07-17.json")
        for path in ec["package_files"]
    )
    assert len(ec["package_files"]) == 11
    assert ec["deadline_support_status"] == (
        "OFFICIAL_SUPPORT_CONFIRMED_CLOSE_TIME_APPLICATION_NOT_SUBMITTED"
    )
    assert ec["deadline_support_sent_utc"] == "2026-07-17T12:05:34Z"
    assert ec["deadline_support_do_not_duplicate_send"] is True
    assert ec["deadline_support_email_is_application"] is False
    assert ec["deadline_support_reply_required"] is False
    assert ec["deadline_timezone_explicit_in_message"] is False
    assert ec["operational_timezone"] == "America/Chicago"
    assert any("Do not duplicate" in row for row in ec["today_work"])
    assert ec["action_gate_status"] == "PORTAL_SUBMISSION_CONFIRMED"
    assert ec["action_gate_submission_ready_for_human_click"] is False
    assert ec["action_gate_required_private_gate_count"] == 15
    assert ec["action_gate_passed_private_gate_count"] == 15
    assert ec["action_gate_open_gate_count"] == 0
    assert ec["action_gate_private_input_present"] is True
    assert ec["action_gate_private_values_exposed"] is False
    assert ec["private_capture_target_git_ignored"] is True
    assert ec["private_capture_required_founder_prompt_count"] == 6
    assert ec["private_capture_required_portal_answer_count"] == 11
    assert ec["private_capture_collector"].endswith(
        "CAPTURE_NASHVILLE_EC_PRIVATE_FACTS.py"
    )
    assert ec["private_capture_workflow"].endswith(
        "NASHVILLE_EC_PRIVATE_FACT_CAPTURE_WORKFLOW_2026-07-17.md"
    )
    assert ec["external_send_allowed_without_human"] is False
    assert ec["final_submit_allowed_without_human"] is False

    darpa = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "DARPA-SN-26-97"
    )
    assert darpa["command"] == "SENT_VERIFIED"
    assert darpa["submission_status"] == "EMAIL_SUBMISSION_SENT_BEFORE_DEADLINE"
    assert darpa["sent_utc"] == "2026-07-17T19:27:49Z"
    assert darpa["deadline_utc"] == "2026-07-17T21:00:00Z"
    assert darpa["acknowledgment_received"] is False
    assert darpa["human_gate"] == []
    assert len(darpa["receipt_attachment_sha256"]) == 64
    assert len(darpa["package_files"]) == 2

    build_week = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "OPENAI-BUILD-WEEK-2026"
    )
    assert build_week["command"] == "STAGE_APPLICATION"
    assert build_week["deadline_date"] == "2026-07-21"
    assert build_week["deadline_utc"] == "2026-07-22T00:00:00Z"
    assert build_week["deadline_semantics"] == "OFFICIAL_RULES_DEADLINE_VERIFIED"
    assert build_week["readiness_status"] == (
        "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"
    )
    assert build_week["readiness_gate_total"] == 10
    assert build_week["readiness_gate_pass_count"] == 5
    assert build_week["readiness_gate_open_count"] == 5
    assert build_week["public_demo_url"] == (
        "https://lumen-core.ai/build_week/prooflock_console/"
    )
    assert build_week["youtube_demo_url"] is None
    assert build_week["feedback_session_id_present"] is False
    assert build_week["confirmed_model_present"] is False
    assert len(build_week["package_files"]) == 5

    missionweave = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "DLA26BZ03-NV011"
    )
    missionweave_gate = json.loads(
        MISSIONWEAVE_ACTION_GATE.read_text(encoding="utf-8")
    )
    missionweave_gate_summary = missionweave_gate["gate_summary"]
    assert missionweave["command"] == "STAGE_DSIP_PROPOSAL"
    assert missionweave["deadline_date"] == "2026-07-22"
    assert missionweave["deadline_utc"] == "2026-07-22T16:00:00Z"
    assert missionweave["deadline_semantics"] == (
        "CROSS_SOURCE_2026_DATE_CONFIRMED_BAA_YEAR_TYPO_RECHECK_DSIP"
    )
    assert missionweave["deadline_source_discrepancy_present"] is True
    assert "July 22, 2025" in missionweave["official_deadline_text"]
    assert missionweave["package_manifest_integrity_pass"] is True
    assert missionweave["package_manifest_file_count"] == 15
    assert missionweave["action_gate_status"] == (
        "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    )
    assert missionweave["action_gate_submission_ready_for_human_click"] is False
    assert missionweave["action_gate_required_private_gate_count"] == (
        missionweave_gate_summary["required_private_gate_count"]
    )
    assert missionweave["action_gate_passed_private_gate_count"] == (
        missionweave_gate_summary["passed_private_gate_count"]
    )
    assert missionweave["action_gate_open_gate_count"] == (
        missionweave_gate_summary["open_gate_count"]
    )
    assert missionweave["action_gate_private_input_present"] is True
    assert missionweave["action_gate_private_values_exposed"] is False
    assert missionweave["action_gate_private_input_sha256_exposed"] is False
    assert missionweave["action_gate_private_capture_tool"].endswith(
        "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py"
    )
    assert missionweave["action_gate_private_volume2_finalizer"].endswith(
        "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py"
    )
    assert missionweave["action_gate_private_capture_workflow"].endswith(
        "MISSIONWEAVE_DSIP_PRIVATE_CAPTURE_WORKFLOW_2026-07-17.md"
    )
    assert missionweave["action_gate_private_final_volume2_present"] is True
    assert missionweave["action_gate_private_final_volume2_path_exposed"] is False
    assert missionweave["action_gate_private_final_volume2_sha256_exposed"] is False
    assert missionweave["action_gate_pre_submit_excludes_action_time_approval"] is True
    assert missionweave["action_gate_credential_values_accepted"] is False
    assert missionweave["action_gate_firm_pin_value_accepted"] is False
    assert missionweave["phase1_duration_months"] == 6
    assert missionweave["phase1_cost_ceiling_usd"] == 100000
    assert missionweave["topic_phase1_max_duration_months"] == 12
    assert missionweave["topic_phase1_max_cost_usd"] == 100000
    assert missionweave["itar_flag"] is True
    assert missionweave["projected_cmmc_level"] == "Level 2 (Self)"
    assert len(missionweave["package_files"]) == 12
    assert any(
        path.endswith("MISSIONWEAVE_DSIP_PACKAGE_MANIFEST_2026-07-16.json")
        for path in missionweave["package_files"]
    )
    assert any(
        path.endswith("MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.pdf")
        for path in missionweave["package_files"]
    )
    assert any(
        path.endswith("MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json")
        for path in missionweave["package_files"]
    )
    assert any(
        path.endswith("MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md")
        for path in missionweave["package_files"]
    )
    assert any(
        path.endswith("CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py")
        for path in missionweave["package_files"]
    )
    assert any(
        path.endswith("FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py")
        for path in missionweave["package_files"]
    )
    assert any(
        path.endswith("MISSIONWEAVE_DSIP_PRIVATE_CAPTURE_WORKFLOW_2026-07-17.md")
        for path in missionweave["package_files"]
    )
    assert missionweave["external_send_allowed_without_human"] is False
    assert missionweave["final_submit_allowed_without_human"] is False
    assert "DLA26BZ03-NV011" in payload["summary"]["best_grants_lane"]

    launchtn = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "LAUNCHTN-3686-2026"
    )
    assert launchtn["command"] == "STAGE_APPLICATION"
    assert launchtn["deadline_date"] == "2026-08-13"
    assert launchtn["deadline_utc"] == "2026-08-14T04:59:00Z"
    assert launchtn["deadline_semantics"] == "VERIFIED_CDT_TIMESTAMP"
    assert len(launchtn["package_files"]) == 4
    assert any(
        path.endswith("LUMENCORE_3686_PITCH_DECK_2026-07-29_REVIEW_REQUIRED.pptx")
        for path in launchtn["package_files"]
    )
    assert any(path.endswith("LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx") for path in launchtn["package_files"])
    assert launchtn["external_send_allowed_without_human"] is False
    assert launchtn["final_submit_allowed_without_human"] is False

    erdc = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "W912HZ26SC005"
    )
    assert erdc["command"] == "REVERIFY_SOURCE_BEFORE_STAGE"
    assert erdc["pre_freshness_command"] == "STAGE_CONCEPT_PAPER"
    assert erdc["source_data_current"] is False
    assert erdc["deadline_actionable"] is False
    assert erdc["format_and_marker_checks_pass"] is True
    assert erdc["semantic_review_complete"] is False
    assert erdc["solution_brief_status"] == (
        "CURRENT_PUBLIC_DRAFT_FORMAT_AND_MARKER_CHECKS_PASS_SEMANTIC_EVIDENCE_AND_PRIVATE_FINALIZATION_REQUIRED"
    )
    assert erdc["rom_gate_status"] == "PRIVATE_ROM_INPUT_NOT_CAPTURED"
    assert erdc["rom_private_input_present"] is False
    assert erdc["rom_ready_for_private_pdf_insertion"] is False
    assert erdc["private_final_candidate_gate_status"] == (
        "PRIVATE_FINAL_INPUTS_NOT_CAPTURED"
    )
    assert erdc["private_final_pdf_present"] is False
    assert erdc["private_final_document_checks_pass"] is False
    assert erdc["private_values_exposed_in_public_gate"] is False
    assert erdc["funding_currently_available"] is False
    assert any("Submittable" in item for item in erdc["today_work"])
    assert any("all-awards" in item for item in erdc["human_gate"])
    assert "FORMAT_AND_MARKER_CHECKS_PASS" in erdc["eligibility_state"]
    assert "REQUIRES_GOVERNMENT_COMPARATOR_EXTERNAL_TRUST_ROOT" in erdc["fit_state"]
    assert len(erdc["package_files"]) == 7
    assert not any("CONCEPT_STUB" in path for path in erdc["package_files"])
    assert any(
        path.endswith("ERDC_SDC_PHASE2_ROM_GATE_2026-07-29.json")
        for path in erdc["package_files"]
    )
    assert any(
        path.endswith("LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-29.pdf")
        for path in erdc["package_files"]
    )
    assert any(
        path.endswith("ERDC_SDC_PRIVATE_FINAL_CANDIDATE_GATE_2026-07-29.json")
        for path in erdc["package_files"]
    )
    assert any(
        path.endswith("ERDC_SDC_PRIVATE_FINAL_CANDIDATE_WORKFLOW_2026-07-29.md")
        for path in erdc["package_files"]
    )
    assert erdc["external_send_allowed_without_human"] is False
    assert erdc["final_submit_allowed_without_human"] is False


def test_current_board_never_promotes_expired_lanes_in_summary():
    module = load_module()
    payload = module.build_payload(
        scan_date=date(2026, 7, 29),
        generated_utc="2026-07-29T08:14:15Z",
        as_of_utc="2026-07-29T08:14:15Z",
    )

    summary = payload["summary"]
    assert summary["expired_without_verified_send_count"] == 8
    assert summary["sent_verified_count"] == 6
    assert summary["human_action_due_count"] == 1
    assert summary["closest_deadline_lane"].startswith(
        "NASHVILLE-EC-FALL-2026"
    )
    assert "Finish the OpenAI Build Week" not in summary["strongest_today_action"]
    assert "MissionWeave Phase I" not in summary["best_grants_lane"]
    assert "W912HZ26SC005" in summary["strongest_today_action"]
    assert "LaunchTN 3686" in summary["strongest_today_action"]
    assert "$10,000" in summary["strongest_today_action"]
    assert "LAUNCHTN-3686-2026" in summary[
        "best_near_term_cash_award_lane"
    ]
    assert "no selection or award is implied" in summary[
        "best_near_term_cash_award_lane"
    ]
    assert "NSF 26-510" in summary["best_grants_lane"]
    assert "W912HZ26SC005" in summary["best_contract_lane"]
    assert summary["fastest_low_friction_lane"] == (
        "No low-friction staging lane is currently supported by the board."
    )
    assert "Expired lanes remain closed" in summary["strongest_today_action"]
    assert summary["stage_candidate_count"] == 2
    assert summary["stage_ready_count"] == 0
    assert payload["stage_ready"] == []
    lanes = {row["opportunity_number"]: row for row in payload["lanes"]}
    assert lanes["NASHVILLE-EC-FALL-2026"]["command"] == (
        "FOUNDER_ONBOARDING_ACTION_DUE"
    )
    assert lanes["NASHVILLE-EC-FALL-2026"]["deadline_utc"] is None
    assert lanes["NASHVILLE-EC-FALL-2026"]["deadline_date"] == "2026-07-31"
    assert lanes["NASHVILLE-EC-FALL-2026"]["live_form_control_count"] == 47
    assert (
        lanes["NASHVILLE-EC-FALL-2026"]["live_form_required_control_count"]
        == 36
    )
    assert lanes["NASHVILLE-EC-FALL-2026"]["live_form_optional_control_count"] == 11
    assert (
        lanes["NASHVILLE-EC-FALL-2026"][
            "live_form_agreement_or_signature_count"
        ]
        == 5
    )
    assert (
        lanes["NASHVILLE-EC-FALL-2026"][
            "live_form_native_required_count_previously_observed"
        ]
        == 17
    )
    assert (
        lanes["NASHVILLE-EC-FALL-2026"][
            "live_form_native_required_count_complete"
        ]
        is False
    )
    current_rendered = module.render_markdown(payload)
    assert "Live form controls: `47`" in current_rendered
    assert "Visibly required controls: `36`" in current_rendered
    assert "Earlier native-required count complete: `false`" in current_rendered
    assert lanes["OPENAI-BUILD-WEEK-2026"]["command"] == "SENT_VERIFIED"
    assert lanes["OPENAI-BUILD-WEEK-2026"]["verification_scope"] == (
        "OFFICIAL_DEVPOST_CONFIRMATION_EMAIL"
    )
    assert lanes["ONC-ARGOS-SSN-2026-OS351107"]["command"] == "SENT_VERIFIED"
    assert lanes["ONC-ARGOS-SSN-2026-OS351107"]["verification_scope"] == (
        "SENT_COPY_VERIFIED_AUTOMATIC_REPLY_ONLY"
    )
    assert lanes["DLA26BZ03-NV011"]["command"] == "EXPIRED_NO_SUBMISSION"
    assert lanes["DLA26BZ03-NV011"]["submission_status"] == (
        "OFFICIAL_DLA_CONFIRMED_PROPOSAL_IN_PROGRESS_NOT_SUBMITTED"
    )
    launchtn = next(
        row
        for row in payload["stage_now"]
        if row["opportunity_number"] == "LAUNCHTN-3686-2026"
    )
    assert launchtn["classification"] == "STAGE_CANDIDATE_NOT_READINESS_CLAIM"
    assert launchtn["deadline_actionable"] is False
    assert launchtn["submission_ready"] is False
    rendered = module.render_markdown(payload)
    assert "Finish the OpenAI Build Week" not in rendered
    assert "MissionWeave DSIP package for July 22" not in rendered
    assert "## Stage Candidates" in rendered
    assert "not readiness claims" in rendered


def test_current_official_recheck_updates_active_and_closed_lanes():
    module = load_module()
    payload = module.build_payload(
        scan_date=date(2026, 7, 29),
        generated_utc="2026-07-29T10:30:00Z",
        as_of_utc="2026-07-29T10:30:00Z",
    )

    summary = payload["summary"]
    assert summary["lane_count"] == 27
    assert summary["stage_candidate_count"] == 3
    assert summary["stage_ready_count"] == 0
    assert summary["sent_verified_count"] == 6
    assert summary["no_bid_or_partner_only_count"] == 8
    assert summary["expired_without_verified_send_count"] == 8
    assert summary["human_gated_count"] == 11
    assert summary["human_action_due_count"] == 1
    assert summary["freshness_blocked_lane_count"] == 10
    assert payload["stage_ready"] == []

    lanes = {row["opportunity_number"]: row for row in payload["lanes"]}

    erdc = lanes["W912HZ26SC005"]
    assert erdc["command"] == "STAGE_CONCEPT_PAPER"
    assert erdc["source_freshness_status"] == "CURRENT_OFFICIAL_RECHECK"
    assert erdc["source_data_current"] is True
    assert erdc["source_data_current_scope"] == (
        "PUBLIC_OPPORTUNITY_STATUS_SCHEDULE_AND_CURRENT_ATTACHMENT_SET"
    )
    assert erdc["source_attachment_set_current"] is True
    assert erdc["deadline_actionable"] is True
    assert erdc["freshness_blockers"] == []
    assert erdc["funding_currently_available"] is False
    assert erdc["response_type"] == "RFI_ONLY_NO_CURRENT_FUNDING"
    assert erdc["private_final_pdf_present"] is False
    assert erdc["private_final_candidate_gate_status"] == (
        "PRIVATE_FINAL_INPUTS_NOT_CAPTURED"
    )
    assert erdc["private_final_document_checks_pass"] is False
    assert erdc["portal_upload_set_status"] == "NONE_PRIVATE_FINAL_REQUIRED"
    assert erdc["portal_upload_files"] == []
    assert erdc["submission_ready"] is False
    assert erdc["semantic_review_complete"] is False
    assert erdc["official_source_integrity_pass"] is True
    assert erdc["bounded_evidence_receipt_pass"] is True
    assert erdc["rom_submission_ready"] is False
    assert erdc["private_final_submission_ready"] is False
    assert erdc["private_final_unresolved_gate_count_effective"] == 12
    assert (
        "CURRENT_OFFICIAL_SOURCE_INTEGRITY"
        in erdc["private_final_unresolved_gates_raw"]
    )
    assert (
        "CURRENT_OFFICIAL_SOURCE_INTEGRITY"
        not in erdc["private_final_unresolved_gates_effective"]
    )
    assert (
        "BOUNDED_EVIDENCE_RECEIPT"
        not in erdc["private_final_unresolved_gates_effective"]
    )

    launchtn = lanes["LAUNCHTN-3686-2026"]
    assert launchtn["command"] == "STAGE_APPLICATION"
    assert launchtn["source_freshness_status"] == "CURRENT_OFFICIAL_RECHECK"
    assert launchtn["deadline_actionable"] is True
    assert launchtn["submission_ready"] is False
    assert launchtn["attachment_deck_status"] == (
        "VENUE_DECK_QA_PASSED_FOUNDER_FACTS_AND_FINAL_REVIEW_REQUIRED"
    )
    assert launchtn["attachment_financial_status"] == (
        "PLANNING_MODEL_ARITHMETIC_QA_ONLY_FOUNDER_ASSUMPTION_APPROVAL_REQUIRED"
    )
    assert launchtn["portal_upload_set_status"] == (
        "NONE_ATTACHMENT_AND_PORTAL_GATES_OPEN"
    )
    assert launchtn["portal_upload_files"] == []
    assert launchtn["application_manifest_status"] == "CURRENT_CANONICAL_MANIFEST"
    assert launchtn["application_required_field_count"] == 25
    assert launchtn["application_field_count"] == 30
    assert launchtn["human_or_private_fact_gate_count"] == 14
    assert launchtn["required_attachment_count"] == 2
    assert launchtn["required_attachments_present"] == 2
    assert launchtn["required_attachments_structural_qa_passed"] == 2
    assert launchtn["required_attachments_final_qa_passed"] == 0
    assert launchtn["required_attachments_safe_to_upload"] == 0
    assert launchtn["attachments_final_qa"] == "0/2"
    assert launchtn["safe_upload_count"] == 0
    assert launchtn["upload_set_ready"] is False
    assert any(
        path.endswith(
            "LUMENCORE_3686_PITCH_DECK_2026-07-29_REVIEW_REQUIRED.pptx"
        )
        for path in launchtn["package_files"]
    )
    assert not any(
        path.endswith("LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx")
        for path in launchtn["package_files"]
    )
    rendered = module.render_markdown(payload)
    assert "Required attachments final QA: `0/2`" in rendered
    assert "Safe upload count: `0`" in rendered
    assert "Semantic review complete: `false`" in rendered
    assert "Effective private-final unresolved gates: `12`" in rendered

    fhwa = lanes["693JJ326R000012"]
    assert fhwa["official_recheck_status"] == "ACTIVE_AMENDED"
    assert fhwa["command"] == "NO_SOLO_SUBMIT_PARTNER_ONLY"
    assert fhwa["deadline_actionable"] is True

    army = lanes["W900KK-26-R-0001"]
    assert army["command"] == "AUTHENTICATED_ATTACHMENT_REVIEW_REQUIRED"
    assert army["source_data_current"] is True
    assert army["deadline_actionable"] is False

    mda = lanes["MDA26BZ04-NV007"]
    assert mda["command"] == "NO_BID_TOPIC_REMOVED"
    assert mda["deadline_utc"] is None
    assert mda["deadline_date"] is None
    assert mda["deadline_actionable"] is False

    falcon = lanes["DPA26BZ04-DV016"]
    assert falcon["command"] == "NO_BID_TECHNICAL_GATE_FAILED"
    assert falcon["official_recheck_status"] == "OPEN"
    assert falcon["deadline_actionable"] is False

    nsf = lanes["26-510"]
    assert nsf["source_freshness_status"] == "CURRENT_OFFICIAL_RECHECK"
    assert nsf["deadline_semantics"] == (
        "PROJECT_PITCH_ROLLING_NEXT_FULL_PROPOSAL_DEADLINE_INVITATION_REQUIRED"
    )
    assert nsf["deadline_actionable"] is False

    for lane in payload["lanes"]:
        assert lane["external_send_allowed_without_human"] is False
        assert lane["final_submit_allowed_without_human"] is False


def test_near_deadline_board_keeps_hud_and_bop_behind_correct_gates():
    module = load_module()
    payload = build_test_payload(module)

    lanes = {row["opportunity_number"]: row for row in payload["lanes"]}
    assert lanes["PDR-2600-DC-029Q"]["command"] == "EXPIRED_NO_SUBMISSION"
    assert lanes["PDR-2600-DC-029Q"]["pre_expiry_command"] == "ELIGIBILITY_AND_PARTNER_GATE"
    assert lanes["PDR-2600-DC-029Q"]["submission_status"] == "DEADLINE_PASSED_NO_VERIFIED_SEND"
    assert lanes["PDR-2600-DC-029Q"]["deadline_utc"] == "2026-07-14T03:59:59Z"
    assert lanes["PDR-2600-DC-029Q"]["official_deadline_text"].endswith("Eastern Time")
    assert lanes["15BCMS26Q70000005"]["command"] == "NO_SOLO_SUBMIT_PARTNER_ONLY"
    assert "HIPAA_ATO_HSPD12" in lanes["15BCMS26Q70000005"]["fit_state"]
    assert lanes["15BCMS26Q70000005"]["official_url"].endswith(
        "/52680f2a89c241b3a055c35d816b7f20/view"
    )
    assert lanes["HHS-2026-ACF-ACYF-CA-0037"]["command"] == "NO_SOLO_SUBMIT_PARTNER_ONLY"
    assert lanes["HHS-2026-ACL-NIDILRR-REGE-0212"]["eligibility_state"] == "SMALL_BUSINESS_ELIGIBLE"
    assert lanes["26-508"]["command"] == "NO_BID_MISSED_PREREQUISITE"
    assert "JUNE_16" in lanes["26-508"]["eligibility_state"]

    for lane in payload["lanes"]:
        assert lane["external_send_allowed_without_human"] is False
        assert lane["final_submit_allowed_without_human"] is False
        assert lane["days_to_close"] == module.days_to_close(
            lane["deadline_date"], SCAN_DATE
        )
        assert lane["deadline_bucket"] == module.deadline_bucket(lane["days_to_close"])
        assert lane["eligibility_state"]
        assert lane["fit_state"]
        assert len(lane["lane_sha256"]) == 64


def test_near_deadline_board_rendering_is_safe_and_cites_sources():
    module = load_module()
    payload = build_test_payload(module)
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Near-Deadline Submission Command Board" in rendered
    assert "Final submit without human: `false`" in rendered
    assert "https://seedfund.nsf.gov/project-pitch/" in rendered
    assert "https://ec.co/apply/" in rendered
    assert "https://www.grants.gov/search-results-detail/362360" in rendered
    assert "Sent And Verified" in rendered
    assert "No-Bid Or Partner-Only" in rendered
    assert "Expired without verified send: `1`" in rendered
    assert "CDC acknowledged receipt" in rendered
    assert "Nashville EC is portal-confirmed" in rendered
    assert "DARPA was sent before deadline with acknowledgment pending" in rendered
    assert "SAM.gov public credential rotation became overdue" in rendered
    assert "Guarded installer: `code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py`" in rendered
    assert "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE" in rendered
    assert "Status: `PORTAL_SUBMISSION_CONFIRMED`" in rendered
    assert "OPENAI-BUILD-WEEK-2026" in rendered
    assert "5/10 gates pass" in rendered
    assert "Action gate: `PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN`" in rendered
    missionweave_gate = json.loads(
        MISSIONWEAVE_ACTION_GATE.read_text(encoding="utf-8")
    )
    missionweave_gate_summary = missionweave_gate["gate_summary"]
    assert (
        "Action gates passed: "
        f"`{missionweave_gate_summary['passed_private_gate_count']}/"
        f"{missionweave_gate_summary['required_private_gate_count']}`"
        in rendered
    )
    assert len(payload["command_board_sha256"]) == 64

    for source in (
        "cdc_engagement_receipt",
        "doj_bop_go_no_go",
        "doj_bop_source_manifest",
        "nsf_project_pitch_portal_fields",
        "nsf_project_pitch_routing_manifest",
        "nashville_ec_portal_field_map",
        "nashville_ec_application_manifest",
        "nashville_ec_human_fact_resolution",
        "nashville_ec_private_collector",
        "nashville_ec_private_validator",
        "nashville_ec_private_workflow",
        "nashville_ec_deadline_preservation_receipt",
        "nashville_ec_deadline_response_control",
        "nashville_ec_official_deadline_confirmation",
        "nashville_ec_submission_receipt",
        "darpa_sn_26_97_submission_receipt",
        "openai_build_week_submission_readiness",
        "openai_build_week_project_description",
        "openai_build_week_demo_script",
        "openai_build_week_requirements",
        "missionweave_dsip_package_manifest",
        "missionweave_dsip_assembly_map",
        "missionweave_volume2_pdf",
        "missionweave_dsip_action_gate",
        "missionweave_dsip_portal_checklist",
        "missionweave_dsip_private_capture_tool",
        "missionweave_dsip_private_capture_workflow",
        "missionweave_official_topic",
        "missionweave_baa_amendment_2",
        "missionweave_dla_component_instructions",
        "launchtn_3686_portal_field_map",
        "launchtn_3686_application_manifest",
        "launchtn_3686_pitch_deck",
        "launchtn_3686_financial_model",
        "external_engagement_response_register",
        "fhwa_partner_outreach_control",
        "fhwa_partner_response_control",
        "erdc_solution_brief_compliance_gate",
        "erdc_phase2_rom_gate",
        "erdc_phase2_rom_workflow",
        "erdc_private_final_candidate_gate",
        "erdc_private_final_candidate_workflow",
        "erdc_source_manifest",
        "erdc_public_draft_pdf",
        "sam_public_key_rotation_control",
        "patent_deadline_evidence_control",
    ):
        assert payload["source_ledgers"][source]["present"] is True

    for marker in module.SENSITIVE_MARKERS:
        assert marker not in lowered


def test_curated_open_navy_lanes_are_complete_and_status_distinct() -> None:
    module = load_module()
    payload = build_test_payload(module, date(2026, 7, 18))
    lanes = {row["opportunity_number"]: row for row in payload["lanes"]}

    curated_numbers = {
        "DON26BZ03-NV061",
        "DON26BZ03-NV063",
        "DON26BZ03-NV065",
    }
    assert curated_numbers <= lanes.keys()
    assert payload["summary"]["curated_navy_lane_count"] == 3
    assert curated_numbers <= set(payload["lane_status_groups"]["portal_only"])

    for number in curated_numbers:
        lane = lanes[number]
        assert lane["deadline_date"] == "2026-07-22"
        assert lane["deadline_utc"] == "2026-07-22T16:00:00Z"
        assert lane["official_deadline_text"] == (
            "Closes July 22, 2026 at 12:00 PM ET"
        )
        assert lane["deadline_source"].endswith(
            "config/grant_reviewer_curation_v1.json"
        )
        assert lane["deadline_currently_verified"] is False
        assert lane["deadline_actionable"] is False
        assert lane["published_window_open_by_recorded_dates"] is True
        assert lane["published_window_actionable"] is False
        assert lane["eligibility_verified"] is False
        assert lane["source_data_current"] is False
        assert lane["source_recheck_required"] is True
        assert lane["portal_status"] == "PORTAL_ONLY_UNVERIFIED"
        assert lane["portal_status_verified"] is False
        assert lane["command"] == "REVERIFY_SOURCE_BEFORE_STAGE"
        assert lane["submission_ready"] is False
        assert lane["final_submit_allowed_without_human"] is False
        assert "DSIP_CONTROLLING_NOTICE_RECHECK_REQUIRED" in lane[
            "freshness_blockers"
        ]
        assert "unofficial" in lane["source_authority_boundary"].lower()

    harbor = lanes["DON26BZ03-NV063"]
    assert harbor["package_status"] == "DEDICATED_PACKAGE"
    assert harbor["urgency_status"] == (
        "URGENT_PUBLISHED_DEADLINE_REVERIFY_REQUIRED"
    )
    assert harbor["readiness_status"] == "URGENT_NOT_READY"
    assert harbor["package_manifest_status"] == (
        "LOCAL_SEVEN_VOLUME_ASSEMBLY_PORTAL_AND_HUMAN_GATED"
    )
    assert any(
        path.endswith("NV063_DSIP_PACKAGE_MANIFEST_2026-07-16.json")
        for path in harbor["package_files"]
    )
    assert "real adversary labels" in harbor["claim_boundary"]

    assert lanes["DON26BZ03-NV061"]["package_status"] == "CONCEPT"
    assert lanes["DON26BZ03-NV065"]["package_status"] == "CONCEPT"
    assert {
        "DON26BZ03-NV061",
        "DON26BZ03-NV065",
    } <= set(payload["lane_status_groups"]["concept"])


def test_stale_sources_and_zero_row_sam_fail_closed() -> None:
    module = load_module()
    payload = build_test_payload(module, date(2026, 7, 18))
    freshness = payload["source_freshness"]

    assert freshness["as_of_utc"] == BOARD_AS_OF
    assert freshness["overall_status"] == "BLOCKED_REVERIFY_REQUIRED"
    assert freshness["submission_decisions_fail_closed"] is True
    for source in (
        "grant_reviewer_curation",
        "grant_reviewer_feed",
        "sam_rush_board",
        "grants_ranked",
        "zero_friction_pack",
    ):
        descriptor = freshness["sources"][source]
        assert descriptor["freshness_status"] in {
            "STALE_REVERIFY_REQUIRED",
            "FUTURE_TIMESTAMP_REVERIFY_REQUIRED",
        }
        assert descriptor["blocking"] is True

    sam = freshness["sources"]["sam_live_discovery"]
    assert sam["records"] == 0
    assert sam["zero_rows"] is True
    assert sam["status"] == "ZERO_ROW_SAM_RESPONSE_INCONCLUSIVE_BLOCKER"
    assert sam["freshness_status"] == "STALE_REVERIFY_REQUIRED"
    assert sam["reported_freshness_status_at_feed_build"] == (
        "CURRENT_WITHIN_TTL"
    )
    assert sam["blocking"] is True
    assert payload["zero_friction_pack_status"] == "STALE_REVERIFY_REQUIRED"
    assert payload["zero_friction_pack_reported_status"].endswith(
        "HUMAN_ACTION_REQUIRED"
    )

    lanes = {row["opportunity_number"]: row for row in payload["lanes"]}
    erdc = lanes["W912HZ26SC005"]
    assert erdc["pre_freshness_command"] == "STAGE_CONCEPT_PAPER"
    assert erdc["command"] == "REVERIFY_SOURCE_BEFORE_STAGE"
    assert erdc["package_status"] == "CONCEPT"
    assert erdc["source_data_current"] is False
    assert erdc["deadline_actionable"] is False
    assert erdc["submission_ready"] is False
    assert any("ZERO_ROW_SAM" in blocker for blocker in erdc["freshness_blockers"])
    assert "W912HZ26SC005" not in {
        row["opportunity_number"] for row in payload["stage_now"]
    }
    assert lanes["80TECH26RFI0020"]["command"] == "SENT_VERIFIED"

    rebuilt = build_test_payload(module, date(2026, 7, 18))
    assert rebuilt == payload
    assert rebuilt["command_board_sha256"] == payload["command_board_sha256"]


def test_nashville_private_action_gate_summarizes_without_exposing_values(
    tmp_path: Path,
) -> None:
    module = load_module()
    private_map = tmp_path / "nashville_ec_portal_fill_map.private.json"
    private_map.write_text(
        json.dumps(
            {
                "schema": "lumencore.nashville_ec_private_portal_fill_map.v1",
                "status": "VALIDATED_PRIVATE_PORTAL_FILL_MAP",
                "private_portal_only": True,
                "public_repo_publish_allowed": False,
                "question_answer_count": 11,
                "question_answers": [
                    {"question_id": 38, "value": "DO_NOT_EXPOSE_SENTINEL"}
                ],
                "final_action_gate": {
                    "private_facts_validated": True,
                    "live_portal_preview_reviewed": False,
                    "fee_and_terms_reviewed": False,
                    "final_submission_authorized_at_action_time": False,
                },
            }
        ),
        encoding="utf-8",
    )
    module.NASHVILLE_EC_PRIVATE_FILL_MAP = private_map

    gate = module.nashville_private_action_gate()

    assert gate["status"] == "PRIVATE_FACTS_VALIDATED_PORTAL_PREVIEW_REQUIRED"
    assert gate["required_private_gate_count"] == 15
    assert gate["passed_private_gate_count"] == 12
    assert gate["open_gate_count"] == 3
    assert gate["private_input_present"] is True
    assert gate["private_values_exposed"] is False
    assert "DO_NOT_EXPOSE_SENTINEL" not in json.dumps(gate)


def test_missionweave_dsip_action_gate_historical_mirror_receipt_is_consistent():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 16
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_values_mirrored"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        assert artifact["bytes"] == artifact["copy_bytes"]
        assert artifact["sha256"] == artifact["copy_sha256"]
        assert artifact["copy_sha256_matched"] is True
        destination = Path(artifact["destination"])
        if destination.is_file():
            assert destination.stat().st_size == artifact["copy_bytes"]
            assert sha256_file(destination) == artifact["copy_sha256"]
