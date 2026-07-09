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
PROFILE_JSON = ROOT / "data" / "company_profile.json"

REVIEWER_GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
DOCKET_JSON = OUT_OPS / "human_action_docket_latest.json"
MANIFEST_JSON = OUT_OPS / "data_room_manifest_latest.json"
AUTONOMY_JSON = OUT_OPS / "autonomous_quant_governance_packet_latest.json"
IP_JSON = OUT_OPS / "ip_counsel_diligence_packet_latest.json"

OUT_JSON = OUT_OPS / "federal_submission_protocol_packet_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "federal_submission_protocol_packet.json"
OUT_MD = SPRINT_DIR / "FEDERAL_SUBMISSION_PROTOCOL_PACKET_2026-07-09.md"

OFFICIAL_SOURCES = [
    {
        "label": "SAM.gov entity registration",
        "url": "https://sam.gov/entity-registration",
        "protocol_fact": "SAM.gov assigns the Unique Entity ID during entity registration and says registrations must be renewed every 365 days to stay active.",
        "lumen_gate": "Robert verifies active registration, UEI/CAGE status, renewal date, entity roles, assertions, and representations directly in SAM.gov.",
    },
    {
        "label": "SAM.gov entity registration checklist",
        "url": "https://sam.gov/sites/default/files/2024-11/entity-checklist.pdf",
        "protocol_fact": "The checklist says to allow at least ten business days after submitting a SAM registration for it to become active.",
        "lumen_gate": "Do not treat a local profile field as award eligibility; portal status must be checked before final submission.",
    },
    {
        "label": "Grants.gov applicant registration",
        "url": "https://www.grants.gov/applicants/applicant-registration",
        "protocol_fact": "Grants.gov says an organization profile uses the SAM.gov UEI and the EBiz POC assigns roles such as AOR and Workspace Manager.",
        "lumen_gate": "Robert verifies profile, role, workspace, and application package state before any Grants.gov action.",
    },
    {
        "label": "Grants.gov EBiz POC role authorization",
        "url": "https://www.grants.gov/applicants/applicant-registration/ebiz-poc-authorizes-profile-roles",
        "protocol_fact": "Grants.gov says the EBiz POC must authorize roles before a user can complete or submit application packages on behalf of the organization.",
        "lumen_gate": "AOR authority and signing responsibility remain human verified before final submit.",
    },
    {
        "label": "Grants.gov Workspace roles",
        "url": "https://www.grants.gov/applicants/workspace-overview/workspace-roles",
        "protocol_fact": "Grants.gov says Standard AOR can submit the final application and Workspace Manager is the minimum core role to create and start a workspace.",
        "lumen_gate": "Workspace participation and AOR privileges must be checked opportunity by opportunity.",
    },
    {
        "label": "SBIR/STTR eligibility tutorial",
        "url": "https://www.sbir.gov/tutorials/program-basics/tutorial-2",
        "protocol_fact": "SBIR.gov states the small business must be primarily U.S. owned, generally at least 51% by U.S. citizens or permanent residents.",
        "lumen_gate": "Ownership, affiliate, PI employment, for-profit status, and award-time eligibility stay human verified.",
    },
    {
        "label": "SBIR/STTR eligibility FAQ",
        "url": "https://www.sbir.gov/faq/all",
        "protocol_fact": "SBIR.gov says the awardee must qualify as a Small Business Concern under SBA SBIR/STTR rules.",
        "lumen_gate": "Local small-business posture is evidence for review, not final eligibility certification.",
    },
    {
        "label": "Defense SBIR/STTR funding opportunities",
        "url": "https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/",
        "protocol_fact": "Defense SBIR/STTR says all DoW SBIR and STTR proposals must be submitted electronically through DSIP as described in the BAA or CSO.",
        "lumen_gate": "DSIP organization linkage, Firm PIN, topic forms, cost package, certifications, and submit button remain human controlled.",
    },
    {
        "label": "DARPA SBIR/STTR participation guide",
        "url": "https://www.darpa.mil/work-with-us/communities/small-business/sbir-sttr-participate",
        "protocol_fact": "DARPA says SBIR/STTR proposals are prepared and submitted through DSIP and are not considered submitted until Submit Proposal is clicked.",
        "lumen_gate": "DICE and other DARPA-package final submit stays blocked until Robert verifies the complete package and portal status.",
    },
    {
        "label": "DoW CIO CMMC program",
        "url": "https://dodcio.defense.gov/CMMC/",
        "protocol_fact": "DoW CIO says CMMC Phase 1 implementation runs November 10, 2025 through November 9, 2026 and focuses primarily on Level 1 and Level 2 self-assessments.",
        "lumen_gate": "No CMMC, SPRS, FCI, CUI, or enclave representation is made unless official evidence supports the exact claim.",
    },
    {
        "label": "DoW CIO About CMMC",
        "url": "https://dodcio.defense.gov/cmmc/About/",
        "protocol_fact": "DoW CIO says CMMC addresses safeguarding requirements for FCI and CUI and requires specified levels as a condition of contract award when applicable.",
        "lumen_gate": "Any FCI/CUI work requires a scoped environment, solicitation-specific requirements, and human-approved cybersecurity representation.",
    },
]

