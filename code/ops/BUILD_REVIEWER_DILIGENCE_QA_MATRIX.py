from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

DECISION_JSON = OUT_OPS / "reviewer_decision_brief_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
MANIFEST_JSON = OUT_OPS / "data_room_manifest_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"

OUT_JSON = OUT_OPS / "reviewer_diligence_qa_matrix_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "reviewer_diligence_qa_matrix.json"
OUT_MD = SPRINT_DIR / "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md"

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "xox",
]

SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.I),
]

QA_ROWS = [
    {
        "question": "What is the shortest safe reviewer path through the packet?",
        "answer": "Start with the decision brief, then use the authority matrix for final-action gates, the human docket for dates, and the data-room manifest for hashes and custody.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        ],
        "claim_boundary": "This is a review route, not approval to send or submit anything.",
        "decision_use": "Orient a reviewer in under five minutes.",
        "human_gate": "Human approval before external send or portal action.",
    },
    {
        "question": "Is LumenCore claiming award, investment, or agency approval?",
        "answer": "No. The packet represents submitted or prepared materials, live traction signals, and human-gated readiness controls; it does not represent award, investment decision, agency approval, or production deployment.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        ],
        "claim_boundary": "No award, approval, deployment, investment, or revenue claim.",
        "decision_use": "Prevent overclaim risk during reviewer or investor diligence.",
        "human_gate": "Human review before any public claim reuse.",
    },
    {
        "question": "What traction is strongest right now?",
        "answer": "The strongest live signals are SAM.gov validation watch, EVTit/Black Dog meeting prep, LANL VISION licensing follow-up, USPTO Georgia PATENTS routing, LvlUp First Check review watch, DARPA DICE full-proposal sprint, FHWA TSMO, NASA data-center RFI, DSIP MissionWeave, NSF Project Pitch, and buyer-discovery signals such as Protecnium ITS infrastructure.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
        ],
        "claim_boundary": "Traction means documented opportunity movement, not outcome certainty.",
        "decision_use": "Focus time and capital on lanes with current evidence.",
        "human_gate": "Human decides follow-up timing and content.",
    },
    {
        "question": "Which actions are urgent?",
        "answer": "The current urgent actions are SAM.gov validation monitoring, EVTit meeting/build-scope follow-up, LANL VISION licensing follow-up, USPTO Georgia PATENTS counsel routing, DARPA DICE full-proposal compliance build, and OpenAI API continuity routing.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
        ],
        "claim_boundary": "Urgent does not mean autonomous; all external actions remain blocked without human authority.",
        "decision_use": "Prioritize next human moves.",
        "human_gate": "Human approval for meeting actions, BAA package action, or vendor account action.",
    },
    {
        "question": "What can be prepared internally without human final approval?",
        "answer": "Drafting, compliance matrices, evidence organization, reviewer packets, and partner-route intelligence can be prepared internally. Sends, portal submissions, certifications, filings, pricing, term acceptance, trading, and capital movement cannot.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        ],
        "claim_boundary": "Internal preparation is not external authorization.",
        "decision_use": "Preserve speed while respecting legal, agency, and account gates.",
        "human_gate": "Named authority gate per lane in the authority matrix.",
    },
    {
        "question": "Which agency/IP packages are assembled enough for review?",
        "answer": "The assembly gate separates review-ready packages from validation watch, counsel-required, partner-only, and scout-only lanes. It shows 15 federal/IP assembly lanes, component states, first artifacts, blockers, and the required human authority for each lane.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/AGENCY_SUBMISSION_ASSEMBLY_GATE_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/AGENCY_ACCOUNT_ACTIVATION_DOCKET_2026-07-09.md",
        ],
        "claim_boundary": "Assembly readiness means reviewer packet organization, not final portal readiness, legal certification, award eligibility, or permission to submit.",
        "decision_use": "Let an agency reviewer or investor see exactly what is ready to review and what still blocks final action.",
        "human_gate": "Human approval before send, upload, certification, filing, pricing, or final submission.",
    },
    {
        "question": "How are live-source credentials and premium social lanes protected?",
        "answer": "The key governance firewall keeps YouTube, Spotify, Meta/Facebook, and other live-source lanes environment-driven and read-only for proof generation, while blocking public posting, ad spend, account mutation, live trading, withdrawals, and capital movement.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/KEY_GOVERNANCE_FIREWALL_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
        ],
        "claim_boundary": "Credential presence is not permission to write, spend, trade, mutate accounts, publish private provider data, or bypass human approval.",
        "decision_use": "Show technical reviewers and investors that premium/live data can increase proof quality without increasing account-control risk.",
        "human_gate": "Human approval before any external account action, write action, spend, credential rotation, or public release.",
    },
    {
        "question": "What proof exists for government protocol readiness?",
        "answer": "The packet includes agency protocol controls, reviewer gate scans, submission authority rows, and lane-specific packages for FHWA, NASA, DSIP, NSF, DICE, EPA routing, and partner-only federal lanes.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        ],
        "claim_boundary": "Protocol readiness is preparation and control maturity, not certification or award eligibility.",
        "decision_use": "Show agencies and reviewers that final authority is controlled.",
        "human_gate": "SAM/AOR, DSIP Firm PIN, BAA, RFI, and portal gates remain human-controlled.",
    },
    {
        "question": "How is IP and patent-risk handled?",
        "answer": "The packet separates claim boundaries from legal action, includes a patent counsel lane, and blocks public expansion of patent, ownership, or freedom-to-operate claims without licensed counsel.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        ],
        "claim_boundary": "No legal advice, patentability, ownership, or freedom-to-operate opinion is represented.",
        "decision_use": "Let counsel and investors see that IP risk is actively bounded.",
        "human_gate": "Licensed patent counsel and Robert decide filing or disclosure action.",
    },
    {
        "question": "How is autonomous quant or AI-risk controlled?",
        "answer": "The packet explicitly blocks live trading, capital movement, autonomous external action, and overclaim language while allowing internal proof-stack development and review.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        ],
        "claim_boundary": "No live-profit, risk-free, autonomous-trading-ready, or capital-control claim.",
        "decision_use": "Make the autonomy ambition fundable without creating uncontrolled action risk.",
        "human_gate": "Human authority before trading, capital movement, send, submit, or certification.",
    },
    {
        "question": "Which lanes should not be pursued solo?",
        "answer": "HHS AI Power User Pilot, CSOSA public safety analytics, EPA UCMR 6 lab services, and Defense Energy Consortium are partner-only, intro-only, or parked unless a qualified partner leads.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
        ],
        "claim_boundary": "No FedRAMP, ATO, regulated lab, public-safety deployment, consortium management, or project-financing claim.",
        "decision_use": "Save time by not chasing weak solo-prime bids.",
        "human_gate": "Qualified partner and human approval before reactivation.",
    },
    {
        "question": "What makes this easier for a reviewer or investor?",
        "answer": "Every lane has a first artifact, decision question, claim boundary, authority gate, and machine-readable proof receipt. The data-room manifest hashes the artifacts and mirrors them to E drive.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
        ],
        "claim_boundary": "Ease of review does not imply approval or investment.",
        "decision_use": "Reduce diligence friction and make reviewer handoff cleaner.",
        "human_gate": "Human chooses what to share externally.",
    },
    {
        "question": "What should be shared first externally?",
        "answer": "Share only human-approved front-door artifacts, starting with the reviewer decision brief and data-room manifest, then lane-specific packages if the reviewer asks.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        ],
        "claim_boundary": "No unreviewed archives, meeting access details, credentials, or private account material should be shared.",
        "decision_use": "Keep outreach tight and public-safe.",
        "human_gate": "Human approval before any external send.",
    },
    {
        "question": "What remains unproven or still needs external validation?",
        "answer": "No external field result, savings result, agency acceptance, independent pilot result, legal IP conclusion, or investment term is represented until an external owner, counsel, agency, or investor verifies it.",
        "evidence_artifacts": [
            "grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        ],
        "claim_boundary": "The packet is strongest because it states these limits clearly.",
        "decision_use": "Show mature risk framing instead of pretending the gaps are gone.",
        "human_gate": "External validation owner or licensed reviewer must confirm future claims.",
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
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def artifact_status(paths: list[str]) -> list[dict[str, Any]]:
    rows = []
    for item in paths:
        path = ROOT / item
        rows.append(
            {
                "path": item,
                "present": path.exists(),
                "bytes": path.stat().st_size if path.exists() else 0,
                "sha256": sha256_file(path) if path.exists() else "",
            }
        )
    return rows


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_payload() -> dict[str, Any]:
    decision = read_json(DECISION_JSON)
    authority = read_json(AUTHORITY_JSON)
    docket = read_json(DOCKET_JSON)
    manifest = read_json(MANIFEST_JSON)
    gate = read_json(REVIEWER_GATE_JSON)

    rows = []
    for index, row in enumerate(QA_ROWS, start=1):
        enriched = dict(row)
        enriched["index"] = index
        enriched["evidence_status"] = artifact_status(row["evidence_artifacts"])
        enriched["missing_evidence_count"] = sum(1 for item in enriched["evidence_status"] if not item["present"])
        enriched["qa_row_sha256"] = hashlib.sha256(
            json.dumps(enriched, sort_keys=True).encode("utf-8")
        ).hexdigest()
        rows.append(enriched)

    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate["summary"]["unsafe_secret_count"]) == 0 and int(gate["summary"]["unsafe_claim_count"]) == 0
    all_final_actions_blocked = bool(decision["summary"]["all_final_actions_blocked_without_human"]) and bool(
        authority["summary"]["all_final_actions_blocked_without_human"]
    )
    all_evidence_present = all(row["missing_evidence_count"] == 0 for row in rows)

    payload = {
        "generated_utc": now_utc(),
        "schema": "reviewer_diligence_qa_matrix_v1",
        "status": "REVIEWER_DILIGENCE_QA_READY" if gate_clear and all_final_actions_blocked and all_evidence_present else "REVIEWER_DILIGENCE_QA_BLOCKED",
        "summary": {
            "qa_count": len(rows),
            "missing_evidence_count": sum(row["missing_evidence_count"] for row in rows),
            "decision_lane_count": int(decision["summary"]["lane_count"]),
            "urgent_lane_count": int(decision["summary"]["urgent_lane_count"]),
            "authority_lane_count": int(authority["summary"]["lane_count"]),
            "docket_lane_count": int(docket["summary"]["lane_count"]),
            "manifested_markdown_count": int(manifest["summary"]["manifested_markdown_count"]),
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "qa_rows": rows,
        "source_ledgers": {
            "decision": rel(DECISION_JSON),
            "authority": rel(AUTHORITY_JSON),
            "docket": rel(DOCKET_JSON),
            "manifest": rel(MANIFEST_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["qa_matrix_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reviewer Diligence Q&A Matrix - 2026-07-09",
        "",
        "Purpose: answer the questions a reviewer, investor, agency contact, partner, or counsel is likely to ask before advancing LumenCore.",
        "",
        "This matrix is evidence-backed and human-gated. It does not authorize external sends, submissions, filings, certifications, term acceptance, trading, or capital movement.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Q&A rows: `{summary['qa_count']}`",
        f"- Missing evidence references: `{summary['missing_evidence_count']}`",
        f"- Decision lanes: `{summary['decision_lane_count']}`",
        f"- Urgent lanes: `{summary['urgent_lane_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Q&A matrix SHA-256: `{payload['qa_matrix_sha256']}`",
        "",
        "## Q&A",
        "",
    ]
    for row in payload["qa_rows"]:
        lines.extend(
            [
                f"### {row['index']}. {row['question']}",
                "",
                f"- Answer: {row['answer']}",
                f"- Decision use: {row['decision_use']}",
                f"- Claim boundary: {row['claim_boundary']}",
                f"- Human gate: {row['human_gate']}",
                f"- Missing evidence count: `{row['missing_evidence_count']}`",
                f"- Row SHA-256: `{row['qa_row_sha256']}`",
                "",
                "Evidence:",
            ]
        )
        for evidence in row["evidence_status"]:
            state = "present" if evidence["present"] else "missing"
            lines.append(f"- `{state}` `{evidence['path']}` sha256=`{evidence['sha256']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    hits = {marker for marker in SENSITIVE_MARKERS if marker in lowered}
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            hits.add(pattern.pattern)
    return sorted(hits)


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public diligence markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "qa_count": payload["summary"]["qa_count"],
                "missing_evidence": payload["summary"]["missing_evidence_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
