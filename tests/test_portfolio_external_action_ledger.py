from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PORTFOLIO_EXTERNAL_ACTION_LEDGER.py"
CONFIG = ROOT / "config" / "portfolio_external_action_ledger_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "portfolio_external_action_ledger",
        SCRIPT,
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def build_payload(module, config: dict | None = None) -> dict:
    return module.build_ledger(
        config or load_config(),
        root=ROOT,
        config_path=CONFIG,
        generator_path=SCRIPT,
    )


def records_by_id(payload: dict) -> dict[str, dict]:
    return {record["record_id"]: record for record in payload["records"]}


def test_current_config_builds_a_private_safe_fail_closed_ledger():
    module = load_module()
    config = load_config()

    module.validate_config(config, root=ROOT)
    payload = build_payload(module, config)

    assert module.verify_ledger_hash(payload) is True
    assert payload["status"] == "RECONCILED_FAIL_CLOSED_LEDGER_READY"
    assert payload["coverage"] == {
        "central_grant_queue_item_count": 132,
        "engagement_register_lane_count": 15,
        "explicit_standalone_action_count": 8,
        "statement": (
            "The ledger covers every item in the configured central grant queue, "
            "every lane in the configured engagement register, and the declared "
            "standalone action records. It cannot discover an external action that "
            "was never registered or given a source record."
        ),
    }
    assert payload["summary"]["record_count"] == 155
    assert payload["summary"]["unique_action_key_count"] == 155
    assert payload["controls"]["builder_can_email"] is False
    assert payload["controls"]["builder_can_submit"] is False
    module._scan_forbidden_keys(payload)


def test_lvlup_followups_are_distinct_hash_only_monitor_records():
    module = load_module()
    payload = build_payload(module)
    records = records_by_id(payload)

    intro = records["external::lvlup_warm_investor_intro_followup_1"]
    status = records["external::lvlup_application_review_status_followup_1"]

    assert intro["lifecycle_state"] == "OUTBOUND_FOLLOWUP_SENT_MONITOR_ONLY"
    assert status["lifecycle_state"] == (
        "APPLICATION_ACTIVE_COMMITTEE_REVIEW_INBOUND_ONLY"
    )
    assert intro["duplicate_action_blocked"] is True
    assert status["duplicate_action_blocked"] is True
    assert intro["primary_receipt_sha256"] != status["primary_receipt_sha256"]
    assert intro["primary_receipt_pointer"] == "/receipts/0"
    assert status["primary_receipt_pointer"] is None
    assert status["receipt_class"] == "OFFICIAL_APPLICATION_STATUS_EMAIL_STATE"
    assert all(row["passed"] for row in intro["evidence_assertions"])
    assert all(row["passed"] for row in status["evidence_assertions"])

    serialized = json.dumps(payload, sort_keys=True).lower()
    assert "@lvlup.vc" not in serialized
    assert '"message_id"' not in serialized
    assert '"thread_id"' not in serialized


def test_third_sphere_outreach_is_hash_only_and_duplicate_blocked():
    module = load_module()
    payload = build_payload(module)
    records = records_by_id(payload)

    record = records["external::third_sphere_seedstrap_initial_review_request_1"]

    assert record["lifecycle_state"] == (
        "INITIAL_PUBLIC_SAFE_REVIEW_REQUEST_SENT_MONITOR_ONLY"
    )
    assert record["duplicate_action_blocked"] is True
    assert record["primary_receipt_pointer"] == "/receipt"
    assert all(row["passed"] for row in record["evidence_assertions"])

    serialized = json.dumps(payload, sort_keys=True).lower()
    assert "@thirdsphere." not in serialized
    assert '"message_id"' not in serialized
    assert '"thread_id"' not in serialized


def test_epri_overlay_tracks_completed_mou_without_authorizing_send():
    module = load_module()
    payload = build_payload(module)
    record = records_by_id(payload)["external::epri_open_power_ai_mou"]

    assert record["external_evidence_state"] == (
        "MOU_COMPLETED_BY_ALL_PARTIES_PRIVATE_CUSTODY_REQUIRED"
    )
    assert record["lifecycle_state"] == (
        "MOU_COMPLETED_PRIVATE_CUSTODY_AND_OBLIGATION_REVIEW_PENDING"
    )
    assert record["duplicate_action_blocked"] is True
    assert record["action_allowed_by_builder"] is False
    assert record["action_time_human_review_required"] is True
    assert "do not reply automatically" in record["next_action"].lower()


def test_argos_partner_and_government_sends_are_distinct_and_duplicate_blocked():
    module = load_module()
    payload = build_payload(module)
    records = records_by_id(payload)
    partner = records["external::argos_emi_teaming_inquiry"]
    government = records["external::argos_government_sources_sought"]

    assert partner["external_evidence_state"] == (
        "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY"
    )
    assert partner["lifecycle_state"] == (
        "PARTNER_INQUIRY_SENT_ONCE_MONITOR_ONLY"
    )
    assert partner["category"] == "EXTERNAL_COMMUNICATION_RECORDED"
    assert partner["duplicate_action_blocked"] is True
    assert partner["action_allowed_by_builder"] is False
    assert partner["action_time_human_review_required"] is True
    assert all(row["passed"] for row in partner["evidence_assertions"])
    assert partner["primary_receipt_sha256"] != government["primary_receipt_sha256"]

    assert government["lifecycle_state"] == (
        "OUTBOUND_SUBMISSION_SENT_AUTOMATIC_REPLY_ONLY_MONITOR"
    )
    assert government["category"] == "EXTERNAL_SUBMISSION_RECORDED_OUTBOUND"
    assert government["duplicate_action_blocked"] is True
    assert government["action_allowed_by_builder"] is False
    assert all(row["passed"] for row in government["evidence_assertions"])
    assert "Do not resend" in government["next_action"]


