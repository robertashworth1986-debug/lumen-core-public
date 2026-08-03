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
SAM_CAPTURE_JSON = OUT_OPS / "sam_gov_entity_status_capture_latest.json"
FEDERAL_JSON = OUT_OPS / "federal_submission_protocol_packet_latest.json"
AUTHORITY_JSON = OUT_OPS / "submission_authority_matrix_latest.json"
MANIFEST_JSON = OUT_OPS / "data_room_manifest_latest.json"
GATE_JSON = OUT_OPS / "funding_sprint_reviewer_gate_latest.json"
IP_JSON = OUT_OPS / "ip_counsel_diligence_packet_latest.json"
AUTONOMY_JSON = OUT_OPS / "autonomous_quant_governance_packet_latest.json"

OUT_JSON = OUT_OPS / "agency_account_activation_docket_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "agency_account_activation_docket.json"
OUT_MD = SPRINT_DIR / "AGENCY_ACCOUNT_ACTIVATION_DOCKET_2026-07-09.md"

SENSITIVE_MARKERS = [
    "zoom.us",
    "meeting id",
    "password",
    "one tap mobile",
    "private key",
    "refresh_token",
    "client_secret",
    "api_key",
    "sk-",
    "xox",
]

OFFICIAL_SOURCES = [
    {
        "label": "SAM.gov entity registration",
        "url": "https://sam.gov/entity-registration",
        "activation_use": "Entity registration, renewal, Entity Workspace review, and active-status verification.",
    },
    {
        "label": "Grants.gov applicant registration",
        "url": "https://www.grants.gov/applicants/applicant-registration",
        "activation_use": "Organization profile and applicant registration path.",
    },
    {
        "label": "Grants.gov Workspace roles",
        "url": "https://www.grants.gov/applicants/workspace-overview/workspace-roles",
        "activation_use": "Workspace Manager and AOR role checks before package submit.",
    },
    {
        "label": "NSF Project Pitch",
        "url": "https://seedfund.nsf.gov/project-pitch/",
        "activation_use": "Project Pitch and invitation-gated full proposal path.",
    },
    {
        "label": "Defense SBIR/STTR opportunities",
        "url": "https://www.defensesbirsttr.mil/SBIR-STTR/Opportunities/",
        "activation_use": "DSIP topic workspace, firm linkage, and Defense SBIR/STTR submission path.",
    },
    {
        "label": "DARPA SBIR/STTR participation guide",
        "url": "https://www.darpa.mil/work-with-us/communities/small-business/sbir-sttr-participate",
        "activation_use": "DARPA/DSIP preparation and final submit boundary.",
    },
    {
        "label": "DoD CIO CMMC",
        "url": "https://dodcio.defense.gov/CMMC/",
        "activation_use": "Cybersecurity representation boundary for FCI/CUI and CMMC/SPRS implications.",
    },
    {
        "label": "USPTO Patent Center",
        "url": "https://patentcenter.uspto.gov/",
        "activation_use": "Patent status, deadlines, and counsel-confirmed IP posture.",
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
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


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


def bool_field(value: Any) -> bool:
    return bool(value) if isinstance(value, bool) else False


def local_readiness(profile: dict[str, Any], sam_capture: dict[str, Any]) -> dict[str, Any]:
    company = profile.get("company", {}) if isinstance(profile.get("company"), dict) else {}
    readiness = profile.get("submission_readiness", {}) if isinstance(profile.get("submission_readiness"), dict) else {}
    blocked_keys = [
        key
        for key in [
            "grants_gov_account_verified",
            "research_gov_account_verified",
            "nsf_project_pitch_submitted",
            "aor_authority_verified",
            "dsip_account_verified",
            "dod_compliance_verified",
        ]
        if not bool_field(readiness.get(key))
    ]
    portal_status = str(sam_capture.get("registration_status") or "")
    return {
        "company_profile_status": str(company.get("sam_gov_status") or ""),
        "uei_present_locally": bool(company.get("duns_or_uei")),
        "cage_present_locally": bool(company.get("cage_code")),
        "sam_portal_capture_present": bool(sam_capture),
        "sam_portal_active_registration_observed": portal_status.lower() == "active registration",
        "sam_expiration_date_observed": str(sam_capture.get("expiration_date") or ""),
        "blocked_readiness_flags": blocked_keys,
        "blocked_readiness_count": len(blocked_keys),
        "ready_readiness_count": 6 - len(blocked_keys),
        "private_identifier_policy": "Public docket uses presence/status flags only; exact private identifiers and contact fields stay out of the markdown.",
    }


def activation_rows(readiness: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "id": "sam_entity_renewal",
            "portal": "SAM.gov Entity Workspace",
            "status": "READY_HUMAN_CERTIFICATION_REQUIRED"
            if readiness["sam_portal_active_registration_observed"]
            else "BLOCKED_PORTAL_STATUS_RECHECK_REQUIRED",
            "evidence_signal": "Signed-in SAM workspace status capture is available; renewal/update relationship certification remains human-only.",
            "next_human_actions": [
                "Review the active entity record in SAM.gov.",
                "Confirm relationship to entity and authority directly in the portal.",
                "Review all update/renewal sections before any certification or submit step.",
                "Save a private portal receipt after final human action.",
            ],
            "blocks": [
                "SAM-dependent contracts and grants if the registration lapses.",
                "Any claim that the renewal was submitted unless the portal confirms it.",
            ],
        },
        {
            "id": "grants_gov_profile_aor",
            "portal": "Grants.gov",
            "status": "BLOCKED_ACCOUNT_ROLE_VERIFICATION_REQUIRED",
            "evidence_signal": "Local readiness flags do not yet verify Grants.gov profile or AOR authority.",
            "next_human_actions": [
                "Sign in and verify organization profile linkage.",
                "Confirm Workspace Manager and AOR roles.",
                "Confirm EBiz POC authorization before any package submit.",
            ],
            "blocks": [
                "Final Grants.gov package submission.",
                "Any signature-equivalent certification in Grants.gov.",
            ],
        },
        {
            "id": "research_gov_nsf_pitch",
            "portal": "Research.gov / NSF Project Pitch",
            "status": "BLOCKED_ACCOUNT_OR_PITCH_GATE_REQUIRED",
            "evidence_signal": "Research.gov account and NSF Project Pitch submission are not verified locally.",
            "next_human_actions": [
                "Verify Research.gov access.",
                "Check whether an NSF Project Pitch is pending.",
                "Submit pitch only after final human review of the bounded language.",
            ],
            "blocks": [
                "NSF full proposal eligibility claims.",
                "Any claim that an NSF invitation has been issued.",
            ],
        },
        {
            "id": "dsip_firm_pin_topic_access",
            "portal": "DSIP / Defense SBIR-STTR",
            "status": "BLOCKED_ACCOUNT_LINKAGE_REQUIRED",
            "evidence_signal": "DSIP account, firm linkage, and topic workspace authority are not verified locally.",
            "next_human_actions": [
                "Verify DSIP user and firm linkage.",
                "Confirm firm-level access and topic workspace visibility.",
                "Keep Firm PIN, certifications, and final submit human-only.",
            ],
            "blocks": [
                "Defense SBIR/STTR final proposal submit.",
                "DARPA/DLA package certification or Firm PIN use.",
            ],
        },
        {
            "id": "dod_cyber_cmmc_scope",
            "portal": "DoD cyber / CMMC / SPRS scope",
            "status": "BLOCKED_CYBER_SCOPE_REQUIRED",
            "evidence_signal": "DoD compliance flag is not verified locally; FCI/CUI scope must be solicitation-specific.",
            "next_human_actions": [
                "Confirm whether the opportunity involves FCI or CUI.",
                "Confirm CMMC/SPRS level, enclave, and flow-down obligations.",
                "Do not process protected federal data in ordinary sync or public tools.",
            ],
            "blocks": [
                "Cybersecurity representations.",
                "Any CMMC, SPRS, FCI, CUI, or controlled-environment claim.",
            ],
        },
        {
            "id": "ip_patent_center_counsel",
            "portal": "USPTO Patent Center / counsel",
            "status": "BLOCKED_PATENT_CENTER_COUNSEL_REQUIRED",
            "evidence_signal": "Internal profile lists a nonprovisional application reference, but official status and deadlines require Patent Center/counsel verification.",
            "next_human_actions": [
                "Verify application status and response deadlines in Patent Center.",
                "Ask licensed counsel to approve disclosure boundaries.",
                "Separate filed claims from new-matter concepts in reviewer materials.",
            ],
            "blocks": [
                "Patent-rights expansion language.",
                "Freedom-to-operate or ownership assertions beyond verified records.",
            ],
        },
        {
            "id": "submission_signer_pricing_authority",
            "portal": "Human signature, pricing, and final authority",
            "status": "BLOCKED_FINAL_AUTHORITY_REQUIRED",
            "evidence_signal": "The authority matrix blocks all sends, submits, certifications, pricing, and term acceptance without human approval.",
            "next_human_actions": [
                "Approve final package contents.",
                "Approve pricing or cost basis.",
                "Approve certifications, representations, and signature-equivalent actions.",
            ],
            "blocks": [
                "All final submissions.",
                "All external sends and acceptance of legal, financial, or program terms.",
            ],
        },
        {
            "id": "secure_artifact_custody",
            "portal": "Proof vault / data-room custody",
            "status": "READY_HUMAN_SHARE_REQUIRED",
            "evidence_signal": "Data-room and reviewer gates are clear when all control artifacts are present and unsafe scans remain zero.",
            "next_human_actions": [
                "Share only the public-safe front-door files.",
                "Keep portal receipts and private identifiers in private custody.",
                "Run hash checks after each E-drive refresh.",
            ],
            "blocks": [
                "Unreviewed archive sharing.",
                "Credential, portal, meeting-access, or private-identifier leakage.",
            ],
        },
    ]

    finalized_rows = []
    for row in rows:
        row = row | {
            "human_required": True,
            "portal_action_allowed_without_human": False,
            "credential_entry_allowed_without_human": False,
            "certification_allowed_without_human": False,
            "final_submit_allowed_without_human": False,
            "external_share_allowed_without_human": False,
        }
        row["row_sha256"] = hashlib.sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()
        finalized_rows.append(row)
    return finalized_rows


def build_payload() -> dict[str, Any]:
    profile = read_json(PROFILE_JSON)
    sam_capture = read_json(SAM_CAPTURE_JSON)
    federal = read_json(FEDERAL_JSON)
    authority = read_json(AUTHORITY_JSON)
    manifest = read_json(MANIFEST_JSON)
    gate = read_json(GATE_JSON)
    ip = read_json(IP_JSON)
    autonomy = read_json(AUTONOMY_JSON)

    readiness = local_readiness(profile, sam_capture)
    rows = activation_rows(readiness)
    gate_summary = gate.get("summary", {}) if isinstance(gate.get("summary"), dict) else {}
    manifest_summary = manifest.get("summary", {}) if isinstance(manifest.get("summary"), dict) else {}

    submission_argument_gate_clear = bool(gate.get("reviewer_gate_clear"))
    reviewer_packaging_gate_clear = (
        bool(gate_summary.get("packaging_checks_clear"))
        and int(gate_summary.get("unsafe_secret_count") or 0) == 0
        and int(gate_summary.get("unsafe_claim_count") or 0) == 0
    )
    blocked_rows = [row for row in rows if str(row["status"]).startswith("BLOCKED")]
    ready_rows = [row for row in rows if str(row["status"]).startswith("READY")]
    all_human_gated = all(
        row["human_required"]
        and not row["portal_action_allowed_without_human"]
        and not row["credential_entry_allowed_without_human"]
        and not row["certification_allowed_without_human"]
        and not row["final_submit_allowed_without_human"]
        and not row["external_share_allowed_without_human"]
        for row in rows
    )

    evidence_paths = [
        PROFILE_JSON,
        SAM_CAPTURE_JSON,
        FEDERAL_JSON,
        AUTHORITY_JSON,
        MANIFEST_JSON,
        GATE_JSON,
        IP_JSON,
        AUTONOMY_JSON,
    ]
    payload = {
        "generated_utc": now_utc(),
        "schema": "agency_account_activation_docket_v1",
        "status": "AGENCY_ACCOUNT_ACTIVATION_READY_HUMAN_PORTAL_REQUIRED"
        if reviewer_packaging_gate_clear and all_human_gated
        else "AGENCY_ACCOUNT_ACTIVATION_BLOCKED",
        "summary": {
            "activation_item_count": len(rows),
            "ready_item_count": len(ready_rows),
            "blocked_item_count": len(blocked_rows),
            "human_required_item_count": len(rows),
            "blocked_readiness_count": readiness["blocked_readiness_count"],
            "ready_readiness_count": readiness["ready_readiness_count"],
            "sam_portal_active_registration_observed": readiness["sam_portal_active_registration_observed"],
            "sam_expiration_date_observed": readiness["sam_expiration_date_observed"],
            "reviewer_packaging_gate_clear": reviewer_packaging_gate_clear,
            "submission_argument_gate_clear": submission_argument_gate_clear,
            "unsafe_secret_count": int(gate_summary.get("unsafe_secret_count") or 0),
            "unsafe_claim_count": int(gate_summary.get("unsafe_claim_count") or 0),
            "data_room_markdown_count": int(manifest_summary.get("manifested_markdown_count") or 0),
            "data_room_control_artifact_count": int(manifest_summary.get("control_artifact_count") or 0),
            "external_send_allowed_without_human": False,
            "final_submission_allowed_without_human": False,
            "portal_action_allowed_without_human": False,
            "credential_entry_allowed_without_human": False,
            "certification_allowed_without_human": False,
            "calendar_or_meeting_invite_allowed_without_human": False,
            "live_trading_allowed": False,
        },
        "local_readiness": readiness,
        "activation_rows": rows,
        "official_sources": OFFICIAL_SOURCES,
        "source_statuses": {
            "federal_submission_protocol_packet": federal.get("status", ""),
            "submission_authority_matrix": authority.get("status", ""),
            "data_room_manifest": manifest.get("status", ""),
            "funding_sprint_reviewer_gate": gate.get("status", ""),
            "ip_counsel_diligence_packet": ip.get("status", ""),
            "autonomous_quant_governance_packet": autonomy.get("status", ""),
        },
        "evidence_status": [artifact_status(path) for path in evidence_paths],
        "human_stop_rule": "Prepare only. Human controls credentials, legal authority certifications, portal submit, uploads, shares, pricing, representations, and final acceptance.",
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
    }
    payload["activation_docket_sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    readiness = payload["local_readiness"]
    lines = [
        "# Agency Account Activation Docket - 2026-07-09",
        "",
        "Purpose: turn federal account readiness into a reviewer-safe activation board for SAM.gov, Grants.gov, Research.gov, DSIP, DoD cyber scope, IP counsel, signer authority, and proof-vault custody.",
        "",
        "This docket is preparation-only. It does not authorize credentials, certifications, final submissions, uploads, external shares, pricing, legal terms, trading, or capital movement.",
        "",
        "## Status",
        "",
        f"- Status: `{payload['status']}`",
        f"- Activation items: `{summary['activation_item_count']}`",
        f"- Ready items: `{summary['ready_item_count']}`",
        f"- Blocked items: `{summary['blocked_item_count']}`",
        f"- Human-required items: `{summary['human_required_item_count']}`",
        f"- Blocked readiness flags: `{summary['blocked_readiness_count']}`",
        f"- SAM active registration observed in private capture: `{str(summary['sam_portal_active_registration_observed']).lower()}`",
        f"- SAM expiration date observed: `{summary['sam_expiration_date_observed']}`",
        f"- Reviewer packaging gate clear: `{str(summary['reviewer_packaging_gate_clear']).lower()}`",
        f"- Submission argument gate clear: `{str(summary['submission_argument_gate_clear']).lower()}`",
        f"- Unsafe sensitive hits: `{summary['unsafe_secret_count']}`",
        f"- Unsafe claim hits: `{summary['unsafe_claim_count']}`",
        f"- Data-room Markdown artifacts: `{summary['data_room_markdown_count']}`",
        f"- Data-room control artifacts: `{summary['data_room_control_artifact_count']}`",
        f"- Portal action without human: `{str(summary['portal_action_allowed_without_human']).lower()}`",
        f"- Credential entry without human: `{str(summary['credential_entry_allowed_without_human']).lower()}`",
        f"- Certification without human: `{str(summary['certification_allowed_without_human']).lower()}`",
        f"- Final submission without human: `{str(summary['final_submission_allowed_without_human']).lower()}`",
        f"- External send without human: `{str(summary['external_send_allowed_without_human']).lower()}`",
        f"- Live trading allowed: `{str(summary['live_trading_allowed']).lower()}`",
        f"- Docket SHA-256: `{payload['activation_docket_sha256']}`",
        "",
        "## Local Readiness Signals",
        "",
        f"- Company profile SAM status: `{readiness['company_profile_status']}`",
        f"- UEI present locally: `{str(readiness['uei_present_locally']).lower()}`",
        f"- CAGE present locally: `{str(readiness['cage_present_locally']).lower()}`",
        f"- SAM portal capture present: `{str(readiness['sam_portal_capture_present']).lower()}`",
        f"- Ready readiness flags: `{readiness['ready_readiness_count']}`",
        f"- Blocked readiness flags: `{', '.join(readiness['blocked_readiness_flags'])}`",
        f"- Private identifier policy: {readiness['private_identifier_policy']}",
        "",
        "## Activation Rows",
        "",
    ]
    for row in payload["activation_rows"]:
        lines.extend(
            [
                f"### {row['id']}",
                "",
                f"- Portal: {row['portal']}",
                f"- Status: `{row['status']}`",
                f"- Evidence signal: {row['evidence_signal']}",
                f"- Human required: `{str(row['human_required']).lower()}`",
                f"- Portal action without human: `{str(row['portal_action_allowed_without_human']).lower()}`",
                f"- Credential entry without human: `{str(row['credential_entry_allowed_without_human']).lower()}`",
                f"- Certification without human: `{str(row['certification_allowed_without_human']).lower()}`",
                f"- Final submit without human: `{str(row['final_submit_allowed_without_human']).lower()}`",
                f"- External share without human: `{str(row['external_share_allowed_without_human']).lower()}`",
                f"- Row SHA-256: `{row['row_sha256']}`",
                "",
                "Next human actions:",
            ]
        )
        for action in row["next_human_actions"]:
            lines.append(f"- {action}")
        lines.extend(["", "Blocks:"])
        for block in row["blocks"]:
            lines.append(f"- {block}")
        lines.append("")

    lines.extend(["## Official Source Map", ""])
    for source in payload["official_sources"]:
        lines.extend(
            [
                f"### {source['label']}",
                "",
                f"- URL: {source['url']}",
                f"- Activation use: {source['activation_use']}",
                "",
            ]
        )

    lines.extend(["## Source Statuses", ""])
    for key, value in payload["source_statuses"].items():
        lines.append(f"- `{key}`: `{value}`")

    lines.extend(["", "## Evidence Sources", ""])
    for row in payload["evidence_status"]:
        lines.append(
            f"- `{row['path']}` | present=`{str(row['present']).lower()}` | bytes=`{row['bytes']}` | sha256=`{row['sha256']}`"
        )

    lines.extend(["", "## Human Stop Rule", "", payload["human_stop_rule"], ""])
    return "\n".join(lines)


def scan_sensitive_text(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({marker for marker in SENSITIVE_MARKERS if marker in lowered})


def private_profile_markers(profile: dict[str, Any]) -> list[str]:
    company = profile.get("company", {}) if isinstance(profile.get("company"), dict) else {}
    markers = []
    for key in ["duns_or_uei", "cage_code", "ein", "address_line1", "phone", "email"]:
        value = str(company.get(key) or "").strip()
        if value:
            markers.append(value)
    return markers


def main() -> None:
    payload = build_payload()
    markdown = render_markdown(payload)
    profile = read_json(PROFILE_JSON)
    sensitive_hits = scan_sensitive_text(markdown)
    private_hits = [marker for marker in private_profile_markers(profile) if marker and marker in markdown]
    if sensitive_hits or private_hits:
        raise SystemExit(
            f"Refusing to write public agency activation docket with sensitive markers={sensitive_hits} private_hits={private_hits}"
        )
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, markdown)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "activation_items": payload["summary"]["activation_item_count"],
                "blocked_items": payload["summary"]["blocked_item_count"],
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
