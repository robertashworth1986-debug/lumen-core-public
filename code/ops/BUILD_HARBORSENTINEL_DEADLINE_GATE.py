from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVIDENCE = ROOT / "config" / "harborsentinel_deadline_evidence_v1.json"
JSON_OUT = ROOT / "dashboard" / "data" / "harborsentinel_deadline_gate.json"
MD_OUT = ROOT / "docs" / "HARBORSENTINEL_DEADLINE_READINESS_GATE_2026-07-19.md"

UNKNOWN = "UNKNOWN_NOT_VERIFIED"
VERIFIED = "VERIFIED"
CURRENT_SOURCE = "VERIFIED_CURRENT"
EXPECTED_SOURCE_ROLES = {
    "release_preface",
    "navy_component_instructions_and_topics",
    "dsip_current_solicitation_page",
    "navy_current_baa_index",
}
EXPECTED_TOPIC = "DON26BZ03-NV063"
EXPECTED_VOLUMES = list(range(1, 8))
EXPECTED_DEADLINE_LOCAL = "2026-07-22T12:00:00-04:00"
EXPECTED_DEADLINE_UTC = "2026-07-22T16:00:00Z"
PRIVATE_PATH = re.compile(r"(?i)(?:^|[\s\"'])\b[a-z]:[\\/]")
PRIVATE_EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("HarborSentinel evidence must be a JSON object.")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def is_sha256(value: Any) -> bool:
    return bool(re.fullmatch(r"[0-9A-F]{64}", str(value or "")))


def is_official_url(value: Any) -> bool:
    parsed = urlparse(str(value or ""))
    return parsed.scheme == "https" and parsed.hostname in {
        "www.dodsbirsttr.mil",
        "www.navysbir.com",
    }


def deadline_is_consistent(notice: dict[str, Any]) -> bool:
    try:
        local_deadline = datetime.fromisoformat(str(notice["deadline_local_iso"]))
        utc_deadline = datetime.fromisoformat(
            str(notice["deadline_utc_iso"]).replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError):
        return False
    return (
        local_deadline.tzinfo is not None
        and utc_deadline.tzinfo is not None
        and local_deadline.astimezone(timezone.utc)
        == utc_deadline.astimezone(timezone.utc)
        and notice.get("deadline_local_iso") == EXPECTED_DEADLINE_LOCAL
        and notice.get("deadline_utc_iso") == EXPECTED_DEADLINE_UTC
        and str(notice.get("timezone_source")) == "ET"
        and str(notice.get("timezone_iana")) == "America/New_York"
    )


def source_checks(evidence: dict[str, Any]) -> dict[str, bool]:
    sources = evidence.get("official_sources", [])
    if not isinstance(sources, list):
        sources = []
    by_role = {
        str(source.get("role")): source
        for source in sources
        if isinstance(source, dict) and source.get("role")
    }
    role_checks = {
        role: (
            role in by_role
            and by_role[role].get("verification") == CURRENT_SOURCE
            and is_official_url(by_role[role].get("url"))
        )
        for role in EXPECTED_SOURCE_ROLES
    }
    for role in ("release_preface", "navy_component_instructions_and_topics"):
        source = by_role.get(role, {})
        role_checks[role] = bool(
            role_checks[role]
            and source.get("http_status") == 200
            and int(source.get("bytes", 0)) > 0
            and is_sha256(source.get("sha256"))
            and source.get("local_authoritative_copy_hash_match") is True
        )
    return dict(sorted(role_checks.items()))


def applicant_checks(evidence: dict[str, Any]) -> dict[str, bool]:
    proposal = evidence.get("proposal_state", {})
    eligibility = evidence.get("eligibility", [])
    all_eligibility_verified = bool(eligibility) and all(
        isinstance(item, dict) and item.get("applicant_status") == VERIFIED
        for item in eligibility
    )
    return {
        "all_required_volumes_complete": proposal.get("all_required_volumes_complete")
        == VERIFIED,
        "corporate_official_certification_verified": proposal.get(
            "corporate_official_certification"
        )
        == VERIFIED,
        "dsip_proposal_record_verified": proposal.get("dsip_proposal_record")
        == VERIFIED,
        "eligibility_verified": proposal.get("eligibility_complete") == VERIFIED
        and all_eligibility_verified,
        "portal_status_verified": proposal.get("portal_status") == VERIFIED,
        "required_attachments_complete": proposal.get("required_attachments_complete")
        == VERIFIED,
        "submission_receipt_verified": proposal.get("submission_receipt") == VERIFIED,
        "submission_status_verified": proposal.get("submission_status") == VERIFIED,
    }


def display_status(value: Any) -> str:
    if value == UNKNOWN:
        return "UNKNOWN / NOT VERIFIED"
    return str(value or "UNKNOWN / NOT VERIFIED").replace("_", " ")


