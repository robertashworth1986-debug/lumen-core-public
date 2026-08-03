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

REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
MANIFEST_JSON = OUT_OPS / "data_room_manifest_latest.json"
QA_JSON = OUT_OPS / "reviewer_diligence_qa_matrix_latest.json"
LINKEDIN_JSON = OUT_OPS / "linkedin_universe_profile_packet_latest.json"
PATENT_DEADLINE_CONTROL_JSON = (
    SPRINT_DIR / "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json"
)

OUT_JSON = OUT_OPS / "ip_counsel_diligence_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "ip_counsel_diligence_packet.json"
OUT_MD = SPRINT_DIR / "IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md"

OFFICIAL_SOURCES = [
    {
        "label": "USPTO incomplete or missing application information",
        "url": "https://www.uspto.gov/patents/apply/when-patent-applications-are-incomplete-or-missing-information",
        "packet_use": "Identify the role of OPAP notices and the response period stated in the controlling notice.",
        "verified_fact": "USPTO guidance says an OPAP notice identifies missing or deficient application items, the reply period, and any additional fees.",
    },
    {
        "label": "USPTO nonprovisional utility filing guide",
        "url": "https://www.uspto.gov/patents/basics/apply/utility-patent",
        "packet_use": "Confirm that a corresponding nonprovisional is required during provisional pendency to benefit from the earlier filing.",
        "verified_fact": "USPTO guidance describes nonprovisional applications as examined by an examiner and potentially issuable if patentability requirements are met.",
    },
    {
        "label": "USPTO Patent Center status check",
        "url": "https://www.uspto.gov/patents/apply/checking-application-status/check-filing-status-your-patent-application",
        "packet_use": "Human or counsel checks application status, file history, and official records.",
        "verified_fact": "USPTO describes Patent Center as the route to check status and electronically file or manage patent applications.",
    },
    {
        "label": "USPTO Patent Pro Bono Program",
        "url": "https://www.uspto.gov/patents/basics/using-legal-services/pro-bono/patent-pro-bono-program",
        "packet_use": "Counsel-access route for under-resourced inventors or small businesses.",
        "verified_fact": "USPTO describes a nationwide network matching volunteer patent attorneys and agents with financially under-resourced inventors and small businesses.",
    },
    {
        "label": "WIPO PCT restoration of priority",
        "url": "https://www.wipo.int/en/web/pct-system/texts/restoration",
        "packet_use": "Counsel-only review of any time-sensitive foreign or PCT priority strategy.",
        "verified_fact": "WIPO describes restoration of priority as limited, jurisdiction-dependent, and time-sensitive; availability must not be assumed.",
    },
]

INVENTION_FAMILIES = [
    {
        "id": "A",
        "name": "Proof-to-pilot evidence operating system",
        "reviewer_safe_summary": "Source, baseline, candidate, metric, hash, reviewer, and claim-boundary records are packaged into proof packets.",
        "hold_back": "Implementation-specific claim charts, unreleased schemas, orchestration internals, and enabling diagrams until counsel review.",
    },
    {
        "id": "B",
        "name": "Controlled emergence and distributed AI validation",
        "reviewer_safe_summary": "Reproducible evidence controls for AI systems evaluated under measured replay constraints.",
        "hold_back": "Agent orchestration internals, hidden constants, and unpublished system interaction details.",
    },
    {
        "id": "C",
        "name": "Geometry, flowform, and route-control families",
        "reviewer_safe_summary": "Candidate geometry or control families are evaluated against named baselines under locked replay constraints.",
        "hold_back": "New formulas, unreleased diagrams, feature construction details, and claim-critical family definitions.",
    },
    {
        "id": "D",
        "name": "Live-source breadth and public proof feeds",
        "reviewer_safe_summary": "Measured-source inventory and hash-backed proof feeds support public-safe reviewer orientation.",
        "hold_back": "Provider keys, nonpublic adapter internals, unreleased measurement logic, and private data access routes.",
    },
    {
        "id": "E",
        "name": "Domain translation packets",
        "reviewer_safe_summary": "The same evidence spine is adapted to MissionWeave, HarborSentinel, TSMO, NASA data-center, nuclear partner, and NSF-style review packets.",
        "hold_back": "Domain-specific implementation details created after any earlier filing until counsel determines support.",
    },
    {
        "id": "F",
        "name": "Autonomous research and quant evaluation controls",
        "reviewer_safe_summary": "Autonomous research and replay evaluation loops operate under human-gated execution controls and immutable audit logging.",
        "hold_back": "Live execution logic, capital-control details, and compliance-sensitive trading claims.",
    },
]

