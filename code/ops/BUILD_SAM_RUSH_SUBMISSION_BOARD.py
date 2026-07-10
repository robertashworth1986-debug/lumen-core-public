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

OUT_JSON = OUT_OPS / "sam_rush_submission_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "sam_rush_submission_board.json"
OUT_MD = SPRINT_DIR / "SAM_RUSH_SUBMISSION_BOARD_2026-07-10.md"

SCAN_DATE = date(2026, 7, 10)

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
        "Sweetspot federal-contract searches were run on July 10, 2026 for active AI validation, "
        "transportation systems management, data-center infrastructure, cyber/cloud, and data-product opportunities."
    ),
    "sam_official": (
        "SAM.gov search results were used for official notice IDs, status snippets, and public opportunity URLs where available."
    ),
    "submission_boundary": (
        "This file prepares submission materials. It does not click final submit, certify representations, set pricing, "
        "or claim agency approval without human review."
    ),
}

OPPORTUNITIES: list[dict[str, Any]] = [
    {
        "rank": 1,
        "opportunity_id": "fhwa_tsmo_data_initiative",
        "title": "Transportation Systems Management and Operations Data Initiative",
        "solicitation_number": "693JJ326R000012",
        "agency": "Federal Highway Administration",
        "department": "Department of Transportation",
        "notice_type": "Solicitation",
        "set_aside": "Full and open",
        "deadline_utc": "2026-08-03T13:00:00Z",
        "submission_route": "SAM.gov / official solicitation instructions",
        "official_url": "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/bc3fd412-e7f6-578a-b86a-7ced6686e715",
        "posture": "PRIMARY_SUBMISSION_PACKAGE_READY_HUMAN_SUBMIT",
        "fit_score": 97,
        "urgency_score": 70,
        "award_fit": "Strongest solo or small-team agency fit.",
        "why_fit": (
            "The notice is explicitly about data barriers limiting AI in TSMO, prototype algorithms/models, "
            "prioritized use cases, and benchmarkable outcomes. LumenCore's measured-source proof stack, replay receipts, "
            "and validation ledger can be framed as the AI-readiness and prototype-evaluation layer."
        ),
        "submit_now_work": [
            "Use the existing FHWA Phase I technical capability outline as the base volume.",
            "Add a compliance matrix against the official solicitation attachments.",
            "Attach evidence-register excerpts only after reviewing attachment limits.",
            "Keep field-validation claims bounded to proposed pilots unless a transportation partner signs off.",
        ],
        "human_gates": [
            "Official attachments and amendments reviewed.",
            "Phase I volume, reps/certs, and any price/cost language approved by Robert.",
            "Final SAM.gov upload/submission preview approved by Robert.",
        ],
        "package_files": [
            "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
            "LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf",
            "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md",
        ],
    },
    {
        "rank": 2,
        "opportunity_id": "nasa_data_center_infrastructure_rfi",
        "title": "Strategic Partnerships for NASA Data Center Infrastructure",
        "solicitation_number": "80TECH26RFI0020",
        "agency": "NASA IT Procurement Office",
        "department": "National Aeronautics and Space Administration",
        "notice_type": "Sources Sought / RFI",
        "set_aside": "Market research",
        "deadline_utc": "2026-07-17T21:00:00Z",
        "submission_route": "Email response per RFI instructions",
        "official_url": "https://sam.gov/opp/312af51a7fc14110b1239bdd32252213/view",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/cd3ba4d9-cc57-52f7-8a10-95ac309aa0f4",
        "posture": "RFI_RESPONSE_READY_HUMAN_SEND",
        "fit_score": 91,
        "urgency_score": 90,
        "award_fit": "Fast RFI response, strong credibility signal.",
        "why_fit": (
            "NASA asked for strategic ideas for modern, resilient, secure, scalable, cost-effective data-center infrastructure, "
            "including hybrid/cloud approaches and AI-driven operations. LumenCore can offer a bounded validation and "
            "decision-evidence layer for comparing modernization paths before large capital commitments."
        ),
        "submit_now_work": [
            "Convert existing NASA outline into a 6-10 page RFI response.",
            "Use measured proof language: evidence manifest, replay harness, resilience scoring, governance receipts.",
            "State that no NASA production access or agency validation is claimed.",
        ],
        "human_gates": [
            "Confirm RFI email recipients and page limit from the official SAM notice.",
            "Approve any company capability, past-performance, and availability statements.",
            "Approve final email send.",
        ],
        "package_files": [
            "NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
            "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md",
        ],
    },
    {
        "rank": 3,
        "opportunity_id": "erdc_sovereign_defense_cloud_cso",
        "title": "Sovereign Defense Cloud for High-Performance Computing Commercial Solutions Opening",
        "solicitation_number": "W912HZ26SC005",
        "agency": "ERDC Information Technology Laboratory / HPCMP",
        "department": "Department of the Army",
        "notice_type": "Special Notice / CSO",
        "set_aside": "Full and open",
        "deadline_utc": "2026-08-07T21:00:00Z",
        "submission_route": "ERDCWERX Commercial Solutions Opening portal",
        "official_url": "https://sam.gov/opp/8e32f0dfcdee42eeb3b2b03819a6ed25/view",
        "secondary_url": "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/",
        "posture": "CSO_CONCEPT_READY_HUMAN_PORTAL_SUBMIT",
        "fit_score": 88,
        "urgency_score": 64,
        "award_fit": "Strong concept-paper lane if framed as a modular proof fabric, not a full cloud prime.",
        "why_fit": (
            "The CSO targets hybrid cloud, workflow automation, secure data fabric, portability, interoperability, "
            "and a sovereign AI-driven government capability. LumenCore can credibly propose a proof and validation fabric "
            "for measuring workflow reliability, data lineage, and governance readiness across HPC/cloud environments."
        ),
        "submit_now_work": [
            "Use ERDCWERX CSO route and select Commercial Solutions Opening.",
            "Frame LumenCore as a modular verification, replay, and evidence-control layer.",
            "Avoid claiming ownership of a complete sovereign cloud platform.",
        ],
        "human_gates": [
            "Open ERDCWERX form and confirm required fields.",
            "Approve solution title, commercial item framing, data-rights language, and any pricing.",
            "Approve final portal submit.",
        ],
        "package_files": [
            "ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md",
        ],
    },
    {
        "rank": 4,
        "opportunity_id": "doj_bop_historical_medical_claims_analysis",
        "title": "Historical Medical Claims Data Analysis",
        "solicitation_number": "15BCMS26Q70000005",
        "agency": "Federal Bureau of Prisons",
        "department": "Department of Justice",
        "notice_type": "Combined Synopsis/Solicitation",
        "set_aside": "Total small business set-aside",
        "deadline_utc": "2026-07-23T15:00:00Z",
        "submission_route": "Email quote per solicitation instructions",
        "official_url": "",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/8f7dec78-58cd-59be-bad1-d581c166f4a1",
        "posture": "QUOTE_STUB_READY_PRICE_AND_COMPLIANCE_GATE",
        "fit_score": 78,
        "urgency_score": 82,
        "award_fit": "Fast small-business analytics quote if requirements and pricing are supportable.",
        "why_fit": (
            "The work is bounded historical claims analysis with deliverable reports and a stated path for AI use if disclosed, "
            "kept out of model training, and human-reviewed. LumenCore can offer measured analytics, anomaly detection, "
            "human-reviewed findings, and transparent report custody."
        ),
        "submit_now_work": [
            "Build a quote response around fixed deliverables, human-reviewed analytics, and report formats.",
            "Explicitly disclose any AI-assisted analysis and prohibit government data training.",
            "Keep price, schedule, and responsibility determinations human-approved.",
        ],
        "human_gates": [
            "Download official solicitation and confirm deliverables, clauses, and quote format.",
            "Robert approves price and any past-performance statement.",
            "Final email quote approved by Robert.",
        ],
        "package_files": [
            "DOJ_BOP_MEDICAL_CLAIMS_ANALYSIS_QUOTE_STUB_2026-07-10.md",
        ],
    },
    {
        "rank": 5,
        "opportunity_id": "ustda_indo_pacific_digital_infrastructure_scoping",
        "title": "Indo-Pacific Digital Infrastructure Project Scoping Services",
        "solicitation_number": "1131PL26R0049",
        "agency": "United States Trade and Development Agency",
        "department": "USTDA",
        "notice_type": "Combined Synopsis/Solicitation",
        "set_aside": "Total small business set-aside",
        "deadline_utc": "2026-07-22T17:00:00Z",
        "submission_route": "SAM.gov / official solicitation instructions",
        "official_url": "https://sam.gov/workspace/contract/opp/fdefc4a420e04049a6a768f744d040c9/view",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/ee4a2cbe-98ea-56df-aef1-11106cf6105c",
        "posture": "PARTNER_OR_SCOPING_NOTE_ONLY",
        "fit_score": 72,
        "urgency_score": 84,
        "award_fit": "Possible consulting/scoping lane, better with a senior infrastructure partner.",
        "why_fit": (
            "The scope includes digital connectivity, cloud/data infrastructure, cybersecurity, digital public services, "
            "and AI applications. LumenCore can contribute a technical evaluation matrix and proof stack, but the lead likely "
            "needs international scoping and travel capacity."
        ),
        "submit_now_work": [
            "Prepare a narrow capability appendix for a prime or partner.",
            "Do not present as a full international infrastructure scoping prime without confirming travel and staffing.",
        ],
        "human_gates": [
            "Confirm staffing, travel, and project-report requirements.",
            "Decide whether to prime or partner.",
            "Approve any proposal or partner outreach.",
        ],
        "package_files": [
            "USTDA_INDO_PACIFIC_DIGITAL_INFRA_SCOPING_STUB_2026-07-10.md",
        ],
    },
    {
        "rank": 6,
        "opportunity_id": "army_aidp_rfi4",
        "title": "Army Intelligence Data Platform RFI #4",
        "solicitation_number": "ACCAPGAIDPRFI4",
        "agency": "Army Contracting Command - Aberdeen Proving Ground",
        "department": "Department of the Army",
        "notice_type": "Sources Sought / RFI",
        "set_aside": "Market research",
        "deadline_utc": "2026-07-15T21:00:00Z",
        "submission_route": "Email RFI feedback per official instructions",
        "official_url": "https://sam.gov/workspace/contract/opp/3d72f2df3aaf459797c14cefb41fd235/view",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/0c046e88-3d0d-5e26-bcc9-f78afc14164c",
        "posture": "PARTNER_CAPABILITY_NOTE_ONLY",
        "fit_score": 70,
        "urgency_score": 94,
        "award_fit": "Useful defense-data platform signal, not a solo-prime bid.",
        "why_fit": (
            "The RFI asks about modular data platform modernization across enterprise cloud and tactical edge. LumenCore can "
            "offer traceability, replay receipts, degraded-network evidence packs, and model/data validation as a module."
        ),
        "submit_now_work": [
            "Prepare a one-page partner note.",
            "Do not claim classified, SIPR, or full Army intelligence platform delivery capability.",
        ],
        "human_gates": [
            "Official markings and distribution reviewed.",
            "Partner or agency-contact route approved.",
            "Final send approved by Robert.",
        ],
        "package_files": [
            "ARMY_AIDP_RFI4_PARTNER_NOTE_STUB_2026-07-10.md",
        ],
    },
    {
        "rank": 7,
        "opportunity_id": "army_training_simulation_rfi",
        "title": "Request for Information: Training & Simulation",
        "solicitation_number": "W900KK-26-R-0001",
        "agency": "ACC-Orlando / PEO STRI",
        "department": "Department of the Army",
        "notice_type": "Special Notice / RFI",
        "set_aside": "Market research",
        "deadline_utc": "2026-08-15T21:00:00Z",
        "submission_route": "Email RFI feedback per official instructions",
        "official_url": "https://sam.gov/opp/e577d0eef9a84d51aa46bce6ed779233/view",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/937726e0-c87a-5c19-974c-f15392b57483",
        "posture": "WATCH_AND_PARTNER_FEEDBACK",
        "fit_score": 69,
        "urgency_score": 48,
        "award_fit": "Good longer-window validation/replay module lane.",
        "why_fit": (
            "The RFI is for an integrated LVC simulation environment with AI, commercial gaming, cloud computing, and realistic "
            "multi-domain training/test experimentation. LumenCore can contribute telemetry proof, scenario replay, and "
            "evaluation scorecards as a narrow validation module."
        ),
        "submit_now_work": [
            "Track as a partner lane after the urgent July deadlines.",
            "Prepare a validation/replay module paragraph for future partner conversations.",
        ],
        "human_gates": [
            "Confirm official status because search snippets showed active/inactive ambiguity.",
            "Approve partner or agency send route.",
        ],
        "package_files": [],
    },
    {
        "rank": 8,
        "opportunity_id": "fhwa_intersection_safety_systems_baa",
        "title": "Intersection Safety Systems Prototyping",
        "solicitation_number": "693JJ3-26-BAA-0004",
        "agency": "Federal Highway Administration",
        "department": "Department of Transportation",
        "notice_type": "Solicitation / BAA",
        "set_aside": "Full and open",
        "deadline_utc": "2026-07-20T19:00:00Z",
        "submission_route": "Email proposal per BAA instructions",
        "official_url": "",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/0f453e7c-d159-5512-b083-9ac58b3c4eb0",
        "posture": "PARTNER_ONLY_TESTBED_REQUIRED",
        "fit_score": 66,
        "urgency_score": 86,
        "award_fit": "Large potential, but requires jurisdiction/testbed team.",
        "why_fit": (
            "LumenCore can support conflict-prediction validation and evidence scoring, but the opportunity requires a lead system "
            "developer, public-sector jurisdiction partner, and access-controlled testbed operator."
        ),
        "submit_now_work": [
            "Do not solo-submit.",
            "Use as a field-validation partner target with cities, DOTs, universities, or testbed operators.",
        ],
        "human_gates": [
            "A qualified public-sector partner and testbed operator are confirmed.",
            "Team role, IP, and pricing are approved.",
        ],
        "package_files": [],
    },
    {
        "rank": 9,
        "opportunity_id": "hhs_ai_power_user_pilot",
        "title": "HHS AI Power User Advanced Models and Features Pilot",
        "solicitation_number": "7571TE26R00004",
        "agency": "Department of Health and Human Services",
        "department": "HHS",
        "notice_type": "Combined Synopsis/Solicitation",
        "set_aside": "Full and open",
        "deadline_utc": "2026-07-14T21:00:00Z",
        "submission_route": "SAM.gov / solicitation instructions",
        "official_url": "",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/f1005384-03c0-5bc7-be84-d193c876ddd8",
        "posture": "NO_SOLO_BID_PLATFORM_GATE",
        "fit_score": 52,
        "urgency_score": 96,
        "award_fit": "Partner intelligence only unless a compliant AI platform leads.",
        "why_fit": (
            "The measurement and telemetry language is relevant, but the buyer appears to need commercial AI platform access bundles "
            "and security-path documentation at production scale."
        ),
        "submit_now_work": [
            "Do not rush a solo bid.",
            "Use as evidence that agencies are buying AI baselines and telemetry.",
        ],
        "human_gates": [
            "Qualified platform partner identified.",
            "Security, pricing, and service obligations reviewed.",
        ],
        "package_files": [],
    },
    {
        "rank": 10,
        "opportunity_id": "air_force_16ws_cloud_platform_bpa",
        "title": "16WS Cloud Platform BPA",
        "solicitation_number": "FA460026Q0071",
        "agency": "16th Weather Squadron",
        "department": "Department of the Air Force",
        "notice_type": "Combined Synopsis/Solicitation",
        "set_aside": "Total small business set-aside",
        "deadline_utc": "2026-07-20T16:00:00Z",
        "submission_route": "Email quote per solicitation instructions",
        "official_url": "",
        "secondary_url": "https://console.sweetspotgov.com/federal-contracts/56c789df-7326-546d-8be5-82fefd289e30",
        "posture": "NO_BID_AWS_RESELLER_GATE",
        "fit_score": 35,
        "urgency_score": 86,
        "award_fit": "No-bid unless AWS resale partner status exists.",
        "why_fit": (
            "It mentions AI weather prototypes and cloud, but the procurement is mainly AWS credit resale under FedRAMP/DoD cloud rules."
        ),
        "submit_now_work": [
            "Skip unless AWS Partner Status for resale is confirmed.",
        ],
        "human_gates": [
            "AWS resale eligibility confirmed.",
            "Cloud compliance and quote terms approved.",
        ],
        "package_files": [],
    },
]

