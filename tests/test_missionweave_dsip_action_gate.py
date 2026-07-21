from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_MISSIONWEAVE_DSIP_ACTION_GATE.py"
TEMPLATE = ROOT / "config" / "missionweave_dsip_action_private_template_v1.json"
JCP_PROTOCOL = (
    ROOT
    / "grant_submissions"
    / "DLA26BZ03_NV011_MissionWeave"
    / "MISSIONWEAVE_JCP_EVIDENCE_PROTOCOL_2026-07-18.json"
)
CMMC_PACKET = (
    ROOT
    / "grant_submissions"
    / "compliance_evidence"
    / "CMMC_EXPORT_EVIDENCE_PACKET_2026-07-18.json"
)
REFERENCE_UTC = datetime(2026, 7, 19, 3, 20, tzinfo=timezone.utc)
AUTHORITATIVE_OPEN_GATES = {
    "ACTION_TIME_APPROVAL_TIMESTAMP",
    "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
    "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
    "COMPLETE_PORTAL_PREVIEW_REVIEW",
    "CONFLICTS_AND_JOINT_VENTURE_STATUS",
    "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
    "CURRENT_CMMC_REQUIREMENTS_REVIEW",
    "DD2345_OR_JCP_APPLICATION_EVIDENCE",
    "DSIP_FIRM_PIN_AVAILABILITY",
    "NO_DUPLICATE_COST_OR_DELIVERABLE",
    "PORTAL_PREVIEW_RECEIPT_HASH",
    "TECHNICAL_DATA_RIGHTS_ASSERTION",
    "TECHNOLOGY_CONTROL_PLAN_DECISION",
    "VOLUME3_COST_BASIS",
    "VOLUME5_UPLOAD_SET",
}


def load_module():
    spec = importlib.util.spec_from_file_location("missionweave_dsip_action_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic_private_payload(
    module,
    source_state: dict,
    *,
    volume3_artifact_state: dict,
    jcp_evidence_state: dict,
    cmmc_packet_state: dict,
    documentary_register_state: dict,
) -> tuple[dict, str]:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    payload["template_only"] = False
    payload["captured_utc"] = (REFERENCE_UTC - timedelta(minutes=6)).isoformat()
    for field in module.IDENTITY_GATES:
        payload["identity"][field] = True
    for field in module.PROPOSAL_FLAG_GATES:
        payload["proposal"][field] = True
    for field in module.COMPLIANCE_GATES:
        payload["eligibility_and_compliance"][field] = True
    for field in module.APPROVAL_FLAG_GATES:
        payload["approval"][field] = True

    private_proposal_number = "DLA26BZ03-NV011-TEST0001"
    payload["proposal"].update(
        {
            "proposal_number": private_proposal_number,
            "volume2_pdf_sha256": source_state["volume2_sha256"],
            "volume3_total_usd": "100000.00",
            "portal_preview_sha256": "A" * 64,
            "portal_preview_captured_utc": (
                REFERENCE_UTC - timedelta(minutes=5)
            ).isoformat(),
        }
    )
    payload["eligibility_and_compliance"]["itar_scope_determination"] = (
        "SUBJECT_TO_ITAR"
    )
    payload["proposal"]["portal_preview_binding_sha256"] = (
        module.preview_evidence_binding_sha256(
            payload,
            volume3_artifact_state=volume3_artifact_state,
            jcp_evidence_state=jcp_evidence_state,
            cmmc_packet_state=cmmc_packet_state,
            documentary_register_state=documentary_register_state,
        )
    )
    payload["approval"]["approval_utc"] = (
        REFERENCE_UTC - timedelta(minutes=1)
    ).isoformat()
    payload["approval"]["approval_binding_sha256"] = (
        module.action_time_approval_binding_sha256(
            payload,
            approval_utc=payload["approval"]["approval_utc"],
            volume3_artifact_state=volume3_artifact_state,
            jcp_evidence_state=jcp_evidence_state,
            cmmc_packet_state=cmmc_packet_state,
            documentary_register_state=documentary_register_state,
        )
    )
    return payload, private_proposal_number


def private_final_source_state(source_state: dict) -> dict:
    private_state = deepcopy(source_state)
    private_state["volume2_path"] = "IGNORED_PRIVATE_FINAL_VOLUME2"
    private_state["volume2_sha256_present"] = True
    private_state["volume2_sha256_exposed"] = False
    private_state["private_final_volume2_used"] = True
    private_state["private_final_volume2_sha256_exposed"] = False
    private_state["absolute_private_path_exposed"] = False
    private_state["neutral_proposal_header_present"] = False
    return private_state


def valid_jcp_evidence_state(module) -> dict:
    return {
        "receipt_present": True,
        "receipt_header_valid": True,
        "evidence_file_present": True,
        "evidence_pdf": True,
        "evidence_hash_matches_receipt": True,
        "source_metadata_valid": True,
        "entity_match_confirmed": True,
        "corporate_official_reviewed": True,
        "evidence_integrity_pass": True,
        "evidence_kind": "JCP_APPLICATION_SUBMISSION_RECEIPT",
        "failure_code": None,
        "evidence_binding_sha256": "E" * 64,
        "private_path_exposed": False,
        "private_hash_exposed": False,
    }


def valid_volume3_artifact_state() -> dict:
    return {
        "receipt_present": True,
        "workbook_present": True,
        "receipt_header_valid": True,
        "workbook_size_matches_receipt": True,
        "workbook_hash_matches_receipt": True,
        "workbook_ooxml_valid": True,
        "workbook_structure_valid": True,
        "workbook_sheet_names_match_receipt": True,
        "workbook_formula_count": 3,
        "workbook_formula_error_count": 0,
        "workbook_error_cell_count": 0,
        "workbook_financials_derived_from_contents": True,
        "workbook_content_failure_code": None,
        "formula_scan_clean": True,
        "export_reimport_verified": True,
        "financial_reconciliation_pass": True,
        "review_guardrails_preserved": True,
        "receipt_integrity_pass": True,
        "artifact_binding_sha256": "D" * 64,
        "private_path_exposed": False,
        "private_hash_exposed": False,
    }


