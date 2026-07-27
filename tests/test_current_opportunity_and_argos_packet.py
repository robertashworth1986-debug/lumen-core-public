from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BRAND_DIR = ROOT / "assets" / "brand"
ARGOS_DIR = ROOT / "grant_submissions" / "ONC_ARGOS_20260730"
ARGOS_OUTPUT = ARGOS_DIR / "output"
OPPORTUNITY_MAP = ROOT / "docs" / "CURRENT_FEDERAL_OPPORTUNITY_GATE_MAP_2026-07-26.md"
SCIENCE_MAP = ROOT / "docs" / "SCIENTIFIC_CONTRIBUTION_AND_NEXT_EXPERIMENTS_2026-07-26.md"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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
    primary = load_json(
        ARGOS_DIR / "ARGOS_TEAMING_CANDIDATE_REGISTER_2026-07-27.json"
    )["candidates"][0]

    assert gate["schema"] == "lumencore.argos_partner_dispatch_gate.v1"
    assert gate["recipient_route"]["organization"] == "EMI Advisors LLC"
    assert gate["recipient_route"]["public_route_verified"] is True
    assert gate["recipient_route"]["recipient_address_stored_in_public_gate"] is False
    assert gate["message"]["body_sha256"] == sha256(body)
    assert gate["message"]["body_bytes"] == body.stat().st_size
    assert gate["message"]["attachment_count"] == 0
    assert gate["message"]["cc_count"] == 0
    assert gate["message"]["bcc_count"] == 0
    assert gate["mailbox_duplicate_preflight"]["matching_messages_before_draft"] == 0
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
