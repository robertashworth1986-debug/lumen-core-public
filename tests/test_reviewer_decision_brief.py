from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_REVIEWER_DECISION_BRIEF.py"


def load_module():
    spec = importlib.util.spec_from_file_location("reviewer_decision_brief", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_reviewer_decision_brief_summarizes_full_control_stack():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "reviewer_decision_brief_v1"
    assert payload["status"] == "REVIEWER_DECISION_BRIEF_READY"
    assert payload["summary"]["lane_count"] == 19
    assert payload["summary"]["top_ready_lane_count"] == 10
    assert payload["summary"]["urgent_lane_count"] == 6
    assert payload["summary"]["partner_blocked_lane_count"] == 4
    assert payload["summary"]["authority_lane_count"] == 19
    assert payload["summary"]["docket_lane_count"] == 20
    assert payload["summary"]["concierge_lane_count"] == 20
    assert payload["summary"]["traction_lane_count"] == 20
    assert payload["summary"]["reviewer_gate_clear"] is True
    assert payload["summary"]["all_final_actions_blocked_without_human"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert len(payload["decision_brief_sha256"]) == 64


def test_decision_cards_keep_review_artifacts_and_final_action_blocks():
    module = load_module()
    payload = module.build_payload()
    cards = {card["lane_id"]: card for card in payload["decision_cards"]}

    assert set(payload["top_ready_lane_ids"]) == {
        "sam_registration_external_validation_watch",
        "evtit_blackdog_inkind",
        "lanl_vision_licensing_followup",
        "uspto_georgia_patents_route",
        "lvlup_first_check",
        "darpa_dice_full_submission",
        "fhwa_tsmo_data_initiative",
        "nasa_data_center_rfi",
        "dla_missionweave_sbir",
        "nsf_project_pitch",
    }
    assert set(payload["urgent_lane_ids"]) == {
        "sam_registration_external_validation_watch",
        "evtit_blackdog_inkind",
        "lanl_vision_licensing_followup",
        "uspto_georgia_patents_route",
        "darpa_dice_full_submission",
        "openai_api_continuity",
    }

    for card in payload["decision_cards"]:
        assert card["first_artifact"]
        assert card["reviewer_decision"]
        assert card["next_human_action"]
        assert card["required_authority"]
        assert card["claim_boundary"]
        assert card["can_send_external_without_human"] is False
        assert card["can_submit_without_human"] is False
        assert card["can_accept_terms_without_human"] is False
        assert len(card["decision_card_sha256"]) == 64

    assert cards["hhs_ai_power_user_pilot"]["decision_stance"] == "Do not pursue solo."
    assert cards["csosa_public_safety_analytics"]["decision_stance"] == "Do not pursue solo."
    assert cards["sam_registration_external_validation_watch"]["decision_stance"] == "Monitor validation; do not claim Active status until SAM confirms it."
    assert "lab follow-up" in cards["lanl_vision_licensing_followup"]["decision_stance"]
    assert "buyer-discovery" in cards["protecnium_its_infrastructure_signal"]["decision_stance"]
    assert "Firm PIN" in cards["dla_missionweave_sbir"]["required_authority"]
    assert "Counsel" in cards["patent_deadline_counsel"]["decision_stance"]


def test_rendered_decision_brief_is_public_safe_and_non_final():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Reviewer Decision Brief" in rendered
    assert "All final actions blocked without human: `true`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert "No final portal action" in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