COUNSEL_QUESTIONS = [
    "What official filing receipt, application number, filing date, title, and named-inventor facts control the current deadline posture?",
    "Which current public packets are supported by the existing filing record, and which contain possible new matter?",
    "Which invention families should be handled as new provisional filings, continuations, divisionals, PCT questions, or nonpublic internal material?",
    "Which public repository, dashboard, LinkedIn, investor, grant, or agency artifacts should be withheld or simplified before further disclosure?",
    "What assignment, contributor, co-inventor, contractor, or prior-disclosure facts must be documented before investor or agency diligence?",
    "What exact wording may be used in grants and investor materials without implying patent grant, legal exclusivity, or clearance to operate?",
]

COUNSEL_INTAKE_ITEMS = [
    {
        "item": "Official USPTO record",
        "needed_from_human": "Filing receipt, application number, filing date, title, entity status, correspondence history, and any office communications.",
        "automation_status": "Not retrieved by automation; human or counsel must verify in Patent Center.",
    },
    {
        "item": "Current claim drafts",
        "needed_from_human": "All claim drafts, diagrams, specification drafts, and dated invention notes.",
        "automation_status": "Packet lists invention families only; no full claim chart is published.",
    },
    {
        "item": "Public disclosure timeline",
        "needed_from_human": "Dates and links for public demos, posts, decks, GitHub pushes, grant submissions, emails, dashboards, and shared PDFs.",
        "automation_status": "Can be assembled from repo history and public artifacts after human approval.",
    },
    {
        "item": "New matter map",
        "needed_from_human": "Feature list separating what existed at the controlling filing date from later additions.",
        "automation_status": "Initial family list is ready; counsel must classify support.",
    },
    {
        "item": "Investor and grant wording",
        "needed_from_human": "Counsel-approved phrases for pitch, grant, SBIR, RFI, LinkedIn, and data-room use.",
        "automation_status": "Current packet uses cautious non-legal, no-exclusivity language.",
    },
]

PUBLIC_RULES = {
    "allowed": [
        "patent strategy under counsel review",
        "invention-family artifacts preserved for counsel review",
        "public materials are intentionally non-enabling and claim-bounded",
        "full claim scope is not represented in this packet",
        "human or counsel must verify official filing status before legal or investor reliance",
    ],
    "blocked": [
        "do not use 'patented' unless a granted patent is verified",
        "do not use 'patent-protected' unless counsel approves the exact scope",
        "do not use 'freedom to operate'",
        "do not say a nonprovisional deadline is safe without official receipt review",
        "do not publish full claim charts or enabling diagrams until counsel approves",
    ],
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
    "xox",
]

SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.I),
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
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_status(path_text: str) -> dict[str, Any]:
    path = ROOT / path_text
    return {
        "path": path_text,
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    hits = {marker for marker in SENSITIVE_MARKERS if marker in lowered}
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            hits.add(pattern.pattern)
    return sorted(hits)


def build_payload() -> dict[str, Any]:
    gate = read_json(REVIEWER_GATE_JSON)
    authority = read_json(AUTHORITY_JSON)
    docket = read_json(DOCKET_JSON)
    manifest = read_json(MANIFEST_JSON)
    qa = read_json(QA_JSON)
    linkedin = read_json(LINKEDIN_JSON)
    patent_deadline_control = read_json(PATENT_DEADLINE_CONTROL_JSON)

    evidence_paths = [
        "grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
        "grant_submissions/PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md",
        "grant_submissions/funding_sprint_20260709/REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        "grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.md",
    ]
    evidence_status = [artifact_status(path) for path in evidence_paths]

    gate_summary = gate.get("summary") or {}
    submission_argument_gate_clear = bool(gate.get("reviewer_gate_clear"))
    reviewer_packaging_gate_clear = (
        bool(gate_summary.get("packaging_checks_clear"))
        and int(gate_summary.get("unsafe_secret_count") or 0) == 0
        and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    )
    authority_summary = authority.get("summary", {}) if isinstance(authority.get("summary"), dict) else {}
    all_final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human"))
    evidence_present = all(row["present"] for row in evidence_status)

    payload = {
        "generated_utc": now_utc(),
        "schema": "ip_counsel_diligence_packet_v1",
        "status": "IP_COUNSEL_DILIGENCE_READY_HUMAN_COUNSEL_REQUIRED"
        if reviewer_packaging_gate_clear
        and all_final_actions_blocked
        and evidence_present
        else "IP_COUNSEL_DILIGENCE_BLOCKED",
        "official_sources": OFFICIAL_SOURCES,
        "summary": {
            "official_source_count": len(OFFICIAL_SOURCES),
            "invention_family_count": len(INVENTION_FAMILIES),
            "counsel_question_count": len(COUNSEL_QUESTIONS),
            "intake_item_count": len(COUNSEL_INTAKE_ITEMS),
            "evidence_artifact_count": len(evidence_status),
            "missing_evidence_count": sum(1 for row in evidence_status if not row["present"]),
            "reviewer_packaging_gate_clear": reviewer_packaging_gate_clear,
            "submission_argument_gate_clear": submission_argument_gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "legal_advice_claimed": False,
            "patent_grant_claimed": False,
            "clearance_to_operate_claimed": False,
            "public_disclosure_review_required": True,
            "licensed_counsel_required": True,
            "human_patent_center_check_required": True,
            "patent_deadline_control_status": patent_deadline_control.get("status", "MISSING"),
            "us_prosecution_deadline_verified": False,
            "foreign_pct_priority_review_time_sensitive": (
                "TIME_SENSITIVE"
                in str(
                    (patent_deadline_control.get("deadline_posture") or {}).get(
                        "foreign_pct_priority", ""
                    )
                )
            ),
            "qa_count": int((qa.get("summary") or {}).get("qa_count") or 0),
            "data_room_markdown_count": int((manifest.get("summary") or {}).get("manifested_markdown_count") or 0),
            "linkedin_packet_ready": str(linkedin.get("status") or "").endswith("HUMAN_POST_REQUIRED"),
        },
        "invention_families": INVENTION_FAMILIES,
        "counsel_questions": COUNSEL_QUESTIONS,
        "counsel_intake_items": COUNSEL_INTAKE_ITEMS,
        "public_rules": PUBLIC_RULES,
        "deadline_posture": patent_deadline_control.get("deadline_posture", {}),
        "patent_deadline_control": {
            "status": patent_deadline_control.get("status", "MISSING"),
            "control_artifact": rel(PATENT_DEADLINE_CONTROL_JSON),
            "direct_answer": patent_deadline_control.get("direct_answer", ""),
            "private_paths_published": bool(
                (patent_deadline_control.get("public_evidence_summary") or {}).get(
                    "private_paths_published", True
                )
            ),
            "application_identifier_published": bool(
                (patent_deadline_control.get("public_evidence_summary") or {}).get(
                    "application_identifier_published", True
                )
            ),
        },
        "evidence_status": evidence_status,
        "human_gate": {
            "patent_center_access_allowed_without_human": False,
            "legal_filing_allowed_without_human": False,
            "public_disclosure_expansion_allowed_without_human": False,
            "investor_ip_claim_expansion_allowed_without_human": False,
            "rule": "Human and licensed patent counsel must verify official status, deadlines, support, disclosures, and exact public language.",
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["ip_counsel_diligence_packet_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines: list[str] = [
        "# IP Counsel Diligence Packet - 2026-07-09",
        "",
        "Purpose: give patent counsel, investors, and grant reviewers a bounded map of the LumenCore invention universe without turning automation into legal advice.",
        "",
        "This packet is not legal advice. It does not claim patent grant, patentability, legal exclusivity, clearance to operate, safe deadline status, or filing sufficiency.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Official USPTO sources: `{summary['official_source_count']}`",
        f"- Invention families: `{summary['invention_family_count']}`",
        f"- Counsel questions: `{summary['counsel_question_count']}`",
        f"- Intake items: `{summary['intake_item_count']}`",
        f"- Evidence artifacts: `{summary['evidence_artifact_count']}`",
        f"- Missing evidence: `{summary['missing_evidence_count']}`",
        f"- Reviewer packaging gate clear: `{str(summary['reviewer_packaging_gate_clear']).lower()}`",
        f"- Submission argument gate clear: `{str(summary['submission_argument_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Legal advice claimed: `{str(summary['legal_advice_claimed']).lower()}`",
        f"- Patent grant claimed: `{str(summary['patent_grant_claimed']).lower()}`",
        f"- Clearance to operate claimed: `{str(summary['clearance_to_operate_claimed']).lower()}`",
        f"- Public disclosure review required: `{str(summary['public_disclosure_review_required']).lower()}`",
        f"- Licensed counsel required: `{str(summary['licensed_counsel_required']).lower()}`",
        f"- Human Patent Center check required: `{str(summary['human_patent_center_check_required']).lower()}`",
        f"- Patent deadline control: `{summary['patent_deadline_control_status']}`",
        f"- U.S. prosecution deadline verified: `{str(summary['us_prosecution_deadline_verified']).lower()}`",
        f"- Foreign or PCT priority review time-sensitive: `{str(summary['foreign_pct_priority_review_time_sensitive']).lower()}`",
        f"- Packet SHA-256: `{payload['ip_counsel_diligence_packet_sha256']}`",
        "",
        "## Deadline Evidence Control",
        "",
        payload["patent_deadline_control"]["direct_answer"],
        "",
        f"- Status: `{payload['patent_deadline_control']['status']}`",
        f"- Control artifact: `{payload['patent_deadline_control']['control_artifact']}`",
        f"- Private paths published: `{str(payload['patent_deadline_control']['private_paths_published']).lower()}`",
        f"- Application identifier published: `{str(payload['patent_deadline_control']['application_identifier_published']).lower()}`",
        "",
        "## Official Sources",
        "",
    ]
    for source in payload["official_sources"]:
        lines.extend(
            [
                f"### {source['label']}",
                "",
                f"- URL: {source['url']}",
                f"- Packet use: {source['packet_use']}",
                f"- Verified fact: {source['verified_fact']}",
                "",
            ]
        )

    lines.extend(["## Invention Family Map", ""])
    for family in payload["invention_families"]:
        lines.extend(
            [
                f"### Family {family['id']} - {family['name']}",
                "",
                f"- Reviewer-safe summary: {family['reviewer_safe_summary']}",
                f"- Hold back until counsel review: {family['hold_back']}",
                "",
            ]
        )

    lines.extend(["## Counsel Questions", ""])
    for idx, question in enumerate(payload["counsel_questions"], start=1):
        lines.append(f"{idx}. {question}")

    lines.extend(["", "## Counsel Intake Items", ""])
    for item in payload["counsel_intake_items"]:
        lines.extend(
            [
                f"### {item['item']}",
                "",
                f"- Needed from human: {item['needed_from_human']}",
                f"- Automation status: {item['automation_status']}",
                "",
            ]
        )

    lines.extend(["## Public Rules", "", "### Allowed", ""])
    for item in payload["public_rules"]["allowed"]:
        lines.append(f"- {item}")
    lines.extend(["", "### Blocked", ""])
    for item in payload["public_rules"]["blocked"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Human Gate", ""])
    for key, value in payload["human_gate"].items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public IP markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(json.dumps({"status": payload["status"], "outputs": payload["outputs"]}, indent=2))
    return 0 if payload["status"].endswith("HUMAN_COUNSEL_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
