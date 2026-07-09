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
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
DATA_ROOM_JSON = OUT_OPS / "data_room_manifest_latest.json"

OUT_JSON = OUT_OPS / "traction_followup_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "traction_followup_packet.json"
OUT_MD = SPRINT_DIR / "EVTIT_TRACTION_FOLLOWUP_PACKET_2026-07-09.md"

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

THREAD_SIGNALS = [
    {
        "source_ref": "gmail:19f43c8a4ba9346e",
        "safe_signal": "EVTit requested the internal application form so its process could start.",
        "action_meaning": "Application and review process exists; keep next response concise and source-backed.",
    },
    {
        "source_ref": "gmail:19f44a3d4a48d2c6",
        "safe_signal": "Robert recorded that the EVTit application form was submitted.",
        "action_meaning": "Follow-up should assume intake is in motion, not resubmit the same material.",
    },
    {
        "source_ref": "gmail:19f47e797960c0cd",
        "safe_signal": "EVTit indicated its technical team was reviewing the materials already sent.",
        "action_meaning": "Provide a reviewer index and build-scope menu instead of a long narrative reset.",
    },
    {
        "source_ref": "gmail:19f47fa385e22fce",
        "safe_signal": "EVTit offered a short first conversation and indicated a longer technical-team call could follow.",
        "action_meaning": "Ask for a 30-minute technical follow-up if there is still fit.",
    },
    {
        "source_ref": "gmail:19f4822c21a4a861",
        "safe_signal": "EVTit acknowledged the missed-window note without escalation.",
        "action_meaning": "Keep the tone calm, accountable, and forward-moving.",
    },
    {
        "source_ref": "gmail:19f484a1fe4aea3b",
        "safe_signal": "Robert sent the same-day note that he was present and the issue was timing confusion.",
        "action_meaning": "Do not send another apology-only message; pair the reset with a concrete next step.",
    },
]

BUILD_SCOPE_MENU = [
    {
        "scope_id": "proof_portal_hardening",
        "title": "Proof portal hardening",
        "outcome": "Cleaner reviewer entry point, proof-card navigation, and public-safe claim gates.",
        "owner_gate": "Robert approves public wording and any external share.",
    },
    {
        "scope_id": "replay_runner_manifest",
        "title": "Replay runner and evidence manifest",
        "outcome": "Hash-backed replay receipts, source provenance, baseline locking, and reproducibility handoff.",
        "owner_gate": "External data owner or reviewer chooses any buyer-specific data, metric, and baseline.",
    },
    {
        "scope_id": "pilot_onboarding",
        "title": "Pilot onboarding path",
        "outcome": "A 30-day path from technical fit call to scoped validation study or engineering sprint.",
        "owner_gate": "Human approves pilot terms, data boundary, schedule, and economics.",
    },
    {
        "scope_id": "api_reliability_cost_controls",
        "title": "API reliability and cost controls",
        "outcome": "Usage guardrails, retry limits, model routing, and operating receipts for proof-stack continuity.",
        "owner_gate": "Human approves vendor terms, billing, and operational limits.",
    },
    {
        "scope_id": "grant_investor_packet_support",
        "title": "Grant and investor packet support",
        "outcome": "Sharper SBIR, RFI, investor, and partner materials with official-source protocol gates.",
        "owner_gate": "Human approves every portal action, send, certification, and term.",
    },
    {
        "scope_id": "security_claim_boundary",
        "title": "Security and claim-boundary layer",
        "outcome": "A stricter separation between evidence, draft claims, counsel review, and final authority.",
        "owner_gate": "No cybersecurity, IP, field result, or government-readiness claim without exact evidence.",
    },
]

