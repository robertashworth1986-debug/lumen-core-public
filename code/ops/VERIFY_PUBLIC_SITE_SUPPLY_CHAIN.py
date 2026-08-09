#!/usr/bin/env python3
"""Fail-closed verifier for the exact public-site SBOM and attestation workflow."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
BUILDER_PATH = ROOT / "code" / "deploy" / "build_public_site_supply_chain.py"
DEFAULT_WORKFLOW = ROOT / ".github" / "workflows" / "public-site-supply-chain.yml"
DEFAULT_GUIDE = ROOT / "docs" / "PUBLIC_SITE_SUPPLY_CHAIN_ASSURANCE.md"
WORKFLOW_REQUIREMENTS = (
    "permissions:\n      contents: read",
    "permissions:\n      contents: read\n      id-token: write\n      attestations: write\n      artifact-metadata: write",
    "if: github.event_name == 'push' && github.ref == 'refs/heads/main'",
    "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
    "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
    "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    "actions/download-artifact@3e5f45b2cfb9172054b4087a40e8e0b5a5461e7c",
    "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6",
    "sbom-path: /tmp/public-site-supply-chain/public-site-release.cdx.json",
    "--predicate-type https://cyclonedx.org/bom",
    "--signer-workflow \"$GITHUB_REPOSITORY/.github/workflows/public-site-supply-chain.yml\"",
    "--source-digest \"$GITHUB_SHA\"",
    "--source-ref refs/heads/main",
    "--cert-oidc-issuer https://token.actions.githubusercontent.com",
    "--deny-self-hosted-runners",
    "git diff --check \"${BASE_SHA}...HEAD\"",
    "python code/ops/VERIFY_PUBLIC_SITE_SUPPLY_CHAIN.py",
    "test_public_site_supply_chain.py",
)
GUIDE_REQUIREMENTS = (
    "CycloneDX 1.6",
    "exact 43-file public release",
    "legacy-route HOLD stubs",
    "GitHub-hosted `main` workflow",
    "Sigstore-signed",
    "No SLSA level is claimed",
    "not a complete VPS",
    "live site remains `HOLD`",
    "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
    "gh attestation verify",
)


class SupplyChainVerificationError(ValueError):
    """Raised when supply-chain evidence is incomplete, drifted, or promoted."""


def _load_builder(root: Path):
    path = root / "code" / "deploy" / "build_public_site_supply_chain.py"
    spec = importlib.util.spec_from_file_location("public_site_supply_chain_builder", path)
    if spec is None or spec.loader is None:
        raise SupplyChainVerificationError("cannot load public-site supply-chain builder")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_regular(path: Path, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise SupplyChainVerificationError(f"{label} must be a regular non-symlink file")


def _require_text(path: Path, label: str) -> str:
    _require_regular(path, label)
    try:
        return path.read_text(encoding="utf-8").replace("\r\n", "\n")
    except UnicodeDecodeError as exc:
        raise SupplyChainVerificationError(f"{label} is not valid UTF-8") from exc


def _exact_render(value: dict[str, Any]) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n").encode(
        "utf-8"
    )


def verify_supply_chain(
    *,
    root: Path,
    archive_path: Path,
    manifest_path: Path,
    source_commit: str,
    sbom_path: Path,
    receipt_path: Path,
    workflow_path: Path,
    guide_path: Path,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    for label, path in (
        ("archive", archive_path),
        ("manifest", manifest_path),
        ("SBOM", sbom_path),
        ("receipt", receipt_path),
    ):
        _require_regular(path, label)

    builder = _load_builder(root)
    try:
        manifest, rows = builder.validate_release_inputs(
            repo_root=root,
            archive_path=archive_path,
            manifest_path=manifest_path,
            source_commit=source_commit,
        )
        actual_sbom = builder.read_json(sbom_path, max_bytes=4_000_000)
        actual_receipt = builder.read_json(receipt_path, max_bytes=1_000_000)
    except (OSError, builder.SupplyChainBuildError, json.JSONDecodeError) as exc:
        raise SupplyChainVerificationError(str(exc)) from exc

    expected_sbom = builder.build_sbom(manifest=manifest, rows=rows)
    expected_receipt = builder.build_receipt(
        archive_path=archive_path,
        manifest_path=manifest_path,
        manifest=manifest,
        rows=rows,
        sbom=expected_sbom,
    )
    if actual_sbom != expected_sbom:
        raise SupplyChainVerificationError("CycloneDX inventory content drift")
    if actual_receipt != expected_receipt:
        raise SupplyChainVerificationError("supply-chain receipt content drift")
    if sbom_path.read_bytes() != _exact_render(expected_sbom):
        raise SupplyChainVerificationError("CycloneDX inventory serialization drift")
    if receipt_path.read_bytes() != _exact_render(expected_receipt):
        raise SupplyChainVerificationError("supply-chain receipt serialization drift")

    root_component = actual_sbom.get("metadata", {}).get("component", {})
    components = actual_sbom.get("components")
    dependencies = actual_sbom.get("dependencies")
    if actual_sbom.get("bomFormat") != "CycloneDX" or actual_sbom.get("specVersion") != "1.6":
        raise SupplyChainVerificationError("CycloneDX identity mismatch")
    if not isinstance(components, list) or len(components) != manifest["file_count"]:
        raise SupplyChainVerificationError("CycloneDX component coverage mismatch")
    if not isinstance(dependencies, list) or len(dependencies) != len(components) + 1:
        raise SupplyChainVerificationError("CycloneDX dependency graph coverage mismatch")
    if root_component.get("hashes") != [
        {"alg": "SHA-256", "content": manifest["archive_sha256"]}
    ]:
        raise SupplyChainVerificationError("CycloneDX release subject hash mismatch")
    actual_names = [component.get("name") for component in components]
    expected_names = [row["archive_name"] for row in rows]
    if actual_names != expected_names or len(actual_names) != len(set(actual_names)):
        raise SupplyChainVerificationError("CycloneDX release component identity mismatch")
    if actual_receipt.get("production_decision") != (
        "HOLD_UNTIL_EXPLICIT_DEPLOYMENT_AND_EXACT_LIVE_VERIFICATION"
    ):
        raise SupplyChainVerificationError("production decision was promoted")
    if actual_receipt.get("signed_attestation_state") != (
        "NOT_CREATED_BY_THIS_LOCAL_BUILDER"
    ):
        raise SupplyChainVerificationError("local builder must not claim a signature")
    if actual_receipt.get("coverage", {}).get("exact_release_file_coverage_ratio") != 1.0:
        raise SupplyChainVerificationError("release-file inventory is incomplete")
    expected_receipt_hash = builder.sha256_bytes(
        builder.canonical_bytes(
            {key: value for key, value in actual_receipt.items() if key != "receipt_sha256"}
        )
    )
    if actual_receipt.get("receipt_sha256") != expected_receipt_hash:
        raise SupplyChainVerificationError("receipt self-hash mismatch")

    workflow = _require_text(workflow_path, "workflow")
    for required in WORKFLOW_REQUIREMENTS:
        if required not in workflow:
            raise SupplyChainVerificationError(f"workflow binding missing: {required}")
    attest_job = workflow.split("  attest:", maxsplit=1)
    if len(attest_job) != 2:
        raise SupplyChainVerificationError("separate main-only attestation job is missing")
    if "pull_request" in attest_job[1].split("permissions:", maxsplit=1)[0]:
        raise SupplyChainVerificationError("attestation job cannot be enabled for pull requests")

    guide = _require_text(guide_path, "guide")
    normalized_guide = " ".join(guide.lower().split())
    for required in GUIDE_REQUIREMENTS:
        if " ".join(required.lower().split()) not in normalized_guide:
            raise SupplyChainVerificationError(f"guide limitation missing: {required}")
    forbidden_guide_claims = (
        "slsa build l1 achieved",
        "slsa build l2 achieved",
        "slsa build l3 achieved",
        "complete product sbom",
        "production deployment verified",
        "independently validated",
    )
    for forbidden in forbidden_guide_claims:
        if forbidden in normalized_guide:
            raise SupplyChainVerificationError(f"unsupported guide promotion: {forbidden}")

    verification: dict[str, Any] = {
        "schema": "lumencore.public_site_supply_chain_verification.v1",
        "valid": True,
        "repository": builder.REPOSITORY,
        "source_commit": source_commit,
        "release_subject_sha256": manifest["archive_sha256"],
        "release_manifest_sha256": sha256_file(manifest_path),
        "sbom_sha256": sha256_file(sbom_path),
        "supply_chain_receipt_sha256": sha256_file(receipt_path),
        "release_file_count": manifest["file_count"],
        "inventoried_release_file_count": len(components),
        "inventory_coverage_ratio": 1.0,
        "signed_attestation_scope": "MAIN_BRANCH_GITHUB_HOSTED_WORKFLOW_ONLY",
        "production_decision": "HOLD_UNTIL_EXPLICIT_DEPLOYMENT_AND_EXACT_LIVE_VERIFICATION",
        "claim_boundary": (
            "This verifies exact-release SBOM construction and attestation workflow policy. "
            "It does not prove that a signed main-branch attestation exists until that workflow "
            "runs successfully, and it does not establish a SLSA level, certification, external "
            "validation, security, or live-domain parity."
        ),
    }
    verification["verification_sha256"] = builder.sha256_bytes(
        builder.canonical_bytes(verification)
    )
    return verification


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        prefix=f".{path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(rendered)
        temporary_path = Path(temporary.name)
    try:
        temporary_path.replace(path)
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument("--workflow", type=Path, default=DEFAULT_WORKFLOW)
    parser.add_argument("--guide", type=Path, default=DEFAULT_GUIDE)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        verification = verify_supply_chain(
            root=args.root,
            archive_path=args.archive,
            manifest_path=args.manifest,
            source_commit=args.source_commit,
            sbom_path=args.sbom,
            receipt_path=args.receipt,
            workflow_path=args.workflow,
            guide_path=args.guide,
        )
    except (OSError, SupplyChainVerificationError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    if args.json_out:
        _write_json(args.json_out, verification)
    print(json.dumps(verification, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
