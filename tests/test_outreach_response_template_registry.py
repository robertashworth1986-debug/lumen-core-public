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
        "source_thread_id": "synthetic-thread-id",
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
    by_id = {row["template_id"]: row for row in registry["templates"]}
    assert by_id["PORTAL_SUPPORT_DEADLINE_RESCUE"]["deadline_policy"] == "REQUIRED"
    assert by_id["COMPONENT_INSTRUCTION_ESCALATION"]["deadline_policy"] == "REQUIRED"
    assert all("deadline_policy" in row for row in registry["templates"])
    for row in registry["templates"]:
        if row["send_policy"] == "MONITOR_NO_SEND":
            continue
        assert {"recipient_email", "source_message_id", "source_thread_id"} <= set(
            row["routing_fields"]
        )
        assert set(row["routing_fields"]) <= set(row["sensitive_fields"])


def test_registry_rejects_missing_or_inconsistent_deadline_policy():
    module = load_module()
    missing = module.read_registry()
    missing["templates"][1].pop("deadline_policy")
    try:
        module.validate_registry(missing)
    except module.OutreachRegistryError as exc:
        assert str(exc) == "DEADLINE_POLICY_INVALID:DEADLINE_CLARIFICATION"
    else:
        raise AssertionError("missing deadline policy must fail closed")

    inconsistent = module.read_registry()
    rescue = next(
        row
        for row in inconsistent["templates"]
        if row["template_id"] == "PORTAL_SUPPORT_DEADLINE_RESCUE"
    )
    rescue["required_fields"].remove("deadline_iso")
    try:
        module.validate_registry(inconsistent)
    except module.OutreachRegistryError as exc:
        assert str(exc) == (
            "REQUIRED_DEADLINE_FIELD_UNDECLARED:PORTAL_SUPPORT_DEADLINE_RESCUE"
        )
    else:
        raise AssertionError("required deadline policy must declare deadline_iso")


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


