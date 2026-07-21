from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "CAPTURE_MISSIONWEAVE_JCP_EVIDENCE.py"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "capture_missionweave_jcp_evidence", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_pdf(path: Path, marker: bytes = b"one") -> Path:
    path.write_bytes(b"%PDF-1.7\n" + marker + b"\n%%EOF\n")
    return path


def persist(module, tmp_path: Path, *, source: Path, replace: bool = False):
    private_dir = tmp_path / "private"
    receipt_path = private_dir / "MISSIONWEAVE_JCP_EVIDENCE_RECEIPT.private.json"
    return module.persist_private_bundle(
        evidence_source=source,
        evidence_kind="JCP_APPLICATION_SUBMISSION_RECEIPT",
        source_issued_utc="2026-07-21T18:00:00Z",
        captured_utc="2026-07-21T18:05:00Z",
        entity_match_confirmed=True,
        corporate_official_reviewed=True,
        private_dir=private_dir,
        receipt_path=receipt_path,
        replace_existing=replace,
        enforce_canonical_private_dir=False,
    )


def test_capture_copies_pdf_and_builds_exact_private_receipt(tmp_path):
    module = load_module()
    source = write_pdf(tmp_path / "official.pdf")
    result = persist(module, tmp_path, source=source)
    private_dir = tmp_path / "private"
    receipt_path = private_dir / "MISSIONWEAVE_JCP_EVIDENCE_RECEIPT.private.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    evidence = private_dir / receipt["evidence_file"]

    assert result["evidence_integrity_pass"] is True
    assert result["private_path_redacted"] is True
    assert result["private_hash_redacted"] is True
    assert receipt["schema"] == module.SCHEMA
    assert receipt["topic"] == module.TOPIC
    assert receipt["source_channel"] == "JCP_PORTAL"
    assert receipt["entity_match_confirmed"] is True
    assert receipt["corporate_official_reviewed"] is True
    assert evidence.read_bytes() == source.read_bytes()
    assert module.sha256_file(evidence) == receipt["evidence_file_sha256"]


def test_capture_requires_explicit_entity_and_corporate_review():
    module = load_module()
    with pytest.raises(module.JcpEvidenceCaptureError, match="ENTITY_MATCH"):
        module.build_receipt(
            evidence_kind="JCP_APPLICATION_SUBMISSION_RECEIPT",
            evidence_sha256="A" * 64,
            source_issued_utc="2026-07-21T18:00:00Z",
            captured_utc="2026-07-21T18:05:00Z",
            entity_match_confirmed=False,
            corporate_official_reviewed=True,
        )
    with pytest.raises(module.JcpEvidenceCaptureError, match="CORPORATE_REVIEW"):
        module.build_receipt(
            evidence_kind="JCP_APPLICATION_SUBMISSION_RECEIPT",
            evidence_sha256="A" * 64,
            source_issued_utc="2026-07-21T18:00:00Z",
            captured_utc="2026-07-21T18:05:00Z",
            entity_match_confirmed=True,
            corporate_official_reviewed=False,
        )


def test_capture_rejects_non_pdf_and_naive_timestamp(tmp_path):
    module = load_module()
    fake = tmp_path / "fake.pdf"
    fake.write_text("not a pdf", encoding="utf-8")
    with pytest.raises(module.JcpEvidenceCaptureError, match="NOT_PDF"):
        module.inspect_official_pdf(fake)
    with pytest.raises(module.JcpEvidenceCaptureError, match="INVALID_AWARE"):
        module.parse_utc("2026-07-21T18:00:00")


def test_capture_is_idempotent_but_requires_replace_for_different_evidence(tmp_path):
    module = load_module()
    source = write_pdf(tmp_path / "official.pdf", b"one")
    persist(module, tmp_path, source=source)
    persist(module, tmp_path, source=source)

    replacement = write_pdf(tmp_path / "replacement.pdf", b"two")
    with pytest.raises(module.JcpEvidenceCaptureError, match="ALREADY_EXISTS_DIFFERENT"):
        persist(module, tmp_path, source=replacement)
    result = persist(module, tmp_path, source=replacement, replace=True)
    assert result["evidence_integrity_pass"] is True


def test_capture_rejects_receipt_target_outside_private_directory(tmp_path):
    module = load_module()
    source = write_pdf(tmp_path / "official.pdf")
    with pytest.raises(module.JcpEvidenceCaptureError, match="OUTSIDE_PRIVATE_DIR"):
        module.persist_private_bundle(
            evidence_source=source,
            evidence_kind="JCP_APPLICATION_SUBMISSION_RECEIPT",
            source_issued_utc="2026-07-21T18:00:00Z",
            captured_utc="2026-07-21T18:05:00Z",
            entity_match_confirmed=True,
            corporate_official_reviewed=True,
            private_dir=tmp_path / "private",
            receipt_path=tmp_path / "outside.json",
            enforce_canonical_private_dir=False,
        )


def test_capture_rejects_symlinked_private_targets(tmp_path):
    module = load_module()
    source = write_pdf(tmp_path / "official.pdf")
    real_private_dir = tmp_path / "real_private"
    real_private_dir.mkdir()
    linked_private_dir = tmp_path / "linked_private"
    try:
        linked_private_dir.symlink_to(real_private_dir, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks are unavailable in this test environment")

    with pytest.raises(module.JcpEvidenceCaptureError, match="SYMLINK_REJECTED"):
        module.persist_private_bundle(
            evidence_source=source,
            evidence_kind="JCP_APPLICATION_SUBMISSION_RECEIPT",
            source_issued_utc="2026-07-21T18:00:00Z",
            captured_utc="2026-07-21T18:05:00Z",
            entity_match_confirmed=True,
            corporate_official_reviewed=True,
            private_dir=linked_private_dir,
            receipt_path=linked_private_dir / "receipt.json",
            enforce_canonical_private_dir=False,
        )
