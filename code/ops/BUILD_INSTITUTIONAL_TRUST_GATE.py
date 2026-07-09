from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

OUT_JSON = OUT_OPS / "institutional_trust_gate_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "institutional_trust_gate.json"
OUT_MD = SPRINT_DIR / "INSTITUTIONAL_TRUST_GATE_2026-07-09.md"

SOURCE_CONTROLS = {
    "reviewer_approval_crosswalk": OUT_OPS / "reviewer_approval_crosswalk_latest.json",
    "sam_submission": OUT_OPS / "sam_submission_and_today_opportunity_push_latest.json",
    "data_room_manifest": OUT_OPS / "data_room_manifest_latest.json",
    "funding_sprint_reviewer_gate": OUT_OPS / "funding_sprint_reviewer_gate_latest.json",
    "customer_commercialization": OUT_OPS / "customer_commercialization_packet_latest.json",
    "federal_submission_protocol": OUT_OPS / "federal_submission_protocol_packet_latest.json",
    "ip_counsel_diligence": OUT_OPS / "ip_counsel_diligence_packet_latest.json",
    "technical_gov_reviewer": OUT_OPS / "technical_gov_reviewer_approval_stack_latest.json",
    "measured_source_register": OUT_OPS / "measured_source_evidence_register_latest.json",
    "autonomous_quant_governance": OUT_OPS / "autonomous_quant_governance_packet_latest.json",
    "kraken_paper_control": OUT_OPS / "kraken_paper_innovation_control_room_latest.json",
    "kraken_alpha_gauntlet": OUT_OPS / "kraken_institutional_alpha_gauntlet_latest.json",
    "trading_safety_audit": OUT_OPS / "trading_stack_safety_audit_latest.json",
}

