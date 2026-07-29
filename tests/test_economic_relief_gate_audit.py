from __future__ import annotations

import importlib.util
import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_ECONOMIC_RELIEF_GATE_AUDIT.py"
CONFIG = ROOT / "config" / "economic_relief_gate_audit_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("economic_relief_gate_audit", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def gate_by_id(report: dict, gate_id: str) -> dict:
    for gate in report["gates"]:
        if gate["gate_id"] == gate_id:
            return gate
    raise AssertionError(f"missing gate: {gate_id}")


def copy_declared_sources(config: dict, destination: Path) -> None:
    for source in config["sources"].values():
        relative = Path(source["path"])
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)


def test_default_report_is_deterministic_complete_and_hash_valid():
    module = load_module()
    config = load_config()
    first = module.build_report(config)
    second = module.build_report(deepcopy(config))

    assert first == second
    assert module.verify_report_hash(first)
    assert first["report_state"] == "BLOCKERS_IDENTIFIED"
    assert first["summary"]["gate_count"] == 33
    assert first["summary"]["open_blocker_count"] == 26
    assert first["summary"]["closed_route_count"] == 2
    assert first["summary"]["unsupported_assumption_count"] == 3
    assert first["summary"]["cleared_gate_count"] == 2
    assert first["summary"]["evidence_mismatch_count"] == 0
    assert sum(first["summary"]["by_classification"].values()) == 33
    assert sum(first["summary"]["by_domain"].values()) == 33


def test_all_required_domains_and_remediation_classes_are_covered():
    module = load_module()
    report = module.build_report(load_config())

    assert tuple(report["required_domains"]) == module.REQUIRED_DOMAINS
    assert tuple(report["classifications"]) == module.CLASSIFICATIONS
    assert set(report["summary"]["by_domain"]) == set(module.REQUIRED_DOMAINS)
    assert set(report["summary"]["by_classification"]) == set(module.CLASSIFICATIONS)
    assert all(report["summary"]["by_domain"].values())
    assert all(report["summary"]["by_classification"].values())


def test_current_high_consequence_gates_remain_fail_closed():
    module = load_module()
    report = module.build_report(load_config())
    expected_states = {
        "sam.active_registration_action_time_currentness": "PARTIAL",
        "grants_gov.workspace_manager_aor_ebiz_authority": "OPEN",
        "research_gov.organization_registration_and_admin_role": "OPEN",
        "dsip.firm_pin_availability": "OPEN",
        "dsip.missionweave_release_deadline": "CLOSED_ROUTE",
        "jcp.application_submission_receipt": "OPEN",
        "jcp.dd2345_certification": "OPEN",
        "cmmc.authoritative_evidence_inventory": "OPEN",
        "export.itar_and_ear_classification": "OPEN",
        "founder.action_time_submission_authorization": "OPEN",
        "budget.nist_packet_exceeds_ceiling": "OPEN",
        "receipts.portfolio_submission_ledger_reconciliation": "CLEARED",
    }
    for gate_id, state in expected_states.items():
        gate = gate_by_id(report, gate_id)
        assert gate["effective_state"] == state
        if state == "CLEARED":
            assert gate["clearance_status"] == "CLEARED_BY_LOCAL_CONTROL"
        else:
            assert gate["clearance_status"] != "CLEARED_BY_AUTHORITATIVE_EVIDENCE"
        assert gate["evidence_status"] == "MATCHED_CONFIGURED_FINDING"


def test_private_source_paths_and_observed_values_are_not_emitted():
    module = load_module()
    report = module.build_report(load_config())
    serialized = json.dumps(report, sort_keys=True).lower()

    private_sources = [
        source for source in report["source_inventory"] if source["sensitivity"] == "PRIVATE"
    ]
    assert private_sources
    assert all(module.PRIVATE_REF_RE.fullmatch(item["source_ref"]) for item in private_sources)
    assert "grant_submissions/dla26bz03_nv011_missionweave/private/" not in serialized
    assert "\\users\\" not in serialized
    assert "@" not in serialized
    assert "observed_value" not in serialized
    assert '"password":' not in serialized
    assert '"token":' not in serialized


