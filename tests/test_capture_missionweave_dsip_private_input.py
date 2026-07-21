from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "CAPTURE_MISSIONWEAVE_DSIP_PRIVATE_INPUT.py"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "MISSIONWEAVE_DSIP_PRIVATE_COLLECTOR_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
MIRROR_RECEIPT_COPY = Path(
    "E:/LumaProofVault/SUBMISSIONS/MISSIONWEAVE_DSIP_PRIVATE_COLLECTOR_20260717/"
    "grant_submissions/funding_sprint_20260709/"
    "MISSIONWEAVE_DSIP_PRIVATE_COLLECTOR_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
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
    "ITAR_SCOPE_CONFIRMED",
    "NO_DUPLICATE_COST_OR_DELIVERABLE",
    "PORTAL_PREVIEW_RECEIPT_HASH",
    "SAM_REPRESENTATIONS_CURRENT",
    "TECHNICAL_DATA_RIGHTS_ASSERTION",
    "TECHNOLOGY_CONTROL_PLAN_DECISION",
    "VOLUME3_COST_BASIS",
    "VOLUME5_UPLOAD_SET",
}


def load_module():
    spec = importlib.util.spec_from_file_location(
        "capture_missionweave_dsip_private_input", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def prompt_from(values: list[str]):
    remaining = list(values)
    messages: list[str] = []

    def prompt(message: str) -> str:
        messages.append(message)
        assert remaining, "collector requested an unexpected extra answer"
        return remaining.pop(0)

    prompt.remaining = remaining
    prompt.messages = messages
    return prompt


def synthetic_source_state() -> dict[str, str]:
    return {"volume2_sha256": "A" * 64}


def unresolved_evidence_kwargs(module) -> dict:
    return {
        "volume3_artifact_state": {"receipt_integrity_pass": False},
        "jcp_evidence_state": {"evidence_integrity_pass": False},
        "cmmc_packet_state": {
            "packet_present": True,
            "packet_regular_file": True,
            "schema_valid": True,
            "integrity_valid": True,
            "generated_timestamp_valid": True,
            "missionweave_program_unique": True,
            "cmmc_requirement_unique": True,
            "requirement_source_policy_valid": True,
            "packet_consumed": True,
            "packet_state": "EVIDENCE_INCOMPLETE",
            "requirement_evidence_state": "APPLICABILITY_UNRESOLVED",
            "requirements_review_basis_present": True,
            "phase_i_position_supported": False,
            "overclaim_boundary_present": True,
            "packet_binding_sha256": "C" * 64,
            "failure_code": None,
        },
    }


def authoritative_private_payload(module, proposal_number: str) -> dict:
    payload = module.load_template()
    payload["template_only"] = False
    payload["captured_utc"] = (REFERENCE_UTC - timedelta(minutes=5)).isoformat()
    for field in module.GATE.IDENTITY_GATES:
        payload["identity"][field] = True
    for field in module.GATE.PROPOSAL_FLAG_GATES:
        payload["proposal"][field] = True
    for field in module.GATE.COMPLIANCE_GATES:
        payload["eligibility_and_compliance"][field] = True

    payload["identity"]["firm_pin_available_in_dsip"] = False
    payload["identity"]["sam_representations_current"] = False
    payload["proposal"].update(
        {
            "proposal_number": proposal_number,
            "volume2_pdf_sha256": "A" * 64,
            "volume3_total_usd": "100000.00",
            "portal_preview_sha256": None,
            "portal_preview_captured_utc": None,
            "portal_preview_binding_sha256": None,
            "volume3_cost_basis_supported": False,
            "volume5_upload_set_reviewed": False,
            "portal_preview_reviewed": False,
        }
    )
    compliance = payload["eligibility_and_compliance"]
    for field in (
        "cmmc_phase_i_self_assessment_position_supported",
        "conflicts_and_joint_venture_status_reviewed",
        "current_cmmc_requirements_reviewed",
        "dd2345_or_jcp_application_evidence_ready",
        "technology_control_plan_decision_documented",
    ):
        compliance[field] = False
    compliance["itar_scope_determination"] = "SUBJECT_TO_ITAR"
    return payload


def keep_pre_submit_answers() -> list[str]:
    return [
        *(["k"] * 13),
        "",
        *(["k"] * 10),
        "",
        "",
        "",
        *(["k"] * 17),
        "k",
    ]


def test_pre_submit_preserves_authoritative_33_of_50_and_excludes_approval(
    tmp_path: Path,
):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"
    proposal_number = "DLA26BZ03-NV011-TEST0001"
    private_dir.mkdir(parents=True)
    target.write_text(
        json.dumps(authoritative_private_payload(module, proposal_number)),
        encoding="utf-8",
    )
    prompt = prompt_from(keep_pre_submit_answers())

    receipt = module.capture_private_sections(
        ["pre-submit"],
        prompt=prompt,
        target=target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
        source_state=synthetic_source_state(),
        volume2_text=f"{proposal_number}\nfinal assigned proposal header",
        reference_utc=REFERENCE_UTC,
        **unresolved_evidence_kwargs(module),
    )

    private = json.loads(target.read_text(encoding="utf-8"))
    public_receipt = json.dumps(receipt, sort_keys=True)
    assert prompt.remaining == []
    assert private["template_only"] is False
    assert private["proposal"]["proposal_number"] == proposal_number
    assert private["proposal"]["volume3_total_usd"] == "100000.00"
    assert private["eligibility_and_compliance"]["itar_scope_determination"] == (
        "SUBJECT_TO_ITAR"
    )
    assert private["approval"]["final_submission_authorized_at_action_time"] is False
    assert receipt["status"] == "PRIVATE_INPUT_SECTION_CAPTURED_GATES_OPEN"
    assert receipt["sections_updated"] == list(module.PRE_SUBMIT_SECTIONS)
    assert receipt["approval_section_explicitly_requested"] is False
    assert receipt["gate_summary"]["required_gate_count"] == 50
    assert receipt["gate_summary"]["passed_gate_count"] == 33
    assert receipt["gate_summary"]["open_gate_count"] == 17
    assert set(receipt["gate_summary"]["unresolved_gates"]) == (
        AUTHORITATIVE_OPEN_GATES
    )
    assert receipt["credential_values_requested"] is False
    assert receipt["firm_pin_value_requested"] is False
    assert receipt["browser_navigation_performed"] is False
    assert receipt["portal_submission_performed"] is False
    assert proposal_number not in public_receipt
    assert "A" * 64 not in public_receipt
    assert "B" * 64 not in public_receipt
    assert "100000.00" not in public_receipt


def test_explicit_approval_cannot_turn_authoritative_open_state_into_50_of_50(
    tmp_path: Path,
):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"
    proposal_number = "DLA26BZ03-NV011-TEST0002"
    source_state = synthetic_source_state()
    volume2_text = f"{proposal_number}\nfinal assigned proposal header"

    private_dir.mkdir(parents=True)
    target.write_text(
        json.dumps(authoritative_private_payload(module, proposal_number)),
        encoding="utf-8",
    )
    before = target.read_bytes()

    with pytest.raises(module.CaptureError) as error:
        module.capture_private_sections(
            ["approval"],
            prompt=prompt_from(["y", "y"]),
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
            source_state=source_state,
            volume2_text=volume2_text,
            reference_utc=REFERENCE_UTC,
            **unresolved_evidence_kwargs(module),
        )

    assert error.value.code == "APPROVAL_REQUIRES_FRESH_CURRENT_PREVIEW"
    assert target.read_bytes() == before


def test_fresh_preview_and_approval_bind_current_upload_then_upstream_change_clears_them(
    tmp_path: Path,
):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"
    proposal_number = "DLA26BZ03-NV011-TEST0003"
    source_state = synthetic_source_state()
    volume2_text = f"{proposal_number}\nfinal assigned proposal header"
    private_dir.mkdir(parents=True)
    target.write_text(
        json.dumps(authoritative_private_payload(module, proposal_number)),
        encoding="utf-8",
    )
    preview_file = tmp_path / "current-private-preview.txt"
    preview_file.write_text("current portal preview and upload set", encoding="utf-8")
    preview_timestamp = REFERENCE_UTC.timestamp()
    os.utime(preview_file, (preview_timestamp, preview_timestamp))
    proposal_answers = [
        "",
        "k",
        "k",
        "k",
        "k",
        "k",
        "k",
        "y",
        "k",
        "k",
        "y",
        "",
        "",
    ]

    preview_receipt = module.capture_private_sections(
        ["proposal"],
        prompt=prompt_from(proposal_answers),
        target=target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
        preview_receipt_file=preview_file,
        source_state=source_state,
        volume2_text=volume2_text,
        reference_utc=REFERENCE_UTC,
        **unresolved_evidence_kwargs(module),
    )
    approval_receipt = module.capture_private_sections(
        ["approval"],
        prompt=prompt_from(["y", "y"]),
        target=target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
        source_state=source_state,
        volume2_text=volume2_text,
        reference_utc=REFERENCE_UTC + timedelta(minutes=1),
        **unresolved_evidence_kwargs(module),
    )
    private = json.loads(target.read_text(encoding="utf-8"))

    assert preview_receipt["action_time_authorization_gate_passed"] is False
    assert approval_receipt["status"] == "PRIVATE_INPUT_SECTION_CAPTURED_GATES_OPEN"
    assert approval_receipt["action_time_authorization_gate_passed"] is True
    assert approval_receipt["gate_summary"]["passed_gate_count"] == 39
    assert approval_receipt["gate_summary"]["open_gate_count"] == 11
    assert "CMMC_PHASE_I_SELF_ASSESSMENT_POSITION" in approval_receipt[
        "gate_summary"
    ]["unresolved_gates"]
    assert module.GATE.valid_sha256(
        private["proposal"]["portal_preview_binding_sha256"]
    )
    assert module.GATE.valid_sha256(private["approval"]["approval_binding_sha256"])

    module.capture_private_sections(
        ["identity"],
        prompt=prompt_from(["n", *(["k"] * 12)]),
        target=target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
        source_state=source_state,
        volume2_text=volume2_text,
        reference_utc=REFERENCE_UTC + timedelta(minutes=2),
        **unresolved_evidence_kwargs(module),
    )
    invalidated = json.loads(target.read_text(encoding="utf-8"))
    assert invalidated["proposal"]["portal_preview_reviewed"] is False
    assert invalidated["proposal"]["portal_preview_captured_utc"] is None
    assert invalidated["proposal"]["portal_preview_binding_sha256"] is None
    assert invalidated["approval"]["corporate_official_reviewed_all_volumes"] is False
    assert invalidated["approval"]["final_submission_authorized_at_action_time"] is False
    assert invalidated["approval"]["approval_utc"] is None
    assert invalidated["approval"]["approval_binding_sha256"] is None


def test_template_placeholders_cannot_clear_legal_founder_or_portal_gates(
    tmp_path: Path,
):
    module = load_module()
    template = json.loads(module.TEMPLATE.read_text(encoding="utf-8"))
    template["captured_utc"] = REFERENCE_UTC.isoformat()
    for section_name in (
        "identity",
        "proposal",
        "eligibility_and_compliance",
        "approval",
    ):
        for field, value in template[section_name].items():
            if isinstance(value, bool):
                template[section_name][field] = True
    template["proposal"].update(
        {
            "proposal_number": "DLA26BZ03-NV011-PLACEHOLDER",
            "volume2_pdf_sha256": "A" * 64,
            "volume3_total_usd": "100000.00",
            "portal_preview_sha256": "B" * 64,
        }
    )
    template["eligibility_and_compliance"]["itar_scope_determination"] = (
        "SUBJECT_TO_ITAR"
    )
    template["approval"]["approval_utc"] = REFERENCE_UTC.isoformat()
    placeholder_path = tmp_path / "placeholder-template.json"
    placeholder_path.write_text(json.dumps(template), encoding="utf-8")

    clean = module.load_template(placeholder_path)

    assert clean["captured_utc"] is None
    assert all(value is False for value in clean["identity"].values())
    assert all(clean["proposal"][field] is False for field in module.GATE.PROPOSAL_FLAG_GATES)
    assert all(
        clean["proposal"][field] is None
        for field in module.GATE.PROPOSAL_VALUE_KEYS
        | module.GATE.PROPOSAL_CONSISTENCY_KEYS
    )
    assert all(
        clean["eligibility_and_compliance"][field] is False
        for field in module.GATE.COMPLIANCE_GATES
    )
    assert clean["eligibility_and_compliance"]["itar_scope_determination"] is None
    assert all(clean["approval"][field] is False for field in module.GATE.APPROVAL_FLAG_GATES)
    assert all(
        clean["approval"][field] is None
        for field in module.GATE.APPROVAL_VALUE_KEYS
        | module.GATE.APPROVAL_CONSISTENCY_KEYS
    )


def test_approval_cannot_authorize_before_all_volume_review(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"

    with pytest.raises(module.CaptureError) as error:
        module.capture_private_sections(
            ["approval"],
            prompt=prompt_from(["n", "y"]),
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
            source_state=synthetic_source_state(),
            volume2_text="neutral candidate",
            reference_utc=REFERENCE_UTC,
            **unresolved_evidence_kwargs(module),
        )

    assert error.value.code == "APPROVAL_REQUIRES_ALL_VOLUME_REVIEW"
    assert not target.exists()


def test_firm_pin_prompt_accepts_only_boolean_and_does_not_echo_value(capsys):
    module = load_module()
    attempted_pin = "123456789"
    answers = ["y", "y", "y", attempted_pin, "y", *(["y"] * 9)]
    prompt = prompt_from(answers)
    payload = module.load_template()
    payload["template_only"] = False

    module.collect_identity(payload, prompt=prompt)
    output = capsys.readouterr().out

    assert prompt.remaining == []
    assert payload["identity"]["firm_pin_available_in_dsip"] is True
    assert attempted_pin not in output
    firm_pin_prompts = [message for message in prompt.messages if "Firm PIN" in message]
    assert len(firm_pin_prompts) == 2
    assert all("[Y/N/K=keep]" in message for message in firm_pin_prompts)
    assert all("enter the pin" not in message.casefold() for message in firm_pin_prompts)


def test_credential_like_proposal_value_is_rejected_without_echo(capsys):
    module = load_module()
    marker = "password=DoNotStoreThis"
    prompt = prompt_from([marker, "DLA26BZ03-NV011-VALID"])

    value = module.choose_proposal_number(None, prompt=prompt)
    output = capsys.readouterr().out

    assert value == "DLA26BZ03-NV011-VALID"
    assert marker not in output
    assert "never a credential" in output


def test_schema_drift_or_public_target_fails_before_hidden_prompts(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    private_dir.mkdir(parents=True)
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"
    drift = module.load_template()
    drift["credential"] = "must never be accepted"
    target.write_text(json.dumps(drift), encoding="utf-8")

    def unexpected_prompt(_message: str) -> str:
        raise AssertionError("schema validation must happen before prompting")

    with pytest.raises(module.CaptureError) as drift_error:
        module.capture_private_sections(
            ["identity"],
            prompt=unexpected_prompt,
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
            source_state=synthetic_source_state(),
            volume2_text="neutral candidate",
            reference_utc=REFERENCE_UTC,
            **unresolved_evidence_kwargs(module),
        )

    with pytest.raises(module.CaptureError) as public_error:
        module.validate_private_target(
            root / "public" / "facts.json",
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
        )

    assert drift_error.value.code == "PRIVATE_TOP_LEVEL_SCHEMA_DRIFT"
    assert public_error.value.code == "TARGET_OUTSIDE_PRIVATE_DIRECTORY"

    malformed = module.load_template()
    malformed["proposal"]["proposal_number"] = {"credential": "not allowed"}
    with pytest.raises(module.CaptureError) as type_error:
        module.validate_payload_shape(malformed)
    assert type_error.value.code == "PROPOSAL_NUMBER_TYPE_INVALID"

    with pytest.raises(module.CaptureError) as section_error:
        module.normalize_sections(["all"])
    assert section_error.value.code == "UNKNOWN_CAPTURE_SECTION"


def test_existing_credential_like_value_fails_before_prompting(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    private_dir.mkdir(parents=True)
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"
    payload = module.load_template()
    payload["template_only"] = False
    payload["proposal"]["proposal_number"] = "password-not-a-proposal"
    target.write_text(json.dumps(payload), encoding="utf-8")

    def unexpected_prompt(_message: str) -> str:
        raise AssertionError("credential scan must happen before prompting")

    with pytest.raises(module.CaptureError) as error:
        module.capture_private_sections(
            ["identity"],
            prompt=unexpected_prompt,
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
            source_state=synthetic_source_state(),
            volume2_text="neutral candidate",
            reference_utc=REFERENCE_UTC,
            **unresolved_evidence_kwargs(module),
        )

    assert error.value.code == "CREDENTIAL_LIKE_VALUE_REJECTED"


def test_atomic_failure_leaves_no_partial_private_record(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"

    def fail_replace(_source, _destination):
        raise OSError("simulated replace failure")

    with pytest.raises(module.CaptureError) as error:
        module.capture_private_sections(
            ["identity"],
            prompt=prompt_from(["y"] * 13),
            target=target,
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
            replacer=fail_replace,
            source_state=synthetic_source_state(),
            volume2_text="neutral candidate",
        )

    assert error.value.code == "ATOMIC_PRIVATE_WRITE_FAILED"
    assert not target.exists()
    assert list(private_dir.glob(".missionweave-dsip-private-*.tmp")) == []


def test_target_check_does_not_read_existing_private_contents(tmp_path: Path):
    module = load_module()
    root = tmp_path / "repo"
    private_dir = root / "private"
    private_dir.mkdir(parents=True)
    target = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"
    marker = "not-json-private-marker"
    target.write_text(marker, encoding="utf-8")

    readiness = module.inspect_readiness(
        target,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
    )

    rendered = json.dumps(readiness, sort_keys=True)
    assert readiness["status"] == "READY_FOR_HIDDEN_SECTION_CAPTURE"
    assert readiness["output_exists"] is True
    assert readiness["private_file_contents_read"] is False
    assert readiness["pre_submit_excludes_action_time_approval"] is True
    assert readiness["credential_values_accepted"] is False
    assert readiness["firm_pin_value_accepted"] is False
    assert marker not in rendered


def test_preview_receipt_hashes_locally_without_returning_path(tmp_path: Path):
    module = load_module()
    receipt_file = tmp_path / "private-preview-receipt.txt"
    receipt_file.write_text("private portal preview", encoding="utf-8")

    digest = module.hash_receipt_file(receipt_file)

    assert module.GATE.valid_sha256(digest)
    assert str(receipt_file) not in digest


def test_preview_receipt_rejects_stale_file_and_manual_digest_has_no_binding(
    tmp_path: Path,
):
    module = load_module()
    receipt_file = tmp_path / "stale-private-preview.txt"
    receipt_file.write_text("stale portal preview", encoding="utf-8")
    stale_timestamp = (REFERENCE_UTC - timedelta(minutes=31)).timestamp()
    os.utime(receipt_file, (stale_timestamp, stale_timestamp))

    with pytest.raises(module.CaptureError) as stale_error:
        module.capture_preview_receipt(receipt_file, reference_utc=REFERENCE_UTC)
    assert stale_error.value.code == "PREVIEW_RECEIPT_NOT_FRESH"

    payload = authoritative_private_payload(
        module, "DLA26BZ03-NV011-MANUALHASH"
    )
    module.collect_proposal(
        payload,
        prompt=prompt_from(
            ["", *(["k"] * 10), "", "", "B" * 64]
        ),
        use_current_volume2_hash=False,
        preview_receipt_file=None,
        reference_utc=REFERENCE_UTC,
        **unresolved_evidence_kwargs(module),
    )

    assert payload["proposal"]["portal_preview_sha256"] == "B" * 64
    assert payload["proposal"]["portal_preview_captured_utc"] is None
    assert payload["proposal"]["portal_preview_binding_sha256"] is None


def test_current_volume2_hash_uses_only_guarded_private_final(
    tmp_path: Path, monkeypatch
) -> None:
    module = load_module()
    private_pdf = tmp_path / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.pdf"
    private_pdf.write_bytes(b"assigned-number-private-final")
    monkeypatch.setattr(module.GATE, "PRIVATE_FINAL_VOLUME2_PDF", private_pdf)
    monkeypatch.setattr(module.GATE, "validate_private_target", lambda path: path)

    digest = module.hash_private_final_volume2()

    assert digest == hashlib.sha256(private_pdf.read_bytes()).hexdigest().upper()

    private_pdf.unlink()
    with pytest.raises(module.CaptureError) as error:
        module.hash_private_final_volume2()
    assert error.value.code == "PRIVATE_FINAL_VOLUME2_NOT_FOUND"


def test_private_collector_snapshot_remains_immutable_on_e_drive() -> None:
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 19
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_founder_values_mirrored"] is False

    for artifact in receipt["artifacts"]:
        relative = Path(artifact["source"])
        destination = Path(artifact["destination"])
        assert relative.is_absolute() is False
        assert ".." not in relative.parts
        assert destination.is_file(), artifact["destination"]
        assert destination.stat().st_size == artifact["bytes"]
        destination_hash = hashlib.sha256(destination.read_bytes()).hexdigest().upper()
        assert destination_hash == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert MIRROR_RECEIPT_COPY.is_file()
    assert hashlib.sha256(MIRROR_RECEIPT.read_bytes()).hexdigest() == hashlib.sha256(
        MIRROR_RECEIPT_COPY.read_bytes()
    ).hexdigest()
    assert "does not prove" in receipt["claim_boundary"]
