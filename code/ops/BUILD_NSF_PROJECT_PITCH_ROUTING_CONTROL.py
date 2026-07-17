from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT = (
    ROOT
    / "grant_submissions"
    / "NSF_Project_Pitch"
    / "NSF_PROJECT_PITCH_ROUTING_MANIFEST_2026-07-16.json"
)

AS_OF_DATE = "2026-07-17"
FULL_PROPOSAL_DEADLINES = (
    "2026-07-27",
    "2026-11-04",
    "2027-03-04",
    "2027-07-07",
)


def build_manifest() -> dict[str, Any]:
    return {
        "schema": "lumencore.nsf_project_pitch_routing.v1",
        "as_of_date": AS_OF_DATE,
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
            "one_active_pitch_at_a_time": True,
            "company_pitch_limit_per_12_months": 2,
            "invitation_valid_for_next_full_proposal_deadlines": 2,
            "final_submit_allowed_without_human": False,
            "portal_url": "https://seedfund.nsf.gov/project-pitch/",
        },
        "full_proposal": {
            "current_official_schedule_checked_on": AS_OF_DATE,
            "listed_deadlines": list(FULL_PROPOSAL_DEADLINES),
            "deadline_time": "17:00",
            "deadline_timezone_semantics": "SUBMITTING_ORGANIZATION_LOCAL_TIME",
            "nearest_listed_deadline": FULL_PROPOSAL_DEADLINES[0],
            "july_27_2026_currently_listed": True,
            "july_27_2026_reachable": False,
            "july_27_2026_access_state": (
                "BLOCKED_NO_VERIFIED_PROJECT_PITCH_INVITATION"
            ),
            "invitation_required": True,
            "invitation_verified": False,
            "next_planning_target": "2026-11-04",
            "next_planning_target_semantics": (
                "EARLIEST_REALISTIC_TARGET_NOT_AUTHORIZATION_OR_GUARANTEE"
            ),
            "submission_allowed": False,
        },
        "gmail_evidence": {
            "search_as_of_date": AS_OF_DATE,
            "inbound_invitation_found": False,
            "search_scope": (
                "Official NSF and Seed Fund Project Pitch invitation terms were "
                "searched in the connected mailbox."
            ),
            "evidence_boundary": (
                "Mailbox search is not portal state and does not prove that an "
                "invitation cannot exist elsewhere."
            ),
        },
        "portal_state": {
            "pending_project_pitch_status_verified": False,
            "open_invitation_status_verified": False,
            "full_proposal_under_review_verified": False,
        },
        "field_limits": {
            "Technology Innovation": 3500,
            "Technical Objectives and Challenges": 3500,
            "Market Opportunity": 1750,
            "Company and Team": 1750,
        },
        "official_sources": {
            "project_pitch_overview": "https://seedfund.nsf.gov/project-pitch/",
            "project_pitch_details": (
                "https://seedfund.nsf.gov/apply/project-pitch/"
            ),
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
        },
        "claim_boundary": [
            "No NSF invitation is claimed.",
            "No full-proposal authorization is claimed.",
            (
                "A listed full-proposal deadline is not represented as reachable "
                "without a verified Project Pitch invitation."
            ),
            (
                "No customer commitment, independent validation, award, or realized "
                "economic impact is claimed."
            ),
            "Portal state and legal company facts require human confirmation.",
        ],
    }


def validate_manifest(payload: dict[str, Any]) -> None:
    full = payload["full_proposal"]
    if full["listed_deadlines"] != list(FULL_PROPOSAL_DEADLINES):
        raise ValueError("NSF full-proposal deadline snapshot is inconsistent")
    if full["nearest_listed_deadline"] != FULL_PROPOSAL_DEADLINES[0]:
        raise ValueError("NSF nearest listed deadline is inconsistent")
    if full["july_27_2026_currently_listed"] is not True:
        raise ValueError("NSF July 27 listing correction is missing")
    if full["july_27_2026_reachable"] is not False:
        raise ValueError("NSF invitation gate is not enforced")
    if full["submission_allowed"] is not False:
        raise ValueError("NSF full proposal is incorrectly submit-authorized")


def main() -> int:
    payload = build_manifest()
    validate_manifest(payload)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "status": "NSF_PROJECT_PITCH_ROUTING_CONTROL_WRITTEN",
                "output": OUT.relative_to(ROOT).as_posix(),
                "nearest_listed_full_proposal_deadline": payload["full_proposal"][
                    "nearest_listed_deadline"
                ],
                "nearest_deadline_reachable": payload["full_proposal"][
                    "july_27_2026_reachable"
                ],
                "next_planning_target": payload["full_proposal"][
                    "next_planning_target"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
