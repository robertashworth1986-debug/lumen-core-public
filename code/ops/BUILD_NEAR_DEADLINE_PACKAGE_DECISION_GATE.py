from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
GRANTS = ROOT / "grant_submissions"
SPRINT = GRANTS / "funding_sprint_20260709"
NSF = GRANTS / "NSF_Project_Pitch"
OUT = ROOT / "out" / "ops"

JSON_OUT = OUT / "near_deadline_package_decision_gate_latest.json"
MD_OUT = SPRINT / "NEAR_DEADLINE_PACKAGE_DECISION_GATE_2026-07-29.md"
TEAMING_OUT = SPRINT / "FHWA_TSMO_QUALIFIED_TEAMING_REQUEST_2026-07-16.md"
NSF_SOURCE_OUT = NSF / "NSF_PROJECT_PITCH_SOURCE_AUDIT_2026-07-29.json"
ERDC_SOURCE_DIR = SPRINT / "source_attachments" / "W912HZ26SC005"
ERDC_SOURCE_OUT = ERDC_SOURCE_DIR / "SOURCE_MANIFEST_2026-07-29.json"
SAM_CAPTURE = OUT / "sam_gov_entity_status_capture_latest.json"
FHWA_PARTNER_EVIDENCE = SPRINT / "FHWA_TSMO_QUALIFIED_PARTNER_EVIDENCE.json"
FHWA_OUTREACH_CONTROL = (
    SPRINT / "FHWA_TSMO_PARTNER_OUTREACH_CONTROL_2026-07-17.json"
)

NSF_FIELDS = NSF / "PROJECT_PITCH_PORTAL_FIELDS_2026-07-29.md"
NSF_ROUTING = NSF / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-29.json"

NSF_LIMITS = {
    "Technology Innovation": 3500,
    "Technical Objectives and Challenges": 3500,
    "Market Opportunity": 1750,
    "Company and Team": 1750,
}

