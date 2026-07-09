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
REVIEWER_DECISION_JSON = OUT_OPS / "reviewer_decision_brief_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
DATA_ROOM_JSON = OUT_OPS / "data_room_manifest_latest.json"
MEASURED_SOURCE_JSON = OUT_OPS / "measured_source_evidence_register_latest.json"
EVTIT_JSON = OUT_OPS / "evtit_technical_sprint_scope_packet_latest.json"
FEDERAL_PROTOCOL_JSON = OUT_OPS / "federal_submission_protocol_packet_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"

OUT_JSON = OUT_OPS / "customer_commercialization_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "customer_commercialization_packet.json"
OUT_MD = SPRINT_DIR / "CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md"

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

CUSTOMER_SEGMENTS = [
    {
        "segment_id": "agency_program_reviewer",
        "name": "Agency program or SBIR reviewer",
        "buyer_role": "Program lead, technical evaluator, contracting specialist, or SBIR topic reviewer",
        "job_to_be_done": "Decide whether LumenCore is credible enough to fund, invite, or route to a pilot path.",
        "pain": "Advanced claims arrive faster than a reviewer can verify source, boundary, and repeatability.",
        "proof_needed": "Source-backed packet, official-opportunity fit, human authority gates, and a clear no-final-action boundary.",
        "first_offer": "Submission preparation and reviewer proof packet",
        "decision_trigger": "A live opportunity, RFI, SBIR topic, BAA call, or agency meeting creates a deadline.",
    },
    {
        "segment_id": "technical_validation_owner",
        "name": "Technical validation owner",
        "buyer_role": "Data owner, lab lead, platform engineer, or applied AI reviewer",
        "job_to_be_done": "Convert a complex model or proof stack into a repeatable validation receipt.",
        "pain": "Manual review is slow when source freshness, baselines, metrics, and replay receipts are scattered.",
        "proof_needed": "Measured-source register, replay runner scope, baseline lock, and hash-backed receipt plan.",
        "first_offer": "Paid evidence review and replay-scope sprint",
        "decision_trigger": "A partner needs to know what data, metric, and baseline would make a pilot defensible.",
    },
    {
        "segment_id": "venture_builder_or_investor",
        "name": "Venture builder or investor",
        "buyer_role": "Venture studio partner, early investor, accelerator reviewer, or technical diligence lead",
        "job_to_be_done": "See whether the company can turn evidence into funded work without unsupported promises.",
        "pain": "Diligence slows down when technical excitement is not paired with a buyer path and claim controls.",
        "proof_needed": "Customer segments, productized offers, traction lanes, data-room map, and blocked-claim policy.",
        "first_offer": "30-day commercialization and technical sprint",
        "decision_trigger": "A diligence call asks for the business model, first customer, and near-term revenue motion.",
    },
    {
        "segment_id": "pilot_partner",
        "name": "Pilot partner",
        "buyer_role": "University lab, enterprise innovation team, infrastructure operator, or qualified prime",
        "job_to_be_done": "Start a bounded study without exposing private data or accepting broad terms too early.",
        "pain": "Partners need the work scoped before they can share data, assign reviewers, or commit budget.",
        "proof_needed": "Pilot intake path, human approvals, data boundary, acceptance standard, and review artifacts.",
        "first_offer": "Pilot intake and acceptance-standard design",
        "decision_trigger": "The partner has a problem area and needs a controlled way to test fit.",
    },
    {
        "segment_id": "ip_or_compliance_reviewer",
        "name": "IP or compliance reviewer",
        "buyer_role": "Patent counsel, compliance lead, or governance reviewer",
        "job_to_be_done": "Separate defensible claims from language that needs counsel, agency, or security review.",
        "pain": "Public materials can drift into overclaiming unless every claim has an owner and evidence boundary.",
        "proof_needed": "IP diligence packet, federal protocol packet, authority matrix, and public-safe data-room manifest.",
        "first_offer": "Claim-boundary and diligence-room cleanup",
        "decision_trigger": "A filing, investor review, public packet, or agency account step approaches.",
    },
]

