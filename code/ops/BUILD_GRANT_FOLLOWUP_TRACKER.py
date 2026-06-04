from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = ROOT / "out" / "ops"
WAITING_ACTIONS_LATEST = OPS_ROOT / "grant_waiting_actions_latest.json"


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


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "priority",
        "opp_num",
        "grants_tracking_number",
        "status",
        "owner",
        "cadence",
        "action",
        "due_utc",
        "escalation_utc",
        "source",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in fields})


def build_rows(payload: dict[str, Any], owner: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    run_now = now_utc()

    blocked = payload.get("blocked_or_fix_now") if isinstance(payload, dict) else []
    waiting = payload.get("waiting_followups") if isinstance(payload, dict) else []
    blocked = blocked if isinstance(blocked, list) else []
    waiting = waiting if isinstance(waiting, list) else []

    for item in blocked:
        if not isinstance(item, dict):
            continue
        actions = item.get("next_actions") if isinstance(item.get("next_actions"), list) else []
        for idx, action in enumerate(actions):
            due = run_now + timedelta(hours=(idx + 1) * 6)
            rows.append(
                {
                    "priority": "P0",
                    "opp_num": str(item.get("opp_num") or "").strip(),
                    "grants_tracking_number": str(item.get("grants_tracking_number") or "").strip(),
                    "status": str(item.get("status") or "").strip(),
                    "owner": owner,
                    "cadence": "same_day_recovery",
                    "action": str(action),
                    "due_utc": due.isoformat(),
                    "escalation_utc": (run_now + timedelta(hours=24)).isoformat(),
                    "source": str(item.get("source") or "").strip(),
                }
            )

    for item in waiting:
        if not isinstance(item, dict):
            continue
        actions = item.get("next_actions") if isinstance(item.get("next_actions"), list) else []
        schedule = [1, 3, 5]
        for idx, action in enumerate(actions[:3]):
            day_offset = schedule[idx] if idx < len(schedule) else (idx + 1)
            due = run_now + timedelta(days=day_offset)
            rows.append(
                {
                    "priority": "P1",
                    "opp_num": str(item.get("opp_num") or "").strip(),
                    "grants_tracking_number": str(item.get("grants_tracking_number") or "").strip(),
                    "status": str(item.get("status") or "").strip(),
                    "owner": owner,
                    "cadence": "daily_then_5_day_escalation",
                    "action": str(action),
                    "due_utc": due.isoformat(),
                    "escalation_utc": (run_now + timedelta(days=5)).isoformat(),
                    "source": str(item.get("source") or "").strip(),
                }
            )

    rows.sort(key=lambda r: (r.get("due_utc", ""), r.get("priority", "")))
    return rows


def build_markdown(payload: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Grant Follow-Up Tracker",
        "",
        f"Generated UTC: {payload.get('generated_utc', '')}",
        "",
        "## Headline",
        "",
        f"- rows: {len(rows)}",
        f"- blocked lanes: {payload.get('headline', {}).get('blocked_count', 0)}",
        f"- waiting lanes: {payload.get('headline', {}).get('waiting_followup_count', 0)}",
        "",
        "## Tasks",
        "",
    ]

    if rows:
        for idx, row in enumerate(rows, start=1):
            lines.append(
                f"{idx}. [{row.get('priority', '')}] {row.get('opp_num', '')} / {row.get('grants_tracking_number', '')}"
            )
            lines.append(f"   - due_utc: {row.get('due_utc', '')}")
            lines.append(f"   - action: {row.get('action', '')}")
    else:
        lines.append("- none")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = load_json(WAITING_ACTIONS_LATEST, {})
    owner = "Robert Ashworth"
    rows = build_rows(payload, owner=owner)

    stamp = now_tag()
    report = {
        "generated_utc": now_iso(),
        "scope": "grant_followup_tracker",
        "owner": owner,
        "headline": {
            "rows": len(rows),
            "blocked_count": payload.get("headline", {}).get("blocked_count", 0),
            "waiting_followup_count": payload.get("headline", {}).get("waiting_followup_count", 0),
        },
        "rows": rows,
        "source_artifacts": {
            "waiting_actions_latest_json": str(WAITING_ACTIONS_LATEST),
        },
    }

    json_tagged = OPS_ROOT / f"grant_followup_tracker_{stamp}.json"
    json_latest = OPS_ROOT / "grant_followup_tracker_latest.json"
    csv_tagged = OPS_ROOT / f"grant_followup_tracker_{stamp}.csv"
    csv_latest = OPS_ROOT / "grant_followup_tracker_latest.csv"
    md_tagged = OPS_ROOT / f"grant_followup_tracker_{stamp}.md"
    md_latest = OPS_ROOT / "grant_followup_tracker_latest.md"

    write_json(json_tagged, report)
    write_json(json_latest, report)
    write_csv(csv_tagged, rows)
    write_csv(csv_latest, rows)

    md_text = build_markdown(report, rows)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    print("BUILD_GRANT_FOLLOWUP_TRACKER")
    print(f"rows={len(rows)}")
    print(f"latest_json={json_latest}")
    print(f"latest_csv={csv_latest}")
    print(f"latest_md={md_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
