from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
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
    assert len(rows) == 17
    assert len({row["lane_id"] for row in rows}) == 17
    assert payload["controls"] == {
        "action_time_human_review_required": True,
        "builder_can_send_email": False,
        "inbox_recheck_required_before_any_followup": True,
        "missing_lane_policy_fail_closed": True,
        "past_hold_does_not_authorize_send": True,
    }

    proactive = [row for row in rows if row["max_proactive_sends"]]
    assert len(proactive) == 2
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
        "ROUTING_INTEGRITY_EXCEPTION_NO_SEND",
    }
    assert actual["summary"]["lane_count"] == 17
    assert sum(actual["summary"]["action_state_counts"].values()) == 17
    assert actual["summary"]["draft_rendered_count"] == 0
    assert actual["summary"]["send_now_count"] == 0
    assert actual["summary"]["recorded_proactive_send_count"] == 1
    assert actual["summary"]["routing_integrity_exception_count"] == 1
    assert actual["summary"]["external_send_allowed_without_human"] is False
    assert actual["controls"]["mailbox_recheck_max_age_seconds"] == 900
    assert actual["controls"]["mailbox_recheck_receipt_required"] is True
    assert actual["controls"][
        "proactive_send_count_derived_from_sealed_ledger"
    ] is True
    assert actual["controls"][
        "historical_send_timing_exceptions_fail_closed"
    ] is True
    assert all(row["send_now"] is False for row in actual["actions"])
    assert all(row["draft_rendered"] is False for row in actual["actions"])
    assert sum(
        row["recorded_proactive_send_count"] for row in actual["actions"]
    ) == 1
    by_lane = {row["lane_id"]: row for row in actual["actions"]}
    assert by_lane["missionweave_dsip_proposal"][
        "recorded_proactive_send_count"
    ] == 1
    assert all(
        row["inbox_recheck_required"] is True
        for row in actual["actions"]
        if row["action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
    )
    assert len(actual["queue_sha256"]) == 64


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
    assert at_gate["status"] == "ROUTING_INTEGRITY_EXCEPTION_NO_SEND"
    assert at_gate["summary"]["due_for_mailbox_recheck_count"] == 1
    assert at_gate["summary"]["routing_integrity_exception_count"] == 1
    assert at_gate["summary"]["send_now_count"] == 0


def test_lanl_followup_render_requires_every_gate_and_never_sends():
    module = load_module()
    mailbox_receipt = "0123456789ABCDEF" * 4
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
            mailbox_rechecked=True,
            mailbox_rechecked_utc="2026-07-23T13:59:30Z",
            mailbox_check_receipt_sha256=mailbox_receipt,
            no_reply_confirmed=True,
        )

    for mailbox_rechecked, no_reply_confirmed in ((False, True), (True, False)):
        with pytest.raises(ValueError, match="Fresh mailbox recheck"):
            module.render_due_followup(
                "lanl_vision_licensing_followup",
                facts,
                as_of_utc="2026-07-23T14:00:00Z",
                mailbox_rechecked=mailbox_rechecked,
                mailbox_rechecked_utc="2026-07-23T13:59:30Z",
                mailbox_check_receipt_sha256=mailbox_receipt,
                no_reply_confirmed=no_reply_confirmed,
            )

    rendered = module.render_due_followup(
        "lanl_vision_licensing_followup",
        facts,
        as_of_utc="2026-07-23T14:00:00Z",
        mailbox_rechecked=True,
        mailbox_rechecked_utc="2026-07-23T13:59:30Z",
        mailbox_check_receipt_sha256=mailbox_receipt,
        no_reply_confirmed=True,
    )
    assert rendered["status"] == "READY_FOR_PRIVATE_ACTION_TIME_REVIEW"
    assert rendered["template_id"] == "BOUNDED_REVIEW_FOLLOWUP"
    assert rendered["queue_action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
    assert rendered["attachment_policy"] == "NONE"
    assert rendered["send_allowed_by_builder"] is False
    assert rendered["send_performed"] is False
    assert rendered["mailbox_rechecked"] is True
    assert rendered["mailbox_rechecked_utc"] == "2026-07-23T13:59:30Z"
    assert rendered["mailbox_recheck_age_seconds"] == 30
    assert rendered["mailbox_check_receipt_sha256"] == mailbox_receipt
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
        ("2026-07-23T13:59:30Z", "not-a-hash", "receipt SHA-256"),
    ),
)
def test_followup_render_rejects_unreceipted_or_nonfresh_mailbox_checks(
    mailbox_rechecked_utc, receipt, error
):
    module = load_module()
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
            mailbox_rechecked=True,
            mailbox_rechecked_utc=mailbox_rechecked_utc,
            mailbox_check_receipt_sha256=receipt,
            no_reply_confirmed=True,
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
    counts, digests, timing_exceptions = module.validate_followup_send_ledger(
        ledger, policies, template_ids, as_of=as_of
    )

    assert counts["lanl_vision_licensing_followup"] == 1
    assert len(digests["lanl_vision_licensing_followup"][0]) == 64
    assert timing_exceptions == []
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

    assert before["status"] == "ROUTING_INTEGRITY_EXCEPTION_NO_SEND"
    assert due["status"] == "ROUTING_INTEGRITY_EXCEPTION_NO_SEND"
    assert before["routing_integrity_exceptions"] == [
        {
            "exception": "SENT_BEFORE_CONFIGURED_HOLD",
            "lane_id": "missionweave_dsip_proposal",
            "not_before_utc": "2026-07-20T17:00:00Z",
            "sent_utc": "2026-07-20T15:36:02Z",
            "sent_message_receipt_sha256": (
                "6DC9E2D4DAD3D146AEB6A397FBED865B5B9C8A83AB66929F3F2D47A6153F8A16"
            ),
        }
    ]


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
    assert rows["openai_build_week_prooflock"]["action_state"] == (
        "MONITOR_INBOUND_ONLY"
    )
    assert rows["missionweave_dsip_proposal"]["action_state"] == "HELD_NO_SEND"
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
    with pytest.raises(ValueError, match="Source evidence byte/hash drift"):
        module.validate_sources(
            stale_evidence, registry, policies, send_ledger, as_of=as_of
        )


def test_source_identity_accepts_only_eol_equivalent_committed_bytes():
    module = load_module()
    status = module.source_status(module.FOLLOWUP_POLICY_CONFIG)

    assert status["identity_source"] == "COMMITTED_GIT_BLOB"
    assert isinstance(status["worktree_eol_differs_from_git_blob"], bool)
    assert len(status["sha256"]) == 64


def test_source_status_uses_committed_bytes_without_checkout_eol_drift(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    source = tmp_path / "source.txt"
    source.write_bytes(b"alpha\r\nbeta\r\n")
    committed = b"alpha\nbeta\n"
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "read_head_blob", lambda _path: committed)

    status = module.source_status(source)

    assert status["identity_source"] == "COMMITTED_GIT_BLOB"
    assert status["bytes"] == len(committed)
    assert status["sha256"] == hashlib.sha256(committed).hexdigest().upper()
    assert status["worktree_eol_differs_from_git_blob"] is False


def test_public_outputs_exclude_mailbox_and_secret_material():
    module = load_module()
    payload = module.build_payload(module.REFERENCE_AS_OF_UTC)
    rendered = json.dumps(payload, sort_keys=True) + "\n" + MD_OUT.read_text(
        encoding="utf-8"
    )
    lowered = rendered.lower()

    assert "hold expiration requires a fresh mailbox check" in lowered
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
