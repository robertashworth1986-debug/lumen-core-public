from __future__ import annotations

import argparse
import hashlib
import importlib.util
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
PARTNER_DISPATCH_BINDING = (
    ARGOS_DIR / "ARGOS_EMI_TEAMING_DISPATCH_BINDING_2026-07-27.json"
)
PARTNER_STATUS = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "ARGOS_PARTNER_OUTREACH_STATUS_2026-07-28.json"
)
CLAIM_EVIDENCE_MAP = ARGOS_DIR / "ARGOS_CLAIM_EVIDENCE_MAP_2026-07-27.json"
RESPONSE_MARKDOWN = ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md"
BUILD_RECEIPT = OUTPUT_DIR / "build_receipt.json"
RENDER_RECEIPT = OUTPUT_DIR / "render_qa_receipt.json"
DOCX = OUTPUT_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx"
PDF = OUTPUT_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.pdf"
OFFICIAL_SOW = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "source_attachments"
    / "Project Argos SOW - SSN.pdf"
)
OFFICIAL_SOW_SHA256 = (
    "6a1608c024bd87b0204370baab58b0a218c044d403bce6dbe0cfb5164faf6354"
)
OFFICIAL_SOW_BYTES = 174359
OFFICIAL_SOW_SOURCE_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "source_attachments"
    / "PROJECT_ARGOS_SOW_OFFICIAL_SOURCE_RECEIPT_2026-07-28.json"
)
SECURITY_GATE = (
    ARGOS_DIR / "ARGOS_PUBLIC_REPOSITORY_SECURITY_GATE_2026-07-28.json"
)
SECURITY_STATUS = ROOT / "config" / "public_credential_remediation_status_v1.json"
PUBLIC_CREDENTIAL_CONFIG = ROOT / "LamaScout" / "config" / "api_registry.yaml"
SECURITY_VERIFIER = (
    ROOT / "code" / "ops" / "VERIFY_PUBLIC_REPO_CREDENTIAL_HYGIENE.py"
)
OFFICIAL_NOTICE_MAX_AGE_SECONDS = 24 * 60 * 60

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


def security_receipts_equivalent(committed: dict, current: dict) -> bool:
    portable_receipts = []
    for receipt in (committed, current):
        portable = json.loads(json.dumps(receipt))
        history = portable.get("history")
        if not isinstance(history, dict):
            return False
        reachable_ref_count = history.get("local_reachable_ref_count")
        if (
            not isinstance(reachable_ref_count, int)
            or isinstance(reachable_ref_count, bool)
            or reachable_ref_count < 1
        ):
            return False
        history.pop("local_reachable_ref_count")
        portable_receipts.append(portable)
    return portable_receipts[0] == portable_receipts[1]


