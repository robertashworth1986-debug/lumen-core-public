from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_PRIVATE_ICLOUD_NOTE_INDEX.py"


def load_module():
    spec = importlib.util.spec_from_file_location("private_icloud_note_index", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_minimal_docx(path: Path, text: str) -> None:
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", xml)


def test_private_note_index_hashes_deduplicates_and_does_not_serialize_bodies(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "icloud"
    root.mkdir()
    body = "FAA aviation benchmark and patent claim notes"
    (root / "note-one.txt").write_text(body, encoding="utf-8")
    (root / "note-copy.md").write_text(body, encoding="utf-8")
    (root / "credential-note.txt").write_text("api_key must-not-be-serialized", encoding="utf-8")

    payload = module.build_payload(root)
    serialized = json.dumps(payload)

    assert payload["summary"]["record_count"] == 3
    assert payload["summary"]["unique_content_hashes"] == 2
    assert payload["summary"]["duplicate_file_count"] == 1
    assert payload["summary"]["duplicate_group_count"] == 1
    assert payload["summary"]["theoretical_duplicate_reclaimable_bytes"] == len(body.encode("utf-8"))
    assert payload["summary"]["locally_hashed_count"] == 3
    assert payload["summary"]["cloud_placeholder_count"] == 0
    assert payload["summary"]["sensitive_flagged_count"] == 1
    assert "aviation" in payload["summary"]["by_concept_tag"]
    assert "patent" in payload["summary"]["by_concept_tag"]
    assert "must-not-be-serialized" not in serialized
    assert all(row["public_release_allowed"] is False for row in payload["records"])
    duplicate = payload["duplicate_review"]["groups"][0]
    assert duplicate["copies"] == 2
    assert duplicate["automatic_deletion_allowed"] is False
    assert len(duplicate["review_only_paths"]) == 1


def test_shell_language_is_tagged_but_never_executed_or_serialized(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "icloud"
    root.mkdir()
    (root / "phone-script.txt").write_text(
        "PowerShell Invoke-WebRequest https://example.test",
        encoding="utf-8",
    )

    payload = module.build_payload(root)

    assert payload["records"][0]["concept_tags"] == ["code_or_shell"]
    assert "Invoke-WebRequest" not in json.dumps(payload)


def test_docx_text_is_classified_without_storing_the_text(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "icloud"
    root.mkdir()
    path = root / "research.docx"
    write_minimal_docx(path, "Independent validation and baseline benchmark")

    payload = module.build_payload(root)
    record = payload["records"][0]

    assert record["extraction"] == "docx_xml"
    assert record["word_count"] == 5
    assert record["concept_tags"] == ["benchmarking", "validation"]
    assert "Independent validation" not in json.dumps(payload)


def test_writer_creates_timestamped_latest_and_hashed_manifest(tmp_path: Path) -> None:
    module = load_module()
    root = tmp_path / "icloud"
    root.mkdir()
    (root / "note.txt").write_text("reproducible manifest", encoding="utf-8")
    payload = module.build_payload(root)

    paths = module.write_payload(payload, tmp_path / "vault")

    for path in paths.values():
        assert Path(path).exists()
    manifest = json.loads(Path(paths["manifest"]).read_text(encoding="utf-8"))
    assert manifest["schema"] == "lumencore.private_icloud_note_index_manifest.v1"
    assert len(manifest["files"]) == 3
    assert all(len(row["sha256"]) == 64 for row in manifest["files"])
    capsule = json.loads(Path(paths["context_capsule"]).read_text(encoding="utf-8"))
    assert capsule["schema"] == "lumencore.private_context_capsule.v1"
    assert capsule["concept_register"]["provenance"]["unique_content_count"] == 1
    assert "reproducible manifest" not in json.dumps(capsule)
