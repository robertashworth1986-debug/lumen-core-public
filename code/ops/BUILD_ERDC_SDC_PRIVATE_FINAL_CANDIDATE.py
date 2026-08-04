from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any

from pypdf import PdfReader


ROOT = Path(__file__).resolve().parents[2]
SPRINT_DIR = ROOT / "grant_submissions" / "funding_sprint_20260709"
PRIVATE_DIR = SPRINT_DIR / "private" / "W912HZ26SC005"
DEFAULT_PRIVATE_INPUT = PRIVATE_DIR / "ERDC_SDC_PRIVATE_FINAL.private.json"
DEFAULT_ROM_INPUT = PRIVATE_DIR / "ERDC_SDC_PHASE2_ROM.private.json"
PRIVATE_PDF = (
    PRIVATE_DIR
    / "LumenCore_ERDC_SDC_Solution_Brief_PRIVATE_FINAL_CANDIDATE_2026-07-29.pdf"
)
TEMPLATE = ROOT / "config" / "erdc_sdc_private_final_template_v1.json"
OUT_JSON = SPRINT_DIR / "ERDC_SDC_PRIVATE_FINAL_CANDIDATE_GATE_2026-07-29.json"
OUT_MD = SPRINT_DIR / "ERDC_SDC_PRIVATE_FINAL_CANDIDATE_GATE_2026-07-29.md"
PUBLIC_BUILDER_PATH = ROOT / "code" / "ops" / "BUILD_ERDC_SDC_SOLUTION_BRIEF.py"
ROM_GATE_PATH = ROOT / "code" / "ops" / "BUILD_ERDC_SDC_PHASE2_ROM_GATE.py"