FOLLOWUP_DRAFTS = [
    {
        "draft_id": "same_day_reset_next_step",
        "subject": "LumenCore x EVTit - short reset and next technical step",
        "body": [
            "Hi Terry,",
            "",
            "Thank you for the grace on the timing confusion today. I do not want the miss to turn into noise for your team, so I tightened the follow-up into the concrete decision point.",
            "",
            "The clean fit question is whether EVTit / Black Dog wants to help turn LumenCore's proof-to-pilot stack into a 30-day productization sprint: proof portal, replay runner, evidence manifest, pilot onboarding, API reliability controls, and grant/investor packet support.",
            "",
            "If the team is still open to it, the useful next step would be a 30-minute technical fit call with Bruno and Aron focused on build scope, validation path, and what an in-kind engineering sprint would actually deliver.",
            "",
            "I will keep the claims tight: no partnership, investment, field validation, savings, or production deployment is represented unless your team formally confirms it.",
            "",
            "Thank you,",
            "Robert",
        ],
        "human_send_required": True,
    },
    {
        "draft_id": "technical_team_packet_note",
        "subject": "Technical packet: LumenCore proof-to-pilot sprint scope",
        "body": [
            "Hi Terry, Bruno, Aron, and Scott,",
            "",
            "For technical review, I would frame LumenCore as a proof-to-pilot infrastructure layer: source registry, hash-backed replay, locked baselines, reviewer-safe dashboards, and claim gates that keep unsupported claims out of the materials.",
            "",
            "The most useful EVTit contribution would be engineering lift around the reviewer portal, repeatable replay runner, evidence manifest, pilot onboarding flow, API/cost reliability, and packaged grant/investor review surfaces.",
            "",
            "My ask is not for anyone to accept a broad claim. It is to choose a narrow 30-day build sprint that makes the evidence easier for serious reviewers, agencies, and pilot partners to inspect.",
            "",
            "Best,",
            "Robert",
        ],
        "human_send_required": True,
    },
]

