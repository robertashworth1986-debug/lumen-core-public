from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = ROOT / "out" / "ops"
LEDGER_LATEST = OPS_ROOT / "grants_live_submission_ledger_latest.json"
WAITING_ACTIONS_LATEST = OPS_ROOT / "grant_waiting_actions_latest.json"
FIT_PACK_LATEST = OPS_ROOT / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def now_iso() -> str:
    return now_utc().isoformat()


def now_tag() -> str:
    return now_utc().strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def norm(value: Any) -> str:
    return str(value or "").strip().upper()


def norm_status(value: Any) -> str:
    txt = str(value or "").strip().lower().replace("-", " ")
    return "_".join(part for part in txt.split() if part)


def pick_target(waiting_payload: dict[str, Any], ledger_payload: dict[str, Any], tracking: str, opp_num: str) -> dict[str, Any] | None:
    blocked = waiting_payload.get("blocked_or_fix_now") if isinstance(waiting_payload, dict) else []
    waiting = waiting_payload.get("waiting_followups") if isinstance(waiting_payload, dict) else []
    blocked = blocked if isinstance(blocked, list) else []
    waiting = waiting if isinstance(waiting, list) else []

    records = ledger_payload.get("records") if isinstance(ledger_payload, dict) else []
    records = records if isinstance(records, list) else []

    wanted_tracking = norm(tracking)
    wanted_opp = norm(opp_num)

    if wanted_tracking or wanted_opp:
        for row in blocked + waiting + records:
            if not isinstance(row, dict):
                continue
            row_tracking = norm(row.get("grants_tracking_number"))
            row_opp = norm(row.get("opp_num"))
            tracking_match = (not wanted_tracking) or (row_tracking == wanted_tracking)
            opp_match = (not wanted_opp) or (row_opp == wanted_opp)
            if tracking_match and opp_match:
                return row

    for row in blocked:
        if isinstance(row, dict):
            return row

    for row in records:
        if not isinstance(row, dict):
            continue
        status = norm_status(row.get("status"))
        if any(token in status for token in ("rejected", "error", "invalid", "denied")):
            return row

    return records[0] if records and isinstance(records[0], dict) else None


def find_fit_entry(fit_payload: dict[str, Any], opp_num: str) -> dict[str, Any]:
    rows = fit_payload.get("opportunities") if isinstance(fit_payload, dict) else []
    rows = rows if isinstance(rows, list) else []
    wanted = norm(opp_num)
    for row in rows:
        if not isinstance(row, dict):
            continue
        if norm(row.get("opp_num")) == wanted:
            return row
    return {}


def build_payload(target: dict[str, Any], fit_entry: dict[str, Any], owner: str, due_hours: int) -> dict[str, Any]:
    status = norm_status(target.get("status"))
    urgency = "P0" if any(token in status for token in ("rejected", "error", "invalid", "denied")) else "P1"

    deadline = now_utc() + timedelta(hours=max(1, int(due_hours)))
    opp_num = str(target.get("opp_num") or "").strip()
    tracking = str(target.get("grants_tracking_number") or "").strip()

    checklist = [
        {
            "step": "Pull exact validation errors from Grants.gov status detail",
            "owner": owner,
            "priority": "P0",
            "status": "pending",
            "evidence_required": "Error code(s), failing field names, and message text",
        },
        {
            "step": "Correct SF-424 and package metadata fields",
            "owner": owner,
            "priority": "P0",
            "status": "pending",
            "evidence_required": "Updated SF-424 map + field diff",
        },
        {
            "step": "Rebuild submission packet and run preflight checks",
            "owner": owner,
            "priority": "P0",
            "status": "pending",
            "evidence_required": "submission_packet.json with ready=true",
        },
        {
            "step": "Resubmit package in Grants.gov workspace",
            "owner": owner,
            "priority": "P0",
            "status": "pending",
            "evidence_required": "New grants tracking number",
        },
        {
            "step": "Upsert new tracking receipt and refresh dashboard artifacts",
            "owner": owner,
            "priority": "P0",
            "status": "pending",
            "evidence_required": "Updated grants_live_submission_ledger_latest.json + mission control support",
        },
    ]

    commands = [
        "python code/ops/UPSERT_GRANTS_EMAIL_RECEIPT.py --opp-num <OPP_NUM> --tracking-number <NEW_TRACKING> --status 'Received by Agency' --source grantsgov_status_check",
        "python code/ops/BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS.py",
        "python code/ops/BUILD_GRANT_WAITING_ACTIONS.py",
        "python code/ops/BUILD_GRANT_FOLLOWUP_TRACKER.py",
    ]

    payload = {
        "generated_utc": now_iso(),
        "scope": "grant_resubmission_checklist",
        "target": {
            "opp_num": opp_num,
            "grants_tracking_number": tracking,
            "status": status,
            "source": str(target.get("source") or "").strip(),
            "status_local_time": str(target.get("status_local_time") or target.get("email_received_local") or "").strip(),
            "agency_tracking_number": str(target.get("agency_tracking_number") or "").strip(),
            "application_name": str(target.get("application_name") or "").strip(),
        },
        "fit_context": {
            "title": str(fit_entry.get("title") or "").strip(),
            "agency": str(fit_entry.get("agency") or "").strip(),
            "fit_status": str(fit_entry.get("fit_status") or "").strip(),
            "blueprint_alignment_score": fit_entry.get("blueprint_alignment_score"),
            "days_to_close": fit_entry.get("days_to_close"),
        },
        "execution": {
            "owner": owner,
            "priority": urgency,
            "due_utc": deadline.isoformat(),
            "checklist": checklist,
            "commands": commands,
        },
        "go_no_go_gate": {
            "go_if": [
                "All validation errors cleared in Check Application",
                "Submission packet indicates ready=true",
                "New tracking number is captured and added to receipts ledger",
            ],
            "hold_if": [
                "Any unresolved SF-424/attachment validation error persists",
                "Tracking number not issued after submit attempt",
            ],
        },
        "evidence_paths": {
            "ledger_latest_json": str(LEDGER_LATEST),
            "waiting_actions_latest_json": str(WAITING_ACTIONS_LATEST),
            "fit_pack_latest_json": str(FIT_PACK_LATEST),
            "grants_console": "INSTITUTIONAL_STACK_V2/dashboard/grants.html",
        },
    }
    return payload


