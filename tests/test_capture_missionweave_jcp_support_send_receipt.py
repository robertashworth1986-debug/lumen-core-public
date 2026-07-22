from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "CAPTURE_MISSIONWEAVE_JCP_SUPPORT_SEND_RECEIPT.py"
ESCALATION = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_JCP_SUPPORT_ESCALATION_2026-07-22.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "capture_missionweave_jcp_support_send_receipt", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def escalation():
    return json.loads(ESCALATION.read_text(encoding="utf-8"))


def private_observation():
    packet = escalation()
    draft = packet["draft"]
    return {
        "action_time_human_unlock_confirmed": True,
        "action_time_human_unlock_phrase": packet["action"][
            "exact_human_unlock_phrase"
        ],
        "attachment_count": 0,
        "bcc": [],
        "body_sha256": draft["body_sha256"],
        "cc": [],
        "founder_review_confirmed": True,
        "labels": ["SENT"],
        "message_id": "synthetic-private-message-id",
        "outbound_request_identity_sha256": draft[
            "outbound_request_identity_sha256"
        ],
        "recipient": draft["recipient"],
        "route_id": packet["route_id"],
        "schema": (
            "lumencore.missionweave_jcp_support_gmail_sent_observation.private.v1"
        ),
        "sent_utc": "2026-07-22T03:00:00Z",
        "subject": draft["subject"],
        "thread_id": "synthetic-private-thread-id",
    }


def build(module, **overrides):
    args = {
        "escalation": escalation(),
        "private_observation": private_observation(),
        "private_observation_sha256": "A" * 64,
        "generated_utc": "2026-07-22T03:01:00Z",
    }
    args.update(overrides)
    return module.build_receipt(**args)


def test_builds_privacy_safe_exact_sent_receipt():
    module = load_module()
    receipt = build(module)

    assert receipt["schema"] == module.PUBLIC_RECEIPT_SCHEMA
    assert receipt["delivery_state"] == "GMAIL_SENT_FOLDER_RECORDED"
    assert receipt["controls"]["duplicate_send_allowed"] is False
    assert receipt["controls"]["request_identity_matched"] is True
    assert receipt["controls"]["gmail_message_id_exposed"] is False
    assert receipt["controls"]["gmail_thread_id_exposed"] is False
    assert receipt["sent_utc"] == "2026-07-22T03:00:00Z"


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("recipient", "other@example.com", "RECIPIENT_MISMATCH"),
        ("subject", "changed", "SUBJECT_MISMATCH"),
        ("body_sha256", "B" * 64, "BODY_HASH_MISMATCH"),
        (
            "outbound_request_identity_sha256",
            "C" * 64,
            "REQUEST_IDENTITY_MISMATCH",
        ),
        ("attachment_count", 1, "ATTACHMENT_COUNT_NOT_ZERO"),
        ("labels", ["DRAFT"], "GMAIL_SENT_STATE_INVALID"),
        ("founder_review_confirmed", False, "FOUNDER_REVIEW_NOT_CONFIRMED"),
        (
            "action_time_human_unlock_confirmed",
            False,
            "ACTION_TIME_HUMAN_UNLOCK_NOT_CONFIRMED",
        ),
        (
            "action_time_human_unlock_phrase",
            "SEND SOMETHING ELSE",
            "ACTION_TIME_HUMAN_UNLOCK_PHRASE_MISMATCH",
        ),
    ],
)
def test_rejects_any_sent_observation_mismatch(field, value, error):
    module = load_module()
    observation = private_observation()
    observation[field] = value

    with pytest.raises(module.JcpSupportSendReceiptError, match=error):
        build(module, private_observation=observation)


def test_rejects_send_at_or_after_deadline_and_pre_send_receipt():
    module = load_module()
    observation = private_observation()
    observation["sent_utc"] = "2026-07-22T16:00:00Z"

    with pytest.raises(module.JcpSupportSendReceiptError, match="AT_OR_AFTER"):
        build(module, private_observation=observation)

    observation["sent_utc"] = "2026-07-22T03:02:00Z"
    with pytest.raises(module.JcpSupportSendReceiptError, match="BEFORE_SEND"):
        build(module, private_observation=observation)


def test_public_receipt_and_markdown_exclude_private_mail_identifiers():
    module = load_module()
    receipt = build(module)
    rendered = json.dumps(receipt, sort_keys=True) + module.render_markdown(receipt)

    for forbidden in (
        "synthetic-private-message-id",
        "synthetic-private-thread-id",
        "message_id\"",
        "thread_id\"",
        "jcp-admin@dla.mil",
        "Urgent JCP portal status sync",
    ):
        assert forbidden not in rendered
    assert "Duplicate send allowed:** `false`" in rendered


def test_receipt_and_markdown_are_deterministic():
    module = load_module()
    first = build(module)
    second = build(module)

    assert first == second
    assert module.render_markdown(first) == module.render_markdown(second)
