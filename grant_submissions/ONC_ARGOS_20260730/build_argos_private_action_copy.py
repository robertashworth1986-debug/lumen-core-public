from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt


ARGOS_DIR = Path(__file__).resolve().parent
ROOT = ARGOS_DIR.parents[1]
PUBLIC_MARKDOWN = ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md"
PUBLIC_DOCX = (
    ARGOS_DIR / "output" / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx"
)
SUBMISSION_GATE = ARGOS_DIR / "ARGOS_SUBMISSION_GATE_2026-07-26.json"
TEAM_REGISTER = ARGOS_DIR / "ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json"

NOTICE_ID = "ONC-ARGOS-SSN-2026-OS351107"
FACT_SCHEMA = "lumencore.argos_private_facts.v1"
PRIVATE_MARKER = "ACTION_TIME_PRIVATE_FACT_REQUIRED"
PRIVATE_DISPLAY_MARKER = "Pending action-time fact"
PRIVATE_STATUS = "PRIVATE ACTION COPY - HUMAN REVIEW REQUIRED"
TEXT_OUTPUT_NAME = "ARGOS_PRIVATE_ACTION_COPY.md"
DOCX_OUTPUT_NAME = "ARGOS_PRIVATE_ACTION_COPY.docx"
RECEIPT_OUTPUT_NAME = "ARGOS_PRIVATE_ACTION_COPY_RECEIPT.json"

