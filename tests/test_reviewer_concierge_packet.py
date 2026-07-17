from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_CONCIERGE_PACKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_concierge_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_concierge_packet_indexes_all_live_lanes_with_complete_artifacts():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "reviewer_concierge_packet_v1"
    assert payload["status"] == "REVIEWER_CONCIERGE_READY_HUMAN_ACTION_REQUIRED"
    assert payload["summary"]["lane_count"] == 20
    assert payload["summary"]["top_priority_count"] == 11
    assert payload["summary"]["top_priority_artifacts_complete"] is True
    assert payload["summary"]["missing_artifact_count"] == 0
    assert payload["summary"]["reviewer_gate_clear"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert len(payload["concierge_sha256"]) == 64


def test_concierge_cards_keep_decision_questions_hashes_and_human_gates():
    module = load_module()
    payload = module.build_payload()
    cards = {card["lane_id"]: card for card in payload["concierge_cards"]}

    expected = {
        "sam_registration_external_validation_watch",
        "lanl_vision_licensing_followup",
        "uspto_georgia_patents_route",
        "protecnium_its_infrastructure_signal",
        "evtit_blackdog_inkind",
        "lvlup_first_check",
        "darpa_dice_full_submission",
        "fhwa_tsmo_data_initiative",
        "nasa_data_center_rfi",
        "dla_missionweave_sbir",
        "nsf_project_pitch",
        "patent_deadline_counsel",
        "openai_build_week_prooflock",
    }
    assert expected.issubset(cards)
    assert cards["dla_missionweave_sbir"]["status"] == "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    assert cards["lvlup_first_check"]["status"] == "WRITTEN_NO_SPONSOR_SPEND_INDEPENDENT_REVIEW_CONFIRMED"
    assert cards["evtit_blackdog_inkind"]["status"] == "OUTBOUND_FOLLOWUPS_SENT_NO_INBOUND_REPLY"
    assert "2026-07-22T16:00:00Z" in cards["dla_missionweave_sbir"]["deadline_or_gate"]
    assert cards["openai_build_week_prooflock"]["status"] == (
        "PROJECT_CORE_VERIFIED_EXTERNAL_SUBMISSION_FIELDS_OPEN"
    )
    assert cards["openai_build_week_prooflock"]["artifact_count"] == 5

    for card in payload["concierge_cards"]:
        assert card["artifact_count"] > 0
        assert card["artifact_missing_count"] == 0
        assert card["artifact_present_count"] == card["artifact_count"]
        assert card["decision_question"]
        assert card["best_first_read"]
        assert card["legacy_intake_status"]
        assert card["state_source"]
        assert "Human" in card["human_gate"]
        assert len(card["concierge_card_sha256"]) == 64
        for artifact in card["artifacts"]:
            assert artifact["present"] is True
            assert len(artifact["sha256"]) == 64


def test_rendered_concierge_markdown_is_public_safe_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Reviewer Concierge Packet Index" in rendered
    assert "External send without human: `false`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "A clear concierge packet means the materials are organized for review." in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
