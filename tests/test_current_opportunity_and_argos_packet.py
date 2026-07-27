from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "assets" / "brand"
ARGOS_DIR = ROOT / "grant_submissions" / "ONC_ARGOS_20260730"
ARGOS_OUTPUT = ARGOS_DIR / "output"
OPPORTUNITY_MAP = ROOT / "docs" / "CURRENT_FEDERAL_OPPORTUNITY_GATE_MAP_2026-07-26.md"
SCIENCE_MAP = ROOT / "docs" / "SCIENTIFIC_CONTRIBUTION_AND_NEXT_EXPERIMENTS_2026-07-26.md"
ARGOS_CONFORMANCE = ARGOS_DIR / "ARGOS_RESPONSE_CONFORMANCE_GATE_2026-07-27.json"
ARGOS_PRIVATE_READINESS = (
    ARGOS_DIR / "ARGOS_PRIVATE_FINALIZER_READINESS_2026-07-27.json"
)
ARGOS_PRIVATE_SCHEMA = ARGOS_DIR / "ARGOS_PRIVATE_FACTS_SCHEMA_2026-07-27.json"
ARGOS_CLAIM_MAP = ARGOS_DIR / "ARGOS_CLAIM_EVIDENCE_MAP_2026-07-27.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def custody_bytes(path: Path, hash_mode: str) -> bytes:
    data = path.read_bytes()
    if hash_mode == "BINARY_RAW":
        return data
    assert hash_mode == "TEXT_UTF8_LF"
    text = data.decode("utf-8")
    return text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")