REQUIRED_FACT_KEYS = (
    "legal_company_name",
    "uei",
    "duns_if_notice_or_entity_record_requires_it",
    "company_address",
    "authorized_point_of_contact_name_and_title",
    "authorized_point_of_contact_phone",
    "authorized_point_of_contact_email",
    "small_business_designations",
    "sam_registration_status_and_expiration",
)
NOT_APPLICABLE_ALLOWED = {"duns_if_notice_or_entity_record_requires_it"}
SOURCE_KINDS = {
    "OFFICIAL_ENTITY_RECORD",
    "OFFICIAL_SAM_RECORD",
    "FOUNDER_VERIFIED_BUSINESS_RECORD",
    "OFFICIAL_CORRESPONDENCE",
}
PROHIBITED_KEYS = {
    "ein",
    "tin",
    "ssn",
    "bank_account",
    "routing_number",
    "password",
    "credential",
    "api_key",
    "otp",
}
MAX_VALUE_LENGTHS = {
    "legal_company_name": 120,
    "uei": 12,
    "duns_if_notice_or_entity_record_requires_it": 14,
    "company_address": 180,
    "authorized_point_of_contact_name_and_title": 120,
    "authorized_point_of_contact_phone": 40,
    "authorized_point_of_contact_email": 254,
    "small_business_designations": 160,
    "sam_registration_status_and_expiration": 120,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def validate_private_path(path: Path, label: str) -> Path:
    resolved = path.expanduser().resolve()
    if is_within(resolved, ROOT):
        raise ValueError(f"{label} must be outside the public repository")
    return resolved


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_fact_value(key: str, fact: dict, evaluated: datetime) -> None:
    if set(fact) != {"value", "status", "source_kind", "verified_utc"}:
        raise ValueError(f"{key} must contain only value, status, source_kind, verified_utc")
    status = fact["status"]
    value = fact["value"]
    if status == "NOT_APPLICABLE":
        if key not in NOT_APPLICABLE_ALLOWED or value != "NOT_APPLICABLE":
            raise ValueError(f"{key} cannot be marked NOT_APPLICABLE")
    elif status != "VERIFIED":
        raise ValueError(f"{key} must be VERIFIED")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must have a non-empty value")
    if len(value) > MAX_VALUE_LENGTHS[key]:
        raise ValueError(f"{key} exceeds the private-cover length limit")
    if any(ord(character) < 32 and character not in "\r\n\t" for character in value):
        raise ValueError(f"{key} contains a prohibited control character")
    if PRIVATE_MARKER in value or PRIVATE_DISPLAY_MARKER in value:
        raise ValueError(f"{key} still contains a placeholder")
    if fact["source_kind"] not in SOURCE_KINDS:
        raise ValueError(f"{key} has an unsupported source_kind")
    verified = parse_utc(fact["verified_utc"])
    if verified > evaluated:
        raise ValueError(f"{key} has a future verification timestamp")

    if key == "uei" and not re.fullmatch(r"[A-Za-z0-9]{12}", value):
        raise ValueError("uei must contain exactly 12 alphanumeric characters")
    if (
        key == "duns_if_notice_or_entity_record_requires_it"
        and status == "VERIFIED"
        and not re.fullmatch(r"\d{9}", value)
    ):
        raise ValueError("a verified DUNS must contain exactly 9 digits")
    if key == "authorized_point_of_contact_email" and not re.fullmatch(
        r"[^@\s]+@[^@\s]+\.[^@\s]+", value
    ):
        raise ValueError("authorized point-of-contact email is malformed")
    if key == "authorized_point_of_contact_phone":
        digits = re.sub(r"\D", "", value)
        if not 10 <= len(digits) <= 15:
            raise ValueError("authorized point-of-contact phone is malformed")


def validate_facts(payload: dict, evaluated: datetime) -> dict:
    expected_top_level = {
        "schema",
        "notice_id",
        "facts",
        "assertions",
    }
    if set(payload) != expected_top_level:
        raise ValueError("private facts file has unexpected top-level fields")
    if payload["schema"] != FACT_SCHEMA:
        raise ValueError("private facts schema is not supported")
    if payload["notice_id"] != NOTICE_ID:
        raise ValueError("private facts notice_id does not match Project Argos")

    facts = payload["facts"]
    if not isinstance(facts, dict):
        raise ValueError("facts must be an object")
    unexpected = set(facts) - set(REQUIRED_FACT_KEYS)
    prohibited = {key for key in unexpected if key.lower() in PROHIBITED_KEYS}
    if prohibited:
        raise ValueError("private facts file contains prohibited sensitive fields")
    if unexpected:
        raise ValueError("private facts file contains fields not required by this response")
    missing = set(REQUIRED_FACT_KEYS) - set(facts)
    if missing:
        raise ValueError("private facts file is missing required fields")
    for key in REQUIRED_FACT_KEYS:
        if not isinstance(facts[key], dict):
            raise ValueError(f"{key} must be an object")
        validate_fact_value(key, facts[key], evaluated)

    assertions = payload["assertions"]
    if set(assertions) != {
        "facts_current_and_accurate",
        "authorized_for_this_response",
        "minimum_necessary_business_information_only",
    }:
        raise ValueError("private facts assertions are incomplete")
    if not all(value is True for value in assertions.values()):
        raise ValueError("every private facts assertion must be explicitly true")
    return facts


def display_values(facts: dict) -> dict[str, str]:
    value = lambda key: facts[key]["value"].strip()
    duns = value("duns_if_notice_or_entity_record_requires_it")
    if facts["duns_if_notice_or_entity_record_requires_it"]["status"] == "NOT_APPLICABLE":
        duns = "Not applicable"
    return {
        "Responding legal entity": value("legal_company_name"),
        "UEI / DUNS if applicable": f"UEI: {value('uei')}; DUNS: {duns}",
        "Company address": value("company_address"),
        "Authorized point of contact": value(
            "authorized_point_of_contact_name_and_title"
        ),
        "Telephone / email": (
            f"{value('authorized_point_of_contact_phone')} / "
            f"{value('authorized_point_of_contact_email')}"
        ),
        "Small-business designation(s)": (
            f"{value('small_business_designations')}; "
            f"SAM: {value('sam_registration_status_and_expiration')}"
        ),
    }


def markdown_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|").replace("\r", " ").replace(
        "\n", " "
    )


