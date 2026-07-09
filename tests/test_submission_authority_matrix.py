from __future__ import annotations

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
    assert payload["status"] == "SUBMISSION_AUTHORITY_MATRIX_READY"
    assert payload["summary"]["lane_count"] == 15
    assert payload["summary"]["docket_lane_count"] == 15
    assert payload["summary"]["concierge_lane_count"] == 15
    assert payload["summary"]["all_artifacts_present"] is True
    assert payload["summary"]["reviewer_gate_clear"] is True
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

    assert rows["darpa_dice_full_submission"]["readiness_mode"] == "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED"
    assert "BAA" in rows["darpa_dice_full_submission"]["required_authority"]
    assert rows["fhwa_tsmo_data_initiative"]["readiness_mode"] == "FEDERAL_DRAFT_READY_SUBMISSION_BLOCKED"
    assert "SAM" in rows["fhwa_tsmo_data_initiative"]["required_authority"]
    assert rows["nasa_data_center_rfi"]["readiness_mode"] == "RFI_DRAFT_READY_SEND_BLOCKED"
    assert rows["dla_missionweave_sbir"]["readiness_mode"] == "SBIR_DRAFT_READY_PORTAL_BLOCKED"
    assert "Firm PIN" in rows["dla_missionweave_sbir"]["required_authority"]
    assert rows["nsf_project_pitch"]["readiness_mode"] == "ROLLING_GATE_READY_RULE_CHECK_REQUIRED"
    assert "one-pending-pitch" in rows["nsf_project_pitch"]["required_authority"]
    assert rows["patent_deadline_counsel"]["readiness_mode"] == "IP_PACKET_READY_COUNSEL_REQUIRED"
    assert "Licensed patent counsel" in rows["patent_deadline_counsel"]["required_authority"]
    assert rows["hhs_ai_power_user_pilot"]["readiness_mode"] == "PARKED_NO_SOLO_ACTION"
    assert rows["csosa_public_safety_analytics"]["readiness_mode"] == "PARKED_NO_SOLO_ACTION"


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
