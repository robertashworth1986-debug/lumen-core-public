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

TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
FOLLOWUP_JSON = OUT_OPS / "traction_followup_packet_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
DATA_ROOM_JSON = OUT_OPS / "data_room_manifest_latest.json"
MEASURED_SOURCE_JSON = OUT_OPS / "measured_source_evidence_register_latest.json"
FEDERAL_PROTOCOL_JSON = OUT_OPS / "federal_submission_protocol_packet_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
IP_JSON = OUT_OPS / "ip_counsel_diligence_packet_latest.json"
AUTONOMY_JSON = OUT_OPS / "autonomous_quant_governance_packet_latest.json"

OUT_JSON = OUT_OPS / "evtit_technical_sprint_scope_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "evtit_technical_sprint_scope_packet.json"
OUT_MD = SPRINT_DIR / "EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET_2026-07-09.md"

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
    "@evtit",
    "@blackdog",
]

WORKSTREAMS = [
    {
        "id": "proof_portal_front_door",
        "title": "Proof portal front door",
        "problem": "Reviewers need one clean path from thesis to artifacts without reading the whole repository.",
        "deliverable": "A reviewer-facing portal surface with proof-card navigation, source register, and data-room links.",
        "acceptance_check": "A reviewer can identify thesis, source register, claim boundaries, and next validation gate in under five minutes.",
        "evidence_output": "public-safe screenshot, route map, hash-linked front-door artifact list",
    },
    {
        "id": "replay_runner_manifest",
        "title": "Replay runner and manifest",
        "problem": "Evidence needs a repeatable path from source snapshot to baseline comparison to reviewer receipt.",
        "deliverable": "A replay runner shell that records source, baseline, candidate, metric, run config, and SHA-256 receipt.",
        "acceptance_check": "A dry-run receipt can be generated without external send, credentials, or capital movement.",
        "evidence_output": "run manifest JSON, markdown receipt, failure/negative-result slot",
    },
    {
        "id": "measured_source_register_ui",
        "title": "Measured-source register UI",
        "problem": "The source inventory must distinguish registry continuity from current hash-backed probe rows.",
        "deliverable": "A concise UI/table for registry sources, current measured rows, hash status, and refresh gaps.",
        "acceptance_check": "The UI visibly separates registry-measured rows from current hash-backed measured rows.",
        "evidence_output": "source-register component, reconciliation note, no-claim banner",
    },
    {
        "id": "pilot_onboarding_path",
        "title": "Pilot onboarding path",
        "problem": "A serious partner needs to know exactly how a validation study would start without accepting terms on the call.",
        "deliverable": "A gated onboarding flow: problem, data owner, baseline, metric, holdout window, scope, economics review.",
        "acceptance_check": "The flow blocks until human approves data boundary, economics, legal terms, and final share.",
        "evidence_output": "pilot intake checklist, authority stop points, acceptance-standard template",
    },
    {
        "id": "api_reliability_cost_controls",
        "title": "API reliability and cost controls",
        "problem": "Proof generation must be reliable enough for demos and bounded enough for budget review.",
        "deliverable": "Retry, timeout, cost-limit, source-refresh, and status-receipt controls for proof-stack jobs.",
        "acceptance_check": "Each job records success/failure status, cost boundary, and whether human action is required.",
        "evidence_output": "job receipt schema, status dashboard row, cost-control policy",
    },
    {
        "id": "grant_investor_packet_automation",
        "title": "Grant and investor packet automation",
        "problem": "Funding materials need to stay synchronized with source, claim, IP, and agency-readiness gates.",
        "deliverable": "A packet refresh workflow that rebuilds public-safe reviewer artifacts and machine controls.",
        "acceptance_check": "A refresh produces manifest counts, gate status, E-drive receipt, and blocked-final-action flags.",
        "evidence_output": "packet build log, data-room manifest, reviewer gate, E-drive hash receipt",
    },
]

