from __future__ import annotations

import argparse
import hashlib
import hmac
import importlib.util
import json
import os
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"

EMAIL_RECONCILIATION = (
    SPRINT_DIR / "EMAIL_ACTION_RECONCILIATION_2026-07-18.json"
)
RESPONSE_TEMPLATE_REGISTRY = (
    SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)
RESPONSE_REGISTRY_BUILDER = (
    ROOT / "code" / "ops" / "BUILD_OUTREACH_RESPONSE_TEMPLATE_REGISTRY.py"
)
FOLLOWUP_POLICY_CONFIG = ROOT / "config" / "outreach_followup_policies_v1.json"
FOLLOWUP_SEND_LEDGER = (
    SPRINT_DIR / "OUTREACH_FOLLOWUP_SEND_LEDGER_2026-07-18.json"
)

CANONICAL_JSON = SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
CANONICAL_MD = SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.md"
LATEST_JSON = OUT_OPS / "outreach_followup_action_queue_latest.json"

SCHEMA = "lumencore.outreach_followup_action_queue.v1"
SEND_LEDGER_SCHEMA = "lumencore.outreach_followup_send_ledger.v1"
MAILBOX_RECHECK_RECEIPT_SCHEMA = "lumencore.mailbox_recheck_receipt.v1"
FOLLOWUP_DISPATCH_BINDING_SCHEMA = "lumencore.outreach_dispatch_binding.v1"
ACTION_TIME_APPROVAL_SCHEMA = "lumencore.outreach_action_time_approval.v1"
AUTHORIZED_DISPATCH_SCHEMA = "lumencore.outreach_authorized_dispatch.v1"
REFERENCE_AS_OF_UTC = "2026-07-18T12:20:24Z"
MAILBOX_RECHECK_MAX_AGE_SECONDS = 15 * 60
ACTION_TIME_APPROVAL_MAX_AGE_SECONDS = 5 * 60
ACTION_TIME_APPROVAL_SCOPE = "ONE_SEND_EXACT_DRAFT"
HUMAN_UNLOCK_ENV_VAR = "LUMA_HUMAN_UNLOCK_TOKEN"
HUMAN_UNLOCK_MIN_LENGTH = 32
MAILBOX_RECHECK_RECEIPT_FIELDS = {
    "full_thread_read",
    "inbound_after_source_count",
    "lane_id",
    "latest_observed_message_utc",
    "mailbox_rechecked_utc",
    "no_reply_confirmed",
    "observed_message_count",
    "receipt_sha256",
    "schema",
    "source_message_id_sha256",
    "source_sent_utc",
    "thread_id_sha256",
    "thread_truncated",
}
FOLLOWUP_DISPATCH_BINDING_FIELDS = {
    "attachment_sha256s",
    "body_sha256",
    "dispatch_sha256",
    "lane_id",
    "mailbox_check_receipt_sha256",
    "max_proactive_sends",
    "prior_followup_count",
    "recipient_route_sha256",
    "schema",
    "subject_sha256",
    "template_id",
}
ACTION_TIME_APPROVAL_FIELDS = {
    "approval_code_sha256",
    "approval_receipt_sha256",
    "approval_scope",
    "approved_utc",
    "dispatch_sha256",
    "expires_utc",
    "human_unlock_proof_sha256",
    "lane_id",
    "mailbox_check_receipt_sha256",
    "prior_followup_count",
    "schema",
    "template_id",
}
AUTHORIZED_DISPATCH_FIELDS = {
    "action_approval_receipt_sha256",
    "approval_scope",
    "authorization_sha256",
    "authorized_utc",
    "dispatch_sha256",
    "expires_utc",
    "lane_id",
    "mailbox_check_receipt_sha256",
    "prior_followup_count",
    "schema",
    "send_allowed_by_builder",
    "send_performed",
    "single_use",
    "status",
    "template_id",
}
ACTION_BOUND_SEND_RECEIPT_FIELDS = {
    "action_approval_receipt_sha256",
    "approval_scope",
    "authorization_sha256",
    "dispatch_sha256",
    "mailbox_check_receipt_sha256",
    "prior_followup_count",
}
PRIVATE_SEND_RECEIPT_KEYS = {
    "body",
    "message_id",
    "recipient_email",
    "subject",
    "thread_id",
}

