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
    assert len(packet["draft"]["body_sha256"]) == 64
    assert len(packet["draft"]["outbound_request_identity_sha256"]) == 64
    assert packet["draft"]["identity_schema"] == (
        module.OUTBOUND_REQUEST_IDENTITY_SCHEMA
    )
    assert packet["draft"]["mailbox_draft_created"] is False
    assert packet["action"]["send_authorized"] is False
    assert packet["action"]["send_performed"] is False
    assert packet["action"]["action_time_ready"] is False
    assert set(packet["action"]["missing_readiness_controls"]) == {
        "fresh_duplicate_check_confirmed",
        "founder_review_confirmed",
        "gmail_draft_created",
        "gmail_draft_identity_match_confirmed",
    }
    assert packet["existing_component_route"]["send_now"] is False
    assert packet["deadline"]["seconds_remaining_at_generation"] == 50400
    assert packet["portal_evidence"]["private_hash_redacted"] is True
    assert "private_receipt_sha256" not in packet["portal_evidence"]
    assert packet["official_support"]["availability"] == "24/7/365"
    assert packet["official_support"]["private_caller_input_values_included"] is False
    assert packet["operator_policy"]["call_now"] is True
    assert packet["operator_policy"]["hard_stop_utc"] == "2026-07-22T14:30:00Z"


def test_action_time_readiness_requires_all_controls_but_never_authorizes():
    module = load_module()
    partial = build(module, founder_review_confirmed=True)
    ready = build(
        module,
        founder_review_confirmed=True,
        fresh_duplicate_check_confirmed=True,
        gmail_draft_created=True,
        gmail_draft_identity_match_confirmed=True,
    )

    assert partial["action"]["action_time_ready"] is False
    assert ready["action"]["action_time_ready"] is True
    assert ready["action"]["missing_readiness_controls"] == []
    assert ready["action"]["send_authorized"] is False
    assert ready["draft"]["mailbox_draft_created"] is True
    assert ready["action"]["send_decision"] == (
        "READY_FOR_ACTION_TIME_HUMAN_UNLOCK_NOT_AUTHORIZED"
    )


def test_outbound_request_identity_is_stable_and_mutation_sensitive():
    module = load_module()
    first = build(module)
    repeated = build(module)
    changed_config = json.loads(CONFIG.read_text(encoding="utf-8"))
    changed_config["subject"] += " [changed]"
    changed = build(module, config=changed_config)

    first_identity = first["draft"]["outbound_request_identity_sha256"]
    assert first_identity == repeated["draft"]["outbound_request_identity_sha256"]
    assert first_identity != changed["draft"]["outbound_request_identity_sha256"]
    assert first["draft"]["body_sha256"] == repeated["draft"]["body_sha256"]
    assert first["draft"]["body_sha256"] == changed["draft"]["body_sha256"]


def test_outbound_request_identity_binds_no_attachment_policy():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    body = "\n\n".join(config["body_paragraphs"])
    identity = module.build_outbound_request_identity(config, body)
    altered = dict(config)
    altered["attachment_policy"] = "ONE_FILE"
    altered_identity = module.build_outbound_request_identity(altered, body)

    assert identity["attachment_policy"] == "NONE"
    assert identity["outbound_request_identity_sha256"] != (
        altered_identity["outbound_request_identity_sha256"]
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


def test_official_call_route_is_privacy_safe_and_receipt_only():
    module = load_module()
    packet = build(module)
    support = packet["official_support"]
    policy = packet["operator_policy"]
    script = policy["call_script"].lower()

    assert support["source_url"].startswith("https://www.dla.mil/")
    assert support["private_caller_inputs_required"] == [
        "entity_name",
        "cage_or_ncage_code",
    ]
    assert "i have not submitted a jcp application" in script
    assert "i am not claiming jcp certification" in script
    assert "cage code:" not in script
    assert policy["outcomes"] == module.REQUIRED_OPERATOR_OUTCOMES
    assert policy["outcomes"]["portal_has_no_official_receipt_at_hard_stop"] == (
        "STOP_NO_VOLUME_V_OR_FINAL_SUBMISSION"
    )
    assert "JCP organization-creation receipt" in policy["prohibited_substitutes"]


def test_rejects_nonofficial_support_source_or_short_hard_stop_buffer():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["official_support"]["source_url"] = "https://example.com/jcp"

    with pytest.raises(module.JcpSupportEscalationError, match="SOURCE_INVALID"):
        build(module, config=config)

    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["operator_policy"]["hard_stop_utc"] = "2026-07-22T15:30:00Z"

    with pytest.raises(module.JcpSupportEscalationError, match="BUFFER_INVALID"):
        build(module, config=config)


def test_render_is_deterministic_and_records_human_unlock_phrase():
    module = load_module()
    first = build(module)
    second = build(module)

    assert first == second
    markdown = module.render_markdown(first)
    assert "SEND ONE JCP URGENT SUPPORT REQUEST" in markdown
    assert "Send performed:** `false`" in markdown
    assert "**Outbound request identity:**" in markdown
    assert "## Call Now" in markdown
    assert "24/7/365" in markdown
    assert "do not upload a substitute" in markdown.lower()