def valid_cmmc_packet_state(*, position_supported: bool = True) -> dict:
    return {
        "packet_present": True,
        "packet_regular_file": True,
        "schema_valid": True,
        "integrity_valid": True,
        "generated_timestamp_valid": True,
        "missionweave_program_unique": True,
        "cmmc_requirement_unique": True,
        "requirement_source_policy_valid": True,
        "packet_consumed": True,
        "packet_state": (
            "AUTHORITATIVE_EVIDENCE_INVENTORIED"
            if position_supported
            else "EVIDENCE_INCOMPLETE"
        ),
        "requirement_evidence_state": (
            "AUTHORITATIVE_PROOF_INVENTORIED"
            if position_supported
            else "APPLICABILITY_UNRESOLVED"
        ),
        "requirements_review_basis_present": True,
        "phase_i_position_supported": position_supported,
        "overclaim_boundary_present": True,
        "packet_binding_sha256": "C" * 64,
        "failure_code": None,
    }


def valid_documentary_register_state(module) -> dict:
    return {
        "register_present": True,
        "register_regular_file": True,
        "schema_valid": True,
        "topic_valid": True,
        "generated_timestamp_valid": True,
        "integrity_valid": True,
        "source_set_valid": True,
        "source_hashes_current": True,
        "gate_set_valid": True,
        "gate_rows_valid": True,
        "controls_valid": True,
        "claim_boundary_present": True,
        "register_consumed": True,
        "status": "DOCUMENTARY_PREREQUISITES_CLEAR",
        "gate_decisions": {
            gate_id: True
            for gate_id in sorted(module.CERTIFICATION_DOCUMENTARY_GATE_IDS)
        },
        "open_gate_ids": [],
        "register_binding_sha256": "D" * 64,
        "failure_code": None,
    }


def complete_evidence_states(module) -> tuple[dict, dict, dict, dict]:
    return (
        valid_volume3_artifact_state(),
        valid_jcp_evidence_state(module),
        valid_cmmc_packet_state(),
        valid_documentary_register_state(module),
    )


