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
QA_JSON = OUT_OPS / "reviewer_diligence_qa_matrix_latest.json"
IP_JSON = OUT_OPS / "ip_counsel_diligence_packet_latest.json"
FEDERAL_JSON = OUT_OPS / "federal_submission_protocol_packet_latest.json"
AGENCY_JSON = OUT_OPS / "agency_account_activation_docket_latest.json"
KEY_FIREWALL_JSON = OUT_OPS / "key_governance_firewall_latest.json"
TRACTION_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"

OUT_JSON = OUT_OPS / "reviewer_investor_fast_lane_router_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "reviewer_investor_fast_lane_router.json"
OUT_MD = SPRINT_DIR / "REVIEWER_INVESTOR_FAST_LANE_ROUTER_2026-07-09.md"

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

SENSITIVE_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{12,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}", re.I),
]

ROUTES = [
    {
        "route_id": "five_minute_reviewer_start",
        "audience": "reviewer_or_investor",
        "question": "Where should a busy reviewer start?",
        "answer": "Open the decision brief, then the diligence Q&A, then the authority matrix. This gives the lane count, evidence posture, final-action gates, and the first artifact for each opportunity.",
        "first_open": "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/DATA_ROOM_MANIFEST_2026-07-09.md",
        ],
        "funding_use": "Make initial diligence fast enough that a reviewer can say what is ready, what is blocked, and what to ask next.",
        "claim_boundary": "This route proves organization and review readiness, not approval, award, investment, or field validation.",
        "human_gate": "Human chooses what to send externally.",
    },
    {
        "route_id": "agency_submission_protocol",
        "audience": "agency_reviewer_or_contracting_contact",
        "question": "Is LumenCore disciplined enough for agency protocol?",
        "answer": "Use the federal protocol packet and agency activation docket to show portal gates, authority gates, readiness flags, and blocked certification claims.",
        "first_open": "grant_submissions/funding_sprint_20260709/FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/AGENCY_SUBMISSION_ASSEMBLY_GATE_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/AGENCY_ACCOUNT_ACTIVATION_DOCKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
        ],
        "funding_use": "Reduce agency risk by making SAM, Grants.gov, Research.gov, DSIP, cyber, and signer authority gates explicit.",
        "claim_boundary": "No SAM Active status, AOR authority, DSIP authority, CMMC status, award eligibility, or certification is claimed unless official portal records prove it.",
        "human_gate": "Human controls portal login, signer authority, certifications, uploads, and final submission.",
    },
    {
        "route_id": "ip_patent_claim_boundary",
        "audience": "patent_counsel_or_ip_diligence",
        "question": "What can be said about IP without overclaiming?",
        "answer": "Use the IP counsel packet and boundary register to separate invention-family summaries from legal claims, claim charts, filing decisions, and freedom-to-operate language.",
        "first_open": "grant_submissions/funding_sprint_20260709/IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
            "grant_submissions/PATENT_LEGAL_RESCUE_PACKET_2026-06-20.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        ],
        "funding_use": "Let counsel and investors see disciplined invention-family preservation without publishing enabling claim strategy.",
        "claim_boundary": "No legal advice, patentability, ownership, exclusivity, granted patent, or clearance-to-operate opinion is represented.",
        "human_gate": "Licensed patent counsel and Robert decide filing, disclosure, and exact claim language.",
    },
    {
        "route_id": "live_source_and_key_governance",
        "audience": "technical_diligence_or_security_reviewer",
        "question": "Can live sources be used without turning credentials into risk?",
        "answer": "Use the key governance firewall and measured-source register to show environment-based credential handling, read-only source posture, and blocked write/spend/control actions.",
        "first_open": "grant_submissions/funding_sprint_20260709/KEY_GOVERNANCE_FIREWALL_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        ],
        "funding_use": "Show that premium/live data lanes can support proof generation while social posting, spend, account mutation, trading, and capital movement remain blocked.",
        "claim_boundary": "Live-source availability is not permission to mutate accounts, post publicly, spend money, trade, withdraw, or publish provider-specific private data.",
        "human_gate": "Human approves any external account action, write action, spend, or credential rotation.",
    },
    {
        "route_id": "traction_deadline_action",
        "audience": "operator_or_non_dilutive_funding_reviewer",
        "question": "Which lanes deserve action first?",
        "answer": "Use the traction ledger and human docket to see the 19-lane opportunity map, urgent dates, response status, and required next human action.",
        "first_open": "grant_submissions/funding_sprint_20260709/TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/HUMAN_ACTION_DOCKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/CLOSEST_QUALIFIED_GRANTS_AND_CONTRACTS_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_CONCIERGE_PACKET_INDEX_2026-07-09.md",
        ],
        "funding_use": "Convert scattered emails, portals, RFIs, SBIR paths, and partner signals into a current, prioritized action board.",
        "claim_boundary": "A lane is traction only if it has a source-backed signal; it is not a customer commitment, agency approval, award, or investment.",
        "human_gate": "Human sends replies, books meetings, signs certifications, and decides go/no-go.",
    },
    {
        "route_id": "autonomous_quant_safety",
        "audience": "quant_or_ai_risk_reviewer",
        "question": "How can the autonomous ambition be funded without uncontrolled action risk?",
        "answer": "Use the autonomous governance packet and innovation safety protocol to show that research, replay, comparison, and packaging are allowed while live execution and capital actions remain blocked.",
        "first_open": "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
            "docs/KRAKEN_INSTITUTIONAL_ALPHA_GAUNTLET_2026-07-09.md",
            "docs/KRAKEN_PAPER_INNOVATION_CONTROL_ROOM_2026-07-09.md",
        ],
        "funding_use": "Frame quant/autonomy as an evidence engine that can mature toward institutional diligence without claiming live fund readiness.",
        "claim_boundary": "No live-profit, guaranteed-return, hedge-fund-ready, autonomous-trading, or capital-control claim is represented.",
        "human_gate": "Human approval is required before trading, broker action, capital movement, or public performance expansion.",
    },
    {
        "route_id": "commercialization_customer_roi",
        "audience": "pilot_buyer_or_commercialization_reviewer",
        "question": "How does this become customer value without overclaiming savings?",
        "answer": "Use the commercialization packet and proof-to-revenue controls to translate proof artifacts into buyer questions, pilot scopes, and measured value hypotheses.",
        "first_open": "grant_submissions/funding_sprint_20260709/CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/PROOF_STACK_EDGE_INDEX_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        ],
        "funding_use": "Give buyers and investors a sober path from proof to pilot without inventing field-savings numbers.",
        "claim_boundary": "No realized savings, ROI guarantee, production deployment, or customer conversion is claimed.",
        "human_gate": "Human validates buyer identity, pilot scope, pricing, and terms before external commitment.",
    },
    {
        "route_id": "investor_profile_and_terms",
        "audience": "investor_or_profile_reviewer",
        "question": "What should an investor see before a deeper call?",
        "answer": "Use the LinkedIn universe packet, venture-studio guardrail, and pitch receipt to show public positioning, terms discipline, and shareable front-door material.",
        "first_open": "grant_submissions/funding_sprint_20260709/LINKEDIN_UNIVERSE_PROFILE_PACKET_2026-07-09.md",
        "supporting_artifacts": [
            "grant_submissions/funding_sprint_20260709/VENTURE_STUDIO_TERMS_GUARDRAIL_PACKET_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/PITCH_DECK_SEND_RECEIPT_2026-07-09.md",
            "grant_submissions/funding_sprint_20260709/REVIEWER_DECISION_BRIEF_2026-07-09.md",
        ],
        "funding_use": "Keep the investor story coherent while avoiding rushed equity, paid pitch traps, or unsupported claims.",
        "claim_boundary": "No investment, partnership, valuation, or term acceptance is represented by this route.",
        "human_gate": "Human approves any deck send, investor reply, term sheet, equity grant, or paid program.",
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


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


def build_routes() -> list[dict[str, Any]]:
    rows = []
    for index, route in enumerate(ROUTES, start=1):
        enriched = dict(route)
        artifacts = [route["first_open"], *route["supporting_artifacts"]]
        enriched["index"] = index
        enriched["artifact_status"] = artifact_status(artifacts)
        enriched["missing_artifact_count"] = sum(1 for item in enriched["artifact_status"] if not item["present"])
        enriched["external_send_allowed_without_human"] = False
        enriched["final_action_allowed_without_human"] = False
        enriched["route_sha256"] = hashlib.sha256(
            json.dumps(enriched, sort_keys=True).encode("utf-8")
        ).hexdigest()
        rows.append(enriched)
    return rows


def build_payload() -> dict[str, Any]:
    decision = read_json(DECISION_JSON)
    qa = read_json(QA_JSON)
    ip = read_json(IP_JSON)
    federal = read_json(FEDERAL_JSON)
    agency = read_json(AGENCY_JSON)
    key_firewall = read_json(KEY_FIREWALL_JSON)
    traction = read_json(TRACTION_JSON)
    gate = read_json(REVIEWER_GATE_JSON)

    routes = build_routes()
    missing_artifacts = sum(row["missing_artifact_count"] for row in routes)

    gate_clear = (
        bool(gate.get("reviewer_gate_clear"))
        and int(gate["summary"]["unsafe_secret_count"]) == 0
        and int(gate["summary"]["unsafe_claim_count"]) == 0
    )
    all_final_actions_blocked = bool(decision["summary"]["all_final_actions_blocked_without_human"])
    key_firewall_ready = (
        key_firewall.get("status") == "KEY_FIREWALL_READY_HUMAN_GATED"
        and int(key_firewall["summary"]["lamascout_inline_credential_hit_count"]) == 0
        and bool(key_firewall["summary"]["raw_credential_values_stored"]) is False
    )
    ip_bound = (
        ip.get("status") == "IP_COUNSEL_DILIGENCE_READY_HUMAN_COUNSEL_REQUIRED"
        and bool(ip["summary"]["legal_advice_claimed"]) is False
        and bool(ip["summary"]["patent_grant_claimed"]) is False
        and bool(ip["summary"]["clearance_to_operate_claimed"]) is False
    )
    agency_bound = (
        federal.get("status") == "FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED"
        and agency.get("status") == "AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED"
        and bool(federal["summary"]["final_submission_allowed_without_human"]) is False
        and bool(agency["summary"]["portal_action_allowed_without_human"]) is False
    )
    route_ready = (
        gate_clear
        and all_final_actions_blocked
        and key_firewall_ready
        and ip_bound
        and agency_bound
        and missing_artifacts == 0
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "reviewer_investor_fast_lane_router_v1",
        "status": "FAST_LANE_ROUTER_READY_HUMAN_SHARE_REQUIRED" if route_ready else "FAST_LANE_ROUTER_BLOCKED",
        "purpose": "Give reviewers, investors, counsel, and agency contacts a one-page route map from question to evidence, while keeping legal, agency, account, trading, and capital gates human-controlled.",
        "summary": {
            "route_count": len(routes),
            "missing_artifact_count": missing_artifacts,
            "decision_lane_count": int(decision["summary"]["lane_count"]),
            "top_ready_lane_count": int(decision["summary"]["top_ready_lane_count"]),
            "urgent_lane_count": int(decision["summary"]["urgent_lane_count"]),
            "traction_lane_count": int(traction["summary"]["lane_count"]),
            "qa_count": int(qa["summary"]["qa_count"]),
            "ip_invention_family_count": int(ip["summary"]["invention_family_count"]),
            "agency_activation_item_count": int(agency["summary"]["activation_item_count"]),
            "agency_blocked_item_count": int(agency["summary"]["blocked_item_count"]),
            "key_firewall_status": key_firewall.get("status", ""),
            "lamascout_active_source_count": int(key_firewall["summary"]["lamascout_active_source_count"]),
            "key_registry_present_slots": int(key_firewall["summary"]["registry_present_key_slots"]),
            "key_registry_total_slots": int(key_firewall["summary"]["registry_total_key_slots"]),
            "reviewer_gate_clear": gate_clear,
            "key_firewall_ready": key_firewall_ready,
            "ip_boundary_ready": ip_bound,
            "agency_protocol_ready": agency_bound,
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "legal_filing_allowed_without_human": False,
            "social_posting_allowed_without_human": False,
            "ad_spend_allowed_without_human": False,
            "live_trading_allowed": False,
            "capital_movement_allowed": False,
            "unsafe_secret_count": int(gate["summary"]["unsafe_secret_count"]),
            "unsafe_claim_count": int(gate["summary"]["unsafe_claim_count"]),
        },
        "routes": routes,
        "share_rules": {
            "share_front_door_only_until_human_approves_scope": True,
            "exclude_credentials_and_meeting_access": True,
            "exclude_unreviewed_claim_charts": True,
            "exclude_private_account_material": True,
            "require_human_approval_before_external_send": True,
        },
        "source_ledgers": {
            "decision": rel(DECISION_JSON),
            "qa": rel(QA_JSON),
            "ip": rel(IP_JSON),
            "federal": rel(FEDERAL_JSON),
            "agency": rel(AGENCY_JSON),
            "key_firewall": rel(KEY_FIREWALL_JSON),
            "traction": rel(TRACTION_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["fast_lane_router_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Reviewer Investor Fast-Lane Router - 2026-07-09",
        "",
        f"Purpose: {payload['purpose']}",
        "",
        "This router is a navigation layer. It does not authorize external sends, portal submissions, filings, certifications, public posts, term acceptance, trading, or capital movement.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Routes: `{summary['route_count']}`",
        f"- Missing artifacts: `{summary['missing_artifact_count']}`",
        f"- Decision lanes: `{summary['decision_lane_count']}`",
        f"- Top-ready lanes: `{summary['top_ready_lane_count']}`",
        f"- Urgent lanes: `{summary['urgent_lane_count']}`",
        f"- Traction lanes: `{summary['traction_lane_count']}`",
        f"- Q&A rows: `{summary['qa_count']}`",
        f"- IP invention families: `{summary['ip_invention_family_count']}`",
        f"- Agency activation items: `{summary['agency_activation_item_count']}`",
        f"- Agency blocked items: `{summary['agency_blocked_item_count']}`",
        f"- Key firewall status: `{summary['key_firewall_status']}`",
        f"- LumaScout active sources: `{summary['lamascout_active_source_count']}`",
        f"- Key registry present slots: `{summary['key_registry_present_slots']}/{summary['key_registry_total_slots']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Key firewall ready: `{str(summary['key_firewall_ready']).lower()}`",
        f"- IP boundary ready: `{str(summary['ip_boundary_ready']).lower()}`",
        f"- Agency protocol ready: `{str(summary['agency_protocol_ready']).lower()}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Legal filing without human: `{str(summary['legal_filing_allowed_without_human']).lower()}`",
        f"- Social posting without human: `{str(summary['social_posting_allowed_without_human']).lower()}`",
        f"- Ad spend without human: `{str(summary['ad_spend_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Capital movement allowed: `{str(summary['capital_movement_allowed']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Router SHA-256: `{payload['fast_lane_router_sha256']}`",
        "",
        "## Routes",
        "",
    ]
    for route in payload["routes"]:
        lines.extend(
            [
                f"### {route['index']}. {route['route_id']}",
                "",
                f"- Audience: `{route['audience']}`",
                f"- Reviewer question: {route['question']}",
                f"- Answer: {route['answer']}",
                f"- First open: `{route['first_open']}`",
                f"- Funding use: {route['funding_use']}",
                f"- Claim boundary: {route['claim_boundary']}",
                f"- Human gate: {route['human_gate']}",
                f"- External send without human: `{str(route['external_send_allowed_without_human']).lower()}`",
                f"- Final action without human: `{str(route['final_action_allowed_without_human']).lower()}`",
                f"- Missing artifacts: `{route['missing_artifact_count']}`",
                f"- Route SHA-256: `{route['route_sha256']}`",
                "",
                "Artifacts:",
            ]
        )
        for artifact in route["artifact_status"]:
            state = "present" if artifact["present"] else "missing"
            lines.append(f"- `{state}` `{artifact['path']}` sha256=`{artifact['sha256']}`")
        lines.append("")
    lines.extend(["## Share Rules", ""])
    for key, value in payload["share_rules"].items():
        lines.append(f"- {key}: `{str(value).lower()}`")
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
        raise SystemExit(f"Refusing to write sensitive fast-lane router markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "routes": payload["summary"]["route_count"],
                "missing_artifacts": payload["summary"]["missing_artifact_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