def load_argos_conformance_builder():
    path = ARGOS_DIR / "build_argos_conformance_gate.py"
    spec = importlib.util.spec_from_file_location("build_argos_conformance_gate", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_argos_private_finalizer():
    path = ARGOS_DIR / "build_argos_private_action_copy.py"
    spec = importlib.util.spec_from_file_location("build_argos_private_action_copy", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_argos_claim_evidence_builder():
    path = ARGOS_DIR / "build_argos_claim_evidence_map.py"
    spec = importlib.util.spec_from_file_location("build_argos_claim_evidence_map", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dummy_private_fact_payload() -> dict:
    verified = "2026-07-27T18:00:00Z"

    def fact(value: str, source_kind: str = "OFFICIAL_ENTITY_RECORD") -> dict:
        return {
            "value": value,
            "status": "VERIFIED",
            "source_kind": source_kind,
            "verified_utc": verified,
        }

    return {
        "schema": "lumencore.argos_private_facts.v1",
        "notice_id": "ONC-ARGOS-SSN-2026-OS351107",
        "facts": {
            "legal_company_name": fact("Example Test Entity LLC"),
            "uei": fact("ABCDEF123456", "OFFICIAL_SAM_RECORD"),
            "duns_if_notice_or_entity_record_requires_it": {
                "value": "NOT_APPLICABLE",
                "status": "NOT_APPLICABLE",
                "source_kind": "OFFICIAL_SAM_RECORD",
                "verified_utc": verified,
            },
            "company_address": fact("100 Test Avenue, Example City, TN 37000"),
            "authorized_point_of_contact_name_and_title": fact(
                "Casey Example, Authorized Representative",
                "FOUNDER_VERIFIED_BUSINESS_RECORD",
            ),
            "authorized_point_of_contact_phone": fact(
                "(555) 010-1234", "FOUNDER_VERIFIED_BUSINESS_RECORD"
            ),
            "authorized_point_of_contact_email": fact(
                "casey@example.invalid", "FOUNDER_VERIFIED_BUSINESS_RECORD"
            ),
            "small_business_designations": fact(
                "Small business test fixture", "OFFICIAL_SAM_RECORD"
            ),
            "sam_registration_status_and_expiration": fact(
                "ACTIVE through 2099-12-31 test fixture", "OFFICIAL_SAM_RECORD"
            ),
        },
        "assertions": {
            "facts_current_and_accurate": True,
            "authorized_for_this_response": True,
            "minimum_necessary_business_information_only": True,
        },
    }


def test_lumencore_company_and_lumaarc_seal_are_distinct_and_hash_locked():
    receipt = load_json(BRAND_DIR / "lumaarc_arc_seal_v1.receipt.json")
    logo = BRAND_DIR / "lumaarc_arc_seal_v1.png"

    assert receipt["schema"] == "lumencore.brand_asset_receipt.v1"
    assert receipt["company_name"] == "LumenCore"
    assert receipt["seal_name"] == "LumaArc seal of approval"
    assert receipt["status"] == "FOUNDER_CONFIRMED_LUMAARC_SEAL_FOR_LUMENCORE_MATERIALS"
    assert receipt["claim_boundary"]["company_rename_claim_allowed"] is False
    assert receipt["claim_boundary"]["legal_entity_name_inferred_from_seal"] is False
    assert sha256(logo) == receipt["sha256"]


def test_argos_gate_remains_partner_first_and_fail_closed():
    gate = load_json(ARGOS_DIR / "ARGOS_SUBMISSION_GATE_2026-07-26.json")

    assert gate["schema"] == "lumencore.opportunity_submission_gate.v1"
    assert gate["opportunity"]["notice_id"] == "ONC-ARGOS-SSN-2026-OS351107"
    assert gate["opportunity"]["deadline_utc"] == "2026-07-30T21:00:00Z"
    assert gate["response"]["company_name"] == "LumenCore"
    assert gate["response"]["strategy"] == "PARTNER_FIRST_EVIDENCE_ASSURANCE_WORKSTREAM"
    assert gate["brand"]["seal_name"] == "LumaArc seal of approval"
    assert gate["send_gate"]["submission_authorized"] is False
    assert gate["send_gate"]["exact_action_time_human_approval_required"] is True
    assert gate["send_gate"]["decision"] == "BLOCK_SEND"
    assert gate["partner_search"]["status"] == "PRIMARY_GMAIL_DRAFT_CREATED_NOT_SENT"
    assert gate["partner_search"]["outreach_sent_count"] == 0
    assert gate["partner_search"]["gmail_draft_count"] == 1
    assert gate["claim_boundaries"]["full_prime_readiness_claim_allowed"] is False
    assert gate["claim_boundaries"]["realized_savings_claim_allowed"] is False


def test_argos_generated_outputs_match_their_receipts():
    logo = BRAND_DIR / "lumaarc_arc_seal_v1.png"
    markdown = ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md"
    docx = ARGOS_OUTPUT / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx"
    pdf = ARGOS_OUTPUT / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.pdf"
    build = load_json(ARGOS_OUTPUT / "build_receipt.json")
    qa = load_json(ARGOS_OUTPUT / "render_qa_receipt.json")

    assert build["schema"] == "lumencore.argos_response_build_receipt.v1"
    assert build["logo_sha256"] == sha256(logo)
    assert build["markdown"]["sha256"] == sha256(markdown)
    assert build["docx"]["sha256"] == sha256(docx)
    assert build["submission_authorized"] is False
    assert build["exact_action_time_human_approval_required"] is True

    assert qa["schema"] == "lumencore.argos_render_qa.v1"
    assert qa["company_name"] == "LumenCore"
    assert qa["seal_name"] == "LumaArc seal of approval"
    assert qa["docx_sha256"] == sha256(docx)
    assert qa["pdf_sha256"] == sha256(pdf)
    assert qa["total_pages"] == 10
    assert qa["content_pages"] == 9
    assert qa["content_pages"] <= qa["content_page_limit"]
    assert qa["visual_inspection_passed"] is True
    assert qa["overlap_or_clipping_found"] is False
    assert qa["submission_authorized"] is False


def test_argos_response_uses_the_company_name_without_inflated_claims():
    response = (ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md").read_text(
        encoding="utf-8"
    )

    assert "LumenCore offers Project Argos a bounded evidence-assurance" in response
    assert "LumaArc seal of approval" in response
    assert "LumaArc responds" not in response
    assert "| Brand | LumaArc |" not in response
    assert "does not claim presently qualified full-scope health IT prime readiness" in response
    assert "a proof-of-concept result alone is not an Authority to Operate" in response
    assert "No direct LumenCore prior-performance reference is claimed" in response
    assert "public reviewer surface" in response
    assert "live reviewer surface" not in response
    assert "Measured public EIA replay" not in response
    assert "negative Kuramoto result" not in response
    assert "patent-sensitive" not in response


def test_argos_teaming_register_is_source_bound_and_does_not_claim_commitment():
    register = load_json(ARGOS_DIR / "ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json")

    assert register["schema"] == "lumencore.argos_teaming_candidate_register.v1"
    assert register["status"] == "PRIMARY_GMAIL_DRAFT_CREATED_NOT_SENT"
    assert register["opportunity"]["named_team_members_and_roles_required"] is True
    assert len(register["candidates"]) == 3
    assert register["selection_strategy"]["contact_sequence"] == (
        "ONE_ROUTE_AT_A_TIME_WITH_FRESH_DUPLICATE_CHECK"
    )
    for candidate in register["candidates"]:
        assert candidate["primary_sources"]
        assert all(source.startswith("https://") for source in candidate["primary_sources"])
        assert candidate["verification"]["interest_confirmed"] is False
        assert candidate["verification"]["authorization_to_name_in_response"] is False
        assert candidate["outreach"]["sent"] is False
    assert register["claim_boundaries"]["candidate_listing_is_not_a_commitment"] is True
    assert register["claim_boundaries"]["no_outreach_send_is_authorized_by_this_register"] is True


def test_argos_primary_partner_draft_is_exactly_bound_and_still_unsent():
    body = ARGOS_DIR / "ARGOS_EMI_TEAMING_INQUIRY_BODY.md"
    gate = load_json(ARGOS_DIR / "ARGOS_EMI_TEAMING_DISPATCH_GATE_2026-07-27.json")
    registry = load_json(
        ROOT
        / "grant_submissions"
        / "funding_sprint_20260709"
        / "OUTREACH_RESPONSE_TEMPLATE_REGISTRY_2026-07-18.json"
    )
    primary = load_json(
        ARGOS_DIR / "ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json"
    )["candidates"][0]

    assert gate["schema"] == "lumencore.argos_partner_dispatch_gate.v1"
    assert gate["recipient_route"]["organization"] == "EMI Advisors LLC"
    assert gate["recipient_route"]["public_route_verified"] is True
    assert gate["recipient_route"]["recipient_address_stored_in_public_gate"] is False
    selection = gate["template_selection"]
    template = next(
        row
        for row in registry["templates"]
        if row["template_id"] == selection["template_id"]
    )
    template_sha256 = hashlib.sha256(
        json.dumps(
            template, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest().upper()
    assert selection["template_id"] == "INITIAL_PARTNER_TEAMING_INQUIRY"
    assert selection["registry_source_config_sha256"] == registry[
        "source_config_sha256"
    ]
    assert selection["template_canonical_sha256"] == template_sha256
    assert selection["relationship"] == "OPPORTUNITY_SPECIFIC_SPECIALIZATION"
    assert selection["message_body_independently_hash_bound"] is True
    assert template["send_policy"] == "HUMAN_ACTION_DUE"
    assert template["attachment_policy"] == "NONE"
    assert "FRESH_DUPLICATE_RECHECK_BEFORE_SEND" in selection[
        "required_controls_preserved"
    ]
    assert gate["message"]["body_sha256"] == sha256(body)
    assert gate["message"]["body_bytes"] == body.stat().st_size
    assert gate["message"]["official_notice_link_present"] is True
    assert gate["message"]["duplicate_disclosure_present"] is True
    assert gate["message"]["attachment_count"] == 0
    assert gate["message"]["cc_count"] == 0
    assert gate["message"]["bcc_count"] == 0
    assert gate["mailbox_duplicate_preflight"]["matching_messages_before_draft"] == 0
    assert gate["fresh_duplicate_recheck"]["matching_message_count"] == 1
    assert gate["fresh_duplicate_recheck"]["matching_current_draft_count"] == 1
    assert gate["fresh_duplicate_recheck"]["matching_sent_or_received_count"] == 0
    assert gate["fresh_duplicate_recheck"]["decision"] == (
        "NO_DUPLICATE_ONLY_CURRENT_DRAFT"
    )
    assert gate["gmail_draft_receipt"]["draft_present"] is True
    assert gate["gmail_draft_receipt"]["subject_matches"] is True
    assert gate["gmail_draft_receipt"]["body_matches_source_after_newline_normalization"] is True
    assert gate["gmail_draft_receipt"]["attachment_count"] == 0
    assert gate["gmail_draft_receipt"]["sent"] is False
    assert gate["controls"]["draft_creation_authorizes_send"] is False
    assert gate["controls"]["single_use_action_time_approval_required"] is True
    assert gate["decision"] == "GMAIL_DRAFT_READY_SEND_BLOCKED"
    assert primary["outreach"]["gmail_draft_created"] is True
    assert primary["outreach"]["gmail_identifiers_stored_public"] is False
    assert primary["outreach"]["sent"] is False


def test_argos_conformance_gate_binds_requirements_and_current_blockers():
    conformance = load_json(ARGOS_CONFORMANCE)
    checks = {row["check_id"]: row for row in conformance["checks"]}

    assert conformance["schema"] == "lumencore.argos_response_conformance_gate.v1"
    assert conformance["notice_id"] == "ONC-ARGOS-SSN-2026-OS351107"
    assert conformance["deadline_utc"] == "2026-07-30T21:00:00Z"
    assert conformance["decision"] == "BLOCK_SEND_MISSING_REQUIRED_FACTS_AND_AUTHORITY"
    assert conformance["summary"] == {
        "blocked_count": 5,
        "check_count": 19,
        "external_action_performed": False,
        "fail_count": 0,
        "pass_count": 14,
        "submission_authorized": False,
    }

    expected_pass = {
        "OFFICIAL_NOTICE_CURRENT",
        "DEADLINE_OPEN",
        "ACCEPTED_FILES_PRESENT",
        "ARTIFACT_HASH_CUSTODY",
        "US_LETTER_SIZE",
        "ONE_INCH_MARGINS",
        "TWELVE_POINT_TIMES_NEW_ROMAN",
        "CONTENT_PAGE_LIMIT",
        "VISUAL_QA",
        "NO_UNAUTHORIZED_PARTNER_NAME",
        "SIMILAR_SCOPE_BOUNDARY",
        "CLAIM_BOUNDARIES",
        "CLAIM_EVIDENCE_TRACEABILITY",
        "PARTNER_DRAFT_UNSENT",
    }
    expected_blocked = {
        "PRIVATE_COVER_FACTS",
        "AUTHORIZED_NAMED_TEAM",
        "GOVERNMENT_DUPLICATE_RECHECK",
        "FINAL_DISPATCH_BINDING",
        "ACTION_TIME_APPROVAL",
    }
    assert {check_id for check_id, row in checks.items() if row["status"] == "PASS"} == expected_pass
    assert {
        check_id for check_id, row in checks.items() if row["status"] == "BLOCKED"
    } == expected_blocked
    assert all(row["status"] != "FAIL" for row in checks.values())

    custody = {row["path"]: row for row in conformance["source_custody"]}
    for relative_path, row in custody.items():
        source = ROOT / relative_path
        source_bytes = custody_bytes(source, row["hash_mode"])
        assert len(source_bytes) == row["bytes"]
        assert hashlib.sha256(source_bytes).hexdigest() == row["sha256"]


def test_argos_material_claims_are_bound_to_exact_public_evidence():
    claim_map = load_json(ARGOS_CLAIM_MAP)

    assert claim_map["schema"] == "lumencore.argos_claim_evidence_map.v1"
    assert claim_map["status"] == "VERIFIED_BOUNDED_CLAIM_MAP"
    assert claim_map["response"]["sha256"] == sha256(
        ARGOS_DIR / "ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md"
    )
    assert claim_map["response"]["material_claim_count"] == 3
    assert all(claim_map["checks"].values())
    assert all(claim["supported"] for claim in claim_map["claims"])
    assert claim_map["external_action_performed"] is False
    assert claim_map["submission_authorized"] is False

    by_id = {row["claim_id"]: row for row in claim_map["claims"]}
    replay = by_id["BOUNDED_REPRODUCIBILITY_COUNTS"]
    assert replay["evidence"]["source_commit"] == (
        "1c0eb51754beffac6f4df484914e35efc21c253f"
    )
    assert replay["evidence"]["suite_pass_count"] == 3
    assert replay["evidence"]["assertion_pass_count"] == 31
    assert "external_validation" in replay["does_not_support"]

    for row in claim_map["source_custody"]:
        source = ROOT / row["path"]
        source_bytes = custody_bytes(source, row["hash_mode"])
        assert hashlib.sha256(source_bytes).hexdigest() == row["sha256"]


def test_argos_claim_evidence_map_is_deterministic():
    result = subprocess.run(
        [
            sys.executable,
            str(ARGOS_DIR / "build_argos_claim_evidence_map.py"),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "CURRENT"
    assert receipt["decision"] == "VERIFIED_BOUNDED_CLAIM_MAP"
    assert receipt["claim_count"] == 3
    assert receipt["all_claims_supported"] is True
    assert receipt["external_action_performed"] is False
    assert receipt["submission_authorized"] is False


def test_argos_claim_evidence_map_fails_closed_on_receipt_drift(
    monkeypatch, tmp_path
):
    builder = load_argos_claim_evidence_builder()
    receipt = builder.read_json(builder.REVIEWER_RECEIPT)
    receipt["summary"]["assertion_pass_count"] = 30
    tainted = tmp_path / "reviewer_reproducibility_receipt.json"
    tainted.write_text(
        json.dumps(receipt, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(builder, "REVIEWER_RECEIPT", tainted)
    monkeypatch.setattr(builder, "rel", lambda path: str(path))

    payload = builder.build_payload("2026-07-27T20:30:00Z")
    claims = {row["claim_id"]: row for row in payload["claims"]}

    assert payload["status"] == "FAIL_CLAIM_TRACEABILITY"
    assert payload["checks"]["reviewer_receipt_counts_hold"] is False
    assert claims["BOUNDED_REPRODUCIBILITY_COUNTS"]["supported"] is False


def test_argos_conformance_outputs_are_deterministic():
    result = subprocess.run(
        [
            sys.executable,
            str(ARGOS_DIR / "build_argos_conformance_gate.py"),
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    assert receipt["status"] == "CURRENT"
    assert receipt["decision"] == "BLOCK_SEND_MISSING_REQUIRED_FACTS_AND_AUTHORITY"
    assert receipt["fail_count"] == 0
    assert receipt["submission_authorized"] is False
    assert receipt["external_action_performed"] is False


def test_argos_conformance_canonicalizes_fractional_action_timestamps():
    module = load_argos_conformance_builder()

    fractional = module.build_payload("2026-07-27T22:20:07.4384411+00:00")
    canonical = module.build_payload("2026-07-27T22:20:07Z")

    assert fractional == canonical
    assert fractional["evaluated_utc"] == "2026-07-27T22:20:07Z"
    deadline_check = next(
        row for row in fractional["checks"] if row["check_id"] == "DEADLINE_OPEN"
    )
    assert "evaluated=2026-07-27T22:20:07Z" in deadline_check["evidence"]


def test_argos_conformance_fails_on_unauthorized_partner_injection(
    monkeypatch, tmp_path
):
    builder = load_argos_conformance_builder()
    original = builder.RESPONSE_MARKDOWN.read_text(encoding="utf-8")
    tainted = tmp_path / builder.RESPONSE_MARKDOWN.name
    tainted.write_text(
        original + "\nProposed committed team member: EMI Advisors\n",
        encoding="utf-8",
        newline="\n",
    )
    monkeypatch.setattr(builder, "RESPONSE_MARKDOWN", tainted)
    monkeypatch.setattr(builder, "rel", lambda path: str(path))

    payload = builder.build_payload("2026-07-27T19:46:00Z")
    checks = {row["check_id"]: row for row in payload["checks"]}

    assert checks["NO_UNAUTHORIZED_PARTNER_NAME"]["status"] == "FAIL"
    assert "EMI Advisors" in checks["NO_UNAUTHORIZED_PARTNER_NAME"]["evidence"]
    assert checks["ARTIFACT_HASH_CUSTODY"]["status"] == "FAIL"
    assert payload["summary"]["fail_count"] >= 2
    assert payload["decision"] == "FAIL_CONFORMANCE"


def test_argos_text_custody_is_stable_across_line_endings(tmp_path):
    builder = load_argos_conformance_builder()
    lf = tmp_path / "lf.json"
    crlf = tmp_path / "crlf.json"
    lf.write_bytes(b'{\n  "status": "BLOCKED"\n}\n')
    crlf.write_bytes(b'{\r\n  "status": "BLOCKED"\r\n}\r\n')

    assert builder.custody_hash_mode(lf) == "TEXT_UTF8_LF"
    assert builder.custody_bytes(lf) == builder.custody_bytes(crlf)
    assert hashlib.sha256(builder.custody_bytes(lf)).hexdigest() == hashlib.sha256(
        builder.custody_bytes(crlf)
    ).hexdigest()


def test_argos_private_finalizer_readiness_is_redacted_and_fail_closed():
    readiness = load_json(ARGOS_PRIVATE_READINESS)
    schema = load_json(ARGOS_PRIVATE_SCHEMA)

    assert readiness["schema"] == "lumencore.argos_private_finalizer_readiness.v1"
    assert readiness["status"] == "TOOLING_VERIFIED_NO_PRIVATE_COPY_GENERATED"
    assert readiness["decision"] == "PRIVATE_INPUT_AND_ACTION_TIME_ATTESTATION_REQUIRED"
    assert readiness["required_fact_count"] == 9
    assert readiness["controls"] == {
        "external_action_performed": False,
        "government_send_authorized": False,
        "populated_facts_file_allowed_in_repository": False,
        "private_output_allowed_in_repository": False,
        "private_output_mirrored_to_public_vault": False,
        "private_values_logged": False,
        "public_templates_mutated": False,
        "team_authority_bypassed": False,
    }
    assert {"ein", "tin", "ssn", "bank_account", "routing_number", "otp"} <= set(
        readiness["prohibited_private_fields"]
    )
    assert schema["$id"] == "lumencore.argos_private_facts.v1"
    assert readiness["tool_sha256"] == sha256(
        ARGOS_DIR / "build_argos_private_action_copy.py"
    )
    assert readiness["input_schema_sha256"] == sha256(ARGOS_PRIVATE_SCHEMA)
    assert set(schema["properties"]["facts"]["required"]) == set(
        readiness["required_fact_keys"]
    )
    assert readiness["verification"]["focused_test_count"] == 37
    assert readiness["verification"]["focused_test_pass_count"] == 37
    assert readiness["verification"]["synthetic_private_values_only"] is True
    assert readiness["verification"]["synthetic_pdf_page_count"] == 10
    assert readiness["verification"]["synthetic_pdf_page_size"] == "US Letter"
    assert readiness["verification"]["post_validation_failure_cleanup_tested"] is True
    assert readiness["verification"]["duplicate_json_key_rejection_tested"] is True
    assert readiness["verification"]["public_vault_path_rejection_tested"] is True
    assert readiness["verification"]["receipt_schema_validation_tested"] is True
    assert (
        readiness["verification"][
            "tampered_external_action_controls_rejection_tested"
        ]
        is True
    )
    assert readiness["verification"]["output_size_drift_rejection_tested"] is True
    assert (
        readiness["verification"]["individual_private_value_leak_rejection_tested"]
        is True
    )
    assert readiness["verification"]["actual_private_facts_used"] is False
    assert (
        readiness["verification"]["actual_private_action_copy_generated"] is False
    )
    serialized = json.dumps({"readiness": readiness, "schema": schema}).lower()
    assert "example test entity" not in serialized
    assert "abcde" not in serialized


def test_argos_private_finalizer_builds_without_public_mutation_or_value_logging(
    tmp_path,
):
    builder = load_argos_private_finalizer()
    facts_path = tmp_path / "private_facts.json"
    output_dir = tmp_path / "private_action_copy"
    payload = dummy_private_fact_payload()
    facts_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    public_hashes_before = {
        "markdown": sha256(builder.PUBLIC_MARKDOWN),
        "docx": sha256(builder.PUBLIC_DOCX),
    }

    receipt = builder.build_private_copy(
        facts_path,
        output_dir,
        "2026-07-27T19:55:00Z",
    )
    private_markdown = output_dir / builder.TEXT_OUTPUT_NAME
    private_docx = output_dir / builder.DOCX_OUTPUT_NAME
    private_receipt = output_dir / builder.RECEIPT_OUTPUT_NAME

    assert receipt["decision"] == "PRIVATE_COVER_READY_TEAM_AND_DISPATCH_BLOCKED"
    assert receipt["required_fact_count"] == 9
    assert receipt["private_value_count"] == 9
    assert receipt["placeholder_count"] == 0
    assert receipt["public_templates"]["unchanged"] is True
    assert receipt["team_authority_resolved"] is False
    assert receipt["candidate_name_authorization_count"] == 0
    assert receipt["government_send_ready"] is False
    assert receipt["submission_authorized"] is False
    assert receipt["external_action_performed"] is False
    assert receipt["private_values_logged"] is False
    assert receipt["private_output_mirrored_to_public_vault"] is False
    assert private_markdown.is_file()
    assert private_docx.is_file()
    assert private_receipt.is_file()
    assert receipt["outputs"]["markdown"]["sha256"] == sha256(private_markdown)
    assert receipt["outputs"]["docx"]["sha256"] == sha256(private_docx)

    markdown_text = private_markdown.read_text(encoding="utf-8")
    assert builder.PRIVATE_MARKER not in markdown_text
    assert builder.PRIVATE_DISPLAY_MARKER not in markdown_text
    assert builder.PRIVATE_STATUS in markdown_text
    assert "No tax, banking, credential" in markdown_text
    for fact in payload["facts"].values():
        if fact["value"] != "NOT_APPLICABLE":
            assert fact["value"] in markdown_text

    document = builder.Document(private_docx)
    docx_text = "\n".join(
        cell.text
        for table in document.tables
        for row in table.rows
        for cell in row.cells
    )
    assert builder.PRIVATE_DISPLAY_MARKER not in docx_text
    assert payload["facts"]["legal_company_name"]["value"] in docx_text
    assert payload["facts"]["uei"]["value"] in docx_text
    header_text = "\n".join(
        paragraph.text
        for section in document.sections
        for paragraph in section.header.paragraphs
    )
    assert "Private action copy" in header_text
    assert "| Draft" not in header_text

    receipt_text = private_receipt.read_text(encoding="utf-8")
    for fact in payload["facts"].values():
        if fact["value"] != "NOT_APPLICABLE":
            assert fact["value"] not in receipt_text
    assert str(facts_path) not in receipt_text
    assert public_hashes_before == {
        "markdown": sha256(builder.PUBLIC_MARKDOWN),
        "docx": sha256(builder.PUBLIC_DOCX),
    }

    checked = builder.check_private_copy(
        facts_path,
        output_dir,
        "2026-07-27T19:56:00Z",
    )
    assert checked["outputs"] == receipt["outputs"]

    cli = subprocess.run(
        [
            sys.executable,
            str(ARGOS_DIR / "build_argos_private_action_copy.py"),
            "--facts",
            str(facts_path),
            "--output-dir",
            str(output_dir),
            "--as-of-utc",
            "2026-07-27T19:56:00Z",
            "--check",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert cli.returncode == 0, cli.stderr
    assert json.loads(cli.stdout)["status"] == "CURRENT"
    for fact in payload["facts"].values():
        if fact["value"] != "NOT_APPLICABLE":
            assert fact["value"] not in cli.stdout


def test_argos_private_finalizer_rejects_tampered_receipt_controls(tmp_path):
    builder = load_argos_private_finalizer()
    facts_path = tmp_path / "private_facts.json"
    output_dir = tmp_path / "private_action_copy"
    facts_path.write_text(
        json.dumps(dummy_private_fact_payload(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    builder.build_private_copy(
        facts_path,
        output_dir,
        "2026-07-27T19:55:00Z",
    )
    receipt_path = output_dir / builder.RECEIPT_OUTPUT_NAME
    original = json.loads(receipt_path.read_text(encoding="utf-8"))

    tampered = json.loads(json.dumps(original))
    tampered["submission_authorized"] = True
    receipt_path.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="external-action controls"):
        builder.check_private_copy(
            facts_path,
            output_dir,
            "2026-07-27T19:56:00Z",
        )

    tampered = json.loads(json.dumps(original))
    tampered["outputs"]["docx"]["bytes"] += 1
    receipt_path.write_text(
        json.dumps(tampered, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="DOCX byte count is stale"):
        builder.check_private_copy(
            facts_path,
            output_dir,
            "2026-07-27T19:56:00Z",
        )


def test_argos_private_finalizer_rejects_receipt_value_leaks(tmp_path):
    builder = load_argos_private_finalizer()
    payload = dummy_private_fact_payload()
    facts_path = tmp_path / "private_facts.json"
    output_dir = tmp_path / "private_action_copy"
    facts_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    builder.build_private_copy(
        facts_path,
        output_dir,
        "2026-07-27T19:55:00Z",
    )
    receipt_path = output_dir / builder.RECEIPT_OUTPUT_NAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["claim_boundary"] += f" {payload['facts']['uei']['value']}"
    receipt_path.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="private value leaked"):
        builder.check_private_copy(
            facts_path,
            output_dir,
            "2026-07-27T19:56:00Z",
        )


def test_argos_private_finalizer_cleans_partial_outputs_after_validation_failure(
    tmp_path,
    monkeypatch,
):
    builder = load_argos_private_finalizer()
    facts_path = tmp_path / "private_facts.json"
    output_dir = tmp_path / "private_action_copy"
    facts_path.write_text(
        json.dumps(dummy_private_fact_payload(), indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    def fail_validation(*args, **kwargs):
        raise RuntimeError("synthetic receipt validation failure")

    monkeypatch.setattr(builder, "validate_private_receipt", fail_validation)
    with pytest.raises(RuntimeError, match="synthetic receipt validation failure"):
        builder.build_private_copy(
            facts_path,
            output_dir,
            "2026-07-27T19:55:00Z",
        )

    assert output_dir.is_dir()
    assert list(output_dir.iterdir()) == []


def test_argos_private_finalizer_rejects_duplicate_json_keys(tmp_path):
    builder = load_argos_private_finalizer()
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(
        '{"schema":"first","schema":"second"}\n',
        encoding="utf-8",
        newline="\n",
    )

    with pytest.raises(ValueError, match="duplicate JSON key: schema"):
        builder.read_json(duplicate)


def test_argos_private_finalizer_rejects_public_paths_and_prohibited_fields(
    tmp_path,
    monkeypatch,
):
    builder = load_argos_private_finalizer()
    payload = dummy_private_fact_payload()
    facts_path = tmp_path / "private_facts.json"
    facts_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")

    with pytest.raises(ValueError, match="outside the public repository"):
        builder.build_private_copy(
            facts_path,
            ARGOS_DIR / "forbidden_private_output",
            "2026-07-27T19:55:00Z",
        )

    public_vault = tmp_path / "public_vault"
    monkeypatch.setattr(builder, "PUBLIC_VAULT_ROOTS", (public_vault,))
    with pytest.raises(ValueError, match="public mirror vaults"):
        builder.build_private_copy(
            facts_path,
            public_vault / "forbidden_private_output",
            "2026-07-27T19:55:00Z",
        )

    payload["facts"]["ein"] = {
        "value": "prohibited-test-value",
        "status": "VERIFIED",
        "source_kind": "OFFICIAL_ENTITY_RECORD",
        "verified_utc": "2026-07-27T18:00:00Z",
    }
    facts_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="prohibited sensitive fields"):
        builder.build_private_copy(
            facts_path,
            tmp_path / "prohibited_output",
            "2026-07-27T19:55:00Z",
        )


def test_argos_private_finalizer_rejects_false_or_future_attestations(tmp_path):
    builder = load_argos_private_finalizer()
    payload = dummy_private_fact_payload()
    payload["assertions"]["facts_current_and_accurate"] = False
    facts_path = tmp_path / "private_facts.json"
    facts_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="assertion must be explicitly true"):
        builder.build_private_copy(
            facts_path,
            tmp_path / "false_attestation",
            "2026-07-27T19:55:00Z",
        )

    payload = dummy_private_fact_payload()
    payload["facts"]["uei"]["verified_utc"] = "2026-07-28T00:00:00Z"
    facts_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="future verification timestamp"):
        builder.build_private_copy(
            facts_path,
            tmp_path / "future_attestation",
            "2026-07-27T19:55:00Z",
        )

    payload = dummy_private_fact_payload()
    payload["facts"]["company_address"]["value"] = "X" * 181
    facts_path.write_text(json.dumps(payload), encoding="utf-8", newline="\n")
    with pytest.raises(ValueError, match="private-cover length limit"):
        builder.build_private_copy(
            facts_path,
            tmp_path / "oversized_value",
            "2026-07-27T19:55:00Z",
        )


def test_argos_outreach_sequence_and_action_time_gate_remain_unsent():
    outreach = (
        ARGOS_DIR / "ARGOS_TEAMING_OUTREACH_DRAFTS_2026-07-27.md"
    ).read_text(encoding="utf-8")
    checklist = (
        ARGOS_DIR / "ARGOS_ACTION_TIME_FINALIZATION_CHECKLIST_2026-07-27.md"
    ).read_text(encoding="utf-8")

    assert "READY_FOR_REVIEW - NOT SENT" in outreach
    assert "First-contact attachment set: none." in outreach
    assert "not sent in parallel by default" in outreach
    assert "Current decision:** `BLOCK_SEND`" in checklist
    assert "Exact action-time approval" in checklist
    assert "Private identifiers stay outside the public repository" in checklist


def test_opportunity_and_science_maps_preserve_current_gates():
    opportunity = OPPORTUNITY_MAP.read_text(encoding="utf-8")
    science = SCIENCE_MAP.read_text(encoding="utf-8")

    assert "Benefits.gov has closed" in opportunity
    assert "USA.gov Benefit Finder" in opportunity
    assert "DLA Emergent IV R&D BAA" in opportunity
    assert "DLA / DoD SBIR-STTR Release 4" in opportunity
    assert "FHWA TSMO Data Initiative" in opportunity
    assert "NSF Energy-Water Security Consortium BAA" in opportunity
    assert "DoDEA Data and AI Modernization Support" in opportunity
    assert "Explicit Pass Lanes" in opportunity
    assert "no verified, action-safe solo-prime submission" in opportunity
    assert "SAM.gov Data Services" in opportunity
    assert "Acquisition.gov" in opportunity
    assert "USAspending.gov" in opportunity
    assert "not where LumenCore submits a bid" in opportunity
    assert "not an opportunity or application portal" in opportunity
    assert "not guaranteed payments" in opportunity
    assert "No automated sign-in" in opportunity
    assert "exact action-time approval" in opportunity
    assert "Deadline Action Sentinel" in opportunity

    assert "no promoted champion" in science
    assert "Kuramoto phase-coupling candidate recorded 1.253509" in science
    assert "XGBoost residual model at MASE 0.211206" in science
    assert "not yet a champion" in science
    assert "dollar values must be labeled scenarios" in science


def test_e_drive_tools_are_non_destructive_and_explicit_file_only():
    mirror = (ROOT / "code" / "ops" / "MIRROR_REVIEW_PACKET_TO_E_DRIVE.ps1").read_text(
        encoding="utf-8"
    )
    inventory = (
        ROOT / "code" / "ops" / "BUILD_E_DRIVE_PROOF_VAULT_INVENTORY.ps1"
    ).read_text(encoding="utf-8")
    combined = mirror + inventory

    for forbidden in ("Remove-Item", "Move-Item", "robocopy", "/MIR"):
        assert forbidden not in combined
    assert "Only explicit files are accepted" in mirror
    assert "destructive_delete_used = $false" in mirror
    assert "source_commit = $sourceCommit" in mirror
    assert "source_worktree_clean = $true" in mirror
    assert "SourceRoot must be clean" in mirror
    assert "private_filenames_exported = $false" in inventory


def test_packet_files_have_cross_platform_byte_custody():
    expected = {
        "assets/brand/lumaarc_arc_seal_v1.png": {
            "text": "unset",
            "binary": "set",
        },
        "grant_submissions/ONC_ARGOS_20260730/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.md": {
            "text": "set",
            "eol": "lf",
            "binary": "unspecified",
        },
        "grant_submissions/ONC_ARGOS_20260730/output/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.docx": {
            "text": "unset",
            "binary": "set",
        },
        "grant_submissions/ONC_ARGOS_20260730/output/ARGOS_PARTNER_FIRST_CAPABILITY_RESPONSE_DRAFT.pdf": {
            "text": "unset",
            "binary": "set",
        },
    }
    paths = list(expected)
    result = subprocess.run(
        ["git", "check-attr", "text", "eol", "binary", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    observed: dict[str, dict[str, str]] = {path: {} for path in paths}
    for line in result.stdout.splitlines():
        path, attribute, value = line.rsplit(": ", 2)
        observed[path][attribute] = value

    for path, attributes in expected.items():
        for attribute, value in attributes.items():
            assert observed[path][attribute] == value
