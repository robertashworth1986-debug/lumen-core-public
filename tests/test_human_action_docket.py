from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HUMAN_ACTION_DOCKET.py"


def load_module():
    spec = importlib.util.spec_from_file_location("human_action_docket", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_human_action_docket_builds_date_aware_lane_board():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "human_action_docket_v1"
    assert payload["current_date"] == "2026-07-09"
    assert payload["status"] == "HUMAN_ACTION_DOCKET_READY"
    assert payload["summary"]["lane_count"] == 20
    assert payload["summary"]["traction_lane_count"] == 20
    assert payload["summary"]["concierge_lane_count"] == 20
    assert payload["summary"]["all_artifacts_present"] is True
    assert payload["summary"]["reviewer_gate_clear"] is True
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert len(payload["docket_sha256"]) == 64


def test_immediate_and_urgent_lanes_are_explicit_and_human_gated():
    module = load_module()
    payload = module.build_payload()
    items = {item["lane_id"]: item for item in payload["docket_items"]}

    expected_urgent = {
        "sam_registration_external_validation_watch",
        "evtit_blackdog_inkind",
        "lanl_vision_licensing_followup",
        "uspto_georgia_patents_route",
        "darpa_dice_full_submission",
        "openai_api_continuity",
    }
    assert set(payload["summary"]["immediate_or_urgent_lane_ids"]) == expected_urgent
    assert payload["summary"]["immediate_or_urgent_count"] == len(expected_urgent)

    assert items["sam_registration_external_validation_watch"]["action_due"] == "2026-07-13"
    assert items["evtit_blackdog_inkind"]["action_due"] == "2026-07-09"
    assert items["lanl_vision_licensing_followup"]["action_due"] == "2026-07-13"
    assert items["uspto_georgia_patents_route"]["action_due"] == "2026-07-10"
    assert items["darpa_dice_full_submission"]["action_due"] == "2026-07-12"
    assert items["openai_api_continuity"]["action_due"] == "2026-07-10"
    assert items["patent_deadline_counsel"]["action_due"] == "2026-07-25"
    assert items["openai_build_week_prooflock"]["action_due"] == "2026-07-21"
    assert items["openai_build_week_prooflock"]["action_type"] == "developer_challenge_build"
    assert items["protecnium_its_infrastructure_signal"]["action_type"] == "customer_discovery_watch"
    assert items["hhs_ai_power_user_pilot"]["urgency"] == "PARKED_UNLESS_PARTNER"
    assert items["csosa_public_safety_analytics"]["urgency"] == "PARKED_UNLESS_PARTNER"

    for item in payload["docket_items"]:
        assert item["first_artifact"]
        assert item["artifact_missing_count"] == 0
        assert "Human" in item["human_gate"]
        assert item["no_final_action_rule"] == module.NO_FINAL_ACTION
        assert len(item["docket_item_sha256"]) == 64


def test_rendered_docket_is_public_safe_and_blocks_final_action():
    module = load_module()
    payload = module.build_payload()
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "Human Action Docket" in rendered
    assert "External send without human: `false`" in rendered
    assert "Final submission without human: `false`" in rendered
    assert "Live trading allowed: `false`" in rendered
    assert module.NO_FINAL_ACTION in rendered
    assert "zoom.us" not in lowered
    assert "meeting id" not in lowered
    assert "password" not in lowered
    assert "one tap mobile" not in lowered
    assert "private key" not in lowered
    assert "refresh_token" not in lowered
    assert "client_secret" not in lowered
    assert "api_key" not in lowered
