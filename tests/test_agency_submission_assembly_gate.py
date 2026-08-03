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


def test_assembly_gate_indexes_current_funding_and_ip_lanes():
    module = load_module()
    payload = module.build_payload()
    summary = payload["summary"]

    assert payload["schema"] == "agency_submission_assembly_gate_v2"
    assert payload["status"] == "AGENCY_SUBMISSION_ASSEMBLY_BLOCKED"
    assert summary["assembly_lane_count"] == 19
    assert summary["first_artifacts_present"] is True
    assert summary["reviewer_gate_clear"] is False
    assert summary["submission_conformance_status"] == "SUBMISSION_CONFORMANCE_BLOCKED"
    assert summary["submission_conformance_all_current_lanes_covered"] is True
    assert summary["assembly_conformance_coverage_clear"] is True
    assert summary["unrepresented_active_conformance_lane_count"] == 0
    assert summary["active_submission_candidate_count"] == 3
    assert summary["active_argument_pass_count"] == 0
    assert summary["active_argument_blocked_count"] == 3
    assert summary["argument_gate_clear"] is False
    assert summary["federal_protocol_status"] == "FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED"
    assert summary["agency_activation_status"] == "AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED"
    assert summary["authority_lane_count"] == 26
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
        "cdc_ai_acquisition_rfi",
        "erdc_sovereign_cloud_cso",
        "darpa_falcon_dpa26bz04_dv016",
        "launchtn_3686_pitch_2026",
    ]:
        assert lane_id in rows

    assert status_counts["ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW"] == 3
    assert status_counts["CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"] == 1
    assert status_counts["EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"] == 1
    assert status_counts["MONITOR_ONLY_NO_DUPLICATE_SUBMISSION"] == 3
    assert status_counts["NO_CURRENT_SUBMISSION_ROUTE"] == 5
    assert status_counts["PARTNER_OR_NO_SOLO_BLOCKED"] == 4
    assert status_counts["TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY"] == 1
    assert rows["sam_registration_external_validation_watch"]["package_status"] == "NO_CURRENT_SUBMISSION_ROUTE"
    assert rows["darpa_dice_full_submission"]["package_status"] == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    assert rows["darpa_dice_full_submission"]["submission_conformance_status"] == "CLOSED_OFFICIAL_DECISION_POSTMORTEM_ONLY"
    assert rows["dla_missionweave_sbir"]["package_status"] == "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"
    assert rows["dla_missionweave_sbir"]["submission_conformance_status"] == "EXPIRED_NO_VERIFIED_SUBMISSION_REUSE_BLOCKED"
    assert rows["dla_missionweave_sbir"]["argument_conformance_pass"] is False
    assert rows["nsf_project_pitch"]["package_status"] == "ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW"
    assert rows["nsf_project_pitch"]["argument_conformance_pass"] is False
    assert rows["dla_missionweave_sbir"]["status"] == "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    assert rows["uspto_georgia_patents_route"]["package_status"] == "NO_CURRENT_SUBMISSION_ROUTE"
    assert rows["uspto_georgia_patents_route"]["status"] == "OUTBOUND_SENT_INTAKE_RESPONSE_PENDING"
    assert rows["erdc_sovereign_cloud_cso"]["package_status"] == "ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW"
    assert rows["launchtn_3686_pitch_2026"]["package_status"] == "ARGUMENT_CONFORMANCE_BLOCKED_BEFORE_REVIEW"
    assert rows["darpa_falcon_dpa26bz04_dv016"]["package_status"] == "TECHNICAL_NO_GO_EVIDENCE_SPRINT_ONLY"

    for row in payload["assembly_rows"]:
        assert row["component_count"] == 9
        assert row["review_ready_component_count"] < row["component_count"]
        assert row["first_artifact"]["present"] is True
        assert row["first_artifact"]["bytes"] > 0
        assert len(row["first_artifact"]["sha256"]) == 64
        assert row["assembly_blockers"]
        assert row["legacy_intake_status"]
        assert row["state_source"]
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
    assert "Submission conformance status: `SUBMISSION_CONFORMANCE_BLOCKED`" in rendered
    assert "Active argument blocks: `3`" in rendered
    assert "Assembly represents every active conformance lane: `true`" in rendered
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
