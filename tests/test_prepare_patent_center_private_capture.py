from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py"
WORKFLOW = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md"
)
PRACTITIONER_TEMPLATE = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md"
)
MIRROR_RECEIPT = (
    ROOT
    / "grant_submissions"
    / "funding_sprint_20260709"
    / "PATENT_CENTER_PRIVATE_CAPTURE_E_DRIVE_SYNC_RECEIPT_2026-07-17.json"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "prepare_patent_center_private_capture", SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def private_paths(tmp_path: Path):
    root = tmp_path / "repo"
    private_base = root / "out" / "private"
    capture_root = private_base / "patent_center_capture"
    return root, private_base, capture_root


def initialize(module, tmp_path: Path):
    root, private_base, capture_root = private_paths(tmp_path)
    result = module.initialize_capture(
        capture_root,
        root=root,
        private_base=private_base,
        ignored_checker=lambda _path: True,
    )
    return root, private_base, capture_root, result


def test_initialize_creates_private_role_folders_and_empty_metadata(tmp_path: Path):
    module = load_module()
    root, private_base, capture_root, result = initialize(module, tmp_path)

    assert result["status"] == "PRIVATE_CAPTURE_DIRECTORIES_READY"
    assert result["required_role_directory_count"] == 6
    assert result["optional_role_directory_count"] == 3
    assert result["target_git_ignored"] is True
    assert result["private_values_returned_or_printed"] is False
    assert result["browser_navigation_performed"] is False
    assert result["legal_filing_performed"] is False
    assert all((capture_root / role).is_dir() for role in module.ALL_ROLES)
    metadata = json.loads((capture_root / module.METADATA_NAME).read_text(encoding="utf-8"))
    assert metadata == module.metadata_template()
    assert module.path_is_within(capture_root, private_base)
    assert module.path_is_within(capture_root, root)


def test_readiness_reports_role_counts_without_filenames_or_hashes(tmp_path: Path):
    module = load_module()
    root, private_base, capture_root, _ = initialize(module, tmp_path)
    private_filename = "application-99-999999-filing-receipt.pdf"
    (capture_root / "filing_receipt" / private_filename).write_bytes(b"filing receipt")

    readiness = module.inspect_capture(
        capture_root,
        root=root,
        private_base=private_base,
        ignored_checker=lambda _path: True,
    )
    rendered = json.dumps(readiness, sort_keys=True)

    assert readiness["status"] == "PRIVATE_CAPTURE_INCOMPLETE"
    assert readiness["captured_required_role_count"] == 1
    assert readiness["role_file_counts"]["filing_receipt"] == 1
    assert len(readiness["missing_required_roles"]) == 5
    assert readiness["source_filenames_returned_or_printed"] is False
    assert readiness["source_hashes_returned_or_printed"] is False
    assert readiness["private_metadata_values_read_or_printed"] is False
    assert private_filename not in rendered


def test_complete_private_capture_builds_redacted_public_control(tmp_path: Path):
    module = load_module()
    root, private_base, capture_root, _ = initialize(module, tmp_path)
    private_filenames = []
    for index, role in enumerate(module.REQUIRED_ROLES, start=1):
        filename = f"private-application-99-999999-{role}.pdf"
        private_filenames.append(filename)
        (capture_root / role / filename).write_bytes(
            f"official private {role} fixture {index}".encode("ascii")
        )
    metadata = module.metadata_template()
    metadata.update(
        {
            "application_number": "99/999,999",
            "application_type": "Utility nonprovisional fixture",
            "payment_received_date": "2030-01-02",
        }
    )
    (capture_root / module.METADATA_NAME).write_text(
        json.dumps(metadata), encoding="utf-8"
    )
    private_output = capture_root / "docket.private.json"
    public_json = root / "public" / "control.json"
    public_markdown = root / "public" / "control.md"

    receipt = module.build_capture(
        capture_root,
        root=root,
        private_base=private_base,
        private_output=private_output,
        public_json=public_json,
        public_markdown=public_markdown,
        ignored_checker=lambda _path: True,
    )

    private_payload = json.loads(private_output.read_text(encoding="utf-8"))
    public_payload = json.loads(public_json.read_text(encoding="utf-8"))
    public_text = public_json.read_text(encoding="utf-8") + public_markdown.read_text(
        encoding="utf-8"
    )
    receipt_text = json.dumps(receipt, sort_keys=True)
    assert receipt["status"] == "OFFICIAL_DOCKET_CAPTURED_PRACTITIONER_REVIEW_REQUIRED"
    assert receipt["captured_required_role_count"] == 6
    assert receipt["missing_required_roles"] == []
    assert receipt["private_docket_written"] is True
    assert receipt["private_metadata_values_returned_or_printed"] is False
    assert receipt["legal_filing_performed"] is False
    assert private_payload["application_number"] == "99/999,999"
    assert public_payload["public_evidence_summary"]["docket_capture_complete"] is True
    assert "99/999,999" not in public_text
    assert "2030-01-02" not in public_text
    assert "99/999,999" not in receipt_text
    for filename in private_filenames:
        assert filename not in public_text
        assert filename not in receipt_text
    for evidence in private_payload["evidence"]:
        assert evidence["source_sha256"] not in public_text
        assert evidence["source_sha256"] not in receipt_text


def test_complete_build_fails_closed_when_required_category_is_missing(tmp_path: Path):
    module = load_module()
    root, private_base, capture_root, _ = initialize(module, tmp_path)
    (capture_root / "filing_receipt" / "receipt.pdf").write_bytes(b"fixture")
    public_json = root / "public" / "control.json"

    with pytest.raises(module.CaptureError) as error:
        module.build_capture(
            capture_root,
            root=root,
            private_base=private_base,
            public_json=public_json,
            public_markdown=root / "public" / "control.md",
            ignored_checker=lambda _path: True,
        )

    assert error.value.code == "REQUIRED_DOCKET_CATEGORIES_MISSING"
    assert not public_json.exists()


def test_private_metadata_validation_rejects_unknown_or_malformed_values():
    module = load_module()
    payload = module.metadata_template()
    payload["unknown"] = "value"
    with pytest.raises(module.CaptureError) as unknown:
        module.validate_metadata(payload)

    payload = module.metadata_template()
    payload["payment_received_date"] = "01/02/2030"
    with pytest.raises(module.CaptureError) as date_error:
        module.validate_metadata(payload)

    payload = module.metadata_template()
    payload["payment_received_date"] = "2030-02-31"
    with pytest.raises(module.CaptureError) as impossible_date_error:
        module.validate_metadata(payload)

    payload = module.metadata_template()
    payload["application_number"] = "99/999,999\nleak"
    with pytest.raises(module.CaptureError) as newline_error:
        module.validate_metadata(payload)

    assert unknown.value.code == "PRIVATE_METADATA_KEYS_INVALID"
    assert date_error.value.code == "PRIVATE_METADATA_DATE_INVALID"
    assert impossible_date_error.value.code == "PRIVATE_METADATA_DATE_INVALID"
    assert newline_error.value.code == "PRIVATE_METADATA_VALUE_INVALID"


def test_empty_or_oversized_private_metadata_fails_closed(tmp_path: Path):
    module = load_module()
    _, _, capture_root, _ = initialize(module, tmp_path)
    metadata_path = capture_root / module.METADATA_NAME

    metadata_path.write_bytes(b"")
    with pytest.raises(module.CaptureError) as empty_error:
        module.read_private_metadata(capture_root)

    metadata_path.write_bytes(b"x" * (module.MAX_METADATA_BYTES + 1))
    with pytest.raises(module.CaptureError) as oversized_error:
        module.read_private_metadata(capture_root)

    assert empty_error.value.code == "PRIVATE_METADATA_SIZE_INVALID"
    assert oversized_error.value.code == "PRIVATE_METADATA_SIZE_INVALID"


def test_malformed_private_metadata_fails_with_safe_error_code(tmp_path: Path):
    module = load_module()
    _, _, capture_root, _ = initialize(module, tmp_path)
    (capture_root / module.METADATA_NAME).write_text("{not-json", encoding="utf-8")

    with pytest.raises(module.CaptureError) as error:
        module.read_private_metadata(capture_root)

    assert error.value.code == "PRIVATE_METADATA_JSON_INVALID"


def test_capture_root_must_remain_inside_ignored_private_boundary(tmp_path: Path):
    module = load_module()
    root, private_base, capture_root = private_paths(tmp_path)
    public_root = root / "grant_submissions" / "patent"

    with pytest.raises(module.CaptureError) as outside_private:
        module.validate_capture_root(
            public_root,
            root=root,
            private_base=private_base,
            ignored_checker=lambda _path: True,
        )
    with pytest.raises(module.CaptureError) as not_ignored:
        module.validate_capture_root(
            capture_root,
            root=root,
            private_base=private_base,
            ignored_checker=lambda _path: False,
        )

    assert outside_private.value.code == "CAPTURE_ROOT_OUTSIDE_PRIVATE_BOUNDARY"
    assert not_ignored.value.code == "CAPTURE_ROOT_NOT_GIT_IGNORED"


def test_workflow_and_held_practitioner_template_preserve_legal_boundary():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    template = PRACTITIONER_TEMPLATE.read_text(encoding="utf-8")
    lowered = template.lower()

    assert "July 25 date is not treated as a verified legal deadline" in workflow
    assert "fails closed until all six required categories" in workflow
    assert "does not file, pay, sign, submit, or navigate the browser" in workflow
    assert "secure intake channel" in template
    assert "will not send application identifiers" in lowered
    assert "not treating a payment acknowledgement or filing anniversary as deadline proof" in lowered
    assert "do not attach the private docket" in lowered
    assert "application_number" not in template


def test_public_capture_controls_have_private_safe_e_drive_receipt():
    receipt = json.loads(MIRROR_RECEIPT.read_text(encoding="utf-8"))

    assert receipt["schema"] == "lumencore.bounded_mirror_receipt.v1"
    assert receipt["artifact_count"] == len(receipt["artifacts"]) == 8
    assert receipt["all_sha256_matched_after_copy"] is True
    assert receipt["browser_navigation_performed"] is False
    assert receipt["private_patent_values_mirrored"] is False
    assert receipt["private_docket_files_mirrored"] is False
    destination = Path(receipt["destination_root"])
    mirrored_sources = {artifact["source"] for artifact in receipt["artifacts"]}
    assert mirrored_sources == {
        "code/ops/BUILD_PATENT_DEADLINE_EVIDENCE_CONTROL.py",
        "code/ops/PREPARE_PATENT_CENTER_PRIVATE_CAPTURE.py",
        "tests/test_patent_deadline_evidence_control.py",
        "tests/test_prepare_patent_center_private_capture.py",
        "grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.json",
        "grant_submissions/funding_sprint_20260709/PATENT_DEADLINE_EVIDENCE_CONTROL_2026-07-16.md",
        "grant_submissions/funding_sprint_20260709/PATENT_CENTER_PRIVATE_DOCKET_CAPTURE_WORKFLOW_2026-07-17.md",
        "grant_submissions/funding_sprint_20260709/PATENT_PRACTITIONER_DOCKET_REVIEW_REQUEST_TEMPLATE_2026-07-17.md",
    }
    for artifact in receipt["artifacts"]:
        normalized = artifact["source"].replace("\\", "/").lower()
        assert "/private/" not in f"/{normalized}/"
        assert ".private." not in normalized
        source = ROOT / artifact["source"]
        mirror = Path(artifact["destination"])
        assert source.is_file(), artifact["source"]
        assert mirror.is_file(), artifact["destination"]
        assert mirror.parent == destination
        assert source.stat().st_size == artifact["bytes"]
        assert mirror.stat().st_size == artifact["bytes"]
        assert hashlib.sha256(source.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert hashlib.sha256(mirror.read_bytes()).hexdigest().upper() == artifact["sha256"]
        assert artifact["copy_sha256_matched"] is True

    assert "does not prove" in receipt["claim_boundary"]