def current_security_payload(committed: dict) -> tuple[dict, bool]:
    spec = importlib.util.spec_from_file_location(
        "argos_conformance_credential_hygiene",
        SECURITY_VERIFIER,
    )
    if spec is None or spec.loader is None:
        raise ValueError("public repository security verifier cannot be loaded")
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    current = verifier.build_payload()
    receipt_current = security_receipts_equivalent(committed, current)
    return current, receipt_current


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
    evaluated = parse_utc(as_of_utc).replace(microsecond=0)
    evaluated_utc = evaluated.strftime("%Y-%m-%dT%H:%M:%SZ")
    gate = read_json(SUBMISSION_GATE)
    team = read_json(TEAM_REGISTER)
    partner_dispatch = read_json(PARTNER_DISPATCH_GATE)
    partner_binding = read_json(PARTNER_DISPATCH_BINDING)
    partner_status = read_json(PARTNER_STATUS)
    claim_evidence_map = read_json(CLAIM_EVIDENCE_MAP)
    security_gate = read_json(SECURITY_GATE)
    security_state, security_receipt_current = current_security_payload(
        security_gate
    )
    official_sow_source = read_json(OFFICIAL_SOW_SOURCE_RECEIPT)
    build = read_json(BUILD_RECEIPT)
    render = read_json(RENDER_RECEIPT)
    response = RESPONSE_MARKDOWN.read_text(encoding="utf-8")
    docx_format = inspect_docx_format(DOCX)

    deadline = parse_utc(gate["opportunity"]["deadline_utc"])
    notice_checked = parse_utc(gate["official_notice_recheck"]["checked_utc"])
    notice_age_seconds = (evaluated - notice_checked).total_seconds()
    official_notice_current = (
        0 <= notice_age_seconds <= OFFICIAL_NOTICE_MAX_AGE_SECONDS
        and gate["official_notice_recheck"]["notice_active"] is True
        and gate["official_notice_recheck"]["deadline_utc"]
        == gate["opportunity"]["deadline_utc"]
        and gate["official_notice_recheck"]["official_url"]
        == gate["opportunity"]["official_url"]
        and gate["official_notice_recheck"]["notice_id"]
        == gate["opportunity"]["notice_id"]
        and gate["official_notice_recheck"]["amendment_observed"] is False
    )
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
    claim_map_sources_hold = all(
        (ROOT / row["path"]).is_file()
        and hashlib.sha256(custody_bytes(ROOT / row["path"])).hexdigest()
        == row["sha256"]
        and row["hash_mode"] == custody_hash_mode(ROOT / row["path"])
        for row in claim_evidence_map["source_custody"]
    )
    claim_evidence_traceability = (
        claim_evidence_map["status"] == "VERIFIED_BOUNDED_CLAIM_MAP"
        and claim_evidence_map["response"]["sha256"] == sha256(RESPONSE_MARKDOWN)
        and claim_evidence_map["response"]["material_claim_count"]
        == len(claim_evidence_map["claims"])
        and all(row["supported"] for row in claim_evidence_map["claims"])
        and claim_map_sources_hold
        and claim_evidence_map["external_action_performed"] is False
        and claim_evidence_map["submission_authorized"] is False
    )
    official_sow_custody = (
        OFFICIAL_SOW.is_file()
        and OFFICIAL_SOW.stat().st_size == OFFICIAL_SOW_BYTES
        and sha256(OFFICIAL_SOW) == OFFICIAL_SOW_SHA256
        and official_sow_source.get("schema")
        == "lumencore.official_source_attachment_receipt.v1"
        and official_sow_source["notice"]["notice_id"]
        == gate["opportunity"]["notice_id"]
        and official_sow_source["notice"]["official_url"]
        == gate["opportunity"]["official_url"]
        and official_sow_source["attachment"]["document_name"]
        == OFFICIAL_SOW.name
        and official_sow_source["attachment"]["access"] == "PUBLIC"
        and official_sow_source["local_copy"]["path"] == rel(OFFICIAL_SOW)
        and official_sow_source["local_copy"]["bytes"] == OFFICIAL_SOW_BYTES
        and official_sow_source["local_copy"]["sha256"]
        == OFFICIAL_SOW_SHA256
        and official_sow_source["remote_refresh"]["http_status"] == 200
        and official_sow_source["remote_refresh"]["downloaded_bytes"]
        == OFFICIAL_SOW_BYTES
        and official_sow_source["remote_refresh"]["sha256"]
        == OFFICIAL_SOW_SHA256
        and official_sow_source["remote_refresh"]["matches_local_copy"] is True
        and all(official_sow_source["checks"].values())
    )
    security_receipt_current = (
        security_receipt_current
        and security_state.get("schema")
        == "lumencore.public_repository_security_gate.v1"
        and security_state.get("target_path")
        == PUBLIC_CREDENTIAL_CONFIG.relative_to(ROOT).as_posix()
        and security_state.get("target_sha256")
        == sha256(PUBLIC_CREDENTIAL_CONFIG)
        and security_state["current_file"]["placeholder_only"] is True
        and security_state["current_file"]["non_placeholder_value_count"] == 0
        and security_state["current_file"][
            "required_environment_references_present"
        ]
        is True
        and security_state["history"]["scan_complete"] is True
        and security_state["history"]["scan_failure_count"] == 0
        and security_state.get("external_action_performed") is False
    )
    security_rotation_and_history_clear = (
        security_receipt_current
        and all(
            row["confirmed"]
            for row in security_state["provider_rotation"].values()
        )
        and security_state["history"]["remediation_confirmed"] is True
        and security_state["history"][
            "remote_public_history_verification_confirmed"
        ]
        is True
        and security_state["history"]["historical_exposure_detected"] is False
        and security_state["decision"]
        == "PASS_TARGETED_CREDENTIAL_AND_REMOTE_HISTORY_GATE"
        and security_state["public_repository_link_allowed"] is True
        and security_state["final_argos_send_allowed_by_security_gate"] is True
    )
    partner_outreach_sent_once = (
        partner_status.get("schema")
        == "lumencore.argos_partner_outreach_status.v1"
        and partner_status.get("status")
        == "SENT_ONCE_POST_SEND_VERIFIED_WAITING_FOR_REPLY"
        and partner_status["mailbox_observation"]["matching_current_draft_count"] == 0
        and partner_status["mailbox_observation"]["matching_sent_count"] == 1
        and partner_status["mailbox_observation"]["matching_inbound_count"] == 0
        and partner_status["mailbox_observation"]["sent_copy_present"] is True
        and partner_status["mailbox_observation"]["attachment_count"] == 0
        and partner_status["mailbox_observation"]["cc_count"] == 0
        and partner_status["mailbox_observation"]["bcc_count"] == 0
        and partner_status["controls"]["final_send_performed"] is True
        and partner_status["controls"]["post_send_sent_copy_verified"] is True
        and partner_status["controls"]["duplicate_send_prohibited"] is True
        and partner_status["controls"]["partner_name_use_requires_written_authority"]
        is True
    )

    checks = [
        result(
            "OFFICIAL_NOTICE_CURRENT",
            "The official notice is active and its identity and deadline are explicit.",
            "PASS" if official_notice_current else "FAIL",
            (
                f"{gate['opportunity']['official_url']}; "
                f"checked_utc={gate['official_notice_recheck']['checked_utc']}; "
                f"age_seconds={int(notice_age_seconds)}; "
                "amendment_observed="
                f"{gate['official_notice_recheck']['amendment_observed']}"
            ),
        ),
        result(
            "OFFICIAL_SOW_SOURCE_CUSTODY",
            "The official four-page draft SOW attachment is preserved with exact binary custody.",
            "PASS" if official_sow_custody else "FAIL",
            (
                f"bytes={OFFICIAL_SOW.stat().st_size if OFFICIAL_SOW.is_file() else 0}; "
                f"sha256={sha256(OFFICIAL_SOW) if OFFICIAL_SOW.is_file() else 'MISSING'}; "
                f"source_receipt_sha256={sha256(OFFICIAL_SOW_SOURCE_RECEIPT)}"
            ),
        ),
        result(
            "PUBLIC_REPOSITORY_CREDENTIAL_RECEIPT",
            "The current public credential configuration contains environment references only and its receipt matches the current file.",
            "PASS" if security_receipt_current else "FAIL",
            (
                "placeholder_only="
                f"{security_state['current_file']['placeholder_only']}; "
                "non_placeholder_value_count="
                f"{security_state['current_file']['non_placeholder_value_count']}; "
                "required_environment_references_present="
                f"{security_state['current_file']['required_environment_references_present']}; "
                f"scan_complete={security_state['history']['scan_complete']}; "
                f"scan_failure_count={security_state['history']['scan_failure_count']}"
            ),
        ),
        result(
            "PUBLIC_REPOSITORY_ROTATION_AND_HISTORY",
            "Previously exposed provider credentials are rotated and prior public Git objects are remediated before the repository is linked or the final response is sent.",
            "PASS" if security_rotation_and_history_clear else "BLOCKED",
            (
                "provider_rotations_confirmed="
                f"{all(row['confirmed'] for row in security_state['provider_rotation'].values())}; "
                "history_remediation_confirmed="
                f"{security_state['history']['remediation_confirmed']}; "
                "remote_public_history_verification_confirmed="
                f"{security_state['history']['remote_public_history_verification_confirmed']}; "
                "historical_exposure_detected="
                f"{security_state['history']['historical_exposure_detected']}; "
                "public_repository_link_allowed="
                f"{security_state['public_repository_link_allowed']}"
            ),
            (
                "Rotate the affected provider credentials, record non-secret "
                "receipts, remediate reachable public Git history, and verify "
                "the remote before linking the repository or sending."
            ),
        ),
        result(
            "DEADLINE_OPEN",
            "The response is evaluated before the exact Government deadline.",
            "PASS" if evaluated < deadline else "FAIL",
            f"evaluated={evaluated_utc}; deadline={gate['opportunity']['deadline_utc']}",
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
            "CLAIM_EVIDENCE_TRACEABILITY",
            "Each affirmative engineering proof statement is bound to named public evidence and explicit non-claims.",
            "PASS" if claim_evidence_traceability else "FAIL",
            (
                f"claim_count={len(claim_evidence_map['claims'])}; "
                f"status={claim_evidence_map['status']}; "
                f"source_custody_hold={claim_map_sources_hold}"
            ),
        ),
        result(
            "PARTNER_OUTREACH_SENT_ONCE",
            "The bounded partner inquiry was sent exactly once without attachments, CC, or BCC and is now duplicate-locked while awaiting a reply.",
            "PASS" if partner_outreach_sent_once else "FAIL",
            (
                "drafts="
                f"{partner_status['mailbox_observation']['matching_current_draft_count']}; "
                "sent="
                f"{partner_status['mailbox_observation']['matching_sent_count']}; "
                "inbound="
                f"{partner_status['mailbox_observation']['matching_inbound_count']}; "
                "sent_copy_verified="
                f"{partner_status['controls']['post_send_sent_copy_verified']}; "
                "duplicate_send_prohibited="
                f"{partner_status['controls']['duplicate_send_prohibited']}"
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
        PARTNER_DISPATCH_BINDING,
        PARTNER_STATUS,
        CLAIM_EVIDENCE_MAP,
        RESPONSE_MARKDOWN,
        BUILD_RECEIPT,
        RENDER_RECEIPT,
        DOCX,
        PDF,
        OFFICIAL_SOW,
        OFFICIAL_SOW_SOURCE_RECEIPT,
        SECURITY_GATE,
        SECURITY_STATUS,
        PUBLIC_CREDENTIAL_CONFIG,
        SECURITY_VERIFIER,
    )
    return {
        "schema": "lumencore.argos_response_conformance_gate.v1",
        "evaluated_utc": evaluated_utc,
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
            "Complete provider credential rotation and public-history remediation, "
            "then resolve the private cover and authorized-team blockers. Rebuild the "
            "private final copy, rerun this gate, repeat the official-notice and "
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
