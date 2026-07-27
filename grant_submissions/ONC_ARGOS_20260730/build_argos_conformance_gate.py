from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


ARGOS_DIR = Path(__file__).resolve().parent
ROOT = ARGOS_DIR.parents[1]
OUTPUT_DIR = ARGOS_DIR / "output"
DEFAULT_JSON = ARGOS_DIR / "ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.json"
DEFAULT_MARKDOWN = ARGOS_DIR / "ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.md"

SUBMISSION_GATE = ARGOS_DIR / "ARGOS_SUBMISSION_GATE_2026-07-26.json"
TEAM_REGISTER = ARGOS_DIR / "ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json"
PARTNER_DISPATCH_GATE = ARGOS_DIR / "ARGOS_EMI_TEAMING_DISPATCH_GATE_2026-07-27.json"
RESPONSE_MARKDOWN = ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md"
BUILD_RECEIPT = OUTPUT_DIR / "build_receipt.json"
RENDER_RECEIPT = OUTPUT_DIR / "render_qa_receipt.json"
DOCX = OUTPUT_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx"
PDF = OUTPUT_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.pdf"

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NS = {"w": W_NS}
PRIVATE_PLACEHOLDER = "ACTION_TIME_PRIVATE_FACT_REQUIRED"
UNAUTHORIZED_PARTNER_NAMES = ("EMI Advisors", "Index Analytics", "BookZurman")
FORBIDDEN_PROMOTION_PHRASES = (
    "agency approved",
    "hhs authorized",
    "externally validated",
    "field validated",
    "guaranteed savings",
    "full-prime ready",
)
TEXT_CUSTODY_SUFFIXES = {".json", ".md", ".py"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def custody_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() not in TEXT_CUSTODY_SUFFIXES:
        return data
    text = data.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def custody_hash_mode(path: Path) -> str:
    if path.suffix.lower() in TEXT_CUSTODY_SUFFIXES:
        return "TEXT_UTF8_LF"
    return "BINARY_RAW"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("Timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def inspect_docx_format(path: Path) -> dict:
    with ZipFile(path) as archive:
        styles = ElementTree.fromstring(archive.read("word/styles.xml"))
        document = ElementTree.fromstring(archive.read("word/document.xml"))

    normal = styles.find('.//w:style[@w:styleId="Normal"]', NS)
    if normal is None:
        raise ValueError("Normal style is missing")
    fonts = normal.find(".//w:rFonts", NS)
    size = normal.find(".//w:sz", NS)
    sections = document.findall(".//w:sectPr", NS)
    if fonts is None or size is None or not sections:
        raise ValueError("Required document format properties are missing")

    attr = lambda name: f"{{{W_NS}}}{name}"
    section_rows = []
    for section in sections:
        page_size = section.find("w:pgSz", NS)
        margins = section.find("w:pgMar", NS)
        if page_size is None or margins is None:
            raise ValueError("Page size or margin properties are missing")
        section_rows.append(
            {
                "width_twips": int(page_size.attrib[attr("w")]),
                "height_twips": int(page_size.attrib[attr("h")]),
                "top_twips": int(margins.attrib[attr("top")]),
                "right_twips": int(margins.attrib[attr("right")]),
                "bottom_twips": int(margins.attrib[attr("bottom")]),
                "left_twips": int(margins.attrib[attr("left")]),
            }
        )

    return {
        "normal_font_ascii": fonts.attrib.get(attr("ascii")),
        "normal_font_hansi": fonts.attrib.get(attr("hAnsi")),
        "normal_font_size_half_points": int(size.attrib[attr("val")]),
        "sections": section_rows,
    }


def result(
    check_id: str,
    requirement: str,
    status: str,
    evidence: str,
    blocker: str | None = None,
) -> dict:
    row = {
        "check_id": check_id,
        "requirement": requirement,
        "status": status,
        "evidence": evidence,
    }
    if blocker:
        row["blocker"] = blocker
    return row


def build_payload(as_of_utc: str) -> dict:
    evaluated = parse_utc(as_of_utc)
    gate = read_json(SUBMISSION_GATE)
    team = read_json(TEAM_REGISTER)
    partner_dispatch = read_json(PARTNER_DISPATCH_GATE)
    build = read_json(BUILD_RECEIPT)
    render = read_json(RENDER_RECEIPT)
    response = RESPONSE_MARKDOWN.read_text(encoding="utf-8")
    docx_format = inspect_docx_format(DOCX)

    deadline = parse_utc(gate["opportunity"]["deadline_utc"])
    placeholders = response.count(PRIVATE_PLACEHOLDER)
    unauthorized_names = [
        name for name in UNAUTHORIZED_PARTNER_NAMES if name.lower() in response.lower()
    ]
    forbidden_phrases = [
        phrase for phrase in FORBIDDEN_PROMOTION_PHRASES if phrase in response.lower()
    ]
    sections = docx_format["sections"]
    letter_size = all(
        row["width_twips"] == 12240 and row["height_twips"] == 15840
        for row in sections
    )
    one_inch_margins = all(
        all(row[key] == 1440 for key in ("top_twips", "right_twips", "bottom_twips", "left_twips"))
        for row in sections
    )
    twelve_point_tnr = (
        docx_format["normal_font_ascii"] == "Times New Roman"
        and docx_format["normal_font_hansi"] == "Times New Roman"
        and docx_format["normal_font_size_half_points"] == 24
    )
    artifact_hashes_match = (
        build["markdown"]["sha256"] == sha256(RESPONSE_MARKDOWN)
        and build["docx"]["sha256"] == sha256(DOCX)
        and render["docx_sha256"] == sha256(DOCX)
        and render["pdf_sha256"] == sha256(PDF)
    )
    required_false_claims = (
        "current_fhir_r4_or_chpl_delivery_claim_allowed",
        "current_hhs_ato_claim_allowed",
        "current_3pao_claim_allowed",
        "federal_health_prior_performance_claim_allowed",
        "agency_approval_claim_allowed",
        "external_validation_claim_allowed",
        "field_performance_claim_allowed",
        "realized_savings_claim_allowed",
        "full_prime_readiness_claim_allowed",
    )
    claim_boundaries_hold = all(
        gate["claim_boundaries"][field] is False for field in required_false_claims
    )
    all_files_present = all(
        path.is_file()
        for path in (
            RESPONSE_MARKDOWN,
            DOCX,
            PDF,
            BUILD_RECEIPT,
            RENDER_RECEIPT,
        )
    )
    candidate_authorizations = sum(
        int(candidate["verification"]["authorization_to_name_in_response"])
        for candidate in team["candidates"]
    )

    checks = [
        result(
            "OFFICIAL_NOTICE_CURRENT",
            "The official notice is active and its identity and deadline are explicit.",
            "PASS"
            if gate["official_notice_recheck"]["notice_active"]
            and gate["official_notice_recheck"]["deadline_utc"]
            == gate["opportunity"]["deadline_utc"]
            else "FAIL",
            gate["opportunity"]["official_url"],
        ),
        result(
            "DEADLINE_OPEN",
            "The response is evaluated before the exact Government deadline.",
            "PASS" if evaluated < deadline else "FAIL",
            f"evaluated={as_of_utc}; deadline={gate['opportunity']['deadline_utc']}",
        ),
        result(
            "ACCEPTED_FILES_PRESENT",
            "Both accepted review formats and their receipts are present.",
            "PASS" if all_files_present else "FAIL",
            f"docx={DOCX.is_file()}; pdf={PDF.is_file()}; receipts={BUILD_RECEIPT.is_file() and RENDER_RECEIPT.is_file()}",
        ),
        result(
            "ARTIFACT_HASH_CUSTODY",
            "Markdown, DOCX, and PDF hashes reconcile to the current receipts.",
            "PASS" if artifact_hashes_match else "FAIL",
            f"docx_sha256={sha256(DOCX)}; pdf_sha256={sha256(PDF)}",
        ),
        result(
            "US_LETTER_SIZE",
            "Every DOCX section uses US Letter dimensions.",
            "PASS" if letter_size else "FAIL",
            f"sections={len(sections)}; expected_twips=12240x15840",
        ),
        result(
            "ONE_INCH_MARGINS",
            "Every DOCX section uses one-inch content margins.",
            "PASS" if one_inch_margins else "FAIL",
            f"sections={len(sections)}; expected_twips=1440",
        ),
        result(
            "TWELVE_POINT_TIMES_NEW_ROMAN",
            "The Normal style is Times New Roman 12 point.",
            "PASS" if twelve_point_tnr else "FAIL",
            (
                f"font={docx_format['normal_font_ascii']}; "
                f"half_points={docx_format['normal_font_size_half_points']}"
            ),
        ),
        result(
            "CONTENT_PAGE_LIMIT",
            "The response stays within ten content pages excluding the cover.",
            "PASS"
            if render["page_limit_passed"]
            and render["content_pages"] <= render["content_page_limit"]
            else "FAIL",
            (
                f"cover_pages={render['cover_pages']}; "
                f"content_pages={render['content_pages']}; "
                f"limit={render['content_page_limit']}"
            ),
        ),
        result(
            "VISUAL_QA",
            "Every rendered page is inspected without clipping or overlap.",
            "PASS"
            if render["visual_inspection_passed"]
            and not render["overlap_or_clipping_found"]
            else "FAIL",
            f"inspected_pages={render['inspected_pages']}",
        ),
        result(
            "PRIVATE_COVER_FACTS",
            "Every required cover fact is resolved and no placeholder remains.",
            "PASS"
            if gate["send_gate"]["all_private_facts_resolved"] and placeholders == 0
            else "BLOCKED",
            f"placeholder_count={placeholders}; required_private_fact_count={len(gate['required_private_facts'])}",
            "Insert only currently verified private entity and contact facts in the private final copy.",
        ),
        result(
            "AUTHORIZED_NAMED_TEAM",
            "Every named team role, credential, and reference is documented and authorized.",
            "PASS"
            if gate["send_gate"]["all_teaming_facts_resolved"]
            and candidate_authorizations > 0
            else "BLOCKED",
            (
                f"required_teaming_fact_count={len(gate['required_teaming_facts'])}; "
                f"candidate_name_authorizations={candidate_authorizations}"
            ),
            "Obtain written partner role, name, credential, and reference authorization.",
        ),
        result(
            "NO_UNAUTHORIZED_PARTNER_NAME",
            "The Government response names no uncommitted teaming candidate.",
            "PASS" if not unauthorized_names else "FAIL",
            f"unauthorized_names_found={unauthorized_names}",
        ),
        result(
            "SIMILAR_SCOPE_BOUNDARY",
            "Adjacent component evidence is not represented as federal-health prior performance.",
            "PASS"
            if "No direct LumenCore prior-performance reference is claimed" in response
            and "No full-prime readiness or comparable federal health delivery is claimed"
            in response
            else "FAIL",
            "Explicit similar-scope matrix and acquisition implications are present.",
        ),
        result(
            "CLAIM_BOUNDARIES",
            "Unsupported certification, authorization, validation, savings, and prime claims remain prohibited.",
            "PASS" if claim_boundaries_hold and not forbidden_phrases else "FAIL",
            f"forbidden_promotion_phrases_found={forbidden_phrases}",
        ),
        result(
            "PARTNER_DRAFT_UNSENT",
            "The bounded partner inquiry remains an unsent, no-attachment draft.",
            "PASS"
            if partner_dispatch["gmail_draft_receipt"]["draft_present"]
            and not partner_dispatch["gmail_draft_receipt"]["sent"]
            and partner_dispatch["message"]["attachment_count"] == 0
            else "FAIL",
            (
                f"draft_present={partner_dispatch['gmail_draft_receipt']['draft_present']}; "
                f"sent={partner_dispatch['gmail_draft_receipt']['sent']}; "
                f"attachments={partner_dispatch['message']['attachment_count']}"
            ),
        ),
        result(
            "GOVERNMENT_DUPLICATE_RECHECK",
            "A fresh full-mailbox duplicate check is bound to the final Government response.",
            "PASS" if gate["send_gate"]["duplicate_send_rechecked"] else "BLOCKED",
            f"last_preliminary_check={gate['duplicate_send_check']['checked_utc']}",
            "Repeat the exact Government-response duplicate search immediately before send.",
        ),
        result(
            "FINAL_DISPATCH_BINDING",
            "The final Government recipient, subject, body, and attachment set are verified together.",
            "PASS"
            if all(
                gate["send_gate"][field]
                for field in (
                    "final_recipient_verified",
                    "final_subject_verified",
                    "final_body_verified",
                    "final_attachments_verified",
                )
            )
            else "BLOCKED",
            (
                "recipient={final_recipient_verified}; subject={final_subject_verified}; "
                "body={final_body_verified}; attachments={final_attachments_verified}"
            ).format(**gate["send_gate"]),
            "Build and inspect the private final action packet after the cover and team gates pass.",
        ),
        result(
            "ACTION_TIME_APPROVAL",
            "Single-use action-time human approval is bound to the exact Government dispatch.",
            "PASS"
            if gate["send_gate"]["exact_action_time_human_approval_required"]
            and gate["send_gate"]["submission_authorized"]
            else "BLOCKED"
            if gate["send_gate"]["exact_action_time_human_approval_required"]
            else "FAIL",
            (
                "approval_required={exact_action_time_human_approval_required}; "
                "submission_authorized={submission_authorized}"
            ).format(**gate["send_gate"]),
            "Obtain exact action-time approval only after every other blocker is cleared.",
        ),
    ]

    counts = {
        status: sum(row["status"] == status for row in checks)
        for status in ("PASS", "BLOCKED", "FAIL")
    }
    decision = (
        "FAIL_CONFORMANCE"
        if counts["FAIL"]
        else "BLOCK_SEND_MISSING_REQUIRED_FACTS_AND_AUTHORITY"
        if counts["BLOCKED"]
        else "READY_FOR_ACTION_TIME_REVIEW"
    )
    source_paths = (
        SUBMISSION_GATE,
        TEAM_REGISTER,
        PARTNER_DISPATCH_GATE,
        RESPONSE_MARKDOWN,
        BUILD_RECEIPT,
        RENDER_RECEIPT,
        DOCX,
        PDF,
    )
    return {
        "schema": "lumencore.argos_response_conformance_gate.v1",
        "evaluated_utc": evaluated.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "notice_id": gate["opportunity"]["notice_id"],
        "deadline_utc": gate["opportunity"]["deadline_utc"],
        "decision": decision,
        "summary": {
            "check_count": len(checks),
            "pass_count": counts["PASS"],
            "blocked_count": counts["BLOCKED"],
            "fail_count": counts["FAIL"],
            "submission_authorized": gate["send_gate"]["submission_authorized"],
            "external_action_performed": False,
        },
        "checks": checks,
        "source_custody": [
            {
                "path": rel(path),
                "bytes": len(custody_bytes(path)),
                "sha256": hashlib.sha256(custody_bytes(path)).hexdigest(),
                "hash_mode": custody_hash_mode(path),
            }
            for path in source_paths
        ],
        "claim_boundary": (
            "PASS means the named documentary or formatting requirement is supported. "
            "BLOCKED means the current artifact is intentionally not send-ready. "
            "Neither passing checks nor a polished packet establishes submission, "
            "acceptance, selection, award, authorization, certification, external "
            "validation, field performance, or savings."
        ),
        "safest_next_action": (
            "Resolve the private cover and authorized-team blockers first. Then rebuild "
            "the private final copy, rerun this gate, repeat the official-notice and "
            "full-mailbox duplicate checks, and request exact action-time approval."
        ),
    }


def render_markdown(payload: dict) -> str:
    lines = [
        "# Project Argos Response Conformance Gate",
        "",
        f"Evaluated UTC: `{payload['evaluated_utc']}`",
        f"Decision: `{payload['decision']}`",
        "",
        "## Summary",
        "",
        f"- Checks: `{payload['summary']['check_count']}`",
        f"- Pass: `{payload['summary']['pass_count']}`",
        f"- Blocked: `{payload['summary']['blocked_count']}`",
        f"- Fail: `{payload['summary']['fail_count']}`",
        f"- Submission authorized: `{str(payload['summary']['submission_authorized']).lower()}`",
        f"- External action performed: `{str(payload['summary']['external_action_performed']).lower()}`",
        "",
        "## Requirement Matrix",
        "",
        "| Check | Status | Requirement | Evidence |",
        "| --- | --- | --- | --- |",
    ]
    for row in payload["checks"]:
        evidence = row["evidence"].replace("|", "\\|").replace("\n", " ")
        requirement = row["requirement"].replace("|", "\\|")
        lines.append(
            f"| `{row['check_id']}` | `{row['status']}` | {requirement} | {evidence} |"
        )
        if row.get("blocker"):
            lines.append(f"|  |  | **Blocker action** | {row['blocker']} |")
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["claim_boundary"],
            "",
            "## Safest Next Action",
            "",
            payload["safest_next_action"],
            "",
        ]
    )
    return "\n".join(lines)


def write_or_check(path: Path, content: str, check_only: bool) -> bool:
    if check_only:
        return path.is_file() and path.read_text(encoding="utf-8") == content
    path.write_text(content, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the fail-closed Project Argos response conformance gate."
    )
    parser.add_argument("--as-of-utc")
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    as_of = args.as_of_utc
    if args.check and not as_of and args.json_output.is_file():
        as_of = read_json(args.json_output)["evaluated_utc"]
    if not as_of:
        as_of = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    payload = build_payload(as_of)
    json_text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    markdown_text = render_markdown(payload)
    json_ok = write_or_check(args.json_output, json_text, args.check)
    markdown_ok = write_or_check(args.markdown_output, markdown_text, args.check)
    status = "CURRENT" if args.check and json_ok and markdown_ok else "WRITTEN"
    if args.check and not (json_ok and markdown_ok):
        status = "STALE"

    print(
        json.dumps(
            {
                "status": status,
                "decision": payload["decision"],
                **payload["summary"],
                "json_output": str(args.json_output),
                "markdown_output": str(args.markdown_output),
            },
            indent=2,
        )
    )
    return 0 if status != "STALE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
