from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT / "config" / "deadline_action_sentinel_v1.json"
DEFAULT_JSON = (
    ROOT
    / "evidence"
    / "opportunity"
    / "deadline_action_sentinel_latest.json"
)
DEFAULT_MARKDOWN = ROOT / "docs" / "DEADLINE_ACTION_SENTINEL.md"

REQUIRED_FALSE_CONTROLS = {
    "autonomous_email_send_allowed",
    "autonomous_portal_action_allowed",
    "autonomous_agreement_acceptance_allowed",
    "autonomous_payment_allowed",
    "autonomous_signature_allowed",
    "autonomous_certification_allowed",
    "authenticated_portal_session_use_allowed",
}
REQUIRED_TRUE_CONTROLS = {
    "read_only_builder",
    "action_time_human_approval_required",
    "unknown_deadline_time_fail_closed",
    "duplicate_recheck_required_before_external_send",
}
REQUIRED_PROHIBITED_ACTIONS = {
    "SEND_EMAIL",
    "OPEN_AUTHENTICATED_PORTAL",
    "CHANGE_PORTAL_ANSWER",
    "UPLOAD_FILE",
    "ACCEPT_AGREEMENT",
    "SIGN",
    "CERTIFY",
    "SUBMIT",
    "PAY",
}
PRIVATE_FIELD_KEYS = {
    "account_number",
    "access_code",
    "discount_code",
    "ein",
    "message_id",
    "password",
    "recipient_email",
    "sender_email",
    "source_message_id",
    "tax_id",
    "thread_id",
    "token",
}


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_aware_datetime(value: str, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid ISO 8601 datetime") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{label} must include an explicit timezone offset")
    return parsed.astimezone(timezone.utc)


