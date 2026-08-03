from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

CONTROL_ROOM_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"

# Compatibility paths only. Tests and callers can redirect every write.
OUT_JSON = OUT_OPS / "paid_pilot_outreach_queue_latest.json"
OUT_CSV = OUT_OPS / "paid_pilot_outreach_queue_latest.csv"
DASHBOARD_JSON = DASHBOARD_DATA / "paid_pilot_outreach_queue.json"
OUT_MD = DOCS / "PAID_PILOT_OUTREACH_QUEUE_2026-06-25.md"

SCHEMA = "paid_pilot_outreach_queue_v2"
BOUNDARY = (
    "This legacy-named artifact is a local protocol-review scoping queue only. "
    "It identifies bounded services that may be scoped after current-source, duplicate, "
    "recipient-authority, claim, and action-time approval checks. It does not identify a "
    "performance champion, select a recipient, create a send-ready target, authorize outreach, "
    "claim field validation or savings, or inherit any geometry performance claim."
)

SERVICE_SCOPES: tuple[dict[str, Any], ...] = (
    {
        "service_id": "protocol_review",
        "service_name": "Protocol review",
        "price_currency": "USD",
        "price_min": 2500,
        "price_max": 7500,
        "deliverable": (
            "A bounded review of the proposed task, source-native baselines, preregistration, "
            "holdout design, correction rules, reproducibility requirements, and claim limits."
        ),
    },
    {
        "service_id": "optional_benchmark_implementation",
        "service_name": "Optional benchmark implementation",
        "price_currency": "USD",
        "price_min": 7500,
        "price_max": 25000,
        "deliverable": (
            "An optional implementation of a buyer-approved benchmark protocol after data rights, "
            "source-native baselines, acceptance criteria, and scope are documented."
        ),
    },
)

