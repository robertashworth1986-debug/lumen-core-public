from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path

import pytest


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
ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE = (
    ROOT / "config" / "outreach_action_time_mailbox_receipt_template_v1.json"
)


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


def direct_investor_facts() -> dict[str, str]:
    facts = common_facts()
    facts.update(
        {
            "investor_program_name": "Synthetic Review Program",
            "company_one_line": (
                "LumenCore builds bounded, replayable technical-claim reviews."
            ),
            "current_raise_amount": "$250,000",
            "current_raise_purpose": (
                "one buyer-controlled independent evaluation"
            ),
            "six_month_milestone": (
                "complete one preregistered evaluation and retain all results"
            ),
            "climate_component": (
                "evaluate grid-planning workflows without claiming savings"
            ),
            "current_stage_disclosure": (
                "pre-revenue and pilot-stage; no field performance is claimed"
            ),
            "public_company_url": "https://example.org",
            "public_proof_url": "https://example.org/proof",
        }
    )
    return facts


def partner_teaming_facts() -> dict[str, str]:
    facts = common_facts()
    facts.pop("source_message_id")
    facts.update(
        {
            "agency_name": "Synthetic Health Agency",
            "opportunity_name": "Synthetic Evidence Assurance Sources Sought",
            "notice_type": "sources sought notice for market research",
            "opportunity_summary": (
                "a bounded proof of concept for monitoring public program artifacts"
            ),
            "deadline_iso": "2026-07-30T17:00:00-04:00",
            "teaming_basis": (
                "The official notice permits respondents to identify proposed "
                "team members and roles."
            ),
            "bounded_contribution": (
                "authorized public-source custody, deterministic validation, "
                "traceability, and reproducible evidence packages."
            ),
            "qualification_boundary": (
                "No health-agency authorization, certification, prior "
                "performance, or prime-delivery qualification is claimed."
            ),
            "partner_fit_basis": (
                "The recipient publishes directly relevant interoperability "
                "and program-policy experience."
            ),
            "requested_partner_role": (
                "evaluate serving as the domain-policy lead or convening a "
                "qualified team."
            ),
            "authorization_request": (
                "the role under evaluation, authorized principal, available "
                "technical and security leads, and any additional organization "
                "that should join the discussion."
            ),
            "duplicate_review_disclosure": (
                "A full-mailbox search found no prior message to this route "
                "about this opportunity."
            ),
            "source_opportunity_url": "https://example.gov/opportunity",
            "public_company_url": "https://example.org",
            "public_proof_url": "https://example.org/proof",
        }
    )
    return facts


def mailbox_receipt(
    binding: dict[str, object],
    *,
    checked_utc: str = "2026-07-27T22:04:55Z",
) -> dict[str, object]:
    return {
        "attachment_count": binding["attachment_count"],
        "attachment_set_sha256": binding["attachment_set_sha256"],
        "bcc_count": 0,
        "body_sha256": binding["body_sha256"],
        "cc_count": 0,
        "checked_utc": checked_utc,
        "current_draft_only": True,
        "draft_present": True,
        "draft_readback_checked_utc": checked_utc,
        "draft_sent": False,
        "full_mailbox_search_completed": True,
        "identifiers_omitted": True,
        "matching_current_draft_count": 1,
        "matching_received_after_draft_count": 0,
        "matching_sent_count": 0,
        "message_body_omitted": True,
        "recipient_route_sha256": binding["recipient_route_sha256"],
        "schema": "lumencore.outreach_action_time_mailbox_receipt.v1",
        "search_scope": "ALL_MAIL_BOUND_ROUTE_THREAD_SUBJECT_BODY",
        "source_message_id_sha256": binding["source_message_id_sha256"],
        "subject_sha256": binding["subject_sha256"],
    }


def test_registry_validates_and_covers_high_value_response_states():
    module = load_module()
    registry = module.validate_registry(module.read_registry())
    ids = {row["template_id"] for row in registry["templates"]}

    assert registry["schema"] == module.SCHEMA
    assert len(ids) == 17
    assert {
        "NO_DUPLICATE_MONITOR",
        "NO_DUPLICATE_MEETING_PREP",
        "DEADLINE_CLARIFICATION",
        "PORTAL_SUPPORT_DEADLINE_RESCUE",
        "REQUESTED_INFORMATION_REPLY",
        "REQUESTED_ASSET_DELIVERY_REPLY",
        "SUBMISSION_RECEIPT_FOLLOWUP",
        "COMPONENT_INSTRUCTION_ESCALATION",
        "BOUNDED_REVIEW_FOLLOWUP",
        "WARM_INVESTOR_INTRO_REQUEST",
        "FUNDING_REVIEW_STATUS_CHECK",
        "DIRECT_INVESTOR_REVIEW_REQUEST",
        "INITIAL_PARTNER_TEAMING_INQUIRY",
        "VALIDATION_PILOT_REQUEST",
        "DECLINE_CLOSEOUT",
        "MOU_ONBOARDING_REPLY",
        "MEETING_REBOOK_REQUEST",
    } == ids


