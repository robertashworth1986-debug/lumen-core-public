from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CMMC_EXPORT_EVIDENCE_PACKET.py"
CONFIG = ROOT / "config" / "cmmc_export_evidence_packet_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("cmmc_export_evidence_packet", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def requirement(config: dict, fact_id: str) -> dict:
    for program in config["programs"]:
        for item in program["requirements"]:
            if item["fact_id"] == fact_id:
                return item
    raise AssertionError(f"missing fact: {fact_id}")


def valid_jcp_evidence(evidence_id: str = "jcp-proof") -> dict:
    return {
        "artifact_ref": f"private-ref:{evidence_id}",
        "artifact_sha256": "a" * 64,
        "conflict": False,
        "entity_match": "MATCH",
        "evidence_id": evidence_id,
        "expires_utc": "2027-01-01T00:00:00Z",
        "issued_utc": "2026-07-18T00:00:00Z",
        "issuer": "JCP",
        "proof_state": "ISSUED",
        "scope_match": "MATCH",
        "source_class": "PORTAL_ISSUED",
    }


def test_default_packet_is_private_safe_incomplete_and_hash_valid():
    module = load_module()
    config = load_config()
    first = module.build_packet(config)
    second = module.build_packet(config)

    assert first == second
    assert first["packet_state"] == "EVIDENCE_INCOMPLETE"
    assert first["summary"]["program_count"] == 3
    assert first["summary"]["open_requirement_count"] == first["summary"]["requirement_count"]
    assert module.verify_packet_hash(first)
    assert first["source_classes"] == list(module.ALLOWED_SOURCE_CLASSES)

    serialized = json.dumps(first, sort_keys=True).lower()
    assert "reviewer_name" not in serialized
    assert "@" not in serialized
    assert "\\users\\" not in serialized
    assert "uei" not in serialized
    assert "cage" not in serialized
    assert "does not determine or claim compliance" in first["claim_boundary"].lower()
    assert "does not open referenced private evidence" in first["evaluation_limit"].lower()
    assert first["summary"]["issue_count"] >= first["summary"]["open_requirement_count"]


def test_founder_boolean_or_portal_observation_never_upgrades_proof():
    module = load_module()
    config = load_config()
    item = requirement(config, "missionweave.jcp_application_submitted")
    item["evidence"] = [
        {
            **valid_jcp_evidence("founder-says-yes"),
            "proof_state": "ATTESTED",
            "source_class": "FOUNDER_ATTESTATION",
            "value": True,
        },
        {
            **valid_jcp_evidence("portal-seen"),
            "proof_state": "OBSERVED",
            "source_class": "PORTAL_OBSERVED",
        },
    ]

    packet = module.build_packet(config)
    result = next(
        row
        for program in packet["programs"]
        for row in program["requirements"]
        if row["fact_id"] == item["fact_id"]
    )
    assert result["authoritative_proof_count"] == 0
    assert result["evidence_state"] == "MISSING_OFFICIAL_PROOF"
    codes = {issue["code"] for issue in result["issues"]}
    assert "LOCAL_OR_OBSERVED_EVIDENCE_NOT_AUTHORITATIVE" in codes
    assert "MISSING_OFFICIAL_PROOF" in codes


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ({"entity_match": "MISMATCH"}, "ENTITY_NOT_MATCHED"),
        ({"scope_match": "MISMATCH"}, "SCOPE_NOT_MATCHED"),
        ({"conflict": True}, "CONFLICT_PRESENT_OR_UNRESOLVED"),
        ({"artifact_sha256": "not-a-hash"}, "ARTIFACT_SHA256_MALFORMED"),
        ({"expires_utc": "2026-07-01T00:00:00Z"}, "EVIDENCE_EXPIRED"),
    ],
)
def test_wrong_scope_entity_stale_conflict_or_hash_fails_closed(mutation, expected_code):
    module = load_module()
    config = load_config()
    item = requirement(config, "missionweave.jcp_application_submitted")
    evidence = valid_jcp_evidence()
    evidence.update(mutation)
    item["evidence"] = [evidence]

    packet = module.build_packet(config)
    result = next(
        row
        for program in packet["programs"]
        for row in program["requirements"]
        if row["fact_id"] == item["fact_id"]
    )
    assert result["evidence_state"] == "MISSING_OFFICIAL_PROOF"
    assert result["authoritative_proof_count"] == 0
    assert expected_code in {issue["code"] for issue in result["issues"]}


