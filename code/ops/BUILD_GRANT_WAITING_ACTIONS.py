from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = ROOT / "out" / "ops"
LEDGER_LATEST = OPS_ROOT / "grants_live_submission_ledger_latest.json"
PORTAL_BULK_LATEST = OPS_ROOT / "grants_portal_bulk_intake" / "grants_portal_bulk_intake_20260602_1549Z.json"


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


def norm_status(value: Any) -> str:
    text = str(value or "").strip().lower().replace("-", " ")
    return "_".join(part for part in text.split() if part)


def norm_opp(value: Any) -> str:
    return str(value or "").strip().upper()


def classify_status(status: str) -> str:
    if any(token in status for token in ("rejected", "error", "invalid", "denied")):
        return "blocked"
    if any(token in status for token in ("received_by_agency", "agency_tracking", "submitted", "validated")):
        return "waiting"
    return "info"


def waiting_actions() -> list[str]:
    return [
        "Keep this lane in monitor mode; check status detail daily until agency review outcome changes.",
        "Pre-stage clarifications, budget backup, and technical narrative addenda for rapid response to agency requests.",
        "If no movement after 5 business days, send a status inquiry through agency/grants support channel with tracking number.",
    ]


def blocked_actions() -> list[str]:
    return [
        "Open Grants.gov status detail for this tracking number and capture exact validation errors.",
        "Patch SF-424/package fields, regenerate package, and resubmit under same opportunity in the next 24 hours.",
        "Log corrected submission tracking number back into grants_email_receipts_latest.json and rerun BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS.py.",
    ]


def build_payload(ledger: dict[str, Any]) -> dict[str, Any]:
    rows = ledger.get("records") if isinstance(ledger, dict) else []
    records = rows if isinstance(rows, list) else []

    waiting_opp_keys: set[str] = set()
    for row in records:
        if not isinstance(row, dict):
            continue
        opp_key = norm_opp(row.get("opp_num"))
        if not opp_key:
            continue
        status = norm_status(row.get("status"))
        if classify_status(status) == "waiting":
            waiting_opp_keys.add(opp_key)

    newly_submitted: list[dict[str, Any]] = []
    waiting_followups: list[dict[str, Any]] = []
    blocked_fix_now: list[dict[str, Any]] = []
    info_rows: list[dict[str, Any]] = []

    run_now = now_utc()

    for row in records:
        if not isinstance(row, dict):
            continue

        status = norm_status(row.get("status"))
        category = classify_status(status)
        source = str(row.get("source") or "").strip()
        tracking = str(row.get("grants_tracking_number") or "").strip()
        opp_num = str(row.get("opp_num") or "").strip()
        opp_key = norm_opp(opp_num)

        base = {
            "opp_num": opp_num,
            "grants_tracking_number": tracking,
            "status": status,
            "status_local_time": str(row.get("email_received_local") or ""),
            "source": source,
        }

        if source.lower() == "grantsgov_status_check":
            newly_submitted.append(dict(base))

        if category == "blocked":
            if opp_key in waiting_opp_keys:
                enriched = dict(base)
                enriched["priority"] = "P2"
                enriched["next_actions"] = [
                    "Superseded by a newer tracking lane on this same opportunity that is already in waiting/agency-review state.",
                    "Preserve for audit history only; do not treat as active blocker unless the waiting lane regresses.",
                ]
                enriched["superseded_by_waiting_lane"] = True
                info_rows.append(enriched)
                continue
            enriched = dict(base)
            enriched["priority"] = "P0"
            enriched["next_actions"] = blocked_actions()
            enriched["due_utc"] = (run_now + timedelta(hours=24)).isoformat()
            blocked_fix_now.append(enriched)
        elif category == "waiting":
            enriched = dict(base)
            enriched["priority"] = "P1"
            enriched["next_actions"] = waiting_actions()
            enriched["due_utc"] = (run_now + timedelta(hours=24)).isoformat()
            waiting_followups.append(enriched)
        else:
            enriched = dict(base)
            enriched["priority"] = "P2"
            enriched["next_actions"] = ["No immediate action required; retain for audit trail."]
            info_rows.append(enriched)

    payload = {
        "generated_utc": now_iso(),
        "scope": "grant_waiting_actions",
        "headline": {
            "ledger_record_count": len(records),
            "newly_submitted_status_rows": len(newly_submitted),
            "waiting_followup_count": len(waiting_followups),
            "blocked_count": len(blocked_fix_now),
        },
        "newly_submitted": newly_submitted,
        "waiting_followups": waiting_followups,
        "blocked_or_fix_now": blocked_fix_now,
        "info": info_rows,
        "evidence": {
            "ledger_latest_json": str(LEDGER_LATEST),
            "portal_bulk_intake_json": str(PORTAL_BULK_LATEST),
        },
    }
    return payload


def build_markdown(payload: dict[str, Any]) -> str:
    waiting_rows = payload.get("waiting_followups") if isinstance(payload, dict) else []
    blocked_rows = payload.get("blocked_or_fix_now") if isinstance(payload, dict) else []
    waiting_rows = waiting_rows if isinstance(waiting_rows, list) else []
    blocked_rows = blocked_rows if isinstance(blocked_rows, list) else []

    lines: list[str] = [
        "# Grant Waiting Actions",
        "",
        f"Generated UTC: {payload.get('generated_utc', '')}",
        "",
        "## Headline",
        "",
        f"- Ledger records: {payload.get('headline', {}).get('ledger_record_count', 0)}",
        f"- Newly submitted status rows: {payload.get('headline', {}).get('newly_submitted_status_rows', 0)}",
        f"- Waiting follow-ups: {payload.get('headline', {}).get('waiting_followup_count', 0)}",
        f"- Blocked/fix-now: {payload.get('headline', {}).get('blocked_count', 0)}",
        "",
        "## Waiting Follow-Ups",
        "",
    ]

    if waiting_rows:
        for idx, row in enumerate(waiting_rows, start=1):
            lines.append(
                f"{idx}. {row.get('opp_num', '')} | {row.get('grants_tracking_number', '')} | {row.get('status', '')}"
            )
            for action in row.get("next_actions", []) or []:
                lines.append(f"   - {action}")
    else:
        lines.append("- none")

    lines += ["", "## Blocked / Fix-Now", ""]

    if blocked_rows:
        for idx, row in enumerate(blocked_rows, start=1):
            lines.append(
                f"{idx}. {row.get('opp_num', '')} | {row.get('grants_tracking_number', '')} | {row.get('status', '')}"
            )
            for action in row.get("next_actions", []) or []:
                lines.append(f"   - {action}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ledger = load_json(LEDGER_LATEST, {})
    payload = build_payload(ledger)

    stamp = now_tag()
    json_tagged = OPS_ROOT / f"grant_waiting_actions_{stamp}.json"
    json_latest = OPS_ROOT / "grant_waiting_actions_latest.json"
    md_tagged = OPS_ROOT / f"grant_waiting_actions_{stamp}.md"
    md_latest = OPS_ROOT / "grant_waiting_actions_latest.md"

    write_json(json_tagged, payload)
    write_json(json_latest, payload)

    md_text = build_markdown(payload)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    print("BUILD_GRANT_WAITING_ACTIONS")
    print(f"ledger_record_count={payload['headline']['ledger_record_count']}")
    print(f"waiting_followup_count={payload['headline']['waiting_followup_count']}")
    print(f"blocked_count={payload['headline']['blocked_count']}")
    print(f"latest_json={json_latest}")
    print(f"latest_md={md_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