MODE_STATES = {
    "ACCOUNT_ACTION": "HUMAN_ACCOUNT_ACTION_OPEN",
    "CLOSED": "CLOSED_NO_ACTION",
    "INBOUND_ONLY": "MONITOR_INBOUND_ONLY",
    "PORTAL_ACTION": "HUMAN_PORTAL_ACTION_OPEN",
    "PRIVATE_RECONCILIATION": "PRIVATE_RECONCILIATION_OPEN",
}
PROACTIVE_OUTREACH_MODES = {
    "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD",
    "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE",
}
DUE_MAILBOX_RECHECK_STATES = {
    "RECHECK_MAILBOX_BEFORE_DRAFT",
    "DEADLINE_ACTION_DUE_MAILBOX_RECHECK",
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def parse_aware_utc(value: str) -> datetime:
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {value}") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"Timezone required: {value}")
    return parsed.astimezone(timezone.utc)


def utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def source_status(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def canonical_object_sha256(payload: dict[str, Any], *, omit: set[str]) -> str:
    bounded = {key: value for key, value in payload.items() if key not in omit}
    return hashlib.sha256(
        json.dumps(bounded, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()


def normalize_sha256(value: Any, label: str) -> str:
    normalized = str(value or "").strip().upper()
    if len(normalized) != 64 or any(
        char not in "0123456789ABCDEF" for char in normalized
    ):
        raise ValueError(f"{label} SHA-256 is invalid")
    return normalized


def configured_human_unlock_token() -> bytes:
    value = os.environ.get(HUMAN_UNLOCK_ENV_VAR)
    if not isinstance(value, str) or len(value) < HUMAN_UNLOCK_MIN_LENGTH:
        raise ValueError(
            f"{HUMAN_UNLOCK_ENV_VAR} is not configured with a sufficiently long "
            "private bearer token"
        )
    return value.encode("utf-8")


def validate_presented_human_unlock_token(presented_token: str) -> bytes:
    if not isinstance(presented_token, str):
        raise ValueError("HumanUnlock bearer token is required at action time")
    configured_token = configured_human_unlock_token()
    if not hmac.compare_digest(
        presented_token.encode("utf-8"), configured_token
    ):
        raise ValueError("HumanUnlock bearer token does not match")
    return configured_token


def action_time_human_unlock_proof(
    receipt: dict[str, Any], token: bytes
) -> str:
    bounded = {
        key: value
        for key, value in receipt.items()
        if key not in {
            "approval_receipt_sha256",
            "human_unlock_proof_sha256",
        }
    }
    message = (
        b"lumencore.outreach.action-time-human-unlock.v1\x00"
        + json.dumps(
            bounded, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )
    return hmac.new(token, message, hashlib.sha256).hexdigest().upper()


def build_mailbox_recheck_receipt(
    *,
    lane_id: str,
    mailbox_rechecked_utc: str,
    thread_id_sha256: str,
    source_message_id_sha256: str,
    source_sent_utc: str,
    latest_observed_message_utc: str,
    observed_message_count: int,
    inbound_after_source_count: int,
) -> dict[str, Any]:
    receipt = {
        "schema": MAILBOX_RECHECK_RECEIPT_SCHEMA,
        "lane_id": lane_id,
        "mailbox_rechecked_utc": utc_iso(
            parse_aware_utc(mailbox_rechecked_utc)
        ),
        "thread_id_sha256": normalize_sha256(
            thread_id_sha256, "Mailbox thread identifier"
        ),
        "source_message_id_sha256": normalize_sha256(
            source_message_id_sha256, "Mailbox source message identifier"
        ),
        "source_sent_utc": utc_iso(parse_aware_utc(source_sent_utc)),
        "latest_observed_message_utc": utc_iso(
            parse_aware_utc(latest_observed_message_utc)
        ),
        "observed_message_count": observed_message_count,
        "inbound_after_source_count": inbound_after_source_count,
        "full_thread_read": True,
        "thread_truncated": False,
        "no_reply_confirmed": inbound_after_source_count == 0,
    }
    receipt["receipt_sha256"] = canonical_object_sha256(
        receipt, omit={"receipt_sha256"}
    )
    validate_mailbox_recheck_receipt(receipt, expected_lane_id=lane_id)
    return receipt


def validate_mailbox_recheck_receipt(
    receipt: dict[str, Any], *, expected_lane_id: str
) -> tuple[datetime, str]:
    if not isinstance(receipt, dict):
        raise ValueError("Mailbox recheck receipt must be an object")
    receipt_fields = set(receipt)
    if receipt_fields != MAILBOX_RECHECK_RECEIPT_FIELDS:
        missing = sorted(MAILBOX_RECHECK_RECEIPT_FIELDS - receipt_fields)
        extra = sorted(receipt_fields - MAILBOX_RECHECK_RECEIPT_FIELDS)
        details = []
        if missing:
            details.append("missing=" + ",".join(missing))
        if extra:
            details.append("extra=" + ",".join(extra))
        raise ValueError(
            "Mailbox recheck receipt fields are invalid: " + "; ".join(details)
        )
    if receipt.get("schema") != MAILBOX_RECHECK_RECEIPT_SCHEMA:
        raise ValueError("Mailbox recheck receipt schema is invalid")
    if receipt.get("lane_id") != expected_lane_id:
        raise ValueError("Mailbox recheck receipt lane mismatch")
    if receipt.get("full_thread_read") is not True:
        raise ValueError("Mailbox recheck receipt is not a full-thread read")
    if receipt.get("thread_truncated") is not False:
        raise ValueError("Mailbox recheck receipt thread is truncated")

    observed_count = receipt.get("observed_message_count")
    inbound_after_source = receipt.get("inbound_after_source_count")
    if (
        isinstance(observed_count, bool)
        or not isinstance(observed_count, int)
        or observed_count < 1
    ):
        raise ValueError("Mailbox recheck receipt message count is invalid")
    if (
        isinstance(inbound_after_source, bool)
        or not isinstance(inbound_after_source, int)
        or inbound_after_source < 0
    ):
        raise ValueError("Mailbox recheck receipt reply count is invalid")
    if (
        receipt.get("no_reply_confirmed") is not True
        or inbound_after_source != 0
    ):
        raise ValueError("Mailbox recheck receipt does not confirm no reply")

    normalize_sha256(
        receipt.get("thread_id_sha256"), "Mailbox thread identifier"
    )
    normalize_sha256(
        receipt.get("source_message_id_sha256"),
        "Mailbox source message identifier",
    )
    mailbox_checked_at = parse_aware_utc(
        str(receipt.get("mailbox_rechecked_utc") or "")
    )
    source_sent_at = parse_aware_utc(str(receipt.get("source_sent_utc") or ""))
    latest_observed_at = parse_aware_utc(
        str(receipt.get("latest_observed_message_utc") or "")
    )
    if receipt["mailbox_rechecked_utc"] != utc_iso(mailbox_checked_at):
        raise ValueError("Mailbox recheck receipt timestamp is not canonical")
    if receipt["source_sent_utc"] != utc_iso(source_sent_at):
        raise ValueError("Mailbox source message timestamp is not canonical")
    if receipt["latest_observed_message_utc"] != utc_iso(latest_observed_at):
        raise ValueError("Mailbox latest message timestamp is not canonical")
    if source_sent_at > latest_observed_at:
        raise ValueError("Mailbox source message is newer than the observed thread")
    if latest_observed_at > mailbox_checked_at:
        raise ValueError("Mailbox receipt observes a message from the future")

    expected_receipt_sha = canonical_object_sha256(
        receipt, omit={"receipt_sha256"}
    )
    actual_receipt_sha = normalize_sha256(
        receipt.get("receipt_sha256"), "Mailbox recheck receipt"
    )
    if actual_receipt_sha != expected_receipt_sha:
        raise ValueError("Mailbox recheck receipt integrity check failed")
    return mailbox_checked_at, actual_receipt_sha


def validate_followup_send_ledger(
    ledger: dict[str, Any],
    policies: dict[str, dict[str, Any]],
    template_ids: set[str],
    *,
    as_of: datetime,
) -> tuple[Counter[str], dict[str, list[str]]]:
    if ledger.get("schema") != SEND_LEDGER_SCHEMA:
        raise ValueError("Follow-up send ledger schema is invalid")
    controls = ledger.get("controls", {})
    if (
        controls.get("append_only") is not True
        or controls.get("count_derived_from_receipts") is not True
        or controls.get("private_identifiers_prohibited") is not True
        or controls.get("exact_dispatch_binding_required_for_new_receipts")
        is not True
        or controls.get("single_use_action_approval_required_for_new_receipts")
        is not True
    ):
        raise ValueError("Follow-up send ledger controls are unsafe")
    approval_control_effective = parse_aware_utc(
        str(controls.get("action_time_approval_required_after_utc") or "")
    )
    if controls["action_time_approval_required_after_utc"] != utc_iso(
        approval_control_effective
    ):
        raise ValueError("Follow-up send ledger approval-control time is not canonical")
    expected_ledger_sha = canonical_object_sha256(ledger, omit={"ledger_sha256"})
    if normalize_sha256(ledger.get("ledger_sha256"), "Follow-up send ledger") != (
        expected_ledger_sha
    ):
        raise ValueError("Follow-up send ledger integrity check failed")

    receipts = ledger.get("receipts")
    if not isinstance(receipts, list):
        raise ValueError("Follow-up send ledger receipts must be a list")
    counts: Counter[str] = Counter()
    receipt_digests: dict[str, list[str]] = {}
    seen_sent_receipts: set[str] = set()
    seen_approval_receipts: set[str] = set()
    seen_dispatches: set[str] = set()
    seen_authorizations: set[str] = set()
    historical_counts: Counter[str] = Counter()
    previous_sent_at: datetime | None = None
    for index, receipt in enumerate(receipts):
        if not isinstance(receipt, dict):
            raise ValueError(f"Follow-up send receipt {index} is invalid")
        exposed = PRIVATE_SEND_RECEIPT_KEYS.intersection(receipt)
        if exposed:
            raise ValueError(
                "Follow-up send receipt exposes private message material: "
                + ", ".join(sorted(exposed))
            )
        lane_id = str(receipt.get("lane_id") or "")
        policy = policies.get(lane_id)
        if policy is None:
            raise ValueError(f"Follow-up send receipt has unknown lane: {lane_id}")
        if policy.get("mode") not in PROACTIVE_OUTREACH_MODES:
            raise ValueError(f"Non-proactive lane has a send receipt: {lane_id}")
        template_id = receipt.get("template_id")
        if (
            template_id not in template_ids
            or template_id != policy.get("eligible_template_id")
        ):
            raise ValueError(f"Follow-up send receipt template mismatch: {lane_id}")
        if receipt.get("delivery_state") != "SENT":
            raise ValueError(f"Follow-up send receipt state is not SENT: {lane_id}")
        sent_at = parse_aware_utc(str(receipt.get("sent_utc") or ""))
        if receipt["sent_utc"] != utc_iso(sent_at):
            raise ValueError("Follow-up send receipt timestamp is not canonical")
        if previous_sent_at is not None and sent_at < previous_sent_at:
            raise ValueError("Follow-up send ledger is not append-ordered")
        previous_sent_at = sent_at
        sent_receipt_sha = normalize_sha256(
            receipt.get("sent_message_receipt_sha256"), "Sent message receipt"
        )
        if sent_receipt_sha in seen_sent_receipts:
            raise ValueError("Follow-up send ledger contains a duplicate receipt")
        seen_sent_receipts.add(sent_receipt_sha)

        action_fields_present = ACTION_BOUND_SEND_RECEIPT_FIELDS.intersection(receipt)
        action_binding_required = sent_at >= approval_control_effective
        unbound_send_observed = (
            receipt.get("governance_exception") == "UNBOUND_SEND_OBSERVED"
        )
        if unbound_send_observed:
            if (
                receipt.get("authorization_verified") is not False
                or action_fields_present
            ):
                raise ValueError(
                    "Observed unbound send exception contains invalid authorization data"
                )
        elif "governance_exception" in receipt or "authorization_verified" in receipt:
            raise ValueError("Follow-up send receipt governance exception is invalid")
        elif action_binding_required or action_fields_present:
            missing_action_fields = ACTION_BOUND_SEND_RECEIPT_FIELDS - set(receipt)
            if missing_action_fields:
                raise ValueError(
                    "Follow-up send receipt is missing action-time bindings: "
                    + ", ".join(sorted(missing_action_fields))
                )
            if receipt.get("approval_scope") != ACTION_TIME_APPROVAL_SCOPE:
                raise ValueError("Follow-up send receipt approval scope is invalid")
            prior_count = receipt.get("prior_followup_count")
            if (
                isinstance(prior_count, bool)
                or not isinstance(prior_count, int)
                or prior_count != historical_counts[lane_id]
            ):
                raise ValueError("Follow-up send receipt prior count is invalid")
            approval_sha = normalize_sha256(
                receipt.get("action_approval_receipt_sha256"),
                "Action-time approval receipt",
            )
            dispatch_sha = normalize_sha256(
                receipt.get("dispatch_sha256"), "Follow-up dispatch"
            )
            mailbox_sha = normalize_sha256(
                receipt.get("mailbox_check_receipt_sha256"),
                "Follow-up mailbox receipt",
            )
            authorization_sha = normalize_sha256(
                receipt.get("authorization_sha256"),
                "Follow-up dispatch authorization",
            )
            canonical_hashes = {
                "action_approval_receipt_sha256": approval_sha,
                "dispatch_sha256": dispatch_sha,
                "mailbox_check_receipt_sha256": mailbox_sha,
                "authorization_sha256": authorization_sha,
            }
            if any(
                receipt[field] != normalized
                for field, normalized in canonical_hashes.items()
            ):
                raise ValueError(
                    "Follow-up action-time binding SHA-256 is not canonical"
                )
            if approval_sha in seen_approval_receipts:
                raise ValueError(
                    "Follow-up send ledger reuses an action-time approval receipt"
                )
            if dispatch_sha in seen_dispatches:
                raise ValueError("Follow-up send ledger repeats an exact dispatch")
            if authorization_sha in seen_authorizations:
                raise ValueError(
                    "Follow-up send ledger reuses a dispatch authorization"
                )
            seen_approval_receipts.add(approval_sha)
            seen_dispatches.add(dispatch_sha)
            seen_authorizations.add(authorization_sha)

        historical_counts[lane_id] += 1
        if historical_counts[lane_id] > int(policy["max_proactive_sends"]):
            raise ValueError(f"Follow-up send limit exceeded in ledger: {lane_id}")
        # The ledger is append-only, so a historical queue rebuild can contain
        # receipts recorded after that snapshot. Validate them, but count only
        # receipts that existed by the requested as-of time.
        if sent_at > as_of:
            continue
        counts[lane_id] += 1
        receipt_digests.setdefault(lane_id, []).append(
            canonical_object_sha256(receipt, omit=set())
        )

    for lane_id, count in counts.items():
        if count > int(policies[lane_id]["max_proactive_sends"]):
            raise ValueError(f"Follow-up send limit exceeded in ledger: {lane_id}")
    return counts, receipt_digests


def validate_embedded_source_evidence(reconciliation: dict[str, Any]) -> None:
    evidence = reconciliation.get("source_evidence")
    if not isinstance(evidence, dict) or not evidence:
        raise ValueError("Email reconciliation source evidence is missing")

    root = ROOT.resolve()
    for source_id, recorded in evidence.items():
        if not isinstance(recorded, dict) or not recorded.get("path"):
            raise ValueError(f"Invalid source evidence row: {source_id}")
        candidate = (ROOT / str(recorded["path"])).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"Source evidence path escapes repository: {source_id}") from exc

        present = candidate.is_file()
        if present != (recorded.get("present") is True):
            raise ValueError(f"Source evidence presence drift: {source_id}")
        if not present:
            continue
        if candidate.stat().st_size != recorded.get("bytes"):
            raise ValueError(f"Source evidence byte-count drift: {source_id}")
        if sha256_file(candidate) != recorded.get("sha256"):
            raise ValueError(f"Source evidence hash drift: {source_id}")


def validate_sources(
    reconciliation: dict[str, Any],
    registry: dict[str, Any],
    policy_config: dict[str, Any],
    send_ledger: dict[str, Any],
    *,
    as_of: datetime,
) -> tuple[
    set[str],
    dict[str, dict[str, Any]],
    Counter[str],
    dict[str, list[str]],
]:
    reconciliation_status = reconciliation.get("status")
    deadline_action_count = reconciliation.get("summary", {}).get(
        "deadline_action_required_count", 0
    )
    if (
        reconciliation.get("schema")
        != "lumencore.email_action_reconciliation.v1"
        or reconciliation_status
        not in {
            "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION",
            "DEADLINE_ACTION_DUE_HUMAN_REVIEW",
        }
        or (
            deadline_action_count > 0
            and reconciliation_status != "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
        )
        or (
            deadline_action_count == 0
            and reconciliation_status
            != "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
        )
        or reconciliation.get("summary", {}).get("send_now_count") != 0
    ):
        raise ValueError("Email reconciliation is missing, stale, or send-active")
    validate_embedded_source_evidence(reconciliation)
    if (
        registry.get("schema")
        != "lumencore.outreach_response_template_registry.v1"
        or registry.get("controls", {}).get("builder_can_send_email") is not False
        or registry.get("controls", {}).get("duplicate_send_fail_closed") is not True
    ):
        raise ValueError("Response template registry is missing or unsafe")
    if (
        policy_config.get("schema")
        != "lumencore.outreach_followup_policies.v1"
        or policy_config.get("controls", {}).get("builder_can_send_email") is not False
        or policy_config.get("controls", {}).get(
            "inbox_recheck_required_before_any_followup"
        )
        is not True
        or policy_config.get("controls", {}).get("past_hold_does_not_authorize_send")
        is not True
    ):
        raise ValueError("Follow-up policy config is missing or unsafe")

    template_ids = {
        row.get("template_id") for row in registry.get("templates", [])
    }
    policies = {
        row.get("lane_id"): row for row in policy_config.get("lane_policies", [])
    }
    if len(policies) != len(policy_config.get("lane_policies", [])):
        raise ValueError("Follow-up policy lane IDs are duplicated")

    lanes = reconciliation.get("lanes", [])
    lane_ids = {row.get("lane_id") for row in lanes}
    if lane_ids != set(policies):
        raise ValueError("Follow-up policy coverage does not match reconciliation lanes")
    quarantined_lanes = [
        lane
        for lane in lanes
        if lane.get("conflicting_gmail_draft_count", 0) > 0
    ]
    if (
        reconciliation.get("summary", {}).get(
            "conflicting_gmail_draft_count"
        )
        != sum(
            lane.get("conflicting_gmail_draft_count", 0)
            for lane in quarantined_lanes
        )
        or reconciliation.get("summary", {}).get(
            "conflicting_gmail_draft_lane_count"
        )
        != len(quarantined_lanes)
        or any(
            lane.get("draft_quarantine_status")
            != "QUARANTINED_NOT_SENDABLE"
            or lane.get("send_now") is not False
            or lane.get("response_template_id") != "NO_DUPLICATE_MONITOR"
            for lane in quarantined_lanes
        )
    ):
        raise ValueError("Email reconciliation draft quarantine is incomplete")
    for lane in lanes:
        lane_policy = lane.get("follow_up_policy")
        if lane_policy != policies[lane["lane_id"]]:
            raise ValueError(f"Embedded follow-up policy drift: {lane['lane_id']}")
        template_id = lane_policy.get("eligible_template_id")
        if template_id and template_id not in template_ids:
            raise ValueError(f"Unknown eligible template: {template_id}")
    send_counts, send_receipt_digests = validate_followup_send_ledger(
        send_ledger, policies, template_ids, as_of=as_of
    )
    return template_ids, policies, send_counts, send_receipt_digests


def evaluate_lane(
    lane: dict[str, Any], as_of: datetime, sent_counts: Counter[str]
) -> dict[str, Any]:
    policy = lane["follow_up_policy"]
    mode = policy["mode"]
    recorded_send_count = sent_counts.get(lane["lane_id"], 0)
    row = {
        "lane_id": lane["lane_id"],
        "organization": lane["organization"],
        "source_state": lane["state"],
        "follow_up_mode": mode,
        "current_response_template_id": lane.get("response_template_id"),
        "eligible_template_id": policy.get("eligible_template_id"),
        "not_before_utc": policy.get("not_before_utc"),
        "deadline_utc": policy.get("deadline_utc"),
        "partner_interest_target_utc": policy.get("partner_interest_target_utc"),
        "max_proactive_sends": policy.get("max_proactive_sends"),
        "recorded_proactive_send_count": recorded_send_count,
        "rationale": policy["rationale"],
        "send_now": False,
        "draft_rendered": False,
        "inbox_recheck_required": False,
        "conflicting_gmail_draft_count": lane.get(
            "conflicting_gmail_draft_count", 0
        ),
        "draft_quarantine_status": lane.get("draft_quarantine_status"),
        "action_time_human_review_required": True,
        "next_action": lane["next_action"],
    }
    if row["conflicting_gmail_draft_count"]:
        row["quarantined_draft_conflict_type"] = lane[
            "quarantined_draft_conflict_type"
        ]
        row["quarantined_draft_observed_utc"] = lane[
            "quarantined_draft_observed_utc"
        ]

    if mode in MODE_STATES:
        row["action_state"] = MODE_STATES[mode]
        return row
    if mode not in PROACTIVE_OUTREACH_MODES:
        raise ValueError(f"Unsupported follow-up mode: {mode}")

    if recorded_send_count >= int(policy["max_proactive_sends"]):
        row.update(
            {
                "action_state": (
                    "INITIAL_OUTREACH_LIMIT_REACHED_NO_SEND"
                    if mode == "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE"
                    else "FOLLOWUP_LIMIT_REACHED_NO_SEND"
                ),
                "next_action": (
                    "The bounded proactive outreach allowance is exhausted. Monitor the "
                    "existing thread and respond only to a specific inbound request."
                ),
            }
        )
        return row

    not_before = parse_aware_utc(str(policy["not_before_utc"]))
    deadline: datetime | None = None
    if mode == "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE":
        deadline = parse_aware_utc(str(policy.get("deadline_utc") or ""))
        partner_target = parse_aware_utc(
            str(policy.get("partner_interest_target_utc") or "")
        )
        if not_before >= deadline or partner_target >= deadline:
            raise ValueError("Initial outreach deadline ordering is invalid")
        row["seconds_until_deadline"] = int((deadline - as_of).total_seconds())
        row["partner_target_passed"] = as_of >= partner_target
        if as_of >= deadline:
            row.update(
                {
                    "action_state": "DEADLINE_PASSED_NO_SEND",
                    "seconds_until_deadline": 0,
                    "next_action": (
                        "The official deadline has passed. Do not send late or revive "
                        "the draft; retain the record and monitor only for inbound contact."
                    ),
                }
            )
            return row
    if as_of < not_before:
        row["action_state"] = "HELD_NO_SEND"
        row["hold_seconds_remaining"] = int((not_before - as_of).total_seconds())
        return row

    row.update(
        {
            "action_state": (
                "DEADLINE_ACTION_DUE_MAILBOX_RECHECK"
                if mode == "ONE_BOUNDED_INITIAL_OUTREACH_BEFORE_DEADLINE"
                else "RECHECK_MAILBOX_BEFORE_DRAFT"
            ),
            "hold_seconds_remaining": 0,
            "inbox_recheck_required": True,
            "next_action": (
                "Recheck the complete thread and full mailbox for any reply, sent copy, "
                "or delivery change. Only if no duplicate exists may one bounded draft "
                "be rendered or rebound for action-time review."
            ),
        }
    )
    return row


def load_response_registry_module():
    spec = importlib.util.spec_from_file_location(
        "outreach_response_template_registry", RESPONSE_REGISTRY_BUILDER
    )
    if spec is None or spec.loader is None:
        raise ValueError("Response registry builder cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_due_followup(
    lane_id: str,
    facts: dict[str, Any],
    *,
    as_of_utc: str,
    mailbox_check_receipt: dict[str, Any],
) -> dict[str, Any]:
    queue = build_payload(as_of_utc)
    action = next(
        (row for row in queue["actions"] if row["lane_id"] == lane_id), None
    )
    if action is None:
        raise ValueError(f"Unknown follow-up lane: {lane_id}")
    if action["action_state"] not in DUE_MAILBOX_RECHECK_STATES:
        raise ValueError("Proactive outreach is not due for mailbox recheck")
    as_of = parse_aware_utc(as_of_utc)
    mailbox_checked_at, receipt = validate_mailbox_recheck_receipt(
        mailbox_check_receipt, expected_lane_id=lane_id
    )
    mailbox_check_age_seconds = int((as_of - mailbox_checked_at).total_seconds())
    if mailbox_check_age_seconds < 0:
        raise ValueError("Mailbox recheck timestamp cannot be in the future")
    if mailbox_check_age_seconds > MAILBOX_RECHECK_MAX_AGE_SECONDS:
        raise ValueError("Mailbox recheck is stale")
    not_before_utc = action.get("not_before_utc")
    if not not_before_utc:
        raise ValueError("Due follow-up is missing its hold boundary")
    if mailbox_checked_at < parse_aware_utc(not_before_utc):
        raise ValueError("Mailbox recheck predates the follow-up hold boundary")
    deadline_utc = action.get("deadline_utc")
    if deadline_utc and as_of >= parse_aware_utc(str(deadline_utc)):
        raise ValueError("Proactive outreach deadline has passed")
    template_id = action.get("eligible_template_id")
    if not template_id:
        raise ValueError("No eligible follow-up template is configured")

    registry_module = load_response_registry_module()
    rendered = registry_module.render_response(
        template_id,
        facts,
        already_sent=False,
        inbound_requires_response=True,
        explicit_attachment_request=False,
        current_utc=as_of_utc,
    )
    if not str(rendered.get("status", "")).startswith("READY_FOR_"):
        raise ValueError(f"Follow-up render blocked: {rendered.get('status')}")
    if rendered.get("send_allowed_by_builder") is not False:
        raise ValueError("Follow-up renderer exposed send authority")
    rendered["lane_id"] = lane_id
    rendered["queue_action_state"] = action["action_state"]
    rendered["mailbox_rechecked"] = True
    rendered["mailbox_rechecked_utc"] = utc_iso(mailbox_checked_at)
    rendered["mailbox_recheck_age_seconds"] = mailbox_check_age_seconds
    rendered["mailbox_check_receipt_sha256"] = receipt
    rendered["no_reply_confirmed"] = True
    rendered["prior_followup_count"] = action["recorded_proactive_send_count"]
    rendered["max_proactive_sends"] = action["max_proactive_sends"]
    return rendered


def recipient_route_sha256(recipient_route: dict[str, Any]) -> str:
    if not isinstance(recipient_route, dict) or set(recipient_route) != {
        "to",
        "cc",
        "bcc",
    }:
        raise ValueError("Recipient route must contain exactly to, cc, and bcc")
    email_pattern = load_response_registry_module().EMAIL_RE
    normalized: dict[str, list[str]] = {}
    seen: set[str] = set()
    for channel in ("to", "cc", "bcc"):
        values = recipient_route[channel]
        if not isinstance(values, list):
            raise ValueError(f"Recipient route {channel} must be a list")
        channel_values: list[str] = []
        for value in values:
            if not isinstance(value, str):
                raise ValueError(f"Recipient route {channel} contains a non-string")
            address = value.strip().lower()
            if not email_pattern.fullmatch(address):
                raise ValueError(f"Recipient route {channel} contains an invalid email")
            if address in seen:
                raise ValueError("Recipient route contains a duplicate address")
            seen.add(address)
            channel_values.append(address)
        normalized[channel] = sorted(channel_values)
    if not normalized["to"]:
        raise ValueError("Recipient route requires at least one to address")
    return canonical_object_sha256(normalized, omit=set())


def validate_followup_dispatch_binding(binding: dict[str, Any]) -> str:
    if not isinstance(binding, dict) or set(binding) != (
        FOLLOWUP_DISPATCH_BINDING_FIELDS
    ):
        raise ValueError("Follow-up dispatch binding fields are invalid")
    if binding.get("schema") != FOLLOWUP_DISPATCH_BINDING_SCHEMA:
        raise ValueError("Follow-up dispatch binding schema is invalid")
    if not str(binding.get("lane_id") or "").strip():
        raise ValueError("Follow-up dispatch binding lane is missing")
    if not str(binding.get("template_id") or "").strip():
        raise ValueError("Follow-up dispatch binding template is missing")

    for field, label in (
        ("subject_sha256", "Dispatch subject"),
        ("body_sha256", "Dispatch body"),
        ("recipient_route_sha256", "Dispatch recipient route"),
        ("mailbox_check_receipt_sha256", "Dispatch mailbox receipt"),
    ):
        normalized = normalize_sha256(binding.get(field), label)
        if binding[field] != normalized:
            raise ValueError(f"{label} SHA-256 is not canonical")

    attachment_hashes = binding.get("attachment_sha256s")
    if not isinstance(attachment_hashes, list):
        raise ValueError("Dispatch attachment hashes must be a list")
    normalized_attachments = [
        normalize_sha256(value, "Dispatch attachment") for value in attachment_hashes
    ]
    if normalized_attachments != sorted(set(normalized_attachments)):
        raise ValueError("Dispatch attachment hashes are not canonical and unique")

    prior_count = binding.get("prior_followup_count")
    max_sends = binding.get("max_proactive_sends")
    if (
        isinstance(prior_count, bool)
        or not isinstance(prior_count, int)
        or prior_count < 0
    ):
        raise ValueError("Dispatch prior follow-up count is invalid")
    if isinstance(max_sends, bool) or not isinstance(max_sends, int) or max_sends < 1:
        raise ValueError("Dispatch maximum proactive send count is invalid")
    if prior_count >= max_sends:
        raise ValueError("Dispatch proactive follow-up allowance is exhausted")

    expected = canonical_object_sha256(binding, omit={"dispatch_sha256"})
    actual = normalize_sha256(binding.get("dispatch_sha256"), "Dispatch binding")
    if binding["dispatch_sha256"] != actual or actual != expected:
        raise ValueError("Follow-up dispatch binding integrity check failed")
    return actual


def build_followup_dispatch_binding(
    lane_id: str,
    rendered: dict[str, Any],
    *,
    recipient_route: dict[str, Any],
    attachment_sha256s: list[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    if not isinstance(rendered, dict):
        raise ValueError("Rendered follow-up must be an object")
    if rendered.get("lane_id") != lane_id:
        raise ValueError("Rendered follow-up lane mismatch")
    if not str(rendered.get("status", "")).startswith("READY_FOR_"):
        raise ValueError("Rendered follow-up is not ready for action-time review")
    if (
        rendered.get("send_allowed_by_builder") is not False
        or rendered.get("send_performed") is not False
    ):
        raise ValueError("Rendered follow-up exposes send authority")
    if rendered.get("duplicate_send_blocked") is not False:
        raise ValueError("Rendered follow-up is duplicate-blocked")
    if (
        rendered.get("mailbox_rechecked") is not True
        or rendered.get("no_reply_confirmed") is not True
    ):
        raise ValueError("Rendered follow-up lacks no-reply mailbox evidence")

    subject = rendered.get("subject")
    body = rendered.get("body")
    if not isinstance(subject, str) or not subject.strip():
        raise ValueError("Rendered follow-up subject is missing")
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Rendered follow-up body is missing")

    normalized_attachments = sorted(
        normalize_sha256(value, "Dispatch attachment")
        for value in attachment_sha256s
    )
    if len(normalized_attachments) != len(set(normalized_attachments)):
        raise ValueError("Dispatch contains a duplicate attachment")
    attachment_count = rendered.get("attachment_count")
    if (
        isinstance(attachment_count, bool)
        or not isinstance(attachment_count, int)
        or attachment_count != len(normalized_attachments)
    ):
        raise ValueError("Dispatch attachment count does not match the render")
    if rendered.get("attachment_policy") == "NONE" and normalized_attachments:
        raise ValueError("Dispatch attachments are prohibited by the template")

    binding: dict[str, Any] = {
        "schema": FOLLOWUP_DISPATCH_BINDING_SCHEMA,
        "lane_id": lane_id,
        "template_id": str(rendered.get("template_id") or ""),
        "subject_sha256": hashlib.sha256(subject.encode("utf-8")).hexdigest().upper(),
        "body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest().upper(),
        "recipient_route_sha256": recipient_route_sha256(recipient_route),
        "attachment_sha256s": normalized_attachments,
        "mailbox_check_receipt_sha256": normalize_sha256(
            rendered.get("mailbox_check_receipt_sha256"),
            "Dispatch mailbox receipt",
        ),
        "prior_followup_count": rendered.get("prior_followup_count"),
        "max_proactive_sends": rendered.get("max_proactive_sends"),
    }
    binding["dispatch_sha256"] = canonical_object_sha256(
        binding, omit={"dispatch_sha256"}
    )
    validate_followup_dispatch_binding(binding)
    return binding


def expected_followup_approval_phrase(binding: dict[str, Any]) -> str:
    dispatch_sha = validate_followup_dispatch_binding(binding)
    return (
        f"APPROVE SEND {str(binding['lane_id']).upper()} "
        f"{dispatch_sha[:12]}"
    )


def validate_action_time_approval_receipt(
    receipt: dict[str, Any],
    *,
    dispatch_binding: dict[str, Any],
    as_of_utc: str,
) -> tuple[datetime, datetime, str]:
    dispatch_sha = validate_followup_dispatch_binding(dispatch_binding)
    if not isinstance(receipt, dict) or set(receipt) != ACTION_TIME_APPROVAL_FIELDS:
        raise ValueError("Action-time approval receipt fields are invalid")
    if receipt.get("schema") != ACTION_TIME_APPROVAL_SCHEMA:
        raise ValueError("Action-time approval receipt schema is invalid")
    if receipt.get("approval_scope") != ACTION_TIME_APPROVAL_SCOPE:
        raise ValueError("Action-time approval scope is invalid")

    matches = {
        "lane_id": dispatch_binding["lane_id"],
        "template_id": dispatch_binding["template_id"],
        "dispatch_sha256": dispatch_sha,
        "mailbox_check_receipt_sha256": dispatch_binding[
            "mailbox_check_receipt_sha256"
        ],
        "prior_followup_count": dispatch_binding["prior_followup_count"],
    }
    for field, expected in matches.items():
        if receipt.get(field) != expected:
            raise ValueError(f"Action-time approval {field} mismatch")

    approved_at = parse_aware_utc(str(receipt.get("approved_utc") or ""))
    expires_at = parse_aware_utc(str(receipt.get("expires_utc") or ""))
    as_of = parse_aware_utc(as_of_utc)
    if receipt["approved_utc"] != utc_iso(approved_at):
        raise ValueError("Action-time approval timestamp is not canonical")
    if receipt["expires_utc"] != utc_iso(expires_at):
        raise ValueError("Action-time approval expiry is not canonical")
    expected_expiry = approved_at + timedelta(
        seconds=ACTION_TIME_APPROVAL_MAX_AGE_SECONDS
    )
    if expires_at != expected_expiry:
        raise ValueError("Action-time approval expiry window is invalid")
    if as_of < approved_at:
        raise ValueError("Action-time approval timestamp is in the future")
    if as_of > expires_at:
        raise ValueError("Action-time approval is stale")

    expected_phrase = expected_followup_approval_phrase(dispatch_binding)
    expected_code_sha = hashlib.sha256(
        expected_phrase.encode("utf-8")
    ).hexdigest().upper()
    actual_code_sha = normalize_sha256(
        receipt.get("approval_code_sha256"), "Action-time approval code"
    )
    if actual_code_sha != expected_code_sha:
        raise ValueError("Action-time approval code does not match the exact dispatch")

    expected_unlock_proof = action_time_human_unlock_proof(
        receipt, configured_human_unlock_token()
    )
    actual_unlock_proof = normalize_sha256(
        receipt.get("human_unlock_proof_sha256"),
        "Action-time HumanUnlock proof",
    )
    if not hmac.compare_digest(actual_unlock_proof, expected_unlock_proof):
        raise ValueError("Action-time HumanUnlock proof is invalid")

    expected_receipt_sha = canonical_object_sha256(
        receipt, omit={"approval_receipt_sha256"}
    )
    actual_receipt_sha = normalize_sha256(
        receipt.get("approval_receipt_sha256"), "Action-time approval receipt"
    )
    if actual_receipt_sha != expected_receipt_sha:
        raise ValueError("Action-time approval receipt integrity check failed")
    return approved_at, expires_at, actual_receipt_sha


def build_action_time_approval_receipt(
    dispatch_binding: dict[str, Any],
    *,
    approved_utc: str,
    approval_phrase: str,
    human_unlock_token: str,
) -> dict[str, Any]:
    dispatch_sha = validate_followup_dispatch_binding(dispatch_binding)
    configured_token = validate_presented_human_unlock_token(
        human_unlock_token
    )
    expected_phrase = expected_followup_approval_phrase(dispatch_binding)
    if approval_phrase.strip() != expected_phrase:
        raise ValueError(
            "Action-time approval phrase does not match the exact dispatch"
        )
    approved_at = parse_aware_utc(approved_utc)
    receipt: dict[str, Any] = {
        "schema": ACTION_TIME_APPROVAL_SCHEMA,
        "approval_scope": ACTION_TIME_APPROVAL_SCOPE,
        "lane_id": dispatch_binding["lane_id"],
        "template_id": dispatch_binding["template_id"],
        "dispatch_sha256": dispatch_sha,
        "mailbox_check_receipt_sha256": dispatch_binding[
            "mailbox_check_receipt_sha256"
        ],
        "prior_followup_count": dispatch_binding["prior_followup_count"],
        "approved_utc": utc_iso(approved_at),
        "expires_utc": utc_iso(
            approved_at
            + timedelta(seconds=ACTION_TIME_APPROVAL_MAX_AGE_SECONDS)
        ),
        "approval_code_sha256": hashlib.sha256(
            expected_phrase.encode("utf-8")
        ).hexdigest().upper(),
    }
    receipt["human_unlock_proof_sha256"] = action_time_human_unlock_proof(
        receipt, configured_token
    )
    receipt["approval_receipt_sha256"] = canonical_object_sha256(
        receipt, omit={"approval_receipt_sha256"}
    )
    validate_action_time_approval_receipt(
        receipt,
        dispatch_binding=dispatch_binding,
        as_of_utc=utc_iso(approved_at),
    )
    return receipt


def validate_authorized_dispatch(
    authorization: dict[str, Any], *, as_of_utc: str
) -> str:
    if not isinstance(authorization, dict) or set(authorization) != (
        AUTHORIZED_DISPATCH_FIELDS
    ):
        raise ValueError("Authorized dispatch fields are invalid")
    if authorization.get("schema") != AUTHORIZED_DISPATCH_SCHEMA:
        raise ValueError("Authorized dispatch schema is invalid")
    if authorization.get("status") != "READY_FOR_EXPLICIT_GMAIL_SEND":
        raise ValueError("Authorized dispatch status is invalid")
    if (
        authorization.get("approval_scope") != ACTION_TIME_APPROVAL_SCOPE
        or authorization.get("single_use") is not True
        or authorization.get("send_allowed_by_builder") is not False
        or authorization.get("send_performed") is not False
    ):
        raise ValueError("Authorized dispatch controls are invalid")
    for field, label in (
        ("dispatch_sha256", "Authorized dispatch binding"),
        ("mailbox_check_receipt_sha256", "Authorized mailbox receipt"),
        ("action_approval_receipt_sha256", "Authorized approval receipt"),
    ):
        normalized = normalize_sha256(authorization.get(field), label)
        if authorization[field] != normalized:
            raise ValueError(f"{label} SHA-256 is not canonical")
    prior_count = authorization.get("prior_followup_count")
    if (
        isinstance(prior_count, bool)
        or not isinstance(prior_count, int)
        or prior_count < 0
    ):
        raise ValueError("Authorized dispatch prior count is invalid")

    authorized_at = parse_aware_utc(str(authorization.get("authorized_utc") or ""))
    expires_at = parse_aware_utc(str(authorization.get("expires_utc") or ""))
    as_of = parse_aware_utc(as_of_utc)
    if authorization["authorized_utc"] != utc_iso(authorized_at):
        raise ValueError("Authorized dispatch timestamp is not canonical")
    if authorization["expires_utc"] != utc_iso(expires_at):
        raise ValueError("Authorized dispatch expiry is not canonical")
    if authorized_at > as_of:
        raise ValueError("Authorized dispatch timestamp is in the future")
    if as_of > expires_at:
        raise ValueError("Authorized dispatch is stale")

    expected = canonical_object_sha256(
        authorization, omit={"authorization_sha256"}
    )
    actual = normalize_sha256(
        authorization.get("authorization_sha256"), "Dispatch authorization"
    )
    if actual != expected:
        raise ValueError("Authorized dispatch integrity check failed")
    return actual


def authorize_followup_dispatch(
    dispatch_binding: dict[str, Any],
    approval_receipt: dict[str, Any],
    mailbox_check_receipt: dict[str, Any],
    *,
    as_of_utc: str,
    send_ledger: dict[str, Any] | None = None,
) -> dict[str, Any]:
    dispatch_sha = validate_followup_dispatch_binding(dispatch_binding)
    as_of = parse_aware_utc(as_of_utc)
    mailbox_checked_at, mailbox_receipt_sha = validate_mailbox_recheck_receipt(
        mailbox_check_receipt,
        expected_lane_id=str(dispatch_binding["lane_id"]),
    )
    if mailbox_receipt_sha != dispatch_binding["mailbox_check_receipt_sha256"]:
        raise ValueError("Dispatch mailbox receipt mismatch")
    mailbox_age_seconds = int((as_of - mailbox_checked_at).total_seconds())
    if mailbox_age_seconds < 0:
        raise ValueError("Dispatch mailbox recheck timestamp is in the future")
    if mailbox_age_seconds > MAILBOX_RECHECK_MAX_AGE_SECONDS:
        raise ValueError("Dispatch mailbox recheck is stale")

    approved_at, expires_at, approval_receipt_sha = (
        validate_action_time_approval_receipt(
            approval_receipt,
            dispatch_binding=dispatch_binding,
            as_of_utc=as_of_utc,
        )
    )
    if approved_at < mailbox_checked_at:
        raise ValueError("Action-time approval predates the mailbox recheck")

    ledger = send_ledger or read_json(FOLLOWUP_SEND_LEDGER)
    policy_payload = read_json(FOLLOWUP_POLICY_CONFIG)
    registry = read_json(RESPONSE_TEMPLATE_REGISTRY)
    policies = {
        row["lane_id"]: row for row in policy_payload["lane_policies"]
    }
    template_ids = {row["template_id"] for row in registry["templates"]}
    counts, _ = validate_followup_send_ledger(
        ledger, policies, template_ids, as_of=as_of
    )
    for receipt in ledger["receipts"]:
        if receipt.get("action_approval_receipt_sha256") == approval_receipt_sha:
            raise ValueError("Action-time approval receipt has already been consumed")
        if receipt.get("dispatch_sha256") == dispatch_sha:
            raise ValueError("Exact follow-up dispatch has already been sent")

    lane_id = str(dispatch_binding["lane_id"])
    policy = policies.get(lane_id)
    if policy is None:
        raise ValueError("Dispatch lane is not configured")
    if policy.get("mode") not in PROACTIVE_OUTREACH_MODES:
        raise ValueError("Dispatch lane does not permit proactive outreach")
    if policy.get("eligible_template_id") != dispatch_binding["template_id"]:
        raise ValueError("Dispatch template no longer matches policy")
    if int(policy["max_proactive_sends"]) != dispatch_binding[
        "max_proactive_sends"
    ]:
        raise ValueError("Dispatch send limit no longer matches policy")
    current_count = counts.get(lane_id, 0)
    if current_count != dispatch_binding["prior_followup_count"]:
        raise ValueError("Dispatch prior follow-up count has changed")
    if current_count >= int(policy["max_proactive_sends"]):
        raise ValueError("Dispatch proactive follow-up allowance is exhausted")
    if as_of < parse_aware_utc(str(policy["not_before_utc"])):
        raise ValueError("Dispatch hold boundary has not elapsed")
    deadline_utc = policy.get("deadline_utc")
    if deadline_utc and as_of >= parse_aware_utc(str(deadline_utc)):
        raise ValueError("Dispatch deadline has passed")

    authorization: dict[str, Any] = {
        "schema": AUTHORIZED_DISPATCH_SCHEMA,
        "status": "READY_FOR_EXPLICIT_GMAIL_SEND",
        "lane_id": lane_id,
        "template_id": dispatch_binding["template_id"],
        "dispatch_sha256": dispatch_sha,
        "mailbox_check_receipt_sha256": mailbox_receipt_sha,
        "action_approval_receipt_sha256": approval_receipt_sha,
        "approval_scope": ACTION_TIME_APPROVAL_SCOPE,
        "prior_followup_count": current_count,
        "authorized_utc": utc_iso(as_of),
        "expires_utc": utc_iso(expires_at),
        "single_use": True,
        "send_allowed_by_builder": False,
        "send_performed": False,
    }
    authorization["authorization_sha256"] = canonical_object_sha256(
        authorization, omit={"authorization_sha256"}
    )
    validate_authorized_dispatch(authorization, as_of_utc=as_of_utc)
    return authorization


def build_followup_send_receipt(
    authorization: dict[str, Any],
    *,
    sent_message_receipt_sha256: str,
    sent_utc: str,
) -> dict[str, Any]:
    sent_at = parse_aware_utc(sent_utc)
    authorization_sha = validate_authorized_dispatch(
        authorization, as_of_utc=utc_iso(sent_at)
    )
    return {
        "delivery_state": "SENT",
        "lane_id": authorization["lane_id"],
        "template_id": authorization["template_id"],
        "sent_utc": utc_iso(sent_at),
        "sent_message_receipt_sha256": normalize_sha256(
            sent_message_receipt_sha256, "Sent message receipt"
        ),
        "approval_scope": ACTION_TIME_APPROVAL_SCOPE,
        "prior_followup_count": authorization["prior_followup_count"],
        "mailbox_check_receipt_sha256": authorization[
            "mailbox_check_receipt_sha256"
        ],
        "dispatch_sha256": authorization["dispatch_sha256"],
        "action_approval_receipt_sha256": authorization[
            "action_approval_receipt_sha256"
        ],
        "authorization_sha256": authorization_sha,
    }


def build_payload(as_of_utc: str | None = None) -> dict[str, Any]:
    as_of = (
        datetime.now(timezone.utc)
        if as_of_utc is None
        else parse_aware_utc(as_of_utc)
    )
    reconciliation = read_json(EMAIL_RECONCILIATION)
    registry = read_json(RESPONSE_TEMPLATE_REGISTRY)
    policy_config = read_json(FOLLOWUP_POLICY_CONFIG)
    send_ledger = read_json(FOLLOWUP_SEND_LEDGER)
    _, _, sent_counts, sent_receipt_digests = validate_sources(
        reconciliation,
        registry,
        policy_config,
        send_ledger,
        as_of=as_of,
    )

    actions = [
        evaluate_lane(lane, as_of, sent_counts)
        for lane in reconciliation["lanes"]
    ]
    action_counts = Counter(row["action_state"] for row in actions)
    followup_due_count = action_counts.get("RECHECK_MAILBOX_BEFORE_DRAFT", 0)
    deadline_due_count = action_counts.get(
        "DEADLINE_ACTION_DUE_MAILBOX_RECHECK", 0
    )
    due_count = followup_due_count + deadline_due_count
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "as_of_utc": utc_iso(as_of),
        "status": (
            "DEADLINE_ACTION_DUE_HUMAN_REVIEW"
            if deadline_due_count
            else (
                "FOLLOWUP_RECHECK_DUE_HUMAN_REVIEW"
                if followup_due_count
                else "NO_EXTERNAL_FOLLOWUP_DUE"
            )
        ),
        "summary": {
            "lane_count": len(actions),
            "action_state_counts": dict(sorted(action_counts.items())),
            "due_for_mailbox_recheck_count": due_count,
            "deadline_action_due_count": deadline_due_count,
            "followup_recheck_due_count": followup_due_count,
            "held_no_send_count": action_counts.get("HELD_NO_SEND", 0),
            "draft_rendered_count": sum(1 for row in actions if row["draft_rendered"]),
            "send_now_count": sum(1 for row in actions if row["send_now"]),
            "recorded_proactive_send_count": sum(sent_counts.values()),
            "conflicting_gmail_draft_count": sum(
                row["conflicting_gmail_draft_count"] for row in actions
            ),
            "conflicting_gmail_draft_lane_count": sum(
                1
                for row in actions
                if row["conflicting_gmail_draft_count"] > 0
            ),
            "external_send_allowed_without_human": False,
        },
        "actions": actions,
        "controls": {
            "builder_can_send_email": False,
            "past_hold_authorizes_send": False,
            "inbox_recheck_required_before_draft": True,
            "mailbox_recheck_max_age_seconds": MAILBOX_RECHECK_MAX_AGE_SECONDS,
            "mailbox_recheck_receipt_required": True,
            "exact_dispatch_binding_required_before_send": True,
            "single_use_action_time_approval_required": True,
            "private_human_unlock_bearer_token_required": True,
            "action_time_approval_max_age_seconds": (
                ACTION_TIME_APPROVAL_MAX_AGE_SECONDS
            ),
            "proactive_send_count_derived_from_sealed_ledger": True,
            "conflicting_gmail_drafts_fail_closed": True,
            "action_time_human_review_required": True,
            "final_send_performed": False,
        },
        "source_evidence": {
            "email_reconciliation": source_status(EMAIL_RECONCILIATION),
            "response_template_registry": source_status(RESPONSE_TEMPLATE_REGISTRY),
            "response_registry_builder": source_status(RESPONSE_REGISTRY_BUILDER),
            "followup_policy_config": source_status(FOLLOWUP_POLICY_CONFIG),
            "followup_send_ledger": source_status(FOLLOWUP_SEND_LEDGER),
        },
        "followup_send_receipt_digests": dict(sorted(sent_receipt_digests.items())),
        "claim_boundary": (
            "This queue evaluates communication timing and routing controls only. A hold "
            "expiration or open deadline requires a fresh mailbox check that is recent, "
            "timestamped, and receipted; a current draft is not a sent message, and prior "
            "proactive sends are derived from a sealed receipt ledger. None of those "
            "conditions authorizes a draft or send. Any future send must also "
            "bind the exact subject, body, recipient route, attachments, mailbox receipt, "
            "single-use action-time approval, and possession of a private HumanUnlock "
            "bearer token before an explicit Gmail action. The bearer proof records token "
            "possession only; it does not establish identity or legal signing authority. "
            "The queue does not establish submission, receipt, selection, funding, endorsement, "
            "validation, technical performance, or authority to disclose private information."
        ),
    }
    payload["queue_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest().upper()
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if payload.get("schema") != SCHEMA:
        raise ValueError("Follow-up queue schema is invalid")
    if payload["summary"]["lane_count"] != len(payload["actions"]):
        raise ValueError("Follow-up queue lane count is invalid")
    if payload["summary"]["send_now_count"] != 0:
        raise ValueError("Follow-up queue attempted an autonomous send")
    if payload["summary"]["draft_rendered_count"] != 0:
        raise ValueError("Follow-up queue rendered a draft without a fresh inbox check")
    if any(row["send_now"] for row in payload["actions"]):
        raise ValueError("Follow-up queue contains a send-now row")
    if payload["summary"]["recorded_proactive_send_count"] != sum(
        row["recorded_proactive_send_count"] for row in payload["actions"]
    ):
        raise ValueError("Follow-up send ledger count is inconsistent")
    quarantined_actions = [
        row
        for row in payload["actions"]
        if row.get("conflicting_gmail_draft_count", 0) > 0
    ]
    if (
        payload["summary"]["conflicting_gmail_draft_count"]
        != sum(
            row["conflicting_gmail_draft_count"]
            for row in quarantined_actions
        )
        or payload["summary"]["conflicting_gmail_draft_lane_count"]
        != len(quarantined_actions)
        or any(
            row.get("draft_quarantine_status")
            != "QUARANTINED_NOT_SENDABLE"
            or row.get("send_now") is not False
            or row.get("draft_rendered") is not False
            for row in quarantined_actions
        )
    ):
        raise ValueError("Follow-up queue draft quarantine is incomplete")
    due_actions = [
        row
        for row in payload["actions"]
        if row["action_state"] in DUE_MAILBOX_RECHECK_STATES
    ]
    if (
        payload["summary"]["due_for_mailbox_recheck_count"] != len(due_actions)
        or payload["summary"]["deadline_action_due_count"]
        != sum(
            row["action_state"] == "DEADLINE_ACTION_DUE_MAILBOX_RECHECK"
            for row in due_actions
        )
        or payload["summary"]["followup_recheck_due_count"]
        != sum(
            row["action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
            for row in due_actions
        )
        or any(not row["inbox_recheck_required"] for row in due_actions)
    ):
        raise ValueError("A due proactive outreach bypasses the inbox recheck")
    deadline_due_actions = [
        row
        for row in due_actions
        if row["action_state"] == "DEADLINE_ACTION_DUE_MAILBOX_RECHECK"
    ]
    if any(
        not row.get("deadline_utc")
        or row.get("eligible_template_id") != "INITIAL_PARTNER_TEAMING_INQUIRY"
        or row.get("recorded_proactive_send_count") != 0
        or row.get("send_now") is not False
        for row in deadline_due_actions
    ):
        raise ValueError("Deadline-bound initial outreach control is incomplete")
    controls = payload.get("controls", {})
    if (
        controls.get("builder_can_send_email") is not False
        or controls.get("exact_dispatch_binding_required_before_send") is not True
        or controls.get("single_use_action_time_approval_required") is not True
        or controls.get("private_human_unlock_bearer_token_required") is not True
        or controls.get("action_time_approval_max_age_seconds")
        != ACTION_TIME_APPROVAL_MAX_AGE_SECONDS
        or controls.get("conflicting_gmail_drafts_fail_closed") is not True
    ):
        raise ValueError("Follow-up queue action-time controls are unsafe")
    actual_queue_sha = normalize_sha256(
        payload.get("queue_sha256"), "Follow-up queue"
    )
    expected_queue_sha = canonical_object_sha256(
        payload, omit={"queue_sha256"}
    )
    if actual_queue_sha != expected_queue_sha:
        raise ValueError("Follow-up queue integrity check failed")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Outreach Follow-up Action Queue - 2026-07-18",
        "",
        f"- Status: `{payload['status']}`",
        f"- As of UTC: `{payload['as_of_utc']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Due for mailbox recheck: `{summary['due_for_mailbox_recheck_count']}`",
        f"- Deadline actions due: `{summary['deadline_action_due_count']}`",
        f"- Held no-send: `{summary['held_no_send_count']}`",
        f"- Drafts rendered: `{summary['draft_rendered_count']}`",
        f"- Conflicting Gmail drafts: `{summary['conflicting_gmail_draft_count']}`",
        f"- Quarantined draft lanes: `{summary['conflicting_gmail_draft_lane_count']}`",
        f"- Send now: `{summary['send_now_count']}`",
        f"- Autonomous external send allowed: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Queue SHA-256: `{payload['queue_sha256']}`",
        "",
        "## Action Queue",
        "",
        "| Organization | Mode | Action state | Deadline UTC | Not before | Eligible template |",
        "|---|---|---|---|---|---|",
    ]
    for row in payload["actions"]:
        lines.append(
            f"| {row['organization']} | `{row['follow_up_mode']}` | "
            f"`{row['action_state']}` | `{row.get('deadline_utc') or 'none'}` | "
            f"`{row['not_before_utc'] or 'none'}` | "
            f"`{row['eligible_template_id'] or 'none'}` |"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed outreach follow-up action queue."
    )
    parser.add_argument(
        "--as-of-utc",
        help="Aware timestamp to evaluate; defaults to the current UTC time.",
    )
    args = parser.parse_args()

    payload = build_payload(args.as_of_utc)
    validate_payload(payload)
    write_json(CANONICAL_JSON, payload)
    write_text(CANONICAL_MD, render_markdown(payload))
    write_json(LATEST_JSON, payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lane_count": payload["summary"]["lane_count"],
                "due_for_mailbox_recheck_count": payload["summary"][
                    "due_for_mailbox_recheck_count"
                ],
                "held_no_send_count": payload["summary"]["held_no_send_count"],
                "send_now_count": payload["summary"]["send_now_count"],
                "json": CANONICAL_JSON.relative_to(ROOT).as_posix(),
                "markdown": CANONICAL_MD.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