MILESTONES = [
    {
        "day_range": "Days 1-3",
        "name": "Scope lock",
        "output": "Choose workstreams, owner roles, artifacts, non-goals, and approval boundaries.",
        "human_gate": "Robert approves any shared scope, schedule, economics, or contributor access.",
    },
    {
        "day_range": "Days 4-10",
        "name": "Front-door prototype",
        "output": "Portal/navigation prototype and measured-source register view.",
        "human_gate": "No private file, account, portal, or credential material is exposed.",
    },
    {
        "day_range": "Days 11-18",
        "name": "Replay receipt skeleton",
        "output": "Runner receipt schema, baseline/candidate fields, and no-claim result template.",
        "human_gate": "No external data owner result is represented without explicit owner acceptance.",
    },
    {
        "day_range": "Days 19-24",
        "name": "Pilot intake and authority gates",
        "output": "Pilot intake checklist, approval stops, and reviewer-safe data-room handoff.",
        "human_gate": "Terms, economics, file sharing, and schedule remain human-approved only.",
    },
    {
        "day_range": "Days 25-30",
        "name": "Reviewer handoff",
        "output": "Final sprint packet, demo script, hash manifest, and next validation ask.",
        "human_gate": "Human decides whether to send, schedule, accept terms, or share the packet.",
    },
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def find_evtit_lane(traction: dict[str, Any]) -> dict[str, Any]:
    lanes = traction.get("lanes", [])
    if isinstance(lanes, list):
        for lane in lanes:
            if isinstance(lane, dict) and lane.get("lane_id") == "evtit_blackdog_inkind":
                return lane
    return {}


def build_payload() -> dict[str, Any]:
    traction = read_json(TRACTION_JSON)
    followup = read_json(FOLLOWUP_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    data_room = read_json(DATA_ROOM_JSON)
    measured = read_json(MEASURED_SOURCE_JSON)
    federal = read_json(FEDERAL_PROTOCOL_JSON)
    authority = read_json(AUTHORITY_JSON)
    ip = read_json(IP_JSON)
    autonomy = read_json(AUTONOMY_JSON)

    gate_summary = gate.get("summary", {}) if isinstance(gate.get("summary"), dict) else {}
    data_summary = data_room.get("summary", {}) if isinstance(data_room.get("summary"), dict) else {}
    measured_summary = measured.get("summary", {}) if isinstance(measured.get("summary"), dict) else {}
    authority_summary = authority.get("summary", {}) if isinstance(authority.get("summary"), dict) else {}

    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate_summary.get("unsafe_secret_count") or 0) == 0 and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human"))
    lane = find_evtit_lane(traction)
    evidence_paths = [
        OUT_JSON,
        TRACTION_JSON,
        FOLLOWUP_JSON,
        REVIEWER_GATE_JSON,
        DATA_ROOM_JSON,
        MEASURED_SOURCE_JSON,
        FEDERAL_PROTOCOL_JSON,
        AUTHORITY_JSON,
        IP_JSON,
        AUTONOMY_JSON,
    ]

    payload = {
        "generated_utc": now_utc(),
        "schema": "evtit_technical_sprint_scope_packet_v1",
        "status": "EVTIT_TECHNICAL_SPRINT_SCOPE_READY_HUMAN_TERMS_REQUIRED"
        if gate_clear and final_actions_blocked
        else "EVTIT_TECHNICAL_SPRINT_SCOPE_BLOCKED",
        "lane": {
            "lane_id": "evtit_blackdog_inkind",
            "name": lane.get("name", "EVTit / Black Dog in-kind engineering fund"),
            "status": lane.get("status", "MEETING_OR_TECH_REVIEW_PENDING"),
            "fit_score": int(lane.get("fit_score") or 92),
            "claim_boundary": lane.get(
                "claim_boundary",
                "Meeting and application evidence only; no investment, services award, or partnership has been accepted.",
            ),
        },
        "summary": {
            "workstream_count": len(WORKSTREAMS),
            "milestone_count": len(MILESTONES),
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "data_room_status": data_room.get("status", ""),
            "data_room_markdown_count": int(data_summary.get("manifested_markdown_count") or 0),
            "data_room_control_count": int(data_summary.get("control_artifact_count") or 0),
            "registry_enabled_sources": int(measured_summary.get("registry_enabled_sources") or 0),
            "registry_measured_sources": int(measured_summary.get("registry_measured_sources") or 0),
            "current_probe_measured_sources": int(measured_summary.get("current_probe_measured_sources") or 0),
            "measured_source_reconciliation_required": bool(measured_summary.get("reconciliation_required")),
            "followup_status": followup.get("status", ""),
            "federal_protocol_status": federal.get("status", ""),
            "ip_packet_status": ip.get("status", ""),
            "autonomy_packet_status": autonomy.get("status", ""),
            "human_terms_required": True,
            "external_send_allowed_without_human": False,
            "schedule_allowed_without_human": False,
            "share_private_files_allowed_without_human": False,
            "equity_or_services_terms_allowed_without_human": False,
            "partnership_claimed": False,
            "investment_claimed": False,
            "services_award_claimed": False,
            "customer_outcome_value_claimed": False,
            "production_deployment_claimed": False,
        },
        "positioning": {
            "one_sentence": (
                "A 30-day technical sprint to convert LumenCore's proof-to-pilot stack into a cleaner reviewer portal, "
                "repeatable evidence receipts, measured-source visibility, and pilot-ready intake gates."
            ),
            "decision_question": "Can EVTit help productize the evidence system so serious reviewers can inspect it faster?",
            "best_next_meeting": "30-minute technical fit call with named engineering owners and a workstream selection decision.",
        },
        "workstreams": WORKSTREAMS,
        "milestones": MILESTONES,
        "human_gate": {
            "scope_share_allowed_without_human": False,
            "email_send_allowed_without_human": False,
            "meeting_schedule_allowed_without_human": False,
            "terms_acceptance_allowed_without_human": False,
            "private_file_share_allowed_without_human": False,
            "rule": "This packet is a scope-preparation artifact only. Robert approves any external send, meeting schedule, access grant, economics, equity/service terms, or file sharing.",
        },
        "evidence_status": [artifact_status(path) for path in evidence_paths if path != OUT_JSON or path.exists()],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["evtit_sprint_scope_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lane = payload["lane"]
    lines = [
        "# EVTit Technical Sprint Scope Packet - 2026-07-09",
        "",
        "Purpose: give Terry and the EVTit technical team a concrete 30-day sprint shape without accepting terms, sharing private material, or claiming a partnership.",
        "",
        "This packet is preparation-only. It does not send email, schedule a meeting, accept equity or services terms, grant access, share files, or authorize final external action.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lane ID: `{lane['lane_id']}`",
        f"- Lane status: `{lane['status']}`",
        f"- Fit score: `{lane['fit_score']}`",
        f"- Workstreams: `{summary['workstream_count']}`",
        f"- Milestones: `{summary['milestone_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Registry enabled sources: `{summary['registry_enabled_sources']}`",
        f"- Registry measured sources: `{summary['registry_measured_sources']}`",
        f"- Current probe measured sources: `{summary['current_probe_measured_sources']}`",
        f"- Measured-source reconciliation required: `{str(summary['measured_source_reconciliation_required']).lower()}`",
        f"- Human terms required: `{str(summary['human_terms_required']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Schedule without human: `{str(summary['schedule_allowed_without_human']).lower()}`",
        f"- Share private files without human: `{str(summary['share_private_files_allowed_without_human']).lower()}`",
        f"- Equity or services terms without human: `{str(summary['equity_or_services_terms_allowed_without_human']).lower()}`",
        f"- Partnership claimed: `{str(summary['partnership_claimed']).lower()}`",
        f"- Investment claimed: `{str(summary['investment_claimed']).lower()}`",
        f"- Services award claimed: `{str(summary['services_award_claimed']).lower()}`",
        f"- Customer outcome value claimed: `{str(summary['customer_outcome_value_claimed']).lower()}`",
        f"- Production deployment claimed: `{str(summary['production_deployment_claimed']).lower()}`",
        f"- Packet SHA-256: `{payload['evtit_sprint_scope_sha256']}`",
        "",
        "## Positioning",
        "",
        f"- One sentence: {payload['positioning']['one_sentence']}",
        f"- Decision question: {payload['positioning']['decision_question']}",
        f"- Best next meeting: {payload['positioning']['best_next_meeting']}",
        "",
        "## Claim Boundary",
        "",
        lane["claim_boundary"],
        "",
        "## Workstreams",
        "",
    ]
    for stream in payload["workstreams"]:
        lines.extend(
            [
                f"### {stream['title']}",
                "",
                f"- Workstream ID: `{stream['id']}`",
                f"- Problem: {stream['problem']}",
                f"- Deliverable: {stream['deliverable']}",
                f"- Acceptance check: {stream['acceptance_check']}",
                f"- Evidence output: {stream['evidence_output']}",
                "",
            ]
        )

    lines.extend(["## 30-Day Milestones", ""])
    for milestone in payload["milestones"]:
        lines.extend(
            [
                f"### {milestone['day_range']} - {milestone['name']}",
                "",
                f"- Output: {milestone['output']}",
                f"- Human gate: {milestone['human_gate']}",
                "",
            ]
        )

    lines.extend(["## Human Gate", ""])
    for key, value in payload["human_gate"].items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> int:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public sprint-scope markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "workstreams": payload["summary"]["workstream_count"],
                "milestones": payload["summary"]["milestone_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"].endswith("HUMAN_TERMS_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
