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

OUT_JSON = OUT_OPS / "data_room_manifest_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "data_room_manifest.json"
OUT_MD = SPRINT_DIR / "DATA_ROOM_MANIFEST_2026-07-09.md"

CONTROL_NAMES = [
    "funding_sprint_reviewer_gate",
    "traction_opportunity_intake_ledger",
    "reviewer_concierge_packet",
    "human_action_docket",
    "submission_authority_matrix",
    "reviewer_decision_brief",
    "reviewer_diligence_qa_matrix",
    "linkedin_universe_profile_packet",
]

FRONT_DOOR_FILES = {
    "REVIEWER_DECISION_BRIEF_2026-07-09.md",
    "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
    "LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
    "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
    "HUMAN_ACTION_DOCKET_2026-07-09.md",
    "REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
    "TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
    "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
}

LANE_FILES = {
    "AIR_FORCE_AAC_RFI_CAPABILITY_STATEMENT_2026-07-09.md",
    "DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md",
    "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
    "NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
    "NSF_PROJECT_PITCH_DRAFT_2026-07-09.md",
    "NUCLEAR_LICENSING_EVIDENCE_PARTNER_ONE_PAGER_2026-07-09.md",
    "NUCLEAR_OPPORTUNITY_TIMING_2026-07-09.md",
    "NUCLEAR_PARTNER_OUTREACH_DRAFTS_2026-07-09.md",
}

BOUNDARY_FILES = {
    "AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
    "AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
    "CURRENT_LANE_SYNC_STATUS_2026-07-09.md",
    "FUNDING_ACTION_MATRIX_2026-07-09.md",
    "IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
    "PROOF_STACK_EDGE_INDEX_2026-07-09.md",
    "SBIR_PHASE1_TRIAGE_2026-07-09.md",
}