PROTOCOL_ROWS = [
    {
        "gate": "SAM/UEI/CAGE",
        "local_signal": "company_profile.sam_gov_status",
        "required_human_check": "Confirm active SAM.gov status, UEI, CAGE if assigned, renewal date, entity administrator, entity POCs, and current representations.",
        "blocked_without_check": "Do not submit federal contract or assistance material as eligible from local profile alone.",
    },
    {
        "gate": "Grants.gov AOR/Workspace",
        "local_signal": "submission_readiness.grants_gov_account_verified and aor_authority_verified",
        "required_human_check": "Confirm Grants.gov account, organization profile, EBiz POC authorization, AOR role, workspace access, and package status.",
        "blocked_without_check": "Do not click final submission, certification, or signature-equivalent steps.",
    },
    {
        "gate": "Research.gov / NSF",
        "local_signal": "submission_readiness.research_gov_account_verified and nsf_project_pitch_submitted",
        "required_human_check": "Confirm NSF Project Pitch pending status, invitation status, Research.gov access, PI eligibility, and one-pending-pitch rule.",
        "blocked_without_check": "Do not represent an NSF invitation or full-proposal eligibility unless NSF issued it.",
    },
    {
        "gate": "DSIP / Defense SBIR-STTR",
        "local_signal": "submission_readiness.dsip_account_verified and dod_compliance_verified",
        "required_human_check": "Confirm DSIP account, firm linkage, Firm PIN, topic forms, cost volume, reps, certifications, and final upload preview.",
        "blocked_without_check": "Do not submit, certify, or claim DoW integration or procurement readiness.",
    },
    {
        "gate": "Cyber / FCI / CUI",
        "local_signal": "proposal material currently treated as Unclassified and non-CUI unless official source marks otherwise",
        "required_human_check": "Confirm whether the solicitation involves FCI, CUI, export controls, SPRS, CMMC level, enclave scope, or flow-down obligations.",
        "blocked_without_check": "Do not process protected federal information in general-purpose public tooling or ordinary sync folders.",
    },
    {
        "gate": "IP / Disclosure",
        "local_signal": "ip_counsel_diligence_packet",
        "required_human_check": "Confirm official patent status, support, new-matter risk, disclosure limits, and counsel-approved language.",
        "blocked_without_check": "Do not expand patent-rights or exclusivity language in agency or investor materials.",
    },
    {
        "gate": "Runtime / Autonomy",
        "local_signal": "autonomous_quant_governance_packet",
        "required_human_check": "Confirm paper/runtime state, external-action authority, and no capital-impacting step before any operational escalation.",
        "blocked_without_check": "Do not let autonomous systems submit, sign, certify, transact, or move capital.",
    },
]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_status(path: Path) -> dict[str, Any]:
    return {
        "path": rel(path),
        "present": path.exists(),
        "bytes": path.stat().st_size if path.exists() else 0,
        "sha256": sha256_file(path) if path.exists() else "",
    }


