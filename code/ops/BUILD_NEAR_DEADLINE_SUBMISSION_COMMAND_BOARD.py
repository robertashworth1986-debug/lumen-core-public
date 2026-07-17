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

SAM_BOARD = OUT_OPS / "sam_rush_submission_board_latest.json"
GRANTS_RANKED = ROOT / "out" / "grants" / "grants_ranked_v2.json"
ZERO_FRICTION = OUT_OPS / "funding_reviewer_zero_friction_pack_latest.json"
SUBMISSION_RECEIPT = SPRINT_DIR / "EXTERNAL_SUBMISSION_RECEIPT_2026-07-13.json"
CDC_ENGAGEMENT_RECEIPT = (
    SPRINT_DIR / "CDC_AI_ACQUISITION_RFI_ENGAGEMENT_RECEIPT_2026-07-16.json"
)
DOJ_BOP_DECISION = (
    ROOT
    / "grant_submissions"
    / "DOJ_BOP_15BCMS26Q70000005"
    / "DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md"
)
DOJ_BOP_SOURCE_MANIFEST = (
    ROOT
    / "grant_submissions"
    / "DOJ_BOP_15BCMS26Q70000005"
    / "DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json"
)
NSF_PITCH_DIR = ROOT / "grant_submissions" / "NSF_Project_Pitch"
NSF_PORTAL_FIELDS = NSF_PITCH_DIR / "PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md"
NSF_ROUTING_MANIFEST = (
    NSF_PITCH_DIR / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json"
)
NASHVILLE_EC_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
NASHVILLE_EC_FIELD_MAP = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md"
)
NASHVILLE_EC_MANIFEST = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
)
NASHVILLE_EC_FACT_RESOLUTION_JSON = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.json"
)
NASHVILLE_EC_FACT_RESOLUTION_MD = (
    NASHVILLE_EC_DIR / "NASHVILLE_EC_HUMAN_FACT_RESOLUTION_2026-07-16.md"
)
EXTERNAL_ENGAGEMENT_REGISTER = (
    SPRINT_DIR / "EXTERNAL_ENGAGEMENT_RESPONSE_REGISTER_2026-07-16.json"
)
SAM_KEY_ROTATION_CONTROL = (
    SPRINT_DIR / "SAM_PUBLIC_CREDENTIAL_ROTATION_CONTROL_2026-07-16.json"
)
PATENT_DEADLINE_CONTROL = (
    SPRINT_DIR / "PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json"
)

OUT_JSON = OUT_OPS / "near_deadline_submission_command_board_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "near_deadline_submission_command_board.json"
SCAN_DATE = date.today()
OUT_MD = SPRINT_DIR / f"NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_{SCAN_DATE.isoformat()}.md"

STAGE_COMMANDS = {
    "STAGE_NOW",
    "STAGE_RFI_FEEDBACK",
    "BUILD_PRIMARY_VOLUME",
    "STAGE_PROJECT_PITCH",
    "STAGE_CONCEPT_PAPER",
    "STAGE_APPLICATION",
}
NO_BID_COMMANDS = {
    "NO_BID_MISSED_PREREQUISITE",
    "NO_SOLO_SUBMIT_PARTNER_ONLY",
    "PARTNER_OR_NO_BID",
}
EXPIRED_COMMAND = "EXPIRED_NO_SUBMISSION"

SENSITIVE_MARKERS = [
    "password",
    "meeting id",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key=",
    "sk-",
    "xox",
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def deadline_bucket(days: int | None) -> str:
    if days is None:
        return "unknown"
    if days < 0:
        return "past_due"
    if days <= 2:
        return "48_hour_sprint"
    if days <= 7:
        return "seven_day_sprint"
    if days <= 14:
        return "two_week_sprint"
    if days <= 31:
        return "thirty_day_sprint"
    return "later"


def days_to_close(deadline_date: str, scan_date: date = SCAN_DATE) -> int:
    return (date.fromisoformat(deadline_date) - scan_date).days


def normalize_lane_deadlines(
    lanes: list[dict[str, Any]], scan_date: date = SCAN_DATE
) -> None:
    for lane in lanes:
        deadline_date = str(lane.get("deadline_date") or lane.get("deadline_utc", "")[:10])
        lane["deadline_date"] = deadline_date
        days = days_to_close(deadline_date, scan_date)
        lane["days_to_close"] = days
        lane["days_to_close_from_scan_date"] = days
        lane["deadline_bucket"] = deadline_bucket(days)


def sam_lookup(sam_board: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("solicitation_number")): row
        for row in sam_board.get("opportunities", [])
        if row.get("solicitation_number")
    }