def render_private_markdown(template: str, values: dict[str, str]) -> str:
    output = template.replace(
        "**Status:** `DRAFT - HUMAN REVIEW AND ACTION-TIME FACTS REQUIRED`",
        f"**Status:** `{PRIVATE_STATUS}`",
    )
    lines = []
    replaced = set()
    for line in output.splitlines():
        if line.startswith("|") and line.endswith("|"):
            parts = [part.strip() for part in line[1:-1].split("|")]
            if parts and parts[0] in values:
                label = parts[0]
                line = f"| {label} | {markdown_escape(values[label])} |"
                replaced.add(label)
        lines.append(line)
    if replaced != set(values):
        raise ValueError("public Markdown cover fields do not match the finalizer map")
    output = "\n".join(lines).rstrip() + "\n"
    if PRIVATE_MARKER in output or PRIVATE_DISPLAY_MARKER in output:
        raise ValueError("private Markdown still contains a private-fact placeholder")
    handling = (
        "\n**Handling:** Minimum necessary verified business registration and contact "
        "facts only. No tax, banking, credential, patient, CUI, classified, or "
        "patent-sensitive information.\n"
    )
    status_line = f"**Status:** `{PRIVATE_STATUS}`\n"
    return output.replace(status_line, status_line + handling, 1)


def style_private_cell(cell) -> None:
    for paragraph in cell.paragraphs:
        paragraph.paragraph_format.space_after = Pt(0)
        paragraph.paragraph_format.line_spacing = 1.0
        for run in paragraph.runs:
            run.font.name = "Times New Roman"
            run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
            run.font.size = Pt(8.2)


def replace_paragraph_text(
    paragraph,
    text: str,
    *,
    bold: bool,
    italic: bool = False,
    size: float = 10,
) -> None:
    paragraph.text = text
    for run in paragraph.runs:
        run.font.name = "Times New Roman"
        run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), "Times New Roman")
        run.font.size = Pt(size)
        run.bold = bold
        run.italic = italic


def render_private_docx(template_path: Path, output_path: Path, values: dict[str, str]) -> None:
    doc = Document(template_path)
    replaced = set()
    for table in doc.tables:
        for row in table.rows:
            label = row.cells[0].text.strip()
            if label in values:
                row.cells[1].text = values[label]
                style_private_cell(row.cells[1])
                replaced.add(label)
    if replaced != set(values):
        raise ValueError("public DOCX cover fields do not match the finalizer map")

    status_replaced = False
    note_replaced = False
    for paragraph in doc.paragraphs:
        if paragraph.text.strip() == (
            "DRAFT - HUMAN REVIEW AND ACTION-TIME FACTS REQUIRED"
        ):
            replace_paragraph_text(paragraph, PRIVATE_STATUS, bold=True)
            status_replaced = True
        if paragraph.text.strip() == (
            "Market research response only. No proprietary, classified, confidential, "
            "CUI, patient, or sensitive information is included."
        ):
            replace_paragraph_text(
                paragraph,
                "Market research response only. Contains the minimum necessary verified "
                "business contact and registration facts; no tax, banking, credential, "
                "classified, CUI, patient, or patent-sensitive information is included.",
                bold=False,
                italic=True,
                size=8.2,
            )
            note_replaced = True
    if not status_replaced or not note_replaced:
        raise ValueError("public DOCX status or handling notice could not be replaced")

    doc.core_properties.title = "Project Argos Private Action Copy"
    doc.core_properties.subject = (
        "Private human-review copy; not evidence of submission or authorization"
    )
    for section in doc.sections:
        for paragraph in section.header.paragraphs:
            for run in paragraph.runs:
                if "Draft" in run.text:
                    run.text = run.text.replace("Draft", "Private action copy")
    doc.save(output_path)
    with ZipFile(output_path) as archive:
        document_xml = archive.read("word/document.xml")
    if (
        PRIVATE_MARKER.encode() in document_xml
        or PRIVATE_DISPLAY_MARKER.encode() in document_xml
    ):
        raise ValueError("private DOCX still contains a private-fact placeholder")


