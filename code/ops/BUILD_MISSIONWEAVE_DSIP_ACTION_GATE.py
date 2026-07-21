from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import re
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


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
OUT_JSON = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
OUT_MD = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.md"
OUT_CHECKLIST = PACKAGE_DIR / "MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md"

PRIVATE_SCHEMA = "lumencore.missionweave_dsip_action_private.v1"
PUBLIC_SCHEMA = "lumencore.missionweave_dsip_action_gate.v1"
PRIVATE_VOLUME3_RECEIPT_SCHEMA = (
    "lumencore.missionweave_dsip_volume3_final_receipt_private.v1"
)
PRIVATE_JCP_EVIDENCE_SCHEMA = "lumencore.missionweave_jcp_evidence_private.v1"
CMMC_PACKET_SCHEMA = "lumencore.cmmc_export_evidence_packet.v1"
CMMC_PROGRAM_ID = "MissionWeave"
CMMC_FACT_ID = "missionweave.cmmc_l2_self_status"
CMMC_CONTROL = "CMMC_L2_SELF_STATUS"
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
    state["formula_scan_clean"] = receipt.get("formula_error_count") == 0
    state["export_reimport_verified"] = receipt.get("export_reimport_verified") is True
    state["financial_reconciliation_pass"] = bool(
        parse_phase_i_total(receipt.get("total_usd")) == PHASE_I_CEILING
        and parse_phase_i_total(receipt.get("firm_cost_usd")) == PHASE_I_CEILING
        and parse_phase_i_total(receipt.get("subcontractor_cost_usd")) == Decimal("0")
        and receipt.get("taba_requested") is False
        and receipt.get("duration_months") == 6
        and receipt.get("pi_hours") == 640
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
    path = shutil.which(executable)
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

    info_text = run_pdf_tool("pdfinfo.exe", [str(selected_volume2)])
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


def current_upload_set_identity_sha256(
    payload: dict[str, Any],
    *,
    jcp_evidence_state: dict[str, Any],
    volume3_artifact_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
) -> str:
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
    }
    return stable_sha256(context).upper()


def preview_evidence_binding_sha256(
    payload: dict[str, Any],
    *,
    jcp_evidence_state: dict[str, Any],
    volume3_artifact_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
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
        ),
        "upload_set_identity_sha256": current_upload_set_identity_sha256(
            payload,
            jcp_evidence_state=jcp_evidence_state,
            volume3_artifact_state=volume3_artifact_state,
            cmmc_packet_state=cmmc_packet_state,
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
    corporate_review_current = gate_state["CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW"]
    volume3_cost_basis_supported = proposal.get("volume3_cost_basis_supported") is True
    gate_state["TECHNICAL_DATA_RIGHTS_ASSERTION"] = bool(
        compliance.get("technical_data_rights_assertion_supported") is True
        and volume3_cost_basis_supported
        and corporate_review_current
    )
    gate_state["NO_DUPLICATE_COST_OR_DELIVERABLE"] = bool(
        compliance.get("no_duplicate_cost_or_deliverable") is True
        and gate_state["PRIOR_CURRENT_PENDING_SUPPORT"]
        and gate_state["PI_640_HOURS"]
        and gate_state["TECHNICAL_DATA_RIGHTS_ASSERTION"]
        and volume3_cost_basis_supported
        and corporate_review_current
    )
    itar_scope_confirmed = bool(
        compliance.get("itar_scope_determination") == "SUBJECT_TO_ITAR"
        and jcp_evidence_verified
        and compliance.get("technology_control_plan_decision_documented") is True
        and compliance.get("controlled_data_excluded_from_submission") is True
    )

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
    evaluation = (
        evaluate_private_payload(
            private_payload,
            source_state=source_state,
            volume2_text=volume2_text,
            volume3_artifact_state=volume3_artifact_state,
            jcp_evidence_state=jcp_evidence_state,
            cmmc_packet_state=cmmc_packet_state,
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
    public_volume3_artifact_state = {
        key: volume3_artifact_state.get(key)
        for key in (
            "receipt_present",
            "workbook_present",
            "receipt_header_valid",
            "workbook_size_matches_receipt",
            "workbook_hash_matches_receipt",
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
            "expected_path": "IGNORED_PRIVATE_ACTION_INPUT",
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
            "jcp_evidence_receipt_expected_path": (
                "IGNORED_PRIVATE_JCP_EVIDENCE_RECEIPT"
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
        "## Reconciliation Groups",
        "",
    ]
    for group_id, group in payload["gate_summary"]["reconciliation_groups"].items():
        lines.append(
            f"- `{group_id}`: `{group['count']}` gates (`{group['status']}`)"
        )
    lines.extend(["", "## Open Gates", ""])
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
            "6. Run `--section approval` only after the corporate official reviews the fresh complete portal preview at action time. The collector binds that authorization to the current preview/upload-set identity and never requests or accepts a Firm PIN or login credential.",
            "7. Run this public gate with `--private-input`; require every gate to pass before asking for the final human click.",
            "",
            "## Controls",
            "",
            f"- Browser navigation performed: `{str(payload['controls']['browser_navigation_performed']).lower()}`",
            f"- External send performed: `{str(payload['controls']['external_send_performed']).lower()}`",
            f"- Portal submit performed: `{str(payload['controls']['portal_submit_performed']).lower()}`",
            f"- Builder can click final submit: `{str(payload['controls']['builder_can_click_final_submit']).lower()}`",
            f"- Action-time human required: `{str(payload['controls']['action_time_human_required']).lower()}`",
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
- Treat the topic as ITAR-marked. Keep controlled technical data out of the proposal and document the DD Form 2345/JCP and Technology Control Plan decisions.
- Projected CMMC level: `{instruction['projected_cmmc_level']}`. {instruction['cmmc_amendment_note']} Consume `{payload['cmmc_evidence_packet']['path']}` and do not claim an assessment, certification, or compliant enclave without current authoritative evidence.
- Confirm foreign-citizen participation, foreign affiliations, conflicts, joint-venture status, and each technical-data/software-rights assertion from current records.
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
python code\ops\BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py --private-input <IGNORED_PRIVATE_INPUT>
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
