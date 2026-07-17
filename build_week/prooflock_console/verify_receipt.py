from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DEFAULT_RECEIPT = HERE / "sample_receipt.json"
ALLOWED_GATE_STATUSES = {"PASS", "FAIL", "OPEN", "NOT_APPLICABLE"}


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


def resolve_repo_path(relative_path: str, root: Path = ROOT) -> Path:
    candidate = (root / relative_path).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"artifact path escapes repository root: {relative_path}") from exc
    return candidate


def verify_receipt(receipt: dict[str, Any], root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if receipt.get("schema") != "lumencore.prooflock_receipt.v1":
        errors.append("unsupported or missing receipt schema")
    if not str(receipt.get("claim_boundary") or "").strip():
        errors.append("claim_boundary is required")

    expected_receipt_hash = str(receipt.get("receipt_sha256") or "").lower()
    computed_receipt_hash = stable_hash(receipt_payload(receipt))
    receipt_hash_matches = expected_receipt_hash == computed_receipt_hash
    if not receipt_hash_matches:
        errors.append("receipt_sha256 does not match the canonical receipt payload")

    artifacts: list[dict[str, Any]] = []
    for row in receipt.get("artifacts", []):
        relative_path = str(row.get("repo_relative_path") or "")
        expected_hash = str(row.get("expected_sha256") or "").lower()
        result = {
            "artifact_id": str(row.get("artifact_id") or ""),
            "repo_relative_path": relative_path,
            "expected_sha256": expected_hash,
            "observed_sha256": "",
            "bytes": 0,
            "exists": False,
            "hash_matches": False,
        }
        try:
            target = resolve_repo_path(relative_path, root)
        except ValueError as exc:
            errors.append(str(exc))
            artifacts.append(result)
            continue
        if not target.is_file():
            errors.append(f"artifact is missing: {relative_path}")
            artifacts.append(result)
            continue
        result["exists"] = True
        result["bytes"] = target.stat().st_size
        result["observed_sha256"] = file_sha256(target)
        result["hash_matches"] = result["observed_sha256"] == expected_hash
        if not result["hash_matches"]:
            errors.append(f"artifact hash mismatch: {relative_path}")
        artifacts.append(result)

    if not artifacts:
        errors.append("at least one artifact is required")

    gate_counts = {status: 0 for status in ALLOWED_GATE_STATUSES}
    required_open_or_failed: list[str] = []
    seen_gate_ids: set[str] = set()
    for gate in receipt.get("gates", []):
        gate_id = str(gate.get("gate_id") or "")
        status = str(gate.get("status") or "")
        required = bool(gate.get("required_for_promotion"))
        if not gate_id:
            errors.append("every gate requires gate_id")
        elif gate_id in seen_gate_ids:
            errors.append(f"duplicate gate_id: {gate_id}")
        seen_gate_ids.add(gate_id)
        if status not in ALLOWED_GATE_STATUSES:
            errors.append(f"invalid gate status for {gate_id or '<missing>'}: {status}")
            continue
        gate_counts[status] += 1
        if required and status != "PASS":
            required_open_or_failed.append(gate_id)

    if not receipt.get("gates"):
        errors.append("at least one gate is required")

    decision = str(receipt.get("decision") or "").upper()
    promotion_allowed = not required_open_or_failed and not errors
    if decision == "PROMOTE" and required_open_or_failed:
        errors.append("PROMOTE is prohibited while required gates are not PASS")
        promotion_allowed = False
    if decision not in {"HOLD", "PROMOTE", "REJECT"}:
        errors.append("decision must be HOLD, PROMOTE, or REJECT")

    if not receipt.get("limitations"):
        warnings.append("no limitations were recorded")

    return {
        "schema": "lumencore.prooflock_verification_report.v1",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "receipt_id": receipt.get("receipt_id"),
        "integrity_valid": not errors,
        "promotion_allowed": promotion_allowed,
        "recorded_decision": decision,
        "receipt_hash": {
            "expected": expected_receipt_hash,
            "computed": computed_receipt_hash,
            "matches": receipt_hash_matches,
        },
        "artifacts": artifacts,
        "artifact_count": len(artifacts),
        "artifact_hash_match_count": sum(1 for row in artifacts if row["hash_matches"]),
        "gate_counts": gate_counts,
        "required_open_or_failed_gates": required_open_or_failed,
        "errors": errors,
        "warnings": warnings,
        "claim_boundary": receipt.get("claim_boundary", ""),
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
    return 0 if report["integrity_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
