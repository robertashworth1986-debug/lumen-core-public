#!/usr/bin/env python3
"""Materialize the exact governed public release for the recovery Worker."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile


SOURCE_RELEASE = "1ce7c35975a4011fa844e8b39ccbc950c8c0f398"
EXPECTED_FILE_COUNT = 43
EXPECTED_ARCHIVE_SHA256 = (
    "681c89bb446a83393b52d02d02ea05bb6ccabf63a60d65bdb9efb074c56b3fa9"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    recovery_root = Path(__file__).resolve().parents[1]
    repo_root = recovery_root.parent.resolve()
    site_root = (recovery_root / "site").resolve()
    release_root = (recovery_root / ".release").resolve()

    if site_root.parent != recovery_root or release_root.parent != recovery_root:
        raise RuntimeError("bounded recovery paths resolved outside the recovery root")
    if site_root.is_symlink() or release_root.is_symlink():
        raise RuntimeError("refusing symlinked recovery output paths")

    if site_root.exists():
        shutil.rmtree(site_root)
    if release_root.exists():
        shutil.rmtree(release_root)
    site_root.mkdir(mode=0o700)
    release_root.mkdir(mode=0o700)

    archive_path = release_root / "public-site-release.tar"
    manifest_path = release_root / "public-site-release-manifest.json"
    package_script = repo_root / "code" / "deploy" / "package_public_site_release.py"
    subprocess.run(
        [
            sys.executable,
            str(package_script),
            "--source-commit",
            SOURCE_RELEASE,
            "--archive",
            str(archive_path),
            "--manifest",
            str(manifest_path),
        ],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "lumencore.public_site_release_manifest.v1":
        raise RuntimeError("unexpected release manifest schema")
    if manifest.get("source_commit") != SOURCE_RELEASE:
        raise RuntimeError("release manifest is not bound to the governed source")
    if manifest.get("file_count") != EXPECTED_FILE_COUNT:
        raise RuntimeError("release manifest file count changed")
    if manifest.get("archive_sha256") != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("release archive hash differs from the governed release")
    if sha256_file(archive_path) != EXPECTED_ARCHIVE_SHA256:
        raise RuntimeError("release archive hash does not match the manifest")

    records = manifest.get("files")
    if not isinstance(records, list) or len(records) != EXPECTED_FILE_COUNT:
        raise RuntimeError("release manifest inventory is incomplete")
    expected = {record["archive_name"]: record for record in records}
    if len(expected) != EXPECTED_FILE_COUNT:
        raise RuntimeError("release manifest contains duplicate archive names")

    with tarfile.open(archive_path, mode="r:") as archive:
        members = archive.getmembers()
        if {member.name for member in members} != set(expected):
            raise RuntimeError("release archive membership differs from the manifest")
        for member in members:
            if not member.isfile() or member.name.startswith("/") or ".." in Path(member.name).parts:
                raise RuntimeError(f"unsafe release archive member: {member.name}")
            target = (site_root / member.name).resolve()
            if site_root not in target.parents:
                raise RuntimeError(f"release archive member escapes site root: {member.name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise RuntimeError(f"unable to read release archive member: {member.name}")
            with source, target.open("wb") as output:
                shutil.copyfileobj(source, output)
            os.chmod(target, 0o600)

    for archive_name, record in expected.items():
        target = site_root / archive_name
        if target.stat().st_size != record["bytes"]:
            raise RuntimeError(f"release byte count mismatch: {archive_name}")
        if sha256_file(target) != record["sha256"]:
            raise RuntimeError(f"release hash mismatch: {archive_name}")

    receipt = {
        "status": "ok",
        "source_release": SOURCE_RELEASE,
        "file_count": EXPECTED_FILE_COUNT,
        "archive_sha256": manifest["archive_sha256"],
        "site_directory": str(site_root),
    }
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
