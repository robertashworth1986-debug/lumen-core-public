from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_ROOT = ROOT / "out" / "ops"
SUPPORT_ROOT = OPS_ROOT / "mission_control_support"

LIVE_BREADTH_PATH = OPS_ROOT / "live_breadth_value_panel_latest.json"
READINESS_PATH = OPS_ROOT / "investor_metric_readiness_latest.json"
LINKEDIN_BUILD_PATH = OPS_ROOT / "lumalinkedin_v1_build_latest.json"
MISSION_PACK_PATH = OPS_ROOT / "investor_mission_control" / "investor_mission_control_pack_latest.json"
GRANT_FIT_PATH = OPS_ROOT / "grant_submit_fit_pack" / "grant_submit_fit_pack_latest.json"
GRANT_QUEUE_PATH = ROOT / "out" / "grant_approval_queue.json"
GRANT_EMAIL_RECEIPTS_PATH = OPS_ROOT / "grants_email_receipts_latest.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def to_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def first_nonempty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _signal_metrics(readiness: dict[str, Any]) -> dict[str, Any]:
    summary = readiness.get("summary") if isinstance(readiness, dict) else {}
    if isinstance(summary, dict) and isinstance(summary.get("signal_evidence"), dict):
        return summary.get("signal_evidence", {})
    return {}


def build_helmyer_payload(
    live_breadth: dict[str, Any],
    readiness: dict[str, Any],
    linkedin_build: dict[str, Any],
    mission_pack: dict[str, Any],
    grant_fit: dict[str, Any],
) -> dict[str, Any]:
    headline = live_breadth.get("headline") if isinstance(live_breadth, dict) else {}
    readiness_summary = readiness.get("summary") if isinstance(readiness, dict) else {}
    signal = _signal_metrics(readiness)
    li_metrics = linkedin_build.get("metrics") if isinstance(linkedin_build, dict) else {}
    mission_headline = mission_pack.get("headline") if isinstance(mission_pack, dict) else {}
    fit_summary = grant_fit.get("summary") if isinstance(grant_fit, dict) else {}

    measured = to_int(
        first_nonempty(
            headline.get("measured_sources"),
            signal.get("measured_sources"),
            mission_headline.get("measured_sources"),
        ),
        0,
    )
    enabled = to_int(
        first_nonempty(
            headline.get("enabled_sources"),
            signal.get("enabled_sources"),
            mission_headline.get("enabled_sources"),
        ),
        measured,
    )
    coverage = to_float(
        first_nonempty(
            headline.get("measured_coverage_pct"),
            signal.get("measured_coverage_pct"),
        ),
        0.0,
    )
    annual_value = to_float(
        first_nonempty(
            headline.get("total_estimated_annual_value_usd"),
            signal.get("annual_value_usd"),
            mission_headline.get("annual_value_signal_usd"),
        ),
        0.0,
    )
    top_sector = first_nonempty(
        headline.get("top_sector"),
        signal.get("top_sector"),
        mission_headline.get("top_sector"),
        "n/a",
    )
    top_sector_hourly = to_float(
        first_nonempty(
            headline.get("top_sector_hourly_value_usd"),
            signal.get("top_sector_hourly_value_usd"),
        ),
        0.0,
    )
    router_edge = to_float(
        first_nonempty(
            headline.get("router_edge_pct"),
            signal.get("router_edge_pct"),
            li_metrics.get("router_edge_pct"),
            mission_headline.get("router_edge_pct"),
        ),
        0.0,
    )
    harmonic_win = to_float(
        first_nonempty(
            headline.get("harmonic_win_rate_pct"),
            signal.get("harmonic_win_rate_pct"),
            li_metrics.get("harmonic_win_rate_pct"),
            mission_headline.get("harmonic_win_rate_pct"),
        ),
        0.0,
    )
    runtime_mode = first_nonempty(
        li_metrics.get("runtime_mode"),
        readiness_summary.get("capital_and_risk_gate_evidence", {}).get("runtime_mode") if isinstance(readiness_summary.get("capital_and_risk_gate_evidence"), dict) else "",
        "paper",
    )
    allow_live = bool(
        li_metrics.get("allow_live_orders")
        if "allow_live_orders" in li_metrics
        else (
            readiness_summary.get("capital_and_risk_gate_evidence", {}).get("allow_live_orders")
            if isinstance(readiness_summary.get("capital_and_risk_gate_evidence"), dict)
            else False
        )
    )
    readiness_status = first_nonempty(
        readiness_summary.get("status") if isinstance(readiness_summary, dict) else "",
        mission_headline.get("readiness_status") if isinstance(mission_headline, dict) else "",
        "capital_and_risk_guarded",
    )
    first_action = first_nonempty(
        readiness_summary.get("first_thursday_action") if isinstance(readiness_summary, dict) else "",
        headline.get("first_thursday_action") if isinstance(headline, dict) else "",
        "fund incremental capital allocation to exit micro-notional constraint",
    )

    selected = to_int(fit_summary.get("selected_opportunities") if isinstance(fit_summary, dict) else 0, 0)
    fit_likely = to_int(fit_summary.get("fit_likely") if isinstance(fit_summary, dict) else 0, 0)
    manual_check = to_int(fit_summary.get("manual_check") if isinstance(fit_summary, dict) else 0, 0)

    items = [
        {
            "question": "What is live measured proof coverage right now?",
            "answer": f"{measured}/{enabled} measured sources ({coverage:.2f}% coverage).",
        },
        {
            "question": "What is the current annualized value surface?",
            "answer": f"Modeled annual preserved-value signal is ${annual_value:,.2f}.",
        },
        {
            "question": "Which sector is carrying top mission impact?",
            "answer": f"Top sector is {top_sector} at ${top_sector_hourly:,.2f} per hour.",
        },
        {
            "question": "How strong is the routing and harmonic signal quality?",
            "answer": f"Router edge is {router_edge:.2f}% and harmonic win rate is {harmonic_win:.2f}%.",
        },
        {
            "question": "Is live execution currently enabled?",
            "answer": f"Runtime mode is {runtime_mode}; allow_live_orders is {'ON' if allow_live else 'OFF'} with posture {readiness_status}.",
        },
        {
            "question": "What is the grant submission readiness posture?",
            "answer": f"Selected opportunities: {selected} (fit likely: {fit_likely}, manual check: {manual_check}). Next capital action: {first_action}.",
        },
    ]

    return {
        "generated_utc": now_iso(),
        "scope": "helmyer_qa",
        "items": items,
        "source_artifacts": {
            "live_breadth_value_panel_latest": str(LIVE_BREADTH_PATH),
            "investor_metric_readiness_latest": str(READINESS_PATH),
            "lumalinkedin_v1_build_latest": str(LINKEDIN_BUILD_PATH),
            "investor_mission_control_pack_latest": str(MISSION_PACK_PATH),
            "grant_submit_fit_pack_latest": str(GRANT_FIT_PATH),
        },
    }


