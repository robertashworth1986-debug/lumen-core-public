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
MD_OUT = SPRINT / "NEAR_DEADLINE_PACKAGE_DECISION_GATE_2026-07-16.md"
TEAMING_OUT = SPRINT / "FHWA_TSMO_QUALIFIED_TEAMING_REQUEST_2026-07-16.md"
NSF_SOURCE_OUT = NSF / "NSF_PROJECT_PITCH_SOURCE_AUDIT_2026-07-16.json"
ERDC_SOURCE_DIR = SPRINT / "source_attachments" / "W912HZ26SC005"
ERDC_SOURCE_OUT = ERDC_SOURCE_DIR / "SOURCE_MANIFEST_2026-07-16.json"
SAM_CAPTURE = OUT / "sam_gov_entity_status_capture_latest.json"
FHWA_PARTNER_EVIDENCE = SPRINT / "FHWA_TSMO_QUALIFIED_PARTNER_EVIDENCE.json"

NSF_FIELDS = NSF / "PROJECT_PITCH_PORTAL_FIELDS_2026-07-16.md"
NSF_ROUTING = NSF / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json"

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
    "HPCMP_SDC_FAQ_9June2026.pdf": {
        "url": "https://www.erdcwerx.org/wp-content/uploads/2026/06/HPCMP-SDC-FAQ-Website-9June2026.pdf",
        "expected_pages": 6,
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
    files = []
    for name, source in ERDC_FILES.items():
        path = ERDC_SOURCE_DIR / name
        files.append(
            {
                "path": rel(path),
                "exists": path.exists(),
                "bytes": path.stat().st_size if path.exists() else None,
                "sha256": sha256_file(path) if path.exists() else None,
                "expected_pages": source["expected_pages"],
                "official_url": source["url"],
            }
        )
    return {
        "schema": "lumencore.erdc_sdc_source_manifest.v1",
        "as_of_date": "2026-07-16",
        "opportunity_number": "W912HZ26SC005",
        "files": files,
        "all_present": all(item["exists"] for item in files),
        "claim_boundary": (
            "These files establish public solicitation requirements only; they do not "
            "establish selection, funding availability, award, or technical validation."
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
    erdc_sources = erdc_source_manifest()
    sam = safe_sam_status()
    nsf_local_ready = (
        set(fields) == set(NSF_LIMITS)
        and all(row["passes"] for row in fields.values())
        and routing.get("schema") == "lumencore.nsf_project_pitch_routing.v1"
    )
    erdc_source_ready = erdc_sources["all_present"]
    sam_all_awards = (
        sam["registration_status"] == "Active Registration"
        and sam["purpose_of_registration"] == "All Awards"
    )
    partner_verified = FHWA_PARTNER_EVIDENCE.exists()

    lanes = [
        {
            "rank": 1,
            "lane": "NSF Project Pitch",
            "deadline": None,
            "deadline_semantics": "ROLLING_PROJECT_PITCH",
            "posture": (
                "STAGE_IN_PORTAL_AFTER_DUPLICATE_GATE"
                if nsf_local_ready
                else "LOCAL_REPAIR_REQUIRED"
            ),
            "local_ready": nsf_local_ready,
            "quick_funding_fit": "BEST_DIRECT_FIT_OF_THESE_THREE",
            "hard_gates": [
                "Confirm no pending Project Pitch, open invitation, or Phase I proposal under review.",
                "Confirm the legal business name and founder/PI title shown in the account.",
                "Human reviews the final portal preview and performs the final submit action.",
            ],
            "field_counts": fields,
            "official_sources": [
                "https://seedfund.nsf.gov/apply/project-pitch/",
                "https://seedfund.nsf.gov/solicitations/",
            ],
        },
        {
            "rank": 2,
            "lane": "ERDC Sovereign Defense Cloud CSO",
            "opportunity_number": "W912HZ26SC005",
            "deadline": "2026-08-07T16:00:00-05:00",
            "posture": (
                "BUILD_FIVE_PAGE_SOLUTION_BRIEF"
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
                "The notice states that funding is not currently available.",
                "Human confirms the ROM and performs the final portal submit action.",
            ],
            "source_manifest": erdc_sources,
            "sam_status": sam,
            "official_sources": [
                "https://www.erdcwerx.org/sovereign-defense-cloud-for-high-performance-computing/",
                ERDC_FILES["CSO_HPCMP_SDC_30April2026_FINAL.pdf"]["url"],
                ERDC_FILES["HPCMP_SDC_FAQ_9June2026.pdf"]["url"],
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
                else "NO_GO_AS_SOLO_PRIME_UNLESS_QUALIFIED_PARTNER_JOINS"
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
        "as_of_date": "2026-07-16",
        "decision": {
            "primary_lane": "NSF Project Pitch",
            "secondary_lane": "ERDC Sovereign Defense Cloud CSO",
            "partner_only_lane": "FHWA TSMO Data Initiative",
            "reason": (
                "NSF has the smallest truthful completion gap and no fixed Project Pitch "
                "deadline. ERDC is a credible five-page validation lane but currently has no "
                "available funding. FHWA is not compliant as a solo prime without qualifying "
                "TSMO corporate experience or a partner that supplies it."
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
    return {
        "schema": "lumencore.nsf_project_pitch_source_audit.v1",
        "as_of_date": gate["as_of_date"],
        "official_facts": {
            "field_limits": NSF_LIMITS,
            "typical_response_time": "1-2 months",
            "only_one_pending_pitch": True,
            "full_proposal_requires_invitation": True,
            "current_invited_full_proposal_deadline": "2026-11-04",
            "july_27_2026_currently_listed": False,
        },
        "local_field_counts": nsf_lane["field_counts"],
        "official_sources": nsf_lane["official_sources"],
        "claim_boundary": (
            "Official schedule and field controls do not prove portal eligibility, invitation, "
            "submission, review, or award."
        ),
    }


def render_markdown(gate: dict[str, Any]) -> str:
    lines = [
        "# Near-Deadline Package Decision Gate",
        "",
        "As of: July 16, 2026",
        "",
        "## Decision",
        "",
        "1. **NSF Project Pitch** - stage first after checking the duplicate-pitch/open-invitation gate in the portal.",
        "2. **ERDC Sovereign Defense Cloud** - build the compliant five-page solution brief as a validation and relationship lane; the notice says funding is not currently available.",
        "3. **FHWA TSMO** - do not submit as a solo prime unless a qualified partner supplies the mandatory corporate-experience evidence.",
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
    TEAMING_OUT.write_text(render_teaming_request(), encoding="utf-8")
    NSF_SOURCE_OUT.write_text(
        json.dumps(nsf_source_audit(gate), indent=2) + "\n", encoding="utf-8"
    )
    ERDC_SOURCE_OUT.write_text(
        json.dumps(erdc_source_manifest(), indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    gate = build_gate()
    write_outputs(gate)
    print(json.dumps(gate["decision"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
