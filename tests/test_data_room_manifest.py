from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DATA_ROOM_MANIFEST.py"


def load_module():
    spec = importlib.util.spec_from_file_location("data_room_manifest", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_data_room_manifest_indexes_markdown_controls_and_mirrors():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "data_room_manifest_v1"
    assert payload["status"] == "DATA_ROOM_MANIFEST_READY"
    assert payload["summary"]["manifested_markdown_count"] >= 42
    assert payload["summary"]["control_artifact_count"] == 46
    assert payload["summary"]["missing_control_artifact_count"] == 0
    assert payload["summary"]["reviewer_gate_clear"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["decision_status"] == "REVIEWER_DECISION_BRIEF_READY"
    assert payload["summary"]["authority_status"] == "SUBMISSION_AUTHORITY_MATRIX_READY"
    assert payload["summary"]["all_final_actions_blocked_without_human"] is True
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert payload["summary"]["e_drive_target_count"] == 3
    assert len(payload["manifest_seed_sha256"]) == 64
    assert len(payload["data_room_manifest_sha256"]) == 64


def test_manifest_artifacts_have_hashes_and_front_door_order():
    module = load_module()
    payload = module.build_payload()
    markdown_by_name = {row["name"]: row for row in payload["markdown_artifacts"]}

    expected_front_doors = {
        "REVIEWER_DECISION_BRIEF_2026-07-09.md",
        "CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
        "VENTURE_STUDIO_TERMS_GUARDRAIL_PACKET_2026-07-09.md",
        "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        "LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
        "IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
        "AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
        "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
        "AGENCY_ACCOUNT_ACTIVATION_DOCKET_2026-07-09.md",
        "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
        "IMMEDIATE_FEDERAL_AI_OPPORTUNITY_RADAR_2026-07-09.md",
        "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md",
        "SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md",
        "REVIEWER_APPROVAL_CROSSWALK_2026-07-09.md",
        "INSTITUTIONAL_TRUST_GATE_2026-07-09.md",
        "KEY_GOVERNANCE_FIREWALL_2026-07-09.md",
        "EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET_2026-07-09.md",
        "EVTIT_TRACTION_FOLLOWUP_PACKET_2026-07-09.md",
        "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "HUMAN_ACTION_DOCKET_2026-07-09.md",
        "REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
        "TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
    }
    assert expected_front_doors.issubset(markdown_by_name)
    assert payload["front_door_order"][0].endswith("REVIEWER_DECISION_BRIEF_2026-07-09.md")

    for row in payload["markdown_artifacts"]:
        assert row["classification"] == "public_safe_markdown_review_required"
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64

    for row in payload["control_artifacts"]:
        assert row["present"] is True
        assert row["classification"] == "machine_readable_proof_receipt"
        assert row["bytes"] > 0
        assert len(row["sha256"]) == 64


def test_rendered_manifest_is_public_safe_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Data Room Manifest" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "human_approval_required_before_external_send: `true`" in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