SYNC_RECEIPT_FILES = {
    "E_DRIVE_PROTOCOL_LAYER_SYNC_RECEIPT_2026-07-09.md",
    "E_DRIVE_SYNC_RECEIPT_2026-07-09.md",
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

E_DRIVE_TARGETS = [
    "E:\\LumaProofVault\\LUMA_FUNDING_SPRINT_20260709_20260709T030617Z",
    "E:\\LumenCoreSync\\funding_sprint_20260709",
    "E:\\INSTITUTIONAL_STACK_V2\\grant_submissions\\funding_sprint_20260709",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_category(name: str) -> str:
    if name in FRONT_DOOR_FILES:
        return "front_door_control"
    if name in LANE_FILES:
        return "lane_package"
    if name in BOUNDARY_FILES:
        return "claim_protocol_boundary"
    if name in SYNC_RECEIPT_FILES:
        return "sync_receipt"
    return "supporting_markdown"


def markdown_artifacts() -> list[dict[str, Any]]:
    rows = []
    for path in sorted(SPRINT_DIR.glob("*.md")):
        if not path.is_file() or path.name == OUT_MD.name:
            continue
        rows.append(
            {
                "name": path.name,
                "path": rel(path),
                "category": artifact_category(path.name),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
                "classification": "public_safe_markdown_review_required",
            }
        )
    return rows


def control_artifacts() -> list[dict[str, Any]]:
    rows = []
    for name in CONTROL_NAMES:
        out_path = OUT_OPS / f"{name}_latest.json"
        dashboard_path = DASHBOARD_DATA / f"{name}.json"
        for role, path in [("machine_control_json", out_path), ("dashboard_control_json", dashboard_path)]:
            rows.append(
                {
                    "name": path.name,
                    "path": rel(path),
                    "control_name": name,
                    "role": role,
                    "present": path.exists(),
                    "bytes": path.stat().st_size if path.exists() else 0,
                    "sha256": sha256_file(path) if path.exists() else "",
                    "classification": "machine_readable_proof_receipt",
                }
            )
    return rows


def build_payload() -> dict[str, Any]:
    controls = {name: read_json(OUT_OPS / f"{name}_latest.json") for name in CONTROL_NAMES}
    markdown = markdown_artifacts()
    control_rows = control_artifacts()
    missing_controls = [row for row in control_rows if not row["present"]]
    category_counts: dict[str, int] = {}
    for row in markdown:
        category_counts[row["category"]] = category_counts.get(row["category"], 0) + 1

    all_control_statuses = {
        name: controls[name].get("status", "")
        for name in CONTROL_NAMES
    }
    gate = controls["funding_sprint_reviewer_gate"]
    decision = controls["reviewer_decision_brief"]
    authority = controls["submission_authority_matrix"]

    all_final_actions_blocked = bool(decision["summary"]["all_final_actions_blocked_without_human"]) and bool(
        authority["summary"]["all_final_actions_blocked_without_human"]
    )
    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate["summary"]["unsafe_secret_count"]) == 0 and int(gate["summary"]["unsafe_claim_count"]) == 0
    all_controls_present = not missing_controls

    manifest_seed = {
        "markdown": [{k: row[k] for k in ("path", "sha256", "bytes", "category")} for row in markdown],
        "controls": [{k: row[k] for k in ("path", "sha256", "bytes", "control_name", "role")} for row in control_rows],
    }

    payload = {
        "generated_utc": now_utc(),
        "schema": "data_room_manifest_v1",
        "status": "DATA_ROOM_MANIFEST_READY" if gate_clear and all_controls_present and all_final_actions_blocked else "DATA_ROOM_MANIFEST_BLOCKED",
        "summary": {
            "manifested_markdown_count": len(markdown),
            "control_artifact_count": len(control_rows),
            "missing_control_artifact_count": len(missing_controls),
            "category_counts": dict(sorted(category_counts.items())),
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
            "decision_status": decision.get("status", ""),
            "decision_lane_count": int(decision["summary"]["lane_count"]),
            "decision_top_ready_lane_count": int(decision["summary"]["top_ready_lane_count"]),
            "decision_urgent_lane_count": int(decision["summary"]["urgent_lane_count"]),
            "authority_status": authority.get("status", ""),
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "live_trading_allowed": False,
            "e_drive_target_count": len(E_DRIVE_TARGETS),
        },
        "front_door_order": [
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        ],
        "control_statuses": all_control_statuses,
        "markdown_artifacts": markdown,
        "control_artifacts": control_rows,
        "e_drive_targets": E_DRIVE_TARGETS,
        "sharing_rules": {
            "public_safe_by_default": True,
            "exclude_meeting_access_details": True,
            "exclude_credentials": True,
            "exclude_unreviewed_archives": True,
            "human_approval_required_before_external_send": True,
        },
        "manifest_seed_sha256": hashlib.sha256(json.dumps(manifest_seed, sort_keys=True).encode("utf-8")).hexdigest(),
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["data_room_manifest_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Data Room Manifest - 2026-07-09",
        "",
        "Purpose: provide a hash-backed map of the LumenCore reviewer data room, machine receipts, and E-drive mirror targets.",
        "",
        "This manifest is a navigation and custody artifact. It does not authorize external sends, submissions, filings, certifications, term acceptance, trading, or capital movement.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Manifested Markdown artifacts: `{summary['manifested_markdown_count']}`",
        f"- Control artifacts: `{summary['control_artifact_count']}`",
        f"- Missing control artifacts: `{summary['missing_control_artifact_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Decision status: `{summary['decision_status']}`",
        f"- Decision lanes: `{summary['decision_lane_count']}`",
        f"- Top-ready lanes: `{summary['decision_top_ready_lane_count']}`",
        f"- Urgent lanes: `{summary['decision_urgent_lane_count']}`",
        f"- Authority status: `{summary['authority_status']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Manifest seed SHA-256: `{payload['manifest_seed_sha256']}`",
        f"- Data-room manifest SHA-256: `{payload['data_room_manifest_sha256']}`",
        "",
        "## Front Door Order",
        "",
    ]
    for path in payload["front_door_order"]:
        lines.append(f"- `{path}`")
    lines.extend(["", "## Category Counts", ""])
    for key, value in summary["category_counts"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Control Statuses", ""])
    for key, value in payload["control_statuses"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Markdown Artifacts", ""])
    for row in payload["markdown_artifacts"]:
        lines.append(f"- `{row['category']}` `{row['path']}` sha256=`{row['sha256']}` bytes=`{row['bytes']}`")
    lines.extend(["", "## Machine Control Artifacts", ""])
    for row in payload["control_artifacts"]:
        state = "present" if row["present"] else "missing"
        lines.append(f"- `{state}` `{row['path']}` control=`{row['control_name']}` role=`{row['role']}` sha256=`{row['sha256']}`")
    lines.extend(["", "## E-Drive Mirror Targets", ""])
    for target in payload["e_drive_targets"]:
        lines.append(f"- `{target}`")
    lines.extend(["", "## Sharing Rules", ""])
    for key, value in payload["sharing_rules"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public data-room markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "markdown_artifacts": payload["summary"]["manifested_markdown_count"],
                "control_artifacts": payload["summary"]["control_artifact_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