def grant_lookup(grants: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for row in grants.get("ranked", []):
        opp_num = str(row.get("opp_num") or "")
        if opp_num:
            rows[opp_num] = row
    return rows


def base_sources() -> dict[str, Any]:
    sources = {}
    for key, path in {
        "sam_rush_board": SAM_BOARD,
        "grants_ranked": GRANTS_RANKED,
        "funding_reviewer_zero_friction_pack": ZERO_FRICTION,
        "external_submission_receipt": SUBMISSION_RECEIPT,
        "cdc_engagement_receipt": CDC_ENGAGEMENT_RECEIPT,
        "doj_bop_go_no_go": DOJ_BOP_DECISION,
        "doj_bop_source_manifest": DOJ_BOP_SOURCE_MANIFEST,
        "nsf_project_pitch_portal_fields": NSF_PORTAL_FIELDS,
        "nsf_project_pitch_routing_manifest": NSF_ROUTING_MANIFEST,
        "nashville_ec_portal_field_map": NASHVILLE_EC_FIELD_MAP,
        "nashville_ec_application_manifest": NASHVILLE_EC_MANIFEST,
        "nashville_ec_human_fact_resolution": NASHVILLE_EC_FACT_RESOLUTION_JSON,
        "external_engagement_response_register": EXTERNAL_ENGAGEMENT_REGISTER,
        "sam_public_key_rotation_control": SAM_KEY_ROTATION_CONTROL,
        "patent_deadline_evidence_control": PATENT_DEADLINE_CONTROL,
    }.items():
        if path.exists():
            data = path.read_bytes()
            sources[key] = {
                "path": rel(path),
                "present": True,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        else:
            sources[key] = {"path": rel(path), "present": False}
    return sources


def apply_submission_receipts(lanes: list[dict[str, Any]], receipt: dict[str, Any]) -> None:
    sent_by_notice = {
        str(row.get("notice_id")): row
        for row in receipt.get("submissions", [])
        if str(row.get("result", "")).startswith("SENT_")
    }
    for lane in lanes:
        sent = sent_by_notice.get(str(lane.get("opportunity_number")))
        if sent is None:
            continue
        lane["pre_send_command"] = lane["command"]
        lane["command"] = "SENT_VERIFIED"
        lane["submission_status"] = sent["result"]
        lane["sent_utc"] = sent["sent_utc"]
        lane["receipt_path"] = rel(SUBMISSION_RECEIPT)
        lane["receipt_attachment_sha256"] = sent["attachment_sha256"]
        lane["today_work"] = [
            "Monitor for an inbound response, amendment, or clarification request.",
            "Do not resend unless the agency requests a replacement or the receipt fails verification.",
        ]
        lane["human_gate"] = []


def build_cdc_receipt_lane(receipt: dict[str, Any]) -> dict[str, Any] | None:
    opportunity = receipt.get("opportunity", {})
    submission = receipt.get("submission", {})
    acknowledgment = receipt.get("acknowledgment", {})
    if (
        receipt.get("schema") != "lumencore.external_engagement_receipt.v1"
        or opportunity.get("notice_id") != "75D301-26-RFI-73483"
        or acknowledgment.get("status") != "RECEIPT_CONFIRMED_FOLLOW_UP_PENDING"
    ):
        return None
    attachment = submission.get("attachment", {})
    return {
        "rank": 2.5,
        "lane_id": "cdc_ai_acquisition_rfi",
        "source_system": "SAM.gov / Gmail receipt",
        "opportunity_number": "75D301-26-RFI-73483",
        "title": opportunity.get(
            "title", "CDC Artificial Intelligence for Acquisition Support"
        ),
        "agency": opportunity.get(
            "agency", "Centers for Disease Control and Prevention"
        ),
        "deadline_utc": "2026-07-30T21:00:00Z",
        "deadline_date": "2026-07-30",
        "official_deadline_text": "July 30, 2026 at 5:00 PM Eastern Time",
        "command": "SENT_VERIFIED",
        "eligibility_state": "RFI_MARKET_RESEARCH_RESPONSE_RECEIVED",
        "fit_state": "BOUNDED_AI_ACQUISITION_EVIDENCE_RESPONSE_DELIVERED",
        "submission_route": "Email response per the official RFI instructions",
        "official_url": "https://sam.gov/opp/3b42d94270da435fa690c2fc5f26e157/view",
        "package_files": [
            "CDC_AI_ACQUISITION_RFI_75D301-26-RFI-73483_2026-07-15.md",
            "LumenCore_CDC_AI_Acquisition_RFI_75D301-26-RFI-73483_2026-07-15.pdf",
            CDC_ENGAGEMENT_RECEIPT.name,
        ],
        "why_now": (
            "CDC confirmed receipt and said it will follow up. Preserve the receipt and "
            "monitor; do not duplicate-send."
        ),
        "today_work": [
            "Monitor the existing Gmail thread for a CDC clarification or follow-up.",
            "Do not resend unless CDC asks for a replacement or additional material.",
        ],
        "human_gate": [],
        "external_send_allowed_without_human": False,
        "final_submit_allowed_without_human": False,
        "submission_status": acknowledgment["status"],
        "sent_utc": submission.get("sent_utc"),
        "receipt_path": rel(CDC_ENGAGEMENT_RECEIPT),
        "receipt_attachment_sha256": attachment.get("sha256"),
        "claim_boundary": receipt.get("claim_boundary"),
    }


def expire_closed_lanes(lanes: list[dict[str, Any]]) -> None:
    protected = {"SENT_VERIFIED", *NO_BID_COMMANDS, EXPIRED_COMMAND}
    for lane in lanes:
        if lane["days_to_close"] >= 0 or lane["command"] in protected:
            continue
        lane["pre_expiry_command"] = lane["command"]
        lane["command"] = EXPIRED_COMMAND
        lane["submission_status"] = "DEADLINE_PASSED_NO_VERIFIED_SEND"
        lane["why_now"] = (
            "The response deadline passed without a verified transmission receipt. "
            "This lane is archival and must not be represented as submitted."
        )
        lane["today_work"] = [
            "Archive the lane as missed; do not imply a submission occurred.",
            "Retain reusable public-safe material only for a future verified opportunity.",
        ]
        lane["human_gate"] = []


def build_command_lanes(
    sam_board: dict[str, Any],
    grants_ranked: dict[str, Any],
    submission_receipt: dict[str, Any] | None = None,
    cdc_engagement_receipt: dict[str, Any] | None = None,
    scan_date: date = SCAN_DATE,
) -> list[dict[str, Any]]:
    sam = sam_lookup(sam_board)
    grants = grant_lookup(grants_ranked)

    nasa = sam.get("80TECH26RFI0020", {})
    fhwa = sam.get("693JJ326R000012", {})
    erdc = sam.get("W912HZ26SC005", {})
    bop = sam.get("15BCMS26Q70000005", {})
    nsf = grants.get("26-510", {})
    hud = grants.get("PDR-2600-DC-029Q", {})
    hhs_child = grants.get("HHS-2026-ACF-ACYF-CA-0037", {})

    lanes: list[dict[str, Any]] = [
        {
            "rank": 1,
            "lane_id": "nasa_data_center_rfi",
            "source_system": "SAM.gov",
            "opportunity_number": "80TECH26RFI0020",
            "title": nasa.get("title", "Strategic Partnerships for NASA Data Center Infrastructure"),
            "agency": nasa.get("agency", "NASA IT Procurement Office"),
            "deadline_utc": nasa.get("deadline_utc", "2026-07-17T21:00:00Z"),
            "deadline_date": "2026-07-17",
            "command": "STAGE_NOW",
            "eligibility_state": "OPEN_RFI_RESPONSE",
            "fit_state": "STRONG_CAPABILITY_RESPONSE_FIT",
            "submission_route": nasa.get("submission_route", "Email response per RFI instructions"),
            "official_url": nasa.get("official_url", "https://sam.gov/opp/312af51a7fc14110b1239bdd32252213/view"),
            "package_files": nasa.get(
                "package_files",
                [
                    "NASA_DATA_CENTER_RFI_RESPONSE_OUTLINE_2026-07-09.md",
                    "NASA_DATA_CENTER_RFI_RESPONSE_STUB_2026-07-10.md",
                ],
            )
            + [
                "NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.md",
                "NASA_DATA_CENTER_RFI_READY_RESPONSE_2026-07-11.pdf",
                "NASA_DATA_CENTER_RFI_EMAIL_DRAFT_2026-07-11.md",
            ],
            "why_now": "Fastest clean federal market-research lane: no pricing needed, response can be bounded to capability, proof-to-decision validation, and no agency-validation claims.",
            "today_work": [
                "Confirm official RFI email recipients, page cap, attachments, and amendments.",
                "Promote the NASA outline/stub into a reviewer-ready RFI response.",
                "Stage email subject/body and attachment list for human approval.",
            ],
            "human_gate": [
                "Robert approves final capability language and any past-performance statement.",
                "Robert approves the final email send.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 1.5,
            "lane_id": "nashville_ec_fall_2026_takeoff",
            "source_system": "Nashville Entrepreneur Center official site / Gmail newsletter",
            "opportunity_number": "NASHVILLE-EC-FALL-2026",
            "title": "Nashville Entrepreneur Center Fall 2026 Accelerators",
            "agency": "Nashville Entrepreneur Center",
            "deadline_utc": None,
            "deadline_date": "2026-07-17",
            "official_deadline_text": (
                "Applications close July 17, 2026; the official page does not list a "
                "closing time"
            ),
            "deadline_semantics": "DATE_ONLY_CLOSE_TIME_NOT_LISTED_SUBMIT_EARLY",
            "command": "STAGE_APPLICATION",
            "eligibility_state": "MIDDLE_TENNESSEE_SOLO_FOUNDER_FIT_HUMAN_FACTS_UNVERIFIED",
            "fit_state": "STRONG_TAKEOFF_MVP_AND_CUSTOMER_VALIDATION_FIT",
            "submission_route": "Nashville Entrepreneur Center common accelerator application",
            "official_url": "https://ec.co/apply/",
            "secondary_url": "https://ec.co/accelerators/takeoff/",
            "package_files": [
                rel(NASHVILLE_EC_FIELD_MAP),
                rel(NASHVILLE_EC_MANIFEST),
                rel(NASHVILLE_EC_FACT_RESOLUTION_JSON),
                rel(NASHVILLE_EC_FACT_RESOLUTION_MD),
            ],
            "why_now": (
                "This is the nearest legitimate local reviewer and commercialization route. "
                "TakeOff fits a Nashville-based solo founder with a working MVP and no "
                "claimed customers. The listed $500 program fee and $125 start payment are "
                "not authorized; the application should answer no on fee readiness and "
                "request financial aid before accepting terms."
            ),
            "today_work": [
                "Collect the six concise founder confirmations in the human-fact resolution artifact.",
                "Paste the claim-bounded answers into the common application and select TakeOff.",
                "Stop at final preview; do not accept a fee, terms, or cohort seat during application staging.",
            ],
            "human_gate": [
                "Robert answers all six prompts covering founder status, weekly hours, conversation count, revenue, founder investment, received funding, and business debt.",
                "Robert reviews the final portal preview and approves submission before the July 17 close.",
                "Any later program fee, financial-aid arrangement, terms, or cohort acceptance requires a separate decision.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 3,
            "lane_id": "fhwa_tsmo_data_initiative",
            "source_system": "SAM.gov",
            "opportunity_number": "693JJ326R000012",
            "title": fhwa.get("title", "Transportation Systems Management and Operations Data Initiative"),
            "agency": fhwa.get("agency", "Federal Highway Administration"),
            "deadline_utc": fhwa.get("deadline_utc", "2026-08-03T13:00:00Z"),
            "deadline_date": "2026-08-03",
            "command": "BUILD_PRIMARY_VOLUME",
            "eligibility_state": "SOLICITATION_REVIEW_REQUIRED",
            "fit_state": "STRONG_MEASUREMENT_AND_TSMO_FIT",
            "submission_route": fhwa.get("submission_route", "SAM.gov / official solicitation instructions"),
            "official_url": fhwa.get("official_url", "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view"),
            "package_files": fhwa.get(
                "package_files",
                [
                    "FHWA_TSMO_PHASE1_TECHNICAL_CAPABILITY_OUTLINE_2026-07-09.md",
                    "LUMENCORE_FHWA_TSMO_CAPABILITY_NOTE_693JJ326R000012_2026-07-09.pdf",
                    "FHWA_TSMO_PHASE1_SUBMISSION_STUB_2026-07-10.md",
                ],
            )
            + [
                "FHWA_TSMO_COMPLIANCE_MATRIX_DRAFT_2026-07-11.md",
            ],
            "why_now": "Best fit for LumenCore's measured-source validation story: TSMO data barriers, prototype algorithms, use-case prioritization, and evidence-backed evaluation.",
            "today_work": [
                "Download/review official attachments and amendments.",
                "Add a compliance matrix to the Phase I outline.",
                "Stage SAM.gov upload packet and hold at final preview.",
            ],
            "human_gate": [
                "Robert approves Phase I volume, reps/certs, and any price/cost language.",
                "Robert approves final SAM.gov submission preview.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 4,
            "lane_id": "nsf_sbir_project_pitch",
            "source_system": "NSF Seed Fund Project Pitch",
            "opportunity_number": "26-510",
            "title": nsf.get(
                "title",
                "NSF Small Business Innovation Research / Small Business Technology Transfer Programs Phase I",
            ),
            "agency": nsf.get("raw", {}).get("agency", "U.S. National Science Foundation"),
            "deadline_utc": None,
            "deadline_date": "2026-11-04",
            "deadline_semantics": "PROJECT_PITCH_GATE_ROLLING_FULL_PROPOSAL_INVITATION_REQUIRED",
            "project_pitch_due_date": None,
            "full_proposal_planning_deadline_date": "2026-11-04",
            "full_proposal_submission_allowed": False,
            "invitation_verified": False,
            "portal_state_verified": False,
            "official_deadline_text": (
                "Project Pitch is the current rolling gate; November 4, 2026 is a "
                "planning target for a full proposal only if NSF issues a valid invitation"
            ),
            "command": "STAGE_PROJECT_PITCH",
            "eligibility_state": "PROJECT_PITCH_REQUIRED_INVITATION_NOT_VERIFIED",
            "fit_state": "STRONG_TRUSTWORTHY_AI_FIT_26_510_26_511_STAFF_CONFIRMATION_REQUIRED",
            "submission_route": (
                "NSF Seed Fund Project Pitch now; Research.gov full proposal only after "
                "an official invitation"
            ),
            "official_url": "https://seedfund.nsf.gov/project-pitch/",
            "secondary_url": "https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation",
            "alternate_url": "https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology-0/nsf26-511/solicitation",
            "package_files": [
                rel(NSF_PORTAL_FIELDS),
                rel(NSF_PITCH_DIR / "PROJECT_PITCH_PASTE_CHECK_2026-07-16.md"),
                rel(NSF_ROUTING_MANIFEST),
                rel(NSF_PITCH_DIR / "PROJECT_PITCH_READINESS.md"),
            ],
            "why_now": (
                "This is the strongest grants-side route, but the immediate action is the "
                "rolling Project Pitch rather than a July 27 full proposal. NSF 26-510 is "
                "the cleaner general deep-technology fit; use 26-511 only if NSF confirms "
                "the software-defined scientific-instrumentation framing."
            ),
            "today_work": [
                "Confirm in the Project Pitch portal that no pitch is pending and no invitation or full proposal is open.",
                "Paste the four locally counted, claim-bounded fields from the canonical portal packet.",
                "Stop at final review so the legal company facts and submission certification can be checked.",
            ],
            "human_gate": [
                "Robert confirms the legal company profile, PI eligibility, and portal status.",
                "Robert reviews the final portal preview and approves the Project Pitch submission.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 10,
            "lane_id": "hud_robotics_ai_home_construction",
            "source_system": "Grants.gov / HUD",
            "opportunity_number": "PDR-2600-DC-029Q",
            "title": hud.get(
                "title",
                "Mass Market Solutions for Leveraging Robotics and AI Technologies for Home Construction Demonstration",
            ),
            "agency": hud.get("raw", {}).get("agency", "Department of Housing and Urban Development"),
            "deadline_utc": "2026-07-14T03:59:59Z",
            "deadline_date": "2026-07-13",
            "official_deadline_text": "July 13, 2026 at 11:59:59 PM Eastern Time",
            "command": "ELIGIBILITY_AND_PARTNER_GATE",
            "eligibility_state": "BUSINESS_ELIGIBILITY_POSSIBLE_PROJECT_CAPACITY_UNPROVEN",
            "fit_state": "TITLE_MATCH_ONLY_NO_CONSTRUCTION_DEMONSTRATION_EVIDENCE",
            "submission_route": "Grants.gov Workspace package if eligibility and demonstration facts are supportable",
            "official_url": "https://www.grants.gov/search-results-detail/362360",
            "package_files": [
                "HUD_ROBOTICS_AI_EMERGENCY_ELIGIBILITY_GATE_2026-07-11.md",
                "NEAR_DEADLINE_SUBMISSION_COMMAND_BOARD_2026-07-11.md",
                "FUNDING_REVIEWER_ZERO_FRICTION_PACK_2026-07-10.md",
            ],
            "why_now": "Deadline is closest and the title matches robotics/AI, but it likely needs a credible construction demonstration plan, budget, and project facts. Treat as emergency only if eligibility passes.",
            "today_work": [
                "Open Grants.gov package and confirm eligible applicant categories, required forms, and attachments.",
                "If eligible, draft a narrow AI/robotics validation-and-instrumentation demonstration narrative.",
                "Stop before budget, certifications, and final submission.",
            ],
            "human_gate": [
                "Robert confirms eligible applicant status and real project/demonstration facts.",
                "Robert approves all Grants.gov certifications and final submission.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 5,
            "lane_id": "erdc_sovereign_cloud_cso",
            "source_system": "SAM.gov / ERDCWERX",
            "opportunity_number": "W912HZ26SC005",
            "title": erdc.get("title", "Sovereign Defense Cloud for High-Performance Computing CSO"),
            "agency": erdc.get("agency", "ERDC Information Technology Laboratory / HPCMP"),
            "deadline_utc": erdc.get("deadline_utc", "2026-08-07T21:00:00Z"),
            "deadline_date": "2026-08-07",
            "official_deadline_text": "August 7, 2026 at 4:00 PM Central Time",
            "command": "STAGE_CONCEPT_PAPER",
            "eligibility_state": "OPEN_CSO_COMMERCIAL_SOLUTION",
            "fit_state": "STRONG_MODULAR_PROOF_FABRIC_COMPONENT_FIT",
            "submission_route": erdc.get("submission_route", "ERDCWERX Commercial Solutions Opening portal"),
            "official_url": erdc.get("official_url", "https://sam.gov/opp/8e32f0dfcdee42eeb3b2b03819a6ed25/view"),
            "secondary_url": erdc.get("secondary_url", "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/"),
            "package_files": erdc.get("package_files", ["ERDC_SOVEREIGN_DEFENSE_CLOUD_CSO_CONCEPT_STUB_2026-07-10.md"]),
            "why_now": "Good concept-paper lane if LumenCore is framed as a proof fabric module, not a full sovereign cloud prime.",
            "today_work": [
                "Open ERDCWERX and confirm form fields.",
                "Stage concept title, problem, modular solution, and data-rights boundary.",
            ],
            "human_gate": [
                "Robert approves title, commercial item framing, data rights, and any price.",
                "Robert approves final portal submit.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 6,
            "lane_id": "doj_bop_medical_claims_quote",
            "source_system": "SAM.gov",
            "opportunity_number": "15BCMS26Q70000005",
            "title": bop.get("title", "Historical Medical Claims Data Analysis"),
            "agency": bop.get("agency", "Federal Bureau of Prisons"),
            "deadline_utc": bop.get("deadline_utc", "2026-07-23T15:00:00Z"),
            "deadline_date": "2026-07-23",
            "official_deadline_text": "July 23, 2026 at 11:00 AM Eastern Time",
            "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
            "eligibility_state": "SMALL_BUSINESS_SET_ASIDE_SOLO_DELIVERY_GATES_NOT_MET",
            "fit_state": "ANALYTICS_COMPONENT_FIT_HIPAA_ATO_HSPD12_MEDICAL_CLAIMS_AND_FFP_GATES_OPEN",
            "submission_route": bop.get("submission_route", "Email quote per solicitation instructions"),
            "official_url": "https://sam.gov/opp/52680f2a89c241b3a055c35d816b7f20/view",
            "package_files": [
                "grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_SOURCE_MANIFEST_2026-07-16.json",
                "grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_GO_NO_GO_2026-07-16.md",
                "grant_submissions/DOJ_BOP_15BCMS26Q70000005/DOJ_BOP_15BCMS26Q70000005_PARTNER_OUTREACH_TEMPLATE_2026-07-16.md",
            ],
            "why_now": "Official-source review supports only a conditional partner route. LumenCore does not currently evidence the HIPAA officer, ATO/ISSO delivery capacity, screened personnel, medical-claims expertise, or firm-fixed-price delivery posture required for a responsible solo quote.",
            "today_work": [
                "Do not send a solo quote.",
                "Use the bounded partner template only if a qualified healthcare-claims and federal-security prime is identified.",
                "Require the partner to own compliance, staffing, pricing, and protected-data delivery commitments.",
            ],
            "human_gate": [
                "A qualified prime confirms HIPAA, ATO/ISSO, HSPD-12, medical-claims, and delivery responsibility in writing.",
                "Robert approves the partner outreach, role, price, representations, and any final quote.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
        {
            "rank": 14,
            "lane_id": "hhs_predictive_analytics_child_welfare",
            "source_system": "Grants.gov",
            "opportunity_number": "HHS-2026-ACF-ACYF-CA-0037",
            "title": hhs_child.get("title", "Predictive Analytics in Child Welfare Demonstration Grants"),
            "agency": hhs_child.get("raw", {}).get("agency", "Administration for Children and Families"),
            "deadline_utc": "2026-07-14T03:59:00Z",
            "deadline_date": "2026-07-13",
            "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
            "eligibility_state": "INELIGIBLE_AS_SOLO_SMALL_BUSINESS",
            "fit_state": "PARTNER_ONLY_CHILD_WELFARE_DOMAIN",
            "submission_route": "Partner with eligible public/tribal child-welfare agency only",
            "official_url": "https://www.grants.gov/search-results-detail/361912",
            "package_files": [],
            "why_now": "The title is relevant, but it is not a safe solo submission lane unless an eligible agency partner controls the application.",
            "today_work": [
                "Do not spend the sprint here unless an eligible agency partner is already available.",
                "Keep as a future proof-to-pilot target for predictive analytics ethics and validation.",
            ],
            "human_gate": [
                "Eligible agency partner identified and approves participation.",
                "Robert approves partner outreach or subrecipient role.",
            ],
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
        },
    ]

    lanes.extend(
        [
            {
                "rank": 2,
                "lane_id": "army_aidp_rfi4",
                "source_system": "SAM.gov",
                "opportunity_number": "ACCAPGAIDPRFI4",
                "title": "Army Intelligence Data Platform RFI #4",
                "agency": "U.S. Army Contracting Command - Aberdeen Proving Ground",
                "deadline_utc": "2026-07-15T21:00:00Z",
                "deadline_date": "2026-07-15",
                "official_deadline_text": "July 15, 2026 at 5:00 PM Eastern Time",
                "command": "STAGE_RFI_FEEDBACK",
                "eligibility_state": "OPEN_RFI_FEEDBACK_ATTACHMENT_ACCESS_REQUIRED",
                "fit_state": "STRONG_DATA_PLATFORM_AND_AUDITABILITY_FEEDBACK_FIT",
                "submission_route": "Email questions and feedback using the official spreadsheet attachment",
                "official_url": "https://sam.gov/workspace/contract/opp/3d72f2df3aaf459797c14cefb41fd235/view",
                "package_files": ["ARMY_AIDP_RFI4_PARTNER_NOTE_STUB_2026-07-10.md"],
                "why_now": "The Army is requesting structured feedback on a draft data-platform solution. LumenCore can contribute bounded comments on evidence provenance, replay, observability, and decision auditability without claiming to supply the entire platform.",
                "today_work": [
                    "Download the public instructions and questions-and-feedback spreadsheet.",
                    "Map only documented LumenCore capabilities to draft requirements.",
                    "Stage the completed feedback sheet and email for review.",
                ],
                "human_gate": [
                    "Robert approves every capability and past-performance statement.",
                    "Robert approves the final feedback email.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 7,
                "lane_id": "ustda_indo_pacific_digital_infrastructure",
                "source_system": "SAM.gov",
                "opportunity_number": "1131PL26R0049",
                "title": "Indo-Pacific Digital Infrastructure Project Scoping Services",
                "agency": "U.S. Trade and Development Agency",
                "deadline_utc": "2026-07-22T17:00:00Z",
                "deadline_date": "2026-07-22",
                "official_deadline_text": "July 22, 2026 at 1:00 PM Eastern Time",
                "command": "PRICE_PAST_PERFORMANCE_AND_CAPACITY_GATE",
                "eligibility_state": "TOTAL_SMALL_BUSINESS_SET_ASIDE_US_FIRM",
                "fit_state": "ADJACENT_DIGITAL_INFRASTRUCTURE_FIT_SCOPING_CAPACITY_UNPROVEN",
                "submission_route": "Proposal under the official RFP instructions",
                "official_url": "https://sam.gov/workspace/contract/opp/fdefc4a420e04049a6a768f744d040c9/view",
                "package_files": ["USTDA_INDO_PACIFIC_DIGITAL_INFRA_SCOPING_STUB_2026-07-10.md"],
                "why_now": "It is a total small-business set-aside and adjacent to digital-infrastructure evaluation, but the prime must prove project-scoping capacity, international delivery, price, and relevant past performance.",
                "today_work": [
                    "Review Sections B through E and the performance work statement.",
                    "Run a strict responsibility, staffing, travel, and past-performance gate.",
                    "Proceed only if every mandatory role and deliverable can be evidenced.",
                ],
                "human_gate": [
                    "Robert confirms staffing, international-delivery capacity, and past performance.",
                    "Robert approves price, representations, and final proposal submission.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 8,
                "lane_id": "acl_ai_assistive_rehabilitation_rerc",
                "source_system": "Grants.gov / Simpler.Grants.gov",
                "opportunity_number": "HHS-2026-ACL-NIDILRR-REGE-0212",
                "title": "RERC on AI-Driven Assistive and Rehabilitation Technologies",
                "agency": "Administration for Community Living",
                "deadline_utc": "2026-07-17T03:59:00Z",
                "deadline_date": "2026-07-16",
                "official_deadline_text": "July 16, 2026 at 11:59 PM Eastern Time",
                "command": "TECHNICAL_CAPACITY_AND_DOMAIN_GATE",
                "eligibility_state": "SMALL_BUSINESS_ELIGIBLE",
                "fit_state": "POTENTIAL_LUMA_SKIN_SUIT_FIT_NOT_YET_EVIDENCED_IN_REPOSITORY",
                "submission_route": "Grants.gov Workspace",
                "official_url": "https://simpler.grants.gov/opportunity/c08bbf7a-563b-4af4-a79b-b1cb7bdd71ad",
                "package_files": [],
                "why_now": "Small businesses are eligible and the topic could fit an assistive-technology lane, but this is a five-year research center award. No repository evidence currently proves the required rehabilitation domain, team, facilities, or evaluation plan.",
                "today_work": [
                    "Open the NOFO and extract all mandatory research-center and domain requirements.",
                    "Locate dated Luma Skin/Suit evidence, investigators, facilities, and disability-community participation.",
                    "Do not start portal certifications unless the capacity gate passes.",
                ],
                "human_gate": [
                    "Robert confirms the proposed technology, investigators, facilities, and community partners are real and available.",
                    "Robert approves all certifications and final submission.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 9,
                "lane_id": "usda_farm_business_benchmarking",
                "source_system": "Grants.gov / NIFA",
                "opportunity_number": "USDA-NIFA-KFBMB-32830",
                "title": "Farm Business Management and Benchmarking Competitive Grants Program",
                "agency": "USDA National Institute of Food and Agriculture",
                "deadline_utc": "2026-07-20T21:00:00Z",
                "deadline_date": "2026-07-20",
                "official_deadline_text": "July 20, 2026 at 5:00 PM Eastern Time",
                "command": "AGRICULTURE_PARTNER_AND_DATA_GATE",
                "eligibility_state": "PRIVATE_ORGANIZATIONS_AND_CORPORATIONS_ELIGIBLE",
                "fit_state": "BENCHMARKING_METHOD_FIT_FARM_NETWORK_AND_FINBIN_DELIVERY_UNPROVEN",
                "submission_route": "Grants.gov Workspace",
                "official_url": "https://simpler.grants.gov/opportunity/a6c41cc0-e597-45c5-8507-1037d8cf7360",
                "secondary_url": "https://www.nifa.usda.gov/grants/funding-opportunities/farm-business-management-benchmarking-competitive-grants-program",
                "package_files": [],
                "why_now": "LumenCore's measurement methods are adjacent and private corporations are eligible, but the program requires genuine farm-management delivery, partner associations, outreach, and required farm-data contributions.",
                "today_work": [
                    "Extract the mandatory partner, farm-record, outreach, and FINBIN requirements.",
                    "Stop unless real agriculture partners and qualifying farm records are already available.",
                ],
                "human_gate": [
                    "Robert confirms qualifying agriculture partners, farm records, and program-delivery capacity.",
                    "Robert approves the budget, certifications, and final submission.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 11,
                "lane_id": "fhwa_intersection_safety_prototyping",
                "source_system": "SAM.gov",
                "opportunity_number": "693JJ3-26-BAA-0004",
                "title": "Intersection Safety Systems Prototyping",
                "agency": "Federal Highway Administration",
                "deadline_utc": "2026-07-20T19:00:00Z",
                "deadline_date": "2026-07-20",
                "official_deadline_text": "July 20, 2026 at 3:00 PM Eastern Time",
                "command": "NO_SOLO_SUBMIT_PARTNER_ONLY",
                "eligibility_state": "OPEN_BAA_TEAM_COMPOSITION_REQUIRED",
                "fit_state": "STRONG_MEASUREMENT_FIT_TESTBED_AND_PUBLIC_SECTOR_PARTNERS_MISSING",
                "submission_route": "Email proposal per the BAA instructions",
                "official_url": "https://sam.gov/opp/a08fe6151b524fbd87e4c7ce8f6a4abb/view",
                "package_files": [],
                "why_now": "The measurement and data-fusion problem is relevant, but a compliant team needs a lead system developer, an access-controlled roadway testbed, and a public-sector partner with jurisdictional authority.",
                "today_work": [
                    "Treat as a teaming lane, not a solo proposal.",
                    "Stage a bounded validation work-package only if qualified partners are already identified.",
                ],
                "human_gate": [
                    "Qualified lead, testbed, and public-sector partners confirm participation.",
                    "Robert approves role, price, representations, and final proposal.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 12,
                "lane_id": "hhs_ai_power_user_pilot",
                "source_system": "SAM.gov",
                "opportunity_number": "7571TE26R00004",
                "title": "HHS AI Power User Advanced Models and Features Pilot",
                "agency": "Department of Health and Human Services",
                "deadline_utc": "2026-07-14T21:00:00Z",
                "deadline_date": "2026-07-14",
                "official_deadline_text": "July 14, 2026 at 5:00 PM Eastern Time",
                "command": "PARTNER_OR_NO_BID",
                "eligibility_state": "OPEN_SOLICITATION_NO_SET_ASIDE",
                "fit_state": "THEMATIC_MEASUREMENT_FIT_PRIME_DELIVERY_REQUIREMENTS_NOT_MET",
                "submission_route": "SAM.gov solicitation instructions",
                "official_url": "https://sam.gov/workspace/contract/opp/d60ae511937b410fa6f13473acbae762/view",
                "package_files": [],
                "why_now": "The baselining and auditability language is highly relevant, but the prime must provide an integrated enterprise model-access bundle for up to 1,000 users plus security, administration, reporting, and authorization-path artifacts. LumenCore should not represent that capacity without an eligible platform prime.",
                "today_work": [
                    "Do not submit as a solo prime.",
                    "Preserve the solicitation as market validation for LumenCore's measurement and persistent-validation architecture.",
                ],
                "human_gate": [
                    "A qualified enterprise AI platform prime requests a documented subcontract role.",
                    "Robert approves any teaming terms, price, and external response.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
            {
                "rank": 13,
                "lane_id": "nsf_techaccess_ai_ready_america_round1",
                "source_system": "NSF / Research.gov",
                "opportunity_number": "26-508",
                "title": "TechAccess: AI-Ready America - State/Territory Coordination Hubs",
                "agency": "U.S. National Science Foundation",
                "deadline_utc": None,
                "deadline_date": "2026-07-16",
                "official_deadline_text": "July 16, 2026 at 5:00 PM submitting organization's local time",
                "command": "NO_BID_MISSED_PREREQUISITE",
                "eligibility_state": "ROUND_ONE_REQUIRED_LOI_DUE_JUNE_16_WAS_MISSED",
                "fit_state": "STRATEGIC_PARTNER_FIT_WATCH_ROUND_TWO",
                "submission_route": "Research.gov or Grants.gov after required Letter of Intent",
                "official_url": "https://www.nsf.gov/funding/opportunities/techaccess-ai-ready-america/nsf26-508/solicitation",
                "package_files": [],
                "why_now": "Round one cannot be pursued because the required June 16 Letter of Intent deadline passed. The January 15, 2027 round-two deadline remains a legitimate statewide consortium target.",
                "today_work": [
                    "Mark round one no-bid; do not waste portal time.",
                    "Start a round-two partner map with statewide conveners, workforce organizations, universities, and government stakeholders.",
                ],
                "human_gate": [
                    "Robert approves partner outreach for the round-two consortium.",
                    "An eligible lead institution and statewide partner structure are confirmed.",
                ],
                "external_send_allowed_without_human": False,
                "final_submit_allowed_without_human": False,
            },
        ]
    )

    cdc_lane = build_cdc_receipt_lane(cdc_engagement_receipt or {})
    if cdc_lane is not None:
        lanes.append(cdc_lane)

    apply_submission_receipts(lanes, submission_receipt or {})
    normalize_lane_deadlines(lanes, scan_date)
    expire_closed_lanes(lanes)
    lanes.sort(key=lambda row: (float(row["rank"]), row["opportunity_number"]))
    for rank, lane in enumerate(lanes, start=1):
        lane["rank"] = rank
        lane["lane_sha256"] = stable_sha256(lane)
    return lanes


def describe_lane(row: dict[str, Any] | None) -> str:
    if row is None:
        return "No open lane is currently supported by the board."
    deadline = row.get("official_deadline_text") or row.get("deadline_utc")
    return (
        f"{row['opportunity_number']} {row['title']}, due {deadline}; "
        f"command {row['command']}; fit {row['fit_state']}."
    )


def build_payload(scan_date: date = SCAN_DATE) -> dict[str, Any]:
    sam_board = read_json(SAM_BOARD)
    grants_ranked = read_json(GRANTS_RANKED)
    zero = read_json(ZERO_FRICTION)
    submission_receipt = read_json(SUBMISSION_RECEIPT)
    cdc_engagement_receipt = read_json(CDC_ENGAGEMENT_RECEIPT)
    sam_rotation_control = read_json(SAM_KEY_ROTATION_CONTROL)
    if sam_rotation_control.get("schema") != "lumencore.sam_public_credential_rotation_control.v1":
        raise ValueError("SAM.gov API-key rotation control is missing or stale")
    sam_deadline_state = sam_rotation_control["deadline"]["state"]
    if sam_rotation_control["rotation_verified"]:
        sam_critical_action = (
            "SAM.gov public API-key rotation is locally detected and live-API verified; preserve the "
            "private key boundary and continue monitoring client health."
        )
    elif sam_deadline_state == "PAST_DUE":
        sam_critical_action = (
            "SAM.gov public API-key rotation became overdue after 2026-07-16. Use the guarded hidden-input "
            "installer immediately, then require changed-fingerprint and live-API verification. Entity "
            "registration remains active; credential rotation is a separate account-maintenance action."
        )
    elif sam_deadline_state == "DUE_TODAY":
        sam_critical_action = (
            "SAM.gov public API-key rotation is due 2026-07-16. Use the guarded hidden-input installer "
            "today; entity registration remains active and credential rotation is a separate "
            "account-maintenance action."
        )
    else:
        sam_critical_action = (
            "SAM.gov public API-key rotation is upcoming. Use the guarded hidden-input installer before "
            "the deadline and verify the replacement without exposing it."
        )
    patent_deadline_control = read_json(PATENT_DEADLINE_CONTROL)
    if patent_deadline_control.get("schema") != "lumencore.patent_deadline_evidence_control.v1":
        raise ValueError("Patent deadline evidence control is missing or stale")
    lanes = build_command_lanes(
        sam_board,
        grants_ranked,
        submission_receipt,
        cdc_engagement_receipt,
        scan_date,
    )
    stage_now = [row for row in lanes if row["command"] in STAGE_COMMANDS]
    sent_verified = [row for row in lanes if row["command"] == "SENT_VERIFIED"]
    emergency_gate = [row for row in lanes if row["command"] == "ELIGIBILITY_AND_PARTNER_GATE"]
    no_bid = [row for row in lanes if row["command"] in NO_BID_COMMANDS]
    expired = [row for row in lanes if row["command"] == EXPIRED_COMMAND]
    human_gated = [row for row in lanes if row["human_gate"]]
    open_candidates = [
        row
        for row in lanes
        if row["days_to_close"] >= 0
        and row["command"] not in {"SENT_VERIFIED", EXPIRED_COMMAND, *NO_BID_COMMANDS}
    ]
    closest_open = min(
        open_candidates,
        key=lambda row: (row["days_to_close"], row["rank"]),
        default=None,
    )
    closest_stage = min(
        stage_now,
        key=lambda row: (row["days_to_close"], row["rank"]),
        default=None,
    )

    payload: dict[str, Any] = {
        "schema": "near_deadline_submission_command_board_v4",
        "generated_utc": now_utc(),
        "scan_date": scan_date.isoformat(),
        "status": "NEAR_DEADLINE_COMMAND_BOARD_ACTIVE_WITH_VERIFIED_SENDS",
        "source_ledgers": base_sources(),
        "summary": {
            "lane_count": len(lanes),
            "stage_now_count": len(stage_now),
            "sent_verified_count": len(sent_verified),
            "emergency_eligibility_gate_count": len(emergency_gate),
            "no_bid_or_partner_only_count": len(no_bid),
            "expired_without_verified_send_count": len(expired),
            "human_gated_count": len(human_gated),
            "strongest_today_action": "Retrieve and install the already-generated SAM.gov replacement public API key without exposing it, complete the Nashville EC TakeOff human-fact gate and final portal preview before the July 17 close, then capture the complete Patent Center docket for the separate U.S.-deadline and foreign/PCT-priority reviews; NASA, Army, and CDC are already sent and receipt-backed.",
            "critical_same_day_infrastructure_action": sam_critical_action,
            "closest_deadline_lane": describe_lane(closest_open),
            "closest_stage_ready_lane": describe_lane(closest_stage),
            "best_grants_lane": "NSF 26-510 Project Pitch gate; no fixed pitch due date is listed, and a full proposal requires an invitation. November 4, 2026 is planning only.",
            "best_contract_lane": "693JJ326R000012 FHWA TSMO Data Initiative, due 2026-08-03.",
            "fastest_low_friction_lane": "The Nashville EC TakeOff application is the nearest low-friction reviewer route, but six founder confirmations and final portal submission remain human-gated.",
            "all_final_actions_blocked_without_human": True,
            "external_send_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
            "pricing_allowed_without_human": False,
            "legal_certification_allowed_without_human": False,
        },
        "operational_controls": {
            "sam_public_key_rotation": {
                "status": sam_rotation_control["status"],
                "deadline_local": sam_rotation_control["deadline"]["date_local"],
                "deadline_state": sam_deadline_state,
                "aliases_consistent": sam_rotation_control["local_configuration"]["aliases_consistent"],
                "replacement_installation_detected": sam_rotation_control["local_configuration"]["replacement_installation_detected"],
                "api_probe": sam_rotation_control["api_probe"]["classification"],
                "rotation_verified": sam_rotation_control["rotation_verified"],
                "private_installer": sam_rotation_control["private_installer"]["path"],
                "control_artifact": rel(SAM_KEY_ROTATION_CONTROL),
                "human_action_required": True,
                "browser_navigation_performed": False,
            },
            "patent_deadline_evidence": {
                "status": patent_deadline_control["status"],
                "payment_acknowledgement_found": patent_deadline_control["public_evidence_summary"]["payment_acknowledgement_found"],
                "filing_receipt_found": patent_deadline_control["public_evidence_summary"]["filing_receipt_found"],
                "official_correspondence_found": patent_deadline_control["public_evidence_summary"]["official_correspondence_found"],
                "official_status_record_found": patent_deadline_control["public_evidence_summary"]["official_status_record_found"],
                "us_prosecution_deadline": patent_deadline_control["deadline_posture"]["us_prosecution_deadline"],
                "foreign_pct_priority": patent_deadline_control["deadline_posture"]["foreign_pct_priority"],
                "control_artifact": rel(PATENT_DEADLINE_CONTROL),
                "human_action_required": True,
                "browser_navigation_performed": False,
            },
        },
        "lanes": lanes,
        "sent_verified": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "submission_status": row["submission_status"],
                "sent_utc": row["sent_utc"],
                "receipt_path": row["receipt_path"],
                "receipt_attachment_sha256": row["receipt_attachment_sha256"],
            }
            for row in sent_verified
        ],
        "stage_now": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_utc": row["deadline_utc"],
                "official_deadline_text": row.get("official_deadline_text"),
                "official_url": row["official_url"],
                "package_files": row["package_files"],
            }
            for row in stage_now
        ],
        "emergency_gate": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_utc": row["deadline_utc"],
                "official_url": row["official_url"],
                "human_gate": row["human_gate"],
            }
            for row in emergency_gate
        ],
        "no_bid_or_partner_only": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "command": row["command"],
                "deadline_date": row["deadline_date"],
                "eligibility_state": row["eligibility_state"],
                "fit_state": row["fit_state"],
                "official_url": row["official_url"],
            }
            for row in no_bid
        ],
        "expired_without_verified_send": [
            {
                "rank": row["rank"],
                "opportunity_number": row["opportunity_number"],
                "title": row["title"],
                "deadline_date": row["deadline_date"],
                "pre_expiry_command": row.get("pre_expiry_command"),
                "submission_status": row.get("submission_status"),
                "official_url": row["official_url"],
            }
            for row in expired
        ],
        "zero_friction_pack_status": zero.get("status", "UNKNOWN"),
        "submission_boundary": {
            "can_open_pages": True,
            "can_stage_drafts": True,
            "can_fill_nonfinal_routine_fields_after_user_login": True,
            "can_final_submit_without_human": False,
            "must_stop_before": [
                "final Grants.gov submit",
                "final SAM.gov submit",
                "final email send",
                "legal certification",
                "signature",
                "terms acceptance",
                "pricing or quote amount",
                "claim of agency validation, award, realized savings, or customer ROI",
            ],
        },
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["command_board_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        f"# Near-Deadline Submission Command Board - {payload['scan_date']}",
        "",
        "This is the action board for getting the closest credible grants and federal contract responses fully staged.",
        "",
        f"Direct answer: NASA, Army, and CDC are sent and receipt-backed. {summary['critical_same_day_infrastructure_action']} Finish the July 17 Nashville EC TakeOff application, stage the rolling NSF Project Pitch, and re-verify FHWA while keeping DOJ/BOP partner-only.",
        "",
        "## Control Line",
        "",
        f"- Status: `{payload['status']}`",
        f"- Scan date: `{payload['scan_date']}`",
        f"- Lane count: `{summary['lane_count']}`",
        f"- Stage-now lanes: `{summary['stage_now_count']}`",
        f"- Sent and verified lanes: `{summary['sent_verified_count']}`",
        f"- Emergency eligibility gates: `{summary['emergency_eligibility_gate_count']}`",
        f"- No-bid or partner-only lanes: `{summary['no_bid_or_partner_only_count']}`",
        f"- Expired without verified send: `{summary['expired_without_verified_send_count']}`",
        f"- Human-gated lanes: `{summary['human_gated_count']}`",
        f"- Strongest today action: {summary['strongest_today_action']}",
        f"- Critical infrastructure action: {summary['critical_same_day_infrastructure_action']}",
        f"- Closest deadline lane: {summary['closest_deadline_lane']}",
        f"- Closest stage-ready lane: {summary['closest_stage_ready_lane']}",
        f"- Best grants lane: {summary['best_grants_lane']}",
        f"- Best contract lane: {summary['best_contract_lane']}",
        f"- Fastest low-friction lane: {summary['fastest_low_friction_lane']}",
        f"- Final submit without human: `{str(summary['final_submit_allowed_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Pricing without human: `{str(summary['pricing_allowed_without_human']).lower()}`",
        f"- Legal certification without human: `{str(summary['legal_certification_allowed_without_human']).lower()}`",
        f"- Command board SHA-256: `{payload['command_board_sha256']}`",
        "",
        "## Operational Controls",
        "",
    ]
    for key, control in payload["operational_controls"].items():
        lines.extend([f"### {key}", "", f"- Status: `{control['status']}`"])
        if key == "sam_public_key_rotation":
            lines.extend(
                [
                    f"- Deadline local: `{control['deadline_local']}`",
                    f"- Deadline state: `{control['deadline_state']}`",
                    f"- Aliases consistent: `{str(control['aliases_consistent']).lower()}`",
                    f"- Replacement installation detected: `{str(control['replacement_installation_detected']).lower()}`",
                    f"- API probe: `{control['api_probe']}`",
                    f"- Rotation verified: `{str(control['rotation_verified']).lower()}`",
                    f"- Guarded installer: `{control['private_installer']}`",
                ]
            )
        elif key == "patent_deadline_evidence":
            lines.extend(
                [
                    f"- Payment acknowledgement found: `{str(control['payment_acknowledgement_found']).lower()}`",
                    f"- Filing Receipt found: `{str(control['filing_receipt_found']).lower()}`",
                    f"- Official correspondence found: `{str(control['official_correspondence_found']).lower()}`",
                    f"- Official status record found: `{str(control['official_status_record_found']).lower()}`",
                    f"- U.S. prosecution deadline: `{control['us_prosecution_deadline']}`",
                    f"- Foreign or PCT priority: `{control['foreign_pct_priority']}`",
                ]
            )
        lines.extend(
            [
                f"- Human action required: `{str(control['human_action_required']).lower()}`",
                f"- Browser navigation performed: `{str(control['browser_navigation_performed']).lower()}`",
                f"- Control artifact: `{control['control_artifact']}`",
                "",
            ]
        )
    lines.extend(
        [
        "## Sent And Verified",
        "",
        ]
    )
    for row in payload["sent_verified"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Status: `{row['submission_status']}`",
                f"- Sent UTC: `{row['sent_utc']}`",
                f"- Receipt: `{row['receipt_path']}`",
                f"- Attachment SHA-256: `{row['receipt_attachment_sha256']}`",
                "",
            ]
        )

    lines.extend(["## Stage Now", ""])
    for row in payload["stage_now"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Official deadline: {row.get('official_deadline_text') or row['deadline_utc']}",
                f"- Official URL: {row['official_url']}",
                "- Package files:",
            ]
        )
        for file in row["package_files"]:
            lines.append(f"  - `{file}`")
        lines.append("")

    lines.extend(["## Emergency Gate", ""])
    for row in payload["emergency_gate"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline UTC: `{row['deadline_utc']}`",
                f"- Official URL: {row['official_url']}",
                "- Human gate:",
            ]
        )
        for gate in row["human_gate"]:
            lines.append(f"  - {gate}")
        lines.append("")

    lines.extend(["## No-Bid Or Partner-Only", ""])
    for row in payload["no_bid_or_partner_only"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Command: `{row['command']}`",
                f"- Deadline date: `{row['deadline_date']}`",
                f"- Eligibility: `{row['eligibility_state']}`",
                f"- Fit: `{row['fit_state']}`",
                f"- Official URL: {row['official_url']}",
                "",
            ]
        )

    lines.extend(["## Expired Without Verified Send", ""])
    for row in payload["expired_without_verified_send"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['opportunity_number']} - {row['title']}",
                "",
                f"- Deadline date: `{row['deadline_date']}`",
                f"- Prior command: `{row['pre_expiry_command']}`",
                f"- Status: `{row['submission_status']}`",
                f"- Official URL: {row['official_url']}",
                "",
            ]
        )

    lines.extend(["## Full Lane Detail", ""])
    for lane in payload["lanes"]:
        lines.extend(
            [
                f"### {lane['rank']}. {lane['opportunity_number']} - {lane['title']}",
                "",
                f"- Source: `{lane['source_system']}`",
                f"- Agency: `{lane['agency']}`",
                f"- Deadline UTC: `{lane['deadline_utc']}`",
                f"- Official deadline: {lane.get('official_deadline_text') or lane['deadline_utc']}",
                f"- Days to close from scan date: `{lane['days_to_close']}`",
                f"- Deadline bucket: `{lane['deadline_bucket']}`",
                f"- Command: `{lane['command']}`",
                f"- Eligibility: `{lane['eligibility_state']}`",
                f"- Fit: `{lane['fit_state']}`",
                f"- Route: {lane['submission_route']}",
                f"- Official URL: {lane['official_url']}",
            ]
        )
        if lane.get("secondary_url"):
            lines.append(f"- Secondary URL: {lane['secondary_url']}")
        lines.extend(
            [
                f"- Why now: {lane['why_now']}",
                "- Today work:",
            ]
        )
        for item in lane["today_work"]:
            lines.append(f"  - {item}")
        if lane["human_gate"]:
            lines.append("- Human gate:")
            for gate in lane["human_gate"]:
                lines.append(f"  - {gate}")
        if lane["package_files"]:
            lines.append("- Package files:")
            for file in lane["package_files"]:
                lines.append(f"  - `{file}`")
        lines.extend(
            [
                f"- External send without human: `{str(lane['external_send_allowed_without_human']).lower()}`",
                f"- Final submit without human: `{str(lane['final_submit_allowed_without_human']).lower()}`",
                f"- Lane SHA-256: `{lane['lane_sha256']}`",
                "",
            ]
        )

    lines.extend(["## Submission Boundary", ""])
    boundary = payload["submission_boundary"]
    for key, value in boundary.items():
        if isinstance(value, list):
            lines.append(f"- {key}:")
            for item in value:
                lines.append(f"  - {item}")
        else:
            lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(["", "## Source Ledgers", ""])
    for key, source in payload["source_ledgers"].items():
        lines.append(f"- `{key}`: `{source.get('path')}` present=`{str(source.get('present')).lower()}` sha256=`{source.get('sha256', '')}`")
    return "\n".join(lines) + "\n"


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def main() -> None:
    payload = build_payload()
    rendered = render_markdown(payload)
    hits = scan_sensitive_text(rendered)
    if hits:
        raise SystemExit(f"Refusing to write sensitive markers: {hits}")
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, rendered)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "lanes": payload["summary"]["lane_count"],
                "stage_now": payload["summary"]["stage_now_count"],
                "emergency_gates": payload["summary"]["emergency_eligibility_gate_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
