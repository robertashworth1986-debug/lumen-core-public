#!/usr/bin/env python3
"""Verify the bounded incident-response policy and deterministic tabletop."""

from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS = Path(__file__).resolve().parent
if str(OPS) not in sys.path:
    sys.path.insert(0, str(OPS))

import CLASSIFY_PUBLIC_RELEASE_INCIDENT as classifier  # noqa: E402


POLICY_PATH = ROOT / "config" / "incident_response_and_continuity_v1.json"
PLAN_PATH = ROOT / "docs" / "INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md"
REGISTER_PATH = ROOT / "config" / "institutional_readiness_register_v1.json"
LIVE_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy.yml"
READINESS_WORKFLOW_PATH = ROOT / ".github" / "workflows" / "incident-response-readiness.yml"

REQUIRED_PLAN_TEXT = (
    "documented first-party control with deterministic CI exercises",
    "not a tested live incident-response program",
    "The public-site classifier is intentionally capped at `SEV-2`",
    "DEPLOY_PUBLIC_SITE_EXACT_SNAPSHOT",
    "non-contractual, unvalidated planning targets",
    "No automated workflow may notify",
    "not evidence of a completed live restoration",
    "keep every rejected candidate attempt red",
    "later recovery requires a separate human-reviewed decision",
    "A red live audit is an incident signal, not permission to mutate production.",
)
REQUIRED_LIVE_WORKFLOW_TEXT = (
    "CLASSIFY_PUBLIC_RELEASE_INCIDENT.py",
    "incident-classification.json",
    "config/incident_response_and_continuity_v1.json",
    "exit \"$audit_rc\"",
)
REQUIRED_READINESS_WORKFLOW_TEXT = (
    "VERIFY_INCIDENT_RESPONSE_AND_CONTINUITY.py",
    "test_public_release_incident_classifier.py",
    "incident-response-readiness/receipt.json",
)
REQUIRED_REGISTER_EVIDENCE = {
    "config/incident_response_and_continuity_v1.json",
    "docs/INCIDENT_RESPONSE_AND_CONTINUITY_PLAN.md",
    "code/ops/CLASSIFY_PUBLIC_RELEASE_INCIDENT.py",
    "code/ops/VERIFY_INCIDENT_RESPONSE_AND_CONTINUITY.py",
    ".github/workflows/deploy.yml",
    ".github/workflows/incident-response-readiness.yml",
}


