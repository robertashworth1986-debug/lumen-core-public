from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NSF_DIR = ROOT / "grant_submissions" / "NSF_Project_Pitch"
OUT = (
    NSF_DIR
    / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-29.json"
)
SOURCE_AUDIT_OUT = (
    NSF_DIR
    / "NSF_PROJECT_PITCH_SOURCE_AUDIT_2026-07-29.json"
)

AS_OF_DATE = "2026-07-29"
CURRENT_DATE = date.fromisoformat(AS_OF_DATE)
FULL_PROPOSAL_DEADLINES = (
    "2026-07-27",
    "2026-11-04",
    "2027-03-04",
    "2027-07-07",
)
NEXT_LISTED_DEADLINE = next(
    deadline
    for deadline in FULL_PROPOSAL_DEADLINES
    if date.fromisoformat(deadline) >= CURRENT_DATE
)
PAST_LISTED_DEADLINES = tuple(
    deadline
    for deadline in FULL_PROPOSAL_DEADLINES
    if date.fromisoformat(deadline) < CURRENT_DATE
)
FUTURE_LISTED_DEADLINES = tuple(
    deadline
    for deadline in FULL_PROPOSAL_DEADLINES
    if date.fromisoformat(deadline) >= CURRENT_DATE
)

OFFICIAL_SOURCES = {
    "project_pitch_overview": "https://seedfund.nsf.gov/project-pitch/",
    "project_pitch_details": "https://seedfund.nsf.gov/apply/project-pitch/",
    "solicitation_26_510": (
        "https://www.nsf.gov/funding/opportunities/"
        "small-business-innovation-research-small-business-technology/"
        "nsf26-510/solicitation"
    ),
    "solicitation_26_511": (
        "https://www.nsf.gov/funding/opportunities/"
        "small-business-innovation-research-small-business-technology-0/"
        "nsf26-511/solicitation"
    ),
    "solicitation_schedule": "https://seedfund.nsf.gov/solicitations/",
}

FIELD_LIMITS = {
    "Technology Innovation": 3500,
    "Technical Objectives and Challenges": 3500,
    "Market Opportunity": 1750,
    "Company and Team": 1750,
}


def build_source_audit() -> dict[str, Any]:
    return {
        "schema": "lumencore.nsf_project_pitch_source_audit.v1",
        "as_of_date": AS_OF_DATE,
        "scope": "CURRENT_PUBLIC_OFFICIAL_SOURCES_ONLY",
        "authenticated_portal_access_performed": False,
        "sources": OFFICIAL_SOURCES,
        "verified_public_facts": {
            "project_pitch_is_rolling": True,
            "project_pitch_has_no_standalone_calendar_deadline": True,
            "one_active_pitch_invitation_or_phase_i_proposal_constraint": True,
            "full_proposal_requires_official_invitation": True,
            "field_limits": FIELD_LIMITS,
            "listed_full_proposal_deadlines": list(FULL_PROPOSAL_DEADLINES),
            "next_listed_full_proposal_deadline": NEXT_LISTED_DEADLINE,
            "deadline_time": "17:00",
            "deadline_timezone_semantics": (
                "SUBMITTING_ORGANIZATION_LOCAL_TIME"
            ),
        },
        "not_verified_by_public_source_review": [
            "Authenticated MyWork Project Pitch form schema and title limit.",
            "Whether a Project Pitch is pending for the applicant.",
            "Whether an open invitation or Phase I proposal exists.",
            "Legal entity, ownership, employee-count, and U.S.-performance facts.",
            "Principal Investigator employment and effort eligibility.",
            "Applicant representations, certifications, and submission authority.",
        ],
        "claim_boundary": (
            "This audit establishes only the current public instructions, field "
            "limits, invitation gate, and listed schedule. It does not establish "
            "applicant eligibility, portal state, invitation status, or authority "
            "to submit."
        ),
    }


