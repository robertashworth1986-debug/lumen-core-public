#!/usr/bin/env python3
"""Fail-closed verifier for bounded repository security-assurance controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTER = ROOT / "config" / "repository_security_assurance_v1.json"
DEFAULT_DOSSIER = ROOT / "docs" / "REPOSITORY_SECURITY_ASSURANCE.md"
DEFAULT_CODEQL = ROOT / ".github" / "workflows" / "codeql.yml"
DEFAULT_DEPENDENCY_REVIEW = ROOT / ".github" / "workflows" / "dependency-review.yml"
DEFAULT_DEPENDABOT = ROOT / ".github" / "dependabot.yml"
DEFAULT_SECURITY_POLICY = ROOT / "SECURITY.md"
DEFAULT_PACKAGE = ROOT / "dashboard" / "package.json"
DEFAULT_PACKAGE_LOCK = ROOT / "dashboard" / "package-lock.json"

TOP_LEVEL_FIELDS = {
    "schema_version",
    "generated_utc",
    "repository",
    "scope",
    "decision",
    "production_decision",
    "controls",
    "remote_observation",
    "claim_boundaries",
}
CONTROL_FIELDS = {
    "id",
    "status",
    "evidence_paths",
    "establishes",
    "does_not_establish",
}
EXPECTED_CONTROL_STATUS = {
    "code_scanning": "configured_first_party",
    "dependency_change_review": "configured_first_party",
    "declared_dependency_remediation": "configured_first_party",
    "dependency_update_automation": "configured_first_party",
    "private_reporting": "documented_control",
    "triage_remediation_and_exceptions": "documented_control",
    "secret_scanning_and_push_protection": (
        "configured_remote_with_open_historical_provider_gate"
    ),
    "default_branch_protection": "remote_gap_observed",
}
REQUIRED_LIMITATION_MARKER = {
    "code_scanning": "vulnerability-free",
    "dependency_change_review": "existing dependency set",
    "declared_dependency_remediation": "closure of github alerts",
    "dependency_update_automation": "automatic merge",
    "private_reporting": "response-time guarantee",
    "triage_remediation_and_exceptions": "vps",
    "secret_scanning_and_push_protection": "provider rotation",
    "default_branch_protection": "branch protection is configured",
}
REQUIRED_BOUNDARIES = {
    "no_vulnerability_free_claim",
    "no_penetration_test",
    "no_security_certification",
    "no_external_security_audit",
    "no_vps_gateway_or_runtime_scan",
    "no_production_authorization",
    "no_automatic_merge_or_deployment",
    "no_provider_rotation_or_revocation_claim",
    "no_git_history_remediation_claim",
    "no_zero_secret_alert_claim",
    "no_branch_protection_claim",
}
REMOTE_OBSERVATION_FIELDS = {
    "observed_utc",
    "observed_main_commit",
    "security_features",
    "open_alerts",
    "secret_scanning_triage",
    "default_branch_protection",
}
SECURITY_FEATURE_FIELDS = {
    "dependabot_security_updates",
    "secret_scanning",
    "secret_scanning_push_protection",
}
OPEN_ALERT_FIELDS = {"dependabot", "code_scanning", "secret_scanning"}
SECRET_TRIAGE_FIELDS = {
    "resolved_false_positive_alert_count",
    "resolved_false_positive_alert_numbers",
    "resolved_false_positive_type",
    "verified_historical_location_count",
    "generator_expression",
    "current_tracked_occurrence_count",
    "remaining_alert",
}
REMAINING_ALERT_FIELDS = {
    "number",
    "type",
    "validity",
    "scope",
    "provider_rotation_confirmed",
    "git_history_remediation_confirmed",
}
BRANCH_PROTECTION_FIELDS = {
    "main_protected",
    "required_status_checks_enforced",
    "required_pull_request_reviews_enforced",
    "decision",
}
CODEQL_SHA = "5595ccaf912efad79be6eef63a5619ff05969be3"
DEPENDENCY_REVIEW_SHA = "a1d282b36b6f3519aa1f3fc636f609c47dddb294"


class SecurityAssuranceError(ValueError):
    """Raised when security-assurance evidence fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SecurityAssuranceError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_non_finite(value: str) -> None:
    raise SecurityAssuranceError(f"non-finite JSON number: {value}")