def write_volume3_workbook(
    path: Path,
    *,
    total_value: str = "100000",
    total_type: str = "n",
    workbook_content_type_as_default: bool = False,
) -> None:
    workbook_default = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"
        if workbook_content_type_as_default
        else "application/xml"
    )
    workbook_override = (
        ""
        if workbook_content_type_as_default
        else '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    )
    content_types = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="{workbook_default}"/>
  {workbook_override}
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""
    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""
    workbook = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Cost" sheetId="1" r:id="rId1"/>
    <sheet name="Spend Plan" sheetId="2" r:id="rId2"/>
  </sheets>
</workbook>"""
    workbook_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
</Relationships>"""
    cost_sheet = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="18">
      <c r="C18" t="inlineStr"><is><t>Total Hours / Average rate</t></is></c>
      <c r="D18"><f>SUM(D8:D17)</f><v>640</v></c>
    </row>
    <row r="58">
      <c r="C58" t="inlineStr"><is><t>Total Sub Contract Labor</t></is></c>
      <c r="F58"><f>SUM(F52:F56)</f><v>0</v></c>
    </row>
    <row r="84">
      <c r="B84" t="inlineStr"><is><t>Total Estimated Cost and Profit</t></is></c>
      <c r="F84" t="{total_type}"><f>SUM(F80:F83)</f><v>{total_value}</v></c>
    </row>
  </sheetData>
</worksheet>"""
    spend_sheet = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    <row r="1"><c r="B1"><f>'Cost'!$F$84</f><v>100000</v></c></row>
    <row r="2">
      <c r="B2" t="inlineStr"><is><t>Month 1</t></is></c>
      <c r="C2" t="inlineStr"><is><t>Month 2</t></is></c>
      <c r="D2" t="inlineStr"><is><t>Month 3</t></is></c>
      <c r="E2" t="inlineStr"><is><t>Month 4</t></is></c>
      <c r="F2" t="inlineStr"><is><t>Month 5</t></is></c>
      <c r="G2" t="inlineStr"><is><t>Month 6</t></is></c>
    </row>
    <row r="3">
      <c r="B3"><v>16667</v></c><c r="C3"><v>16667</v></c>
      <c r="D3"><v>16667</v></c><c r="E3"><v>16667</v></c>
      <c r="F3"><v>16667</v></c><c r="G3"><v>16665</v></c>
    </row>
    <row r="5">
      <c r="A5" t="inlineStr"><is><t>Cumulative Total</t></is></c>
      <c r="G5"><f>SUM($B$3:G3)</f><v>100000</v></c>
    </row>
  </sheetData>
</worksheet>"""
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", root_rels)
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", workbook_rels)
        archive.writestr("xl/worksheets/sheet1.xml", cost_sheet)
        archive.writestr("xl/worksheets/sheet2.xml", spend_sheet)


def write_volume3_receipt(module, receipt: Path, workbook: Path) -> str:
    workbook_bytes = workbook.read_bytes()
    workbook_sha256 = hashlib.sha256(workbook_bytes).hexdigest().upper()
    receipt.write_text(
        json.dumps(
            {
                "schema": module.PRIVATE_VOLUME3_RECEIPT_SCHEMA,
                "topic": module.TOPIC,
                "file": workbook.name,
                "bytes": len(workbook_bytes),
                "sha256": workbook_sha256,
                "sheets": ["Cost", "Spend Plan"],
                "total_usd": 100000,
                "firm_cost_usd": 100000,
                "subcontractor_cost_usd": 0,
                "taba_requested": False,
                "duration_months": 6,
                "pi_hours": 640,
                "formula_error_count": 0,
                "export_reimport_verified": True,
                "corporate_official_review_required": True,
                "cost_basis_supported": False,
            }
        ),
        encoding="utf-8",
    )
    return workbook_sha256


def test_default_gate_verifies_package_and_fails_closed_without_private_input():
    module = load_module()
    payload = module.build_payload()

    assert payload["schema"] == "lumencore.missionweave_dsip_action_gate.v1"
    assert payload["topic"] == "DLA26BZ03-NV011"
    assert payload["status"] == "PRIVATE_DSIP_FACTS_NOT_CAPTURED"
    assert payload["submission_ready_for_human_click"] is False
    source = payload["source_integrity"]
    assert source["manifest_header_pass"] is True
    assert source["manifest_file_count"] == 15
    assert source["all_manifest_files_match"] is True
    assert source["volume2_pages"] == 12
    assert source["volume2_page_limit"] == 20
    assert source["volume2_letter_size"] is True
    assert source["volume2_encrypted"] is False
    assert source["volume2_searchable"] is True
    assert source["volume2_required_sections_present"] is True
    assert source["neutral_proposal_header_present"] is True
    assert source["private_final_volume2_sha256_exposed"] is False
    assert source["all_checks_pass"] is True
    assert payload["gate_summary"]["required_private_gate_count"] == 50
    assert payload["gate_summary"]["passed_private_gate_count"] == 0
    assert payload["gate_summary"]["open_gate_count"] == 50
    groups = payload["gate_summary"]["reconciliation_groups"]
    assert sum(group["count"] for group in groups.values()) == 50
    assert groups["F_CLEARED_BY_EVIDENCE"]["count"] == 0
    lifecycle = payload["gate_lifecycle"]
    lifecycle_open = [
        gate
        for stage in lifecycle["stages"].values()
        for gate in stage["open_gates"]
    ]
    assert set(lifecycle_open) == set(payload["gate_summary"]["unresolved_gates"])
    assert len(lifecycle_open) == len(set(lifecycle_open))
    assert lifecycle["submission_readiness_logic_unchanged"] is True
    assert lifecycle["classification_can_clear_gate"] is False
    assert lifecycle["all_open_gates_classified_once"] is True
    assert lifecycle["classification_version"] == "missionweave.gate_lifecycle.v2"
    assert lifecycle["dependency_graph_acyclic"] is True
    assert lifecycle["dependency_stage_order_valid"] is True
    sequence = payload["founder_action_sequence"]
    sequenced_open = [
        gate
        for step in sequence["ordered_steps"]
        for gate in step["open_gates"]
    ]
    assert set(sequenced_open) == set(payload["gate_summary"]["unresolved_gates"])
    assert len(sequenced_open) == len(set(sequenced_open))
    assert sequence["classification_can_clear_gate"] is False
    assert sequence["final_submission_human_only"] is True
    assert payload["private_input"]["git_ignored_target"] is True
    assert payload["private_input"]["private_values_exposed"] is False
    assert payload["private_input"]["sha256"] is None
    assert payload["private_input"]["sha256_present"] is False
    assert payload["private_input"]["sha256_exposed"] is False
    assert payload["private_input"]["capture_tool"].endswith(
        "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py"
    )
    assert payload["private_input"]["capture_workflow"].endswith(
        "MISSIONWEAVE_DSIP_PRIVATE_CAPTURE_WORKFLOW_2026-07-17.md"
    )
    assert payload["private_input"]["private_volume2_finalizer"].endswith(
        "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py"
    )
    assert payload["private_input"]["private_final_volume2_path_exposed"] is False
    assert payload["private_input"]["private_final_volume2_sha256_exposed"] is False
    assert payload["private_input"]["pre_submit_excludes_action_time_approval"] is True
    assert payload["private_input"]["credential_values_accepted"] is False
    assert payload["private_input"]["firm_pin_value_accepted"] is False
    assert payload["private_jcp_evidence"]["receipt_present"] is False
    assert payload["private_jcp_evidence"]["evidence_integrity_pass"] is False
    assert payload["controls"]["bare_jcp_checkbox_can_clear_gate"] is False
    assert payload["jcp_evidence_protocol"]["bare_boolean_can_clear_gate"] is False
    assert len(payload["jcp_evidence_protocol"]["sha256"]) == 64
    assert payload["controls"]["browser_navigation_performed"] is False
    assert payload["controls"]["portal_submit_performed"] is False


def test_jcp_protocol_accepts_only_official_hash_matched_private_evidence():
    protocol = json.loads(JCP_PROTOCOL.read_text(encoding="utf-8"))

    assert protocol["schema"] == "lumencore.missionweave_jcp_evidence_protocol.v1"
    assert protocol["topic"] == "DLA26BZ03-NV011"
    assert set(protocol["accepted_private_evidence_kinds"]) == {
        "CERTIFIED_DD2345",
        "JCP_APPLICATION_SUBMISSION_RECEIPT",
    }
    assert protocol["controls"]["bare_boolean_can_clear_gate"] is False
    assert protocol["controls"]["evidence_file_sha256_match_required"] is True
    assert protocol["controls"]["builder_can_accept_prerequisites_in_progress"] is False
    assert "prerequisites-in-progress" in protocol["rejected_substitutes"]
    assert any(
        row.get("url") == "https://www.public.dacs.dla.mil/jcp/ext/"
        for row in protocol["official_sources"]
    )


def test_cmmc_packet_is_consumed_but_unresolved_position_stays_open(
    tmp_path: Path,
):
    module = load_module()
    packet_state = module.inspect_cmmc_evidence_packet(CMMC_PACKET)

    assert packet_state["packet_consumed"] is True
    assert packet_state["integrity_valid"] is True
    assert packet_state["requirement_evidence_state"] == "APPLICABILITY_UNRESOLVED"
    assert packet_state["phase_i_position_supported"] is False
    assert packet_state["overclaim_boundary_present"] is True

    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state = valid_volume3_artifact_state()
    jcp_state = valid_jcp_evidence_state(module)
    documentary_state = valid_documentary_register_state(module)
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=packet_state,
        documentary_register_state=documentary_state,
    )
    payload = module.build_payload(
        private,
        source_state=source_state,
        volume2_text=f"{proposal_number}\nassigned final header",
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=packet_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )

    assert payload["gate_summary"]["unresolved_gates"] == [
        "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION"
    ]
    assert payload["private_fact_state"]["cmmc_packet_consumed"] is True
    assert payload["private_fact_state"]["cmmc_phase_i_position_supported"] is False

    tampered_packet = json.loads(CMMC_PACKET.read_text(encoding="utf-8"))
    missionweave = next(
        row for row in tampered_packet["programs"] if row["program_id"] == "MissionWeave"
    )
    cmmc = next(
        row
        for row in missionweave["requirements"]
        if row["fact_id"] == module.CMMC_FACT_ID
    )
    cmmc["evidence_state"] = "AUTHORITATIVE_PROOF_INVENTORIED"
    cmmc["issues"] = []
    tampered_path = tmp_path / "tampered-cmmc-packet.json"
    tampered_path.write_text(json.dumps(tampered_packet), encoding="utf-8")

    rejected = module.inspect_cmmc_evidence_packet(tampered_path)
    assert rejected["integrity_valid"] is False
    assert rejected["packet_consumed"] is False
    assert rejected["phase_i_position_supported"] is False

    tampered_packet["integrity"]["packet_sha256"] = ""
    tampered_packet["integrity"]["packet_sha256"] = module.stable_sha256(
        tampered_packet
    )
    tampered_path.write_text(json.dumps(tampered_packet), encoding="utf-8")
    self_hashed_placeholder = module.inspect_cmmc_evidence_packet(tampered_path)
    assert self_hashed_placeholder["integrity_valid"] is True
    assert self_hashed_placeholder["packet_consumed"] is True
    assert self_hashed_placeholder["phase_i_position_supported"] is False