class ContinuityVerificationError(ValueError):
    """Raised when an incident-readiness control fails closed."""


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _parse_utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ContinuityVerificationError("verified_utc must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ContinuityVerificationError("verified_utc must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_oid(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


def _manifest(names: list[str]) -> dict[str, Any]:
    return {
        "archive_sha256": _digest("tabletop-archive"),
        "file_count": len(names),
        "files": [
            {
                "archive_name": name,
                "bytes": 100 + index,
                "git_blob_oid": _git_oid(name),
                "install_mode": "0644",
                "repo_path": f"dashboard/{name}",
                "sha256": _digest(name),
            }
            for index, name in enumerate(names)
        ],
        "schema": "lumencore.public_site_release_manifest.v1",
        "source_commit": "a" * 40,
        "target_directory": "/opt/lumencore/dashboard",
    }


def _audit(manifest: dict[str, Any], statuses: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    commit = manifest["source_commit"]
    for file_row in manifest["files"]:
        name = file_row["archive_name"]
        expected = file_row["sha256"]
        status = statuses.get(name, "MATCH")
        row: dict[str, Any] = {
            "archive_name": name,
            "expected_sha256": expected,
            "status": status,
            "url": classifier.expected_live_url(name, commit),
        }
        if status == "ERROR":
            row["detail"] = "deterministic tabletop failure"
        else:
            row.update(
                {
                    "actual_sha256": expected if status == "MATCH" else _digest(name + "-drift"),
                    "bytes": file_row["bytes"],
                    "content_type": "text/plain",
                    "content_type_allowed": True,
                    "http_status": 200,
                }
            )
        rows.append(row)
    matched = sum(row["status"] == "MATCH" for row in rows)
    return {
        "base_url": "https://lumen-core.ai",
        "checked_at_utc": "2026-08-08T00:00:00Z",
        "expected_file_count": len(rows),
        "matched_file_count": matched,
        "release_verified": matched == len(rows),
        "results": rows,
        "schema": "lumencore.public_site_live_verification.v1",
        "source_commit": commit,
    }


def _require_text(path: Path, required: tuple[str, ...]) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ContinuityVerificationError(f"cannot read UTF-8 control file: {path}") from exc
    lowered = " ".join(text.lower().split())
    for phrase in required:
        if " ".join(phrase.lower().split()) not in lowered:
            raise ContinuityVerificationError(f"{path.name} missing required boundary: {phrase}")
    return text


def _verify_register(register: dict[str, Any]) -> None:
    domains = register.get("assurance_domains")
    if not isinstance(domains, list):
        raise ContinuityVerificationError("readiness assurance_domains is invalid")
    matches = [row for row in domains if isinstance(row, dict) and row.get("id") == "incident_response_and_continuity"]
    if len(matches) != 1:
        raise ContinuityVerificationError("incident readiness domain is missing or duplicated")
    domain = matches[0]
    if domain.get("status") != "documented_control":
        raise ContinuityVerificationError("incident readiness status must remain documented_control")
    evidence = domain.get("evidence_paths")
    if not isinstance(evidence, list) or not REQUIRED_REGISTER_EVIDENCE <= set(evidence):
        raise ContinuityVerificationError("incident readiness evidence binding is incomplete")
    negative = str(domain.get("does_not_prove", "")).lower()
    for phrase in ("tested live recovery", "customer notification", "external audit"):
        if phrase not in negative:
            raise ContinuityVerificationError(f"incident readiness negative boundary missing: {phrase}")


def verify(*, root: Path = ROOT, verified_utc: str) -> dict[str, Any]:
    root = root.resolve(strict=True)
    policy_path = root / POLICY_PATH.relative_to(ROOT)
    plan_path = root / PLAN_PATH.relative_to(ROOT)
    register_path = root / REGISTER_PATH.relative_to(ROOT)
    live_workflow_path = root / LIVE_WORKFLOW_PATH.relative_to(ROOT)
    readiness_workflow_path = root / READINESS_WORKFLOW_PATH.relative_to(ROOT)

    policy = classifier.read_json(policy_path)
    classifier.validate_policy(policy)
    register = classifier.read_json(register_path)
    _verify_register(register)
    _require_text(plan_path, REQUIRED_PLAN_TEXT)
    _require_text(live_workflow_path, REQUIRED_LIVE_WORKFLOW_TEXT)
    _require_text(readiness_workflow_path, REQUIRED_READINESS_WORKFLOW_TEXT)

    names = list(policy["critical_surfaces"]) + [
        "assets/lumencore.css",
        "assets/luma_command_fabric.js",
        "robots.txt",
        "sitemap.xml",
        "site.webmanifest",
    ]
    manifest = _manifest(names)
    scenarios = {
        "exact_release": ({}, "NONE", "MONITOR"),
        "critical_surface_drift": ({"operator_home.html": "MISMATCH"}, "SEV-2", "HOLD_PUBLIC_RELEASE_PROMOTION"),
        "threshold_drift": ({"robots.txt": "MISMATCH", "sitemap.xml": "ERROR", "site.webmanifest": "MISMATCH"}, "SEV-2", "HOLD_PUBLIC_RELEASE_PROMOTION"),
        "limited_noncritical_drift": ({"robots.txt": "ERROR"}, "SEV-3", "HOLD_AFFECTED_SURFACE_PROMOTION"),
    }
    outcomes: list[dict[str, Any]] = []
    for name, (statuses, expected_severity, expected_decision) in scenarios.items():
        result = classifier.classify(
            policy=deepcopy(policy),
            manifest=deepcopy(manifest),
            audit=_audit(manifest, statuses),
        )
        if result["severity"] != expected_severity or result["decision"] != expected_decision:
            raise ContinuityVerificationError(f"tabletop outcome drift: {name}")
        if result["production_mutation_performed"] or result["external_notification_performed"]:
            raise ContinuityVerificationError(f"unsafe automatic action in tabletop: {name}")
        outcomes.append(
            {
                "scenario": name,
                "severity": result["severity"],
                "decision": result["decision"],
                "affected_file_count": result["affected_file_count"],
                "incident_fingerprint_sha256": result["incident_fingerprint_sha256"],
            }
        )

    if policy["classification_contract"]["highest_automatic_severity"] != "SEV-2":
        raise ContinuityVerificationError("automatic SEV-1 promotion is not allowed")
    verified = _parse_utc(verified_utc)
    evidence_paths = [
        policy_path,
        plan_path,
        register_path,
        live_workflow_path,
        readiness_workflow_path,
        root / "code" / "ops" / "CLASSIFY_PUBLIC_RELEASE_INCIDENT.py",
        root / "code" / "ops" / "VERIFY_INCIDENT_RESPONSE_AND_CONTINUITY.py",
        root / "tests" / "test_public_release_incident_classifier.py",
    ]
    evidence = [
        {
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256_file(path),
        }
        for path in sorted(evidence_paths)
    ]
    receipt: dict[str, Any] = {
        "receipt_schema": "lumencore.incident_response_readiness.v1",
        "valid": True,
        "verified_utc": verified,
        "commit": _git_commit(root),
        "assurance_state": "documented_first_party_control_with_ci_exercise",
        "live_recovery_exercised": False,
        "enterprise_sla_established": False,
        "independent_audit_completed": False,
        "automatic_severity_cap": "SEV-2",
        "tabletop_scenarios": outcomes,
        "evidence": evidence,
    }
    receipt["receipt_sha256"] = classifier.canonical_sha256(receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument(
        "--verified-utc",
        default=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    )
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        receipt = verify(root=args.root, verified_utc=args.verified_utc)
    except (OSError, UnicodeError, json.JSONDecodeError, classifier.IncidentClassificationError, ContinuityVerificationError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, sort_keys=True), file=sys.stderr)
        return 1
    rendered = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8", newline="\n")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