def _norm_status(value: Any) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    return "_".join(part for part in text.replace("-", " ").split() if part)


def build_grants_live_submission_ledger(
    grant_queue: dict[str, Any],
    grant_fit: dict[str, Any],
    email_receipts: dict[str, Any],
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    queue_records_added = 0
    email_records_added = 0

    queue_items: list[Any] = []
    if isinstance(grant_queue, dict):
        if isinstance(grant_queue.get("items"), list):
            queue_items = grant_queue.get("items", [])
        elif isinstance(grant_queue.get("records"), list):
            queue_items = grant_queue.get("records", [])

    for row in queue_items:
        if not isinstance(row, dict):
            continue
        status = _norm_status(first_nonempty(row.get("status"), row.get("state")))
        if "submit" not in status:
            continue
        opp_num = first_nonempty(row.get("opp_num"), row.get("opportunity_number"), row.get("opportunity_id"))
        grants_tracking_number = first_nonempty(
            row.get("grants_tracking_number"),
            row.get("tracking_number"),
            row.get("tracking_id"),
        )
        workspace_id = first_nonempty(row.get("workspace_id"), row.get("workspace"))
        if not (opp_num or grants_tracking_number or workspace_id):
            continue
        key = (opp_num, grants_tracking_number, workspace_id)
        if key in seen:
            continue
        seen.add(key)
        records.append(
            {
                "opp_num": opp_num,
                "status": "submitted",
                "grants_tracking_number": grants_tracking_number,
                "workspace_id": workspace_id,
                "source": "grant_approval_queue",
            }
        )
        queue_records_added += 1

    receipt_rows = email_receipts.get("records") if isinstance(email_receipts, dict) else []
    if isinstance(receipt_rows, list):
        for row in receipt_rows:
            if not isinstance(row, dict):
                continue
            opp_num = first_nonempty(row.get("opp_num"), row.get("opportunity_number"), row.get("opportunity_id"))
            grants_tracking_number = first_nonempty(
                row.get("grants_tracking_number"),
                row.get("tracking_number"),
                row.get("tracking_id"),
            )
            workspace_id = first_nonempty(row.get("workspace_id"), row.get("workspace"))
            if not (opp_num or grants_tracking_number or workspace_id):
                continue
            key = (opp_num, grants_tracking_number, workspace_id)
            if key in seen:
                continue
            seen.add(key)

            status = _norm_status(first_nonempty(row.get("status"), "submitted_email_receipt"))
            if not status:
                status = "submitted_email_receipt"
            source = first_nonempty(row.get("source"), "gmail_manual_receipt")

            merged = {
                "opp_num": opp_num,
                "status": status,
                "grants_tracking_number": grants_tracking_number,
                "workspace_id": workspace_id,
                "source": source,
            }

            for field in (
                "grant_id",
                "agency_tracking_number",
                "application_name",
                "aor_name",
                "uei",
                "event_utc",
                "email_subject",
                "email_received_local",
                "email_link",
                "opportunity_name",
                "notes",
            ):
                value = row.get(field)
                if value not in (None, ""):
                    merged[field] = value

            records.append(merged)
            email_records_added += 1

    fit_summary = grant_fit.get("summary") if isinstance(grant_fit, dict) else {}
    selected = to_int(fit_summary.get("selected_opportunities") if isinstance(fit_summary, dict) else 0, 0)
    fit_likely = to_int(fit_summary.get("fit_likely") if isinstance(fit_summary, dict) else 0, 0)

    if records and queue_records_added and email_records_added:
        notes = (
            "Derived from submitted records found in grant approval queue artifacts and "
            "manual external email receipt ingestion."
        )
    elif records and email_records_added:
        notes = "Derived from manual external email receipt ingestion."
    elif records:
        notes = "Derived from submitted records found in grant approval queue artifacts."
    else:
        notes = (
            "No externally confirmed submitted records found in local queue artifacts; "
            "ledger intentionally empty until validated submissions are present."
        )

    return {
        "generated_utc": now_iso(),
        "scope": "grants_live_submission_ledger",
        "records": records,
        "summary": {
            "record_count": len(records),
            "fit_selected_opportunities": selected,
            "fit_likely_count": fit_likely,
            "queue_records_added": queue_records_added,
            "email_records_added": email_records_added,
        },
        "notes": notes,
        "source_artifacts": {
            "grant_approval_queue": str(GRANT_QUEUE_PATH),
            "grant_submit_fit_pack_latest": str(GRANT_FIT_PATH),
            "grants_email_receipts_latest": str(GRANT_EMAIL_RECEIPTS_PATH),
        },
    }


def main() -> int:
    live_breadth = load_json(LIVE_BREADTH_PATH, {})
    readiness = load_json(READINESS_PATH, {})
    linkedin_build = load_json(LINKEDIN_BUILD_PATH, {})
    mission_pack = load_json(MISSION_PACK_PATH, {})
    grant_fit = load_json(GRANT_FIT_PATH, {})
    grant_queue = load_json(GRANT_QUEUE_PATH, {})
    email_receipts = load_json(GRANT_EMAIL_RECEIPTS_PATH, {})

    helmyer_payload = build_helmyer_payload(
        live_breadth=live_breadth,
        readiness=readiness,
        linkedin_build=linkedin_build,
        mission_pack=mission_pack,
        grant_fit=grant_fit,
    )
    grant_ledger_payload = build_grants_live_submission_ledger(
        grant_queue=grant_queue,
        grant_fit=grant_fit,
        email_receipts=email_receipts,
    )

    stamp = now_tag()
    helmyer_tagged = OPS_ROOT / f"helmyer_qa_{stamp}.json"
    helmyer_latest = OPS_ROOT / "helmyer_qa_latest.json"
    grants_tagged = OPS_ROOT / f"grants_live_submission_ledger_{stamp}.json"
    grants_latest = OPS_ROOT / "grants_live_submission_ledger_latest.json"

    write_json(helmyer_tagged, helmyer_payload)
    write_json(helmyer_latest, helmyer_payload)
    write_json(grants_tagged, grant_ledger_payload)
    write_json(grants_latest, grant_ledger_payload)

    summary = {
        "generated_utc": now_iso(),
        "scope": "mission_control_support_artifacts",
        "artifacts": {
            "helmyer_qa_latest_json": str(helmyer_latest),
            "helmyer_qa_tagged_json": str(helmyer_tagged),
            "grants_live_submission_ledger_latest_json": str(grants_latest),
            "grants_live_submission_ledger_tagged_json": str(grants_tagged),
        },
        "stats": {
            "helmyer_items": len(helmyer_payload.get("items", [])),
            "external_submission_records": len(grant_ledger_payload.get("records", [])),
        },
    }

    summary_tagged = SUPPORT_ROOT / f"mission_control_support_{stamp}.json"
    summary_latest = SUPPORT_ROOT / "mission_control_support_latest.json"
    heartbeat_latest = SUPPORT_ROOT / "mission_control_support_heartbeat_latest.json"

    write_json(summary_tagged, summary)
    write_json(summary_latest, summary)
    write_json(
        heartbeat_latest,
        {
            "generated_utc": summary["generated_utc"],
            "scope": "mission_control_support_artifacts",
            "status": "ok",
            "helmyer_items": summary["stats"]["helmyer_items"],
            "external_submission_records": summary["stats"]["external_submission_records"],
            "latest_artifact": str(summary_tagged),
        },
    )

    print("BUILD_MISSION_CONTROL_SUPPORT_ARTIFACTS")
    print(f"helmyer_items={summary['stats']['helmyer_items']}")
    print(f"external_submission_records={summary['stats']['external_submission_records']}")
    print(f"helmyer_latest={helmyer_latest}")
    print(f"grants_ledger_latest={grants_latest}")
    print(f"summary={summary_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
