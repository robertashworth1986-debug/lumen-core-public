#!/usr/bin/env python3
"""Fail-closed verifier for retained exact public-site deployment receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RECEIPT_ROOT = ROOT / "evidence" / "public-site-deployments"
DEFAULT_SOURCE_COMMIT = "1ce7c35975a4011fa844e8b39ccbc950c8c0f398"
DEFAULT_RECEIPT = (
    RECEIPT_ROOT
    / DEFAULT_SOURCE_COMMIT
    / "deployment-receipt.json"
)
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_public_site_release.py"
SUPPLY_CHAIN_PATH = ROOT / "code" / "deploy" / "build_public_site_supply_chain.py"
HEX64 = re.compile(r"[0-9a-f]{64}")
HEX40 = re.compile(r"[0-9a-f]{40}")

REQUIRED_BOUNDARIES = {
    "independent audit or certification",
    "43 allowlisted static public-release files",
    "does not establish scientific validity",
    "does not authorize later deployments",
}


class DeploymentReceiptError(ValueError):
    """Raised when the retained receipt is malformed, drifted, or promoted."""


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise DeploymentReceiptError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_packager_at_commit(
    *, root: Path, source_commit: str, destination: Path
):
    """Load the packager retained by the receipt's Git subject, not today's allowlist."""
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "show",
                f"{source_commit}:code/deploy/package_public_site_release.py",
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"").decode("utf-8", errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise DeploymentReceiptError(
            f"cannot recover historical packager from {source_commit}{suffix}"
        ) from exc
    destination.write_bytes(completed.stdout)
    return _load(destination, f"deployment_packager_{source_commit}")


def _reject_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DeploymentReceiptError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > 1_000_000:
        raise DeploymentReceiptError("receipt exceeds size limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_reject_duplicates)
    except UnicodeDecodeError as exc:
        raise DeploymentReceiptError("receipt is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise DeploymentReceiptError("receipt must be an object")
    return value


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise DeploymentReceiptError(f"{label} must be a lowercase SHA-256")
    return value


def _require_successful_run(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise DeploymentReceiptError(f"{label} must be an object")
    if value.get("conclusion") != "success":
        raise DeploymentReceiptError(f"{label} is not successful")
    run_id = value.get("run_id")
    url = value.get("url")
    if not isinstance(run_id, int) or run_id <= 0:
        raise DeploymentReceiptError(f"{label}.run_id is invalid")
    expected_url = (
        "https://github.com/robertashworth1986-debug/lumen-core-public/"
        f"actions/runs/{run_id}"
    )
    if url != expected_url:
        raise DeploymentReceiptError(f"{label}.url is not bound to run_id")


def _bind_repository_receipt_path(
    *, root: Path, receipt_path: Path, source_commit: str
) -> None:
    receipt_root = (root / "evidence" / "public-site-deployments").resolve()
    resolved = receipt_path.resolve()
    try:
        relative = resolved.relative_to(receipt_root)
    except ValueError:
        return
    if relative.parts != (source_commit, "deployment-receipt.json"):
        raise DeploymentReceiptError("receipt path is not bound to source commit")


def verify_receipt(
    *, root: Path = ROOT, receipt_path: Path = DEFAULT_RECEIPT
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    receipt = read_json(receipt_path)
    if receipt.get("schema") != "lumencore.public_site_exact_deployment_receipt.v1":
        raise DeploymentReceiptError("receipt schema mismatch")
    if receipt.get("repository") != "robertashworth1986-debug/lumen-core-public":
        raise DeploymentReceiptError("repository mismatch")
    source_commit = receipt.get("source_commit")
    if not isinstance(source_commit, str) or HEX40.fullmatch(source_commit) is None:
        raise DeploymentReceiptError("source commit must be a lowercase Git SHA")
    _bind_repository_receipt_path(
        root=root, receipt_path=receipt_path, source_commit=source_commit
    )

    recorded_self_hash = _require_sha(receipt.get("receipt_sha256"), "receipt_sha256")
    unsigned = dict(receipt)
    unsigned.pop("receipt_sha256")
    if sha256_bytes(canonical_bytes(unsigned)) != recorded_self_hash:
        raise DeploymentReceiptError("receipt self-hash mismatch")

    subject = receipt.get("release_subject")
    if not isinstance(subject, dict):
        raise DeploymentReceiptError("release_subject must be an object")
    if subject.get("release_file_count") != 43:
        raise DeploymentReceiptError("release file count mismatch")
    if subject.get("cyclonedx_component_count") != 43:
        raise DeploymentReceiptError("CycloneDX component count mismatch")
    if subject.get("cyclonedx_spec_version") != "1.6":
        raise DeploymentReceiptError("CycloneDX version mismatch")
    for field in ("archive_sha256", "manifest_sha256", "cyclonedx_sha256"):
        _require_sha(subject.get(field), f"release_subject.{field}")

    supply_chain = _load(
        root / SUPPLY_CHAIN_PATH.relative_to(ROOT), "deployment_supply_chain"
    )
    with tempfile.TemporaryDirectory() as tmp:
        packager = _load_packager_at_commit(
            root=root,
            source_commit=source_commit,
            destination=Path(tmp) / "package_public_site_release.py",
        )
        if len(packager.RELEASE_PATHS) != 43:
            raise DeploymentReceiptError("historical allowlist count drifted from receipt")
        archive = Path(tmp) / "public-site-release.tar"
        manifest_path = Path(tmp) / "public-site-release-manifest.json"
        built = packager.build_release_package(
            repo_root=root,
            source_commit=source_commit,
            archive_path=archive,
            manifest_path=manifest_path,
        )
        if built.get("file_count") != 43:
            raise DeploymentReceiptError("reconstructed file count mismatch")
        if archive.stat().st_size != subject.get("archive_bytes"):
            raise DeploymentReceiptError("archive byte count mismatch")
        if sha256_bytes(archive.read_bytes()) != subject.get("archive_sha256"):
            raise DeploymentReceiptError("archive SHA-256 mismatch")
        if sha256_bytes(manifest_path.read_bytes()) != subject.get("manifest_sha256"):
            raise DeploymentReceiptError("manifest SHA-256 mismatch")
        manifest = supply_chain.read_json(manifest_path)
        rows = manifest.get("files")
        if not isinstance(rows, list) or len(rows) != 43:
            raise DeploymentReceiptError("historical manifest row count mismatch")
        sbom = supply_chain.build_sbom(manifest=manifest, rows=rows)
        rendered_sbom = json.dumps(
            sbom, indent=2, sort_keys=True, ensure_ascii=True
        ).encode("utf-8") + b"\n"
        if sha256_bytes(rendered_sbom) != subject.get("cyclonedx_sha256"):
            raise DeploymentReceiptError("CycloneDX SHA-256 mismatch")

    supply = receipt.get("supply_chain")
    _require_successful_run(supply, "supply_chain")
    if supply.get("event") != "push":
        raise DeploymentReceiptError("supply-chain trigger mismatch")
    if supply.get("signed_attestation_scope") != "MAIN_BRANCH_GITHUB_HOSTED_WORKFLOW_ONLY":
        raise DeploymentReceiptError("signed attestation scope mismatch")
    attestations = supply.get("attestations")
    if not isinstance(attestations, list) or len(attestations) != 2:
        raise DeploymentReceiptError("attestation set mismatch")
    if {item.get("predicate_type") for item in attestations} != {
        "https://slsa.dev/provenance/v1",
        "https://cyclonedx.org/bom",
    }:
        raise DeploymentReceiptError("predicate set mismatch")
    for index, item in enumerate(attestations):
        if item.get("verification_state") != "VERIFIED":
            raise DeploymentReceiptError(f"attestations[{index}] is not verified")
        if item.get("verified_timestamp_count") != 1:
            raise DeploymentReceiptError(f"attestations[{index}] timestamp mismatch")
        _require_sha(item.get("bundle_sha256"), f"attestations[{index}].bundle_sha256")
        _require_sha(
            item.get("verification_sha256"),
            f"attestations[{index}].verification_sha256",
        )

    deployment = receipt.get("deployment")
    _require_successful_run(deployment, "deployment")
    if deployment.get("approval") != "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT":
        raise DeploymentReceiptError("deployment approval mismatch")
    if deployment.get("expected_file_count") != 43 or deployment.get(
        "matched_file_count"
    ) != 43:
        raise DeploymentReceiptError("deployment live-gate count mismatch")
    if deployment.get("release_verified") is not True:
        raise DeploymentReceiptError("deployment release is not verified")
    _require_sha(deployment.get("deployment_receipt_sha256"), "deployment receipt")
    _require_sha(deployment.get("live_gate_sha256"), "deployment live gate")

    audit = receipt.get("post_deployment_audit")
    _require_successful_run(audit, "post_deployment_audit")
    if audit.get("expected_file_count") != 43 or audit.get("matched_file_count") != 43:
        raise DeploymentReceiptError("post-deployment audit count mismatch")
    if audit.get("release_verified") is not True:
        raise DeploymentReceiptError("post-deployment release is not verified")
    if audit.get("incident_state") != "NO_INCIDENT_OBSERVED":
        raise DeploymentReceiptError("post-deployment incident state mismatch")
    if audit.get("severity") != "NONE" or audit.get("decision") != "MONITOR":
        raise DeploymentReceiptError("post-deployment classification mismatch")
    _require_sha(audit.get("live_verification_sha256"), "audit live verification")
    _require_sha(audit.get("incident_receipt_sha256"), "audit incident receipt")

    boundaries = receipt.get("claim_boundaries")
    if not isinstance(boundaries, list) or len(boundaries) != 4:
        raise DeploymentReceiptError("claim boundary set mismatch")
    boundary_text = " ".join(boundaries).lower()
    for required in REQUIRED_BOUNDARIES:
        if required.lower() not in boundary_text:
            raise DeploymentReceiptError(f"missing claim boundary: {required}")

    verification = {
        "schema": "lumencore.public_site_exact_deployment_verification.v1",
        "valid": True,
        "source_commit": source_commit,
        "release_file_count": 43,
        "archive_sha256": subject["archive_sha256"],
        "supply_chain_run_id": supply["run_id"],
        "deployment_run_id": deployment["run_id"],
        "audit_run_id": audit["run_id"],
        "live_release_verified": True,
        "incident_state": audit["incident_state"],
        "receipt_sha256": recorded_self_hash,
        "claim_boundary": (
            "This local verifier reconstructs the exact Git subject and checks the "
            "retained first-party receipt. It does not perform a fresh remote signature "
            "lookup or live HTTP audit."
        ),
    }
    verification["verification_sha256"] = sha256_bytes(canonical_bytes(verification))
    return verification


def verify_all_receipts(
    *, root: Path = ROOT, receipt_root: Path | None = None
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    receipt_root = (
        receipt_root.resolve(strict=True)
        if receipt_root is not None
        else root / "evidence" / "public-site-deployments"
    )
    paths = sorted(receipt_root.glob("*/deployment-receipt.json"))
    if not paths:
        raise DeploymentReceiptError("no retained deployment receipts found")

    verified = [verify_receipt(root=root, receipt_path=path) for path in paths]
    source_commits = [item["source_commit"] for item in verified]
    if len(source_commits) != len(set(source_commits)):
        raise DeploymentReceiptError("duplicate retained source commit")

    result = {
        "schema": "lumencore.public_site_exact_deployment_history_verification.v1",
        "valid": True,
        "receipt_count": len(verified),
        "source_commits": source_commits,
        "receipts": verified,
        "claim_boundary": (
            "This local history verifier reconstructs every retained Git subject and "
            "checks each first-party receipt. It does not perform a fresh remote "
            "signature lookup or live HTTP audit."
        ),
    }
    result["verification_sha256"] = sha256_bytes(canonical_bytes(result))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--receipt",
        type=Path,
        help="Verify one receipt; omit to reconstruct and verify the full history.",
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        result = (
            verify_receipt(root=args.root, receipt_path=args.receipt)
            if args.receipt is not None
            else verify_all_receipts(root=args.root)
        )
    except (OSError, DeploymentReceiptError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