def assert_public_safe(payload: dict[str, Any]) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    if PRIVATE_PATH.search(serialized):
        raise ValueError("Public gate contains an absolute local path.")
    if PRIVATE_EMAIL.search(serialized):
        raise ValueError("Public gate contains an email address.")
    lowered = serialized.lower()
    for prohibited in (
        "private patent",
        "patent application",
        "proprietary proposal text",
    ):
        if prohibited in lowered:
            raise ValueError(f"Public gate contains prohibited content: {prohibited}")


def build_gate(evidence: dict[str, Any]) -> dict[str, Any]:
    if evidence.get("schema") != "harborsentinel_deadline_evidence_v1":
        raise ValueError("Unexpected HarborSentinel evidence schema.")
    if evidence.get("public_safe") is not True:
        raise ValueError("HarborSentinel evidence is not marked public-safe.")

    notice = evidence.get("notice", {})
    requirements = evidence.get("requirements", {})
    volumes = requirements.get("required_volumes", [])
    volume_numbers = [item.get("volume") for item in volumes if isinstance(item, dict)]
    sources = source_checks(evidence)
    official_facts = {
        "authoritative_sources_current": bool(sources) and all(sources.values()),
        "deadline_exact_and_timezone_consistent": deadline_is_consistent(notice),
        "official_notice_exact": (
            notice.get("notice_id") == "DOD_SBIR_2026_P1_CBZ"
            and notice.get("release") == 3
            and notice.get("amendment") == 2
            and notice.get("amendment_date") == "2026-07-15"
        ),
        "official_topic_exact": (
            notice.get("topic_id") == EXPECTED_TOPIC
            and notice.get("topic_title")
            == "Anomalous Behavior Detection and Alerting for Congested Maritime Environments"
        ),
        "official_portal_exact": (
            notice.get("portal_name") == "Defense SBIR/STTR Innovation Portal (DSIP)"
            and notice.get("portal_url") == "https://www.dodsbirsttr.mil/submissions/"
        ),
        "seven_volume_structure_verified": (
            requirements.get("all_seven_volumes_required") is True
            and volume_numbers == EXPECTED_VOLUMES
        ),
    }
    deadline_verified = all(
        official_facts[name]
        for name in (
            "authoritative_sources_current",
            "deadline_exact_and_timezone_consistent",
            "official_notice_exact",
            "official_topic_exact",
        )
    )
    requirements_verified = all(official_facts.values())
    action_checks = applicant_checks(evidence)
    current_action_ready = all(action_checks.values())

    blockers = [
        f"{name}: UNKNOWN / NOT VERIFIED"
        for name, passed in action_checks.items()
        if not passed
    ]
    if not requirements_verified:
        blockers.insert(
            0,
            "authoritative deadline or requirement source set: UNKNOWN / NOT VERIFIED",
        )

    proposal = evidence.get("proposal_state", {})
    local_candidate_exists = (
        proposal.get("local_candidate", {}).get("status") == "EXISTS_LOCAL_DRAFT"
    )
    if not requirements_verified:
        posture = "BLOCKED_SOURCE_UNKNOWN_NOT_VERIFIED"
    elif not current_action_ready:
        posture = "BLOCKED_UNKNOWN_NOT_VERIFIED"
    else:
        posture = "HUMAN_REVIEW_REQUIRED"

    gate = {
        "schema": "harborsentinel_deadline_gate_v1",
        "as_of_utc": evidence.get("as_of_utc"),
        "public_safe": True,
        "posture": posture,
        "deadline_conclusion": "VERIFIED_REAL_DEADLINE"
        if deadline_verified
        else UNKNOWN,
        "requirements_conclusion": "VERIFIED_REQUIREMENTS"
        if requirements_verified
        else UNKNOWN,
        "proposal_conclusion": (
            "LOCAL_DRAFT_EXISTS_DSIP_UNKNOWN_NOT_VERIFIED"
            if local_candidate_exists
            and not action_checks["dsip_proposal_record_verified"]
            else UNKNOWN
        ),
        "notice": notice,
        "official_sources": evidence.get("official_sources", []),
        "source_checks": sources,
        "official_fact_checks": official_facts,
        "requirements": requirements,
        "eligibility": evidence.get("eligibility", []),
        "proposal_state": proposal,
        "action_readiness_checks": action_checks,
        "blockers": blockers,
        "authority_boundary": {
            "upload_authorized": False,
            "certification_authorized": False,
            "submission_authorized": False,
            "signature_authorized": False,
            "external_contact_authorized": False,
            "claim": (
                "This public-safe gate verifies solicitation facts only. It does not certify the applicant, "
                "prove a DSIP proposal exists, establish portal status, or authorize any external action."
            ),
        },
        "safest_next_action": (
            "An authorized human should sign in to DSIP and capture a redacted, read-only receipt showing "
            "whether a DON26BZ03-NV063 proposal record exists and its current portal state. During that "
            "capture, do not certify, upload, submit, accept new terms on another person's behalf, or expose "
            "private identifiers. Then verify each eligibility and conditional-attachment blocker against "
            "authoritative records."
        ),
    }
    assert_public_safe(gate)
    return gate