def read_json(path: Path, *, max_bytes: int = 1_000_000) -> dict[str, Any]:
    raw = path.read_bytes()
    if len(raw) > max_bytes:
        raise SecurityAssuranceError(f"register exceeds {max_bytes} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite,
        )
    except UnicodeDecodeError as exc:
        raise SecurityAssuranceError("register is not valid UTF-8") from exc
    if not isinstance(value, dict):
        raise SecurityAssuranceError("register must be a JSON object")
    return value


def _require_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise SecurityAssuranceError(f"{label} must be a trimmed non-empty string")
    return value


def _parse_utc(value: Any, label: str) -> str:
    raw = _require_text(value, label)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SecurityAssuranceError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise SecurityAssuranceError(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_evidence(root: Path, raw: Any, label: str) -> tuple[str, Path]:
    value = _require_text(raw, label)
    if "\\" in value:
        raise SecurityAssuranceError(f"{label} must use POSIX separators")
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or value.startswith("./"):
        raise SecurityAssuranceError(f"{label} must be repository-relative")
    candidate = (root / Path(*pure.parts)).resolve(strict=True)
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise SecurityAssuranceError(f"{label} escapes repository") from exc
    if not candidate.is_file():
        raise SecurityAssuranceError(f"{label} is not a file")
    return value, candidate


def verify_codeql_workflow(text: str) -> None:
    required = (
        "pull_request:",
        "schedule:",
        "security-events: write",
        "packages: read",
        "python",
        "javascript-typescript",
        "build-mode: none",
        "queries: security-extended",
        f"github/codeql-action/init@{CODEQL_SHA}",
        f"github/codeql-action/analyze@{CODEQL_SHA}",
        "persist-credentials: false",
    )
    for marker in required:
        if marker not in text:
            raise SecurityAssuranceError(f"CodeQL workflow missing: {marker}")
    if "github/codeql-action/init@v" in text or "github/codeql-action/analyze@v" in text:
        raise SecurityAssuranceError("CodeQL actions must use immutable commits")


def verify_dependency_review_workflow(text: str) -> None:
    required = (
        "pull_request:",
        "contents: read",
        "persist-credentials: false",
        f"actions/dependency-review-action@{DEPENDENCY_REVIEW_SHA}",
        "fail-on-severity: high",
        "fail-on-scopes: runtime, development",
        "comment-summary-in-pr: never",
    )
    for marker in required:
        if marker not in text:
            raise SecurityAssuranceError(
                f"dependency-review workflow missing: {marker}"
            )
    if "security-events: write" in text or "pull-requests: write" in text:
        raise SecurityAssuranceError("dependency review exceeds read-only permissions")


def verify_dependabot_config(text: str) -> None:
    required = (
        "version: 2",
        "package-ecosystem: github-actions",
        "package-ecosystem: pip",
        "package-ecosystem: npm",
        "package-ecosystem: docker",
        "directory: /dashboard",
        "directory: /containers/codecheck-reviewer",
        "interval: weekly",
    )
    for marker in required:
        if marker not in text:
            raise SecurityAssuranceError(f"Dependabot config missing: {marker}")


def verify_dashboard_dependencies(package: dict[str, Any], lock: dict[str, Any]) -> None:
    dependencies = package.get("dependencies")
    overrides = package.get("overrides")
    if not isinstance(dependencies, dict) or not isinstance(overrides, dict):
        raise SecurityAssuranceError("dashboard package dependency contract missing")
    expected_ranges = {
        "@google/model-viewer": "^4.3.1",
        "echarts": "^6.1.0",
        "echarts-gl": "^2.1.0",
        "postprocessing": "^6.39.4",
        "three": "^0.183.2",
    }
    for name, expected in expected_ranges.items():
        if dependencies.get(name) != expected:
            raise SecurityAssuranceError(f"dashboard dependency range drift: {name}")
    if overrides.get("form-data") != "4.0.6":
        raise SecurityAssuranceError("form-data remediation override missing")

    packages = lock.get("packages")
    if lock.get("lockfileVersion") != 3 or not isinstance(packages, dict):
        raise SecurityAssuranceError("dashboard lockfile v3 package map missing")
    expected_versions = {
        "node_modules/@google/model-viewer": "4.3.1",
        "node_modules/echarts": "6.1.0",
        "node_modules/echarts-gl": "2.1.0",
        "node_modules/form-data": "4.0.6",
        "node_modules/postprocessing": "6.39.4",
        "node_modules/three": "0.183.2",
    }
    for path, expected in expected_versions.items():
        entry = packages.get(path)
        if not isinstance(entry, dict) or entry.get("version") != expected:
            raise SecurityAssuranceError(f"dashboard lockfile version drift: {path}")


def verify_security_policy(text: str) -> None:
    required = (
        "private security-advisory channel",
        "## Severity, containment, and remediation targets",
        "These are operational targets, not contractual guarantees.",
        "## Time-bounded exceptions",
        "expiration date",
        "compensating control",
        "closure receipt",
    )
    for marker in required:
        if marker not in text:
            raise SecurityAssuranceError(f"security policy missing: {marker}")


def verify_dossier(text: str) -> None:
    required = (
        "Production remains on `HOLD`.",
        "does not mean zero vulnerabilities",
        "Nothing is auto-merged.",
        "do **not** establish a vulnerability-free codebase",
        "VPS operating system",
        "authorized independent penetration test",
        "Alert 1 remains open.",
        "default `main` branch was not protected",
        "no non-secret provider",
    )
    for marker in required:
        if marker not in text:
            raise SecurityAssuranceError(f"security dossier missing: {marker}")


def verify_remote_observation(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != REMOTE_OBSERVATION_FIELDS:
        raise SecurityAssuranceError("remote observation fields mismatch")
    _parse_utc(value["observed_utc"], "remote_observation.observed_utc")
    commit = _require_text(
        value["observed_main_commit"], "remote_observation.observed_main_commit"
    ).lower()
    if len(commit) != 40 or any(
        character not in "0123456789abcdef" for character in commit
    ):
        raise SecurityAssuranceError("remote observation commit must be a full SHA")

    features = value["security_features"]
    if not isinstance(features, dict) or set(features) != SECURITY_FEATURE_FIELDS:
        raise SecurityAssuranceError("remote security feature fields mismatch")
    if any(features[field] != "enabled" for field in SECURITY_FEATURE_FIELDS):
        raise SecurityAssuranceError("remote security feature status drift")

    alerts = value["open_alerts"]
    if not isinstance(alerts, dict) or set(alerts) != OPEN_ALERT_FIELDS:
        raise SecurityAssuranceError("remote open-alert fields mismatch")
    if alerts != {"dependabot": 0, "code_scanning": 0, "secret_scanning": 1}:
        raise SecurityAssuranceError("remote open-alert snapshot drift")

    triage = value["secret_scanning_triage"]
    if not isinstance(triage, dict) or set(triage) != SECRET_TRIAGE_FIELDS:
        raise SecurityAssuranceError("secret-scanning triage fields mismatch")
    expected_numbers = list(range(2, 30))
    if triage["resolved_false_positive_alert_count"] != len(expected_numbers):
        raise SecurityAssuranceError("false-positive alert count mismatch")
    if triage["resolved_false_positive_alert_numbers"] != expected_numbers:
        raise SecurityAssuranceError("false-positive alert number set mismatch")
    if triage["resolved_false_positive_type"] != "GoCardless Live Access Token":
        raise SecurityAssuranceError("false-positive alert type mismatch")
    if triage["verified_historical_location_count"] != 51:
        raise SecurityAssuranceError("historical alert location count mismatch")
    if triage["generator_expression"] != "live_domain_proof_feeds_<UTC_STAMP>":
        raise SecurityAssuranceError("stage-identifier generator mismatch")
    if triage["current_tracked_occurrence_count"] != 0:
        raise SecurityAssuranceError("current tracked secret occurrence must remain zero")

    remaining = triage["remaining_alert"]
    if not isinstance(remaining, dict) or set(remaining) != REMAINING_ALERT_FIELDS:
        raise SecurityAssuranceError("remaining alert fields mismatch")
    if remaining != {
        "number": 1,
        "type": "Google API Key",
        "validity": "unknown",
        "scope": "historical_only_current_tree_absent",
        "provider_rotation_confirmed": False,
        "git_history_remediation_confirmed": False,
    }:
        raise SecurityAssuranceError("remaining historical provider gate drift")

    branch = value["default_branch_protection"]
    if not isinstance(branch, dict) or set(branch) != BRANCH_PROTECTION_FIELDS:
        raise SecurityAssuranceError("branch-protection observation fields mismatch")
    if branch != {
        "main_protected": False,
        "required_status_checks_enforced": False,
        "required_pull_request_reviews_enforced": False,
        "decision": "HOLD_ACCOUNT_SETTING_REQUIRES_FOUNDER",
    }:
        raise SecurityAssuranceError("branch-protection gap must remain explicit")
    return value


def _git_commit(root: Path) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    value = result.stdout.strip().lower()
    if result.returncode == 0 and len(value) == 40 and all(c in "0123456789abcdef" for c in value):
        return value
    return None


def verify_register(
    *,
    root: Path = ROOT,
    register_path: Path = DEFAULT_REGISTER,
    dossier_path: Path = DEFAULT_DOSSIER,
    codeql_path: Path = DEFAULT_CODEQL,
    dependency_review_path: Path = DEFAULT_DEPENDENCY_REVIEW,
    dependabot_path: Path = DEFAULT_DEPENDABOT,
    security_policy_path: Path = DEFAULT_SECURITY_POLICY,
    package_path: Path = DEFAULT_PACKAGE,
    package_lock_path: Path = DEFAULT_PACKAGE_LOCK,
    verified_utc: str | None = None,
) -> dict[str, Any]:
    root = root.resolve(strict=True)
    register = read_json(register_path)
    if set(register) != TOP_LEVEL_FIELDS:
        raise SecurityAssuranceError("top-level register fields mismatch")
    if register["schema_version"] != "1.1":
        raise SecurityAssuranceError("schema_version must be 1.1")
    _parse_utc(register["generated_utc"], "generated_utc")
    if register["repository"] != "robertashworth1986-debug/lumen-core-public":
        raise SecurityAssuranceError("canonical repository mismatch")
    if register["scope"] != "public_repository_source_and_declared_dependencies":
        raise SecurityAssuranceError("scope mismatch")
    if register["decision"] != (
        "CONFIGURED_FIRST_PARTY_SECURITY_CONTROLS_WITH_OPEN_CREDENTIAL_"
        "HISTORY_RUNTIME_AND_BRANCH_PROTECTION_GAPS"
    ):
        raise SecurityAssuranceError("decision mismatch")
    if register["production_decision"] != "HOLD":
        raise SecurityAssuranceError("production decision must remain HOLD")

    controls = register["controls"]
    if not isinstance(controls, list) or len(controls) != len(EXPECTED_CONTROL_STATUS):
        raise SecurityAssuranceError("control set mismatch")
    observed: dict[str, str] = {}
    evidence: dict[str, dict[str, str]] = {}
    for index, control in enumerate(controls):
        label = f"controls[{index}]"
        if not isinstance(control, dict) or set(control) != CONTROL_FIELDS:
            raise SecurityAssuranceError(f"{label} fields mismatch")
        control_id = _require_text(control["id"], f"{label}.id")
        if control_id in observed:
            raise SecurityAssuranceError(f"duplicate control id: {control_id}")
        status = _require_text(control["status"], f"{label}.status")
        expected = EXPECTED_CONTROL_STATUS.get(control_id)
        if expected is None or status != expected:
            raise SecurityAssuranceError(f"status promotion or drift: {control_id}")
        observed[control_id] = status
        establishes = _require_text(control["establishes"], f"{label}.establishes")
        limitation = _require_text(
            control["does_not_establish"], f"{label}.does_not_establish"
        )
        required_limitation = REQUIRED_LIMITATION_MARKER[control_id]
        if required_limitation not in limitation.lower():
            raise SecurityAssuranceError(
                f"negative boundary missing for {control_id}: {required_limitation}"
            )
        paths = control["evidence_paths"]
        if not isinstance(paths, list) or not paths:
            raise SecurityAssuranceError(f"{label}.evidence_paths must be non-empty")
        for path_index, raw_path in enumerate(paths):
            value, resolved = _resolve_evidence(
                root, raw_path, f"{label}.evidence_paths[{path_index}]"
            )
            evidence[value] = {
                "sha256": _sha256_file(resolved),
                "bytes": str(resolved.stat().st_size),
            }

    if set(observed) != set(EXPECTED_CONTROL_STATUS):
        raise SecurityAssuranceError("control identifiers mismatch")
    boundaries = register["claim_boundaries"]
    if not isinstance(boundaries, list) or set(boundaries) != REQUIRED_BOUNDARIES:
        raise SecurityAssuranceError("claim boundaries mismatch")
    if len(boundaries) != len(set(boundaries)):
        raise SecurityAssuranceError("duplicate claim boundary")
    remote_observation = verify_remote_observation(register["remote_observation"])

    verify_codeql_workflow(codeql_path.read_text(encoding="utf-8"))
    verify_dependency_review_workflow(
        dependency_review_path.read_text(encoding="utf-8")
    )
    verify_dependabot_config(dependabot_path.read_text(encoding="utf-8"))
    verify_dashboard_dependencies(read_json(package_path), read_json(package_lock_path))
    verify_security_policy(security_policy_path.read_text(encoding="utf-8"))
    verify_dossier(dossier_path.read_text(encoding="utf-8"))

    verified = _parse_utc(
        verified_utc or datetime.now(timezone.utc).isoformat(), "verified_utc"
    )
    receipt: dict[str, Any] = {
        "schema_version": "1.0",
        "valid": True,
        "repository": register["repository"],
        "scope": register["scope"],
        "decision": register["decision"],
        "production_decision": "HOLD",
        "verified_utc": verified,
        "source_commit": _git_commit(root),
        "control_count": len(controls),
        "status_counts": dict(sorted(Counter(observed.values()).items())),
        "claim_boundary_count": len(boundaries),
        "evidence": dict(sorted(evidence.items())),
        "workflow_boundaries": {
            "codeql_languages": ["javascript-typescript", "python"],
            "codeql_queries": "security-extended",
            "dependency_failure_threshold": "high",
            "automatic_merge": False,
            "runtime_scan": False,
            "secret_scanning_enabled": True,
            "secret_scanning_push_protection_enabled": True,
            "open_secret_scanning_alert_count": remote_observation["open_alerts"][
                "secret_scanning"
            ],
            "provider_rotation_confirmed": False,
            "default_branch_protection_enforced": False,
        },
        "remote_observation": remote_observation,
    }
    canonical = json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    receipt["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verified-utc")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    receipt = verify_register(verified_utc=args.verified_utc)
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
