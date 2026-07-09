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

OUT_JSON = OUT_OPS / "reviewer_approval_crosswalk_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "reviewer_approval_crosswalk.json"
OUT_MD = SPRINT_DIR / "REVIEWER_APPROVAL_CROSSWALK_2026-07-09.md"

SOURCE_CONTROLS = {
    "sam_submission": OUT_OPS / "sam_submission_and_today_opportunity_push_latest.json",
    "data_room_manifest": OUT_OPS / "data_room_manifest_latest.json",
    "funding_sprint_reviewer_gate": OUT_OPS / "funding_sprint_reviewer_gate_latest.json",
    "reviewer_decision_brief": OUT_OPS / "reviewer_decision_brief_latest.json",
    "customer_commercialization": OUT_OPS / "customer_commercialization_packet_latest.json",
    "ip_counsel_diligence": OUT_OPS / "ip_counsel_diligence_packet_latest.json",
    "technical_gov_reviewer": OUT_OPS / "technical_gov_reviewer_approval_stack_latest.json",
    "measured_source_register": OUT_OPS / "measured_source_evidence_register_latest.json",
    "autonomous_quant_governance": OUT_OPS / "autonomous_quant_governance_packet_latest.json",
    "federal_submission_protocol": OUT_OPS / "federal_submission_protocol_packet_latest.json",
}

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


