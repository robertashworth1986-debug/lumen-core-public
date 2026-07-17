from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py"
SCAN_DATE = date(2026, 7, 16)


def load_module():
    spec = importlib.util.spec_from_file_location("near_deadline_submission_command_board", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_near_deadline_board_identifies_stage_now_and_human_gates():
    module = load_module()
    payload = module.build_payload(scan_date=SCAN_DATE)

    assert payload["schema"] == "near_deadline_submission_command_board_v4"
    assert payload["status"] == "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_WITH_VERIFIED_SENDS"
    assert payload["summary"]["lane_count"] == 17
    assert payload["summary"]["stage_now_count"] == 4
    assert payload["summary"]["sent_verified_count"] == 3
    assert payload["summary"]["emergency_eligibility_gate_count"] == 0
    assert payload["summary"]["no_bid_or_partner_only_count"] == 6
    assert payload["summary"]["expired_without_verified_send_count"] == 1
    assert payload["summary"]["human_gated_count"] == 13
    assert payload["summary"]["final_submit_allowed_without_human"] is False
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["pricing_allowed_without_human"] is False
    assert payload["summary"]["legal_certification_allowed_without_human"] is False
    assert "SAM.gov public credential rotation" in payload["summary"]["critical_same_day_infrastructure_action"]
    sam_rotation = payload["operational_controls"]["sam_public_key_rotation"]
    assert sam_rotation["status"] == "ROTATION_OVERDUE_REPLACEMENT_NOT_DETECTED"
    assert sam_rotation["deadline_state"] == "PAST_DUE"
    assert sam_rotation["aliases_consistent"] is True
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
    assert "W912HZ26SC005" in stage_ids
    assert "NASHVILLE-EC-FALL-2026" in stage_ids
    assert "LAUNCHTN-3686-2026" in stage_ids

    sent_ids = {row["opportunity_number"] for row in payload["sent_verified"]}
    assert sent_ids == {
        "80TECH26RFI0020",
        "ACCAPGAIDPRFI4",
        "75D301-26-RFI-73483",
    }

    assert "HHS-2026-ACL-NIDILRR-REGE-0212" in payload["summary"]["closest_deadline_lane"]
    assert "NASHVILLE-EC-FALL-2026" in payload["summary"]["closest_stage_ready_lane"]

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
    assert nsf["nearest_listed_full_proposal_deadline_date"] == "2026-07-27"
    assert nsf["nearest_listed_deadline_reachable"] is False
    assert nsf["full_proposal_planning_deadline_date"] == "2026-11-04"
    assert nsf["full_proposal_submission_allowed"] is False
    assert nsf["invitation_verified"] is False
    assert nsf["deadline_semantics"] == (
        "PROJECT_PITCH_GATE_ROLLING_FULL_PROPOSAL_INVITATION_REQUIRED"
    )
    assert "July 27" in nsf["official_deadline_text"]
    assert "not currently reachable" in nsf["official_deadline_text"]
    assert "26-510" in payload["summary"]["best_grants_lane"]
    assert "officially listed but currently inaccessible" in payload["summary"][
        "best_grants_lane"
    ]
    assert "planning only" in payload["summary"]["best_grants_lane"]
    fhwa = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "693JJ326R000012"
    )
    assert fhwa["command"] == "NO_SOLO_SUBMIT_PARTNER_ONLY"
    assert fhwa["eligibility_state"] == (
        "QUALIFIED_TARGET_CONTACTED_PARTNER_CONFIRMATION_PENDING"
    )
    assert fhwa["partner_outreach_status"] == (
        "OUTBOUND_SENT_PARTNER_CONFIRMATION_PENDING"
    )
    assert fhwa["qualified_partner_evidence_present"] is False
    assert fhwa["no_follow_up_before"] == "2026-07-23"
    assert "no solo bid" in payload["summary"]["best_contract_lane"].lower()
    rendered = module.render_markdown(payload)
    assert "INVITATION_CONTINGENT_PLANNING_TARGET" in rendered

    ec = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "NASHVILLE-EC-FALL-2026"
    )
    assert ec["command"] == "STAGE_APPLICATION"
    assert ec["deadline_date"] == "2026-07-17"
    assert ec["deadline_utc"] is None
    assert ec["deadline_semantics"] == "DATE_ONLY_CLOSE_TIME_NOT_LISTED_SUBMIT_EARLY"
    assert "TAKEOFF" in ec["fit_state"]
    assert "does not list a closing time" in ec["official_deadline_text"]
    assert any("six concise founder confirmations" in row for row in ec["today_work"])
    assert any(
        path.endswith("NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json")
        for path in ec["package_files"]
    )
    assert ec["external_send_allowed_without_human"] is False
    assert ec["final_submit_allowed_without_human"] is False

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
    assert any(path.endswith("LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx") for path in launchtn["package_files"])
    assert any(path.endswith("LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx") for path in launchtn["package_files"])
    assert launchtn["external_send_allowed_without_human"] is False
    assert launchtn["final_submit_allowed_without_human"] is False


def test_near_deadline_board_keeps_hud_and_bop_behind_correct_gates():
    module = load_module()
    payload = module.build_payload(scan_date=SCAN_DATE)

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
    payload = module.build_payload(scan_date=SCAN_DATE)
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
    assert "CDC are sent and receipt-backed" in rendered
    assert "SAM.gov public credential rotation became overdue" in rendered
    assert "Guarded installer: `code/ops/INSTALL_SAM_PUBLIC_CREDENTIAL.py`" in rendered
    assert "HTTP_404_EMPTY_RESPONSE_INCONCLUSIVE" in rendered
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
        "launchtn_3686_portal_field_map",
        "launchtn_3686_application_manifest",
        "launchtn_3686_pitch_deck",
        "launchtn_3686_financial_model",
        "external_engagement_response_register",
        "fhwa_partner_outreach_control",
        "sam_public_key_rotation_control",
        "patent_deadline_evidence_control",
    ):
        assert payload["source_ledgers"][source]["present"] is True

    for marker in module.SENSITIVE_MARKERS:
        assert marker not in lowered