def test_valid_portal_issued_metadata_only_inventories_one_requirement():
    module = load_module()
    config = load_config()
    item = requirement(config, "missionweave.jcp_application_submitted")
    item["evidence"] = [valid_jcp_evidence()]

    packet = module.build_packet(config)
    result = next(
        row
        for program in packet["programs"]
        for row in program["requirements"]
        if row["fact_id"] == item["fact_id"]
    )
    assert result["evidence_state"] == "AUTHORITATIVE_PROOF_INVENTORIED"
    assert result["authoritative_proof_count"] == 1
    assert packet["packet_state"] == "EVIDENCE_INCOMPLETE"
    assert all(term in result["prohibited_conclusions"] for term in module.PROHIBITED_CONCLUSIONS)


def test_not_applicable_requires_named_legal_or_contracting_review():
    module = load_module()
    config = load_config()
    item = requirement(config, "missionweave.subcontractor_flowdown")
    item["applicability"] = {"state": "NOT_APPLICABLE"}

    packet = module.build_packet(config)
    result = next(
        row
        for program in packet["programs"]
        for row in program["requirements"]
        if row["fact_id"] == item["fact_id"]
    )
    assert result["evidence_state"] == "NOT_APPLICABLE_UNSUPPORTED"
    assert "NOT_APPLICABLE_REQUIRES_NAMED_REVIEW" in {
        issue["code"] for issue in result["issues"]
    }

    item["applicability"] = {
        "decided_by_source_class": "LEGAL_REVIEW",
        "decided_utc": "2026-07-18T00:00:00Z",
        "decision_ref": "private-ref:subcontract-review",
        "decision_sha256": "b" * 64,
        "reviewer_name": "Qualified Reviewer",
        "reviewer_role": "Export legal counsel",
        "state": "NOT_APPLICABLE",
    }
    packet = module.build_packet(config)
    result = next(
        row
        for program in packet["programs"]
        for row in program["requirements"]
        if row["fact_id"] == item["fact_id"]
    )
    assert result["evidence_state"] == "NOT_APPLICABLE_REVIEW_INVENTORIED"
    assert result["applicability"]["named_reviewer_present"] is True
    assert "reviewer_name" not in result["applicability"]


def test_itar_ear_and_jcp_certification_are_distinct_facts():
    module = load_module()
    packet = module.build_packet(load_config())
    fact_ids = {
        row["fact_id"]
        for program in packet["programs"]
        for row in program["requirements"]
    }
    for prefix in ("harbor", "missionweave"):
        assert f"{prefix}.itar_classification" in fact_ids
        assert f"{prefix}.ear_classification" in fact_ids
        assert f"{prefix}.jcp_application_submitted" in fact_ids
        assert f"{prefix}.dd2345_certified" in fact_ids


def test_invalid_source_class_and_unsafe_source_path_are_rejected():
    module = load_module()
    config = load_config()
    item = requirement(config, "dice.cmmc_l1_sprs_final")
    item["accepted_source_classes"] = ["LOCAL_RECEIPT"]
    with pytest.raises(module.PacketConfigError):
        module.build_packet(config)


def test_duplicate_facts_and_evidence_ids_are_rejected():
    module = load_module()
    config = load_config()
    config["programs"][1]["requirements"][0]["fact_id"] = config["programs"][0][
        "requirements"
    ][0]["fact_id"]
    with pytest.raises(module.PacketConfigError):
        module.build_packet(config)

    config = load_config()
    item = requirement(config, "missionweave.jcp_application_submitted")
    item["evidence"] = [valid_jcp_evidence(), valid_jcp_evidence()]
    with pytest.raises(module.PacketConfigError):
        module.build_packet(config)

    config = load_config()
    config["programs"][0]["requirements_sources"][0]["path"] = "../private.pdf"
    with pytest.raises(module.PacketConfigError):
        module.build_packet(config)


def test_json_and_markdown_outputs_are_deterministic(tmp_path):
    module = load_module()
    packet = module.build_packet(load_config())
    first_json = tmp_path / "first.json"
    first_md = tmp_path / "first.md"
    second_json = tmp_path / "second.json"
    second_md = tmp_path / "second.md"

    module.write_outputs(packet, first_json, first_md)
    module.write_outputs(deepcopy(packet), second_json, second_md)
    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_md.read_bytes() == second_md.read_bytes()
    assert packet["integrity"]["packet_sha256"] in first_md.read_text(encoding="utf-8")