def test_current_certification_documentary_register_is_consumed_and_open():
    module = load_module()
    state = module.inspect_certification_documentary_register()

    assert state["register_consumed"] is True
    assert state["source_hashes_current"] is True
    assert state["gate_decisions"] == {
        "NO_DUPLICATE_COST_OR_DELIVERABLE": False,
        "TECHNICAL_DATA_RIGHTS_ASSERTION": False,
    }
    assert state["open_gate_ids"] == sorted(module.CERTIFICATION_DOCUMENTARY_GATE_IDS)
    assert module.certification_documentary_register_is_consumed(state) is True


def test_canonical_tracked_sha256_uses_committed_bytes_for_eol_only_drift(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    source = tmp_path / "source.md"
    source.write_bytes(b"alpha\r\nbeta\r\n")
    committed = b"alpha\nbeta\n"
    monkeypatch.setattr(module, "read_head_blob", lambda _path: committed)

    assert module.canonical_tracked_sha256(source) == hashlib.sha256(
        committed
    ).hexdigest().upper()


def test_private_booleans_cannot_clear_open_documentary_gates():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state = valid_volume3_artifact_state()
    jcp_state = valid_jcp_evidence_state(module)
    cmmc_state = valid_cmmc_packet_state()
    documentary_state = module.inspect_certification_documentary_register()
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )

    payload = module.build_payload(
        private,
        source_state=source_state,
        volume2_text=f"{proposal_number}\nassigned final header",
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )

    assert private["eligibility_and_compliance"][
        "no_duplicate_cost_or_deliverable"
    ] is True
    assert private["eligibility_and_compliance"][
        "technical_data_rights_assertion_supported"
    ] is True
    assert set(payload["gate_summary"]["unresolved_gates"]) == {
        "NO_DUPLICATE_COST_OR_DELIVERABLE",
        "TECHNICAL_DATA_RIGHTS_ASSERTION",
    }
    assert payload["private_fact_state"][
        "no_duplicate_cost_documentary_clear"
    ] is False
    assert payload["private_fact_state"][
        "technical_data_rights_documentary_clear"
    ] is False


def test_documentary_register_tampering_fails_closed(tmp_path: Path):
    module = load_module()
    register = json.loads(
        module.CERTIFICATION_DOCUMENTARY_REGISTER.read_text(encoding="utf-8")
    )

    wrong_source = deepcopy(register)
    wrong_source["source_artifacts"][0]["sha256"] = "0" * 64
    wrong_source["integrity"]["register_sha256"] = ""
    wrong_source["integrity"]["register_sha256"] = module.stable_sha256(wrong_source)
    wrong_source_path = tmp_path / "wrong-source.json"
    wrong_source_path.write_text(json.dumps(wrong_source), encoding="utf-8")
    wrong_source_state = module.inspect_certification_documentary_register(
        wrong_source_path
    )
    assert wrong_source_state["integrity_valid"] is True
    assert wrong_source_state["source_hashes_current"] is False
    assert wrong_source_state["register_consumed"] is False
    assert all(
        decision is False
        for decision in wrong_source_state["gate_decisions"].values()
    )

    wrong_self_hash = deepcopy(register)
    wrong_self_hash["claim_boundary"] += " tampered"
    wrong_self_hash_path = tmp_path / "wrong-self-hash.json"
    wrong_self_hash_path.write_text(json.dumps(wrong_self_hash), encoding="utf-8")
    wrong_self_hash_state = module.inspect_certification_documentary_register(
        wrong_self_hash_path
    )
    assert wrong_self_hash_state["integrity_valid"] is False
    assert wrong_self_hash_state["register_consumed"] is False