def control_status(name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_name": name,
        "path": rel(path),
        "present": path.exists(),
        "status": str(payload.get("status") or ""),
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


def build_approval_rows(controls: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    sam = controls["sam_submission"]
    manifest = controls["data_room_manifest"]
    gate = controls["funding_sprint_reviewer_gate"]
    decision = controls["reviewer_decision_brief"]
    customer = controls["customer_commercialization"]
    ip = controls["ip_counsel_diligence"]
    technical = controls["technical_gov_reviewer"]
    measured = controls["measured_source_register"]
    autonomy = controls["autonomous_quant_governance"]
    federal = controls["federal_submission_protocol"]

    tech_metrics = as_dict(as_dict(technical.get("core_truth")).get("metrics"))
    manifest_summary = as_dict(manifest.get("summary"))
    gate_summary = as_dict(gate.get("summary"))
    customer_cards = as_list(customer.get("customer_cards"))
    remaining_gates = as_list(sam.get("remaining_gates"))
    measured_summary = as_dict(measured.get("summary"))
    sector_counts = as_dict(measured.get("sector_counts"))
    current_probe = as_dict(sector_counts.get("current_probe"))

    rows = [
        {
            "approval_question": "Is the federal identity and eligibility path real enough to continue review?",
            "decision_id": "federal_identity_and_sam",
            "answer": "Yes for preparation and reviewer routing: SAM renewal reached submitted-confirmation state and a SAM confirmation email was received. Final active status still needs monitoring.",
            "evidence_strength": "official_portal_confirmation_plus_email_receipt",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/SAM_SUBMISSION_AND_TODAY_OPPORTUNITY_PUSH_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
            ],
            "remaining_gate": "Monitor SAM status until active renewal is reflected; continue to keep portal certifications human-gated.",
            "claim_boundary": "Submission confirmation is not an award, not source selection, and not proof of final active renewal acceptance.",
        },
        {
            "approval_question": "What exactly is LumenCore asking reviewers to fund or route?",
            "decision_id": "fundable_product_shape",
            "answer": "A proof-to-pilot evidence operating system: source provenance, baseline-vs-candidate replay, reviewer packets, human authority gates, and hash-backed custody for complex AI/quant/infrastructure decisions.",
            "evidence_strength": "business_packet_plus_data_room_manifest",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
            ],
            "remaining_gate": "Translate each funded route into a named sprint, acceptance standard, data boundary, and human-signed scope.",
            "claim_boundary": "No customer result, paid pilot, agency use, or investor decision is implied unless separately evidenced.",
        },
        {
            "approval_question": "Is there technical substance behind the story?",
            "decision_id": "technical_validation_spine",
            "answer": (
                "Yes at the internal evidence level: the current stack records measured sources, replay receipts, "
                "holdout metrics, and data-room controls that make outside validation easier."
            ),
            "evidence_strength": "internal_replay_and_measured_source_evidence",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md",
            ],
            "metrics": {
                "kuramoto_holdouts": tech_metrics.get("kuramoto_holdout_count", 0),
                "kuramoto_wins_vs_kalman": tech_metrics.get("kuramoto_wins_vs_kalman", 0),
                "estimated_replay_rows": tech_metrics.get("kuramoto_estimated_rows_replayed", 0),
                "data_room_markdown_artifacts": manifest_summary.get("manifested_markdown_count", 0),
                "data_room_control_artifacts": manifest_summary.get("control_artifact_count", 0),
                "current_probe_sector_count": len(current_probe),
                "measured_register_status": measured.get("status", "MEASURED_SOURCE_REGISTER_PRESENT"),
                "measured_summary": measured_summary,
            },
            "remaining_gate": "External reviewers must run or accept a field replay before the stack may claim external validation or economic impact.",
            "claim_boundary": "Internal replay evidence is not field validation, realized savings, certified assurance, or deployment acceptance.",
        },
        {
            "approval_question": "Is the IP universe organized without overclaiming?",
            "decision_id": "ip_and_claim_defense",
            "answer": "Yes for counsel intake: invention families, hold-back rules, USPTO source references, and public wording rules are separated from legal conclusions.",
            "evidence_strength": "counsel_ready_intake_not_legal_opinion",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
                "grant_submissions/PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md",
            ],
            "metrics": {
                "invention_families": as_dict(ip.get("summary")).get("invention_family_count", 0),
                "official_uspto_sources": as_dict(ip.get("summary")).get("official_source_count", 0),
                "licensed_counsel_required": as_dict(ip.get("summary")).get("licensed_counsel_required", True),
            },
            "remaining_gate": "Licensed counsel must confirm filing status, support, disclosure timing, ownership, and exact public wording.",
            "claim_boundary": "This is not legal advice, patent grant proof, exclusivity, or clearance to operate.",
        },
        {
            "approval_question": "Can a government or investor reviewer trust the control posture?",
            "decision_id": "governance_and_safety",
            "answer": "Yes for review: sensitive-data scans, claim boundaries, human authority controls, and no-live-execution rules are explicit and machine-readable.",
            "evidence_strength": "machine_gate_and_human_authority_controls",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
            ],
            "metrics": {
                "unsafe_sensitive_hits": gate_summary.get("unsafe_secret_count", 0),
                "unsafe_claim_hits": gate_summary.get("unsafe_claim_count", 0),
                "external_send_allowed_without_human": gate_summary.get("autonomous_external_action_allowed", False),
                "live_trading_allowed": gate_summary.get("live_trading_allowed", False),
                "autonomous_modes": len(as_list(autonomy.get("allowed_modes"))),
            },
            "remaining_gate": "Any external send, portal submit, filing, pricing approval, or capital-impacting action remains human controlled.",
            "claim_boundary": "Governance readiness is not cybersecurity certification, ATO, CMMC certification, or operating authority.",
        },
        {
            "approval_question": "Where is the closest traction after SAM submission?",
            "decision_id": "near_term_funding_traction",
            "answer": "Air Force AAC was sent as an RFI response, FHWA was sent a bounded capability/instruction note, and the remaining highest-leverage gates are FHWA full proposal, DSIP MissionWeave, and NSF pitch/invitation path.",
            "evidence_strength": "sent_receipts_plus_deadline_gate_map",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/LUMENCORE_AAC_RFI_RESPONSE_SAF-AQ-RFI-26-0001_2026-07-09.pdf",
                "grant_submissions/funding_sprint_20260709/LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf",
                "grant_submissions/funding_sprint_20260709/CLOSEST_QUALIFIED_GRANTS_AND_CONTRACTS_2026-07-09.md",
            ],
            "metrics": {
                "same_day_federal_email_pushes": as_dict(sam.get("summary")).get("same_day_federal_email_push_count", 0),
                "remaining_portal_gates": len(remaining_gates),
                "decision_lanes": as_dict(decision.get("summary")).get("lane_count", 0),
                "customer_segments": len(customer_cards),
            },
            "remaining_gate": "Build compliant final packages only after official instructions, portal authority, cost/pricing, and final preview are reviewed.",
            "claim_boundary": "RFI and capability-note sends do not prove award, acceptance, selection, or customer savings.",
        },
        {
            "approval_question": "Can a reviewer verify custody without digging through the whole machine?",
            "decision_id": "data_room_and_mirror_custody",
            "answer": "Yes: the manifest hashes markdown and machine controls, and the E-drive proof-vault receipt records additive copy custody.",
            "evidence_strength": "hash_manifest_and_e_drive_receipt",
            "primary_artifacts": [
                "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/E_DRIVE_SYNC_RECEIPT_2026-07-09.md",
                "grant_submissions/funding_sprint_20260709/E_DRIVE_PROTOCOL_LAYER_SYNC_RECEIPT_2026-07-09.md",
            ],
            "metrics": {
                "manifested_markdown_count": manifest_summary.get("manifested_markdown_count", 0),
                "control_artifact_count": manifest_summary.get("control_artifact_count", 0),
                "e_drive_target_count": manifest_summary.get("e_drive_target_count", 0),
                "missing_control_artifact_count": manifest_summary.get("missing_control_artifact_count", 0),
            },
            "remaining_gate": "Refresh hashes after each new packet, sent receipt, or portal confirmation.",
            "claim_boundary": "Custody proves file integrity and availability, not truth of unverified business or field claims.",
        },
    ]

    for row in rows:
        row["artifact_status"] = [artifact_status(path) for path in row["primary_artifacts"]]
        row["all_primary_artifacts_present"] = all(item["present"] for item in row["artifact_status"])
        row["approval_row_sha256"] = stable_sha256(row)
    return rows


