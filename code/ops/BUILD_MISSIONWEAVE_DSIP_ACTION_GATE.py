from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import posixpath
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from zipfile import BadZipFile, ZipFile


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
PRIVATE_DIR = PACKAGE_DIR / "private"
DEFAULT_PRIVATE_INPUT = PRIVATE_DIR / "MISSIONWEAVE_DSIP_ACTION.private.json"
TEMPLATE = ROOT / "config" / "missionweave_dsip_action_private_template_v1.json"
PRIVATE_CAPTURE_TOOL = ROOT / "code" / "ops" / "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py"
PRIVATE_FINALIZER = ROOT / "code" / "ops" / "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py"
PRIVATE_CAPTURE_WORKFLOW = (
    PACKAGE_DIR / "MISSIONWEAVE_DSIP_PRIVATE_CAPTURE_WORKFLOW_2026-07-17.md"
)
MANIFEST = PACKAGE_DIR / "MISSIONWEAVE_DSIP_PACKAGE_MANIFEST_2026-07-16.json"
VOLUME2_PDF = PACKAGE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.pdf"
PRIVATE_FINAL_VOLUME2_PDF = PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.pdf"
PRIVATE_FINAL_VOLUME3_WORKBOOK = (
    PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
)
PRIVATE_FINAL_VOLUME3_RECEIPT = (
    PRIVATE_DIR / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
)
PRIVATE_JCP_EVIDENCE_RECEIPT = (
    PRIVATE_DIR / "MISSIONWEAVE_JCP_EVIDENCE_RECEIPT.private.json"
)
PRIVATE_JCP_EVIDENCE_TEMPLATE = (
    ROOT / "config" / "missionweave_jcp_evidence_private_template_v1.json"
)
JCP_EVIDENCE_PROTOCOL = (
    PACKAGE_DIR / "MISSIONWEAVE_JCP_EVIDENCE_PROTOCOL_2026-07-18.json"
)
CMMC_EVIDENCE_PACKET = (
    ROOT
    / "grant_submissions"
    / "compliance_evidence"
    / "CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.json"
)
CERTIFICATION_DOCUMENTARY_REGISTER = (
    PACKAGE_DIR / "MISSIONWEAVE_CERTIFICATION_DOCUMENTARY_REGISTER_2026-07-21.json"
)
OUT_JSON = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
OUT_MD = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.md"
OUT_CHECKLIST = PACKAGE_DIR / "MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md"

PRIVATE_SCHEMA = "lumencore.missionweave_dsip_action_private.v1"
PUBLIC_SCHEMA = "lumencore.missionweave_dsip_action_gate.v1"
PRIVATE_VOLUME3_RECEIPT_SCHEMA = (
    "lumencore.missionweave_dsip_volume3_final_receipt_private.v1"
)
OOXML_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
OOXML_DOCUMENT_REL_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
OOXML_PACKAGE_REL_NS = (
    "http://schemas.openxmlformats.org/package/2006/relationships"
)
OOXML_CONTENT_TYPES_NS = (
    "http://schemas.openxmlformats.org/package/2006/content-types"
)
OOXML_WORKBOOK_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
)
VOLUME3_EXPECTED_SHEETS = ("Cost", "Spend Plan")
VOLUME3_MAX_ZIP_ENTRIES = 256
VOLUME3_MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
VOLUME3_PROHIBITED_PART_PREFIXES = (
    "xl/activex/",
    "xl/embeddings/",
    "xl/externallinks/",
)
EXCEL_ERROR_VALUES = frozenset(
    {
        "#NULL!",
        "#DIV/0!",
        "#VALUE!",
        "#REF!",
        "#NAME?",
        "#NUM!",
        "#N/A",
        "#GETTING_DATA",
    }
)
PRIVATE_JCP_EVIDENCE_SCHEMA = "lumencore.missionweave_jcp_evidence_private.v1"
CMMC_PACKET_SCHEMA = "lumencore.cmmc_export_evidence_packet.v1"
CMMC_PROGRAM_ID = "MissionWeave"
CMMC_FACT_ID = "missionweave.cmmc_l2_self_status"
CMMC_CONTROL = "CMMC_L2_SELF_STATUS"
CERTIFICATION_DOCUMENTARY_SCHEMA = (
    "lumencore.missionweave_certification_documentary_register.v1"
)
CERTIFICATION_DOCUMENTARY_GATE_IDS = frozenset(
    {
        "NO_DUPLICATE_COST_OR_DELIVERABLE",
        "TECHNICAL_DATA_RIGHTS_ASSERTION",
    }
)
CERTIFICATION_DOCUMENTARY_SOURCE_PATHS = {
    "PUBLIC_REPOSITORY_LICENSE": ROOT / "LICENSE",
    "RELATED_EFFORT_OVERLAP_MATRIX": (
        PACKAGE_DIR / "MISSIONWEAVE_RELATED_EFFORT_OVERLAP_MATRIX_2026-07-18.md"
    ),
    "VOLUME2_TECHNICAL_DATA_RIGHTS_ASSERTION": (
        PACKAGE_DIR / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE_2026-07-16.md"
    ),
    "VOLUME5_RIGHTS_AND_OVERLAP_WORKSHEET": (
        PACKAGE_DIR / "MISSIONWEAVE_DSIP_VOLUME5_WORKSHEET_2026-07-16.md"
    ),
}
CERTIFICATION_DOCUMENTARY_GATE_SOURCE_ROLES = {
    "NO_DUPLICATE_COST_OR_DELIVERABLE": frozenset(
        {
            "RELATED_EFFORT_OVERLAP_MATRIX",
            "VOLUME5_RIGHTS_AND_OVERLAP_WORKSHEET",
        }
    ),
    "TECHNICAL_DATA_RIGHTS_ASSERTION": frozenset(
        {
            "PUBLIC_REPOSITORY_LICENSE",
            "VOLUME2_TECHNICAL_DATA_RIGHTS_ASSERTION",
            "VOLUME5_RIGHTS_AND_OVERLAP_WORKSHEET",
        }
    ),
}
CERTIFICATION_DOCUMENTARY_REVIEW_AUTHORITIES = {
    "NO_DUPLICATE_COST_OR_DELIVERABLE": "CORPORATE_OFFICIAL",
    "TECHNICAL_DATA_RIGHTS_ASSERTION": (
        "QUALIFIED_RIGHTS_REVIEW_AND_CORPORATE_OFFICIAL"
    ),
}
CMMC_READY_EVIDENCE_STATES = frozenset(
    {"AUTHORITATIVE_PROOF_INVENTORIED", "NOT_APPLICABLE_REVIEW_INVENTORIED"}
)
CMMC_PROHIBITED_CONCLUSIONS = frozenset(
    {"compliant", "certified", "award_eligible"}
)
CMMC_NON_AUTHORITATIVE_SOURCE_CLASSES = frozenset(
    {"FOUNDER_ATTESTATION", "PORTAL_OBSERVED"}
)
JCP_EVIDENCE_KINDS = frozenset(
    {"CERTIFIED_DD2345", "JCP_APPLICATION_SUBMISSION_RECEIPT"}
)
TOPIC = "DLA26BZ03-NV011"
EXPECTED_DEADLINE = "2026-07-22T12:00:00-04:00"
PHASE_I_CEILING = Decimal("100000")
VOLUME2_PAGE_LIMIT = 20
NEUTRAL_PROPOSAL_HEADER = "Proposal No. assigned in DSIP"
PREVIEW_RECEIPT_MAX_AGE = timedelta(minutes=30)
ACTION_TIME_APPROVAL_MAX_AGE = timedelta(minutes=15)
FUTURE_TIMESTAMP_TOLERANCE = timedelta(minutes=2)
ACTION_CONTEXT_SCHEMA = "lumencore.missionweave_dsip_action_context.v1"
PREVIEW_EVIDENCE_BINDING_SCHEMA = (
    "lumencore.missionweave_dsip_preview_evidence_binding.v1"
)
ACTION_APPROVAL_BINDING_SCHEMA = (
    "lumencore.missionweave_dsip_action_approval_binding.v1"
)

IDENTITY_GATES = {
    "dsip_authenticated": "DSIP_AUTHENTICATION",
    "organization_linked": "DSIP_ORGANIZATION_LINKAGE",
    "firm_admin_confirmed": "DSIP_FIRM_ADMIN",
    "firm_pin_available_in_dsip": "DSIP_FIRM_PIN_AVAILABILITY",
    "firm_level_forms_complete": "DSIP_FIRM_LEVEL_FORMS",
    "sam_active_verified": "SAM_ACTIVE_STATUS",
    "sam_representations_current": "SAM_REPRESENTATIONS_CURRENT",
    "sam_legal_name_match": "SAM_LEGAL_NAME_MATCH",
    "uei_match_verified": "UEI_MATCH",
    "cage_match_verified": "CAGE_MATCH",
    "sba_company_registry_verified": "SBA_COMPANY_REGISTRY",
    "sbc_control_id_verified": "SBC_CONTROL_ID",
    "submitter_authority_confirmed": "SUBMITTER_AUTHORITY",
}

PROPOSAL_FLAG_GATES = {
    "live_deadline_confirmed": "LIVE_DSIP_DEADLINE_CONFIRMATION",
    "volume1_public_release_text_reviewed": "VOLUME1_PUBLIC_RELEASE_TEXT_REVIEW",
    "volume2_pdf_rebuilt_with_assigned_proposal_number": "VOLUME2_REBUILD",
    "volume2_virus_scan_passed": "VOLUME2_VIRUS_SCAN",
    "volume3_cost_basis_supported": "VOLUME3_COST_BASIS",
    "volume4_ccr_answer_verified": "VOLUME4_CCR",
    "volume5_upload_set_reviewed": "VOLUME5_UPLOAD_SET",
    "volume6_fwa_training_current": "VOLUME6_FWA_TRAINING",
    "volume7_webform_complete": "VOLUME7_FOREIGN_AFFILIATIONS_WEBFORM",
    "portal_preview_reviewed": "COMPLETE_PORTAL_PREVIEW_REVIEW",
}

COMPLIANCE_GATES = {
    "pi_primary_employment_confirmed": "PI_PRIMARY_EMPLOYMENT",
    "pi_640_hours_confirmed": "PI_640_HOURS",
    "sbir_work_share_confirmed": "SBIR_PERCENTAGE_OF_WORK",
    "us_small_business_eligibility_confirmed": "US_SMALL_BUSINESS_ELIGIBILITY",
    "ownership_and_affiliates_reviewed": "OWNERSHIP_AND_AFFILIATES",
    "prior_current_pending_support_reviewed": "PRIOR_CURRENT_PENDING_SUPPORT",
    "no_duplicate_cost_or_deliverable": "NO_DUPLICATE_COST_OR_DELIVERABLE",
    "dd2345_or_jcp_application_evidence_ready": "DD2345_OR_JCP_APPLICATION_EVIDENCE",
    "controlled_data_excluded_from_submission": "CONTROLLED_DATA_EXCLUDED",
    "technology_control_plan_decision_documented": "TECHNOLOGY_CONTROL_PLAN_DECISION",
    "current_cmmc_requirements_reviewed": "CURRENT_CMMC_REQUIREMENTS_REVIEW",
    "cmmc_phase_i_self_assessment_position_supported": "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
    "no_cmmc_status_overclaim": "NO_CMMC_STATUS_OVERCLAIM",
    "foreign_citizen_answer_verified": "FOREIGN_CITIZEN_ANSWER",
    "foreign_affiliations_webform_answered_from_current_facts": "FOREIGN_AFFILIATIONS_CURRENT_FACTS",
    "conflicts_and_joint_venture_status_reviewed": "CONFLICTS_AND_JOINT_VENTURE_STATUS",
    "technical_data_rights_assertion_supported": "TECHNICAL_DATA_RIGHTS_ASSERTION",
}

APPROVAL_FLAG_GATES = {
    "corporate_official_reviewed_all_volumes": "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
    "final_submission_authorized_at_action_time": "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
}

PROPOSAL_VALUE_KEYS = {
    "proposal_number",
    "volume2_pdf_sha256",
    "volume3_total_usd",
    "portal_preview_sha256",
}
PROPOSAL_CONSISTENCY_KEYS = {
    "portal_preview_binding_sha256",
    "portal_preview_captured_utc",
}
APPROVAL_VALUE_KEYS = {"approval_utc"}
APPROVAL_CONSISTENCY_KEYS = {"approval_binding_sha256"}

SPECIAL_GATES = (
    "PRIVATE_INPUT_TIMESTAMP",
    "ASSIGNED_PROPOSAL_NUMBER_CAPTURE",
    "VOLUME2_PDF_HASH_MATCH",
    "VOLUME2_ASSIGNED_PROPOSAL_NUMBER_EMBEDDED",
    "VOLUME3_TOTAL_MATCHES_PHASE_I_CEILING",
    "PORTAL_PREVIEW_RECEIPT_HASH",
    "ITAR_SCOPE_CONFIRMED",
    "ACTION_TIME_APPROVAL_TIMESTAMP",
)

GATE_RECONCILIATION_GROUPS = {
    "A_DOCUMENTARY_RETRIEVAL": frozenset(
        {
            "ASSIGNED_PROPOSAL_NUMBER_CAPTURE",
            "CAGE_MATCH",
            "DD2345_OR_JCP_APPLICATION_EVIDENCE",
            "DSIP_FIRM_PIN_AVAILABILITY",
            "PORTAL_PREVIEW_RECEIPT_HASH",
            "PRIVATE_INPUT_TIMESTAMP",
            "SAM_ACTIVE_STATUS",
            "SAM_LEGAL_NAME_MATCH",
            "SAM_REPRESENTATIONS_CURRENT",
            "SBA_COMPANY_REGISTRY",
            "SBC_CONTROL_ID",
            "UEI_MATCH",
            "VOLUME6_FWA_TRAINING",
        }
    ),
    "B_FOUNDER_FACTUAL_ANSWER": frozenset(
        {
            "CONFLICTS_AND_JOINT_VENTURE_STATUS",
            "FOREIGN_CITIZEN_ANSWER",
            "NO_DUPLICATE_COST_OR_DELIVERABLE",
            "OWNERSHIP_AND_AFFILIATES",
            "PI_640_HOURS",
            "PI_PRIMARY_EMPLOYMENT",
            "PRIOR_CURRENT_PENDING_SUPPORT",
            "SBIR_PERCENTAGE_OF_WORK",
            "SUBMITTER_AUTHORITY",
            "US_SMALL_BUSINESS_ELIGIBILITY",
        }
    ),
    "C_LEGAL_CERTIFICATION_DECISION": frozenset(
        {
            "ACTION_TIME_APPROVAL_TIMESTAMP",
            "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
            "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
            "CONTROLLED_DATA_EXCLUDED",
            "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
            "CURRENT_CMMC_REQUIREMENTS_REVIEW",
            "FOREIGN_AFFILIATIONS_CURRENT_FACTS",
            "ITAR_SCOPE_CONFIRMED",
            "NO_CMMC_STATUS_OVERCLAIM",
            "TECHNICAL_DATA_RIGHTS_ASSERTION",
            "TECHNOLOGY_CONTROL_PLAN_DECISION",
            "VOLUME4_CCR",
        }
    ),
    "D_PORTAL_MECHANICS": frozenset(
        {
            "COMPLETE_PORTAL_PREVIEW_REVIEW",
            "DSIP_AUTHENTICATION",
            "DSIP_FIRM_ADMIN",
            "DSIP_FIRM_LEVEL_FORMS",
            "DSIP_ORGANIZATION_LINKAGE",
            "LIVE_DSIP_DEADLINE_CONFIRMATION",
            "VOLUME7_FOREIGN_AFFILIATIONS_WEBFORM",
        }
    ),
    "E_TECHNICAL_VOLUME_CONSISTENCY": frozenset(
        {
            "VOLUME1_PUBLIC_RELEASE_TEXT_REVIEW",
            "VOLUME2_ASSIGNED_PROPOSAL_NUMBER_EMBEDDED",
            "VOLUME2_PDF_HASH_MATCH",
            "VOLUME2_REBUILD",
            "VOLUME2_VIRUS_SCAN",
            "VOLUME3_COST_BASIS",
            "VOLUME3_TOTAL_MATCHES_PHASE_I_CEILING",
            "VOLUME5_UPLOAD_SET",
        }
    ),
}

LIFECYCLE_PRE_AWARD_OR_NEGOTIATION_GATES = frozenset(
    {
        "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
        "TECHNOLOGY_CONTROL_PLAN_DECISION",
    }
)

LIFECYCLE_ACTION_TIME_GATES = frozenset(
    {
        "ACTION_TIME_APPROVAL_TIMESTAMP",
        "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
        "COMPLETE_PORTAL_PREVIEW_REVIEW",
        "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
        "PORTAL_PREVIEW_RECEIPT_HASH",
    }
)