def build_manifest() -> dict[str, Any]:
    return {
        "schema": "lumencore.nsf_project_pitch_routing.v2",
        "as_of_date": AS_OF_DATE,
        "source_scope": "CURRENT_PUBLIC_OFFICIAL_SOURCES_ONLY",
        "source_audit": SOURCE_AUDIT_OUT.relative_to(ROOT).as_posix(),
        "routing": {
            "primary_solicitation": "NSF 26-510",
            "alternate_solicitation": (
                "NSF 26-511 only if NSF confirms scientific-instrumentation fit"
            ),
            "reason": (
                "The current proposal is a trustworthy-AI software and validation "
                "platform; the general deep-technology solicitation is the cleaner "
                "documented fit."
            ),
        },
        "project_pitch": {
            "current_gate": True,
            "deadline": None,
            "deadline_semantics": "ROLLING_PREREQUISITE_NO_FIXED_DUE_DATE",
            "typical_response_time": "1-2 months",
            "one_active_pitch_invitation_or_proposal_at_a_time": True,
            "authenticated_portal_state_verified": False,
            "legal_eligibility_verified": False,
            "submission_allowed": False,
            "final_submit_allowed_without_human": False,
            "portal_url": "https://seedfund.nsf.gov/project-pitch/",
        },
        "full_proposal": {
            "current_official_schedule_checked_on": AS_OF_DATE,
            "listed_deadlines": list(FULL_PROPOSAL_DEADLINES),
            "past_listed_deadlines": list(PAST_LISTED_DEADLINES),
            "future_listed_deadlines": list(FUTURE_LISTED_DEADLINES),
            "deadline_time": "17:00",
            "deadline_timezone_semantics": "SUBMITTING_ORGANIZATION_LOCAL_TIME",
            "next_listed_deadline": NEXT_LISTED_DEADLINE,
            "next_listed_deadline_reachable": False,
            "access_state": "BLOCKED_NO_VERIFIED_PROJECT_PITCH_INVITATION",
            "invitation_required": True,
            "invitation_verified": False,
            "planning_target": NEXT_LISTED_DEADLINE,
            "planning_target_semantics": (
                "INVITATION_CONTINGENT_NOT_AUTHORIZATION_OR_GUARANTEE"
            ),
            "submission_allowed": False,
        },
        "portal_state": {
            "pending_project_pitch_status_verified": False,
            "open_invitation_status_verified": False,
            "full_proposal_under_review_verified": False,
        },
        "applicant_fact_gates": {
            "legal_business_name_verified": False,
            "small_business_eligibility_verified": False,
            "ownership_eligibility_verified": False,
            "principal_investigator_verified": False,
            "principal_investigator_employment_and_effort_verified": False,
            "submission_authority_verified": False,
        },
        "field_limits": FIELD_LIMITS,
        "official_sources": OFFICIAL_SOURCES,
        "claim_boundary": [
            "No NSF invitation is claimed.",
            "No full-proposal authorization is claimed.",
            (
                "The past July 27 deadline is retained only as schedule history "
                "and is not represented as the current deadline."
            ),
            (
                "The November 4 date is invitation-contingent planning, not a "
                "Project Pitch deadline or submission authorization."
            ),
            (
                "No customer commitment, independent validation, award, or realized "
                "economic impact is claimed."
            ),
            "Portal state and legal company facts require human confirmation.",
        ],
    }


def validate_source_audit(payload: dict[str, Any]) -> None:
    facts = payload["verified_public_facts"]
    if facts["field_limits"] != FIELD_LIMITS:
        raise ValueError("NSF Project Pitch field-limit audit is inconsistent")
    if facts["next_listed_full_proposal_deadline"] != NEXT_LISTED_DEADLINE:
        raise ValueError("NSF next-deadline source audit is inconsistent")
    if payload["authenticated_portal_access_performed"] is not False:
        raise ValueError("NSF source audit must remain public and read-only")


def validate_manifest(payload: dict[str, Any]) -> None:
    full = payload["full_proposal"]
    pitch = payload["project_pitch"]
    if full["listed_deadlines"] != list(FULL_PROPOSAL_DEADLINES):
        raise ValueError("NSF full-proposal deadline snapshot is inconsistent")
    if full["past_listed_deadlines"] != list(PAST_LISTED_DEADLINES):
        raise ValueError("NSF past deadline history is inconsistent")
    if full["future_listed_deadlines"] != list(FUTURE_LISTED_DEADLINES):
        raise ValueError("NSF future deadline schedule is inconsistent")
    if full["next_listed_deadline"] != NEXT_LISTED_DEADLINE:
        raise ValueError("NSF next listed deadline is inconsistent")
    if full["next_listed_deadline_reachable"] is not False:
        raise ValueError("NSF invitation gate is not enforced")
    if full["submission_allowed"] is not False:
        raise ValueError("NSF full proposal is incorrectly submit-authorized")
    if pitch["deadline"] is not None:
        raise ValueError("NSF rolling Project Pitch has a fixed deadline")
    if pitch["submission_allowed"] is not False:
        raise ValueError("NSF Project Pitch is incorrectly submit-authorized")
    if pitch["final_submit_allowed_without_human"] is not False:
        raise ValueError("NSF Project Pitch human gate is missing")


def main() -> int:
    source_audit = build_source_audit()
    payload = build_manifest()
    validate_source_audit(source_audit)
    validate_manifest(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    SOURCE_AUDIT_OUT.write_text(
        json.dumps(source_audit, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "NSF_PROJECT_PITCH_ROUTING_CONTROL_WRITTEN",
                "outputs": [
                    OUT.relative_to(ROOT).as_posix(),
                    SOURCE_AUDIT_OUT.relative_to(ROOT).as_posix(),
                ],
                "next_listed_full_proposal_deadline": payload[
                    "full_proposal"
                ]["next_listed_deadline"],
                "next_deadline_reachable": payload["full_proposal"][
                    "next_listed_deadline_reachable"
                ],
                "project_pitch_submission_allowed": payload["project_pitch"][
                    "submission_allowed"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
