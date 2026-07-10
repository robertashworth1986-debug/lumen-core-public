from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_AGENCY_SUBMISSION_ASSEMBLY_GATE.py"


def load_module():
    spec = importlib.util.spec_from_file_location("agency_submission_assembly_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_assembly_gate_indexes_federal_and_ip_lanes():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "agency_submission_assembly_gate_v1"
    assert payload["status"] == "AGENCY_SUBMISSION_ASSEMBLY_READY_HUMAN_GATED"
    assert summary["assembly_lane_count"] == 15
    assert summary["first_artifacts_present"] is True
    assert summary["reviewer_gate_clear"] is True
    assert summary["federal_protocol_status"] == "FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED"
    assert summary["agency_activation_status"] == "AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED"
    assert summary["authority_lane_count"] == 19
    assert summary["all_final_actions_blocked_without_human"] is True
    assert summary["external_send_allowed_without_human"] is False
    assert summary["final_submission_allowed_without_human"] is False
    assert summary["legal_or_certification_action_allowed_without_human"] is False
    assert summary["live_trading_allowed"] is False
    assert summary["capital_movement_allowed"] is False
    assert summary["unsafe_secret_count"] == 0
    assert summary["unsafe_claim_count"] == 0
    assert len(payload["assembly_gate_sha256"]) == 64


def test_assembly_rows_have_components_blockers_and_hashes():
    module = load_module()
    payload = module.build_payload()
    rows = {row["lane_id"]: row for row in payload["assembly_rows"]}
    status_counts = payload["summary"]["status_counts"]

    for lane_id in [
        "sam_registration_external_validation_watch",
        "darpa_dice_full_submission",
        "dla_missionweave_sbir",
        "nsf_project_pitch",
        "uspto_georgia_patents_route",
        "patent_deadline_counsel",
        "hhs_ai_power_user_pilot",
    ]:
        assert lane_id in rows

    assert status_counts["ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED"] == 5
    assert status_counts["COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED"] == 2
    assert status_counts["PARTNER_OR_NO_SOLO_BLOCKED"] == 4
    assert rows["sam_registration_external_validation_watch"]["package_status"] == "VALIDATION_WATCH_NOT_SUBMISSION"
    assert rows["darpa_dice_full_submission"]["package_status"] == "ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED"
    assert rows["dla_missionweave_sbir"]["package_status"] == "ASSEMBLED_FOR_REVIEW_FINAL_ACTION_BLOCKED"
    assert rows["uspto_georgia_patents_route"]["package_status"] == "COUNSEL_PACKET_READY_LEGAL_ACTION_BLOCKED"

    for row in payload["assembly_rows"]:
        assert row["component_count"] == 8
        assert row["review_ready_component_count"] == 8
        assert row["first_artifact"]["present"] is True
        assert row["first_artifact"]["bytes"] > 0
        assert len(row["first_artifact"]["sha256"]) == 64
        assert row["assembly_blockers"]
        assert row["claim_boundary"]
        assert row["external_send_allowed_without_human"] is False
        assert row["final_submission_allowed_without_human"] is False
        assert row["legal_or_certification_action_allowed_without_human"] is False
        assert len(row["assembly_row_sha256"]) == 64


def test_rendered_assembly_gate_is_public_safe_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Agency Submission Assembly Gate" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Legal/certification action without human: `false`" in rendered
    assert "Capital movement allowed: `false`" in rendered
    assert "sam_registration_external_validation_watch" in rendered
    assert "darpa_dice_full_submission" in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
