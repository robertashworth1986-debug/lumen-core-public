from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MONDAY_FEDERAL_ACTION_PACKET.py"
CONFIG = ROOT / "config" / "monday_federal_action_packet_v1.json"
AS_OF_UTC = "2026-07-26T01:15:24Z"


def load_module():
    spec = importlib.util.spec_from_file_location("monday_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def test_config_is_fail_closed_and_uses_official_sources():
    module = load_module()
    config = load_config()
    module.validate_config(config)

    assert module.ARC_SEAL_LOGO == (
        ROOT / "assets" / "brand" / "lumaarc_eclipse_corona_concept_v1.png"
    )
    assert module.ARC_SEAL_LOGO.is_file()
    assert config["controls"] == module.EXPECTED_CONTROLS
    assert config["controls"]["autonomous_email_send_allowed"] is False
    assert config["controls"]["autonomous_submission_allowed"] is False
    assert config["controls"]["action_time_human_approval_required"] is True
    assert config["controls"]["response_instructions_structured"] is True
    assert (
        config["controls"]["source_set_completeness_required_for_ready_state"] is True
    )
    assert len(config["opportunities"]) == 5
    for opportunity in config["opportunities"]:
        assert opportunity["official_url"].startswith("https://sam.gov/")
        assert opportunity["mandatory_requirements"]
        assert opportunity["source_files"]
        assert all(
            set(source_file) == {"path", "official_url", "role"}
            for source_file in opportunity["source_files"]
        )
        assert set(opportunity["response_instructions"]) == (
            module.REQUIRED_RESPONSE_INSTRUCTION_FIELDS
        )
        assert all(
            requirement["state"] == "NOT_ESTABLISHED"
            for requirement in opportunity["mandatory_requirements"]
        )


def test_packet_has_no_ready_prime_or_partner_response():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)

    assert payload["status"] == "NO_TRUTHFUL_MONDAY_PRIME_OR_PARTNER_RESPONSE_READY"
    assert payload["summary"] == {
        "opportunity_count": 5,
        "prime_submission_ready_count": 0,
        "partner_brief_ready_count": 0,
        "future_partner_route_count": 3,
        "complete_source_set_count": 4,
        "partial_source_set_count": 1,
        "instruction_conformance_ready_count": 0,
        "no_go_or_partner_only_count": 5,
        "closed_deadline_count": 0,
        "external_action_count": 0,
    }
    assert len(payload["control_sha256"]) == 64
    assert all(
        opportunity["external_action_authorized"] is False
        for opportunity in payload["opportunities"]
    )
    snapshot = payload["current_evidence_snapshot"]
    assert snapshot["registered_family_count"] == 140
    assert snapshot["implementation_present_count"] == 35
    assert snapshot["executed_direct_source_baseline_comparison_count"] == 126
    assert snapshot["promotion_gate_pass_count"] == 0
    assert snapshot["global_holm_positive_count"] == 0
    assert snapshot["prospective_protocol_status"] == (
        "FROZEN_AWAITING_FUTURE_OBSERVATIONS"
    )
    assert snapshot["performance_claim_allowed"] is False
    assert all(len(receipt["sha256"]) == 64 for receipt in snapshot["source_receipts"])


def test_csdr_future_partner_route_is_blocked_with_frozen_source_receipts():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)
    csdr = next(
        row for row in payload["opportunities"] if row["notice_id"] == "FA701426SCS01"
    )

    assert csdr["decision"] == "NO_READY_RESPONSE_FUTURE_PARTNER_ROUTE_BLOCKED"
    assert csdr["prime_submission_ready"] is False
    assert csdr["partner_brief_ready"] is False
    assert csdr["future_partner_route_possible_not_ready"] is True
    assert csdr["instruction_conformance_ready"] is False
    assert csdr["duplicate_state"] == (
        "FRIDAY_CAPABILITY_EMAIL_ALREADY_SENT_NO_DUPLICATE"
    )
    assert set(csdr["missing_mandatory_evidence"]) == {
        "direct_csdr_flexfile_experience",
        "secret_cleared_personnel",
        "task_three_lead",
        "task_four_lead",
    }
    assert {receipt["sha256"] for receipt in csdr["source_files"]} == {
        "477A943F5813507CE6B36B612F1EEAFD005BD88EC1BED7F2D2F299AC5DC8DC91",
        "0B899A7565115FDFC694A7ED163A751BA8A71A2DAA8D08175761C1D2EFAF8849",
    }