def test_source_drift_turns_affected_gate_into_evidence_mismatch(tmp_path):
    module = load_module()
    config = load_config()
    copy_declared_sources(config, tmp_path)
    action_path = (
        tmp_path
        / "grant_submissions"
        / "DLA26BZ03_NV011_MissionWeave"
        / "private"
        / "MISSIONWEAVE_DSIP_ACTION.private.json"
    )
    payload = json.loads(action_path.read_text(encoding="utf-8"))
    payload["identity"]["firm_pin_available_in_dsip"] = True
    action_path.write_text(json.dumps(payload), encoding="utf-8")

    report = module.build_report(config, root=tmp_path)
    gate = gate_by_id(report, "dsip.firm_pin_availability")
    assert gate["effective_state"] == "EVIDENCE_MISMATCH_FAIL_CLOSED"
    assert gate["evidence_status"] == "MISMATCH_FAIL_CLOSED"
    assert report["report_state"] == "EVIDENCE_MISMATCH_FAIL_CLOSED"
    assert report["summary"]["evidence_mismatch_count"] >= 1


def test_local_or_observed_source_cannot_be_configured_as_clearance():
    module = load_module()
    config = load_config()
    target = next(
        gate
        for gate in config["gates"]
        if gate["gate_id"] == "dsip.account_firm_and_organization_linkage"
    )
    target["state"] = "CLEARED"
    target["clearance_evidence_source_ids"] = ["missionweave_action_private"]

    with pytest.raises(module.AuditConfigError, match="cannot be cleared"):
        module.build_report(config)


def test_local_control_can_clear_only_a_locally_fixable_process_gate():
    module = load_module()
    config = load_config()
    process_gate = next(
        gate
        for gate in config["gates"]
        if gate["gate_id"] == "receipts.portfolio_submission_ledger_reconciliation"
    )
    assert process_gate["state"] == "CLEARED"
    report = module.build_report(config)
    cleared = gate_by_id(
        report, "receipts.portfolio_submission_ledger_reconciliation"
    )
    assert cleared["clearance_status"] == "CLEARED_BY_LOCAL_CONTROL"
    assert cleared["blocks_current_pursuit"] is False

    external_gate = next(
        gate
        for gate in config["gates"]
        if gate["gate_id"] == "dsip.account_firm_and_organization_linkage"
    )
    external_gate["state"] = "CLEARED"
    external_gate["clearance_evidence_source_ids"] = [
        "portfolio_external_action_ledger"
    ]
    with pytest.raises(module.AuditConfigError, match="cannot be cleared"):
        module.build_report(config)


def test_closed_and_unsupported_classifications_cannot_masquerade_as_open():
    module = load_module()
    config = load_config()
    closed = next(
        gate
        for gate in config["gates"]
        if gate["classification"] == "EXPIRED_OR_CLOSED_ROUTE"
    )
    closed["state"] = "OPEN"
    with pytest.raises(module.AuditConfigError, match="requires CLOSED_ROUTE"):
        module.build_report(config)

    config = load_config()
    unsupported = next(
        gate
        for gate in config["gates"]
        if gate["classification"] == "UNSUPPORTED_ASSUMPTION"
    )
    unsupported["state"] = "PARTIAL"
    with pytest.raises(module.AuditConfigError, match="require NOT_A_GATE"):
        module.build_report(config)


def test_source_escape_and_missing_domain_are_rejected():
    module = load_module()
    config = load_config()
    config["sources"]["grant_queue_index"]["path"] = "../queue.json"
    with pytest.raises(module.AuditConfigError):
        module.build_report(config)

    config = load_config()
    config["gates"] = [
        gate for gate in config["gates"] if gate["domain"] != "GRANTS_GOV"
    ]
    with pytest.raises(module.AuditConfigError, match="does not cover required domains"):
        module.build_report(config)


def test_json_and_markdown_outputs_are_deterministic_and_checkable(tmp_path):
    module = load_module()
    report = module.build_report(load_config())
    first_json = tmp_path / "first.json"
    first_md = tmp_path / "first.md"
    second_json = tmp_path / "second.json"
    second_md = tmp_path / "second.md"

    module.write_outputs(report, first_json, first_md)
    module.write_outputs(deepcopy(report), second_json, second_md)
    assert first_json.read_bytes() == second_json.read_bytes()
    assert first_md.read_bytes() == second_md.read_bytes()
    assert module.check_outputs(report, first_json, first_md) == []
    assert report["integrity"]["report_sha256"] in first_md.read_text(encoding="utf-8")
    markdown = first_md.read_text(encoding="utf-8")
    for classification in module.CLASSIFICATIONS:
        assert classification.replace("_", " ").title() in markdown

    first_md.write_text(markdown + "\nTAMPERED\n", encoding="utf-8")
    assert module.check_outputs(report, first_json, first_md) == [str(first_md)]


def test_report_hash_detects_tampering():
    module = load_module()
    report = module.build_report(load_config())
    assert module.verify_report_hash(report)
    report["summary"]["open_blocker_count"] -= 1
    assert not module.verify_report_hash(report)
