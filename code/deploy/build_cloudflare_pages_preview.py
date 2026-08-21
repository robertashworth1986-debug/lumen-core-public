#!/usr/bin/env python3
"""Build a non-deploying Cloudflare Pages preview from immutable Git blobs."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import sys
import tempfile
from typing import Final

import package_public_site_release as release


ROOT = Path(__file__).resolve().parents[2]
SCHEMA: Final = "lumencore.cloudflare_pages_preview_manifest.v1"
ALIASES: Final = {
    "index.html": "operator_home.html",
    "evidence/index.html": "evidence/index_bounded.html",
}


class PagesPreviewError(RuntimeError):
    """Raised when a Pages preview cannot be built safely."""


def _safe_relative_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or ".." in path.parts:
        raise PagesPreviewError(f"unsafe preview path: {value}")
    return path


def _write_file(root: Path, relative_name: str, body: bytes) -> None:
    relative = _safe_relative_path(relative_name)
    target = root.joinpath(*relative.parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    target.chmod(0o644)


def build_pages_preview(
    *, repo_root: Path, source_commit: str, output_dir: Path, manifest_path: Path
) -> dict[str, object]:
    """Materialize the bounded public site without reading worktree file bytes."""

    repo_root = repo_root.resolve()
    output_dir = output_dir.resolve()
    manifest_path = manifest_path.resolve()
    if output_dir.exists():
        raise PagesPreviewError(f"output directory already exists: {output_dir}")
    if manifest_path.exists():
        raise PagesPreviewError(f"manifest already exists: {manifest_path}")
    if output_dir == manifest_path or output_dir in manifest_path.parents:
        raise PagesPreviewError("manifest must be outside the preview directory")

    try:
        resolved_commit = release._resolve_commit(repo_root, source_commit)
    except release.ReleasePackageError as exc:
        raise PagesPreviewError(str(exc)) from exc

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    temporary_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}.", dir=output_dir.parent)
    )
    files: list[dict[str, object]] = []
    bodies: dict[str, bytes] = {}
    try:
        for repo_path in release.RELEASE_PATHS:
            archive_name = release.archive_name(repo_path)
            try:
                blob_oid, body = release._read_commit_blob(
                    repo_root, resolved_commit, repo_path
                )
            except release.ReleasePackageError as exc:
                raise PagesPreviewError(str(exc)) from exc
            _write_file(temporary_dir, archive_name, body)
            bodies[archive_name] = body
            files.append(
                {
                    "bytes": len(body),
                    "git_blob_oid": blob_oid,
                    "path": archive_name,
                    "repo_path": repo_path,
                    "sha256": release._sha256(body),
                    "source": "git_blob",
                }
            )

        aliases: list[dict[str, object]] = []
        for alias_name, source_name in ALIASES.items():
            if alias_name in bodies or source_name not in bodies:
                raise PagesPreviewError(f"invalid preview alias: {alias_name}")
            body = bodies[source_name]
            _write_file(temporary_dir, alias_name, body)
            aliases.append(
                {
                    "bytes": len(body),
                    "path": alias_name,
                    "sha256": release._sha256(body),
                    "source_path": source_name,
                }
            )

        os.replace(temporary_dir, output_dir)
        payload: dict[str, object] = {
            "alias_count": len(aliases),
            "aliases": aliases,
            "deployment_state": "NOT_DEPLOYED",
            "file_count": len(files) + len(aliases),
            "files": files,
            "schema": SCHEMA,
            "source_commit": resolved_commit,
            "source_file_count": len(files),
        }
        release._write_manifest(manifest_path, payload)
        return payload
    except Exception:
        shutil.rmtree(temporary_dir, ignore_errors=True)
        if output_dir.exists():
            shutil.rmtree(output_dir, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        payload = build_pages_preview(
            repo_root=args.repo_root,
            source_commit=args.source_commit,
            output_dir=args.output_dir,
            manifest_path=args.manifest,
        )
    except PagesPreviewError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
