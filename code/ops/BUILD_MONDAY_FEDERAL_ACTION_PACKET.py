"""Build a fail-closed Monday federal opportunity decision packet.

The builder converts a source-bound local configuration into a deterministic
decision register, a future-partner blocker brief, and a public-safe capability
statement PDF. It has no email, portal, certification, signing, or submission
capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "monday_federal_action_packet_v1.json"
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
OUTPUT_JSON = SPRINT_DIR / "MONDAY_FEDERAL_ACTION_PACKET_2026-07-26.json"
OUTPUT_MD = SPRINT_DIR / "MONDAY_FEDERAL_ACTION_PACKET_2026-07-26.md"
CSDR_MD = SPRINT_DIR / "FA701426SCS01_PARTNER_ONLY_BRIEF_2026-07-26.md"
OUTPUT_PDF = ROOT / "output" / "pdf" / "LumenCore_Federal_Capability_Statement_CURRENT.pdf"
ARC_SEAL_LOGO = ROOT / "assets" / "brand" / "lumaarc_eclipse_corona_concept_v1.png"
SOURCE_NATIVE_LEDGER = (
    ROOT / "out" / "ops" / "source_native_family_baseline_ledger_latest.json"
)
PROSPECTIVE_PROTOCOL = (
    ROOT / "config" / "time_series_source_native_prospective_protocol_v3.json"
)
PROSPECTIVE_PROTOCOL_STATUS = (
    ROOT
    / "docs"
    / "receipts"
    / "TIME_SERIES_SOURCE_NATIVE_PROSPECTIVE_V3_STATUS_2026-08-04.json"
)
SCHEMA = "lumencore.monday_federal_action_packet.v1"
CONFIG_SCHEMA = "lumencore.monday_federal_action_packet_config.v1"

EXPECTED_CONTROLS = {
    "action_time_human_approval_required": True,
    "authenticated_portal_action_allowed": False,
    "autonomous_certification_allowed": False,
    "autonomous_email_send_allowed": False,
    "autonomous_submission_allowed": False,
    "duplicate_suppression_required": True,
    "mandatory_requirement_fail_closed": True,
    "performance_claims_require_independent_evidence": True,
    "private_identifiers_omitted": True,
    "response_instructions_structured": True,
    "source_set_completeness_required_for_ready_state": True,
}
ALLOWED_DECISIONS = {
    "NO_READY_RESPONSE_FUTURE_PARTNER_ROUTE_BLOCKED",
    "NO_GO_PRIME_PARTNER_ROUTE_POSSIBLE_NOT_READY",
    "NO_GO_INTENDED_SOLE_SOURCE_EQUIVALENCE_NOT_ESTABLISHED",
}
ALLOWED_PARTNER_ROUTE_STATES = {"NONE", "POSSIBLE_NOT_READY", "READY"}
ALLOWED_SOURCE_SET_STATES = {
    "FROZEN_REVIEWED",
    "FROZEN_PARTIAL_ATTACHMENTS_NOT_CAPTURED",
}
REQUIRED_RESPONSE_INSTRUCTION_FIELDS = {
    "channel",
    "recipient_role_count",
    "subject_line",
    "file_format",
    "page_limit",
    "format_rules",
    "required_contents",
    "source_precedence",
}


class PacketError(ValueError):
    """Raised when a packet invariant is violated."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketError(f"Unreadable JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise PacketError(f"Expected an object: {path}")
    return payload


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def canonical_sha256(payload: Any) -> str:
    rendered = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest().upper()


