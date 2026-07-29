from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "LAUNCHTN_3686_PITCH_2026"
OUT_JSON = OUT_DIR / "LAUNCHTN_3686_APPLICATION_MANIFEST_2026-07-29.json"
OUT_MD = OUT_DIR / "LAUNCHTN_3686_PORTAL_FIELD_MAP_2026-07-29.md"
PITCH_DECK_PATH = (
    ROOT
    / "output"
    / "pptx"
    / "LumenCore_Evidence_to_Pilot_Deck_CURRENT_REVIEW_REQUIRED.pptx"
)
FINANCIAL_MODEL_PATH = OUT_DIR / "LUMENCORE_3686_FINANCIAL_MODEL_2026-07-17.xlsx"

FORM_URL = "https://airtable.com/app6GRZNbU72OmaK1/pagudvfO1hH7SmzBl/form"
INVESTTN_URL = "https://investtn.org/"

SOURCE_ARTIFACTS = {
    "current_source_native_whitepaper": ROOT
    / "docs"
    / "LUMENCORE_SOURCE_NATIVE_BENCHMARK_WHITEPAPER_CURRENT.md",
    "current_family_ledger": ROOT
    / "out"
    / "ops"
    / "source_native_family_baseline_ledger_latest.json",
    "current_market_benchmark": ROOT
    / "out"
    / "ops"
    / "market_signal_source_native_benchmark_latest.json",
    "pitch_deck_governance": ROOT
    / "out"
    / "ops"
    / "pitch_deck_governance_latest.json",
    "application_refresh": OUT_DIR / "LAUNCHTN_3686_APPLICATION_REFRESH_2026-07-29.md",
    "lanl_receipt": ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "LANL_VISION_FOLLOWUP_ENGAGEMENT_RECEIPT_2026-07-16.json",
}

COMPANY_STRUCTURE_OPTIONS = (
    "C Corporation",
    "S Corporation",
    "Limited Liability Corporation",
    "Limited Liability Partnership",
    "Partnership",
    "Sole Proprietorship",
    "Other",
    "Not Determined Yet",
)
TENNESSEE_ELIGIBILITY_OPTIONS = (
    "51% of my company's employees are domiciled in Tennessee",
    "My company is headquartered in TN",
    "A majority of my company's senior management are domiciled in TN",
    "None of the above",
)
PRIOR_LAUNCHTN_CAPITAL_OPTIONS = ("None", "Yes", "No")
BUSINESS_MODEL_OPTIONS = ("B2B", "B2C", "D2C", "B2B2C", "Other")
PRIMARY_PRODUCT_OPTIONS = (
    "Software / SaaS Platform",
    "Mobile App",
    "Physical Product / Device",
    "Biotechnology / Life Sciences Solution",
    "Medical Device",
    "Consumer Packaged Good (CPG)",
    "Marketplace Platform",
    "AI / Machine Learning Tool",
    "Fintech Solution",
    "Healthtech Solution",
    "Clean Energy / Sustainability Product",
    "Manufacturing / Industrial Technology",
    "Agricultural / Food Technology",
    "Service-Based Offering",
    "Other (please specify)",
)
PRODUCT_STATUS_OPTIONS = (
    "MVP not yet in development",
    "MVP development in Progress",
    "MVP development completed",
    "Beta Testing Initial Users",
    "Intial Product full developed and validated",
    "Currently live in market",
)
SECTOR_OPTIONS = (
    "Advanced Materials",
    "AgTech",
    "FinTech",
    "Mobility & Transportation",
    "Advanced Energy/Battery Solutions",
    "AR/VR",
    "Bio Tech/Life Sciences/Med Device",
    "Blockchain/Crypto/Web 3.0",
    "ClimateTech/CleanTech",
    "Construction Tech/Manufacturing",
    "Consumer/E-Commerce",
    "Data/AI/ML",
    "EdTech",
    "Entertainment/Media/Gaming",
    "FemTech",
    "General",
    "Health & Wellness",
    "HR Tech",
    "Robotics",
    "Security/Cybersecurity",
    "SaaS",
    "InsurTech/Legal Tech",
    "Other",
)

