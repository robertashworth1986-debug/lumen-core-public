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
    payload = module.build_payload("2026-07-27")

    assert payload["schema"] == "human_action_docket_v1"
    assert payload["current_date"] == "2026-07-27"
    assert payload["status"] == "HUMAN_ACTION_DOCKET_READY"
    assert payload["summary"]["lane_count"] == 26
    assert payload["summary"]["traction_lane_count"] == 20
    assert payload["summary"]["concierge_lane_count"] == 20
    assert payload["summary"]["all_artifacts_present"] is True
    assert payload["summary"]["reviewer_packaging_gate_clear"] is True
    assert payload["summary"]["submission_argument_gate_clear"] is False
    assert payload["summary"]["unsafe_secret_count"] == 0
    assert payload["summary"]["unsafe_claim_count"] == 0
    assert payload["summary"]["external_send_allowed_without_human"] is False
    assert payload["summary"]["final_submission_allowed_without_human"] is False
    assert payload["summary"]["live_trading_allowed"] is False
    assert set(payload["source_ledgers"]) == {
        "concierge",
        "traction",
        "reviewer_gate",
        "email_reconciliation",
        "followup_queue",
        "official_events",
        "external_engagement",
    }
    for source in payload["source_ledgers"].values():
        assert source["path"]
        assert len(source["sha256"]) == 64
    assert len(payload["docket_sha256"]) == 64


def test_immediate_and_urgent_lanes_are_explicit_and_human_gated():
    module = load_module()
    payload = module.build_payload("2026-07-27")
    items = {item["lane_id"]: item for item in payload["docket_items"]}

    expected_urgent = {
        "nashville_ec_takeoff_fall_2026",
        "login_gov_new_device_signin",
        "sam_public_credential_rotation",
    }
    assert set(payload["summary"]["immediate_or_urgent_lane_ids"]) == expected_urgent
    assert payload["summary"]["immediate_or_urgent_count"] == len(expected_urgent)

    assert items["nashville_ec_takeoff_fall_2026"]["action_due"] == "2026-07-31"
    assert items["argos_emi_teaming_inquiry"]["action_due"] is None
    assert items["argos_emi_teaming_inquiry"]["urgency"] == (
        "ROLLING_OR_EVENT_GATED"
    )
    assert items["argos_emi_teaming_inquiry"]["action_type"] == (
        "inbound_only_monitor"
    )
    assert items["argos_emi_teaming_inquiry"]["send_now"] is False
    assert items["argos_emi_teaming_inquiry"]["current_draft_count"] == 0
    assert items["argos_emi_teaming_inquiry"]["matching_sent_count"] == 1
    assert items["argos_emi_teaming_inquiry"]["selected_template_id"] == (
        "NO_DUPLICATE_MONITOR"
    )
    assert items["nashville_ec_takeoff_fall_2026"]["urgency"] == "URGENT_5D"
    assert items["login_gov_new_device_signin"]["urgency"] == "IMMEDIATE_24H"
    assert items["sam_public_credential_rotation"]["action_due"] == "2026-07-16"
    assert items["sam_public_credential_rotation"]["urgency"] == "OVERDUE_ACTION"
    assert items["dla_missionweave_sbir"]["action_type"] == "read_only_portal_verification"
    assert items["dla_amps_application_access"]["action_type"] == "account_role_verification"
    assert items["epri_open_power_ai_mou_completed"]["action_type"] == "private_agreement_obligation_review"
    assert items["lanl_vision_licensing_followup"]["action_type"] == "inbound_only_monitor"
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
    payload = module.build_payload("2026-07-27")
    rendered = module.render_markdown(payload)
    lowered = rendered.lower()

    assert "# Human Action Docket - 2026-07-27" in rendered
    assert "SAM.gov credential rotation" in rendered
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
