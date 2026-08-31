#!/usr/bin/env python3
"""Classify exact-snapshot public release drift without mutating production."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any
from urllib.parse import parse_qs, quote, urljoin, urlparse


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY = ROOT / "config" / "incident_response_and_continuity_v1.json"

FULL_COMMIT = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")
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
AUDIT_FIELDS = {
    "base_url",
    "checked_at_utc",
    "expected_file_count",
    "matched_file_count",
    "release_verified",
    "results",
    "schema",
    "source_commit",
}
RESULT_COMMON_FIELDS = {"archive_name", "expected_sha256", "status", "url"}
RESULT_ERROR_FIELDS = RESULT_COMMON_FIELDS | {"detail"}
RESULT_HTTP_FIELDS = RESULT_COMMON_FIELDS | {
    "actual_sha256",
    "bytes",
    "content_type",
    "content_type_allowed",
    "http_status",
}
POLICY_FIELDS = {
    "schema_version",
    "scope",
    "status",
    "incident_owner",
    "classification_contract",
    "critical_surfaces",
    "severity_levels",
    "automated_actions_allowed",
    "human_authorization_required",
    "containment_sequence",
    "recovery_sequence",
    "evidence_retention",
    "planning_targets",
    "claim_boundaries",
}
OWNER_FIELDS = {
    "accountable_role",
    "evidence_custodian",
    "customer_communications_owner",
    "release_authority",
}
CLASSIFICATION_FIELDS = {
    "release_verified",
    "any_critical_surface_not_match",
    "affected_ratio_at_or_above",
    "affected_ratio_severity",
    "any_other_not_match",
    "highest_automatic_severity",
    "manual_only_sev1_conditions",
}
EXPECTED_SEVERITY_IDS = ["NONE", "SEV-4", "SEV-3", "SEV-2", "SEV-1"]
EXPECTED_SEVERITY_DECISIONS = {
    "NONE": "MONITOR",
    "SEV-4": "REVIEW",
    "SEV-3": "HOLD_AFFECTED_SURFACE_PROMOTION",
    "SEV-2": "HOLD_PUBLIC_RELEASE_PROMOTION",
    "SEV-1": "HUMAN_EMERGENCY_RESPONSE",
}
EXPECTED_MANUAL_SEV1_CONDITIONS = {
    "confirmed credential or secret exposure",
    "confirmed buyer-data disclosure",
    "confirmed unauthorized production control",
    "confirmed financial or trading impact",
    "confirmed safety or regulated-system impact",
}
EXPECTED_AUTOMATED_ACTIONS = {
    "package immutable public-site bytes from Git",
    "collect public HTTP status, MIME, byte count, and SHA-256 evidence",
    "classify bounded release drift up to SEV-2",
    "emit and upload a machine-readable incident receipt",
    "fail the audit workflow and recommend a promotion hold",
    "within the same still-running human-approved exact-snapshot workflow attempt, restore only its captured allowlisted local static state after external live-gate rejection",
}
REQUIRED_HUMAN_ACTIONS = {
    "deploy an exact public-site snapshot",
    "repair or restart the public gateway",
    "install, rotate, or revoke a credential or secret",
    "notify a customer, regulator, insurer, partner, or the public",
    "place a trade or enable production execution",
    "close an incident after a live production change",
}
REQUIRED_CLAIM_BOUNDARIES = {
    "not_a_tested_live_incident_response_program",
    "not_a_business_continuity_certification",
    "not_a_disaster_recovery_certification",
    "not_an_enterprise_sla",
    "not_a_security_audit_or_penetration_test",
    "not_proof_of_customer_notification_or_regulatory_compliance",
    "not_authority_to_deploy_repair_rotate_notify_delete_trade_or_close",
}


class IncidentClassificationError(ValueError):
    """Raised when an incident input or policy fails closed."""


def expected_live_url(archive_name: str, source_commit: str) -> str:
    """Return the one canonical public URL allowed for a manifest entry."""
    route_map = {
        "operator_home.html": "/",
        "evidence/index_bounded.html": "/evidence/",
        "build_week/prooflock_console/index.html": "/build_week/prooflock_console/",
    }
    path = route_map.get(archive_name, "/" + quote(archive_name, safe="/"))
    return urljoin("https://lumen-core.ai/", path.lstrip("/")) + (
        f"?release={source_commit}"
    )


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise IncidentClassificationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def reject_non_finite(value: str) -> None:
    raise IncidentClassificationError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 5_000_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise IncidentClassificationError(f"JSON exceeds {max_bytes} bytes: {path}")
    try:
        payload = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_non_finite,
        )
    except UnicodeDecodeError as exc:
        raise IncidentClassificationError(f"JSON is not UTF-8: {path}") from exc
    if not isinstance(payload, dict):
        raise IncidentClassificationError(f"expected JSON object: {path}")
    return payload


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise IncidentClassificationError(f"{label} must be a trimmed non-empty string")
    return value


def require_int(value: Any, label: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise IncidentClassificationError(f"{label} must be an integer >= {minimum}")
    return value


def require_unique_text_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise IncidentClassificationError(f"{label} must be a non-empty list")
    result = [require_text(item, f"{label} item") for item in value]
    if len(result) != len(set(result)):
        raise IncidentClassificationError(f"{label} contains duplicates")
    return result


def require_utc(value: Any, label: str) -> str:
    text = require_text(value, label)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise IncidentClassificationError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise IncidentClassificationError(f"{label} must include a timezone")
    canonical = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if canonical != text:
        raise IncidentClassificationError(f"{label} must use canonical UTC form")
    return text


def validate_policy(policy: dict[str, Any]) -> dict[str, Any]:
    if set(policy) != POLICY_FIELDS:
        raise IncidentClassificationError("incident policy fields mismatch")
    if policy["schema_version"] != "1.0":
        raise IncidentClassificationError("incident policy schema must be 1.0")
    if policy["scope"] != "public_review_surface_and_bounded_validation_sprint":
        raise IncidentClassificationError("incident policy scope mismatch")
    if policy["status"] != "documented_first_party_control_with_ci_exercise":
        raise IncidentClassificationError("incident policy status is not bounded")

    owner = policy["incident_owner"]
    if not isinstance(owner, dict) or set(owner) != OWNER_FIELDS:
        raise IncidentClassificationError("incident owner fields mismatch")
    if owner["accountable_role"] != "founder_operator":
        raise IncidentClassificationError("incident owner must remain founder_operator")
    if owner["release_authority"] != "human_unlock_only":
        raise IncidentClassificationError("release authority must remain human_unlock_only")

    contract = policy["classification_contract"]
    if not isinstance(contract, dict) or set(contract) != CLASSIFICATION_FIELDS:
        raise IncidentClassificationError("classification contract fields mismatch")
    expected_values = {
        "release_verified": "NONE",
        "any_critical_surface_not_match": "SEV-2",
        "affected_ratio_severity": "SEV-2",
        "any_other_not_match": "SEV-3",
        "highest_automatic_severity": "SEV-2",
    }
    for field, expected in expected_values.items():
        if contract[field] != expected:
            raise IncidentClassificationError(f"unsafe classification contract: {field}")
    threshold = contract["affected_ratio_at_or_above"]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise IncidentClassificationError("affected ratio threshold must be numeric")
    if not 0 < float(threshold) <= 1:
        raise IncidentClassificationError("affected ratio threshold must be in (0, 1]")
    manual_sev1 = require_unique_text_list(
        contract["manual_only_sev1_conditions"], "manual_only_sev1_conditions"
    )
    if set(manual_sev1) != EXPECTED_MANUAL_SEV1_CONDITIONS:
        raise IncidentClassificationError("manual SEV-1 conditions are incomplete or drifted")

    critical = require_unique_text_list(policy["critical_surfaces"], "critical_surfaces")
    for index, name in enumerate(critical):
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != name:
            raise IncidentClassificationError(
                f"critical_surfaces[{index}] is not a safe canonical path"
            )

    severity_levels = policy["severity_levels"]
    if not isinstance(severity_levels, list) or [row.get("id") for row in severity_levels if isinstance(row, dict)] != EXPECTED_SEVERITY_IDS:
        raise IncidentClassificationError("severity level set or order mismatch")
    for row in severity_levels:
        if not isinstance(row, dict) or set(row) != {"id", "meaning", "default_decision"}:
            raise IncidentClassificationError("severity row fields mismatch")
        require_text(row["meaning"], f"severity {row['id']} meaning")
        require_text(row["default_decision"], f"severity {row['id']} decision")
        if row["default_decision"] != EXPECTED_SEVERITY_DECISIONS[row["id"]]:
            raise IncidentClassificationError(f"severity decision drift: {row['id']}")

    automated = set(
        require_unique_text_list(policy["automated_actions_allowed"], "automated_actions_allowed")
    )
    if automated != EXPECTED_AUTOMATED_ACTIONS:
        raise IncidentClassificationError("automated action boundary drift")
    human_actions = set(
        require_unique_text_list(
            policy["human_authorization_required"], "human_authorization_required"
        )
    )
    if not REQUIRED_HUMAN_ACTIONS <= human_actions:
        raise IncidentClassificationError("required HumanUnlock actions are missing")
    require_unique_text_list(policy["containment_sequence"], "containment_sequence")
    require_unique_text_list(policy["recovery_sequence"], "recovery_sequence")

    retention = policy["evidence_retention"]
    if not isinstance(retention, dict) or set(retention) != {
        "github_actions_artifact_days",
        "durable_local_target",
        "preserve_failures",
        "preserve_negative_results",
        "customer_data_retention",
    }:
        raise IncidentClassificationError("evidence retention fields mismatch")
    if require_int(retention["github_actions_artifact_days"], "artifact days", minimum=1) != 30:
        raise IncidentClassificationError("artifact retention must remain 30 days")
    if retention["preserve_failures"] is not True or retention["preserve_negative_results"] is not True:
        raise IncidentClassificationError("negative evidence retention must remain enabled")
    require_text(retention["durable_local_target"], "durable local target")
    require_text(retention["customer_data_retention"], "customer data retention")

    targets = policy["planning_targets"]
    if not isinstance(targets, dict) or set(targets) != {
        "contract_status",
        "public_audit_cadence_hours",
        "classification_target",
        "public_static_restore_target_hours_after_valid_human_authorization",
        "release_byte_rpo",
        "buyer_data_rto_rpo",
    }:
        raise IncidentClassificationError("planning target fields mismatch")
    if targets["contract_status"] != "non_contractual_unvalidated_planning_targets":
        raise IncidentClassificationError("planning targets must remain non-contractual")
    require_int(targets["public_audit_cadence_hours"], "audit cadence", minimum=1)
    require_int(
        targets["public_static_restore_target_hours_after_valid_human_authorization"],
        "static restore target",
        minimum=1,
    )
    if "not established" not in str(targets["buyer_data_rto_rpo"]).lower():
        raise IncidentClassificationError("buyer-data RTO/RPO must remain unestablished")

    boundaries = set(require_unique_text_list(policy["claim_boundaries"], "claim_boundaries"))
    if boundaries != REQUIRED_CLAIM_BOUNDARIES:
        raise IncidentClassificationError("incident claim boundaries mismatch")
    return policy


def validate_manifest(manifest: dict[str, Any]) -> tuple[str, dict[str, dict[str, Any]]]:
    if set(manifest) != MANIFEST_FIELDS:
        raise IncidentClassificationError("release manifest fields mismatch")
    if manifest["schema"] != "lumencore.public_site_release_manifest.v1":
        raise IncidentClassificationError("release manifest schema mismatch")
    source_commit = require_text(manifest["source_commit"], "manifest source_commit")
    if not FULL_COMMIT.fullmatch(source_commit):
        raise IncidentClassificationError("manifest source_commit is invalid")
    if manifest["target_directory"] != "/opt/lumencore/dashboard":
        raise IncidentClassificationError("manifest target directory mismatch")
    if not SHA256.fullmatch(str(manifest["archive_sha256"])):
        raise IncidentClassificationError("manifest archive_sha256 is invalid")
    rows = manifest["files"]
    count = require_int(manifest["file_count"], "manifest file_count", minimum=1)
    if not isinstance(rows, list) or len(rows) != count:
        raise IncidentClassificationError("manifest file count drift")
    by_name: dict[str, dict[str, Any]] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != MANIFEST_FILE_FIELDS:
            raise IncidentClassificationError(f"manifest file row {index} fields mismatch")
        name = require_text(row["archive_name"], f"manifest files[{index}].archive_name")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts or path.as_posix() != name or name in by_name:
            raise IncidentClassificationError(f"unsafe or duplicate manifest path: {name}")
        if row["repo_path"] != f"dashboard/{name}" or row["install_mode"] != "0644":
            raise IncidentClassificationError(f"manifest path or mode mismatch: {name}")
        if not FULL_COMMIT.fullmatch(str(row["git_blob_oid"])):
            raise IncidentClassificationError(f"manifest Git blob is invalid: {name}")
        if not SHA256.fullmatch(str(row["sha256"])):
            raise IncidentClassificationError(f"manifest SHA-256 is invalid: {name}")
        require_int(row["bytes"], f"manifest bytes for {name}")
        by_name[name] = row
    return source_commit, by_name


def validate_audit(
    audit: dict[str, Any],
    *,
    source_commit: str,
    manifest_files: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if set(audit) != AUDIT_FIELDS:
        raise IncidentClassificationError("live audit fields mismatch")
    if audit["schema"] != "lumencore.public_site_live_verification.v1":
        raise IncidentClassificationError("live audit schema mismatch")
    if audit["source_commit"] != source_commit:
        raise IncidentClassificationError("live audit source commit mismatch")
    if audit["base_url"] != "https://lumen-core.ai":
        raise IncidentClassificationError("live audit base URL is not canonical")
    require_utc(audit["checked_at_utc"], "audit checked_at_utc")
    expected_count = require_int(audit["expected_file_count"], "expected_file_count", minimum=1)
    matched_count = require_int(audit["matched_file_count"], "matched_file_count")
    if expected_count != len(manifest_files) or matched_count > expected_count:
        raise IncidentClassificationError("live audit count drift")
    results = audit["results"]
    if not isinstance(results, list) or len(results) != expected_count:
        raise IncidentClassificationError("live audit result count drift")

    seen: set[str] = set()
    actual_matches = 0
    for index, row in enumerate(results):
        if not isinstance(row, dict):
            raise IncidentClassificationError(f"live result {index} must be an object")
        status = row.get("status")
        expected_fields = RESULT_ERROR_FIELDS if status == "ERROR" else RESULT_HTTP_FIELDS
        if status not in {"MATCH", "MISMATCH", "ERROR"} or set(row) != expected_fields:
            raise IncidentClassificationError(f"live result {index} fields or status mismatch")
        name = require_text(row["archive_name"], f"live result {index} archive_name")
        if name in seen or name not in manifest_files:
            raise IncidentClassificationError(f"unknown or duplicate live result: {name}")
        seen.add(name)
        manifest_row = manifest_files[name]
        if row["expected_sha256"] != manifest_row["sha256"]:
            raise IncidentClassificationError(f"expected SHA-256 drift for {name}")
        supplied_url = require_text(row["url"], f"live result URL for {name}")
        parsed = urlparse(supplied_url)
        if parsed.scheme != "https" or parsed.netloc != "lumen-core.ai":
            raise IncidentClassificationError(f"noncanonical live result URL for {name}")
        if parse_qs(parsed.query) != {"release": [source_commit]}:
            raise IncidentClassificationError(f"release query mismatch for {name}")
        if supplied_url != expected_live_url(name, source_commit):
            raise IncidentClassificationError(f"live result route mismatch for {name}")
        if status == "ERROR":
            require_text(row["detail"], f"live result detail for {name}")
            continue
        if not SHA256.fullmatch(str(row["actual_sha256"])):
            raise IncidentClassificationError(f"actual SHA-256 is invalid for {name}")
        require_int(row["bytes"], f"live bytes for {name}")
        require_int(row["http_status"], f"HTTP status for {name}", minimum=100)
        require_text(row["content_type"], f"content type for {name}")
        if not isinstance(row["content_type_allowed"], bool):
            raise IncidentClassificationError(f"MIME decision is invalid for {name}")
        computed_match = (
            row["http_status"] == 200
            and row["actual_sha256"] == row["expected_sha256"]
            and row["content_type_allowed"] is True
        )
        if (status == "MATCH") != computed_match:
            raise IncidentClassificationError(f"live result status is inconsistent for {name}")
        actual_matches += int(computed_match)

    if seen != set(manifest_files):
        raise IncidentClassificationError("live audit does not cover the manifest exactly")
    verified = actual_matches == expected_count
    if matched_count != actual_matches or audit["release_verified"] is not verified:
        raise IncidentClassificationError("live audit summary is inconsistent")
    return results


def classify(
    *,
    policy: dict[str, Any],
    manifest: dict[str, Any],
    audit: dict[str, Any],
) -> dict[str, Any]:
    validate_policy(policy)
    source_commit, manifest_files = validate_manifest(manifest)
    critical = set(policy["critical_surfaces"])
    if not critical <= set(manifest_files):
        raise IncidentClassificationError("critical surface is absent from the release manifest")
    results = validate_audit(
        audit, source_commit=source_commit, manifest_files=manifest_files
    )
    affected = [
        {
            "archive_name": row["archive_name"],
            "critical": row["archive_name"] in critical,
            "status": row["status"],
        }
        for row in results
        if row["status"] != "MATCH"
    ]
    affected_count = len(affected)
    expected_count = len(results)
    affected_ratio = affected_count / expected_count
    critical_affected = sorted(
        row["archive_name"] for row in affected if row["critical"]
    )
    error_count = sum(row["status"] == "ERROR" for row in affected)
    mismatch_count = sum(row["status"] == "MISMATCH" for row in affected)
    contract = policy["classification_contract"]

    if not affected:
        severity = contract["release_verified"]
        state = "NO_INCIDENT_OBSERVED"
        decision = "MONITOR"
    elif critical_affected or affected_ratio >= float(contract["affected_ratio_at_or_above"]):
        severity = contract["any_critical_surface_not_match"]
        state = "ACTIVE_PUBLIC_RELEASE_INTEGRITY_INCIDENT"
        decision = "HOLD_PUBLIC_RELEASE_PROMOTION"
    else:
        severity = contract["any_other_not_match"]
        state = "ACTIVE_LIMITED_PUBLIC_RELEASE_INCIDENT"
        decision = "HOLD_AFFECTED_SURFACE_PROMOTION"

    severity_rank = {"NONE": 0, "SEV-4": 1, "SEV-3": 2, "SEV-2": 3, "SEV-1": 4}
    if severity_rank[severity] > severity_rank[contract["highest_automatic_severity"]]:
        raise IncidentClassificationError("automatic classification exceeded SEV-2")

    affected_sorted = sorted(affected, key=lambda row: row["archive_name"])
    fingerprint_material = {
        "base_url": audit["base_url"],
        "source_commit": source_commit,
        "severity": severity,
        "affected": affected_sorted,
    }
    receipt: dict[str, Any] = {
        "receipt_schema": "lumencore.public_release_incident.v1",
        "valid": True,
        "classified_at_utc": audit["checked_at_utc"],
        "source_commit": source_commit,
        "base_url": audit["base_url"],
        "incident_state": state,
        "severity": severity,
        "decision": decision,
        "release_verified": audit["release_verified"],
        "expected_file_count": expected_count,
        "matched_file_count": audit["matched_file_count"],
        "affected_file_count": affected_count,
        "affected_ratio": round(affected_ratio, 6),
        "mismatch_count": mismatch_count,
        "error_count": error_count,
        "critical_affected": critical_affected,
        "affected": affected_sorted,
        "incident_fingerprint_sha256": canonical_sha256(fingerprint_material),
        "manifest_canonical_sha256": canonical_sha256(manifest),
        "live_audit_canonical_sha256": canonical_sha256(audit),
        "policy_canonical_sha256": canonical_sha256(policy),
        "containment_sequence": policy["containment_sequence"],
        "recovery_sequence": policy["recovery_sequence"],
        "human_authorization_required": policy["human_authorization_required"],
        "planning_targets": policy["planning_targets"],
        "automatic_actions_performed": [
            "machine_classification",
            "incident_receipt_generation",
        ],
        "production_mutation_performed": False,
        "external_notification_performed": False,
        "incident_closure_authorized": False,
        "claim_boundaries": policy["claim_boundaries"],
    }
    receipt["receipt_sha256"] = canonical_sha256(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--live-verification", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        receipt = classify(
            policy=read_json(args.policy),
            manifest=read_json(args.manifest),
            audit=read_json(args.live_verification),
        )
    except (OSError, UnicodeError, json.JSONDecodeError, IncidentClassificationError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True))
        return 1
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
