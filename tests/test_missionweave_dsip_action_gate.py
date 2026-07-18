from __future__ import annotations

import hashlib
import importlib.util
import json
from copy import deepcopy
from pathlib import Path

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


def load_module():
    spec = importlib.util.spec_from_file_location("missionweave_dsip_action_gate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def synthetic_private_payload(module, source_state: dict) -> tuple[dict, str]:
    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    payload["template_only"] = False
    payload["captured_utc"] = "2026-07-17T12:00:00-05:00"
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
        }
    )
    payload["eligibility_and_compliance"]["itar_scope_determination"] = (
        "SUBJECT_TO_ITAR"
    )
    payload["approval"]["approval_utc"] = "2026-07-17T12:05:00-05:00"
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
        "private_path_exposed": False,
        "private_hash_exposed": False,
    }


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


def test_complete_private_record_can_pass_without_exposing_private_values():
    module = load_module()
    source_state, _ = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    private, proposal_number = synthetic_private_payload(module, source_state)
    synthetic_volume2_text = f"{proposal_number}\nFinal assigned proposal header"

    payload = module.build_payload(
        private,
        private_input_sha256="B" * 64,
        source_state=source_state,
        volume2_text=synthetic_volume2_text,
        jcp_evidence_state=valid_jcp_evidence_state(module),
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
    facts = payload["private_fact_state"]
    assert facts["assigned_proposal_number_present"] is True
    assert facts["assigned_proposal_number_embedded_in_volume2"] is True
    assert facts["volume2_pdf_hash_matches_private_record"] is True
    assert facts["volume3_total_matches_official_ceiling"] is True
    assert facts["portal_preview_receipt_present"] is True
    assert facts["corporate_official_reviewed"] is True
    assert facts["action_time_authorized"] is True
    assert facts["approval_timestamp_present"] is True
    assert facts["dd2345_or_jcp_evidence_verified"] is True
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


def test_private_record_stays_open_when_pdf_header_or_action_gate_is_missing():
    module = load_module()
    source_state, actual_text = module.inspect_source_package()
    source_state = private_final_source_state(source_state)
    private, _ = synthetic_private_payload(module, source_state)
    private["approval"]["final_submission_authorized_at_action_time"] = False

    payload = module.build_payload(
        private,
        private_input_sha256="C" * 64,
        source_state=source_state,
        volume2_text=actual_text,
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
    private, proposal_number = synthetic_private_payload(module, private_state)
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
        jcp_evidence_state=valid_jcp_evidence_state(module),
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

    private, _ = synthetic_private_payload(module, source_state)
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
    workbook_bytes = b"synthetic-private-volume3-workbook"
    workbook.write_bytes(workbook_bytes)
    workbook_sha256 = hashlib.sha256(workbook_bytes).hexdigest().upper()
    receipt.write_text(
        json.dumps(
            {
                "schema": module.PRIVATE_VOLUME3_RECEIPT_SCHEMA,
                "topic": module.TOPIC,
                "file": workbook.name,
                "bytes": len(workbook_bytes),
                "sha256": workbook_sha256,
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
    monkeypatch.setattr(
        module, "validate_private_target", lambda path: Path(path).resolve()
    )

    state = module.inspect_private_volume3_artifact(receipt, workbook)
    serialized = json.dumps(state, sort_keys=True)

    assert state["receipt_integrity_pass"] is True
    assert state["workbook_hash_matches_receipt"] is True
    assert state["financial_reconciliation_pass"] is True
    assert state["review_guardrails_preserved"] is True
    assert state["private_path_exposed"] is False
    assert state["private_hash_exposed"] is False
    assert str(workbook) not in serialized
    assert workbook_sha256 not in serialized


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
    private, proposal_number = synthetic_private_payload(module, source_state)

    payload = module.build_payload(
        private,
        private_input_sha256="E" * 64,
        source_state=source_state,
        volume2_text=f"{proposal_number}\nassigned final header",
        jcp_evidence_state={"evidence_integrity_pass": False},
    )

    assert payload["submission_ready_for_human_click"] is False
    assert "DD2345_OR_JCP_APPLICATION_EVIDENCE" in payload["gate_summary"][
        "unresolved_gates"
    ]
    assert payload["private_fact_state"][
        "dd2345_or_jcp_evidence_verified"
    ] is False


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
    assert required == 50
    assert passed + open_count == required
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
    assert "## Reconciliation Groups" in markdown
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
    assert "READY_FOR_HUMAN_FINAL_SUBMIT_CLICK" in checklist
    assert "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section identity" in checklist
    assert "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py --section approval" in checklist
    assert "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py" in checklist
    assert "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py" in markdown
    assert "Private DD Form 2345/JCP Evidence Integrity" in markdown
    assert "A boolean answer cannot clear this gate" in markdown
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
    private, proposal_number = synthetic_private_payload(module, source_state)

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