def format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_date(value: str, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a valid YYYY-MM-DD date") from exc


def resolve_field(payload: dict[str, Any], dotted_path: str) -> Any:
    current: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise ValueError(f"source field not found: {dotted_path}")
        current = current[part]
    return current


def assert_no_private_fields(value: Any, path: str = "config") -> None:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key.lower() in PRIVATE_FIELD_KEYS:
                raise ValueError(f"private field is not permitted in sentinel data: {path}.{key}")
            assert_no_private_fields(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            assert_no_private_fields(nested, f"{path}[{index}]")


def source_receipt(binding: dict[str, Any], deadline: dict[str, Any]) -> dict[str, Any]:
    kind = str(binding.get("kind", "")).strip()
    if kind in {"REPOSITORY_GATE", "REPOSITORY_DATE_GATE"}:
        relative_path = Path(str(binding.get("path", "")))
        if not relative_path.as_posix() or relative_path.is_absolute():
            raise ValueError("repository source path must be relative")
        source_path = (ROOT / relative_path).resolve()
        try:
            source_path.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise ValueError("repository source path must stay inside the worktree") from exc
        if not source_path.is_file():
            raise ValueError(f"repository source does not exist: {relative_path.as_posix()}")

        source = read_json(source_path)
        deadline_field = str(binding.get("deadline_field", "")).strip()
        status_field = str(binding.get("status_field", "")).strip()
        observed_deadline = str(resolve_field(source, deadline_field))
        observed_status = str(resolve_field(source, status_field))
        required_status = str(binding.get("required_status", "")).strip()

        if kind == "REPOSITORY_GATE":
            if deadline.get("precision") != "EXACT":
                raise ValueError("repository deadline binding requires EXACT precision")
            if parse_aware_datetime(
                observed_deadline, deadline_field
            ) != parse_aware_datetime(
                str(deadline.get("iso_utc", "")), "deadline.iso_utc"
            ):
                raise ValueError("configured deadline does not match the repository gate")
        else:
            if deadline.get("precision") != "DATE_ONLY":
                raise ValueError(
                    "repository date binding requires DATE_ONLY precision"
                )
            if parse_date(observed_deadline, deadline_field) != parse_date(
                str(deadline.get("date", "")), "deadline.date"
            ):
                raise ValueError("configured date does not match the repository gate")
        if observed_status != required_status:
            raise ValueError(
                "repository gate status changed: "
                f"expected {required_status}, observed {observed_status}"
            )

        return {
            "kind": kind,
            "path": relative_path.as_posix(),
            "sha256": sha256(source_path),
            "bound_deadline_field": deadline_field,
            "observed_status": observed_status,
        }

    if kind == "PRIVATE_OFFICIAL_INBOUND_STATUS_EVENT":
        if binding.get("private_source_excluded") is not True:
            raise ValueError("private source metadata must remain excluded")
        if binding.get("identifiers_excluded") is not True:
            raise ValueError("private source identifiers must remain excluded")
        return {
            "kind": kind,
            "private_source_excluded": True,
            "identifiers_excluded": True,
        }

    raise ValueError(f"unsupported source binding kind: {kind}")


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != "lumencore.deadline_action_sentinel_config.v1":
        raise ValueError("unexpected deadline sentinel config schema")
    assert_no_private_fields(config)

    controls = config.get("controls")
    if not isinstance(controls, dict):
        raise ValueError("controls must be an object")
    for key in sorted(REQUIRED_FALSE_CONTROLS):
        if controls.get(key) is not False:
            raise ValueError(f"control must remain false: {key}")
    for key in sorted(REQUIRED_TRUE_CONTROLS):
        if controls.get(key) is not True:
            raise ValueError(f"control must remain true: {key}")

    prohibited = config.get("prohibited_actions")
    if not isinstance(prohibited, list):
        raise ValueError("prohibited_actions must be a list")
    missing = REQUIRED_PROHIBITED_ACTIONS.difference(str(value) for value in prohibited)
    if missing:
        raise ValueError(f"missing prohibited actions: {sorted(missing)}")

    alert_window = config.get("alert_window_hours")
    if not isinstance(alert_window, int) or alert_window <= 0:
        raise ValueError("alert_window_hours must be a positive integer")

    lanes = config.get("lanes")
    if not isinstance(lanes, list) or not lanes:
        raise ValueError("lanes must be a non-empty list")
    ids: set[str] = set()
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ValueError("each lane must be an object")
        lane_id = str(lane.get("id", "")).strip()
        if not lane_id or lane_id in ids:
            raise ValueError(f"lane id must be present and unique: {lane_id}")
        ids.add(lane_id)
        if lane.get("completion_evidence_present") is not False:
            raise ValueError(f"{lane_id} must not claim completion without evidence")
        blockers = lane.get("blockers")
        if not isinstance(blockers, list) or not blockers:
            raise ValueError(f"{lane_id} must retain at least one blocker")

        deadline = lane.get("deadline")
        if not isinstance(deadline, dict):
            raise ValueError(f"{lane_id} deadline must be an object")
        precision = deadline.get("precision")
        if precision == "EXACT":
            parse_aware_datetime(str(deadline.get("iso_utc", "")), f"{lane_id}.iso_utc")
            if deadline.get("cutoff_time_known") is not True:
                raise ValueError(f"{lane_id} exact deadline must have a known cutoff")
            if deadline.get("timezone_known") is not True:
                raise ValueError(f"{lane_id} exact deadline must have a known timezone")
            if not str(deadline.get("timezone", "")).strip():
                raise ValueError(f"{lane_id} exact deadline must name its timezone")
        elif precision == "DATE_ONLY":
            parse_date(str(deadline.get("date", "")), f"{lane_id}.date")
            if deadline.get("cutoff_time_known") is not False:
                raise ValueError(f"{lane_id} date-only cutoff must remain unknown")
            if deadline.get("timezone_known") is not False:
                raise ValueError(f"{lane_id} date-only timezone must remain unknown")
            for forbidden in ("iso_utc", "local_display", "timezone"):
                if forbidden in deadline:
                    raise ValueError(
                        f"{lane_id} date-only deadline cannot contain {forbidden}"
                    )
        else:
            raise ValueError(f"{lane_id} has unsupported deadline precision: {precision}")

        binding = lane.get("source_binding")
        if not isinstance(binding, dict):
            raise ValueError(f"{lane_id} source_binding must be an object")
        source_receipt(binding, deadline)


def urgency_for(seconds_until: int, alert_window_hours: int) -> str:
    if seconds_until < 0:
        return "PAST"
    hours_until = seconds_until / 3600
    if hours_until <= 8:
        return "WITHIN_8_HOURS"
    if hours_until <= 24:
        return "WITHIN_24_HOURS"
    if hours_until <= 72:
        return "WITHIN_72_HOURS"
    if hours_until <= alert_window_hours:
        return "WITHIN_ALERT_WINDOW"
    return "LATER"


def evaluate_lane(
    lane: dict[str, Any], as_of_utc: datetime, alert_window_hours: int
) -> dict[str, Any]:
    deadline = lane["deadline"]
    blockers = [str(value) for value in lane["blockers"]]
    precision = deadline["precision"]

    result: dict[str, Any] = {
        "id": str(lane["id"]),
        "title": str(lane["title"]),
        "visibility": str(lane["visibility"]),
        "external_action_type": str(lane["external_action_type"]),
        "completion_evidence_present": False,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "requires_human_attention": True,
        "external_action_authorized": False,
        "send_now": False,
        "external_action_executed": False,
        "safest_next_action": str(lane["safest_next_action"]),
        "source_receipt": source_receipt(lane["source_binding"], deadline),
    }

    if precision == "EXACT":
        deadline_utc = parse_aware_datetime(str(deadline["iso_utc"]), "deadline.iso_utc")
        seconds_until = int((deadline_utc - as_of_utc).total_seconds())
        if seconds_until < 0:
            state = "PAST_DEADLINE_NO_EXTERNAL_ACTION_AUTHORIZED"
        elif seconds_until <= alert_window_hours * 3600:
            state = "BLOCKED_HUMAN_ACTION_DUE"
        else:
            state = "BLOCKED_MONITOR"
        result.update(
            {
                "state": state,
                "urgency": urgency_for(seconds_until, alert_window_hours),
                "deadline": {
                    "precision": "EXACT",
                    "iso_utc": format_utc(deadline_utc),
                    "local_display": str(deadline["local_display"]),
                    "timezone": str(deadline["timezone"]),
                    "cutoff_time_known": True,
                    "timezone_known": True,
                    "exact_countdown_available": True,
                    "deadline_passed": seconds_until < 0,
                    "seconds_until_deadline": seconds_until,
                    "hours_until_deadline": round(seconds_until / 3600, 2),
                },
            }
        )
        return result

    deadline_date = parse_date(str(deadline["date"]), "deadline.date")
    if as_of_utc.date() < deadline_date:
        state = "HUMAN_DATE_ONLY_ACTION_OPEN"
        relation = "FUTURE_BY_UTC_CALENDAR_DATE"
    elif as_of_utc.date() == deadline_date:
        state = "HUMAN_DATE_ONLY_ACTION_DUE_DATE_UNKNOWN_CUTOFF"
        relation = "SAME_UTC_CALENDAR_DATE"
    else:
        state = "HUMAN_DATE_ONLY_RECONCILIATION_REQUIRED"
        relation = "AFTER_DATE_BY_UTC_CALENDAR_ONLY"
    result.update(
        {
            "state": state,
            "urgency": "UNKNOWN_EXACT_CUTOFF_FAIL_CLOSED",
            "deadline": {
                "precision": "DATE_ONLY",
                "date": deadline_date.isoformat(),
                "cutoff_time_known": False,
                "timezone_known": False,
                "exact_countdown_available": False,
                "deadline_passed": None,
                "calendar_relation": relation,
            },
        }
    )
    return result


def lane_sort_key(lane: dict[str, Any]) -> tuple[str, str]:
    deadline = lane["deadline"]
    if deadline["precision"] == "EXACT":
        return str(deadline["iso_utc"]), str(lane["id"])
    return f"{deadline['date']}T23:59:59Z", str(lane["id"])


def build_sentinel(config_path: Path, as_of_utc: datetime) -> dict[str, Any]:
    if as_of_utc.tzinfo is None or as_of_utc.utcoffset() is None:
        raise ValueError("as_of_utc must be timezone-aware")
    as_of_utc = as_of_utc.astimezone(timezone.utc).replace(microsecond=0)
    config = read_json(config_path)
    validate_config(config)

    alert_window_hours = int(config["alert_window_hours"])
    evaluated = [
        evaluate_lane(lane, as_of_utc, alert_window_hours)
        for lane in sorted(config["lanes"], key=lane_sort_key)
    ]
    states = Counter(str(lane["state"]) for lane in evaluated)
    posture = (
        "HUMAN_ACTION_REQUIRED_FAIL_CLOSED"
        if any(lane["requires_human_attention"] for lane in evaluated)
        else "MONITOR_FAIL_CLOSED"
    )

    payload: dict[str, Any] = {
        "schema": "lumencore.deadline_action_sentinel.v1",
        "evaluated_utc": format_utc(as_of_utc),
        "posture": posture,
        "controls": dict(config["controls"]),
        "prohibited_actions": list(config["prohibited_actions"]),
        "alert_window_hours": alert_window_hours,
        "summary": {
            "lane_count": len(evaluated),
            "human_attention_count": sum(
                1 for lane in evaluated if lane["requires_human_attention"]
            ),
            "exact_deadline_count": sum(
                1 for lane in evaluated if lane["deadline"]["precision"] == "EXACT"
            ),
            "date_only_deadline_count": sum(
                1
                for lane in evaluated
                if lane["deadline"]["precision"] == "DATE_ONLY"
            ),
            "autonomous_external_action_count": 0,
            "external_actions_executed_count": 0,
            "state_counts": dict(sorted(states.items())),
        },
        "lanes": evaluated,
        "claim_boundaries": [
            "This sentinel is a read-only deadline and blocker view.",
            (
                "A warning is not authority to send, open a signed-in portal, "
                "upload, accept terms, sign, certify, submit, or pay."
            ),
            (
                "Date-only milestones never receive an invented cutoff time, "
                "timezone, exact countdown, or definitive overdue label."
            ),
            "Drafted, sent, submitted, accepted, and paid remain distinct evidence states.",
        ],
    }
    assert_no_private_fields(payload, "output")
    return payload


def deadline_display(lane: dict[str, Any]) -> str:
    deadline = lane["deadline"]
    if deadline["precision"] == "EXACT":
        return str(deadline["local_display"])
    return f"{deadline['date']} (time and timezone unverified)"


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Deadline Action Sentinel",
        "",
        f"Evaluated UTC: `{payload['evaluated_utc']}`",
        f"Posture: `{payload['posture']}`",
        "",
        "## Control Boundary",
        "",
        "- Read-only builder: `true`",
        (
            "- Autonomous email, portal, agreement, signature, certification, "
            "submission, and payment actions: `false`"
        ),
        "- Exact action-time human approval required: `true`",
        "- Unknown deadline time or timezone: `FAIL_CLOSED`",
        "- External actions executed by this build: `0`",
        "",
        "## Current Lanes",
        "",
        "| Priority | Lane | Deadline | State | Blockers | Safest next action |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for priority, lane in enumerate(payload["lanes"], start=1):
        action = str(lane["safest_next_action"]).replace("|", "/")
        lines.append(
            f"| {priority} | {lane['title']} | {deadline_display(lane)} | "
            f"`{lane['state']}` | {lane['blocker_count']} | {action} |"
        )

    lines.extend(
        [
            "",
            "## Source Custody",
            "",
        ]
    )
    for lane in payload["lanes"]:
        receipt = lane["source_receipt"]
        if receipt["kind"] in {"REPOSITORY_GATE", "REPOSITORY_DATE_GATE"}:
            lines.append(
                f"- `{lane['id']}`: `{receipt['path']}` at SHA-256 "
                f"`{receipt['sha256']}`; observed gate `{receipt['observed_status']}`."
            )
        else:
            lines.append(
                f"- `{lane['id']}`: private official-event metadata only; source "
                "content and identifiers intentionally excluded."
            )

    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
        ]
    )
    lines.extend(f"- {boundary}" for boundary in payload["claim_boundaries"])
    lines.append("")
    return "\n".join(lines)