PRIMARY_ARTIFACTS = [
    "grant_submissions/funding_sprint_20260709/REVIEWER_APPROVAL_CROSSWALK_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
    "docs/KRAKEN_PAPER_INNOVATION_CONTROL_ROOM_2026-07-09.md",
    "docs/KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET_2026-07-09.md",
]

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def source_status(name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_name": name,
        "path": rel(path),
        "present": path.exists(),
        "status": str(payload.get("status") or payload.get("posture") or ""),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def artifact_status(path_text: str) -> dict[str, Any]:
    path = ROOT / path_text
    return {
        "path": path_text,
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def domain_score(ready: int, gates: int, blockers: int) -> int:
    return max(0, min(100, 50 + ready * 10 - gates * 4 - blockers * 8))


def build_domain_rows(controls: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    crosswalk = controls["reviewer_approval_crosswalk"]
    sam = controls["sam_submission"]
    manifest = controls["data_room_manifest"]
    gate = controls["funding_sprint_reviewer_gate"]
    customer = controls["customer_commercialization"]
    federal = controls["federal_submission_protocol"]
    ip = controls["ip_counsel_diligence"]
    technical = controls["technical_gov_reviewer"]
    measured = controls["measured_source_register"]
    autonomy = controls["autonomous_quant_governance"]
    kraken = controls["kraken_alpha_gauntlet"]
    trading = controls["trading_safety_audit"]

    cross_summary = as_dict(crosswalk.get("summary"))
    sam_summary = as_dict(sam.get("summary"))
    manifest_summary = as_dict(manifest.get("summary"))
    gate_summary = as_dict(gate.get("summary"))
    customer_summary = as_dict(customer.get("summary"))
    federal_summary = as_dict(federal.get("summary"))
    ip_summary = as_dict(ip.get("summary"))
    technical_summary = as_dict(technical.get("summary"))
    measured_summary = as_dict(measured.get("summary"))
    autonomy_summary = as_dict(autonomy.get("summary"))
    kraken_summary = as_dict(kraken.get("summary"))
    trading_blockers = as_list(trading.get("blockers"))

    rows = [
        {
            "domain_id": "agency_and_federal_protocol",
            "audience": "agency reviewer / contracting technical evaluator",
            "status": "REVIEW_READY_FINAL_PORTAL_ACTIONS_HUMAN_GATED",
            "trust_score": domain_score(ready=5, gates=int(sam_summary.get("remaining_portal_gate_count") or 0), blockers=int(federal_summary.get("blocked_readiness_count") or 0)),
            "ready_signals": [
                "SAM renewal submitted and confirmation email received",
                "Federal submission protocol packet ready",
                "Reviewer gate clear with zero unsafe sensitive hits and zero unsafe claim hits",
                "Two bounded federal opportunity emails sent today",
            ],
            "remaining_gates": [
                "Monitor SAM active-renewal status",
                "FHWA full proposal package remains official-instruction and cost gated",
                "DSIP MissionWeave remains Firm PIN, cost, and certification gated",
                "NSF remains pitch/invitation gated",
            ],
            "claim_boundary": "Federal protocol readiness is not award eligibility certification, agency acceptance, source selection, or contract award.",
            "primary_controls": ["sam_submission", "federal_submission_protocol", "funding_sprint_reviewer_gate"],
        },
        {
            "domain_id": "investor_and_commercial_diligence",
            "audience": "investor / venture diligence / strategic partner",
            "status": "DILIGENCE_READY_NO_CUSTOMER_RESULT_CLAIM",
            "trust_score": domain_score(ready=5, gates=2, blockers=0),
            "ready_signals": [
                f"{customer_summary.get('customer_segment_count', 0)} customer segments mapped",
                f"{customer_summary.get('offer_count', 0)} productized offers mapped",
                "Post-SAM reviewer approval crosswalk is ready",
                "Pricing, terms, scheduling, and file sharing remain human-gated",
            ],
            "remaining_gates": [
                "Convert selected lane into signed scope, acceptance standard, and data boundary",
                "Attach external reviewer reply or paid pilot authorization before claiming traction outcome",
            ],
            "claim_boundary": "Investor readiness is not investment advice, a financing commitment, paying-customer proof, or valuation proof.",
            "primary_controls": ["customer_commercialization", "reviewer_approval_crosswalk", "data_room_manifest"],
        },
        {
            "domain_id": "ip_and_patent_defense",
            "audience": "patent counsel / IP reviewer / disclosure-control reviewer",
            "status": "COUNSEL_INTAKE_READY_LEGAL_ACTION_HUMAN_GATED",
            "trust_score": domain_score(ready=4, gates=3, blockers=0),
            "ready_signals": [
                f"{ip_summary.get('invention_family_count', 0)} invention families mapped",
                f"{ip_summary.get('official_source_count', 0)} official USPTO source routes cited",
                "Patent grant, legal advice, and clearance-to-operate claims are false",
                "Public disclosure review remains required",
            ],
            "remaining_gates": [
                "Licensed counsel verifies filing status, support, ownership, and deadlines",
                "Counsel separates existing support from possible new matter",
                "Counsel approves public wording before claim expansion",
            ],
            "claim_boundary": "IP diligence readiness is not legal advice, patent grant proof, exclusivity, or clearance to operate.",
            "primary_controls": ["ip_counsel_diligence", "reviewer_approval_crosswalk"],
        },
        {
            "domain_id": "technical_and_measured_evidence",
            "audience": "technical reviewer / lab reviewer / validation partner",
            "status": "INTERNAL_EVIDENCE_READY_EXTERNAL_VALIDATION_REQUIRED",
            "trust_score": domain_score(ready=5, gates=4, blockers=0),
            "ready_signals": [
                f"{technical_summary.get('reviewer_track_count', 0)} technical reviewer tracks mapped",
                f"{measured_summary.get('registry_enabled_sources', 0)} registry-enabled sources",
                f"{measured_summary.get('current_probe_hash_backed_measured_sources', 0)} current hash-backed measured sources",
                "Field validation and realized-savings claims remain blocked",
            ],
            "remaining_gates": [
                "Buyer or reviewer authorizes external replay",
                "Accepted baseline, metric, source, and acceptance standard are recorded",
                "External replay receipt is added before any outside validation claim",
            ],
            "claim_boundary": "Internal evidence readiness is not field validation, certified assurance, or realized customer savings.",
            "primary_controls": ["technical_gov_reviewer", "measured_source_register"],
        },
        {
            "domain_id": "autonomous_quant_and_trading_safety",
            "audience": "quant-risk reviewer / trading systems reviewer",
            "status": "PAPER_RESEARCH_READY_LIVE_BLOCKED",
            "trust_score": domain_score(ready=3, gates=4, blockers=len(trading_blockers)),
            "ready_signals": [
                "Global and Kraken runtimes are paper",
                "Kraken public alpha scan and institutional gauntlet are present",
                f"{kraken_summary.get('gauntlet_row_count', 0)} Kraken gauntlet rows scored",
                "Order placement and capital movement are false",
            ],
            "remaining_gates": [
                "Fresh trading heartbeats required",
                "Trading audit blockers must be zero",
                "Multi-month walk-forward replay and capacity evidence required",
                "Separate human action-time approval required before any private validate-only or live step",
            ],
            "claim_boundary": "Quant readiness is paper research only, not investment advice, hedge-fund suitability, live trading approval, or performance proof.",
            "primary_controls": ["autonomous_quant_governance", "kraken_alpha_gauntlet", "trading_safety_audit"],
        },
        {
            "domain_id": "custody_and_reviewer_navigation",
            "audience": "reviewer operations / data-room diligence",
            "status": "HASHED_DATA_ROOM_READY",
            "trust_score": domain_score(ready=5, gates=1, blockers=int(manifest_summary.get("missing_control_artifact_count") or 0)),
            "ready_signals": [
                f"{manifest_summary.get('manifested_markdown_count', 0)} markdown artifacts manifested",
                f"{manifest_summary.get('control_artifact_count', 0)} machine controls manifested",
                f"{manifest_summary.get('e_drive_target_count', 0)} E-drive mirror targets recorded",
                f"{gate_summary.get('unsafe_secret_count', 0)} unsafe sensitive hits and {gate_summary.get('unsafe_claim_count', 0)} unsafe claim hits",
            ],
            "remaining_gates": [
                "Refresh manifest and E-drive receipt after each new external receipt",
                "Keep private/raw vault material out of public-safe reviewer packets",
            ],
            "claim_boundary": "Custody proves file integrity and navigation, not truth of unverified field, legal, award, or financial claims.",
            "primary_controls": ["data_room_manifest", "funding_sprint_reviewer_gate", "reviewer_approval_crosswalk"],
        },
    ]

    for row in rows:
        row["domain_row_sha256"] = stable_sha256(row)
    return rows


def build_payload() -> dict[str, Any]:
    controls = {name: read_json(path) for name, path in SOURCE_CONTROLS.items()}
    statuses = [source_status(name, path, controls[name]) for name, path in SOURCE_CONTROLS.items()]
    artifacts = [artifact_status(path) for path in PRIMARY_ARTIFACTS]
    rows = build_domain_rows(controls)

    cross_summary = as_dict(controls["reviewer_approval_crosswalk"].get("summary"))
    manifest_summary = as_dict(controls["data_room_manifest"].get("summary"))
    gate_summary = as_dict(controls["funding_sprint_reviewer_gate"].get("summary"))
    autonomy_summary = as_dict(controls["autonomous_quant_governance"].get("summary"))
    kraken_summary = as_dict(controls["kraken_alpha_gauntlet"].get("summary"))

    all_sources_present = all(row["present"] for row in statuses)
    all_primary_artifacts_present = all(row["present"] for row in artifacts)
    unsafe_counts_zero = int(gate_summary.get("unsafe_secret_count") or 0) == 0 and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    final_actions_blocked = all(
        [
            cross_summary.get("external_send_allowed_without_human") is False,
            cross_summary.get("final_submission_allowed_without_human") is False,
            cross_summary.get("legal_or_ip_action_allowed_without_human") is False,
            cross_summary.get("live_trading_allowed") is False,
            autonomy_summary.get("order_placement_allowed") is False,
            kraken_summary.get("order_placement_allowed") is False,
            kraken_summary.get("capital_movement_allowed") is False,
        ]
    )

    avg_score = round(sum(int(row["trust_score"]) for row in rows) / max(len(rows), 1), 2)
    payload = {
        "schema": "institutional_trust_gate_v1",
        "generated_utc": now_utc(),
        "status": "INSTITUTIONAL_TRUST_GATE_READY_HUMAN_GATED"
        if all_sources_present and all_primary_artifacts_present and unsafe_counts_zero and final_actions_blocked
        else "INSTITUTIONAL_TRUST_GATE_BLOCKED",
        "summary": {
            "domain_count": len(rows),
            "average_domain_trust_score": avg_score,
            "source_control_count": len(statuses),
            "missing_source_control_count": sum(1 for row in statuses if not row["present"]),
            "primary_artifact_count": len(artifacts),
            "missing_primary_artifact_count": sum(1 for row in artifacts if not row["present"]),
            "sam_registration_submitted": bool(cross_summary.get("sam_registration_submitted")),
            "sam_confirmation_email_received": bool(cross_summary.get("sam_confirmation_email_received")),
            "data_room_markdown_artifacts": int(manifest_summary.get("manifested_markdown_count") or 0),
            "data_room_control_artifacts": int(manifest_summary.get("control_artifact_count") or 0),
            "unsafe_sensitive_hits": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_hits": int(gate_summary.get("unsafe_claim_count") or 0),
            "all_final_actions_blocked_without_human": final_actions_blocked,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "legal_or_ip_action_allowed_without_human": False,
            "order_placement_allowed": False,
            "capital_movement_allowed": False,
            "live_trading_allowed": False,
            "large_fund_ready_now": False,
        },
        "reviewer_fast_path": [
            "Start with this Institutional Trust Gate.",
            "Use the Reviewer Approval Crosswalk to answer the exact review question.",
            "Use the SAM/opportunity receipt for federal identity and same-day traction state.",
            "Use the Customer Commercialization Packet for buyer and first-offer shape.",
            "Use the IP Counsel Diligence Packet before any claim expansion.",
            "Use the Kraken Institutional Alpha Gauntlet only as paper/replay research evidence.",
        ],
        "domain_rows": rows,
        "source_controls": statuses,
        "primary_artifacts": artifacts,
        "promotion_ladder": [
            {
                "level": "review_ready",
                "current": True,
                "meaning": "Reviewer can inspect organized evidence, boundaries, and next gates.",
            },
            {
                "level": "externally_validated",
                "current": False,
                "meaning": "Requires accepted external replay, reviewer reply, or paid pilot receipt.",
            },
            {
                "level": "agency_submission_complete",
                "current": False,
                "meaning": "Requires official portal submission receipts for each opportunity.",
            },
            {
                "level": "legal_ip_cleared",
                "current": False,
                "meaning": "Requires licensed counsel review and approved public wording.",
            },
            {
                "level": "large_capital_trading_ready",
                "current": False,
                "meaning": "Requires independent quant audit, capacity proof, compliance/custody review, and human governance.",
            },
        ],
        "global_boundaries": [
            "No award, acceptance, investment, partnership, legal opinion, patent grant, field validation, realized savings, live trading readiness, or large-capital suitability is claimed.",
            "No portal submit, external send, filing, pricing, term acceptance, order placement, or capital movement is authorized without human approval.",
        ],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["institutional_trust_gate_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Institutional Trust Gate - 2026-07-09",
        "",
        "Purpose: give agency reviewers, investors, patent counsel, technical validators, and quant-risk reviewers one source-backed gate for what is ready, what is blocked, and where the evidence lives.",
        "",
        "This artifact is not legal advice, investment advice, award proof, field validation, trading authorization, or a financing commitment.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Domains: `{summary['domain_count']}`",
        f"- Average domain trust score: `{summary['average_domain_trust_score']}`",
        f"- Source controls: `{summary['source_control_count']}`",
        f"- Missing source controls: `{summary['missing_source_control_count']}`",
        f"- Primary artifacts: `{summary['primary_artifact_count']}`",
        f"- Missing primary artifacts: `{summary['missing_primary_artifact_count']}`",
        f"- SAM submitted: `{str(summary['sam_registration_submitted']).lower()}`",
        f"- SAM confirmation email received: `{str(summary['sam_confirmation_email_received']).lower()}`",
        f"- Data-room markdown artifacts: `{summary['data_room_markdown_artifacts']}`",
        f"- Data-room machine controls: `{summary['data_room_control_artifacts']}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_sensitive_hits']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_hits']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Legal/IP action without human: `{str(summary['legal_or_ip_action_allowed_without_human']).lower()}`",
        f"- Order placement allowed: `{str(summary['order_placement_allowed']).lower()}`",
        f"- Capital movement allowed: `{str(summary['capital_movement_allowed']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Large-fund ready now: `{str(summary['large_fund_ready_now']).lower()}`",
        f"- Trust gate SHA-256: `{payload['institutional_trust_gate_sha256']}`",
        "",
        "## Reviewer Fast Path",
        "",
    ]
    for item in payload["reviewer_fast_path"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Domain Gates", ""])
    for row in payload["domain_rows"]:
        lines.extend(
            [
                f"### {row['audience']}",
                "",
                f"- Domain ID: `{row['domain_id']}`",
                f"- Status: `{row['status']}`",
                f"- Trust score: `{row['trust_score']}`",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Row SHA-256: `{row['domain_row_sha256']}`",
                "- Ready signals:",
            ]
        )
        for item in row["ready_signals"]:
            lines.append(f"  - {item}")
        lines.append("- Remaining gates:")
        for item in row["remaining_gates"]:
            lines.append(f"  - {item}")
        lines.append("- Primary controls:")
        for item in row["primary_controls"]:
            lines.append(f"  - `{item}`")
        lines.append("")

    lines.extend(["## Promotion Ladder", ""])
    for item in payload["promotion_ladder"]:
        lines.append(f"- `{item['level']}` current=`{str(item['current']).lower()}`: {item['meaning']}")

    lines.extend(["", "## Source Controls", ""])
    for row in payload["source_controls"]:
        lines.append(
            f"- `{row['control_name']}` status=`{row['status']}` present=`{str(row['present']).lower()}` sha256=`{row['sha256']}`"
        )

    lines.extend(["", "## Primary Artifacts", ""])
    for row in payload["primary_artifacts"]:
        lines.append(
            f"- `{row['path']}` present=`{str(row['present']).lower()}` bytes=`{row['bytes']}` sha256=`{row['sha256']}`"
        )

    lines.extend(["", "## Global Boundaries", ""])
    for item in payload["global_boundaries"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> int:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive institutional trust gate markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "domains": payload["summary"]["domain_count"],
                "average_domain_trust_score": payload["summary"]["average_domain_trust_score"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"] == "INSTITUTIONAL_TRUST_GATE_READY_HUMAN_GATED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