OFFERS = [
    {
        "offer_id": "reviewer_proof_sprint",
        "name": "Reviewer proof sprint",
        "buyer": "Agency, SBIR, investor, or partner reviewer",
        "duration": "5 to 10 business days",
        "deliverable": "Proof-card index, source register, decision brief, reviewer Q&A, and claim-boundary map.",
        "price_posture": "Quoted after scope; no fixed price promise in this packet.",
        "success_gate": "Reviewer can answer what is ready, what is blocked, and what decision is being requested.",
    },
    {
        "offer_id": "paid_replay_scope",
        "name": "Paid replay-scope package",
        "buyer": "Technical validation owner or data owner",
        "duration": "10 to 20 business days",
        "deliverable": "Baseline, metric, holdout window, data boundary, replay receipt schema, and dry-run report.",
        "price_posture": "Quoted after data and acceptance criteria are reviewed.",
        "success_gate": "Buyer knows what evidence would support a paid validation study.",
    },
    {
        "offer_id": "agency_submission_factory",
        "name": "Agency submission preparation package",
        "buyer": "Founder, prime, partner team, or grant reviewer",
        "duration": "Deadline-driven",
        "deliverable": "Opportunity fit matrix, official-source checklist, technical volume outline, and final-action docket.",
        "price_posture": "Quoted after portal, eligibility, reps/certs, and attachment requirements are verified.",
        "success_gate": "Human has a clean package ready for final portal review and submission authority.",
    },
    {
        "offer_id": "proof_portal_subscription",
        "name": "Proof portal and dashboard subscription",
        "buyer": "Investor, partner, or internal reviewer team",
        "duration": "Monthly or sprint-retainer after a paid setup",
        "deliverable": "Dashboard JSON, proof-room navigation, source freshness, packet refreshes, and evidence receipts.",
        "price_posture": "Post-pilot subscription; not quoted before a buyer-specific scope.",
        "success_gate": "Reviewer has a repeatable portal for source-backed updates and diligence refreshes.",
    },
    {
        "offer_id": "partner_diligence_room",
        "name": "Partner diligence room",
        "buyer": "Qualified prime, venture builder, lab, or strategic partner",
        "duration": "2 to 4 weeks",
        "deliverable": "Data-room manifest, claim controls, technical scope, customer path, and partner-only action list.",
        "price_posture": "Quoted after partner role, data boundary, and deliverable ownership are clear.",
        "success_gate": "Partner can decide whether to intro, team, sponsor, or fund the next scoped sprint.",
    },
]