def test_complete_private_record_can_pass_without_exposing_private_values():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    synthetic_volume2_text = f"{proposal_number}\nFinal assigned proposal header"

    payload = module.build_payload(
        private,
        private_input_sha256="B" * 64,
        source_state=source_state,
        volume2_text=synthetic_volume2_text,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )
    serialized = json.dumps(payload, sort_keys=True)

    assert payload["status"] == "READY_FOR_HUMAN_FINAL_SUBMIT_CLICK"
    assert payload["submission_ready_for_human_click"] is True
    assert payload["gate_summary"]["required_private_gate_count"] == 50
    assert payload["gate_summary"]["passed_private_gate_count"] == 50
    assert payload["gate_summary"]["open_gate_count"] == 0
    assert payload["gate_summary"]["unresolved_gates"] == []
    groups = payload["gate_summary"]["reconciliation_groups"]
    assert sum(group["count"] for group in groups.values()) == 50
    assert groups["F_CLEARED_BY_EVIDENCE"] == {
        "status": "CLEARED",
        "count": 50,
        "gates": module.required_private_gates(),
    }
    assert all(
        stage["open_gate_count"] == 0
        for stage in payload["gate_lifecycle"]["stages"].values()
    )
    assert payload["founder_action_sequence"]["ordered_steps"] == []
    facts = payload["private_fact_state"]
    assert facts["assigned_proposal_number_present"] is True
    assert facts["assigned_proposal_number_embedded_in_volume2"] is True
    assert facts["volume2_pdf_hash_matches_private_record"] is True
    assert facts["volume3_total_matches_official_ceiling"] is True
    assert facts["portal_preview_receipt_present"] is True
    assert facts["portal_preview_binding_matches_current_upload_set"] is True
    assert facts["portal_preview_evidence_current"] is True
    assert facts["corporate_official_reviewed"] is True
    assert facts["action_time_authorized"] is True
    assert facts["approval_timestamp_present"] is True
    assert facts["dd2345_or_jcp_evidence_verified"] is True
    assert facts["cmmc_packet_consumed"] is True
    assert facts["cmmc_phase_i_position_supported"] is True
    assert proposal_number not in serialized
    assert "B" * 64 not in serialized
    assert "A" * 64 not in serialized
    assert "100000.00" not in serialized
    assert facts["assigned_proposal_number_value_exposed"] is False
    assert facts["portal_preview_receipt_value_exposed"] is False
    assert payload["controls"]["builder_can_click_final_submit"] is False
    public_source = payload["source_integrity"]
    assert public_source["volume2_path"] == "IGNORED_PRIVATE_FINAL_VOLUME2"
    assert public_source["volume2_sha256"] is None
    assert public_source["volume2_sha256_present"] is True
    assert public_source["volume2_sha256_exposed"] is False
    assert public_source["absolute_private_path_exposed"] is False
    assert source_state["volume2_sha256"] not in serialized


def test_stale_or_rebound_preview_cannot_reuse_action_time_approval():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    volume2_text = f"{proposal_number}\nassigned final header"

    stale = module.build_payload(
        private,
        source_state=source_state,
        volume2_text=volume2_text,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC + timedelta(minutes=26),
    )
    stale_open = set(stale["gate_summary"]["unresolved_gates"])
    assert {
        "PORTAL_PREVIEW_RECEIPT_HASH",
        "COMPLETE_PORTAL_PREVIEW_REVIEW",
        "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
        "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
        "ACTION_TIME_APPROVAL_TIMESTAMP",
    }.issubset(stale_open)
    assert stale["private_fact_state"]["portal_preview_receipt_fresh"] is False

    rebound = deepcopy(private)
    rebound["proposal"]["portal_preview_sha256"] = "F" * 64
    rebound["proposal"]["portal_preview_binding_sha256"] = (
        module.preview_evidence_binding_sha256(
            rebound,
            volume3_artifact_state=volume3_state,
            jcp_evidence_state=jcp_state,
            cmmc_packet_state=cmmc_state,
            documentary_register_state=documentary_state,
        )
    )
    rebound_payload = module.build_payload(
        rebound,
        source_state=source_state,
        volume2_text=volume2_text,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )
    rebound_facts = rebound_payload["private_fact_state"]
    rebound_open = set(rebound_payload["gate_summary"]["unresolved_gates"])
    assert rebound_facts["portal_preview_evidence_current"] is True
    assert rebound_facts["approval_binding_matches_current_upload_set"] is False
    assert {
        "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
        "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
        "ACTION_TIME_APPROVAL_TIMESTAMP",
    }.issubset(rebound_open)


def test_upload_set_change_invalidates_preview_and_approval_bindings():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    private["proposal"]["volume5_upload_set_reviewed"] = False

    payload = module.build_payload(
        private,
        source_state=source_state,
        volume2_text=f"{proposal_number}\nassigned final header",
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )
    facts = payload["private_fact_state"]
    unresolved = set(payload["gate_summary"]["unresolved_gates"])

    assert facts["portal_preview_receipt_fresh"] is True
    assert facts["portal_preview_binding_matches_current_upload_set"] is False
    assert facts["approval_binding_matches_current_upload_set"] is False
    assert {
        "VOLUME5_UPLOAD_SET",
        "PORTAL_PREVIEW_RECEIPT_HASH",
        "COMPLETE_PORTAL_PREVIEW_REVIEW",
        "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
        "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
        "ACTION_TIME_APPROVAL_TIMESTAMP",
    }.issubset(unresolved)


def test_documentary_register_change_invalidates_preview_and_approval_bindings():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    changed_documentary_state = deepcopy(documentary_state)
    changed_documentary_state["register_binding_sha256"] = "E" * 64

    payload = module.build_payload(
        private,
        source_state=source_state,
        volume2_text=f"{proposal_number}\nassigned final header",
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=changed_documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )
    facts = payload["private_fact_state"]
    unresolved = set(payload["gate_summary"]["unresolved_gates"])

    assert facts["portal_preview_binding_matches_current_upload_set"] is False
    assert facts["approval_binding_matches_current_upload_set"] is False
    assert {
        "PORTAL_PREVIEW_RECEIPT_HASH",
        "COMPLETE_PORTAL_PREVIEW_REVIEW",
        "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
        "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION",
        "ACTION_TIME_APPROVAL_TIMESTAMP",
    }.issubset(unresolved)


def test_private_record_stays_open_when_pdf_header_or_action_gate_is_missing():
    module = load_module()
    source_state, actual_text = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, _ = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    private["approval"]["final_submission_authorized_at_action_time"] = False

    payload = module.build_payload(
        private,
        private_input_sha256="C" * 64,
        source_state=source_state,
        volume2_text=actual_text,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )

    assert payload["status"] == "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    assert payload["submission_ready_for_human_click"] is False
    assert "VOLUME2_ASSIGNED_PROPOSAL_NUMBER_EMBEDDED" in payload["gate_summary"][
        "unresolved_gates"
    ]
    assert "ACTION_TIME_FINAL_SUBMISSION_AUTHORIZATION" in payload[
        "gate_summary"
    ]["unresolved_gates"]