PRODUCT_SERVICE = (
    "LumenCore is a proof-to-pilot AI validation platform for energy and infrastructure "
    "forecasting. It takes an approved time-series dataset, locks the baseline, candidate, "
    "metrics, and evaluation window, then runs past-only comparisons and issues "
    "hash-verifiable receipts showing wins, losses, and abstentions. Technical buyers use "
    "those receipts to decide whether a model deserves an independently reviewed pilot. "
    "The first product is a bounded evidence-review sprint followed by a buyer-controlled "
    "replay pilot; an annual platform license follows only after validation."
)

PROBLEM_AND_CUSTOMER = (
    "Utilities, laboratories, agencies, and industrial operators are being asked to trust "
    "AI outputs that can be difficult to reproduce, compare fairly, or defend after a "
    "decision. The initial customer is the technical or innovation leader responsible for "
    "forecasting, anomaly detection, timing, or operational-model assurance. Existing "
    "benchmark tools often stop at a score. LumenCore also locks the data window and metric, "
    "prevents future-data leakage, preserves negative results, supports abstention when the "
    "evidence is weak, and creates a hash-verifiable custody trail. The immediate customer "
    "outcome is a defensible go/no-go decision for a pilot, not an unsupported promise of "
    "savings or deployment readiness."
)

REVENUE_MODEL = (
    "Planned, not yet realized: LumenCore uses a staged B2B model consisting of a scoped "
    "technical evidence review, a buyer-controlled historical replay pilot, and software plus "
    "verification support only after agreed acceptance gates pass. Grant-funded validation "
    "and government R&D contracts are complementary channels rather than recurring software "
    "revenue. No price, raise amount, forecast, booked revenue, or signed customer is approved "
    "in this packet; every commercial and financial assumption requires founder review."
)

GO_TO_MARKET = (
    "Start with a narrow energy and infrastructure wedge: utilities, grid analytics firms, "
    "national laboratories, agencies, and industrial operators that already own historical "
    "time-series data and an accepted baseline. Use founder-led targeted outreach, warm "
    "Tennessee ecosystem introductions, consortia, technical events, and the public proof "
    "portal to reach technical decision-makers. Qualify each account on data authority, "
    "baseline, metric, reviewer, and economic decision before proposing work. Convert the "
    "first engagement into a fixed-scope evidence review, then a buyer-controlled replay "
    "pilot, then an annual license only after the acceptance gate passes. SBIR/STTR and "
    "federal market-research channels support validation but do not replace customer discovery."
)

ACHIEVEMENTS = (
    "A working technical MVP and public reviewer surface exist with locked "
    "baseline-versus-candidate protocols, past-only evaluation, explicit abstention, "
    "negative-result preservation, reproducible manifests, and hash-verifiable receipts. The "
    "current source-native research ledger records 140 registered families, 35 implementations, "
    "126 direct comparisons across 23 candidate-source cards, zero global Holm-positive "
    "comparisons, and zero promoted champions. Those are local software and protocol results, "
    "not field or independent validation. Outreach records prove bounded transmission only; "
    "they do not prove receipt, endorsement, partnership, award, or customer traction. The next "
    "milestone is one independent reproduction and one buyer-owned replay pilot with "
    "preregistered acceptance metrics."
)

OPTIONAL_NOTE = (
    "LumenCore is a pre-revenue technical project seeking disciplined help with customer focus "
    "and conversion from reproducible local proof to a first paid buyer-controlled pilot. "
    "Tennessee eligibility and every legal, employment, funding-history, pricing, and raise "
    "statement remain subject to founder verification. Performance results remain labeled as "
    "local until independently reproduced."
)

