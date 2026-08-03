from __future__ import annotations

import copy
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_SUBMISSION_AUTHORITY_MATRIX.py"


def load_module():
    spec = importlib.util.spec_from_file_location("submission_authority_matrix", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_submission_authority_matrix_blocks_all_final_actions():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "submission_authority_matrix_v1"
    assert payload["status"] == "SUBMISSION_AUTHORITY_MATRIX_BLOCKED"
    assert payload["control_integrity_status"] == (
        "CONTROL_INTEGRITY_PASS_ACTION_BLOCKED"
    )
    assert payload["summary"]["lane_count"] == 26
    assert payload["summary"]["docket_lane_count"] == 26
    assert payload["summary"]["concierge_lane_count"] == 20
    assert payload["summary"]["source_lane_counts_match"] is False
    assert payload["summary"]["all_action_types_mapped"] is True
    assert payload["summary"]["unmapped_action_types"] == []
    assert payload["summary"]["all_artifacts_present"] is True
    assert payload["summary"]["reviewer_gate_clear"] is False
    assert payload["summary"]["all_final_actions_blocked_without_human"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert len(payload["authority_matrix_sha256"]) == 64

    for row in payload["authority_rows"]:
        assert row["can_send_external_without_human"] is False
        assert row["can_submit_without_human"] is False
        assert row["can_accept_terms_without_human"] is False
        assert row["action_type_mapped"] is True
        assert row["required_authority"]
        assert row["pre_action_checks"]
        assert row["first_artifact"]
        assert row["artifact_missing_count"] == 0
        assert row["authority_stop_rule"] == module.NO_FINAL_AUTHORITY
        assert len(row["authority_row_sha256"]) == 64


def test_specific_authority_gates_match_high_risk_lanes():
    module = load_module()
    payload = module.build_payload()
    rows = {row["lane_id"]: row for row in payload["authority_rows"]}

    assert rows["sam_registration_external_validation_watch"]["readiness_mode"] == "FEDERAL_REGISTRATION_SUBMITTED_VALIDATION_PENDING"
    assert "Active registration" in rows["sam_registration_external_validation_watch"]["pre_action_checks"][0]
    assert rows["lanl_vision_licensing_followup"]["readiness_mode"] == (
        "INBOUND_ONLY_MONITOR_NO_OUTBOUND_ACTION"
    )
    assert "new inbound message" in rows["lanl_vision_licensing_followup"][
        "required_authority"
    ]
    assert rows["uspto_georgia_patents_route"]["readiness_mode"] == "IP_PACKET_READY_COUNSEL_REQUIRED"
    assert rows["protecnium_its_infrastructure_signal"]["readiness_mode"] == "CUSTOMER_DISCOVERY_SIGNAL_READY_HUMAN_REPLY_REQUIRED"
    assert rows["darpa_dice_full_submission"]["readiness_mode"] == "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED"
    assert "BAA" in rows["darpa_dice_full_submission"]["required_authority"]
    assert rows["fhwa_tsmo_data_initiative"]["readiness_mode"] == (
        "HUMAN_REVIEW_REQUIRED_NO_EXTERNAL_ACTION"
    )
    assert rows["nasa_data_center_rfi"]["readiness_mode"] == (
        "HUMAN_REVIEW_REQUIRED_NO_EXTERNAL_ACTION"
    )
    assert rows["dla_missionweave_sbir"]["readiness_mode"] == (
        "PORTAL_READ_ONLY_STATUS_VERIFICATION"
    )
    assert "read-only status check" in rows["dla_missionweave_sbir"][
        "required_authority"
    ]
    assert rows["nsf_project_pitch"]["readiness_mode"] == "ROLLING_GATE_READY_RULE_CHECK_REQUIRED"
    assert "one-pending-pitch" in rows["nsf_project_pitch"]["required_authority"]
    assert rows["patent_deadline_counsel"]["readiness_mode"] == "IP_PACKET_READY_COUNSEL_REQUIRED"
    assert "Licensed patent counsel" in rows["patent_deadline_counsel"]["required_authority"]
    assert rows["hhs_ai_power_user_pilot"]["readiness_mode"] == "PARKED_NO_SOLO_ACTION"
    assert rows["csosa_public_safety_analytics"]["readiness_mode"] == "PARKED_NO_SOLO_ACTION"
    assert rows["login_gov_new_device_signin"]["readiness_mode"] == (
        "ACCOUNT_SECURITY_EVENT_HUMAN_REVIEW_REQUIRED"
    )
    assert rows["dla_amps_application_access"]["readiness_mode"] == (
        "ACCOUNT_ROLE_READ_ONLY_VERIFICATION_REQUIRED"
    )
    assert rows["epri_open_power_ai_mou_completed"]["readiness_mode"] == (
        "PRIVATE_AGREEMENT_CUSTODY_AND_OBLIGATION_REVIEW"
    )


def test_unknown_action_type_is_fail_closed_instead_of_crashing():
    module = load_module()
    original_read_json = module.read_json

    def read_with_unknown(path):
        payload = original_read_json(path)
        if path != module.DOCKET_JSON:
            return payload
        docket = copy.deepcopy(payload)
        unknown = copy.deepcopy(docket["docket_items"][0])
        unknown["lane_id"] = "unknown_fixture"
        unknown["name"] = "Unknown fixture"
        unknown["priority"] = 999
        unknown["action_type"] = "future_unregistered_action"
        docket["docket_items"].append(unknown)
        docket["summary"]["lane_count"] += 1
        return docket

    module.read_json = read_with_unknown
    payload = module.build_payload()
    row = next(
        row
        for row in payload["authority_rows"]
        if row["lane_id"] == "unknown_fixture"
    )

    assert payload["status"] == "SUBMISSION_AUTHORITY_MATRIX_BLOCKED"
    assert payload["control_integrity_status"] == "CONTROL_INTEGRITY_BLOCKED"
    assert payload["summary"]["all_action_types_mapped"] is False
    assert payload["summary"]["unmapped_action_types"] == [
        "future_unregistered_action"
    ]
    assert row["action_type_mapped"] is False
    assert row["readiness_mode"] == "UNMAPPED_ACTION_TYPE_BLOCKED"
    assert row["can_prepare_internal"] is False
    assert row["can_send_external_without_human"] is False
    assert row["can_submit_without_human"] is False


def test_rendered_authority_matrix_is_public_safe_and_action_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Submission Authority Matrix" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Can submit without human: `false`" in rendered
    assert "Can accept terms without human: `false`" in rendered
    assert module.NO_FINAL_AUTHORITY in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
