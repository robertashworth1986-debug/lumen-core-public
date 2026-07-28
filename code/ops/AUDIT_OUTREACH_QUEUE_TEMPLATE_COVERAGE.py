from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
DEFAULT_QUEUE = (
    SPRINT_DIR / "OUTREACH_FOLLOWUP_ACTION_QUEUE_2026-07-18.json"
)
DEFAULT_REGISTRY = (
    SPRINT_DIR / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
)
DEFAULT_JSON = (
    ROOT / "out" / "ops" / "outreach_queue_template_coverage_latest.json"
)
DEFAULT_MD = (
    ROOT / "out" / "ops" / "outreach_queue_template_coverage_latest.md"
)

QUEUE_SCHEMA = "lumencore.outreach_followup_action_queue.v1"
REGISTRY_SCHEMA = "lumencore.outreach_response_template_registry.v1"
AUDIT_SCHEMA = "lumencore.outreach_queue_template_coverage.v1"
LANE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_]*$")

EMAIL_DUE_STATES = {
    "DEADLINE_ACTION_DUE_MAILBOX_RECHECK",
    "RECHECK_MAILBOX_BEFORE_DRAFT",
}
NO_SEND_STATES = {
    "CLOSED_NO_ACTION",
    "DEADLINE_PASSED_NO_SEND",
    "FOLLOWUP_LIMIT_REACHED_NO_SEND",
    "HELD_NO_SEND",
    "MONITOR_INBOUND_ONLY",
}
NON_EMAIL_ACTION_STATES = {
    "HUMAN_ACCOUNT_ACTION_OPEN",
    "HUMAN_PORTAL_ACTION_OPEN",
    "PRIVATE_RECONCILIATION_OPEN",
}
ALLOWED_ACTION_STATES = (
    EMAIL_DUE_STATES | NO_SEND_STATES | NON_EMAIL_ACTION_STATES
)
NO_SEND_TEMPLATE_ID = "NO_DUPLICATE_MONITOR"


class CoverageAuditError(ValueError):
    pass


