from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "code" / "ops" / "RUN_REVIEWER_REPRODUCIBILITY_CAPSULE.py"
PROTOCOL = ROOT / "config" / "reviewer_reproducibility_protocol_v1.json"
PUBLISHED = ROOT / "out" / "ops" / "reviewer_reproducibility_capsule_latest.json"
DASHBOARD = ROOT / "dashboard" / "data" / "reviewer_reproducibility_capsule.json"
SBOM = ROOT / "evidence" / "reproducibility" / "reviewer_suite_sbom_20260714.cdx.json"
MARKDOWN = ROOT / "docs" / "REVIEWER_REPRODUCIBILITY_CAPSULE_2026-07-14.md"
WORKFLOW = ROOT / ".github" / "workflows" / "reviewer-reproducibility.yml"


def load_module():
    spec = importlib.util.spec_from_file_location(
        "reviewer_reproducibility_capsule", SCRIPT
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_protocol_is_frozen_version_pinned_and_claim_bounded():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    assert protocol["schema"] == "reviewer_reproducibility_protocol.v1"
    assert protocol["protocol_id"] == "LUMENCORE_REVIEWER_REPRODUCIBILITY_20260714"
    assert protocol["environment"]["python"] == "3.11.9"
    environment = protocol["environment"]
    assert environment["artifact_hash_lock_complete"] is True
    assert environment["cross_platform_artifact_hash_lock_complete"] is False
    assert environment["requirements_lock_package_count"] == 18
    assert environment["requirements_lock_resolver"]["target_platform"] == (
        "x86_64-unknown-linux-gnu"
    )
    assert environment["requirements_lock_resolver"]["source_builds_allowed"] is False
    assert environment["authoritative_runner"] == {
        "github_image": "ubuntu-24.04",
        "system": "Linux",
        "machine": "x86_64",
        "python": "3.11.9",
    }
    assert len(protocol["dependencies"]) == 8
    assert len(protocol["suites"]) == 3
    assert {row["runner"] for row in protocol["suites"]} == {
        "eia_wave",
        "eia_residual",
        "mda_open_set",
    }
    assert all(
        row["expected"]["promotion_gate_passed"] is False for row in protocol["suites"]
    )
    assert "not a NIST certification" in protocol["standards_references"][0]["use"]
    assert (
        "not independent scientific or field validation"
        in protocol["excluded_full_replays"][2]["reason"]
    )
    assert "TO_BE_FROZEN" not in json.dumps(protocol)
    assert protocol["amendment"]["failed_github_run_ids"] == [
        29335084468,
        29335574945,
    ]
    assert "post-observation" in protocol["amendment"]["preregistration_boundary"]
    residual = next(row for row in protocol["suites"] if row["runner"] == "eia_residual")
    assert residual["expected"]["relative_tolerance"] == 0.01
    assert "tolerance" not in residual["expected"]
    fixture_filter = protocol["fixture_test_command"][-1]
    assert "not published_receipt_reconciles_hashes" in fixture_filter
    assert "not sbom_has_scoped_component_identity" in fixture_filter
    assert "not markdown_reports_failures" in fixture_filter
    assert "code/ops/RUN_FAA_SDR_10K_BENCHMARK.py" in protocol["control_paths"]
    assert "config/reviewer_protocol_provenance_v1.json" in protocol["control_paths"]

    pins = {
        line.split("==", 1)[0]: line.split("==", 1)[1]
        for line in (ROOT / protocol["environment"]["requirements_path"])
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    }
    assert pins == {
        row["distribution"]: row["version"] for row in protocol["dependencies"]
    }


def test_workflow_excludes_checksum_manifest_from_its_own_hash_set():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.count('- "README.md"') == 2
    assert workflow.count('- "requirements-reviewer-ubuntu-py311.lock"') == 2
    assert "--require-hashes --only-binary=:all:" in workflow
    assert "VERIFY_REVIEWER_DEPENDENCY_LOCK.py" in workflow
    assert "--publish" in workflow
    assert "Verify the generated reviewer publications" in workflow
    assert "-type f ! -name SHA256SUMS -print0" in workflow
    assert "LC_ALL=C sort -z" in workflow
    assert (
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
        in workflow
    )


def test_packaged_eia_panel_is_deterministic_secret_free_and_hash_valid():
    module = load_module()
    protocol = module.load_protocol()
    frozen = protocol["frozen_inputs"][0]
    path = ROOT / frozen["path"]
    compressed = path.read_bytes()

    assert compressed[4:8] == b"\x00\x00\x00\x00"
    assert hashlib.sha256(compressed).hexdigest() == frozen["compressed_sha256"]
    raw = gzip.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == frozen["uncompressed_sha256"]

    panel = json.loads(raw.decode("utf-8"))
    assert panel["schema"] == "eia_grid_validation_panel.v1"
    assert panel["quality"]["row_count"] == 14_704
    assert panel["quality"]["authority_count"] == 8
    assert panel["quality"]["duplicate_conflict_count"] == 0
    assert panel["source"]["credential_serialized"] is False
    assert module.canonical_sha256(panel["rows"]) == frozen["row_chain_sha256"]
    assert not module.scan_private(panel)


def test_materialized_panel_is_scoped_verified_and_removed(tmp_path, monkeypatch):
    module = load_module()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    raw = b'{"schema":"fixture"}\n'
    protocol = {
        "frozen_inputs": [
            {
                "materialized_path": "data/panel.json",
                "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
            }
        ]
    }
    target = tmp_path / "data" / "panel.json"

    with module.materialize_frozen_panel(protocol, raw) as materialized:
        assert materialized == target
        assert target.read_bytes() == raw

    assert not target.exists()


def test_gitless_release_manifest_state_is_verified_and_fail_closed(
    tmp_path, monkeypatch
):
    module = load_module()
    source_commit = "a" * 40
    content = b"bounded\n"
    source = tmp_path / "source.txt"
    source.write_bytes(content)
    row = {
        "path": "source.txt",
        "bytes": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "hash_mode": "utf8_lf",
    }
    manifest = {
        "schema": "codecheck_eia_release_manifest.v1",
        "source_commit": source_commit,
        "bundle_inputs": [row],
    }
    (tmp_path / "RELEASE_MANIFEST.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "safe_git", lambda _args: "")
    monkeypatch.setenv("CODECHECK_SOURCE_COMMIT", source_commit)

    state = module.git_state([row])

    assert state["mode"] == "release_manifest"
    assert state["commit"] == source_commit
    assert state["source_state_verified"] is True
    assert state["relevant_source_clean"] is True
    assert state["release_manifest"]["bundle_input_pass_count"] == 1

    source.write_text("tampered\n", encoding="utf-8")
    assert module.git_state([row])["relevant_source_clean"] is False


def test_authoritative_runtime_gate_requires_linux_x86_64_python_3119(monkeypatch):
    module = load_module()
    protocol = module.load_protocol()
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(module.platform, "python_version", lambda: "3.11.9")

    receipt = module.authoritative_runtime_receipt(protocol)

    assert receipt["matches"] is True
    assert all(receipt["checks"].values())

    monkeypatch.setattr(module.platform, "system", lambda: "Windows")
    assert module.authoritative_runtime_receipt(protocol)["matches"] is False


def test_dependency_closure_gate_rejects_missing_or_unexpected_packages():
    module = load_module()
    dependency_lock = {"locked_packages": {"alpha": "1.0", "beta": "2.0"}}
    exact_sbom = {
        "components": [
            {"name": "Alpha", "version": "1.0", "purl": "pkg:pypi/alpha@1.0"},
            {"name": "beta", "version": "2.0", "purl": "pkg:pypi/beta@2.0"},
        ]
    }

    assert module.dependency_closure_receipt(dependency_lock, exact_sbom)["passed"]

    exact_sbom["components"].append(
        {"name": "gamma", "version": "3.0", "purl": "pkg:pypi/gamma@3.0"}
    )
    receipt = module.dependency_closure_receipt(dependency_lock, exact_sbom)
    assert receipt["passed"] is False
    assert receipt["unexpected_packages"] == ["gamma"]


def test_failed_suite_receipt_is_bounded_and_redacts_local_paths():
    module = load_module()
    suite = {
        "suite_id": "fixture",
        "kind": "fixture",
        "runner": "fixture",
    }

    receipt = module.failed_suite_result(
        suite,
        FileNotFoundError(r"C:\Users\Example\private\missing.json"),
    )

    assert receipt["passed"] is False
    assert receipt["error"]["type"] == "FileNotFoundError"
    assert "C:\\Users" not in receipt["error"]["message"]
    assert receipt["fact_projection_sha256"] == module.canonical_sha256({})

    portability = module.assertion(
        "portable_metric",
        0.2112062642583228,
        0.21211186326437864,
        relative_tolerance=0.01,
    )
    assert portability["passed"] is True
    assert portability["relative_difference"] < portability["relative_tolerance"]


def test_published_receipt_reconciles_hashes_assertions_and_public_projection():
    module = load_module()
    receipt = json.loads(PUBLISHED.read_text(encoding="utf-8"))
    dashboard = json.loads(DASHBOARD.read_text(encoding="utf-8"))

    assert receipt == dashboard
    assert receipt["status"] == "BOUNDED_REPRODUCIBILITY_PASS"
    assert (
        receipt["summary"]["suite_pass_count"] == receipt["summary"]["suite_count"] == 3
    )
    assert (
        receipt["summary"]["assertion_pass_count"]
        == receipt["summary"]["assertion_count"]
        == 31
    )
    assert receipt["summary"]["dependency_versions_exact_match"] is True
    assert receipt["summary"]["sbom_component_count"] >= 8
    assert receipt["summary"]["deterministic_environment_match"] is True
    assert receipt["summary"]["authoritative_runtime_match"] is True
    assert receipt["summary"]["dependency_closure_exact_match"] is True
    assert receipt["summary"]["artifact_hash_lock_complete"] is True
    assert receipt["summary"]["cross_platform_artifact_hash_lock_complete"] is False
    assert receipt["summary"]["locked_package_count"] == 18
    assert receipt["dependency_lock"]["passed"] is True
    assert receipt["dependency_lock"]["status"] == (
        "AUTHORITATIVE_RUNNER_LOCK_VALID"
    )
    assert receipt["dependency_lock"]["requirements_lock_sha256"] == (
        receipt["summary"]["dependency_lock_sha256"]
    )
    assert receipt["summary"]["external_validation_complete"] is False
    assert receipt["summary"]["agency_certification_complete"] is False
    assert "post-observation" in receipt["protocol_amendment"][
        "preregistration_boundary"
    ]
    if receipt["summary"]["fixture_tests_executed"]:
        assert receipt["summary"]["fixture_tests_passed"] is True
    assert receipt["privacy_scan"] == {
        "configured_pattern_hit_count": 0,
        "passed": True,
    }
    assert all(suite["passed"] for suite in receipt["suites"])
    assert all(
        check["passed"] for suite in receipt["suites"] for check in suite["assertions"]
    )
    assert receipt["source_chain_sha256"] == module.canonical_sha256(
        receipt["source_artifacts"]
    )
    without_hash = {
        key: value for key, value in receipt.items() if key != "capsule_sha256"
    }
    assert receipt["capsule_sha256"] == module.canonical_sha256(without_hash)
    assert not module.scan_private(receipt)

    artifacts = {row["path"]: row for row in receipt["source_artifacts"]}
    for path_text, artifact in artifacts.items():
        path = ROOT / path_text
        assert path.is_file()
        content = module.portable_file_bytes(path, artifact["hash_mode"])
        assert len(content) == artifact["bytes"]
        assert module.hashlib.sha256(content).hexdigest() == artifact["sha256"]


def test_portable_source_hash_normalizes_text_but_preserves_binary(tmp_path):
    module = load_module()
    text_path = tmp_path / "portable.py"
    text_path.write_bytes(b"alpha\r\nbeta\r\n")
    windows_bytes = module.portable_file_bytes(text_path)
    text_path.write_bytes(b"alpha\nbeta\n")
    linux_bytes = module.portable_file_bytes(text_path)

    binary_path = tmp_path / "frozen.json.gz"
    binary_path.write_bytes(b"\x1f\x8b\r\n\x00")

    assert windows_bytes == linux_bytes == b"alpha\nbeta\n"
    assert module.portable_file_bytes(binary_path) == b"\x1f\x8b\r\n\x00"


def test_sbom_has_scoped_component_identity_and_dependency_relationships():
    payload = json.loads(SBOM.read_text(encoding="utf-8"))
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))

    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.6"
    assert payload["serialNumber"].startswith("urn:uuid:")
    assert (
        payload["metadata"]["component"]["name"]
        == "LumenCore reviewer reproducibility capsule"
    )
    assert len(payload["components"]) >= 8
    assert all(
        row["name"] and row["version"] and row["purl"] for row in payload["components"]
    )
    root_ref = payload["metadata"]["component"]["bom-ref"]
    dependency_row = next(
        row for row in payload["dependencies"] if row["ref"] == root_ref
    )
    components_by_name = {row["name"].casefold(): row for row in payload["components"]}
    expected_direct_refs = {
        components_by_name[row["distribution"].casefold()]["bom-ref"]
        for row in protocol["dependencies"]
    }
    assert set(dependency_row["dependsOn"]) == expected_direct_refs
    valid_refs = {root_ref, *(row["bom-ref"] for row in payload["components"])}
    assert all(row["ref"] in valid_refs for row in payload["dependencies"])
    assert all(
        set(row["dependsOn"]).issubset(valid_refs) for row in payload["dependencies"]
    )


def test_markdown_reports_failures_and_unmet_external_gates_plainly():
    rendered = MARKDOWN.read_text(encoding="utf-8")

    assert "Suites passed: `3/3`" in rendered
    assert "Assertions passed: `31/31`" in rendered
    assert "`promotion_gate_passed`: `False`" in rendered
    assert "`coverage_gate_passed`: `False`" in rendered
    assert "External validation complete: `false`" in rendered
    assert "Agency certification complete: `false`" in rendered
    assert "Deterministic environment matched: `true`" in rendered
    assert "Authoritative runtime matched: `true`" in rendered
    assert "Installed dependency closure matched lock: `true`" in rendered
    assert "Artifact hash lock complete for authoritative runner: `true`" in rendered
    assert "Cross-platform artifact hash lock complete: `false`" in rendered
    assert "Dependency lock verification: `AUTHORITATIVE_RUNNER_LOCK_VALID`" in rendered
    assert "Fixture tests executed: `" in rendered
    assert "Fixture tests passed: `" in rendered
    assert "## Protocol Amendment" in rendered
    assert "post-observation" in rendered
    assert "relative_tolerance=`0.01`" in rendered
    assert "not a complete product SBOM" in rendered
    assert "about 114 MB" in rendered
