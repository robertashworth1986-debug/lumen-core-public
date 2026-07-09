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

OUT_JSON = OUT_OPS / "traction_opportunity_intake_ledger_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "traction_opportunity_intake_ledger.json"
OUT_MD = SPRINT_DIR / "TRACTION_OPPORTUNITY_INTAKE_LEDGER_2026-07-09.md"

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

PUBLIC_SOURCES = {
    "sam_fhwa_tsmo": "https://sam.gov/opp/0ebbe1e43167440ebb111f80fd065ed4/view",
    "sam_nasa_data_center": "https://sam.gov/workspace/contract/opp/b6d14a4b9eac476b997894d0c5a47a27/view",
    "sam_epa_icpoes": "https://sam.gov/opp/d9cebf54026d4eae918897e0c34d5a28/view",
    "sam_fhwa_baa_call_3": "https://sam.gov/opp/99e6bba615c746e9af27e1527a05a897/view",
    "darpa_dice": "https://www.darpa.mil/research/programs/decentralized-artificial-intelligence-through-controlled-emergence",
    "sbir_topics": "https://www.sbir.gov/topics",
    "nsf_project_pitch": "https://seedfund.nsf.gov/project-pitch/",
    "nsf_project_pitch_apply": "https://seedfund.nsf.gov/apply/project-pitch/",
    "uspto_provisional": "https://www.uspto.gov/patents/basics/apply/provisional-application",
    "uspto_utility": "https://www.uspto.gov/patents/basics/apply/utility-patent",
    "lvlup_first_check": "https://www.lvlup.vc/fund/first-check-fund",
    "black_dog": "https://blackdogceo.com/",
    "evtit_event": "https://www.eventbrite.com/e/the-equity-for-code-revolution-evtits-10m-in-kind-venture-fund-tickets-1993026582158",
    "openai_contact_sales": "https://openai.com/contact-sales/",
}

CONNECTED_EVIDENCE = {
    "gmail_profile": "Robert Ashworth mailbox confirmed through Gmail connector.",
    "gmail_window": "Gmail searched in:anywhere after 2026-04-09 for funding, SBIR, RFI/RFP, deadline, calendar, and application terms.",
    "calendar_window": "Google Calendar searched 2026-07-09 through 2026-07-11 for the EVTit booking; no matching calendar event was returned, so Gmail invite evidence is authoritative for this ledger.",
    "sweetspot_window": "Sweetspot federal contracts searched for active opportunities after 2026-07-09 and before 2026-08-31 across AI validation, lab data QA, data center, and transportation operations lanes.",
}

