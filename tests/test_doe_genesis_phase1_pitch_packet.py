from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_DOE_GENESIS_PHASE1_PITCH_PACKET.py"
AS_OF_UTC = "2026-07-29T19:30:00Z"


def load_module():
    spec = importlib.util.spec_from_file_location("doe_genesis_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_official_guide_identity_and_word_caps_are_enforced():
    module = load_module()
    guide = module.validate_pitch_guide()
    sections = module.build_pitch_sections()

    assert guide["sha256"] == module.EXPECTED_GUIDE_SHA256
    assert guide["requirements_verified"] is True
    assert guide["word_limits"] == {
        "summary_topic_mission_alignment": 100,
        "technical_promise": 200,
        "commercialization_potential": 200,
        "team_qualifications": 200,
    }
    assert len(sections) == 4
    assert all(section["within_limit"] for section in sections)
    assert all(
        section["word_count"] <= section["word_limit"] for section in sections
    )


def test_packet_is_source_bound_and_fail_closed():
    module = load_module()
    payload = module.build_packet(as_of_utc=AS_OF_UTC)

    assert payload["fit_decision"] == "CONDITIONAL_FIT_NOT_YET_SUBMISSION_READY"
    assert payload["submission_ready"] is False
    assert payload["send_now"] is False
    assert payload["external_action_count"] == 0
    assert payload["portal_submit_allowed_without_human"] is False
    assert payload["autonomous_certification_allowed"] is False
    assert payload["autonomous_upload_allowed"] is False
    assert payload["official_state"]["active_solicitation"] is True
    assert payload["official_state"]["application_portal_state"] == "COMING_SOON"
    assert payload["official_state"]["deadline_literal"] == (
        "September 10, 2026 at 2 PM ET"
    )
    assert len(payload["control_sha256"]) == 64


def test_packet_preserves_current_evidence_limits():
    module = load_module()
    payload = module.build_packet(as_of_utc=AS_OF_UTC)
    evidence = payload["current_evidence_snapshot"]

    assert evidence["registered_family_count"] == 140
    assert evidence["implementation_present_count"] == 35
    assert evidence["implementation_required_count"] == 105
    assert evidence["promotion_gate_pass_count"] == 0
    assert evidence["public_performance_claim_allowed"] is False
    assert evidence["prospective_protocol_status"] == (
        "FROZEN_AWAITING_FUTURE_OBSERVATIONS"
    )
    assert evidence["eligible_future_observation_count"] == 0
    assert len(evidence["evidence_receipts"]) == 8
    assert all(
        len(receipt["sha256"]) == 64
        for receipt in evidence["evidence_receipts"]
    )


def test_protocol_uses_named_baselines_and_marks_targets_as_unproven():
    module = load_module()
    payload = module.build_packet(as_of_utc=AS_OF_UTC)
    protocol = payload["proposed_phase_i_protocol"]

    assert protocol["phase_i_scope"] == (
        "SIMULATION_AND_FAULT_INJECTION_NO_LAB_DEPLOYMENT_CLAIM"
    )
    assert len(protocol["named_baselines"]) == 5
    assert any("Bluesky" in item for item in protocol["named_baselines"])
    assert any("HELAO" in item for item in protocol["named_baselines"])
    assert protocol["target_status"] == (
        "PROPOSED_MUST_BE_FROZEN_BEFORE_EVALUATION"
    )
    assert len(protocol["proposed_targets_not_results"]) == 8
    assert all(
        reference["relationship_claimed"] is False
        for reference in payload["reference_candidates"]
    )
    assert payload["red_team"]["reviewer_verdict"] == (
        "BORDERLINE_NOT_INVITE_READY_TODAY"
    )
    assert "autonomous laboratory operation" in payload["red_team"]["must_not_claim"]


def test_markdown_names_every_open_gate_and_refuses_false_claims():
    module = load_module()
    payload = module.build_packet(as_of_utc=AS_OF_UTC)
    rendered = module.render_markdown(payload)

    assert "CONDITIONAL_FIT_NOT_YET_SUBMISSION_READY" in rendered
    assert "Proposed Targets, Not Results" in rendered
    assert "not a claim that LumenCore already operates a laboratory" in rendered
    assert "no relationship claimed" in rendered
    assert "FOUNDER_CONFIRMATION_REQUIRED" in rendered
    assert "DIRECT_PORTAL_EVIDENCE_REQUIRED" in rendered
    assert "HUMAN_REVIEW_REQUIRED" in rendered
    assert "TRUTHFUL_DISCLOSURE_REQUIRED" in rendered
    assert "Generative-AI use must be truthfully disclosed" in rendered
    assert "Independent Red-Team Decision" in rendered
    assert "BORDERLINE_NOT_INVITE_READY_TODAY" in rendered
    assert "post-hoc log inspection without pre-dispatch command mediation" in rendered
    assert "External action taken by this builder: `0`." in rendered
