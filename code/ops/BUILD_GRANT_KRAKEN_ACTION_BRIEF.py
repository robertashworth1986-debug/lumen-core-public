from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = ROOT / "out" / "ops"
EXEC_ROOT = ROOT / "out" / "execution"

LEDGER_LATEST = OPS_ROOT / "grants_live_submission_ledger_latest.json"
WAITING_LATEST = OPS_ROOT / "grant_waiting_actions_latest.json"
FOLLOWUP_LATEST = OPS_ROOT / "grant_followup_tracker_latest.json"
RESUB_LATEST = OPS_ROOT / "grant_resubmission_checklist_latest.json"
BLEED_LATEST = OPS_ROOT / "trader_bleed_snapshot" / "trader_bleed_snapshot_latest.json"

EXEC_HEARTBEAT = EXEC_ROOT / "live_executor_heartbeat.json"
GROWTH_STATUS = EXEC_ROOT / "vps_growth_controller_status.json"

OUT_DIR = OPS_ROOT / "grant_kraken_action_brief"


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


def parse_iso_to_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def age_seconds_from_iso(value: Any) -> float | None:
    dt = parse_iso_to_dt(value)
    if dt is None:
        return None
    return (now_utc() - dt).total_seconds()


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def extract_actions(
    waiting_payload: dict[str, Any],
    followup_payload: dict[str, Any],
    resub_payload: dict[str, Any],
    bleed_payload: dict[str, Any],
    exec_hb_payload: dict[str, Any],
    growth_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []

    waiting_headline = waiting_payload.get("headline", {}) if isinstance(waiting_payload, dict) else {}
    blocked_count = to_int(waiting_headline.get("blocked_count", 0))
    waiting_count = to_int(waiting_headline.get("waiting_followup_count", 0))

    blocked_rows = waiting_payload.get("blocked_or_fix_now", []) if isinstance(waiting_payload, dict) else []
    if isinstance(blocked_rows, list):
        for row in blocked_rows:
            if not isinstance(row, dict):
                continue
            actions.append(
                {
                    "priority": "P0",
                    "lane": "grants_ops",
                    "title": "Recover rejected grant submission now",
                    "detail": f"{row.get('opp_num', '')} / {row.get('grants_tracking_number', '')} status={row.get('status', '')}",
                    "due_utc": row.get("due_utc", ""),
                    "command": "python code/ops/BUILD_GRANT_RESUBMISSION_CHECKLIST.py --owner 'Robert Ashworth'",
                }
            )

    if blocked_count == 0 and waiting_count > 0:
        actions.append(
            {
                "priority": "P1",
                "lane": "grants_ops",
                "title": "Maintain grant follow-up cadence",
                "detail": f"waiting_followup_count={waiting_count}",
                "due_utc": (now_utc() + timedelta(hours=24)).isoformat(),
                "command": "python code/ops/BUILD_GRANT_FOLLOWUP_TRACKER.py",
            }
        )

    followup_headline = followup_payload.get("headline", {}) if isinstance(followup_payload, dict) else {}
    if to_int(followup_headline.get("rows", 0)) > 0:
        actions.append(
            {
                "priority": "P1",
                "lane": "grants_ops",
                "title": "Execute today follow-up tasks",
                "detail": f"tracker_rows={to_int(followup_headline.get('rows', 0))}",
                "due_utc": (now_utc() + timedelta(hours=8)).isoformat(),
                "command": "python code/ops/BUILD_GRANT_WAITING_ACTIONS.py",
            }
        )

    resub_target = resub_payload.get("target", {}) if isinstance(resub_payload, dict) else {}
    if str(resub_target.get("status", "")).strip().lower() == "rejected_with_errors":
        actions.append(
            {
                "priority": "P0",
                "lane": "grants_ops",
                "title": "Capture validation error codes before resubmission",
                "detail": f"tracking={resub_target.get('grants_tracking_number', '')}",
                "due_utc": str((resub_payload.get("execution", {}) if isinstance(resub_payload, dict) else {}).get("due_utc", "")),
                "command": "Open Grants.gov status details and patch SF-424/package fields",
            }
        )

    hb_age = age_seconds_from_iso(exec_hb_payload.get("timestamp_utc"))
    hb_status = str(exec_hb_payload.get("status", "")).strip()
    symbol_intel_stale = bool(exec_hb_payload.get("symbol_intel_stale", False))
    symbol_intel_age = to_float(exec_hb_payload.get("symbol_intel_age_sec", 0.0))

    if hb_age is not None and hb_age > 1200.0:
        actions.append(
            {
                "priority": "P1",
                "lane": "execution_ops",
                "title": "Refresh stale live executor heartbeat",
                "detail": f"status={hb_status} age_sec={round(hb_age, 1)}",
                "due_utc": (now_utc() + timedelta(minutes=30)).isoformat(),
                "command": "python code/execution/kraken_live_growth_controller.py --cached --controller Robert",
            }
        )

    if symbol_intel_stale or symbol_intel_age > 21600.0:
        actions.append(
            {
                "priority": "P1",
                "lane": "execution_quant",
                "title": "Rebuild stale symbol-intel cache",
                "detail": f"symbol_intel_stale={symbol_intel_stale} symbol_intel_age_sec={round(symbol_intel_age, 1)}",
                "due_utc": (now_utc() + timedelta(hours=2)).isoformat(),
                "command": "python code/execution/symbol_flip_intel_daemon.py",
            }
        )

    guard = growth_payload.get("guard", {}) if isinstance(growth_payload, dict) else {}
    guard_reasons = guard.get("reasons", []) if isinstance(guard, dict) else []
    if not isinstance(guard_reasons, list):
        guard_reasons = []
    mode = str(growth_payload.get("mode", ""))
    heartbeat_age_min = to_float(guard.get("heartbeat_age_minutes", 0.0))

    if guard_reasons:
        actions.append(
            {
                "priority": "P1",
                "lane": "execution_ops",
                "title": "Resolve Kraken controller guard blockers",
                "detail": f"mode={mode} reasons={','.join(str(r) for r in guard_reasons)} heartbeat_age_min={round(heartbeat_age_min, 2)}",
                "due_utc": (now_utc() + timedelta(hours=1)).isoformat(),
                "command": "python code/execution/kraken_live_growth_controller.py --cached --controller Robert",
            }
        )

    diag = bleed_payload.get("diagnosis", {}) if isinstance(bleed_payload, dict) else {}
    findings = diag.get("findings", []) if isinstance(diag, dict) else []
    if not isinstance(findings, list):
        findings = []
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        severity = str(finding.get("severity", "")).strip().lower()
        if severity == "high":
            actions.append(
                {
                    "priority": "P1",
                    "lane": "execution_risk",
                    "title": "Patch bleed risk finding",
                    "detail": f"{finding.get('issue', '')}: {finding.get('detail', '')}",
                    "due_utc": (now_utc() + timedelta(hours=4)).isoformat(),
                    "command": "python code/ops/ANALYZE_TRADER_BLEED.py",
                }
            )

    priorities = {"P0": 0, "P1": 1, "P2": 2}
    actions.sort(key=lambda row: priorities.get(str(row.get("priority", "P2")), 3))
    return actions


def build_payload() -> dict[str, Any]:
    ledger = load_json(LEDGER_LATEST, {})
    waiting = load_json(WAITING_LATEST, {})
    followup = load_json(FOLLOWUP_LATEST, {})
    resub = load_json(RESUB_LATEST, {})
    bleed = load_json(BLEED_LATEST, {})
    exec_hb = load_json(EXEC_HEARTBEAT, {})
    growth = load_json(GROWTH_STATUS, {})

    actions = extract_actions(waiting, followup, resub, bleed, exec_hb, growth)

    payload = {
        "generated_utc": now_iso(),
        "scope": "grant_kraken_action_brief",
        "snapshot": {
            "ledger_record_count": to_int((ledger.get("summary", {}) if isinstance(ledger, dict) else {}).get("record_count", 0)),
            "grants_blocked_count": to_int((waiting.get("headline", {}) if isinstance(waiting, dict) else {}).get("blocked_count", 0)),
            "grants_waiting_followup_count": to_int((waiting.get("headline", {}) if isinstance(waiting, dict) else {}).get("waiting_followup_count", 0)),
            "executor_status": str(exec_hb.get("status", "")) if isinstance(exec_hb, dict) else "",
            "executor_heartbeat_age_sec": age_seconds_from_iso((exec_hb.get("timestamp_utc", "") if isinstance(exec_hb, dict) else "")),
            "symbol_intel_stale": bool(exec_hb.get("symbol_intel_stale", False)) if isinstance(exec_hb, dict) else False,
            "symbol_intel_age_sec": to_float((exec_hb.get("symbol_intel_age_sec", 0.0) if isinstance(exec_hb, dict) else 0.0)),
            "controller_mode": str(growth.get("mode", "")) if isinstance(growth, dict) else "",
            "controller_guard_reasons": (growth.get("guard", {}) if isinstance(growth, dict) else {}).get("reasons", []),
            "bleed_findings_count": len((bleed.get("diagnosis", {}) if isinstance(bleed, dict) else {}).get("findings", [])),
        },
        "prioritized_actions": actions,
        "evidence_paths": {
            "grants_live_submission_ledger_latest_json": str(LEDGER_LATEST),
            "grant_waiting_actions_latest_json": str(WAITING_LATEST),
            "grant_followup_tracker_latest_json": str(FOLLOWUP_LATEST),
            "grant_resubmission_checklist_latest_json": str(RESUB_LATEST),
            "trader_bleed_snapshot_latest_json": str(BLEED_LATEST),
            "live_executor_heartbeat_json": str(EXEC_HEARTBEAT),
            "vps_growth_controller_status_json": str(GROWTH_STATUS),
        },
    }
    return payload


def build_markdown(payload: dict[str, Any]) -> str:
    snapshot = payload.get("snapshot", {}) if isinstance(payload, dict) else {}
    actions = payload.get("prioritized_actions", []) if isinstance(payload, dict) else []
    if not isinstance(actions, list):
        actions = []

    lines: list[str] = []
    lines.append("# Grant + Kraken Action Brief")
    lines.append("")
    lines.append(f"Generated UTC: {payload.get('generated_utc', '')}")
    lines.append("")
    lines.append("## Snapshot")
    lines.append(f"- Grant ledger records: {to_int(snapshot.get('ledger_record_count', 0))}")
    lines.append(f"- Grant blocked count: {to_int(snapshot.get('grants_blocked_count', 0))}")
    lines.append(f"- Grant waiting follow-up count: {to_int(snapshot.get('grants_waiting_followup_count', 0))}")
    lines.append(f"- Executor status: {snapshot.get('executor_status', '')}")
    lines.append(f"- Executor heartbeat age sec: {to_float(snapshot.get('executor_heartbeat_age_sec', 0.0)):.1f}")
    lines.append(f"- Symbol intel stale: {bool(snapshot.get('symbol_intel_stale', False))}")
    lines.append(f"- Symbol intel age sec: {to_float(snapshot.get('symbol_intel_age_sec', 0.0)):.1f}")
    lines.append(f"- Controller mode: {snapshot.get('controller_mode', '')}")
    lines.append(f"- Bleed findings count: {to_int(snapshot.get('bleed_findings_count', 0))}")
    lines.append("")
    lines.append("## Prioritized Actions")

    if actions:
        for idx, row in enumerate(actions, start=1):
            lines.append(
                f"{idx}. {row.get('priority', 'P2')} | {row.get('lane', '')} | {row.get('title', '')}"
            )
            lines.append(f"   - detail: {row.get('detail', '')}")
            lines.append(f"   - due_utc: {row.get('due_utc', '')}")
            lines.append(f"   - command: {row.get('command', '')}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("## Evidence Paths")
    evidence_paths = payload.get("evidence_paths", {}) if isinstance(payload, dict) else {}
    if isinstance(evidence_paths, dict):
        for key, value in evidence_paths.items():
            lines.append(f"- {key}: {value}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    stamp = now_tag()

    json_tagged = OUT_DIR / f"grant_kraken_action_brief_{stamp}.json"
    json_latest = OUT_DIR / "grant_kraken_action_brief_latest.json"
    md_tagged = OUT_DIR / f"grant_kraken_action_brief_{stamp}.md"
    md_latest = OUT_DIR / "grant_kraken_action_brief_latest.md"

    write_json(json_tagged, payload)
    write_json(json_latest, payload)

    md_text = build_markdown(payload)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    print("BUILD_GRANT_KRAKEN_ACTION_BRIEF")
    print(f"actions={len(payload.get('prioritized_actions', []))}")
    print(f"latest_json={json_latest}")
    print(f"latest_md={md_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
