from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "grant_submissions" / "NASHVILLE_EC_FALL_2026"
OUT_JSON = OUT_DIR / "NASHVILLE_EC_FALL_2026_APPLICATION_MANIFEST_2026-07-16.json"
OUT_MD = OUT_DIR / "NASHVILLE_EC_FALL_2026_PORTAL_FIELD_MAP_2026-07-16.md"

OFFICIAL_SOURCES = {
    "application": "https://ec.co/apply/",
    "accelerators": "https://ec.co/accelerators/",
    "takeoff": "https://ec.co/accelerators/takeoff/",
    "inflight": "https://ec.co/accelerators/inflight/",
    "project_healthcare": "https://ec.co/accelerators/project-healthcare/",
}

PORTAL_FORM_URL = "https://form.jotform.com/261305765806056"
HOURS_PER_WEEK_OPTIONS = (
    "Less than 10",
    "10\u201320",
    "20\u201330",
    "30+",
)
CUSTOMER_CONVERSATION_OPTIONS = (
    "0",
    "1 to 10",
    "11 to 25",
    "26 to 50",
    "50+",
)

BUSINESS_DESCRIPTION = (
    "LumenCore is a proof-to-pilot AI validation platform for infrastructure, "
    "energy, and other high-consequence time-series systems. It helps technical "
    "buyers compare candidate models and workflows against locked baselines using "
    "past-only evaluation, calibrated uncertainty, explicit abstention, and "
    "hash-verifiable replay receipts. The problem is that teams can deploy confident "
    "AI outputs without a defensible record of which data, metric, or validation "
    "window justified the decision. LumenCore's first commercial product is a paid "
    "evidence-review and replay-scoping sprint that defines what a buyer-controlled "
    "pilot would need to prove."
)

PROBLEM_EVIDENCE = (
    "Current evidence is technical and engagement-stage, not customer-result proof. "
    "LumenCore has reproducible benchmark and replay infrastructure with preserved "
    "negative results, while EPRI initiated Open Power AI consortium onboarding and "
    "LANL received a bounded reviewer package. Those signals show that controlled "
    "benchmarking and reviewer-safe evidence matter to serious institutions; the next "
    "proof needed is a buyer-owned historical replay or paid pilot with locked "
    "acceptance metrics."
)

SUCCESS_6_TO_12_MONTHS = (
    "Secure one paid buyer-controlled evaluation, complete one independent "
    "reproduction with a signed receipt, convert at least one institutional "
    "relationship into a scoped pilot, and establish a repeatable sales process for "
    "evidence-review and replay-scope packages. Success will be measured by signed "
    "scope, lawful data access, preregistered acceptance metrics, reviewer completion, "
    "and paid work rather than unsupported valuation or savings claims."
)

WHY_NOW = (
    "The technical MVP and evidence controls exist; the bottleneck has moved from "
    "building to customer selection, positioning, pricing, and pilot conversion. EPRI "
    "has initiated consortium onboarding, LANL has received a bounded reviewer packet, "
    "and federal capability responses have produced transmission receipts, but no paid "
    "customer or field validation is claimed. The Fall cohort aligns with the need for "
    "local mentors, buyer introductions, and a disciplined go-to-market process."
)


def field(
    question_id: int,
    section: str,
    label: str,
    required: bool,
    proposed_answer: str,
    status: str = "READY",
    evidence: str = "Public-safe local business record",
    portal_options: tuple[str, ...] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "question_id": question_id,
        "section": section,
        "label": label,
        "required": required,
        "proposed_answer": proposed_answer,
        "status": status,
        "evidence": evidence,
    }
    if portal_options is not None:
        row["portal_options"] = list(portal_options)
    return row


