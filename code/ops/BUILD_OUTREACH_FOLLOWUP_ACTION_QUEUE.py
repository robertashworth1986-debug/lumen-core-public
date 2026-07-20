from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
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
REFERENCE_AS_OF_UTC = "2026-07-18T12:20:24Z"
MAILBOX_RECHECK_MAX_AGE_SECONDS = 15 * 60
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
    ):
        raise ValueError("Follow-up send ledger controls are unsafe")
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
        if policy.get("mode") != "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD":
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
        sent_receipt_sha = normalize_sha256(
            receipt.get("sent_message_receipt_sha256"), "Sent message receipt"
        )
        if sent_receipt_sha in seen_sent_receipts:
            raise ValueError("Follow-up send ledger contains a duplicate receipt")
        seen_sent_receipts.add(sent_receipt_sha)
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
    if (
        reconciliation.get("schema")
        != "lumencore.email_action_reconciliation.v1"
        or reconciliation.get("status")
        not in {
            "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION",
            "DEADLINE_BEARING_PORTAL_ACTION_OPEN_NO_EMAIL_SEND",
        }
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
        "max_proactive_sends": policy.get("max_proactive_sends"),
        "recorded_proactive_send_count": recorded_send_count,
        "rationale": policy["rationale"],
        "send_now": False,
        "draft_rendered": False,
        "inbox_recheck_required": False,
        "action_time_human_review_required": True,
        "next_action": lane["next_action"],
    }
    for key in (
        "deadline_date",
        "deadline_utc",
        "deadline_time_status",
        "deadline_timezone_status",
        "internal_finish_target",
        "financial_aid_form_action_required",
        "initial_application_resubmission_required",
        "final_form_submit_human_gated",
    ):
        if key in lane:
            row[key] = lane[key]

    if mode in MODE_STATES:
        row["action_state"] = MODE_STATES[mode]
        return row
    if mode != "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD":
        raise ValueError(f"Unsupported follow-up mode: {mode}")

    if recorded_send_count >= int(policy["max_proactive_sends"]):
        row.update(
            {
                "action_state": "FOLLOWUP_LIMIT_REACHED_NO_SEND",
                "next_action": (
                    "The bounded proactive follow-up allowance is exhausted. Monitor the "
                    "existing thread and respond only to a specific inbound request."
                ),
            }
        )
        return row

    not_before = parse_aware_utc(str(policy["not_before_utc"]))
    if as_of < not_before:
        row["action_state"] = "HELD_NO_SEND"
        row["hold_seconds_remaining"] = int((not_before - as_of).total_seconds())
        return row

    row.update(
        {
            "action_state": "RECHECK_MAILBOX_BEFORE_DRAFT",
            "hold_seconds_remaining": 0,
            "inbox_recheck_required": True,
            "next_action": (
                "Recheck the complete thread for any reply or delivery change. Only if no "
                "reply exists may one bounded draft be rendered for action-time review."
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
    mailbox_rechecked: bool,
    mailbox_rechecked_utc: str,
    mailbox_check_receipt_sha256: str,
    no_reply_confirmed: bool,
) -> dict[str, Any]:
    queue = build_payload(as_of_utc)
    action = next(
        (row for row in queue["actions"] if row["lane_id"] == lane_id), None
    )
    if action is None:
        raise ValueError(f"Unknown follow-up lane: {lane_id}")
    if action["action_state"] != "RECHECK_MAILBOX_BEFORE_DRAFT":
        raise ValueError("Follow-up is not due for mailbox recheck")
    if not mailbox_rechecked or not no_reply_confirmed:
        raise ValueError("Fresh mailbox recheck and no-reply confirmation are required")
    as_of = parse_aware_utc(as_of_utc)
    mailbox_checked_at = parse_aware_utc(mailbox_rechecked_utc)
    mailbox_check_age_seconds = int((as_of - mailbox_checked_at).total_seconds())
    if mailbox_check_age_seconds < 0:
        raise ValueError("Mailbox recheck timestamp cannot be in the future")
    if mailbox_check_age_seconds > MAILBOX_RECHECK_MAX_AGE_SECONDS:
        raise ValueError("Mailbox recheck is stale")
    receipt = normalize_sha256(
        mailbox_check_receipt_sha256, "Mailbox recheck receipt"
    )
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
    rendered["queue_action_state"] = action["action_state"]
    rendered["mailbox_rechecked"] = True
    rendered["mailbox_rechecked_utc"] = utc_iso(mailbox_checked_at)
    rendered["mailbox_recheck_age_seconds"] = mailbox_check_age_seconds
    rendered["mailbox_check_receipt_sha256"] = receipt
    rendered["no_reply_confirmed"] = True
    rendered["prior_followup_count"] = action["recorded_proactive_send_count"]
    rendered["max_proactive_sends"] = action["max_proactive_sends"]
    return rendered


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
    due_count = action_counts.get("RECHECK_MAILBOX_BEFORE_DRAFT", 0)
    deadline_portal_count = sum(
        1
        for row in actions
        if row["action_state"] == "HUMAN_PORTAL_ACTION_OPEN"
        and (row.get("deadline_date") is not None or row.get("deadline_utc") is not None)
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "as_of_utc": utc_iso(as_of),
        "status": (
            "FOLLOWUP_RECHECK_DUE_HUMAN_REVIEW"
            if due_count
            else (
                "DEADLINE_PORTAL_ACTION_OPEN_NO_EMAIL_SEND"
                if deadline_portal_count
                else "NO_EXTERNAL_FOLLOWUP_DUE"
            )
        ),
        "summary": {
            "lane_count": len(actions),
            "action_state_counts": dict(sorted(action_counts.items())),
            "due_for_mailbox_recheck_count": due_count,
            "held_no_send_count": action_counts.get("HELD_NO_SEND", 0),
            "human_portal_action_count": action_counts.get(
                "HUMAN_PORTAL_ACTION_OPEN", 0
            ),
            "deadline_bearing_portal_action_count": deadline_portal_count,
            "draft_rendered_count": sum(1 for row in actions if row["draft_rendered"]),
            "send_now_count": sum(1 for row in actions if row["send_now"]),
            "recorded_proactive_send_count": sum(sent_counts.values()),
            "external_send_allowed_without_human": False,
        },
        "actions": actions,
        "controls": {
            "builder_can_send_email": False,
            "past_hold_authorizes_send": False,
            "inbox_recheck_required_before_draft": True,
            "mailbox_recheck_max_age_seconds": MAILBOX_RECHECK_MAX_AGE_SECONDS,
            "mailbox_recheck_receipt_required": True,
            "proactive_send_count_derived_from_sealed_ledger": True,
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
            "expiration requires a fresh mailbox check that is recent, timestamped, and "
            "receipted; prior proactive sends are derived from a sealed receipt ledger, "
            "and neither condition authorizes a draft or send. "
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
    if any(
        row["action_state"] == "RECHECK_MAILBOX_BEFORE_DRAFT"
        and not row["inbox_recheck_required"]
        for row in payload["actions"]
    ):
        raise ValueError("A due follow-up bypasses the inbox recheck")
    if len(payload.get("queue_sha256", "")) != 64:
        raise ValueError("Follow-up queue hash is invalid")


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Outreach Follow-up Action Queue - 2026-07-18",
        "",
        f"- Status: `{payload['status']}`",
        f"- As of UTC: `{payload['as_of_utc']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Due for mailbox recheck: `{summary['due_for_mailbox_recheck_count']}`",
        f"- Held no-send: `{summary['held_no_send_count']}`",
        f"- Human portal actions: `{summary['human_portal_action_count']}`",
        f"- Deadline-bearing portal actions: `{summary['deadline_bearing_portal_action_count']}`",
        f"- Drafts rendered: `{summary['draft_rendered_count']}`",
        f"- Send now: `{summary['send_now_count']}`",
        f"- Autonomous external send allowed: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Queue SHA-256: `{payload['queue_sha256']}`",
        "",
        "## Action Queue",
        "",
        "| Organization | Mode | Action state | Deadline | Not before | Eligible template |",
        "|---|---|---|---|---|---|",
    ]
    for row in payload["actions"]:
        lines.append(
            f"| {row['organization']} | `{row['follow_up_mode']}` | "
            f"`{row['action_state']}` | "
            f"`{row.get('deadline_date') or row.get('deadline_utc') or 'none'}` | "
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
