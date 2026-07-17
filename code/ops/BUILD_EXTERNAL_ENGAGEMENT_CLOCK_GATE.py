from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
REGISTER = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json"
OUT_JSON = ROOT / "out" / "ops" / "external_engagement_clock_gate_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "external_engagement_clock_gate.json"
CANONICAL_JSON = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_CLOCK_GATE_2026-07-16.json"
OUT_MD = SPRINT_DIR / "EXTERNAL_ENGAGEMENT_CLOCK_GATE_2026-07-16.md"

LOCAL_ZONE = ZoneInfo("America/Chicago")
CLAIM_BOUNDARY = (
    "This gate verifies recorded communication controls, source hashes, deadline precision, "
    "and follow-up holds. It does not prove receipt unless a source receipt says so, and it "
    "does not establish evaluation, selection, membership, endorsement, independent validation, "
    "a pilot, funding, an award, a contract, deployment, realized savings, or technical performance."
)
PRIVATE_MARKERS = (
    "meeting id",
    "passcode",
    "zoom.us",
    "teams.microsoft.com",
    "client_secret",
    "refresh_token",
    "api_key",
    "private key",
    "full legal party name",
    "business address",
    "signatory email",
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_hash(payload: Any) -> str:
    return sha256_bytes(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def parse_utc(value: str | datetime | None) -> datetime:
    if value is None:
        return now_utc()
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("as_of_utc must include a timezone")
    return parsed.astimezone(timezone.utc)


def read_register() -> tuple[dict[str, Any], bytes]:
    raw = REGISTER.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if payload.get("schema") != "lumencore.external_engagement_response_register.v1":
        raise ValueError("External engagement register schema is missing or unsupported")
    if not isinstance(payload.get("records"), list) or not payload["records"]:
        raise ValueError("External engagement register has no records")
    return payload, raw


def verify_embedded_hash(payload: dict[str, Any], field: str) -> bool:
    expected = payload.get(field)
    if not isinstance(expected, str):
        return False
    unsigned = dict(payload)
    unsigned.pop(field, None)
    return stable_hash(unsigned) == expected.lower()


def verify_record_hash(row: dict[str, Any]) -> bool:
    expected = row.get("record_sha256")
    if not isinstance(expected, str):
        return False
    unsigned = dict(row)
    unsigned.pop("record_sha256", None)
    return stable_hash(unsigned) == expected.lower()


def deadline_control(value: str | None, as_of_utc: datetime) -> dict[str, Any]:
    if not value:
        return {
            "deadline_precision": "NONE",
            "deadline_state": "NO_DEADLINE_RECORDED",
            "days_remaining_local": None,
            "hours_remaining": None,
        }

    if "T" not in value:
        deadline_date = date.fromisoformat(value)
        days = (deadline_date - as_of_utc.astimezone(LOCAL_ZONE).date()).days
        if days < 0:
            state = "PAST_DATE_TIME_UNVERIFIED"
        elif days == 0:
            state = "DUE_TODAY_TIME_UNVERIFIED_SUBMIT_EARLY"
        elif days == 1:
            state = "DUE_NEXT_LOCAL_DAY_TIME_UNVERIFIED"
        else:
            state = "UPCOMING_DATE_ONLY_TIME_UNVERIFIED"
        return {
            "deadline_precision": "DATE_ONLY_CLOSE_TIME_NOT_RECORDED",
            "deadline_state": state,
            "days_remaining_local": days,
            "hours_remaining": None,
        }

    deadline = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if deadline.tzinfo is None:
        raise ValueError(f"Timestamp deadline lacks a timezone: {value}")
    hours = (deadline.astimezone(timezone.utc) - as_of_utc).total_seconds() / 3600
    if hours < 0:
        state = "PAST_EXACT_DEADLINE"
    elif hours <= 24:
        state = "UNDER_24_HOURS"
    elif hours <= 72:
        state = "UNDER_72_HOURS"
    else:
        state = "FUTURE_EXACT_DEADLINE"
    return {
        "deadline_precision": "TIMESTAMP_WITH_TIMEZONE",
        "deadline_state": state,
        "days_remaining_local": None,
        "hours_remaining": round(hours, 2),
    }


def hold_control(value: str | None, as_of_utc: datetime) -> dict[str, Any]:
    if not value:
        return {
            "follow_up_hold_state": "NO_HOLD_RECORDED",
            "hold_days_remaining_local": None,
        }
    hold_date = date.fromisoformat(value)
    days = (hold_date - as_of_utc.astimezone(LOCAL_ZONE).date()).days
    return {
        "follow_up_hold_state": (
            "FOLLOW_UP_HOLD_ACTIVE"
            if days > 0
            else "FOLLOW_UP_WINDOW_OPEN_HUMAN_REVIEW_REQUIRED"
        ),
        "hold_days_remaining_local": max(days, 0),
    }


def priority_for(row: dict[str, Any], deadline: dict[str, Any]) -> str:
    state = str(row.get("state", ""))
    deadline_state = deadline["deadline_state"]
    if "HUMAN_FACTS_REQUIRED" in state and deadline_state in {
        "DUE_TODAY_TIME_UNVERIFIED_SUBMIT_EARLY",
        "DUE_NEXT_LOCAL_DAY_TIME_UNVERIFIED",
    }:
        return "P0_HUMAN_FACTS_NOW"
    if row.get("do_not_duplicate_send"):
        return "P2_MONITOR_NO_DUPLICATE"
    if deadline_state in {"UNDER_24_HOURS", "UNDER_72_HOURS"}:
        return "P1_DEADLINE_REVIEW"
    return "P3_MONITOR"


def build_payload(
    as_of_utc: str | datetime | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    as_of = parse_utc(as_of_utc)
    register, register_raw = read_register()
    controls: list[dict[str, Any]] = []

    for row in register["records"]:
        deadline = deadline_control(row.get("deadline"), as_of)
        hold = hold_control(row.get("no_send_before"), as_of)
        control = {
            "lane_id": row["lane_id"],
            "organization": row["organization"],
            "record_hash_valid": verify_record_hash(row),
            "source_state": row["state"],
            "source_decision": row["decision"],
            "priority": priority_for(row, deadline),
            "response_channel": row["response_channel"],
            "human_action_required_now": (
                "HUMAN_FACTS_REQUIRED" in str(row.get("state", ""))
                and deadline["deadline_state"]
                in {
                    "DUE_TODAY_TIME_UNVERIFIED_SUBMIT_EARLY",
                    "DUE_NEXT_LOCAL_DAY_TIME_UNVERIFIED",
                }
            ),
            "duplicate_send_control": (
                "BLOCKED_DO_NOT_DUPLICATE"
                if row.get("do_not_duplicate_send")
                else "NOT_APPLICABLE"
            ),
            "autonomous_external_send_allowed": False,
            "autonomous_final_submit_allowed": False,
            "action_gate": row["action_gate"],
            "next_action": row["next_action"],
            "response_artifact": row["response_artifact"],
            "claim_boundary": row["claim_boundary"],
            **deadline,
            **hold,
        }
        control["control_sha256"] = stable_hash(control)
        controls.append(control)

    priority_order = {
        "P0_HUMAN_FACTS_NOW": 0,
        "P1_DEADLINE_REVIEW": 1,
        "P2_MONITOR_NO_DUPLICATE": 2,
        "P3_MONITOR": 3,
    }
    controls.sort(key=lambda row: (priority_order[row["priority"]], row["organization"]))
    record_hashes_valid = sum(1 for row in controls if row["record_hash_valid"])
    human_now = [row for row in controls if row["human_action_required_now"]]
    date_only = [
        row
        for row in controls
        if row["deadline_precision"] == "DATE_ONLY_CLOSE_TIME_NOT_RECORDED"
    ]
    holds = [row for row in controls if row["follow_up_hold_state"] == "FOLLOW_UP_HOLD_ACTIVE"]

    payload: dict[str, Any] = {
        "schema": "lumencore.external_engagement_clock_gate.v1",
        "generated_utc": generated_utc or now_utc().isoformat(),
        "as_of_utc": as_of.isoformat(),
        "as_of_local": as_of.astimezone(LOCAL_ZONE).isoformat(),
        "timezone": str(LOCAL_ZONE),
        "status": "HUMAN_ACTION_DUE_NO_AUTONOMOUS_SEND" if human_now else "MONITOR_ONLY",
        "direct_answer": (
            "The Nashville EC application is the only immediate human-fact action. Its July 17 "
            "deadline is date-only, so no exact closing hour is claimed. EPRI, Georgia PATENTS, "
            "CDC, LANL, NASA, and Army remain monitor-only and duplicate-send blocked where recorded."
        ),
        "summary": {
            "lane_count": len(controls),
            "verified_record_hash_count": record_hashes_valid,
            "all_record_hashes_valid": record_hashes_valid == len(controls),
            "source_register_hash_valid": verify_embedded_hash(register, "register_sha256"),
            "immediate_human_action_count": len(human_now),
            "date_only_deadline_count": len(date_only),
            "active_follow_up_hold_count": len(holds),
            "duplicate_send_block_count": sum(
                1 for row in controls if row["duplicate_send_control"] == "BLOCKED_DO_NOT_DUPLICATE"
            ),
            "autonomous_external_send_allowed": False,
            "autonomous_final_submit_allowed": False,
            "browser_navigation_performed": False,
        },
        "controls": controls,
        "source": {
            "path": rel(REGISTER),
            "bytes": len(register_raw),
            "sha256": sha256_bytes(register_raw),
            "embedded_register_sha256": register.get("register_sha256"),
        },
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {
            "canonical_json": rel(CANONICAL_JSON),
            "markdown": rel(OUT_MD),
            "latest_json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
        },
    }
    payload["gate_sha256"] = stable_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# External Engagement Clock Gate - 2026-07-16",
        "",
        payload["direct_answer"],
        "",
        "## Gate Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- As of UTC: `{payload['as_of_utc']}`",
        f"- As of local: `{payload['as_of_local']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Verified record hashes: `{summary['verified_record_hash_count']}`",
        f"- All record hashes valid: `{str(summary['all_record_hashes_valid']).lower()}`",
        f"- Source register hash valid: `{str(summary['source_register_hash_valid']).lower()}`",
        f"- Immediate human actions: `{summary['immediate_human_action_count']}`",
        f"- Date-only deadlines: `{summary['date_only_deadline_count']}`",
        f"- Active follow-up holds: `{summary['active_follow_up_hold_count']}`",
        f"- Duplicate-send blocks: `{summary['duplicate_send_block_count']}`",
        f"- Autonomous external send: `{str(summary['autonomous_external_send_allowed']).lower()}`",
        f"- Autonomous final submit: `{str(summary['autonomous_final_submit_allowed']).lower()}`",
        f"- Session-browser navigation performed: `{str(summary['browser_navigation_performed']).lower()}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Clocked Queue",
        "",
        "| Priority | Organization | Deadline state | Follow-up state | Send control |",
        "|---|---|---|---|---|",
    ]
    for row in payload["controls"]:
        lines.append(
            f"| `{row['priority']}` | {row['organization']} | `{row['deadline_state']}` | "
            f"`{row['follow_up_hold_state']}` | `{row['duplicate_send_control']}` |"
        )

    for row in payload["controls"]:
        lines.extend(
            [
                "",
                f"### {row['organization']}",
                "",
                f"- Lane: `{row['lane_id']}`",
                f"- Priority: `{row['priority']}`",
                f"- Source state: `{row['source_state']}`",
                f"- Source decision: `{row['source_decision']}`",
                f"- Deadline precision: `{row['deadline_precision']}`",
                f"- Deadline state: `{row['deadline_state']}`",
                f"- Follow-up hold: `{row['follow_up_hold_state']}`",
                f"- Duplicate send: `{row['duplicate_send_control']}`",
                f"- Record hash valid: `{str(row['record_hash_valid']).lower()}`",
                f"- Human action required now: `{str(row['human_action_required_now']).lower()}`",
                f"- Action gate: {row['action_gate']}",
                f"- Next action: {row['next_action']}",
                f"- Response artifact: `{row['response_artifact']}`",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Control SHA-256: `{row['control_sha256']}`",
            ]
        )

    lines.extend(
        [
            "",
            "## Source Integrity",
            "",
            f"- Path: `{payload['source']['path']}`",
            f"- Bytes: `{payload['source']['bytes']}`",
            f"- File SHA-256: `{payload['source']['sha256']}`",
            f"- Embedded register SHA-256: `{payload['source']['embedded_register_sha256']}`",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def ensure_public_safe(text: str) -> None:
    lowered = text.lower()
    hits = sorted(marker for marker in PRIVATE_MARKERS if marker in lowered)
    if hits:
        raise ValueError(f"Refusing to write private markers: {hits}")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    ensure_public_safe(json.dumps(payload, sort_keys=True))
    ensure_public_safe(markdown)
    for path in (OUT_JSON, DASHBOARD_JSON, CANONICAL_JSON):
        write_json(path, payload)
    OUT_MD.write_text(markdown, encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "immediate_human_actions": payload["summary"]["immediate_human_action_count"],
                "all_record_hashes_valid": payload["summary"]["all_record_hashes_valid"],
                "source_register_hash_valid": payload["summary"]["source_register_hash_valid"],
                "browser_navigation_performed": payload["summary"]["browser_navigation_performed"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