def reject_duplicate_keys(
    pairs: list[tuple[str, Any]],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CoverageAuditError(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def read_json_object(path: Path, error_code: str) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )
    if not isinstance(payload, dict):
        raise CoverageAuditError(error_code)
    return payload


def canonical_sha256(payload: dict[str, Any]) -> str:
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest().upper()


def nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def add_blocker(blockers: list[str], code: str) -> None:
    if code not in blockers:
        blockers.append(code)


def audit_lane(
    action: dict[str, Any],
    template_ids: set[str],
) -> dict[str, Any]:
    blockers: list[str] = []
    lane_id = action.get("lane_id")
    state = action.get("action_state")
    mode = action.get("follow_up_mode")
    eligible = action.get("eligible_template_id")
    current = action.get("current_response_template_id")

    if (
        not isinstance(lane_id, str)
        or LANE_ID_RE.fullmatch(lane_id) is None
    ):
        add_blocker(blockers, "LANE_ID_INVALID")
    if state not in ALLOWED_ACTION_STATES:
        add_blocker(blockers, "ACTION_STATE_UNKNOWN")
    if not nonempty_text(mode):
        add_blocker(blockers, "FOLLOW_UP_MODE_MISSING")
    if not nonempty_text(action.get("next_action")):
        add_blocker(blockers, "NEXT_ACTION_MISSING")
    if action.get("send_now") is not False:
        add_blocker(blockers, "AUTONOMOUS_SEND_STATE_FORBIDDEN")
    if action.get("action_time_human_review_required") is not True:
        add_blocker(blockers, "ACTION_TIME_HUMAN_REVIEW_NOT_REQUIRED")

    for field, template_id in (
        ("eligible", eligible),
        ("current", current),
    ):
        if template_id is not None and template_id not in template_ids:
            add_blocker(
                blockers,
                f"{field.upper()}_TEMPLATE_UNKNOWN",
            )

    coverage_basis = "UNMAPPED"
    if state in EMAIL_DUE_STATES:
        coverage_basis = "SENDABLE_TEMPLATE_BOUND"
        if eligible is None:
            add_blocker(blockers, "DUE_LANE_ELIGIBLE_TEMPLATE_MISSING")
        if current is None:
            add_blocker(blockers, "DUE_LANE_CURRENT_TEMPLATE_MISSING")
        if eligible is not None and current != eligible:
            add_blocker(blockers, "DUE_LANE_TEMPLATE_MISMATCH")
        if action.get("inbox_recheck_required") is not True:
            add_blocker(blockers, "DUE_LANE_INBOX_RECHECK_NOT_REQUIRED")
    elif state == "FOLLOWUP_LIMIT_REACHED_NO_SEND":
        coverage_basis = "EXHAUSTED_ROUTE_MONITOR_BOUND"
        if current != NO_SEND_TEMPLATE_ID:
            add_blocker(blockers, "EXHAUSTED_ROUTE_MONITOR_MISSING")
        if action.get("inbox_recheck_required") is not False:
            add_blocker(blockers, "EXHAUSTED_ROUTE_RECHECK_INVALID")
    elif state in NO_SEND_STATES:
        coverage_basis = "NO_SEND_TEMPLATE_BOUND"
        if current != NO_SEND_TEMPLATE_ID:
            add_blocker(blockers, "NO_SEND_TEMPLATE_MISSING")
        if action.get("inbox_recheck_required") is not False:
            add_blocker(blockers, "NO_SEND_RECHECK_INVALID")
    elif state in NON_EMAIL_ACTION_STATES:
        coverage_basis = "EXPLICIT_NON_EMAIL_ACTION"
        if eligible is not None:
            add_blocker(
                blockers,
                "NON_EMAIL_ACTION_ELIGIBLE_TEMPLATE_FORBIDDEN",
            )
        if current not in (None, NO_SEND_TEMPLATE_ID):
            add_blocker(
                blockers,
                "NON_EMAIL_ACTION_CURRENT_TEMPLATE_INVALID",
            )
        if action.get("inbox_recheck_required") is not False:
            add_blocker(blockers, "NON_EMAIL_ACTION_RECHECK_INVALID")

    return {
        "lane_id": lane_id,
        "action_state": state,
        "follow_up_mode": mode,
        "coverage_basis": coverage_basis,
        "eligible_template_id": eligible,
        "current_response_template_id": current,
        "inbox_recheck_required": action.get(
            "inbox_recheck_required"
        ),
        "send_now": action.get("send_now"),
        "next_action_present": nonempty_text(action.get("next_action")),
        "status": "PASS" if not blockers else "FAIL",
        "blockers": sorted(blockers),
    }


def audit_coverage(
    queue: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if queue.get("schema") != QUEUE_SCHEMA:
        add_blocker(blockers, "QUEUE_SCHEMA_INVALID")
    if registry.get("schema") != REGISTRY_SCHEMA:
        add_blocker(blockers, "REGISTRY_SCHEMA_INVALID")

    actions = queue.get("actions")
    templates = registry.get("templates")
    if not isinstance(actions, list) or not all(
        isinstance(row, dict) for row in actions
    ):
        raise CoverageAuditError("QUEUE_ACTIONS_INVALID")
    if not isinstance(templates, list) or not all(
        isinstance(row, dict) for row in templates
    ):
        raise CoverageAuditError("REGISTRY_TEMPLATES_INVALID")

    template_ids = [
        row.get("template_id")
        for row in templates
        if isinstance(row.get("template_id"), str)
    ]
    if len(template_ids) != len(templates):
        add_blocker(blockers, "REGISTRY_TEMPLATE_ID_MISSING")
    duplicate_templates = sorted(
        template_id
        for template_id, count in Counter(template_ids).items()
        if count > 1
    )
    if duplicate_templates:
        add_blocker(blockers, "REGISTRY_TEMPLATE_ID_DUPLICATE")
    template_id_set = set(template_ids)
    if NO_SEND_TEMPLATE_ID not in template_id_set:
        add_blocker(blockers, "NO_SEND_TEMPLATE_UNAVAILABLE")

    registry_controls = registry.get("controls")
    if not isinstance(registry_controls, dict):
        add_blocker(blockers, "REGISTRY_CONTROLS_MISSING")
    else:
        if registry_controls.get("builder_can_send_email") is not False:
            add_blocker(blockers, "REGISTRY_BUILDER_SEND_CONTROL_INVALID")
        if (
            registry_controls.get("action_time_human_review_required")
            is not True
        ):
            add_blocker(
                blockers,
                "REGISTRY_ACTION_TIME_REVIEW_CONTROL_INVALID",
            )

    queue_controls = queue.get("controls")
    if not isinstance(queue_controls, dict):
        add_blocker(blockers, "QUEUE_CONTROLS_MISSING")
    else:
        if queue_controls.get("builder_can_send_email") is not False:
            add_blocker(blockers, "QUEUE_BUILDER_SEND_CONTROL_INVALID")
        if queue_controls.get("final_send_performed") is not False:
            add_blocker(blockers, "QUEUE_FINAL_SEND_STATE_INVALID")
        if (
            queue_controls.get("action_time_human_review_required")
            is not True
        ):
            add_blocker(
                blockers,
                "QUEUE_ACTION_TIME_REVIEW_CONTROL_INVALID",
            )

    lane_ids = [
        row.get("lane_id")
        for row in actions
        if isinstance(row.get("lane_id"), str)
    ]
    duplicate_lanes = sorted(
        lane_id
        for lane_id, count in Counter(lane_ids).items()
        if count > 1
    )
    if duplicate_lanes:
        add_blocker(blockers, "QUEUE_LANE_ID_DUPLICATE")

    rows = [audit_lane(row, template_id_set) for row in actions]
    for row in rows:
        if row["status"] != "PASS":
            add_blocker(blockers, "LANE_COVERAGE_FAILURE")

    summary = queue.get("summary")
    if not isinstance(summary, dict):
        add_blocker(blockers, "QUEUE_SUMMARY_MISSING")
    else:
        if summary.get("lane_count") != len(actions):
            add_blocker(blockers, "QUEUE_LANE_COUNT_MISMATCH")
        expected_state_counts = dict(
            sorted(
                Counter(
                    row.get("action_state") for row in actions
                ).items()
            )
        )
        if summary.get("action_state_counts") != expected_state_counts:
            add_blocker(blockers, "QUEUE_STATE_COUNTS_MISMATCH")
        expected_send_now_count = sum(
            row.get("send_now") is True for row in actions
        )
        if (
            "send_now_count" in summary
            and summary.get("send_now_count")
            != expected_send_now_count
        ):
            add_blocker(blockers, "QUEUE_SEND_NOW_COUNT_MISMATCH")
        if expected_send_now_count != 0:
            add_blocker(blockers, "QUEUE_AUTONOMOUS_SEND_PRESENT")

    failed_rows = [
        row for row in rows if row["status"] != "PASS"
    ]
    core = {
        "schema": AUDIT_SCHEMA,
        "status": "PASS" if not blockers else "FAIL",
        "queue_as_of_utc": queue.get("as_of_utc"),
        "queue_status": queue.get("status"),
        "queue_sha256": canonical_sha256(queue),
        "registry_sha256": canonical_sha256(registry),
        "lane_count": len(actions),
        "template_count": len(templates),
        "email_due_lane_count": sum(
            row["action_state"] in EMAIL_DUE_STATES for row in rows
        ),
        "explicit_no_send_lane_count": sum(
            row["action_state"] in NO_SEND_STATES for row in rows
        ),
        "non_email_action_lane_count": sum(
            row["action_state"] in NON_EMAIL_ACTION_STATES
            for row in rows
        ),
        "failed_lane_count": len(failed_rows),
        "failed_lane_ids": sorted(
            str(row["lane_id"]) for row in failed_rows
        ),
        "blockers": sorted(blockers),
        "rows": rows,
        "external_action_performed": False,
        "builder_can_send_email": False,
        "claim_boundary": (
            "This audit proves only that the supplied queue maps every known "
            "lane to a validated response template or an explicit non-email "
            "or no-send disposition and that queue summary counts reconcile. "
            "It does not recheck Gmail, authorize or send email, perform a "
            "portal action, certify facts, prove delivery or response, or "
            "establish submission, acceptance, award, funding, validation, "
            "performance, or savings."
        ),
    }
    return {
        **core,
        "audit_sha256": canonical_sha256(core),
    }


def render_markdown(audit: dict[str, Any]) -> str:
    lines = [
        "# Outreach Queue Template Coverage",
        "",
        f"- Status: `{audit['status']}`",
        f"- Queue as of UTC: `{audit['queue_as_of_utc']}`",
        f"- Lanes: `{audit['lane_count']}`",
        f"- Templates: `{audit['template_count']}`",
        f"- Email lanes due: `{audit['email_due_lane_count']}`",
        f"- Explicit no-send lanes: `{audit['explicit_no_send_lane_count']}`",
        f"- Non-email action lanes: `{audit['non_email_action_lane_count']}`",
        f"- Failed lanes: `{audit['failed_lane_count']}`",
        "- Builder can send email: `false`",
        "- External action performed: `false`",
        "",
        "## Lane Coverage",
        "",
        "| Lane | State | Coverage | Template | Status |",
        "|---|---|---|---|---|",
    ]
    for row in audit["rows"]:
        template_id = (
            row["current_response_template_id"]
            or row["eligible_template_id"]
            or "none"
        )
        lines.append(
            f"| `{row['lane_id']}` | `{row['action_state']}` | "
            f"`{row['coverage_basis']}` | `{template_id}` | "
            f"`{row['status']}` |"
        )
    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    if audit["blockers"]:
        lines.extend(f"- `{code}`" for code in audit["blockers"])
    else:
        lines.append("- `none`")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            audit["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="\n",
        ) as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Audit every outreach queue lane for a validated response "
            "template or explicit non-email/no-send disposition. This tool "
            "cannot access Gmail or send email."
        )
    )
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MD)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate and print a summary without writing outputs.",
    )
    args = parser.parse_args()

    audit = audit_coverage(
        read_json_object(args.queue, "QUEUE_NOT_OBJECT"),
        read_json_object(args.registry, "REGISTRY_NOT_OBJECT"),
    )
    if not args.check:
        write_text_atomic(
            args.json_output,
            json.dumps(audit, indent=2, sort_keys=True) + "\n",
        )
        write_text_atomic(args.markdown_output, render_markdown(audit))
    print(
        json.dumps(
            {
                "status": audit["status"],
                "lane_count": audit["lane_count"],
                "template_count": audit["template_count"],
                "email_due_lane_count": audit[
                    "email_due_lane_count"
                ],
                "failed_lane_count": audit["failed_lane_count"],
                "failed_lane_ids": audit["failed_lane_ids"],
                "blockers": audit["blockers"],
                "builder_can_send_email": False,
                "external_action_performed": False,
                "outputs_written": not args.check,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if audit["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
