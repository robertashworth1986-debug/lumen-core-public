from __future__ import annotations

import argparse
import hashlib
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
FOLLOWUP_POLICY_CONFIG = ROOT / "config" / "outreach_followup_policies_v1.json"

CANONICAL_JSON = SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
CANONICAL_MD = SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.md"
LATEST_JSON = OUT_OPS / "outreach_followup_action_queue_latest.json"

SCHEMA = "lumencore.outreach_followup_action_queue.v1"
DEFAULT_AS_OF_UTC = "2026-07-18T12:20:24Z"

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


def validate_sources(
    reconciliation: dict[str, Any],
    registry: dict[str, Any],
    policy_config: dict[str, Any],
) -> tuple[set[str], dict[str, dict[str, Any]]]:
    if (
        reconciliation.get("schema")
        != "lumencore.email_action_reconciliation.v1"
        or reconciliation.get("status")
        != "NO_UNANSWERED_DEADLINE_CRITICAL_EMAIL_ACTION"
        or reconciliation.get("summary", {}).get("send_now_count") != 0
    ):
        raise ValueError("Email reconciliation is missing, stale, or send-active")
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
    return template_ids, policies


def evaluate_lane(lane: dict[str, Any], as_of: datetime) -> dict[str, Any]:
    policy = lane["follow_up_policy"]
    mode = policy["mode"]
    row = {
        "lane_id": lane["lane_id"],
        "organization": lane["organization"],
        "source_state": lane["state"],
        "follow_up_mode": mode,
        "current_response_template_id": lane.get("response_template_id"),
        "eligible_template_id": policy.get("eligible_template_id"),
        "not_before_utc": policy.get("not_before_utc"),
        "max_proactive_sends": policy.get("max_proactive_sends"),
        "rationale": policy["rationale"],
        "send_now": False,
        "draft_rendered": False,
        "inbox_recheck_required": False,
        "action_time_human_review_required": True,
        "next_action": lane["next_action"],
    }

    if mode in MODE_STATES:
        row["action_state"] = MODE_STATES[mode]
        return row
    if mode != "ONE_BOUNDED_FOLLOW_UP_AFTER_HOLD":
        raise ValueError(f"Unsupported follow-up mode: {mode}")

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


def build_payload(as_of_utc: str = DEFAULT_AS_OF_UTC) -> dict[str, Any]:
    as_of = parse_aware_utc(as_of_utc)
    reconciliation = read_json(EMAIL_RECONCILIATION)
    registry = read_json(RESPONSE_TEMPLATE_REGISTRY)
    policy_config = read_json(FOLLOWUP_POLICY_CONFIG)
    validate_sources(reconciliation, registry, policy_config)

    actions = [evaluate_lane(lane, as_of) for lane in reconciliation["lanes"]]
    action_counts = Counter(row["action_state"] for row in actions)
    due_count = action_counts.get("RECHECK_MAILBOX_BEFORE_DRAFT", 0)
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "as_of_utc": utc_iso(as_of),
        "status": (
            "FOLLOWUP_RECHECK_DUE_HUMAN_REVIEW"
            if due_count
            else "NO_EXTERNAL_FOLLOWUP_DUE"
        ),
        "summary": {
            "lane_count": len(actions),
            "action_state_counts": dict(sorted(action_counts.items())),
            "due_for_mailbox_recheck_count": due_count,
            "held_no_send_count": action_counts.get("HELD_NO_SEND", 0),
            "draft_rendered_count": sum(1 for row in actions if row["draft_rendered"]),
            "send_now_count": sum(1 for row in actions if row["send_now"]),
            "external_send_allowed_without_human": False,
        },
        "actions": actions,
        "controls": {
            "builder_can_send_email": False,
            "past_hold_authorizes_send": False,
            "inbox_recheck_required_before_draft": True,
            "action_time_human_review_required": True,
            "final_send_performed": False,
        },
        "source_evidence": {
            "email_reconciliation": source_status(EMAIL_RECONCILIATION),
            "response_template_registry": source_status(RESPONSE_TEMPLATE_REGISTRY),
            "followup_policy_config": source_status(FOLLOWUP_POLICY_CONFIG),
        },
        "claim_boundary": (
            "This queue evaluates communication timing and routing controls only. A hold "
            "expiration requires a fresh mailbox check and does not authorize a draft or send. "
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
        f"- Drafts rendered: `{summary['draft_rendered_count']}`",
        f"- Send now: `{summary['send_now_count']}`",
        f"- Autonomous external send allowed: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Queue SHA-256: `{payload['queue_sha256']}`",
        "",
        "## Action Queue",
        "",
        "| Organization | Mode | Action state | Not before | Eligible template |",
        "|---|---|---|---|---|",
    ]
    for row in payload["actions"]:
        lines.append(
            f"| {row['organization']} | `{row['follow_up_mode']}` | "
            f"`{row['action_state']}` | `{row['not_before_utc'] or 'none'}` | "
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
    parser.add_argument("--as-of-utc", default=DEFAULT_AS_OF_UTC)
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
