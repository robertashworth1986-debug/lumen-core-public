from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_HARBORSENTINEL_DEADLINE_GATE.py"
EVIDENCE = ROOT / "config" / "harborsentinel_deadline_evidence_v1.json"
JSON_OUT = ROOT / "dashboard" / "data" / "harborsentinel_deadline_gate.json"
MD_OUT = ROOT / "docs" / "HARBORSENTINEL_DEADLINE_READINESS_GATE_2026-07-19.md"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "harborsentinel_deadline_gate", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_checked_in_gate_verifies_deadline_and_fails_closed():
    module = load_module()
    gate = module.build_gate(load_evidence())

    assert gate["schema"] == "harborsentinel_deadline_gate_v1"
    assert gate["posture"] == "BLOCKED_UNKNOWN_NOT_VERIFIED"
    assert gate["deadline_conclusion"] == "VERIFIED_REAL_DEADLINE"
    assert gate["requirements_conclusion"] == "VERIFIED_REQUIREMENTS"
    assert gate["notice"]["topic_id"] == "DON26BZ03-NV063"
    assert gate["notice"]["deadline_local_iso"] == "2026-07-22T12:00:00-04:00"
    assert gate["notice"]["deadline_utc_iso"] == "2026-07-22T16:00:00Z"
    assert gate["proposal_state"]["local_candidate"]["status"] == "EXISTS_LOCAL_DRAFT"
    assert gate["proposal_state"]["dsip_proposal_record"] == module.UNKNOWN
    assert gate["proposal_state"]["portal_status"] == module.UNKNOWN
    assert gate["proposal_state"]["submission_status"] == module.UNKNOWN
    assert [
        item["volume"] for item in gate["requirements"]["required_volumes"]
    ] == list(range(1, 8))
    assert gate["authority_boundary"]["upload_authorized"] is False
    assert gate["authority_boundary"]["certification_authorized"] is False
    assert gate["authority_boundary"]["submission_authorized"] is False
    assert gate["blockers"]


def test_verified_deadline_cannot_clear_unknown_portal_or_eligibility_state():
    module = load_module()
    evidence = load_evidence()
    for item in evidence["eligibility"]:
        item["applicant_status"] = module.VERIFIED
    evidence["proposal_state"]["eligibility_complete"] = module.VERIFIED

    gate = module.build_gate(evidence)

    assert gate["deadline_conclusion"] == "VERIFIED_REAL_DEADLINE"
    assert gate["action_readiness_checks"]["eligibility_verified"] is True
    assert gate["action_readiness_checks"]["dsip_proposal_record_verified"] is False
    assert gate["posture"] == "BLOCKED_UNKNOWN_NOT_VERIFIED"
    assert gate["authority_boundary"]["submission_authorized"] is False


def test_unverified_official_source_makes_deadline_unknown_and_blocks():
    module = load_module()
    evidence = copy.deepcopy(load_evidence())
    evidence["official_sources"][0]["verification"] = module.UNKNOWN

    gate = module.build_gate(evidence)

    assert gate["deadline_conclusion"] == module.UNKNOWN
    assert gate["posture"] == "BLOCKED_SOURCE_UNKNOWN_NOT_VERIFIED"
    assert gate["official_fact_checks"]["authoritative_sources_current"] is False
    assert gate["authority_boundary"]["submission_authorized"] is False


def test_missing_volume_descriptor_fails_source_gate():
    module = load_module()
    evidence = copy.deepcopy(load_evidence())
    evidence["requirements"]["required_volumes"].pop()

    gate = module.build_gate(evidence)

    assert gate["official_fact_checks"]["seven_volume_structure_verified"] is False
    assert gate["deadline_conclusion"] == "VERIFIED_REAL_DEADLINE"
    assert gate["requirements_conclusion"] == module.UNKNOWN
    assert gate["posture"] == "BLOCKED_SOURCE_UNKNOWN_NOT_VERIFIED"


def test_checked_in_artifacts_are_deterministic_and_public_safe():
    module = load_module()
    gate = module.build_gate(load_evidence())
    serialized = json.dumps(gate, sort_keys=True)

    assert json.loads(JSON_OUT.read_text(encoding="utf-8")) == gate
    assert (
        MD_OUT.read_text(encoding="utf-8")
        == module.render_markdown(gate).rstrip() + "\n"
    )
    assert not re.search(r"(?i)\b[a-z]:[\\/]", serialized)
    assert not re.search(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", serialized, re.IGNORECASE
    )
    assert "proposal_body" not in serialized
    assert "patent" not in serialized.lower()
