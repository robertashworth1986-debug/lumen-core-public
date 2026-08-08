#!/usr/bin/env python3
"""Build the bounded public-site snapshot from immutable Git blobs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
from typing import Final


ROOT = Path(__file__).resolve().parents[2]
SCHEMA: Final = "lumencore.public_site_release_manifest.v1"
FULL_COMMIT = re.compile(r"[0-9a-fA-F]{40}")
RELEASE_PATHS: Final = (
    "dashboard/operator_home.html",
    "dashboard/opportunity_sprint.html",
    "dashboard/proof_to_pilot.html",
    "dashboard/external_review.html",
    "dashboard/mission_control.html",
    "dashboard/evidence/index_bounded.html",
    "dashboard/robots.txt",
    "dashboard/sitemap.xml",
    "dashboard/site.webmanifest",
    "dashboard/manifest.json",
    "dashboard/assets/lumencore-mark.svg",
    "dashboard/assets/lumencore.css",
    "dashboard/assets/luma_command_fabric.css",
    "dashboard/assets/luma_command_fabric.js",
    "dashboard/assets/luma_institutional_surface.css",
    "dashboard/assets/luma_institutional_surface.js",
    "dashboard/assets/prooflock/bounded_validation_protocol_v1.json",
    "dashboard/assets/prooflock/bounded_validation_protocol_v2.json",
    "dashboard/build_week/prooflock_console/app.js",
    "dashboard/build_week/prooflock_console/bootstrap.js",
    "dashboard/build_week/prooflock_console/index.html",
    "dashboard/build_week/prooflock_console/prooflock_core.js",
    "dashboard/build_week/prooflock_console/prooflock_favicon.svg",
    "dashboard/build_week/prooflock_console/prooflock_lattice.css",
    "dashboard/build_week/prooflock_console/prooflock_lattice.js",
    "dashboard/build_week/prooflock_console/sample_receipt.json",
    "dashboard/build_week/prooflock_console/styles.css",
    "dashboard/build_week/prooflock_console/three.core.min.js",
    "dashboard/build_week/prooflock_console/three.module.min.js",
)


class ReleasePackageError(RuntimeError):
    """Raised when the requested Git snapshot is not a safe release source."""


def archive_name(repo_path: str) -> str:
    path = PurePosixPath(repo_path)
    if not path.parts or path.parts[0] != "dashboard":
        raise ReleasePackageError(f"release path is outside dashboard: {repo_path}")
    relative = PurePosixPath(*path.parts[1:])
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ReleasePackageError(f"unsafe release path: {repo_path}")
    return relative.as_posix()


def _git(repo_root: Path, *args: str) -> bytes:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), *args],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", b"").decode("utf-8", errors="replace").strip()
        suffix = f": {detail}" if detail else ""
        raise ReleasePackageError(f"git {' '.join(args)} failed{suffix}") from exc
    return completed.stdout


def _resolve_commit(repo_root: Path, source_commit: str) -> str:
    if FULL_COMMIT.fullmatch(source_commit) is None:
        raise ReleasePackageError("source commit must be a full 40-character SHA-1")
    resolved = (
        _git(repo_root, "rev-parse", "--verify", f"{source_commit}^{{commit}}")
        .decode("ascii")
        .strip()
        .lower()
    )
    if resolved != source_commit.lower():
        raise ReleasePackageError("source commit did not resolve to the exact pinned commit")
    return resolved


def _read_commit_blob(
    repo_root: Path, source_commit: str, repo_path: str
) -> tuple[str, bytes]:
    tree_output = _git(repo_root, "ls-tree", "-z", source_commit, "--", repo_path)
    entries = [entry for entry in tree_output.split(b"\0") if entry]
    if len(entries) != 1 or b"\t" not in entries[0]:
        raise ReleasePackageError(f"release path is missing or ambiguous: {repo_path}")

    metadata, encoded_path = entries[0].split(b"\t", 1)
    try:
        mode, object_type, blob_oid = metadata.decode("ascii").split()
        actual_path = encoded_path.decode("utf-8")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReleasePackageError(f"invalid Git tree entry for {repo_path}") from exc

    if actual_path != repo_path:
        raise ReleasePackageError(f"Git returned an unexpected release path: {actual_path}")
    if mode != "100644" or object_type != "blob":
        raise ReleasePackageError(
            f"release path must be a non-executable regular Git blob: {repo_path}"
        )
    return blob_oid, _git(repo_root, "cat-file", "blob", blob_oid)


def _sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _write_archive(archive_path: Path, files: list[tuple[str, bytes]]) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=archive_path.parent, prefix=f".{archive_path.name}.", delete=False
    ) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with tarfile.open(temporary_path, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            for name, body in files:
                entry = tarfile.TarInfo(name=name)
                entry.size = len(body)
                entry.mode = 0o644
                entry.uid = 0
                entry.gid = 0
                entry.uname = "root"
                entry.gname = "root"
                entry.mtime = 0
                archive.addfile(entry, io.BytesIO(body))
        os.replace(temporary_path, archive_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _write_manifest(manifest_path: Path, payload: dict[str, object]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="\n",
        dir=manifest_path.parent,
        prefix=f".{manifest_path.name}.",
        delete=False,
    ) as temporary:
        temporary.write(rendered)
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, manifest_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def build_release_package(
    *, repo_root: Path, source_commit: str, archive_path: Path, manifest_path: Path
) -> dict[str, object]:
    repo_root = repo_root.resolve()
    archive_path = archive_path.resolve()
    manifest_path = manifest_path.resolve()
    if archive_path == manifest_path:
        raise ReleasePackageError("archive and manifest paths must differ")

    resolved_commit = _resolve_commit(repo_root, source_commit)
    archive_files: list[tuple[str, bytes]] = []
    manifest_files: list[dict[str, object]] = []
    seen_names: set[str] = set()
    for repo_path in RELEASE_PATHS:
        name = archive_name(repo_path)
        if name in seen_names:
            raise ReleasePackageError(f"duplicate archive path: {name}")
        seen_names.add(name)
        blob_oid, body = _read_commit_blob(repo_root, resolved_commit, repo_path)
        archive_files.append((name, body))
        manifest_files.append(
            {
                "archive_name": name,
                "bytes": len(body),
                "git_blob_oid": blob_oid,
                "install_mode": "0644",
                "repo_path": repo_path,
                "sha256": _sha256(body),
            }
        )

    _write_archive(archive_path, archive_files)
    payload: dict[str, object] = {
        "archive_sha256": _sha256(archive_path.read_bytes()),
        "file_count": len(manifest_files),
        "files": manifest_files,
        "schema": SCHEMA,
        "source_commit": resolved_commit,
        "target_directory": "/opt/lumencore/dashboard",
    }
    _write_manifest(manifest_path, payload)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        payload = build_release_package(
            repo_root=args.repo_root,
            source_commit=args.source_commit,
            archive_path=args.archive,
            manifest_path=args.manifest,
        )
    except ReleasePackageError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
