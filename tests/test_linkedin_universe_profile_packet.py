from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_LINKEDIN_UNIVERSE_PROFILE_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("linkedin_universe_profile_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_linkedin_universe_packet_is_ready_and_profile_bounded():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "linkedin_universe_profile_packet_v1"
    assert payload["status"] == "LINKEDIN_UNIVERSE_PROFILE_READY_HUMAN_POST_REQUIRED"
    assert payload["profile_url"].startswith("https://www.linkedin.com/in/")
    assert "LumenCore" in payload["profile_copy"]["recommended_headline"]
    assert "Proof-to-Pilot" in payload["profile_copy"]["recommended_headline"]
    assert payload["summary"]["headline_character_count"] <= 220
    assert payload["summary"]["about_character_count"] <= 2600
    assert payload["summary"]["reviewer_packaging_gate_clear"] is True
    assert payload["summary"]["submission_argument_gate_clear"] is False
    assert payload["summary"]["all_final_actions_blocked_without_human"] is True
    assert payload["summary"]["linkedin_public_action_requires_human"] is True


def test_public_copy_avoids_risky_claims_and_secrets():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert payload["summary"]["public_copy_sensitive_count"] == 0
    assert payload["summary"]["public_copy_unsafe_count"] == 0
    for phrase in [
        "field validated",
        "realized savings",
        "guaranteed award",
        "guaranteed returns",
        "risk-free",
        "autonomous trading system ready",
        "freedom to operate",
        "patented",
    ]:
        assert phrase not in lowered
    for marker in [
        "zoom.us",
        "meeting id",
        "password",
        "one tap mobile",
        "private key",
        "refresh_token",
        "client_secret",
        "api_key",
    ]:
        assert marker not in lowered


def test_linkedin_packet_keeps_public_actions_human_gated():
    module = load_module()
    payload = module.build_payload()
    gate = payload["human_gate"]

    assert gate["profile_edit_allowed_without_human"] is False
    assert gate["post_allowed_without_human"] is False
    assert gate["message_allowed_without_human"] is False
    assert gate["company_page_change_allowed_without_human"] is False
    assert "Human approval" in gate["rule"]
    assert "human review" in " ".join(payload["profile_copy"]["manual_update_sequence"]).lower()


def test_linkedin_packet_maps_to_front_door_evidence():
    module = load_module()
    payload = module.build_payload()
    evidence_by_name = {Path(row["path"]).name: row for row in payload["evidence_status"]}

    for name in [
        "REVIEWER_DECISION_BRIEF_2026-07-09.md",
        "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "HUMAN_ACTION_DOCKET_2026-07-09.md",
        "DATA_ROOM_MANIFEST_2026-07-09.md",
        "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
    ]:
        assert evidence_by_name[name]["present"] is True
        assert evidence_by_name[name]["bytes"] > 0
        assert len(evidence_by_name[name]["sha256"]) == 64

    assert payload["proof_stack_alignment"]["top_decision_cards"]
    assert payload["proof_stack_alignment"]["urgent_docket_items"]