def build_payload() -> dict[str, Any]:
    controls = {name: read_json(path) for name, path in SOURCE_CONTROLS.items()}
    source_status = [
        control_status(name, path, controls[name])
        for name, path in SOURCE_CONTROLS.items()
    ]
    rows = build_approval_rows(controls)
    all_sources_present = all(row["present"] for row in source_status)
    all_artifacts_present = all(row["all_primary_artifacts_present"] for row in rows)
    sam_summary = as_dict(controls["sam_submission"].get("summary"))
    gate_summary = as_dict(controls["funding_sprint_reviewer_gate"].get("summary"))
    manifest_summary = as_dict(controls["data_room_manifest"].get("summary"))

    payload = {
        "schema": "reviewer_approval_crosswalk_v1",
        "generated_utc": now_utc(),
        "status": "REVIEWER_APPROVAL_CROSSWALK_READY_POST_SAM"
        if all_sources_present and all_artifacts_present
        else "REVIEWER_APPROVAL_CROSSWALK_BLOCKED",
        "summary": {
            "approval_question_count": len(rows),
            "source_control_count": len(source_status),
            "missing_source_control_count": sum(1 for row in source_status if not row["present"]),
            "all_primary_artifacts_present": all_artifacts_present,
            "sam_registration_submitted": bool(sam_summary.get("sam_registration_submitted")),
            "sam_confirmation_email_received": bool(sam_summary.get("sam_confirmation_email_received")),
            "same_day_federal_email_push_count": int(sam_summary.get("same_day_federal_email_push_count") or 0),
            "remaining_portal_gate_count": int(sam_summary.get("remaining_portal_gate_count") or 0),
            "data_room_markdown_artifacts": int(manifest_summary.get("manifested_markdown_count") or 0),
            "data_room_control_artifacts": int(manifest_summary.get("control_artifact_count") or 0),
            "unsafe_sensitive_hits": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_hits": int(gate_summary.get("unsafe_claim_count") or 0),
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "legal_or_ip_action_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "controlling_update": {
            "plain_english": (
                "The newest controlling state is post-SAM-submission: SAM renewal was submitted and confirmed by email. "
                "Older packets that describe SAM as a pending renewal blocker should be read as pre-submission context."
            ),
            "reviewer_use": "Start with this crosswalk, then open only the primary artifacts for the question being reviewed.",
        },
        "approval_rows": rows,
        "source_controls": source_status,
        "reviewer_fast_path": [
            "Open the SAM/opportunity receipt to verify the federal identity and same-day traction state.",
            "Open the customer packet to understand who pays and what the first funded sprint buys.",
            "Open the technical/government packet and measured-source register to inspect evidence depth.",
            "Open the IP counsel packet to separate invention posture from legal conclusions.",
            "Open the reviewer gate and authority matrix before any external action.",
        ],
        "global_boundaries": [
            "No award, selection, paid pilot, investor decision, legal conclusion, deployment acceptance, external validation, realized economic impact, or operating authority is claimed.",
            "No portal submit, certification, filing, pricing, term acceptance, external send, trading, or capital movement is allowed without human approval.",
        ],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["approval_crosswalk_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reviewer Approval Crosswalk - 2026-07-09",
        "",
        "Purpose: make LumenCore easier to review after the SAM submission by mapping each funding, agency, investor, IP, and safety question to exact proof artifacts and remaining gates.",
        "",
        "This crosswalk is a navigation and claim-control layer. It does not authorize external sends, portal submissions, filings, legal conclusions, pricing, trading, or capital movement.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Approval questions: `{summary['approval_question_count']}`",
        f"- Source controls: `{summary['source_control_count']}`",
        f"- Missing source controls: `{summary['missing_source_control_count']}`",
        f"- All primary artifacts present: `{str(summary['all_primary_artifacts_present']).lower()}`",
        f"- SAM submitted: `{str(summary['sam_registration_submitted']).lower()}`",
        f"- SAM confirmation email received: `{str(summary['sam_confirmation_email_received']).lower()}`",
        f"- Same-day federal email pushes: `{summary['same_day_federal_email_push_count']}`",
        f"- Remaining portal gates: `{summary['remaining_portal_gate_count']}`",
        f"- Data-room markdown artifacts: `{summary['data_room_markdown_artifacts']}`",
        f"- Data-room control artifacts: `{summary['data_room_control_artifacts']}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_sensitive_hits']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_hits']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Legal/IP action without human: `{str(summary['legal_or_ip_action_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Crosswalk SHA-256: `{payload['approval_crosswalk_sha256']}`",
        "",
        "## Controlling Update",
        "",
        payload["controlling_update"]["plain_english"],
        "",
        payload["controlling_update"]["reviewer_use"],
        "",
        "## Reviewer Fast Path",
        "",
    ]
    for item in payload["reviewer_fast_path"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Approval Questions", ""])
    for row in payload["approval_rows"]:
        lines.extend(
            [
                f"### {row['approval_question']}",
                "",
                f"- Decision ID: `{row['decision_id']}`",
                f"- Answer: {row['answer']}",
                f"- Evidence strength: `{row['evidence_strength']}`",
                f"- Remaining gate: {row['remaining_gate']}",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- All primary artifacts present: `{str(row['all_primary_artifacts_present']).lower()}`",
                f"- Row SHA-256: `{row['approval_row_sha256']}`",
                "- Primary artifacts:",
            ]
        )
        for artifact in row["artifact_status"]:
            lines.append(
                f"  - `{artifact['path']}` present=`{str(artifact['present']).lower()}` sha256=`{artifact['sha256']}`"
            )
        metrics = row.get("metrics")
        if isinstance(metrics, dict) and metrics:
            lines.append("- Metrics:")
            for key, value in metrics.items():
                lines.append(f"  - `{key}`: `{value}`")
        lines.append("")

    lines.extend(["## Source Controls", ""])
    for source in payload["source_controls"]:
        lines.append(
            f"- `{source['control_name']}` status=`{source['status']}` present=`{str(source['present']).lower()}` sha256=`{source['sha256']}`"
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
        raise SystemExit(f"Refusing to write sensitive public approval crosswalk markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "approval_questions": payload["summary"]["approval_question_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"].endswith("POST_SAM") else 1


if __name__ == "__main__":
    raise SystemExit(main())