def test_markdown_refuses_polish_as_a_substitute_for_qualification():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)
    rendered = module.render_markdown(payload)
    partner = module.render_csdr_partner_brief(payload)

    assert "A polished response cannot cure a mandatory qualification gap." in rendered
    assert "Do not submit a prime CSDR white paper." in rendered
    assert "NOT_READY_FOR_PRIME_OR_PARTNER_SEND" in partner
    assert "not a send-ready partner brief" in partner
    assert "No outreach was sent by this builder." in partner
    assert "does not claim direct CSDR or FlexFile past performance" in partner
    assert "every performing contractor and subcontractor person" in partner
    assert "Bounded Partner Outreach Draft" not in partner


def test_pha_uses_current_qa_and_future_partner_state_without_il5_false_gate():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)
    pha = next(
        row
        for row in payload["opportunities"]
        if row["notice_id"] == "HT003826SC004AOI1"
    )

    assert pha["partner_route_state"] == "POSSIBLE_NOT_READY"
    assert pha["partner_brief_ready"] is False
    assert "dod_il5_environment" not in {
        requirement["id"] for requirement in pha["mandatory_requirements"]
    }
    assert {receipt["sha256"] for receipt in pha["source_files"]} == {
        "34C8135B4D3E5FA128010702C55684B71A3632DEE70C8693A658D8DFAE12A6AC",
        "A3CDD12A01A9DE4745D0C3F6DB7E7FAE12A10B1B3F4148917F11125FB3E1684B",
    }
    assert "synthetic" in pha["response_instructions"]["format_rules"].lower()


def test_literal_timezone_and_conservative_cutoffs_are_preserved():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)
    by_notice = {row["notice_id"]: row for row in payload["opportunities"]}

    nasa = by_notice["80NSSC26938528Q"]
    assert "Central Standard Time" in nasa["deadline_source_literal"]
    assert nasa["deadline_utc"] == "2026-07-27T17:00:00Z"
    assert nasa["timezone_clarification_required"] is True

    jmitt = by_notice["HS002126QE046"]
    assert jmitt["deadline_source_literal"].endswith("10:00 a.m. EST")
    assert jmitt["deadline_utc"] == "2026-07-27T14:00:00Z"
    assert jmitt["timezone_clarification_required"] is True
    assert jmitt["source_set_complete"] is False
    assert jmitt["source_set_state"] == (
        "FROZEN_PARTIAL_ATTACHMENTS_NOT_CAPTURED"
    )


def test_response_instructions_and_frozen_source_receipts_are_structured():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)

    for opportunity in payload["opportunities"]:
        instructions = opportunity["response_instructions"]
        assert instructions["channel"]
        assert instructions["recipient_role_count"] >= 1
        assert instructions["subject_line"]
        assert instructions["file_format"]
        assert instructions["page_limit"]
        assert instructions["required_contents"]
        assert instructions["source_precedence"]
        for receipt in opportunity["source_files"]:
            assert receipt["official_url"].startswith("https://sam.gov/")
            assert receipt["role"]
            assert receipt["bytes"] > 0
            assert len(receipt["sha256"]) == 64


def test_duplicate_notice_or_relaxed_control_is_rejected():
    module = load_module()
    duplicate = load_config()
    duplicate["opportunities"][1]["notice_id"] = duplicate["opportunities"][0][
        "notice_id"
    ]
    with pytest.raises(module.PacketError, match="Duplicate"):
        module.validate_config(duplicate)

    relaxed = load_config()
    relaxed["controls"]["autonomous_email_send_allowed"] = True
    with pytest.raises(module.PacketError, match="fail-closed"):
        module.validate_config(relaxed)


def test_unverified_mandatory_requirement_cannot_be_prime_ready():
    module = load_module()
    payload = module.build_packet(CONFIG, as_of_utc=AS_OF_UTC)
    assert not any(row["prime_submission_ready"] for row in payload["opportunities"])

    tampered = copy.deepcopy(load_config())
    tampered["opportunities"][0]["decision"] = "PREPARE_FOR_HUMAN_SUBMIT_REVIEW"
    with pytest.raises(module.PacketError, match="decision is invalid"):
        module.validate_config(tampered)