ERDC_FILES = {
    "CSO_HPCMP_SDC_30April2026_FINAL.pdf": {
        "url": "https://www.erdcwerx.org/wp-content/uploads/2026/05/CSO-HPCMP-SDC-30April2026-FINAL.pdf",
        "expected_pages": 7,
    },
    "HPCMP_SDC_FAQ_20Jul2026.pdf": {
        "url": "https://www.erdcwerx.org/wp-content/uploads/2026/07/HPCMP-SDC-FAQ-Website-20Jul2026.pdf",
        "expected_pages": 13,
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_nsf_fields(path: Path = NSF_FIELDS) -> dict[str, dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^##\s+(.+?)\s*$", text, re.MULTILINE))
    fields: dict[str, dict[str, Any]] = {}
    for index, match in enumerate(headings):
        title = match.group(1).strip()
        if title not in NSF_LIMITS:
            continue
        start = match.end()
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[start:end].strip()
        limit = NSF_LIMITS[title]
        fields[title] = {
            "characters": len(body),
            "limit": limit,
            "remaining": limit - len(body),
            "passes": len(body) <= limit,
        }
    return fields


def erdc_source_manifest() -> dict[str, Any]:
    manifest = read_json(ERDC_SOURCE_OUT)
    files = []
    for item in manifest.get("files", []):
        path = ROOT / item["path"]
        exists = path.is_file()
        actual_bytes = path.stat().st_size if exists else None
        actual_sha256 = sha256_file(path) if exists else None
        files.append(
            {
                **item,
                "exists": exists,
                "actual_bytes": actual_bytes,
                "actual_sha256": actual_sha256,
                "bytes_match": actual_bytes == item.get("bytes"),
                "sha256_match": actual_sha256 == item.get("sha256"),
            }
        )
    return {
        **manifest,
        "files": files,
        "all_present": bool(files) and all(item["exists"] for item in files),
        "all_current_checks_pass": (
            manifest.get("schema") == "lumencore.erdc_sdc_source_manifest.v2"
            and manifest.get("as_of_date") == "2026-07-29"
            and manifest.get("current_attachment_set_complete") is True
            and bool(files)
            and all(
                item["exists"]
                and item["bytes_match"]
                and item["sha256_match"]
                for item in files
            )
        ),
    }


def safe_sam_status() -> dict[str, Any]:
    payload = read_json(SAM_CAPTURE)
    return {
        "verified": payload.get("schema") == "sam_gov_entity_status_capture_v1",
        "registration_status": payload.get("registration_status", "unverified"),
        "purpose_of_registration": payload.get("purpose_of_registration", "unverified"),
        "expiration_date": payload.get("expiration_date", "unverified"),
        "identifiers_included": False,
    }


def build_gate() -> dict[str, Any]:
    fields = extract_nsf_fields()
    routing = read_json(NSF_ROUTING)
    full_proposal = routing.get("full_proposal", {})
    erdc_sources = erdc_source_manifest()
    sam = safe_sam_status()
    nsf_local_ready = (
        set(fields) == set(NSF_LIMITS)
        and all(row["passes"] for row in fields.values())
        and routing.get("schema") == "lumencore.nsf_project_pitch_routing.v2"
        and full_proposal.get("listed_deadlines")
        == ["2026-07-27", "2026-11-04", "2027-03-04", "2027-07-07"]
        and full_proposal.get("past_listed_deadlines") == ["2026-07-27"]
        and full_proposal.get("next_listed_deadline") == "2026-11-04"
        and full_proposal.get("next_listed_deadline_reachable") is False
        and full_proposal.get("submission_allowed") is False
    )
    erdc_source_ready = erdc_sources["all_current_checks_pass"]
    sam_all_awards = (
        sam["registration_status"] == "Active Registration"
        and sam["purpose_of_registration"] == "All Awards"
    )
    partner_verified = FHWA_PARTNER_EVIDENCE.exists()
    fhwa_outreach = read_json(FHWA_OUTREACH_CONTROL)
    fhwa_control_current = (
        fhwa_outreach.get("schema")
        == "lumencore.fhwa_tsmo_partner_outreach_control.v3"
        and fhwa_outreach.get("status")
        == "RESPONSE_LEAD_DECLINED_ADDITIONAL_PARTNER_TEAM_SET"
    )
    qualified_target_contacted = (
        fhwa_control_current
        and fhwa_outreach.get("response_control", {}).get(
            "qualified_partner_evidence_present"
        )
        is False
        and fhwa_outreach.get("response_control", {}).get(
            "qualified_response_lead_referral_present"
        )
        is True
    )
    fhwa_route_closed = (
        fhwa_control_current
        and fhwa_outreach.get("response_control", {}).get("state")
        == "NO_GO_TEAM_SET_NO_ADDITIONAL_PARTNERS"
        and fhwa_outreach.get("delivery_reconciliation", {}).get(
            "team_set_decline_count"
        )
        == 1
    )

    lanes = [
        {
            "rank": 1,
            "lane": "NSF Project Pitch",
            "deadline": None,
            "deadline_semantics": "ROLLING_PROJECT_PITCH",
            "posture": (
                "LOCAL_DRAFT_COMPLETE_PORTAL_AND_ELIGIBILITY_GATES_OPEN"
                if nsf_local_ready
                else "LOCAL_REPAIR_REQUIRED"
            ),
            "local_ready": False,
            "local_draft_complete": nsf_local_ready,
            "quick_funding_fit": "BEST_DIRECT_FIT_OF_THESE_THREE",
            "hard_gates": [
                "Confirm no pending Project Pitch, open invitation, or Phase I proposal under review.",
                "Confirm legal entity, ownership, U.S.-performance, PI employment and effort, and submission authority.",
                "Confirm the authenticated prompts, title limit, and topic selection.",
                "Human reviews the final portal preview and performs the final submit action.",
            ],
            "field_counts": fields,
            "full_proposal_schedule": full_proposal,
            "official_sources": [
                "https://seedfund.nsf.gov/apply/project-pitch/",
                "https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology/nsf26-510/solicitation",
            ],
        },
        {
            "rank": 2,
            "lane": "ERDC Sovereign Defense Cloud CSO",
            "opportunity_number": "W912HZ26SC005",
            "deadline": "2026-08-07T16:00:00-05:00",
            "posture": (
                "CURRENT_SOURCES_READY_PRIVATE_FINAL_GATES_OPEN"
                if erdc_source_ready and sam_all_awards
                else "SOURCE_OR_REGISTRATION_REPAIR_REQUIRED"
            ),
            "local_ready": False,
            "quick_funding_fit": "VALIDATION_AND_RELATIONSHIP_LANE_NOT_CONFIRMED_NEAR_TERM_FUNDING",
            "hard_gates": [
                "Five-page maximum, portrait, 12-point Times New Roman, one-inch margins.",
                "No classified or proprietary information.",
                "ROM covers Phase II prototype development only.",
                "Submission address must match the active SAM registration.",
                "Current proposal contact email must be accurate.",
                "A private final PDF must be validated against the July 20 FAQ.",
                "The notice states that funding is not currently available.",
                "Human confirms the ROM and performs the final portal submit action.",
            ],
            "source_manifest": erdc_sources,
            "sam_status": sam,
            "official_sources": [
                "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/",
                ERDC_FILES["CSO_HPCMP_SDC_30April2026_FINAL.pdf"]["url"],
                ERDC_FILES["HPCMP_SDC_FAQ_20Jul2026.pdf"]["url"],
            ],
        },
        {
            "rank": 3,
            "lane": "FHWA TSMO Data Initiative",
            "opportunity_number": "693JJ326R000012",
            "deadline": "2026-08-03T09:00:00-04:00",
            "posture": (
                "QUALIFIED_PARTNER_EVIDENCE_PRESENT_REVIEW_REQUIRED"
                if partner_verified
                else (
                    "TEAM_SET_DECLINED_NO_GO_UNLESS_NEW_QUALIFIED_PARTNER_JOINS"
                    if fhwa_route_closed
                    else "REFERRED_RESPONSE_LEAD_NO_GO_UNTIL_PARTNER_CONFIRMATION"
                    if qualified_target_contacted
                    else "NO_GO_AS_SOLO_PRIME_UNLESS_QUALIFIED_PARTNER_JOINS"
                )
            ),
            "local_ready": False,
            "quick_funding_fit": "PARTNER_DEPENDENT",
            "hard_gates": [
                "Mandatory five or more years of successfully executed TSMO data-processing experience.",
                "Corporate examples require customer contact, organization, value, work narrative, and period of performance.",
                "Phase I is one PDF: one-page cover, four-page technical capability, three-page corporate experience.",
                "Email must be under 25 MB, unzipped, and use the required subject line.",
                "AI-tool use must be disclosed and all proposal information certified accurate and verified.",
                "Recheck SAM.gov for amendments before submission.",
            ],
            "qualified_partner_evidence_present": partner_verified,
            "qualified_target_contacted": qualified_target_contacted,
            "delivery_failure_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("delivery_failure_count", 0),
            "replacement_send_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("replacement_send_count", 0),
            "confirmed_delivery_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("confirmed_delivery_count", 0),
            "qualified_response_lead_referral_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("qualified_response_lead_referral_count", 0),
            "threaded_acknowledgment_send_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("threaded_acknowledgment_send_count", 0),
            "fit_check_confirmed_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("fit_check_confirmed_count", 0),
            "inbound_response_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("response_count", 0),
            "team_set_decline_count": fhwa_outreach.get(
                "delivery_reconciliation", {}
            ).get("team_set_decline_count", 0),
            "outreach_route_closed": fhwa_route_closed,
            "partner_outreach_control": (
                rel(FHWA_OUTREACH_CONTROL) if fhwa_control_current else None
            ),
            "official_notice": "https://sam.gov/opp/82cfdcdb95ae40a7b70dba615c31f89b/view",
            "source_caveat": (
                "The SAM public API returned 404 during this audit. Requirements were checked "
                "against the public government-RFP text mirror and must be rechecked against "
                "the signed-in SAM attachment and amendments before submission."
            ),
        },
    ]

    return {
        "schema": "lumencore.near_deadline_package_decision_gate.v1",
        "generated_utc": now_utc(),
        "as_of_date": "2026-07-29",
        "decision": {
            "primary_lane": "NSF Project Pitch",
            "secondary_lane": "ERDC Sovereign Defense Cloud CSO",
            "partner_only_lane": "FHWA TSMO Data Initiative",
            "reason": (
                "NSF has the smallest truthful completion gap and no fixed Project Pitch "
                "deadline. ERDC is a credible five-page validation lane but currently has no "
                "available funding. The first FHWA TSMO contact route rejected delivery; the "
                "replacement route replied and referred the request to its response lead. That "
                "lead confirmed the team was already set and would not add partners. This route "
                "is closed, and FHWA remains noncompliant as a solo prime unless a different "
                "qualified partner supplies written corporate-experience evidence."
            ),
        },
        "lanes": lanes,
        "claim_boundary": [
            "No award, invitation, customer commitment, partner commitment, or funding availability is claimed.",
            "No portal state is inferred from local files.",
            "No final submission is authorized by this audit artifact.",
        ],
    }


def nsf_source_audit(gate: dict[str, Any]) -> dict[str, Any]:
    nsf_lane = next(item for item in gate["lanes"] if item["lane"] == "NSF Project Pitch")
    source = read_json(NSF_SOURCE_OUT)
    return {
        **source,
        "local_field_counts": nsf_lane["field_counts"],
    }


def render_markdown(gate: dict[str, Any]) -> str:
    lines = [
        "# Near-Deadline Package Decision Gate",
        "",
        "As of: July 29, 2026",
        "",
        "## Decision",
        "",
        "1. **NSF Project Pitch** - the local draft is complete; verify applicant facts, authenticated prompts, and the duplicate-pitch/open-invitation gate before any final action.",
        "2. **ERDC Sovereign Defense Cloud** - current sources and a conforming public draft exist, but only a separately validated private final PDF may become an upload candidate; the notice says funding is not currently available.",
        "3. **FHWA TSMO** - Cambridge Systematics confirmed its team was already set after the replacement route reached its response lead. Close that route without another follow-up. Do not submit as a solo prime unless a different qualified partner supplies written corporate-experience evidence.",
        "",
        gate["decision"]["reason"],
        "",
        "## Package Gates",
        "",
    ]
    for lane in gate["lanes"]:
        deadline = lane.get("deadline") or "Rolling Project Pitch"
        lines.extend(
            [
                f"### {lane['rank']}. {lane['lane']}",
                "",
                f"- Deadline: `{deadline}`",
                f"- Posture: `{lane['posture']}`",
                f"- Quick-funding fit: `{lane['quick_funding_fit']}`",
                "- Hard gates:",
            ]
        )
        lines.extend(f"  - {item}" for item in lane["hard_gates"])
        lines.append("")
    lines.extend(
        [
            "## Submission Boundary",
            "",
            "This gate does not claim an invitation, award, partner, customer, or available funding. Portal state and final legal or financial representations require human verification at action time.",
            "",
        ]
    )
    return "\n".join(lines)


def render_teaming_request() -> str:
    return """# FHWA TSMO Qualified Teaming Request

Opportunity: `693JJ326R000012`
Government deadline: August 3, 2026, 9:00 AM ET
Internal partner-evidence target: July 23, 2026

## Subject

FHWA TSMO Data Initiative - qualified data-processing teaming discussion

## Message

Hello [Name],

LumenCore is evaluating a focused teaming role for the FHWA Transportation Systems Management and Operations Data Initiative, solicitation 693JJ326R000012. Our contribution would be a bounded validation and prototype layer for data-quality controls, chronological model benchmarking, uncertainty and abstention, reproducible evidence manifests, and API-based decision support.

FHWA Phase I includes a mandatory corporate-experience gate: five or more years of successfully executed TSMO data-processing projects, supported by recent project descriptions with customer contacts, organization, total value, work performed, and period of performance. We will not represent experience that we cannot document.

Would your organization be open to a rapid prime/subcontractor fit check? Before discussing proposal language, we would need written confirmation that your team can document the mandatory experience and that the cited customers may be contacted by the Government. We would provide a clearly bounded technical role and an AI-use disclosure, and all claims would remain subject to joint verification.

If the fit is real, the next step is a 30-minute compliance call covering role split, references, facilities, conflicts, data rights, and the August 3 submission schedule. No confidential information is needed for the initial fit check.

Best,
Robert Ashworth
Founder and Chief Scientist, LumenCore

## Send Gate

- Add a named recipient only after verifying that the organization performs TSMO data processing.
- Do not attach patent-sensitive, proprietary, or private customer material.
- Do not state that a teaming relationship exists until both parties confirm it in writing.
- Do not send after July 23 without first reassessing whether enough time remains for a compliant joint package.
"""


def write_outputs(gate: dict[str, Any]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ERDC_SOURCE_DIR.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(gate, indent=2) + "\n", encoding="utf-8")
    MD_OUT.write_text(render_markdown(gate), encoding="utf-8")


def main() -> int:
    gate = build_gate()
    write_outputs(gate)
    print(json.dumps(gate["decision"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
