from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "external_validation_authority_docket_v1.json"
SCRIPT_PATH = Path(__file__).resolve()
TEST_PATH = ROOT / "tests" / "test_external_validation_authority_docket.py"
OUT_JSON = (
    ROOT
    / "evidence"
    / "external_validation"
    / "eia_router_validation_authority_docket_20260714.json"
)
OUT_MD = ROOT / "docs" / "EXTERNAL_VALIDATION_AUTHORITY_DOCKET_2026-07-14.md"

CHECKSUM_PATTERN = re.compile(
    r"^(?P<digest>[0-9a-f]{64})  out/reproducibility/ci/(?P<path>.+)$"
)
PRIVATE_PATTERNS = (
    re.compile(r"[A-Za-z]:[/\\]Users[/\\]", re.I),
    re.compile(r"private_estate", re.I),
    re.compile(r"cp575notice", re.I),
    re.compile(
        r"(?:api|access|refresh|client)[_-]?(?:key|token|secret)"
        r"\s*[:=]\s*[\"']?[^\s\"']{8,}",
        re.I,
    ),
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path, *, required: bool = True) -> dict[str, Any]:
    if not path.is_file():
        if required:
            raise FileNotFoundError(path)
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected a JSON object at {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def repo_path(path: Path, *, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def scan_private(value: Any) -> list[str]:
    text = json.dumps(value, sort_keys=True, default=str)
    return [pattern.pattern for pattern in PRIVATE_PATTERNS if pattern.search(text)]


def artifact_row(path: Path, *, root: Path = ROOT) -> dict[str, Any]:
    return {
        "path": repo_path(path, root=root),
        "bytes": path.stat().st_size,
        "sha256": file_sha256(path),
    }


def parse_checksum_manifest(manifest_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line_number, line in enumerate(
        manifest_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        match = CHECKSUM_PATTERN.fullmatch(line.strip())
        if not match:
            raise ValueError(f"malformed checksum manifest line {line_number}")
        relative = Path(match.group("path"))
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"unsafe checksum path on line {line_number}")
        if relative.name == "SHA256SUMS":
            raise ValueError("checksum manifest must not hash itself")
        rows.append(
            {
                "path": relative.as_posix(),
                "sha256": match.group("digest"),
            }
        )
    if not rows:
        raise ValueError("checksum manifest is empty")
    return rows


def verify_ci_bundle(
    bundle_dir: Path, config: dict[str, Any], *, root: Path = ROOT
) -> dict[str, Any]:
    manifest_path = bundle_dir / "SHA256SUMS"
    if not manifest_path.is_file():
        return {
            "available": False,
            "verified": False,
            "reason": "checksum_manifest_missing",
        }

    rows = parse_checksum_manifest(manifest_path)
    verified_rows: list[dict[str, Any]] = []
    for row in rows:
        path = bundle_dir / Path(row["path"])
        actual = file_sha256(path) if path.is_file() else None
        verified_rows.append(
            {
                **row,
                "bytes": path.stat().st_size if path.is_file() else None,
                "actual_sha256": actual,
                "passed": actual == row["sha256"],
            }
        )

    listed = {row["path"] for row in rows}
    present = {
        path.relative_to(bundle_dir).as_posix()
        for path in bundle_dir.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS"
    }
    archive_text = "\n".join(
        (bundle_dir / Path(relative)).read_text(encoding="utf-8", errors="replace")
        for relative in sorted(present)
    )
    archive_private_hits = scan_private(archive_text)
    receipt_path = bundle_dir / "reviewer_reproducibility_receipt.json"
    receipt = read_json(receipt_path, required=False)
    expected = config["clean_runner_verification"]
    receipt_summary = receipt.get("summary", {})
    identity_checks = {
        "status_passed": receipt.get("status") == "BOUNDED_REPRODUCIBILITY_PASS",
        "commit_matched": receipt.get("git", {}).get("commit") == expected["commit"],
        "capsule_hash_matched": receipt.get("capsule_sha256")
        == expected["receipt_capsule_sha256"],
        "source_clean": receipt_summary.get("relevant_source_clean") is True,
        "clean_runner": receipt_summary.get("clean_runner_replay") is True,
        "dependency_versions_matched": receipt_summary.get(
            "dependency_versions_exact_match"
        )
        is True,
        "all_suites_passed": receipt_summary.get("suite_count")
        == receipt_summary.get("suite_pass_count")
        == 3,
        "all_assertions_passed": receipt_summary.get("assertion_count")
        == receipt_summary.get("assertion_pass_count")
        == 31,
        "privacy_scan_passed": receipt.get("privacy_scan", {}).get("passed") is True,
        "archive_privacy_scan_passed": not archive_private_hits,
    }
    checksums_passed = bool(verified_rows) and all(
        row["passed"] for row in verified_rows
    )
    complete_coverage = listed == present
    verified = checksums_passed and complete_coverage and all(identity_checks.values())
    try:
        archive_path = repo_path(bundle_dir, root=root)
    except ValueError:
        archive_path = "external_verified_source"
    return {
        "available": True,
        "verified": verified,
        "archive_path": archive_path,
        "manifest_sha256": file_sha256(manifest_path),
        "checksum_entry_count": len(rows),
        "checksum_pass_count": sum(1 for row in verified_rows if row["passed"]),
        "complete_file_coverage": complete_coverage,
        "archive_privacy_pattern_hit_count": len(archive_private_hits),
        "identity_checks": identity_checks,
        "files": verified_rows,
        "receipt_projection": {
            "status": receipt.get("status"),
            "commit": receipt.get("git", {}).get("commit"),
            "capsule_sha256": receipt.get("capsule_sha256"),
            "suite_pass_count": receipt_summary.get("suite_pass_count"),
            "suite_count": receipt_summary.get("suite_count"),
            "assertion_pass_count": receipt_summary.get("assertion_pass_count"),
            "assertion_count": receipt_summary.get("assertion_count"),
            "sbom_component_count": receipt_summary.get("sbom_component_count"),
            "external_validation_complete": receipt_summary.get(
                "external_validation_complete"
            ),
            "agency_certification_complete": receipt_summary.get(
                "agency_certification_complete"
            ),
        },
    }


def archive_ci_bundle(source_dir: Path, archive_dir: Path, config: dict[str, Any]) -> None:
    source_receipt = verify_ci_bundle(source_dir, config)
    if not source_receipt.get("verified"):
        raise ValueError("source CI bundle failed verification")
    archive_dir.mkdir(parents=True, exist_ok=True)
    manifest = source_dir / "SHA256SUMS"
    shutil.copy2(manifest, archive_dir / manifest.name)
    for row in parse_checksum_manifest(manifest):
        source = source_dir / Path(row["path"])
        target = archive_dir / Path(row["path"])
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    archived = verify_ci_bundle(archive_dir, config)
    if not archived.get("verified"):
        raise ValueError("archived CI bundle failed post-copy verification")


def project_runtime_status(
    runtime_path: Path, expected_protocol_sha256: str
) -> dict[str, Any]:
    status = read_json(runtime_path, required=False)
    if not status:
        return {
            "available": False,
            "state": "RUNTIME_SNAPSHOT_UNAVAILABLE",
            "protocol_identity_matched": False,
            "prediction_count": 0,
            "settlement_count": 0,
            "common_settled_day_count": 0,
            "promotion_evaluation_complete": False,
            "confirmatory_gate_passed": False,
            "external_partner_replication_complete": False,
        }
    safe_keys = (
        "schema",
        "generated_utc",
        "state",
        "prediction_count",
        "prediction_count_by_authority",
        "settlement_count",
        "settlement_count_by_authority",
        "common_settled_day_count",
        "first_common_settled_date",
        "latest_common_settled_date",
        "sample_gates",
        "promotion_evaluation_complete",
        "confirmatory_gate_passed",
        "external_partner_replication_complete",
        "operational_receipt_sha256",
        "protocol_sha256",
        "protocol_commit",
    )
    projection = {key: status.get(key) for key in safe_keys if key in status}
    projection.update(
        {
            "available": True,
            "snapshot_sha256": file_sha256(runtime_path),
            "protocol_identity_matched": status.get("protocol_sha256")
            == expected_protocol_sha256,
        }
    )
    return projection


def derive_maturity(
    runtime: dict[str, Any],
    *,
    evaluator_signoff_complete: bool = False,
    independent_hash_verification_complete: bool = False,
) -> dict[str, Any]:
    sample_gates = runtime.get("sample_gates") or {}
    level_4 = bool(
        runtime.get("available")
        and runtime.get("protocol_identity_matched")
        and sample_gates.get("confirmatory_90_days_ready")
        and runtime.get("promotion_evaluation_complete")
        and runtime.get("confirmatory_gate_passed")
    )
    level_5 = bool(
        level_4
        and sample_gates.get("durability_180_days_ready")
        and runtime.get("external_partner_replication_complete")
        and evaluator_signoff_complete
        and independent_hash_verification_complete
    )
    return {
        "current_supported_level": 5 if level_5 else 4 if level_4 else 3,
        "level_4_gate_passed": level_4,
        "level_5_gate_passed": level_5,
        "external_validation_complete": level_5,
        "independent_evaluator_signoff_complete": evaluator_signoff_complete,
        "independent_hash_verification_complete": (
            independent_hash_verification_complete
        ),
    }


def derive_status(
    *, integrity_passed: bool, runtime: dict[str, Any], maturity: dict[str, Any]
) -> str:
    if not integrity_passed:
        return "EXTERNAL_VALIDATION_DOCKET_FAIL_CLOSED"
    if maturity["level_5_gate_passed"]:
        return "LEVEL_5_EXTERNAL_VALIDATION_COMPLETE"
    if maturity["level_4_gate_passed"]:
        return "LEVEL_4_EVIDENCE_READY_EXTERNAL_REPLICATION_REQUIRED"
    if not runtime.get("available"):
        return "EVALUATOR_DOCKET_READY_RUNTIME_SNAPSHOT_UNAVAILABLE"
    if int(runtime.get("prediction_count") or 0) == 0:
        return "PROSPECTIVE_COLLECTION_ACTIVE_AWAITING_FIRST_ELIGIBLE_SEAL"
    return "PROSPECTIVE_COLLECTION_ACTIVE_BELOW_LEVEL_4_GATE"


def build_payload(
    *,
    root: Path = ROOT,
    generated_utc: str | None = None,
) -> dict[str, Any]:
    config_path = root / CONFIG_PATH.relative_to(ROOT)
    config = read_json(config_path)
    lane = config["evidence_lane"]
    protocol_path = root / lane["protocol_path"]
    protocol = read_json(protocol_path)
    protocol_sha256 = file_sha256(protocol_path)
    archive_dir = root / config["clean_runner_verification"]["archive_path"]
    ci_bundle = verify_ci_bundle(archive_dir, config, root=root)
    runtime_path = root / lane["runtime_status_path"]
    runtime = project_runtime_status(runtime_path, protocol_sha256)

    source_paths = [
        config_path,
        root / SCRIPT_PATH.relative_to(ROOT),
        root / TEST_PATH.relative_to(ROOT),
        *(root / value for value in config["portable_input_paths"]),
    ]
    unique_paths = list(dict.fromkeys(path.resolve() for path in source_paths))
    artifacts = [artifact_row(path, root=root) for path in unique_paths]
    protocol_identity = {
        "schema_matched": protocol.get("schema")
        == "eia_grid_prospective_hybrid_router_protocol.v1",
        "first_allowed_target_matched": protocol.get("prospective_window", {}).get(
            "first_allowed_target_date"
        )
        == lane["first_allowed_target_date"],
        "backfill_blocked": protocol.get("prospective_window", {}).get(
            "backfilled_predictions_allowed"
        )
        is False,
        "dynamic_override_blocked": protocol.get("router", {}).get(
            "dynamic_override_allowed"
        )
        is False,
    }
    evaluator_acceptance = {
        field: None
        for field in config["evaluator_authority_contract"][
            "required_identity_fields"
        ]
    }
    evaluator_acceptance["complete"] = False
    maturity = derive_maturity(runtime)
    runtime_protocol_identity_passed = bool(
        not runtime.get("available") or runtime.get("protocol_identity_matched")
    )
    integrity_passed = (
        bool(ci_bundle.get("verified"))
        and all(protocol_identity.values())
        and runtime_protocol_identity_passed
    )
    status = derive_status(
        integrity_passed=integrity_passed,
        runtime=runtime,
        maturity=maturity,
    )
    payload: dict[str, Any] = {
        "schema": "external_validation_authority_docket.v1",
        "protocol_id": config["protocol_id"],
        "generated_utc": generated_utc or now_utc(),
        "status": status,
        "summary": {
            "integrity_gate_passed": integrity_passed,
            "portable_input_count": len(artifacts),
            "clean_runner_bundle_verified": bool(ci_bundle.get("verified")),
            "prospective_runtime_snapshot_available": runtime.get("available", False),
            "prediction_count": int(runtime.get("prediction_count") or 0),
            "settlement_count": int(runtime.get("settlement_count") or 0),
            "common_settled_day_count": int(
                runtime.get("common_settled_day_count") or 0
            ),
            "current_supported_level": maturity["current_supported_level"],
            "level_4_gate_passed": maturity["level_4_gate_passed"],
            "level_5_gate_passed": maturity["level_5_gate_passed"],
            "external_validation_complete": maturity[
                "external_validation_complete"
            ],
            "independent_evaluator_named": False,
            "ready_to_invite_independent_evaluator": integrity_passed,
            "agency_certification_complete": False,
            "field_validation_complete": False,
            "realized_savings_claim_allowed": False,
        },
        "evidence_lane": {
            **lane,
            "protocol_sha256": protocol_sha256,
            "protocol_commit": runtime.get("protocol_commit"),
            "claim_boundary": protocol.get("claim_boundary"),
        },
        "protocol_identity_checks": protocol_identity,
        "prospective_runtime_snapshot": runtime,
        "clean_runner_bundle": ci_bundle,
        "portable_inputs": artifacts,
        "portable_input_chain_sha256": canonical_sha256(artifacts),
        "maturity": maturity,
        "maturity_gates": config["maturity_gates"],
        "evaluator_acceptance": evaluator_acceptance,
        "evaluator_authority_contract": config["evaluator_authority_contract"],
        "reviewer_decision_request": config["reviewer_decision_request"],
        "reviewer_handoff_steps": [
            "Rehash every portable input and every archived clean-runner artifact.",
            "Review the frozen EIA protocol before inspecting prospective outcomes.",
            "Complete identity, authority, and conflict-of-interest fields without operator substitution.",
            "Observe prediction seals and settlements through the agreed evaluation window.",
            "Inspect all routes, fallbacks, exclusions, negative results, and chain-verification events.",
            "Independently reproduce the final metric and statistical decision.",
            "Sign only the maturity level supported by the complete evidence record.",
        ],
        "nist_ai_rmf_informative_crosswalk": config[
            "nist_ai_rmf_informative_crosswalk"
        ],
        "standards_references": config["standards_references"],
        "claim_boundary": config["claim_boundary"],
    }
    private_hits = scan_private(payload)
    payload["privacy_scan"] = {
        "passed": not private_hits,
        "configured_pattern_hit_count": len(private_hits),
    }
    if private_hits:
        payload["status"] = "EXTERNAL_VALIDATION_DOCKET_FAIL_CLOSED"
        payload["summary"]["integrity_gate_passed"] = False
        payload["summary"]["ready_to_invite_independent_evaluator"] = False
    payload["docket_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    runtime = payload["prospective_runtime_snapshot"]
    lines = [
        "# External Validation Authority Docket",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["claim_boundary"],
        "",
        "## Decision",
        "",
        f"- Status: `{payload['status']}`",
        f"- Requested decision: {payload['reviewer_decision_request']['decision']}",
        f"- Fundable scope: {payload['reviewer_decision_request']['fundable_scope']}",
        f"- Docket SHA-256: `{payload['docket_sha256']}`",
        "",
        "## Current Evidence",
        "",
        f"- Current supported level: `{summary['current_supported_level']}`",
        f"- Level 4 gate passed: `{str(summary['level_4_gate_passed']).lower()}`",
        f"- Level 5 gate passed: `{str(summary['level_5_gate_passed']).lower()}`",
        f"- External validation complete: `{str(summary['external_validation_complete']).lower()}`",
        f"- Independent evaluator named: `{str(summary['independent_evaluator_named']).lower()}`",
        f"- Clean-runner bundle verified: `{str(summary['clean_runner_bundle_verified']).lower()}`",
        f"- Predictions sealed: `{summary['prediction_count']}`",
        f"- Settlements recorded: `{summary['settlement_count']}`",
        f"- Common settled days: `{summary['common_settled_day_count']}`",
        f"- Runtime state: `{runtime.get('state')}`",
        "",
        "## Evaluator Handoff",
        "",
    ]
    for index, step in enumerate(payload["reviewer_handoff_steps"], start=1):
        lines.append(f"{index}. {step}")
    lines.extend(["", "## Maturity Gates", ""])
    level_4 = payload["maturity_gates"]["level_4"]
    level_5 = payload["maturity_gates"]["level_5"]
    lines.extend(
        [
            f"- Level 4: at least `{level_4['minimum_common_settled_days_per_authority']}` common settled days per authority plus the complete confirmatory gate.",
            f"- Level 5: at least `{level_5['minimum_common_settled_days_per_authority']}` common settled days per authority, Level 4, independent replication, hash verification, conflict disclosure, and evaluator signoff.",
            "",
            "## NIST AI RMF Informative Crosswalk",
            "",
            "This is a voluntary, informative mapping. It is not a NIST certification or conformity assessment.",
            "",
            "| Function | Implemented control | Remaining gap |",
            "| --- | --- | --- |",
        ]
    )
    for row in payload["nist_ai_rmf_informative_crosswalk"]:
        lines.append(
            f"| `{row['function']}` | {row['implemented_control']} | {row['remaining_gap']} |"
        )
    lines.extend(["", "## Official References", ""])
    for row in payload["standards_references"]:
        lines.append(f"- [{row['name']}]({row['url']}): {row['use']}")
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any]) -> None:
    write_json(OUT_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-ci-dir", type=Path)
    parser.add_argument("--check-only", action="store_true")
    args = parser.parse_args()

    config = read_json(CONFIG_PATH)
    archive_dir = ROOT / config["clean_runner_verification"]["archive_path"]
    if args.archive_ci_dir:
        archive_ci_bundle(args.archive_ci_dir.resolve(), archive_dir, config)

    payload = build_payload()
    if not args.check_only:
        write_outputs(payload)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "integrity_gate_passed": payload["summary"][
                    "integrity_gate_passed"
                ],
                "clean_runner_bundle_verified": payload["summary"][
                    "clean_runner_bundle_verified"
                ],
                "current_supported_level": payload["summary"][
                    "current_supported_level"
                ],
                "prediction_count": payload["summary"]["prediction_count"],
                "docket_sha256": payload["docket_sha256"],
            },
            indent=2,
        )
    )
    return 0 if payload["summary"]["integrity_gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