def test_initial_partner_teaming_inquiry_is_deadline_bound_and_no_attachment():
    module = load_module()
    facts = partner_teaming_facts()

    rendered = module.render_response(
        "INITIAL_PARTNER_TEAMING_INQUIRY",
        facts,
        current_utc="2026-07-27T22:00:00Z",
    )

    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["template_id"] == "INITIAL_PARTNER_TEAMING_INQUIRY"
    assert rendered["attachment_policy"] == "NONE"
    assert rendered["attachment_count"] == 0
    assert rendered["deadline"]["deadline_utc"] == "2026-07-30T21:00:00+00:00"
    assert rendered["deadline"]["urgency"] == "HIGH_UNDER_72_HOURS"
    assert "2026-07-30T21:00:00Z" in rendered["body"]
    assert "No attachment is included" in rendered["body"]
    assert "No health-agency authorization" in rendered["body"]
    assert rendered["draft_binding_complete"] is True
    assert rendered["exact_action_time_approval_ready"] is False
    assert rendered["exact_action_time_approval_phrase"] is None
    assert rendered["exact_action_time_approval_blockers"] == [
        "ACTION_TIME_MAILBOX_RECEIPT_REQUIRED"
    ]

    duplicate = module.render_response(
        "INITIAL_PARTNER_TEAMING_INQUIRY",
        facts,
        already_sent=True,
        inbound_requires_response=False,
        current_utc="2026-07-27T22:00:00Z",
    )
    assert duplicate["status"] == "MONITOR_NO_DUPLICATE"
    assert duplicate["body"] is None


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
    meeting_prep = module.render_response("NO_DUPLICATE_MEETING_PREP", {})

    assert duplicate["status"] == "MONITOR_NO_DUPLICATE"
    assert duplicate["duplicate_send_blocked"] is True
    assert duplicate["subject"] is None
    assert duplicate["body"] is None
    assert duplicate["dispatch_binding"] is None
    assert duplicate["exact_action_time_approval_ready"] is False
    assert monitor["status"] == "MONITOR_NO_SEND"
    assert monitor["send_performed"] is False
    assert monitor["dispatch_binding"] is None
    assert monitor["exact_action_time_approval_phrase"] is None
    assert meeting_prep["status"] == "MONITOR_NO_SEND"
    assert meeting_prep["send_performed"] is False
    assert meeting_prep["subject"] is None
    assert meeting_prep["body"] is None
    assert meeting_prep["dispatch_binding"] is None
    assert meeting_prep["exact_action_time_approval_phrase"] is None


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
    assert critical["dispatch_binding"]["deadline_utc"] == "2026-07-19T16:00:00Z"

    later_deadline_facts = copy.deepcopy(facts)
    later_deadline_facts["deadline_iso"] = "2026-07-19T12:00:00-05:00"
    later_deadline = module.render_response(
        "DEADLINE_CLARIFICATION",
        later_deadline_facts,
        current_utc="2026-07-18T17:00:00+00:00",
    )
    assert later_deadline["dispatch_binding"]["binding_sha256"] != critical[
        "dispatch_binding"
    ]["binding_sha256"]

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
            "deadline_iso": "2026-07-22T12:00:00-04:00",
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
        current_utc="2026-07-20T12:00:00Z",
    )
    assert rendered_component["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered_component["attachment_policy"] == "NONE"
    assert "following up once" in rendered_component["body"]
    assert "prerequisites-in-progress" in rendered_component["body"]
    assert "will not duplicate the proposal package" in rendered_component["body"]
    assert "2026-07-22T16:00:00Z" in rendered_component["body"]
    assert rendered_component["rendered_deadline_iso"] == "2026-07-22T16:00:00Z"
    assert rendered_component["send_allowed_by_builder"] is False


def test_investor_intro_and_review_status_templates_are_bounded_and_attachment_free():
    module = load_module()
    intro = common_facts()
    intro.update(
        {
            "current_raise_amount": "$250,000",
            "current_raise_purpose": (
                "one buyer-controlled, independently reviewable pilot"
            ),
            "primary_fund_name": "Synthetic Deep Tech Fund",
            "primary_fit_reason": (
                "Its energy, infrastructure, and enterprise AI focus is the closest fit."
            ),
            "secondary_fund_name": "Synthetic Seed Fund",
            "public_proof_url": "https://example.org/proof",
            "current_stage_disclosure": (
                "pre-revenue and pilot-stage; no field validation, customer revenue, "
                "or award is claimed"
            ),
        }
    )
    rendered_intro = module.render_response("WARM_INVESTOR_INTRO_REQUEST", intro)

    assert rendered_intro["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered_intro["attachment_policy"] == "NONE"
    assert "following up once" in rendered_intro["body"]
    assert "No attachment is included" in rendered_intro["body"]
    assert "will not send another introduction follow-up" in rendered_intro["body"]
    assert rendered_intro["send_allowed_by_builder"] is False

    review = common_facts()
    review.update(
        {
            "application_name": "Synthetic Seed Fund application",
            "application_date_local": "July 4, 2026",
            "stated_review_window": "5-10 business days",
            "duplicate_review_disclosure": (
                "One separate program update was sent to its named reviewer; "
                "this request does not duplicate that review."
            ),
        }
    )
    rendered_review = module.render_response("FUNDING_REVIEW_STATUS_CHECK", review)

    assert rendered_review["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered_review["attachment_policy"] == "NONE"
    assert "following up once" in rendered_review["body"]
    assert "status check only, not a duplicate application" in rendered_review["body"]
    assert rendered_review["send_allowed_by_builder"] is False

    duplicate = module.render_response(
        "WARM_INVESTOR_INTRO_REQUEST",
        intro,
        already_sent=True,
        inbound_requires_response=False,
    )
    assert duplicate["status"] == "MONITOR_NO_DUPLICATE"
    assert duplicate["body"] is None


def test_written_public_registry_is_current_and_contains_no_contact_values():
    module = load_module()
    payload = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    markdown = OUT_MD.read_text(encoding="utf-8")
    combined = OUT_JSON.read_text(encoding="utf-8") + markdown

    assert payload["schema"] == module.PUBLIC_SCHEMA
    assert payload["template_count"] == 17
    assert payload["controls"]["builder_can_send_email"] is False
    assert payload["controls"]["duplicate_send_fail_closed"] is True
    assert payload["quality_gate"]["status"] == "PASS"
    assert payload["quality_gate"]["all_templates_pass"] is True
    assert payload["quality_gate"]["template_count"] == 17
    assert payload["quality_gate"]["check_count"] == 204
    assert payload["quality_gate"]["deadline_control_template_ids"] == [
        "COMPONENT_INSTRUCTION_ESCALATION",
        "INITIAL_PARTNER_TEAMING_INQUIRY",
        "PORTAL_SUPPORT_DEADLINE_RESCUE",
    ]
    assert payload["quality_gate"]["https_public_url_field_count"] == 6
    assert all(
        row["status"] == "PASS"
        for row in payload["quality_gate"]["template_results"]
    )
    assert payload["controls"]["known_deadline_requires_aware_iso_control"] is True
    assert payload["controls"]["rendered_deadline_matches_evaluated_deadline"] is True
    assert payload["controls"]["public_url_requires_https_without_credentials"] is True
    assert payload["controls"]["rendered_subject_header_injection_fail_closed"] is True
    assert payload["controls"]["rendered_fact_claim_guard_fail_closed"] is True
    assert (
        payload["controls"][
            "high_risk_claim_requires_hash_bound_evidence_receipt"
        ]
        is True
    )
    assert payload["controls"]["claim_evidence_source_artifacts_rehashed"] is True
    assert payload["controls"]["duplicate_json_key_fail_closed"] is True
    assert payload["controls"]["ready_render_has_dispatch_binding"] is True
    assert (
        payload["controls"]["recipient_route_and_source_thread_hash_bound"] is True
    )
    assert (
        payload["controls"]["subject_body_deadline_and_attachment_set_hash_bound"]
        is True
    )
    assert (
        payload["controls"][
            "attachment_content_hash_required_for_exact_approval"
        ]
        is True
    )
    assert payload["controls"]["exact_approval_phrase_is_binding_scoped"] is True
    assert payload["controls"]["draft_binding_is_not_send_authorization"] is True
    assert payload["controls"]["action_time_mailbox_receipt_required"] is True
    assert payload["controls"]["action_time_mailbox_receipt_schema"] == (
        module.ACTION_TIME_MAILBOX_RECEIPT_SCHEMA
    )
    assert payload["controls"]["action_time_mailbox_receipt_template"] == (
        "config/outreach_action_time_mailbox_receipt_template_v1.json"
    )
    assert payload["controls"][
        "action_time_mailbox_receipt_template_sha256"
    ] == module.canonical_object_sha256(
        module.validate_action_time_mailbox_receipt_template()
    )
    assert payload["controls"]["action_time_mailbox_max_age_seconds"] == 900
    assert payload["controls"]["action_time_approval_window_seconds"] == 300
    assert payload["controls"]["exact_approval_expires"] is True
    assert payload["controls"]["single_use_action_time_binding"] is True
    assert payload["controls"]["claim_evidence_receipt_schema"] == (
        module.CLAIM_EVIDENCE_RECEIPT_SCHEMA
    )
    assert payload["controls"]["claim_evidence_receipt_template"] == (
        "config/outreach_claim_evidence_receipt_template_v1.json"
    )
    assert (
        payload["controls"]["source_config_hash_cross_platform_canonical_json"]
        is True
    )
    assert payload["source_config_hash_basis"] == "SORTED_COMPACT_JSON_UTF8"
    assert "Duplicate-send gate: `FAIL_CLOSED`" in markdown
    assert "Inserted-fact claim gate: `FAIL_CLOSED`" in markdown
    assert "EXACT_VALUE_AND_SOURCE_HASH_BOUND" in markdown
    assert "RECIPIENT_THREAD_BODY_DEADLINE_EVIDENCE_HASH_BOUND" in markdown
    assert "Draft binding is send authorization: `false`" in markdown
    assert "Action-time mailbox receipt: `REQUIRED`" in markdown
    assert "Exact approval phrase: `BINDING_SCOPED_SINGLE_USE`" in markdown
    assert "Exact approval window: `5_MINUTES_MAX`" in markdown
    assert "Static quality gate: `PASS`" in markdown
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

    assert payload["source_config_sha256"] == module.canonical_object_sha256(
        registry
    )
    assert payload["source_config_hash_basis"] == "SORTED_COMPACT_JSON_UTF8"
    assert payload["send_policy_counts"] == {
        "HUMAN_ACTION_DUE": 9,
        "MONITOR_NO_SEND": 2,
        "REPLY_AFTER_FACT_REVIEW": 6,
    }


def test_quality_gate_rejects_unused_and_overlapping_field_declarations():
    module = load_module()
    registry = module.read_registry(CONFIG)
    broken = copy.deepcopy(registry)
    template = next(
        row
        for row in broken["templates"]
        if row["template_id"] == "PORTAL_SUPPORT_DEADLINE_RESCUE"
    )
    template["required_fields"].append("unused_fact")
    with pytest.raises(module.OutreachRegistryError, match="QUALITY_GATE_FAILED"):
        module.validate_registry(broken)

    broken = copy.deepcopy(registry)
    template = next(
        row
        for row in broken["templates"]
        if row["template_id"] == "PORTAL_SUPPORT_DEADLINE_RESCUE"
    )
    template["required_fields"] = [
        "deadline_local" if field == "deadline_iso" else field
        for field in template["required_fields"]
    ]
    template["body"] = template["body"].replace(
        "{deadline_iso}", "{deadline_local}"
    )
    with pytest.raises(
        module.OutreachRegistryError,
        match="known_deadline_uses_single_structured_value",
    ):
        module.validate_registry(broken)

    broken = copy.deepcopy(registry)
    template = next(
        row
        for row in broken["templates"]
        if row["template_id"] == "DEADLINE_CLARIFICATION"
    )
    template["required_fields"].append("recipient_email")
    with pytest.raises(module.OutreachRegistryError, match="QUALITY_GATE_FAILED"):
        module.validate_registry(broken)


def test_known_deadlines_urls_and_rendered_subjects_fail_closed():
    module = load_module()
    portal = common_facts()
    portal.update(
        {
            "submission_name": "Synthetic Submission",
            "portal_name": "Synthetic Portal",
            "portal_blocker": "The final validation page does not load.",
            "steps_already_tried": "Signed out, signed back in, and retried once.",
        }
    )
    missing_deadline = module.render_response(
        "PORTAL_SUPPORT_DEADLINE_RESCUE",
        portal,
        current_utc="2026-07-23T12:00:00Z",
    )
    assert missing_deadline["status"] == "BLOCKED_MISSING_FACTS"
    assert "deadline_iso" in missing_deadline["missing_fields"]

    intro = common_facts()
    intro.update(
        {
            "current_raise_amount": "$250,000",
            "current_raise_purpose": "a bounded independent evaluation",
            "primary_fund_name": "Synthetic Fund",
            "primary_fit_reason": "Its stated focus is aligned.",
            "secondary_fund_name": "Synthetic Secondary Fund",
            "public_proof_url": "http://example.org/proof",
            "current_stage_disclosure": "pre-revenue and pilot-stage",
        }
    )
    invalid_url = module.render_response("WARM_INVESTOR_INTRO_REQUEST", intro)
    assert invalid_url["status"] == "BLOCKED_INVALID_PUBLIC_URL"
    assert invalid_url["invalid_url_fields"] == ["public_proof_url"]

    review = common_facts()
    review.update(
        {
            "source_subject": "Review update\r\nBcc: hidden@example.org",
            "application_name": "Synthetic application",
            "application_date_local": "July 4, 2026",
            "stated_review_window": "5-10 business days",
            "duplicate_review_disclosure": "No duplicate review requested.",
        }
    )
    unsafe = module.render_response("FUNDING_REVIEW_STATUS_CHECK", review)
    assert unsafe["status"] == "BLOCKED_UNSAFE_RENDERED_CONTENT"
    assert "SUBJECT_LINE_BREAK" in unsafe["unsafe_reasons"]
    assert unsafe["subject"] is None
    assert unsafe["body"] is None


def test_requested_information_may_contain_literal_json_braces():
    module = load_module()
    facts = common_facts()
    facts["requested_information"] = '{"status":"bounded","send_now":false}'

    rendered = module.render_response("REQUESTED_INFORMATION_REPLY", facts)

    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert '{"status":"bounded","send_now":false}' in rendered["body"]
    assert rendered["dispatch_binding"]["schema"] == module.DISPATCH_BINDING_SCHEMA
    assert rendered["draft_binding_complete"] is True
    assert rendered["exact_action_time_approval_ready"] is False
    assert rendered["exact_action_time_approval_phrase"] is None


def test_ready_dispatch_binding_is_stable_private_safe_and_scope_sensitive():
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
    second = module.render_response("VALIDATION_PILOT_REQUEST", copy.deepcopy(facts))

    assert first["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert first["dispatch_binding"] == second["dispatch_binding"]
    binding = first["dispatch_binding"]
    assert binding["schema"] == module.DISPATCH_BINDING_SCHEMA
    assert binding["binding_sha256"] == module.canonical_object_sha256(
        binding, omit={"binding_sha256"}
    )
    assert binding["attachment_count"] == 0
    assert binding["attachment_content_hashes_bound"] is True
    assert first["draft_binding_complete"] is True
    assert first["exact_action_time_approval_ready"] is False
    assert first["exact_action_time_approval_blockers"] == [
        "ACTION_TIME_MAILBOX_RECEIPT_REQUIRED"
    ]
    assert first["exact_action_time_approval_phrase"] is None
    private_safe_binding = json.dumps(binding, sort_keys=True)
    assert facts["recipient_email"] not in private_safe_binding
    assert facts["source_message_id"] not in private_safe_binding

    recipient_change = copy.deepcopy(facts)
    recipient_change["recipient_email"] = "other-reviewer@example.org"
    source_change = copy.deepcopy(facts)
    source_change["source_message_id"] = "different-synthetic-message"
    body_change = copy.deepcopy(facts)
    body_change["requested_next_step"] = "name two technical reviewers"

    assert (
        module.render_response(
            "VALIDATION_PILOT_REQUEST", recipient_change
        )["dispatch_binding"]["binding_sha256"]
        != binding["binding_sha256"]
    )
    assert (
        module.render_response(
            "VALIDATION_PILOT_REQUEST", source_change
        )["dispatch_binding"]["binding_sha256"]
        != binding["binding_sha256"]
    )
    body_changed_render = module.render_response(
        "VALIDATION_PILOT_REQUEST", body_change
    )
    assert body_changed_render["dispatch_binding"]["body_sha256"] != binding[
        "body_sha256"
    ]
    assert body_changed_render["dispatch_binding"]["binding_sha256"] != binding[
        "binding_sha256"
    ]


def test_action_time_authorization_is_private_safe_exact_and_five_minutes():
    module = load_module()
    facts = common_facts()
    facts["requested_information"] = "One bounded technical-review summary."
    rendered = module.render_response("REQUESTED_INFORMATION_REPLY", facts)
    binding = rendered["dispatch_binding"]

    authorization = module.build_action_time_authorization(
        rendered,
        mailbox_receipt(binding),
        current_utc="2026-07-27T22:05:00Z",
    )

    assert authorization["schema"] == module.ACTION_TIME_AUTHORIZATION_SCHEMA
    assert authorization["status"] == "READY_FOR_SINGLE_USE_EXACT_APPROVAL"
    assert authorization["approval_binding"]["approval_window_opened_utc"] == (
        "2026-07-27T22:05:00Z"
    )
    assert authorization["approval_binding"]["approval_window_expires_utc"] == (
        "2026-07-27T22:10:00Z"
    )
    assert authorization["controls"]["approval_window_seconds"] == 300
    assert authorization["controls"]["single_use"] is True
    assert authorization["builder_can_send_email"] is False
    assert authorization["send_authorized"] is False
    assert authorization["send_performed"] is False
    phrase = authorization["exact_action_time_approval_phrase"]
    assert phrase.startswith("APPROVE ONE OUTREACH DISPATCH:")
    assert authorization["approval_binding"]["binding_sha256"] in phrase
    assert binding["binding_sha256"] in phrase
    serialized = json.dumps(authorization, sort_keys=True)
    assert facts["recipient_email"] not in serialized
    assert facts["source_message_id"] not in serialized

    current = module.evaluate_action_time_authorization(
        authorization,
        exact_approval_phrase=phrase,
        current_utc="2026-07-27T22:09:59Z",
    )
    assert current["status"] == "CURRENT_EXACT_APPROVAL_PRESENT"
    assert current["action_time_approval_valid"] is True
    assert current["send_authorized"] is True
    assert current["builder_can_send_email"] is False
    assert current["send_performed"] is False

    expired = module.evaluate_action_time_authorization(
        authorization,
        exact_approval_phrase=phrase,
        current_utc="2026-07-27T22:10:00Z",
    )
    assert expired["action_time_approval_valid"] is False
    assert expired["send_authorized"] is False
    assert expired["blockers"] == ["APPROVAL_WINDOW_EXPIRED"]

    wrong_phrase = module.evaluate_action_time_authorization(
        authorization,
        exact_approval_phrase=phrase + " altered",
        current_utc="2026-07-27T22:06:00Z",
    )
    assert wrong_phrase["action_time_approval_valid"] is False
    assert wrong_phrase["blockers"] == ["EXACT_APPROVAL_PHRASE_MISMATCH"]

    consumed = module.evaluate_action_time_authorization(
        authorization,
        exact_approval_phrase=phrase,
        current_utc="2026-07-27T22:06:00Z",
        dispatch_consumed=True,
    )
    assert consumed["action_time_approval_valid"] is False
    assert consumed["blockers"] == ["SINGLE_USE_BINDING_ALREADY_CONSUMED"]

    extended = copy.deepcopy(authorization)
    extended_binding = extended["approval_binding"]
    extended_binding["approval_window_expires_utc"] = "2026-07-27T22:20:00Z"
    extended_binding["binding_sha256"] = module.canonical_object_sha256(
        extended_binding,
        omit={"binding_sha256"},
    )
    extended_phrase = module._action_time_approval_phrase(extended_binding)
    extended["exact_action_time_approval_phrase"] = extended_phrase
    extended_result = module.evaluate_action_time_authorization(
        extended,
        exact_approval_phrase=extended_phrase,
        current_utc="2026-07-27T22:06:00Z",
    )
    assert extended_result["action_time_approval_valid"] is False
    assert "APPROVAL_WINDOW_BOUNDS_INVALID" in extended_result["blockers"]

    tampered_dispatch = copy.deepcopy(authorization)
    tampered_dispatch["dispatch_binding"]["body_sha256"] = "F" * 64
    tampered_dispatch_result = module.evaluate_action_time_authorization(
        tampered_dispatch,
        exact_approval_phrase=phrase,
        current_utc="2026-07-27T22:06:00Z",
    )
    assert tampered_dispatch_result["action_time_approval_valid"] is False
    assert "DISPATCH_BINDING_HASH_MISMATCH" in (
        tampered_dispatch_result["blockers"]
    )

    tampered_receipt = copy.deepcopy(authorization)
    tampered_receipt["mailbox_receipt"]["matching_sent_count"] = 1
    tampered_receipt_result = module.evaluate_action_time_authorization(
        tampered_receipt,
        exact_approval_phrase=phrase,
        current_utc="2026-07-27T22:06:00Z",
    )
    assert tampered_receipt_result["action_time_approval_valid"] is False
    assert "ACTION_TIME_MAILBOX_RECEIPT_HASH_MISMATCH" in (
        tampered_receipt_result["blockers"]
    )


def test_action_time_authorization_rejects_deadline_and_bad_mailbox_evidence():
    module = load_module()
    rendered = module.render_response(
        "INITIAL_PARTNER_TEAMING_INQUIRY",
        partner_teaming_facts(),
        current_utc="2026-07-27T22:00:00Z",
    )
    binding = rendered["dispatch_binding"]

    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_DEADLINE_REACHED",
    ):
        module.build_action_time_authorization(
            rendered,
            mailbox_receipt(binding, checked_utc="2026-07-30T20:59:59Z"),
            current_utc="2026-07-30T21:00:00Z",
        )

    cases = [
        (
            {"matching_sent_count": 1},
            "2026-07-27T22:05:00Z",
            "ACTION_TIME_MAILBOX_COUNT_INVALID:matching_sent_count",
        ),
        (
            {"matching_received_after_draft_count": 1},
            "2026-07-27T22:05:00Z",
            "ACTION_TIME_MAILBOX_COUNT_INVALID:matching_received_after_draft_count",
        ),
        (
            {"draft_sent": True},
            "2026-07-27T22:05:00Z",
            "ACTION_TIME_DRAFT_ALREADY_SENT",
        ),
        (
            {"body_sha256": "F" * 64},
            "2026-07-27T22:05:00Z",
            "ACTION_TIME_BODY_MISMATCH",
        ),
        (
            {"private_message_id": "must-not-be-present"},
            "2026-07-27T22:05:00Z",
            "ACTION_TIME_MAILBOX_RECEIPT_FIELDS_INVALID",
        ),
    ]
    for changes, current_utc, expected in cases:
        receipt = mailbox_receipt(binding)
        receipt.update(changes)
        with pytest.raises(module.OutreachRegistryError, match=expected):
            module.build_action_time_authorization(
                rendered,
                receipt,
                current_utc=current_utc,
            )

    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_MAILBOX_SEARCH_STALE",
    ):
        module.build_action_time_authorization(
            rendered,
            mailbox_receipt(binding),
            current_utc="2026-07-27T22:20:00Z",
        )

    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_MAILBOX_SEARCH_FROM_FUTURE",
    ):
        module.build_action_time_authorization(
            rendered,
            mailbox_receipt(binding),
            current_utc="2026-07-27T22:04:00Z",
        )

    stale_readback = mailbox_receipt(binding)
    stale_readback["checked_utc"] = "2026-07-27T22:19:59Z"
    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_DRAFT_READBACK_STALE",
    ):
        module.build_action_time_authorization(
            rendered,
            stale_readback,
            current_utc="2026-07-27T22:20:00Z",
        )

    future_readback = mailbox_receipt(binding)
    future_readback["checked_utc"] = "2026-07-27T22:03:59Z"
    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_DRAFT_READBACK_FROM_FUTURE",
    ):
        module.build_action_time_authorization(
            rendered,
            future_readback,
            current_utc="2026-07-27T22:04:00Z",
        )


