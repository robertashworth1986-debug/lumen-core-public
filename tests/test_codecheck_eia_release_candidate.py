from __future__ import annotations

import importlib.util
import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "BUILD_CODECHECK_EIA_RELEASE_CANDIDATE.py"
CONFIG = ROOT / "config" / "codecheck_eia_release_candidate_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("codecheck_release_candidate", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_release_definition_is_complete_public_and_fail_closed():
    module = load_module()
    definition = module.inspect_release_candidate()

    assert definition["internal_release_candidate_ready"] is True
    assert definition["publication_ready"] is False
    assert all(definition["checks"].values())
    assert definition["bundle_input_count"] >= 30
    assert definition["privacy_scan"]["passed"] is True
    assert definition["publication_state"]["stable_public_identifier"] is None
    assert definition["publication_state"]["github_release_published"] is False
    assert definition["publication_state"]["zenodo_doi_issued"] is False
    assert definition["publication_state"]["codecheck_request_opened"] is False
    assert definition["publication_state"]["external_validation_complete"] is False


def test_release_assets_are_byte_deterministic_and_self_reconciling(tmp_path):
    module = load_module()
    source_commit = "1" * 40
    source_time = "2026-07-21T12:34:56+00:00"
    first = tmp_path / "first"
    second = tmp_path / "second"

    receipt_a = module.build_release_candidate(
        first,
        source_commit=source_commit,
        source_commit_time=source_time,
    )
    receipt_b = module.build_release_candidate(
        second,
        source_commit=source_commit,
        source_commit_time=source_time,
    )

    for name in (
        "LumenCore_CODECHECK_EIA_Source_Bundle_v0.1.0.zip",
        "LumenCore_CODECHECK_EIA_Preprint_v0.1.0.pdf",
        "LumenCore_CODECHECK_EIA_RELEASE_NOTES_v0.1.0.md",
        "LumenCore_CODECHECK_EIA_RELEASE_RECEIPT_v0.1.0.json",
        "SHA256SUMS",
    ):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name

    assert receipt_a["bundle_asset"]["sha256"] == receipt_b["bundle_asset"]["sha256"]
    assert json.loads(
        (first / "LumenCore_CODECHECK_EIA_RELEASE_RECEIPT_v0.1.0.json").read_text(
            encoding="utf-8"
        )
    ) == receipt_a
    assert receipt_a["bundle_verification"]["verified"] is True
    assert receipt_a["publication_ready"] is False
    assert receipt_a["external_validation_complete"] is False
    assert all(
        value is False or value is None
        for value in receipt_a["publication_state"].values()
    )


def test_bundle_has_fixed_metadata_exact_inputs_and_no_duplicate_names(tmp_path):
    module = load_module()
    definition = module.inspect_release_candidate()
    receipt = module.build_release_candidate(
        tmp_path,
        source_commit="2" * 40,
        source_commit_time="2026-07-21T00:00:00Z",
    )
    bundle = tmp_path / receipt["bundle_asset"]["name"]

    with zipfile.ZipFile(bundle, "r") as archive:
        names = archive.namelist()
        assert len(names) == len(set(names))
        assert all(row.date_time == (1980, 1, 1, 0, 0, 0) for row in archive.infolist())
        root = definition["release"]["archive_root"]
        assert (
            f"{root}/code/ops/VERIFY_CODECHECK_REVIEWER_RUNTIME.py" in names
        )
        assert f"{root}/config/codecheck_reviewer_runtime_v1.json" in names
        assert (
            f"{root}/evidence/reproducibility/"
            "codecheck_reviewer_runtime_receipt_d60ae723_20260721.json"
            in names
        )
        manifest = json.loads(archive.read(f"{root}/RELEASE_MANIFEST.json"))
        assert manifest["source_commit"] == "2" * 40
        assert manifest["bundle_input_chain_sha256"] == definition[
            "bundle_input_chain_sha256"
        ]
        assert manifest["publication_state"]["external_validation_complete"] is False


def test_unsafe_path_blocks_the_definition(tmp_path):
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    config["bundle_paths"] = config["bundle_paths"] + ["../private.txt"]
    unsafe = tmp_path / "unsafe.json"
    unsafe.write_text(json.dumps(config), encoding="utf-8")

    definition = module.inspect_release_candidate(unsafe)

    assert definition["checks"]["bundle_paths_safe"] is False
    assert definition["checks"]["bundle_paths_present"] is False
    assert definition["internal_release_candidate_ready"] is False


def test_private_path_and_secret_patterns_are_detected(tmp_path):
    module = load_module()
    leaked = tmp_path / "leaked.md"
    leaked.write_text(
        "C:" + "/Users/privateuser/private.txt\n"
        + "api_" + "key=" + "abcdefghijk12345\n",
        encoding="utf-8",
    )

    hits = module.scan_private_text(leaked)

    assert len(hits) == 2


def test_text_hash_mode_is_cross_platform_lf_stable(tmp_path):
    module = load_module()
    lf = tmp_path / "lf.md"
    crlf = tmp_path / "crlf.md"
    lf.write_bytes(b"alpha\nbeta\n")
    crlf.write_bytes(b"alpha\r\nbeta\r\n")

    lf_bytes, lf_mode = module.portable_file_bytes(lf)
    crlf_bytes, crlf_mode = module.portable_file_bytes(crlf)

    assert lf_mode == crlf_mode == "utf8_lf"
    assert lf_bytes == crlf_bytes == b"alpha\nbeta\n"


def test_release_notes_preserve_human_and_claim_boundaries():
    module = load_module()
    definition = module.inspect_release_candidate()
    notes = module.render_release_notes(
        definition,
        "3" * 40,
        "2026-07-21T00:00:00Z",
    )

    assert "GitHub release published: `false`" in notes
    assert "Zenodo DOI issued: `false`" in notes
    assert "CODECHECK request opened: `false`" in notes
    assert "External validation complete: `false`" in notes
    assert "fresh action-time HumanUnlock" in notes
    assert "It is not a published release" in notes
