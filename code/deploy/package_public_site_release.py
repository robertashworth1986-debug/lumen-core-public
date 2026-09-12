#!/usr/bin/env python3
"""Build the bounded public-site snapshot from immutable Git blobs."""

from __future__ import annotations

import argparse
import ast
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
    "dashboard/reviewer_docket.json",
    "dashboard/mission_control.html",
    "dashboard/quant_lab.html",
    "dashboard/grants.html",
    "dashboard/kraken_execution_dashboard.html",
    "dashboard/forecast.html",
    "dashboard/anomalies.html",
    "dashboard/explain.html",
    "dashboard/lab.html",
    "dashboard/evidence/index_bounded.html",
    "dashboard/robots.txt",
    "dashboard/sitemap.xml",
    "dashboard/site.webmanifest",
    "dashboard/manifest.json",
    "dashboard/assets/lumaarc_arc_seal_v1.png",
    "dashboard/assets/lumencore.css",
    "dashboard/assets/lumencore.js",
    "dashboard/assets/luma_command_fabric.css",
    "dashboard/assets/luma_command_fabric.js",
    "dashboard/assets/luma_institutional_surface.css",
    "dashboard/assets/luma_institutional_surface.js",
    "dashboard/assets/vendor/three.min.js",
    "dashboard/js/alpha_globe_3d.js",
    "dashboard/js/cinematic_telemetry_layer.js",
    "dashboard/js/luma_design_system.js",
    "dashboard/js/luma_path_resolver.js",
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
    "dashboard/cohort/index.html",
    "dashboard/cohort/studio.css",
    "dashboard/cohort/studio.js",
    "dashboard/cohort/core.js",
    "dashboard/cohort/mark.svg",
    "dashboard/cohort/catalog.json",
    "dashboard/cohort/downloads/manifest.json",
    "dashboard/cohort/downloads/aa-window-washing.zip",
    "dashboard/cohort/downloads/advia-solutions.zip",
    "dashboard/cohort/downloads/aegiskeep.zip",
    "dashboard/cohort/downloads/aligned-strategy-partners.zip",
    "dashboard/cohort/downloads/amara-bitters.zip",
    "dashboard/cohort/downloads/autarko.zip",
    "dashboard/cohort/downloads/bagel.zip",
    "dashboard/cohort/downloads/buyunrepped.zip",
    "dashboard/cohort/downloads/c3-measures-registry.zip",
    "dashboard/cohort/downloads/claridense.zip",
    "dashboard/cohort/downloads/clark-wester-corporation.zip",
    "dashboard/cohort/downloads/cog-learning-inc.zip",
    "dashboard/cohort/downloads/compounds-dev-inc.zip",
    "dashboard/cohort/downloads/csh-hub.zip",
    "dashboard/cohort/downloads/decre.zip",
    "dashboard/cohort/downloads/double-r-strategies-and-consulting.zip",
    "dashboard/cohort/downloads/dust-to-dust-llc.zip",
    "dashboard/cohort/downloads/encompass-financial-services-inc.zip",
    "dashboard/cohort/downloads/excalis.zip",
    "dashboard/cohort/downloads/firma-q-gaas.zip",
    "dashboard/cohort/downloads/fizzy-mixology.zip",
    "dashboard/cohort/downloads/fox-force.zip",
    "dashboard/cohort/downloads/glow-up-sports.zip",
    "dashboard/cohort/downloads/govfetchr-ai.zip",
    "dashboard/cohort/downloads/gutless-topical-supplements.zip",
    "dashboard/cohort/downloads/happy-overall.zip",
    "dashboard/cohort/downloads/holastra.zip",
    "dashboard/cohort/downloads/hopeconnect-health.zip",
    "dashboard/cohort/downloads/hot-mess-inc.zip",
    "dashboard/cohort/downloads/incourage-enterprises.zip",
    "dashboard/cohort/downloads/itty-bitty-city.zip",
    "dashboard/cohort/downloads/learnkairo.zip",
    "dashboard/cohort/downloads/limer.zip",
    "dashboard/cohort/downloads/lode-labs.zip",
    "dashboard/cohort/downloads/lumencore.zip",
    "dashboard/cohort/downloads/maaven.zip",
    "dashboard/cohort/downloads/margaret-ray-interiors.zip",
    "dashboard/cohort/downloads/moneybot.zip",
    "dashboard/cohort/downloads/music-utility-network.zip",
    "dashboard/cohort/downloads/obviecare.zip",
    "dashboard/cohort/downloads/paragon-parcels.zip",
    "dashboard/cohort/downloads/petrarch-strategy.zip",
    "dashboard/cohort/downloads/proworx.zip",
    "dashboard/cohort/downloads/prsnt.zip",
    "dashboard/cohort/downloads/ptln.zip",
    "dashboard/cohort/downloads/public-speaking-pros.zip",
    "dashboard/cohort/downloads/recovery-matters.zip",
    "dashboard/cohort/downloads/remedy-haus.zip",
    "dashboard/cohort/downloads/renuiam.zip",
    "dashboard/cohort/downloads/scoreboardz-inc.zip",
    "dashboard/cohort/downloads/smr-pet-services.zip",
    "dashboard/cohort/downloads/specinate.zip",
    "dashboard/cohort/downloads/spilburg-solutions.zip",
    "dashboard/cohort/downloads/starra-llc.zip",
    "dashboard/cohort/downloads/tarapy-inc.zip",
    "dashboard/cohort/downloads/the-37208.zip",
    "dashboard/cohort/downloads/the-designery-nashville-south.zip",
    "dashboard/cohort/downloads/the-nash-philanthropist.zip",
    "dashboard/cohort/downloads/the-tennessee-hospitality-group.zip",
    "dashboard/cohort/downloads/threadwell-studio.zip",
    "dashboard/cohort/downloads/true-vena.zip",
    "dashboard/cohort/downloads/ultra-beauty-supply-skin-and-nails.zip",
    "dashboard/cohort/downloads/unapologetically-me.zip",
    "dashboard/cohort/downloads/validflo.zip",
    "dashboard/cohort/downloads/volume-one-nashville.zip",
    "dashboard/cohort/downloads/voxring.zip",
    "dashboard/cohort/downloads/wednesday.zip",
    "dashboard/cohort/downloads/xi.zip",
    "dashboard/cohort/downloads/yoamigo.zip",
    "dashboard/cohort/directory.html",
    "dashboard/cohort/members/aa-window-washing.html",
    "dashboard/cohort/members/advia-solutions.html",
    "dashboard/cohort/members/aegiskeep.html",
    "dashboard/cohort/members/aligned-strategy-partners.html",
    "dashboard/cohort/members/amara-bitters.html",
    "dashboard/cohort/members/autarko.html",
    "dashboard/cohort/members/bagel.html",
    "dashboard/cohort/members/buyunrepped.html",
    "dashboard/cohort/members/c3-measures-registry.html",
    "dashboard/cohort/members/claridense.html",
    "dashboard/cohort/members/clark-wester-corporation.html",
    "dashboard/cohort/members/cog-learning-inc.html",
    "dashboard/cohort/members/compounds-dev-inc.html",
    "dashboard/cohort/members/csh-hub.html",
    "dashboard/cohort/members/decre.html",
    "dashboard/cohort/members/double-r-strategies-and-consulting.html",
    "dashboard/cohort/members/dust-to-dust-llc.html",
    "dashboard/cohort/members/encompass-financial-services-inc.html",
    "dashboard/cohort/members/excalis.html",
    "dashboard/cohort/members/firma-q-gaas.html",
    "dashboard/cohort/members/fizzy-mixology.html",
    "dashboard/cohort/members/fox-force.html",
    "dashboard/cohort/members/glow-up-sports.html",
    "dashboard/cohort/members/govfetchr-ai.html",
    "dashboard/cohort/members/gutless-topical-supplements.html",
    "dashboard/cohort/members/happy-overall.html",
    "dashboard/cohort/members/holastra.html",
    "dashboard/cohort/members/hopeconnect-health.html",
    "dashboard/cohort/members/hot-mess-inc.html",
    "dashboard/cohort/members/incourage-enterprises.html",
    "dashboard/cohort/members/itty-bitty-city.html",
    "dashboard/cohort/members/learnkairo.html",
    "dashboard/cohort/members/limer.html",
    "dashboard/cohort/members/lode-labs.html",
    "dashboard/cohort/members/lumencore.html",
    "dashboard/cohort/members/maaven.html",
    "dashboard/cohort/members/margaret-ray-interiors.html",
    "dashboard/cohort/members/moneybot.html",
    "dashboard/cohort/members/music-utility-network.html",
    "dashboard/cohort/members/obviecare.html",
    "dashboard/cohort/members/paragon-parcels.html",
    "dashboard/cohort/members/petrarch-strategy.html",
    "dashboard/cohort/members/proworx.html",
    "dashboard/cohort/members/prsnt.html",
    "dashboard/cohort/members/ptln.html",
    "dashboard/cohort/members/public-speaking-pros.html",
    "dashboard/cohort/members/recovery-matters.html",
    "dashboard/cohort/members/remedy-haus.html",
    "dashboard/cohort/members/renuiam.html",
    "dashboard/cohort/members/scoreboardz-inc.html",
    "dashboard/cohort/members/smr-pet-services.html",
    "dashboard/cohort/members/specinate.html",
    "dashboard/cohort/members/spilburg-solutions.html",
    "dashboard/cohort/members/starra-llc.html",
    "dashboard/cohort/members/tarapy-inc.html",
    "dashboard/cohort/members/the-37208.html",
    "dashboard/cohort/members/the-designery-nashville-south.html",
    "dashboard/cohort/members/the-nash-philanthropist.html",
    "dashboard/cohort/members/the-tennessee-hospitality-group.html",
    "dashboard/cohort/members/threadwell-studio.html",
    "dashboard/cohort/members/true-vena.html",
    "dashboard/cohort/members/ultra-beauty-supply-skin-and-nails.html",
    "dashboard/cohort/members/unapologetically-me.html",
    "dashboard/cohort/members/validflo.html",
    "dashboard/cohort/members/volume-one-nashville.html",
    "dashboard/cohort/members/voxring.html",
    "dashboard/cohort/members/wednesday.html",
    "dashboard/cohort/members/xi.html",
    "dashboard/cohort/members/yoamigo.html",
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