def test_mailbox_receipt_template_is_deliberately_non_authorizing(tmp_path):
    module = load_module()
    template = json.loads(
        ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE.read_text(encoding="utf-8")
    )
    assert set(template) == module.ACTION_TIME_MAILBOX_RECEIPT_FIELDS
    assert template["schema"] == module.ACTION_TIME_MAILBOX_RECEIPT_SCHEMA
    assert template["full_mailbox_search_completed"] is False
    assert template["draft_present"] is False
    assert template["matching_current_draft_count"] == 0
    assert module.validate_action_time_mailbox_receipt_template() == template
    unsafe_template = copy.deepcopy(template)
    unsafe_template["full_mailbox_search_completed"] = True
    unsafe_path = tmp_path / "unsafe_mailbox_receipt.json"
    unsafe_path.write_text(
        json.dumps(unsafe_template, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_MAILBOX_RECEIPT_TEMPLATE_MUST_NOT_AUTHORIZE",
    ):
        module.validate_action_time_mailbox_receipt_template(unsafe_path)

    facts = common_facts()
    facts["requested_information"] = "One bounded technical-review summary."
    rendered = module.render_response("REQUESTED_INFORMATION_REPLY", facts)
    with pytest.raises(
        module.OutreachRegistryError,
        match="ACTION_TIME_MAILBOX_CONTROL_INVALID",
    ):
        module.build_action_time_authorization(
            rendered,
            template,
            current_utc="2026-07-27T22:05:00Z",
        )


def test_requested_asset_delivery_requires_explicit_request_and_private_review():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "requested_asset_summary": "light-background and dark-background PNG logos",
            "attachment_inventory": "lumencore-light.png; lumencore-dark.png",
            "permitted_use_boundary": (
                "consortium member listing and related onboarding materials only"
            ),
            "attachment_files": [
                "lumencore-light.png",
                "lumencore-dark.png",
            ],
        }
    )

    blocked = module.render_response("REQUESTED_ASSET_DELIVERY_REPLY", facts)
    assert blocked["status"] == "BLOCKED_ATTACHMENT_NOT_AUTHORIZED"
    assert blocked["attachment_count"] == 2

    rendered = module.render_response(
        "REQUESTED_ASSET_DELIVERY_REPLY",
        facts,
        explicit_attachment_request=True,
    )
    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["private_render"] is True
    assert rendered["public_safe"] is False
    assert rendered["attachment_count"] == 2
    assert rendered["attachment_policy"] == "EXPLICIT_REQUEST_ONLY"
    assert "Attachment inventory:" in rendered["body"]
    assert "Permitted use:" in rendered["body"]
    assert "do not imply endorsement" in rendered["body"]
    assert rendered["send_allowed_by_builder"] is False
    assert rendered["send_performed"] is False
    assert rendered["dispatch_binding"]["attachment_content_hashes_bound"] is False
    assert rendered["exact_action_time_approval_ready"] is False
    assert rendered["exact_action_time_approval_phrase"] is None
    assert rendered["exact_action_time_approval_blockers"] == [
        "ACTION_TIME_MAILBOX_RECEIPT_REQUIRED",
        "ATTACHMENT_CONTENT_HASHES_REQUIRED",
    ]
    with pytest.raises(
        module.OutreachRegistryError,
        match="DRAFT_BINDING_INCOMPLETE",
    ):
        module.build_action_time_authorization(
            rendered,
            mailbox_receipt(rendered["dispatch_binding"]),
            current_utc="2026-07-27T22:05:00Z",
        )

    content_hashes = {
        "lumencore-light.png": "A" * 64,
        "lumencore-dark.png": "B" * 64,
    }
    hash_bound = module.render_response(
        "REQUESTED_ASSET_DELIVERY_REPLY",
        facts,
        explicit_attachment_request=True,
        attachment_sha256s=content_hashes,
    )
    assert hash_bound["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert hash_bound["dispatch_binding"]["attachment_content_hashes_bound"] is True
    assert hash_bound["draft_binding_complete"] is True
    assert hash_bound["exact_action_time_approval_ready"] is False
    assert hash_bound["exact_action_time_approval_blockers"] == [
        "ACTION_TIME_MAILBOX_RECEIPT_REQUIRED"
    ]
    assert hash_bound["exact_action_time_approval_phrase"] is None
    assert "lumencore-light.png" not in json.dumps(
        hash_bound["dispatch_binding"], sort_keys=True
    )

    changed_hashes = dict(content_hashes)
    changed_hashes["lumencore-dark.png"] = "C" * 64
    changed = module.render_response(
        "REQUESTED_ASSET_DELIVERY_REPLY",
        facts,
        explicit_attachment_request=True,
        attachment_sha256s=changed_hashes,
    )
    assert changed["dispatch_binding"]["attachment_set_sha256"] != hash_bound[
        "dispatch_binding"
    ]["attachment_set_sha256"]
    assert changed["dispatch_binding"]["binding_sha256"] != hash_bound[
        "dispatch_binding"
    ]["binding_sha256"]

    with pytest.raises(
        module.OutreachRegistryError, match="ATTACHMENT_HASH_SET_MISMATCH"
    ):
        module.render_response(
            "REQUESTED_ASSET_DELIVERY_REPLY",
            facts,
            explicit_attachment_request=True,
            attachment_sha256s={"lumencore-light.png": "A" * 64},
        )

    with pytest.raises(
        module.OutreachRegistryError, match="ATTACHMENT_SHA256_MAP_INVALID"
    ):
        module.render_response(
            "REQUESTED_ASSET_DELIVERY_REPLY",
            facts,
            explicit_attachment_request=True,
            attachment_sha256s=[],
        )

    duplicate_names = copy.deepcopy(facts)
    duplicate_names["attachment_files"] = [
        "lumencore-light.png",
        "LUMENCORE-LIGHT.PNG",
    ]
    with pytest.raises(
        module.OutreachRegistryError, match="DUPLICATE_ATTACHMENT_NAME"
    ):
        module.render_response(
            "REQUESTED_ASSET_DELIVERY_REPLY",
            duplicate_names,
            explicit_attachment_request=True,
        )


def test_high_risk_inserted_claims_require_exact_evidence_receipts():
    module = load_module()
    facts = direct_investor_facts()
    facts["six_month_milestone"] = (
        "Deliver a best-in-class deployment that will save $10 million annually."
    )

    rendered = module.render_response(
        "DIRECT_INVESTOR_REVIEW_REQUEST",
        facts,
    )

    assert rendered["status"] == "BLOCKED_UNSUPPORTED_CLAIM_FACTS"
    assert rendered["subject"] is None
    assert rendered["body"] is None
    assert rendered["claim_risk_fields"] == ["six_month_milestone"]
    assert rendered["claim_risk_codes"] == [
        "UNSUPPORTED_ECONOMIC_OUTCOME",
        "UNSUPPORTED_SUPERLATIVE",
    ]
    assert rendered["invalid_claim_evidence_fields"] == {
        "six_month_milestone": "MISSING_EVIDENCE_RECEIPT"
    }


def test_explicitly_negated_claim_boundaries_do_not_trigger_claim_gate():
    module = load_module()
    facts = direct_investor_facts()
    facts["current_stage_disclosure"] = (
        "The work is not independently validated, and no realized savings "
        "or award is claimed."
    )

    rendered = module.render_response(
        "DIRECT_INVESTOR_REVIEW_REQUEST",
        facts,
    )

    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["claim_risk_fields"] == []
    assert rendered["claim_evidence_receipt_sha256s"] == {}


def test_exact_claim_receipt_rehashes_sources_and_fails_after_tampering(
    tmp_path, monkeypatch
):
    module = load_module()
    registry = module.validate_registry(module.read_registry(CONFIG))
    monkeypatch.setattr(module, "ROOT", tmp_path)

    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    source_path = evidence_dir / "official_result.txt"
    source_path.write_text(
        "Synthetic official result for receipt-binding test.\n",
        encoding="utf-8",
    )
    fact_value = "LumenCore received an award under the synthetic test record."
    risk_codes = module.claim_fact_risks(
        {"six_month_milestone": fact_value}
    )["six_month_milestone"]
    receipt = {
        "claim_allowed": True,
        "fact_field": "six_month_milestone",
        "fact_value_sha256": module.sha256_bytes(
            fact_value.encode("utf-8")
        ),
        "receipt_sha256": "",
        "review_basis": (
            "Synthetic test fixture exercising exact-value and source custody."
        ),
        "reviewed_utc": "2026-07-26T00:00:00Z",
        "risk_codes": risk_codes,
        "schema": module.CLAIM_EVIDENCE_RECEIPT_SCHEMA,
        "source_artifacts": [
            {
                "path": "evidence/official_result.txt",
                "sha256": module.sha256_bytes(source_path.read_bytes()),
            }
        ],
    }
    receipt["receipt_sha256"] = module.canonical_object_sha256(
        receipt, omit={"receipt_sha256"}
    )
    receipt_path = evidence_dir / "claim_receipt.json"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    facts = direct_investor_facts()
    facts["six_month_milestone"] = fact_value
    rendered = module.render_response(
        "DIRECT_INVESTOR_REVIEW_REQUEST",
        facts,
        claim_evidence_receipts={
            "six_month_milestone": "evidence/claim_receipt.json"
        },
        registry=registry,
    )

    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["claim_risk_fields"] == ["six_month_milestone"]
    assert rendered["claim_evidence_receipt_sha256s"] == {
        "six_month_milestone": receipt["receipt_sha256"]
    }

    revised_receipt = copy.deepcopy(receipt)
    revised_receipt["review_basis"] += " Second independent review pass."
    revised_receipt["receipt_sha256"] = module.canonical_object_sha256(
        revised_receipt, omit={"receipt_sha256"}
    )
    receipt_path.write_text(
        json.dumps(revised_receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    revised_render = module.render_response(
        "DIRECT_INVESTOR_REVIEW_REQUEST",
        facts,
        claim_evidence_receipts={
            "six_month_milestone": "evidence/claim_receipt.json"
        },
        registry=registry,
    )
    assert revised_render["claim_evidence_receipt_sha256s"] == {
        "six_month_milestone": revised_receipt["receipt_sha256"]
    }
    assert revised_render["dispatch_binding"]["binding_sha256"] != rendered[
        "dispatch_binding"
    ]["binding_sha256"]

    source_path.write_text("Tampered after review.\n", encoding="utf-8")
    blocked = module.render_response(
        "DIRECT_INVESTOR_REVIEW_REQUEST",
        facts,
        claim_evidence_receipts={
            "six_month_milestone": "evidence/claim_receipt.json"
        },
        registry=registry,
    )
    assert blocked["status"] == "BLOCKED_UNSUPPORTED_CLAIM_FACTS"
    assert blocked["invalid_claim_evidence_fields"] == {
        "six_month_milestone": "CLAIM_EVIDENCE_SOURCE_HASH_MISMATCH"
    }


def test_claim_evidence_template_is_deliberately_non_authorizing():
    module = load_module()

    with pytest.raises(
        module.OutreachRegistryError,
        match="CLAIM_EVIDENCE_NOT_APPROVED",
    ):
        module.validate_claim_evidence_receipt(
            "config/outreach_claim_evidence_receipt_template_v1.json",
            fact_field="six_month_milestone",
            fact_value="Synthetic claim",
            risk_codes=["UNSUPPORTED_AWARD_OR_CONTRACT"],
        )


def test_duplicate_json_keys_fail_closed_in_registry_and_evidence_receipts(
    tmp_path, monkeypatch
):
    module = load_module()
    duplicate_registry = tmp_path / "duplicate_registry.json"
    duplicate_registry.write_text(
        '{"schema":"first","schema":"second"}\n',
        encoding="utf-8",
    )
    with pytest.raises(
        module.OutreachRegistryError, match=r"DUPLICATE_JSON_KEY:schema"
    ):
        module.read_registry(duplicate_registry)

    monkeypatch.setattr(module, "ROOT", tmp_path)
    evidence_dir = tmp_path / "evidence"
    evidence_dir.mkdir()
    duplicate_receipt = evidence_dir / "duplicate_receipt.json"
    duplicate_receipt.write_text(
        '{"schema":"first","schema":"second"}\n',
        encoding="utf-8",
    )
    with pytest.raises(
        module.OutreachRegistryError, match=r"DUPLICATE_JSON_KEY:schema"
    ):
        module.validate_claim_evidence_receipt(
            "evidence/duplicate_receipt.json",
            fact_field="six_month_milestone",
            fact_value="Synthetic claim",
            risk_codes=["UNSUPPORTED_AWARD_OR_CONTRACT"],
        )


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
