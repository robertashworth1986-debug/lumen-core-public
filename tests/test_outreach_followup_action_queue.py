from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
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
LANL_DRAFT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "LANL_VISION_BOUNDED_FOLLOWUP_DRAFT_2026-07-23.md"
)
LANL_DRAFT_STATE = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "LANL_VISION_BOUNDED_FOLLOWUP_DRAFT_STATE_2026-07-23.json"
)
LANL_DISPATCH_BINDING = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "LANL_VISION_BOUNDED_FOLLOWUP_DISPATCH_BINDING_2026-07-23.json"
)
TEST_HUMAN_UNLOCK_TOKEN = "test-only-human-unlock-token-0123456789abcdef"


def load_module():
    spec = importlib.util.spec_from_file_location("outreach_followup_action_queue", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_live_lanl_draft_is_hash_bound_and_cannot_send():
    module = load_module()
    state = json.loads(LANL_DRAFT_STATE.read_text(encoding="utf-8"))
    binding = json.loads(LANL_DISPATCH_BINDING.read_text(encoding="utf-8"))
    markdown = LANL_DRAFT.read_text(encoding="utf-8")
    match = re.search(r"```text\n(.*?)\n```", markdown, re.DOTALL)

    assert match is not None
    assert hashlib.sha256(match.group(1).encode("utf-8")).hexdigest().upper() == (
        state["body_sha256"]
    )
    assert state["status"] == (
        "EXACT_DISPATCH_BOUND_ACTION_TIME_APPROVAL_REQUIRED_NOT_SENT"
    )
    assert state["template_id"] == "BOUNDED_REVIEW_FOLLOWUP"
    assert state["send_now"] is False
    assert state["send_allowed_by_builder"] is False
    assert state["action_time_human_approval_present"] is False
    assert state["recipient_route_bound"] is True
    assert state["dispatch_sha256"] == module.validate_followup_dispatch_binding(
        binding
    )
    assert binding["body_sha256"] == state["body_sha256"]
    assert binding["mailbox_check_receipt_sha256"] == state[
        "mailbox_check_receipt_sha256"
    ]
    assert binding["attachment_sha256s"] == []
    assert state["gmail_draft_created"] is False
    assert state["prior_proactive_send_count"] == 0
    assert state["max_proactive_sends"] == 1
    assert "No email has been sent or drafted in Gmail." in markdown


def mailbox_receipt(
    module,
    *,
    checked_utc: str = "2026-07-23T14:00:00Z",
    lane_id: str = "lanl_vision_licensing_followup",
    observed_message_count: int = 2,
    inbound_after_source_count: int = 0,
) -> dict:
    return module.build_mailbox_recheck_receipt(
        lane_id=lane_id,
        mailbox_rechecked_utc=checked_utc,
        thread_id_sha256="A" * 64,
        source_message_id_sha256="B" * 64,
        source_sent_utc="2026-07-16T18:50:16Z",
        latest_observed_message_utc="2026-07-16T18:50:16Z",
        observed_message_count=observed_message_count,
        inbound_after_source_count=inbound_after_source_count,
    )


def live_followup_fixture(module):
    receipt = mailbox_receipt(module)
    facts = {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "source_message_id": "synthetic-message-id",
        "source_subject": "Bounded technical package",
        "sent_date_local": "July 16, 2026",
        "package_name": "a bounded technical package",
        "review_scope": "a short Stage 0 diligence and evaluation-fit discussion",
        "requested_next_step": "a 20-minute technical fit check",
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
    }
    rendered = module.render_due_followup(
        "lanl_vision_licensing_followup",
        facts,
        as_of_utc="2026-07-23T14:00:30Z",
        mailbox_check_receipt=receipt,
    )
    binding = module.build_followup_dispatch_binding(
        "lanl_vision_licensing_followup",
        rendered,
        recipient_route={
            "to": ["reviewer@example.org"],
            "cc": ["observer@example.org"],
            "bcc": [],
        },
    )
    return receipt, rendered, binding


def test_followup_policy_config_is_complete_and_fail_closed():
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = payload["lane_policies"]

    assert payload["schema"] == "lumencore.outreach_followup_policies.v1"
    assert payload["version"] == 1
    assert len(rows) == 28
    assert len({row["lane_id"] for row in rows}) == 28
    assert payload["controls"] == {
        "action_time_human_review_required": True,
        "builder_can_send_email": False,
        "inbox_recheck_required_before_any_followup": True,
        "missing_lane_policy_fail_closed": True,
        "past_hold_does_not_authorize_send": True,
    }

    proactive = [row for row in rows if row["max_proactive_sends"]]
    assert len(proactive) == 3
    by_lane = {row["lane_id"]: row for row in proactive}
    assert by_lane["lanl_vision_licensing_followup"]["max_proactive_sends"] == 1
    assert by_lane["lanl_vision_licensing_followup"]["eligible_template_id"] == (
        "BOUNDED_REVIEW_FOLLOWUP"
    )
    assert by_lane["lanl_vision_licensing_followup"]["not_before_utc"] == (
        "2026-07-23T14:00:00Z"
    )
    assert by_lane["missionweave_dsip_proposal"]["max_proactive_sends"] == 1
    assert by_lane["missionweave_dsip_proposal"]["eligible_template_id"] == (
        "COMPONENT_INSTRUCTION_ESCALATION"
    )
    assert by_lane["missionweave_dsip_proposal"]["not_before_utc"] == (
        "2026-07-20T17:00:00Z"
    )
    assert by_lane["argos_emi_teaming_inquiry"]["mode"] == (
        "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE"
    )
    assert by_lane["argos_emi_teaming_inquiry"]["eligible_template_id"] == (
        "INITIAL_PARTNER_TEAMING_INQUIRY"
    )
    assert by_lane["argos_emi_teaming_inquiry"]["max_proactive_sends"] == 1
    assert by_lane["argos_emi_teaming_inquiry"]["deadline_utc"] == (
        "2026-07-30T21:00:00Z"
    )


def test_current_queue_is_deterministic_and_never_sends():
    module = load_module()
    actual = json.loads(JSON_OUT.read_text(encoding="utf-8"))
    expected = module.build_payload(actual["as_of_utc"])

    module.validate_payload(actual)
    assert actual == expected
    assert actual["as_of_utc"].endswith("Z")
    assert actual["status"] in {
        "NO_EXTERNAL_FOLLOWUP_DUE",
        "FOLLOWUP_RECHECK_DUE_HUMAN_REVIEW",
        "DEADLINE_ACTION_DUE_HUMAN_REVIEW",
    }
    assert actual["summary"]["lane_count"] == 28
    assert sum(actual["summary"]["action_state_counts"].values()) == 28
    assert actual["summary"]["draft_rendered_count"] == 0
    assert actual["summary"]["send_now_count"] == 0
    assert actual["summary"]["recorded_proactive_send_count"] == 3
    assert actual["summary"]["conflicting_gmail_draft_count"] == 1
    assert actual["summary"]["conflicting_gmail_draft_lane_count"] == 1
    assert actual["summary"]["external_send_allowed_without_human"] is False
    assert actual["controls"]["mailbox_recheck_max_age_seconds"] == 900
    assert actual["controls"]["mailbox_recheck_receipt_required"] is True
    assert actual["controls"]["exact_dispatch_binding_required_before_send"] is True
    assert actual["controls"]["single_use_action_time_approval_required"] is True
    assert actual["controls"]["private_human_unlock_bearer_token_required"] is True
    assert actual["controls"]["action_time_approval_max_age_seconds"] == 300
    assert actual["controls"][
        "proactive_send_count_derived_from_sealed_ledger"
    ] is True
    assert actual["controls"]["conflicting_gmail_drafts_fail_closed"] is True
    assert all(row["send_now"] is False for row in actual["actions"])
    assert all(row["draft_rendered"] is False for row in actual["actions"])
    assert sum(
        row["recorded_proactive_send_count"] for row in actual["actions"]
    ) == 3
    by_lane = {row["lane_id"]: row for row in actual["actions"]}
    argos = by_lane["argos_emi_teaming_inquiry"]
    nashville = by_lane["nashville_ec_takeoff_fall_2026"]
    terry = by_lane["terry_vynetic_followup"]
    assert nashville["action_state"] == "HUMAN_ACCOUNT_ACTION_OPEN"
    assert nashville["conflicting_gmail_draft_count"] == 0
    assert nashville["draft_quarantine_status"] is None
    assert nashville["send_now"] is False
    assert by_lane["tsa_industry_portal_capability"]["action_state"] == (
        "HUMAN_PORTAL_ACTION_OPEN"
    )
    assert by_lane["dla_amps_application_access"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )
    assert by_lane["login_gov_new_device_signin"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )
    assert terry["action_state"] == "MONITOR_INBOUND_ONLY"
    assert terry["conflicting_gmail_draft_count"] == 1
    assert terry["draft_quarantine_status"] == "QUARANTINED_NOT_SENDABLE"
    assert terry["send_now"] is False
    assert argos["action_state"] == "INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND"
    assert argos["inbox_recheck_required"] is False
    assert argos["eligible_template_id"] == "INITIAL_PARTNER_TEAMING_INQUIRY"
    assert argos["recorded_proactive_send_count"] == 1
    assert argos["deadline_utc"] == "2026-07-30T21:00:00Z"
    assert argos["send_now"] is False
    assert by_lane["missionweave_dsip_proposal"][
        "recorded_proactive_send_count"
    ] == 1
    assert by_lane["lanl_vision_licensing_followup"]["action_state"] == (
        "FOLLOWUP_LIMIT_REACHED_NO_SEND"
    )
    assert by_lane["lanl_vision_licensing_followup"][
        "recorded_proactive_send_count"
    ] == 1
    assert all(
        row["inbox_recheck_required"] is True
        for row in actual["actions"]
        if row["action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
    )
    assert len(actual["queue_sha256"]) == 64


def test_argos_deadline_lane_is_held_due_closed_and_send_limited():
    module = load_module()

    before = module.build_payload("2026-07-27T19:34:26Z")
    due = module.build_payload("2026-07-27T19:34:27Z")
    expired = module.build_payload("2026-07-30T21:00:00Z")

    before_row = {row["lane_id"]: row for row in before["actions"]}[
        "argos_emi_teaming_inquiry"
    ]
    due_row = {row["lane_id"]: row for row in due["actions"]}[
        "argos_emi_teaming_inquiry"
    ]
    expired_row = {row["lane_id"]: row for row in expired["actions"]}[
        "argos_emi_teaming_inquiry"
    ]

    assert before_row["action_state"] == "HELD_NO_SEND"
    assert before_row["hold_seconds_remaining"] == 1
    assert before_row["send_now"] is False
    assert due_row["action_state"] == "DEADLINE_ACTION_DUE_MAILBOX_RECHECK"
    assert due_row["inbox_recheck_required"] is True
    assert due_row["send_now"] is False
    assert expired_row["action_state"] == (
        "INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND"
    )
    assert expired_row["recorded_proactive_send_count"] == 1
    assert expired_row["send_now"] is False

    reconciliation = module.read_json(module.EMAIL_RECONCILIATION)
    argos_lane = next(
        row
        for row in reconciliation["lanes"]
        if row["lane_id"] == "argos_emi_teaming_inquiry"
    )
    exhausted = module.evaluate_lane(
        argos_lane,
        module.parse_aware_utc("2026-07-28T04:18:00Z"),
        {"argos_emi_teaming_inquiry": 1},
    )
    assert exhausted["action_state"] == "INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND"
    assert exhausted["recorded_proactive_send_count"] == 1
    assert exhausted["send_now"] is False


def test_argos_render_and_authorization_reject_at_deadline(monkeypatch):
    module = load_module()
    monkeypatch.setenv(module.HUMAN_UNLOCK_ENV_VAR, TEST_HUMAN_UNLOCK_TOKEN)
    original_read_json = module.read_json
    unsent_ledger = original_read_json(module.FOLLOWUP_SEND_LEDGER)
    unsent_ledger["receipts"] = [
        row
        for row in unsent_ledger["receipts"]
        if row["lane_id"] != "argos_emi_teaming_inquiry"
    ]
    unsent_ledger["ledger_sha256"] = module.canonical_object_sha256(
        unsent_ledger, omit={"ledger_sha256"}
    )

    def read_json_without_argos_send(path):
        if path == module.FOLLOWUP_SEND_LEDGER:
            return copy.deepcopy(unsent_ledger)
        return original_read_json(path)

    monkeypatch.setattr(module, "read_json", read_json_without_argos_send)
    check_utc = "2026-07-30T20:59:58Z"
    mailbox_check = mailbox_receipt(
        module,
        checked_utc=check_utc,
        lane_id="argos_emi_teaming_inquiry",
        observed_message_count=1,
    )
    facts = {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "agency_name": "Synthetic Agency",
        "opportunity_name": "Synthetic Teaming Notice",
        "notice_type": "request for information",
        "opportunity_summary": "a bounded public-sector research response",
        "deadline_iso": "2026-07-30T17:00:00-04:00",
        "teaming_basis": "The notice permits a prime-led response.",
        "bounded_contribution": "a replayable evidence protocol using public data",
        "qualification_boundary": (
            "No unverified past performance, certification, clearance, or vehicle "
            "is represented"
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
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
    }
    rendered = module.render_due_followup(
        "argos_emi_teaming_inquiry",
        facts,
        as_of_utc=check_utc,
        mailbox_check_receipt=mailbox_check,
    )
    binding = module.build_followup_dispatch_binding(
        "argos_emi_teaming_inquiry",
        rendered,
        recipient_route={
            "to": ["reviewer@example.org"],
            "cc": [],
            "bcc": [],
        },
    )
    approval = module.build_action_time_approval_receipt(
        binding,
        approved_utc="2026-07-30T20:59:59Z",
        approval_phrase=module.expected_followup_approval_phrase(binding),
        human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
    )

    with pytest.raises(ValueError, match="deadline has passed"):
        module.authorize_followup_dispatch(
            binding,
            approval,
            mailbox_check,
            as_of_utc="2026-07-30T21:00:00Z",
        )
    with pytest.raises(ValueError, match="not due"):
        module.render_due_followup(
            "argos_emi_teaming_inquiry",
            facts,
            as_of_utc="2026-07-30T21:00:00Z",
            mailbox_check_receipt=mailbox_check,
        )


def test_queue_integrity_hash_detects_public_output_tampering():
    module = load_module()
    payload = module.build_payload(module.REFERENCE_AS_OF_UTC)
    payload["summary"]["send_now_count"] = 1
    with pytest.raises(ValueError, match="autonomous send"):
        module.validate_payload(payload)

    payload = module.build_payload(module.REFERENCE_AS_OF_UTC)
    payload["claim_boundary"] += " altered"
    with pytest.raises(ValueError, match="integrity"):
        module.validate_payload(payload)


def test_default_build_uses_current_utc_instead_of_frozen_reference():
    module = load_module()
    before = datetime.now(timezone.utc)
    payload = module.build_payload()
    after = datetime.now(timezone.utc)
    observed = module.parse_aware_utc(payload["as_of_utc"])

    assert before <= observed <= after
    assert payload["as_of_utc"] != module.REFERENCE_AS_OF_UTC


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
    assert due_lanl["eligible_template_id"] == "BOUNDED_REVIEW_FOLLOWUP"
    assert due_lanl["draft_rendered"] is False
    assert due_lanl["send_now"] is False
    assert at_gate["status"] == "FOLLOWUP_RECHECK_DUE_HUMAN_REVIEW"
    assert at_gate["summary"]["due_for_mailbox_recheck_count"] == 1
    assert at_gate["summary"]["send_now_count"] == 0


def test_lanl_followup_render_requires_every_gate_and_never_sends():
    module = load_module()
    before_hold_receipt = mailbox_receipt(
        module, checked_utc="2026-07-23T13:59:30Z"
    )
    current_receipt = mailbox_receipt(module)
    facts = {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "source_message_id": "synthetic-message-id",
        "source_subject": "Bounded technical package",
        "sent_date_local": "July 16, 2026",
        "package_name": "a bounded technical package",
        "review_scope": "a short Stage 0 diligence and evaluation-fit discussion",
        "requested_next_step": "a 20-minute technical fit check",
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
    }

    with pytest.raises(ValueError, match="not due"):
        module.render_due_followup(
            "lanl_vision_licensing_followup",
            facts,
            as_of_utc="2026-07-23T13:59:59Z",
            mailbox_check_receipt=before_hold_receipt,
        )

    rendered = module.render_due_followup(
        "lanl_vision_licensing_followup",
        facts,
        as_of_utc="2026-07-23T14:00:30Z",
        mailbox_check_receipt=current_receipt,
    )
    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["template_id"] == "BOUNDED_REVIEW_FOLLOWUP"
    assert rendered["queue_action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
    assert rendered["attachment_policy"] == "NONE"
    assert rendered["send_allowed_by_builder"] is False
    assert rendered["send_performed"] is False
    assert rendered["mailbox_rechecked"] is True
    assert rendered["mailbox_rechecked_utc"] == "2026-07-23T14:00:00Z"
    assert rendered["mailbox_recheck_age_seconds"] == 30
    assert rendered["mailbox_check_receipt_sha256"] == current_receipt[
        "receipt_sha256"
    ]
    assert rendered["no_reply_confirmed"] is True
    assert rendered["prior_followup_count"] == 0
    assert "following up once" in rendered["body"]
    assert "does not assert receipt, endorsement, independent validation" in (
        rendered["body"]
    )
    assert "will not send another follow-up" in rendered["body"]


@pytest.mark.parametrize(
    ("mailbox_rechecked_utc", "receipt", "error"),
    (
        ("2026-07-23T13:44:59Z", "0123456789ABCDEF" * 4, "stale"),
        ("2026-07-23T14:00:01Z", "0123456789ABCDEF" * 4, "future"),
        ("2026-07-23T14:00:00Z", "not-a-hash", "receipt SHA-256"),
    ),
)
def test_followup_render_rejects_unreceipted_or_nonfresh_mailbox_checks(
    mailbox_rechecked_utc, receipt, error
):
    module = load_module()
    check_receipt = mailbox_receipt(module, checked_utc=mailbox_rechecked_utc)
    if receipt == "not-a-hash":
        check_receipt["receipt_sha256"] = receipt
    facts = {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "source_message_id": "synthetic-message-id",
        "source_subject": "Bounded technical package",
        "sent_date_local": "July 16, 2026",
        "package_name": "a bounded technical package",
        "review_scope": "a short Stage 0 diligence and evaluation-fit discussion",
        "requested_next_step": "a 20-minute technical fit check",
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
    }

    with pytest.raises(ValueError, match=error):
        module.render_due_followup(
            "lanl_vision_licensing_followup",
            facts,
            as_of_utc="2026-07-23T14:00:00Z",
            mailbox_check_receipt=check_receipt,
        )


def test_followup_render_rejects_mailbox_check_before_hold_boundary():
    module = load_module()
    check_receipt = mailbox_receipt(
        module, checked_utc="2026-07-23T13:59:59Z"
    )
    facts = {
        "recipient_name": "Reviewer",
        "recipient_email": "reviewer@example.org",
        "source_message_id": "synthetic-message-id",
        "source_subject": "Bounded technical package",
        "sent_date_local": "July 16, 2026",
        "package_name": "a bounded technical package",
        "review_scope": "a short Stage 0 diligence and evaluation-fit discussion",
        "requested_next_step": "a 20-minute technical fit check",
        "sender_name": "Founder",
        "sender_title": "Founder / Systems Architect",
        "organization_name": "LumenCore",
    }

    with pytest.raises(ValueError, match="predates the follow-up hold boundary"):
        module.render_due_followup(
            "lanl_vision_licensing_followup",
            facts,
            as_of_utc="2026-07-23T14:00:00Z",
            mailbox_check_receipt=check_receipt,
        )


@pytest.mark.parametrize(
    ("mutator", "error"),
    (
        (lambda receipt: receipt.update(full_thread_read=False), "full-thread"),
        (lambda receipt: receipt.update(thread_truncated=True), "truncated"),
        (
            lambda receipt: receipt.update(
                inbound_after_source_count=1, no_reply_confirmed=False
            ),
            "does not confirm no reply",
        ),
        (lambda receipt: receipt.update(thread_id="private-thread-id"), "fields"),
    ),
)
def test_mailbox_recheck_receipt_fails_closed_on_unsafe_evidence(mutator, error):
    module = load_module()
    receipt = mailbox_receipt(module)
    mutator(receipt)
    receipt["receipt_sha256"] = module.canonical_object_sha256(
        receipt, omit={"receipt_sha256"}
    )

    with pytest.raises(ValueError, match=error):
        module.validate_mailbox_recheck_receipt(
            receipt, expected_lane_id="lanl_vision_licensing_followup"
        )


def test_mailbox_recheck_receipt_detects_tampering_and_lane_mismatch():
    module = load_module()
    receipt = mailbox_receipt(module)
    receipt["observed_message_count"] = 3

    with pytest.raises(ValueError, match="integrity"):
        module.validate_mailbox_recheck_receipt(
            receipt, expected_lane_id="lanl_vision_licensing_followup"
        )
    with pytest.raises(ValueError, match="lane mismatch"):
        module.validate_mailbox_recheck_receipt(
            mailbox_receipt(module), expected_lane_id="another_lane"
        )


def test_action_time_approval_binds_exact_dispatch_and_remains_send_inert(
    monkeypatch,
):
    module = load_module()
    monkeypatch.setenv(module.HUMAN_UNLOCK_ENV_VAR, TEST_HUMAN_UNLOCK_TOKEN)
    mailbox_check, rendered, binding = live_followup_fixture(module)
    phrase = module.expected_followup_approval_phrase(binding)
    assert phrase.endswith(binding["dispatch_sha256"][:12])
    assert "LANL_VISION_LICENSING_FOLLOWUP" in phrase
    assert set(binding) == module.FOLLOWUP_DISPATCH_BINDING_FIELDS
    serialized_binding = json.dumps(binding, sort_keys=True).lower()
    assert "reviewer@example.org" not in serialized_binding
    assert rendered["subject"].lower() not in serialized_binding
    assert rendered["body"].lower() not in serialized_binding

    approval = module.build_action_time_approval_receipt(
        binding,
        approved_utc="2026-07-23T14:00:31Z",
        approval_phrase=phrase,
        human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
    )
    assert set(approval) == module.ACTION_TIME_APPROVAL_FIELDS
    assert TEST_HUMAN_UNLOCK_TOKEN not in json.dumps(approval, sort_keys=True)
    authorization = module.authorize_followup_dispatch(
        binding,
        approval,
        mailbox_check,
        as_of_utc="2026-07-23T14:00:32Z",
    )
    assert authorization["status"] == "READY_FOR_EXPLICIT_GMAIL_SEND"
    assert authorization["single_use"] is True
    assert authorization["send_allowed_by_builder"] is False
    assert authorization["send_performed"] is False

    send_receipt = module.build_followup_send_receipt(
        authorization,
        sent_message_receipt_sha256="C" * 64,
        sent_utc="2026-07-23T14:00:33Z",
    )
    assert module.ACTION_BOUND_SEND_RECEIPT_FIELDS.issubset(send_receipt)
    assert not module.PRIVATE_SEND_RECEIPT_KEYS.intersection(send_receipt)


def test_action_time_approval_rejects_changed_draft_route_and_wrong_phrase(
    monkeypatch,
):
    module = load_module()
    monkeypatch.setenv(module.HUMAN_UNLOCK_ENV_VAR, TEST_HUMAN_UNLOCK_TOKEN)
    _, rendered, binding = live_followup_fixture(module)
    phrase = module.expected_followup_approval_phrase(binding)
    approval = module.build_action_time_approval_receipt(
        binding,
        approved_utc="2026-07-23T14:00:31Z",
        approval_phrase=phrase,
        human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
    )

    changed_render = copy.deepcopy(rendered)
    changed_render["body"] += "\nChanged after review."
    changed_binding = module.build_followup_dispatch_binding(
        "lanl_vision_licensing_followup",
        changed_render,
        recipient_route={
            "to": ["reviewer@example.org"],
            "cc": ["observer@example.org"],
            "bcc": [],
        },
    )
    with pytest.raises(ValueError, match="dispatch_sha256 mismatch"):
        module.validate_action_time_approval_receipt(
            approval,
            dispatch_binding=changed_binding,
            as_of_utc="2026-07-23T14:00:32Z",
        )

    changed_route = module.build_followup_dispatch_binding(
        "lanl_vision_licensing_followup",
        rendered,
        recipient_route={
            "to": ["another-reviewer@example.org"],
            "cc": ["observer@example.org"],
            "bcc": [],
        },
    )
    with pytest.raises(ValueError, match="dispatch_sha256 mismatch"):
        module.validate_action_time_approval_receipt(
            approval,
            dispatch_binding=changed_route,
            as_of_utc="2026-07-23T14:00:32Z",
        )
    with pytest.raises(ValueError, match="phrase"):
        module.build_action_time_approval_receipt(
            binding,
            approved_utc="2026-07-23T14:00:31Z",
            approval_phrase="APPROVE LANL SEND",
            human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
        )


def test_action_time_approval_requires_private_human_unlock(monkeypatch):
    module = load_module()
    _, _, binding = live_followup_fixture(module)
    phrase = module.expected_followup_approval_phrase(binding)

    monkeypatch.delenv(module.HUMAN_UNLOCK_ENV_VAR, raising=False)
    with pytest.raises(ValueError, match=module.HUMAN_UNLOCK_ENV_VAR):
        module.build_action_time_approval_receipt(
            binding,
            approved_utc="2026-07-23T14:00:31Z",
            approval_phrase=phrase,
            human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
        )

    monkeypatch.setenv(module.HUMAN_UNLOCK_ENV_VAR, TEST_HUMAN_UNLOCK_TOKEN)
    with pytest.raises(ValueError, match="does not match"):
        module.build_action_time_approval_receipt(
            binding,
            approved_utc="2026-07-23T14:00:31Z",
            approval_phrase=phrase,
            human_unlock_token="wrong-test-token-with-sufficient-length-0000",
        )

    approval = module.build_action_time_approval_receipt(
        binding,
        approved_utc="2026-07-23T14:00:31Z",
        approval_phrase=phrase,
        human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
    )
    approval["human_unlock_proof_sha256"] = "E" * 64
    approval["approval_receipt_sha256"] = module.canonical_object_sha256(
        approval, omit={"approval_receipt_sha256"}
    )
    with pytest.raises(ValueError, match="HumanUnlock proof"):
        module.validate_action_time_approval_receipt(
            approval,
            dispatch_binding=binding,
            as_of_utc="2026-07-23T14:00:32Z",
        )


def test_action_time_approval_rejects_stale_wrong_lane_and_replay(monkeypatch):
    module = load_module()
    monkeypatch.setenv(module.HUMAN_UNLOCK_ENV_VAR, TEST_HUMAN_UNLOCK_TOKEN)
    mailbox_check, _, binding = live_followup_fixture(module)
    approval = module.build_action_time_approval_receipt(
        binding,
        approved_utc="2026-07-23T14:00:31Z",
        approval_phrase=module.expected_followup_approval_phrase(binding),
        human_unlock_token=TEST_HUMAN_UNLOCK_TOKEN,
    )
    with pytest.raises(ValueError, match="stale"):
        module.validate_action_time_approval_receipt(
            approval,
            dispatch_binding=binding,
            as_of_utc="2026-07-23T14:05:32Z",
        )

    wrong_lane = copy.deepcopy(approval)
    wrong_lane["lane_id"] = "missionweave_dsip_proposal"
    wrong_lane["approval_receipt_sha256"] = module.canonical_object_sha256(
        wrong_lane, omit={"approval_receipt_sha256"}
    )
    with pytest.raises(ValueError, match="lane_id mismatch"):
        module.validate_action_time_approval_receipt(
            wrong_lane,
            dispatch_binding=binding,
            as_of_utc="2026-07-23T14:00:32Z",
        )

    authorization = module.authorize_followup_dispatch(
        binding,
        approval,
        mailbox_check,
        as_of_utc="2026-07-23T14:00:32Z",
    )
    sent = module.build_followup_send_receipt(
        authorization,
        sent_message_receipt_sha256="D" * 64,
        sent_utc="2026-07-23T14:00:33Z",
    )
    ledger = module.read_json(module.FOLLOWUP_SEND_LEDGER)
    ledger["receipts"] = [
        row
        for row in ledger["receipts"]
        if row["lane_id"] != "lanl_vision_licensing_followup"
    ]
    ledger["receipts"].append(sent)
    ledger["receipts"].sort(key=lambda row: row["sent_utc"])
    ledger["ledger_sha256"] = module.canonical_object_sha256(
        ledger, omit={"ledger_sha256"}
    )
    with pytest.raises(ValueError, match="already been consumed|already been sent"):
        module.authorize_followup_dispatch(
            binding,
            approval,
            mailbox_check,
            as_of_utc="2026-07-23T14:00:34Z",
            send_ledger=ledger,
        )


def test_recipient_route_rejects_duplicates_and_invalid_shapes():
    module = load_module()
    _, rendered, _ = live_followup_fixture(module)
    with pytest.raises(ValueError, match="duplicate address"):
        module.build_followup_dispatch_binding(
            "lanl_vision_licensing_followup",
            rendered,
            recipient_route={
                "to": ["reviewer@example.org"],
                "cc": ["reviewer@example.org"],
                "bcc": [],
            },
        )
    with pytest.raises(ValueError, match="exactly"):
        module.build_followup_dispatch_binding(
            "lanl_vision_licensing_followup",
            rendered,
            recipient_route={"to": ["reviewer@example.org"]},
        )


def test_send_ledger_requires_action_bindings_after_control_effective_time():
    module = load_module()
    ledger = module.read_json(module.FOLLOWUP_SEND_LEDGER)
    policies_payload = module.read_json(module.FOLLOWUP_POLICY_CONFIG)
    policies = {
        row["lane_id"]: row for row in policies_payload["lane_policies"]
    }
    registry = module.read_json(module.RESPONSE_TEMPLATE_REGISTRY)
    template_ids = {row["template_id"] for row in registry["templates"]}
    ledger["receipts"] = [
        row
        for row in ledger["receipts"]
        if row["lane_id"] != "lanl_vision_licensing_followup"
    ]
    ledger["receipts"].append(
        {
            "delivery_state": "SENT",
            "lane_id": "lanl_vision_licensing_followup",
            "sent_message_receipt_sha256": "E" * 64,
            "sent_utc": "2026-07-23T18:26:48Z",
            "template_id": "BOUNDED_REVIEW_FOLLOWUP",
        }
    )
    ledger["receipts"].sort(key=lambda row: row["sent_utc"])
    ledger["ledger_sha256"] = module.canonical_object_sha256(
        ledger, omit={"ledger_sha256"}
    )
    with pytest.raises(ValueError, match="missing action-time bindings"):
        module.validate_followup_send_ledger(
            ledger,
            policies,
            template_ids,
            as_of=module.parse_aware_utc("2026-07-23T18:27:00Z"),
        )


def test_observed_unbound_send_consumes_allowance_without_claiming_authorization():
    module = load_module()
    ledger = module.read_json(module.FOLLOWUP_SEND_LEDGER)
    policies_payload = module.read_json(module.FOLLOWUP_POLICY_CONFIG)
    policies = {
        row["lane_id"]: row for row in policies_payload["lane_policies"]
    }
    registry = module.read_json(module.RESPONSE_TEMPLATE_REGISTRY)
    template_ids = {row["template_id"] for row in registry["templates"]}

    receipt = next(
        row
        for row in ledger["receipts"]
        if row["lane_id"] == "lanl_vision_licensing_followup"
    )
    assert receipt["governance_exception"] == "UNBOUND_SEND_OBSERVED"
    assert receipt["authorization_verified"] is False

    counts, _ = module.validate_followup_send_ledger(
        ledger,
        policies,
        template_ids,
        as_of=module.parse_aware_utc("2026-07-27T19:00:00Z"),
    )
    assert counts["lanl_vision_licensing_followup"] == 1

    tampered = copy.deepcopy(ledger)
    tampered_receipt = next(
        row
        for row in tampered["receipts"]
        if row["lane_id"] == "lanl_vision_licensing_followup"
    )
    tampered_receipt["authorization_verified"] = True
    tampered["ledger_sha256"] = module.canonical_object_sha256(
        tampered, omit={"ledger_sha256"}
    )
    with pytest.raises(ValueError, match="invalid authorization data"):
        module.validate_followup_send_ledger(
            tampered,
            policies,
            template_ids,
            as_of=module.parse_aware_utc("2026-07-27T19:00:00Z"),
        )


def test_sealed_send_ledger_derives_count_and_exhausts_bounded_lane():
    module = load_module()
    ledger = module.read_json(module.FOLLOWUP_SEND_LEDGER)
    policies_payload = module.read_json(module.FOLLOWUP_POLICY_CONFIG)
    policies = {
        row["lane_id"]: row for row in policies_payload["lane_policies"]
    }
    registry = module.read_json(module.RESPONSE_TEMPLATE_REGISTRY)
    template_ids = {row["template_id"] for row in registry["templates"]}
    as_of = module.parse_aware_utc("2026-07-23T15:00:00Z")

    receipt = {
        "delivery_state": "SENT",
        "lane_id": "lanl_vision_licensing_followup",
        "sent_message_receipt_sha256": "A" * 64,
        "sent_utc": "2026-07-23T14:30:00Z",
        "template_id": "BOUNDED_REVIEW_FOLLOWUP",
    }
    ledger["receipts"] = [receipt]
    ledger["ledger_sha256"] = module.canonical_object_sha256(
        ledger, omit={"ledger_sha256"}
    )
    counts, digests = module.validate_followup_send_ledger(
        ledger, policies, template_ids, as_of=as_of
    )

    assert counts["lanl_vision_licensing_followup"] == 1
    assert len(digests["lanl_vision_licensing_followup"][0]) == 64
    reconciliation = module.read_json(module.EMAIL_RECONCILIATION)
    lane = next(
        row
        for row in reconciliation["lanes"]
        if row["lane_id"] == "lanl_vision_licensing_followup"
    )
    action = module.evaluate_lane(lane, as_of, counts)
    assert action["action_state"] == "FOLLOWUP_LIMIT_REACHED_NO_SEND"
    assert action["recorded_proactive_send_count"] == 1
    assert action["send_now"] is False
    assert "allowance is exhausted" in action["next_action"]


def test_send_ledger_tamper_duplicate_and_private_material_fail_closed():
    module = load_module()
    base = module.read_json(module.FOLLOWUP_SEND_LEDGER)
    policies_payload = module.read_json(module.FOLLOWUP_POLICY_CONFIG)
    policies = {
        row["lane_id"]: row for row in policies_payload["lane_policies"]
    }
    registry = module.read_json(module.RESPONSE_TEMPLATE_REGISTRY)
    template_ids = {row["template_id"] for row in registry["templates"]}
    as_of = module.parse_aware_utc("2026-07-23T15:00:00Z")
    receipt = {
        "delivery_state": "SENT",
        "lane_id": "lanl_vision_licensing_followup",
        "sent_message_receipt_sha256": "B" * 64,
        "sent_utc": "2026-07-23T14:30:00Z",
        "template_id": "BOUNDED_REVIEW_FOLLOWUP",
    }

    tampered = copy.deepcopy(base)
    tampered["receipts"] = [receipt]
    with pytest.raises(ValueError, match="integrity"):
        module.validate_followup_send_ledger(
            tampered, policies, template_ids, as_of=as_of
        )

    duplicate = copy.deepcopy(base)
    duplicate["receipts"] = [receipt, dict(receipt)]
    duplicate["ledger_sha256"] = module.canonical_object_sha256(
        duplicate, omit={"ledger_sha256"}
    )
    with pytest.raises(ValueError, match="duplicate receipt"):
        module.validate_followup_send_ledger(
            duplicate, policies, template_ids, as_of=as_of
        )

    private = copy.deepcopy(base)
    private_receipt = dict(receipt, message_id="private-message-id")
    private["receipts"] = [private_receipt]
    private["ledger_sha256"] = module.canonical_object_sha256(
        private, omit={"ledger_sha256"}
    )
    with pytest.raises(ValueError, match="private message material"):
        module.validate_followup_send_ledger(
            private, policies, template_ids, as_of=as_of
        )


def test_recorded_missionweave_followup_exhausts_lane_before_and_after_gate():
    module = load_module()
    before = module.build_payload("2026-07-20T16:59:59Z")
    due = module.build_payload("2026-07-20T17:00:00Z")
    before_row = {row["lane_id"]: row for row in before["actions"]}[
        "missionweave_dsip_proposal"
    ]
    due_row = {row["lane_id"]: row for row in due["actions"]}[
        "missionweave_dsip_proposal"
    ]

    for row in (before_row, due_row):
        assert row["action_state"] == "FOLLOWUP_LIMIT_REACHED_NO_SEND"
        assert row["recorded_proactive_send_count"] == 1
        assert row["draft_rendered"] is False
        assert row["send_now"] is False


def test_modes_route_closed_inbound_portal_private_and_account_work_separately():
    module = load_module()
    rows = {
        row["lane_id"]: row
        for row in module.build_payload(module.REFERENCE_AS_OF_UTC)["actions"]
    }

    assert rows["fhwa_tsmo_qualified_partner_outreach"]["action_state"] == (
        "CLOSED_NO_ACTION"
    )
    assert rows["epri_open_power_ai_mou"]["action_state"] == (
        "MONITOR_INBOUND_ONLY"
    )
    assert rows["epri_open_power_ai_mou"]["source_state"] == (
        "LOGO_PAIR_SENT_ONCE_POST_SEND_VERIFIED_DO_NOT_RESEND"
    )
    assert "Do not resend the logo pair." in rows[
        "epri_open_power_ai_mou"
    ]["next_action"]
    assert rows["lvlup_warm_investor_intro"]["action_state"] == (
        "MONITOR_INBOUND_ONLY"
    )
    assert rows["lvlup_application_review_status"]["action_state"] == (
        "MONITOR_INBOUND_ONLY"
    )
    assert rows["third_sphere_seedstrap_direct_review"]["action_state"] == (
        "MONITOR_INBOUND_ONLY"
    )
    assert rows["uspto_document_services_copy_route"]["action_state"] == (
        "HUMAN_PORTAL_ACTION_OPEN"
    )
    assert rows["nccu_ip_clinic_intake"]["action_state"] == "CLOSED_NO_ACTION"
    assert rows["missionweave_dsip_proposal"]["action_state"] == "HELD_NO_SEND"
    assert rows["openai_build_week_internal_handoff"]["action_state"] == (
        "PRIVATE_RECONCILIATION_OPEN"
    )
    assert rows["sam_public_credential_rotation"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )
    assert rows["nashville_ec_takeoff_fall_2026"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )
    assert rows["tsa_industry_portal_capability"]["action_state"] == (
        "HUMAN_PORTAL_ACTION_OPEN"
    )
    assert rows["dla_amps_application_access"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )
    assert rows["login_gov_new_device_signin"]["action_state"] == (
        "HUMAN_ACCOUNT_ACTION_OPEN"
    )


def test_missing_or_drifted_lane_policy_fails_closed():
    module = load_module()
    reconciliation = module.read_json(module.EMAIL_RECONCILIATION)
    registry = module.read_json(module.RESPONSE_TEMPLATE_REGISTRY)
    policies = module.read_json(module.FOLLOWUP_POLICY_CONFIG)
    send_ledger = module.read_json(module.FOLLOWUP_SEND_LEDGER)
    as_of = module.parse_aware_utc(module.REFERENCE_AS_OF_UTC)

    missing = copy.deepcopy(policies)
    missing["lane_policies"] = missing["lane_policies"][:-1]
    with pytest.raises(ValueError, match="coverage"):
        module.validate_sources(
            reconciliation, registry, missing, send_ledger, as_of=as_of
        )

    drifted = copy.deepcopy(reconciliation)
    drifted["lanes"][0]["follow_up_policy"]["mode"] = "CLOSED"
    with pytest.raises(ValueError, match="policy drift"):
        module.validate_sources(
            drifted, registry, policies, send_ledger, as_of=as_of
        )

    stale_evidence = copy.deepcopy(reconciliation)
    source_id = next(iter(stale_evidence["source_evidence"]))
    stale_evidence["source_evidence"][source_id]["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="Source evidence hash drift"):
        module.validate_sources(
            stale_evidence, registry, policies, send_ledger, as_of=as_of
        )


def test_public_outputs_exclude_mailbox_and_secret_material():
    module = load_module()
    payload = module.build_payload(module.REFERENCE_AS_OF_UTC)
    rendered = json.dumps(payload, sort_keys=True) + "\n" + MD_OUT.read_text(
        encoding="utf-8"
    )
    lowered = rendered.lower()

    assert "hold expiration or open deadline requires a fresh mailbox check" in lowered
    assert "prior proactive sends are derived from a sealed receipt ledger" in lowered
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
