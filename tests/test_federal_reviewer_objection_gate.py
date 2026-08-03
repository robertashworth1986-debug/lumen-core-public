from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = (
    ROOT / "code" / "ops" / "BUILD_FEDERAL_REVIEWER_OBJECTION_GATE.py"
)
CONFIG_PATH = ROOT / "config" / "federal_reviewer_objection_register_v1.json"
AS_OF_UTC = "2026-07-26T22:12:20Z"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "federal_reviewer_objection_gate",
        MODULE_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def copy_review_materials(config: dict, destination_root: Path) -> Path:
    destination_root.mkdir(parents=True, exist_ok=True)
    for material in config["review_scope"]["materials"]:
        source = ROOT / material["path"]
        destination = destination_root / material["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    return destination_root


def objection_by_id(gate: dict, objection_id: str) -> dict:
    return next(row for row in gate["objections"] if row["id"] == objection_id)


def blocker_codes(gate: dict) -> set[str]:
    return {row["code"] for row in gate["material_blockers"]}


def test_register_covers_all_mandatory_cross_agency_categories():
    module = load_module()
    config = load_config()

    module.validate_config(config)

    categories = {row["category"] for row in config["objections"]}
    assert module.MANDATORY_CATEGORIES <= categories
    assert {
        "legal_entity_registration",
        "naics_psc_set_aside_fit",
        "past_performance",
        "personnel_and_clearances",
        "cybersecurity",
        "data_rights",
        "technical_baselines",
        "independent_evidence",
        "staffing_price_schedule",
        "deployment_and_operations",
        "teaming_boundaries",
        "exact_solicitation_conformance",
    } <= categories
    for row in config["objections"]:
        assert row["required_evidence"]
        assert row["current_state"]["code"]
        assert row["claim_boundary"]
        assert row["safe_next_action"]


def test_current_gate_fails_closed_with_zero_external_actions():
    module = load_module()
    config = load_config()

    gate = module.build_gate(config, root=ROOT, as_of_utc=AS_OF_UTC)

    assert gate["summary"]["status"] == (
        "BLOCKED_UNRESOLVED_REVIEWER_OBJECTIONS"
    )
    assert gate["summary"]["material_blocker_count"] == 0
    assert gate["summary"]["objection_count"] == 14
    assert gate["summary"]["unresolved_objection_count"] == 13
    assert gate["summary"]["blocking_objection_count"] == 13
    assert gate["summary"]["resolved_objection_count"] == 1
    assert gate["summary"]["prime_submission_allowed"] is False
    assert gate["summary"]["external_capability_distribution_allowed"] is False
    assert gate["summary"]["partner_outreach_allowed"] is False
    assert gate["summary"]["external_action_count"] == 0
    assert gate["capability_boundary"]["network_access_performed"] is False
    assert gate["capability_boundary"]["email_send_performed"] is False
    assert gate["capability_boundary"]["portal_action_performed"] is False
    assert gate["capability_boundary"]["submission_performed"] is False


def test_software_pattern_and_operational_proof_are_not_conflated():
    module = load_module()
    gate = module.build_gate(load_config(), root=ROOT, as_of_utc=AS_OF_UTC)

    baseline = objection_by_id(gate, "OBJ-BASELINE-001")
    operations = objection_by_id(gate, "OBJ-OPS-001")

    assert baseline["current_state"]["code"] == "SOFTWARE_PATTERN_PROOF_ONLY"
    assert baseline["current_state"]["evidence_class"] == (
        "SOFTWARE_PATTERN_PROOF"
    )
    assert operations["current_state"]["code"] == (
        "DEPLOYMENT_OPERATIONS_NOT_ESTABLISHED"
    )
    assert operations["current_state"]["evidence_class"] == "OPERATIONAL_PROOF"
    assert gate["evidence_distinction"][
        "software_pattern_proof_satisfies_operational_proof"
    ] is False
    assert "never converts" in gate["evidence_distinction"][
        "conversion_rule"
    ].lower()


def test_current_materials_match_frozen_hashes_and_monday_packet_is_blocked():
    module = load_module()
    gate = module.build_gate(load_config(), root=ROOT, as_of_utc=AS_OF_UTC)

    assert len(gate["material_receipts"]) == 5
    assert all(row["exists"] for row in gate["material_receipts"])
    assert all(row["hash_matches"] for row in gate["material_receipts"])
    assert all(row["content_checks_valid"] for row in gate["material_receipts"])

    monday = gate["monday_packet_observation"]
    assert monday["valid"] is True
    assert monday["opportunity_count"] == 5
    assert monday["prime_submission_ready_count"] == 0
    assert monday["partner_brief_ready_count"] == 0
    assert monday["external_action_count"] == 0
    assert monday["all_prime_blocked"] is True
    assert monday["all_partner_briefs_blocked"] is True
    assert monday["all_external_actions_blocked"] is True


def test_missing_required_material_blocks_before_objection_resolution():
    module = load_module()
    config = load_config()
    config["review_scope"]["materials"][0]["path"] = (
        "grant_submissions/missing_monday_packet.json"
    )

    gate = module.build_gate(config, root=ROOT, as_of_utc=AS_OF_UTC)

    assert gate["summary"]["status"] == "BLOCKED_REVIEW_MATERIALS_UNRESOLVED"
    assert "REQUIRED_MATERIAL_MISSING" in blocker_codes(gate)
    assert gate["summary"]["prime_submission_allowed"] is False


def test_material_hash_drift_blocks_external_use():
    module = load_module()
    config = load_config()
    config["review_scope"]["materials"][1]["expected_sha256"] = "0" * 64

    gate = module.build_gate(config, root=ROOT, as_of_utc=AS_OF_UTC)

    assert gate["summary"]["status"] == "BLOCKED_REVIEW_MATERIALS_UNRESOLVED"
    assert "MATERIAL_HASH_MISMATCH" in blocker_codes(gate)
    assert gate["summary"]["external_capability_distribution_allowed"] is False


def test_tampered_monday_packet_cannot_become_prime_ready(
    tmp_path: Path,
):
    module = load_module()
    config = load_config()
    fixture_root = copy_review_materials(config, tmp_path / "repo")
    monday_path = fixture_root / config["review_scope"]["materials"][0]["path"]
    payload = json.loads(monday_path.read_text(encoding="utf-8"))
    payload["summary"]["prime_submission_ready_count"] = 1
    payload["opportunities"][0]["prime_submission_ready"] = True
    monday_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    config["review_scope"]["materials"][0]["expected_sha256"] = (
        module.file_sha256(monday_path)
    )

    gate = module.build_gate(
        config,
        root=fixture_root,
        as_of_utc=AS_OF_UTC,
    )

    assert gate["summary"]["status"] == "BLOCKED_REVIEW_MATERIALS_UNRESOLVED"
    assert "MATERIAL_CONTENT_CHECK_FAILED" in blocker_codes(gate)
    assert gate["monday_packet_observation"]["valid"] is False
    assert "MONDAY_PRIME_READY_COUNT_NONZERO" in gate[
        "monday_packet_observation"
    ]["failures"]
    assert "MONDAY_PRIME_FLAG_NOT_FAIL_CLOSED" in gate[
        "monday_packet_observation"
    ]["failures"]


def test_tampered_monday_packet_cannot_become_partner_ready(
    tmp_path: Path,
):
    module = load_module()
    config = load_config()
    fixture_root = copy_review_materials(config, tmp_path / "repo")
    monday_path = fixture_root / config["review_scope"]["materials"][0]["path"]
    payload = json.loads(monday_path.read_text(encoding="utf-8"))
    payload["summary"]["partner_brief_ready_count"] = 1
    payload["opportunities"][0]["partner_brief_ready"] = True
    monday_path.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    config["review_scope"]["materials"][0]["expected_sha256"] = (
        module.file_sha256(monday_path)
    )

    gate = module.build_gate(
        config,
        root=fixture_root,
        as_of_utc=AS_OF_UTC,
    )

    assert gate["summary"]["status"] == "BLOCKED_REVIEW_MATERIALS_UNRESOLVED"
    assert "MATERIAL_CONTENT_CHECK_FAILED" in blocker_codes(gate)
    assert "MONDAY_PARTNER_READY_COUNT_NONZERO" in gate[
        "monday_packet_observation"
    ]["failures"]
    assert "MONDAY_PARTNER_FLAG_NOT_FAIL_CLOSED" in gate[
        "monday_packet_observation"
    ]["failures"]


def test_relaxed_control_or_private_identifier_is_rejected():
    module = load_module()

    relaxed = load_config()
    relaxed["controls"]["autonomous_email_send_allowed"] = True
    with pytest.raises(module.GateError, match="fail-closed"):
        module.validate_config(relaxed)

    private = load_config()
    private["objections"][0]["email_address"] = "reviewer@example.invalid"
    with pytest.raises(module.GateError, match="private-data key"):
        module.validate_config(private)


def test_arc_seal_is_bound_and_render_verified_but_distribution_stays_blocked():
    module = load_module()
    gate = module.build_gate(load_config(), root=ROOT, as_of_utc=AS_OF_UTC)
    brand = objection_by_id(gate, "OBJ-BRAND-001")

    assert brand["current_state"]["code"] == "ARC_SEAL_BOUND_AND_RENDER_VERIFIED"
    assert brand["resolved"] is True
    assert brand["current_state"]["page_count"] == 2
    assert brand["current_state"]["asset_sha256"] == (
        "1ED1C9B00E273AA9E781BD7FD0A4FCC3FC542257C6D294C8E8FBFADA500701AF"
    )
    assert brand["current_state"]["rendered_pdf_sha256"] == (
        "C5CD72F62491688781EEC801BB9ED6A2C368EB9A7412754D476B25DE3EDE5967"
    )
    assert "both pages" in brand["current_state"]["basis"].lower()
    assert gate["summary"]["external_capability_distribution_allowed"] is False


def test_gate_hash_and_documentation_are_deterministic_and_public_safe():
    module = load_module()
    config = load_config()

    first = module.build_gate(config, root=ROOT, as_of_utc=AS_OF_UTC)
    second = module.build_gate(config, root=ROOT, as_of_utc=AS_OF_UTC)
    document = module.render_documentation(first)

    expected = dict(first)
    observed_hash = expected.pop("gate_sha256")
    assert first == second
    assert observed_hash == module.canonical_sha256(expected)
    assert "Prime submission allowed: `false`" in document
    assert "Software-pattern proof" in document
    assert "Operational proof" in document
    assert "@" not in document
    assert "zoom.us" not in document.lower()
    assert "teams.microsoft.com" not in document.lower()


def test_builder_source_has_no_network_or_external_action_client():
    source = MODULE_PATH.read_text(encoding="utf-8").lower()

    assert "import requests" not in source
    assert "import smtplib" not in source
    assert "import webbrowser" not in source
    assert "import selenium" not in source
    assert "import playwright" not in source
    assert "subprocess" not in source


def test_strict_mode_returns_nonzero_without_writing(monkeypatch):
    module = load_module()
    writes: list[dict] = []
    monkeypatch.setattr(
        module,
        "write_outputs",
        lambda gate: writes.append(gate),
    )

    result = module.main(
        [
            "--config",
            str(CONFIG_PATH),
            "--as-of-utc",
            AS_OF_UTC,
            "--strict",
        ]
    )

    assert result == 1
    assert len(writes) == 1
    assert writes[0]["summary"]["status"] == (
        "BLOCKED_UNRESOLVED_REVIEWER_OBJECTIONS"
    )
    assert writes[0]["summary"]["external_action_count"] == 0
