from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
import struct
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
    "baseline_contract",
    "held_out_evaluation",
    "independent_review",
    "human_release",
}
VERIFIER_DERIVED_GATE_IDS = {"artifact_hashes", "lineage_manifest"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
SAFE_ARTIFACT_PATTERN = re.compile(r"^assets/[A-Za-z0-9._/-]+$")
SCHEME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
RECEIPT_SCHEMA = "lumencore.prooflock_receipt.v1"
RECEIPT_SCHEMA_V2 = "lumencore.prooflock_receipt.v2"
CANONICALIZATION_V1 = "lumencore.prooflock_c14n.legacy.v1"
CANONICALIZATION_V2 = "lumencore.prooflock_c14n.binary64.v2"
MAX_SAFE_INTEGER = 2**53 - 1
MAX_JSON_TEXT = 2_000_000
MAX_DEPTH = 100


def serialization_profile(receipt: Any) -> str:
    schema = receipt.get("schema") if isinstance(receipt, dict) else None
    profile = CANONICALIZATION_V2 if schema == RECEIPT_SCHEMA_V2 else CANONICALIZATION_V1
    if isinstance(receipt, dict):
        if "canonicalization" in receipt and receipt["canonicalization"] != profile:
            raise ValueError("unsupported canonicalization profile")
        if schema == RECEIPT_SCHEMA_V2 and receipt.get("canonicalization") != profile:
            raise ValueError("v2 receipts require an explicit canonicalization profile")
    return profile


def scalar_string(value: str) -> str:
    if any(0xD800 <= ord(character) <= 0xDFFF for character in value):
        raise ValueError("unpaired Unicode surrogate is prohibited")
    return value


def canonical_json(payload: Any, profile: str | None = None) -> str:
    """V1's restricted legacy JSON or V2's explicitly tagged binary64 text."""
    profile = profile or serialization_profile(payload)
    if profile not in {CANONICALIZATION_V1, CANONICALIZATION_V2}:
        raise ValueError("unsupported canonicalization profile")

    def encode(value: Any, depth: int) -> str:
        if depth > MAX_DEPTH:
            raise ValueError("canonical payload exceeds the nesting limit")
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            scalar_string(value)
            if profile == CANONICALIZATION_V1 and "\x7f" in value:
                raise ValueError("v1 does not support DEL characters; use an explicit v2 receipt")
            return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
        if isinstance(value, (int, float)):
            if isinstance(value, int):
                if abs(value) > MAX_SAFE_INTEGER:
                    raise ValueError("nonfinite or unsafe integer number is prohibited")
            elif not math.isfinite(value) or (value.is_integer() and abs(value) > MAX_SAFE_INTEGER):
                raise ValueError("nonfinite or unsafe integer number is prohibited")
            if profile == CANONICALIZATION_V1:
                if not isinstance(value, int):
                    raise ValueError("v1 supports safe integer numbers only; use an explicit v2 receipt")
                return str(value)
            number = float(value)
            return "N" + struct.pack(">d", 0.0 if number == 0 else number).hex() + ";"
        if isinstance(value, list):
            return "[" + ",".join(encode(item, depth + 1) for item in value) + "]"
        if isinstance(value, dict):
            for key in value:
                if not isinstance(key, str):
                    raise ValueError("JSON object keys must be strings")
                scalar_string(key)
                if profile == CANONICALIZATION_V1 and any(ord(c) > 0x7E for c in key):
                    raise ValueError("v1 requires ASCII object keys; use an explicit v2 receipt")
            return "{" + ",".join(
                json.dumps(key, ensure_ascii=True) + ":" + encode(value[key], depth + 1)
                for key in sorted(value)
            ) + "}"
        raise ValueError("canonical payload must contain only JSON data types")

    return encode(payload, 0)


def strict_json_loads(text: str, profile: str | None = None) -> Any:
    if not isinstance(text, str) or len(text) > MAX_JSON_TEXT:
        raise ValueError("JSON input exceeds the text limit")
    try:
        if len(text.encode("utf-8")) > MAX_JSON_TEXT:
            raise ValueError("JSON input exceeds the text limit")
    except UnicodeEncodeError as exc:
        raise ValueError("unpaired Unicode surrogate is prohibited") from exc
    numeric_tokens: list[str] = []

    def number(token: str) -> int | float:
        numeric_tokens.append(token)
        if re.fullmatch(r"-?(?:0|[1-9][0-9]*)", token):
            value = int(token)
            if abs(value) > MAX_SAFE_INTEGER:
                raise ValueError("nonfinite or unsafe integer number is prohibited")
            return value
        value = float(token)
        if not math.isfinite(value) or (value.is_integer() and abs(value) > MAX_SAFE_INTEGER):
            raise ValueError("nonfinite or unsafe integer number is prohibited")
        return value

    def object_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in pairs:
            if key in output:
                raise ValueError(f"duplicate decoded JSON key: {key}")
            output[key] = value
        return output

    def invalid_constant(token: str) -> None:
        raise ValueError(f"nonfinite JSON number is prohibited: {token}")

    try:
        parsed = json.loads(text, parse_int=number, parse_float=number,
                            parse_constant=invalid_constant, object_pairs_hook=object_pairs)
    except RecursionError as exc:
        raise ValueError("JSON input exceeds the nesting limit") from exc
    schema = parsed.get("schema") if isinstance(parsed, dict) else None
    profile = profile or (CANONICALIZATION_V1 if schema == RECEIPT_SCHEMA else
                          CANONICALIZATION_V2 if schema == RECEIPT_SCHEMA_V2 else None)
    if profile == CANONICALIZATION_V1 and any(
        not re.fullmatch(r"-?(?:0|[1-9][0-9]*)", token) or token == "-0"
        for token in numeric_tokens
    ):
        raise ValueError("v1 raw JSON supports safe integer lexemes only; use an explicit v2 receipt")
    canonical_json(parsed, profile or CANONICALIZATION_V2)
    return parsed


def stable_hash(payload: Any, profile: str | None = None) -> str:
    return hashlib.sha256(canonical_json(payload, profile).encode("utf-8")).hexdigest()


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
    current = manifest_payloads.get("current_protocol_manifest")
    predecessor = manifest_payloads.get("predecessor_protocol_manifest")
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

    if safe_receipt.get("schema") not in {RECEIPT_SCHEMA, RECEIPT_SCHEMA_V2}:
        integrity_errors.append("unsupported or missing receipt schema")
    if not str(safe_receipt.get("claim_boundary") or "").strip():
        integrity_errors.append("claim_boundary is required")

    expected_receipt_hash = str(safe_receipt.get("receipt_sha256") or "").lower()
    computed_receipt_hash = ""
    profile = ""
    try:
        profile = serialization_profile(safe_receipt)
        computed_receipt_hash = stable_hash(receipt_payload(safe_receipt), profile)
    except (ValueError, TypeError, RecursionError) as exc:
        integrity_errors.append(f"unsupported canonical receipt payload: {exc}")
    receipt_hash_matches = bool(computed_receipt_hash) and expected_receipt_hash == computed_receipt_hash
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
            "current_protocol_manifest",
            "predecessor_protocol_manifest",
        }:
            try:
                parsed_manifest = strict_json_loads(target.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, ValueError):
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
        "serialization_profile": profile,
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
    receipt = strict_json_loads(path.read_text(encoding="utf-8"))
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    receipt["receipt_sha256"] = stable_hash(receipt_payload(receipt))
    path.write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a ProofLock receipt and its repository artifacts.")
    parser.add_argument("receipt", nargs="?", type=Path, default=DEFAULT_RECEIPT)
    parser.add_argument("--write-hash", action="store_true", help="Explicitly recompute receipt_sha256 in the declared schema; no v1 migration or ambiguous-number resealing.")
    args = parser.parse_args()

    path = args.receipt.resolve()
    try:
        receipt = write_receipt_hash(path) if args.write_hash else strict_json_loads(path.read_text(encoding="utf-8"))
        report = verify_receipt(receipt)
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        report = {"schema": "lumencore.prooflock_verification_report.v1", "integrity_valid": False,
                  "policy_valid": False, "promotion_allowed": False, "errors": [str(exc)]}
    print(json.dumps(report, indent=2, ensure_ascii=True))
    return 0 if report["integrity_valid"] and report["policy_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
