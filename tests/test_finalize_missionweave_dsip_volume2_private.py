from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "FINALIZE_MISSIONWEAVE_DSIP_VOLUME2_PRIVATE.py"
TEMPLATE = ROOT / "config" / "missionweave_dsip_action_private_template_v1.json"
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)
MIRROR_RECEIPT_COPY = Path(
    "E:/LumaProofVault/SUBMISSIONS/MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_20260717/"
    "grant_submissions/funding_sprint_20260709/"
    "MISSIONWEAVE_DSIP_PRIVATE_FINALIZER_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "missionweave_dsip_private_volume2_finalizer", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def make_workspace(tmp_path: Path, module):
    root = tmp_path / "repo"
    package = (
        root / "grant_submissions" / "DLA26BZ03_NV011_MissionWeave"
    )
    private_dir = package / "private"
    private_dir.mkdir(parents=True)
    source = package / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_CANDIDATE.md"
    source.write_text("# Bounded MissionWeave source\n", encoding="utf-8")
    private_input = private_dir / "MISSIONWEAVE_DSIP_ACTION.private.json"

    payload = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    payload["template_only"] = False
    payload["captured_utc"] = "2026-07-17T09:00:00-05:00"
    proposal_number = "DLA26BZ03-NV011-TEST0001"
    payload["proposal"]["proposal_number"] = proposal_number
    private_input.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    outputs = (
        private_dir / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.docx",
        private_dir / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.pdf",
        private_dir / "MISSIONWEAVE_DSIP_VOLUME2_BUILD_METADATA.private.json",
        private_dir / "MISSIONWEAVE_DSIP_VOLUME2_FINAL_MANIFEST.private.json",
    )
    return root, private_dir, source, private_input, outputs, proposal_number


def safe_fake_builder(source: Path, output: Path, metadata: Path, number: str) -> None:
    output.write_bytes(b"private-docx")
    metadata.write_text(
        json.dumps(
            {
                "schema": "missionweave_dsip_volume2_build_metadata.v2",
                "source": source.name,
                "output": output.name,
                "proposal_number_header_state": "ASSIGNED_PRIVATE_VALUE",
                "proposal_number_value_exposed": False,
                "proposal_number_sha256": hashlib.sha256(
                    number.encode("utf-8")
                ).hexdigest().upper(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def safe_fake_converter(docx_path: Path, output_dir: Path) -> Path:
    output = output_dir / f"{docx_path.stem}.pdf"
    output.write_bytes(b"private-pdf")
    return output


def passing_inspector(_pdf: Path, _number: str) -> dict[str, object]:
    return {
        "pages": 11,
        "page_limit": 20,
        "letter_size": True,
        "encrypted": False,
        "searchable": True,
        "required_sections_present": True,
        "proposal_number_embedded": True,
        "neutral_header_absent": True,
        "all_checks_pass": True,
    }


def finalize(module, workspace, **overrides):
    root, private_dir, source, private_input, outputs, _ = workspace
    arguments = {
        "private_input_path": private_input,
        "source_md": source,
        "final_docx": outputs[0],
        "final_pdf": outputs[1],
        "final_metadata": outputs[2],
        "final_manifest": outputs[3],
        "root": root,
        "private_dir": private_dir,
        "ignored_checker": lambda _path: True,
        "document_builder": safe_fake_builder,
        "converter": safe_fake_converter,
        "inspector": passing_inspector,
    }
    arguments.update(overrides)
    return module.finalize_private_volume2(**arguments)


def test_private_finalizer_publishes_four_artifacts_and_redacted_receipt(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    *_, private_input, outputs, proposal_number = workspace

    receipt = finalize(module, workspace)
    serialized_receipt = json.dumps(receipt, sort_keys=True)
    updated = json.loads(private_input.read_text(encoding="utf-8"))
    manifest = json.loads(outputs[3].read_text(encoding="utf-8"))
    metadata = json.loads(outputs[2].read_text(encoding="utf-8"))

    assert all(path.is_file() for path in outputs)
    assert receipt["status"] == "PRIVATE_VOLUME2_REBUILT_AND_QA_PASSED"
    assert receipt["artifact_count"] == 4
    assert receipt["assigned_proposal_number_embedded"] is True
    assert receipt["proposal_number_value_exposed"] is False
    assert receipt["private_pdf_sha256_exposed"] is False
    assert proposal_number not in serialized_receipt
    assert updated["proposal"][
        "volume2_pdf_rebuilt_with_assigned_proposal_number"
    ] is True
    assert updated["proposal"]["volume2_pdf_sha256"] == module.sha256_file(
        outputs[1]
    )
    assert manifest["artifact_count"] == 3
    assert manifest["proposal_number_value_exposed"] is False
    assert proposal_number not in json.dumps(manifest, sort_keys=True)
    assert metadata["proposal_number_header_state"] == "ASSIGNED_PRIVATE_VALUE"
    assert proposal_number not in json.dumps(metadata, sort_keys=True)


def test_pdf_qa_failure_leaves_outputs_absent_and_private_input_unchanged(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    *_, private_input, outputs, _ = workspace
    original = private_input.read_bytes()

    with pytest.raises(module.FinalizationError) as exc:
        finalize(
            module,
            workspace,
            inspector=lambda _pdf, _number: {"all_checks_pass": False},
        )

    assert exc.value.code == "PRIVATE_FINAL_PDF_QA_FAILED"
    assert not any(path.exists() for path in outputs)
    assert private_input.read_bytes() == original


def test_existing_output_fails_before_private_input_is_read(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    *_, private_input, outputs, _ = workspace
    private_input.write_text("not-json", encoding="utf-8")
    outputs[0].write_bytes(b"existing")

    with pytest.raises(module.FinalizationError) as exc:
        finalize(module, workspace)

    assert exc.value.code == "PRIVATE_FINAL_OUTPUT_ALREADY_EXISTS"
    assert outputs[0].read_bytes() == b"existing"


def test_schema_drift_and_unbounded_targets_fail_closed(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    root, private_dir, _, private_input, outputs, _ = workspace
    drift = json.loads(private_input.read_text(encoding="utf-8"))
    drift["credential"] = "must-not-be-accepted"
    private_input.write_text(json.dumps(drift), encoding="utf-8")

    with pytest.raises(module.FinalizationError) as drift_error:
        finalize(module, workspace)
    assert drift_error.value.code == "PRIVATE_TOP_LEVEL_SCHEMA_DRIFT"
    assert not any(path.exists() for path in outputs)

    with pytest.raises(module.FinalizationError) as target_error:
        module.validate_private_artifact_target(
            root / "public" / "final.pdf",
            root=root,
            private_dir=private_dir,
            ignored_checker=lambda _path: True,
        )
    assert target_error.value.code == "PRIVATE_ARTIFACT_OUTSIDE_BOUNDED_DIRECTORY"


def test_bounded_source_cannot_be_read_from_private_directory(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    root, private_dir, _, _, _, _ = workspace
    private_source = private_dir / "private-source.md"
    private_source.write_text("private", encoding="utf-8")

    with pytest.raises(module.FinalizationError) as error:
        module.validate_bounded_source(
            private_source,
            root=root,
            private_dir=private_dir,
        )

    assert error.value.code == "BOUNDED_SOURCE_OUTSIDE_PACKAGE"


def test_builder_metadata_must_not_expose_assigned_number(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    *_, outputs, proposal_number = workspace

    def leaking_builder(source: Path, output: Path, metadata: Path, number: str):
        output.write_bytes(b"private-docx")
        metadata.write_text(
            json.dumps(
                {
                    "schema": "missionweave_dsip_volume2_build_metadata.v2",
                    "proposal_number_header_state": "ASSIGNED_PRIVATE_VALUE",
                    "proposal_number_value_exposed": False,
                    "leak": number,
                }
            ),
            encoding="utf-8",
        )

    with pytest.raises(module.FinalizationError) as exc:
        finalize(module, workspace, document_builder=leaking_builder)

    assert exc.value.code == "PRIVATE_BUILD_METADATA_EXPOSES_PROPOSAL_NUMBER"
    assert proposal_number not in json.dumps(
        {"receipt": exc.value.code}, sort_keys=True
    )
    assert not any(path.exists() for path in outputs)


def test_converter_output_must_stay_inside_private_staging_directory(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    outside = tmp_path / "outside.pdf"

    def outside_converter(_docx: Path, _output_dir: Path) -> Path:
        outside.write_bytes(b"unsafe-location")
        return outside

    with pytest.raises(module.FinalizationError) as exc:
        finalize(module, workspace, converter=outside_converter)

    assert exc.value.code == "PRIVATE_PDF_CONVERSION_OUTPUT_MISSING"


def test_readiness_is_metadata_only_and_uses_injected_private_targets(tmp_path):
    module = load_module()
    workspace = make_workspace(tmp_path, module)
    root, private_dir, _, private_input, outputs, proposal_number = workspace
    private_input.write_text(proposal_number, encoding="utf-8")

    readiness = module.inspect_readiness(
        private_input_path=private_input,
        root=root,
        private_dir=private_dir,
        ignored_checker=lambda _path: True,
        output_paths=outputs,
        soffice_finder=lambda: Path("C:/fake/soffice.exe"),
    )

    assert readiness["status"] == "READY_FOR_PRIVATE_VOLUME2_FINALIZATION"
    assert readiness["private_input_present"] is True
    assert readiness["private_input_contents_read"] is False
    assert readiness["existing_private_output_count"] == 0
    assert readiness["soffice_available"] is True
    assert proposal_number not in json.dumps(readiness, sort_keys=True)


def test_libreoffice_console_launcher_is_selected_synchronously(tmp_path):
    module = load_module()
    console = tmp_path / "soffice.com"
    gui = tmp_path / "soffice.exe"
    console.write_bytes(b"console-launcher")
    gui.write_bytes(b"gui-launcher")

    selected = module.find_soffice(
        candidates=[console, gui], which=lambda _command: None
    )

    assert selected == console.resolve()


def test_conversion_uses_short_external_libreoffice_profile(tmp_path, monkeypatch):
    module = load_module()
    output_dir = tmp_path / "deep" / "private-stage"
    output_dir.mkdir(parents=True)
    docx = output_dir / "MISSIONWEAVE_DSIP_VOLUME2_FINAL.private.docx"
    docx.write_bytes(b"docx")
    soffice = tmp_path / "soffice.com"
    soffice.write_bytes(b"launcher")
    short_profile = tmp_path / "short-profile"
    captured: dict[str, object] = {}

    def fake_mkdtemp(*, prefix: str):
        assert prefix == "lumencore-lo-"
        short_profile.mkdir()
        return str(short_profile)

    def fake_run(command, **_kwargs):
        captured["command"] = command
        (output_dir / f"{docx.stem}.pdf").write_bytes(b"pdf")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(module.tempfile, "mkdtemp", fake_mkdtemp)
    monkeypatch.setattr(module.subprocess, "run", fake_run)

    output = module.convert_docx_to_pdf(docx, output_dir, soffice_path=soffice)
    command = captured["command"]

    assert output.is_file()
    assert f"-env:UserInstallation={short_profile.resolve().as_uri()}" in command
    assert not (output_dir / ".libreoffice-profile").exists()
    assert not short_profile.exists()


def test_cli_builder_rejects_assigned_number_and_redacts_private_metadata(tmp_path):
    module = load_module()
    builder = module.CANDIDATE_BUILDER
    assigned_number = "DLA26BZ03-NV011-TEST0001"

    assert (
        builder.validate_cli_proposal_number(builder.NEUTRAL_PROPOSAL_HEADER)
        == builder.NEUTRAL_PROPOSAL_HEADER
    )
    with pytest.raises(ValueError, match="ASSIGNED_PROPOSAL_NUMBER_REQUIRES_PRIVATE_FINALIZER"):
        builder.validate_cli_proposal_number(assigned_number)

    output = tmp_path / "private.docx"
    metadata_path = tmp_path / "private.json"
    builder.build_document(module.SOURCE_MD, output, metadata_path, assigned_number)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    document = Document(output)
    header = " ".join(
        paragraph.text for paragraph in document.sections[0].header.paragraphs
    )

    assert assigned_number in header
    assert metadata["schema"] == "missionweave_dsip_volume2_build_metadata.v2"
    assert metadata["proposal_number_header_state"] == "ASSIGNED_PRIVATE_VALUE"
    assert metadata["proposal_number_value_exposed"] is False
    assert assigned_number not in json.dumps(metadata, sort_keys=True)


def test_private_finalizer_public_snapshot_is_immutable_on_e_drive() -> None:
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 37
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_input_mirrored"] is False
    assert receipt["private_assigned_number_artifacts_mirrored"] is False
    assert receipt["private_values_or_credentials_mirrored"] is False
    assert receipt["public_neutral_package_only"] is True

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
