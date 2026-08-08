#!/usr/bin/env python3
"""Build a deterministic CycloneDX inventory for the exact public-site release."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
import tempfile
from typing import Any, Final
import uuid


ROOT = Path(__file__).resolve().parents[2]
PACKAGER_PATH = ROOT / "code" / "deploy" / "package_public_site_release.py"
RELEASE_MANIFEST_SCHEMA: Final = "lumencore.public_site_release_manifest.v1"
RECEIPT_SCHEMA: Final = "lumencore.public_site_supply_chain_receipt.v1"
CYCLONEDX_SPEC_VERSION: Final = "1.6"
REPOSITORY: Final = "robertashworth1986-debug/lumen-core-public"
REPOSITORY_URL: Final = f"https://github.com/{REPOSITORY}"
TARGET_DIRECTORY: Final = "/opt/lumencore/dashboard"
FULL_SHA1 = re.compile(r"[0-9a-f]{40}")
FULL_SHA256 = re.compile(r"[0-9a-f]{64}")
MANIFEST_FIELDS = {
    "archive_sha256",
    "file_count",
    "files",
    "schema",
    "source_commit",
    "target_directory",
}
MANIFEST_FILE_FIELDS = {
    "archive_name",
    "bytes",
    "git_blob_oid",
    "install_mode",
    "repo_path",
    "sha256",
}
CLAIM_BOUNDARIES: Final = (
    "Exact release-file inventory only; not a complete VPS, operating-system, gateway, container, private-stack, or organization-wide SBOM.",
    "First-party deterministic receipt only; the receipt is not a cryptographic signature or independent attestation.",
    "A GitHub-hosted main-branch workflow may add Sigstore-signed provenance and SBOM attestations, but no SLSA level, certification, security assurance, or live-deployment parity is claimed.",
)


class SupplyChainBuildError(ValueError):
    """Raised when an exact-release supply-chain artifact cannot be built safely."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SupplyChainBuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise SupplyChainBuildError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 2_000_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise SupplyChainBuildError(f"JSON input exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except UnicodeDecodeError as exc:
        raise SupplyChainBuildError("JSON input is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise SupplyChainBuildError("JSON input must be an object")
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _load_packager(repo_root: Path):
    path = repo_root / "code" / "deploy" / "package_public_site_release.py"
    spec = importlib.util.spec_from_file_location("public_site_release_packager", path)
    if spec is None or spec.loader is None:
        raise SupplyChainBuildError("cannot load the canonical public-site packager")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _safe_archive_name(value: Any) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or "\\" in value:
        raise SupplyChainBuildError("manifest archive_name is not canonical")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or path.as_posix() != value:
        raise SupplyChainBuildError(f"unsafe manifest archive_name: {value}")
    return value


def validate_release_inputs(
    *, repo_root: Path, archive_path: Path, manifest_path: Path, source_commit: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if FULL_SHA1.fullmatch(source_commit) is None:
        raise SupplyChainBuildError("source commit must be a full lowercase SHA-1")
    for label, path in (("archive", archive_path), ("manifest", manifest_path)):
        if not path.is_file() or path.is_symlink():
            raise SupplyChainBuildError(f"{label} must be a regular non-symlink file")

    manifest = read_json(manifest_path)
    if set(manifest) != MANIFEST_FIELDS:
        raise SupplyChainBuildError("release manifest fields do not match the strict schema")
    if manifest["schema"] != RELEASE_MANIFEST_SCHEMA:
        raise SupplyChainBuildError("release manifest schema mismatch")
    if manifest["source_commit"] != source_commit:
        raise SupplyChainBuildError("release manifest source commit mismatch")
    if manifest["target_directory"] != TARGET_DIRECTORY:
        raise SupplyChainBuildError("release manifest target directory mismatch")
    archive_sha256 = sha256_file(archive_path)
    if manifest["archive_sha256"] != archive_sha256:
        raise SupplyChainBuildError("release archive hash mismatch")

    packager = _load_packager(repo_root)
    expected_rows = [
        (repo_path, packager.archive_name(repo_path))
        for repo_path in packager.RELEASE_PATHS
    ]
    commit_files: dict[str, bytes] = {}
    rows = manifest["files"]
    if (
        not isinstance(rows, list)
        or manifest["file_count"] != len(expected_rows)
        or len(rows) != len(expected_rows)
    ):
        raise SupplyChainBuildError("release manifest file count mismatch")

    normalized: list[dict[str, Any]] = []
    seen_names: set[str] = set()
    for index, (row, expected) in enumerate(zip(rows, expected_rows, strict=True)):
        if not isinstance(row, dict) or set(row) != MANIFEST_FILE_FIELDS:
            raise SupplyChainBuildError(f"release manifest file row {index} fields mismatch")
        repo_path, archive_name = expected
        name = _safe_archive_name(row["archive_name"])
        if name in seen_names:
            raise SupplyChainBuildError(f"duplicate release archive name: {name}")
        seen_names.add(name)
        if name != archive_name or row["repo_path"] != repo_path:
            raise SupplyChainBuildError(f"release path order or identity mismatch: {name}")
        if row["install_mode"] != "0644":
            raise SupplyChainBuildError(f"release install mode mismatch: {name}")
        if not isinstance(row["bytes"], int) or isinstance(row["bytes"], bool) or row["bytes"] < 0:
            raise SupplyChainBuildError(f"release byte count is invalid: {name}")
        if FULL_SHA1.fullmatch(str(row["git_blob_oid"])) is None:
            raise SupplyChainBuildError(f"release Git blob identity is invalid: {name}")
        if FULL_SHA256.fullmatch(str(row["sha256"])) is None:
            raise SupplyChainBuildError(f"release SHA-256 is invalid: {name}")
        try:
            expected_blob_oid, expected_body = packager._read_commit_blob(
                repo_root, source_commit, repo_path
            )
        except packager.ReleasePackageError as exc:
            raise SupplyChainBuildError(
                f"release path cannot be resolved from source commit: {repo_path}"
            ) from exc
        if row["git_blob_oid"] != expected_blob_oid:
            raise SupplyChainBuildError(
                f"release Git blob identity does not match source commit: {name}"
            )
        if row["bytes"] != len(expected_body) or row["sha256"] != sha256_bytes(
            expected_body
        ):
            raise SupplyChainBuildError(
                f"release manifest content does not match source commit: {name}"
            )
        commit_files[name] = expected_body
        normalized.append(dict(row))

    archive_files: list[tuple[str, bytes]] = []
    try:
        with tarfile.open(archive_path, mode="r:") as archive:
            members = archive.getmembers()
            if [member.name for member in members] != [row["archive_name"] for row in normalized]:
                raise SupplyChainBuildError("release archive member order or identity mismatch")
            for member, row in zip(members, normalized, strict=True):
                if not member.isfile() or member.mode & 0o777 != 0o644:
                    raise SupplyChainBuildError(
                        f"release archive member is not a regular 0644 file: {member.name}"
                    )
                if (
                    member.uid != 0
                    or member.gid != 0
                    or member.uname != "root"
                    or member.gname != "root"
                    or member.mtime != 0
                ):
                    raise SupplyChainBuildError(
                        f"release archive metadata is not deterministic: {member.name}"
                    )
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise SupplyChainBuildError(
                        f"release archive member cannot be read: {member.name}"
                    )
                body = extracted.read()
                if len(body) != row["bytes"] or sha256_bytes(body) != row["sha256"]:
                    raise SupplyChainBuildError(
                        f"release archive content does not match manifest: {member.name}"
                    )
                if body != commit_files[member.name]:
                    raise SupplyChainBuildError(
                        f"release archive content does not match source commit: {member.name}"
                    )
                archive_files.append((member.name, body))
    except (tarfile.TarError, EOFError) as exc:
        raise SupplyChainBuildError("release archive is not a valid deterministic tar") from exc

    canonical_archive = io.BytesIO()
    with tarfile.open(fileobj=canonical_archive, mode="w", format=tarfile.USTAR_FORMAT) as rebuilt:
        for name, body in archive_files:
            entry = tarfile.TarInfo(name=name)
            entry.size = len(body)
            entry.mode = 0o644
            entry.uid = 0
            entry.gid = 0
            entry.uname = "root"
            entry.gname = "root"
            entry.mtime = 0
            rebuilt.addfile(entry, io.BytesIO(body))
    if archive_path.read_bytes() != canonical_archive.getvalue():
        raise SupplyChainBuildError("release archive bytes are not the canonical deterministic tar")
    return manifest, normalized


def _component_ref(source_commit: str, archive_name: str) -> str:
    encoded = archive_name.replace("/", "%2F")
    return f"pkg:generic/lumencore-public-site-file@{source_commit}?path={encoded}"


def build_sbom(
    *, manifest: dict[str, Any], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    source_commit = manifest["source_commit"]
    archive_sha256 = manifest["archive_sha256"]
    root_ref = f"pkg:generic/lumencore-public-site@{source_commit}"
    component_refs = [_component_ref(source_commit, row["archive_name"]) for row in rows]
    serial_seed = f"{REPOSITORY}:{source_commit}:{archive_sha256}"
    serial = uuid.uuid5(uuid.NAMESPACE_URL, serial_seed)
    components = []
    for row, component_ref in zip(rows, component_refs, strict=True):
        components.append(
            {
                "type": "file",
                "bom-ref": component_ref,
                "name": row["archive_name"],
                "version": source_commit,
                "hashes": [{"alg": "SHA-256", "content": row["sha256"]}],
                "properties": [
                    {"name": "lumencore:repo_path", "value": row["repo_path"]},
                    {"name": "lumencore:git_blob_oid", "value": row["git_blob_oid"]},
                    {"name": "lumencore:install_mode", "value": row["install_mode"]},
                    {"name": "lumencore:bytes", "value": str(row["bytes"])},
                ],
            }
        )
    return {
        "bomFormat": "CycloneDX",
        "specVersion": CYCLONEDX_SPEC_VERSION,
        "serialNumber": f"urn:uuid:{serial}",
        "version": 1,
        "metadata": {
            "component": {
                "type": "application",
                "bom-ref": root_ref,
                "group": "ai.lumen-core",
                "name": "lumencore-public-site-exact-release",
                "version": source_commit,
                "purl": root_ref,
                "hashes": [{"alg": "SHA-256", "content": archive_sha256}],
                "externalReferences": [
                    {
                        "type": "vcs",
                        "url": f"{REPOSITORY_URL}/tree/{source_commit}",
                    }
                ],
                "properties": [
                    {"name": "lumencore:scope", "value": "exact_public_release_allowlist"},
                    {"name": "lumencore:target_directory", "value": TARGET_DIRECTORY},
                    {"name": "lumencore:release_file_count", "value": str(len(rows))},
                    {"name": "lumencore:live_deployment_verified", "value": "false"},
                    {"name": "lumencore:slsa_level_claimed", "value": "none"},
                ],
            }
        },
        "components": components,
        "dependencies": [
            {"ref": root_ref, "dependsOn": component_refs},
            *({"ref": component_ref, "dependsOn": []} for component_ref in component_refs),
        ],
    }


def build_receipt(
    *,
    archive_path: Path,
    manifest_path: Path,
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    sbom: dict[str, Any],
) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "repository": REPOSITORY,
        "source_commit": manifest["source_commit"],
        "subject": {
            "name": "public-site-release.tar",
            "bytes": archive_path.stat().st_size,
            "sha256": manifest["archive_sha256"],
        },
        "release_manifest": {
            "name": "public-site-release-manifest.json",
            "bytes": manifest_path.stat().st_size,
            "sha256": sha256_file(manifest_path),
            "schema": manifest["schema"],
        },
        "sbom": {
            "name": "public-site-release.cdx.json",
            "bom_format": sbom["bomFormat"],
            "spec_version": sbom["specVersion"],
            "canonical_sha256": sha256_bytes(canonical_bytes(sbom)),
            "release_file_component_count": len(sbom["components"]),
        },
        "coverage": {
            "expected_release_file_count": manifest["file_count"],
            "inventoried_release_file_count": len(rows),
            "exact_release_file_coverage_ratio": 1.0,
            "excluded_runtime_layers": [
                "VPS operating system and installed packages",
                "reverse proxy and gateway runtime",
                "private services, data, credentials, and logs",
                "external SaaS and network infrastructure",
            ],
        },
        "claim_boundaries": list(CLAIM_BOUNDARIES),
        "signed_attestation_state": "NOT_CREATED_BY_THIS_LOCAL_BUILDER",
        "production_decision": "HOLD_UNTIL_EXPLICIT_DEPLOYMENT_AND_EXACT_LIVE_VERIFICATION",
    }
    receipt["receipt_sha256"] = sha256_bytes(canonical_bytes(receipt))
    return receipt


def build_supply_chain(
    *,
    repo_root: Path,
    archive_path: Path,
    manifest_path: Path,
    source_commit: str,
    sbom_path: Path,
    receipt_path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    resolved = [
        archive_path.resolve(),
        manifest_path.resolve(),
        sbom_path.resolve(),
        receipt_path.resolve(),
    ]
    if len(resolved) != len(set(resolved)):
        raise SupplyChainBuildError("archive, manifest, SBOM, and receipt paths must differ")
    if sbom_path.is_symlink() or receipt_path.is_symlink():
        raise SupplyChainBuildError("output paths cannot be symlinks")
    manifest, rows = validate_release_inputs(
        repo_root=repo_root,
        archive_path=archive_path,
        manifest_path=manifest_path,
        source_commit=source_commit,
    )
    sbom = build_sbom(manifest=manifest, rows=rows)
    receipt = build_receipt(
        archive_path=archive_path,
        manifest_path=manifest_path,
        manifest=manifest,
        rows=rows,
        sbom=sbom,
    )
    _write_json(sbom_path, sbom)
    _write_json(receipt_path, receipt)
    return sbom, receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    try:
        _sbom, receipt = build_supply_chain(
            repo_root=args.repo_root.resolve(),
            archive_path=args.archive.resolve(),
            manifest_path=args.manifest.resolve(),
            source_commit=args.source_commit,
            sbom_path=args.sbom.resolve(),
            receipt_path=args.receipt.resolve(),
        )
    except (OSError, SupplyChainBuildError, json.JSONDecodeError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
