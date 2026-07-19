#!/usr/bin/env python3
"""Validate a public-safe LumenCore Proof Capsule and verify referenced file hashes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

VERIFIER_VERSION = "2.0"
DEFAULT_MAX_CAPSULE_BYTES = 1 * 1024 * 1024
DEFAULT_MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
MAX_HASH_RECORDS = 10_000

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
MODULES = {
    "LumenCore",
    "LumaTrader",
    "LumaScout",
    "LumaJet",
    "LumaSuit",
    "LumaSkin",
    "EchoForm",
    "FlowForm",
    "Other",
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
SOURCE_TYPES = {
    "dataset",
    "stream",
    "sensor",
    "benchmark",
    "sample",
    "document",
    "dashboard",
    "simulation",
}
RIGHTS_STATUSES = {"public", "private", "buyer_authorized", "synthetic", "unknown"}
BASELINE_TYPES = {
    "incumbent",
    "naive",
    "named_method",
    "synthetic_control",
    "historical",
    "benchmark",
}
RUN_TYPES = {"measured", "replay", "synthetic", "bench", "modeled"}
PILOT_STATUSES = {"promote", "rerun", "external_review", "hold", "reject"}
EVIDENCE_RUN_COMPATIBILITY = {
    "measured": {"measured", "bench"},
    "replay": {"replay"},
    "synthetic": {"synthetic", "bench"},
    "modeled": {"modeled"},
}
FORBIDDEN_PROMOTION_PHRASES = {
    "audited revenue",
    "guaranteed roi",
    "guaranteed savings",
    "field-validated savings",
    "agency endorsed",
    "agency endorsement confirmed",
    "certified operational",
    "certified aircraft",
    "certified suit",
    "weapons capability",
    "autonomous physical control",
    "medical diagnosis",
    "grant award likelihood",
    "customer deployment confirmed",
    "profitable live trading",
    "universal superiority",
}
NON_EXTERNAL_BOUNDARY_TERMS = (
    "external validation",
    "field validation",
    "field performance",
    "operational performance",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
CAPSULE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")


class CapsuleError(ValueError):
    """Raised when a capsule fails a public-safety or integrity gate."""


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if parsed < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return parsed


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise CapsuleError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_capsule(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_CAPSULE_BYTES,
) -> dict[str, Any]:
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CapsuleError(f"cannot stat capsule: {exc}") from exc
    if size > max_bytes:
        raise CapsuleError(f"capsule exceeds maximum size of {max_bytes} bytes")
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CapsuleError(f"cannot read capsule: {exc}") from exc
    if len(raw) > max_bytes:
        raise CapsuleError(f"capsule exceeds maximum size of {max_bytes} bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CapsuleError("capsule must be valid UTF-8") from exc
    try:
        capsule = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        raise CapsuleError(f"invalid JSON: {exc}") from exc
    if not isinstance(capsule, dict):
        raise CapsuleError("capsule root must be a JSON object")
    return capsule


def _require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CapsuleError(f"{key} must be an object")
    return value


def _require_nonempty_string(
    parent: dict[str, Any],
    key: str,
    context: str,
) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapsuleError(f"{context}.{key} must be a non-empty string")
    normalized = value.strip()
    if "\x00" in normalized:
        raise CapsuleError(f"{context}.{key} contains a NUL character")
    return normalized


def _require_enum(
    parent: dict[str, Any],
    key: str,
    context: str,
    allowed: set[str],
) -> str:
    value = _require_nonempty_string(parent, key, context)
    if value not in allowed:
        raise CapsuleError(f"unsupported {context}.{key}: {value}")
    return value


def _require_list(parent: dict[str, Any], key: str, context: str) -> list[Any]:
    value = parent.get(key)
    if not isinstance(value, list):
        raise CapsuleError(f"{context}.{key} must be an array")
    return value


def _require_string_list(
    parent: dict[str, Any],
    key: str,
    context: str,
    *,
    nonempty: bool = False,
) -> list[str]:
    values = _require_list(parent, key, context)
    if nonempty and not values:
        raise CapsuleError(f"{context}.{key} must not be empty")
    output: list[str] = []
    seen: set[str] = set()
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            raise CapsuleError(f"{context}.{key}[{index}] must be a non-empty string")
        normalized = value.strip()
        if "\x00" in normalized:
            raise CapsuleError(f"{context}.{key}[{index}] contains a NUL character")
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            raise CapsuleError(
                f"{context}.{key} contains a duplicate entry: {normalized}"
            )
        seen.add(dedupe_key)
        output.append(normalized)
    return output


def _require_sha256(parent: dict[str, Any], key: str, context: str) -> str:
    value = _require_nonempty_string(parent, key, context).lower()
    if not SHA256_RE.fullmatch(value):
        raise CapsuleError(f"{context}.{key} is not a SHA-256 hex digest")
    return value


def _parse_utc_timestamp(value: str, context: str) -> datetime:
    text = value.strip()
    parse_text = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(parse_text)
    except ValueError as exc:
        raise CapsuleError(f"{context} must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise CapsuleError(f"{context} must include an explicit UTC offset")
    return parsed.astimezone(timezone.utc)


def _canonical_manifest_path(raw_path: str) -> str:
    if CONTROL_CHAR_RE.search(raw_path):
        raise CapsuleError(
            f"manifest path contains a control character: {raw_path!r}"
        )
    if "\\" in raw_path:
        raise CapsuleError(f"manifest path must use POSIX separators: {raw_path}")
    if WINDOWS_DRIVE_RE.match(raw_path) or raw_path.startswith("//"):
        raise CapsuleError(
            f"manifest path must be repository-relative: {raw_path}"
        )
    pure = PurePosixPath(raw_path)
    if pure.is_absolute() or not pure.parts:
        raise CapsuleError(
            f"manifest path must be repository-relative: {raw_path}"
        )
    if any(part in {"", ".", ".."} for part in pure.parts):
        raise CapsuleError(f"manifest path is not canonical: {raw_path}")
    normalized = pure.as_posix()
    if normalized != raw_path:
        raise CapsuleError(f"manifest path is not canonical: {raw_path}")
    return normalized


def _safe_path(root: Path, raw_path: str) -> tuple[str, Path]:
    canonical = _canonical_manifest_path(raw_path)
    root_resolved = root.resolve()
    candidate = (
        root_resolved / Path(*PurePosixPath(canonical).parts)
    ).resolve()
    if candidate != root_resolved and root_resolved not in candidate.parents:
        raise CapsuleError(f"manifest path escapes root: {raw_path}")
    return canonical, candidate


def _stat_signature(info: os.stat_result) -> tuple[int, int, int, int]:
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)


def _sha256(path: Path, *, max_bytes: int) -> tuple[str, int]:
    try:
        path_before = path.stat()
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_before.st_mode):
                raise CapsuleError(
                    f"manifest target is not a regular file: {path}"
                )
            if opened_before.st_size > max_bytes:
                raise CapsuleError(
                    f"manifest file exceeds maximum size of {max_bytes} bytes: {path}"
                )
            if _stat_signature(path_before) != _stat_signature(opened_before):
                raise CapsuleError(
                    f"manifest file changed before hashing: {path}"
                )

            digest = hashlib.sha256()
            total = 0
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                total += len(block)
                if total > max_bytes:
                    raise CapsuleError(
                        f"manifest file exceeds maximum size of {max_bytes} bytes: {path}"
                    )
                digest.update(block)
            opened_after = os.fstat(handle.fileno())
        path_after = path.stat()
    except CapsuleError:
        raise
    except OSError as exc:
        raise CapsuleError(
            f"cannot hash manifest file {path}: {exc}"
        ) from exc

    signatures = {
        _stat_signature(path_before),
        _stat_signature(opened_before),
        _stat_signature(opened_after),
        _stat_signature(path_after),
    }
    if len(signatures) != 1 or total != opened_after.st_size:
        raise CapsuleError(f"manifest file changed while hashing: {path}")
    return digest.hexdigest(), total


def _validate_hash_records(
    records: list[Any],
    root: Path,
    label: str,
    *,
    seen_paths: set[str],
    seen_targets: set[Path],
    max_artifact_bytes: int,
) -> tuple[list[str], int]:
    material: list[str] = []
    verified_bytes = 0
    for index, record in enumerate(records):
        context = f"manifest.{label}[{index}]"
        if not isinstance(record, dict):
            raise CapsuleError(f"{context} must be an object")
        raw_path = _require_nonempty_string(record, "path", context)
        expected = _require_sha256(record, "sha256", context)
        canonical, path = _safe_path(root, raw_path)
        path_key = canonical.casefold()
        if path_key in seen_paths:
            raise CapsuleError(f"duplicate manifest path: {canonical}")
        seen_paths.add(path_key)
        if path in seen_targets:
            raise CapsuleError(
                f"multiple manifest paths resolve to the same file: {canonical}"
            )
        seen_targets.add(path)
        if not path.exists():
            raise CapsuleError(f"manifest file does not exist: {canonical}")
        actual, byte_count = _sha256(
            path,
            max_bytes=max_artifact_bytes,
        )
        if actual != expected:
            raise CapsuleError(
                f"hash mismatch for {canonical}: expected {expected}, got {actual}"
            )
        verified_bytes += byte_count
        material.append(f"{canonical}:{expected}\n")
    return material, verified_bytes


def validate_capsule(
    capsule: dict[str, Any],
    root: Path,
    *,
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
) -> dict[str, Any]:
    if max_artifact_bytes < 1:
        raise CapsuleError("max_artifact_bytes must be positive")

    missing = sorted(TOP_LEVEL_FIELDS - capsule.keys())
    if missing:
        raise CapsuleError(f"missing top-level fields: {', '.join(missing)}")

    capsule_id = _require_nonempty_string(capsule, "capsule_id", "capsule")
    if not CAPSULE_ID_RE.fullmatch(capsule_id):
        raise CapsuleError(
            "capsule.capsule_id must use 3-128 URL-safe identifier characters"
        )
    title = _require_nonempty_string(capsule, "title", "capsule")
    _require_enum(capsule, "module", "capsule", MODULES)
    evidence_type = _require_enum(
        capsule,
        "evidence_type",
        "capsule",
        EVIDENCE_TYPES,
    )

    source = _require_mapping(capsule, "source")
    _require_nonempty_string(source, "name", "source")
    _require_enum(source, "type", "source", SOURCE_TYPES)
    rights_status = _require_enum(
        source,
        "rights_status",
        "source",
        RIGHTS_STATUSES,
    )
    _require_nonempty_string(source, "row_count_or_window", "source")
    if rights_status == "unknown":
        raise CapsuleError(
            "source.rights_status must be resolved before public verification"
        )

    baseline = _require_mapping(capsule, "baseline")
    _require_nonempty_string(baseline, "name", "baseline")
    _require_enum(
        baseline,
        "baseline_type",
        "baseline",
        BASELINE_TYPES,
    )
    selection_time = _require_nonempty_string(
        baseline,
        "selection_time",
        "baseline",
    )
    if selection_time != "before_scoring":
        raise CapsuleError(
            "baseline.selection_time must be before_scoring for a promoted public capsule"
        )

    metric = _require_mapping(capsule, "locked_metric")
    _require_nonempty_string(metric, "name", "locked_metric")
    _require_nonempty_string(metric, "definition", "locked_metric")
    if metric.get("locked_before_run") is not True:
        raise CapsuleError("locked_metric.locked_before_run must be true")

    run = _require_mapping(capsule, "run")
    _require_nonempty_string(run, "run_id", "run")
    run_type = _require_enum(run, "run_type", "run", RUN_TYPES)
    timestamp_text = _require_nonempty_string(
        run,
        "timestamp_utc",
        "run",
    )
    run_timestamp = _parse_utc_timestamp(
        timestamp_text,
        "run.timestamp_utc",
    )
    code_commit = _require_nonempty_string(run, "code_commit", "run")
    if not (
        code_commit.lower().startswith("unknown")
        or GIT_SHA_RE.fullmatch(code_commit)
    ):
        raise CapsuleError(
            "run.code_commit must be a 7-64 character Git SHA or an explicit unknown value"
        )
    _require_nonempty_string(run, "dependency_lock", "run")
    _require_nonempty_string(run, "seed_or_window", "run")
    compatible = EVIDENCE_RUN_COMPATIBILITY.get(evidence_type)
    if compatible is not None and run_type not in compatible:
        allowed = ", ".join(sorted(compatible))
        raise CapsuleError(
            f"run.run_type {run_type!r} is incompatible with evidence_type "
            f"{evidence_type!r}; expected {allowed}"
        )

    manifest = _require_mapping(capsule, "manifest")
    if manifest.get("public_safe") is not True:
        raise CapsuleError("manifest.public_safe must be true")
    input_records = _require_list(manifest, "input_hashes", "manifest")
    output_records = _require_list(manifest, "output_hashes", "manifest")
    record_count = len(input_records) + len(output_records)
    if record_count == 0:
        raise CapsuleError(
            "manifest must contain at least one input or output hash record"
        )
    if record_count > MAX_HASH_RECORDS:
        raise CapsuleError(
            f"manifest exceeds the {MAX_HASH_RECORDS} record safety limit"
        )
    seen_paths: set[str] = set()
    seen_targets: set[Path] = set()
    input_material, input_bytes = _validate_hash_records(
        input_records,
        root,
        "input_hashes",
        seen_paths=seen_paths,
        seen_targets=seen_targets,
        max_artifact_bytes=max_artifact_bytes,
    )
    output_material, output_bytes = _validate_hash_records(
        output_records,
        root,
        "output_hashes",
        seen_paths=seen_paths,
        seen_targets=seen_targets,
        max_artifact_bytes=max_artifact_bytes,
    )
    manifest_material = input_material + output_material
    expected_manifest_hash = _require_sha256(
        manifest,
        "manifest_hash",
        "manifest",
    )
    actual_manifest_hash = hashlib.sha256(
        "".join(manifest_material).encode("utf-8")
    ).hexdigest()
    if actual_manifest_hash != expected_manifest_hash:
        raise CapsuleError(
            f"manifest hash mismatch: expected {expected_manifest_hash}, "
            f"got {actual_manifest_hash}"
        )

    result = _require_mapping(capsule, "result")
    summary = _require_nonempty_string(result, "summary", "result")
    primary_delta = _require_nonempty_string(
        result,
        "primary_delta",
        "result",
    )
    _require_string_list(result, "secondary_metrics", "result")
    _require_string_list(
        result,
        "negative_results",
        "result",
        nonempty=True,
    )
    _require_string_list(
        result,
        "failure_notes",
        "result",
        nonempty=True,
    )

    boundary = _require_mapping(capsule, "claim_boundary")
    _require_string_list(
        boundary,
        "proves",
        "claim_boundary",
        nonempty=True,
    )
    does_not_prove = _require_string_list(
        boundary,
        "does_not_prove",
        "claim_boundary",
        nonempty=True,
    )
    safe_sentence = _require_nonempty_string(
        boundary,
        "safe_public_sentence",
        "claim_boundary",
    )
    if evidence_type != "externally_validated":
        boundary_text = " ".join(does_not_prove).casefold()
        if not any(
            term in boundary_text
            for term in NON_EXTERNAL_BOUNDARY_TERMS
        ):
            raise CapsuleError(
                "claim_boundary.does_not_prove must explicitly retain an "
                "external/field/operational validation boundary"
            )

    promotion_text = " ".join(
        (title, summary, primary_delta, safe_sentence)
    ).casefold()
    forbidden_hits = sorted(
        phrase
        for phrase in FORBIDDEN_PROMOTION_PHRASES
        if phrase in promotion_text
    )
    if forbidden_hits:
        raise CapsuleError(
            f"forbidden promotion phrase(s): {', '.join(forbidden_hits)}"
        )

    decision = _require_mapping(capsule, "pilot_decision")
    status = _require_enum(
        decision,
        "status",
        "pilot_decision",
        PILOT_STATUSES,
    )
    _require_nonempty_string(decision, "next_gate", "pilot_decision")
    _require_nonempty_string(decision, "owner", "pilot_decision")

    return {
        "valid": True,
        "verifier_version": VERIFIER_VERSION,
        "capsule_id": capsule_id,
        "evidence_type": evidence_type,
        "run_type": run_type,
        "run_timestamp_utc": run_timestamp.isoformat().replace(
            "+00:00",
            "Z",
        ),
        "verified_hash_records": record_count,
        "verified_bytes": input_bytes + output_bytes,
        "manifest_hash": actual_manifest_hash,
        "pilot_decision": status,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "capsule",
        type=Path,
        help="Path to the Proof Capsule JSON file",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="Repository root for hash paths",
    )
    parser.add_argument(
        "--max-capsule-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_CAPSULE_BYTES,
        help=(
            "Maximum capsule JSON size "
            f"(default: {DEFAULT_MAX_CAPSULE_BYTES})"
        ),
    )
    parser.add_argument(
        "--max-artifact-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_ARTIFACT_BYTES,
        help=(
            "Maximum size of each referenced artifact "
            f"(default: {DEFAULT_MAX_ARTIFACT_BYTES})"
        ),
    )
    args = parser.parse_args(argv)

    try:
        capsule = load_capsule(
            args.capsule,
            max_bytes=args.max_capsule_bytes,
        )
        result = validate_capsule(
            capsule,
            args.root,
            max_artifact_bytes=args.max_artifact_bytes,
        )
    except CapsuleError as exc:
        print(
            json.dumps({"valid": False, "error": str(exc)}, indent=2),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
