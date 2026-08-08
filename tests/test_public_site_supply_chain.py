from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_public_site_release.py"
BUILDER_PATH = ROOT / "code" / "deploy" / "build_public_site_supply_chain.py"
VERIFIER_PATH = ROOT / "code" / "ops" / "VERIFY_PUBLIC_SITE_SUPPLY_CHAIN.py"
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "public-site-supply-chain.yml"
GUIDE_PATH = ROOT / "docs" / "PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md"
EXACT_SNAPSHOT_CI = ROOT / ".github" / "workflows" / "public-site-exact-snapshot-ci.yml"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PACKAGER = load_module(PACKAGER_PATH, "public_site_packager_supply_chain_tests")
BUILDER = load_module(BUILDER_PATH, "public_site_supply_chain_builder_tests")
VERIFIER = load_module(VERIFIER_PATH, "public_site_supply_chain_verifier_tests")


def current_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def build_fixture(tmp_path: Path):
    commit = current_commit()
    archive = tmp_path / "public-site-release.tar"
    manifest = tmp_path / "public-site-release-manifest.json"
    sbom = tmp_path / "public-site-release.cdx.json"
    receipt = tmp_path / "public-site-supply-chain-receipt.json"
    PACKAGER.build_release_package(
        repo_root=ROOT,
        source_commit=commit,
        archive_path=archive,
        manifest_path=manifest,
    )
    BUILDER.build_supply_chain(
        repo_root=ROOT,
        archive_path=archive,
        manifest_path=manifest,
        source_commit=commit,
        sbom_path=sbom,
        receipt_path=receipt,
    )
    return commit, archive, manifest, sbom, receipt


def verify_fixture(commit, archive, manifest, sbom, receipt, **overrides):
    return VERIFIER.verify_supply_chain(
        root=ROOT,
        archive_path=archive,
        manifest_path=manifest,
        source_commit=commit,
        sbom_path=sbom,
        receipt_path=receipt,
        workflow_path=overrides.get("workflow", WORKFLOW_PATH),
        guide_path=overrides.get("guide", GUIDE_PATH),
    )


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_current_commit_builds_and_verifies_exact_release_inventory(tmp_path):
    commit, archive, manifest, sbom, receipt = build_fixture(tmp_path)
    verification = verify_fixture(commit, archive, manifest, sbom, receipt)
    payload = json.loads(sbom.read_text(encoding="utf-8"))
    local = json.loads(receipt.read_text(encoding="utf-8"))

    assert verification["valid"] is True
    assert verification["source_commit"] == commit
    assert verification["release_file_count"] == 30
    assert verification["inventoried_release_file_count"] == 30
    assert verification["inventory_coverage_ratio"] == 1.0
    assert verification["production_decision"].startswith("HOLD_")
    assert payload["bomFormat"] == "CycloneDX"
    assert payload["specVersion"] == "1.6"
    assert len(payload["components"]) == 30
    assert len(payload["dependencies"]) == 31
    assert local["signed_attestation_state"] == "NOT_CREATED_BY_THIS_LOCAL_BUILDER"
    assert local["coverage"]["exact_release_file_coverage_ratio"] == 1.0


def test_inventory_and_receipt_are_byte_deterministic(tmp_path):
    commit, archive, manifest, first_sbom, first_receipt = build_fixture(tmp_path / "first")
    second_root = tmp_path / "second"
    second_root.mkdir()
    second_sbom = second_root / first_sbom.name
    second_receipt = second_root / first_receipt.name
    BUILDER.build_supply_chain(
        repo_root=ROOT,
        archive_path=archive,
        manifest_path=manifest,
        source_commit=commit,
        sbom_path=second_sbom,
        receipt_path=second_receipt,
    )
    assert first_sbom.read_bytes() == second_sbom.read_bytes()
    assert first_receipt.read_bytes() == second_receipt.read_bytes()


def test_duplicate_and_nonfinite_json_are_rejected(tmp_path):
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text('{"schema":"one","schema":"two"}\n', encoding="utf-8")
    with pytest.raises(BUILDER.SupplyChainBuildError, match="duplicate JSON key"):
        BUILDER.read_json(duplicate)

    nonfinite = tmp_path / "nonfinite.json"
    nonfinite.write_text('{"value":NaN}\n', encoding="utf-8")
    with pytest.raises(BUILDER.SupplyChainBuildError, match="non-finite"):
        BUILDER.read_json(nonfinite)


def test_archive_tamper_is_rejected_even_if_manifest_archive_hash_is_rewritten(tmp_path):
    commit, archive, manifest, _sbom, _receipt = build_fixture(tmp_path)
    archive.write_bytes(archive.read_bytes() + b"tamper")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["archive_sha256"] = hashlib.sha256(archive.read_bytes()).hexdigest()
    write_json(manifest, payload)
    with pytest.raises(BUILDER.SupplyChainBuildError, match="archive"):
        BUILDER.validate_release_inputs(
            repo_root=ROOT,
            archive_path=archive,
            manifest_path=manifest,
            source_commit=commit,
        )


