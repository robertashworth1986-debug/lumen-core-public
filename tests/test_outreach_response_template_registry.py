from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY.py"
CONFIG = ROOT / "config" / "outreach_response_templates_v1.json"
OUT_JSON = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)
OUT_MD = OUT_JSON.with_suffix(".md")


def load_module():
    spec = importlib.util.spec_from_file_location("outreach_response_registry", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def common_facts() -> dict[str, str]:
    return {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "source_message_id": "synthetic-message-id",
        "source_subject": "Validation inquiry",
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
    }


def test_registry_validates_and_covers_high_value_response_states():
    module = load_module()
    registry = module.validate_registry(module.read_registry())
    ids = {row["template_id"] for row in registry["templates"]}

    assert registry["schema"] == module.SCHEMA
    assert len(ids) == 11
    assert {
        "NO_DUPLICATE_MONITOR",
        "DEADLINE_CLARIFICATION",
        "PORTAL_SUPPORT_DEADLINE_RESCUE",
        "REQUESTED_INFORMATION_REPLY",
        "SUBMISSION_RECEIPT_FOLLOWUP",
        "COMPONENT_INSTRUCTION_ESCALATION",
        "BOUNDED_REVIEW_FOLLOWUP",
        "VALIDATION_PILOT_REQUEST",
        "DECLINE_CLOSEOUT",
        "MOU_ONBOARDING_REPLY",
        "MEETING_REBOOK_REQUEST",
    } == ids


def test_duplicate_send_and_monitor_states_fail_closed_without_rendering_message():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "problem_lane": "grid forecast replay",
            "validation_scope": "one frozen public dataset and one incumbent baseline",
            "protocol_summary": "predeclare splits, metrics, exclusions, and stop rules",
            "requested_next_step": "name one technical reviewer",
        }
    )

    duplicate = module.render_response(
        "VALIDATION_PILOT_REQUEST",
        facts,
        already_sent=True,
        inbound_requires_response=False,
    )
    monitor = module.render_response("NO_DUPLICATE_MONITOR", {})

    assert duplicate["status"] == "MONITOR_NO_DUPLICATE"
    assert duplicate["duplicate_send_blocked"] is True
    assert duplicate["subject"] is None
    assert duplicate["body"] is None
    assert monitor["status"] == "MONITOR_NO_SEND"
    assert monitor["send_performed"] is False


def test_missing_facts_invalid_email_and_unrequested_attachment_block_render():
    module = load_module()
    missing = module.render_response("DEADLINE_CLARIFICATION", {})
    assert missing["status"] == "BLOCKED_MISSING_FACTS"
    assert "recipient_email" in missing["missing_fields"]

    facts = common_facts()
    facts.update(
        {
            "opportunity_name": "Synthetic Notice",
            "eligibility_question": "a sole proprietor may apply",
            "recipient_email": "not-an-email",
        }
    )
    invalid = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert invalid["status"] == "BLOCKED_INVALID_EMAIL"
    assert invalid["invalid_email_fields"] == ["recipient_email"]

    facts["recipient_email"] = "reviewer@example.org"
    facts["attachment_files"] = ["packet.pdf"]
    attachment = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert attachment["status"] == "BLOCKED_ATTACHMENT_NOT_AUTHORIZED"
    assert attachment["attachment_count"] == 1


def test_deadline_urgency_is_timezone_aware_and_past_deadlines_block():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "opportunity_name": "Synthetic Notice",
            "eligibility_question": "the current entity type is eligible",
            "deadline_iso": "2026-07-19T11:00:00-05:00",
        }
    )
    critical = module.render_response(
        "DEADLINE_CLARIFICATION",
        facts,
        current_utc="2026-07-18T17:00:00+00:00",
    )
    assert critical["deadline"]["urgency"] == "CRITICAL_UNDER_24_HOURS"
    assert critical["deadline"]["hours_remaining"] == 23.0

    past = module.render_response(
        "DEADLINE_CLARIFICATION",
        facts,
        current_utc="2026-07-19T17:00:01+00:00",
    )
    assert past["status"] == "BLOCKED_DEADLINE_PASSED"


