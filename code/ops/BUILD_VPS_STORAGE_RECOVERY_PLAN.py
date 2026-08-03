#!/usr/bin/env python3
"""Build a bounded, read-only VPS storage recovery plan from local evidence.

The planner reads a source-pinned local policy and, optionally, one current
local JSON snapshot. It emits one self-hashed JSON document to standard output.
It performs no network access, writes no files, changes no services, and grants
no operational authority.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


SNAPSHOT_SCHEMA = "luma.vps_storage_snapshot.v1"
PLAN_SCHEMA = "luma.vps_storage_recovery_plan.v1"
POLICY_SCHEMA = "luma.vps_storage_retention_policy.v1"
POLICY_VERSION = "2026-07-25"
CRITICAL_USED_PERCENT = 95.0
WARNING_USED_PERCENT = 85.0
MAX_ARCHIVE_CANDIDATES = 5
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = REPO_ROOT / "config" / "vps_storage_retention_policy_v1.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
ALIAS_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
SAFE_PATH_TOKEN_RE = re.compile(r"^[a-z0-9_./-]{1,160}$")
SAFE_MOUNT_RE = re.compile(
    r"^/(?:$|(?:opt|var|srv|mnt)(?:/[a-z0-9._-]+){0,5})$"
)

REQUIRED_TOP_LEVEL_FIELDS = (
    "schema",
    "observed_at_utc",
    "scope",
    "filesystems",
    "mounts",
    "directory_usage",
    "service_health",
    "backup_state",
    "retention_state",
    "hosting_state",
)

MUTABLE_CONTENT_CLASSES = {
    "artifacts",
    "cache",
    "logs",
    "mutable_data",
    "outputs",
    "snapshots",
}

HUMAN_UNLOCK_ACTIONS = (
    "deletion",
    "archive_or_move",
    "service_restart",
    "dns_change",
    "storage_purchase",
    "storage_resize",
    "deploy",
    "credential_action",
)

SENSITIVE_KEY_MARKERS = (
    "api_key",
    "credential",
    "otp",
    "passphrase",
    "password",
    "private_key",
    "secret",
    "token",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def seal_plan(plan: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(plan)
    sealed.pop("plan_sha256", None)
    sealed["plan_sha256"] = sha256_json(sealed)
    return sealed


def verify_plan_hash(plan: dict[str, Any]) -> bool:
    declared = plan.get("plan_sha256")
    if not isinstance(declared, str) or not SHA256_RE.fullmatch(declared):
        return False
    unsigned = dict(plan)
    unsigned.pop("plan_sha256", None)
    return declared == sha256_json(unsigned)


def _policy_issue(code: str, field: str, detail: str) -> dict[str, str]:
    return {"code": code, "field": field, "detail": detail}


def load_policy(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None, [
            _policy_issue(
                "policy_unreadable",
                "$",
                "The local retention policy could not be read.",
            )
        ]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return None, [
            _policy_issue(
                "policy_invalid_json",
                "$",
                "The local retention policy is not valid JSON.",
            )
        ]
    if not isinstance(value, dict):
        return None, [
            _policy_issue(
                "policy_invalid_root",
                "$",
                "The local retention policy root must be an object.",
            )
        ]
    return value, []


def validate_policy(
    policy: Any,
    repo_root: Path = REPO_ROOT,
    *,
    verify_evidence_files: bool = True,
) -> tuple[list[dict[str, str]], dict[str, Any], dict[str, dict[str, Any]]]:
    issues: list[dict[str, str]] = []
    evidence_status: list[dict[str, Any]] = []
    candidate_index: dict[str, dict[str, Any]] = {}
    if not isinstance(policy, dict):
        return (
            [
                _policy_issue(
                    "policy_invalid_root",
                    "$",
                    "The local retention policy root must be an object.",
                )
            ],
            {
                "schema": POLICY_SCHEMA,
                "accepted": False,
                "evidence_sources": [],
            },
            {},
        )

    if policy.get("schema") != POLICY_SCHEMA:
        issues.append(
            _policy_issue(
                "policy_unexpected_schema",
                "$.schema",
                f"Expected {POLICY_SCHEMA}.",
            )
        )
    if policy.get("policy_version") != POLICY_VERSION:
        issues.append(
            _policy_issue(
                "policy_version_mismatch",
                "$.policy_version",
                f"Expected {POLICY_VERSION}.",
            )
        )
    scope = policy.get("scope")
    if not isinstance(scope, dict):
        issues.append(
            _policy_issue("policy_scope_invalid", "$.scope", "Expected an object.")
        )
    else:
        if scope.get("source_mode") != "existing_local_evidence_only":
            issues.append(
                _policy_issue(
                    "policy_source_mode_invalid",
                    "$.scope.source_mode",
                    "Only existing_local_evidence_only is accepted.",
                )
            )
        for field in (
            "observation_only",
            "external_actions_authorized",
            "current_vps_state_claimed",
        ):
            if not isinstance(scope.get(field), bool):
                issues.append(
                    _policy_issue(
                        "policy_scope_boolean_invalid",
                        f"$.scope.{field}",
                        "Expected true or false.",
                    )
                )
        if scope.get("observation_only") is not True:
            issues.append(
                _policy_issue(
                    "policy_not_observation_only",
                    "$.scope.observation_only",
                    "Policy must remain observation-only.",
                )
            )
        if scope.get("external_actions_authorized") is not False:
            issues.append(
                _policy_issue(
                    "policy_external_action_authorized",
                    "$.scope.external_actions_authorized",
                    "Policy must not authorize external action.",
                )
            )
        if scope.get("current_vps_state_claimed") is not False:
            issues.append(
                _policy_issue(
                    "policy_current_state_claimed",
                    "$.scope.current_vps_state_claimed",
                    "Historical local evidence cannot be promoted to current VPS state.",
                )
            )

    declared_policy_hash = policy.get("policy_payload_sha256")
    unsigned_policy = dict(policy)
    unsigned_policy.pop("policy_payload_sha256", None)
    computed_policy_hash = sha256_json(unsigned_policy)
    if not isinstance(declared_policy_hash, str) or not SHA256_RE.fullmatch(
        declared_policy_hash
    ):
        issues.append(
            _policy_issue(
                "policy_self_hash_missing_or_invalid",
                "$.policy_payload_sha256",
                "Expected a lowercase SHA-256 digest.",
            )
        )
    elif declared_policy_hash != computed_policy_hash:
        issues.append(
            _policy_issue(
                "policy_self_hash_mismatch",
                "$.policy_payload_sha256",
                "Policy self-hash does not match canonical JSON without the hash field.",
            )
        )

    evidence_ids: set[str] = set()
    sources = policy.get("evidence_sources")
    if not isinstance(sources, list) or not sources:
        issues.append(
            _policy_issue(
                "policy_evidence_sources_invalid",
                "$.evidence_sources",
                "Expected at least one source-pinned local evidence record.",
            )
        )
        sources = []
    resolved_root = repo_root.resolve()
    for index, row in enumerate(sources):
        field = f"$.evidence_sources[{index}]"
        if not isinstance(row, dict):
            issues.append(
                _policy_issue("policy_evidence_record_invalid", field, "Expected an object.")
            )
            continue
        source_id = row.get("id")
        relative_path = row.get("path")
        expected_hash = row.get("sha256")
        if not isinstance(source_id, str) or not ALIAS_RE.fullmatch(source_id):
            issues.append(
                _policy_issue(
                    "policy_evidence_id_invalid",
                    f"{field}.id",
                    "Expected a non-private lowercase alias.",
                )
            )
            continue
        if source_id in evidence_ids:
            issues.append(
                _policy_issue(
                    "policy_evidence_id_duplicate",
                    f"{field}.id",
                    "Evidence source aliases must be unique.",
                )
            )
            continue
        evidence_ids.add(source_id)
        if (
            not isinstance(relative_path, str)
            or not relative_path
            or Path(relative_path).is_absolute()
            or ".." in Path(relative_path).parts
        ):
            issues.append(
                _policy_issue(
                    "policy_evidence_path_invalid",
                    f"{field}.path",
                    "Expected a repository-relative path without traversal.",
                )
            )
            continue
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            issues.append(
                _policy_issue(
                    "policy_evidence_hash_invalid",
                    f"{field}.sha256",
                    "Expected a lowercase SHA-256 digest.",
                )
            )
            continue
        status: dict[str, Any] = {
            "id": source_id,
            "path": relative_path.replace("\\", "/"),
            "expected_sha256": expected_hash,
            "observed_sha256": None,
            "status": "NOT_VERIFIED",
        }
        if verify_evidence_files:
            source_path = (resolved_root / relative_path).resolve()
            path_within_root = True
            try:
                source_path.relative_to(resolved_root)
            except ValueError:
                path_within_root = False
                issues.append(
                    _policy_issue(
                        "policy_evidence_path_escape",
                        f"{field}.path",
                        "Evidence path escapes the repository root.",
                    )
                )
                status["status"] = "BLOCKED_PATH_ESCAPE"
            if path_within_root and not source_path.is_file():
                issues.append(
                    _policy_issue(
                        "policy_evidence_missing",
                        f"{field}.path",
                        "Pinned local evidence file is missing.",
                    )
                )
                status["status"] = "BLOCKED_MISSING"
            elif path_within_root:
                observed_hash = sha256_file(source_path)
                status["observed_sha256"] = observed_hash
                if observed_hash != expected_hash:
                    issues.append(
                        _policy_issue(
                            "policy_evidence_hash_mismatch",
                            f"{field}.sha256",
                            "Pinned local evidence changed; review and repin deliberately.",
                        )
                    )
                    status["status"] = "BLOCKED_HASH_MISMATCH"
                else:
                    status["status"] = "VERIFIED_LOCAL_FILE"
        evidence_status.append(status)

    candidates = policy.get("known_candidate_directories")
    if not isinstance(candidates, list) or not candidates:
        issues.append(
            _policy_issue(
                "policy_candidates_invalid",
                "$.known_candidate_directories",
                "Expected at least one candidate-directory record.",
            )
        )
        candidates = []
    for index, row in enumerate(candidates):
        field = f"$.known_candidate_directories[{index}]"
        if not isinstance(row, dict):
            issues.append(
                _policy_issue("policy_candidate_record_invalid", field, "Expected an object.")
            )
            continue
        alias = row.get("path_alias")
        if not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias):
            issues.append(
                _policy_issue(
                    "policy_candidate_alias_invalid",
                    f"{field}.path_alias",
                    "Expected a non-private lowercase alias.",
                )
            )
            continue
        if alias in candidate_index:
            issues.append(
                _policy_issue(
                    "policy_candidate_alias_duplicate",
                    f"{field}.path_alias",
                    "Candidate aliases must be unique.",
                )
            )
            continue
        path_token = row.get("path_token")
        if not isinstance(path_token, str) or not SAFE_PATH_TOKEN_RE.fullmatch(path_token):
            issues.append(
                _policy_issue(
                    "policy_candidate_path_token_invalid",
                    f"{field}.path_token",
                    "Expected a bounded public-safe path token.",
                )
            )
        content_class = row.get("content_class")
        if not isinstance(content_class, str) or not ALIAS_RE.fullmatch(content_class):
            issues.append(
                _policy_issue(
                    "policy_candidate_content_class_invalid",
                    f"{field}.content_class",
                    "Expected a lowercase content-class alias.",
                )
            )
        accounting_group = row.get("size_accounting_group")
        if not isinstance(accounting_group, str) or not ALIAS_RE.fullmatch(
            accounting_group
        ):
            issues.append(
                _policy_issue(
                    "policy_candidate_accounting_group_invalid",
                    f"{field}.size_accounting_group",
                    "Expected a lowercase accounting-group alias.",
                )
            )
        if not isinstance(row.get("review_candidate"), bool):
            issues.append(
                _policy_issue(
                    "policy_candidate_review_flag_invalid",
                    f"{field}.review_candidate",
                    "Expected true or false.",
                )
            )
        source_ids = row.get("evidence_source_ids")
        if not isinstance(source_ids, list) or not source_ids:
            issues.append(
                _policy_issue(
                    "policy_candidate_evidence_invalid",
                    f"{field}.evidence_source_ids",
                    "Expected at least one evidence-source alias.",
                )
            )
        else:
            unknown = sorted(
                item
                for item in source_ids
                if not isinstance(item, str) or item not in evidence_ids
            )
            if unknown:
                issues.append(
                    _policy_issue(
                        "policy_candidate_evidence_unknown",
                        f"{field}.evidence_source_ids",
                        "Candidate references an unknown evidence-source alias.",
                    )
                )
        candidate_index[alias] = dict(row)

    decision_requirements = policy.get("decision_requirements")
    if not isinstance(decision_requirements, dict):
        issues.append(
            _policy_issue(
                "policy_decision_requirements_invalid",
                "$.decision_requirements",
                "Expected archive, delete, resize, and redeploy decision records.",
            )
        )
    else:
        for lane in ("archive", "delete", "resize", "redeploy"):
            record = decision_requirements.get(lane)
            if not isinstance(record, dict):
                issues.append(
                    _policy_issue(
                        "policy_decision_lane_missing",
                        f"$.decision_requirements.{lane}",
                        "Required decision lane is missing.",
                    )
                )
                continue
            if record.get("planner_may_authorize") is not False:
                issues.append(
                    _policy_issue(
                        "policy_decision_lane_authorizes",
                        f"$.decision_requirements.{lane}.planner_may_authorize",
                        "Planner authority must remain false.",
                    )
                )
            if record.get("requires_human_unlock") is not True:
                issues.append(
                    _policy_issue(
                        "policy_decision_lane_unlock_missing",
                        f"$.decision_requirements.{lane}.requires_human_unlock",
                        "Every future mutation requires HumanUnlock.",
                    )
                )
            required_evidence = record.get("required_evidence")
            if not isinstance(required_evidence, list) or not required_evidence:
                issues.append(
                    _policy_issue(
                        "policy_decision_lane_evidence_missing",
                        f"$.decision_requirements.{lane}.required_evidence",
                        "At least one prerequisite is required.",
                    )
                )

    human_unlock = policy.get("human_unlock")
    if not isinstance(human_unlock, dict):
        issues.append(
            _policy_issue(
                "policy_human_unlock_invalid",
                "$.human_unlock",
                "Expected a HumanUnlock boundary.",
            )
        )
    else:
        if human_unlock.get("required_for_every_mutation") is not True:
            issues.append(
                _policy_issue(
                    "policy_human_unlock_not_required",
                    "$.human_unlock.required_for_every_mutation",
                    "Every mutation must require HumanUnlock.",
                )
            )
        if human_unlock.get("planner_can_grant") is not False:
            issues.append(
                _policy_issue(
                    "policy_human_unlock_planner_authority",
                    "$.human_unlock.planner_can_grant",
                    "The planner can never grant HumanUnlock.",
                )
            )

    summary = {
        "schema": policy.get("schema"),
        "policy_version": policy.get("policy_version"),
        "status": policy.get("status"),
        "policy_payload_sha256": declared_policy_hash,
        "computed_policy_payload_sha256": computed_policy_hash,
        "accepted": not issues,
        "evidence_sources": evidence_status,
        "candidate_count": len(candidate_index),
    }
    return issues, summary, candidate_index


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _valid_timestamp(value: Any) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _sensitive_key_paths(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).lower()
            child_path = f"{path}.{key}"
            if any(marker in normalized for marker in SENSITIVE_KEY_MARKERS):
                found.append(child_path)
            found.extend(_sensitive_key_paths(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_sensitive_key_paths(child, f"{path}[{index}]"))
    return found


def _issue(code: str, field: str, detail: str) -> dict[str, str]:
    return {"code": code, "field": field, "detail": detail}


def _require_keys(
    value: dict[str, Any],
    keys: tuple[str, ...],
    path: str,
    issues: list[dict[str, str]],
) -> None:
    for key in keys:
        if key not in value:
            issues.append(
                _issue(
                    "missing_required_field",
                    f"{path}.{key}",
                    "Required snapshot evidence is missing.",
                )
            )


def _validate_filesystems(
    rows: Any,
    issues: list[dict[str, str]],
) -> set[str]:
    mounts: set[str] = set()
    if not isinstance(rows, list) or not rows:
        issues.append(
            _issue(
                "invalid_filesystems",
                "$.filesystems",
                "At least one filesystem observation is required.",
            )
        )
        return mounts

    required = (
        "mount",
        "filesystem_type",
        "capacity_bytes",
        "used_bytes",
        "available_bytes",
        "used_percent",
    )
    for index, row in enumerate(rows):
        path = f"$.filesystems[{index}]"
        if not isinstance(row, dict):
            issues.append(_issue("invalid_record", path, "Expected an object."))
            continue
        _require_keys(row, required, path, issues)
        mount = row.get("mount")
        if not isinstance(mount, str) or not SAFE_MOUNT_RE.fullmatch(mount):
            issues.append(
                _issue(
                    "invalid_mount",
                    f"{path}.mount",
                    "Expected a bounded system mount path without private identifiers.",
                )
            )
        elif mount in mounts:
            issues.append(_issue("duplicate_mount", f"{path}.mount", "Mount observations must be unique."))
        else:
            mounts.add(mount)

        filesystem_type = row.get("filesystem_type")
        if not isinstance(filesystem_type, str) or not filesystem_type:
            issues.append(
                _issue(
                    "invalid_filesystem_type",
                    f"{path}.filesystem_type",
                    "Expected a non-empty string.",
                )
            )

        for field in ("capacity_bytes", "used_bytes", "available_bytes", "used_percent"):
            number = row.get(field)
            if not _is_number(number) or number < 0:
                issues.append(
                    _issue(
                        "invalid_numeric_fact",
                        f"{path}.{field}",
                        "Expected a non-negative number.",
                    )
                )

        capacity = row.get("capacity_bytes")
        used = row.get("used_bytes")
        used_percent = row.get("used_percent")
        if _is_number(capacity) and capacity <= 0:
            issues.append(
                _issue(
                    "invalid_capacity",
                    f"{path}.capacity_bytes",
                    "Capacity must be greater than zero.",
                )
            )
        if _is_number(capacity) and _is_number(used) and used > capacity:
            issues.append(
                _issue(
                    "inconsistent_usage",
                    path,
                    "Used bytes cannot exceed observed capacity.",
                )
            )
        if _is_number(used_percent) and used_percent > 100:
            issues.append(
                _issue(
                    "invalid_used_percent",
                    f"{path}.used_percent",
                    "Used percent must be between 0 and 100.",
                )
            )
    return mounts


def _validate_mounts(
    rows: Any,
    filesystem_mounts: set[str],
    issues: list[dict[str, str]],
) -> None:
    if not isinstance(rows, list) or not rows:
        issues.append(
            _issue(
                "invalid_mounts",
                "$.mounts",
                "At least one mount relationship is required.",
            )
        )
        return
    observed: set[str] = set()
    required = ("mount", "device_alias", "volume_role", "separate_volume")
    for index, row in enumerate(rows):
        path = f"$.mounts[{index}]"
        if not isinstance(row, dict):
            issues.append(_issue("invalid_record", path, "Expected an object."))
            continue
        _require_keys(row, required, path, issues)
        mount = row.get("mount")
        if not isinstance(mount, str) or not SAFE_MOUNT_RE.fullmatch(mount):
            issues.append(
                _issue(
                    "invalid_mount",
                    f"{path}.mount",
                    "Expected a bounded system mount path without private identifiers.",
                )
            )
        else:
            observed.add(mount)
            if filesystem_mounts and mount not in filesystem_mounts:
                issues.append(
                    _issue(
                        "unknown_mount",
                        f"{path}.mount",
                        "Mount relationship references an unaccepted filesystem mount.",
                    )
                )
        for field in ("device_alias", "volume_role"):
            value = row.get(field)
            if not isinstance(value, str) or not ALIAS_RE.fullmatch(value):
                issues.append(
                    _issue(
                        "invalid_alias",
                        f"{path}.{field}",
                        "Expected a non-private lowercase alias.",
                    )
                )
        if not isinstance(row.get("separate_volume"), bool):
            issues.append(
                _issue(
                    "invalid_boolean",
                    f"{path}.separate_volume",
                    "Expected true or false.",
                )
            )
    for mount in sorted(filesystem_mounts - observed):
        issues.append(
            _issue(
                "missing_mount_relationship",
                "$.mounts",
                "An accepted filesystem mount has no mount relationship.",
            )
        )


def _validate_directory_usage(
    rows: Any,
    filesystem_mounts: set[str],
    candidate_index: dict[str, dict[str, Any]],
    issues: list[dict[str, str]],
) -> set[str]:
    aliases: set[str] = set()
    if not isinstance(rows, list):
        issues.append(
            _issue(
                "invalid_directory_usage",
                "$.directory_usage",
                "Expected a list of directory-usage observations.",
            )
        )
        return aliases
    required = ("path_alias", "mount", "bytes", "content_class")
    for index, row in enumerate(rows):
        path = f"$.directory_usage[{index}]"
        if not isinstance(row, dict):
            issues.append(_issue("invalid_record", path, "Expected an object."))
            continue
        _require_keys(row, required, path, issues)
        alias = row.get("path_alias")
        if not isinstance(alias, str) or not ALIAS_RE.fullmatch(alias):
            issues.append(
                _issue(
                    "invalid_path_alias",
                    f"{path}.path_alias",
                    "Expected a non-private lowercase alias.",
                )
            )
        elif alias in aliases:
            issues.append(
                _issue(
                    "duplicate_path_alias",
                    f"{path}.path_alias",
                    "Directory aliases must be unique.",
                )
            )
        else:
            aliases.add(alias)
            if alias not in candidate_index:
                issues.append(
                    _issue(
                        "unregistered_candidate_alias",
                        f"{path}.path_alias",
                        "Directory alias is not registered in the source-pinned policy.",
                    )
                )
        mount = row.get("mount")
        if not isinstance(mount, str) or not SAFE_MOUNT_RE.fullmatch(mount):
            issues.append(
                _issue(
                    "invalid_mount",
                    f"{path}.mount",
                    "Expected a bounded system mount path without private identifiers.",
                )
            )
        elif filesystem_mounts and mount not in filesystem_mounts:
            issues.append(
                _issue(
                    "unknown_mount",
                    f"{path}.mount",
                    "Directory usage references an unaccepted filesystem mount.",
                )
            )
        if not _is_number(row.get("bytes")) or row.get("bytes", -1) < 0:
            issues.append(
                _issue(
                    "invalid_numeric_fact",
                    f"{path}.bytes",
                    "Expected a non-negative number.",
                )
            )
        content_class = row.get("content_class")
        if not isinstance(content_class, str) or not ALIAS_RE.fullmatch(content_class):
            issues.append(
                _issue(
                    "invalid_content_class",
                    f"{path}.content_class",
                    "Expected a lowercase content-class alias.",
                )
            )
        elif alias in candidate_index and content_class != candidate_index[alias].get(
            "content_class"
        ):
            issues.append(
                _issue(
                    "content_class_policy_mismatch",
                    f"{path}.content_class",
                    "Snapshot content class does not match the source-pinned policy.",
                )
            )
    return aliases


def _validate_service_health(
    rows: Any,
    filesystem_mounts: set[str],
    issues: list[dict[str, str]],
) -> None:
    if not isinstance(rows, list):
        issues.append(
            _issue(
                "invalid_service_health",
                "$.service_health",
                "Expected a list of service observations.",
            )
        )
        return
    required = ("service_alias", "status", "health", "depends_on_mounts")
    for index, row in enumerate(rows):
        path = f"$.service_health[{index}]"
        if not isinstance(row, dict):
            issues.append(_issue("invalid_record", path, "Expected an object."))
            continue
        _require_keys(row, required, path, issues)
        for field in ("service_alias", "status", "health"):
            value = row.get(field)
            if not isinstance(value, str) or not ALIAS_RE.fullmatch(value):
                issues.append(
                    _issue(
                        "invalid_service_fact",
                        f"{path}.{field}",
                        "Expected a non-private lowercase alias.",
                    )
                )
        dependencies = row.get("depends_on_mounts")
        if not isinstance(dependencies, list) or any(not isinstance(item, str) for item in dependencies):
            issues.append(
                _issue(
                    "invalid_dependencies",
                    f"{path}.depends_on_mounts",
                    "Expected a list of mount strings.",
                )
            )
        else:
            for mount in dependencies:
                if filesystem_mounts and mount not in filesystem_mounts:
                    issues.append(
                        _issue(
                            "unknown_mount",
                            f"{path}.depends_on_mounts",
                            "Service dependency references an unaccepted filesystem mount.",
                        )
                    )


def _validate_authority_state(
    snapshot: dict[str, Any],
    directory_aliases: set[str],
    issues: list[dict[str, str]],
) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    backup = snapshot.get("backup_state")
    if not isinstance(backup, dict):
        issues.append(
            _issue(
                "invalid_backup_state",
                "$.backup_state",
                "Expected a backup-state object.",
            )
        )
    else:
        _require_keys(
            backup,
            ("verified", "authority_confirmed", "evidence_refs", "covers_path_aliases"),
            "$.backup_state",
            issues,
        )
        if not isinstance(backup.get("verified"), bool):
            issues.append(
                _issue(
                    "invalid_boolean",
                    "$.backup_state.verified",
                    "Expected true or false.",
                )
            )
        elif not backup["verified"]:
            gaps.append(
                _issue(
                    "backup_not_verified",
                    "$.backup_state.verified",
                    "Backup verification is not established.",
                )
            )
        if not isinstance(backup.get("authority_confirmed"), bool):
            issues.append(
                _issue(
                    "invalid_boolean",
                    "$.backup_state.authority_confirmed",
                    "Expected true or false.",
                )
            )
        elif not backup["authority_confirmed"]:
            gaps.append(
                _issue(
                    "backup_authority_missing",
                    "$.backup_state.authority_confirmed",
                    "An authorized backup owner has not been confirmed.",
                )
            )
        evidence_refs = backup.get("evidence_refs")
        if not isinstance(evidence_refs, list) or any(
            not isinstance(item, str) or not item for item in evidence_refs
        ):
            issues.append(
                _issue(
                    "invalid_evidence_refs",
                    "$.backup_state.evidence_refs",
                    "Expected a list of non-empty evidence references.",
                )
            )
        elif not evidence_refs:
            gaps.append(
                _issue(
                    "backup_evidence_missing",
                    "$.backup_state.evidence_refs",
                    "No backup verification evidence reference is present.",
                )
            )
        coverage = backup.get("covers_path_aliases")
        if not isinstance(coverage, list) or any(
            not isinstance(item, str) or not ALIAS_RE.fullmatch(item)
            for item in coverage
        ):
            issues.append(
                _issue(
                    "invalid_backup_coverage",
                    "$.backup_state.covers_path_aliases",
                    "Expected a list of non-empty directory aliases.",
                )
            )
        else:
            missing = sorted(directory_aliases - set(coverage))
            if missing:
                gaps.append(
                    _issue(
                        "backup_coverage_incomplete",
                        "$.backup_state.covers_path_aliases",
                        "Backup coverage is missing observed directory aliases: " + ", ".join(missing),
                    )
                )

    retention = snapshot.get("retention_state")
    if not isinstance(retention, dict):
        issues.append(
            _issue(
                "invalid_retention_state",
                "$.retention_state",
                "Expected a retention-state object.",
            )
        )
    else:
        _require_keys(
            retention,
            ("policy_present", "authority_confirmed", "policy_ref"),
            "$.retention_state",
            issues,
        )
        if not isinstance(retention.get("policy_present"), bool):
            issues.append(
                _issue(
                    "invalid_boolean",
                    "$.retention_state.policy_present",
                    "Expected true or false.",
                )
            )
        elif not retention["policy_present"]:
            gaps.append(
                _issue(
                    "retention_policy_missing",
                    "$.retention_state.policy_present",
                    "No retention policy is established for the observed data.",
                )
            )
        if not isinstance(retention.get("authority_confirmed"), bool):
            issues.append(
                _issue(
                    "invalid_boolean",
                    "$.retention_state.authority_confirmed",
                    "Expected true or false.",
                )
            )
        elif not retention["authority_confirmed"]:
            gaps.append(
                _issue(
                    "retention_authority_missing",
                    "$.retention_state.authority_confirmed",
                    "No authorized retention decision owner is confirmed.",
                )
            )
        policy_ref = retention.get("policy_ref")
        if policy_ref is not None and (not isinstance(policy_ref, str) or not policy_ref):
            issues.append(
                _issue(
                    "invalid_policy_ref",
                    "$.retention_state.policy_ref",
                    "Expected a non-empty reference or null.",
                )
            )
        if not policy_ref:
            gaps.append(
                _issue(
                    "retention_policy_evidence_missing",
                    "$.retention_state.policy_ref",
                    "No retention policy evidence reference is present.",
                )
            )
    return gaps


def validate_snapshot(
    snapshot: Any,
    candidate_index: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    issues: list[dict[str, str]] = []
    if not isinstance(snapshot, dict):
        return (
            [_issue("invalid_snapshot", "$", "Snapshot root must be an object.")],
            [],
        )

    sensitive_paths = _sensitive_key_paths(snapshot)
    if sensitive_paths:
        return (
            [
                _issue(
                    "sensitive_input_rejected",
                    path,
                    "Snapshot keys must not contain credentials or secret material.",
                )
                for path in sensitive_paths
            ],
            [],
        )

    for field in REQUIRED_TOP_LEVEL_FIELDS:
        if field not in snapshot:
            issues.append(
                _issue(
                    "missing_required_field",
                    f"$.{field}",
                    "Required snapshot evidence is missing.",
                )
            )

    if snapshot.get("schema") != SNAPSHOT_SCHEMA:
        issues.append(
            _issue(
                "unexpected_schema",
                "$.schema",
                f"Expected {SNAPSHOT_SCHEMA}.",
            )
        )
    if not _valid_timestamp(snapshot.get("observed_at_utc")):
        issues.append(
            _issue(
                "invalid_timestamp",
                "$.observed_at_utc",
                "Expected an offset-aware ISO 8601 timestamp.",
            )
        )

    scope = snapshot.get("scope")
    if not isinstance(scope, dict):
        issues.append(_issue("invalid_scope", "$.scope", "Expected a scope object."))
    else:
        _require_keys(scope, ("source_kind", "observation_only"), "$.scope", issues)
        if scope.get("source_kind") != "local_json_snapshot":
            issues.append(
                _issue(
                    "invalid_source_kind",
                    "$.scope.source_kind",
                    "Only a local JSON snapshot is accepted.",
                )
            )
        if scope.get("observation_only") is not True:
            issues.append(
                _issue(
                    "scope_not_observation_only",
                    "$.scope.observation_only",
                    "Snapshot scope must be explicitly observation-only.",
                )
            )
        host_alias = scope.get("host_alias")
        if host_alias is not None and (
            not isinstance(host_alias, str) or not ALIAS_RE.fullmatch(host_alias)
        ):
            issues.append(
                _issue(
                    "invalid_host_alias",
                    "$.scope.host_alias",
                    "Expected a non-private lowercase alias.",
                )
            )

    filesystem_mounts = _validate_filesystems(snapshot.get("filesystems"), issues)
    _validate_mounts(snapshot.get("mounts"), filesystem_mounts, issues)
    directory_aliases = _validate_directory_usage(
        snapshot.get("directory_usage"),
        filesystem_mounts,
        candidate_index or {},
        issues,
    )
    _validate_service_health(snapshot.get("service_health"), filesystem_mounts, issues)

    hosting = snapshot.get("hosting_state")
    if not isinstance(hosting, dict):
        issues.append(
            _issue(
                "invalid_hosting_state",
                "$.hosting_state",
                "Expected a hosting-state object.",
            )
        )
    else:
        required_hosting = (
            "static_surface_present",
            "dynamic_service_present",
            "shared_root_volume",
        )
        _require_keys(hosting, required_hosting, "$.hosting_state", issues)
        for field in required_hosting:
            if not isinstance(hosting.get(field), bool):
                issues.append(
                    _issue(
                        "invalid_boolean",
                        f"$.hosting_state.{field}",
                        "Expected true or false.",
                    )
                )

    authority_gaps = _validate_authority_state(
        snapshot,
        directory_aliases,
        issues,
    )
    return issues, authority_gaps


def _known_dict(value: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {key: value.get(key) for key in keys if key in value}


def _known_rows(value: Any, keys: tuple[str, ...], sort_key: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows = [_known_dict(row, keys) for row in value if isinstance(row, dict)]
    return sorted(rows, key=lambda row: str(row.get(sort_key, "")))


def _hashed_reference_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, list):
        return {"count": 0, "reference_sha256": []}
    accepted = [item for item in value if isinstance(item, str) and item]
    return {
        "count": len(accepted),
        "reference_sha256": sorted(
            hashlib.sha256(item.encode("utf-8")).hexdigest() for item in accepted
        ),
    }


def _hashed_optional_reference(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def build_candidate_inventory(
    policy: dict[str, Any],
    directory_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    measurements = {
        row.get("path_alias"): row
        for row in (directory_rows or [])
        if isinstance(row.get("path_alias"), str)
    }
    inventory: list[dict[str, Any]] = []
    for policy_row in policy.get("known_candidate_directories", []):
        if not isinstance(policy_row, dict):
            continue
        alias = policy_row.get("path_alias")
        measurement = measurements.get(alias, {})
        observed_bytes = measurement.get("bytes")
        if not _is_number(observed_bytes):
            observed_bytes = None
        is_review_candidate = policy_row.get("review_candidate") is True
        inventory.append(
            {
                "path_alias": alias,
                "path_token": policy_row.get("path_token"),
                "content_class": policy_row.get("content_class"),
                "size_accounting_group": policy_row.get("size_accounting_group"),
                "review_candidate": is_review_candidate,
                "default_decision": policy_row.get("default_decision"),
                "evidence_source_ids": sorted(
                    policy_row.get("evidence_source_ids", [])
                ),
                "current_observed_bytes": observed_bytes,
                "measurement_status": (
                    "CURRENT_LOCAL_SNAPSHOT_OBSERVED"
                    if observed_bytes is not None
                    else "CURRENT_SIZE_NOT_EVIDENCED"
                ),
                "confirmed_reclaimable_bytes": 0,
                "potential_reclaimable_upper_bound_bytes": (
                    observed_bytes if is_review_candidate else None
                ),
                "safe_to_archive": False,
                "safe_to_delete": False,
                "execution_authorized": False,
            }
        )
    return sorted(inventory, key=lambda row: str(row.get("path_alias", "")))


def derive_reclaim_estimate(
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    group_maxima: dict[str, int | float] = {}
    candidate_rows: list[dict[str, Any]] = []
    for row in inventory:
        observed_bytes = row.get("current_observed_bytes")
        if row.get("review_candidate") is not True or not _is_number(observed_bytes):
            continue
        group = str(row.get("size_accounting_group", "unknown"))
        group_maxima[group] = max(group_maxima.get(group, 0), observed_bytes)
        candidate_rows.append(
            {
                "path_alias": row.get("path_alias"),
                "observed_bytes": observed_bytes,
                "confirmed_reclaimable_bytes": 0,
                "potential_reclaimable_upper_bound_bytes": observed_bytes,
                "classification": "UNVERIFIED_UPPER_BOUND_ONLY",
                "safe_to_archive": False,
                "safe_to_delete": False,
            }
        )
    potential_upper_bound = (
        sum(group_maxima.values()) if group_maxima else None
    )
    return {
        "status": (
            "UNVERIFIED_UPPER_BOUND_ONLY"
            if candidate_rows
            else "BLOCKED_CURRENT_SIZE_EVIDENCE_MISSING"
        ),
        "confirmed_reclaimable_bytes": 0,
        "potential_reclaimable_upper_bound_bytes": potential_upper_bound,
        "upper_bound_basis": (
            "sum_of_maximum_observed_bytes_per_non_additive_accounting_group"
            if candidate_rows
            else "no_current_candidate_measurements"
        ),
        "candidate_observed_bytes_are_not_safe_delete_bytes": True,
        "candidate_observed_bytes_are_not_safe_archive_bytes": True,
        "overlap_double_count_prevented_by_group_maximum": True,
        "candidates": sorted(
            candidate_rows,
            key=lambda row: (-float(row["observed_bytes"]), str(row["path_alias"])),
        ),
    }


def derive_observed_facts(
    snapshot: dict[str, Any],
    policy: dict[str, Any],
) -> dict[str, Any]:
    filesystems = _known_rows(
        snapshot.get("filesystems"),
        (
            "mount",
            "filesystem_type",
            "capacity_bytes",
            "used_bytes",
            "available_bytes",
            "used_percent",
        ),
        "mount",
    )
    mounts = _known_rows(
        snapshot.get("mounts"),
        ("mount", "device_alias", "volume_role", "separate_volume"),
        "mount",
    )
    directories = _known_rows(
        snapshot.get("directory_usage"),
        ("path_alias", "mount", "bytes", "content_class"),
        "path_alias",
    )
    services = _known_rows(
        snapshot.get("service_health"),
        ("service_alias", "status", "health", "depends_on_mounts"),
        "service_alias",
    )
    capacity_by_mount = {
        row["mount"]: row["capacity_bytes"]
        for row in filesystems
        if isinstance(row.get("mount"), str)
        and _is_number(row.get("capacity_bytes"))
        and row["capacity_bytes"] > 0
    }

    filesystem_pressure: list[dict[str, Any]] = []
    for row in filesystems:
        used_percent = row.get("used_percent")
        if not _is_number(used_percent):
            classification = "unknown"
        elif used_percent >= CRITICAL_USED_PERCENT:
            classification = "critical"
        elif used_percent >= WARNING_USED_PERCENT:
            classification = "warning"
        else:
            classification = "normal"
        filesystem_pressure.append(
            {
                "mount": row.get("mount"),
                "used_percent": used_percent,
                "available_bytes": row.get("available_bytes"),
                "classification": classification,
                "derivation": "threshold_applied_to_snapshot_fact",
            }
        )

    inventory = build_candidate_inventory(policy, directories)
    policy_by_alias = {
        row.get("path_alias"): row
        for row in inventory
        if isinstance(row.get("path_alias"), str)
    }
    candidates: list[dict[str, Any]] = []
    for row in directories:
        alias = row.get("path_alias")
        policy_row = policy_by_alias.get(alias, {})
        mount = row.get("mount")
        byte_count = row.get("bytes")
        if not _is_number(byte_count) or policy_row.get("review_candidate") is not True:
            continue
        capacity = capacity_by_mount.get(mount)
        share = round((byte_count / capacity) * 100, 3) if capacity else None
        candidates.append(
            {
                "path_alias": alias,
                "mount": mount,
                "bytes": byte_count,
                "content_class": row.get("content_class"),
                "size_accounting_group": policy_row.get("size_accounting_group"),
                "share_of_mount_capacity_percent": share,
                "classification": "review_candidate_only",
                "confirmed_reclaimable_bytes": 0,
                "potential_reclaimable_upper_bound_bytes": byte_count,
                "safe_to_archive": False,
                "safe_to_delete": False,
            }
        )
    candidates.sort(key=lambda row: float(row.get("bytes", 0)), reverse=True)

    unhealthy_services = [
        {
            "service_alias": row.get("service_alias"),
            "status": row.get("status"),
            "health": row.get("health"),
            "depends_on_mounts": row.get("depends_on_mounts"),
        }
        for row in services
        if str(row.get("health", "")).lower() not in {"healthy", "ok"}
        or str(row.get("status", "")).lower() not in {"active", "running"}
    ]

    return {
        "source": "input_snapshot_only",
        "snapshot_schema": snapshot.get("schema"),
        "observed_at_utc": snapshot.get("observed_at_utc"),
        "scope": _known_dict(
            snapshot.get("scope"),
            ("source_kind", "observation_only", "host_alias"),
        ),
        "filesystems": filesystems,
        "mounts": mounts,
        "directory_usage": directories,
        "service_health": services,
        "backup_state": {
            **_known_dict(
                snapshot.get("backup_state"),
                ("verified", "authority_confirmed", "covers_path_aliases"),
            ),
            "evidence_references": _hashed_reference_summary(
                snapshot.get("backup_state", {}).get("evidence_refs")
                if isinstance(snapshot.get("backup_state"), dict)
                else None
            ),
        },
        "retention_state": {
            **_known_dict(
                snapshot.get("retention_state"),
                ("policy_present", "authority_confirmed"),
            ),
            "policy_reference_sha256": _hashed_optional_reference(
                snapshot.get("retention_state", {}).get("policy_ref")
                if isinstance(snapshot.get("retention_state"), dict)
                else None
            ),
        },
        "hosting_state": _known_dict(
            snapshot.get("hosting_state"),
            (
                "static_surface_present",
                "dynamic_service_present",
                "shared_root_volume",
            ),
        ),
        "derived_observations": {
            "filesystem_pressure": filesystem_pressure,
            "archive_review_candidates": candidates[:MAX_ARCHIVE_CANDIDATES],
            "unhealthy_services": unhealthy_services,
            "known_candidate_inventory": inventory,
            "reclaim_estimate": derive_reclaim_estimate(inventory),
        },
    }


def inventory_only_facts(policy: dict[str, Any]) -> dict[str, Any]:
    inventory = build_candidate_inventory(policy)
    historical = []
    for row in policy.get("historical_observations", []):
        if not isinstance(row, dict):
            continue
        historical.append(
            {
                key: row.get(key)
                for key in (
                    "fact_id",
                    "observed_date",
                    "path_alias",
                    "fact",
                    "observed_size_text",
                    "numeric_bytes_intentionally_omitted",
                    "current_state_claim_allowed",
                    "evidence_source_id",
                )
                if key in row
            }
        )
    return {
        "source": "source_pinned_policy_inventory_only",
        "accepted": True,
        "current_snapshot_present": False,
        "current_vps_state_claimed": False,
        "historical_observations": historical,
        "derived_observations": {
            "filesystem_pressure": [],
            "archive_review_candidates": [],
            "unhealthy_services": [],
            "known_candidate_inventory": inventory,
            "reclaim_estimate": derive_reclaim_estimate(inventory),
        },
    }


def _recommendation(
    priority: int,
    recommendation_id: str,
    category: str,
    text: str,
    basis: list[str],
    prerequisites: list[str],
    human_unlock_required_for: list[str] | None = None,
) -> tuple[int, dict[str, Any]]:
    return (
        priority,
        {
            "id": recommendation_id,
            "category": category,
            "recommendation": text,
            "basis_fact_refs": basis,
            "prerequisites": prerequisites,
            "human_unlock_required_for": human_unlock_required_for or [],
            "execution_authorized": False,
            "authorization_inferred": False,
        },
    )


def rank_recommendations(
    observed: dict[str, Any],
    validation_issues: list[dict[str, str]],
    authority_gaps: list[dict[str, str]],
) -> list[dict[str, Any]]:
    ranked: list[tuple[int, dict[str, Any]]] = []
    issue_codes = {row["code"] for row in validation_issues}
    gap_codes = {row["code"] for row in authority_gaps}

    if validation_issues:
        ranked.append(
            _recommendation(
                0,
                "complete_local_snapshot",
                "evidence_completion",
                "Complete or correct the local observation snapshot before any recovery decision.",
                ["validation_issues"],
                ["Collect missing facts without changing the VPS."],
            )
        )

    if issue_codes & {
        "invalid_backup_state",
        "missing_required_field",
        "invalid_evidence_refs",
        "invalid_backup_coverage",
    } or gap_codes & {
        "backup_not_verified",
        "backup_authority_missing",
        "backup_evidence_missing",
        "backup_coverage_incomplete",
    }:
        ranked.append(
            _recommendation(
                10,
                "verify_backup_evidence_and_coverage",
                "backup_verification",
                "Verify backup ownership, restore evidence, and coverage for every observed directory alias.",
                ["observed_facts.backup_state", "authority_gaps"],
                [
                    "Use existing local receipts first.",
                    "Do not restore, mount, copy, or remove data as part of this review.",
                ],
                ["credential_action"],
            )
        )

    if issue_codes & {
        "invalid_retention_state",
        "missing_required_field",
        "invalid_policy_ref",
    } or gap_codes & {
        "retention_policy_missing",
        "retention_authority_missing",
        "retention_policy_evidence_missing",
    }:
        ranked.append(
            _recommendation(
                20,
                "review_retention_policy_and_authority",
                "retention_review",
                "Document the applicable retention policy and identify the authorized decision owner.",
                ["observed_facts.retention_state", "authority_gaps"],
                [
                    "Preserve legal, grant, audit, settlement, and reproducibility holds.",
                    "Record an evidence reference without changing stored data.",
                ],
            )
        )

    derived = observed.get("derived_observations", {})
    candidates = derived.get("archive_review_candidates", [])
    if candidates:
        ranked.append(
            _recommendation(
                30,
                "review_largest_archive_candidates",
                "archive_candidate_review",
                "Review the largest mutable-data aliases as archive candidates only; size does not establish permission to move or delete them.",
                [
                    f"observed_facts.derived_observations.archive_review_candidates[{index}]"
                    for index in range(len(candidates))
                ],
                [
                    "Verified backup evidence and coverage.",
                    "Approved retention policy and named authority.",
                    "Dependency review for services and reviewer artifacts.",
                ],
                ["archive_or_move", "deletion"],
            )
        )

    critical_mounts = {
        row.get("mount")
        for row in derived.get("filesystem_pressure", [])
        if row.get("classification") == "critical"
    }
    large_critical_candidates = [
        row
        for row in candidates
        if row.get("mount") in critical_mounts
        and _is_number(row.get("share_of_mount_capacity_percent"))
        and row["share_of_mount_capacity_percent"] >= 10
    ]
    if large_critical_candidates:
        ranked.append(
            _recommendation(
                40,
                "evaluate_separate_mutable_data_volume",
                "storage_architecture",
                "Evaluate a separate volume for high-growth mutable data so application code and operating headroom are not coupled.",
                [
                    "observed_facts.derived_observations.filesystem_pressure",
                    "observed_facts.derived_observations.archive_review_candidates",
                    "observed_facts.mounts",
                ],
                [
                    "Capacity and cost estimate.",
                    "Backup, restore, mount, rollback, and dependency design.",
                    "Action-time owner review.",
                ],
                ["storage_purchase", "storage_resize", "deploy", "credential_action"],
            )
        )

    unhealthy_services = derived.get("unhealthy_services", [])
    if unhealthy_services:
        ranked.append(
            _recommendation(
                50,
                "satisfy_service_restart_prerequisites",
                "service_recovery",
                "Recover verified storage headroom and capture dependency evidence before considering any service restart.",
                [
                    "observed_facts.derived_observations.unhealthy_services",
                    "observed_facts.derived_observations.filesystem_pressure",
                ],
                [
                    "Current logs and failure state captured.",
                    "Configuration and rollback references available.",
                    "Required storage headroom verified.",
                    "Action-time operator approval.",
                ],
                ["service_restart"],
            )
        )

    hosting = observed.get("hosting_state", {})
    if (
        hosting.get("static_surface_present") is True
        and hosting.get("dynamic_service_present") is True
        and hosting.get("shared_root_volume") is True
    ):
        ranked.append(
            _recommendation(
                60,
                "evaluate_static_dynamic_hosting_split",
                "hosting_architecture",
                "Evaluate serving public static reviewer assets separately from dynamic APIs and mutable workloads.",
                ["observed_facts.hosting_state"],
                [
                    "Inventory public-safe static assets.",
                    "Define dynamic API health, rollback, and origin boundaries.",
                    "Review cost, custody, privacy, and availability requirements.",
                ],
                ["dns_change", "deploy", "credential_action", "storage_purchase"],
            )
        )

    if not ranked:
        ranked.append(
            _recommendation(
                90,
                "preserve_observation_and_review_cadence",
                "monitoring",
                "Preserve the snapshot and repeat the read-only review on an approved cadence.",
                ["observed_facts"],
                ["No operational action is authorized by this plan."],
            )
        )

    recommendations: list[dict[str, Any]] = []
    for rank, (_, row) in enumerate(sorted(ranked, key=lambda item: (item[0], item[1]["id"])), start=1):
        recommendations.append({"rank": rank, **row})
    return recommendations


def _human_unlock_boundary() -> dict[str, Any]:
    return {
        "planner_can_grant_human_unlock": False,
        "authorization_inferred_from_snapshot": False,
        "actions": [
            {
                "action": action,
                "required": True,
                "authorized": False,
                "authority_source": "action_time_human_confirmation_only",
            }
            for action in HUMAN_UNLOCK_ACTIONS
        ],
    }


def _decision_lanes(
    policy: dict[str, Any] | None,
    *,
    prerequisites_complete: bool,
) -> dict[str, Any]:
    requirements = (
        policy.get("decision_requirements", {})
        if isinstance(policy, dict)
        else {}
    )
    rows: dict[str, Any] = {}
    for lane in ("archive", "delete", "resize", "redeploy"):
        record = requirements.get(lane, {})
        if lane == "delete":
            status = "BLOCKED_NO_DELETE_AUTHORITY"
        elif prerequisites_complete:
            status = "HUMAN_REVIEW_ELIGIBLE_NO_EXECUTION_AUTHORITY"
        else:
            status = "BLOCKED_PREREQUISITES_INCOMPLETE"
        rows[lane] = {
            "status": status,
            "required_evidence": (
                list(record.get("required_evidence", []))
                if isinstance(record, dict)
                else []
            ),
            "human_unlock_required": True,
            "human_unlock_present": False,
            "planner_may_authorize": False,
            "execution_authorized": False,
        }
    return rows


def _input_failure_plan(
    code: str,
    detail: str,
    *,
    policy: dict[str, Any] | None = None,
    policy_summary: dict[str, Any] | None = None,
    policy_issues: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    issue = _issue(code, "$", detail)
    return seal_plan({
        "schema": PLAN_SCHEMA,
        "policy_version": POLICY_VERSION,
        "decision": (
            "BLOCKED_POLICY_OR_EVIDENCE_DRIFT"
            if policy_issues
            else "BLOCKED_SNAPSHOT_INCOMPLETE"
        ),
        "input_snapshot_sha256": None,
        "policy": policy_summary or {
            "schema": POLICY_SCHEMA,
            "accepted": False,
            "evidence_sources": [],
        },
        "policy_validation_issues": policy_issues or [],
        "observed_facts": (
            inventory_only_facts(policy)
            if isinstance(policy, dict) and not policy_issues
            else {"source": "no_accepted_snapshot", "accepted": False}
        ),
        "validation_issues": [issue],
        "authority_gaps": [],
        "recommendations": [
            {
                "rank": 1,
                "id": "provide_valid_local_snapshot",
                "category": "evidence_completion",
                "recommendation": "Provide a readable local JSON snapshot that satisfies the documented schema.",
                "basis_fact_refs": ["validation_issues"],
                "prerequisites": ["Collect facts without changing the VPS."],
                "human_unlock_required_for": [],
                "execution_authorized": False,
                "authorization_inferred": False,
            }
        ],
        "decision_lanes": _decision_lanes(
            policy,
            prerequisites_complete=False,
        ),
        "human_unlock": _human_unlock_boundary(),
        "safety": {
            "network_access_performed": False,
            "filesystem_mutation_performed": False,
            "service_mutation_performed": False,
            "external_action_performed": False,
            "execution_authorized": False,
            "destructive_shell_commands_emitted": False,
        },
    })


def build_plan(
    snapshot: Any,
    policy: dict[str, Any] | None = None,
    *,
    repo_root: Path = REPO_ROOT,
    verify_evidence_files: bool = True,
) -> dict[str, Any]:
    if policy is None:
        policy, policy_load_issues = load_policy(DEFAULT_POLICY_PATH)
    else:
        policy_load_issues = []
    policy_issues: list[dict[str, str]] = list(policy_load_issues)
    if policy is None:
        policy_summary = {
            "schema": POLICY_SCHEMA,
            "accepted": False,
            "evidence_sources": [],
        }
        candidate_index: dict[str, dict[str, Any]] = {}
    else:
        validation, policy_summary, candidate_index = validate_policy(
            policy,
            repo_root,
            verify_evidence_files=verify_evidence_files,
        )
        policy_issues.extend(validation)

    if snapshot is None:
        validation_issues = [
            _issue(
                "current_snapshot_missing",
                "$",
                "No current local observation snapshot was supplied.",
            )
        ]
        authority_gaps: list[dict[str, str]] = []
    else:
        validation_issues, authority_gaps = validate_snapshot(
            snapshot,
            candidate_index,
        )
    if (
        isinstance(snapshot, dict)
        and not validation_issues
        and policy is not None
        and not policy_issues
    ):
        observed = derive_observed_facts(snapshot, policy)
        snapshot_hash = sha256_json(snapshot)
    elif snapshot is None and policy is not None and not policy_issues:
        observed = inventory_only_facts(policy)
        snapshot_hash = None
    else:
        observed = {"source": "no_accepted_snapshot", "accepted": False}
        snapshot_hash = sha256_json(snapshot) if snapshot is not None else None

    if policy_issues:
        decision = "BLOCKED_POLICY_OR_EVIDENCE_DRIFT"
    elif snapshot is None:
        decision = "BLOCKED_CURRENT_SNAPSHOT_MISSING"
    elif validation_issues:
        decision = "BLOCKED_SNAPSHOT_INCOMPLETE"
    elif authority_gaps:
        decision = "BLOCKED_BACKUP_OR_RETENTION_AUTHORITY"
    else:
        decision = "HUMAN_REVIEW_READY_READ_ONLY"

    prerequisites_complete = (
        decision == "HUMAN_REVIEW_READY_READ_ONLY"
        and not policy_issues
        and not validation_issues
        and not authority_gaps
    )
    plan = {
        "schema": PLAN_SCHEMA,
        "policy_version": POLICY_VERSION,
        "decision": decision,
        "input_snapshot_sha256": snapshot_hash,
        "policy": policy_summary,
        "policy_validation_issues": policy_issues,
        "observed_facts": observed,
        "validation_issues": validation_issues,
        "authority_gaps": authority_gaps,
        "recommendations": rank_recommendations(
            observed,
            validation_issues,
            authority_gaps,
        ),
        "decision_lanes": _decision_lanes(
            policy,
            prerequisites_complete=prerequisites_complete,
        ),
        "human_unlock": _human_unlock_boundary(),
        "safety": {
            "network_access_performed": False,
            "filesystem_mutation_performed": False,
            "service_mutation_performed": False,
            "external_action_performed": False,
            "execution_authorized": False,
            "destructive_shell_commands_emitted": False,
        },
    }
    return seal_plan(plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build a self-hashed, read-only VPS storage recovery plan from "
            "source-pinned local evidence and an optional current snapshot."
        )
    )
    parser.add_argument(
        "--snapshot",
        type=Path,
        help=(
            "Path to a current local JSON snapshot. When omitted, the planner "
            "emits a blocked inventory-only plan."
        ),
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to the local source-pinned retention policy.",
    )
    args = parser.parse_args(argv)

    policy, policy_load_issues = load_policy(args.policy)
    if policy_load_issues or policy is None:
        plan = _input_failure_plan(
            "policy_unavailable",
            "The local source-pinned retention policy is unavailable.",
            policy=policy,
            policy_issues=policy_load_issues,
        )
        sys.stdout.write(json.dumps(plan, indent=2, sort_keys=True) + "\n")
        return 2

    policy_issues, policy_summary, _ = validate_policy(policy, REPO_ROOT)
    if args.snapshot is None:
        snapshot = None
    else:
        try:
            raw = args.snapshot.read_text(encoding="utf-8")
        except OSError:
            plan = _input_failure_plan(
                "snapshot_unreadable",
                "The local snapshot could not be read.",
                policy=policy,
                policy_summary=policy_summary,
                policy_issues=policy_issues,
            )
            sys.stdout.write(json.dumps(plan, indent=2, sort_keys=True) + "\n")
            return 2
        try:
            snapshot = json.loads(raw)
        except json.JSONDecodeError:
            plan = _input_failure_plan(
                "snapshot_invalid_json",
                "The local snapshot is not valid JSON.",
                policy=policy,
                policy_summary=policy_summary,
                policy_issues=policy_issues,
            )
            sys.stdout.write(json.dumps(plan, indent=2, sort_keys=True) + "\n")
            return 2

    plan = build_plan(snapshot, policy, repo_root=REPO_ROOT)
    sys.stdout.write(json.dumps(plan, indent=2, sort_keys=True) + "\n")
    return 0 if plan["decision"] == "HUMAN_REVIEW_READY_READ_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