def test_private_record_auto_selects_guarded_private_final_pdf(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    base_state, _ = module.inspect_source_package()
    private_state = private_final_source_state(base_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        private_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    private_pdf = tmp_path / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.pdf"
    private_pdf.write_bytes(b"private-final-marker")
    calls: list[tuple[Path, bool]] = []

    def fake_inspect(path: Path, *, private_final: bool = False):
        calls.append((path, private_final))
        return private_state, f"{proposal_number}\nassigned final header"

    monkeypatch.setattr(module, "PRIVATE_FINAL_VOLUME2_PDF", private_pdf)
    monkeypatch.setattr(module, "inspect_source_package", fake_inspect)

    payload = module.build_payload(
        private,
        private_input_sha256="D" * 64,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )

    assert calls == [(private_pdf, True)]
    assert payload["status"] == "READY_FOR_HUMAN_FINAL_SUBMIT_CLICK"
    assert payload["source_integrity"]["private_final_volume2_used"] is True
    assert payload["source_integrity"]["volume2_sha256"] is None
    assert payload["source_integrity"]["volume2_sha256_exposed"] is False


def test_template_and_schema_drift_fail_closed():
    module = load_module()
    source_state, text = module.inspect_source_package()
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.evaluate_private_payload(
            template, source_state=source_state, volume2_text=text
        )
    assert exc.value.code == "TEMPLATE_CANNOT_BE_USED_AS_PRIVATE_INPUT"

    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, _ = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )
    private["identity"]["unexpected_private_field"] = "must not be accepted"
    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.evaluate_private_payload(
            private, source_state=source_state, volume2_text=text
        )
    assert exc.value.code == "IDENTITY_SCHEMA_DRIFT"


def test_private_target_must_be_bounded_and_git_ignored(tmp_path):
    module = load_module()
    assert module.validate_private_target(module.DEFAULT_PRIVATE_INPUT) == (
        module.DEFAULT_PRIVATE_INPUT.resolve()
    )
    assert module.git_ignored(module.DEFAULT_PRIVATE_INPUT) is True

    outside = tmp_path / "missionweave.private.json"
    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.validate_private_target(outside)
    assert exc.value.code == "PRIVATE_INPUT_OUTSIDE_BOUNDED_DIRECTORY"


def test_private_volume3_receipt_verifies_workbook_without_exposing_path_or_hash(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    workbook = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
    receipt = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
    write_volume3_workbook(workbook)
    workbook_sha256 = write_volume3_receipt(module, receipt, workbook)
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)
    serialized = json.dumps(state, sort_keys=True)

    assert state["receipt_integrity_pass"] is True
    assert state["workbook_hash_matches_receipt"] is True
    assert state["workbook_ooxml_valid"] is True
    assert state["workbook_structure_valid"] is True
    assert state["workbook_sheet_names_match_receipt"] is True
    assert state["workbook_formula_count"] == 5
    assert state["workbook_formula_error_count"] == 0
    assert state["workbook_error_cell_count"] == 0
    assert state["workbook_financials_derived_from_contents"] is True
    assert state["workbook_content_failure_code"] is None
    assert state["financial_reconciliation_pass"] is True
    assert state["review_guardrails_preserved"] is True
    assert module.volume3_artifact_is_verified(state) is True
    assert module.valid_sha256(state["artifact_binding_sha256"])
    assert state["private_path_exposed"] is False
    assert state["private_hash_exposed"] is False
    assert str(workbook) not in serialized
    assert workbook_sha256 not in serialized


def test_private_volume3_accepts_workbook_content_type_default(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    workbook = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
    receipt = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
    write_volume3_workbook(workbook, workbook_content_type_as_default=True)
    write_volume3_receipt(module, receipt, workbook)
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)

    assert state["workbook_ooxml_valid"] is True
    assert state["workbook_structure_valid"] is True
    assert state["receipt_integrity_pass"] is True


def test_private_volume3_rejects_renamed_non_ooxml_bytes(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    workbook = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
    receipt = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
    workbook.write_bytes(b"not-an-ooxml-workbook")
    write_volume3_receipt(module, receipt, workbook)
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)

    assert state["workbook_hash_matches_receipt"] is True
    assert state["workbook_ooxml_valid"] is False
    assert state["formula_scan_clean"] is False
    assert state["financial_reconciliation_pass"] is False
    assert state["receipt_integrity_pass"] is False
    assert state["artifact_binding_sha256"] is None
    assert module.volume3_artifact_is_verified(state) is False


def test_private_volume3_rejects_duplicate_ooxml_members(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    workbook = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
    receipt = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
    write_volume3_workbook(workbook)
    with pytest.warns(UserWarning, match="Duplicate name"):
        with ZipFile(workbook, "a", compression=ZIP_DEFLATED) as archive:
            archive.writestr("xl/workbook.xml", "<duplicate/>")
    write_volume3_receipt(module, receipt, workbook)
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)

    assert state["workbook_content_failure_code"] == "OOXML_DUPLICATE_MEMBER"
    assert state["workbook_ooxml_valid"] is False
    assert state["receipt_integrity_pass"] is False


def test_private_volume3_receipt_cannot_override_workbook_formula_error(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    workbook = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
    receipt = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
    write_volume3_workbook(workbook, total_value="#VALUE!", total_type="e")
    write_volume3_receipt(module, receipt, workbook)
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)

    assert state["workbook_hash_matches_receipt"] is True
    assert state["workbook_formula_error_count"] == 1
    assert state["workbook_error_cell_count"] == 1
    assert state["formula_scan_clean"] is False
    assert state["financial_reconciliation_pass"] is False
    assert state["receipt_integrity_pass"] is False
    assert module.volume3_artifact_is_verified(state) is False


def test_private_volume3_receipt_cannot_override_workbook_financial_drift(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    workbook = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_COST_FINAL.xlsx"
    receipt = tmp_path / "MISSIONWEAVE_DSIP_VOLUME3_FINAL_RECEIPT.private.json"
    write_volume3_workbook(workbook, total_value="99999")
    write_volume3_receipt(module, receipt, workbook)
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)

    assert state["workbook_hash_matches_receipt"] is True
    assert state["workbook_ooxml_valid"] is False
    assert state["workbook_content_failure_code"] == "OOXML_FINANCIAL_CONTENT_INVALID"
    assert state["financial_reconciliation_pass"] is False
    assert state["receipt_integrity_pass"] is False
    assert module.volume3_artifact_is_verified(state) is False


def test_private_jcp_evidence_requires_hash_matched_portal_pdf(
    tmp_path: Path, monkeypatch
):
    module = load_module()
    evidence = tmp_path / "MISSIONWEAVE_JCP_APPLICATION_SUBMISSION_RECEIPT.private.pdf"
    receipt = tmp_path / "MISSIONWEAVE_JCP_EVIDENCE_RECEIPT.private.json"
    evidence_bytes = b"synthetic-official-jcp-portal-submission-receipt"
    evidence.write_bytes(evidence_bytes)
    evidence_sha256 = hashlib.sha256(evidence_bytes).hexdigest().upper()
    receipt.write_text(
        json.dumps(
            {
                "schema": module.PRIVATE_JCP_EVIDENCE_SCHEMA,
                "topic": module.TOPIC,
                "captured_utc": "2026-07-18T12:00:00-05:00",
                "evidence_kind": "JCP_APPLICATION_SUBMISSION_RECEIPT",
                "evidence_file": evidence.name,
                "evidence_file_sha256": evidence_sha256,
                "source_issued_utc": "2026-07-18T11:58:00-05:00",
                "source_channel": "JCP_PORTAL",
                "entity_match_confirmed": True,
                "corporate_official_reviewed": True,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_jcp_evidence(receipt)
    serialized = json.dumps(state, sort_keys=True)

    assert state["receipt_header_valid"] is True
    assert state["evidence_file_present"] is True
    assert state["evidence_hash_matches_receipt"] is True
    assert state["source_metadata_valid"] is True
    assert state["evidence_integrity_pass"] is True
    assert module.jcp_evidence_is_verified(state) is True
    assert module.valid_sha256(state["evidence_binding_sha256"])
    assert state["private_path_exposed"] is False
    assert state["private_hash_exposed"] is False
    assert str(evidence) not in serialized
    assert evidence_sha256 not in serialized

    receipt_payload = json.loads(receipt.read_text(encoding="utf-8"))
    receipt_payload["evidence_file_sha256"] = "0" * 64
    receipt.write_text(json.dumps(receipt_payload), encoding="utf-8")
    mismatched = module.inspect_private_jcp_evidence(receipt)
    assert mismatched["evidence_integrity_pass"] is False
    assert mismatched["evidence_hash_matches_receipt"] is False


def test_checked_jcp_flag_cannot_clear_gate_without_private_receipt():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )

    payload = module.build_payload(
        private,
        private_input_sha256="E" * 64,
        source_state=source_state,
        volume2_text=f"{proposal_number}\nassigned final header",
        volume3_artifact_state=volume3_state,
        jcp_evidence_state={"evidence_integrity_pass": False},
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
        evaluated_utc=REFERENCE_UTC,
    )

    assert payload["submission_ready_for_human_click"] is False
    assert "DD2345_OR_JCP_APPLICATION_EVIDENCE" in payload["gate_summary"][
        "unresolved_gates"
    ]
    assert payload["private_fact_state"][
        "dd2345_or_jcp_evidence_verified"
    ] is False


def test_lifecycle_fails_closed_if_final_no_duplicate_decision_is_moved_before_preview(
    monkeypatch,
):
    module = load_module()
    monkeypatch.setattr(
        module,
        "LIFECYCLE_ACTION_TIME_GATES",
        frozenset(
            set(module.LIFECYCLE_ACTION_TIME_GATES).difference(
                {"NO_DUPLICATE_COST_OR_DELIVERABLE"}
            )
        ),
    )

    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.gate_lifecycle_stages(module.required_private_gates())

    assert exc.value.code == "GATE_LIFECYCLE_DEPENDENCY_ORDER_INVALID"


def test_written_public_outputs_and_checklist_are_current_and_safe():
    module = load_module()
    payload = json.loads(module.OUT_JSON.read_text(encoding="utf-8"))
    markdown = module.OUT_MD.read_text(encoding="utf-8")
    checklist = module.OUT_CHECKLIST.read_text(encoding="utf-8")
    combined = markdown + checklist + json.dumps(payload, sort_keys=True)

    assert payload["status"] == "PRIVATE_DSIP_FACTS_CAPTURED_GATES_OPEN"
    summary = payload["gate_summary"]
    passed = summary["passed_private_gate_count"]
    open_count = summary["open_gate_count"]
    required = summary["required_private_gate_count"]
    assert (passed, open_count, required) == (35, 15, 50)
    assert set(summary["unresolved_gates"]) == AUTHORITATIVE_OPEN_GATES
    groups = summary["reconciliation_groups"]
    assert sum(group["count"] for group in groups.values()) == required
    assert (
        sum(
            group["count"]
            for key, group in groups.items()
            if key != "F_CLEARED_BY_EVIDENCE"
        )
        == open_count
    )
    assert groups["F_CLEARED_BY_EVIDENCE"]["count"] == passed
    lifecycle = payload["gate_lifecycle"]
    lifecycle_open = [
        gate
        for stage in lifecycle["stages"].values()
        for gate in stage["open_gates"]
    ]
    assert set(lifecycle_open) == AUTHORITATIVE_OPEN_GATES
    assert len(lifecycle_open) == len(set(lifecycle_open))
    assert lifecycle["classification_can_clear_gate"] is False
    assert lifecycle["submission_readiness_logic_unchanged"] is True
    assert lifecycle["classification_version"] == "missionweave.gate_lifecycle.v2"
    assert lifecycle["dependency_graph_acyclic"] is True
    assert lifecycle["dependency_stage_order_valid"] is True
    no_duplicate_dependency = lifecycle["dependencies"][
        "NO_DUPLICATE_COST_OR_DELIVERABLE"
    ]
    assert no_duplicate_dependency["gate_stage"] == (
        "C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN"
    )
    assert set(no_duplicate_dependency["required_gates"]) == {
        "COMPLETE_PORTAL_PREVIEW_REVIEW",
        "CORPORATE_OFFICIAL_ALL_VOLUME_REVIEW",
    }
    assert "NO_DUPLICATE_COST_OR_DELIVERABLE" not in lifecycle["stages"][
        "A_PRE_SUBMISSION_CONTENT_AND_EVIDENCE"
    ]["open_gates"]
    assert "NO_DUPLICATE_COST_OR_DELIVERABLE" in lifecycle["stages"][
        "C_FINAL_PREVIEW_AND_ACTION_TIME_HUMAN"
    ]["open_gates"]
    negotiation = lifecycle["stages"][
        "B_PRE_AWARD_OR_CONTRACT_NEGOTIATION_READINESS"
    ]
    assert set(negotiation["open_gates"]) == {
        "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION",
        "TECHNOLOGY_CONTROL_PLAN_DECISION",
    }
    sequence = payload["founder_action_sequence"]
    sequenced_open = [
        gate
        for step in sequence["ordered_steps"]
        for gate in step["open_gates"]
    ]
    assert set(sequenced_open) == AUTHORITATIVE_OPEN_GATES
    assert len(sequenced_open) == len(set(sequenced_open))
    assert [step["step_id"] for step in sequence["ordered_steps"]] == [
        "01_JCP_APPLICATION_EVIDENCE",
        "02_DSIP_FIRM_PIN_CONFIRMATION",
        "03_VOLUME3_COST_SUPPORT",
        "04_COMPLIANCE_AND_CONFLICT_POSITION",
        "05_VOLUME5_UPLOAD_SET",
        "06_FRESH_PORTAL_PREVIEW",
        "07_ACTION_TIME_REVIEW_AND_AUTHORIZATION",
    ]
    step_by_id = {step["step_id"]: step for step in sequence["ordered_steps"]}
    assert "NO_DUPLICATE_COST_OR_DELIVERABLE" not in step_by_id[
        "04_COMPLIANCE_AND_CONFLICT_POSITION"
    ]["open_gates"]
    assert "NO_DUPLICATE_COST_OR_DELIVERABLE" in step_by_id[
        "07_ACTION_TIME_REVIEW_AND_AUTHORIZATION"
    ]["open_gates"]
    assert "## Reconciliation Groups" in markdown
    assert "## Lifecycle Boundaries" in markdown
    assert "## Founder Action Sequence" in markdown
    assert "## Exact Founder Order Of Operations" in checklist
    assert "covers every currently open gate exactly once" in checklist
    assert "cannot clear a gate or change submission readiness" in markdown
    assert payload["submission_ready_for_human_click"] is False
    assert payload["private_input"]["private_values_exposed"] is False
    assert payload["source_integrity"]["all_checks_pass"] is True
    assert "Seven Volumes" in checklist
    for volume in range(1, 8):
        assert f"Volume {volume}" in checklist
    assert "July 22, 2025" in checklist
    assert "July 22, 2026" in checklist
    assert "July 22, 2026 at 11:00 a.m. Central Time" in checklist
    assert "July 21 at 3:00 p.m. Central" in checklist
    assert "every volume must be completed and endorsed before close" in checklist
    assert "Volume 2 candidate: `12` pages of `20` allowed" in checklist
    assert "Foreign Risk Evaluation (FRE)" in checklist
    assert "Do not upload a foreign-affiliations PDF in Volume 5" in checklist
    assert "CMMC Phase II implementation was suspended" in checklist
    assert "Phase I self-assessment requirements remain" in checklist
    assert "during contracting negotiation" in checklist
    assert "does not establish a current proposal-upload requirement" in checklist
    assert (
        "during contracting negotiation"
        in payload["official_instruction_facts"][
            "technology_control_plan_lifecycle_note"
        ]
    )
    assert "READY_FOR_HUMAN_FINAL_SUBMIT_CLICK" in checklist
    assert "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section identity" in checklist
    assert "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section approval" in checklist
    assert "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py" in checklist
    assert "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py" in markdown
    assert "Private DD Form 2345/JCP Evidence Integrity" in markdown
    assert "## Certification Documentary Register" in markdown
    assert "A boolean answer cannot clear this gate" in markdown
    assert "a private checkbox alone cannot clear" in combined
    assert "https://www.public.dacs.dla.mil/jcp/ext/" in checklist
    assert "prerequisites-in-progress" in checklist
    assert payload["private_input"]["private_final_volume2_path_exposed"] is False
    assert payload["private_input"]["private_final_volume2_sha256_exposed"] is False
    assert "--section pre-submit" in markdown
    assert "never requests or accepts a Firm PIN or login credential" in markdown
    assert "robertashworth4444" not in combined.lower()
    assert "615-438-2502" not in combined
    assert module.PRIVATE_VALUE_MARKERS[0] not in combined.lower()
    assert len(payload["gate_sha256"]) == 64


def test_public_safety_rejects_injected_private_contact_or_proposal_number():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    volume3_state, jcp_state, cmmc_state, documentary_state = (
        complete_evidence_states(module)
    )
    private, proposal_number = synthetic_private_payload(
        module,
        source_state,
        volume3_artifact_state=volume3_state,
        jcp_evidence_state=jcp_state,
        cmmc_packet_state=cmmc_state,
        documentary_register_state=documentary_state,
    )

    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.ensure_public_safe({"unsafe": proposal_number}, private)
    assert exc.value.code == "PRIVATE_PROPOSAL_NUMBER_EXPOSED"

    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.ensure_public_safe(
            {"unsafe": private["proposal"]["volume2_pdf_sha256"]}, private
        )
    assert exc.value.code == "PRIVATE_VOLUME2_PDF_SHA256_EXPOSED"

    with pytest.raises(module.MissionWeaveGateError) as exc:
        module.ensure_public_safe({"unsafe": "person@example.com"})
    assert exc.value.code == "PUBLIC_EMAIL_EXPOSED"
