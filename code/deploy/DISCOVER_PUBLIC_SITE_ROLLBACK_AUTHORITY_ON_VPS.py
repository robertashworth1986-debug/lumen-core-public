#!/usr/bin/env python3
"""Discover one exact completed public-site apply authority after ambiguous transport."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys


SCHEMA = "lumencore.public_site_same_run_rollback_authority.v1"
REPOSITORY = "robertashworth1986-debug/lumen-core-public"
WORKFLOW = ".github/workflows/deploy-public-site-release.yml"
AUTHORITY_SCOPE = "FAILED_EXTERNAL_LIVE_GATE_COMPENSATION_IN_SAME_WORKFLOW_RUN_ONLY"
APPROVAL = "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT"
TARGET = "/opt/lumencore/dashboard"
PRODUCTION_ROLLBACK_BASE = Path("/opt/lumencore/rollbacks/public-site")
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
CAPTURE_NAME = re.compile(r"[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}")
UTC = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
AUTHORITY_KEYS = {
    "authority_scope",
    "created_at_utc",
    "deployment_approval",
    "directory_state_sha256",
    "post_deploy_sha256",
    "pre_deploy_sha256",
    "python_version",
    "receipt_sha256",
    "release_manifest_sha256",
    "repository",
    "rollback_capability_sha256",
    "rollback_capture_id",
    "run_attempt",
    "run_id",
    "schema",
    "source_commit",
    "target_directory",
    "workflow",
}


class DiscoveryError(ValueError):
    """Raised when exact remote apply authority cannot be established."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise DiscoveryError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise DiscoveryError(f"non-finite JSON value: {value}")


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _file_hash(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise DiscoveryError(f"cannot hash authority component: {path.name}") from exc


def _validate_state_file(path: Path, euid: int) -> None:
    try:
        identity = path.lstat()
    except OSError as exc:
        raise DiscoveryError(f"authority state file is unavailable: {path.name}") from exc
    if (
        not stat.S_ISREG(identity.st_mode)
        or identity.st_uid != euid
        or stat.S_IMODE(identity.st_mode) != 0o600
        or identity.st_nlink != 1
    ):
        raise DiscoveryError(f"authority state file identity is invalid: {path.name}")


def _load_authority(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(
            path.read_text(encoding="ascii"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise DiscoveryError(f"authority JSON is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise DiscoveryError("authority JSON is not an object")
    return payload


def discover(
    *,
    rollback_base: Path,
    source_commit: str,
    run_id: int,
    run_attempt: int,
    capability_sha256: str,
) -> tuple[Path, dict[str, object]]:
    if FULL_COMMIT.fullmatch(source_commit) is None:
        raise DiscoveryError("source commit must be a full lowercase SHA-1")
    if run_id <= 0 or run_attempt <= 0:
        raise DiscoveryError("run ID and attempt must be positive")
    if SHA256.fullmatch(capability_sha256) is None:
        raise DiscoveryError("capability digest is invalid")
    requested_base = rollback_base.absolute()
    rollback_base = rollback_base.resolve(strict=True)
    if rollback_base != requested_base:
        raise DiscoveryError("rollback base cannot traverse a symlink")
    base_identity = rollback_base.lstat()
    euid = os.geteuid()
    if (
        not stat.S_ISDIR(base_identity.st_mode)
        or base_identity.st_uid != euid
        or stat.S_IMODE(base_identity.st_mode) != 0o750
    ):
        raise DiscoveryError("rollback base identity is invalid")
    matches: list[tuple[Path, dict[str, object]]] = []
    for candidate in rollback_base.iterdir():
        if not CAPTURE_NAME.fullmatch(candidate.name) or not candidate.name.endswith(
            f"-{source_commit[:12]}"
        ):
            continue
        try:
            candidate_identity = candidate.lstat()
            if (
                not stat.S_ISDIR(candidate_identity.st_mode)
                or candidate_identity.st_uid != euid
                or stat.S_IMODE(candidate_identity.st_mode) != 0o700
            ):
                continue
            authority_path = candidate / "rollback-authority.json"
            _validate_state_file(authority_path, euid)
            authority = _load_authority(authority_path)
            if set(authority) != AUTHORITY_KEYS or authority.get("schema") != SCHEMA:
                continue
            recorded_hash = authority.get("receipt_sha256")
            if not isinstance(recorded_hash, str) or SHA256.fullmatch(recorded_hash) is None:
                continue
            without_hash = dict(authority)
            del without_hash["receipt_sha256"]
            if _canonical_hash(without_hash) != recorded_hash:
                continue
            if (
                authority.get("repository") != REPOSITORY
                or authority.get("workflow") != WORKFLOW
                or authority.get("authority_scope") != AUTHORITY_SCOPE
                or authority.get("deployment_approval") != APPROVAL
                or authority.get("target_directory") != TARGET
                or authority.get("source_commit") != source_commit
                or authority.get("run_id") != run_id
                or authority.get("run_attempt") != run_attempt
                or authority.get("rollback_capability_sha256") != capability_sha256
                or authority.get("rollback_capture_id") != candidate.name
            ):
                continue
            if type(authority.get("run_id")) is not int or type(
                authority.get("run_attempt")
            ) is not int:
                continue
            if not isinstance(authority.get("created_at_utc"), str) or UTC.fullmatch(
                authority["created_at_utc"]
            ) is None:
                continue
            python_version = authority.get("python_version")
            if not isinstance(python_version, str) or re.fullmatch(
                r"[0-9]+\.[0-9]+\.[0-9]+", python_version
            ) is None:
                continue
            if tuple(int(part) for part in python_version.split(".")) < (3, 9, 0):
                continue
            bindings = {
                "release_manifest_sha256": "release-manifest.json",
                "pre_deploy_sha256": "pre-deploy.tsv",
                "directory_state_sha256": "directory-state.tsv",
                "post_deploy_sha256": "post-deploy.tsv",
            }
            bound = True
            for field, filename in bindings.items():
                component = candidate / filename
                _validate_state_file(component, euid)
                value = authority.get(field)
                if (
                    not isinstance(value, str)
                    or SHA256.fullmatch(value) is None
                    or _file_hash(component) != value
                ):
                    bound = False
                    break
            if bound:
                matches.append((candidate, authority))
        except (DiscoveryError, OSError, ValueError):
            continue
    if len(matches) != 1:
        raise DiscoveryError(
            f"expected exactly one matching rollback authority; found {len(matches)}"
        )
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rollback-base", type=Path, default=PRODUCTION_ROLLBACK_BASE)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--capability-sha256", required=True)
    args = parser.parse_args()
    try:
        rollback_dir, authority = discover(
            rollback_base=args.rollback_base,
            source_commit=args.source_commit,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            capability_sha256=args.capability_sha256,
        )
    except (DiscoveryError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(f"PUBLIC_SITE_SOURCE_COMMIT={args.source_commit}")
    print(f"PUBLIC_SITE_RUN_ID={args.run_id}")
    print(f"PUBLIC_SITE_RUN_ATTEMPT={args.run_attempt}")
    print(f"PUBLIC_SITE_ROLLBACK_DIR={rollback_dir}")
    print(f"PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256={authority['receipt_sha256']}")
    print("PUBLIC_SITE_DEPLOYMENT_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