def test_manifest_reorder_and_unsafe_path_are_rejected(tmp_path):
    commit, archive, manifest, _sbom, _receipt = build_fixture(tmp_path)
    original = json.loads(manifest.read_text(encoding="utf-8"))

    reordered = copy.deepcopy(original)
    reordered["files"][0], reordered["files"][1] = (
        reordered["files"][1],
        reordered["files"][0],
    )
    write_json(manifest, reordered)
    with pytest.raises(BUILDER.SupplyChainBuildError, match="order or identity"):
        BUILDER.validate_release_inputs(
            repo_root=ROOT,
            archive_path=archive,
            manifest_path=manifest,
            source_commit=commit,
        )

    unsafe = copy.deepcopy(original)
    unsafe["files"][0]["archive_name"] = "../operator_home.html"
    write_json(manifest, unsafe)
    with pytest.raises(BUILDER.SupplyChainBuildError, match="unsafe"):
        BUILDER.validate_release_inputs(
            repo_root=ROOT,
            archive_path=archive,
            manifest_path=manifest,
            source_commit=commit,
        )


def test_manifest_git_blob_identity_must_match_source_commit(tmp_path):
    commit, archive, manifest, _sbom, _receipt = build_fixture(tmp_path)
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    payload["files"][0]["git_blob_oid"] = "0" * 40
    write_json(manifest, payload)
    with pytest.raises(BUILDER.SupplyChainBuildError, match="does not match source commit"):
        BUILDER.validate_release_inputs(
            repo_root=ROOT,
            archive_path=archive,
            manifest_path=manifest,
            source_commit=commit,
        )


def test_missing_or_modified_sbom_component_fails_closed(tmp_path):
    commit, archive, manifest, sbom, receipt = build_fixture(tmp_path)
    payload = json.loads(sbom.read_text(encoding="utf-8"))
    payload["components"].pop()
    write_json(sbom, payload)
    with pytest.raises(VERIFIER.SupplyChainVerificationError, match="inventory content drift"):
        verify_fixture(commit, archive, manifest, sbom, receipt)


def test_local_receipt_cannot_claim_a_signature_or_production_release(tmp_path):
    commit, archive, manifest, sbom, receipt = build_fixture(tmp_path)
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    payload["signed_attestation_state"] = "SIGNED"
    payload["production_decision"] = "PRODUCTION_VERIFIED"
    write_json(receipt, payload)
    with pytest.raises(VERIFIER.SupplyChainVerificationError, match="receipt content drift"):
        verify_fixture(commit, archive, manifest, sbom, receipt)


def test_workflow_separates_read_only_pr_build_from_main_only_signing(tmp_path):
    commit, archive, manifest, sbom, receipt = build_fixture(tmp_path)
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6" in workflow
    assert "--predicate-type https://cyclonedx.org/bom" in workflow
    assert "--deny-self-hosted-runners" in workflow
    assert "--cert-oidc-issuer https://token.actions.githubusercontent.com" in workflow
    assert "artifact-metadata: write" in workflow

    weakened = tmp_path / "weakened.yml"
    weakened.write_text(
        workflow.replace(
            "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
            "if: always()",
        ),
        encoding="utf-8",
    )
    with pytest.raises(VERIFIER.SupplyChainVerificationError, match="workflow binding"):
        verify_fixture(
            commit,
            archive,
            manifest,
            sbom,
            receipt,
            workflow=weakened,
        )


def test_guide_must_keep_slsa_and_live_deployment_boundaries(tmp_path):
    commit, archive, manifest, sbom, receipt = build_fixture(tmp_path)
    guide = GUIDE_PATH.read_text(encoding="utf-8")
    weakened = tmp_path / "guide.md"
    weakened.write_text(
        guide.replace("No SLSA level is claimed", "A supply-chain level is described"),
        encoding="utf-8",
    )
    with pytest.raises(VERIFIER.SupplyChainVerificationError, match="guide limitation"):
        verify_fixture(
            commit,
            archive,
            manifest,
            sbom,
            receipt,
            guide=weakened,
        )


def test_exact_snapshot_ci_tracks_both_machine_release_files():
    workflow = EXACT_SNAPSHOT_CI.read_text(encoding="utf-8")
    assert workflow.count("dashboard/reviewer_docket.json") == 2
    assert workflow.count("dashboard/manifest.json") == 2


def test_output_symlink_is_rejected_when_supported(tmp_path):
    commit = current_commit()
    archive = tmp_path / "release.tar"
    manifest = tmp_path / "manifest.json"
    PACKAGER.build_release_package(
        repo_root=ROOT,
        source_commit=commit,
        archive_path=archive,
        manifest_path=manifest,
    )
    target = tmp_path / "target.json"
    target.write_text("{}\n", encoding="utf-8")
    sbom = tmp_path / "sbom.json"
    try:
        sbom.symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(BUILDER.SupplyChainBuildError, match="cannot be symlinks"):
        BUILDER.build_supply_chain(
            repo_root=ROOT,
            archive_path=archive,
            manifest_path=manifest,
            source_commit=commit,
            sbom_path=sbom,
            receipt_path=tmp_path / "receipt.json",
        )