FIELDS = [
    field(3, "Founder Information", "Founder Name", True, "Robert Ashworth"),
    field(
        4,
        "Founder Information",
        "Founder Email",
        True,
        "[PRIVATE_PORTAL_ENTRY_FROM_GMAIL_ACCOUNT]",
        "PRIVATE_PORTAL_ENTRY",
        "Authenticated Gmail account",
    ),
    field(
        75,
        "Founder Information",
        "Founder Phone Number",
        False,
        "[PRIVATE_PORTAL_ENTRY]",
        "PRIVATE_PORTAL_ENTRY",
        "Private contact record",
    ),
    field(
        26,
        "Founder Information",
        "LinkedIn Profile URL",
        False,
        "https://www.linkedin.com/in/robert-ashworth-40a9b7376",
    ),
    field(6, "Founder Information", "Business Name", True, "LumenCore"),
    field(27, "Founder Information", "Business City and State", True, "Nashville, TN"),
    field(76, "Founder Information", "Business Website", False, "https://lumen-core.ai"),
    field(
        38,
        "Founder Information",
        "Are you a first-time founder?",
        True,
        "[SELECT YES OR NO AFTER FOUNDER CONFIRMATION]",
        "HUMAN_CONFIRM_REQUIRED",
        "No authoritative local record found",
    ),
    field(
        28,
        "Founder Information",
        "Are you working on this business full-time?",
        True,
        "[SELECT YES OR NO AFTER FOUNDER CONFIRMATION]",
        "HUMAN_CONFIRM_REQUIRED",
        "No authoritative employment-status record found",
    ),
    field(
        29,
        "Founder Information",
        "Hours per week actively working on the business",
        True,
        "30+ only if accurate; otherwise select the truthful listed bracket",
        "HUMAN_CONFIRM_REQUIRED",
        "Founder attestation required",
        HOURS_PER_WEEK_OPTIONS,
    ),
    field(96, "Business Stage", "Tell us about your business", True, BUSINESS_DESCRIPTION),
    field(
        30,
        "Business Stage",
        "Which best describes your business today?",
        True,
        "I am building a prototype or MVP",
        evidence="Repository describes a research prototype and working API/dashboard components",
    ),
    field(
        31,
        "Business Stage",
        "How long have you been working on this business?",
        True,
        "1 to 3 years if accurate",
        "HUMAN_CONFIRM_REQUIRED",
        "Founder attestation required",
    ),
    field(33, "Business Stage", "Industry", True, "Technology or SaaS"),
    field(
        60,
        "Business Stage",
        "Healthcare focus",
        True,
        "Not applicable unless the portal conditionally routes to Project Healthcare",
        "CONDITIONAL_NOT_APPLICABLE",
        "Recommended route is TakeOff",
    ),
    field(32, "Business Stage", "Business model", True, "B2B"),
    field(
        34,
        "Business Stage",
        "Current product or service readiness",
        True,
        "MVP built",
        evidence="Working ingestion, benchmark, API, dashboard, and evidence-manifest components",
    ),
    field(
        35,
        "Business Stage",
        "Do you currently have customers or users?",
        True,
        "No",
        evidence="No paying customer, pilot customer, or production user is currently claimed",
    ),
    field(37, "Business Stage", "Team size including founder", True, "1"),
    field(
        84,
        "Validation",
        "Customer discovery or sales conversations completed",
        True,
        "1 to 10 unless Robert confirms at least 11 genuine customer-discovery or sales conversations; select 0 if none qualify",
        "HUMAN_CONFIRM_REQUIRED",
        "Gmail shows multiple institutional exchanges, but the form's conversation definition requires founder confirmation",
        CUSTOMER_CONVERSATION_OPTIONS,
    ),
    field(85, "Validation", "Clearest evidence the business solves a real problem", True, PROBLEM_EVIDENCE),
    field(
        95,
        "Needs",
        "What are you most trying to figure out right now?",
        False,
        "Find my first customers; Achieve product-market fit; Create a repeatable sales process; Raise capital",
    ),
    field(
        94,
        "Needs",
        "Areas needing the most support",
        True,
        "Clarifying Vision, Strategy, and Priorities; Sales Process and Revenue Growth; Product Development and Product-Market Fit; Business Model and Financial Modeling; Raising Capital",
    ),
    field(88, "Goals", "Success over the next 6 to 12 months", True, SUCCESS_6_TO_12_MONTHS),
    field(89, "Goals", "Why now?", True, WHY_NOW),
    field(
        66,
        "Financials",
        "Total revenue for previous year",
        True,
        "$0 only after founder confirms no business revenue",
        "HUMAN_CONFIRM_REQUIRED",
        "Local materials describe LumenCore as pre-revenue but require founder confirmation",
    ),
    field(
        36,
        "Financials",
        "Current annualized or most recent 12-month revenue",
        True,
        "$0 only after founder confirms no business revenue",
        "HUMAN_CONFIRM_REQUIRED",
        "Local materials describe LumenCore as pre-revenue but require founder confirmation",
    ),
    field(
        62,
        "Financials",
        "Total founder cash invested to date",
        True,
        "[ENTER VERIFIED CUMULATIVE BUSINESS INVESTMENT]",
        "HUMAN_CONFIRM_REQUIRED",
        "No authoritative local total found",
    ),
    field(
        63,
        "Financials",
        "Total grant funding received",
        True,
        "$0 if no grant award funds have been received",
        "HUMAN_CONFIRM_REQUIRED",
        "No grant award is currently claimed",
    ),
    field(
        64,
        "Financials",
        "Total investor capital raised",
        True,
        "$0 if no investor capital has been received",
        "HUMAN_CONFIRM_REQUIRED",
        "No investment is currently claimed",
    ),
    field(
        65,
        "Financials",
        "Total debt leveraged to date",
        True,
        "[ENTER BUSINESS DEBT ONLY; DO NOT INCLUDE PERSONAL DEBT UNLESS THE FORM REQUIRES IT]",
        "HUMAN_CONFIRM_REQUIRED",
        "No authoritative business-debt total found",
    ),
    field(
        61,
        "Financials",
        "Prepared to invest in a program fee at this time?",
        True,
        "No; request financial aid before accepting any fee",
        "READY_NO_FEE_COMMITMENT",
        "TakeOff lists a $500 fee and $125 required to start; no spending is authorized",
    ),
    field(83, "Optional Demographics", "Race and ethnicity", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(82, "Optional Demographics", "Gender", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(81, "Optional Demographics", "LGBTQIA+ identity", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(69, "Optional Demographics", "Pronouns", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(80, "Optional Demographics", "Military service", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(79, "Optional Demographics", "Disability or chronic condition", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(73, "Optional Demographics", "Access needs", False, "Founder choice", "OPTIONAL_FOUNDER_CHOICE"),
    field(24, "Source", "How did you hear about the accelerator?", True, "EC Email Newsletter"),
    field(
        90,
        "Source",
        "Other source details",
        True,
        "Not applicable because EC Email Newsletter is selected",
        "CONDITIONAL_NOT_APPLICABLE",
    ),
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for row in FIELDS:
        status_counts[row["status"]] = status_counts.get(row["status"], 0) + 1

    payload: dict[str, Any] = {
        "schema": "lumencore.nashville_ec_fall_2026_application.v1",
        "generated_utc": generated_utc or now_utc(),
        "opportunity": {
            "name": "Nashville Entrepreneur Center Fall 2026 Accelerators",
            "deadline_date": "2026-07-17",
            "deadline_time": None,
            "deadline_time_status": "NOT_LISTED_ON_OFFICIAL_PAGE",
            "official_deadline_text": "Applications close July 17, 2026; no time is listed on the official page.",
            "operational_finish_target": "2026-07-17T12:00:00-05:00",
            "operational_finish_target_status": "INTERNAL_TARGET_NOT_OFFICIAL_DEADLINE",
            "recommended_route": "TakeOff",
            "alternate_routes": [],
            "eligibility_fit": "Nashville-based solo pre-revenue technology founder with a working MVP",
            "application_form_id": "261305765806056",
            "application_form_url": PORTAL_FORM_URL,
            "portal_schema_status": "OBSERVED_WITHOUT_SAVE_OR_SUBMIT_2026-07-16",
        },
        "program_economics": {
            "application_fee": None,
            "application_fee_status": "NOT_LISTED_ON_REVIEWED_OFFICIAL_PAGES",
            "takeoff_program_fee": 500,
            "takeoff_required_to_start": 125,
            "equity_taken": 0,
            "fee_commitment_authorized": False,
            "financial_aid_request_recommended": True,
        },
        "summary": {
            "field_count": len(FIELDS),
            "required_field_count": sum(1 for row in FIELDS if row["required"]),
            "status_counts": status_counts,
            "portal_ready_except_human_facts": True,
            "final_submit_allowed_without_human": False,
            "accept_program_terms_allowed_without_human": False,
            "fee_commitment_allowed_without_human": False,
        },
        "fields": FIELDS,
        "human_fact_gate": [
            "First-time founder status",
            "Full-time business status and weekly hours",
            "Time working on the business",
            "Qualifying customer-discovery conversation count",
            "Previous-year and trailing-12-month business revenue",
            "Cumulative founder cash investment",
            "Grant funds received and investor capital received",
            "Business debt leveraged",
            "Optional demographic responses",
        ],
        "final_action_gate": {
            "status": "HUMAN_REVIEW_AND_SUBMIT_REQUIRED",
            "action": "Review the final portal preview and submit before the official July 17 close.",
            "submit_allowed_without_human": False,
        },
        "official_sources": OFFICIAL_SOURCES,
        "claim_boundary": (
            "This packet prepares a truthful accelerator application. It does not claim a "
            "paying customer, field validation, independent validation, grant or investment "
            "funding, program acceptance, revenue, realized savings, or permission to accept "
            "fees or terms."
        ),
    }
    payload["application_packet_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    opportunity = payload["opportunity"]
    economics = payload["program_economics"]
    lines = [
        "# Nashville Entrepreneur Center Fall 2026 Portal Field Map",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Decision",
        "",
        f"- Recommended route: `{opportunity['recommended_route']}`",
        f"- Deadline: `{opportunity['official_deadline_text']}`",
        f"- Internal finish target: `{opportunity['operational_finish_target']}` ({opportunity['operational_finish_target_status']})",
        f"- Eligibility fit: {opportunity['eligibility_fit']}",
        f"- TakeOff fee: `${economics['takeoff_program_fee']}`; `${economics['takeoff_required_to_start']}` required to start",
        "- Fee answer: `No`; request financial aid before accepting any fee",
        "- Final submit without human: `false`",
        f"- Packet SHA-256: `{payload['application_packet_sha256']}`",
        "",
        "## Portal Fields",
        "",
    ]
    current_section = None
    for row in payload["fields"]:
        if row["section"] != current_section:
            current_section = row["section"]
            lines.extend([f"### {current_section}", ""])
        lines.extend(
            [
                f"#### Q{row['question_id']} - {row['label']}",
                "",
                f"- Required: `{str(row['required']).lower()}`",
                f"- Status: `{row['status']}`",
                f"- Proposed answer: {row['proposed_answer']}",
                f"- Evidence basis: {row['evidence']}",
                "",
            ]
        )
        if row.get("portal_options"):
            lines.extend(
                [
                    f"- Verified portal options: {'; '.join(row['portal_options'])}",
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
            "- Do not accept program fees, terms, or a cohort seat without a separate human decision.",
            "",
            "## Official Sources",
            "",
            *[f"- {name}: {url}" for name, url in payload["official_sources"].items()],
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "PORTAL_READY_HUMAN_FACTS_AND_FINAL_SUBMIT_GATED",
                "fields": payload["summary"]["field_count"],
                "human_fact_gates": len(payload["human_fact_gate"]),
                "json": OUT_JSON.relative_to(ROOT).as_posix(),
                "markdown": OUT_MD.relative_to(ROOT).as_posix(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