def release_paths_at_commit(repo_root: Path, source_commit: str) -> tuple[str, ...]:
    """Read a pinned literal allowlist as data; never execute historical code."""
    source_commit = _resolve_commit(repo_root, source_commit)
    _oid, body = _read_commit_blob(repo_root, source_commit, "code/deploy/package_public_site_release.py")
    tree = ast.parse(body.decode("utf-8-sig"))
    definitions = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "RELEASE_PATHS":
            definitions.append(node.value)
        elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "RELEASE_PATHS" for t in node.targets):
            definitions.append(node.value)
    if len(definitions) != 1:
        raise ReleasePackageError("pinned release must contain one literal allowlist")
    try:
        paths = ast.literal_eval(definitions[0])
    except (ValueError, TypeError) as exc:
        raise ReleasePackageError("pinned allowlist must be literal data") from exc
    if not isinstance(paths, tuple) or not 1 <= len(paths) <= 1000 or any(not isinstance(p, str) for p in paths) or len(set(paths)) != len(paths):
        raise ReleasePackageError("invalid pinned release membership")
    for path in paths:
        if "\\" in path or PurePosixPath(path).as_posix() != path:
            raise ReleasePackageError("noncanonical pinned release path")
        archive_name(path)
    return paths


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
    *, repo_root: Path, source_commit: str, archive_path: Path, manifest_path: Path,
    release_paths: tuple[str, ...] | None = None,
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
    for repo_path in RELEASE_PATHS if release_paths is None else release_paths:
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