LANES: list[dict[str, Any]] = [
    {
        "lane_id": "evtit_blackdog_inkind",
        "name": "EVTit / Black Dog in-kind engineering fund",
        "channel": "venture_engineering",
        "source_kind": "gmail_plus_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Discovery meeting booked from Gmail invite; public launch event July 22, 2026.",
        "status": "LIVE_MEETING_PREP",
        "fit_score": 92,
        "priority": 1,
        "traction_evidence": [
            "EVTit internal process form requested by Terry Anderton.",
            "LumenCore reply indicates the EVTit application form was submitted.",
            "Discovery meeting invite received with LumenCore proof-to-pilot context.",
        ],
        "reviewer_action": "Prepare a pre-call technical walkthrough, build-scope menu, and proof-card appendix.",
        "human_gate": "Human attends meeting and decides any equity-for-services terms.",
        "claim_boundary": "Meeting and application evidence only; no investment, services award, or partnership has been accepted.",
        "source_refs": ["gmail:19f43c8a4ba9346e", "gmail:19f44a7aa0a8a011", "public:evtit_event", "public:black_dog"],
    },
    {
        "lane_id": "lvlup_first_check",
        "name": "LvlUp Ventures First Check Fund",
        "channel": "venture_cash",
        "source_kind": "gmail_plus_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Submitted July 9, 2026; Gmail reply acknowledged the update.",
        "status": "WAITING_REVIEW",
        "fit_score": 86,
        "priority": 2,
        "traction_evidence": [
            "LumenCore application submitted with proof-to-pilot public proof link.",
            "Jackson Hellmann replied positively to the submitted-update email.",
            "Public program describes first-check funding and startup perks for early founders.",
        ],
        "reviewer_action": "Keep investor brief and short walkthrough ready for under-one-week review.",
        "human_gate": "Human approves any diligence reply or investor terms.",
        "claim_boundary": "Submission and acknowledgement only; no funding decision is represented.",
        "source_refs": ["gmail:19f44c59a4189d31", "public:lvlup_first_check"],
    },
    {
        "lane_id": "darpa_dice_full_submission",
        "name": "DARPA DICE full proposal sprint",
        "channel": "federal_baa",
        "source_kind": "gmail_plus_official_program",
        "evidence_date": "2026-07-08",
        "deadline_or_gate": "Abstract ID HR001126S0010-DICE-PA-052 recorded; full proposal instructions must be confirmed against the controlling BAA before upload.",
        "status": "FULL_PROPOSAL_SPRINT",
        "fit_score": 90,
        "priority": 3,
        "traction_evidence": [
            "Gmail sent follow-up records receipt of the abstract and the assigned identifying number.",
            "Official DARPA DICE page aligns with decentralized coordination and local inference control.",
        ],
        "reviewer_action": "Build full submission matrix, compute plan, performer/team map, and acceptance-test narrative.",
        "human_gate": "Human confirms BAA requirements, reps, budgets, and submission package before any portal action.",
        "claim_boundary": "Abstract receipt is not award selection and not permission to skip BAA instructions.",
        "source_refs": ["gmail:19f4332ca917d603", "public:darpa_dice"],
    },
    {
        "lane_id": "fhwa_tsmo_data_initiative",
        "name": "FHWA TSMO Data Initiative",
        "channel": "federal_contract",
        "source_kind": "sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-08-03 13:00 UTC per Sweetspot search; official SAM notice ID 693JJ326R000012 located.",
        "status": "PHASE_I_TECH_VOLUME",
        "fit_score": 95,
        "priority": 4,
        "traction_evidence": [
            "Sweetspot matched prototype algorithms/models for AI-enabled TSMO data barriers.",
            "Existing LumenCore sprint already contains a Phase I technical capability outline.",
        ],
        "reviewer_action": "Convert the existing outline into a compliance matrix, capability volume, and teaming decision.",
        "human_gate": "Human verifies SAM attachments, terms, pricing, reps/certs, and final submission authority.",
        "claim_boundary": "Prepared capability material only; no FHWA field result, safety benefit, or deployment claim.",
        "source_refs": ["public:sam_fhwa_tsmo", "sweetspot:693JJ326R000012"],
    },
    {
        "lane_id": "nasa_data_center_rfi",
        "name": "NASA Data Center Infrastructure RFI",
        "channel": "federal_rfi",
        "source_kind": "sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-17 21:00 UTC per Sweetspot search; official RFI number 80TECH26RFI0020 located.",
        "status": "RFI_RESPONSE_PREP",
        "fit_score": 89,
        "priority": 5,
        "traction_evidence": [
            "Sweetspot describes NASA interest in modernization, AI-driven operations, resilience, efficiency, and mission continuity.",
            "Existing LumenCore sprint already contains a response outline.",
        ],
        "reviewer_action": "Package the RFI response as architecture, evidence manifest, and operations-risk framing.",
        "human_gate": "Human verifies official response instructions, page limits, contacts, and final send.",
        "claim_boundary": "RFI response only; no NASA partnership, contract, or infrastructure result is represented.",
        "source_refs": ["public:sam_nasa_data_center", "sweetspot:80TECH26RFI0020"],
    },
    {
        "lane_id": "dla_missionweave_sbir",
        "name": "DLA MissionWeave DSIP SBIR",
        "channel": "federal_sbir",
        "source_kind": "existing_sprint_plus_public_sbir",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Current sprint records July 22, 2026 as the active DSIP gate; verify DSIP before final action.",
        "status": "DSIP_PACKAGE_PREP",
        "fit_score": 87,
        "priority": 6,
        "traction_evidence": [
            "Existing sprint contains a MissionWeave fast submission plan.",
            "SBIR.gov topic framework confirms SBIR/STTR topics define the response rules.",
        ],
        "reviewer_action": "Prepare DSIP technical volume, cost notes, and Firm PIN handoff checklist.",
        "human_gate": "Human-only Firm PIN, certifications, cost approval, and final submit.",
        "claim_boundary": "No DLA integration, procurement, or certified readiness claim.",
        "source_refs": ["public:sbir_topics", "local:DSIP_MISSIONWEAVE_FAST_SUBMISSION_PLAN_2026-07-09.md"],
    },
    {
        "lane_id": "nsf_project_pitch",
        "name": "NSF SBIR/STTR Project Pitch",
        "channel": "federal_sbir",
        "source_kind": "official_public_program",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Rolling pitch gate; NSF requires waiting if a Project Pitch, open invitation, or full proposal is already pending.",
        "status": "PITCH_READY_HUMAN_CHECK",
        "fit_score": 78,
        "priority": 7,
        "traction_evidence": [
            "Existing sprint contains an NSF Project Pitch draft.",
            "NSF public guidance confirms the Project Pitch is the gate before invited full proposal submission.",
        ],
        "reviewer_action": "Check the one-pending-pitch rule and submit only if no conflicting NSF item is pending.",
        "human_gate": "Human approves pitch content and submission.",
        "claim_boundary": "No NSF invitation or full-proposal eligibility is represented unless NSF issues it.",
        "source_refs": ["public:nsf_project_pitch", "public:nsf_project_pitch_apply", "local:NSF_PROJECT_PITCH_DRAFT_2026-07-09.md"],
    },
    {
        "lane_id": "epa_r10_icpoes_route",
        "name": "EPA Region 10 ICP-OES RFI route",
        "channel": "federal_market_research",
        "source_kind": "gmail_plus_sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-21 21:30 UTC per Sweetspot search; official notice ID 68HE0726Q0027 located.",
        "status": "ROUTE_ONLY_LOW_FIT",
        "fit_score": 42,
        "priority": 8,
        "traction_evidence": [
            "LumenCore already sent a boundary-safe email clarifying it is not an ICP-OES OEM/reseller.",
            "The only viable angle is routing to lab data QA or audit-ready reporting needs.",
        ],
        "reviewer_action": "Wait for agency routing response; do not prepare a hardware quote.",
        "human_gate": "Human approves any further agency contact.",
        "claim_boundary": "No instrument supply, OEM, reseller, or lab-services qualification claim.",
        "source_refs": ["gmail:19f4332fa2615bd6", "public:sam_epa_icpoes", "sweetspot:68HE0726Q0027"],
    },
    {
        "lane_id": "epa_ucmr6_partner_only",
        "name": "EPA UCMR 6 analytical chemistry lab services",
        "channel": "federal_sources_sought",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-21 20:00 UTC per Sweetspot search.",
        "status": "PARTNER_ONLY",
        "fit_score": 46,
        "priority": 9,
        "traction_evidence": [
            "Scope is analytical chemistry laboratory services, not a software-only proof-to-pilot lane.",
            "Possible fit only as a data QA, anomaly review, or reporting subcontractor to a qualified lab.",
        ],
        "reviewer_action": "Hold for qualified lab partner; do not chase as prime.",
        "human_gate": "Human approves partner outreach.",
        "claim_boundary": "No testing lab, contaminant monitoring, or regulated lab-services claim.",
        "source_refs": ["sweetspot:68HERW26R0020"],
    },
    {
        "lane_id": "fhwa_infrastructure_baa_call3",
        "name": "FHWA Infrastructure R&D BAA Call 3.0",
        "channel": "federal_baa",
        "source_kind": "sweetspot_plus_sam",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-24 17:00 UTC per Sweetspot search; official SAM call located.",
        "status": "SCOUT_TOPIC_MATCH",
        "fit_score": 64,
        "priority": 10,
        "traction_evidence": [
            "Could fit if a topic supports evidence replay, digital asset validation, or nondestructive-evaluation data workflows.",
            "Requires topic-by-topic Appendix C fit check before effort.",
        ],
        "reviewer_action": "Download official attachments and score each Appendix C topic before drafting.",
        "human_gate": "Human approves topic selection and submission.",
        "claim_boundary": "No claim that LumenCore fits all BAA topics.",
        "source_refs": ["public:sam_fhwa_baa_call_3", "sweetspot:693JJ3-23-BAA-0002-3"],
    },
    {
        "lane_id": "hhs_ai_power_user_pilot",
        "name": "HHS AI Power User Advanced Models and Features Pilot",
        "channel": "federal_contract",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-14 21:00 UTC per Sweetspot search.",
        "status": "DO_NOT_PRIME_SOLO",
        "fit_score": 38,
        "priority": 11,
        "traction_evidence": [
            "Attractive AI governance language, but Sweetspot indicates a strict security/authorization pathway.",
            "Solo-prime posture is not reviewer-safe unless a qualified platform partner leads.",
        ],
        "reviewer_action": "Do not chase solo; use as partner-target intelligence only.",
        "human_gate": "Human approves any partner route.",
        "claim_boundary": "No FedRAMP, ATO, HHS pilot, or government production-access claim.",
        "source_refs": ["sweetspot:7571TE26R00004"],
    },
    {
        "lane_id": "csosa_public_safety_analytics",
        "name": "CSOSA Public Safety Data Analytics Platform",
        "channel": "federal_contract",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-14 16:00 UTC per Sweetspot search.",
        "status": "DO_NOT_PRIME_SOLO",
        "fit_score": 35,
        "priority": 12,
        "traction_evidence": [
            "Analytics platform language is relevant, but Sweetspot indicates an active FedRAMP Moderate gate at quote submission.",
            "LumenCore should not represent qualification for this without a compliant platform partner.",
        ],
        "reviewer_action": "Park as a partner-only signal; do not spend proposal time as prime.",
        "human_gate": "Human approves any partner route.",
        "claim_boundary": "No public-safety deployment, law-enforcement feed integration, or FedRAMP authorization claim.",
        "source_refs": ["sweetspot:9594CS26Q0053"],
    },
    {
        "lane_id": "defense_energy_consortium",
        "name": "Defense Energy Consortium CMO",
        "channel": "federal_contract",
        "source_kind": "sweetspot_federal_search",
        "evidence_date": "2026-07-09",
        "deadline_or_gate": "Active until 2026-07-30 19:00 UTC per Sweetspot search.",
        "status": "PARTNER_INTRO_ONLY",
        "fit_score": 58,
        "priority": 13,
        "traction_evidence": [
            "Energy resilience and facility-management language can map to proof-to-pilot evidence workflows.",
            "The prime role appears to require consortium management and private-capital mobilization beyond current solo posture.",
        ],
        "reviewer_action": "Use as investor/strategic-partner conversation material, not immediate solo proposal.",
        "human_gate": "Human approves any partner or investor intro.",
        "claim_boundary": "No consortium management, energy project financing, or installation-performance claim.",
        "source_refs": ["sweetspot:FA8003-26-R-0023"],
    },
    {
        "lane_id": "openai_api_continuity",
        "name": "OpenAI API continuity request",
        "channel": "vendor_credit_or_partner_route",
        "source_kind": "gmail_plus_official_page",
        "evidence_date": "2026-07-08",
        "deadline_or_gate": "No deadline found; request should be submitted through official contact-sales path if still needed.",
        "status": "HUMAN_FORM_READY",
        "fit_score": 80,
        "priority": 14,
        "traction_evidence": [
            "Self-sent packet frames API continuity as a blocker for grant factory and proof-stack maintenance.",
            "Official contact-sales page is the clean route for enterprise/startup routing.",
        ],
        "reviewer_action": "Submit or update the official contact request with conservative proof-to-pilot framing.",
        "human_gate": "Human submits the vendor form and approves any billing or credit terms.",
        "claim_boundary": "No credit, free account, or vendor approval is represented.",
        "source_refs": ["gmail:19f43a156bcf0ab6", "public:openai_contact_sales"],
    },
    {
        "lane_id": "patent_deadline_counsel",
        "name": "Patent counsel / IP deadline defense",
        "channel": "ip_readiness",
        "source_kind": "gmail_plus_uspto_public_guidance",
        "evidence_date": "2026-07-08",
        "deadline_or_gate": "Dossier email states a July 25, 2025 filing date; counsel must verify all actual patent deadlines before action.",
        "status": "URGENT_COUNSEL_WATCH",
        "fit_score": 100,
        "priority": 15,
        "traction_evidence": [
            "Patent counsel outreach was sent with application number, title, and requested limited-scope/pro bono routing.",
            "USPTO public guidance confirms provisional-to-nonprovisional timing is deadline-sensitive when applicable.",
        ],
        "reviewer_action": "Monitor replies, prepare filed-materials packet, and avoid public claim expansion until counsel reviews.",
        "human_gate": "Human and licensed counsel decide any filing, claim, continuation, PCT, or disclosure action.",
        "claim_boundary": "This ledger is not legal advice and does not assert patentability, ownership, or filing sufficiency.",
        "source_refs": ["gmail:19f43b89dd51e2fd", "public:uspto_provisional", "public:uspto_utility"],
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


def lane_hash(lane: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(lane, sort_keys=True).encode("utf-8")).hexdigest()


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def build_payload() -> dict[str, Any]:
    lanes = []
    for lane in LANES:
        row = dict(lane)
        row["lane_sha256"] = lane_hash(row)
        row["human_gate_required"] = True
        lanes.append(row)

    status_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    source_kind_counts: dict[str, int] = {}
    for lane in lanes:
        status_counts[lane["status"]] = status_counts.get(lane["status"], 0) + 1
        channel_counts[lane["channel"]] = channel_counts.get(lane["channel"], 0) + 1
        source_kind_counts[lane["source_kind"]] = source_kind_counts.get(lane["source_kind"], 0) + 1

    public_ref_count = sum(
        1
        for lane in lanes
        for ref in lane["source_refs"]
        if str(ref).startswith("public:")
    )
    gmail_ref_count = sum(
        1
        for lane in lanes
        for ref in lane["source_refs"]
        if str(ref).startswith("gmail:")
    )
    sweetspot_ref_count = sum(
        1
        for lane in lanes
        for ref in lane["source_refs"]
        if str(ref).startswith("sweetspot:")
    )

    payload = {
        "generated_utc": now_utc(),
        "schema": "traction_opportunity_intake_ledger_v1",
        "status": "TRACTION_INTAKE_READY_HUMAN_ACTION_REQUIRED",
        "summary": {
            "lane_count": len(lanes),
            "top_priority_count": sum(1 for lane in lanes if int(lane["priority"]) <= 7),
            "gmail_reference_count": gmail_ref_count,
            "sweetspot_reference_count": sweetspot_ref_count,
            "public_reference_count": public_ref_count,
            "status_counts": dict(sorted(status_counts.items())),
            "channel_counts": dict(sorted(channel_counts.items())),
            "source_kind_counts": dict(sorted(source_kind_counts.items())),
            "human_action_required": True,
            "final_submission_allowed_without_human": False,
            "external_send_allowed_without_human": False,
        },
        "connected_evidence": CONNECTED_EVIDENCE,
        "public_sources": PUBLIC_SOURCES,
        "lanes": sorted(lanes, key=lambda item: int(item["priority"])),
        "next_actions": [
            "Prepare EVTit call packet and short technical walkthrough without meeting credentials.",
            "Advance NASA RFI and FHWA TSMO drafts into final human-review packages.",
            "Build DICE full-proposal compliance matrix after confirming controlling BAA instructions.",
            "Submit or refresh OpenAI API continuity request through official contact route if still needed.",
            "Monitor patent counsel replies and prepare filed-materials packet for licensed review.",
        ],
        "sanitization": {
            "public_packet_excludes_meeting_links": True,
            "public_packet_excludes_phone_numbers": True,
            "public_packet_excludes_financial_account_data": True,
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["ledger_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Traction Opportunity Intake Ledger - 2026-07-09",
        "",
        "Purpose: turn connected Gmail evidence, federal contract search, and official public sources into a reviewer-safe action queue.",
        "",
        "This ledger does not authorize portal submissions, email sends, certifications, calendar edits, IP filings, trading, or capital movement. It is an intake and prioritization artifact for human review.",
        "",
        "## Summary",
        "",
        f"- Status: `{payload['status']}`",
        f"- Lanes tracked: `{summary['lane_count']}`",
        f"- Top priority lanes: `{summary['top_priority_count']}`",
        f"- Gmail references: `{summary['gmail_reference_count']}`",
        f"- Sweetspot references: `{summary['sweetspot_reference_count']}`",
        f"- Public references: `{summary['public_reference_count']}`",
        f"- Human action required: `{str(summary['human_action_required']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Ledger SHA-256: `{payload['ledger_sha256']}`",
        "",
        "## Source Coverage",
        "",
    ]
    for key, value in payload["connected_evidence"].items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Priority Queue", ""])
    for lane in payload["lanes"]:
        lines.extend(
            [
                f"### {lane['priority']}. {lane['name']}",
                "",
                f"- Lane ID: `{lane['lane_id']}`",
                f"- Channel: `{lane['channel']}`",
                f"- Status: `{lane['status']}`",
                f"- Fit score: `{lane['fit_score']}`",
                f"- Gate: {lane['deadline_or_gate']}",
                f"- Reviewer action: {lane['reviewer_action']}",
                f"- Human gate: {lane['human_gate']}",
                f"- Claim boundary: {lane['claim_boundary']}",
                f"- Evidence hash: `{lane['lane_sha256']}`",
                "- Evidence:",
            ]
        )
        for item in lane["traction_evidence"]:
            lines.append(f"  - {item}")
        lines.append("- Sources:")
        for ref in lane["source_refs"]:
            lines.append(f"  - `{ref}`")
        lines.append("")
    lines.extend(["## Public Source Map", ""])
    for key, value in sorted(payload["public_sources"].items()):
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Immediate Next Actions", ""])
    for item in payload["next_actions"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Human-Only Boundary",
            "",
            "No final portal action, email send, certification, legal filing, pricing approval, account authorization, or investor term acceptance is authorized by this ledger.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public ledger markers: {sensitive_hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
