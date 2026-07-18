from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OUTREACH_FOLLOWUP_ACTION_QUEUE.py"
CONFIG = ROOT / "config" / "outreach_followup_policies_v1.json"
JSON_OUT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
)
MD_OUT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.md"
)


def load_module():
    spec = importlib.util.spec_from_file_location("outreach_followup_action_queue", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_followup_policy_config_is_complete_and_fail_closed():
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = payload["lane_policies"]

    assert payload["schema"] == "lumencore.outreach_followup_policies.v1"
    assert payload["version"] == 1
    assert len(rows) == 16
    assert len({row["lane_id"] for row in rows}) == 16
    assert payload["controls"] == {
        "action_time_human_review_required": True,
        "builder_can_send_email": False,
        "inbox_recheck_required_before_any_followup": True,
        "missing_lane_policy_fail_closed": True,
        "past_hold_does_not_authorize_send": True,
    }

    proactive = [row for row in rows if row["max_proactive_sends"]]
    assert len(proactive) == 1
    assert proactive[0]["lane_id"] == "lanl_vision_licensing_followup"
    assert proactive[0]["max_proactive_sends"] == 1
    assert proactive[0]["eligible_template_id"] == "SUBMISSION_RECEIPT_FOLLOWUP"
    assert proactive[0]["not_before_utc"] == "2026-07-23T14:00:00Z"


def test_current_queue_is_deterministic_and_never_sends():
    module = load_module()
    expected = module.build_payload(module.DEFAULT_AS_OF_UTC)
    actual = json.loads(JSON_OUT.read_text(encoding="utf-8"))

    module.validate_payload(actual)
    assert actual == expected
    assert actual["status"] == "NO_EXTERNAL_FOLLOWUP_DUE"
    assert actual["summary"] == {
        "action_state_counts": {
            "CLOSED_NO_ACTION": 2,
            "HELD_NO_SEND": 1,
            "HUMAN_ACCOUNT_ACTION_OPEN": 1,
            "HUMAN_PORTAL_ACTION_OPEN": 3,
            "MONITOR_INBOUND_ONLY": 8,
            "PRIVATE_RECONCILIATION_OPEN": 1,
        },
        "draft_rendered_count": 0,
        "due_for_mailbox_recheck_count": 0,
        "external_send_allowed_without_human": False,
        "held_no_send_count": 1,
        "lane_count": 16,
        "send_now_count": 0,
    }
    assert all(row["send_now"] is False for row in actual["actions"])
    assert all(row["draft_rendered"] is False for row in actual["actions"])
    assert len(actual["queue_sha256"]) == 64


def test_lanl_hold_expiration_requires_recheck_and_still_does_not_authorize_send():
    module = load_module()
    before = module.build_payload("2026-07-23T13:59:59Z")
    at_gate = module.build_payload("2026-07-23T14:00:00Z")

    before_rows = {row["lane_id"]: row for row in before["actions"]}
    due_rows = {row["lane_id"]: row for row in at_gate["actions"]}
    before_lanl = before_rows["lanl_vision_licensing_followup"]
    due_lanl = due_rows["lanl_vision_licensing_followup"]

    assert before_lanl["action_state"] == "HELD_NO_SEND"
    assert before_lanl["hold_seconds_remaining"] == 1
    assert before_lanl["send_now"] is False
    assert due_lanl["action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
    assert due_lanl["inbox_recheck_required"] is True
    assert due_lanl["eligible_template_id"] == "SUBMISSION_RECEIPT_FOLLOWUP"
    assert due_lanl["draft_rendered"] is False
    assert due_lanl["send_now"] is False
    assert at_gate["status"] == "FOLLOWUP_RECHECK_DUE_HUMAN_REVIEW"
    assert at_gate["summary"]["due_for_mailbox_recheck_count"] == 1
    assert at_gate["summary"]["send_now_count"] == 0


def test_modes_route_closed_inbound_portal_private_and_account_work_separately():
    module = load_module()
    rows = {
        row["lane_id"]: row
        for row in module.build_payload(module.DEFAULT_AS_OF_UTC)["actions"]
    }

    assert rows["fhwa_tsmo_qualified_partner_outreach"]["action_state"] == (
        "CLOSED_NO_ACTION"
    )
    assert rows["epri_open_power_ai_mou"]["action_state"] == (
        "MONITOR_INBOUND_ONLY"
    )
    assert rows["missionweave_dsip_proposal"]["action_state"] == (
        "HUMAN_PORTAL_ACTION_OPEN"
    )
    assert rows["openai_build_week_internal_handoff"]["action_state"] == (
        "PRIVATE_RECONCILIATION_OPEN"
    )
    assert rows["sam_public_credential_rotation"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )


def test_missing_or_drifted_lane_policy_fails_closed():
    module = load_module()
    reconciliation = module.read_json(module.EMAIL_RECONCILIATION)
    registry = module.read_json(module.RESPONSE_TEMPLATE_REGISTRY)
    policies = module.read_json(module.FOLLOWUP_POLICY_CONFIG)

    missing = copy.deepcopy(policies)
    missing["lane_policies"] = missing["lane_policies"][:-1]
    with pytest.raises(ValueError, match="coverage"):
        module.validate_sources(reconciliation, registry, missing)

    drifted = copy.deepcopy(reconciliation)
    drifted["lanes"][0]["follow_up_policy"]["mode"] = "CLOSED"
    with pytest.raises(ValueError, match="policy drift"):
        module.validate_sources(drifted, registry, policies)


def test_public_outputs_exclude_mailbox_and_secret_material():
    module = load_module()
    payload = module.build_payload(module.DEFAULT_AS_OF_UTC)
    rendered = json.dumps(payload, sort_keys=True) + "\n" + MD_OUT.read_text(
        encoding="utf-8"
    )
    lowered = rendered.lower()

    assert "hold expiration requires a fresh mailbox check" in lowered
    assert "past hold authorizes send" not in lowered
    for forbidden in (
        "@gmail.com",
        "message_id",
        "thread_id",
        "password:",
        "verification code:",
        "passcode:",
        "client_secret",
        "refresh_token",
        "api_key",
        "zoom.us",
    ):
        assert forbidden not in lowered
