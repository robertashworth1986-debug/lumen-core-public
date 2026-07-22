from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MISSIONWEAVE_JCP_SUPPORT_ESCALATION.py"
CONFIG = ROOT / "config" / "missionweave_jcp_support_escalation_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "build_missionweave_jcp_support_escalation", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def portal_receipt():
    return {
        "schema": "lumencore.missionweave_jcp_portal_organization_receipt.v1",
        "status": "ORGANIZATION_CREATED_APPLICATION_NOT_SUBMITTED",
        "topic": "DLA26BZ03-NV011",
        "events": {
            "organization_created_successfully": True,
            "jcp_application_submitted": False,
            "official_application_submission_receipt_available": False,
        },
        "portal_observations": {"sam_status": "N/A"},
    }


def queue():
    return {
        "actions": [
            {
                "action_state": "FOLLOWUP_LIMIT_REACHED_NO_SEND",
                "lane_id": "missionweave_dsip_proposal",
                "max_proactive_sends": 1,
                "recorded_proactive_send_count": 1,
                "send_now": False,
            }
        ]
    }


def build(module, **overrides):
    args = {
        "config": json.loads(CONFIG.read_text(encoding="utf-8")),
        "queue": queue(),
        "portal_receipt": portal_receipt(),
        "portal_receipt_sha256": "A" * 64,
        "generated_utc": "2026-07-22T02:00:00Z",
    }
    args.update(overrides)
    return module.build_packet(**args)


def test_builds_bounded_support_draft_without_authorizing_send():
    module = load_module()
    packet = build(module)

    assert packet["schema"] == module.PACKET_SCHEMA
    assert packet["route_id"] == "missionweave_jcp_portal_support"
    assert packet["draft"]["recipient"] == "jcp-admin@dla.mil"
    assert packet["draft"]["attachment_policy"] == "NONE"
    assert packet["action"]["send_authorized"] is False
    assert packet["action"]["send_performed"] is False
    assert packet["action"]["action_time_ready"] is False
    assert packet["existing_component_route"]["send_now"] is False
    assert packet["deadline"]["seconds_remaining_at_generation"] == 50400
    assert packet["portal_evidence"]["private_hash_redacted"] is True
    assert "private_receipt_sha256" not in packet["portal_evidence"]


def test_action_time_readiness_requires_both_human_controls_but_never_authorizes():
    module = load_module()
    partial = build(module, founder_review_confirmed=True)
    ready = build(
        module,
        founder_review_confirmed=True,
        fresh_duplicate_check_confirmed=True,
    )

    assert partial["action"]["action_time_ready"] is False
    assert ready["action"]["action_time_ready"] is True
    assert ready["action"]["send_authorized"] is False
    assert ready["action"]["send_decision"] == (
        "READY_FOR_ACTION_TIME_HUMAN_UNLOCK_NOT_AUTHORIZED"
    )


def test_rejects_unsubmitted_portal_facts_that_are_not_exact():
    module = load_module()
    receipt = portal_receipt()
    receipt["events"]["jcp_application_submitted"] = True

    with pytest.raises(module.JcpSupportEscalationError, match="PORTAL_EVENT_INVALID"):
        build(module, portal_receipt=receipt)


def test_rejects_invalid_private_receipt_hash_without_exposing_it():
    module = load_module()

    with pytest.raises(module.JcpSupportEscalationError, match="SHA256_INVALID"):
        build(module, portal_receipt_sha256="not-a-hash")


def test_rejects_reuse_when_component_followup_lane_is_not_held():
    module = load_module()
    altered = queue()
    altered["actions"][0]["action_state"] = "HUMAN_ACTION_DUE"

    with pytest.raises(module.JcpSupportEscalationError, match="COMPONENT_LANE_NOT_HELD"):
        build(module, queue=altered)


def test_draft_excludes_sensitive_identifiers_and_claims():
    module = load_module()
    packet = build(module)
    body = packet["draft"]["body"].lower()

    for forbidden in (
        "14tm8",
        "2613 paddle",
        "uei:",
        "password",
        "one-time code",
        "certified jcp",
    ):
        assert forbidden not in body
    assert "i have not submitted a jcp application" in body
    assert "i am not claiming jcp certification" in body


def test_render_is_deterministic_and_records_human_unlock_phrase():
    module = load_module()
    first = build(module)
    second = build(module)

    assert first == second
    markdown = module.render_markdown(first)
    assert "SEND ONE JCP URGENT SUPPORT REQUEST" in markdown
    assert "Send performed:** `false`" in markdown