def render_markdown(gate: dict[str, Any]) -> str:
    notice = gate["notice"]
    lines = [
        "# HarborSentinel Deadline Readiness Gate",
        "",
        f"Evidence checked UTC: `{gate['as_of_utc']}`",
        "",
        f"Posture: `{gate['posture']}`",
        "",
        f"Deadline conclusion: `{display_status(gate['deadline_conclusion'])}`",
        "",
        f"Requirements conclusion: `{display_status(gate['requirements_conclusion'])}`",
        "",
        f"Proposal conclusion: `{display_status(gate['proposal_conclusion'])}`",
        "",
        "## Deadline Conclusion",
        "",
        f"- Notice: {notice['solicitation']}, Release {notice['release']}, Amendment {notice['amendment']} ({notice['amendment_date']}).",
        f"- Topic: `{notice['topic_id']}` - {notice['topic_title']}.",
        f"- Close: **{notice['deadline_source_text']}** (`{notice['deadline_local_iso']}`; `{notice['deadline_utc_iso']}`).",
        f"- Portal: [{notice['portal_name']}]({notice['portal_url']}).",
        "- Conclusion: the July 22 deadline is real and current. The verified deadline does not establish applicant or proposal readiness.",
        "",
        "## Authoritative Sources",
        "",
    ]
    for source in gate["official_sources"]:
        digest = f"; SHA-256 `{source['sha256']}`" if source.get("sha256") else ""
        lines.append(
            f"- `{source['role']}`: [{source['url']}]({source['url']}) - `{source['verification']}`{digest}."
        )

    lines.extend(
        [
            "",
            "## Required Proposal Structure",
            "",
            "| Volume | Required item | Delivery | Key controls |",
            "|---:|---|---|---|",
        ]
    )
    for volume in gate["requirements"]["required_volumes"]:
        lines.append(
            f"| {volume['volume']} | {volume['name']} | {volume['delivery']} | {volume['controls']} |"
        )

    lines.extend(
        [
            "",
            "All seven volumes, applicable firm-level forms, and electronic Corporate Official certification are required. `In Progress` and `Ready to Certify` are not submitted states.",
            "",
            "## Eligibility Gate",
            "",
            "| Requirement | Applicant evidence status |",
            "|---|---|",
        ]
    )
    for item in gate["eligibility"]:
        lines.append(
            f"| {item['requirement']} | **{display_status(item['applicant_status'])}** |"
        )

    proposal = gate["proposal_state"]
    lines.extend(
        [
            "",
            "## Proposal Existence And Status",
            "",
            f"- Local draft candidate: `{display_status(proposal['local_candidate']['status'])}`. This does not prove a DSIP record.",
            f"- DSIP proposal record: **{display_status(proposal['dsip_proposal_record'])}**.",
            f"- Proposal number: **{display_status(proposal['proposal_number'])}**.",
            f"- Portal status: **{display_status(proposal['portal_status'])}**.",
            f"- Required volumes complete: **{display_status(proposal['all_required_volumes_complete'])}**.",
            f"- Required attachments complete: **{display_status(proposal['required_attachments_complete'])}**.",
            f"- Corporate Official certification: **{display_status(proposal['corporate_official_certification'])}**.",
            f"- Submission status: **{display_status(proposal['submission_status'])}**.",
            f"- Submission receipt: **{display_status(proposal['submission_receipt'])}**.",
            "",
            "## Blocker Register",
            "",
        ]
    )
    lines.extend(f"- {blocker}" for blocker in gate["blockers"])
    lines.extend(
        [
            "",
            "## Authority Boundary",
            "",
            gate["authority_boundary"]["claim"],
            "",
            "No upload, certification, signature, submission, external contact, or eligibility claim is authorized by this artifact.",
            "",
            "## Safest Next Action",
            "",
            gate["safest_next_action"],
        ]
    )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the public-safe HarborSentinel deadline gate."
    )
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    parser.add_argument("--no-write", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate = build_gate(read_json(args.evidence))
    if not args.no_write:
        write_json(JSON_OUT, gate)
        write_text(MD_OUT, render_markdown(gate))
    print(
        json.dumps(
            {
                "posture": gate["posture"],
                "deadline_conclusion": gate["deadline_conclusion"],
                "proposal_conclusion": gate["proposal_conclusion"],
                "blockers": len(gate["blockers"]),
                "submission_authorized": gate["authority_boundary"][
                    "submission_authorized"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