def test_mou_and_validation_templates_preserve_private_and_claim_boundaries():
    module = load_module()
    mou = common_facts()
    mou.update(
        {
            "legal_party_name": "Synthetic Legal Party",
            "business_address": "1 Test Way, Test City, TN 00000",
            "signatory_name": "Synthetic Signatory",
            "signatory_email": "signatory@example.org",
            "signatory_title": "Authorized Signatory",
        }
    )
    rendered_mou = module.render_response("MOU_ONBOARDING_REPLY", mou)
    assert rendered_mou["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered_mou["private_render"] is True
    assert rendered_mou["public_safe"] is False
    assert rendered_mou["send_allowed_by_builder"] is False
    assert "legal_party_name" in rendered_mou["sensitive_field_names"]

    validation = common_facts()
    validation.update(
        {
            "problem_lane": "grid forecast replay",
            "validation_scope": "one frozen public dataset and one incumbent baseline",
            "protocol_summary": "predeclare splits, metrics, exclusions, and stop rules",
            "requested_next_step": "name one technical reviewer",
        }
    )
    rendered_validation = module.render_response("VALIDATION_PILOT_REQUEST", validation)
    assert "requesting a bounded review, not an endorsement" in rendered_validation[
        "body"
    ]
    assert "has not been independently reproduced" in rendered_validation["body"]
    assert "retain negative results" in rendered_validation["body"]
    assert rendered_validation["send_performed"] is False

    followup = common_facts()
    followup.update(
        {
            "sent_date_local": "July 16, 2026",
            "package_name": "a bounded technical package",
            "review_scope": "a short Stage 0 diligence and evaluation-fit discussion",
            "requested_next_step": "a 20-minute technical fit check",
        }
    )
    rendered_followup = module.render_response("BOUNDED_REVIEW_FOLLOWUP", followup)
    assert rendered_followup["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered_followup["private_render"] is True
    assert rendered_followup["attachment_policy"] == "NONE"
    assert "following up once" in rendered_followup["body"]
    assert "does not assert receipt, endorsement, independent validation" in (
        rendered_followup["body"]
    )
    assert "no response is required" in rendered_followup["body"]
    assert "will not send another follow-up" in rendered_followup["body"]
    assert rendered_followup["send_allowed_by_builder"] is False

    component = common_facts()
    component.update(
        {
            "topic_or_notice": "Synthetic Topic",
            "deadline_local": "July 22, 2026 at noon Eastern",
            "original_sent_local": "July 17, 2026",
            "support_redirect_summary": (
                "Portal support directed the question to the component POC."
            ),
            "exact_instruction_question": (
                "whether the official portal submission receipt is required"
            ),
            "requested_reply_by_local": "July 21, 2026 at noon Eastern",
        }
    )
    rendered_component = module.render_response(
        "COMPONENT_INSTRUCTION_ESCALATION", component
    )
    assert rendered_component["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered_component["attachment_policy"] == "NONE"
    assert "following up once" in rendered_component["body"]
    assert "prerequisites-in-progress" in rendered_component["body"]
    assert "will not duplicate the proposal package" in rendered_component["body"]
    assert rendered_component["send_allowed_by_builder"] is False


def test_written_public_registry_is_current_and_contains_no_contact_values():
    module = load_module()
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    markdown = OUT_MD.read_text(encoding="utf-8")
    combined = OUT_JSON.read_text(encoding="utf-8") + markdown

    assert payload["schema"] == module.PUBLIC_SCHEMA
    assert payload["template_count"] == 11
    assert payload["controls"]["builder_can_send_email"] is False
    assert payload["controls"]["duplicate_send_fail_closed"] is True
    assert "Duplicate-send gate: `FAIL_CLOSED`" in markdown
    assert "No message is rendered" in markdown
    assert "receipt check only, not a duplicate submission" in markdown
    assert not re.search(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", combined)
    assert not module.UUID_RE.search(combined)
    assert "robertashworth4444" not in combined.lower()
    assert "615-438-2502" not in combined


def test_source_config_hash_and_builder_payload_agree():
    module = load_module()
    registry = module.validate_registry(module.read_registry(CONFIG))
    payload = module.build_public_payload(
        registry, generated_utc="2026-07-18T00:00:00+00:00"
    )

    assert payload["source_config_sha256"] == module.sha256_bytes(CONFIG.read_bytes())
    assert payload["send_policy_counts"] == {
        "HUMAN_ACTION_DUE": 5,
        "MONITOR_NO_SEND": 1,
        "REPLY_AFTER_FACT_REVIEW": 5,
    }
