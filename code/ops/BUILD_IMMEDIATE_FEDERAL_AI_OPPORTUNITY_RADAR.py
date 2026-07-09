from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

OUT_JSON = OUT_OPS / "immediate_federal_ai_opportunity_radar_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "immediate_federal_ai_opportunity_radar.json"
OUT_MD = SPRINT_DIR / "IMMEDIATE_FEDERAL_AI_OPPORTUNITY_RADAR_2026-07-09.md"

SCAN_DATE = date(2026, 7, 9)

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

SOURCE_NOTES = {
    "sweetspot_primary": (
        "Sweetspot federal contract search run on July 9, 2026 for active AI validation, AI assurance, "
        "data infrastructure, governance, transportation operations, and simulation opportunities."
    ),
    "sam_official": (
        "SAM.gov search results were used to verify official notice IDs and public opportunity pages where available."
    ),
    "gmail_context": (
        "Terry/EVTit feedback and the sent LumenCore pitch deck are treated as business-framing context only; "
        "no opportunity response is authorized by email context alone."
    ),
}

OPPORTUNITIES: list[dict[str, Any]] = [
    {
        "opportunity_id": "air_force_aac_advanced_automation_rfi",
        "title": "REQUEST FOR INFORMATION: Advanced Automation Contract (AAC)",
        "solicitation_number": "SAF-AQ-RFI-26-0001",
        "agency": "Department of the Air Force",
        "notice_type": "Special Notice / RFI",
        "deadline_utc": "2026-07-13T21:00:00Z",
        "official_url": "https://sam.gov/workspace/contract/opp/3fa15f166ec244539c808be5c0496427/view",
        "source_refs": ["sweetspot:SAF-AQ-RFI-26-0001", "sam:SAF-AQ-RFI-26-0001"],
        "fit_score": 76,
        "urgency_score": 94,
        "pursuit_posture": "CAPABILITY_RESPONSE_DRAFT",
        "why_it_matters": (
            "The RFI asks for ways to orchestrate a dynamic advanced automation portfolio. LumenCore can credibly "
            "respond around proof portal, evidence manifest, replay governance, vendor/tool evaluation, and control-room logic."
        ),
        "primary_blockers": [
            "RFI is market research, not direct funding.",
            "Prime role may require portfolio administration capacity beyond the current solo posture.",
            "Official attachments and response format must be checked in SAM.gov before any send.",
        ],
        "reuse_evidence": [
            "REVIEWER_DECISION_BRIEF_2026-07-09.md",
            "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
            "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
            "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
        ],
        "next_action": "Prepare a 2-3 page capability response and partner/prime boundary statement for human review.",
    },
    {
        "opportunity_id": "hhs_ai_power_user_pilot",
        "title": "HHS AI Power User Advanced Models and Features Pilot",
        "solicitation_number": "7571TE26R00004",
        "agency": "Department of Health and Human Services",
        "notice_type": "Combined Synopsis/Solicitation",
        "deadline_utc": "2026-07-14T21:00:00Z",
        "official_url": "https://sam.gov/opp/b502944e30d9426db1d48968e86e9726/view",
        "source_refs": ["sweetspot:7571TE26R00004", "sam:7571TE26R00004"],
        "fit_score": 52,
        "urgency_score": 92,
        "pursuit_posture": "PARTNER_OR_NO_BID",
        "why_it_matters": (
            "The pilot is about operational baselines for frontier AI use, governance, usage telemetry, and acquisition learning. "
            "That maps to LumenCore's measurement language, but the likely prime must provide production-grade AI service access."
        ),
        "primary_blockers": [
            "Likely not a solo-prime fit without a compliant frontier-model platform partner.",
            "Security, access, pricing, and service-bundle requirements must be verified in official attachments.",
            "No FedRAMP, HHS production access, or enterprise service capability should be claimed.",
        ],
        "reuse_evidence": [
            "CUSTOMER_COMMERCIALIZATION_PACKET_2026-07-09.md",
            "PITCH_DECK_SEND_RECEIPT_2026-07-09.md",
            "VENTURE_STUDIO_TERMS_GUARDRAIL_PACKET_2026-07-09.md",
        ],
        "next_action": "Use as partner-target intelligence; do not bid solo unless a qualified platform partner leads.",
    },
    {
        "opportunity_id": "va_omega_2_assurance_services",
        "title": "OMEGA 2.0 Onboarding, Management, Engineering, Governance, and Assurance Services",
        "solicitation_number": "36C10B26Q0590",
        "agency": "Department of Veterans Affairs",
        "notice_type": "Sources Sought",
        "deadline_utc": "2026-07-14T18:00:00Z",
        "official_url": "https://sam.gov/opp/6a975da7c063464eb847c02a105605d3/view",
        "source_refs": ["sweetspot:36C10B26Q0590", "sam:36C10B26Q0590"],
        "fit_score": 62,
        "urgency_score": 90,
        "pursuit_posture": "VERIFY_OFFICIAL_THEN_PARTNER",
        "why_it_matters": (
            "The assurance-services scope maps to AI governance, platform controls, API governance, and evidence-review workflows."
        ),
        "primary_blockers": [
            "Sweetspot summary included stale or conflicting deadline text; official SAM attachments must control.",
            "Likely requires broader platform operations staffing than current LumenCore can credibly prime alone.",
            "Do not claim VA platform assurance experience without a partner or accepted pilot evidence.",
        ],
        "data_quality_flags": [
            "Deadline and historical text conflict in one search summary; verify in SAM.gov before effort."
        ],
        "reuse_evidence": [
            "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
            "AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
            "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        ],
        "next_action": "Open official SAM attachments, confirm active due date, then route as partner capability note if still live.",
    },
    {
        "opportunity_id": "csosa_public_safety_analytics",
        "title": "Public Safety Data Analytics Platform & Support Services",
        "solicitation_number": "9594CS26Q0053",
        "agency": "Court Services and Offender Supervision Agency",
        "notice_type": "Solicitation",
        "deadline_utc": "2026-07-14T16:00:00Z",
        "official_url": "https://sam.gov/workspace/contract/opp/24deb6ceb402464cb04e2a404f07c99a/view",
        "source_refs": ["sweetspot:9594CS26Q0053", "sam:9594CS26Q0053"],
        "fit_score": 34,
        "urgency_score": 91,
        "pursuit_posture": "NO_PRIME_FEDRAMP_GATE",
        "why_it_matters": (
            "Public-safety analytics is adjacent to LumenCore's evidence and integration language, but the solicitation gate appears platform-heavy."
        ),
        "primary_blockers": [
            "Requires active FedRAMP Moderate authorization at quote submission according to search summary.",
            "Likely requires public-safety SaaS operations and on-site staffing beyond the current validated posture.",
            "Do not claim CJIS, FedRAMP, law-enforcement feed integration, or production deployment.",
        ],
        "reuse_evidence": [
            "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
            "AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
        ],
        "next_action": "Park as no-prime; use only if a compliant platform partner asks for evidence/replay subcontract support.",
    },
    {
        "opportunity_id": "army_aidp_rfi4",
        "title": "Army Intelligence Data Platform RFI #4",
        "solicitation_number": "ACCAPGAIDPRFI4",
        "agency": "Department of the Army",
        "notice_type": "Sources Sought / RFI",
        "deadline_utc": "2026-07-15T21:00:00Z",
        "official_url": "https://sam.gov/workspace/contract/opp/1b796810e2834d3f9245b8d4377266bb/view",
        "source_refs": ["sweetspot:ACCAPGAIDPRFI4", "sam:ACCAPGAIDPRFI4"],
        "fit_score": 70,
        "urgency_score": 88,
        "pursuit_posture": "PARTNER_CAPABILITY_NOTE",
        "why_it_matters": (
            "The RFI includes modular data platform, tactical-edge, and degraded-network concerns. LumenCore can position evidence replay, "
            "local validation, and traceability as a narrow proof module rather than a full intelligence platform."
        ),
        "primary_blockers": [
            "Do not prime as a full Army intelligence data platform.",
            "Classified or controlled requirements may exceed current public-safe material.",
            "Official attachments and markings must be checked before drafting any details.",
        ],
        "reuse_evidence": [
            "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
            "PROOF_STACK_EDGE_INDEX_2026-07-09.md",
            "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
        ],
        "next_action": "Prepare a partner-facing capability note about traceable replay and edge validation modules.",
    },
    {
        "opportunity_id": "waveform_governance",
        "title": "Waveform Governance",
        "solicitation_number": "C3NK06042026_2",
        "agency": "Department of the Air Force",
        "notice_type": "Sources Sought",
        "deadline_utc": "2026-07-10T16:00:00Z",
        "official_url": "https://sam.gov/workspace/contract/opp/25b41468a39342629108dda5530921c1/view",
        "source_refs": ["sweetspot:C3NK06042026_2", "sam:C3NK06042026_2"],
        "fit_score": 46,
        "urgency_score": 99,
        "pursuit_posture": "LOW_FIT_SKIP_UNLESS_PARTNER",
        "why_it_matters": (
            "Governance trade-study language is adjacent, but the domain is waveform/radio lifecycle governance, not LumenCore's best current wedge."
        ),
        "primary_blockers": [
            "Very near deadline.",
            "Domain-specific radio and waveform governance depth likely required.",
            "A rushed solo response would weaken credibility."
        ],
        "reuse_evidence": [
            "VENTURE_STUDIO_TERMS_GUARDRAIL_PACKET_2026-07-09.md",
            "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
        ],
        "next_action": "Skip solo; only respond if an existing defense partner needs a governance-evidence appendix.",
    },
    {
        "opportunity_id": "navy_ai_intelligent_automation_support",
        "title": "AI Intelligent Automation Support Services",
        "solicitation_number": "N0017827R3105",
        "agency": "Department of the Navy",
        "notice_type": "Sources Sought",
        "deadline_utc": "2026-07-09T16:00:00Z",
        "official_url": "https://sam.gov/opp/70699db185d2474e8087f681e8374748/view",
        "source_refs": ["sweetspot:N0017827R3105", "sam:N0017827R3105"],
        "fit_score": 50,
        "urgency_score": 100,
        "pursuit_posture": "CLOSED_OR_TOO_LATE",
        "why_it_matters": (
            "The AI/ML lifecycle, MLOps, cybersecurity, prototyping, and test/evaluation language is relevant, but the due time appears passed."
        ),
        "primary_blockers": [
            "Deadline appears to have passed on July 9, 2026.",
            "SeaPort-NxG or other vehicle restrictions may apply.",
            "Use this as market-intelligence language, not a live submission route."
        ],
        "reuse_evidence": [
            "REVIEWER_DILIGENCE_QA_MATRIX_2026-07-09.md",
            "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
        ],
        "next_action": "Archive as terminology intelligence for future AI test/evaluation and MLOps support opportunities.",
    },
    {
        "opportunity_id": "fhwa_tsmo_data_initiative",
        "title": "Transportation Systems Management and Operations Data Initiative",
        "solicitation_number": "693JJ326R000012",
        "agency": "Federal Highway Administration",
        "notice_type": "Solicitation",
        "deadline_utc": "2026-08-03T13:00:00Z",
        "official_url": "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view",
        "source_refs": ["sweetspot:693JJ326R000012", "sam:693JJ326R000012"],
        "fit_score": 95,
        "urgency_score": 72,
        "pursuit_posture": "PRIMARY_PHASE_I_TECHNICAL_VOLUME",
        "why_it_matters": (
            "This remains the best agency-contract fit: AI-enabled TSMO data barriers, prototype algorithms/models, and benchmarkable use cases."
        ),
        "primary_blockers": [
            "Official attachments, two-phase process, terms, and pricing must be checked by a human.",
            "Transportation field data or teaming may be required to make claims stronger.",
            "No safety benefit or field deployment claim until a partner validates it."
        ],
        "reuse_evidence": [
            "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
            "FIELD_VALIDATION_OUTREACH_BOARD_2026-07-09.md",
            "FIELD_VALIDATED_DOLLAR_CLAIM_LADDER_2026-07-09.md",
            "REVIEWER_DECISION_BRIEF_2026-07-09.md",
        ],
        "next_action": "Promote to the main agency proposal lane and build a compliance matrix around the existing FHWA outline.",
    },
    {
        "opportunity_id": "army_training_simulation_rfi",
        "title": "Request for Information: Training & Simulation",
        "solicitation_number": "W900KK-26-R-0001",
        "agency": "Department of the Army",
        "notice_type": "Special Notice / RFI",
        "deadline_utc": "2026-08-15T21:00:00Z",
        "official_url": "https://sam.gov/opp/e577d0eef9a84d51aa46bce6ed779233/view",
        "source_refs": ["sweetspot:W900KK-26-R-0001", "sam:W900KK-26-R-0001"],
        "fit_score": 72,
        "urgency_score": 58,
        "pursuit_posture": "WATCH_AND_PARTNER_FEEDBACK",
        "why_it_matters": (
            "A live/virtual/constructive simulation environment can use evidence replay, telemetry, and validation control layers. "
            "This is a longer-window partner route."
        ),
        "primary_blockers": [
            "SAM search results showed active/inactive ambiguity; official notice must be opened and verified before action.",
            "LumenCore is not a full training-environment prime today.",
            "A narrow validation/replay module is more credible than a broad platform claim."
        ],
        "data_quality_flags": [
            "Search returned both active and inactive SAM result snippets; official page status must control."
        ],
        "reuse_evidence": [
            "PROOF_STACK_EDGE_INDEX_2026-07-09.md",
            "MEASURED_SOURCE_EVIDENCE_REGISTER_2026-07-09.md",
            "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md",
        ],
        "next_action": "Watch and prepare a partner-facing module description after official status is confirmed.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def days_to_deadline(deadline_utc: str) -> int:
    return (datetime.fromisoformat(deadline_utc.replace("Z", "+00:00")).date() - SCAN_DATE).days


def classify_deadline(days: int) -> str:
    if days < 0:
        return "past_due"
    if days == 0:
        return "same_day"
    if days <= 2:
        return "48_hour_sprint"
    if days <= 7:
        return "seven_day_sprint"
    if days <= 30:
        return "thirty_day_sprint"
    return "watchlist"


def recommended_lanes(opportunities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            opp
            for opp in opportunities
            if opp["pursuit_posture"]
            in {
                "CAPABILITY_RESPONSE_DRAFT",
                "PRIMARY_PHASE_I_TECHNICAL_VOLUME",
                "PARTNER_CAPABILITY_NOTE",
                "WATCH_AND_PARTNER_FEEDBACK",
            }
        ],
        key=lambda row: (-int(row["fit_score"]), days_to_deadline(str(row["deadline_utc"]))),
    )


def build_payload() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for opp in OPPORTUNITIES:
        row = dict(opp)
        row["days_to_deadline_from_2026_07_09"] = days_to_deadline(str(row["deadline_utc"]))
        row["deadline_bucket"] = classify_deadline(row["days_to_deadline_from_2026_07_09"])
        row["human_gate_required"] = True
        row["final_submission_allowed_without_human"] = False
        row["opportunity_sha256"] = stable_sha256(row)
        rows.append(row)

    rows = sorted(rows, key=lambda row: (row["days_to_deadline_from_2026_07_09"], -int(row["fit_score"])))
    recommended = recommended_lanes(rows)
    close = [row for row in rows if 0 <= row["days_to_deadline_from_2026_07_09"] <= 7]
    no_prime = [
        row
        for row in rows
        if row["pursuit_posture"] in {"NO_PRIME_FEDRAMP_GATE", "PARTNER_OR_NO_BID", "LOW_FIT_SKIP_UNLESS_PARTNER"}
    ]
    data_quality = [row for row in rows if row.get("data_quality_flags")]

    payload = {
        "schema": "immediate_federal_ai_opportunity_radar_v1",
        "generated_utc": now_utc(),
        "scan_date": SCAN_DATE.isoformat(),
        "status": "IMMEDIATE_FEDERAL_AI_OPPORTUNITY_RADAR_READY_HUMAN_ACTION_REQUIRED",
        "summary": {
            "opportunity_count": len(rows),
            "close_deadline_count": len(close),
            "recommended_action_count": len(recommended),
            "no_prime_or_partner_only_count": len(no_prime),
            "data_quality_flag_count": len(data_quality),
            "human_action_required": True,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "portal_submission_allowed_without_human": False,
            "best_immediate_action": "Air Force AAC capability response draft",
            "best_overall_agency_fit": "FHWA TSMO Data Initiative Phase I technical volume",
            "best_partner_signal": "HHS AI Power User Pilot partner route",
        },
        "source_notes": SOURCE_NOTES,
        "opportunities": rows,
        "recommended_lanes": [
            {
                "opportunity_id": row["opportunity_id"],
                "title": row["title"],
                "solicitation_number": row["solicitation_number"],
                "deadline_utc": row["deadline_utc"],
                "fit_score": row["fit_score"],
                "pursuit_posture": row["pursuit_posture"],
                "next_action": row["next_action"],
            }
            for row in recommended
        ],
        "terry_feedback_translation": {
            "business_objection": "The work needs to be easier to evaluate as a business, not only as a technical stack.",
            "proof_stack_response": [
                "Filter opportunities by fit, deadline, and disqualifying gates.",
                "Show where LumenCore should prime, partner, or skip.",
                "Turn science into field-validation pilots with bounded dollar math.",
                "Keep unsupported FedRAMP, government deployment, award, and savings claims blocked.",
            ],
            "credible_sentence": (
                "LumenCore is a proof-to-pilot validation layer: we help technical buyers decide whether an AI or data system "
                "is reliable enough to fund, route to pilot, or reject, with traceable evidence instead of broad claims."
            ),
        },
        "control_boundary": {
            "no_final_actions": True,
            "human_approval_required_before": [
                "SAM.gov upload",
                "email response",
                "certification",
                "pricing",
                "partner commitment",
                "equity or term acceptance",
                "claim of FedRAMP, ATO, customer savings, or award status",
            ],
            "not_legal_or_procurement_advice": True,
        },
    }
    payload["radar_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Immediate Federal AI Opportunity Radar - 2026-07-09",
        "",
        "Purpose: convert the live federal AI opportunity sweep into a near-deadline action board for LumenCore without overstating qualification, award status, or agency validation.",
        "",
        "This radar is a triage and evidence-routing artifact. It does not authorize portal submission, certification, pricing, partner commitments, or external sends without human approval.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Scan date: `{payload['scan_date']}`",
        f"- Opportunities reviewed: `{summary['opportunity_count']}`",
        f"- Close-deadline opportunities: `{summary['close_deadline_count']}`",
        f"- Recommended action lanes: `{summary['recommended_action_count']}`",
        f"- No-prime or partner-only lanes: `{summary['no_prime_or_partner_only_count']}`",
        f"- Data-quality flags: `{summary['data_quality_flag_count']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Radar SHA-256: `{payload['radar_sha256']}`",
        "",
        "## Direct Answer",
        "",
        f"- Best immediate action: `{summary['best_immediate_action']}`",
        f"- Best overall agency fit: `{summary['best_overall_agency_fit']}`",
        f"- Best partner signal: `{summary['best_partner_signal']}`",
        "",
        "## Recommended Lanes",
        "",
    ]
    for lane in payload["recommended_lanes"]:
        lines.extend(
            [
                f"### {lane['title']}",
                "",
                f"- Solicitation: `{lane['solicitation_number']}`",
                f"- Deadline UTC: `{lane['deadline_utc']}`",
                f"- Fit score: `{lane['fit_score']}`",
                f"- Posture: `{lane['pursuit_posture']}`",
                f"- Next action: {lane['next_action']}",
                "",
            ]
        )

    lines.extend(["## Full Radar", ""])
    for opp in payload["opportunities"]:
        lines.extend(
            [
                f"### {opp['title']}",
                "",
                f"- ID: `{opp['opportunity_id']}`",
                f"- Agency: `{opp['agency']}`",
                f"- Solicitation: `{opp['solicitation_number']}`",
                f"- Deadline UTC: `{opp['deadline_utc']}`",
                f"- Deadline bucket: `{opp['deadline_bucket']}`",
                f"- Fit score: `{opp['fit_score']}`",
                f"- Urgency score: `{opp['urgency_score']}`",
                f"- Posture: `{opp['pursuit_posture']}`",
                f"- Official URL: {opp['official_url']}",
                f"- Why it matters: {opp['why_it_matters']}",
                "- Primary blockers:",
            ]
        )
        for blocker in opp["primary_blockers"]:
            lines.append(f"  - {blocker}")
        if opp.get("data_quality_flags"):
            lines.append("- Data-quality flags:")
            for flag in opp["data_quality_flags"]:
                lines.append(f"  - {flag}")
        lines.append("- Evidence to reuse:")
        for item in opp["reuse_evidence"]:
            lines.append(f"  - `{item}`")
        lines.extend([f"- Next action: {opp['next_action']}", ""])

    translation = payload["terry_feedback_translation"]
    lines.extend(
        [
            "## Terry Feedback Translation",
            "",
            f"- Business objection: {translation['business_objection']}",
            f"- Credible sentence: {translation['credible_sentence']}",
            "- Proof-stack response:",
        ]
    )
    for item in translation["proof_stack_response"]:
        lines.append(f"  - {item}")

    lines.extend(["", "## Control Boundary", ""])
    for item in payload["control_boundary"]["human_approval_required_before"]:
        lines.append(f"- Human approval required before: {item}")
    lines.extend(
        [
            f"- No final actions: `{str(payload['control_boundary']['no_final_actions']).lower()}`",
            f"- Not legal or procurement advice: `{str(payload['control_boundary']['not_legal_or_procurement_advice']).lower()}`",
        ]
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
        raise SystemExit(f"Refusing to write sensitive public data-room markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "opportunities": payload["summary"]["opportunity_count"],
                "recommended": payload["summary"]["recommended_action_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