def test_thread_bound_response_identity_is_deterministic_and_blocks_replay():
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

    first = module.render_response("VALIDATION_PILOT_REQUEST", facts)
    repeated = module.render_response("VALIDATION_PILOT_REQUEST", dict(facts))
    changed_thread = dict(facts, source_thread_id="synthetic-thread-id-2")
    changed = module.render_response("VALIDATION_PILOT_REQUEST", changed_thread)
    replay = module.render_response(
        "VALIDATION_PILOT_REQUEST",
        facts,
        prior_response_identity_sha256s=[first["response_identity_sha256"]],
    )
    malformed = module.render_response(
        "VALIDATION_PILOT_REQUEST",
        facts,
        prior_response_identity_sha256s=["not-a-sha256"],
    )

    assert first["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert first["thread_binding_complete"] is True
    assert re.fullmatch(r"[0-9A-F]{64}", first["response_identity_sha256"])
    assert repeated["response_identity_sha256"] == first["response_identity_sha256"]
    assert changed["response_identity_sha256"] != first["response_identity_sha256"]
    assert replay["status"] == "MONITOR_NO_DUPLICATE_CONTENT"
    assert replay["duplicate_send_blocked"] is True
    assert replay["duplicate_match_basis"] == "RESPONSE_IDENTITY_SHA256"
    assert replay["response_identity_sha256"] == first["response_identity_sha256"]
    assert replay["subject"] is None
    assert replay["body"] is None
    assert malformed["status"] == "BLOCKED_INVALID_PRIOR_RESPONSE_IDENTITY"
    assert malformed["response_identity_sha256"] is None


def test_missing_facts_invalid_email_and_unrequested_attachment_block_render():
    module = load_module()
    missing = module.render_response("DEADLINE_CLARIFICATION", {})
    assert missing["status"] == "BLOCKED_MISSING_FACTS"
    assert "recipient_email" in missing["missing_fields"]
    assert "source_thread_id" in missing["missing_fields"]

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
    facts["source_thread_id"] = "invalid thread id"
    invalid_routing = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert invalid_routing["status"] == "BLOCKED_INVALID_ROUTING_IDENTIFIER"
    assert invalid_routing["invalid_routing_identifier_fields"] == [
        "source_thread_id"
    ]
    assert invalid_routing["thread_binding_complete"] is False

    facts["source_thread_id"] = "synthetic-thread-id"
    facts["attachment_files"] = ["packet.pdf"]
    attachment = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert attachment["status"] == "BLOCKED_ATTACHMENT_NOT_AUTHORIZED"
    assert attachment["attachment_count"] == 1


def test_secret_or_credential_facts_fail_closed_without_echoing_values():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "submission_name": "Synthetic Submission",
            "portal_name": "Synthetic Portal",
            "deadline_local": "July 22, 2026 at noon Eastern",
            "portal_blocker": "Authentication code: 123456",
            "steps_already_tried": "Signed in and requested a new code.",
        }
    )

    blocked_value = module.render_response(
        "PORTAL_SUPPORT_DEADLINE_RESCUE", facts
    )
    assert blocked_value["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert blocked_value["secret_or_credential_fields"] == ["portal_blocker"]
    assert blocked_value["subject"] is None
    assert blocked_value["body"] is None
    assert "123456" not in json.dumps(blocked_value)

    facts["portal_blocker"] = "The authentication-code prompt remains visible."
    facts["one_time_code"] = "654321"
    blocked_key = module.render_response("PORTAL_SUPPORT_DEADLINE_RESCUE", facts)
    assert blocked_key["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert blocked_key["secret_or_credential_fields"] == ["one_time_code"]
    assert "654321" not in json.dumps(blocked_key)


def test_nested_secret_keys_and_private_key_material_fail_closed():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "opportunity_name": "Synthetic Notice",
            "eligibility_question": "the current entity type is eligible",
            "operator_context": {"access-token": "synthetic-secret-value"},
        }
    )
    nested = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert nested["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert nested["secret_or_credential_fields"] == ["operator_context"]
    assert "synthetic-secret-value" not in json.dumps(nested)

    facts.pop("operator_context")
    facts["operator_note"] = "-----BEGIN PRIVATE KEY-----"
    private_key = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert private_key["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert private_key["secret_or_credential_fields"] == ["operator_note"]


def test_camel_case_authorization_and_provider_credentials_fail_closed():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "opportunity_name": "Synthetic Notice",
            "eligibility_question": "the current entity type is eligible",
            "accessToken": "synthetic-value",
        }
    )
    camel_case = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert camel_case["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert camel_case["secret_or_credential_fields"] == ["accessToken"]
    assert "synthetic-value" not in json.dumps(camel_case)

    facts.pop("accessToken")
    facts["operator_note"] = "Authorization: Bearer SYNTHETIC_TOKEN_VALUE_123456"
    authorization = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert authorization["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert authorization["secret_or_credential_fields"] == ["operator_note"]
    assert "SYNTHETIC_TOKEN_VALUE_123456" not in json.dumps(authorization)

    facts["operator_note"] = "sk-" + ("A" * 24)
    provider_key = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert provider_key["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert provider_key["secret_or_credential_fields"] == ["operator_note"]
    assert ("sk-" + ("A" * 24)) not in json.dumps(provider_key)


def test_alphanumeric_codes_opaque_bytes_and_non_object_facts_fail_closed():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "opportunity_name": "Synthetic Notice",
            "eligibility_question": "the current entity type is eligible",
            "operator_note": "Verification code: A1B2C3",
        }
    )
    alphanumeric = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert alphanumeric["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert alphanumeric["secret_or_credential_fields"] == ["operator_note"]
    assert "A1B2C3" not in json.dumps(alphanumeric)

    facts["operator_note"] = b"opaque-private-input"
    opaque = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert opaque["status"] == "BLOCKED_SECRET_OR_CREDENTIAL_FACT"
    assert opaque["secret_or_credential_fields"] == ["operator_note"]
    assert "opaque-private-input" not in json.dumps(opaque)

    try:
        module.render_response("DEADLINE_CLARIFICATION", [])
    except module.OutreachRegistryError as exc:
        assert str(exc) == "FACTS_NOT_OBJECT"
    else:
        raise AssertionError("non-object facts must fail closed")


def test_registry_rejects_hardcoded_credential_material():
    module = load_module()
    registry = module.read_registry()
    registry["templates"][1]["body"] += (
        "\nAuthorization: Bearer SYNTHETIC_TOKEN_VALUE_123456"
    )

    try:
        module.validate_registry(registry)
    except module.OutreachRegistryError as exc:
        assert str(exc) == "HARDCODED_TEMPLATE_CREDENTIAL:DEADLINE_CLARIFICATION"
    else:
        raise AssertionError("hardcoded template credentials must fail closed")


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


def test_deadline_rescue_templates_require_valid_future_machine_deadlines():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "submission_name": "Synthetic Submission",
            "portal_name": "Synthetic Portal",
            "deadline_local": "July 22, 2026 at noon Eastern",
            "portal_blocker": "The supporting-document section remains incomplete.",
            "steps_already_tried": "Reviewed the official instructions and retried once.",
        }
    )

    missing = module.render_response("PORTAL_SUPPORT_DEADLINE_RESCUE", facts)
    assert missing["status"] == "BLOCKED_MISSING_FACTS"
    assert missing["missing_fields"] == ["deadline_iso"]
    assert missing["deadline_policy"] == "REQUIRED"

    facts["deadline_iso"] = "2026-07-22T12:00:00"
    invalid = module.render_response("PORTAL_SUPPORT_DEADLINE_RESCUE", facts)
    assert invalid["status"] == "BLOCKED_INVALID_DEADLINE"
    assert invalid["deadline"]["validation_error"] == "DEADLINE_TIMEZONE_REQUIRED"
    assert invalid["subject"] is None

    facts["deadline_iso"] = "2026-07-22T16:00:00Z"
    past = module.render_response(
        "PORTAL_SUPPORT_DEADLINE_RESCUE",
        facts,
        current_utc="2026-07-22T16:00:01Z",
    )
    assert past["status"] == "BLOCKED_DEADLINE_PASSED"

    ready = module.render_response(
        "PORTAL_SUPPORT_DEADLINE_RESCUE",
        facts,
        current_utc="2026-07-22T15:00:00Z",
    )
    assert ready["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert ready["deadline"]["urgency"] == "CRITICAL_UNDER_24_HOURS"


def test_rendered_subject_and_body_control_characters_fail_closed():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "opportunity_name": "Synthetic Notice",
            "eligibility_question": "the current entity type is eligible",
            "source_subject": "Synthetic Notice\r\nBcc: injected@example.org",
        }
    )
    subject = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert subject["status"] == "BLOCKED_SUBJECT_CONTROL_CHARACTER"
    assert subject["subject"] is None
    assert subject["body"] is None
    assert "injected@example.org" not in json.dumps(subject)

    facts["source_subject"] = "Synthetic Notice"
    facts["eligibility_question"] = "the rule applies\x00without ambiguity"
    body = module.render_response("DEADLINE_CLARIFICATION", facts)
    assert body["status"] == "BLOCKED_BODY_CONTROL_CHARACTER"
    assert body["subject"] is None
    assert body["body"] is None


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
            "deadline_iso": "2026-07-22T16:00:00Z",
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
        "COMPONENT_INSTRUCTION_ESCALATION",
        component,
        current_utc="2026-07-21T16:00:00Z",
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
    assert payload["controls"]["duplicate_response_identity_fail_closed"] is True
    assert payload["controls"]["deterministic_response_identity"] is True
    assert payload["controls"]["source_message_and_thread_binding_required"] is True
    assert payload["controls"]["secret_or_credential_fail_closed"] is True
    assert payload["controls"]["opaque_binary_fact_fail_closed"] is True
    assert payload["controls"]["hardcoded_template_credential_fail_closed"] is True
    assert payload["controls"]["deadline_policy_fail_closed"] is True
    assert payload["controls"]["subject_header_injection_fail_closed"] is True
    assert payload["controls"]["body_control_character_fail_closed"] is True
    assert "Duplicate-send gate: `FAIL_CLOSED`" in markdown
    assert "Duplicate response-identity gate: `FAIL_CLOSED`" in markdown
    assert "Source message/thread binding: `REQUIRED`" in markdown
    assert "Secret-or-credential gate: `FAIL_CLOSED`" in markdown
    assert "Deadline-policy gate: `FAIL_CLOSED`" in markdown
    assert "Subject header-injection gate: `FAIL_CLOSED`" in markdown
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


def test_unchanged_registry_rebuild_is_byte_stable(tmp_path):
    module = load_module()
    registry = module.validate_registry(module.read_registry(CONFIG))

    first = module.build_public_payload(registry)
    second = module.build_public_payload(registry)
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    module.write_json(first_path, first)
    module.write_json(second_path, second)

    assert first == second
    assert first_path.read_bytes() == second_path.read_bytes()
    assert first["generated_utc"] == first["source_effective_utc"]
    assert first["source_effective_utc"] == module.canonical_utc(
        registry["source_effective_utc"]
    )
    assert first["controls"]["unchanged_rebuild_byte_stable"] is True