def build_markdown(payload: dict[str, Any]) -> str:
    tgt = payload.get("target", {}) if isinstance(payload, dict) else {}
    exe = payload.get("execution", {}) if isinstance(payload, dict) else {}
    checklist = exe.get("checklist") if isinstance(exe, dict) else []
    checklist = checklist if isinstance(checklist, list) else []

    lines = [
        "# Grant Resubmission Checklist",
        "",
        f"Generated UTC: {payload.get('generated_utc', '')}",
        "",
        "## Target",
        "",
        f"- opp_num: {tgt.get('opp_num', '')}",
        f"- grants_tracking_number: {tgt.get('grants_tracking_number', '')}",
        f"- status: {tgt.get('status', '')}",
        f"- owner: {exe.get('owner', '')}",
        f"- due_utc: {exe.get('due_utc', '')}",
        "",
        "## Checklist",
        "",
    ]

    for idx, row in enumerate(checklist, start=1):
        lines.append(f"{idx}. {row.get('step', '')} [{row.get('priority', '')}]")
        lines.append(f"   - evidence: {row.get('evidence_required', '')}")

    lines += ["", "## Commands", ""]
    for cmd in exe.get("commands", []) or []:
        lines.append(f"- `{cmd}`")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build targeted grant resubmission checklist")
    parser.add_argument("--tracking-number", default="")
    parser.add_argument("--opp-num", default="")
    parser.add_argument("--owner", default="Robert Ashworth")
    parser.add_argument("--due-hours", type=int, default=24)
    args = parser.parse_args()

    waiting_payload = load_json(WAITING_ACTIONS_LATEST, {})
    ledger_payload = load_json(LEDGER_LATEST, {})
    fit_payload = load_json(FIT_PACK_LATEST, {})

    target = pick_target(waiting_payload, ledger_payload, args.tracking_number, args.opp_num)
    if not isinstance(target, dict):
        raise SystemExit("No grant target found for resubmission checklist")

    fit_entry = find_fit_entry(fit_payload, str(target.get("opp_num") or ""))
    payload = build_payload(target, fit_entry, owner=str(args.owner), due_hours=max(1, int(args.due_hours)))

    stamp = now_tag()
    json_tagged = OPS_ROOT / f"grant_resubmission_checklist_{stamp}.json"
    json_latest = OPS_ROOT / "grant_resubmission_checklist_latest.json"
    md_tagged = OPS_ROOT / f"grant_resubmission_checklist_{stamp}.md"
    md_latest = OPS_ROOT / "grant_resubmission_checklist_latest.md"

    write_json(json_tagged, payload)
    write_json(json_latest, payload)

    md_text = build_markdown(payload)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    print("BUILD_GRANT_RESUBMISSION_CHECKLIST")
    print(f"target_tracking={payload['target']['grants_tracking_number']}")
    print(f"target_status={payload['target']['status']}")
    print(f"due_utc={payload['execution']['due_utc']}")
    print(f"latest_json={json_latest}")
    print(f"latest_md={md_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