def parse_utc(value: str, label: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise PacketError(f"{label} must be canonical UTC with a Z suffix")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise PacketError(f"{label} is invalid") from exc
    return parsed.astimezone(timezone.utc)


def validate_public_url(value: str, label: str) -> None:
    split = urlsplit(value)
    if split.scheme != "https" or not split.hostname:
        raise PacketError(f"{label} must be a public HTTPS URL")
    if split.username or split.password:
        raise PacketError(f"{label} must not contain credentials")


def validate_config(config: dict[str, Any]) -> None:
    if config.get("schema") != CONFIG_SCHEMA or config.get("version") != 1:
        raise PacketError("Unsupported Monday packet config")
    if config.get("controls") != EXPECTED_CONTROLS:
        raise PacketError("Monday packet controls are not fail-closed")

    profile = config.get("company_profile")
    if not isinstance(profile, dict):
        raise PacketError("company_profile must be an object")
    validate_public_url(profile.get("public_domain", ""), "company public_domain")
    validate_public_url(
        profile.get("public_repository", ""),
        "company public_repository",
    )
    if not profile.get("truthful_prime_boundary"):
        raise PacketError("truthful_prime_boundary is required")

    opportunities = config.get("opportunities")
    if not isinstance(opportunities, list) or not opportunities:
        raise PacketError("opportunities must be a nonempty list")
    record_ids: set[str] = set()
    notice_ids: set[str] = set()
    for index, opportunity in enumerate(opportunities):
        label = f"opportunities[{index}]"
        if not isinstance(opportunity, dict):
            raise PacketError(f"{label} must be an object")
        record_id = opportunity.get("record_id")
        notice_id = opportunity.get("notice_id")
        if not isinstance(record_id, str) or not record_id:
            raise PacketError(f"{label}.record_id is required")
        if not isinstance(notice_id, str) or not notice_id:
            raise PacketError(f"{label}.notice_id is required")
        if record_id in record_ids or notice_id in notice_ids:
            raise PacketError("Duplicate record_id or notice_id")
        record_ids.add(record_id)
        notice_ids.add(notice_id)
        validate_public_url(opportunity.get("official_url", ""), f"{label}.official_url")
        parse_utc(opportunity.get("source_observed_utc", ""), f"{label}.source_observed_utc")
        parse_utc(opportunity.get("deadline_utc", ""), f"{label}.deadline_utc")
        for field in (
            "deadline_local",
            "deadline_source_literal",
            "deadline_normalization",
            "truthful_role",
            "duplicate_state",
            "source_set_state",
            "safest_next_action",
        ):
            if not isinstance(opportunity.get(field), str) or not opportunity[field]:
                raise PacketError(f"{label}.{field} is required")
        if not isinstance(opportunity.get("timezone_clarification_required"), bool):
            raise PacketError(
                f"{label}.timezone_clarification_required must be boolean"
            )
        if opportunity.get("decision") not in ALLOWED_DECISIONS:
            raise PacketError(f"{label}.decision is invalid")
        if opportunity.get("partner_route_state") not in ALLOWED_PARTNER_ROUTE_STATES:
            raise PacketError(f"{label}.partner_route_state is invalid")
        if opportunity.get("source_set_state") not in ALLOWED_SOURCE_SET_STATES:
            raise PacketError(f"{label}.source_set_state is invalid")
        if not isinstance(opportunity.get("source_set_complete"), bool):
            raise PacketError(f"{label}.source_set_complete must be boolean")
        if (
            opportunity["source_set_complete"]
            != (opportunity["source_set_state"] == "FROZEN_REVIEWED")
        ):
            raise PacketError(f"{label}.source_set completeness is inconsistent")
        score = opportunity.get("fit_score")
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise PacketError(f"{label}.fit_score must be 0..100")
        response_instructions = opportunity.get("response_instructions")
        if not isinstance(response_instructions, dict):
            raise PacketError(f"{label}.response_instructions must be an object")
        if set(response_instructions) != REQUIRED_RESPONSE_INSTRUCTION_FIELDS:
            raise PacketError(f"{label}.response_instructions fields are incomplete")
        if (
            not isinstance(response_instructions["recipient_role_count"], int)
            or response_instructions["recipient_role_count"] < 1
        ):
            raise PacketError(
                f"{label}.response_instructions.recipient_role_count is invalid"
            )
        if (
            not isinstance(response_instructions["required_contents"], list)
            or not response_instructions["required_contents"]
            or not all(
                isinstance(item, str) and item
                for item in response_instructions["required_contents"]
            )
        ):
            raise PacketError(
                f"{label}.response_instructions.required_contents must be nonempty"
            )
        for field in REQUIRED_RESPONSE_INSTRUCTION_FIELDS - {
            "recipient_role_count",
            "required_contents",
        }:
            if (
                not isinstance(response_instructions.get(field), str)
                or not response_instructions[field]
            ):
                raise PacketError(
                    f"{label}.response_instructions.{field} is required"
                )
        source_files = opportunity.get("source_files")
        if not isinstance(source_files, list) or not source_files:
            raise PacketError(f"{label}.source_files must be nonempty")
        for source_index, source_file in enumerate(source_files):
            source_label = f"{label}.source_files[{source_index}]"
            if not isinstance(source_file, dict):
                raise PacketError(f"{source_label} must be an object")
            if set(source_file) != {"path", "official_url", "role"}:
                raise PacketError(f"{source_label} fields are incomplete")
            if not isinstance(source_file["path"], str) or not source_file["path"]:
                raise PacketError(f"{source_label}.path is required")
            validate_public_url(
                source_file["official_url"], f"{source_label}.official_url"
            )
            if not isinstance(source_file["role"], str) or not source_file["role"]:
                raise PacketError(f"{source_label}.role is required")
        requirements = opportunity.get("mandatory_requirements")
        if not isinstance(requirements, list) or not requirements:
            raise PacketError(f"{label}.mandatory_requirements must be nonempty")
        requirement_ids: set[str] = set()
        for requirement in requirements:
            if not isinstance(requirement, dict):
                raise PacketError(f"{label} requirement must be an object")
            requirement_id = requirement.get("id")
            if not isinstance(requirement_id, str) or not requirement_id:
                raise PacketError(f"{label} requirement id is required")
            if requirement_id in requirement_ids:
                raise PacketError(f"{label} has duplicate requirement ids")
            requirement_ids.add(requirement_id)
            if requirement.get("state") not in {"VERIFIED", "NOT_ESTABLISHED"}:
                raise PacketError(f"{label} requirement state is invalid")

    if config.get("claim_boundary") is None:
        raise PacketError("claim_boundary is required")


def build_current_evidence_snapshot() -> dict[str, Any]:
    ledger = read_json(SOURCE_NATIVE_LEDGER)
    protocol = read_json(PROSPECTIVE_PROTOCOL)
    prospective = read_json(PROSPECTIVE_PROTOCOL_STATUS)
    summary = ledger.get("summary")
    if not isinstance(summary, dict):
        raise PacketError("Source-native ledger summary is missing")
    expected_protocol_hash = canonical_sha256(
        {
            key: value
            for key, value in protocol.items()
            if key != "protocol_payload_sha256"
        }
    )
    if str(protocol.get("protocol_payload_sha256", "")).lower() != (
        expected_protocol_hash.lower()
    ):
        raise PacketError("Version 3 prospective protocol hash is stale")
    expected_status_hash = canonical_sha256(
        {
            key: value
            for key, value in prospective.items()
            if key != "status_sha256"
        }
    )
    if str(prospective.get("status_sha256", "")).lower() != (
        expected_status_hash.lower()
    ):
        raise PacketError("Version 3 prospective status hash is stale")
    if prospective.get("schema") != "time_series_source_native_prospective_status.v3":
        raise PacketError("Unexpected Version 3 prospective status schema")
    if prospective.get("protocol_id") != protocol.get("protocol_id"):
        raise PacketError("Version 3 prospective protocol id is stale")
    if prospective.get("protocol_payload_sha256") != protocol.get(
        "protocol_payload_sha256"
    ):
        raise PacketError("Version 3 prospective protocol receipt is stale")
    if prospective.get("state") != "SEALED_AWAITING_FUTURE_OBSERVATIONS":
        raise PacketError("Version 3 prospective status is not sealed")
    if prospective.get("primary_inference_complete") is not False:
        raise PacketError("Version 3 prospective inference state is unsafe")
    for key in (
        "performance_claim_allowed",
        "trading_alpha_claim_allowed",
        "field_validation_claim_allowed",
        "real_dollar_claim_allowed",
    ):
        if prospective.get(key) is not False:
            raise PacketError(f"Version 3 prospective claim control is unsafe: {key}")

    snapshot = {
        "registered_family_count": summary.get("registered_family_count"),
        "implementation_present_count": summary.get(
            "implementation_present_count"
        ),
        "implementation_required_count": summary.get(
            "implementation_required_count"
        ),
        "executed_direct_source_baseline_comparison_count": summary.get(
            "executed_direct_source_baseline_comparison_count"
        ),
        "exploratory_direct_comparison_count": summary.get(
            "exploratory_direct_comparison_count"
        ),
        "confirmatory_protocol_comparison_count": summary.get(
            "confirmatory_protocol_comparison_count"
        ),
        "promotion_gate_pass_count": summary.get(
            "internal_source_native_promotion_gate_pass_count"
        ),
        "global_holm_positive_count": summary.get(
            "individual_comparison_global_holm_positive_count"
        ),
        "prospective_protocol_id": prospective.get("protocol_id"),
        "prospective_protocol_status": prospective.get("state"),
        "prospective_promotion_decision": prospective.get(
            "promotion_decision"
        ),
        "eligible_future_observation_count": prospective.get(
            "eligible_future_observation_count"
        ),
        "source_native_ledger_generated_utc": ledger.get("generated_utc"),
        "prospective_protocol_generated_utc": prospective.get("generated_at_utc"),
        "performance_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "real_dollar_claim_allowed": False,
        "source_receipts": [
            {
                "path": SOURCE_NATIVE_LEDGER.relative_to(ROOT).as_posix(),
                "bytes": SOURCE_NATIVE_LEDGER.stat().st_size,
                "sha256": sha256_file(SOURCE_NATIVE_LEDGER),
            },
            {
                "path": PROSPECTIVE_PROTOCOL.relative_to(ROOT).as_posix(),
                "bytes": PROSPECTIVE_PROTOCOL.stat().st_size,
                "sha256": sha256_file(PROSPECTIVE_PROTOCOL),
            },
            {
                "path": PROSPECTIVE_PROTOCOL_STATUS.relative_to(ROOT).as_posix(),
                "bytes": PROSPECTIVE_PROTOCOL_STATUS.stat().st_size,
                "sha256": sha256_file(PROSPECTIVE_PROTOCOL_STATUS),
            },
        ],
        "claim_boundary": summary.get("claim_boundary")
        or prospective.get("claim_boundary"),
    }
    required_counts = (
        "registered_family_count",
        "implementation_present_count",
        "implementation_required_count",
        "executed_direct_source_baseline_comparison_count",
        "exploratory_direct_comparison_count",
        "confirmatory_protocol_comparison_count",
        "promotion_gate_pass_count",
        "global_holm_positive_count",
        "eligible_future_observation_count",
    )
    if any(not isinstance(snapshot.get(key), int) for key in required_counts):
        raise PacketError("Current evidence snapshot has non-integer counts")
    for key in (
        "source_native_ledger_generated_utc",
        "prospective_protocol_generated_utc",
    ):
        value = snapshot.get(key)
        if not isinstance(value, str) or not value:
            raise PacketError(f"Current evidence snapshot is missing {key}")
    return snapshot


def build_packet(
    config_path: Path = CONFIG_PATH,
    *,
    as_of_utc: str,
) -> dict[str, Any]:
    config = read_json(config_path)
    validate_config(config)
    now = parse_utc(as_of_utc, "as_of_utc")
    evidence_snapshot = build_current_evidence_snapshot()

    opportunities: list[dict[str, Any]] = []
    for source in config["opportunities"]:
        deadline = parse_utc(source["deadline_utc"], "deadline_utc")
        missing = [
            requirement["id"]
            for requirement in source["mandatory_requirements"]
            if requirement["state"] != "VERIFIED"
        ]
        source_receipts = []
        for source_file in source["source_files"]:
            relative = source_file["path"]
            path = ROOT / relative
            if not path.is_file():
                raise PacketError(f"Missing source file: {relative}")
            source_receipts.append(
                {
                    "path": relative.replace("\\", "/"),
                    "official_url": source_file["official_url"],
                    "role": source_file["role"],
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
            )

        prime_submission_ready = False
        partner_brief_ready = (
            not missing
            and source["source_set_complete"]
            and source["partner_route_state"] == "READY"
            and bool(source["truthful_role"])
        )
        future_partner_route = source["partner_route_state"] == "POSSIBLE_NOT_READY"
        instruction_conformance_ready = (
            source["source_set_complete"]
            and not missing
            and not source["timezone_clarification_required"]
        )
        opportunities.append(
            {
                **source,
                "source_files": source_receipts,
                "seconds_remaining": max(0, int((deadline - now).total_seconds())),
                "deadline_closed": deadline <= now,
                "missing_mandatory_evidence": missing,
                "prime_submission_ready": prime_submission_ready,
                "partner_brief_ready": partner_brief_ready,
                "future_partner_route_possible_not_ready": future_partner_route,
                "instruction_conformance_ready": instruction_conformance_ready,
                "external_action_authorized": False,
            }
        )

    opportunities.sort(key=lambda row: (row["deadline_utc"], -row["fit_score"]))
    summary = {
        "opportunity_count": len(opportunities),
        "prime_submission_ready_count": sum(
            row["prime_submission_ready"] for row in opportunities
        ),
        "partner_brief_ready_count": sum(
            row["partner_brief_ready"] for row in opportunities
        ),
        "future_partner_route_count": sum(
            row["future_partner_route_possible_not_ready"] for row in opportunities
        ),
        "complete_source_set_count": sum(
            row["source_set_complete"] for row in opportunities
        ),
        "partial_source_set_count": sum(
            not row["source_set_complete"] for row in opportunities
        ),
        "instruction_conformance_ready_count": sum(
            row["instruction_conformance_ready"] for row in opportunities
        ),
        "no_go_or_partner_only_count": sum(
            not row["prime_submission_ready"] for row in opportunities
        ),
        "closed_deadline_count": sum(row["deadline_closed"] for row in opportunities),
        "external_action_count": 0,
    }
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "NO_TRUTHFUL_MONDAY_PRIME_OR_PARTNER_RESPONSE_READY",
        "as_of_utc": as_of_utc,
        "summary": summary,
        "controls": config["controls"],
        "company_profile": config["company_profile"],
        "current_evidence_snapshot": evidence_snapshot,
        "opportunities": opportunities,
        "artifacts": {
            "decision_markdown": OUTPUT_MD.relative_to(ROOT).as_posix(),
            "csdr_partner_brief": CSDR_MD.relative_to(ROOT).as_posix(),
            "public_safe_capability_pdf": OUTPUT_PDF.relative_to(ROOT).as_posix(),
        },
        "claim_boundary": config["claim_boundary"],
        "control_sha256": "",
    }
    payload["control_sha256"] = canonical_sha256(
        {key: value for key, value in payload.items() if key != "control_sha256"}
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Monday Federal Opportunity Decision Packet",
        "",
        f"- As of UTC: `{payload['as_of_utc']}`",
        f"- Status: `{payload['status']}`",
        f"- Prime submission ready: `{payload['summary']['prime_submission_ready_count']}`",
        f"- Partner briefs ready: `{payload['summary']['partner_brief_ready_count']}`",
        f"- Future partner routes possible but not ready: `{payload['summary']['future_partner_route_count']}`",
        f"- Complete frozen source sets: `{payload['summary']['complete_source_set_count']}`",
        f"- Partial frozen source sets: `{payload['summary']['partial_source_set_count']}`",
        f"- External actions performed: `{payload['summary']['external_action_count']}`",
        f"- Control SHA-256: `{payload['control_sha256']}`",
        "",
        "## Executive Decision",
        "",
        "No reviewed Monday notice supports a truthful LumenCore prime or partner response with the currently documented experience, personnel, security, product, teaming, and platform evidence. A polished response cannot cure a mandatory qualification gap. CSDR, PHA, and HDB remain possible future partner routes only after the named gates are independently established.",
        "",
        "| Deadline | Notice | Fit | Decision | Safest action |",
        "|---|---|---:|---|---|",
    ]
    for row in payload["opportunities"]:
        lines.append(
            f"| {row['deadline_local']} | `{row['notice_id']}` | "
            f"{row['fit_score']} | `{row['decision']}` | "
            f"{row['safest_next_action']} |"
        )
    lines.extend(
        [
            "",
            "## Requirement Audit",
            "",
        ]
    )
    for row in payload["opportunities"]:
        lines.extend(
            [
                f"### {row['notice_id']} - {row['title']}",
                "",
                f"- Official source: {row['official_url']}",
                f"- Truthful role: {row['truthful_role']}",
                f"- Duplicate state: `{row['duplicate_state']}`",
                f"- Source set: `{row['source_set_state']}`",
                f"- Source set complete: `{str(row['source_set_complete']).lower()}`",
                f"- Prime submission ready: `{str(row['prime_submission_ready']).lower()}`",
                f"- Partner brief ready: `{str(row['partner_brief_ready']).lower()}`",
                f"- Future partner route possible but not ready: `{str(row['future_partner_route_possible_not_ready']).lower()}`",
                f"- Instruction conformance ready: `{str(row['instruction_conformance_ready']).lower()}`",
                f"- Deadline as written: `{row['deadline_source_literal']}`",
                f"- Deadline normalization: {row['deadline_normalization']}",
                f"- Response channel: `{row['response_instructions']['channel']}`",
                f"- Recipient roles: `{row['response_instructions']['recipient_role_count']}`",
                f"- Format / page limit: `{row['response_instructions']['file_format']}` / `{row['response_instructions']['page_limit']}`",
                "",
                "Missing mandatory evidence:",
                "",
            ]
        )
        for requirement in row["mandatory_requirements"]:
            lines.append(
                f"- `{requirement['state']}` - {requirement['description']}"
            )
        if row["source_files"]:
            lines.extend(["", "Frozen source files:", ""])
            for receipt in row["source_files"]:
                lines.append(
                    f"- `{receipt['path']}` - `{receipt['sha256']}` - {receipt['role']}"
                )
        lines.append("")
    lines.extend(
        [
            "## Monday Action Boundary",
            "",
            "- Do not submit a prime CSDR white paper.",
            "- Do not send a partner brief, notice of intent, capability challenge, quote, or portal response for any reviewed Monday lane.",
            "- Do not repeat Friday outreach.",
            "- Keep the CSDR concept internal until a qualified prime establishes all personnel, experience, security, access, OCI, NDA, data-rights, and workshare gates.",
            "- Recheck the live official notice and current entity or registration facts before any later external action.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def render_csdr_partner_brief(payload: dict[str, Any]) -> str:
    csdr = next(
        row for row in payload["opportunities"] if row["notice_id"] == "FA701426SCS01"
    )
    return "\n".join(
        [
            "# FA701426SCS01 Future-Partner Blocker Brief",
            "",
            f"- Prime response deadline: `{csdr['deadline_local']}`",
            f"- Decision: `{csdr['decision']}`",
            "- Status: `NOT_READY_FOR_PRIME_OR_PARTNER_SEND`",
            "- This is not a Step 1 white paper, not a send-ready partner brief, and not approved for direct submission to the Air Force.",
            "",
            "## Qualified-Prime Positioning",
            "",
            "LumenCore can support a qualified CSDR prime with a bounded evidence-engineering workstream for source lineage, validation-plan custody, reproducible transformation runs, exception retention, reviewer traceability, and human-authorized acceptance states. The workstream is designed to preserve which source, rule, parser, configuration, reviewer action, and output produced each asserted data-quality or curation state.",
            "",
            "## Proposed Subcontract Workstream",
            "",
            "1. Register authorized source artifacts, metadata, access boundaries, and hashes.",
            "2. Freeze validation and transformation rules before scoring or curation.",
            "3. Preserve configuration, parser, environment, output, and deviation identity.",
            "4. Retain passed, failed, neutral, inconclusive, and manually corrected outcomes.",
            "5. Produce reviewer-facing traceability from source through rule, exception, correction, and accepted output.",
            "6. Keep acceptance and promotion decisions with authorized Government and prime personnel.",
            "",
            "## Non-Negotiable Boundary",
            "",
            "LumenCore does not claim direct CSDR or FlexFile past performance, Secret-cleared personnel, the required ten-year task-lead qualifications, access to proprietary CSDR data, or authority to perform inside Government systems. The PWS requires every performing contractor and subcontractor person to hold at least a Secret clearance, so a prime cannot cure LumenCore's current personnel gate merely by owning the prime role. A future team must establish the technical approach, staffing, security posture, price, representations, and submission before any partner outreach is considered ready.",
            "",
            "## Missing Mandatory Evidence",
            "",
            *[
                f"- `{requirement['id']}` - {requirement['description']}"
                for requirement in csdr["mandatory_requirements"]
                if requirement["state"] != "VERIFIED"
            ],
            "",
            "## Send Control",
            "",
            "- No recipient is selected.",
            "- No outreach was sent by this builder.",
            "- The Friday CSDR capability email must not be duplicated.",
            "- This blocker brief is internal only and must not be sent as a substitute for qualification.",
            "- A future external action would still require fresh source review and exact action-time approval for a named recipient, subject, body, and attachment.",
            "",
            "## Source Receipts",
            "",
            *[
                f"- `{receipt['path']}` - `{receipt['sha256']}` - {receipt['role']}"
                for receipt in csdr["source_files"]
            ],
            "",
        ]
    )


def build_capability_pdf(payload: dict[str, Any], output_path: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.enums import TA_RIGHT
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import inch
        from reportlab.platypus import (
            Image,
            PageBreak,
            Paragraph,
            SimpleDocTemplate,
            Spacer,
            Table,
            TableStyle,
        )
    except ImportError as exc:
        raise PacketError("reportlab is required to build the capability PDF") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    navy = colors.HexColor("#102A43")
    teal = colors.HexColor("#087F8C")
    green = colors.HexColor("#2B7A4B")
    pale = colors.HexColor("#EAF3F5")
    ink = colors.HexColor("#172B3A")
    muted = colors.HexColor("#52616B")
    line = colors.HexColor("#CAD7DE")
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleLC",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=21,
            leading=24,
            textColor=navy,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SubtitleLC",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=teal,
            spaceAfter=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="H1LC",
            parent=styles["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=12.5,
            leading=15,
            textColor=navy,
            spaceBefore=7,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BodyLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9.2,
            leading=12.8,
            textColor=ink,
            spaceAfter=5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.8,
            leading=10.5,
            textColor=muted,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderLC",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10.2,
            textColor=colors.white,
        )
    )
    styles.add(
        ParagraphStyle(
            name="BulletLC",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.9,
            leading=12.1,
            leftIndent=13,
            firstLineIndent=-7,
            bulletIndent=4,
            textColor=ink,
            spaceAfter=2.5,
        )
    )
    styles.add(
        ParagraphStyle(
            name="CalloutLC",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9.3,
            leading=13,
            textColor=navy,
        )
    )

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(line)
        canvas.setLineWidth(0.5)
        canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
        canvas.setFont("Helvetica", 7.2)
        canvas.setFillColor(muted)
        canvas.drawString(
            0.65 * inch,
            0.35 * inch,
            "Public-safe capability statement | Not an offer, certification, or submission",
        )
        canvas.drawRightString(
            7.85 * inch,
            0.35 * inch,
            f"Prepared {payload['as_of_utc'][:10]} | Page {document.page}",
        )
        canvas.restoreState()

    document = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.55 * inch,
        bottomMargin=0.72 * inch,
        title="LumenCore Federal Capability Statement",
        author="LumenCore",
        subject="Evidence engineering for AI, data, software, and technical decisions",
    )
    profile = payload["company_profile"]
    story = []
    if not ARC_SEAL_LOGO.is_file():
        raise PacketError(f"Canonical Arc Seal logo is missing: {ARC_SEAL_LOGO}")
    if ARC_SEAL_LOGO.is_file():
        logo = Image(str(ARC_SEAL_LOGO), width=0.82 * inch, height=0.82 * inch)
        header = Table(
            [
                [
                    logo,
                    Paragraph(
                        "<b>FEDERAL CAPABILITY STATEMENT</b><br/>"
                        "Evidence engineering for accountable technical decisions",
                        ParagraphStyle(
                            "HeaderRight",
                            parent=styles["BodyLC"],
                            alignment=TA_RIGHT,
                            fontSize=9.3,
                            leading=12,
                            textColor=navy,
                        ),
                    ),
                ]
            ],
            colWidths=[1.05 * inch, 5.95 * inch],
        )
        header.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, -1), 1.0, teal),
                ]
            )
        )
        story.extend([header, Spacer(1, 0.12 * inch)])

    story.extend(
        [
            Paragraph("LumenCore", styles["TitleLC"]),
            Paragraph(profile["positioning"], styles["SubtitleLC"]),
        ]
    )
    lead = Table(
        [
            [
                Paragraph(
                    "<b>Mission fit</b><br/>Independent review, acquisition evidence, "
                    "data provenance, model and workflow evaluation, and controlled "
                    "prototype-to-pilot decisions.",
                    styles["BodyLC"],
                ),
                Paragraph(
                    "<b>Best-fit role</b><br/>A specialized evidence-engineering "
                    "workstream under a qualified prime or a bounded review sprint "
                    "using public or buyer-authorized data.",
                    styles["BodyLC"],
                ),
            ]
        ],
        colWidths=[3.45 * inch, 3.45 * inch],
    )
    lead.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale),
                ("BOX", (0, 0), (-1, -1), 0.75, line),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, line),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("RIGHTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.extend([lead, Paragraph("Core Capabilities", styles["H1LC"])])
    for item in profile["current_capabilities"]:
        story.append(Paragraph(f"- {item}", styles["BulletLC"]))

    story.append(Paragraph("Why This Is Useful to a Government Reviewer", styles["H1LC"]))
    reviewer_rows = [
        (
            "Before evaluation",
            "Lock the source, owner, baseline, metric, threshold, holdout, failure rule, and decision authority.",
        ),
        (
            "During execution",
            "Record code, configuration, environment, inputs, outputs, exceptions, deviations, and hashes.",
        ),
        (
            "After execution",
            "Separate measured evidence from assumptions; preserve adverse and inconclusive results; retain reviewer decisions.",
        ),
        (
            "At promotion",
            "Require an authorized human decision to promote, rerun, hold, reject, or seek independent review.",
        ),
    ]
    review_table = Table(
        [
            [
                Paragraph("Review stage", styles["TableHeaderLC"]),
                Paragraph("Control delivered", styles["TableHeaderLC"]),
            ],
            *[
                [
                    Paragraph(f"<b>{stage}</b>", styles["BodyLC"]),
                    Paragraph(control, styles["BodyLC"]),
                ]
                for stage, control in reviewer_rows
            ],
        ],
        colWidths=[1.38 * inch, 5.52 * inch],
        repeatRows=1,
    )
    review_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), navy),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, line),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            review_table,
            Paragraph("Bounded Engagement Model", styles["H1LC"]),
            Paragraph(
                "<b>Evidence-readiness sprint:</b> agree on one decision, one "
                "authorized data bundle, one incumbent baseline, one candidate "
                "workflow, frozen metrics, named failure conditions, and a "
                "reviewer-owned acceptance state. Deliver the reproducible evidence "
                "bundle and limitations without production connectivity.",
                styles["BodyLC"],
            ),
            PageBreak(),
            Paragraph("Deliverables and Reviewer Answers", styles["TitleLC"]),
            Paragraph(
                "A concise package designed to answer what was tested, against what, "
                "under which authority, with which failures retained, and what the "
                "evidence does and does not authorize.",
                styles["SubtitleLC"],
            ),
            Paragraph("Representative Deliverables", styles["H1LC"]),
        ]
    )
    deliverable_cells = [
        Paragraph(f"- {item}", styles["BodyLC"])
        for item in profile["proposed_deliverables"]
    ]
    deliverables_table = Table(
        [
            [deliverable_cells[0], deliverable_cells[1]],
            [deliverable_cells[2], deliverable_cells[3]],
            [deliverable_cells[4], deliverable_cells[5]],
        ],
        colWidths=[3.45 * inch, 3.45 * inch],
    )
    deliverables_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(deliverables_table)

    story.append(Paragraph("Evidence-to-Decision Workflow", styles["H1LC"]))
    workflow = [
        ("1", "Register", "Sources, ownership, authority, access, freshness, and identity"),
        ("2", "Freeze", "Baseline, candidate, metric, threshold, holdout, exclusions, and failure rules"),
        ("3", "Execute", "Exact software, configuration, environment, inputs, outputs, and deviations"),
        ("4", "Review", "Results, uncertainty, negative controls, adverse cases, and unresolved gaps"),
        ("5", "Authorize", "Human promote, rerun, hold, reject, or independent-review decision"),
    ]
    workflow_table = Table(
        [
            [
                Paragraph("Step", styles["TableHeaderLC"]),
                Paragraph("Gate", styles["TableHeaderLC"]),
                Paragraph("Reviewer-visible record", styles["TableHeaderLC"]),
            ],
            *[
                [
                    Paragraph(f"<b>{number}</b>", styles["BodyLC"]),
                    Paragraph(f"<b>{gate}</b>", styles["BodyLC"]),
                    Paragraph(record, styles["BodyLC"]),
                ]
                for number, gate, record in workflow
            ],
        ],
        colWidths=[0.55 * inch, 1.05 * inch, 5.3 * inch],
        repeatRows=1,
    )
    workflow_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), teal),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.45, line),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 1), (0, -1), "CENTER"),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.extend(
        [
            workflow_table,
            Paragraph("Procurement and Teaming Posture", styles["H1LC"]),
            Paragraph(
                "<b>Prime boundary:</b> LumenCore does not represent current federal "
                "past performance, a production ATO, FedRAMP authorization, CMMC "
                "certification, a facility clearance, cleared personnel, agency "
                "endorsement, or field validation.",
                styles["BodyLC"],
            ),
            Paragraph(
                "<b>Teaming boundary:</b> Security, domain licenses, controlled-data "
                "access, key-person qualifications, staffing, pricing, representations, "
                "and submission authority remain with the qualified prime and "
                "Government.",
                styles["BodyLC"],
            ),
            Paragraph(
                "<b>Relevant routing categories:</b> custom software and data services, "
                "computer systems design, engineering and R&D support, technical "
                "evaluation, and acquisition evidence. Confirm the controlling NAICS, "
                "PSC, set-aside, and entity record for each notice.",
                styles["BodyLC"],
            ),
            Paragraph("Fast Reviewer Questions", styles["H1LC"]),
        ]
    )
    evidence = payload["current_evidence_snapshot"]
    ledger_date = evidence["source_native_ledger_generated_utc"][:10]
    prospective_date = evidence["prospective_protocol_generated_utc"][:10]
    qa_rows = [
        (
            "What is proven now?",
            (
                "Present now: reusable source, replay, receipt, conformance, and "
                f"human-gate software patterns. Snapshot {ledger_date}: "
                f"{evidence['executed_direct_source_baseline_comparison_count']} "
                "direct comparisons "
                f"({evidence['exploratory_direct_comparison_count']} exploratory; "
                f"{evidence['confirmatory_protocol_comparison_count']} confirmatory), "
                f"{evidence['promotion_gate_pass_count']} internal promotion passes, "
                f"and {evidence['global_holm_positive_count']} global Holm positives."
            ),
        ),
        (
            "What is not proven?",
            "Agency deployment, operational suitability, field performance, certification, clearance, endorsement, or realized savings.",
        ),
        (
            "What can start safely?",
            (
                "A bounded public or buyer-authorized data review with a frozen plan "
                "and no production control. Named protocol snapshot "
                f"{prospective_date}: {evidence['eligible_future_observation_count']} "
                "eligible future observations; waiting for new source rows."
            ),
        ),
        (
            "Who decides?",
            "The authorized Government reviewer, buyer, or qualified prime. LumenCore does not automate promotion authority.",
        ),
    ]
    qa_cells = [
        Paragraph(
            f"<b>{question}</b><br/>{answer}",
            styles["BodyLC"],
        )
        for question, answer in qa_rows
    ]
    qa_table = Table(
        [
            [qa_cells[0], qa_cells[1]],
            [qa_cells[2], qa_cells[3]],
        ],
        colWidths=[3.45 * inch, 3.45 * inch],
    )
    qa_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), pale),
                ("GRID", (0, 0), (-1, -1), 0.5, line),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([qa_table, Spacer(1, 0.04 * inch)])

    story.extend(
        [
            Paragraph("Contact and Action Boundary", styles["H1LC"]),
            Paragraph(
                f"<b>Public repository:</b> {profile['public_repository']}<br/>"
                f"<b>Public domain:</b> {profile['public_domain']} "
                "(verify availability at action time; use the repository as the "
                "stable code entry point).<br/>"
                "<b>Identifiers:</b> use current reviewed company and SAM records; "
                "private identifiers are omitted.<br/>"
                "<b>External use:</b> requires a current notice check, source-bound "
                "claim and duplicate review, and authorized human approval.",
                styles["BodyLC"],
            ),
        ]
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def write_outputs(payload: dict[str, Any]) -> None:
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    OUTPUT_MD.write_text(render_markdown(payload), encoding="utf-8")
    CSDR_MD.write_text(render_csdr_partner_brief(payload), encoding="utf-8")
    build_capability_pdf(payload, OUTPUT_PDF)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=CONFIG_PATH)
    parser.add_argument("--as-of-utc", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_packet(args.config, as_of_utc=args.as_of_utc)
    if not args.check:
        write_outputs(payload)
    print(json.dumps(payload["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
