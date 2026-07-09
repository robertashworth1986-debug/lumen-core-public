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

CUSTOMER_JSON = OUT_OPS / "customer_commercialization_packet_latest.json"
EVTIT_JSON = OUT_OPS / "evtit_technical_sprint_scope_packet_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
IP_JSON = OUT_OPS / "ip_counsel_diligence_packet_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
DATA_ROOM_JSON = OUT_OPS / "data_room_manifest_latest.json"

OUT_JSON = OUT_OPS / "venture_studio_terms_guardrail_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "venture_studio_terms_guardrail_packet.json"
OUT_MD = SPRINT_DIR / "VENTURE_STUDIO_TERMS_GUARDRAIL_PACKET_2026-07-09.md"

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

TERMS_SIGNALS = [
    {
        "signal_id": "soft_tech_venture_studio",
        "source": "live_call_note",
        "fact": "Terry described the lane as a soft-tech venture studio credibility path.",
        "meaning": "Treat the partner as a potential credibility, packaging, validation, and venture-building helper.",
        "boundary": "Do not treat this as accepted terms, funding, services award, or partnership.",
    },
    {
        "signal_id": "twenty_percent_equity_model",
        "source": "live_call_note",
        "fact": "The model discussed was 20% equity.",
        "meaning": "Founder should compare the request against cash, deliverables, brand value, funding access, and dilution alternatives.",
        "boundary": "No equity grant is accepted without written terms, cap table review, and counsel review.",
    },
    {
        "signal_id": "founder_funds_remaining_cost",
        "source": "live_call_note",
        "fact": "Robert understood that he may need to fund the rest of the work.",
        "meaning": "Cash budget, runway impact, vendor pass-throughs, and who pays for development must be explicit before agreement.",
        "boundary": "No cash commitment is accepted by this packet.",
    },
    {
        "signal_id": "yc_benchmark",
        "source": "official_public_yc_pages_checked_2026-07-09",
        "fact": "YC's public standard deal is a useful external benchmark: $500k investment for 7% plus an additional uncapped MFN SAFE component.",
        "meaning": "A 20% studio model should clear a higher-value justification bar if it brings less cash or more founder-funded cost.",
        "boundary": "This is a benchmark, not a legal, tax, valuation, or securities opinion.",
    },
]

DILIGENCE_QUESTIONS = [
    {
        "question_id": "equity_vesting",
        "question": "Is the 20% equity fixed at signing, or does it vest against named milestones?",
        "why_it_matters": "Milestone vesting protects the company if deliverables, intros, or validation support do not happen.",
    },
    {
        "question_id": "cash_budget",
        "question": "What exact cash does Luma need to fund during the first 30, 60, and 90 days?",
        "why_it_matters": "Founder-funded services can quietly become more expensive than the equity headline suggests.",
    },
    {
        "question_id": "ip_ownership",
        "question": "Who owns all code, data, models, proof artifacts, brand work, and derivative IP created during the engagement?",
        "why_it_matters": "Luma must preserve ownership and clean chain-of-title for future financing, grants, and patents.",
    },
    {
        "question_id": "deliverables",
        "question": "What are the named deliverables in the first 30 days, and what acceptance criteria prove completion?",
        "why_it_matters": "Credibility support should become inspectable assets, not vague advice.",
    },
    {
        "question_id": "funding_support",
        "question": "What investor, grant, customer, or partner introductions are committed versus best-efforts?",
        "why_it_matters": "Equity should buy leverage, not only service capacity.",
    },
    {
        "question_id": "termination",
        "question": "What happens to equity, work product, data access, and confidentiality if either side stops early?",
        "why_it_matters": "Exit terms prevent dead equity and stranded IP.",
    },
    {
        "question_id": "conflicts",
        "question": "Do they work with any overlapping companies or investors that create conflicts?",
        "why_it_matters": "The proof stack and patent narrative need protected strategic boundaries.",
    },
    {
        "question_id": "safer_start",
        "question": "Can the relationship start with a lower-risk paid or option sprint before final equity?",
        "why_it_matters": "A short credibility sprint can prove fit before major dilution.",
    },
]

