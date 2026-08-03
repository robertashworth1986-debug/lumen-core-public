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

OUT_JSON = OUT_OPS / "funding_reviewer_zero_friction_pack_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "funding_reviewer_zero_friction_pack.json"
OUT_MD = SPRINT_DIR / "FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md"

SOURCE_LEDGERS = {
    "reviewer_decision": OUT_OPS / "reviewer_decision_brief_latest.json",
    "sam_rush": OUT_OPS / "sam_rush_submission_board_latest.json",
    "technical_gov": OUT_OPS / "technical_gov_reviewer_approval_stack_latest.json",
    "ip_counsel": OUT_OPS / "ip_counsel_diligence_packet_latest.json",
    "quant_governance": OUT_OPS / "autonomous_quant_governance_packet_latest.json",
    "proof_to_pilot": OUT_OPS / "proof_to_pilot_control_room_latest.json",
    "live_value": OUT_OPS / "live_proof_value_meter_latest.json",
    "authority": OUT_OPS / "submission_authority_matrix_latest.json",
    "reviewer_gate": OUT_OPS / "funding_sprint_reviewer_gate_latest.json",
    "data_room": OUT_OPS / "data_room_manifest_latest.json",
}

SENSITIVE_MARKERS = [
    "password",
    "zoom.us",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

DEFENSIBLE_CLAIMS = [
    {
        "claim_id": "measured_source_proof_stack",
        "claim": "LumenCore has a measured-source proof stack with hash-backed artifacts, reviewer gates, and source-conditioned evidence records.",
        "evidence": [
            "data_room",
            "reviewer_gate",
            "technical_gov",
        ],
        "boundary": "This is proof-stack readiness, not agency validation or customer production deployment.",
    },
    {
        "claim_id": "agency_submission_readiness",
        "claim": "The current federal traction board has submit-ready, human-gated lanes for FHWA, NASA, ERDC, and DOJ/BOP.",
        "evidence": [
            "sam_rush",
            "authority",
        ],
        "boundary": "Final submit, pricing, reps/certs, and portal upload remain human-controlled.",
    },
    {
        "claim_id": "commercial_pilot_route",
        "claim": "The proof-to-pilot layer can support manual paid-evaluation scoping and buyer-authorized field replay requests.",
        "evidence": [
            "proof_to_pilot",
            "live_value",
        ],
        "boundary": "No realized savings, guaranteed ROI, field validation, or bulk outreach is claimed.",
    },
    {
        "claim_id": "ip_claim_boundary",
        "claim": "The IP lane is mapped into invention families, counsel questions, public disclosure rules, and hold-back boundaries.",
        "evidence": [
            "ip_counsel",
        ],
        "boundary": "No patent grant, patentability, legal advice, clearance to operate, or safe deadline status is claimed.",
    },
    {
        "claim_id": "autonomous_quant_safety",
        "claim": "Autonomous quant work is restricted to replay, paper evaluation, opportunity monitoring, and proof factory modes.",
        "evidence": [
            "quant_governance",
            "authority",
        ],
        "boundary": "No live orders, capital movement, external system action, or public performance claim is authorized.",
    },
]

REVIEWER_DECISION_ROUTES = [
    {
        "route_id": "agency_fast_submit",
        "name": "Agency fast-submit route",
        "reviewer_question": "Which official opportunity can be reviewed first with the least ambiguity?",
        "answer": "Start with NASA RFI for speed, FHWA TSMO for best fit, ERDC CSO for platform-modernization upside, and DOJ/BOP only after pricing/compliance review.",
        "first_artifacts": [
            "SAM_RUSH_SUBMISSION_BOARD_2026-07-10.md",
            "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md",
            "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md",
            "ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md",
        ],
        "human_next_action": "Open the official notice, check attachments/amendments, approve the exact response package, then handle final submit/send.",
    },
    {
        "route_id": "technical_validation",
        "name": "Technical validation route",
        "reviewer_question": "What would a serious technical reviewer evaluate?",
        "answer": "Evaluate source lineage, baseline comparison, holdout/replay discipline, claim boundaries, and whether a buyer-authorized field replay can be designed.",
        "first_artifacts": [
            "TECHNICAL_GOV_REVIEWER_APPROVAL_STACK_2026-07-09.md",
            "PROOF_STACK_EDGE_INDEX_2026-07-09.md",
            "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
        ],
        "human_next_action": "Route only bounded technical packets to labs/agencies or qualified reviewers; hold back enabling IP details until counsel review.",
    },
    {
        "route_id": "ip_defense",
        "name": "IP defense route",
        "reviewer_question": "Is the invention universe protected enough to discuss?",
        "answer": "Discuss only reviewer-safe invention families and proof boundaries; counsel must control claim charts, filings, deadlines, and public disclosure expansion.",
        "first_artifacts": [
            "IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
            "IP_PATENT_CLAIM_BOUNDARY_REGISTER_2026-07-09.md",
        ],
        "human_next_action": "Have counsel verify official filing status, new matter, public disclosure timeline, and approved wording.",
    },
    {
        "route_id": "paid_pilot",
        "name": "Paid pilot route",
        "reviewer_question": "How does this become revenue without overclaiming?",
        "answer": "Offer paid technical evaluation or buyer-authorized pilot scoping where the buyer supplies mission metric context and replay constraints.",
        "first_artifacts": [
            "CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
            "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        ],
        "human_next_action": "Select a narrow buyer problem, pre-register holdout windows, and quote only after data scope and success criteria are approved.",
    },
    {
        "route_id": "autonomous_research",
        "name": "Autonomous research route",
        "reviewer_question": "Can the system keep innovating without creating unmanaged risk?",
        "answer": "Yes for internal replay, paper evaluation, source cataloging, opportunity triage, and artifact generation; no for trading, legal filing, final submission, or external commitments.",
        "first_artifacts": [
            "AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
            "AUTONOMOUS_QUANT_INNOVATION_SAFETY_PROTOCOL_2026-07-09.md",
            "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        ],
        "human_next_action": "Keep autonomous work inside replay/proof lanes and require explicit human approval for anything that affects money, legal status, or external commitments.",
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


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def ledger_statuses() -> dict[str, dict[str, Any]]:
    statuses: dict[str, dict[str, Any]] = {}
    for ledger_id, path in SOURCE_LEDGERS.items():
        statuses[ledger_id] = {
            "path": rel(path),
            "present": path.exists(),
            "bytes": path.stat().st_size if path.exists() else 0,
            "sha256": sha256_file(path) if path.exists() else "",
        }
    return statuses


def linked_claim_status(claim: dict[str, Any], ledgers: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = dict(claim)
    row["evidence_present"] = all(ledgers.get(evidence_id, {}).get("present") for evidence_id in row["evidence"])
    row["claim_allowed_for_review"] = row["evidence_present"]
    row["claim_sha256"] = stable_sha256(row)
    return row


def build_payload() -> dict[str, Any]:
    ledgers = ledger_statuses()
    loaded = {ledger_id: read_json(SOURCE_LEDGERS[ledger_id]) for ledger_id in SOURCE_LEDGERS}

    data_room_summary = loaded["data_room"].get("summary", {})
    reviewer_summary = loaded["reviewer_decision"].get("summary", {})
    sam_summary = loaded["sam_rush"].get("summary", {})
    gate_summary = loaded["reviewer_gate"].get("summary", {})
    authority_summary = loaded["authority"].get("summary", {})
    quant_human_gate = loaded["quant_governance"].get("human_gate", {})
    pilot_summary = loaded["proof_to_pilot"].get("summary", {})
    live_value_gate = loaded["live_value"].get("value_gate", {}).get("safe_claim", {})
    ip_summary = loaded["ip_counsel"].get("summary", {})

    claims = [linked_claim_status(claim, ledgers) for claim in DEFENSIBLE_CLAIMS]
    all_ledgers_present = all(row["present"] for row in ledgers.values())
    all_claims_ready = all(row["claim_allowed_for_review"] for row in claims)
    final_actions_blocked = (
        bool(authority_summary.get("all_final_actions_blocked_without_human"))
        and bool(gate_summary.get("unsafe_secret_count", 1) == 0)
        and bool(gate_summary.get("unsafe_claim_count", 1) == 0)
        and loaded["sam_rush"].get("summary", {}).get("final_submission_allowed_without_human") is False
        and quant_human_gate.get("order_placement_allowed_without_human") is False
    )

    payload = {
        "schema": "funding_reviewer_zero_friction_pack_v1",
        "generated_utc": now_utc(),
        "status": "FUNDING_REVIEWER_ZERO_FRICTION_PACK_READY_HUMAN_ACTION_REQUIRED"
        if all_ledgers_present and all_claims_ready and final_actions_blocked
        else "FUNDING_REVIEWER_ZERO_FRICTION_PACK_BLOCKED",
        "one_screen_answer": {
            "what_to_fund": "A proof-to-pilot validation layer for AI/data systems that turns noisy live data, replay evidence, and governance receipts into agency-reviewable decisions.",
            "why_now": "SAM renewal is submitted, the current federal rush board has four human-gated submit-ready lanes, and the data room now ties agency, IP, quant safety, and pilot evidence into reviewer packets.",
            "why_safe": "The stack is explicit about what is ready, what is only estimated, and what remains blocked until human/counsel/agency review.",
            "best_first_action": "Approve one official response path first: NASA RFI for speed, FHWA TSMO for best technical fit, or ERDC CSO for platform-modernization upside.",
        },
        "summary": {
            "source_ledger_count": len(ledgers),
            "source_ledgers_present": all_ledgers_present,
            "defensible_claim_count": len(claims),
            "defensible_claims_ready": all_claims_ready,
            "decision_route_count": len(REVIEWER_DECISION_ROUTES),
            "sam_submit_ready_human_gate_count": int(sam_summary.get("submit_ready_human_gate_count", 0) or 0),
            "data_room_markdown_count": int(data_room_summary.get("manifested_markdown_count", 0) or 0),
            "data_room_control_artifact_count": int(data_room_summary.get("control_artifact_count", 0) or 0),
            "reviewer_lane_count": int(reviewer_summary.get("lane_count", 0) or 0),
            "top_ready_reviewer_lane_count": int(reviewer_summary.get("top_ready_lane_count", 0) or 0),
            "paid_evaluation_offer_allowed": bool(pilot_summary.get("paid_evaluation_offer_allowed")),
            "manual_reviewed_outreach_allowed": bool(pilot_summary.get("manual_reviewed_outreach_allowed")),
            "estimated_value_signal_allowed": bool(live_value_gate.get("estimated_value_signal_allowed")),
            "realized_savings_claim_allowed": bool(live_value_gate.get("realized_customer_or_government_savings_allowed")),
            "patent_grant_claimed": bool(ip_summary.get("patent_grant_claimed")),
            "legal_advice_claimed": bool(ip_summary.get("legal_advice_claimed")),
            "reviewer_packaging_gate_clear": bool(
                gate_summary.get("packaging_checks_clear")
            )
            and int(gate_summary.get("unsafe_secret_count", 0) or 0) == 0
            and int(gate_summary.get("unsafe_claim_count", 0) or 0) == 0,
            "submission_argument_gate_clear": bool(
                loaded["reviewer_gate"].get("reviewer_gate_clear")
            ),
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count", 0) or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count", 0) or 0),
            "all_final_actions_blocked_without_human": final_actions_blocked,
            "external_send_allowed_without_human": False,
            "portal_submission_allowed_without_human": False,
            "pricing_allowed_without_human": False,
            "legal_or_ip_action_allowed_without_human": False,
            "live_trading_allowed": False,
            "capital_movement_allowed_without_human": False,
        },
        "defensible_claims": claims,
        "reviewer_decision_routes": REVIEWER_DECISION_ROUTES,
        "source_ledgers": ledgers,
        "blocked_until_human": [
            "final SAM.gov or agency portal submit",
            "email send to agency, investor, reviewer, or partner",
            "pricing or fixed quote",
            "legal certification, signature, or reps/certs",
            "patent filing, claim expansion, or public enabling disclosure",
            "live order placement, capital movement, or brokerage runtime escalation",
            "claim of agency validation, patent grant, realized savings, customer ROI, or award certainty",
        ],
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["zero_friction_pack_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    answer = payload["one_screen_answer"]
    lines = [
        "# Funding Reviewer Zero-Friction Pack - 2026-07-10",
        "",
        "Purpose: make the LumenCore funding decision easy to review by tying the proof stack, SAM lanes, IP boundaries, quant safety, and human gates into one control artifact.",
        "",
        "This packet is decision support only. It does not authorize external sends, final portal submissions, pricing, certifications, legal filings, live trading, or capital movement.",
        "",
        "## One-Screen Answer",
        "",
        f"- What to fund: {answer['what_to_fund']}",
        f"- Why now: {answer['why_now']}",
        f"- Why safe: {answer['why_safe']}",
        f"- Best first action: {answer['best_first_action']}",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Source ledgers: `{summary['source_ledger_count']}`",
        f"- Source ledgers present: `{str(summary['source_ledgers_present']).lower()}`",
        f"- Defensible claims: `{summary['defensible_claim_count']}`",
        f"- Defensible claims ready: `{str(summary['defensible_claims_ready']).lower()}`",
        f"- Decision routes: `{summary['decision_route_count']}`",
        f"- SAM submit-ready human-gated lanes: `{summary['sam_submit_ready_human_gate_count']}`",
        f"- Data-room Markdown artifacts: `{summary['data_room_markdown_count']}`",
        f"- Data-room control artifacts: `{summary['data_room_control_artifact_count']}`",
        f"- Reviewer lanes: `{summary['reviewer_lane_count']}`",
        f"- Top-ready reviewer lanes: `{summary['top_ready_reviewer_lane_count']}`",
        f"- Paid evaluation offer allowed: `{str(summary['paid_evaluation_offer_allowed']).lower()}`",
        f"- Manual reviewed outreach allowed: `{str(summary['manual_reviewed_outreach_allowed']).lower()}`",
        f"- Estimated value signal allowed: `{str(summary['estimated_value_signal_allowed']).lower()}`",
        f"- Realized savings claim allowed: `{str(summary['realized_savings_claim_allowed']).lower()}`",
        f"- Patent grant claimed: `{str(summary['patent_grant_claimed']).lower()}`",
        f"- Legal advice claimed: `{str(summary['legal_advice_claimed']).lower()}`",
        f"- Reviewer packaging gate clear: `{str(summary['reviewer_packaging_gate_clear']).lower()}`",
        f"- Submission argument gate clear: `{str(summary['submission_argument_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Portal submission without human: `{str(summary['portal_submission_allowed_without_human']).lower()}`",
        f"- Pricing without human: `{str(summary['pricing_allowed_without_human']).lower()}`",
        f"- Legal/IP action without human: `{str(summary['legal_or_ip_action_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Capital movement without human: `{str(summary['capital_movement_allowed_without_human']).lower()}`",
        f"- Pack SHA-256: `{payload['zero_friction_pack_sha256']}`",
        "",
        "## Defensible Claims",
        "",
    ]
    for claim in payload["defensible_claims"]:
        lines.extend(
            [
                f"### {claim['claim_id']}",
                "",
                f"- Claim: {claim['claim']}",
                f"- Evidence present: `{str(claim['evidence_present']).lower()}`",
                f"- Claim allowed for review: `{str(claim['claim_allowed_for_review']).lower()}`",
                f"- Boundary: {claim['boundary']}",
                "- Evidence ledgers:",
            ]
        )
        for evidence_id in claim["evidence"]:
            lines.append(f"  - `{evidence_id}`")
        lines.extend([f"- Claim SHA-256: `{claim['claim_sha256']}`", ""])

    lines.extend(["## Reviewer Decision Routes", ""])
    for route in payload["reviewer_decision_routes"]:
        lines.extend(
            [
                f"### {route['name']}",
                "",
                f"- Route ID: `{route['route_id']}`",
                f"- Reviewer question: {route['reviewer_question']}",
                f"- Answer: {route['answer']}",
                "- First artifacts:",
            ]
        )
        for artifact in route["first_artifacts"]:
            lines.append(f"  - `{artifact}`")
        lines.extend([f"- Human next action: {route['human_next_action']}", ""])

    lines.extend(["## Blocked Until Human", ""])
    for item in payload["blocked_until_human"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Source Ledgers", ""])
    for ledger_id, row in payload["source_ledgers"].items():
        lines.append(
            f"- `{ledger_id}` `{row['path']}` present=`{str(row['present']).lower()}` bytes=`{row['bytes']}` sha256=`{row['sha256']}`"
        )
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public zero-friction markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_ledgers": payload["summary"]["source_ledger_count"],
                "decision_routes": payload["summary"]["decision_route_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
