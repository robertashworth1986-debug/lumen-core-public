from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_RECEIPT = HERE / "sample_receipt.json"
ALLOWED_GATE_STATUSES = {"PASS", "FAIL", "OPEN", "NOT_APPLICABLE"}
ALLOWED_DECISIONS = {"HOLD", "PROMOTE", "REJECT"}
CANONICAL_REQUIRED_GATE_IDS = {
    "artifact_hashes",
    "lineage_manifest",
    "engineering_cad",
    "prototype_test",
    "qualified_safety_review",
    "human_release",
}
VERIFIER_DERIVED_GATE_IDS = {"artifact_hashes", "lineage_manifest"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SAFE_ARTIFACT_PATTERN = re.compile(r"^assets/[A-Za-z0-9._/-]+$")
SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def receipt_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    payload.pop("receipt_sha256", None)
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_artifact_path(relative_path: str) -> str:
    if not isinstance(relative_path, str) or not relative_path or relative_path != relative_path.strip():
        raise ValueError("artifact path is missing or malformed")
    if "\\" in relative_path or "\0" in relative_path or relative_path.startswith("/"):
        raise ValueError(f"unsafe artifact path: {relative_path}")
    if SCHEME_PATTERN.match(relative_path):
        raise ValueError(f"unsafe artifact path: {relative_path}")
    try:
        decoded = unquote(relative_path, errors="strict")
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"invalid encoded artifact path: {relative_path}") from exc
    if decoded != relative_path:
        raise ValueError(f"encoded artifact path is prohibited: {relative_path}")
    segments = relative_path.split("/")
    if any(not segment or segment in {".", ".."} for segment in segments):
        raise ValueError(f"artifact path traversal is prohibited: {relative_path}")
    if not SAFE_ARTIFACT_PATTERN.fullmatch(relative_path):
        raise ValueError(f"only repository assets/ paths are allowed: {relative_path}")
    return relative_path


def resolve_repo_path(relative_path: str, root: Path = ROOT) -> Path:
    normalized = normalize_artifact_path(relative_path)
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact path escapes repository root: {relative_path}") from exc
    return candidate


def derive_lineage_status(
    receipt: dict[str, Any], manifest_payloads: dict[str, dict[str, Any]]
) -> tuple[str, str]:
    current = manifest_payloads.get("current_concept_manifest")
    predecessor = manifest_payloads.get("predecessor_concept_manifest")
    lineage = receipt.get("lineage")
    subject = receipt.get("subject")
    failures: list[str] = []

    if not isinstance(current, dict):
        failures.append("current concept manifest is missing or invalid JSON")
    if not isinstance(predecessor, dict):
        failures.append("predecessor concept manifest is missing or invalid JSON")
    if not isinstance(lineage, dict):
        failures.append("receipt lineage must be an object")
        lineage = {}
    if not isinstance(subject, dict):
        failures.append("receipt subject must be an object")
        subject = {}

    if not failures:
        current_id = str(current.get("asset_id") or "")
        predecessor_id = str(predecessor.get("asset_id") or "")
        declared_current_id = str(lineage.get("current_asset_id") or "")
        declared_predecessor_id = str(lineage.get("predecessor_asset_id") or "")
        if not current_id or current_id != declared_current_id:
            failures.append("current manifest asset_id does not match receipt lineage")
        if not predecessor_id or predecessor_id != declared_predecessor_id:
            failures.append("predecessor manifest asset_id does not match receipt lineage")
        if str(current.get("supersedes_asset_id") or "") != predecessor_id:
            failures.append("current manifest does not supersede the predecessor asset_id")
        if str(subject.get("asset_id") or "") != current_id:
            failures.append("receipt subject does not match the current manifest asset_id")
        provenance = current.get("generation_provenance")
        if not isinstance(provenance, dict) or str(provenance.get("input_asset_id") or "") != predecessor_id:
            failures.append("current manifest provenance does not reference the predecessor asset_id")

    if failures:
        return "FAIL", "; ".join(failures)
    return (
        "PASS",
        "Verifier parsed both hash-matched manifests and confirmed the declared current, predecessor, supersession, subject, and generation-provenance identifiers.",
    )