def output_paths(output_dir: Path) -> tuple[Path, Path, Path]:
    return (
        output_dir / TEXT_OUTPUT_NAME,
        output_dir / DOCX_OUTPUT_NAME,
        output_dir / RECEIPT_OUTPUT_NAME,
    )


def public_summary(status: str, receipt: dict) -> dict:
    return {
        "status": status,
        "decision": receipt["decision"],
        "required_fact_count": receipt["required_fact_count"],
        "private_value_count": receipt["private_value_count"],
        "placeholder_count": receipt["placeholder_count"],
        "government_send_ready": receipt["government_send_ready"],
        "submission_authorized": receipt["submission_authorized"],
        "external_action_performed": receipt["external_action_performed"],
        "private_values_logged": receipt["private_values_logged"],
    }


def build_private_copy(
    facts_path: Path,
    output_dir: Path,
    as_of_utc: str,
) -> dict:
    evaluated = parse_utc(as_of_utc)
    private_facts_path = validate_private_path(facts_path, "facts path")
    private_output_dir = validate_private_path(output_dir, "output directory")
    payload = read_json(private_facts_path)
    facts = validate_facts(payload, evaluated)
    values = display_values(facts)
    gate = read_json(SUBMISSION_GATE)
    team = read_json(TEAM_REGISTER)

    public_hashes_before = {
        "markdown_sha256": sha256(PUBLIC_MARKDOWN),
        "docx_sha256": sha256(PUBLIC_DOCX),
    }
    private_output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path, docx_path, receipt_path = output_paths(private_output_dir)
    existing = [path.name for path in (markdown_path, docx_path, receipt_path) if path.exists()]
    if existing:
        raise FileExistsError("private output files already exist; use a new output directory")
    temporary_paths = {
        markdown_path: private_output_dir / f".{markdown_path.name}.tmp",
        docx_path: private_output_dir / f".{docx_path.name}.tmp",
        receipt_path: private_output_dir / f".{receipt_path.name}.tmp",
    }
    if any(path.exists() for path in temporary_paths.values()):
        raise FileExistsError("private staging files already exist; use a new output directory")

    private_markdown = render_private_markdown(
        PUBLIC_MARKDOWN.read_text(encoding="utf-8"), values
    )
    staged_markdown = temporary_paths[markdown_path]
    staged_docx = temporary_paths[docx_path]
    staged_receipt = temporary_paths[receipt_path]
    staged_markdown.write_text(private_markdown, encoding="utf-8", newline="\n")
    try:
        render_private_docx(PUBLIC_DOCX, staged_docx, values)
    except Exception:
        for staged_path in temporary_paths.values():
            staged_path.unlink(missing_ok=True)
        raise

    placeholder_count = (
        private_markdown.count(PRIVATE_MARKER)
        + private_markdown.count(PRIVATE_DISPLAY_MARKER)
    )
    public_hashes_after = {
        "markdown_sha256": sha256(PUBLIC_MARKDOWN),
        "docx_sha256": sha256(PUBLIC_DOCX),
    }
    field_states = {
        key: {
            "status": facts[key]["status"],
            "source_kind": facts[key]["source_kind"],
            "verified_utc": parse_utc(facts[key]["verified_utc"]).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        }
        for key in REQUIRED_FACT_KEYS
    }
    team_authority_resolved = bool(gate["send_gate"]["all_teaming_facts_resolved"])
    receipt = {
        "schema": "lumencore.argos_private_action_copy_receipt.v1",
        "evaluated_utc": evaluated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notice_id": NOTICE_ID,
        "decision": "PRIVATE_COVER_READY_TEAM_AND_DISPATCH_BLOCKED",
        "required_fact_count": len(REQUIRED_FACT_KEYS),
        "private_value_count": len(facts),
        "placeholder_count": placeholder_count,
        "field_states": field_states,
        "facts_file": {
            "bytes": private_facts_path.stat().st_size,
            "sha256": sha256(private_facts_path),
            "path_logged": False,
        },
        "public_templates": {
            **public_hashes_after,
            "unchanged": public_hashes_before == public_hashes_after,
        },
        "outputs": {
            "markdown": {
                "name": markdown_path.name,
                "bytes": staged_markdown.stat().st_size,
                "sha256": sha256(staged_markdown),
            },
            "docx": {
                "name": docx_path.name,
                "bytes": staged_docx.stat().st_size,
                "sha256": sha256(staged_docx),
            },
        },
        "team_authority_resolved": team_authority_resolved,
        "candidate_name_authorization_count": sum(
            int(candidate["verification"]["authorization_to_name_in_response"])
            for candidate in team["candidates"]
        ),
        "government_send_ready": False,
        "submission_authorized": False,
        "external_action_performed": False,
        "private_values_logged": False,
        "private_output_mirrored_to_public_vault": False,
        "claim_boundary": (
            "This receipt proves only that a private action copy was generated from a "
            "schema-valid, user-attested facts file without changing the public templates. "
            "It does not prove team authority, final dispatch verification, submission, "
            "acceptance, selection, award, compliance, certification, or authorization."
        ),
        "safest_next_action": (
            "Keep the private copy outside Git and public mirrors. Review every inserted "
            "fact and the rendered cover with the user, resolve written team authority, "
            "then run the Government duplicate and final-dispatch gates before requesting "
            "single-use action-time approval."
        ),
    }
    staged_receipt.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    staged_markdown.replace(markdown_path)
    staged_docx.replace(docx_path)
    staged_receipt.replace(receipt_path)
    return receipt