BLOCKED_CLAIMS = [
    "performance champion",
    "field validated",
    "realized savings",
    "projected savings",
    "return on investment",
    "enterprise value",
    "guaranteed outcome",
    "geometry performance advantage",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_scope_row(service: dict[str, Any], rank: int) -> dict[str, Any]:
    row = {
        "rank": rank,
        "scope_id": f"local_{service['service_id']}_scope",
        "service_id": service["service_id"],
        "service_name": service["service_name"],
        "status": "local_draft_only_not_send_ready",
        "deliverable": service["deliverable"],
        "price_currency": service["price_currency"],
        "price_min": service["price_min"],
        "price_max": service["price_max"],
        "pricing_boundary": (
            "Service price only; not ROI, savings, enterprise value, performance value, "
            "or an estimate of customer economic benefit."
        ),
        "performance_champion": False,
        "geometry_performance_claim_inherited": False,
        "field_validation_claim_allowed": False,
        "savings_claim_allowed": False,
        "roi_or_value_claim_allowed": False,
        "target_selected": False,
        "target_organization": "",
        "recipient_selected": False,
        "recipient_name": "",
        "recipient_email": "",
        "send_ready": False,
        "outreach_allowed": False,
        "bulk_or_manual_outreach_allowed": False,
        "blocked_claims": BLOCKED_CLAIMS,
    }
    row["row_sha256"] = stable_sha256(row)
    return row


def build_queue() -> list[dict[str, Any]]:
    return [
        build_scope_row(service, rank)
        for rank, service in enumerate(SERVICE_SCOPES, start=1)
    ]


def build_payload(
    *,
    control_room: dict[str, Any] | None = None,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    source = read_json(CONTROL_ROOM_JSON) if control_room is None else control_room
    source_schema = str(source.get("schema") or "unavailable")
    queue = build_queue()
    queue_chain_sha256 = stable_sha256(queue)

    return {
        "schema": SCHEMA,
        "generated_utc": generated_utc or now_utc(),
        "boundary": BOUNDARY,
        "inputs": {
            "proof_to_pilot_control_room": str(CONTROL_ROOM_JSON.relative_to(ROOT)),
            "source_schema_observed": source_schema,
            "source_used_for_performance_claims": False,
            "source_used_for_target_or_recipient_selection": False,
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "csv": str(OUT_CSV.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "summary": {
            "queue_count": len(queue),
            "local_scope_count": len(queue),
            "performance_champion_count": 0,
            "recipient_selected_count": 0,
            "send_ready_target_count": 0,
            "manual_outreach_ready_count": 0,
            "manual_reviewed_outreach_allowed": False,
            "bulk_outreach_allowed": False,
            "contact_scraping_allowed": False,
            "field_validation_claim_allowed": False,
            "savings_claim_allowed": False,
            "roi_or_value_claim_allowed": False,
            "geometry_performance_claim_inherited": False,
            "queue_chain_sha256": queue_chain_sha256,
        },
        "service_pricing_boundary": {
            "prices_are_service_fees_only": True,
            "prices_are_roi_or_value": False,
            "prices_are_savings_estimates": False,
            "protocol_review_usd": {"min": 2500, "max": 7500},
            "optional_benchmark_implementation_usd": {"min": 7500, "max": 25000},
        },
        "external_action_gate": {
            "state": "blocked_local_scoping_only",
            "outreach_allowed": False,
            "manual_outreach_allowed": False,
            "bulk_outreach_allowed": False,
            "send_without_action_time_approval_allowed": False,
            "current_official_source_verification_required": True,
            "full_thread_and_sent_mail_duplicate_check_required": True,
            "exact_recipient_and_authority_verification_required": True,
            "scope_claims_and_pricing_revalidation_required": True,
            "data_rights_and_baselines_confirmation_required": True,
            "action_time_human_approval_required": True,
        },
        "queue": queue,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    pricing = payload["service_pricing_boundary"]
    gate = payload["external_action_gate"]
    lines = [
        "# Local Protocol-Review Scoping Queue",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Current State",
        "",
        f"- Local scope records: `{summary['local_scope_count']}`",
        f"- Performance champions: `{summary['performance_champion_count']}`",
        f"- Recipients selected: `{summary['recipient_selected_count']}`",
        f"- Send-ready targets: `{summary['send_ready_target_count']}`",
        f"- Manual outreach allowed: `{str(summary['manual_reviewed_outreach_allowed']).lower()}`",
        f"- Bulk outreach allowed: `{str(summary['bulk_outreach_allowed']).lower()}`",
        f"- Field-validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Savings claim allowed: `{str(summary['savings_claim_allowed']).lower()}`",
        f"- Geometry performance claim inherited: `{str(summary['geometry_performance_claim_inherited']).lower()}`",
        f"- Queue chain SHA-256: `{summary['queue_chain_sha256']}`",
        "",
        "## Allowed Service Ranges",
        "",
        (
            "- Protocol review: "
            f"`${pricing['protocol_review_usd']['min']:,}-${pricing['protocol_review_usd']['max']:,}`"
        ),
        (
            "- Optional benchmark implementation: "
            f"`${pricing['optional_benchmark_implementation_usd']['min']:,}-"
            f"${pricing['optional_benchmark_implementation_usd']['max']:,}`"
        ),
        "- These are service fees only, not ROI, savings, value, or customer-benefit estimates.",
        "",
        "## Local Scope Records",
        "",
    ]
    for row in payload["queue"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['service_name']}",
                "",
                f"- Status: `{row['status']}`",
                f"- Deliverable: {row['deliverable']}",
                f"- Service range: `${row['price_min']:,}-${row['price_max']:,}`",
                f"- Recipient selected: `{str(row['recipient_selected']).lower()}`",
                f"- Send ready: `{str(row['send_ready']).lower()}`",
                f"- Outreach allowed: `{str(row['outreach_allowed']).lower()}`",
                f"- Pricing boundary: {row['pricing_boundary']}",
                "",
            ]
        )
    lines.extend(
        [
            "## External Action Gate",
            "",
            f"- State: `{gate['state']}`",
            "- Verify the current official source before selecting any target.",
            "- Check the complete thread and Sent mail for duplicates.",
            "- Verify the exact recipient and their authority.",
            "- Revalidate scope, claims, pricing, data rights, and source-native baselines.",
            "- Obtain explicit action-time human approval before any external message.",
        ]
    )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "rank",
        "scope_id",
        "service_id",
        "service_name",
        "status",
        "price_currency",
        "price_min",
        "price_max",
        "target_selected",
        "recipient_selected",
        "send_ready",
        "outreach_allowed",
        "geometry_performance_claim_inherited",
        "row_sha256",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_outputs(
    payload: dict[str, Any],
    *,
    json_path: Path,
    csv_path: Path,
    markdown_path: Path,
    dashboard_json_path: Path | None = None,
) -> None:
    write_json(json_path, payload)
    write_csv(csv_path, payload["queue"])
    write_text(markdown_path, render_markdown(payload))
    if dashboard_json_path is not None:
        write_json(dashboard_json_path, payload)


def main() -> int:
    payload = build_payload()
    write_outputs(
        payload,
        json_path=OUT_JSON,
        csv_path=OUT_CSV,
        markdown_path=OUT_MD,
        dashboard_json_path=DASHBOARD_JSON,
    )
    print(f"wrote {OUT_JSON}")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {DASHBOARD_JSON}")
    print(f"wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