ATTACHMENT_QA = {
    "launchtn_pitch_deck": {
        "path": PITCH_DECK_PATH,
        "expected_sha256": "4df644106ac2a4df146a09a9f04a08535c88983a5dce4ded48e2fb72c28ec55a",
        "qa_date": "2026-07-29",
        "qa_checks": [
            "11-slide governed current evidence-to-pilot narrative",
            "Every slide visually inspected at original render resolution",
            "slides_test.py passed with no overflow detected",
            "Current evidence counts and negative results preserved",
        ],
        "blocked_status": "CURRENT_DECK_VENUE_COVERAGE_AND_FOUNDER_REVIEW_REQUIRED",
        "missing_requirements": [
            "LaunchTN-specific competitive landscape",
            "business model and go-to-market framing",
            "customer profile",
            "founder-approved raise ask",
            "founding-team and Tennessee eligibility facts",
        ],
    },
    "launchtn_financial_model": {
        "path": FINANCIAL_MODEL_PATH,
        "expected_sha256": "9da46f8ad94fc53ef561ee33dcfa6df907897caeadf6afbd08fb113fc6887d94",
        "qa_date": "2026-07-17",
        "qa_checks": [
            "Six-sheet formula-driven model",
            "Pricing, COGS, gross margin, and five-year projections present",
            "All model check cells passed",
            "Formula-error scan returned zero matches",
            "Every sheet visually inspected after layout repair",
        ],
        "blocked_status": "PLANNING_MODEL_ARITHMETIC_QA_ONLY_FOUNDER_ASSUMPTION_APPROVAL_REQUIRED",
        "missing_requirements": [
            "founder approval of every pricing assumption",
            "founder approval of raise and use-of-funds assumptions",
            "actual-versus-planning labels on all revenue, customer, hiring, margin, and cash rows",
        ],
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_status(path: Path) -> dict[str, Any]:
    present = path.is_file()
    return {
        "path": rel(path),
        "present": present,
        "bytes": path.stat().st_size if present else None,
        "sha256": sha256_file(path),
    }


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_attachment_record(
    *,
    attachment_id: str,
    portal_requirement: str,
    source_candidate: str | None = None,
    actuals_claimed: bool | None = None,
) -> dict[str, Any]:
    qa = ATTACHMENT_QA[attachment_id]
    artifact = artifact_status(qa["path"])
    qa_hash_matches = bool(
        artifact["present"] and artifact["sha256"] == qa["expected_sha256"]
    )
    if not artifact["present"]:
        status = "ATTACHMENT_MISSING_REBUILD_REQUIRED"
    elif not qa_hash_matches:
        status = "ATTACHMENT_CHANGED_REVIEW_AND_QA_REQUIRED"
    else:
        status = qa["blocked_status"]
    record: dict[str, Any] = {
        "id": attachment_id,
        "portal_requirement": portal_requirement,
        **artifact,
        "expected_sha256": qa["expected_sha256"],
        "qa_hash_matches": qa_hash_matches,
        "qa_date": qa["qa_date"],
        "qa_checks": list(qa["qa_checks"]),
        "status": status,
        "structural_qa_passed": qa_hash_matches,
        "safe_to_upload": False,
        "missing_requirements": list(qa["missing_requirements"]),
        "founder_approval_required": True,
    }
    if source_candidate is not None:
        record["source_candidate"] = source_candidate
    if actuals_claimed is not None:
        record["actuals_claimed"] = actuals_claimed
    return record


def field(
    field_id: str,
    label: str,
    required: bool,
    proposed_answer: str,
    status: str = "READY",
    *,
    evidence: str = "Public-safe local business record",
    char_limit: int | None = None,
    option_group: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "field_id": field_id,
        "label": label,
        "required": required,
        "proposed_answer": proposed_answer,
        "status": status,
        "evidence": evidence,
    }
    if char_limit is not None:
        row["character_limit"] = char_limit
        row["character_count"] = len(proposed_answer)
        row["within_character_limit"] = len(proposed_answer) <= char_limit
    if option_group is not None:
        row["portal_option_group"] = option_group
    return row


FIELDS = [
    field(
        "company_name",
        "Company Name",
        True,
        "[ENTER VERIFIED LEGAL ENTITY OR APPROVED TRADE NAME AS THE FORM REQUIRES]",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Current legal entity record and portal naming instruction required",
    ),
    field("founder_names", "Founder(s) Name(s)", True, "Robert Ashworth"),
    field(
        "founder_phone",
        "Founder's Phone Number",
        False,
        "[PRIVATE_PORTAL_ENTRY]",
        "PRIVATE_PORTAL_ENTRY",
        evidence="Private contact record",
    ),
    field(
        "founder_linkedin",
        "Founder's LinkedIn",
        True,
        "https://www.linkedin.com/in/robert-ashworth-40a9b7376",
    ),
    field(
        "founder_email",
        "Founder's Email",
        True,
        "[PRIVATE_PORTAL_ENTRY_FROM_AUTHENTICATED_GMAIL]",
        "PRIVATE_PORTAL_ENTRY",
        evidence="Authenticated Gmail account",
    ),
    field("company_website", "Company Website (if applicable)", False, "https://lumen-core.ai"),
    field(
        "company_address",
        "Company Address",
        True,
        "[PRIVATE_PORTAL_ENTRY]",
        "PRIVATE_PORTAL_ENTRY",
        evidence="Founder-controlled legal or business address record",
    ),
    field(
        "company_city",
        "Company City",
        True,
        "[ENTER CITY THAT MATCHES THE VERIFIED HEADQUARTERS ADDRESS]",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Must match the private headquarters address entered in the portal",
    ),
    field(
        "company_state",
        "Company State",
        True,
        "[ENTER STATE THAT MATCHES THE VERIFIED HEADQUARTERS ADDRESS]",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Must match the private headquarters address entered in the portal",
    ),
    field(
        "company_zip",
        "Company Zip Code",
        True,
        "[PRIVATE_PORTAL_ENTRY]",
        "PRIVATE_PORTAL_ENTRY",
        evidence="Founder-controlled legal or business address record",
    ),
    field(
        "company_county",
        "Which county is your company HQ?",
        True,
        "Davidson only if the submitted headquarters address is in Davidson County",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Must match the private headquarters address entered in the portal",
        option_group="tennessee_counties",
    ),
    field(
        "additional_office",
        "Additional Office Location (Optional)",
        False,
        "Leave blank unless another current office exists",
        "OPTIONAL_OMIT_UNLESS_TRUE",
    ),
    field(
        "formation_year",
        "Company Year of Formation",
        True,
        "[ENTER VERIFIED LEGAL FORMATION YEAR]",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Legal formation record required",
    ),
    field(
        "company_structure",
        "Company Structure",
        True,
        "[SELECT VERIFIED LEGAL STRUCTURE]",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Legal entity record required",
        option_group="company_structure",
    ),
    field(
        "tennessee_eligibility",
        "Which Statement best describes your company's eligibility?",
        True,
        "My company is headquartered in TN only if the legal and operating facts support it",
        "HUMAN_ATTESTATION_REQUIRED",
        evidence="Founder attestation against the portal's cited Tennessee statute",
        option_group="tennessee_eligibility",
    ),
    field(
        "full_time_employees",
        "Number of Full Time Employees",
        True,
        "[ENTER VERIFIED INTEGER; INCLUDE FOUNDER ONLY IF THE PORTAL DEFINITION ALLOWS]",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Current employment facts required",
    ),
    field(
        "prior_launchtn_capital",
        "Have you previously received capital from LaunchTN, such as from INCITE Fund, Impact Fund, SBIR/STTR matching funds or microgrants?",
        True,
        "No only if no LaunchTN capital has ever been received",
        "HUMAN_CONFIRM_REQUIRED",
        evidence="Founder funding-history attestation required",
        option_group="prior_launchtn_capital",
    ),
    field(
        "product_service",
        "Briefly describe your product/service",
        True,
        PRODUCT_SERVICE,
        char_limit=1200,
        evidence="Current product architecture and public claim boundary",
    ),
    field(
        "problem_customer",
        "What problem does your startup solve, and who is your target customer?",
        True,
        PROBLEM_AND_CUSTOMER,
        char_limit=1500,
        evidence="Current commercialization packet and reviewer-safe product framing",
    ),
    field(
        "revenue_model",
        "How does your company generate or plan to generate revenue?",
        True,
        REVENUE_MODEL,
        "FOUNDER_PRICING_APPROVAL_REQUIRED",
        char_limit=1200,
        evidence="Planning assumptions only; no booked revenue or approved quote",
    ),
    field(
        "go_to_market",
        "What is your go-to-market or sales strategy? How will you reach your customers?",
        True,
        GO_TO_MARKET,
        char_limit=1200,
        evidence="Proof-to-pilot commercialization plan",
    ),
    field(
        "achievements",
        "Share any key achievements, traction, milestones, or validations so far",
        True,
        ACHIEVEMENTS,
        char_limit=1500,
        evidence="Repository proof controls and bounded engagement receipts",
    ),
    field(
        "business_model",
        "What is your Business Model",
        True,
        "B2B",
        option_group="business_model",
    ),
    field(
        "primary_product",
        "What is the primary product that your startup is providing?",
        True,
        "AI / Machine Learning Tool",
        option_group="primary_product",
    ),
    field(
        "product_status",
        "Status of product",
        True,
        "MVP development completed",
        evidence="Working ingestion, benchmark, API, dashboard, and evidence-manifest components",
        option_group="product_status",
    ),
    field(
        "industry_sectors",
        "Indicate the Industry Sector(s) that best describe your company.",
        True,
        "Data/AI/ML; Advanced Energy/Battery Solutions",
        evidence="AI validation platform with an initial energy and infrastructure wedge",
        option_group="industry_sectors",
    ),
    field(
        "pitch_deck",
        "Pitch Deck",
        True,
        "[NO SAFE UPLOAD YET: BUILD AND REVIEW A CURRENT LAUNCHTN-SPECIFIC DECK]",
        "CURRENT_DECK_VENUE_COVERAGE_AND_FOUNDER_REVIEW_REQUIRED",
        evidence="The governed current deck is structurally clean but lacks required venue-specific content",
    ),
    field(
        "financials",
        "Upload attachments that contain information about your financials",
        True,
        "[NO SAFE UPLOAD YET: APPROVE AND RELABEL EVERY PLANNING ASSUMPTION]",
        "PLANNING_MODEL_ARITHMETIC_QA_ONLY_FOUNDER_ASSUMPTION_APPROVAL_REQUIRED",
        evidence="The formula-driven model passes arithmetic checks but its business assumptions are unapproved",
    ),
    field(
        "other_attachment",
        "(Optional) Any other video/documents, and/or demo you want to share, please share it here!",
        False,
        "Leave blank unless a public-safe reviewer artifact is separately approved",
        "OPTIONAL_OMIT_UNLESS_REVIEWED",
    ),
    field(
        "optional_note",
        "(Optional) Anything else you would like us to know?",
        False,
        OPTIONAL_NOTE,
        "OPTIONAL_HOLD_UNTIL_ELIGIBILITY_CONFIRMED",
        evidence="Current claim boundary and commercialization need",
    ),
]


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    fields = [dict(row) for row in FIELDS]
    required_attachments = [
        build_attachment_record(
            attachment_id="launchtn_pitch_deck",
            portal_requirement="Competitive landscape, business model, go-to-market, customer profiles, raise ask, and founding team",
            source_candidate=rel(PITCH_DECK_PATH),
        ),
        build_attachment_record(
            attachment_id="launchtn_financial_model",
            portal_requirement="Pricing, COGS/cost of revenue, gross margin, and 2-5 year projections",
            actuals_claimed=False,
        ),
    ]
    attachment_by_id = {row["id"]: row for row in required_attachments}
    field_to_attachment = {
        "pitch_deck": "launchtn_pitch_deck",
        "financials": "launchtn_financial_model",
    }
    for row in fields:
        attachment_id = field_to_attachment.get(row["field_id"])
        if attachment_id is None:
            continue
        attachment = attachment_by_id[attachment_id]
        row["status"] = attachment["status"]
        row["proposed_answer"] = (
            f"Do not attach yet. Candidate {attachment['path']} is present with SHA-256 "
            f"{attachment['sha256'] or '[missing]'}, but remains blocked by: "
            f"{'; '.join(attachment['missing_requirements'])}."
        )

    status_counts: dict[str, int] = {}
    for row in fields:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    portal_options = {
        "tennessee_counties": ["Davidson", "Other"],
        "company_structure": list(COMPANY_STRUCTURE_OPTIONS),
        "tennessee_eligibility": list(TENNESSEE_ELIGIBILITY_OPTIONS),
        "prior_launchtn_capital": list(PRIOR_LAUNCHTN_CAPITAL_OPTIONS),
        "business_model": list(BUSINESS_MODEL_OPTIONS),
        "primary_product": list(PRIMARY_PRODUCT_OPTIONS),
        "product_status": list(PRODUCT_STATUS_OPTIONS),
        "industry_sectors": list(SECTOR_OPTIONS),
    }
    payload: dict[str, Any] = {
        "schema": "lumencore.launchtn_3686_pitch_application.v2",
        "generated_utc": generated_utc or now_utc(),
        "opportunity": {
            "name": "3686 Pitch Competition 2026, presented by Amazon",
            "organizer": "Launch Tennessee",
            "application_deadline": "2026-08-13T23:59:00-05:00",
            "application_deadline_timezone": "CDT",
            "competition_date": "2026-09-15",
            "competition_location": "Brooklyn Bowl, Nashville",
            "cash_prize_usd": 10000,
            "form_url": FORM_URL,
            "formal_investtn_application": False,
            "investtn_url": INVESTTN_URL,
            "portal_schema_status": (
                "FORM_OPEN_DEADLINE_AND_UPLOAD_FIELDS_RECHECKED_2026-07-29_"
                "FULL_SCHEMA_AND_ATTESTATIONS_REQUIRE_LIVE_REVIEW"
            ),
            "eligibility_fit": "POTENTIAL_TENNESSEE_STARTUP_FIT_REQUIRES_FOUNDER_ATTESTATION",
        },
        "summary": {
            "field_count": len(FIELDS),
            "required_field_count": sum(1 for row in fields if row["required"]),
            "status_counts": status_counts,
            "narrative_fields_within_character_limits": all(
                row.get("within_character_limit", True) for row in FIELDS
            ),
            "human_or_private_fact_gates": sum(
                row["status"]
                in {
                    "PRIVATE_PORTAL_ENTRY",
                    "HUMAN_CONFIRM_REQUIRED",
                    "HUMAN_ATTESTATION_REQUIRED",
                    "FOUNDER_PRICING_APPROVAL_REQUIRED",
                }
                for row in fields
            ),
            "required_attachment_gates": 2,
            "required_attachments_present": sum(
                row["present"] for row in required_attachments
            ),
            "required_attachments_qa_passed": sum(
                row["safe_to_upload"]
                for row in required_attachments
            ),
            "required_attachments_structural_qa_passed": sum(
                row["structural_qa_passed"] for row in required_attachments
            ),
            "required_attachments_safe_to_upload": sum(
                row["safe_to_upload"] for row in required_attachments
            ),
            "upload_set_ready": all(
                row["safe_to_upload"] for row in required_attachments
            ),
            "final_submit_allowed_without_human": False,
        },
        "portal_options": portal_options,
        "fields": fields,
        "required_attachments": required_attachments,
        "human_fact_gate": [
            "Enter private founder email, optional phone, company street address, and ZIP only in the authenticated portal.",
            "Verify legal company name, headquarters city, state, county, and ZIP against the submitted private address.",
            "Verify legal formation year and entity structure.",
            "Attest which Tennessee statutory eligibility statement is true.",
            "Verify the full-time employee count under the portal's definition.",
            "Confirm whether any LaunchTN capital has ever been received.",
            "Approve or replace every pricing, raise, revenue, customer, hiring, margin, and cash assumption.",
            "Build and visually review a LaunchTN-specific deck that covers every requested topic.",
            "Recheck the live portal schema, file limits, terms, and attestations.",
            "Review both required attachments and the complete final portal preview before submission.",
        ],
        "safe_upload_set": [],
        "source_artifacts": {
            name: artifact_status(path) for name, path in SOURCE_ARTIFACTS.items()
        },
        "claim_boundary": (
            "This is an application-preparation artifact. It does not claim a paying customer, "
            "booked revenue, signed pilot, external or field validation, partnership, endorsement, "
            "award, realized savings, product-market fit, investment, competition selection, or "
            "permission to submit without a founder-reviewed final preview."
        ),
        "final_action_gate": {
            "status": (
                "PORTAL_FACTS_VENUE_DECK_FINANCIAL_APPROVAL_AND_"
                "FINAL_PREVIEW_REQUIRED"
            ),
            "submit_allowed_without_human": False,
            "action": (
                "Resolve founder and eligibility facts, rebuild the venue-specific deck, "
                "approve or replace every financial assumption, recheck the live portal, "
                "and stop at the complete final preview for action-time founder review."
            ),
        },
    }
    payload["application_packet_sha256"] = stable_sha256(payload)
    validate_payload(payload)
    return payload


def validate_payload(payload: dict[str, Any]) -> None:
    if not payload["summary"]["narrative_fields_within_character_limits"]:
        raise ValueError("One or more LaunchTN narratives exceed the observed portal limit")
    field_ids = [row["field_id"] for row in payload["fields"]]
    if len(field_ids) != len(set(field_ids)):
        raise ValueError("Duplicate LaunchTN field IDs")
    if payload["summary"]["required_attachment_gates"] != len(
        payload["required_attachments"]
    ):
        raise ValueError("LaunchTN attachment gate count is inconsistent")
    if payload["summary"]["required_attachments_structural_qa_passed"] != len(
        payload["required_attachments"]
    ):
        raise ValueError("One or more LaunchTN attachment candidates failed structural QA")
    if payload["summary"]["required_attachments_safe_to_upload"] != 0:
        raise ValueError("LaunchTN attachment candidates must remain fail-closed")
    if payload["summary"]["upload_set_ready"] or payload["safe_upload_set"]:
        raise ValueError("LaunchTN safe upload set must remain empty until gates pass")
    if payload["summary"]["final_submit_allowed_without_human"]:
        raise ValueError("LaunchTN final submit must remain human-gated")


def render_markdown(payload: dict[str, Any]) -> str:
    opportunity = payload["opportunity"]
    lines = [
        "# Launch Tennessee 3686 Pitch Competition 2026 Current Portal Field Map",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"- Deadline: `{opportunity['application_deadline']}` ({opportunity['application_deadline_timezone']})",
        f"- Competition: `{opportunity['competition_date']}` at {opportunity['competition_location']}",
        f"- Cash prize: `${opportunity['cash_prize_usd']:,}`",
        "- This is not the formal InvestTN investment application.",
        f"- Eligibility: `{opportunity['eligibility_fit']}`",
        f"- Packet SHA-256: `{payload['application_packet_sha256']}`",
        f"- Safe upload set ready: `{str(payload['summary']['upload_set_ready']).lower()}`",
        "- Final submit without founder review: `false`",
        "",
        "## Portal Fields",
        "",
    ]
    for row in payload["fields"]:
        lines.extend(
            [
                f"### {row['label']}",
                "",
                f"- Field ID: `{row['field_id']}`",
                f"- Required: `{str(row['required']).lower()}`",
                f"- Status: `{row['status']}`",
                f"- Proposed answer: {row['proposed_answer']}",
                f"- Evidence basis: {row['evidence']}",
            ]
        )
        if "character_limit" in row:
            lines.append(
                f"- Characters: `{row['character_count']}/{row['character_limit']}`; within limit=`{str(row['within_character_limit']).lower()}`"
            )
        if "portal_option_group" in row:
            options = payload["portal_options"][row["portal_option_group"]]
            lines.append(f"- Observed portal options: {'; '.join(options)}")
        lines.append("")

    lines.extend(["## Required Attachments", ""])
    for attachment in payload["required_attachments"]:
        lines.extend(
            [
                f"### {attachment['id']}",
                "",
                f"- Status: `{attachment['status']}`",
                f"- Path: `{attachment['path']}`",
                f"- Present: `{str(attachment['present']).lower()}`",
                f"- Bytes: `{attachment['bytes']}`",
                f"- SHA-256: `{attachment['sha256']}`",
                f"- QA hash matches: `{str(attachment['qa_hash_matches']).lower()}`",
                f"- Structural QA passed: `{str(attachment['structural_qa_passed']).lower()}`",
                f"- Safe to upload: `{str(attachment['safe_to_upload']).lower()}`",
                f"- QA date: `{attachment['qa_date']}`",
                f"- Portal requirement: {attachment['portal_requirement']}",
                f"- Founder approval required: `{str(attachment['founder_approval_required']).lower()}`",
                f"- QA checks: {'; '.join(attachment['qa_checks'])}",
                f"- Missing requirements: {'; '.join(attachment['missing_requirements'])}",
                "",
            ]
        )

    lines.extend(
        [
            "## Human Fact Gate",
            "",
            *[f"- {item}" for item in payload["human_fact_gate"]],
            "",
            "## Final Action Gate",
            "",
            f"- Status: `{payload['final_action_gate']['status']}`",
            f"- Action: {payload['final_action_gate']['action']}",
            "",
            "## Source Artifacts",
            "",
        ]
    )
    for name, artifact in payload["source_artifacts"].items():
        lines.append(
            f"- `{name}`: present=`{str(artifact['present']).lower()}` bytes=`{artifact['bytes']}` sha256=`{artifact['sha256']}` path=`{artifact['path']}`"
        )
    lines.extend(["", "## Claim Boundary", "", payload["claim_boundary"], ""])
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": payload["final_action_gate"]["status"],
                "fields": payload["summary"]["field_count"],
                "human_or_private_fact_gates": payload["summary"]["human_or_private_fact_gates"],
                "required_attachment_gates": payload["summary"]["required_attachment_gates"],
                "json": rel(OUT_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