BUYER_PROOF_CHECKLIST = [
    "Named customer segment and buyer role",
    "Problem tied to a deadline, decision, or reviewer burden",
    "First paid offer with a bounded deliverable",
    "Evidence artifact that proves the packet exists",
    "Human approval gate for send, submit, schedule, terms, and access",
    "No unearned customer result or award language",
    "Source-count and current-measurement posture visible to reviewer",
    "Next decision phrased as a low-friction funded sprint or pilot-scope step",
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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def build_customer_cards() -> list[dict[str, Any]]:
    cards = []
    offers_by_id = {row["offer_id"]: row for row in OFFERS}
    offer_map = {
        "agency_program_reviewer": "agency_submission_factory",
        "technical_validation_owner": "paid_replay_scope",
        "venture_builder_or_investor": "reviewer_proof_sprint",
        "pilot_partner": "partner_diligence_room",
        "ip_or_compliance_reviewer": "partner_diligence_room",
    }
    for priority, segment in enumerate(CUSTOMER_SEGMENTS, start=1):
        offer = offers_by_id[offer_map[segment["segment_id"]]]
        card = {
            "priority": priority,
            "segment_id": segment["segment_id"],
            "name": segment["name"],
            "buyer_role": segment["buyer_role"],
            "job_to_be_done": segment["job_to_be_done"],
            "pain": segment["pain"],
            "proof_needed": segment["proof_needed"],
            "first_offer": segment["first_offer"],
            "mapped_offer_id": offer["offer_id"],
            "mapped_offer_name": offer["name"],
            "decision_trigger": segment["decision_trigger"],
            "human_terms_required": True,
            "external_send_allowed_without_human": False,
            "customer_result_claimed": False,
        }
        card["customer_card_sha256"] = stable_sha256(card)
        cards.append(card)
    return cards


def build_payload() -> dict[str, Any]:
    traction = read_json(TRACTION_JSON)
    decision = read_json(REVIEWER_DECISION_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    data_room = read_json(DATA_ROOM_JSON)
    measured = read_json(MEASURED_SOURCE_JSON)
    evtit = read_json(EVTIT_JSON)
    federal = read_json(FEDERAL_PROTOCOL_JSON)
    authority = read_json(AUTHORITY_JSON)

    gate_summary = as_dict(gate.get("summary"))
    data_summary = as_dict(data_room.get("summary"))
    measured_summary = as_dict(measured.get("summary"))
    traction_summary = as_dict(traction.get("summary"))
    decision_summary = as_dict(decision.get("summary"))
    evtit_summary = as_dict(evtit.get("summary"))
    authority_summary = as_dict(authority.get("summary"))

    reviewer_gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate_summary.get("unsafe_secret_count") or 0) == 0 and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human"))
    customer_cards = build_customer_cards()
    evidence_artifacts = [
        artifact_status(SPRINT_DIR / "REVIEWER_DECISION_BRIEF_2026-07-09.md"),
        artifact_status(SPRINT_DIR / "TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md"),
        artifact_status(SPRINT_DIR / "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md"),
        artifact_status(SPRINT_DIR / "EVTIT_TECHNICAL_SPRINT_SCOPE_PACKET_2026-07-09.md"),
        artifact_status(SPRINT_DIR / "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md"),
        artifact_status(SPRINT_DIR / "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md"),
    ]
    evidence_present = all(row["present"] for row in evidence_artifacts)

    payload = {
        "generated_utc": now_utc(),
        "schema": "customer_commercialization_packet_v1",
        "status": "CUSTOMER_COMMERCIALIZATION_PACKET_READY_HUMAN_TERMS_REQUIRED"
        if reviewer_gate_clear and final_actions_blocked and evidence_present
        else "CUSTOMER_COMMERCIALIZATION_PACKET_BLOCKED",
        "executive_summary": (
            "LumenCore sells proof-to-pilot infrastructure for reviewers who need complex R&D translated into "
            "inspectable, source-backed, human-gated decision material. The first money motion is a paid proof or "
            "replay-scope sprint; the expansion path is pilot support, agency submission preparation, partner "
            "diligence rooms, and eventually recurring proof portal access."
        ),
        "business_model": {
            "first_revenue_motion": "Paid reviewer proof sprint or paid replay-scope package.",
            "second_revenue_motion": "Pilot intake and partner diligence room for a named validation path.",
            "third_revenue_motion": "Recurring proof portal, dashboard, and packet refresh access after setup.",
            "funding_motion": "SBIR, RFI/BAA response, grants, in-kind engineering, venture diligence, and strategic partner routes.",
            "pricing_rule": "Human quotes only after scope, data boundary, authority, and deliverables are reviewed.",
        },
        "summary": {
            "customer_segment_count": len(CUSTOMER_SEGMENTS),
            "offer_count": len(OFFERS),
            "buyer_proof_check_count": len(BUYER_PROOF_CHECKLIST),
            "traction_lane_count": int(traction_summary.get("lane_count") or 0),
            "decision_lane_count": int(decision_summary.get("lane_count") or 0),
            "data_room_markdown_count": int(data_summary.get("manifested_markdown_count") or 0),
            "data_room_control_artifact_count": int(data_summary.get("control_artifact_count") or 0),
            "evtit_workstream_count": int(evtit_summary.get("workstream_count") or 0),
            "registry_enabled_sources": int(measured_summary.get("registry_enabled_sources") or 0),
            "registry_measured_sources": int(measured_summary.get("registry_measured_sources") or 0),
            "current_probe_measured_sources": int(measured_summary.get("current_probe_measured_sources") or 0),
            "reviewer_gate_clear": reviewer_gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "federal_protocol_status": federal.get("status", ""),
            "authority_status": authority.get("status", ""),
            "all_final_actions_blocked_without_human": final_actions_blocked,
            "evidence_artifacts_present": evidence_present,
            "human_terms_required": True,
            "external_send_allowed_without_human": False,
            "schedule_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "pricing_commitment_allowed_without_human": False,
            "private_file_share_allowed_without_human": False,
            "partnership_claimed": False,
            "investment_claimed": False,
            "award_claimed": False,
            "paying_customer_claimed": False,
            "customer_result_claimed": False,
            "production_deployment_claimed": False,
        },
        "customer_cards": customer_cards,
        "offers": OFFERS,
        "buyer_proof_checklist": BUYER_PROOF_CHECKLIST,
        "fastest_funding_path": [
            "Use the executive summary to anchor the buyer and business model.",
            "Offer a paid reviewer proof sprint or replay-scope package as the first concrete purchase.",
            "Route agencies through official-source submission preparation with final action blocked until human approval.",
            "Route investors and venture builders to the 30-day technical and commercialization sprint.",
            "Route pilot partners to a data-boundary and acceptance-standard discussion before any private data exchange.",
        ],
        "human_gate": {
            "send_email_allowed_without_human": False,
            "schedule_meeting_allowed_without_human": False,
            "accept_terms_allowed_without_human": False,
            "quote_price_allowed_without_human": False,
            "share_private_files_allowed_without_human": False,
            "submit_portal_allowed_without_human": False,
            "rule": "This packet prepares the business-side answer. Robert approves any send, schedule, terms, price, file share, or portal action.",
        },
        "evidence_artifacts": evidence_artifacts,
        "source_ledgers": {
            "traction": rel(TRACTION_JSON),
            "reviewer_decision": rel(REVIEWER_DECISION_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
            "data_room": rel(DATA_ROOM_JSON),
            "measured_source": rel(MEASURED_SOURCE_JSON),
            "evtit_scope": rel(EVTIT_JSON),
            "federal_protocol": rel(FEDERAL_PROTOCOL_JSON),
            "authority": rel(AUTHORITY_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["customer_commercialization_sha256"] = stable_sha256(
        {
            "executive_summary": payload["executive_summary"],
            "business_model": payload["business_model"],
            "summary": payload["summary"],
            "customer_cards": payload["customer_cards"],
            "offers": payload["offers"],
            "buyer_proof_checklist": payload["buyer_proof_checklist"],
            "human_gate": payload["human_gate"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Customer Commercialization Packet - 2026-07-09",
        "",
        "Purpose: answer the business-side reviewer question: who buys LumenCore, why they care now, what they can buy first, and what proof makes the decision easier.",
        "",
        "This packet prepares business positioning only. It does not send outreach, schedule a meeting, quote price, accept terms, share private files, submit a portal action, or claim a customer result.",
        "",
        "## Executive Summary",
        "",
        payload["executive_summary"],
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Customer segments: `{summary['customer_segment_count']}`",
        f"- Productized offers: `{summary['offer_count']}`",
        f"- Buyer proof checks: `{summary['buyer_proof_check_count']}`",
        f"- Traction lanes: `{summary['traction_lane_count']}`",
        f"- Decision lanes: `{summary['decision_lane_count']}`",
        f"- Data-room Markdown artifacts: `{summary['data_room_markdown_count']}`",
        f"- Data-room machine controls: `{summary['data_room_control_artifact_count']}`",
        f"- EVTit workstreams: `{summary['evtit_workstream_count']}`",
        f"- Registry enabled sources: `{summary['registry_enabled_sources']}`",
        f"- Registry measured sources: `{summary['registry_measured_sources']}`",
        f"- Current probe measured sources: `{summary['current_probe_measured_sources']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Human terms required: `{str(summary['human_terms_required']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Pricing commitment without human: `{str(summary['pricing_commitment_allowed_without_human']).lower()}`",
        f"- Partnership claimed: `{str(summary['partnership_claimed']).lower()}`",
        f"- Investment claimed: `{str(summary['investment_claimed']).lower()}`",
        f"- Award claimed: `{str(summary['award_claimed']).lower()}`",
        f"- Paying customer claimed: `{str(summary['paying_customer_claimed']).lower()}`",
        f"- Customer result claimed: `{str(summary['customer_result_claimed']).lower()}`",
        f"- Production deployment claimed: `{str(summary['production_deployment_claimed']).lower()}`",
        f"- Packet SHA-256: `{payload['customer_commercialization_sha256']}`",
        "",
        "## Business Model",
        "",
    ]
    for key, value in payload["business_model"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Customer Segments", ""])
    for card in payload["customer_cards"]:
        lines.extend(
            [
                f"### {card['priority']}. {card['name']}",
                "",
                f"- Segment ID: `{card['segment_id']}`",
                f"- Buyer role: {card['buyer_role']}",
                f"- Job to be done: {card['job_to_be_done']}",
                f"- Pain: {card['pain']}",
                f"- Proof needed: {card['proof_needed']}",
                f"- First offer: {card['first_offer']}",
                f"- Decision trigger: {card['decision_trigger']}",
                f"- External send without human: `{str(card['external_send_allowed_without_human']).lower()}`",
                f"- Customer result claimed: `{str(card['customer_result_claimed']).lower()}`",
                f"- Card SHA-256: `{card['customer_card_sha256']}`",
                "",
            ]
        )

    lines.extend(["## Productized Offers", ""])
    for offer in payload["offers"]:
        lines.extend(
            [
                f"### {offer['name']}",
                "",
                f"- Offer ID: `{offer['offer_id']}`",
                f"- Buyer: {offer['buyer']}",
                f"- Duration: {offer['duration']}",
                f"- Deliverable: {offer['deliverable']}",
                f"- Price posture: {offer['price_posture']}",
                f"- Success gate: {offer['success_gate']}",
                "",
            ]
        )

    lines.extend(["## Buyer Proof Checklist", ""])
    for item in payload["buyer_proof_checklist"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Fastest Funding Path", ""])
    for item in payload["fastest_funding_path"]:
        lines.append(f"- {item}")

    lines.extend(["", "## Evidence Artifacts", ""])
    for row in payload["evidence_artifacts"]:
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
        raise SystemExit(f"Refusing to write sensitive public commercialization markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "segments": payload["summary"]["customer_segment_count"],
                "offers": payload["summary"]["offer_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"].endswith("HUMAN_TERMS_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