STUBS: dict[str, dict[str, Any]] = {
    "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md": {
        "title": "FHWA TSMO Phase I Submission Stub",
        "opportunity": "693JJ326R000012",
        "body": [
            "Submission posture: promote the existing FHWA TSMO Phase I outline into the official Phase I technical capability volume after checking the solicitation attachments.",
            "Proposed framing: LumenCore is a measured-source AI readiness and prototype-validation layer for TSMO use-case prioritization, data barrier diagnosis, algorithm/model benchmarking, and evidence-backed pilot design.",
            "Core proof points to include: evidence manifest, replay receipts, measured live-source registers, governance firewall, validation ladder, and field partner plan.",
            "Boundary language: LumenCore proposes validation and prototype support; it does not claim FHWA deployment, field safety improvement, or agency endorsement before award and pilot validation.",
        ],
    },
    "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md": {
        "title": "NASA Data Center Infrastructure RFI Response Stub",
        "opportunity": "80TECH26RFI0020",
        "body": [
            "Subject draft: Response to RFI 80TECH26RFI0020 - LumenCore strategic partnership concept for AI-ready infrastructure validation.",
            "Opening: LumenCore proposes a proof-to-decision validation layer for comparing on-premises, hybrid, and cloud modernization paths with evidence-backed resilience, cost, security, and operational-readiness scoring.",
            "Technical sections: measured-source evidence fabric, workload replay and benchmark planning, resilience/cost/energy decision ledger, governance receipts, and human-reviewed AI operations recommendations.",
            "Boundary language: This response is market-research input only. LumenCore is not claiming NASA production access, NASA validation, FedRAMP authorization, or realized savings.",
        ],
    },
    "ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md": {
        "title": "ERDC Sovereign Defense Cloud CSO Concept Stub",
        "opportunity": "W912HZ26SC005",
        "body": [
            "Solution title draft: LumenCore Proof Fabric for Sovereign HPC and AI Workflow Validation.",
            "Problem: Sovereign cloud and HPC modernization can fail when agencies cannot compare workflow reliability, data lineage, portability, and governance controls across hybrid environments.",
            "Solution: LumenCore supplies a modular proof fabric that creates replayable workflow receipts, validation scorecards, data-readiness ledgers, and governance evidence for cloud/HPC modernization decisions.",
            "Commercial item framing: modular software and technical services for validation, evidence capture, and decision support; final language requires legal and pricing review.",
            "Boundary language: LumenCore is not proposing to replace the entire HPCMP platform. It is a validation and evidence-control module that can support prime integrators or government technical teams.",
        ],
    },
    "DOJ_BOP_MEDICAL_CLAIMS_ANALYSIS_QUOTE_STUB_2026-07-10.md": {
        "title": "DOJ/BOP Historical Medical Claims Analysis Quote Stub",
        "opportunity": "15BCMS26Q70000005",
        "body": [
            "Quote posture: only proceed after official solicitation download, clause review, and price approval.",
            "Technical approach: ingest historical claims datasets, profile data quality, map diagnostic/procedure/revenue-code patterns, identify anomalies and utilization/cost drivers, and deliver searchable PDF/editable reports within the required window if confirmed.",
            "AI disclosure draft: Any AI-assisted analytics would be used only for pattern discovery and report drafting support. Government data would not be used to train commercial models, and all findings would receive human review before delivery.",
            "Boundary language: Price, responsibility, cybersecurity handling, and past-performance statements require Robert's approval before any quote email is sent.",
        ],
    },
    "USTDA_INDO_PACIFIC_DIGITAL_INFRA_SCOPING_STUB_2026-07-10.md": {
        "title": "USTDA Indo-Pacific Digital Infrastructure Scoping Stub",
        "opportunity": "1131PL26R0049",
        "body": [
            "Submission posture: partner or prime only if staffing, travel, and scoping-report requirements are confirmed.",
            "LumenCore role: technical evaluation matrix for cloud/data infrastructure, cybersecurity, digital public services, and AI-readiness proposals; proof-led risk scoring for grant-funded activity design.",
            "Partner target: infrastructure advisory firm, university center, telecom/cloud integrator, or international development contractor with Indo-Pacific field capacity.",
            "Boundary language: Do not claim full international scoping capacity, embassy coordination experience, or regional deployment history without a qualified partner.",
        ],
    },
    "ARMY_AIDP_RFI4_PARTNER_NOTE_STUB_2026-07-10.md": {
        "title": "Army AIDP RFI #4 Partner Note Stub",
        "opportunity": "ACCAPGAIDPRFI4",
        "body": [
            "Partner note posture: narrow module, not a full intelligence data platform proposal.",
            "LumenCore module: traceable data-product validation, replay receipts, AI-ready table governance, degraded-network evidence packets, and modular scoring for tactical-edge data workflows.",
            "Use case: help a prime demonstrate how raw data is converted into validated decision products with audit-ready lineage and human-review controls.",
            "Boundary language: Do not claim classified environment operations, SIPR delivery, or full AIDP implementation capability in a solo response.",
        ],
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    if days <= 14:
        return "two_week_sprint"
    if days <= 31:
        return "thirty_day_sprint"
    return "watchlist"


def action_bucket(posture: str) -> str:
    if "PRIMARY" in posture or "READY_HUMAN" in posture or "QUOTE_STUB_READY" in posture:
        return "submit_ready_human_gate"
    if "PARTNER" in posture or "WATCH" in posture:
        return "partner_or_watch"
    if "NO_" in posture:
        return "no_bid"
    return "review"


def enrich_opportunity(opp: dict[str, Any]) -> dict[str, Any]:
    row = dict(opp)
    days = days_to_deadline(str(row["deadline_utc"]))
    row["days_to_deadline_from_2026_07_10"] = days
    row["deadline_bucket"] = classify_deadline(days)
    row["action_bucket"] = action_bucket(str(row["posture"]))
    row["human_gate_required"] = True
    row["external_send_allowed_without_human"] = False
    row["final_submission_allowed_without_human"] = False
    row["pricing_allowed_without_human"] = False
    row["opportunity_sha256"] = stable_sha256(row)
    return row


def build_payload() -> dict[str, Any]:
    opportunities = [enrich_opportunity(opp) for opp in OPPORTUNITIES]
    opportunities = sorted(opportunities, key=lambda row: (row["rank"], -int(row["fit_score"])))
    submit_ready = [row for row in opportunities if row["action_bucket"] == "submit_ready_human_gate"]
    partner_watch = [row for row in opportunities if row["action_bucket"] == "partner_or_watch"]
    no_bid = [row for row in opportunities if row["action_bucket"] == "no_bid"]
    urgent = [row for row in opportunities if 0 <= row["days_to_deadline_from_2026_07_10"] <= 14]

    payload = {
        "schema": "sam_rush_submission_board_v1",
        "generated_utc": now_utc(),
        "scan_date": SCAN_DATE.isoformat(),
        "status": "SAM_RUSH_BOARD_READY_HUMAN_SUBMIT_REQUIRED",
        "summary": {
            "opportunity_count": len(opportunities),
            "submit_ready_human_gate_count": len(submit_ready),
            "partner_or_watch_count": len(partner_watch),
            "no_bid_count": len(no_bid),
            "urgent_14_day_count": len(urgent),
            "top_submission_lane": "693JJ326R000012 FHWA TSMO Data Initiative",
            "fastest_rfi_lane": "80TECH26RFI0020 NASA Data Center Infrastructure RFI",
            "strongest_cso_lane": "W912HZ26SC005 ERDC Sovereign Defense Cloud CSO",
            "fast_small_business_lane": "15BCMS26Q70000005 DOJ/BOP Historical Medical Claims Data Analysis",
            "human_action_required": True,
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "pricing_allowed_without_human": False,
            "legal_certification_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "source_notes": SOURCE_NOTES,
        "opportunities": opportunities,
        "submit_ready_human_gate": [
            {
                "rank": row["rank"],
                "title": row["title"],
                "solicitation_number": row["solicitation_number"],
                "deadline_utc": row["deadline_utc"],
                "posture": row["posture"],
                "submission_route": row["submission_route"],
                "package_files": row["package_files"],
            }
            for row in submit_ready
        ],
        "partner_or_watch": [
            {
                "rank": row["rank"],
                "title": row["title"],
                "solicitation_number": row["solicitation_number"],
                "deadline_utc": row["deadline_utc"],
                "posture": row["posture"],
            }
            for row in partner_watch
        ],
        "no_bid_or_do_not_prime": [
            {
                "rank": row["rank"],
                "title": row["title"],
                "solicitation_number": row["solicitation_number"],
                "deadline_utc": row["deadline_utc"],
                "posture": row["posture"],
            }
            for row in no_bid
        ],
        "submission_rule": {
            "can_prepare": True,
            "can_open_pages": True,
            "can_create_drafts": True,
            "can_final_submit_without_human": False,
            "must_stop_before": [
                "legal certification",
                "final portal submit",
                "price offer",
                "term acceptance",
                "signature",
                "claim of agency validation or award",
            ],
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
            "stub_files": [f"grant_submissions/funding_sprint_20260709/{name}" for name in STUBS],
        },
    }
    payload["board_sha256"] = stable_sha256(payload)
    return payload


def render_stub(filename: str, stub: dict[str, Any]) -> str:
    lines = [
        f"# {stub['title']} - 2026-07-10",
        "",
        f"- Opportunity: `{stub['opportunity']}`",
        "- Status: `DRAFT_READY_HUMAN_REVIEW_REQUIRED`",
        "- External send without human: `false`",
        "- Final submission without human: `false`",
        "- Pricing/certification without human: `false`",
        "",
        "## Draft Core",
        "",
    ]
    for item in stub["body"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Final Human Gate",
            "",
            "- Confirm official deadline, submission route, attachment limits, and clauses from the live notice.",
            "- Confirm entity/SAM status and required representations.",
            "- Robert approves the final text, any price, any past-performance statement, and the final submit/send action.",
            "",
            f"Stub file: `{filename}`",
        ]
    )
    return "\n".join(lines) + "\n"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# SAM Rush Submission Board - 2026-07-10",
        "",
        "Purpose: convert the July 10 SAM/federal opportunity sweep into a ranked submission board and draft packet map.",
        "",
        "Direct answer: pursue the four submit-ready lanes first, keep partner-only lanes out of final submission until qualified partners or credentials are confirmed, and skip no-bid lanes that would fail compliance.",
        "",
        "This board prepares submissions. It does not authorize final SAM.gov/portal submit, legal certification, pricing, signature, term acceptance, or agency-validation claims without human review.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Scan date: `{payload['scan_date']}`",
        f"- Opportunities reviewed: `{summary['opportunity_count']}`",
        f"- Submit-ready human-gated lanes: `{summary['submit_ready_human_gate_count']}`",
        f"- Partner/watch lanes: `{summary['partner_or_watch_count']}`",
        f"- No-bid lanes: `{summary['no_bid_count']}`",
        f"- Urgent within 14 days: `{summary['urgent_14_day_count']}`",
        f"- Top submission lane: `{summary['top_submission_lane']}`",
        f"- Fastest RFI lane: `{summary['fastest_rfi_lane']}`",
        f"- Strongest CSO lane: `{summary['strongest_cso_lane']}`",
        f"- Fast small-business lane: `{summary['fast_small_business_lane']}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Pricing without human: `{str(summary['pricing_allowed_without_human']).lower()}`",
        f"- Legal certification without human: `{str(summary['legal_certification_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Board SHA-256: `{payload['board_sha256']}`",
        "",
        "## Submit-Ready, Human-Gated",
        "",
    ]
    for row in payload["submit_ready_human_gate"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['title']}",
                "",
                f"- Solicitation: `{row['solicitation_number']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Posture: `{row['posture']}`",
                f"- Submission route: {row['submission_route']}",
                "- Package files:",
            ]
        )
        for file in row["package_files"]:
            lines.append(f"  - `{file}`")
        lines.append("")

    lines.extend(["## Full Opportunity Board", ""])
    for opp in payload["opportunities"]:
        lines.extend(
            [
                f"### {opp['rank']}. {opp['title']}",
                "",
                f"- Solicitation: `{opp['solicitation_number']}`",
                f"- Agency: `{opp['agency']}`",
                f"- Department: `{opp['department']}`",
                f"- Notice type: `{opp['notice_type']}`",
                f"- Set-aside: `{opp['set_aside']}`",
                f"- Deadline UTC: `{opp['deadline_utc']}`",
                f"- Days from 2026-07-10: `{opp['days_to_deadline_from_2026_07_10']}`",
                f"- Deadline bucket: `{opp['deadline_bucket']}`",
                f"- Action bucket: `{opp['action_bucket']}`",
                f"- Fit score: `{opp['fit_score']}`",
                f"- Urgency score: `{opp['urgency_score']}`",
                f"- Posture: `{opp['posture']}`",
                f"- Award fit: {opp['award_fit']}",
                f"- Official URL: {opp['official_url'] or 'Official SAM URL not resolved in public search; verify inside SAM.gov before action.'}",
                f"- Secondary URL: {opp['secondary_url']}",
                f"- Why fit: {opp['why_fit']}",
                "- Submit-now work:",
            ]
        )
        for item in opp["submit_now_work"]:
            lines.append(f"  - {item}")
        lines.append("- Human gates:")
        for gate in opp["human_gates"]:
            lines.append(f"  - {gate}")
        if opp["package_files"]:
            lines.append("- Package files:")
            for file in opp["package_files"]:
                lines.append(f"  - `{file}`")
        lines.append("")

    lines.extend(["## Submission Rule", ""])
    for key, value in payload["submission_rule"].items():
        if isinstance(value, list):
            lines.append(f"- {key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Source Notes", ""])
    for key, value in payload["source_notes"].items():
        lines.append(f"- `{key}`: {value}")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    sensitive_hits = scan_sensitive_text(markdown)
    if sensitive_hits:
        raise SystemExit(f"Refusing to write sensitive public board markers: {sensitive_hits}")

    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    for filename, stub in STUBS.items():
        rendered = render_stub(filename, stub)
        stub_hits = scan_sensitive_text(rendered)
        if stub_hits:
            raise SystemExit(f"Refusing to write sensitive public stub markers in {filename}: {stub_hits}")
        write_text(SPRINT_DIR / filename, rendered)

    print(
        json.dumps(
            {
                "status": payload["status"],
                "opportunities": payload["summary"]["opportunity_count"],
                "submit_ready_human_gate": payload["summary"]["submit_ready_human_gate_count"],
                "markdown": rel(OUT_MD),
                "stub_files": len(STUBS),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