PRIVATE_SCHEMA = "lumencore.erdc_sdc_private_final.v1"
PUBLIC_SCHEMA = "lumencore.erdc_sdc_private_final_candidate_gate.v1"
OPPORTUNITY_NUMBER = "W912HZ26SC005"
RECENCY_WINDOW = timedelta(hours=72)
PLACEHOLDER_PATTERN = re.compile(
    r"(?:<[^>]+>|\b(?:TODO|TBD|INSERT|REPLACE|EXAMPLE|PLACEHOLDER)\b)",
    re.IGNORECASE,
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
FORBIDDEN_FINAL_MARKERS = (
    "PUBLIC-SAFE DRAFT",
    "DRAFT - NOT FOR SUBMISSION",
    "SUBMISSION BLOCKER",
    "No price is included",
    "Insert privately",
    "REQUIRED PRICE AND PRIVATE SAM-MATCHED IDENTITY ARE NOT INCLUDED",
)
EXPECTED_DELIVERY = {
    "classified_work_proposed": False,
    "evaluator_status": "REQUESTED_NOT_COMMITTED",
    "government_or_prime_integration_owner": True,
    "production_cloud_capacity_committed": False,
    "production_hpc_allocation_committed": False,
    "support_boundary": "BOUNDED_PHASE_II_PROTOTYPE_SUPPORT_ONLY",
    "technical_lead_role": "Founder / Principal Investigator",
    "technical_lead_status": "PROPOSED",
    "transition_owner": "GOVERNMENT_OR_SELECTED_PRIME",
}
REQUIRED_CERTIFICATIONS = (
    "delivery_boundaries_supported",
    "facts_current",
    "founder_approved_private_pdf_candidate",
    "no_invented_commitments",
    "private_identity_authorized_for_proposal",
)
PUBLIC_CLAIM_BOUNDARY = (
    "This public gate reports only whether a guarded private PDF candidate was built and "
    "whether bounded document checks passed. It does not publish the private price, identity, "
    "address, contact, input paths, private PDF path, or private fingerprints. The candidate "
    "is not submission-ready, has not been uploaded, and does not represent ERDC selection, "
    "available funding, an award, deployment, authorization to operate, classified handling, "
    "field validation, customers, revenue, realized savings, or independently validated performance."
)


class PrivateFinalError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PrivateFinalError("DEPENDENCY_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def validate_private_target(path: Path, *, require_file: bool) -> Path:
    if path.is_symlink():
        raise PrivateFinalError("PRIVATE_TARGET_SYMLINK_REJECTED")
    resolved = path.resolve()
    if not path_is_within(resolved, PRIVATE_DIR):
        raise PrivateFinalError("PRIVATE_TARGET_OUTSIDE_BOUNDED_DIRECTORY")
    if require_file and not resolved.is_file():
        raise PrivateFinalError("PRIVATE_INPUT_NOT_FOUND")
    if resolved.exists() and not resolved.is_file():
        raise PrivateFinalError("PRIVATE_TARGET_NOT_REGULAR_FILE")
    if not git_ignored(resolved):
        raise PrivateFinalError("PRIVATE_TARGET_NOT_GIT_IGNORED")
    return resolved


def required_text(value: Any, field: str, *, maximum: int = 160) -> str:
    if not isinstance(value, str):
        raise PrivateFinalError(f"{field}_REQUIRED")
    text = " ".join(value.split())
    if not text or len(text) > maximum or PLACEHOLDER_PATTERN.search(text):
        raise PrivateFinalError(f"{field}_INVALID")
    return text


def recent_timestamp(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise PrivateFinalError(f"{field}_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise PrivateFinalError(f"{field}_INVALID") from None
    if parsed.tzinfo is None:
        raise PrivateFinalError(f"{field}_TIMEZONE_REQUIRED")
    parsed = parsed.astimezone(timezone.utc)
    current = datetime.now(timezone.utc)
    if parsed > current + timedelta(minutes=5):
        raise PrivateFinalError(f"{field}_IN_FUTURE")
    if current - parsed > RECENCY_WINDOW:
        raise PrivateFinalError(f"{field}_STALE")
    return parsed


def format_solution_address(value: Any) -> str:
    if not isinstance(value, dict):
        raise PrivateFinalError("SOLUTION_ADDRESS_REQUIRED")
    expected = {"country", "lines", "locality", "postal_code", "region"}
    if set(value) != expected:
        raise PrivateFinalError("SOLUTION_ADDRESS_FIELDS_INVALID")
    lines = value.get("lines")
    if not isinstance(lines, list) or not 1 <= len(lines) <= 3:
        raise PrivateFinalError("SOLUTION_ADDRESS_LINES_INVALID")
    parts = [
        *[
            required_text(line, "SOLUTION_ADDRESS_LINE", maximum=120)
            for line in lines
        ],
        required_text(value.get("locality"), "SOLUTION_ADDRESS_LOCALITY", maximum=80),
        required_text(value.get("region"), "SOLUTION_ADDRESS_REGION", maximum=80),
        required_text(
            value.get("postal_code"), "SOLUTION_ADDRESS_POSTAL_CODE", maximum=24
        ),
        required_text(value.get("country"), "SOLUTION_ADDRESS_COUNTRY", maximum=80),
    ]
    return ", ".join(parts)


def validate_private_identity(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("schema") != PRIVATE_SCHEMA:
        raise PrivateFinalError("PRIVATE_SCHEMA_MISMATCH")
    if payload.get("opportunity_number") != OPPORTUNITY_NUMBER:
        raise PrivateFinalError("OPPORTUNITY_NUMBER_MISMATCH")
    if payload.get("template_only") is True:
        raise PrivateFinalError("TEMPLATE_CANNOT_BE_USED_AS_PRIVATE_INPUT")

    legal_entity_name = required_text(
        payload.get("legal_entity_name"), "LEGAL_ENTITY_NAME", maximum=180
    )
    solution_address = format_solution_address(payload.get("solution_address"))

    contact = payload.get("proposal_contact")
    if not isinstance(contact, dict) or set(contact) != {
        "email",
        "name",
        "verified_current",
    }:
        raise PrivateFinalError("PROPOSAL_CONTACT_FIELDS_INVALID")
    contact_name = required_text(
        contact.get("name"), "PROPOSAL_CONTACT_NAME", maximum=120
    )
    contact_email = required_text(
        contact.get("email"), "PROPOSAL_CONTACT_EMAIL", maximum=254
    )
    if not EMAIL_PATTERN.fullmatch(contact_email):
        raise PrivateFinalError("PROPOSAL_CONTACT_EMAIL_INVALID")
    if contact.get("verified_current") is not True:
        raise PrivateFinalError("PROPOSAL_CONTACT_NOT_VERIFIED")

    sam = payload.get("sam_verification")
    if not isinstance(sam, dict) or set(sam) != {
        "all_awards_registration_active",
        "exact_legal_name_match",
        "exact_solution_address_match",
        "verified_utc",
    }:
        raise PrivateFinalError("SAM_VERIFICATION_FIELDS_INVALID")
    for key in (
        "all_awards_registration_active",
        "exact_legal_name_match",
        "exact_solution_address_match",
    ):
        if sam.get(key) is not True:
            raise PrivateFinalError(f"SAM_{key.upper()}_REQUIRED")
    recent_timestamp(sam.get("verified_utc"), "SAM_VERIFIED_UTC")

    delivery = payload.get("delivery")
    if not isinstance(delivery, dict) or delivery != EXPECTED_DELIVERY:
        raise PrivateFinalError("DELIVERY_BOUNDARY_MISMATCH")

    certifications = payload.get("certifications")
    if not isinstance(certifications, dict) or set(certifications) != set(
        REQUIRED_CERTIFICATIONS
    ):
        raise PrivateFinalError("CERTIFICATION_FIELDS_INVALID")
    for key in REQUIRED_CERTIFICATIONS:
        if certifications.get(key) is not True:
            raise PrivateFinalError(f"CERTIFICATION_{key.upper()}_REQUIRED")
    recent_timestamp(payload.get("approval_utc"), "APPROVAL_UTC")

    return {
        "legal_entity_name": legal_entity_name,
        "solution_address": solution_address,
        "proposal_contact_name": contact_name,
        "proposal_contact_email": contact_email,
    }


def load_private_json(path: Path) -> dict[str, Any]:
    target = validate_private_target(path, require_file=True)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise PrivateFinalError("PRIVATE_INPUT_NOT_VALID_JSON") from None
    if not isinstance(payload, dict):
        raise PrivateFinalError("PRIVATE_INPUT_NOT_OBJECT")
    return payload


def delivery_statement() -> str:
    return (
        "The Founder / Principal Investigator is the proposed technical lead for the "
        "evidence module and public code. The Government or selected prime owns authorized "
        "interfaces, access, security, and integration. An evaluator role is requested but "
        "not committed. Surrogate development uses contractor-furnished commodity CPU, local "
        "storage, and open software; no production HPC allocation or cloud capacity is "
        "committed. Support is limited to bounded Phase II prototype support, not Level 3 "
        "operations. Transition ownership remains with the Government or selected prime. "
        "No classified work is proposed."
    )


def format_rom(value: Decimal) -> str:
    return f"${value:,.2f}"


def private_pdf_checks(
    path: Path,
    *,
    public_builder: ModuleType,
    evidence: dict[str, Any],
    rom_display: str,
) -> dict[str, Any]:
    inspection = public_builder.inspect_pdf(
        path,
        evidence=evidence,
        document_mode="PRIVATE_FINAL_CANDIDATE",
    )
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    raw = path.read_bytes()
    forbidden_absent = all(marker not in text for marker in FORBIDDEN_FINAL_MARKERS)
    currency_tokens = re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", text)
    active_content_absent = not any(
        token in raw
        for token in (
            b"/JavaScript",
            b"/OpenAction",
            b"/EmbeddedFiles",
            b"/Launch",
        )
    )
    annotations_absent = all("/Annots" not in page for page in reader.pages)
    metadata = reader.metadata or {}
    metadata_text = " ".join(str(value) for value in metadata.values())
    private_values_absent_from_metadata = (
        rom_display not in metadata_text and "$" not in metadata_text
    )
    checks = {
        "physical_page_count": inspection["physical_page_count"],
        "body_page_count": inspection["body_page_count"],
        "bytes": inspection["bytes"],
        "letter_portrait": inspection["all_pages_letter_portrait"],
        "one_inch_text_margins": inspection[
            "all_non_watermark_text_within_one_inch_margins"
        ],
        "all_content_text_12_point": inspection[
            "all_detected_content_text_12_point"
        ],
        "times_new_roman_detected": inspection["times_new_roman_detected"],
        "physical_page_labels_present": inspection[
            "all_physical_page_labels_present"
        ],
        "body_page_labels_present": inspection["body_page_labels_present"],
        "required_content_markers_present": inspection[
            "required_content_markers_present"
        ],
        "required_acronym_entries_present": inspection[
            "required_acronym_entries_present"
        ],
        "evidence_marker_present": inspection["evidence_ablation_marker_present"],
        "private_candidate_marker_present": inspection[
            "private_candidate_marker_present"
        ],
        "draft_watermark_absent": inspection["draft_watermark_absent_every_page"],
        "forbidden_final_markers_absent": forbidden_absent,
        "exactly_one_phase_ii_total": (
            text.count(rom_display) == 1
            and len(currency_tokens) == 1
            and currency_tokens[0].replace(" ", "") == rom_display
        ),
        "active_content_absent": active_content_absent,
        "annotations_absent": annotations_absent,
        "private_values_absent_from_metadata": private_values_absent_from_metadata,
        "under_20_mb": inspection["bytes"] < 20 * 1024 * 1024,
    }
    checks["all_checks_pass"] = all(
        (
            checks["physical_page_count"] == 7,
            checks["body_page_count"] == 5,
            checks["letter_portrait"],
            checks["one_inch_text_margins"],
            checks["all_content_text_12_point"],
            checks["times_new_roman_detected"],
            checks["physical_page_labels_present"],
            checks["body_page_labels_present"],
            checks["required_content_markers_present"],
            checks["required_acronym_entries_present"],
            checks["evidence_marker_present"],
            checks["private_candidate_marker_present"],
            checks["draft_watermark_absent"],
            checks["forbidden_final_markers_absent"],
            checks["exactly_one_phase_ii_total"],
            checks["active_content_absent"],
            checks["annotations_absent"],
            checks["private_values_absent_from_metadata"],
            checks["under_20_mb"],
        )
    )
    return checks


def build_private_candidate(
    *,
    private_input: Path,
    rom_input: Path,
    output_pdf: Path = PRIVATE_PDF,
) -> dict[str, Any]:
    output_target = validate_private_target(output_pdf, require_file=False)
    identity_payload = load_private_json(private_input)
    identity = validate_private_identity(identity_payload)

    rom_gate = load_module("erdc_sdc_phase2_rom_gate_private_final", ROM_GATE_PATH)
    rom_payload, _private_hash = rom_gate.load_private_input(rom_input)
    calculation = rom_gate.calculate_private_rom(rom_payload)
    if not calculation["rom_ready_for_private_pdf_insertion"]:
        raise PrivateFinalError("ROM_NOT_READY_FOR_PRIVATE_PDF_INSERTION")
    rom_display = format_rom(calculation["private_amounts"]["formula_price"])

    public_builder = load_module(
        "erdc_sdc_solution_brief_private_final", PUBLIC_BUILDER_PATH
    )
    sources = public_builder.source_integrity()
    if not sources["all_source_checks_pass"]:
        raise PrivateFinalError("OFFICIAL_SOURCE_INTEGRITY_FAILED")
    evidence = public_builder.evidence_ablation_receipt()
    if not evidence["receipt_checks_pass"]:
        raise PrivateFinalError("EVIDENCE_ABLATION_GATE_FAILED")

    private_context = {
        **identity,
        "delivery_statement": delivery_statement(),
        "rom_display": rom_display,
    }
    output_target.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_target.with_suffix(".building.pdf")
    if temporary.exists():
        temporary.unlink()
    try:
        public_builder.build_pdf(
            temporary,
            evidence=evidence,
            private_context=private_context,
        )
        checks = private_pdf_checks(
            temporary,
            public_builder=public_builder,
            evidence=evidence,
            rom_display=rom_display,
        )
        if not checks["all_checks_pass"]:
            raise PrivateFinalError("PRIVATE_PDF_DOCUMENT_CHECKS_FAILED")
        temporary.replace(output_target)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "candidate_built": True,
        "identity_gate_pass": True,
        "sam_gate_pass": True,
        "contact_gate_pass": True,
        "delivery_gate_pass": True,
        "founder_approval_gate_pass": True,
        "rom_gate_pass": True,
        "source_gate_pass": True,
        "evidence_gate_pass": True,
        "public_preflight_checked": True,
        "public_preflight_error_code": None,
        "pdf_checks": checks,
    }


def baseline_result() -> dict[str, Any]:
    return {
        "candidate_built": False,
        "identity_gate_pass": False,
        "sam_gate_pass": False,
        "contact_gate_pass": False,
        "delivery_gate_pass": False,
        "founder_approval_gate_pass": False,
        "rom_gate_pass": False,
        "source_gate_pass": False,
        "evidence_gate_pass": False,
        "public_preflight_checked": False,
        "public_preflight_error_code": None,
        "pdf_checks": {
            "all_checks_pass": False,
            "private_path_exposed": False,
            "private_fingerprint_exposed": False,
        },
    }


def public_preflight_result() -> dict[str, Any]:
    result = baseline_result()
    try:
        public_builder = load_module(
            "erdc_sdc_solution_brief_public_preflight",
            PUBLIC_BUILDER_PATH,
        )
        sources = public_builder.source_integrity()
        evidence = public_builder.evidence_ablation_receipt()
    except Exception:
        result["public_preflight_checked"] = True
        result["public_preflight_error_code"] = (
            "PUBLIC_PREFLIGHT_DEPENDENCY_CHECK_FAILED"
        )
        return result

    result["source_gate_pass"] = bool(sources.get("all_source_checks_pass"))
    result["evidence_gate_pass"] = bool(evidence.get("receipt_checks_pass"))
    result["public_preflight_checked"] = True
    if not result["source_gate_pass"]:
        result["public_preflight_error_code"] = (
            "CURRENT_OFFICIAL_SOURCE_INTEGRITY_FAILED"
        )
    elif not result["evidence_gate_pass"]:
        result["public_preflight_error_code"] = (
            "BOUNDED_EVIDENCE_RECEIPT_FAILED"
        )
    return result


def unresolved_gates(result: dict[str, Any]) -> list[str]:
    gates = []
    mapping = (
        ("identity_gate_pass", "PRIVATE_IDENTITY_CAPTURE_AND_AUTHORIZATION"),
        ("sam_gate_pass", "CURRENT_SAM_ALL_AWARDS_EXACT_MATCH"),
        ("contact_gate_pass", "CURRENT_PROPOSAL_CONTACT"),
        ("delivery_gate_pass", "SUPPORTED_DELIVERY_BOUNDARIES"),
        ("founder_approval_gate_pass", "FOUNDER_PRIVATE_CANDIDATE_APPROVAL"),
        ("rom_gate_pass", "APPROVED_PHASE_II_ONLY_ROM"),
        ("source_gate_pass", "CURRENT_OFFICIAL_SOURCE_INTEGRITY"),
        ("evidence_gate_pass", "BOUNDED_EVIDENCE_RECEIPT"),
    )
    for field, gate in mapping:
        if not result.get(field):
            gates.append(gate)
    if not result.get("candidate_built"):
        gates.append("PRIVATE_FINAL_CANDIDATE_BUILD")
    gates.extend(
        [
            "AUTHENTICATED_SUBMITTABLE_COMPLETE_FORM_REVIEW",
            "CURRENT_AMENDMENTS_AND_QUESTIONS_RECHECK",
            "HUMAN_FINAL_PDF_AND_PORTAL_FIELD_REVIEW",
            "TERMS_REPRESENTATIONS_AND_CERTIFICATIONS_REVIEW",
            "HUMAN_UPLOAD_AND_FINAL_CONFIRMATION",
        ]
    )
    return gates


def build_public_payload(
    result: dict[str, Any],
    *,
    status: str,
    error_code: str | None = None,
) -> dict[str, Any]:
    pdf_checks = result.get("pdf_checks", {})
    payload: dict[str, Any] = {
        "schema": PUBLIC_SCHEMA,
        "generated_utc": now_utc(),
        "opportunity_number": OPPORTUNITY_NUMBER,
        "deadline": {
            "safest_operational_cutoff": "4:00 PM CT on August 7, 2026",
            "question_submission_cutoff": "July 31, 2026",
        },
        "status": status,
        "error_code": error_code,
        "submission_ready": False,
        "private_final_candidate_built": bool(result.get("candidate_built")),
        "private_inputs": {
            "identity_input_present": bool(result.get("identity_gate_pass")),
            "rom_input_present": bool(result.get("rom_gate_pass")),
            "private_values_exposed": False,
            "private_paths_exposed": False,
            "private_fingerprints_exposed": False,
        },
        "validation": {
            "public_preflight_checked": bool(
                result.get("public_preflight_checked")
            ),
            "public_preflight_error_code": result.get(
                "public_preflight_error_code"
            ),
            "sam_exact_match_current": bool(result.get("sam_gate_pass")),
            "proposal_contact_current": bool(result.get("contact_gate_pass")),
            "delivery_boundaries_supported": bool(result.get("delivery_gate_pass")),
            "no_invented_commitments": bool(result.get("delivery_gate_pass")),
            "founder_private_candidate_approval": bool(
                result.get("founder_approval_gate_pass")
            ),
            "phase_ii_only_rom_ready": bool(result.get("rom_gate_pass")),
            "official_source_integrity": bool(result.get("source_gate_pass")),
            "bounded_evidence_receipt": bool(result.get("evidence_gate_pass")),
        },
        "pdf": {
            "document_checks_pass": bool(pdf_checks.get("all_checks_pass")),
            "physical_page_count": pdf_checks.get("physical_page_count"),
            "body_page_count": pdf_checks.get("body_page_count"),
            "bytes": pdf_checks.get("bytes"),
            "exactly_one_phase_ii_total": bool(
                pdf_checks.get("exactly_one_phase_ii_total")
            ),
            "forbidden_final_markers_absent": bool(
                pdf_checks.get("forbidden_final_markers_absent")
            ),
            "draft_watermark_absent": bool(
                pdf_checks.get("draft_watermark_absent")
            ),
            "active_content_absent": bool(
                pdf_checks.get("active_content_absent")
            ),
            "private_path_exposed": False,
            "private_fingerprint_exposed": False,
        },
        "unresolved_gates": unresolved_gates(result),
        "controls": {
            "external_send_allowed": False,
            "final_portal_submit_allowed": False,
            "browser_navigation_performed": False,
            "private_values_allowed_in_public_output": False,
        },
        "private_template": TEMPLATE.resolve().relative_to(ROOT.resolve()).as_posix(),
        "claim_boundary": PUBLIC_CLAIM_BOUNDARY,
        "outputs": {
            "json": OUT_JSON.resolve().relative_to(ROOT.resolve()).as_posix(),
            "markdown": OUT_MD.resolve().relative_to(ROOT.resolve()).as_posix(),
        },
    }
    payload["gate_sha256"] = stable_hash(payload)
    return payload


def ensure_public_safe(
    payload: dict[str, Any],
    *,
    forbidden_private_values: list[str] | None = None,
) -> None:
    serialized = json.dumps(payload, sort_keys=True)
    if re.search(r"\$\s*\d", serialized):
        raise PrivateFinalError("PRIVATE_DOLLAR_AMOUNT_EXPOSED")
    lowered = serialized.casefold()
    for value in forbidden_private_values or []:
        normalized = " ".join(str(value).split()).casefold()
        if normalized and normalized in lowered:
            raise PrivateFinalError("PRIVATE_VALUE_EXPOSED")
    for forbidden_key in (
        "private_pdf_path",
        "private_pdf_sha256",
        "private_input_path",
        "private_input_sha256",
        "private_fingerprint",
    ):
        if f'"{forbidden_key}"' in lowered:
            raise PrivateFinalError("PRIVATE_REFERENCE_EXPOSED")


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# ERDC SDC Private Final Candidate Gate - 2026-07-29",
        "",
        "This public-safe receipt reports gate state without exposing private identity, price, paths, or fingerprints.",
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        f"- Submission ready: `{str(payload['submission_ready']).lower()}`",
        f"- Private candidate built: `{str(payload['private_final_candidate_built']).lower()}`",
        f"- Document checks pass: `{str(payload['pdf']['document_checks_pass']).lower()}`",
        f"- Exactly one Phase II total: `{str(payload['pdf']['exactly_one_phase_ii_total']).lower()}`",
        f"- Forbidden final markers absent: `{str(payload['pdf']['forbidden_final_markers_absent']).lower()}`",
        f"- Draft watermark absent: `{str(payload['pdf']['draft_watermark_absent']).lower()}`",
        f"- Active content absent: `{str(payload['pdf']['active_content_absent']).lower()}`",
        f"- Private values exposed: `{str(payload['private_inputs']['private_values_exposed']).lower()}`",
        f"- Private paths exposed: `{str(payload['private_inputs']['private_paths_exposed']).lower()}`",
        f"- Private fingerprints exposed: `{str(payload['private_inputs']['private_fingerprints_exposed']).lower()}`",
        f"- Public preflight checked: `{str(payload['validation']['public_preflight_checked']).lower()}`",
        f"- Official source integrity: `{str(payload['validation']['official_source_integrity']).lower()}`",
        f"- Bounded evidence receipt: `{str(payload['validation']['bounded_evidence_receipt']).lower()}`",
        f"- Safest operational cutoff: `{payload['deadline']['safest_operational_cutoff']}`",
        f"- Question cutoff: `{payload['deadline']['question_submission_cutoff']}`",
        f"- Gate SHA-256: `{payload['gate_sha256']}`",
        "",
        "## Unresolved Gates",
        "",
    ]
    lines.extend(f"- `{gate}`" for gate in payload["unresolved_gates"])
    lines.extend(
        [
            "",
            "## Controls",
            "",
            "- No email, upload, certification, signature, terms acceptance, or final submission is performed by this builder.",
            "- A successful private PDF build remains a human-review candidate and never becomes submission-ready automatically.",
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
        ]
    )
    return "\n".join(lines)


def write_public_outputs(
    payload: dict[str, Any],
    *,
    forbidden_private_values: list[str] | None = None,
) -> None:
    markdown = render_markdown(payload)
    ensure_public_safe(
        payload,
        forbidden_private_values=forbidden_private_values,
    )
    ensure_public_safe(
        {"markdown": markdown},
        forbidden_private_values=forbidden_private_values,
    )
    OUT_JSON.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    OUT_MD.write_text(markdown, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a guarded private ERDC final-candidate PDF while publishing only "
            "a redacted gate receipt."
        )
    )
    parser.add_argument(
        "--build-private-candidate",
        action="store_true",
        help="Explicitly validate both ignored private inputs and build the private candidate.",
    )
    parser.add_argument("--private-input", type=Path, default=DEFAULT_PRIVATE_INPUT)
    parser.add_argument("--rom-input", type=Path, default=DEFAULT_ROM_INPUT)
    parser.add_argument(
        "--check-targets",
        action="store_true",
        help="Verify bounded ignored targets without reading private values.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.check_targets:
        try:
            targets = (
                validate_private_target(args.private_input, require_file=False),
                validate_private_target(args.rom_input, require_file=False),
                validate_private_target(PRIVATE_PDF, require_file=False),
            )
            print(
                json.dumps(
                    {
                        "status": "PRIVATE_TARGETS_READY",
                        "bounded_target_count": len(targets),
                        "all_targets_git_ignored": True,
                        "private_values_read_or_printed": False,
                        "browser_navigation_performed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            return
        except PrivateFinalError as exc:
            print(
                json.dumps(
                    {
                        "status": "PRIVATE_TARGET_CHECK_FAILED",
                        "error_code": exc.code,
                        "private_values_read_or_printed": False,
                        "browser_navigation_performed": False,
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
            raise SystemExit(1) from None

    if not args.build_private_candidate:
        result = public_preflight_result()
        payload = build_public_payload(
            result,
            status="PRIVATE_FINAL_INPUTS_NOT_CAPTURED",
        )
        write_public_outputs(payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "submission_ready": False,
                    "private_candidate_built": False,
                    "private_values_printed": False,
                    "browser_navigation_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return

    forbidden_private_values: list[str] = []
    try:
        identity_payload = load_private_json(args.private_input)
        identity = validate_private_identity(identity_payload)
        forbidden_private_values.extend(identity.values())
        result = build_private_candidate(
            private_input=args.private_input,
            rom_input=args.rom_input,
        )
        payload = build_public_payload(
            result,
            status="PRIVATE_FINAL_CANDIDATE_BUILT_HUMAN_PORTAL_REVIEW_REQUIRED",
        )
        write_public_outputs(
            payload,
            forbidden_private_values=forbidden_private_values,
        )
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "submission_ready": False,
                    "private_candidate_built": True,
                    "document_checks_pass": payload["pdf"]["document_checks_pass"],
                    "private_values_printed": False,
                    "browser_navigation_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
    except ValueError as exc:
        error_code = getattr(exc, "code", "PRIVATE_FINAL_BUILD_FAILED")
        result = public_preflight_result()
        payload = build_public_payload(
            result,
            status="PRIVATE_FINAL_CANDIDATE_BLOCKED",
            error_code=error_code,
        )
        write_public_outputs(payload)
        print(
            json.dumps(
                {
                    "status": payload["status"],
                    "error_code": error_code,
                    "submission_ready": False,
                    "private_candidate_built": False,
                    "private_values_printed": False,
                    "browser_navigation_performed": False,
                },
                indent=2,
                sort_keys=True,
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
