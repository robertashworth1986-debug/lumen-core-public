from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
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
    review = receipt["author_review_preflight"]
    assert review["passed"] is True
    assert review["status"] == "READY_FOR_AUTHOR_REVIEW_NO_SEND"
    assert review["human_decision_count"] == 9
    assert review["human_completed_item_count"] == 0
    assert review["human_author_review_complete"] is False
    assert review["production_request_authorized"] is False
    contract = receipt["official_request_contract"]
    assert contract["passed"] is True
    assert contract["status"] == "OFFICIAL_REQUEST_CONTRACT_READY_NO_SEND"
    assert contract["candidate_identifier"] == "2026-022"
    assert contract["candidate_reserved"] is False
    assert contract["external_action_authorized"] is False
    assert contract["request_opened"] is False


def test_official_request_contract_binds_the_frozen_author_package():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    contract = module.inspect_official_request_contract(config)

    assert contract["passed"] is True
    assert len(contract["frozen_author_files"]) == 3
    assert all(row["present"] for row in contract["frozen_author_files"])
    assert all(row["matched"] for row in contract["frozen_author_files"])
    assert all(row["utf8"] for row in contract["frozen_author_files"])
    assert contract["missing_readme_snippets"] == []
    assert contract["missing_license_snippets"] == []
    assert contract["missing_request_snippets"] == []
    assert contract["missing_request_labels"] == []
    assert contract["missing_yaml_root_fields"] == []
    assert contract["checker_managed_yaml_root_fields_present"] == []


def test_frozen_author_package_detects_wrong_blob_identity():
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    row = dict(config["official_request_contract"]["frozen_author_package_files"][0])
    row["blob_sha1"] = "0" * 40

    observed = module.inspect_frozen_git_file(config["frozen_target"]["commit"], row)

    assert observed["present"] is True
    assert observed["matched"] is False


def test_yaml_root_field_parser_exposes_premature_checker_metadata():
    module = load_module()
    fields = module.parse_yaml_root_fields(
        "%YAML 1.1\n---\nmanifest:\n  - file: out/result.json\npaper:\n  title: bounded\n"
        "codechecker:\n  - name: Premature Reviewer\nreport: pending\n"
    )

    assert fields == ["manifest", "paper", "codechecker", "report"]


def test_line_endings_do_not_change_frozen_text_identity(tmp_path):
    module = load_module()
    lf = tmp_path / "sample.txt"
    crlf = tmp_path / "sample-crlf.txt"
    lf.write_bytes(b"alpha\nbeta\n")
    crlf.write_bytes(b"alpha\r\nbeta\r\n")

    assert module.git_blob_sha1(module.portable_bytes(lf, "utf8_lf")) == module.git_blob_sha1(
        module.portable_bytes(crlf, "utf8_lf")
    )


def test_every_frozen_input_has_checkout_custody_matching_its_hash_mode():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    rows = config["exact_frozen_files"]
    paths = [row["path"] for row in rows]
    result = subprocess.run(
        ["git", "check-attr", "text", "eol", "binary", "--", *paths],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )

    assert result.returncode == 0, result.stderr
    observed: dict[str, dict[str, str]] = {path: {} for path in paths}
    for line in result.stdout.splitlines():
        path, attribute, value = line.rsplit(": ", 2)
        observed[path][attribute] = value

    assert set(observed) == set(paths)
    for row in rows:
        attrs = observed[row["path"]]
        if row["hash_mode"] == "utf8_lf":
            assert attrs["text"] == "set", row["path"]
            assert attrs["eol"] == "lf", row["path"]
            assert attrs["binary"] == "unspecified", row["path"]
        else:
            assert row["hash_mode"] == "binary"
            assert attrs["text"] == "unset", row["path"]
            assert attrs["binary"] == "set", row["path"]


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


def test_author_review_card_proves_machine_facts_without_completing_human_gates():
    module = load_module()
    receipt = module.inspect_integration()

    card = module.render_author_review_card(receipt)

    assert "Status: `READY_FOR_AUTHOR_REVIEW_NO_SEND`" in card
    assert "Passed: `14/14`" in card
    assert "Completed by machine: `0/9`" in card
    assert receipt["author_review_preflight"]["author_review_unlock_phrase"] in card
    assert "That phrase records author review only." in card
    assert "`external_validation_complete`: `false`" in card
    assert "production CODECHECK request" in card


def test_checked_public_author_assertion_fails_closed(tmp_path):
    module = load_module()
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    control = config["author_review_control"]
    for key in ("checklist_path", "request_draft_path", "license_path", "citation_path"):
        relative = Path(control[key])
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)

    checklist = tmp_path / control["checklist_path"]
    text = checklist.read_text(encoding="utf-8")
    checklist.write_text(text.replace("- [ ]", "- [x]", 1), encoding="utf-8")
    codecheck_text = (ROOT / "codecheck.yml").read_text(encoding="utf-8")

    review = module.inspect_author_review(config, codecheck_text, tmp_path)

    assert review["passed"] is False
    assert review["status"] == "AUTHOR_REVIEW_PREFLIGHT_BLOCKED"
    assert review["checks"]["checklist_has_no_completed_assertions"] is False
    assert review["human_completed_item_count"] == 1
    assert review["human_author_review_complete"] is False


def test_workflow_hashes_artifacts_from_the_uploaded_root():
    workflow = (ROOT / ".github" / "workflows" / "reviewer-reproducibility.yml").read_text(
        encoding="utf-8"
    )

    assert "fetch-depth: 0" in workflow
    assert "cd out/reproducibility/ci" in workflow
    assert "find . -type f ! -name SHA256SUMS -print0" in workflow
    assert "> SHA256SUMS" in workflow
    assert "find out/reproducibility/ci -type f" not in workflow