SAFE_COUNTERPROPOSALS = [
    {
        "counter_id": "paid_credibility_sprint",
        "name": "Paid 30-day credibility sprint",
        "structure": "Cash or deferred fee for a bounded scope; no immediate 20% equity.",
        "best_when": "The studio can deliver a proof portal, pitch, first-customer path, and diligence room quickly.",
    },
    {
        "counter_id": "milestone_equity_option",
        "name": "Milestone-based equity option",
        "structure": "Equity vests only after written deliverables, funding intros, or customer validation milestones.",
        "best_when": "The studio wants upside but the founder needs protection against under-delivery.",
    },
    {
        "counter_id": "smaller_equity_plus_success",
        "name": "Smaller equity plus success fee",
        "structure": "Lower upfront equity with success-based economics tied to funded outcomes.",
        "best_when": "Their highest claimed value is fundraising, customer access, or partner conversion.",
    },
    {
        "counter_id": "yc_parallel_path",
        "name": "YC-parallel application path",
        "structure": "Prepare YC and venture-studio materials in parallel; compare terms before accepting dilution.",
        "best_when": "YC's public deal and brand provide a strong external reference point.",
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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def build_payload() -> dict[str, Any]:
    customer = read_json(CUSTOMER_JSON)
    evtit = read_json(EVTIT_JSON)
    authority = read_json(AUTHORITY_JSON)
    ip = read_json(IP_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    data_room = read_json(DATA_ROOM_JSON)

    customer_summary = as_dict(customer.get("summary"))
    evtit_summary = as_dict(evtit.get("summary"))
    authority_summary = as_dict(authority.get("summary"))
    gate_summary = as_dict(gate.get("summary"))
    data_summary = as_dict(data_room.get("summary"))

    reviewer_gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate_summary.get("unsafe_secret_count") or 0) == 0 and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human"))
    counsel_required = str(ip.get("status", "")).endswith("HUMAN_COUNSEL_REQUIRED")

    payload = {
        "generated_utc": now_utc(),
        "schema": "venture_studio_terms_guardrail_packet_v1",
        "status": "VENTURE_STUDIO_TERMS_GUARDRAIL_READY_COUNSEL_REVIEW_REQUIRED"
        if reviewer_gate_clear and final_actions_blocked and counsel_required
        else "VENTURE_STUDIO_TERMS_GUARDRAIL_BLOCKED",
        "position": {
            "plain_english": (
                "A soft-tech venture studio may help Luma become more credible, but a 20% equity model plus "
                "founder-funded remaining costs needs written scope, milestone economics, IP ownership, funding support, "
                "and counsel review before any acceptance."
            ),
            "call_posture": "Interested, not committed.",
            "preferred_next_step": "Written 30-day credibility sprint scope before equity acceptance.",
        },
        "yc_benchmark": {
            "source_checked_utc": "2026-07-09",
            "standard_deal_source": "https://www.ycombinator.com/deal",
            "apply_source": "https://www.ycombinator.com/apply",
            "public_terms_summary": "$500k investment for 7% plus an additional uncapped MFN SAFE component.",
            "current_deadline_summary": "On-time Fall 2026 application deadline listed as July 27, 2026 at 8pm PT, with decisions by August 28 for on-time applications.",
            "use": "Benchmark dilution, cash, network, brand, and investor-access value against any 20% studio request.",
        },
        "summary": {
            "terms_signal_count": len(TERMS_SIGNALS),
            "diligence_question_count": len(DILIGENCE_QUESTIONS),
            "counterproposal_count": len(SAFE_COUNTERPROPOSALS),
            "customer_segment_count": int(customer_summary.get("customer_segment_count") or 0),
            "commercial_offer_count": int(customer_summary.get("offer_count") or 0),
            "evtit_workstream_count": int(evtit_summary.get("workstream_count") or 0),
            "data_room_markdown_count": int(data_summary.get("manifested_markdown_count") or 0),
            "data_room_control_artifact_count": int(data_summary.get("control_artifact_count") or 0),
            "reviewer_gate_clear": reviewer_gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "all_final_actions_blocked_without_human": final_actions_blocked,
            "counsel_review_required": True,
            "equity_terms_accepted": False,
            "cash_commitment_accepted": False,
            "services_terms_accepted": False,
            "partnership_claimed": False,
            "investment_claimed": False,
            "funding_intro_committed": False,
            "external_send_allowed_without_human": False,
            "pricing_commitment_allowed_without_human": False,
            "private_file_share_allowed_without_human": False,
        },
        "terms_signals": TERMS_SIGNALS,
        "diligence_questions": DILIGENCE_QUESTIONS,
        "safe_counterproposals": SAFE_COUNTERPROPOSALS,
        "acceptance_blockers": [
            "No written scope and statement of work reviewed.",
            "No cap table and dilution model reviewed.",
            "No cash budget and runway impact reviewed.",
            "No IP ownership and work-product assignment reviewed.",
            "No milestone vesting or termination treatment reviewed.",
            "No counsel review completed.",
        ],
        "human_gate": {
            "accept_equity_allowed_without_human": False,
            "accept_services_terms_without_human": False,
            "commit_cash_without_human": False,
            "share_private_files_without_human": False,
            "send_counteroffer_without_human": False,
            "rule": "This packet records guardrails only. Robert and counsel approve any equity, cash, service, IP, file-sharing, or counteroffer action.",
        },
        "source_ledgers": {
            "customer_commercialization": rel(CUSTOMER_JSON),
            "evtit_scope": rel(EVTIT_JSON),
            "authority": rel(AUTHORITY_JSON),
            "ip_counsel": rel(IP_JSON),
            "reviewer_gate": rel(REVIEWER_GATE_JSON),
            "data_room": rel(DATA_ROOM_JSON),
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["venture_studio_terms_guardrail_sha256"] = stable_sha256(
        {
            "position": payload["position"],
            "yc_benchmark": payload["yc_benchmark"],
            "summary": payload["summary"],
            "terms_signals": payload["terms_signals"],
            "diligence_questions": payload["diligence_questions"],
            "safe_counterproposals": payload["safe_counterproposals"],
            "human_gate": payload["human_gate"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Venture Studio Terms Guardrail Packet - 2026-07-09",
        "",
        "Purpose: protect Luma's leverage while evaluating a soft-tech venture studio model, including a discussed 20% equity structure and founder-funded remaining costs.",
        "",
        "This packet is not legal, tax, valuation, or securities advice. It does not accept equity terms, cash commitments, service terms, file sharing, funding introductions, investment, or partnership status.",
        "",
        "## Position",
        "",
        payload["position"]["plain_english"],
        "",
        f"- Call posture: `{payload['position']['call_posture']}`",
        f"- Preferred next step: {payload['position']['preferred_next_step']}",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Terms signals: `{summary['terms_signal_count']}`",
        f"- Diligence questions: `{summary['diligence_question_count']}`",
        f"- Counterproposals: `{summary['counterproposal_count']}`",
        f"- Customer segments: `{summary['customer_segment_count']}`",
        f"- Commercial offers: `{summary['commercial_offer_count']}`",
        f"- EVTit workstreams: `{summary['evtit_workstream_count']}`",
        f"- Data-room Markdown artifacts: `{summary['data_room_markdown_count']}`",
        f"- Data-room machine controls: `{summary['data_room_control_artifact_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Counsel review required: `{str(summary['counsel_review_required']).lower()}`",
        f"- Equity terms accepted: `{str(summary['equity_terms_accepted']).lower()}`",
        f"- Cash commitment accepted: `{str(summary['cash_commitment_accepted']).lower()}`",
        f"- Services terms accepted: `{str(summary['services_terms_accepted']).lower()}`",
        f"- Partnership claimed: `{str(summary['partnership_claimed']).lower()}`",
        f"- Investment claimed: `{str(summary['investment_claimed']).lower()}`",
        f"- Funding intro committed: `{str(summary['funding_intro_committed']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Pricing commitment without human: `{str(summary['pricing_commitment_allowed_without_human']).lower()}`",
        f"- Private file share without human: `{str(summary['private_file_share_allowed_without_human']).lower()}`",
        f"- Packet SHA-256: `{payload['venture_studio_terms_guardrail_sha256']}`",
        "",
        "## YC Benchmark",
        "",
    ]
    for key, value in payload["yc_benchmark"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Terms Signals", ""])
    for signal in payload["terms_signals"]:
        lines.extend(
            [
                f"### {signal['signal_id']}",
                "",
                f"- Source: `{signal['source']}`",
                f"- Fact: {signal['fact']}",
                f"- Meaning: {signal['meaning']}",
                f"- Boundary: {signal['boundary']}",
                "",
            ]
        )

    lines.extend(["## Diligence Questions", ""])
    for item in payload["diligence_questions"]:
        lines.extend(
            [
                f"### {item['question_id']}",
                "",
                f"- Question: {item['question']}",
                f"- Why it matters: {item['why_it_matters']}",
                "",
            ]
        )

    lines.extend(["## Safer Counterproposal Shapes", ""])
    for item in payload["safe_counterproposals"]:
        lines.extend(
            [
                f"### {item['name']}",
                "",
                f"- Counter ID: `{item['counter_id']}`",
                f"- Structure: {item['structure']}",
                f"- Best when: {item['best_when']}",
                "",
            ]
        )

    lines.extend(["## Acceptance Blockers", ""])
    for item in payload["acceptance_blockers"]:
        lines.append(f"- {item}")

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
        raise SystemExit(f"Refusing to write sensitive public venture-studio markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "questions": payload["summary"]["diligence_question_count"],
                "counterproposals": payload["summary"]["counterproposal_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0 if payload["status"].endswith("COUNSEL_REVIEW_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
