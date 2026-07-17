from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
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
OUT_JSON = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.json"
OUT_MD = PACKAGE_DIR / "MISSIONWEAVE_DSIP_ACTION_GATE_2026-07-17.md"
OUT_CHECKLIST = PACKAGE_DIR / "MISSIONWEAVE_DSIP_PORTAL_CHECKLIST_2026-07-17.md"

PRIVATE_SCHEMA = "lumencore.missionweave_dsip_action_private.v1"
PUBLIC_SCHEMA = "lumencore.missionweave_dsip_action_gate.v1"
PRIVATE_VOLUME3_RECEIPT_SCHEMA = (
    "lumencore.missionweave_dsip_volume3_final_receipt_private.v1"
)
TOPIC = "DLA26BZ03-NV011"
EXPECTED_DEADLINE = "2026-07-22T12:00:00-04:00"
PHASE_I_CEILING = Decimal("100000")
VOLUME2_PAGE_LIMIT = 20
NEUTRAL_PROPOSAL_HEADER = "Proposal No. assigned in DSIP"

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
) -> dict[str, bool]:
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
    return state


def require_exact_keys(section: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(section, dict) or set(section) != expected:
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


def evaluate_private_payload(
    payload: dict[str, Any],
    *,
    source_state: dict[str, Any],
    volume2_text: str,
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
    proposal_value_keys = {
        "proposal_number",
        "volume2_pdf_sha256",
        "volume3_total_usd",
        "portal_preview_sha256",
    }
    proposal = require_exact_keys(
        payload.get("proposal"),
        set(PROPOSAL_FLAG_GATES) | proposal_value_keys,
        "PROPOSAL_SCHEMA_DRIFT",
    )
    compliance = require_exact_keys(
        payload.get("eligibility_and_compliance"),
        set(COMPLIANCE_GATES) | {"itar_scope_determination"},
        "COMPLIANCE_SCHEMA_DRIFT",
    )
    approval = require_exact_keys(
        payload.get("approval"),
        set(APPROVAL_FLAG_GATES) | {"approval_utc"},
        "APPROVAL_SCHEMA_DRIFT",
    )

    gate_state: dict[str, bool] = {}
    for field, gate in IDENTITY_GATES.items():
        gate_state[gate] = identity.get(field) is True
    for field, gate in PROPOSAL_FLAG_GATES.items():
        gate_state[gate] = proposal.get(field) is True
    for field, gate in COMPLIANCE_GATES.items():
        gate_state[gate] = compliance.get(field) is True
    for field, gate in APPROVAL_FLAG_GATES.items():
        gate_state[gate] = approval.get(field) is True

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
    itar_scope_confirmed = compliance.get("itar_scope_determination") == "SUBJECT_TO_ITAR"

    gate_state.update(
        {
            "PRIVATE_INPUT_TIMESTAMP": valid_timestamp(payload.get("captured_utc")),
            "ASSIGNED_PROPOSAL_NUMBER_CAPTURE": proposal_number_present,
            "VOLUME2_PDF_HASH_MATCH": pdf_hash_match,
            "VOLUME2_ASSIGNED_PROPOSAL_NUMBER_EMBEDDED": proposal_number_embedded,
            "VOLUME3_TOTAL_MATCHES_PHASE_I_CEILING": cost_total_matches,
            "PORTAL_PREVIEW_RECEIPT_HASH": preview_receipt_present,
            "ITAR_SCOPE_CONFIRMED": itar_scope_confirmed,
            "ACTION_TIME_APPROVAL_TIMESTAMP": valid_timestamp(approval.get("approval_utc")),
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
        "corporate_official_reviewed": gate_state[
            "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW"
        ],
        "action_time_authorized": gate_state[
            "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION"
        ],
        "approval_timestamp_present": gate_state["ACTION_TIME_APPROVAL_TIMESTAMP"],
    }


def build_payload(
    private_payload: dict[str, Any] | None = None,
    *,
    private_input_sha256: str | None = None,
    source_state: dict[str, Any] | None = None,
    volume2_text: str | None = None,
    volume3_artifact_state: dict[str, bool] | None = None,
) -> dict[str, Any]:
    if source_state is None or volume2_text is None:
        use_private_final = bool(
            private_payload is not None and PRIVATE_FINAL_VOLUME2_PDF.is_file()
        )
        source_state, volume2_text = inspect_source_package(
            PRIVATE_FINAL_VOLUME2_PDF if use_private_final else VOLUME2_PDF,
            private_final=use_private_final,
        )
    evaluation = (
        evaluate_private_payload(
            private_payload, source_state=source_state, volume2_text=volume2_text
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

    if volume3_artifact_state is None:
        volume3_artifact_state = inspect_private_volume3_artifact()

    payload: dict[str, Any] = {
        "schema": PUBLIC_SCHEMA,
        "generated_utc": now_utc(),
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
            "pre_submit_excludes_action_time_approval": True,
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
            "portal_preview_receipt_value_exposed": False,
            "corporate_official_reviewed": bool(
                evaluation and evaluation["corporate_official_reviewed"]
            ),
            "action_time_authorized": bool(
                evaluation and evaluation["action_time_authorized"]
            ),
            "approval_timestamp_present": bool(
                evaluation and evaluation["approval_timestamp_present"]
            ),
        },
        "private_volume3_artifact": deepcopy(volume3_artifact_state),
        "official_instruction_facts": {
            "dsip_volume_count": 7,
            "volume2_page_limit": VOLUME2_PAGE_LIMIT,
            "phase_i_base_ceiling_usd": 100000,
            "phase_i_max_duration_months": 12,
            "current_package_duration_months": 6,
            "topic_itar_flag": True,
            "dd2345_or_jcp_application_evidence_required_if_effort_subject_to_itar": True,
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
    ):
        value = proposal.get(field) if isinstance(proposal, dict) else None
        if isinstance(value, str) and value and value in serialized:
            raise MissionWeaveGateError(f"PRIVATE_{field.upper()}_EXPOSED")


def render_markdown(payload: dict[str, Any]) -> str:
    source = payload["source_integrity"]
    facts = payload["private_fact_state"]
    volume3 = payload["private_volume3_artifact"]
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
        f"- Corporate official reviewed: `{str(facts['corporate_official_reviewed']).lower()}`",
        f"- Action-time authorized: `{str(facts['action_time_authorized']).lower()}`",
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
        "## Open Gates",
        "",
    ]
    lines.extend(f"- `{gate}`" for gate in payload["gate_summary"]["unresolved_gates"])
    lines.extend(
        [
            "",
            "## Private Workflow",
            "",
            f"1. Run `{payload['private_input']['capture_tool']} --check-target`. This validates the ignored destination without reading private contents.",
            "2. Run the hidden collector with `--section pre-submit`. It captures identity, proposal, and compliance sections but deliberately excludes action-time approval.",
            f"3. After DSIP assigns a proposal number, run `{payload['private_input']['private_volume2_finalizer']}`. It reads the number only from the ignored private record, writes the assigned-number DOCX/PDF only to the ignored private area, performs PDF QA, and updates the private PDF hash without exposing either value publicly.",
            "4. Run `--section approval` only after the corporate official reviews the complete portal preview at action time. The collector never requests or accepts a Firm PIN or login credential.",
            "5. Run this public gate with `--private-input`; require every gate to pass before asking for the final human click.",
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
- Recheck the live DSIP countdown before entry and again before final submission.
- Source discrepancy: {payload['deadline']['source_discrepancy']}

## Package Lock

- Manifest files verified: `{source['manifest_file_count']}`
- All manifest hashes and sizes match: `{str(source['all_manifest_files_match']).lower()}`
- Volume 2 candidate: `{source['volume2_pages']}` pages of `{source['volume2_page_limit']}` allowed, letter size, searchable, and unencrypted.
- The candidate still contains the neutral proposal-number header: `{str(source['neutral_proposal_header_present']).lower()}`.
- Ignored assigned-number final PDF selected by the gate: `{str(source['private_final_volume2_used']).lower()}`.
- Do not upload the tracked neutral PDF after DSIP assigns a proposal number. Run `{rel(PRIVATE_FINALIZER)}`; the final PDF remains ignored and its path, number, and hash remain absent from public artifacts.
- Private Volume 3 receipt integrity passes: `{str(payload['private_volume3_artifact']['receipt_integrity_pass']).lower()}`. This verifies the ignored workbook against its ignored receipt without publishing either path or hash; it does not replace corporate-official cost-basis review.

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
5. Volume 5 - Supporting Documents: upload only applicable and current evidence. Because the topic is ITAR-marked, include a certified DD Form 2345 or acceptable JCP application evidence when required. Do not upload the old foreign-affiliations PDF form.
6. Volume 6 - Fraud, Waste, and Abuse Training: complete the current annual DSIP training review.
7. Volume 7 - Foreign Affiliations: complete the current DSIP webform from current facts. The corporate official cannot certify the proposal until this webform is complete.

## Compliance Locks

- Confirm U.S. small-business eligibility, ownership and affiliates, PI primary employment, the proposed 640 PI hours, and the SBIR percentage-of-work rule.
- Compare MissionWeave with every prior, current, pending, or planned proposal. Disclose overlap and request no duplicate PI hours, cloud costs, software work, or deliverables.
- Treat the topic as ITAR-marked. Keep controlled technical data out of the proposal and document the DD Form 2345/JCP and Technology Control Plan decisions.
- Projected CMMC level: `{instruction['projected_cmmc_level']}`. {instruction['cmmc_amendment_note']} Do not claim an assessment, certification, or compliant enclave without current evidence.
- Confirm foreign-citizen participation, foreign affiliations, conflicts, joint-venture status, and each technical-data/software-rights assertion from current records.
- TABA is not requested. Do not add a provider without a named, supported, topic-specific need and a reconciled cost entry.

## Final Preview Gate

1. Run `python code\ops\FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py` after the assigned proposal number is captured. Require `PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED`.
2. Inspect every populated field, all seven volumes, every attachment filename and hash, the cost total, and the live deadline.
3. Save a private local preview receipt and record only its SHA-256 in the ignored private gate file.
4. Capture the action-time approval section separately. This command never clicks submit:

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