FOUNDER_ACTION_DEFINITIONS = (
    {
        "step_id": "01_JCP_APPLICATION_EVIDENCE",
        "title": "Submit the JCP application and retain official evidence",
        "gate_ids": frozenset({"DD2345_OR_JCP_APPLICATION_EVIDENCE"}),
        "instruction": (
            "Use the official JCP portal. Registration or prerequisites in progress are "
            "not enough; retain the official application-submission receipt PDF or a "
            "current certified DD Form 2345 in the ignored private evidence area."
        ),
        "evidence_required": "Hash-matched official JCP receipt PDF or certified DD Form 2345",
        "human_boundary": "The founder completes any portal certification or final JCP submit action.",
    },
    {
        "step_id": "02_DSIP_FIRM_PIN_CONFIRMATION",
        "title": "Confirm Firm PIN availability inside DSIP",
        "gate_ids": frozenset({"DSIP_FIRM_PIN_AVAILABILITY"}),
        "instruction": (
            "Confirm that the organization-linked DSIP account can access the Firm PIN. "
            "Do not place the PIN itself in chat, Git, logs, or the private gate record."
        ),
        "evidence_required": "Boolean availability state only; never the PIN value",
        "human_boundary": "The founder handles authentication and any secret value.",
    },
    {
        "step_id": "03_VOLUME3_COST_SUPPORT",
        "title": "Support and approve the Volume 3 cost basis",
        "gate_ids": frozenset({"VOLUME3_COST_BASIS"}),
        "instruction": (
            "Review the proposed labor rate, 640 PI hours, fringe, indirect base, cloud/data, "
            "travel, software/storage, no-subcontractor position, and 100,000 dollar total "
            "against actual records before approving the cost volume."
        ),
        "evidence_required": "Current founder records and corporate-official cost review",
        "human_boundary": "The founder confirms the factual cost basis; the builder checks arithmetic only.",
    },
    {
        "step_id": "04_COMPLIANCE_AND_CONFLICT_POSITION",
        "title": "Review conflicts, cost separation, data rights, CMMC, and export-control planning",
        "gate_ids": frozenset(
            {
                "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
                "CONFLICTS_AND_JOINT_VENTURE_STATUS",
                "CURRENT_CMMC_REQUIREMENTS_REVIEW",
                "NO_DUPLICATE_COST_OR_DELIVERABLE",
                "TECHNICAL_DATA_RIGHTS_ASSERTION",
                "TECHNOLOGY_CONTROL_PLAN_DECISION",
            }
        ),
        "instruction": (
            "Answer conflicts and joint-venture status from current facts; reconcile the "
            "no-duplicate-cost position and technical-data-rights schedule against source "
            "records; review the live CMMC requirement; preserve the no-overclaim position; "
            "and document whether a Technology Control Plan is a contracting-negotiation deliverable."
        ),
        "evidence_required": (
            "Current source review, hash-bound documentary register, and bounded "
            "founder/corporate-official position"
        ),
        "human_boundary": (
            "No compliance, assessment, certification, or contracting-office acceptance is inferred."
        ),
    },
    {
        "step_id": "05_VOLUME5_UPLOAD_SET",
        "title": "Lock the Volume 5 supporting-document set",
        "gate_ids": frozenset({"VOLUME5_UPLOAD_SET"}),
        "instruction": (
            "Upload only current, applicable documents. For the ITAR-marked scope, include "
            "the verified JCP/DD Form 2345 evidence required by the BAA; do not upload the "
            "obsolete foreign-affiliations PDF."
        ),
        "evidence_required": "Reviewed attachment list with current file hashes",
        "human_boundary": "Any legally consequential upload or representation remains founder reviewed.",
    },
    {
        "step_id": "06_FRESH_PORTAL_PREVIEW",
        "title": "Review and seal a fresh complete DSIP preview",
        "gate_ids": frozenset(
            {"COMPLETE_PORTAL_PREVIEW_REVIEW", "PORTAL_PREVIEW_RECEIPT_HASH"}
        ),
        "instruction": (
            "After every field and upload is final, inspect all seven volumes, filenames, "
            "hashes, cost totals, and the live deadline. Save the current preview receipt "
            "privately and bind it with the collector."
        ),
        "evidence_required": "Fresh portal-preview receipt bound to the exact upload set",
        "human_boundary": "The founder reviews the rendered Government portal preview.",
    },
    {
        "step_id": "07_ACTION_TIME_REVIEW_AND_AUTHORIZATION",
        "title": "Perform corporate review and action-time authorization",
        "gate_ids": frozenset(
            {
                "ACTION_TIME_APPROVAL_TIMESTAMP",
                "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
                "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
            }
        ),
        "instruction": (
            "Only after the fresh preview is stable, review every volume as corporate official, "
            "capture the short-lived approval binding, and authorize the exact final submission."
        ),
        "evidence_required": "Fresh approval timestamp and binding to the current preview/upload set",
        "human_boundary": "The final certification and submit click are founder-only actions.",
    },
)

REQUIRED_VOLUME2_SECTIONS = (
    "1. Identification and Significance of the Problem or Opportunity",
    "2. Phase I Technical Objectives",
    "3. Phase I Statement of Work",
    "6. Commercialization Strategy",
    "12. Technical Data and Software Rights Assertions",
)

PRIVATE_VALUE_MARKERS = (
    "client_secret",
    "refresh_token",
    "private key",
    "api_key=",
    "sk-",
    "xox",
)

CLAIM_BOUNDARY = (
    "This public gate proves package integrity, document-format checks, and the completion state "
    "of a bounded private DSIP fact workflow. It does not expose legal identifiers, a Firm PIN, "
    "the assigned proposal number, private portal evidence, or unsupported compliance facts. It "
    "does not establish DLA validation, CMMC status, ITAR compliance, award eligibility, proposal "
    "acceptance, submission, selection, contract, award, deployment, or realized performance."
)


class MissionWeaveGateError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT.resolve()).as_posix()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def normalize_text_eol(payload: bytes) -> bytes:
    return payload.replace(b"\r\n", b"\n")


def read_head_blob(path: Path) -> bytes | None:
    try:
        relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return None
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    return completed.stdout if completed.returncode == 0 else None


def canonical_tracked_sha256(path: Path) -> str:
    worktree_bytes = path.read_bytes()
    head_blob = read_head_blob(path)
    if (
        head_blob is not None
        and normalize_text_eol(worktree_bytes) == normalize_text_eol(head_blob)
    ):
        worktree_bytes = head_blob
    return hashlib.sha256(worktree_bytes).hexdigest().upper()


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def git_ignored(path: Path) -> bool:
    if not path_is_within(path, ROOT):
        return False
    relative = path.resolve().relative_to(ROOT.resolve()).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_private_target(path: Path) -> Path:
    if path.is_symlink():
        raise MissionWeaveGateError("PRIVATE_INPUT_SYMLINK_REJECTED")
    resolved = path.resolve()
    if not path_is_within(resolved, PRIVATE_DIR):
        raise MissionWeaveGateError("PRIVATE_INPUT_OUTSIDE_BOUNDED_DIRECTORY")
    if resolved.exists() and not resolved.is_file():
        raise MissionWeaveGateError("PRIVATE_INPUT_NOT_REGULAR_FILE")
    if not git_ignored(resolved):
        raise MissionWeaveGateError("PRIVATE_INPUT_NOT_GIT_IGNORED")
    return resolved


def valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def parse_timestamp(value: Any) -> datetime | None:
    if not valid_timestamp(value):
        return None
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc)


def normalize_reference_time(value: datetime | str | None = None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, str):
        parsed = parse_timestamp(value)
        if parsed is None:
            raise MissionWeaveGateError("EVALUATION_TIMESTAMP_INVALID")
        return parsed
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.astimezone(timezone.utc)
    raise MissionWeaveGateError("EVALUATION_TIMESTAMP_INVALID")


def timestamp_is_fresh(
    value: Any,
    *,
    reference_utc: datetime,
    max_age: timedelta,
) -> bool:
    parsed = parse_timestamp(value)
    if parsed is None:
        return False
    age = reference_utc - parsed
    return -FUTURE_TIMESTAMP_TOLERANCE <= age <= max_age


def valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[A-Fa-f0-9]{64}", value) is not None


def valid_proposal_number(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    return (
        5 <= len(candidate) <= 64
        and candidate != NEUTRAL_PROPOSAL_HEADER
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]+", candidate) is not None
    )


def parse_phase_i_total(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    if not amount.is_finite():
        return None
    return amount


def normalize_cell_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value.strip()).lower()


def normalize_formula(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", "", value).upper().lstrip("=")


def ooxml_member_path(base: str, target: str) -> str | None:
    if not isinstance(target, str) or not target or "\\" in target:
        return None
    if target.startswith("/"):
        candidate = posixpath.normpath(target.lstrip("/"))
    else:
        candidate = posixpath.normpath(posixpath.join(posixpath.dirname(base), target))
    if candidate in {"", ".", ".."} or candidate.startswith("../"):
        return None
    return candidate


def ooxml_cell_value(cell: ET.Element, shared_strings: list[str]) -> Any:
    cell_type = cell.get("t")
    value_node = cell.find(f"{{{OOXML_MAIN_NS}}}v")
    if cell_type == "inlineStr":
        return "".join(
            node.text or "" for node in cell.iter(f"{{{OOXML_MAIN_NS}}}t")
        )
    if value_node is None:
        return None
    value = value_node.text
    if cell_type == "s" and value is not None:
        try:
            return shared_strings[int(value)]
        except (IndexError, TypeError, ValueError):
            return None
    return value


def inspect_volume3_workbook_contents(workbook_path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ooxml_valid": False,
        "structure_valid": False,
        "sheet_names": [],
        "formula_count": 0,
        "formula_error_count": 0,
        "error_cell_count": 0,
        "financials_derived_from_contents": False,
        "financials": {},
        "failure_code": "WORKBOOK_NOT_INSPECTED",
    }
    try:
        with ZipFile(workbook_path) as archive:
            infos = archive.infolist()
            if not infos or len(infos) > VOLUME3_MAX_ZIP_ENTRIES:
                result["failure_code"] = "OOXML_ENTRY_COUNT_INVALID"
                return result
            member_names = [info.filename for info in infos]
            if len(member_names) != len(set(member_names)):
                result["failure_code"] = "OOXML_DUPLICATE_MEMBER"
                return result
            if any(info.flag_bits & 0x1 for info in infos):
                result["failure_code"] = "OOXML_ENCRYPTED_PART"
                return result
            if sum(info.file_size for info in infos) > VOLUME3_MAX_UNCOMPRESSED_BYTES:
                result["failure_code"] = "OOXML_UNCOMPRESSED_SIZE_EXCEEDED"
                return result

            members = set(member_names)
            for member in members:
                normalized = posixpath.normpath(member.replace("\\", "/"))
                if (
                    member.startswith(("/", "\\"))
                    or normalized in {"", ".", ".."}
                    or normalized.startswith("../")
                    or normalized != member
                ):
                    result["failure_code"] = "OOXML_UNSAFE_MEMBER_PATH"
                    return result
                lower_member = member.lower()
                if lower_member.endswith("vbaproject.bin") or any(
                    lower_member.startswith(prefix)
                    for prefix in VOLUME3_PROHIBITED_PART_PREFIXES
                ):
                    result["failure_code"] = "OOXML_ACTIVE_OR_EXTERNAL_PART"
                    return result

            required_members = {
                "[Content_Types].xml",
                "_rels/.rels",
                "xl/workbook.xml",
                "xl/_rels/workbook.xml.rels",
            }
            if not required_members.issubset(members):
                result["failure_code"] = "OOXML_REQUIRED_PART_MISSING"
                return result

            for member in sorted(name for name in members if name.endswith(".rels")):
                relation_root = ET.fromstring(archive.read(member))
                for relation in relation_root.findall(
                    f"{{{OOXML_PACKAGE_REL_NS}}}Relationship"
                ):
                    if str(relation.get("TargetMode", "")).lower() == "external":
                        result["failure_code"] = "OOXML_EXTERNAL_RELATIONSHIP"
                        return result

            content_types = ET.fromstring(archive.read("[Content_Types].xml"))
            content_type_overrides = {
                str(override.get("PartName", "")): override.get("ContentType")
                for override in content_types.findall(
                    f"{{{OOXML_CONTENT_TYPES_NS}}}Override"
                )
            }
            content_type_defaults = {
                str(default.get("Extension", "")).lower(): default.get("ContentType")
                for default in content_types.findall(
                    f"{{{OOXML_CONTENT_TYPES_NS}}}Default"
                )
            }
            workbook_content_type = content_type_overrides.get(
                "/xl/workbook.xml"
            ) or content_type_defaults.get("xml")
            workbook_type_valid = workbook_content_type == OOXML_WORKBOOK_CONTENT_TYPE
            if not workbook_type_valid:
                result["failure_code"] = "OOXML_WORKBOOK_CONTENT_TYPE_INVALID"
                return result

            shared_strings: list[str] = []
            if "xl/sharedStrings.xml" in members:
                shared_root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                for shared_item in shared_root.findall(
                    f"{{{OOXML_MAIN_NS}}}si"
                ):
                    shared_strings.append(
                        "".join(
                            node.text or ""
                            for node in shared_item.iter(f"{{{OOXML_MAIN_NS}}}t")
                        )
                    )

            workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
            workbook_rel_root = ET.fromstring(
                archive.read("xl/_rels/workbook.xml.rels")
            )
            workbook_relations = {
                relation.get("Id"): relation.get("Target")
                for relation in workbook_rel_root.findall(
                    f"{{{OOXML_PACKAGE_REL_NS}}}Relationship"
                )
            }
            sheet_nodes = workbook_root.findall(
                f".//{{{OOXML_MAIN_NS}}}sheet"
            )
            sheet_names = [str(node.get("name", "")) for node in sheet_nodes]
            result["sheet_names"] = sheet_names
            if tuple(sheet_names) != VOLUME3_EXPECTED_SHEETS:
                result["failure_code"] = "OOXML_WORKSHEET_SET_INVALID"
                return result

            cells_by_sheet: dict[str, dict[str, dict[str, Any]]] = {}
            formula_count = 0
            formula_error_count = 0
            error_cell_count = 0
            for sheet_node in sheet_nodes:
                relationship_id = sheet_node.get(
                    f"{{{OOXML_DOCUMENT_REL_NS}}}id"
                )
                target = workbook_relations.get(relationship_id)
                sheet_path = ooxml_member_path("xl/workbook.xml", str(target or ""))
                if (
                    sheet_path is None
                    or not sheet_path.startswith("xl/worksheets/")
                    or sheet_path not in members
                ):
                    result["failure_code"] = "OOXML_WORKSHEET_RELATION_INVALID"
                    return result
                sheet_root = ET.fromstring(archive.read(sheet_path))
                sheet_cells: dict[str, dict[str, Any]] = {}
                for cell in sheet_root.findall(f".//{{{OOXML_MAIN_NS}}}c"):
                    coordinate = str(cell.get("r", "")).upper()
                    if not re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]{0,6}", coordinate):
                        result["failure_code"] = "OOXML_CELL_REFERENCE_INVALID"
                        return result
                    formula_node = cell.find(f"{{{OOXML_MAIN_NS}}}f")
                    value = ooxml_cell_value(cell, shared_strings)
                    is_error = bool(
                        cell.get("t") == "e"
                        or (
                            isinstance(value, str)
                            and value.strip().upper() in EXCEL_ERROR_VALUES
                        )
                    )
                    if formula_node is not None:
                        formula_count += 1
                        if is_error:
                            formula_error_count += 1
                    if is_error:
                        error_cell_count += 1
                    sheet_cells[coordinate] = {
                        "value": value,
                        "formula": (
                            formula_node.text if formula_node is not None else None
                        ),
                    }
                cells_by_sheet[str(sheet_node.get("name"))] = sheet_cells

            result["formula_count"] = formula_count
            result["formula_error_count"] = formula_error_count
            result["error_cell_count"] = error_cell_count
            if formula_count == 0:
                result["failure_code"] = "OOXML_FORMULAS_MISSING"
                return result

            cost_cells = cells_by_sheet["Cost"]
            spend_cells = cells_by_sheet["Spend Plan"]
            required_labels = {
                ("Cost", "C18"): "total hours / average rate",
                ("Cost", "C58"): "total sub contract labor",
                ("Cost", "B84"): "total estimated cost and profit",
                ("Spend Plan", "A5"): "cumulative total",
            }
            for (sheet_name, coordinate), expected_label in required_labels.items():
                actual = cells_by_sheet.get(sheet_name, {}).get(coordinate, {}).get(
                    "value"
                )
                if normalize_cell_text(actual) != expected_label:
                    result["failure_code"] = "OOXML_COST_LABEL_BINDING_INVALID"
                    return result

            required_formulas = {
                ("Cost", "F84"): "SUM(F80:F83)",
                ("Spend Plan", "B1"): "'COST'!$F$84",
                ("Spend Plan", "G5"): "SUM($B$3:G3)",
            }
            for (sheet_name, coordinate), expected_formula in required_formulas.items():
                actual = cells_by_sheet.get(sheet_name, {}).get(coordinate, {}).get(
                    "formula"
                )
                if normalize_formula(actual) != normalize_formula(expected_formula):
                    result["failure_code"] = "OOXML_COST_FORMULA_BINDING_INVALID"
                    return result

            total_usd = parse_phase_i_total(cost_cells.get("F84", {}).get("value"))
            subcontractor_cost_usd = parse_phase_i_total(
                cost_cells.get("F58", {}).get("value")
            )
            pi_hours = parse_phase_i_total(cost_cells.get("D18", {}).get("value"))
            spend_plan_total = parse_phase_i_total(
                spend_cells.get("G5", {}).get("value")
            )
            month_values = [
                parse_phase_i_total(spend_cells.get(f"{column}3", {}).get("value"))
                for column in "BCDEFG"
            ]
            month_labels_valid = all(
                normalize_cell_text(spend_cells.get(f"{column}2", {}).get("value"))
                == f"month {index}"
                for index, column in enumerate("BCDEFG", start=1)
            )
            financials_valid = bool(
                total_usd is not None
                and subcontractor_cost_usd is not None
                and pi_hours is not None
                and spend_plan_total is not None
                and all(value is not None for value in month_values)
                and month_labels_valid
                and sum(value for value in month_values if value is not None)
                == spend_plan_total
                and spend_plan_total == total_usd
            )
            if not financials_valid:
                result["failure_code"] = "OOXML_FINANCIAL_CONTENT_INVALID"
                return result

            result.update(
                {
                    "ooxml_valid": True,
                    "structure_valid": True,
                    "financials_derived_from_contents": True,
                    "financials": {
                        "total_usd": total_usd,
                        "firm_cost_usd": total_usd - subcontractor_cost_usd,
                        "subcontractor_cost_usd": subcontractor_cost_usd,
                        "duration_months": len(month_values),
                        "pi_hours": pi_hours,
                    },
                    "failure_code": None,
                }
            )
            return result
    except (BadZipFile, ET.ParseError, KeyError, OSError, RuntimeError, ValueError):
        result["failure_code"] = "OOXML_PARSE_FAILED"
        return result