DILIGENCE_ARTIFACTS = [
    "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
    "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
    "docs/PROOF_TO_PILOT_CONTROL_ROOM_2026-06-25.md",
    "docs/PLATFORM_PROOF_AND_COMMERCIALIZATION_MAP.md",
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


def artifact_status(rel_path: str) -> dict[str, Any]:
    path = ROOT / rel_path
    return {
        "path": rel_path,
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
    gate = read_json(REVIEWER_GATE_JSON)
    data_room = read_json(DATA_ROOM_JSON)
    evtit_lane = find_evtit_lane(traction)
    artifact_rows = [artifact_status(path) for path in DILIGENCE_ARTIFACTS]
    gate_summary = gate.get("summary", {}) if isinstance(gate.get("summary"), dict) else {}
    data_summary = data_room.get("summary", {}) if isinstance(data_room.get("summary"), dict) else {}
    artifacts_present = all(row["present"] for row in artifact_rows)
    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate_summary.get("unsafe_secret_count") or 0) == 0 and int(gate_summary.get("unsafe_claim_count") or 0) == 0

    payload = {
        "generated_utc": now_utc(),
        "schema": "traction_followup_packet_v1",
        "status": "TRACTION_FOLLOWUP_READY_HUMAN_SEND_REQUIRED"
        if gate_clear and artifacts_present
        else "TRACTION_FOLLOWUP_BLOCKED",
        "lane": {
            "lane_id": "evtit_blackdog_inkind",
            "name": evtit_lane.get("name", "EVTit / Black Dog in-kind engineering fund"),
            "status": evtit_lane.get("status", "RESET_NOTE_SENT_TECH_REVIEW_PENDING"),
            "fit_score": evtit_lane.get("fit_score", 92),
            "priority": evtit_lane.get("priority", 1),
            "claim_boundary": evtit_lane.get(
                "claim_boundary",
                "Meeting and application evidence only; no investment, services award, or partnership has been accepted.",
            ),
        },
        "summary": {
            "thread_signal_count": len(THREAD_SIGNALS),
            "build_scope_count": len(BUILD_SCOPE_MENU),
            "draft_count": len(FOLLOWUP_DRAFTS),
            "diligence_artifact_count": len(artifact_rows),
            "diligence_artifacts_present": artifacts_present,
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "data_room_status": data_room.get("status", ""),
            "data_room_markdown_count": int(data_summary.get("manifested_markdown_count") or 0),
            "human_send_required": True,
            "external_send_allowed_without_human": False,
            "equity_terms_allowed_without_human": False,
            "partnership_claimed": False,
            "investment_claimed": False,
            "services_award_claimed": False,
            "field_validation_claimed": False,
        },
        "thread_signals": THREAD_SIGNALS,
        "build_scope_menu": BUILD_SCOPE_MENU,
        "followup_drafts": FOLLOWUP_DRAFTS,
        "diligence_artifacts": artifact_rows,
        "human_gate": {
            "send_email_allowed_without_human": False,
            "schedule_followup_allowed_without_human": False,
            "accept_equity_or_services_terms_without_human": False,
            "share_private_files_without_human": False,
            "rule": "This packet prepares follow-up language and review scope only. Robert approves any send, schedule, terms, or file sharing.",
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["traction_followup_packet_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lane = payload["lane"]
    lines = [
        "# EVTit Traction Follow-Up Packet - 2026-07-09",
        "",
        "Purpose: give Robert a clean, human-approved follow-up surface after the EVTit timing confusion, while preserving the proof-to-pilot opportunity and keeping claims bounded.",
        "",
        "This packet prepares language, scope, and diligence links. It does not send email, schedule a meeting, accept terms, share private files, or claim a partnership.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lane ID: `{lane['lane_id']}`",
        f"- Lane status: `{lane['status']}`",
        f"- Fit score: `{lane['fit_score']}`",
        f"- Thread signals: `{summary['thread_signal_count']}`",
        f"- Build scopes: `{summary['build_scope_count']}`",
        f"- Drafts: `{summary['draft_count']}`",
        f"- Diligence artifacts present: `{str(summary['diligence_artifacts_present']).lower()}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Human send required: `{str(summary['human_send_required']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Equity terms without human: `{str(summary['equity_terms_allowed_without_human']).lower()}`",
        f"- Partnership claimed: `{str(summary['partnership_claimed']).lower()}`",
        f"- Investment claimed: `{str(summary['investment_claimed']).lower()}`",
        f"- Services award claimed: `{str(summary['services_award_claimed']).lower()}`",
        f"- Field validation claimed: `{str(summary['field_validation_claimed']).lower()}`",
        f"- Packet SHA-256: `{payload['traction_followup_packet_sha256']}`",
        "",
        "## Claim Boundary",
        "",
        lane["claim_boundary"],
        "",
        "## Thread Signals",
        "",
    ]
    for signal in payload["thread_signals"]:
        lines.extend(
            [
                f"### {signal['source_ref']}",
                "",
                f"- Safe signal: {signal['safe_signal']}",
                f"- Action meaning: {signal['action_meaning']}",
                "",
            ]
        )

    lines.extend(["## 30-Day Build Scope Menu", ""])
    for scope in payload["build_scope_menu"]:
        lines.extend(
            [
                f"### {scope['title']}",
                "",
                f"- Scope ID: `{scope['scope_id']}`",
                f"- Outcome: {scope['outcome']}",
                f"- Owner gate: {scope['owner_gate']}",
                "",
            ]
        )

    lines.extend(["## Human-Approved Drafts", ""])
    for draft in payload["followup_drafts"]:
        lines.extend(
            [
                f"### {draft['draft_id']}",
                "",
                f"- Subject: {draft['subject']}",
                f"- Human send required: `{str(draft['human_send_required']).lower()}`",
                "",
                "```text",
                *draft["body"],
                "```",
                "",
            ]
        )

    lines.extend(["## Diligence Artifacts", ""])
    for row in payload["diligence_artifacts"]:
        state = "present" if row["present"] else "missing"
        lines.append(f"- `{state}` `{row['path']}` sha256=`{row['sha256']}` bytes=`{row['bytes']}`")

    lines.extend(["", "## Human Gate", ""])
    for key, value in payload["human_gate"].items():
        lines.append(f"- {key}: `{value}`")
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
        raise SystemExit(f"Refusing to write sensitive public follow-up markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "thread_signals": payload["summary"]["thread_signal_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"].endswith("HUMAN_SEND_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
