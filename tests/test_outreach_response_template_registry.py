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


def test_registry_validates_and_covers_high_value_response_states():
    module = load_module()
    registry = module.validate_registry(module.read_registry())
    ids = {row["template_id"] for row in registry["templates"]}

    assert registry["schema"] == module.SCHEMA
    assert len(ids) == 16
    assert {
        "NO_DUPLICATE_MONITOR",
        "INITIAL_PARTNER_TEAMING_INQUIRY",
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


def test_initial_partner_teaming_template_is_bounded_and_no_attachment():
    module = load_module()
    facts = common_facts()
    facts.update(
        {
            "agency_name": "Synthetic Agency",
            "opportunity_name": "Synthetic Teaming Notice",
            "notice_type": "request for information",
            "opportunity_summary": "a bounded public-sector research response",
            "deadline_iso": "2026-07-30T17:00:00-04:00",
            "teaming_basis": "The notice permits a prime-led response.",
            "bounded_contribution": (
                "a replayable evidence protocol using public data"
            ),
            "qualification_boundary": (
                "LumenCore does not represent unverified past performance, "
                "certifications, clearances, or contract vehicles"
            ),
            "partner_fit_basis": (
                "the prospective partner publicly describes relevant prime experience"
            ),
            "requested_partner_role": (
                "prime-led qualification review and a bounded technical fit check"
            ),
            "authorization_request": (
                "the exact role, submission authority, and approved representations"
            ),
            "duplicate_review_disclosure": (
                "the full mailbox was checked and no sent copy or reply was found"
            ),
            "source_opportunity_url": "https://example.gov/opportunity",
            "public_company_url": "https://example.org",
            "public_proof_url": "https://example.org/proof",
        }
    )

    rendered = module.render_response(
        "INITIAL_PARTNER_TEAMING_INQUIRY",
        facts,
        current_utc="2026-07-28T04:18:00Z",
    )

    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["attachment_policy"] == "NONE"
    assert rendered["attachment_count"] == 0
    assert rendered["send_allowed_by_builder"] is False
    assert rendered["send_performed"] is False
    assert "nonbinding fit check only" in rendered["body"]
    assert "does not request pricing" in rendered["body"]
    assert "No attachment is included" in rendered["body"]
    assert "does not represent unverified past performance" in rendered["body"]


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
    assert payload["template_count"] == 16
    assert payload["controls"]["builder_can_send_email"] is False
    assert payload["controls"]["duplicate_send_fail_closed"] is True
    assert payload["quality_gate"]["status"] == "PASS"
    assert payload["quality_gate"]["all_templates_pass"] is True
    assert payload["quality_gate"]["template_count"] == 16
    assert payload["quality_gate"]["check_count"] == 192
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
        "MONITOR_NO_SEND": 1,
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