def inspect_private_volume3_artifact(
    receipt_path: Path = PRIVATE_FINAL_VOLUME3_RECEIPT,
    workbook_path: Path = PRIVATE_FINAL_VOLUME3_WORKBOOK,
) -> dict[str, Any]:
    receipt_target = validate_private_target(receipt_path)
    workbook_target = validate_private_target(workbook_path)
    receipt_present = receipt_target.is_file()
    workbook_present = workbook_target.is_file()
    state = {
        "receipt_present": receipt_present,
        "workbook_present": workbook_present,
        "receipt_header_valid": False,
        "workbook_size_matches_receipt": False,
        "workbook_hash_matches_receipt": False,
        "workbook_ooxml_valid": False,
        "workbook_structure_valid": False,
        "workbook_sheet_names_match_receipt": False,
        "workbook_formula_count": 0,
        "workbook_formula_error_count": None,
        "workbook_error_cell_count": None,
        "workbook_financials_derived_from_contents": False,
        "workbook_content_failure_code": "WORKBOOK_NOT_INSPECTED",
        "formula_scan_clean": False,
        "export_reimport_verified": False,
        "financial_reconciliation_pass": False,
        "review_guardrails_preserved": False,
        "receipt_integrity_pass": False,
        "artifact_binding_sha256": None,
        "private_path_exposed": False,
        "private_hash_exposed": False,
    }
    if not receipt_present or not workbook_present:
        return state

    try:
        receipt = json.loads(receipt_target.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return state
    if not isinstance(receipt, dict):
        return state

    state["receipt_header_valid"] = bool(
        receipt.get("schema") == PRIVATE_VOLUME3_RECEIPT_SCHEMA
        and receipt.get("topic") == TOPIC
        and receipt.get("file") == workbook_target.name
    )
    state["workbook_size_matches_receipt"] = bool(
        isinstance(receipt.get("bytes"), int)
        and receipt["bytes"] == workbook_target.stat().st_size
    )
    state["workbook_hash_matches_receipt"] = bool(
        valid_sha256(receipt.get("sha256"))
        and str(receipt["sha256"]).upper() == sha256_file(workbook_target)
    )
    workbook_contents = inspect_volume3_workbook_contents(workbook_target)
    state["workbook_ooxml_valid"] = workbook_contents["ooxml_valid"]
    state["workbook_structure_valid"] = workbook_contents["structure_valid"]
    state["workbook_sheet_names_match_receipt"] = bool(
        isinstance(receipt.get("sheets"), list)
        and receipt["sheets"] == workbook_contents["sheet_names"]
    )
    state["workbook_formula_count"] = workbook_contents["formula_count"]
    state["workbook_formula_error_count"] = workbook_contents[
        "formula_error_count"
    ]
    state["workbook_error_cell_count"] = workbook_contents["error_cell_count"]
    state["workbook_financials_derived_from_contents"] = workbook_contents[
        "financials_derived_from_contents"
    ]
    state["workbook_content_failure_code"] = workbook_contents["failure_code"]
    state["formula_scan_clean"] = bool(
        state["workbook_ooxml_valid"]
        and state["workbook_formula_count"] > 0
        and state["workbook_formula_error_count"] == 0
        and state["workbook_error_cell_count"] == 0
        and receipt.get("formula_error_count")
        == state["workbook_formula_error_count"]
    )
    state["export_reimport_verified"] = bool(
        state["workbook_ooxml_valid"]
        and receipt.get("export_reimport_verified") is True
    )
    workbook_financials = workbook_contents["financials"]
    state["financial_reconciliation_pass"] = bool(
        state["workbook_financials_derived_from_contents"]
        and workbook_financials.get("total_usd") == PHASE_I_CEILING
        and workbook_financials.get("firm_cost_usd") == PHASE_I_CEILING
        and workbook_financials.get("subcontractor_cost_usd") == Decimal("0")
        and workbook_financials.get("duration_months") == 6
        and workbook_financials.get("pi_hours") == Decimal("640")
        and parse_phase_i_total(receipt.get("total_usd"))
        == workbook_financials.get("total_usd")
        and parse_phase_i_total(receipt.get("firm_cost_usd"))
        == workbook_financials.get("firm_cost_usd")
        and parse_phase_i_total(receipt.get("subcontractor_cost_usd"))
        == workbook_financials.get("subcontractor_cost_usd")
        and receipt.get("taba_requested") is False
        and receipt.get("duration_months")
        == workbook_financials.get("duration_months")
        and parse_phase_i_total(receipt.get("pi_hours"))
        == workbook_financials.get("pi_hours")
    )
    state["review_guardrails_preserved"] = bool(
        receipt.get("corporate_official_review_required") is True
        and receipt.get("cost_basis_supported") is False
    )
    state["receipt_integrity_pass"] = all(
        state[field]
        for field in (
            "receipt_header_valid",
            "workbook_size_matches_receipt",
            "workbook_hash_matches_receipt",
            "workbook_ooxml_valid",
            "workbook_structure_valid",
            "workbook_sheet_names_match_receipt",
            "workbook_financials_derived_from_contents",
            "formula_scan_clean",
            "export_reimport_verified",
            "financial_reconciliation_pass",
            "review_guardrails_preserved",
        )
    )
    state["artifact_binding_sha256"] = (
        stable_sha256(receipt).upper() if state["receipt_integrity_pass"] else None
    )
    return state


def volume3_artifact_is_verified(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    return bool(
        state.get("receipt_present") is True
        and state.get("workbook_present") is True
        and state.get("receipt_header_valid") is True
        and state.get("workbook_size_matches_receipt") is True
        and state.get("workbook_hash_matches_receipt") is True
        and state.get("workbook_ooxml_valid") is True
        and state.get("workbook_structure_valid") is True
        and state.get("workbook_sheet_names_match_receipt") is True
        and isinstance(state.get("workbook_formula_count"), int)
        and state.get("workbook_formula_count", 0) > 0
        and state.get("workbook_formula_error_count") == 0
        and state.get("workbook_error_cell_count") == 0
        and state.get("workbook_financials_derived_from_contents") is True
        and state.get("workbook_content_failure_code") is None
        and state.get("formula_scan_clean") is True
        and state.get("export_reimport_verified") is True
        and state.get("financial_reconciliation_pass") is True
        and state.get("review_guardrails_preserved") is True
        and state.get("receipt_integrity_pass") is True
        and valid_sha256(state.get("artifact_binding_sha256"))
    )


def inspect_private_jcp_evidence(
    receipt_path: Path = PRIVATE_JCP_EVIDENCE_RECEIPT,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "receipt_present": receipt_path.is_file(),
        "receipt_header_valid": False,
        "evidence_file_present": False,
        "evidence_pdf": False,
        "evidence_hash_matches_receipt": False,
        "source_metadata_valid": False,
        "entity_match_confirmed": False,
        "corporate_official_reviewed": False,
        "evidence_integrity_pass": False,
        "evidence_kind": None,
        "failure_code": "PRIVATE_JCP_RECEIPT_NOT_FOUND",
        "evidence_binding_sha256": None,
        "private_path_exposed": False,
        "private_hash_exposed": False,
    }
    if not receipt_path.is_file():
        return state

    try:
        receipt = json.loads(
            validate_private_target(receipt_path).read_text(encoding="utf-8")
        )
    except (MissionWeaveGateError, OSError, UnicodeDecodeError, json.JSONDecodeError):
        state["failure_code"] = "PRIVATE_JCP_RECEIPT_INVALID"
        return state
    if not isinstance(receipt, dict):
        state["failure_code"] = "PRIVATE_JCP_RECEIPT_NOT_OBJECT"
        return state

    required_keys = {
        "schema",
        "topic",
        "captured_utc",
        "evidence_kind",
        "evidence_file",
        "evidence_file_sha256",
        "source_issued_utc",
        "source_channel",
        "entity_match_confirmed",
        "corporate_official_reviewed",
    }
    if set(receipt) != required_keys:
        state["failure_code"] = "PRIVATE_JCP_RECEIPT_SCHEMA_DRIFT"
        return state

    evidence_name = receipt.get("evidence_file")
    evidence_kind = receipt.get("evidence_kind")
    state["evidence_kind"] = (
        evidence_kind if evidence_kind in JCP_EVIDENCE_KINDS else None
    )
    header_valid = bool(
        receipt.get("schema") == PRIVATE_JCP_EVIDENCE_SCHEMA
        and receipt.get("topic") == TOPIC
        and evidence_kind in JCP_EVIDENCE_KINDS
        and valid_timestamp(receipt.get("captured_utc"))
        and isinstance(evidence_name, str)
        and evidence_name == Path(evidence_name).name
        and Path(evidence_name).suffix.casefold() == ".pdf"
        and valid_sha256(receipt.get("evidence_file_sha256"))
    )
    state["receipt_header_valid"] = header_valid
    if not header_valid:
        state["failure_code"] = "PRIVATE_JCP_RECEIPT_HEADER_INVALID"
        return state

    evidence_path = receipt_path.parent / str(evidence_name)
    try:
        evidence_path = validate_private_target(evidence_path)
    except MissionWeaveGateError:
        state["failure_code"] = "PRIVATE_JCP_EVIDENCE_PATH_INVALID"
        return state

    evidence_present = evidence_path.is_file() and evidence_path.stat().st_size > 0
    evidence_hash_match = bool(
        evidence_present
        and sha256_file(evidence_path)
        == str(receipt["evidence_file_sha256"]).upper()
    )
    source_metadata_valid = bool(
        receipt.get("source_channel") == "JCP_PORTAL"
        and valid_timestamp(receipt.get("source_issued_utc"))
    )
    entity_match = receipt.get("entity_match_confirmed") is True
    corporate_review = receipt.get("corporate_official_reviewed") is True
    evidence_integrity_pass = bool(
        header_valid
        and evidence_present
        and evidence_hash_match
        and source_metadata_valid
        and entity_match
        and corporate_review
    )
    state.update(
        {
            "evidence_file_present": evidence_present,
            "evidence_pdf": evidence_present,
            "evidence_hash_matches_receipt": evidence_hash_match,
            "source_metadata_valid": source_metadata_valid,
            "entity_match_confirmed": entity_match,
            "corporate_official_reviewed": corporate_review,
            "evidence_integrity_pass": evidence_integrity_pass,
            "evidence_binding_sha256": (
                stable_sha256(receipt).upper() if evidence_integrity_pass else None
            ),
            "failure_code": (
                None
                if evidence_integrity_pass
                else "PRIVATE_JCP_EVIDENCE_INCOMPLETE"
            ),
        }
    )
    return state


def jcp_evidence_is_verified(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    return bool(
        state.get("receipt_present") is True
        and state.get("receipt_header_valid") is True
        and state.get("evidence_file_present") is True
        and state.get("evidence_pdf") is True
        and state.get("evidence_hash_matches_receipt") is True
        and state.get("source_metadata_valid") is True
        and state.get("entity_match_confirmed") is True
        and state.get("corporate_official_reviewed") is True
        and state.get("evidence_integrity_pass") is True
        and state.get("evidence_kind") in JCP_EVIDENCE_KINDS
        and state.get("failure_code") is None
        and valid_sha256(state.get("evidence_binding_sha256"))
    )


def inspect_cmmc_evidence_packet(
    packet_path: Path = CMMC_EVIDENCE_PACKET,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "packet_present": packet_path.is_file(),
        "packet_regular_file": False,
        "schema_valid": False,
        "integrity_valid": False,
        "generated_timestamp_valid": False,
        "missionweave_program_unique": False,
        "cmmc_requirement_unique": False,
        "requirement_source_policy_valid": False,
        "packet_consumed": False,
        "packet_state": None,
        "requirement_evidence_state": None,
        "requirements_review_basis_present": False,
        "phase_i_position_supported": False,
        "overclaim_boundary_present": False,
        "packet_binding_sha256": None,
        "failure_code": "CMMC_EVIDENCE_PACKET_NOT_FOUND",
    }
    if packet_path.is_symlink() or not packet_path.is_file():
        if packet_path.is_symlink():
            state["failure_code"] = "CMMC_EVIDENCE_PACKET_SYMLINK_REJECTED"
        return state
    state["packet_regular_file"] = True

    try:
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        state["failure_code"] = "CMMC_EVIDENCE_PACKET_INVALID"
        return state
    if not isinstance(packet, dict):
        state["failure_code"] = "CMMC_EVIDENCE_PACKET_NOT_OBJECT"
        return state

    integrity = packet.get("integrity")
    expected_hash = integrity.get("packet_sha256") if isinstance(integrity, dict) else None
    candidate = deepcopy(packet)
    candidate_integrity = candidate.get("integrity")
    if isinstance(candidate_integrity, dict):
        candidate_integrity["packet_sha256"] = ""
    integrity_valid = bool(
        isinstance(integrity, dict)
        and integrity.get("hash_algorithm") == "SHA-256"
        and valid_sha256(expected_hash)
        and hmac.compare_digest(
            str(expected_hash).casefold(), stable_sha256(candidate).casefold()
        )
    )
    state["schema_valid"] = packet.get("schema") == CMMC_PACKET_SCHEMA
    state["integrity_valid"] = integrity_valid
    state["generated_timestamp_valid"] = valid_timestamp(packet.get("generated_utc"))
    state["packet_state"] = (
        packet.get("packet_state")
        if isinstance(packet.get("packet_state"), str)
        else None
    )

    programs = packet.get("programs")
    missionweave_programs = (
        [
            program
            for program in programs
            if isinstance(program, dict)
            and program.get("program_id") == CMMC_PROGRAM_ID
        ]
        if isinstance(programs, list)
        else []
    )
    state["missionweave_program_unique"] = len(missionweave_programs) == 1
    requirements = (
        missionweave_programs[0].get("requirements", [])
        if state["missionweave_program_unique"]
        else []
    )
    cmmc_requirements = (
        [
            requirement
            for requirement in requirements
            if isinstance(requirement, dict)
            and requirement.get("fact_id") == CMMC_FACT_ID
            and requirement.get("control") == CMMC_CONTROL
        ]
        if isinstance(requirements, list)
        else []
    )
    state["cmmc_requirement_unique"] = len(cmmc_requirements) == 1
    requirement = cmmc_requirements[0] if len(cmmc_requirements) == 1 else {}
    accepted_source_classes = requirement.get("accepted_source_classes")
    accepted_source_class_set = (
        {
            item
            for item in accepted_source_classes
            if isinstance(item, str) and item
        }
        if isinstance(accepted_source_classes, list)
        else set()
    )
    state["requirement_source_policy_valid"] = bool(
        accepted_source_class_set
        and not CMMC_NON_AUTHORITATIVE_SOURCE_CLASSES.intersection(
            accepted_source_class_set
        )
    )
    evidence_state = requirement.get("evidence_state")
    state["requirement_evidence_state"] = (
        evidence_state if isinstance(evidence_state, str) else None
    )

    packet_consumed = bool(
        state["packet_regular_file"]
        and state["schema_valid"]
        and state["integrity_valid"]
        and state["generated_timestamp_valid"]
        and state["missionweave_program_unique"]
        and state["cmmc_requirement_unique"]
        and state["requirement_source_policy_valid"]
    )
    packet_prohibited = packet.get("prohibited_conclusions")
    requirement_prohibited = requirement.get("prohibited_conclusions")
    packet_prohibited_set = (
        {item for item in packet_prohibited if isinstance(item, str)}
        if isinstance(packet_prohibited, list)
        else set()
    )
    requirement_prohibited_set = (
        {item for item in requirement_prohibited if isinstance(item, str)}
        if isinstance(requirement_prohibited, list)
        else set()
    )
    evidence_rows = requirement.get("evidence")
    accepted_evidence_count = (
        sum(
            isinstance(row, dict)
            and row.get("evaluation") == "ACCEPTED_PROOF_METADATA"
            for row in evidence_rows
        )
        if isinstance(evidence_rows, list)
        else 0
    )
    authoritative_count = requirement.get("authoritative_proof_count")
    authoritative_position_supported = bool(
        evidence_state == "AUTHORITATIVE_PROOF_INVENTORIED"
        and isinstance(authoritative_count, int)
        and not isinstance(authoritative_count, bool)
        and authoritative_count > 0
        and accepted_evidence_count == authoritative_count
        and requirement.get("issues") == []
    )
    applicability = requirement.get("applicability")
    not_applicable_position_supported = bool(
        evidence_state == "NOT_APPLICABLE_REVIEW_INVENTORIED"
        and isinstance(applicability, dict)
        and applicability.get("state") == "NOT_APPLICABLE"
        and applicability.get("decided_by_source_class")
        in {"LEGAL_REVIEW", "AGENCY_DETERMINATION"}
        and applicability.get("named_reviewer_present") is True
        and isinstance(applicability.get("reviewer_role"), str)
        and bool(applicability.get("reviewer_role"))
        and isinstance(applicability.get("decision_ref"), str)
        and str(applicability.get("decision_ref")).startswith(
            ("private-ref:", "official-source:")
        )
        and valid_sha256(applicability.get("decision_sha256"))
        and requirement.get("issues") == []
    )
    state["packet_consumed"] = packet_consumed
    state["requirements_review_basis_present"] = packet_consumed
    state["phase_i_position_supported"] = bool(
        packet_consumed
        and evidence_state in CMMC_READY_EVIDENCE_STATES
        and (
            authoritative_position_supported
            or not_applicable_position_supported
        )
    )
    state["overclaim_boundary_present"] = bool(
        packet_consumed
        and CMMC_PROHIBITED_CONCLUSIONS.issubset(packet_prohibited_set)
        and CMMC_PROHIBITED_CONCLUSIONS.issubset(requirement_prohibited_set)
    )
    state["packet_binding_sha256"] = (
        str(expected_hash).upper() if packet_consumed else None
    )
    state["failure_code"] = None if packet_consumed else "CMMC_EVIDENCE_PACKET_REJECTED"
    return state


def cmmc_packet_is_consumed(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    return bool(
        state.get("packet_present") is True
        and state.get("packet_regular_file") is True
        and state.get("schema_valid") is True
        and state.get("integrity_valid") is True
        and state.get("generated_timestamp_valid") is True
        and state.get("missionweave_program_unique") is True
        and state.get("cmmc_requirement_unique") is True
        and state.get("requirement_source_policy_valid") is True
        and state.get("packet_consumed") is True
        and state.get("requirements_review_basis_present") is True
        and state.get("failure_code") is None
        and valid_sha256(state.get("packet_binding_sha256"))
    )


def inspect_certification_documentary_register(
    register_path: Path = CERTIFICATION_DOCUMENTARY_REGISTER,
) -> dict[str, Any]:
    gate_decisions = {
        gate_id: False for gate_id in sorted(CERTIFICATION_DOCUMENTARY_GATE_IDS)
    }
    state: dict[str, Any] = {
        "register_present": register_path.is_file(),
        "register_regular_file": False,
        "schema_valid": False,
        "topic_valid": False,
        "generated_timestamp_valid": False,
        "integrity_valid": False,
        "source_set_valid": False,
        "source_hashes_current": False,
        "gate_set_valid": False,
        "gate_rows_valid": False,
        "controls_valid": False,
        "claim_boundary_present": False,
        "register_consumed": False,
        "status": None,
        "gate_decisions": gate_decisions,
        "open_gate_ids": sorted(gate_decisions),
        "register_binding_sha256": None,
        "failure_code": "CERTIFICATION_DOCUMENTARY_REGISTER_NOT_FOUND",
    }
    if register_path.is_symlink() or not register_path.is_file():
        if register_path.is_symlink():
            state["failure_code"] = (
                "CERTIFICATION_DOCUMENTARY_REGISTER_SYMLINK_REJECTED"
            )
        return state
    state["register_regular_file"] = True

    try:
        register = json.loads(register_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        state["failure_code"] = "CERTIFICATION_DOCUMENTARY_REGISTER_INVALID"
        return state
    if not isinstance(register, dict):
        state["failure_code"] = "CERTIFICATION_DOCUMENTARY_REGISTER_NOT_OBJECT"
        return state

    expected_top_keys = {
        "schema",
        "generated_utc",
        "topic",
        "status",
        "source_artifacts",
        "gates",
        "controls",
        "claim_boundary",
        "integrity",
    }
    if set(register) != expected_top_keys:
        state["failure_code"] = "CERTIFICATION_DOCUMENTARY_REGISTER_SCHEMA_DRIFT"
        return state

    integrity = register.get("integrity")
    expected_hash = (
        integrity.get("register_sha256") if isinstance(integrity, dict) else None
    )
    candidate = deepcopy(register)
    candidate_integrity = candidate.get("integrity")
    if isinstance(candidate_integrity, dict):
        candidate_integrity["register_sha256"] = ""
    state["schema_valid"] = (
        register.get("schema") == CERTIFICATION_DOCUMENTARY_SCHEMA
    )
    state["topic_valid"] = register.get("topic") == TOPIC
    state["generated_timestamp_valid"] = valid_timestamp(
        register.get("generated_utc")
    )
    state["integrity_valid"] = bool(
        isinstance(integrity, dict)
        and set(integrity) == {"hash_algorithm", "register_sha256"}
        and integrity.get("hash_algorithm") == "SHA-256"
        and valid_sha256(expected_hash)
        and hmac.compare_digest(
            str(expected_hash).casefold(), stable_sha256(candidate).casefold()
        )
    )

    source_rows = register.get("source_artifacts")
    source_by_role: dict[str, dict[str, Any]] = {}
    source_rows_structural = isinstance(source_rows, list)
    if source_rows_structural:
        for row in source_rows:
            if (
                not isinstance(row, dict)
                or set(row) != {"role", "path", "sha256"}
                or not isinstance(row.get("role"), str)
                or row["role"] in source_by_role
            ):
                source_rows_structural = False
                break
            source_by_role[row["role"]] = row
    state["source_set_valid"] = bool(
        source_rows_structural
        and set(source_by_role) == set(CERTIFICATION_DOCUMENTARY_SOURCE_PATHS)
    )
    source_hashes_current = state["source_set_valid"]
    if source_hashes_current:
        for role, expected_path in CERTIFICATION_DOCUMENTARY_SOURCE_PATHS.items():
            row = source_by_role[role]
            recorded_hash = row.get("sha256")
            if not (
                row.get("path") == rel(expected_path)
                and path_is_within(expected_path, ROOT)
                and expected_path.is_file()
                and not expected_path.is_symlink()
                and valid_sha256(recorded_hash)
                and hmac.compare_digest(
                    str(recorded_hash).casefold(),
                    canonical_tracked_sha256(expected_path).casefold(),
                )
            ):
                source_hashes_current = False
                break
    state["source_hashes_current"] = bool(source_hashes_current)

    gate_rows = register.get("gates")
    gates_by_id: dict[str, dict[str, Any]] = {}
    gate_rows_structural = isinstance(gate_rows, list)
    if gate_rows_structural:
        for row in gate_rows:
            if (
                not isinstance(row, dict)
                or set(row)
                != {
                    "gate_id",
                    "documentary_clear",
                    "private_boolean_can_clear_alone",
                    "required_source_roles",
                    "open_prerequisites",
                    "review_record",
                }
                or not isinstance(row.get("gate_id"), str)
                or row["gate_id"] in gates_by_id
            ):
                gate_rows_structural = False
                break
            gates_by_id[row["gate_id"]] = row
    state["gate_set_valid"] = bool(
        gate_rows_structural
        and set(gates_by_id) == set(CERTIFICATION_DOCUMENTARY_GATE_IDS)
    )

    gate_rows_valid = state["gate_set_valid"]
    if gate_rows_valid:
        for gate_id in sorted(CERTIFICATION_DOCUMENTARY_GATE_IDS):
            row = gates_by_id[gate_id]
            required_roles = row.get("required_source_roles")
            prerequisites = row.get("open_prerequisites")
            review = row.get("review_record")
            documentary_clear = row.get("documentary_clear")
            required_role_set = (
                {
                    value
                    for value in required_roles
                    if isinstance(value, str) and value
                }
                if isinstance(required_roles, list)
                else set()
            )
            prerequisites_valid = bool(
                isinstance(prerequisites, list)
                and all(isinstance(value, str) and value for value in prerequisites)
            )
            review_structural = bool(
                isinstance(review, dict)
                and set(review)
                == {
                    "status",
                    "required_authority",
                    "completed_utc",
                    "private_review_receipt_sha256",
                }
                and review.get("required_authority")
                == CERTIFICATION_DOCUMENTARY_REVIEW_AUTHORITIES[gate_id]
            )
            cleared_review = bool(
                review_structural
                and review.get("status") == "COMPLETE"
                and valid_timestamp(review.get("completed_utc"))
                and valid_sha256(review.get("private_review_receipt_sha256"))
            )
            open_review = bool(
                review_structural
                and review.get("status") == "OPEN"
                and review.get("completed_utc") is None
                and review.get("private_review_receipt_sha256") is None
            )
            row_valid = bool(
                isinstance(documentary_clear, bool)
                and row.get("private_boolean_can_clear_alone") is False
                and required_role_set
                == set(CERTIFICATION_DOCUMENTARY_GATE_SOURCE_ROLES[gate_id])
                and prerequisites_valid
                and (
                    (
                        documentary_clear is True
                        and prerequisites == []
                        and cleared_review
                    )
                    or (
                        documentary_clear is False
                        and bool(prerequisites)
                        and open_review
                    )
                )
            )
            if not row_valid:
                gate_rows_valid = False
                break
            gate_decisions[gate_id] = bool(
                documentary_clear
                and cleared_review
                and set(CERTIFICATION_DOCUMENTARY_GATE_SOURCE_ROLES[gate_id])
                .issubset(source_by_role)
            )
    state["gate_rows_valid"] = bool(gate_rows_valid)

    controls = register.get("controls")
    state["controls_valid"] = bool(
        isinstance(controls, dict)
        and controls
        == {
            "source_hash_match_required": True,
            "all_prerequisites_closed_required": True,
            "review_receipt_hash_required_to_clear": True,
            "private_boolean_can_clear_documentary_gate": False,
            "register_change_invalidates_portal_preview_binding": True,
            "register_change_invalidates_action_time_approval_binding": True,
            "legal_or_accounting_conclusion_automated": False,
        }
    )
    state["claim_boundary_present"] = bool(
        isinstance(register.get("claim_boundary"), str)
        and register["claim_boundary"].strip()
    )
    all_documentary_gates_clear = all(gate_decisions.values())
    expected_status = (
        "DOCUMENTARY_PREREQUISITES_CLEAR"
        if all_documentary_gates_clear
        else "DOCUMENTARY_PREREQUISITES_OPEN"
    )
    state["status"] = (
        register.get("status") if isinstance(register.get("status"), str) else None
    )
    status_valid = state["status"] == expected_status
    register_consumed = bool(
        state["register_regular_file"]
        and state["schema_valid"]
        and state["topic_valid"]
        and state["generated_timestamp_valid"]
        and state["integrity_valid"]
        and state["source_set_valid"]
        and state["source_hashes_current"]
        and state["gate_set_valid"]
        and state["gate_rows_valid"]
        and state["controls_valid"]
        and state["claim_boundary_present"]
        and status_valid
    )
    state["register_consumed"] = register_consumed
    state["gate_decisions"] = (
        gate_decisions
        if register_consumed
        else {gate_id: False for gate_id in sorted(gate_decisions)}
    )
    state["open_gate_ids"] = sorted(
        gate_id
        for gate_id, cleared in state["gate_decisions"].items()
        if not cleared
    )
    state["register_binding_sha256"] = (
        str(expected_hash).upper() if register_consumed else None
    )
    state["failure_code"] = (
        None if register_consumed else "CERTIFICATION_DOCUMENTARY_REGISTER_REJECTED"
    )
    return state


def certification_documentary_register_is_consumed(state: Any) -> bool:
    if not isinstance(state, dict):
        return False
    decisions = state.get("gate_decisions")
    return bool(
        state.get("register_present") is True
        and state.get("register_regular_file") is True
        and state.get("schema_valid") is True
        and state.get("topic_valid") is True
        and state.get("generated_timestamp_valid") is True
        and state.get("integrity_valid") is True
        and state.get("source_set_valid") is True
        and state.get("source_hashes_current") is True
        and state.get("gate_set_valid") is True
        and state.get("gate_rows_valid") is True
        and state.get("controls_valid") is True
        and state.get("claim_boundary_present") is True
        and state.get("register_consumed") is True
        and isinstance(decisions, dict)
        and set(decisions) == set(CERTIFICATION_DOCUMENTARY_GATE_IDS)
        and all(isinstance(value, bool) for value in decisions.values())
        and state.get("failure_code") is None
        and valid_sha256(state.get("register_binding_sha256"))
    )


def require_exact_keys(section: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(section, dict) or set(section) != expected:
        raise MissionWeaveGateError(code)
    return section


def require_compatible_keys(
    section: Any,
    required: set[str],
    optional: set[str],
    code: str,
) -> dict[str, Any]:
    if not isinstance(section, dict):
        raise MissionWeaveGateError(code)
    keys = set(section)
    if not required.issubset(keys) or keys.difference(required | optional):
        raise MissionWeaveGateError(code)
    return section


def run_pdf_tool(executable: str, arguments: list[str]) -> str:
    path = shutil.which(f"{executable}.exe") or shutil.which(executable)
    if not path:
        raise MissionWeaveGateError(f"{executable.upper()}_NOT_AVAILABLE")
    result = subprocess.run(
        [path, *arguments],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise MissionWeaveGateError(f"{executable.upper()}_FAILED")
    return result.stdout


def inspect_source_package(
    volume2_pdf: Path = VOLUME2_PDF,
    *,
    private_final: bool = False,
) -> tuple[dict[str, Any], str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest_header_ok = (
        manifest.get("schema") == "missionweave_dsip_submission_package_manifest.v1"
        and manifest.get("topic") == TOPIC
        and manifest.get("deadline") == EXPECTED_DEADLINE
        and manifest.get("file_count") == len(manifest.get("files", [])) == 15
    )
    file_checks = []
    for item in manifest.get("files", []):
        path = PACKAGE_DIR / str(item.get("path", ""))
        present = path.is_file()
        actual_bytes = path.stat().st_size if present else 0
        actual_sha256 = sha256_file(path) if present else None
        file_checks.append(
            {
                "path": str(item.get("path", "")),
                "present": present,
                "bytes_match": present and actual_bytes == item.get("bytes"),
                "sha256_match": present and actual_sha256 == item.get("sha256"),
            }
        )
    all_manifest_files_match = bool(file_checks) and all(
        row["present"] and row["bytes_match"] and row["sha256_match"]
        for row in file_checks
    )

    if private_final:
        selected_volume2 = validate_private_target(volume2_pdf)
        if not selected_volume2.is_file():
            raise MissionWeaveGateError("PRIVATE_FINAL_VOLUME2_NOT_FOUND")
        volume2_path_label = "IGNORED_PRIVATE_FINAL_VOLUME2"
    else:
        if volume2_pdf.is_symlink():
            raise MissionWeaveGateError("PUBLIC_VOLUME2_SYMLINK_REJECTED")
        selected_volume2 = volume2_pdf.resolve()
        if not path_is_within(selected_volume2, PACKAGE_DIR):
            raise MissionWeaveGateError("PUBLIC_VOLUME2_OUTSIDE_PACKAGE")
        if not selected_volume2.is_file():
            raise MissionWeaveGateError("PUBLIC_VOLUME2_NOT_FOUND")
        volume2_path_label = rel(selected_volume2)

    info_text = run_pdf_tool("pdfinfo", [str(selected_volume2)])
    pages_match = re.search(r"^Pages:\s+(\d+)\s*$", info_text, re.MULTILINE)
    encrypted_match = re.search(r"^Encrypted:\s+(\S+)\s*$", info_text, re.MULTILINE)
    size_match = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+) pts", info_text, re.MULTILINE)
    pages = int(pages_match.group(1)) if pages_match else 0
    encrypted = encrypted_match.group(1).lower() if encrypted_match else "unknown"
    letter_size = bool(
        size_match
        and abs(float(size_match.group(1)) - 612.0) < 0.5
        and abs(float(size_match.group(2)) - 792.0) < 0.5
    )
    volume2_text = run_pdf_tool("pdftotext", [str(selected_volume2), "-"])
    required_sections_present = all(
        heading in volume2_text for heading in REQUIRED_VOLUME2_SECTIONS
    )
    searchable = len(volume2_text.strip()) >= 10000
    candidate_format_pass = (
        1 <= pages <= VOLUME2_PAGE_LIMIT
        and encrypted == "no"
        and letter_size
        and searchable
        and required_sections_present
    )
    all_checks_pass = manifest_header_ok and all_manifest_files_match and candidate_format_pass
    public_state = {
        "manifest_path": rel(MANIFEST),
        "manifest_sha256": sha256_file(MANIFEST),
        "manifest_header_pass": manifest_header_ok,
        "manifest_file_count": len(file_checks),
        "all_manifest_files_match": all_manifest_files_match,
        "volume2_path": volume2_path_label,
        "volume2_sha256": sha256_file(selected_volume2),
        "volume2_sha256_present": True,
        "volume2_sha256_exposed": not private_final,
        "private_final_volume2_used": private_final,
        "private_final_volume2_sha256_exposed": False,
        "absolute_private_path_exposed": False,
        "volume2_pages": pages,
        "volume2_page_limit": VOLUME2_PAGE_LIMIT,
        "volume2_letter_size": letter_size,
        "volume2_encrypted": encrypted != "no",
        "volume2_searchable": searchable,
        "volume2_required_sections_present": required_sections_present,
        "neutral_proposal_header_present": NEUTRAL_PROPOSAL_HEADER in volume2_text,
        "candidate_format_pass": candidate_format_pass,
        "all_checks_pass": all_checks_pass,
        "files": file_checks,
    }
    return public_state, volume2_text


def required_private_gates() -> list[str]:
    return sorted(
        {
            *IDENTITY_GATES.values(),
            *PROPOSAL_FLAG_GATES.values(),
            *COMPLIANCE_GATES.values(),
            *APPROVAL_FLAG_GATES.values(),
            *SPECIAL_GATES,
        }
    )


def gate_reconciliation_groups(unresolved_gates: list[str]) -> dict[str, Any]:
    required = set(required_private_gates())
    classified: set[str] = set()
    for members in GATE_RECONCILIATION_GROUPS.values():
        if classified.intersection(members):
            raise MissionWeaveGateError("GATE_RECONCILIATION_GROUP_OVERLAP")
        classified.update(members)
    if classified != required:
        raise MissionWeaveGateError("GATE_RECONCILIATION_CLASSIFICATION_DRIFT")

    unresolved = set(unresolved_gates)
    unresolved_required = required.intersection(unresolved)
    groups: dict[str, Any] = {}
    for group_id, members in GATE_RECONCILIATION_GROUPS.items():
        gates = sorted(unresolved_required.intersection(members))
        if group_id == "A_DOCUMENTARY_RETRIEVAL" and "OFFICIAL_SOURCE_INTEGRITY" in unresolved:
            gates = ["OFFICIAL_SOURCE_INTEGRITY", *gates]
        groups[group_id] = {
            "status": "OPEN" if gates else "CLEAR",
            "count": len(gates),
            "gates": gates,
        }

    cleared = sorted(required.difference(unresolved_required))
    groups["F_CLEARED_BY_EVIDENCE"] = {
        "status": "CLEARED",
        "count": len(cleared),
        "gates": cleared,
    }
    return groups


def gate_lifecycle_stages(unresolved_gates: list[str]) -> dict[str, Any]:
    required = set(required_private_gates())
    action_time = set(LIFECYCLE_ACTION_TIME_GATES)
    pre_award = set(LIFECYCLE_PRE_AWARD_OR_NEGOTIATION_GATES)
    if action_time.intersection(pre_award):
        raise MissionWeaveGateError("GATE_LIFECYCLE_STAGE_OVERLAP")
    if not action_time.union(pre_award).issubset(required):
        raise MissionWeaveGateError("GATE_LIFECYCLE_CLASSIFICATION_DRIFT")

    pre_submit = required.difference(action_time).difference(pre_award)
    stage_definitions = (
        (
            "A_PRE_SUBMISSION_CONTENT_AND_EVIDENCE",
            pre_submit,
            (
                "Evidence, content, registration, and portal facts required before the "
                "bounded final-submission gate can open."
            ),
            "RESOLVE_BEFORE_FINAL_SUBMISSION",
        ),
        (
            "B_PRE_AWARD_OR_CONTRACT_NEGOTIATION_READINESS",
            pre_award,
            (
                "The proposal must state a current bounded position. Implementation proof "
                "may occur during pre-award or contract negotiation only if the live portal "
                "or contracting office permits it; these gates remain fail-closed now."
            ),
            "REVIEW_AND_BOUND_POSITION_BEFORE_SUBMISSION",
        ),
        (
            "C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN",
            action_time,
            (
                "Fresh preview, corporate review, and final authorization occur only after "
                "the upload set is stable and immediately before the human submit action."
            ),
            "ACTION_TIME_HUMAN_ONLY",
        ),
    )

    classified: set[str] = set()
    for _, members, _, _ in stage_definitions:
        if classified.intersection(members):
            raise MissionWeaveGateError("GATE_LIFECYCLE_STAGE_OVERLAP")
        classified.update(members)
    if classified != required:
        raise MissionWeaveGateError("GATE_LIFECYCLE_CLASSIFICATION_DRIFT")

    unresolved = set(unresolved_gates)
    allowed_unresolved = required.union({"OFFICIAL_SOURCE_INTEGRITY"})
    unknown = sorted(unresolved.difference(allowed_unresolved))
    if unknown:
        raise MissionWeaveGateError("GATE_LIFECYCLE_UNKNOWN_OPEN_GATE")

    stages: dict[str, Any] = {}
    classified_open: list[str] = []
    for stage_id, members, description, submission_effect in stage_definitions:
        open_gates = sorted(unresolved.intersection(members))
        if (
            stage_id == "A_PRE_SUBMISSION_CONTENT_AND_EVIDENCE"
            and "OFFICIAL_SOURCE_INTEGRITY" in unresolved
        ):
            open_gates = ["OFFICIAL_SOURCE_INTEGRITY", *open_gates]
        classified_open.extend(open_gates)
        stages[stage_id] = {
            "status": "OPEN" if open_gates else "CLEAR",
            "open_gate_count": len(open_gates),
            "open_gates": open_gates,
            "all_required_gate_count": len(members),
            "description": description,
            "submission_effect": submission_effect,
        }

    if len(classified_open) != len(set(classified_open)):
        raise MissionWeaveGateError("GATE_LIFECYCLE_OPEN_GATE_DUPLICATED")
    if set(classified_open) != unresolved:
        raise MissionWeaveGateError("GATE_LIFECYCLE_OPEN_GATE_COVERAGE_DRIFT")

    return {
        "classification_version": "missionweave.gate_lifecycle.v1",
        "submission_readiness_logic_unchanged": True,
        "classification_can_clear_gate": False,
        "all_open_gates_classified_once": True,
        "live_portal_or_contracting_office_confirmation_required": True,
        "stages": stages,
    }


def founder_action_sequence(unresolved_gates: list[str]) -> dict[str, Any]:
    unresolved = set(unresolved_gates)
    assigned: set[str] = set()
    ordered_steps: list[dict[str, Any]] = []

    for definition in FOUNDER_ACTION_DEFINITIONS:
        defined_gates = set(definition["gate_ids"])
        overlap = assigned.intersection(defined_gates)
        if overlap:
            raise MissionWeaveGateError("FOUNDER_ACTION_GATE_OVERLAP")
        open_gates = sorted(unresolved.intersection(defined_gates))
        assigned.update(defined_gates)
        if not open_gates:
            continue
        ordered_steps.append(
            {
                "step_id": definition["step_id"],
                "title": definition["title"],
                "status": "OPEN",
                "open_gate_count": len(open_gates),
                "open_gates": open_gates,
                "instruction": definition["instruction"],
                "evidence_required": definition["evidence_required"],
                "human_boundary": definition["human_boundary"],
            }
        )

    residual = sorted(unresolved.difference(assigned))
    if residual:
        ordered_steps.insert(
            0,
            {
                "step_id": "00_OTHER_PRE_SUBMISSION_GATES",
                "title": "Resolve remaining registration, content, and evidence gates",
                "status": "OPEN",
                "open_gate_count": len(residual),
                "open_gates": residual,
                "instruction": (
                    "Resolve each listed gate from current documentary evidence or the live "
                    "portal. Preserve unknown facts as open; do not infer completion."
                ),
                "evidence_required": "Current source, artifact, or authenticated portal evidence",
                "human_boundary": (
                    "Credentials, legal representations, certifications, and final actions remain human controlled."
                ),
            },
        )

    sequenced = [
        gate
        for step in ordered_steps
        for gate in step["open_gates"]
    ]
    if len(sequenced) != len(set(sequenced)):
        raise MissionWeaveGateError("FOUNDER_ACTION_OPEN_GATE_DUPLICATED")
    if set(sequenced) != unresolved:
        raise MissionWeaveGateError("FOUNDER_ACTION_OPEN_GATE_COVERAGE_DRIFT")

    return {
        "sequence_version": "missionweave.founder_action_sequence.v1",
        "open_step_count": len(ordered_steps),
        "all_open_gates_covered_once": True,
        "classification_can_clear_gate": False,
        "final_submission_human_only": True,
        "ordered_steps": ordered_steps,
    }


def current_upload_set_identity_sha256(
    payload: dict[str, Any],
    *,
    jcp_evidence_state: dict[str, Any],
    volume3_artifact_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
    documentary_register_state: dict[str, Any] | None = None,
) -> str:
    if documentary_register_state is None:
        documentary_register_state = inspect_certification_documentary_register()
    identity = payload.get("identity")
    proposal = payload.get("proposal")
    compliance = payload.get("eligibility_and_compliance")
    identity = identity if isinstance(identity, dict) else {}
    proposal = proposal if isinstance(proposal, dict) else {}
    compliance = compliance if isinstance(compliance, dict) else {}
    context = {
        "schema": ACTION_CONTEXT_SCHEMA,
        "topic": payload.get("topic"),
        "identity_gate_state": {
            field: identity.get(field) for field in sorted(IDENTITY_GATES)
        },
        "proposal_upload_state": {
            field: proposal.get(field)
            for field in sorted(
                (set(PROPOSAL_FLAG_GATES) - {"portal_preview_reviewed"})
                | (PROPOSAL_VALUE_KEYS - {"portal_preview_sha256"})
            )
        },
        "compliance_gate_state": {
            field: compliance.get(field)
            for field in sorted(set(COMPLIANCE_GATES) | {"itar_scope_determination"})
        },
        "jcp_evidence_binding_sha256": (
            jcp_evidence_state.get("evidence_binding_sha256")
            if jcp_evidence_is_verified(jcp_evidence_state)
            else None
        ),
        "volume3_artifact_binding_sha256": (
            volume3_artifact_state.get("artifact_binding_sha256")
            if volume3_artifact_is_verified(volume3_artifact_state)
            else None
        ),
        "cmmc_packet_binding_sha256": (
            cmmc_packet_state.get("packet_binding_sha256")
            if cmmc_packet_is_consumed(cmmc_packet_state)
            else None
        ),
        "certification_documentary_register_binding_sha256": (
            documentary_register_state.get("register_binding_sha256")
            if certification_documentary_register_is_consumed(
                documentary_register_state
            )
            else None
        ),
    }
    return stable_sha256(context).upper()


def preview_evidence_binding_sha256(
    payload: dict[str, Any],
    *,
    jcp_evidence_state: dict[str, Any],
    volume3_artifact_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
    documentary_register_state: dict[str, Any] | None = None,
) -> str | None:
    proposal = payload.get("proposal")
    if not isinstance(proposal, dict):
        return None
    preview_sha256 = proposal.get("portal_preview_sha256")
    captured_utc = proposal.get("portal_preview_captured_utc")
    if not valid_sha256(preview_sha256) or not valid_timestamp(captured_utc):
        return None
    binding = {
        "schema": PREVIEW_EVIDENCE_BINDING_SCHEMA,
        "topic": payload.get("topic"),
        "portal_preview_sha256": str(preview_sha256).upper(),
        "portal_preview_captured_utc": captured_utc,
        "upload_set_identity_sha256": current_upload_set_identity_sha256(
            payload,
            jcp_evidence_state=jcp_evidence_state,
            volume3_artifact_state=volume3_artifact_state,
            cmmc_packet_state=cmmc_packet_state,
            documentary_register_state=documentary_register_state,
        ),
    }
    return stable_sha256(binding).upper()


def action_time_approval_binding_sha256(
    payload: dict[str, Any],
    *,
    approval_utc: Any,
    jcp_evidence_state: dict[str, Any],
    volume3_artifact_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
    documentary_register_state: dict[str, Any] | None = None,
) -> str | None:
    if not valid_timestamp(approval_utc):
        return None
    approval = payload.get("approval")
    approval = approval if isinstance(approval, dict) else {}
    binding = {
        "schema": ACTION_APPROVAL_BINDING_SCHEMA,
        "topic": payload.get("topic"),
        "approval_utc": approval_utc,
        "approval_gate_state": {
            field: approval.get(field) for field in sorted(APPROVAL_FLAG_GATES)
        },
        "preview_evidence_binding_sha256": preview_evidence_binding_sha256(
            payload,
            jcp_evidence_state=jcp_evidence_state,
            volume3_artifact_state=volume3_artifact_state,
            cmmc_packet_state=cmmc_packet_state,
            documentary_register_state=documentary_register_state,
        ),
        "upload_set_identity_sha256": current_upload_set_identity_sha256(
            payload,
            jcp_evidence_state=jcp_evidence_state,
            volume3_artifact_state=volume3_artifact_state,
            cmmc_packet_state=cmmc_packet_state,
            documentary_register_state=documentary_register_state,
        ),
    }
    return stable_sha256(binding).upper()


def evaluate_private_payload(
    payload: dict[str, Any],
    *,
    source_state: dict[str, Any],
    volume2_text: str,
    volume3_artifact_state: dict[str, Any] | None = None,
    jcp_evidence_state: dict[str, Any] | None = None,
    cmmc_packet_state: dict[str, Any] | None = None,
    documentary_register_state: dict[str, Any] | None = None,
    evaluated_utc: datetime | str | None = None,
) -> dict[str, Any]:
    if payload.get("schema") != PRIVATE_SCHEMA:
        raise MissionWeaveGateError("PRIVATE_SCHEMA_MISMATCH")
    if payload.get("topic") != TOPIC:
        raise MissionWeaveGateError("TOPIC_MISMATCH")
    if payload.get("template_only") is True:
        raise MissionWeaveGateError("TEMPLATE_CANNOT_BE_USED_AS_PRIVATE_INPUT")
    allowed_top = {
        "schema",
        "topic",
        "template_only",
        "captured_utc",
        "identity",
        "proposal",
        "eligibility_and_compliance",
        "approval",
    }
    if set(payload) != allowed_top:
        raise MissionWeaveGateError("PRIVATE_TOP_LEVEL_SCHEMA_DRIFT")

    identity = require_exact_keys(
        payload.get("identity"), set(IDENTITY_GATES), "IDENTITY_SCHEMA_DRIFT"
    )
    proposal = require_compatible_keys(
        payload.get("proposal"),
        set(PROPOSAL_FLAG_GATES) | PROPOSAL_VALUE_KEYS,
        PROPOSAL_CONSISTENCY_KEYS,
        "PROPOSAL_SCHEMA_DRIFT",
    )
    compliance = require_exact_keys(
        payload.get("eligibility_and_compliance"),
        set(COMPLIANCE_GATES) | {"itar_scope_determination"},
        "COMPLIANCE_SCHEMA_DRIFT",
    )
    approval = require_compatible_keys(
        payload.get("approval"),
        set(APPROVAL_FLAG_GATES) | APPROVAL_VALUE_KEYS,
        APPROVAL_CONSISTENCY_KEYS,
        "APPROVAL_SCHEMA_DRIFT",
    )

    reference_utc = normalize_reference_time(evaluated_utc)
    gate_state: dict[str, bool] = {}
    for field, gate in IDENTITY_GATES.items():
        gate_state[gate] = identity.get(field) is True
    for field, gate in PROPOSAL_FLAG_GATES.items():
        gate_state[gate] = proposal.get(field) is True
    for field, gate in COMPLIANCE_GATES.items():
        gate_state[gate] = compliance.get(field) is True
    for field, gate in APPROVAL_FLAG_GATES.items():
        gate_state[gate] = approval.get(field) is True

    if volume3_artifact_state is None:
        volume3_artifact_state = inspect_private_volume3_artifact()
    if jcp_evidence_state is None:
        jcp_evidence_state = inspect_private_jcp_evidence()
    if cmmc_packet_state is None:
        cmmc_packet_state = inspect_cmmc_evidence_packet()
    if documentary_register_state is None:
        documentary_register_state = inspect_certification_documentary_register()
    jcp_evidence_verified = jcp_evidence_is_verified(jcp_evidence_state)
    gate_state["DD2345_OR_JCP_APPLICATION_EVIDENCE"] = bool(
        compliance.get("dd2345_or_jcp_application_evidence_ready") is True
        and jcp_evidence_verified
    )
    cmmc_packet_consumed = cmmc_packet_is_consumed(cmmc_packet_state)
    gate_state["CURRENT_CMMC_REQUIREMENTS_REVIEW"] = bool(
        compliance.get("current_cmmc_requirements_reviewed") is True
        and cmmc_packet_consumed
        and cmmc_packet_state.get("requirements_review_basis_present") is True
    )
    gate_state["CMMC_PHASE_I_SELF_ASSESSMENT_POSITION"] = bool(
        compliance.get("cmmc_phase_i_self_assessment_position_supported") is True
        and cmmc_packet_consumed
        and cmmc_packet_state.get("phase_i_position_supported") is True
    )
    gate_state["NO_CMMC_STATUS_OVERCLAIM"] = bool(
        compliance.get("no_cmmc_status_overclaim") is True
        and cmmc_packet_consumed
        and cmmc_packet_state.get("overclaim_boundary_present") is True
    )
    documentary_register_consumed = certification_documentary_register_is_consumed(
        documentary_register_state
    )
    documentary_gate_decisions = (
        documentary_register_state.get("gate_decisions", {})
        if documentary_register_consumed
        else {}
    )
    gate_state["NO_DUPLICATE_COST_OR_DELIVERABLE"] = bool(
        compliance.get("no_duplicate_cost_or_deliverable") is True
        and documentary_gate_decisions.get("NO_DUPLICATE_COST_OR_DELIVERABLE")
        is True
    )
    gate_state["TECHNICAL_DATA_RIGHTS_ASSERTION"] = bool(
        compliance.get("technical_data_rights_assertion_supported") is True
        and documentary_gate_decisions.get("TECHNICAL_DATA_RIGHTS_ASSERTION") is True
    )

    proposal_number = proposal.get("proposal_number")
    proposal_number_present = valid_proposal_number(proposal_number)
    proposal_number_embedded = bool(
        proposal_number_present
        and str(proposal_number).strip() in volume2_text
        and NEUTRAL_PROPOSAL_HEADER not in volume2_text
    )
    pdf_hash_match = bool(
        valid_sha256(proposal.get("volume2_pdf_sha256"))
        and str(proposal["volume2_pdf_sha256"]).upper()
        == str(source_state["volume2_sha256"]).upper()
    )
    cost_total = parse_phase_i_total(proposal.get("volume3_total_usd"))
    cost_total_matches = cost_total == PHASE_I_CEILING
    preview_receipt_present = valid_sha256(proposal.get("portal_preview_sha256"))
    preview_receipt_timestamp_present = valid_timestamp(
        proposal.get("portal_preview_captured_utc")
    )
    preview_receipt_fresh = bool(
        preview_receipt_present
        and timestamp_is_fresh(
            proposal.get("portal_preview_captured_utc"),
            reference_utc=reference_utc,
            max_age=PREVIEW_RECEIPT_MAX_AGE,
        )
    )
    recorded_preview_binding = proposal.get("portal_preview_binding_sha256")
    preview_binding_present = valid_sha256(recorded_preview_binding)
    expected_preview_binding = preview_evidence_binding_sha256(
        payload,
        jcp_evidence_state=jcp_evidence_state,
        volume3_artifact_state=volume3_artifact_state,
        cmmc_packet_state=cmmc_packet_state,
        documentary_register_state=documentary_register_state,
    )
    preview_binding_matches = bool(
        expected_preview_binding is not None
        and preview_binding_present
        and hmac.compare_digest(
            str(recorded_preview_binding).upper(), expected_preview_binding
        )
    )
    preview_evidence_current = bool(
        preview_receipt_fresh and preview_binding_matches
    )
    approval_timestamp_present = valid_timestamp(approval.get("approval_utc"))
    approval_timestamp_fresh = timestamp_is_fresh(
        approval.get("approval_utc"),
        reference_utc=reference_utc,
        max_age=ACTION_TIME_APPROVAL_MAX_AGE,
    )
    preview_timestamp = parse_timestamp(proposal.get("portal_preview_captured_utc"))
    approval_timestamp = parse_timestamp(approval.get("approval_utc"))
    approval_not_before_preview = bool(
        preview_timestamp is not None
        and approval_timestamp is not None
        and approval_timestamp >= preview_timestamp
    )
    expected_approval_binding = action_time_approval_binding_sha256(
        payload,
        approval_utc=approval.get("approval_utc"),
        jcp_evidence_state=jcp_evidence_state,
        volume3_artifact_state=volume3_artifact_state,
        cmmc_packet_state=cmmc_packet_state,
        documentary_register_state=documentary_register_state,
    )
    recorded_approval_binding = approval.get("approval_binding_sha256")
    approval_binding_matches = bool(
        expected_approval_binding is not None
        and valid_sha256(recorded_approval_binding)
        and hmac.compare_digest(
            str(recorded_approval_binding).upper(), expected_approval_binding
        )
    )
    approval_context_current = bool(
        preview_evidence_current
        and approval_timestamp_fresh
        and approval_not_before_preview
        and approval_binding_matches
    )
    gate_state["COMPLETE_PORTAL_PREVIEW_REVIEW"] = bool(
        proposal.get("portal_preview_reviewed") is True and preview_evidence_current
    )
    gate_state["CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW"] = bool(
        approval.get("corporate_official_reviewed_all_volumes") is True
        and approval_context_current
    )
    gate_state["ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION"] = bool(
        approval.get("final_submission_authorized_at_action_time") is True
        and approval_context_current
    )
    itar_scope_confirmed = compliance.get("itar_scope_determination") == "SUBJECT_TO_ITAR"

    gate_state.update(
        {
            "PRIVATE_INPUT_TIMESTAMP": valid_timestamp(payload.get("captured_utc")),
            "ASSIGNED_PROPOSAL_NUMBER_CAPTURE": proposal_number_present,
            "VOLUME2_PDF_HASH_MATCH": pdf_hash_match,
            "VOLUME2_ASSIGNED_PROPOSAL_NUMBER_EMBEDDED": proposal_number_embedded,
            "VOLUME3_TOTAL_MATCHES_PHASE_I_CEILING": cost_total_matches,
            "PORTAL_PREVIEW_RECEIPT_HASH": preview_evidence_current,
            "ITAR_SCOPE_CONFIRMED": itar_scope_confirmed,
            "ACTION_TIME_APPROVAL_TIMESTAMP": approval_context_current,
        }
    )
    unresolved = sorted(gate for gate, passed in gate_state.items() if not passed)
    return {
        "required_gate_count": len(gate_state),
        "passed_gate_count": sum(gate_state.values()),
        "open_gate_count": len(unresolved),
        "unresolved_gates": unresolved,
        "all_private_gates_pass": not unresolved,
        "proposal_number_present": proposal_number_present,
        "proposal_number_embedded": proposal_number_embedded,
        "volume2_pdf_hash_match": pdf_hash_match,
        "volume3_total_matches_official_ceiling": cost_total_matches,
        "portal_preview_receipt_present": preview_receipt_present,
        "portal_preview_receipt_timestamp_present": preview_receipt_timestamp_present,
        "portal_preview_receipt_fresh": preview_receipt_fresh,
        "portal_preview_binding_present": preview_binding_present,
        "portal_preview_binding_matches_current_upload_set": preview_binding_matches,
        "portal_preview_evidence_current": preview_evidence_current,
        "corporate_official_reviewed": gate_state[
            "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW"
        ],
        "action_time_authorized": gate_state[
            "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION"
        ],
        "approval_timestamp_present": approval_timestamp_present,
        "approval_timestamp_fresh": approval_timestamp_fresh,
        "approval_not_before_preview": approval_not_before_preview,
        "approval_binding_matches_current_upload_set": approval_binding_matches,
        "dd2345_or_jcp_evidence_verified": gate_state[
            "DD2345_OR_JCP_APPLICATION_EVIDENCE"
        ],
        "cmmc_packet_consumed": cmmc_packet_consumed,
        "cmmc_phase_i_position_supported": bool(
            cmmc_packet_consumed
            and cmmc_packet_state.get("phase_i_position_supported") is True
        ),
        "certification_documentary_register_consumed": (
            documentary_register_consumed
        ),
        "no_duplicate_cost_documentary_clear": bool(
            documentary_gate_decisions.get("NO_DUPLICATE_COST_OR_DELIVERABLE")
            is True
        ),
        "technical_data_rights_documentary_clear": bool(
            documentary_gate_decisions.get("TECHNICAL_DATA_RIGHTS_ASSERTION") is True
        ),
    }


def build_payload(
    private_payload: dict[str, Any] | None = None,
    *,
    private_input_sha256: str | None = None,
    source_state: dict[str, Any] | None = None,
    volume2_text: str | None = None,
    volume3_artifact_state: dict[str, Any] | None = None,
    jcp_evidence_state: dict[str, Any] | None = None,
    cmmc_packet_state: dict[str, Any] | None = None,
    documentary_register_state: dict[str, Any] | None = None,
    evaluated_utc: datetime | str | None = None,
) -> dict[str, Any]:
    reference_utc = normalize_reference_time(evaluated_utc)
    if source_state is None or volume2_text is None:
        use_private_final = bool(
            private_payload is not None and PRIVATE_FINAL_VOLUME2_PDF.is_file()
        )
        source_state, volume2_text = inspect_source_package(
            PRIVATE_FINAL_VOLUME2_PDF if use_private_final else VOLUME2_PDF,
            private_final=use_private_final,
        )
    if volume3_artifact_state is None:
        volume3_artifact_state = inspect_private_volume3_artifact()
    if jcp_evidence_state is None:
        jcp_evidence_state = inspect_private_jcp_evidence()
    if cmmc_packet_state is None:
        cmmc_packet_state = inspect_cmmc_evidence_packet()
    if documentary_register_state is None:
        documentary_register_state = inspect_certification_documentary_register()
    evaluation = (
        evaluate_private_payload(
            private_payload,
            source_state=source_state,
            volume2_text=volume2_text,
            volume3_artifact_state=volume3_artifact_state,
            jcp_evidence_state=jcp_evidence_state,
            cmmc_packet_state=cmmc_packet_state,
            documentary_register_state=documentary_register_state,
            evaluated_utc=reference_utc,
        )
        if private_payload is not None
        else None
    )
    unresolved = (
        evaluation["unresolved_gates"]
        if evaluation is not None
        else required_private_gates()
    )
    if not source_state["all_checks_pass"]:
        unresolved = sorted({"OFFICIAL_SOURCE_INTEGRITY", *unresolved})
        status = "OFFICIAL_SOURCE_OR_PACKAGE_INTEGRITY_FAILED"
    elif evaluation is None:
        status = "PRIVATE_DSIP_FACTS_NOT_CAPTURED"
    elif evaluation["all_private_gates_pass"]:
        status = "READY_FOR_HUMAN_FINAL_SUBMIT_CLICK"
    else:
        status = "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    ready = bool(
        source_state["all_checks_pass"]
        and evaluation is not None
        and evaluation["all_private_gates_pass"]
    )
    public_source_state = deepcopy(source_state)
    if public_source_state.get("private_final_volume2_used") is True:
        public_source_state["volume2_sha256"] = None
        public_source_state["volume2_sha256_present"] = valid_sha256(
            source_state.get("volume2_sha256")
        )
        public_source_state["volume2_sha256_exposed"] = False
        public_source_state["volume2_path"] = "IGNORED_PRIVATE_FINAL_VOLUME2"
        public_source_state["private_final_volume2_sha256_exposed"] = False
        public_source_state["absolute_private_path_exposed"] = False

    reconciliation_groups = gate_reconciliation_groups(unresolved)
    lifecycle_stages = gate_lifecycle_stages(unresolved)
    action_sequence = founder_action_sequence(unresolved)
    public_volume3_artifact_state = {
        key: volume3_artifact_state.get(key)
        for key in (
            "receipt_present",
            "workbook_present",
            "receipt_header_valid",
            "workbook_size_matches_receipt",
            "workbook_hash_matches_receipt",
            "workbook_ooxml_valid",
            "workbook_structure_valid",
            "workbook_sheet_names_match_receipt",
            "workbook_formula_count",
            "workbook_formula_error_count",
            "workbook_error_cell_count",
            "workbook_financials_derived_from_contents",
            "workbook_content_failure_code",
            "formula_scan_clean",
            "export_reimport_verified",
            "financial_reconciliation_pass",
            "review_guardrails_preserved",
            "receipt_integrity_pass",
            "private_path_exposed",
            "private_hash_exposed",
        )
    }
    public_jcp_evidence_state = {
        key: jcp_evidence_state.get(key)
        for key in (
            "receipt_present",
            "receipt_header_valid",
            "evidence_file_present",
            "evidence_pdf",
            "evidence_hash_matches_receipt",
            "source_metadata_valid",
            "entity_match_confirmed",
            "corporate_official_reviewed",
            "evidence_integrity_pass",
            "evidence_kind",
            "failure_code",
            "private_path_exposed",
            "private_hash_exposed",
        )
    }
    public_cmmc_packet_state = {
        key: cmmc_packet_state.get(key)
        for key in (
            "packet_present",
            "packet_regular_file",
            "schema_valid",
            "integrity_valid",
            "generated_timestamp_valid",
            "missionweave_program_unique",
            "cmmc_requirement_unique",
            "requirement_source_policy_valid",
            "packet_consumed",
            "packet_state",
            "requirement_evidence_state",
            "requirements_review_basis_present",
            "phase_i_position_supported",
            "overclaim_boundary_present",
            "failure_code",
        )
    }
    public_documentary_register_state = {
        key: documentary_register_state.get(key)
        for key in (
            "register_present",
            "register_regular_file",
            "schema_valid",
            "topic_valid",
            "generated_timestamp_valid",
            "integrity_valid",
            "source_set_valid",
            "source_hashes_current",
            "gate_set_valid",
            "gate_rows_valid",
            "controls_valid",
            "claim_boundary_present",
            "register_consumed",
            "status",
            "gate_decisions",
            "open_gate_ids",
            "failure_code",
        )
    }

    payload: dict[str, Any] = {
        "schema": PUBLIC_SCHEMA,
        "generated_utc": reference_utc.isoformat(),
        "topic": TOPIC,
        "deadline": {
            "expected_utc": "2026-07-22T16:00:00Z",
            "expected_local": "July 22, 2026 at 12:00 p.m. Eastern Time",
            "live_dsip_recheck_required": True,
            "source_discrepancy": (
                "The Amendment 2 BAA schedule line prints July 22, 2025; the 2026 "
                "SBIR topic record, DLA Release 3 schedule, and package sources agree "
                "on July 22, 2026."
            ),
        },
        "status": status,
        "submission_ready_for_human_click": ready,
        "source_integrity": public_source_state,
        "private_input": {
            "expected_path": rel(DEFAULT_PRIVATE_INPUT),
            "git_ignored_target": git_ignored(DEFAULT_PRIVATE_INPUT),
            "present": private_payload is not None,
            "sha256": None,
            "sha256_present": valid_sha256(private_input_sha256),
            "sha256_exposed": False,
            "private_values_exposed": False,
            "capture_tool": rel(PRIVATE_CAPTURE_TOOL),
            "private_volume2_finalizer": rel(PRIVATE_FINALIZER),
            "private_final_volume2_present": bool(
                private_payload is not None and PRIVATE_FINAL_VOLUME2_PDF.is_file()
            ),
            "private_final_volume2_path_exposed": False,
            "private_final_volume2_sha256_exposed": False,
            "capture_workflow": rel(PRIVATE_CAPTURE_WORKFLOW),
            "jcp_evidence_receipt_expected_path": rel(
                PRIVATE_JCP_EVIDENCE_RECEIPT
            ),
            "jcp_evidence_template": rel(PRIVATE_JCP_EVIDENCE_TEMPLATE),
            "pre_submit_excludes_action_time_approval": True,
            "manual_preview_hash_can_establish_freshness": False,
            "preview_binding_stored_privately": True,
            "approval_binding_stored_privately": True,
            "credential_values_accepted": False,
            "firm_pin_value_accepted": False,
        },
        "gate_summary": {
            "required_private_gate_count": (
                evaluation["required_gate_count"]
                if evaluation is not None
                else len(required_private_gates())
            ),
            "passed_private_gate_count": (
                evaluation["passed_gate_count"] if evaluation is not None else 0
            ),
            "open_gate_count": len(unresolved),
            "unresolved_gates": unresolved,
            "reconciliation_groups": reconciliation_groups,
        },
        "gate_lifecycle": lifecycle_stages,
        "founder_action_sequence": action_sequence,
        "private_fact_state": {
            "assigned_proposal_number_present": bool(
                evaluation and evaluation["proposal_number_present"]
            ),
            "assigned_proposal_number_value_exposed": False,
            "assigned_proposal_number_embedded_in_volume2": bool(
                evaluation and evaluation["proposal_number_embedded"]
            ),
            "volume2_pdf_hash_matches_private_record": bool(
                evaluation and evaluation["volume2_pdf_hash_match"]
            ),
            "volume3_total_matches_official_ceiling": bool(
                evaluation and evaluation["volume3_total_matches_official_ceiling"]
            ),
            "volume3_private_amount_exposed": False,
            "portal_preview_receipt_present": bool(
                evaluation and evaluation["portal_preview_receipt_present"]
            ),
            "portal_preview_receipt_timestamp_present": bool(
                evaluation
                and evaluation["portal_preview_receipt_timestamp_present"]
            ),
            "portal_preview_receipt_fresh": bool(
                evaluation and evaluation["portal_preview_receipt_fresh"]
            ),
            "portal_preview_binding_present": bool(
                evaluation and evaluation["portal_preview_binding_present"]
            ),
            "portal_preview_binding_matches_current_upload_set": bool(
                evaluation
                and evaluation[
                    "portal_preview_binding_matches_current_upload_set"
                ]
            ),
            "portal_preview_evidence_current": bool(
                evaluation and evaluation["portal_preview_evidence_current"]
            ),
            "portal_preview_receipt_value_exposed": False,
            "portal_preview_binding_value_exposed": False,
            "corporate_official_reviewed": bool(
                evaluation and evaluation["corporate_official_reviewed"]
            ),
            "action_time_authorized": bool(
                evaluation and evaluation["action_time_authorized"]
            ),
            "approval_timestamp_present": bool(
                evaluation and evaluation["approval_timestamp_present"]
            ),
            "approval_timestamp_fresh": bool(
                evaluation and evaluation["approval_timestamp_fresh"]
            ),
            "approval_not_before_preview": bool(
                evaluation and evaluation["approval_not_before_preview"]
            ),
            "approval_binding_matches_current_upload_set": bool(
                evaluation
                and evaluation["approval_binding_matches_current_upload_set"]
            ),
            "approval_binding_value_exposed": False,
            "dd2345_or_jcp_evidence_verified": bool(
                evaluation and evaluation["dd2345_or_jcp_evidence_verified"]
            ),
            "cmmc_packet_consumed": bool(
                evaluation and evaluation["cmmc_packet_consumed"]
            ),
            "cmmc_phase_i_position_supported": bool(
                evaluation and evaluation["cmmc_phase_i_position_supported"]
            ),
            "certification_documentary_register_consumed": bool(
                evaluation
                and evaluation["certification_documentary_register_consumed"]
            ),
            "no_duplicate_cost_documentary_clear": bool(
                evaluation and evaluation["no_duplicate_cost_documentary_clear"]
            ),
            "technical_data_rights_documentary_clear": bool(
                evaluation
                and evaluation["technical_data_rights_documentary_clear"]
            ),
        },
        "private_volume3_artifact": public_volume3_artifact_state,
        "private_jcp_evidence": public_jcp_evidence_state,
        "cmmc_evidence_packet": {
            "path": rel(CMMC_EVIDENCE_PACKET),
            "file_sha256": (
                sha256_file(CMMC_EVIDENCE_PACKET)
                if CMMC_EVIDENCE_PACKET.is_file()
                and not CMMC_EVIDENCE_PACKET.is_symlink()
                else None
            ),
            **public_cmmc_packet_state,
        },
        "certification_documentary_register": {
            "path": rel(CERTIFICATION_DOCUMENTARY_REGISTER),
            "file_sha256": (
                sha256_file(CERTIFICATION_DOCUMENTARY_REGISTER)
                if CERTIFICATION_DOCUMENTARY_REGISTER.is_file()
                and not CERTIFICATION_DOCUMENTARY_REGISTER.is_symlink()
                else None
            ),
            **public_documentary_register_state,
        },
        "jcp_evidence_protocol": {
            "path": rel(JCP_EVIDENCE_PROTOCOL),
            "bytes": JCP_EVIDENCE_PROTOCOL.stat().st_size,
            "sha256": sha256_file(JCP_EVIDENCE_PROTOCOL),
            "bare_boolean_can_clear_gate": False,
        },
        "official_instruction_facts": {
            "dsip_volume_count": 7,
            "volume2_page_limit": VOLUME2_PAGE_LIMIT,
            "phase_i_base_ceiling_usd": 100000,
            "phase_i_max_duration_months": 12,
            "current_package_duration_months": 6,
            "topic_itar_flag": True,
            "dd2345_or_jcp_application_evidence_required_if_effort_subject_to_itar": True,
            "dd2345_or_jcp_gate_requires_hash_matched_private_portal_evidence": True,
            "projected_cmmc_level": "Level 2 (Self)",
            "cmmc_amendment_note": (
                "Amendment 2 says CMMC Phase II implementation was suspended on July "
                "13, 2026 while Phase I self-assessment requirements remain in place; "
                "the current live requirement must be reviewed before submission."
            ),
            "volume6_fwa_training_required_annually": True,
            "volume7_is_webform_not_volume5_pdf": True,
            "taba_requested": False,
        },
        "controls": {
            "browser_navigation_performed": False,
            "external_send_performed": False,
            "portal_submit_performed": False,
            "builder_can_click_final_submit": False,
            "action_time_human_required": True,
            "credentials_allowed_in_public_output": False,
            "private_identifiers_allowed_in_public_output": False,
            "bare_jcp_checkbox_can_clear_gate": False,
            "jcp_receipt_fields_required_to_clear_gate": True,
            "cmmc_boolean_can_clear_supported_position_gate": False,
            "cmmc_packet_integrity_required": True,
            "private_boolean_can_clear_documentary_gate": False,
            "documentary_register_integrity_required": True,
            "documentary_review_receipt_hash_required_to_clear": True,
            "preview_receipt_max_age_seconds": int(
                PREVIEW_RECEIPT_MAX_AGE.total_seconds()
            ),
            "action_time_approval_max_age_seconds": int(
                ACTION_TIME_APPROVAL_MAX_AGE.total_seconds()
            ),
            "approval_must_bind_current_preview_and_upload_set": True,
            "upstream_change_invalidates_preview_and_approval": True,
        },
        "private_template": rel(TEMPLATE),
        "portal_checklist": rel(OUT_CHECKLIST),
        "claim_boundary": CLAIM_BOUNDARY,
        "outputs": {"json": rel(OUT_JSON), "markdown": rel(OUT_MD)},
    }
    payload["gate_sha256"] = stable_sha256(payload)
    ensure_public_safe(payload, private_payload)
    return payload


def ensure_public_safe(
    payload: dict[str, Any], private_payload: dict[str, Any] | None = None
) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    lowered = serialized.casefold()
    marker_hits = [marker for marker in PRIVATE_VALUE_MARKERS if marker in lowered]
    if marker_hits:
        raise MissionWeaveGateError("PUBLIC_SECRET_MARKER_EXPOSED")
    if re.search(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", serialized, re.I):
        raise MissionWeaveGateError("PUBLIC_EMAIL_EXPOSED")
    if re.search(
        r"(?<!\d)(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)",
        serialized,
    ):
        raise MissionWeaveGateError("PUBLIC_PHONE_EXPOSED")
    if private_payload is None:
        return
    proposal = private_payload.get("proposal", {})
    for field in (
        "proposal_number",
        "volume2_pdf_sha256",
        "portal_preview_sha256",
        "portal_preview_binding_sha256",
    ):
        value = proposal.get(field) if isinstance(proposal, dict) else None
        if isinstance(value, str) and value and value in serialized:
            raise MissionWeaveGateError(f"PRIVATE_{field.upper()}_EXPOSED")
    approval = private_payload.get("approval", {})
    approval_binding = (
        approval.get("approval_binding_sha256")
        if isinstance(approval, dict)
        else None
    )
    if (
        isinstance(approval_binding, str)
        and approval_binding
        and approval_binding in serialized
    ):
        raise MissionWeaveGateError("PRIVATE_APPROVAL_BINDING_SHA256_EXPOSED")


def render_markdown(payload: dict[str, Any]) -> str:
    source = payload["source_integrity"]
    facts = payload["private_fact_state"]
    volume3 = payload["private_volume3_artifact"]
    jcp = payload["private_jcp_evidence"]
    cmmc = payload["cmmc_evidence_packet"]
    documentary = payload["certification_documentary_register"]
    lines = [
        "# MissionWeave DSIP Action Gate - 2026-07-17",
        "",
        "This public-safe gate reports only package integrity and private-workflow completion state. It contains no legal identifiers, Firm PIN, assigned proposal number, private portal evidence, or unsupported compliance answer.",
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        f"- Submission ready for human click: `{str(payload['submission_ready_for_human_click']).lower()}`",
        f"- Expected deadline: {payload['deadline']['expected_local']}",
        f"- Live DSIP recheck required: `{str(payload['deadline']['live_dsip_recheck_required']).lower()}`",
        f"- Deadline discrepancy: {payload['deadline']['source_discrepancy']}",
        f"- Private input present: `{str(payload['private_input']['present']).lower()}`",
        f"- Private target git-ignored: `{str(payload['private_input']['git_ignored_target']).lower()}`",
        f"- Private values exposed: `{str(payload['private_input']['private_values_exposed']).lower()}`",
        f"- Required private gates: `{payload['gate_summary']['required_private_gate_count']}`",
        f"- Passed private gates: `{payload['gate_summary']['passed_private_gate_count']}`",
        f"- Open gates: `{payload['gate_summary']['open_gate_count']}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Package Integrity",
        "",
        f"- Manifest files: `{source['manifest_file_count']}`",
        f"- All manifest files match: `{str(source['all_manifest_files_match']).lower()}`",
        f"- Volume 2 pages: `{source['volume2_pages']}/{source['volume2_page_limit']}`",
        f"- Letter size: `{str(source['volume2_letter_size']).lower()}`",
        f"- Encrypted: `{str(source['volume2_encrypted']).lower()}`",
        f"- Searchable: `{str(source['volume2_searchable']).lower()}`",
        f"- Required sections present: `{str(source['volume2_required_sections_present']).lower()}`",
        f"- Ignored private final Volume 2 used: `{str(source['private_final_volume2_used']).lower()}`",
        f"- Private final Volume 2 path exposed: `{str(source['absolute_private_path_exposed']).lower()}`",
        f"- Private final Volume 2 hash exposed: `{str(source['private_final_volume2_sha256_exposed']).lower()}`",
        f"- Neutral proposal header still present: `{str(source['neutral_proposal_header_present']).lower()}`",
        f"- All source and format checks pass: `{str(source['all_checks_pass']).lower()}`",
        "",
        "## Private Fact State",
        "",
        f"- Assigned proposal number present: `{str(facts['assigned_proposal_number_present']).lower()}`",
        f"- Assigned proposal number embedded in Volume 2: `{str(facts['assigned_proposal_number_embedded_in_volume2']).lower()}`",
        f"- Assigned proposal number value exposed: `{str(facts['assigned_proposal_number_value_exposed']).lower()}`",
        f"- Volume 2 PDF hash matches private record: `{str(facts['volume2_pdf_hash_matches_private_record']).lower()}`",
        f"- Volume 3 total matches official ceiling: `{str(facts['volume3_total_matches_official_ceiling']).lower()}`",
        f"- Volume 3 private amount exposed: `{str(facts['volume3_private_amount_exposed']).lower()}`",
        f"- Portal preview receipt present: `{str(facts['portal_preview_receipt_present']).lower()}`",
        f"- Portal preview receipt timestamp present: `{str(facts['portal_preview_receipt_timestamp_present']).lower()}`",
        f"- Portal preview receipt fresh: `{str(facts['portal_preview_receipt_fresh']).lower()}`",
        f"- Portal preview binding matches current upload set: `{str(facts['portal_preview_binding_matches_current_upload_set']).lower()}`",
        f"- Portal preview evidence current: `{str(facts['portal_preview_evidence_current']).lower()}`",
        f"- Corporate official reviewed: `{str(facts['corporate_official_reviewed']).lower()}`",
        f"- Action-time authorized: `{str(facts['action_time_authorized']).lower()}`",
        f"- Approval timestamp fresh: `{str(facts['approval_timestamp_fresh']).lower()}`",
        f"- Approval follows the current preview: `{str(facts['approval_not_before_preview']).lower()}`",
        f"- Approval bound to the current preview/upload set: `{str(facts['approval_binding_matches_current_upload_set']).lower()}`",
        f"- Private approval binding exposed: `{str(facts['approval_binding_value_exposed']).lower()}`",
        f"- DD Form 2345/JCP evidence verified: `{str(facts['dd2345_or_jcp_evidence_verified']).lower()}`",
        "",
        "## Private Volume 3 Artifact Integrity",
        "",
        f"- Final workbook present: `{str(volume3['workbook_present']).lower()}`",
        f"- Private receipt present: `{str(volume3['receipt_present']).lower()}`",
        f"- Receipt header valid: `{str(volume3['receipt_header_valid']).lower()}`",
        f"- Workbook size matches receipt: `{str(volume3['workbook_size_matches_receipt']).lower()}`",
        f"- Workbook hash matches receipt: `{str(volume3['workbook_hash_matches_receipt']).lower()}`",
        f"- Workbook OOXML package valid: `{str(volume3['workbook_ooxml_valid']).lower()}`",
        f"- Workbook structure and cell bindings valid: `{str(volume3['workbook_structure_valid']).lower()}`",
        f"- Workbook sheets match receipt: `{str(volume3['workbook_sheet_names_match_receipt']).lower()}`",
        f"- Workbook formulas inspected: `{volume3['workbook_formula_count']}`",
        f"- Workbook formula errors: `{volume3['workbook_formula_error_count']}`",
        f"- Workbook error cells: `{volume3['workbook_error_cell_count']}`",
        f"- Financials derived from workbook contents: `{str(volume3['workbook_financials_derived_from_contents']).lower()}`",
        f"- Workbook content failure code: `{volume3['workbook_content_failure_code']}`",
        f"- Formula scan clean: `{str(volume3['formula_scan_clean']).lower()}`",
        f"- Export/reimport verified: `{str(volume3['export_reimport_verified']).lower()}`",
        f"- Financial reconciliation passes: `{str(volume3['financial_reconciliation_pass']).lower()}`",
        f"- Corporate-review guardrails preserved: `{str(volume3['review_guardrails_preserved']).lower()}`",
        f"- Receipt integrity passes: `{str(volume3['receipt_integrity_pass']).lower()}`",
        f"- Private path exposed: `{str(volume3['private_path_exposed']).lower()}`",
        f"- Private hash exposed: `{str(volume3['private_hash_exposed']).lower()}`",
        "",
        "## Private DD Form 2345/JCP Evidence Integrity",
        "",
        f"- Private receipt present: `{str(jcp['receipt_present']).lower()}`",
        f"- Receipt header valid: `{str(jcp['receipt_header_valid']).lower()}`",
        f"- Evidence PDF present: `{str(jcp['evidence_file_present']).lower()}`",
        f"- Evidence hash matches receipt: `{str(jcp['evidence_hash_matches_receipt']).lower()}`",
        f"- Portal source metadata valid: `{str(jcp['source_metadata_valid']).lower()}`",
        f"- Entity match confirmed: `{str(jcp['entity_match_confirmed']).lower()}`",
        f"- Corporate-official review confirmed: `{str(jcp['corporate_official_reviewed']).lower()}`",
        f"- Evidence integrity passes: `{str(jcp['evidence_integrity_pass']).lower()}`",
        f"- Private path exposed: `{str(jcp['private_path_exposed']).lower()}`",
        f"- Private hash exposed: `{str(jcp['private_hash_exposed']).lower()}`",
        f"- Protocol: `{payload['jcp_evidence_protocol']['path']}`",
        f"- Protocol SHA-256: `{payload['jcp_evidence_protocol']['sha256']}`",
        "",
        "## CMMC Evidence Packet",
        "",
        f"- Packet: `{cmmc['path']}`",
        f"- Schema valid: `{str(cmmc['schema_valid']).lower()}`",
        f"- Integrity valid: `{str(cmmc['integrity_valid']).lower()}`",
        f"- MissionWeave requirement consumed: `{str(cmmc['packet_consumed']).lower()}`",
        f"- Requirement evidence state: `{cmmc['requirement_evidence_state']}`",
        f"- Phase I position supported: `{str(cmmc['phase_i_position_supported']).lower()}`",
        f"- Overclaim boundary present: `{str(cmmc['overclaim_boundary_present']).lower()}`",
        "",
        "## Certification Documentary Register",
        "",
        f"- Register: `{documentary['path']}`",
        f"- Integrity valid: `{str(documentary['integrity_valid']).lower()}`",
        f"- Source hashes current: `{str(documentary['source_hashes_current']).lower()}`",
        f"- Register consumed: `{str(documentary['register_consumed']).lower()}`",
        f"- Status: `{documentary['status']}`",
        f"- No-duplicate-cost documentary prerequisite clear: `{str(documentary['gate_decisions']['NO_DUPLICATE_COST_OR_DELIVERABLE']).lower()}`",
        f"- Technical-data-rights documentary prerequisite clear: `{str(documentary['gate_decisions']['TECHNICAL_DATA_RIGHTS_ASSERTION']).lower()}`",
        "- A private boolean cannot clear either gate without a current, integrity-checked register and a hash-bound review record.",
        "",
        "## Reconciliation Groups",
        "",
    ]
    for group_id, group in payload["gate_summary"]["reconciliation_groups"].items():
        lines.append(
            f"- `{group_id}`: `{group['count']}` gates (`{group['status']}`)"
        )
    lines.extend(["", "## Lifecycle Boundaries", ""])
    lines.extend(
        [
            "This classification is explanatory only. It cannot clear a gate or change submission readiness, and current live portal or contracting-office instructions still control.",
            "",
        ]
    )
    for stage_id, stage in payload["gate_lifecycle"]["stages"].items():
        lines.extend(
            [
                f"### {stage_id}",
                "",
                stage["description"],
                "",
                f"- Submission effect: `{stage['submission_effect']}`",
                f"- Open gates: `{stage['open_gate_count']}`",
            ]
        )
        lines.extend(f"- `{gate}`" for gate in stage["open_gates"])
        lines.append("")

    lines.extend(["## Founder Action Sequence", ""])
    for index, step in enumerate(
        payload["founder_action_sequence"]["ordered_steps"], start=1
    ):
        lines.extend(
            [
                f"### {index}. {step['title']}",
                "",
                step["instruction"],
                "",
                f"- Evidence required: {step['evidence_required']}",
                f"- Human boundary: {step['human_boundary']}",
                f"- Open gates: `{step['open_gate_count']}`",
            ]
        )
        lines.extend(f"- `{gate}`" for gate in step["open_gates"])
        lines.append("")

    lines.extend(["## Open Gates", ""])
    lines.extend(f"- `{gate}`" for gate in payload["gate_summary"]["unresolved_gates"])
    lines.extend(
        [
            "",
            "## Private Workflow",
            "",
            f"1. Run `{payload['private_input']['capture_tool']} --check-target`. This validates the ignored destination without reading private contents.",
            "2. Run the hidden collector with `--section pre-submit`. It captures identity, proposal, and compliance sections but deliberately excludes action-time approval.",
            f"3. After DSIP assigns a proposal number, run `{payload['private_input']['private_volume2_finalizer']}`. It reads the number only from the ignored private record, writes the assigned-number DOCX/PDF only to the ignored private area, performs PDF QA, and updates the private PDF hash without exposing either value publicly. Hash the completed portal-preview receipt with `--preview-receipt-file`; a manually entered digest does not establish freshness.",
            f"4. For the ITAR-marked topic, save only an official JCP portal submission receipt or certified DD Form 2345 as a private PDF and complete `{payload['private_input']['jcp_evidence_template']}` beside it. A boolean answer cannot clear this gate without a matching file hash.",
            f"5. Review the consumed CMMC packet at `{payload['cmmc_evidence_packet']['path']}`. An unresolved packet leaves the supported-position gate open even when a private boolean is checked.",
            f"6. Resolve the source-bound prerequisites in `{payload['certification_documentary_register']['path']}`. Preserve each review receipt privately and bind only its SHA-256 in the register; a private checkbox alone cannot clear the no-duplicate-cost or technical-data-rights gates.",
            "7. Run `--section approval` only after the corporate official reviews the fresh complete portal preview at action time. The collector binds that authorization to the current preview/upload-set identity and never requests or accepts a Firm PIN or login credential.",
            "8. Run this public gate with `--private-input`; require every gate to pass before asking for the final human click.",
            "",
            "## Controls",
            "",
            f"- Browser navigation performed: `{str(payload['controls']['browser_navigation_performed']).lower()}`",
            f"- External send performed: `{str(payload['controls']['external_send_performed']).lower()}`",
            f"- Portal submit performed: `{str(payload['controls']['portal_submit_performed']).lower()}`",
            f"- Builder can click final submit: `{str(payload['controls']['builder_can_click_final_submit']).lower()}`",
            f"- Action-time human required: `{str(payload['controls']['action_time_human_required']).lower()}`",
            f"- Private boolean can clear documentary gate: `{str(payload['controls']['private_boolean_can_clear_documentary_gate']).lower()}`",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def render_portal_checklist(payload: dict[str, Any]) -> str:
    source = payload["source_integrity"]
    instruction = payload["official_instruction_facts"]
    founder_steps = "\n".join(
        (
            f"{index}. **{step['title']}** - {step['instruction']} "
            f"Evidence: {step['evidence_required']}"
        )
        for index, step in enumerate(
            payload["founder_action_sequence"]["ordered_steps"], start=1
        )
    )
    return rf"""# MissionWeave DSIP Portal Checklist - 2026-07-17

Use this sequence only after the user says `I'm in`. Inspect the current in-session browser page before navigating. Preserve any authentication already in progress.

## Deadline Lock

- Topic: `{TOPIC}`
- Expected close: `{payload['deadline']['expected_local']}`
- Central-time conversion: `July 22, 2026 at 11:00 a.m. Central Time`
- Internal operating target: finish uploads and the complete portal preview by `July 21 at 3:00 p.m. Central`; reserve the founder's final endorsement for no later than `July 22 at 9:00 a.m. Central`.
- Inbox confirmation: the July 17 DSIP proposal-creation notice repeats the July 22 noon Eastern deadline and warns that every volume must be completed and endorsed before close.
- Recheck the live DSIP countdown before entry and again before final submission.
- Source discrepancy: {payload['deadline']['source_discrepancy']}
- Amendment control: use `MISSIONWEAVE_AMENDMENT_2_PORTAL_CONTROL_2026-07-18.md`. Amendment 2 renames the due-diligence program as Foreign Risk Evaluation (FRE), but the required Volume 7 webform and its eight disclosure questions remain. Do not upload a foreign-affiliations PDF in Volume 5.

## Exact Founder Order Of Operations

This sequence covers every currently open gate exactly once. It does not certify a fact, clear a gate, or replace current portal instructions.

{founder_steps}

## Package Lock

- Manifest files verified: `{source['manifest_file_count']}`
- All manifest hashes and sizes match: `{str(source['all_manifest_files_match']).lower()}`
- Volume 2 candidate: `{source['volume2_pages']}` pages of `{source['volume2_page_limit']}` allowed, letter size, searchable, and unencrypted.
- The candidate still contains the neutral proposal-number header: `{str(source['neutral_proposal_header_present']).lower()}`.
- Ignored assigned-number final PDF selected by the gate: `{str(source['private_final_volume2_used']).lower()}`.
- Do not upload the tracked neutral PDF after DSIP assigns a proposal number. Run `{rel(PRIVATE_FINALIZER)}`; the final PDF remains ignored and its path, number, and hash remain absent from public artifacts.
- Private Volume 3 receipt integrity passes: `{str(payload['private_volume3_artifact']['receipt_integrity_pass']).lower()}`. This verifies the ignored workbook against its ignored receipt without publishing either path or hash; it does not replace corporate-official cost-basis review.
- Private DD Form 2345/JCP evidence integrity passes: `{str(payload['private_jcp_evidence']['evidence_integrity_pass']).lower()}`. A checked private flag cannot clear this gate unless an official portal PDF exists, its SHA-256 matches the ignored receipt, and entity/corporate review are confirmed.
- CMMC/export evidence packet consumed with valid integrity: `{str(payload['cmmc_evidence_packet']['packet_consumed']).lower()}`. MissionWeave CMMC evidence state: `{payload['cmmc_evidence_packet']['requirement_evidence_state']}`. An unresolved packet cannot support the Phase I position.
- Certification documentary register consumed with valid integrity: `{str(payload['certification_documentary_register']['register_consumed']).lower()}`. Source hashes current: `{str(payload['certification_documentary_register']['source_hashes_current']).lower()}`. A private checkbox cannot clear the no-duplicate-cost or technical-data-rights gate without its source-bound documentary decision and hash-bound review record.

## Registration And Firm Controls

1. Complete Login.gov and DSIP authentication without copying credentials into chat, Git, or artifacts.
2. Verify the exact DSIP organization linkage, Firm Admin, Firm PIN availability, and all firm-level forms.
3. Verify active SAM status, current representations, legal-name match, UEI match, and CAGE match inside authenticated systems.
4. Verify SBA Company Registry completion and the SBC Control ID. Store neither the Firm PIN nor login credentials in the private gate file.
5. Confirm submitter and corporate-official authority.
6. Record only the resulting yes/no completion state with `{rel(PRIVATE_CAPTURE_TOOL)} --section identity`; the collector has no Firm PIN or credential field.

## Seven Volumes

1. Volume 1 - Proposal Cover Sheet: paste only the bounded public abstract and anticipated-benefits text. Each field must remain within 3,000 characters and contain no proprietary or classified material.
2. Volume 2 - Technical Volume: capture the assigned DSIP proposal number in the ignored record, run the guarded private finalizer, require its PDF QA to pass with no neutral header, run a local malware scan, and upload one PDF no longer than {instruction['volume2_page_limit']} pages. Keep the public 15-file neutral manifest unchanged.
3. Volume 3 - Cost Volume: use the DSIP spreadsheet/form, keep the Phase I base at or below the official $100,000 ceiling, support the direct labor and indirect treatment, and reconcile every task, ODC, and percentage-of-work entry.
4. Volume 4 - Company Commercialization Report: answer from actual SBIR/STTR award history and ensure the current company report is complete.
5. Volume 5 - Supporting Documents: upload only applicable and current evidence. Because the topic is ITAR-marked, include a certified DD Form 2345 or acceptable JCP application-submission receipt when required. Use the official JCP portal at `https://www.public.dacs.dla.mil/jcp/ext/`; keep the downloaded evidence and its receipt private, require the file hash to match, and do not treat portal registration or prerequisites-in-progress as submission evidence. Do not upload the old foreign-affiliations PDF form.
6. Volume 6 - Fraud, Waste, and Abuse Training: complete the current annual DSIP training review.
7. Volume 7 - Foreign Affiliations: complete the current DSIP webform from current facts. The corporate official cannot certify the proposal until this webform is complete.

## Compliance Locks

- Confirm U.S. small-business eligibility, ownership and affiliates, PI primary employment, the proposed 640 PI hours, and the SBIR percentage-of-work rule.
- Compare MissionWeave with every prior, current, pending, or planned proposal. Disclose overlap and request no duplicate PI hours, cloud costs, software work, or deliverables.
- Keep `NO_DUPLICATE_COST_OR_DELIVERABLE` open until the authoritative proposal/award record, 640-hour schedule, cost categories, background/proposal separation, and final corporate review are reconciled in `{rel(CERTIFICATION_DOCUMENTARY_REGISTER)}`.
- Treat the topic as ITAR-marked. Keep controlled technical data out of the proposal and document the DD Form 2345/JCP and Technology Control Plan decisions.
- Projected CMMC level: `{instruction['projected_cmmc_level']}`. {instruction['cmmc_amendment_note']} Consume `{payload['cmmc_evidence_packet']['path']}` and do not claim an assessment, certification, or compliant enclave without current authoritative evidence.
- Confirm foreign-citizen participation, foreign affiliations, conflicts, joint-venture status, and each technical-data/software-rights assertion from current records.
- Keep `TECHNICAL_DATA_RIGHTS_ASSERTION` open until every asserted item is mapped to a version and funding-history record, MIT/open-source/public interfaces are separated from any restriction, and qualified rights plus corporate-official review is hash-bound in the documentary register.
- TABA is not requested. Do not add a provider without a named, supported, topic-specific need and a reconciled cost entry.

## Final Preview Gate

1. Run `python code\ops\FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py` after the assigned proposal number is captured. Require `PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED`.
2. Inspect every populated field, all seven volumes, every attachment filename and hash, the cost total, and the live deadline.
3. Save a private local preview receipt and capture it with `--section proposal --preview-receipt-file <private-preview-receipt>`. The collector records only private consistency metadata and rejects a stale receipt; a manually entered digest cannot establish freshness.
4. Capture the action-time approval section separately. It cryptographically binds approval to the current preview/upload set and expires after {int(ACTION_TIME_APPROVAL_MAX_AGE.total_seconds() // 60)} minutes. This command never clicks submit:

```powershell
python code\ops\CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section approval
```

5. Run:

```powershell
python code\ops\BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py --private-input grant_submissions\DLA26BZ03_NV011_MissionWeave\private\MISSIONWEAVE_DSIP_ACTION.private.json
```

6. Require status `READY_FOR_HUMAN_FINAL_SUBMIT_CLICK` and zero open gates.
7. Stop for the final human review. The builder does not click submit, certify facts, accept terms, or create a Government transmission receipt.

## Public Claim Boundary

{payload['claim_boundary']}
"""


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the public-safe MissionWeave DSIP action gate."
    )
    parser.add_argument("--private-input", type=Path)
    parser.add_argument("--check-target", action="store_true")
    args = parser.parse_args()

    if args.check_target:
        target = validate_private_target(DEFAULT_PRIVATE_INPUT)
        print(
            json.dumps(
                {
                    "target": rel(target),
                    "git_ignored": git_ignored(target),
                    "present": target.is_file(),
                    "browser_navigation_performed": False,
                },
                indent=2,
            )
        )
        return

    private_payload = None
    private_input_sha256 = None
    if args.private_input is not None:
        private_path = validate_private_target(args.private_input)
        if not private_path.is_file():
            raise SystemExit("Private input does not exist")
        private_bytes = private_path.read_bytes()
        private_payload = json.loads(private_bytes.decode("utf-8"))
        private_input_sha256 = sha256_bytes(private_bytes)

    payload = build_payload(
        private_payload, private_input_sha256=private_input_sha256
    )
    markdown = render_markdown(payload)
    checklist = render_portal_checklist(payload)
    ensure_public_safe(payload, private_payload)
    ensure_public_safe({"markdown": markdown, "checklist": checklist}, private_payload)
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, markdown)
    write_text(OUT_CHECKLIST, checklist)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source_integrity": payload["source_integrity"]["all_checks_pass"],
                "required_private_gates": payload["gate_summary"][
                    "required_private_gate_count"
                ],
                "open_gates": payload["gate_summary"]["open_gate_count"],
                "browser_navigation_performed": payload["controls"][
                    "browser_navigation_performed"
                ],
                "outputs": payload["outputs"],
                "portal_checklist": payload["portal_checklist"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
