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
    summary = payload["summary"]
    expected_status = (
        "REVIEWER_DECISION_BRIEF_READY"
        if summary["reviewer_gate_clear"] and summary["all_final_actions_blocked_without_human"]
        else "REVIEWER_DECISION_BRIEF_BLOCKED"
    )
    assert payload["status"] == expected_status
    assert summary["lane_count"] == len(payload["decision_cards"])
    assert summary["top_ready_lane_count"] == len(payload["top_ready_lane_ids"])
    assert summary["urgent_lane_count"] == len(payload["urgent_lane_ids"])
    assert summary["authority_lane_count"] >= summary["lane_count"]
    assert summary["docket_lane_count"] >= summary["lane_count"]
    assert summary["concierge_lane_count"] >= 0
    assert summary["traction_lane_count"] >= 0
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

    expected_top_ready = {
        card["lane_id"]
        for card in payload["decision_cards"]
        if int(card["priority"]) <= 7 and int(card["artifact_missing_count"]) == 0
    }
    expected_urgent = {
        card["lane_id"]
        for card in payload["decision_cards"]
        if card["urgency"] in {"IMMEDIATE_24H", "URGENT_5D"}
    }
    assert set(payload["top_ready_lane_ids"]) == expected_top_ready
    assert set(payload["urgent_lane_ids"]) == expected_urgent

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
    assert "human" in cards["lanl_vision_licensing_followup"]["decision_stance"].casefold()
    assert cards["protecnium_its_infrastructure_signal"]["reviewer_decision"]
    assert cards["dla_missionweave_sbir"]["required_authority"]
    assert cards["patent_deadline_counsel"]["next_human_action"]
    assert cards["erdc_sovereign_cloud_cso"]["required_authority"]


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
