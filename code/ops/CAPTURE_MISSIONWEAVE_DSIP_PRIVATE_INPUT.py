from __future__ import annotations

import argparse
import getpass
import hmac
import importlib.util
import json
import os
import re
import subprocess
import tempfile
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
GATE_PATH = Path(__file__).with_name("BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py")
PRIVATE_DIR = ROOT / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave" / "private"
DEFAULT_OUTPUT = PRIVATE_DIR / "MISSIONWEAVE_DSIP_ACTION.private.json"
TEMPLATE = ROOT / "config" / "missionweave_dsip_action_private_template_v1.json"

PRE_SUBMIT_SECTIONS = ("identity", "proposal", "eligibility_and_compliance")
SECTION_ALIASES = {
    "identity": ("identity",),
    "proposal": ("proposal",),
    "compliance": ("eligibility_and_compliance",),
    "approval": ("approval",),
    "pre-submit": PRE_SUBMIT_SECTIONS,
}
FORBIDDEN_TEXT_MARKERS = (
    "api_key",
    "api key",
    "access_token",
    "access token",
    "refresh_token",
    "refresh token",
    "client_secret",
    "client secret",
    "password",
    "passwd",
    "private key",
    "bearer ",
    "firm pin",
    "sk-",
    "xox",
)

IDENTITY_LABELS = {
    "dsip_authenticated": "DSIP authentication is complete in the live session",
    "organization_linked": "The correct organization is linked in DSIP",
    "firm_admin_confirmed": "Firm Admin status is confirmed",
    "firm_pin_available_in_dsip": "DSIP confirms Firm PIN availability (do not provide its value)",
    "firm_level_forms_complete": "All current firm-level forms are complete",
    "sam_active_verified": "Active SAM status was verified in the authenticated system",
    "sam_representations_current": "SAM representations are current",
    "sam_legal_name_match": "SAM legal name matches the proposal identity",
    "uei_match_verified": "UEI matches across the authenticated systems",
    "cage_match_verified": "CAGE code matches across the authenticated systems",
    "sba_company_registry_verified": "SBA Company Registry completion was verified",
    "sbc_control_id_verified": "SBC Control ID was verified (do not enter its value here)",
    "submitter_authority_confirmed": "Submitter authority is confirmed",
}

PROPOSAL_LABELS = {
    "live_deadline_confirmed": "The live DSIP deadline/countdown was rechecked",
    "volume1_public_release_text_reviewed": "Volume 1 public-release text was reviewed",
    "volume2_pdf_rebuilt_with_assigned_proposal_number": "Volume 2 was rebuilt with the assigned proposal number",
    "volume2_virus_scan_passed": "The rebuilt Volume 2 PDF passed a local malware scan",
    "volume3_cost_basis_supported": "Volume 3 cost basis is supported by current records",
    "volume4_ccr_answer_verified": "Volume 4 Company Commercialization Report answers were verified",
    "volume5_upload_set_reviewed": "The applicable Volume 5 upload set was reviewed",
    "volume6_fwa_training_current": "Current annual fraud, waste, and abuse training was reviewed",
    "volume7_webform_complete": "The current foreign-affiliations webform is complete",
    "portal_preview_reviewed": "The complete portal preview was reviewed",
}

COMPLIANCE_LABELS = {
    "pi_primary_employment_confirmed": "PI primary-employment requirement is supported",
    "pi_640_hours_confirmed": "The proposed 640 PI hours are supported",
    "sbir_work_share_confirmed": "The SBIR percentage-of-work requirement is supported",
    "us_small_business_eligibility_confirmed": "U.S. small-business eligibility is supported",
    "ownership_and_affiliates_reviewed": "Ownership and affiliates were reviewed from current facts",
    "prior_current_pending_support_reviewed": "Prior, current, and pending support was reviewed",
    "no_duplicate_cost_or_deliverable": "No duplicate cost, hour, or deliverable is requested",
    "dd2345_or_jcp_application_evidence_ready": "Applicable DD Form 2345 or JCP application evidence is ready",
    "controlled_data_excluded_from_submission": "Controlled technical data is excluded from the submission",
    "technology_control_plan_decision_documented": "Technology Control Plan decision is documented",
    "current_cmmc_requirements_reviewed": "Current CMMC requirements were reviewed",
    "cmmc_phase_i_self_assessment_position_supported": "Any Phase I self-assessment position is supported",
    "no_cmmc_status_overclaim": "No unsupported CMMC status is claimed",
    "foreign_citizen_answer_verified": "Foreign-citizen answer was verified from current facts",
    "foreign_affiliations_webform_answered_from_current_facts": "Foreign-affiliations webform uses current facts",
    "conflicts_and_joint_venture_status_reviewed": "Conflicts and joint-venture status were reviewed",
    "technical_data_rights_assertion_supported": "Technical-data and software-rights assertions are supported",
}


