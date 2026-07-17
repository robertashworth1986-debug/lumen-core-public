from __future__ import annotations

import importlib.util
import hashlib
import json
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD.py"
SCAN_DATE = date(2026, 7, 16)
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "MISSIONWEAVE_DSIP_ACTION_GATE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
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


def test_near_deadline_board_identifies_stage_now_and_human_gates():
    module = load_module()
    payload = module.build_payload(scan_date=SCAN_DATE)

    assert payload["schema"] == "near_deadline_submission_command_board_v4"
    assert payload["status"] == "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_WITH_VERIFIED_SENDS"
    assert payload["summary"]["lane_count"] == 18
    assert payload["summary"]["stage_now_count"] == 5
    assert payload["summary"]["sent_verified_count"] == 3
    assert payload["summary"]["emergency_eligibility_gate_count"] == 0
    assert payload["summary"]["no_bid_or_partner_only_count"] == 6
    assert payload["summary"]["expired_without_verified_send_count"] == 1
    assert payload["summary"]["human_gated_count"] == 14
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
    assert "DLA26BZ03-NV011" in stage_ids
    assert "LAUNCHTN-3686-2026" in stage_ids

    sent_ids = {row["opportunity_number"] for row in payload["sent_verified"]}
    assert sent_ids == {
        "80TECH26RFI0020",
        "ACCAPGAIDPRFI4",
        "75D301-26-RFI-73483",
    }

    assert "HHS-2026-ACL-NIDILRR-REGE-0212" in payload["summary"]["closest_deadline_lane"]
    assert "NASHVILLE-EC-FALL-2026" in payload["summary"]["closest_stage_ready_lane"]
    assert "0/15" in payload["summary"]["strongest_today_action"]
    assert "six-prompt hidden collector" in payload["summary"]["strongest_today_action"]
    assert "must not be duplicated or treated as an application" in payload["summary"][
        "strongest_today_action"
    ]
    assert "hidden-input gate is 0/15" in payload["summary"][
        "fastest_low_friction_lane"
    ]

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
        "QUALIFIED_RESPONSE_LEAD_REFERRED_PARTNER_CONFIRMATION_PENDING"
    )
    assert fhwa["partner_outreach_status"] == (
        "QUALIFIED_RESPONSE_LEAD_REFERRAL_ACKNOWLEDGED_FIT_CHECK_PENDING"
    )
    assert fhwa["partner_outreach_delivery_failure_count"] == 1
    assert fhwa["partner_outreach_replacement_send_count"] == 1
    assert fhwa["partner_outreach_confirmed_delivery_count"] == 1
    assert fhwa["partner_outreach_inbound_response_count"] == 1
    assert fhwa["partner_outreach_referral_count"] == 1
    assert fhwa["partner_outreach_acknowledgment_send_count"] == 1
    assert fhwa["partner_outreach_fit_check_confirmed_count"] == 0
    assert fhwa["qualified_partner_evidence_present"] is False
    assert fhwa["no_follow_up_before"] == "2026-07-21"
    assert any("Do not reuse the rejected address" in row for row in fhwa["today_work"])
    assert any(
        path.endswith("FHWA_TSMO_PARTNER_RESPONSE_CONTROL_2026-07-17.md")
        for path in fhwa["package_files"]
    )
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
    assert any("hidden-prompt founder-fact collector" in row for row in ec["today_work"])
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
    assert len(ec["package_files"]) == 9
    assert ec["deadline_support_status"] == (
        "DEADLINE_PRESERVATION_QUERY_SENT_RESPONSE_PENDING"
    )
    assert ec["deadline_support_sent_utc"] == "2026-07-17T12:05:34Z"
    assert ec["deadline_support_do_not_duplicate_send"] is True
    assert ec["deadline_support_email_is_application"] is False
    assert any("do not resend" in row for row in ec["today_work"])
    assert ec["action_gate_status"] == "READY_FOR_HIDDEN_FOUNDER_INPUT"
    assert ec["action_gate_submission_ready_for_human_click"] is False
    assert ec["action_gate_required_private_gate_count"] == 15
    assert ec["action_gate_passed_private_gate_count"] == 0
    assert ec["action_gate_open_gate_count"] == 15
    assert ec["action_gate_private_input_present"] is False
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

    missionweave = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "DLA26BZ03-NV011"
    )
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
    assert missionweave["action_gate_status"] == "PRIVATE_DSIP_FACTS_NOT_CAPTURED"
    assert missionweave["action_gate_submission_ready_for_human_click"] is False
    assert missionweave["action_gate_required_private_gate_count"] == 50
    assert missionweave["action_gate_passed_private_gate_count"] == 0
    assert missionweave["action_gate_open_gate_count"] == 50
    assert missionweave["action_gate_private_input_present"] is False
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
    assert missionweave["action_gate_private_final_volume2_present"] is False
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
    assert any(path.endswith("LUMENCORE_3686_PITCH_DECK_2026-07-17.pptx") for path in launchtn["package_files"])
    assert any(path.endswith("LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx") for path in launchtn["package_files"])
    assert launchtn["external_send_allowed_without_human"] is False
    assert launchtn["final_submit_allowed_without_human"] is False

    erdc = next(
        row
        for row in payload["lanes"]
        if row["opportunity_number"] == "W912HZ26SC005"
    )
    assert erdc["command"] == "STAGE_CONCEPT_PAPER"
    assert erdc["technical_document_checks_pass"] is True
    assert erdc["solution_brief_status"] == (
        "TECHNICAL_DRAFT_PASS_PRIVATE_ROM_AND_SAM_FINALIZATION_REQUIRED"
    )
    assert erdc["rom_gate_status"] == "PRIVATE_ROM_INPUT_NOT_CAPTURED"
    assert erdc["rom_private_input_present"] is False
    assert erdc["rom_ready_for_private_pdf_insertion"] is False
    assert erdc["funding_currently_available"] is False
    assert "TECHNICAL_DRAFT_PASS" in erdc["eligibility_state"]
    assert "TECHNICAL_DOCUMENT_PASS" in erdc["fit_state"]
    assert len(erdc["package_files"]) == 5
    assert not any("CONCEPT_STUB" in path for path in erdc["package_files"])
    assert any(
        path.endswith("ERDC_SDC_PHASE2_ROM_GATE_2026-07-17.json")
        for path in erdc["package_files"]
    )
    assert any(
        path.endswith("LumenCore_ERDC_SDC_Solution_Brief_PUBLIC_DRAFT_2026-07-17.pdf")
        for path in erdc["package_files"]
    )
    assert erdc["external_send_allowed_without_human"] is False
    assert erdc["final_submit_allowed_without_human"] is False


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
    assert "Action gate: `READY_FOR_HIDDEN_FOUNDER_INPUT`" in rendered
    assert "Action gates passed: `0/15`" in rendered
    assert "Action gate: `PRIVATE_DSIP_FACTS_NOT_CAPTURED`" in rendered
    assert "Action gates passed: `0/50`" in rendered
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
        "erdc_source_manifest",
        "erdc_public_draft_pdf",
        "sam_public_key_rotation_control",
        "patent_deadline_evidence_control",
    ):
        assert payload["source_ledgers"][source]["present"] is True

    for marker in module.SENSITIVE_MARKERS:
        assert marker not in lowered


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


def test_missionweave_dsip_action_gate_historical_mirror_receipt_matches():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 16
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_values_mirrored"] is False
    assert receipt["destination_root"].startswith("E:/LumaProofVault/")
    for artifact in receipt["artifacts"]:
        source = ROOT / artifact["source"]
        destination = Path(artifact["destination"])
        assert source.is_file(), artifact["source"]
        assert destination.is_file(), artifact["destination"]
        assert destination.stat().st_size == artifact["bytes"]
        assert sha256_file(destination) == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True
