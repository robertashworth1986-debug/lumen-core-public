#!/usr/bin/env python3
"""Canonical constants and structural validation for the exact public-site release."""

from __future__ import annotations

from pathlib import PurePosixPath
import re
from typing import Final


SCHEMA: Final = "lumencore.public_site_release_manifest.v1"
TARGET_DIRECTORY: Final = "/opt/lumencore/dashboard"
SHA1 = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
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
)


class PublicSiteReleaseContractError(ValueError):
    """Raised when a manifest is outside the canonical exact-release contract."""


def archive_name(repo_path: str) -> str:
    path = PurePosixPath(repo_path)
    if not path.parts or path.parts[0] != "dashboard":
        raise PublicSiteReleaseContractError(
            f"release path is outside dashboard: {repo_path}"
        )
    relative = PurePosixPath(*path.parts[1:])
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise PublicSiteReleaseContractError(f"unsafe release path: {repo_path}")
    return relative.as_posix()


RELEASE_ARCHIVE_NAMES: Final = tuple(archive_name(path) for path in RELEASE_PATHS)


def validate_release_manifest(
    payload: dict[str, object], *, source_commit: str
) -> dict[str, object]:
    manifest_keys = {
        "archive_sha256",
        "file_count",
        "files",
        "schema",
        "source_commit",
        "target_directory",
    }
    row_keys = {
        "archive_name",
        "bytes",
        "git_blob_oid",
        "install_mode",
        "repo_path",
        "sha256",
    }
    if set(payload) != manifest_keys or payload.get("schema") != SCHEMA:
        raise PublicSiteReleaseContractError("manifest fields or schema are invalid")
    if payload.get("source_commit") != source_commit:
        raise PublicSiteReleaseContractError("manifest source commit is invalid")
    if payload.get("target_directory") != TARGET_DIRECTORY:
        raise PublicSiteReleaseContractError("manifest target directory is invalid")
    if not isinstance(payload.get("archive_sha256"), str) or SHA256.fullmatch(
        payload["archive_sha256"]
    ) is None:
        raise PublicSiteReleaseContractError("manifest archive hash is invalid")
    if type(payload.get("file_count")) is not int or payload["file_count"] != len(
        RELEASE_PATHS
    ):
        raise PublicSiteReleaseContractError("manifest file count is invalid")
    rows = payload.get("files")
    if not isinstance(rows, list) or len(rows) != len(RELEASE_PATHS):
        raise PublicSiteReleaseContractError("manifest file rows are incomplete")
    for row, repo_path, expected_name in zip(
        rows, RELEASE_PATHS, RELEASE_ARCHIVE_NAMES, strict=True
    ):
        if not isinstance(row, dict) or set(row) != row_keys:
            raise PublicSiteReleaseContractError("manifest row fields are invalid")
        if row.get("archive_name") != expected_name:
            raise PublicSiteReleaseContractError("manifest file allowlist or order is invalid")
        if row.get("repo_path") != repo_path or row.get("install_mode") != "0644":
            raise PublicSiteReleaseContractError("manifest row path or mode is invalid")
        if type(row.get("bytes")) is not int or row["bytes"] < 0:
            raise PublicSiteReleaseContractError("manifest row byte count is invalid")
        if not isinstance(row.get("git_blob_oid"), str) or SHA1.fullmatch(
            row["git_blob_oid"]
        ) is None:
            raise PublicSiteReleaseContractError("manifest row Git blob ID is invalid")
        if not isinstance(row.get("sha256"), str) or SHA256.fullmatch(
            row["sha256"]
        ) is None:
            raise PublicSiteReleaseContractError("manifest row SHA-256 is invalid")
    return payload
