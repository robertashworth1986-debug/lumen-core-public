#!/usr/bin/env python3
"""Build a strict status-only receipt for one exact public-site deployment attempt."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from typing import Final

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "deploy"))
from public_site_release_contract import (  # noqa: E402
    RELEASE_ARCHIVE_NAMES,
    RELEASE_PATHS,
    TARGET_DIRECTORY,
    PublicSiteReleaseContractError,
    validate_release_manifest,
)


SCHEMA: Final = "lumencore.public_site_deployment_transaction.v1"
MANIFEST_SCHEMA: Final = "lumencore.public_site_release_manifest.v1"
LIVE_SCHEMA: Final = "lumencore.public_site_live_verification.v1"
COMPENSATION_SCHEMA: Final = "lumencore.public_site_same_run_compensation.v1"
AUTHORITY_SCHEMA: Final = "lumencore.public_site_same_run_rollback_authority.v1"
REPOSITORY: Final = "robertashworth1986-debug/lumen-core-public"
WORKFLOW: Final = ".github/workflows/deploy-public-site-release.yml"
AUTHORITY_SCOPE: Final = "FAILED_EXTERNAL_LIVE_GATE_COMPENSATION_IN_SAME_WORKFLOW_RUN_ONLY"
DEPLOYMENT_APPROVAL: Final = "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT"
TARGET: Final = TARGET_DIRECTORY
EXPECTED_FILE_COUNT: Final = len(RELEASE_PATHS)
EXPECTED_DIRECTORY_COUNT: Final = 7
CLAIM_BOUNDARIES: Final = (
    "Status-only evidence for one exact repository workflow run and attempt.",
    "Verified compensation covers only allowlisted local bytes, numeric ownership, and modes.",
    "Compensation is not candidate success, public recovery proof, incident closure, certification, or SLA evidence.",
)
FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
ROLLBACK_DIR = re.compile(
    r"/opt/lumencore/rollbacks/public-site/[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}"
)


class TransactionReceiptError(ValueError):
    """Raised when component evidence is malformed or cross-run."""


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise TransactionReceiptError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise TransactionReceiptError(f"non-finite JSON value: {value}")


def _load_json(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionReceiptError(f"invalid JSON component {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise TransactionReceiptError(f"component is not an object: {path.name}")
    return payload


def _sha(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as exc:
        raise TransactionReceiptError(f"cannot hash component {path.name}: {exc}") from exc


def _canonical_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _validate_self_hash(payload: dict[str, object], field: str = "receipt_sha256") -> str:
    receipt_hash = payload.get(field)
    if not isinstance(receipt_hash, str) or SHA256.fullmatch(receipt_hash) is None:
        raise TransactionReceiptError("component receipt hash is invalid")
    without_hash = dict(payload)
    del without_hash[field]
    if _canonical_hash(without_hash) != receipt_hash:
        raise TransactionReceiptError("component receipt self-hash mismatch")
    return receipt_hash


def _validate_manifest(path: Path, source_commit: str) -> dict[str, object]:
    payload = _load_json(path)
    try:
        validate_release_manifest(payload, source_commit=source_commit)
    except PublicSiteReleaseContractError as exc:
        raise TransactionReceiptError(str(exc)) from exc
    return payload


def _parse_apply_receipt(
    path: Path, *, source_commit: str, run_id: int, run_attempt: int
) -> dict[str, str]:
    try:
        body = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise TransactionReceiptError(f"invalid apply receipt: {exc}") from exc
    expected = {
        "PUBLIC_SITE_SOURCE_COMMIT": source_commit,
        "PUBLIC_SITE_RUN_ID": str(run_id),
        "PUBLIC_SITE_RUN_ATTEMPT": str(run_attempt),
    }
    parsed: dict[str, str] = {}
    for key in (*expected, "PUBLIC_SITE_ROLLBACK_DIR", "PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256"):
        matches = re.findall(rf"(?m)^{re.escape(key)}=([^\r\n]+)$", body)
        if len(matches) != 1:
            raise TransactionReceiptError(f"apply receipt must contain exactly one {key}")
        parsed[key] = matches[0]
    for key, value in expected.items():
        if parsed[key] != value:
            raise TransactionReceiptError(f"apply receipt binding mismatch: {key}")
    if ROLLBACK_DIR.fullmatch(parsed["PUBLIC_SITE_ROLLBACK_DIR"]) is None:
        raise TransactionReceiptError("apply receipt rollback directory is invalid")
    if not parsed["PUBLIC_SITE_ROLLBACK_DIR"].endswith(f"-{source_commit[:12]}"):
        raise TransactionReceiptError("apply receipt rollback directory commit mismatch")
    if SHA256.fullmatch(parsed["PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256"]) is None:
        raise TransactionReceiptError("apply receipt authority hash is invalid")
    if len(re.findall(r"(?m)^PUBLIC_SITE_DEPLOYMENT_OK$", body)) != 1:
        raise TransactionReceiptError("apply receipt lacks one exact success marker")
    return parsed


def _validate_authority(
    path: Path,
    *,
    source_commit: str,
    run_id: int,
    run_attempt: int,
    manifest_sha256: str,
    apply_data: dict[str, str],
) -> dict[str, object]:
    payload = _load_json(path)
    keys = {
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
    if set(payload) != keys or payload.get("schema") != AUTHORITY_SCHEMA:
        raise TransactionReceiptError("rollback authority fields or schema are invalid")
    authority_hash = _validate_self_hash(payload)
    if authority_hash != apply_data["PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256"]:
        raise TransactionReceiptError("rollback authority does not match the apply receipt")
    if payload.get("repository") != REPOSITORY or payload.get("workflow") != WORKFLOW:
        raise TransactionReceiptError("rollback authority repository or workflow mismatch")
    if payload.get("authority_scope") != AUTHORITY_SCOPE:
        raise TransactionReceiptError("rollback authority scope is invalid")
    if payload.get("deployment_approval") != DEPLOYMENT_APPROVAL:
        raise TransactionReceiptError("rollback authority approval is invalid")
    if payload.get("target_directory") != TARGET:
        raise TransactionReceiptError("rollback authority target is invalid")
    if payload.get("source_commit") != source_commit:
        raise TransactionReceiptError("rollback authority source commit mismatch")
    if type(payload.get("run_id")) is not int or payload["run_id"] != run_id:
        raise TransactionReceiptError("rollback authority run ID mismatch")
    if type(payload.get("run_attempt")) is not int or payload["run_attempt"] != run_attempt:
        raise TransactionReceiptError("rollback authority run attempt mismatch")
    if payload.get("release_manifest_sha256") != manifest_sha256:
        raise TransactionReceiptError("rollback authority manifest mismatch")
    python_version = payload.get("python_version")
    if not isinstance(python_version, str) or re.fullmatch(
        r"[0-9]+\.[0-9]+\.[0-9]+", python_version
    ) is None:
        raise TransactionReceiptError("rollback authority Python version is invalid")
    if tuple(int(part) for part in python_version.split(".")) < (3, 9, 0):
        raise TransactionReceiptError("rollback authority Python version is unsupported")
    expected_capture = Path(apply_data["PUBLIC_SITE_ROLLBACK_DIR"]).name
    if payload.get("rollback_capture_id") != expected_capture:
        raise TransactionReceiptError("rollback authority capture ID mismatch")
    timestamp = payload.get("created_at_utc")
    if not isinstance(timestamp, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", timestamp
    ) is None:
        raise TransactionReceiptError("rollback authority timestamp is invalid")
    for key in (
        "directory_state_sha256",
        "post_deploy_sha256",
        "pre_deploy_sha256",
        "rollback_capability_sha256",
    ):
        value = payload.get(key)
        if not isinstance(value, str) or SHA256.fullmatch(value) is None:
            raise TransactionReceiptError(f"rollback authority digest is invalid: {key}")
    return payload


def _expected_live_url(name: str, source_commit: str) -> str:
    route_map = {
        "operator_home.html": "/",
        "evidence/index_bounded.html": "/evidence/",
        "build_week/prooflock_console/index.html": "/build_week/prooflock_console/",
    }
    route = route_map.get(name, "/" + name)
    return f"https://lumen-core.ai{route}?release={source_commit}"


def _validate_live(
    path: Path,
    source_commit: str,
    manifest: dict[str, object],
    *,
    verified: bool,
) -> dict[str, object]:
    payload = _load_json(path)
    keys = {
        "base_url", "checked_at_utc", "expected_file_count", "matched_file_count",
        "release_verified", "results", "schema", "source_commit"
    }
    if set(payload) != keys or payload.get("schema") != LIVE_SCHEMA:
        raise TransactionReceiptError("live-gate receipt fields or schema are invalid")
    if payload.get("source_commit") != source_commit or payload.get("release_verified") is not verified:
        raise TransactionReceiptError("live-gate receipt binding or result is invalid")
    if payload.get("base_url") != "https://lumen-core.ai":
        raise TransactionReceiptError("live-gate base URL is invalid")
    if not isinstance(payload.get("checked_at_utc"), str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z",
        payload["checked_at_utc"],
    ) is None:
        raise TransactionReceiptError("live-gate timestamp is invalid")
    if type(payload.get("expected_file_count")) is not int or payload["expected_file_count"] != EXPECTED_FILE_COUNT:
        raise TransactionReceiptError("live-gate expected count is invalid")
    matched = payload.get("matched_file_count")
    if type(matched) is not int or not 0 <= matched <= EXPECTED_FILE_COUNT:
        raise TransactionReceiptError("live-gate matched count is invalid")
    if verified and matched != EXPECTED_FILE_COUNT:
        raise TransactionReceiptError("verified live gate did not match every file")
    if not verified and matched == EXPECTED_FILE_COUNT:
        raise TransactionReceiptError("failed live gate contradicts its match count")
    results = payload.get("results")
    if not isinstance(results, list) or len(results) != EXPECTED_FILE_COUNT:
        raise TransactionReceiptError("live-gate result rows are incomplete")
    manifest_rows = manifest["files"]
    assert isinstance(manifest_rows, list)
    recomputed_matches = 0
    error_keys = {"archive_name", "detail", "expected_sha256", "status", "url"}
    observed_keys = {
        "actual_sha256", "archive_name", "bytes", "content_type",
        "content_type_allowed", "expected_sha256", "http_status", "status", "url"
    }
    for result, manifest_row in zip(results, manifest_rows, strict=True):
        if not isinstance(result, dict) or not isinstance(manifest_row, dict):
            raise TransactionReceiptError("live-gate result row is invalid")
        name = manifest_row["archive_name"]
        expected = manifest_row["sha256"]
        if result.get("archive_name") != name or result.get("expected_sha256") != expected:
            raise TransactionReceiptError("live-gate result order or manifest binding is invalid")
        if result.get("url") != _expected_live_url(name, source_commit):
            raise TransactionReceiptError("live-gate result URL is invalid")
        status = result.get("status")
        if status == "ERROR":
            if set(result) != error_keys or not isinstance(result.get("detail"), str) or not result["detail"]:
                raise TransactionReceiptError("live-gate error row is invalid")
            continue
        if set(result) != observed_keys:
            raise TransactionReceiptError("live-gate observed row fields are invalid")
        actual = result.get("actual_sha256")
        byte_count = result.get("bytes")
        http_status = result.get("http_status")
        allowed = result.get("content_type_allowed")
        if (
            not isinstance(actual, str)
            or SHA256.fullmatch(actual) is None
            or type(byte_count) is not int
            or byte_count < 0
            or type(http_status) is not int
            or type(allowed) is not bool
            or not isinstance(result.get("content_type"), str)
            or not result["content_type"]
        ):
            raise TransactionReceiptError("live-gate observed row values are invalid")
        should_match = http_status == 200 and actual == expected and allowed
        if status != ("MATCH" if should_match else "MISMATCH"):
            raise TransactionReceiptError("live-gate row status contradicts its evidence")
        recomputed_matches += int(should_match)
    if recomputed_matches != matched or verified != (recomputed_matches == EXPECTED_FILE_COUNT):
        raise TransactionReceiptError("live-gate aggregate contradicts its result rows")
    return payload


def validate_rejected_live_receipt(
    *, manifest_path: Path, live_gate_path: Path, source_commit: str
) -> dict[str, object]:
    """Validate a complete, strict, source-bound rejected live-gate receipt."""
    manifest = _validate_manifest(manifest_path, source_commit)
    return _validate_live(live_gate_path, source_commit, manifest, verified=False)


def _validate_compensation(
    path: Path,
    *,
    source_commit: str,
    run_id: int,
    run_attempt: int,
    manifest_sha256: str,
    authority_hash: str,
    live_hash: str | None,
) -> dict[str, object]:
    payload = _load_json(path)
    keys = {
        "authority_receipt_sha256", "claim_boundary", "completed_at_utc",
        "live_gate_receipt_sha256", "receipt_sha256", "release_manifest_sha256",
        "repository", "restored_file_count", "restored_pre_deploy_sha256",
        "rollback_verified", "run_attempt", "run_id", "schema", "source_commit",
        "trigger", "verified_directory_count", "workflow"
    }
    if set(payload) != keys or payload.get("schema") != COMPENSATION_SCHEMA:
        raise TransactionReceiptError("compensation receipt fields or schema are invalid")
    _validate_self_hash(payload)
    if payload.get("repository") != REPOSITORY or payload.get("workflow") != WORKFLOW:
        raise TransactionReceiptError("compensation repository or workflow mismatch")
    if payload.get("source_commit") != source_commit:
        raise TransactionReceiptError("compensation source commit mismatch")
    if type(payload.get("run_id")) is not int or payload["run_id"] != run_id:
        raise TransactionReceiptError("compensation run ID mismatch")
    if type(payload.get("run_attempt")) is not int or payload["run_attempt"] != run_attempt:
        raise TransactionReceiptError("compensation run attempt mismatch")
    if payload.get("authority_receipt_sha256") != authority_hash:
        raise TransactionReceiptError("compensation authority mismatch")
    if payload.get("release_manifest_sha256") != manifest_sha256:
        raise TransactionReceiptError("compensation manifest mismatch")
    if payload.get("rollback_verified") is not True:
        raise TransactionReceiptError("compensation is not verified")
    if payload.get("restored_file_count") != EXPECTED_FILE_COUNT:
        raise TransactionReceiptError("compensation file count is incomplete")
    if payload.get("verified_directory_count") != EXPECTED_DIRECTORY_COUNT:
        raise TransactionReceiptError("compensation directory count is incomplete")
    if payload.get("claim_boundary") != "ALLOWLISTED_LOCAL_BYTES_UID_GID_MODE_ONLY":
        raise TransactionReceiptError("compensation claim boundary is invalid")
    if not isinstance(payload.get("restored_pre_deploy_sha256"), str) or SHA256.fullmatch(payload["restored_pre_deploy_sha256"]) is None:
        raise TransactionReceiptError("compensation pre-deploy digest is invalid")
    trigger = payload.get("trigger")
    if live_hash is None:
        if trigger != "LIVE_GATE_ERROR_OR_MISSING" or payload.get("live_gate_receipt_sha256") is not None:
            raise TransactionReceiptError("compensation missing-gate trigger is invalid")
    elif trigger != "LIVE_GATE_REJECTED" or payload.get("live_gate_receipt_sha256") != live_hash:
        raise TransactionReceiptError("compensation rejected-gate binding is invalid")
    return payload


def build_receipt(
    *,
    source_commit: str,
    run_id: int,
    run_attempt: int,
    manifest_path: Path,
    package_receipt_path: Path,
    apply_receipt_path: Path | None,
    authority_receipt_path: Path | None,
    live_gate_path: Path | None,
    compensation_path: Path | None,
    apply_outcome: str,
    live_outcome: str,
    compensation_outcome: str,
) -> dict[str, object]:
    if FULL_COMMIT.fullmatch(source_commit) is None:
        raise TransactionReceiptError("source commit must be a full lowercase SHA-1")
    if type(run_id) is not int or run_id <= 0 or type(run_attempt) is not int or run_attempt <= 0:
        raise TransactionReceiptError("run ID and attempt must be positive integers")
    for label, value in (
        ("apply", apply_outcome),
        ("live gate", live_outcome),
        ("compensation", compensation_outcome),
    ):
        if value not in {"success", "failure", "skipped"}:
            raise TransactionReceiptError(f"{label} outcome is invalid")
    manifest = _validate_manifest(manifest_path, source_commit)
    package_receipt = _load_json(package_receipt_path)
    if package_receipt != manifest:
        raise TransactionReceiptError("package receipt does not equal the exact manifest")
    manifest_hash = _sha(manifest_path)

    apply_data = None
    authority_data = None
    if apply_outcome == "success":
        if apply_receipt_path is None or authority_receipt_path is None:
            raise TransactionReceiptError("successful apply is missing its receipt or authority")
        apply_data = _parse_apply_receipt(
            apply_receipt_path, source_commit=source_commit, run_id=run_id, run_attempt=run_attempt
        )
        authority_data = _validate_authority(
            authority_receipt_path,
            source_commit=source_commit,
            run_id=run_id,
            run_attempt=run_attempt,
            manifest_sha256=manifest_hash,
            apply_data=apply_data,
        )
    elif apply_receipt_path is not None or authority_receipt_path is not None:
        raise TransactionReceiptError("non-successful apply cannot carry success evidence")

    if apply_outcome != "success" and live_outcome != "skipped":
        raise TransactionReceiptError("live gate must be skipped when apply did not succeed")
    if apply_outcome == "success" and live_outcome == "skipped":
        raise TransactionReceiptError("successful apply cannot skip the live gate")

    live_hash: str | None = None
    candidate_verified = False
    if live_outcome == "success":
        if apply_outcome != "success" or live_gate_path is None:
            raise TransactionReceiptError("successful live gate requires a successful apply and receipt")
        _validate_live(live_gate_path, source_commit, manifest, verified=True)
        live_hash = _sha(live_gate_path)
        candidate_verified = True
    elif live_outcome == "failure" and live_gate_path is not None:
        _validate_live(live_gate_path, source_commit, manifest, verified=False)
        live_hash = _sha(live_gate_path)
    elif live_outcome == "skipped" and live_gate_path is not None:
        raise TransactionReceiptError("skipped live gate cannot carry a receipt")

    compensation_verified = False
    if compensation_outcome == "success":
        if apply_data is None or live_outcome != "failure" or compensation_path is None:
            raise TransactionReceiptError("successful compensation has an invalid predecessor state")
        compensation_data = _validate_compensation(
            compensation_path,
            source_commit=source_commit,
            run_id=run_id,
            run_attempt=run_attempt,
            manifest_sha256=manifest_hash,
            authority_hash=apply_data["PUBLIC_SITE_ROLLBACK_AUTHORITY_SHA256"],
            live_hash=live_hash,
        )
        assert authority_data is not None
        if compensation_data.get("restored_pre_deploy_sha256") != authority_data.get(
            "pre_deploy_sha256"
        ):
            raise TransactionReceiptError(
                "compensation pre-deploy digest does not match the rollback authority"
            )
        compensation_verified = True
    elif compensation_path is not None:
        raise TransactionReceiptError("non-successful compensation cannot carry a verified receipt")

    compensation_required = apply_outcome == "success" and not candidate_verified
    if candidate_verified and compensation_outcome != "skipped":
        raise TransactionReceiptError("compensation is forbidden after a verified live gate")
    if compensation_required and compensation_outcome == "skipped":
        raise TransactionReceiptError("required compensation was skipped")
    if not compensation_required and compensation_outcome != "skipped":
        raise TransactionReceiptError("compensation ran without a rejected applied candidate")

    if candidate_verified and compensation_outcome == "skipped":
        final_state = "CANDIDATE_VERIFIED"
    elif compensation_verified:
        final_state = "PRIOR_STATE_RESTORED"
    else:
        final_state = "INDETERMINATE_FAIL_CLOSED"
    workflow_should_succeed = final_state == "CANDIDATE_VERIFIED"

    payload: dict[str, object] = {
        "apply_outcome": apply_outcome,
        "apply_receipt_sha256": _sha(apply_receipt_path) if apply_receipt_path else None,
        "authority_receipt_sha256": (
            _sha(authority_receipt_path) if authority_receipt_path else None
        ),
        "candidate_live_verified": candidate_verified,
        "claim_boundaries": list(CLAIM_BOUNDARIES),
        "compensation_outcome": compensation_outcome,
        "compensation_receipt_sha256": _sha(compensation_path) if compensation_path else None,
        "compensation_required": compensation_required,
        "compensation_verified": compensation_verified,
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "final_state": final_state,
        "live_gate_outcome": live_outcome,
        "live_gate_receipt_sha256": live_hash,
        "manifest_sha256": manifest_hash,
        "package_receipt_sha256": _sha(package_receipt_path),
        "repository": REPOSITORY,
        "run_attempt": run_attempt,
        "run_id": run_id,
        "schema": SCHEMA,
        "source_commit": source_commit,
        "workflow": WORKFLOW,
        "workflow_should_succeed": workflow_should_succeed,
    }
    payload["receipt_sha256"] = _canonical_hash(payload)
    return payload


def verify_receipt(
    payload: dict[str, object],
    *,
    source_commit: str,
    run_id: int,
    run_attempt: int,
    manifest_path: Path,
    package_receipt_path: Path,
    apply_receipt_path: Path,
    authority_receipt_path: Path,
    live_gate_path: Path,
) -> dict[str, object]:
    """Strictly adjudicate a previously built transaction receipt."""
    keys = {
        "apply_outcome",
        "apply_receipt_sha256",
        "authority_receipt_sha256",
        "candidate_live_verified",
        "claim_boundaries",
        "compensation_outcome",
        "compensation_receipt_sha256",
        "compensation_required",
        "compensation_verified",
        "created_at_utc",
        "final_state",
        "live_gate_outcome",
        "live_gate_receipt_sha256",
        "manifest_sha256",
        "package_receipt_sha256",
        "receipt_sha256",
        "repository",
        "run_attempt",
        "run_id",
        "schema",
        "source_commit",
        "workflow",
        "workflow_should_succeed",
    }
    if set(payload) != keys or payload.get("schema") != SCHEMA:
        raise TransactionReceiptError("transaction receipt fields or schema are invalid")
    _validate_self_hash(payload)
    if payload.get("repository") != REPOSITORY or payload.get("workflow") != WORKFLOW:
        raise TransactionReceiptError("transaction receipt repository or workflow mismatch")
    if payload.get("source_commit") != source_commit:
        raise TransactionReceiptError("transaction receipt source commit mismatch")
    if type(payload.get("run_id")) is not int or payload["run_id"] != run_id:
        raise TransactionReceiptError("transaction receipt run ID mismatch")
    if type(payload.get("run_attempt")) is not int or payload["run_attempt"] != run_attempt:
        raise TransactionReceiptError("transaction receipt run attempt mismatch")
    if payload.get("claim_boundaries") != list(CLAIM_BOUNDARIES):
        raise TransactionReceiptError("transaction receipt claim boundaries are invalid")
    created_at = payload.get("created_at_utc")
    if not isinstance(created_at, str) or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", created_at
    ) is None:
        raise TransactionReceiptError("transaction receipt timestamp is invalid")
    try:
        datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise TransactionReceiptError("transaction receipt timestamp is not a real UTC instant") from exc
    for key in ("manifest_sha256", "package_receipt_sha256"):
        value = payload.get(key)
        if not isinstance(value, str) or SHA256.fullmatch(value) is None:
            raise TransactionReceiptError(f"transaction receipt digest is invalid: {key}")
    for key in (
        "apply_receipt_sha256",
        "authority_receipt_sha256",
        "live_gate_receipt_sha256",
        "compensation_receipt_sha256",
    ):
        value = payload.get(key)
        if value is not None and (
            not isinstance(value, str) or SHA256.fullmatch(value) is None
        ):
            raise TransactionReceiptError(f"transaction optional digest is invalid: {key}")
    outcomes = {
        "apply": payload.get("apply_outcome"),
        "live": payload.get("live_gate_outcome"),
        "compensation": payload.get("compensation_outcome"),
    }
    if any(value not in {"success", "failure", "skipped"} for value in outcomes.values()):
        raise TransactionReceiptError("transaction receipt outcome is invalid")
    apply_succeeded = outcomes["apply"] == "success"
    if apply_succeeded != (
        payload.get("apply_receipt_sha256") is not None
        and payload.get("authority_receipt_sha256") is not None
    ):
        raise TransactionReceiptError("transaction apply evidence contradicts its outcome")
    if not apply_succeeded and outcomes["live"] != "skipped":
        raise TransactionReceiptError("transaction live gate must be skipped after failed apply")
    if apply_succeeded and outcomes["live"] == "skipped":
        raise TransactionReceiptError("transaction live gate cannot be skipped after apply")
    candidate_verified = outcomes["live"] == "success"
    if payload.get("candidate_live_verified") is not candidate_verified:
        raise TransactionReceiptError("transaction candidate status contradicts live outcome")
    if candidate_verified != (payload.get("live_gate_receipt_sha256") is not None):
        if not (
            outcomes["live"] == "failure"
            and payload.get("live_gate_receipt_sha256") is not None
        ):
            raise TransactionReceiptError("transaction live evidence contradicts its outcome")
    compensation_required = apply_succeeded and not candidate_verified
    compensation_verified = outcomes["compensation"] == "success"
    if payload.get("compensation_required") is not compensation_required:
        raise TransactionReceiptError("transaction compensation requirement is invalid")
    if payload.get("compensation_verified") is not compensation_verified:
        raise TransactionReceiptError("transaction compensation status is invalid")
    if compensation_verified != (payload.get("compensation_receipt_sha256") is not None):
        raise TransactionReceiptError("transaction compensation evidence contradicts its outcome")
    if candidate_verified and outcomes["compensation"] != "skipped":
        raise TransactionReceiptError("transaction compensation ran after valid live gate")
    if compensation_required and outcomes["compensation"] == "skipped":
        raise TransactionReceiptError("transaction required compensation was skipped")
    if not compensation_required and outcomes["compensation"] != "skipped":
        raise TransactionReceiptError("transaction compensation ran without authority")
    if candidate_verified:
        expected_state = "CANDIDATE_VERIFIED"
    elif compensation_verified:
        expected_state = "PRIOR_STATE_RESTORED"
    else:
        expected_state = "INDETERMINATE_FAIL_CLOSED"
    if payload.get("final_state") != expected_state:
        raise TransactionReceiptError("transaction final state contradicts component outcomes")
    if payload.get("workflow_should_succeed") is not (expected_state == "CANDIDATE_VERIFIED"):
        raise TransactionReceiptError("transaction workflow result contradicts its final state")
    expected = build_receipt(
        source_commit=source_commit,
        run_id=run_id,
        run_attempt=run_attempt,
        manifest_path=manifest_path,
        package_receipt_path=package_receipt_path,
        apply_receipt_path=apply_receipt_path,
        authority_receipt_path=authority_receipt_path,
        live_gate_path=live_gate_path,
        compensation_path=None,
        apply_outcome="success",
        live_outcome="success",
        compensation_outcome="skipped",
    )
    expected["created_at_utc"] = created_at
    expected_without_hash = dict(expected)
    del expected_without_hash["receipt_sha256"]
    expected["receipt_sha256"] = _canonical_hash(expected_without_hash)
    if payload != expected:
        raise TransactionReceiptError(
            "transaction receipt is not the exact component-bound candidate adjudication"
        )
    return payload


def _optional_path(raw: str) -> Path | None:
    return None if raw == "-" else Path(raw)


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="ascii", newline="\n", dir=path.parent, delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(rendered)
    os.replace(temporary, path)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "verify":
        parser = argparse.ArgumentParser(description="Strictly verify a transaction receipt")
        parser.add_argument("verify", nargs=1)
        parser.add_argument("--receipt", required=True, type=Path)
        parser.add_argument("--source-commit", required=True)
        parser.add_argument("--run-id", required=True, type=int)
        parser.add_argument("--run-attempt", required=True, type=int)
        parser.add_argument("--manifest", required=True, type=Path)
        parser.add_argument("--package-receipt", required=True, type=Path)
        parser.add_argument("--apply-receipt", required=True, type=Path)
        parser.add_argument("--authority-receipt", required=True, type=Path)
        parser.add_argument("--live-gate-receipt", required=True, type=Path)
        args = parser.parse_args()
        try:
            payload = _load_json(args.receipt)
            verify_receipt(
                payload,
                source_commit=args.source_commit,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                manifest_path=args.manifest,
                package_receipt_path=args.package_receipt,
                apply_receipt_path=args.apply_receipt,
                authority_receipt_path=args.authority_receipt,
                live_gate_path=args.live_gate_receipt,
            )
        except TransactionReceiptError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True))
        return 0

    if len(sys.argv) > 1 and sys.argv[1] == "validate-rejected-live":
        parser = argparse.ArgumentParser(description="Validate a rejected live-gate receipt")
        parser.add_argument("validate-rejected-live", nargs=1)
        parser.add_argument("--manifest", required=True, type=Path)
        parser.add_argument("--receipt", required=True, type=Path)
        parser.add_argument("--source-commit", required=True)
        args = parser.parse_args()
        try:
            validate_rejected_live_receipt(
                manifest_path=args.manifest,
                live_gate_path=args.receipt,
                source_commit=args.source_commit,
            )
        except TransactionReceiptError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print("STRICT_REJECTED_LIVE_RECEIPT_OK")
        return 0

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--run-id", required=True, type=int)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--package-receipt", required=True, type=Path)
    parser.add_argument("--apply-receipt", required=True)
    parser.add_argument("--authority-receipt", required=True)
    parser.add_argument("--live-gate-receipt", required=True)
    parser.add_argument("--compensation-receipt", required=True)
    parser.add_argument("--apply-outcome", required=True, choices=("success", "failure", "skipped"))
    parser.add_argument("--live-gate-outcome", required=True, choices=("success", "failure", "skipped"))
    parser.add_argument("--compensation-outcome", required=True, choices=("success", "failure", "skipped"))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        receipt = build_receipt(
            source_commit=args.source_commit,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            manifest_path=args.manifest,
            package_receipt_path=args.package_receipt,
            apply_receipt_path=_optional_path(args.apply_receipt),
            authority_receipt_path=_optional_path(args.authority_receipt),
            live_gate_path=_optional_path(args.live_gate_receipt),
            compensation_path=_optional_path(args.compensation_receipt),
            apply_outcome=args.apply_outcome,
            live_outcome=args.live_gate_outcome,
            compensation_outcome=args.compensation_outcome,
        )
    except TransactionReceiptError as exc:
        print(f"ERROR: {exc}", file=__import__("sys").stderr)
        return 1
    _write(args.output, receipt)
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