def submission_readiness(profile: dict[str, Any]) -> dict[str, Any]:
    company = profile.get("company", {}) if isinstance(profile.get("company"), dict) else {}
    readiness = profile.get("submission_readiness", {}) if isinstance(profile.get("submission_readiness"), dict) else {}
    keys = [
        "grants_gov_account_verified",
        "research_gov_account_verified",
        "nsf_project_pitch_submitted",
        "aor_authority_verified",
        "dsip_account_verified",
        "dod_compliance_verified",
    ]
    blocked = [key for key in keys if not bool(readiness.get(key))]
    return {
        "sam_gov_status": str(company.get("sam_gov_status") or ""),
        "uei_present_locally": bool(company.get("duns_or_uei")),
        "cage_present_locally": bool(company.get("cage_code")),
        "blocked_readiness_flags": blocked,
        "blocked_readiness_count": len(blocked),
        "ready_flag_count": len(keys) - len(blocked),
        "profile_source": rel(PROFILE_JSON),
    }


def build_payload() -> dict[str, Any]:
    gate = read_json(REVIEWER_GATE_JSON)
    authority = read_json(AUTHORITY_JSON)
    docket = read_json(DOCKET_JSON)
    manifest = read_json(MANIFEST_JSON)
    autonomy = read_json(AUTONOMY_JSON)
    ip = read_json(IP_JSON)
    profile = read_json(PROFILE_JSON)

    evidence_paths = [
        SPRINT_DIR / "AGENCY_GOV_PROTOCOL_READINESS_CONTROL_ROOM_2026-07-09.md",
        SPRINT_DIR / "SUBMISSION_AUTHORITY_MATRIX_2026-07-09.md",
        SPRINT_DIR / "HUMAN_ACTION_DOCKET_2026-07-09.md",
        SPRINT_DIR / "IP_COUNSEL_DILIGENCE_PACKET_2026-07-09.md",
        SPRINT_DIR / "AUTONOMOUS_QUANT_GOVERNANCE_PACKET_2026-07-09.md",
        SPRINT_DIR / "DATA_ROOM_MANIFEST_2026-07-09.md",
        SPRINT_DIR / "FUNDING_SPRINT_REVIEWER_GATE_2026-07-09.md",
        PROFILE_JSON,
    ]
    evidence_status = [artifact_status(path) for path in evidence_paths]
    readiness = submission_readiness(profile)
    gate_summary = gate.get("summary", {}) if isinstance(gate.get("summary"), dict) else {}
    authority_summary = authority.get("summary", {}) if isinstance(authority.get("summary"), dict) else {}
    docket_summary = docket.get("summary", {}) if isinstance(docket.get("summary"), dict) else {}
    manifest_summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}
    autonomy_status = str(autonomy.get("status") or "")
    ip_status = str(ip.get("status") or "")

    gate_clear = bool(gate.get("reviewer_gate_clear")) and int(gate_summary.get("unsafe_secret_count") or 0) == 0 and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    all_final_actions_blocked = bool(authority_summary.get("all_final_actions_blocked_without_human"))
    evidence_present = all(row["present"] for row in evidence_status)
    human_protocol_required = readiness["blocked_readiness_count"] > 0

    payload = {
        "generated_utc": now_utc(),
        "schema": "federal_submission_protocol_packet_v1",
        "status": "FEDERAL_SUBMISSION_PROTOCOL_READY_HUMAN_PORTAL_REQUIRED"
        if gate_clear and all_final_actions_blocked and evidence_present
        else "FEDERAL_SUBMISSION_PROTOCOL_BLOCKED",
        "official_sources": OFFICIAL_SOURCES,
        "protocol_rows": PROTOCOL_ROWS,
        "submission_readiness": readiness,
        "summary": {
            "official_source_count": len(OFFICIAL_SOURCES),
            "protocol_gate_count": len(PROTOCOL_ROWS),
            "blocked_readiness_count": readiness["blocked_readiness_count"],
            "ready_flag_count": readiness["ready_flag_count"],
            "reviewer_gate_clear": gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "all_final_actions_blocked_without_human": all_final_actions_blocked,
            "human_protocol_required": human_protocol_required,
            "docket_lane_count": int(docket_summary.get("lane_count") or 0),
            "urgent_lane_count": int(docket_summary.get("immediate_or_urgent_count") or docket_summary.get("urgent_lane_count") or 0),
            "data_room_markdown_count": int(manifest_summary.get("manifested_markdown_count") or 0),
            "autonomous_governance_ready": autonomy_status.endswith("HUMAN_RUNTIME_REQUIRED"),
            "ip_counsel_ready": ip_status.endswith("HUMAN_COUNSEL_REQUIRED"),
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "certification_allowed_without_human": False,
            "portal_submit_allowed_without_human": False,
            "cui_processing_claimed": False,
            "cmmc_status_claimed": False,
            "award_eligibility_claimed": False,
        },
        "human_gate": {
            "sam_update_allowed_without_human": False,
            "grants_gov_submit_allowed_without_human": False,
            "dsip_submit_allowed_without_human": False,
            "research_gov_submit_allowed_without_human": False,
            "cybersecurity_representation_allowed_without_human": False,
            "pricing_or_cost_submission_allowed_without_human": False,
            "rule": "Federal submissions remain preparation-only until Robert verifies official portal status, authority, package contents, cybersecurity implications, cost, and final submission intent.",
        },
        "evidence_status": evidence_status,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["federal_submission_protocol_packet_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    readiness = payload["submission_readiness"]
    lines: list[str] = [
        "# Federal Submission Protocol Packet - 2026-07-09",
        "",
        "Purpose: make LumenCore agency, grant, SBIR, RFI, and contracting readiness easy to inspect without overstating portal authority or award eligibility.",
        "",
        "This packet is a protocol-control artifact. It does not authorize external sends, final submissions, signatures, certifications, pricing, cybersecurity representations, or portal actions.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Official sources: `{summary['official_source_count']}`",
        f"- Protocol gates: `{summary['protocol_gate_count']}`",
        f"- Blocked readiness flags: `{summary['blocked_readiness_count']}`",
        f"- Ready flags: `{summary['ready_flag_count']}`",
        f"- Reviewer gate clear: `{str(summary['reviewer_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- All final actions blocked without human: `{str(summary['all_final_actions_blocked_without_human']).lower()}`",
        f"- Human protocol required: `{str(summary['human_protocol_required']).lower()}`",
        f"- Data-room Markdown artifacts: `{summary['data_room_markdown_count']}`",
        f"- Autonomous governance ready: `{str(summary['autonomous_governance_ready']).lower()}`",
        f"- IP counsel packet ready: `{str(summary['ip_counsel_ready']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- Portal submit without human: `{str(summary['portal_submit_allowed_without_human']).lower()}`",
        f"- Cybersecurity representation without human: `false`",
        f"- CUI processing claimed: `{str(summary['cui_processing_claimed']).lower()}`",
        f"- CMMC status claimed: `{str(summary['cmmc_status_claimed']).lower()}`",
        f"- Award eligibility claimed: `{str(summary['award_eligibility_claimed']).lower()}`",
        f"- Packet SHA-256: `{payload['federal_submission_protocol_packet_sha256']}`",
        "",
        "## Local Readiness Snapshot",
        "",
        f"- Local SAM.gov status: `{readiness['sam_gov_status']}`",
        f"- UEI present locally: `{str(readiness['uei_present_locally']).lower()}`",
        f"- CAGE present locally: `{str(readiness['cage_present_locally']).lower()}`",
        f"- Blocked readiness flags: `{', '.join(readiness['blocked_readiness_flags'])}`",
        f"- Profile source: `{readiness['profile_source']}`",
        "",
        "## Official Sources",
        "",
    ]
    for source in payload["official_sources"]:
        lines.extend(
            [
                f"### {source['label']}",
                "",
                f"- URL: {source['url']}",
                f"- Protocol fact: {source['protocol_fact']}",
                f"- LumenCore gate: {source['lumen_gate']}",
                "",
            ]
        )

    lines.extend(["## Protocol Gates", ""])
    for row in payload["protocol_rows"]:
        lines.extend(
            [
                f"### {row['gate']}",
                "",
                f"- Local signal: {row['local_signal']}",
                f"- Required human check: {row['required_human_check']}",
                f"- Blocked without check: {row['blocked_without_check']}",
                "",
            ]
        )

    lines.extend(["## Human Gate", ""])
    for key, value in payload["human_gate"].items():
        lines.append(f"- {key}: `{value}`")

    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(json.dumps({"status": payload["status"], "outputs": payload["outputs"]}, indent=2))
    return 0 if payload["status"].endswith("HUMAN_PORTAL_REQUIRED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