def resolve_cli_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else ROOT / path


def write_outputs(
    payload: dict[str, Any], json_output: Path, markdown_output: Path
) -> None:
    json_output.parent.mkdir(parents=True, exist_ok=True)
    markdown_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(canonical_json(payload), encoding="utf-8", newline="\n")
    markdown_output.write_text(render_markdown(payload), encoding="utf-8", newline="\n")


def check_outputs(
    payload: dict[str, Any], json_output: Path, markdown_output: Path
) -> None:
    expected = {
        json_output: canonical_json(payload),
        markdown_output: render_markdown(payload),
    }
    for path, content in expected.items():
        if not path.is_file():
            raise ValueError(f"expected output is missing: {path}")
        if path.read_text(encoding="utf-8") != content:
            raise ValueError(f"output is stale: {path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed, read-only deadline action sentinel."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG))
    parser.add_argument("--json-output", default=str(DEFAULT_JSON))
    parser.add_argument("--markdown-output", default=str(DEFAULT_MARKDOWN))
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = resolve_cli_path(args.config)
    json_output = resolve_cli_path(args.json_output)
    markdown_output = resolve_cli_path(args.markdown_output)

    as_of_text = args.as_of_utc
    if args.check and not as_of_text:
        if not json_output.is_file():
            raise ValueError("--check requires an existing JSON output or --as-of-utc")
        as_of_text = str(read_json(json_output).get("evaluated_utc", ""))
    as_of_utc = (
        parse_aware_datetime(as_of_text, "--as-of-utc")
        if as_of_text
        else datetime.now(timezone.utc)
    )
    payload = build_sentinel(config_path, as_of_utc)

    if args.check:
        check_outputs(payload, json_output, markdown_output)
        status = "CURRENT"
    else:
        write_outputs(payload, json_output, markdown_output)
        status = "WRITTEN"

    print(
        json.dumps(
            {
                "status": status,
                "posture": payload["posture"],
                "evaluated_utc": payload["evaluated_utc"],
                "lane_count": payload["summary"]["lane_count"],
                "external_actions_executed_count": 0,
                "json_output": str(json_output),
                "markdown_output": str(markdown_output),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