def test_dla_missionweave_uses_official_non_submission_receipt():
    module = load_module()
    payload = build_payload(module)
    record = records_by_id(payload)["external::dla26bz03_nv011_missionweave"]

    assert record["lifecycle_state"] == "NOT_SUBMITTED_DEADLINE_PASSED"
    assert record["category"] == "NOT_SUBMITTED_CLOSED"
    assert record["receipt_class"] == "OFFICIAL_DLA_NON_SUBMISSION_EMAIL_STATE"
    assert record["duplicate_action_blocked"] is True
    assert record["action_allowed_by_builder"] is False
    assert record["current_opportunity_actionable"] is False
    assert all(row["passed"] for row in record["evidence_assertions"])
    assert {
        row["source_id"] for row in record["evidence_assertions"]
    } == {"dla_dsip_official_non_submission_receipt"}
    assert record["primary_receipt_sha256"] == module.file_sha256(
        ROOT
        / "grant_submissions"
        / "funding_sprint_20260709"
        / "DLA_DSIP_OFFICIAL_NON_SUBMISSION_RECEIPT_2026-07-28.json"
    )


def test_lanl_followup_is_sent_once_duplicate_blocked_and_inbound_only():
    module = load_module()
    payload = build_payload(module)
    record = records_by_id(payload)["external::lanl_vision_bounded_followup_1"]

    assert record["category"] == "EXTERNAL_COMMUNICATION_RECORDED"
    assert record["lifecycle_state"] == (
        "BOUNDED_FOLLOWUP_SENT_RESPONSE_PENDING_INBOUND_ONLY"
    )
    assert record["duplicate_action_blocked"] is True
    assert record["action_allowed_by_builder"] is False
    assert record["receipt_class"] == "PRIVACY_SAFE_FULL_THREAD_SEND_STATE"
    assert all(row["passed"] for row in record["evidence_assertions"])
    assert "do not send again" in record["next_action"].lower()

    serialized = json.dumps(record, sort_keys=True).lower()
    assert "@lanl.gov" not in serialized
    assert '"message_id"' not in serialized
    assert '"thread_id"' not in serialized
    assert "meeting id" not in serialized
    assert "passcode" not in serialized


def test_multi_action_receipt_is_bound_to_distinct_subrecords():
    module = load_module()
    payload = build_payload(module)
    records = records_by_id(payload)

    army = records["external::army_aidp_draft_cfs_feedback"]
    nasa = records["external::nasa_data_center_rfi"]

    assert army["primary_receipt_pointer"] == "/submissions/0"
    assert nasa["primary_receipt_pointer"] == "/submissions/1"
    assert army["primary_receipt_sha256"] != nasa["primary_receipt_sha256"]
    assert army["duplicate_action_blocked"] is True
    assert nasa["duplicate_action_blocked"] is True
    assert all(row["passed"] for row in army["evidence_assertions"])
    assert all(row["passed"] for row in nasa["evidence_assertions"])


def test_reusing_one_receipt_subrecord_for_two_actions_fails_closed():
    module = load_module()
    config = copy.deepcopy(load_config())
    actions = {
        action["record_id"]: action for action in config["explicit_actions"]
    }
    nasa = actions["external::nasa_data_center_rfi"]
    nasa["primary_receipt_pointer"] = "/submissions/0"
    nasa["evidence_assertions"] = [
        {
            "expected": "ACCAPGAIDPRFI4",
            "pointer": "/submissions/0/notice_id",
            "source_id": "external_submission_receipt",
        }
    ]

    with pytest.raises(
        module.LedgerConfigError,
        match="one receipt is bound to multiple external action keys",
    ):
        build_payload(module, config)


def test_primary_receipt_selector_requires_a_declared_source():
    module = load_module()
    config = copy.deepcopy(load_config())
    action = config["explicit_actions"][0]
    action["primary_receipt_pointer"] = "/status"
    action.pop("primary_receipt_source_id")

    with pytest.raises(
        module.LedgerConfigError,
        match="primary_receipt_pointer requires primary_receipt_source_id",
    ):
        module.validate_config(config, root=ROOT)


def test_markdown_preserves_claim_and_control_boundaries():
    module = load_module()
    payload = build_payload(module)
    markdown = module.render_markdown(payload)

    assert "# LumenCore Portfolio External Action Ledger" in markdown
    assert "This builder is read-only." in markdown
    assert "cannot log in, email, apply, upload, sign, certify, or submit" in markdown
    assert "External submission records:" in markdown