def verify_receipt(receipt: Any, root: Path = ROOT) -> dict[str, Any]:
    integrity_errors: list[str] = []
    policy_errors: list[str] = []
    warnings: list[str] = []
    receipt_is_object = isinstance(receipt, dict)
    safe_receipt: dict[str, Any] = receipt if receipt_is_object else {}

    if not receipt_is_object:
        integrity_errors.append("receipt must be an object")

    if safe_receipt.get("schema") != "lumencore.prooflock_receipt.v1":
        integrity_errors.append("unsupported or missing receipt schema")
    if not str(safe_receipt.get("claim_boundary") or "").strip():
        integrity_errors.append("claim_boundary is required")

    expected_receipt_hash = str(safe_receipt.get("receipt_sha256") or "").lower()
    computed_receipt_hash = stable_hash(receipt_payload(safe_receipt))
    receipt_hash_matches = expected_receipt_hash == computed_receipt_hash
    if not receipt_hash_matches:
        integrity_errors.append("receipt_sha256 does not match the canonical receipt payload")

    artifact_rows = safe_receipt.get("artifacts")
    if not isinstance(artifact_rows, list):
        integrity_errors.append("artifacts must be an array")
        artifact_rows = []
    artifacts: list[dict[str, Any]] = []
    manifest_payloads: dict[str, dict[str, Any]] = {}
    seen_artifact_ids: set[str] = set()
    for index, row in enumerate(artifact_rows):
        row_is_object = isinstance(row, dict)
        safe_row: dict[str, Any] = row if row_is_object else {}
        if not row_is_object:
            integrity_errors.append(f"artifact row {index} must be an object")
        relative_path = str(safe_row.get("repo_relative_path") or "")
        expected_hash = str(safe_row.get("expected_sha256") or "").lower()
        artifact_id = str(safe_row.get("artifact_id") or "")
        result = {
            "artifact_id": artifact_id,
            "role": str(safe_row.get("role") or ""),
            "repo_relative_path": relative_path,
            "expected_sha256": expected_hash,
            "observed_sha256": "",
            "bytes": 0,
            "exists": False,
            "hash_matches": False,
        }
        if not artifact_id or artifact_id in seen_artifact_ids:
            integrity_errors.append(f"missing or duplicate artifact_id: {artifact_id or '<missing>'}")
        seen_artifact_ids.add(artifact_id)
        if not SHA256_PATTERN.fullmatch(expected_hash):
            integrity_errors.append(f"invalid expected_sha256: {artifact_id or '<missing>'}")
            artifacts.append(result)
            continue
        try:
            target = resolve_repo_path(relative_path, root)
        except ValueError as exc:
            integrity_errors.append(str(exc))
            artifacts.append(result)
            continue
        if not target.is_file():
            integrity_errors.append(f"artifact is missing: {relative_path}")
            artifacts.append(result)
            continue
        result["exists"] = True
        result["bytes"] = target.stat().st_size
        result["observed_sha256"] = file_sha256(target)
        result["hash_matches"] = result["observed_sha256"] == expected_hash
        if not result["hash_matches"]:
            integrity_errors.append(f"artifact hash mismatch: {relative_path}")
        elif result["role"] in {
            "current_concept_manifest",
            "predecessor_concept_manifest",
        }:
            try:
                parsed_manifest = json.loads(target.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                parsed_manifest = None
            if isinstance(parsed_manifest, dict):
                manifest_payloads[result["role"]] = parsed_manifest
        artifacts.append(result)

    if not artifact_rows:
        integrity_errors.append("at least one artifact is required")

    artifact_status = (
        "PASS"
        if artifacts and len(artifacts) == len(artifact_rows) and all(row["hash_matches"] for row in artifacts)
        else "FAIL"
    )
    lineage_status, lineage_basis = derive_lineage_status(safe_receipt, manifest_payloads)
    derived_gates = {
        "artifact_hashes": (
            artifact_status,
            f"Verifier rehashed {sum(1 for row in artifacts if row['hash_matches'])}/{len(artifacts)} declared repository artifacts.",
        ),
        "lineage_manifest": (lineage_status, lineage_basis),
    }

    gate_counts = {status: 0 for status in ALLOWED_GATE_STATUSES}
    recorded_gate_counts = {status: 0 for status in ALLOWED_GATE_STATUSES}
    required_open_or_failed: list[str] = []
    seen_gate_ids: set[str] = set()
    gate_reports: list[dict[str, Any]] = []
    gates = safe_receipt.get("gates")
    if not isinstance(gates, list):
        integrity_errors.append("gates must be an array")
        gates = []
    for index, gate in enumerate(gates):
        gate_is_object = isinstance(gate, dict)
        safe_gate: dict[str, Any] = gate if gate_is_object else {}
        if not gate_is_object:
            integrity_errors.append(f"gate row {index} must be an object")
        gate_id = str(safe_gate.get("gate_id") or "")
        recorded_status = str(safe_gate.get("status") or "")
        required = bool(safe_gate.get("required_for_promotion"))
        if not gate_id or gate_id in seen_gate_ids:
            integrity_errors.append(f"missing or duplicate gate_id: {gate_id or '<missing>'}")
        seen_gate_ids.add(gate_id)
        if gate_id in CANONICAL_REQUIRED_GATE_IDS and not required:
            integrity_errors.append(f"canonical gate must remain required for promotion: {gate_id}")

        if recorded_status not in ALLOWED_GATE_STATUSES:
            integrity_errors.append(
                f"invalid gate status for {gate_id or '<missing>'}: {recorded_status}"
            )
            effective_status = "FAIL"
            authority_source = "INVALID_RECEIPT_DECLARATION"
            verification_basis = "The recorded status is outside the receipt contract."
        elif gate_id in VERIFIER_DERIVED_GATE_IDS:
            recorded_gate_counts[recorded_status] += 1
            effective_status, verification_basis = derived_gates[gate_id]
            authority_source = "VERIFIER_DERIVED"
            if recorded_status != effective_status:
                warnings.append(
                    f"recorded {recorded_status} for {gate_id} was replaced by verifier-derived {effective_status}"
                )
        elif recorded_status == "PASS":
            recorded_gate_counts[recorded_status] += 1
            effective_status = "OPEN"
            authority_source = "UNTRUSTED_RECEIPT_DECLARATION"
            verification_basis = (
                "Recorded PASS was not accepted because this gate requires evidence from a trusted external or human authority verifier."
            )
            if required:
                policy_errors.append(
                    f"required gate {gate_id or '<missing>'} has no verifier-supported authority; recorded PASS was not accepted"
                )
        else:
            recorded_gate_counts[recorded_status] += 1
            effective_status = recorded_status
            authority_source = "RECORDED_HOLD_OR_FAILURE"
            verification_basis = (
                "A self-authored receipt may preserve a hold or failure, but it cannot mint a PASS for this authority gate."
            )

        gate_counts[effective_status] += 1
        gate_reports.append(
            {
                "gate_id": gate_id,
                "label": str(safe_gate.get("label") or ""),
                "status": effective_status,
                "recorded_status": recorded_status,
                "effective_status": effective_status,
                "required_for_promotion": required,
                "basis": str(safe_gate.get("basis") or ""),
                "authority_source": authority_source,
                "verification_basis": verification_basis,
            }
        )
        if required and effective_status != "PASS":
            required_open_or_failed.append(gate_id)

    if not gates:
        integrity_errors.append("at least one gate is required")

    missing_canonical_gates = sorted(CANONICAL_REQUIRED_GATE_IDS - seen_gate_ids)
    if missing_canonical_gates:
        integrity_errors.append(
            "missing canonical required gates: " + ", ".join(missing_canonical_gates)
        )

    decision = str(safe_receipt.get("decision") or "").upper()
    if decision == "PROMOTE" and required_open_or_failed:
        policy_errors.append(
            "PROMOTE is prohibited while required effective gates are not PASS"
        )
    if decision not in ALLOWED_DECISIONS:
        integrity_errors.append("decision must be HOLD, PROMOTE, or REJECT")

    limitations = safe_receipt.get("limitations")
    if not isinstance(limitations, list) or not limitations:
        warnings.append("no limitations were recorded")

    integrity_valid = not integrity_errors
    policy_valid = not policy_errors
    errors = [*integrity_errors, *policy_errors]
    return {
        "schema": "lumencore.prooflock_verification_report.v1",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "receipt_id": safe_receipt.get("receipt_id"),
        "integrity_valid": integrity_valid,
        "policy_valid": policy_valid,
        "promotion_allowed": (
            decision == "PROMOTE"
            and not required_open_or_failed
            and integrity_valid
            and policy_valid
        ),
        "recorded_decision": decision,
        "receipt_hash": {
            "expected": expected_receipt_hash,
            "computed": computed_receipt_hash,
            "matches": receipt_hash_matches,
        },
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifact_hash_match_count": sum(1 for row in artifacts if row["hash_matches"]),
        "gates": gate_reports,
        "gate_counts": gate_counts,
        "recorded_gate_counts": recorded_gate_counts,
        "required_open_or_failed_gates": required_open_or_failed,
        "integrity_errors": integrity_errors,
        "policy_errors": policy_errors,
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": safe_receipt.get("claim_boundary", ""),
    }


def write_receipt_hash(path: Path) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    receipt["receipt_sha256"] = stable_hash(receipt_payload(receipt))
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a ProofLock receipt and its repository artifacts.")
    parser.add_argument("receipt", nargs="?", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--write-hash", action="store_true", help="Recompute receipt_sha256 before verification.")
    args = parser.parse_args()

    path = args.receipt.resolve()
    receipt = write_receipt_hash(path) if args.write_hash else json.loads(path.read_text(encoding="utf-8"))
    report = verify_receipt(receipt)
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["integrity_valid"] and report["policy_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
