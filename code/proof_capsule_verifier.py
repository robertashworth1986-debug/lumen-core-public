#!/usr/bin/env python3
"""Validate a public-safe LumenCore Proof Capsule and verify referenced file hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

TOP_LEVEL_FIELDS = {
    "capsule_id",
    "title",
    "module",
    "evidence_type",
    "source",
    "baseline",
    "locked_metric",
    "run",
    "manifest",
    "result",
    "claim_boundary",
    "pilot_decision",
}
EVIDENCE_TYPES = {
    "measured",
    "replay",
    "synthetic",
    "modeled",
    "estimated",
    "conceptual",
    "externally_validated",
}
RUN_TYPES = {"measured", "replay", "synthetic", "bench", "modeled"}
PILOT_STATUSES = {"promote", "rerun", "external_review", "hold", "reject"}
FORBIDDEN_PROMOTION_PHRASES = {
    "guaranteed roi",
    "guaranteed savings",
    "field-validated savings",
    "agency endorsed",
    "agency endorsement confirmed",
    "certified operational",
    "customer deployment confirmed",
    "profitable live trading",
    "universal superiority",
}


class CapsuleError(ValueError):
    """Raised when a capsule fails a public-safety or integrity gate."""


def _require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CapsuleError(f"{key} must be an object")
    return value


def _require_nonempty_string(parent: dict[str, Any], key: str, context: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapsuleError(f"{context}.{key} must be a non-empty string")
    return value.strip()


def _require_list(parent: dict[str, Any], key: str, context: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise CapsuleError(f"{context}.{key} must be an array")
    return value


def _safe_path(root: Path, raw_path: str) -> Path:
    candidate = (root / raw_path).resolve()
    root_resolved = root.resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise CapsuleError(f"manifest path escapes root: {raw_path}")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validate_hash_records(records: list[Any], root: Path, label: str) -> list[str]:
    material: list[str] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise CapsuleError(f"manifest.{label}[{index}] must be an object")
        raw_path = _require_nonempty_string(record, "path", f"manifest.{label}[{index}]")
        expected = _require_nonempty_string(record, "sha256", f"manifest.{label}[{index}]").lower()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise CapsuleError(f"manifest.{label}[{index}].sha256 is not a SHA-256 hex digest")
        path = _safe_path(root, raw_path)
        if not path.is_file():
            raise CapsuleError(f"manifest file does not exist: {raw_path}")
        actual = _sha256(path)
        if actual != expected:
            raise CapsuleError(f"hash mismatch for {raw_path}: expected {expected}, got {actual}")
        material.append(f"{raw_path}:{expected}\n")
    return material


def validate_capsule(capsule: dict[str, Any], root: Path) -> dict[str, Any]:
    missing = sorted(TOP_LEVEL_FIELDS - capsule.keys())
    if missing:
        raise CapsuleError(f"missing top-level fields: {', '.join(missing)}")

    for key in ("capsule_id", "title", "module", "evidence_type"):
        _require_nonempty_string(capsule, key, "capsule")
    if capsule["evidence_type"] not in EVIDENCE_TYPES:
        raise CapsuleError(f"unsupported evidence_type: {capsule['evidence_type']}")

    source = _require_mapping(capsule, "source")
    for key in ("name", "type", "rights_status", "row_count_or_window"):
        _require_nonempty_string(source, key, "source")

    baseline = _require_mapping(capsule, "baseline")
    for key in ("name", "baseline_type", "selection_time"):
        _require_nonempty_string(baseline, key, "baseline")
    if baseline["selection_time"] != "before_scoring":
        raise CapsuleError("baseline.selection_time must be before_scoring for a promoted public capsule")

    metric = _require_mapping(capsule, "locked_metric")
    _require_nonempty_string(metric, "name", "locked_metric")
    _require_nonempty_string(metric, "definition", "locked_metric")
    if metric.get("locked_before_run") is not True:
        raise CapsuleError("locked_metric.locked_before_run must be true")

    run = _require_mapping(capsule, "run")
    for key in ("run_id", "run_type", "timestamp_utc", "code_commit", "dependency_lock", "seed_or_window"):
        _require_nonempty_string(run, key, "run")
    if run["run_type"] not in RUN_TYPES:
        raise CapsuleError(f"unsupported run.run_type: {run['run_type']}")

    manifest = _require_mapping(capsule, "manifest")
    if manifest.get("public_safe") is not True:
        raise CapsuleError("manifest.public_safe must be true")
    input_records = _require_list(manifest, "input_hashes", "manifest")
    output_records = _require_list(manifest, "output_hashes", "manifest")
    if not input_records and not output_records:
        raise CapsuleError("manifest must contain at least one input or output hash record")
    manifest_material = _validate_hash_records(input_records, root, "input_hashes")
    manifest_material += _validate_hash_records(output_records, root, "output_hashes")
    expected_manifest_hash = _require_nonempty_string(manifest, "manifest_hash", "manifest").lower()
    actual_manifest_hash = hashlib.sha256("".join(manifest_material).encode("utf-8")).hexdigest()
    if actual_manifest_hash != expected_manifest_hash:
        raise CapsuleError(
            f"manifest hash mismatch: expected {expected_manifest_hash}, got {actual_manifest_hash}"
        )

    result = _require_mapping(capsule, "result")
    summary = _require_nonempty_string(result, "summary", "result")
    _require_nonempty_string(result, "primary_delta", "result")
    _require_list(result, "secondary_metrics", "result")
    negative_results = _require_list(result, "negative_results", "result")
    failure_notes = _require_list(result, "failure_notes", "result")
    if not negative_results:
        raise CapsuleError("result.negative_results must preserve at least one negative or neutral result")
    if not failure_notes:
        raise CapsuleError("result.failure_notes must not be empty")

    boundary = _require_mapping(capsule, "claim_boundary")
    proves = _require_list(boundary, "proves", "claim_boundary")
    does_not_prove = _require_list(boundary, "does_not_prove", "claim_boundary")
    safe_sentence = _require_nonempty_string(boundary, "safe_public_sentence", "claim_boundary")
    if not proves or not does_not_prove:
        raise CapsuleError("claim_boundary.proves and does_not_prove must both be non-empty")

    promotion_text = " ".join((str(capsule["title"]), summary, safe_sentence)).lower()
    forbidden_hits = sorted(phrase for phrase in FORBIDDEN_PROMOTION_PHRASES if phrase in promotion_text)
    if forbidden_hits:
        raise CapsuleError(f"forbidden promotion phrase(s): {', '.join(forbidden_hits)}")

    decision = _require_mapping(capsule, "pilot_decision")
    status = _require_nonempty_string(decision, "status", "pilot_decision")
    _require_nonempty_string(decision, "next_gate", "pilot_decision")
    _require_nonempty_string(decision, "owner", "pilot_decision")
    if status not in PILOT_STATUSES:
        raise CapsuleError(f"unsupported pilot_decision.status: {status}")

    return {
        "valid": True,
        "capsule_id": capsule["capsule_id"],
        "evidence_type": capsule["evidence_type"],
        "verified_hash_records": len(input_records) + len(output_records),
        "manifest_hash": actual_manifest_hash,
        "pilot_decision": status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capsule", type=Path, help="Path to the Proof Capsule JSON file")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root for hash paths")
    args = parser.parse_args(argv)

    try:
        capsule = json.loads(args.capsule.read_text(encoding="utf-8"))
        if not isinstance(capsule, dict):
            raise CapsuleError("capsule root must be a JSON object")
        result = validate_capsule(capsule, args.root)
    except (OSError, json.JSONDecodeError, CapsuleError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}, indent=2), file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