def check_private_copy(facts_path: Path, output_dir: Path, as_of_utc: str) -> dict:
    evaluated = parse_utc(as_of_utc)
    private_facts_path = validate_private_path(facts_path, "facts path")
    private_output_dir = validate_private_path(output_dir, "output directory")
    facts = validate_facts(read_json(private_facts_path), evaluated)
    markdown_path, docx_path, receipt_path = output_paths(private_output_dir)
    if not all(path.is_file() for path in (markdown_path, docx_path, receipt_path)):
        raise FileNotFoundError("private action-copy output set is incomplete")
    receipt = read_json(receipt_path)
    values = list(display_values(facts).values())
    receipt_text = receipt_path.read_text(encoding="utf-8")
    if any(value in receipt_text for value in values):
        raise ValueError("private value leaked into the redacted receipt")
    if receipt["facts_file"]["sha256"] != sha256(private_facts_path):
        raise ValueError("private facts custody hash is stale")
    if receipt["outputs"]["markdown"]["sha256"] != sha256(markdown_path):
        raise ValueError("private Markdown custody hash is stale")
    if receipt["outputs"]["docx"]["sha256"] != sha256(docx_path):
        raise ValueError("private DOCX custody hash is stale")
    if receipt["public_templates"]["markdown_sha256"] != sha256(PUBLIC_MARKDOWN):
        raise ValueError("public Markdown template changed")
    if receipt["public_templates"]["docx_sha256"] != sha256(PUBLIC_DOCX):
        raise ValueError("public DOCX template changed")
    if PRIVATE_MARKER in markdown_path.read_text(encoding="utf-8"):
        raise ValueError("private Markdown contains a placeholder")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build or verify a private Project Argos action copy without logging "
            "private values or writing inside the public repository."
        )
    )
    parser.add_argument("--facts", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--as-of-utc")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    as_of = args.as_of_utc or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        receipt = (
            check_private_copy(args.facts, args.output_dir, as_of)
            if args.check
            else build_private_copy(args.facts, args.output_dir, as_of)
        )
    except (ValueError, FileNotFoundError, FileExistsError, KeyError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error_type": type(exc).__name__,
                    "private_values_logged": False,
                    "external_action_performed": False,
                },
                indent=2,
            )
        )
        return 1
    status = "CURRENT" if args.check else "PRIVATE_ACTION_COPY_WRITTEN"
    print(json.dumps(public_summary(status, receipt), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
