from __future__ import annotations

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "VERIFY_CODECHECK_MAINLINE_INTEGRATION.py"
CONFIG = ROOT / "config" / "codecheck_eia_mainline_integration_v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("codecheck_mainline_integration", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mainline_integration_is_exact_bounded_and_fail_closed():
    module = load_module()
    receipt = module.inspect_integration()

    assert receipt["passed"] is True
    assert receipt["status"] == "MAINLINE_INTEGRATION_READY"
    assert receipt["frozen_file_count"] == 30
    assert all(receipt["checks"].values())
    assert len(receipt["manifest_outputs"]) == 6
    assert receipt["privacy_scan"]["passed"] is True
    assert all(value is False for value in receipt["claim_state"].values())
    assert receipt["first_party_receipts"]["passed"] is True


def test_line_endings_do_not_change_frozen_text_identity(tmp_path):
    module = load_module()
    lf = tmp_path / "sample.txt"
    crlf = tmp_path / "sample-crlf.txt"
    lf.write_bytes(b"alpha\nbeta\n")
    crlf.write_bytes(b"alpha\r\nbeta\r\n")

    assert module.git_blob_sha1(module.portable_bytes(lf, "utf8_lf")) == module.git_blob_sha1(
        module.portable_bytes(crlf, "utf8_lf")
    )


def test_manifest_parser_preserves_order_and_rejects_duplicate_or_unsafe_outputs():
    module = load_module()
    text = """manifest:
  - file: "out/a.json"
  - file: "out/b.log"

paper:
  title: "bounded"
"""
    outputs = module.parse_codecheck_manifest(text)

    assert outputs == ["out/a.json", "out/b.log"]
    assert len(outputs) == len(set(outputs))
    assert all(module.safe_repo_path(value) for value in outputs)
    assert module.safe_repo_path("../private.json") is False
    assert module.safe_repo_path("C:" + "/private.json") is False


def test_tampered_frozen_file_is_detected(tmp_path):
    module = load_module()
    target = tmp_path / "artifact.txt"
    target.write_text("changed\n", encoding="utf-8")
    row = {
        "path": "artifact.txt",
        "blob_sha1": module.git_blob_sha1(b"expected\n"),
        "hash_mode": "utf8_lf",
    }

    observed = module.inspect_frozen_file(row, tmp_path)

    assert observed["present"] is True
    assert observed["matched"] is False


def test_protocol_has_no_overlap_between_frozen_core_and_allowed_drift():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    frozen = {row["path"] for row in config["exact_frozen_files"]}
    drift = set(config["allowed_integration_drift_paths"])

    assert frozen.isdisjoint(drift)