class CaptureError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def load_gate():
    spec = importlib.util.spec_from_file_location("missionweave_dsip_action_gate", GATE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("MissionWeave DSIP action gate could not be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = load_gate()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def path_is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def git_ignored(path: Path, *, root: Path = ROOT) -> bool:
    if not path_is_within(path, root):
        return False
    relative = path.resolve().relative_to(root.resolve()).as_posix()
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", relative],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def validate_private_target(
    target: Path,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> Path:
    if target.is_symlink():
        raise CaptureError("SYMLINK_TARGET_REJECTED")
    resolved = target.resolve()
    if not path_is_within(resolved, root):
        raise CaptureError("TARGET_OUTSIDE_REPOSITORY")
    if not path_is_within(resolved, private_dir):
        raise CaptureError("TARGET_OUTSIDE_PRIVATE_DIRECTORY")
    if resolved.exists() and not resolved.is_file():
        raise CaptureError("TARGET_NOT_REGULAR_FILE")
    checker = ignored_checker or (lambda path: git_ignored(path, root=root))
    if not checker(resolved):
        raise CaptureError("TARGET_NOT_GIT_IGNORED")
    return resolved


def require_exact_keys(value: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise CaptureError(code)
    return value


def require_compatible_keys(
    value: Any,
    required: set[str],
    optional: set[str],
    code: str,
) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CaptureError(code)
    keys = set(value)
    if not required.issubset(keys) or keys.difference(required | optional):
        raise CaptureError(code)
    return value


def validate_payload_shape(payload: Any) -> dict[str, Any]:
    top_keys = {
        "schema",
        "topic",
        "template_only",
        "captured_utc",
        "identity",
        "proposal",
        "eligibility_and_compliance",
        "approval",
    }
    record = require_exact_keys(payload, top_keys, "PRIVATE_TOP_LEVEL_SCHEMA_DRIFT")
    if record["schema"] != GATE.PRIVATE_SCHEMA:
        raise CaptureError("PRIVATE_SCHEMA_MISMATCH")
    if record["topic"] != GATE.TOPIC:
        raise CaptureError("TOPIC_MISMATCH")
    if not isinstance(record["template_only"], bool):
        raise CaptureError("TEMPLATE_FLAG_INVALID")
    if record["captured_utc"] is not None and not GATE.valid_timestamp(
        record["captured_utc"]
    ):
        raise CaptureError("CAPTURE_TIMESTAMP_INVALID")

    identity = require_exact_keys(
        record["identity"], set(GATE.IDENTITY_GATES), "IDENTITY_SCHEMA_DRIFT"
    )
    proposal = require_compatible_keys(
        record["proposal"],
        set(GATE.PROPOSAL_FLAG_GATES) | GATE.PROPOSAL_VALUE_KEYS,
        GATE.PROPOSAL_CONSISTENCY_KEYS,
        "PROPOSAL_SCHEMA_DRIFT",
    )
    compliance = require_exact_keys(
        record["eligibility_and_compliance"],
        set(GATE.COMPLIANCE_GATES) | {"itar_scope_determination"},
        "COMPLIANCE_SCHEMA_DRIFT",
    )
    approval = require_compatible_keys(
        record["approval"],
        set(GATE.APPROVAL_FLAG_GATES) | GATE.APPROVAL_VALUE_KEYS,
        GATE.APPROVAL_CONSISTENCY_KEYS,
        "APPROVAL_SCHEMA_DRIFT",
    )
    proposal.setdefault("portal_preview_captured_utc", None)
    proposal.setdefault("portal_preview_binding_sha256", None)
    approval.setdefault("approval_binding_sha256", None)

    for field in GATE.IDENTITY_GATES:
        if not isinstance(identity[field], bool):
            raise CaptureError("IDENTITY_FLAG_TYPE_INVALID")
    for field in GATE.PROPOSAL_FLAG_GATES:
        if not isinstance(proposal[field], bool):
            raise CaptureError("PROPOSAL_FLAG_TYPE_INVALID")
    for field in GATE.COMPLIANCE_GATES:
        if not isinstance(compliance[field], bool):
            raise CaptureError("COMPLIANCE_FLAG_TYPE_INVALID")
    for field in GATE.APPROVAL_FLAG_GATES:
        if not isinstance(approval[field], bool):
            raise CaptureError("APPROVAL_FLAG_TYPE_INVALID")
    if proposal["proposal_number"] is not None and not isinstance(
        proposal["proposal_number"], str
    ):
        raise CaptureError("PROPOSAL_NUMBER_TYPE_INVALID")
    for field in (
        "volume2_pdf_sha256",
        "portal_preview_sha256",
        "portal_preview_binding_sha256",
    ):
        if proposal[field] is not None and not isinstance(proposal[field], str):
            raise CaptureError("PROPOSAL_HASH_TYPE_INVALID")
    if proposal["portal_preview_captured_utc"] is not None and not GATE.valid_timestamp(
        proposal["portal_preview_captured_utc"]
    ):
        raise CaptureError("PREVIEW_RECEIPT_TIMESTAMP_INVALID")
    if proposal["volume3_total_usd"] is not None and (
        isinstance(proposal["volume3_total_usd"], bool)
        or not isinstance(proposal["volume3_total_usd"], (str, int, float))
    ):
        raise CaptureError("PROPOSAL_TOTAL_TYPE_INVALID")
    if compliance["itar_scope_determination"] not in {
        None,
        "SUBJECT_TO_ITAR",
        "NOT_SUBJECT_TO_ITAR",
    }:
        raise CaptureError("ITAR_SCOPE_VALUE_INVALID")
    if approval["approval_utc"] is not None and not GATE.valid_timestamp(
        approval["approval_utc"]
    ):
        raise CaptureError("APPROVAL_TIMESTAMP_INVALID")
    if approval["approval_binding_sha256"] is not None and not GATE.valid_sha256(
        approval["approval_binding_sha256"]
    ):
        raise CaptureError("APPROVAL_BINDING_INVALID")
    return record


def reject_forbidden_text(value: str, field: str) -> None:
    if len(value) > 256:
        raise CaptureError(f"{field.upper()}_TOO_LONG")
    lowered = value.casefold()
    if any(marker in lowered for marker in FORBIDDEN_TEXT_MARKERS):
        raise CaptureError("CREDENTIAL_LIKE_VALUE_REJECTED")


def ensure_private_record_has_no_credential_material(payload: dict[str, Any]) -> None:
    proposal = payload["proposal"]
    for field in ("proposal_number",):
        value = proposal[field]
        if isinstance(value, str):
            reject_forbidden_text(value, field)


def load_template(template_path: Path = TEMPLATE) -> dict[str, Any]:
    try:
        payload = json.loads(template_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError("PRIVATE_TEMPLATE_UNREADABLE") from exc
    clean = deepcopy(validate_payload_shape(payload))
    clean["captured_utc"] = None
    for field in GATE.IDENTITY_GATES:
        clean["identity"][field] = False
    for field in GATE.PROPOSAL_FLAG_GATES:
        clean["proposal"][field] = False
    for field in GATE.PROPOSAL_VALUE_KEYS | GATE.PROPOSAL_CONSISTENCY_KEYS:
        clean["proposal"][field] = None
    for field in GATE.COMPLIANCE_GATES:
        clean["eligibility_and_compliance"][field] = False
    clean["eligibility_and_compliance"]["itar_scope_determination"] = None
    for field in GATE.APPROVAL_FLAG_GATES:
        clean["approval"][field] = False
    for field in GATE.APPROVAL_VALUE_KEYS | GATE.APPROVAL_CONSISTENCY_KEYS:
        clean["approval"][field] = None
    return clean


def load_or_initialize_private_record(
    target: Path, *, template_path: Path = TEMPLATE
) -> tuple[dict[str, Any], bool]:
    if not target.exists():
        payload = load_template(template_path)
        payload["template_only"] = False
        return payload, False
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError("EXISTING_PRIVATE_INPUT_UNREADABLE") from exc
    payload = deepcopy(validate_payload_shape(payload))
    ensure_private_record_has_no_credential_material(payload)
    payload["template_only"] = False
    return payload, True


def choose_bool(
    label: str,
    current: bool,
    *,
    prompt: Callable[[str], str],
) -> bool:
    while True:
        raw = prompt(f"{label} [Y/N/K=keep] (hidden): ").strip().casefold()
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        if raw in {"k", "keep", ""}:
            return current
        print("Invalid selection. Enter Y, N, or K.")


def choose_proposal_number(
    current: str | None, *, prompt: Callable[[str], str]
) -> str | None:
    while True:
        raw = prompt(
            "Assigned DSIP proposal number (hidden; blank keeps current; CLEAR removes): "
        ).strip()
        if not raw:
            return current
        if raw.casefold() == "clear":
            return None
        try:
            reject_forbidden_text(raw, "proposal_number")
        except CaptureError:
            print("Rejected. This field accepts only the assigned proposal number, never a credential.")
            continue
        if GATE.valid_proposal_number(raw):
            return raw
        print("Invalid proposal-number format.")


def choose_sha256(
    label: str,
    current: str | None,
    *,
    prompt: Callable[[str], str],
) -> str | None:
    while True:
        raw = prompt(f"{label} SHA-256 (hidden; blank keeps current; CLEAR removes): ").strip()
        if not raw:
            return current
        if raw.casefold() == "clear":
            return None
        if GATE.valid_sha256(raw):
            return raw.upper()
        print("Invalid SHA-256. Enter exactly 64 hexadecimal characters.")


def choose_phase_i_total(
    current: str | int | float | None,
    *,
    prompt: Callable[[str], str],
) -> str | None:
    while True:
        raw = prompt(
            "Volume 3 Phase I total USD (hidden; blank keeps current; CLEAR removes): "
        ).strip()
        if not raw:
            return None if current is None else str(current)
        if raw.casefold() == "clear":
            return None
        try:
            amount = Decimal(raw.replace(",", ""))
        except InvalidOperation:
            print("Invalid amount. Enter a nonnegative USD amount with at most two decimals.")
            continue
        if not amount.is_finite() or amount < 0 or amount > GATE.PHASE_I_CEILING:
            print("Amount must be between $0 and the official Phase I ceiling.")
            continue
        if amount.as_tuple().exponent < -2:
            print("Amount may contain at most two decimal places.")
            continue
        return format(amount.quantize(Decimal("0.01")), "f")


def choose_itar_scope(
    current: str | None, *, prompt: Callable[[str], str]
) -> str | None:
    menu = (
        "ITAR scope determination\n"
        "  1. SUBJECT_TO_ITAR\n"
        "  2. NOT_SUBJECT_TO_ITAR\n"
        "  3. UNRESOLVED\n"
        "  K. Keep current\n"
        "Selection (hidden): "
    )
    while True:
        raw = prompt(menu).strip().casefold()
        if raw == "1":
            return "SUBJECT_TO_ITAR"
        if raw == "2":
            return "NOT_SUBJECT_TO_ITAR"
        if raw == "3":
            return None
        if raw in {"k", "keep", ""}:
            return current
        print("Invalid selection. Enter 1, 2, 3, or K.")


def collect_identity(payload: dict[str, Any], *, prompt: Callable[[str], str]) -> None:
    section = payload["identity"]
    for field in GATE.IDENTITY_GATES:
        section[field] = choose_bool(
            IDENTITY_LABELS[field], section[field], prompt=prompt
        )


def hash_receipt_file(path: Path) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size <= 0:
        raise CaptureError("PREVIEW_RECEIPT_NOT_REGULAR_FILE")
    before = path.stat()
    digest = GATE.sha256_file(path)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise CaptureError("PREVIEW_RECEIPT_CHANGED_DURING_HASH")
    return digest


def capture_preview_receipt(
    path: Path,
    *,
    reference_utc: datetime,
) -> tuple[str, str]:
    digest = hash_receipt_file(path)
    modified_utc = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
    if not GATE.timestamp_is_fresh(
        modified_utc.isoformat(),
        reference_utc=reference_utc,
        max_age=GATE.PREVIEW_RECEIPT_MAX_AGE,
    ):
        raise CaptureError("PREVIEW_RECEIPT_NOT_FRESH")
    return digest, modified_utc.isoformat()


def hash_private_final_volume2() -> str:
    try:
        target = GATE.validate_private_target(GATE.PRIVATE_FINAL_VOLUME2_PDF)
    except GATE.MissionWeaveGateError as exc:
        raise CaptureError(exc.code) from exc
    if not target.is_file():
        raise CaptureError("PRIVATE_FINAL_VOLUME2_NOT_FOUND")
    return GATE.sha256_file(target)


def clear_action_time_approval(payload: dict[str, Any]) -> None:
    approval = payload["approval"]
    approval["corporate_official_reviewed_all_volumes"] = False
    approval["final_submission_authorized_at_action_time"] = False
    approval["approval_utc"] = None
    approval["approval_binding_sha256"] = None


def clear_preview_evidence(payload: dict[str, Any]) -> None:
    proposal = payload["proposal"]
    proposal["portal_preview_reviewed"] = False
    proposal["portal_preview_captured_utc"] = None
    proposal["portal_preview_binding_sha256"] = None


def collect_proposal(
    payload: dict[str, Any],
    *,
    prompt: Callable[[str], str],
    use_current_volume2_hash: bool,
    preview_receipt_file: Path | None,
    reference_utc: datetime,
    volume3_artifact_state: dict[str, Any],
    jcp_evidence_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
) -> None:
    section = payload["proposal"]
    section["proposal_number"] = choose_proposal_number(
        section["proposal_number"], prompt=prompt
    )
    for field in GATE.PROPOSAL_FLAG_GATES:
        section[field] = choose_bool(
            PROPOSAL_LABELS[field], section[field], prompt=prompt
        )
    if use_current_volume2_hash:
        section["volume2_pdf_sha256"] = hash_private_final_volume2()
    else:
        section["volume2_pdf_sha256"] = choose_sha256(
            "Rebuilt Volume 2 PDF",
            section["volume2_pdf_sha256"],
            prompt=prompt,
        )
    section["volume3_total_usd"] = choose_phase_i_total(
        section["volume3_total_usd"], prompt=prompt
    )
    if preview_receipt_file is not None:
        preview_sha256, preview_captured_utc = capture_preview_receipt(
            preview_receipt_file, reference_utc=reference_utc
        )
        section["portal_preview_sha256"] = preview_sha256
        section["portal_preview_captured_utc"] = preview_captured_utc
        section["portal_preview_binding_sha256"] = (
            GATE.preview_evidence_binding_sha256(
                payload,
                volume3_artifact_state=volume3_artifact_state,
                jcp_evidence_state=jcp_evidence_state,
                cmmc_packet_state=cmmc_packet_state,
            )
        )
    else:
        prior_preview_sha256 = section["portal_preview_sha256"]
        section["portal_preview_sha256"] = choose_sha256(
            "Complete portal preview receipt",
            prior_preview_sha256,
            prompt=prompt,
        )
        if (
            section["portal_preview_sha256"] is None
            or section["portal_preview_sha256"] != prior_preview_sha256
        ):
            section["portal_preview_captured_utc"] = None
            section["portal_preview_binding_sha256"] = None


def collect_compliance(
    payload: dict[str, Any], *, prompt: Callable[[str], str]
) -> None:
    section = payload["eligibility_and_compliance"]
    for field in GATE.COMPLIANCE_GATES:
        section[field] = choose_bool(
            COMPLIANCE_LABELS[field], section[field], prompt=prompt
        )
    section["itar_scope_determination"] = choose_itar_scope(
        section["itar_scope_determination"], prompt=prompt
    )


def collect_approval(
    payload: dict[str, Any],
    *,
    prompt: Callable[[str], str],
    reference_utc: datetime,
    volume3_artifact_state: dict[str, Any],
    jcp_evidence_state: dict[str, Any],
    cmmc_packet_state: dict[str, Any],
) -> None:
    section = payload["approval"]
    section["corporate_official_reviewed_all_volumes"] = choose_bool(
        "The corporate official reviewed every populated field and all seven volumes",
        section["corporate_official_reviewed_all_volumes"],
        prompt=prompt,
    )
    section["final_submission_authorized_at_action_time"] = choose_bool(
        "The corporate official authorizes the final DSIP submission at this action time",
        section["final_submission_authorized_at_action_time"],
        prompt=prompt,
    )
    if section["final_submission_authorized_at_action_time"]:
        if not section["corporate_official_reviewed_all_volumes"]:
            raise CaptureError("APPROVAL_REQUIRES_ALL_VOLUME_REVIEW")
        proposal = payload["proposal"]
        expected_preview_binding = GATE.preview_evidence_binding_sha256(
            payload,
            volume3_artifact_state=volume3_artifact_state,
            jcp_evidence_state=jcp_evidence_state,
            cmmc_packet_state=cmmc_packet_state,
        )
        recorded_preview_binding = proposal.get("portal_preview_binding_sha256")
        preview_fresh = bool(
            GATE.valid_sha256(proposal.get("portal_preview_sha256"))
            and GATE.timestamp_is_fresh(
                proposal.get("portal_preview_captured_utc"),
                reference_utc=reference_utc,
                max_age=GATE.PREVIEW_RECEIPT_MAX_AGE,
            )
            and expected_preview_binding is not None
            and GATE.valid_sha256(recorded_preview_binding)
            and hmac.compare_digest(
                str(recorded_preview_binding).upper(), expected_preview_binding
            )
        )
        if (
            not preview_fresh
            or proposal.get("portal_preview_reviewed") is not True
            or proposal.get("volume5_upload_set_reviewed") is not True
        ):
            raise CaptureError("APPROVAL_REQUIRES_FRESH_CURRENT_PREVIEW")
        section["approval_utc"] = reference_utc.isoformat()
        section["approval_binding_sha256"] = (
            GATE.action_time_approval_binding_sha256(
                payload,
                approval_utc=section["approval_utc"],
                volume3_artifact_state=volume3_artifact_state,
                jcp_evidence_state=jcp_evidence_state,
                cmmc_packet_state=cmmc_packet_state,
            )
        )
    else:
        section["approval_utc"] = None
        section["approval_binding_sha256"] = None


def normalize_sections(requested: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for name in requested:
        if name not in SECTION_ALIASES:
            raise CaptureError("UNKNOWN_CAPTURE_SECTION")
        for section in SECTION_ALIASES[name]:
            if section not in normalized:
                normalized.append(section)
    return tuple(normalized)


def atomic_write_json(
    target: Path,
    payload: dict[str, Any],
    *,
    replacer: Callable[
        [str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None
    ]
    | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    replace = replacer or os.replace
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=target.parent,
            prefix=".missionweave-dsip-private-",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o600)
        replace(temporary_path, target)
        temporary_path = None
    except OSError as exc:
        raise CaptureError("ATOMIC_PRIVATE_WRITE_FAILED") from exc
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def capture_private_sections(
    sections: list[str],
    *,
    prompt: Callable[[str], str] = getpass.getpass,
    target: Path = DEFAULT_OUTPUT,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    template_path: Path = TEMPLATE,
    ignored_checker: Callable[[Path], bool] | None = None,
    replacer: Callable[
        [str | bytes | os.PathLike[str], str | bytes | os.PathLike[str]], None
    ]
    | None = None,
    use_current_volume2_hash: bool = False,
    preview_receipt_file: Path | None = None,
    source_state: dict[str, Any] | None = None,
    volume2_text: str | None = None,
    volume3_artifact_state: dict[str, Any] | None = None,
    jcp_evidence_state: dict[str, Any] | None = None,
    cmmc_packet_state: dict[str, Any] | None = None,
    reference_utc: datetime | str | None = None,
) -> dict[str, Any]:
    selected = normalize_sections(sections)
    if not selected:
        raise CaptureError("NO_CAPTURE_SECTION_SELECTED")
    if preview_receipt_file is not None and selected != ("proposal",):
        raise CaptureError("PREVIEW_RECEIPT_REQUIRES_PROPOSAL_ONLY")
    if use_current_volume2_hash and "proposal" not in selected:
        raise CaptureError("VOLUME2_HASH_REQUIRES_PROPOSAL_SECTION")
    if "approval" in selected and selected != ("approval",):
        raise CaptureError("APPROVAL_SECTION_MUST_BE_CAPTURED_SEPARATELY")
    try:
        evaluated_utc = GATE.normalize_reference_time(reference_utc)
    except GATE.MissionWeaveGateError as exc:
        raise CaptureError(exc.code) from exc

    destination = validate_private_target(
        target,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    payload, resumed = load_or_initialize_private_record(
        destination, template_path=template_path
    )
    if volume3_artifact_state is None:
        volume3_artifact_state = GATE.inspect_private_volume3_artifact()
    if jcp_evidence_state is None:
        jcp_evidence_state = GATE.inspect_private_jcp_evidence()
    if cmmc_packet_state is None:
        cmmc_packet_state = GATE.inspect_cmmc_evidence_packet()

    upload_identity_before = GATE.current_upload_set_identity_sha256(
        payload,
        volume3_artifact_state=volume3_artifact_state,
        jcp_evidence_state=jcp_evidence_state,
        cmmc_packet_state=cmmc_packet_state,
    )
    if selected != ("approval",):
        clear_action_time_approval(payload)

    for section in selected:
        if section == "identity":
            collect_identity(payload, prompt=prompt)
        elif section == "proposal":
            collect_proposal(
                payload,
                prompt=prompt,
                use_current_volume2_hash=use_current_volume2_hash,
                preview_receipt_file=preview_receipt_file,
                reference_utc=evaluated_utc,
                volume3_artifact_state=volume3_artifact_state,
                jcp_evidence_state=jcp_evidence_state,
                cmmc_packet_state=cmmc_packet_state,
            )
        elif section == "eligibility_and_compliance":
            collect_compliance(payload, prompt=prompt)
        elif section == "approval":
            collect_approval(
                payload,
                prompt=prompt,
                reference_utc=evaluated_utc,
                volume3_artifact_state=volume3_artifact_state,
                jcp_evidence_state=jcp_evidence_state,
                cmmc_packet_state=cmmc_packet_state,
            )
        else:
            raise CaptureError("UNKNOWN_CAPTURE_SECTION")

    upload_identity_after = GATE.current_upload_set_identity_sha256(
        payload,
        volume3_artifact_state=volume3_artifact_state,
        jcp_evidence_state=jcp_evidence_state,
        cmmc_packet_state=cmmc_packet_state,
    )
    if (
        selected != ("approval",)
        and preview_receipt_file is None
        and upload_identity_after != upload_identity_before
    ):
        clear_preview_evidence(payload)

    payload["template_only"] = False
    payload["captured_utc"] = evaluated_utc.isoformat()
    validate_payload_shape(payload)
    ensure_private_record_has_no_credential_material(payload)

    if source_state is None or volume2_text is None:
        use_private_final = GATE.PRIVATE_FINAL_VOLUME2_PDF.is_file()
        source_state, volume2_text = GATE.inspect_source_package(
            GATE.PRIVATE_FINAL_VOLUME2_PDF if use_private_final else GATE.VOLUME2_PDF,
            private_final=use_private_final,
        )
    try:
        evaluation = GATE.evaluate_private_payload(
            payload,
            source_state=source_state,
            volume2_text=volume2_text,
            volume3_artifact_state=volume3_artifact_state,
            jcp_evidence_state=jcp_evidence_state,
            cmmc_packet_state=cmmc_packet_state,
            evaluated_utc=evaluated_utc,
        )
    except GATE.MissionWeaveGateError as exc:
        raise CaptureError(exc.code) from exc

    atomic_write_json(destination, payload, replacer=replacer)
    ready = evaluation["all_private_gates_pass"]
    return {
        "schema": "lumencore.missionweave_dsip_private_capture_receipt.v1",
        "status": (
            "PRIVATE_INPUT_COMPLETE_READY_FOR_PUBLIC_GATE"
            if ready
            else "PRIVATE_INPUT_SECTION_CAPTURED_GATES_OPEN"
        ),
        "sections_updated": list(selected),
        "approval_section_explicitly_requested": "approval" in selected,
        "existing_private_input_resumed": resumed,
        "output": destination.relative_to(root.resolve()).as_posix(),
        "target_git_ignored": True,
        "atomic_write_completed": True,
        "gate_summary": {
            "required_gate_count": evaluation["required_gate_count"],
            "passed_gate_count": evaluation["passed_gate_count"],
            "open_gate_count": evaluation["open_gate_count"],
            "unresolved_gates": evaluation["unresolved_gates"],
        },
        "action_time_authorization_gate_passed": evaluation[
            "action_time_authorized"
        ],
        "credential_values_requested": False,
        "firm_pin_value_requested": False,
        "private_values_returned_or_printed": False,
        "private_values_written_to_public_artifact": False,
        "browser_navigation_performed": False,
        "external_send_performed": False,
        "portal_submission_performed": False,
        "next_action": (
            "Run the public MissionWeave action gate, review the complete portal preview, and stop for the final human click."
            if ready
            else "Resolve only the listed gates, rerun the needed hidden-input section, and keep final approval separate until action time."
        ),
    }


def inspect_readiness(
    target: Path = DEFAULT_OUTPUT,
    *,
    root: Path = ROOT,
    private_dir: Path = PRIVATE_DIR,
    ignored_checker: Callable[[Path], bool] | None = None,
) -> dict[str, Any]:
    destination = validate_private_target(
        target,
        root=root,
        private_dir=private_dir,
        ignored_checker=ignored_checker,
    )
    return {
        "schema": "lumencore.missionweave_dsip_private_capture_readiness.v1",
        "status": "READY_FOR_HIDDEN_SECTION_CAPTURE",
        "output": destination.relative_to(root.resolve()).as_posix(),
        "output_exists": destination.exists(),
        "supported_sections": list(SECTION_ALIASES),
        "pre_submit_excludes_action_time_approval": True,
        "target_git_ignored": True,
        "private_file_contents_read": False,
        "private_values_returned_or_printed": False,
        "credential_values_accepted": False,
        "firm_pin_value_accepted": False,
        "browser_navigation_performed": False,
        "portal_submission_performed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture bounded MissionWeave DSIP facts through hidden local prompts. "
            "The collector never requests a Firm PIN or login credential."
        )
    )
    parser.add_argument(
        "--check-target",
        action="store_true",
        help="Validate the ignored target without reading its private contents",
    )
    parser.add_argument(
        "--section",
        action="append",
        choices=tuple(SECTION_ALIASES),
        help=(
            "Capture one section; repeat as needed. pre-submit expands to identity, "
            "proposal, and compliance but intentionally excludes action-time approval."
        ),
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--use-current-volume2-hash",
        action="store_true",
        help=(
            "Hash the ignored assigned-number final Volume 2 PDF instead of requesting "
            "a hash; fails closed when the guarded finalizer has not produced it"
        ),
    )
    parser.add_argument(
        "--preview-receipt-file",
        type=Path,
        help="Hash a local portal-preview receipt without storing or printing its path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        if args.check_target:
            if args.section or args.use_current_volume2_hash or args.preview_receipt_file:
                raise CaptureError("CHECK_TARGET_CANNOT_CAPTURE")
            receipt = inspect_readiness(args.output)
        else:
            if not args.section:
                raise CaptureError("NO_CAPTURE_SECTION_SELECTED")
            receipt = capture_private_sections(
                args.section,
                target=args.output,
                use_current_volume2_hash=args.use_current_volume2_hash,
                preview_receipt_file=args.preview_receipt_file,
            )
        print(json.dumps(receipt, indent=2, sort_keys=True))
    except CaptureError as exc:
        print(
            json.dumps(
                {
                    "status": "PRIVATE_CAPTURE_NOT_COMPLETED",
                    "error_code": exc.code,
                    "private_values_returned_or_printed": False,
                    "credential_values_requested": False,
                    "firm_pin_value_requested": False,
                    "browser_navigation_performed": False,
                    "portal_submission_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
