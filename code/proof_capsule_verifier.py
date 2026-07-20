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
import unicodedata
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, NamedTuple

VERIFIER_VERSION = "3.0"
CAPSULE_SCHEMA_VERSION = "3.0"
RECEIPT_SCHEMA = "proof-capsule-receipt-v3"
MANIFEST_FORMAT = "proof-capsule-manifest-v3"
DEFAULT_MAX_CAPSULE_BYTES = 1 * 1024 * 1024
DEFAULT_MAX_ARTIFACT_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_TOTAL_ARTIFACT_BYTES = 1024 * 1024 * 1024
MAX_HASH_RECORDS = 10_000
MAX_LIST_ITEMS = 10_000
MAX_TEXT_CHARACTERS = 64 * 1024

TOP_LEVEL_FIELDS = {
    "schema_version",
    "capsule_id",
    "title",
    "module",
    "evidence_type",
    "source",
    "baseline",
    "locked_metric",
    "run",
    "manifest",
    "external_validation",
    "result",
    "claim_boundary",
    "pilot_decision",
}
SOURCE_FIELDS = {"name", "type", "rights_status", "row_count_or_window"}
BASELINE_FIELDS = {"name", "baseline_type", "selection_time"}
LOCKED_METRIC_FIELDS = {"name", "definition", "locked_before_run"}
RUN_FIELDS = {
    "run_id",
    "run_type",
    "timestamp_utc",
    "code_commit",
    "dependency_lock",
    "seed_or_window",
}
MANIFEST_FIELDS = {
    "manifest_format",
    "input_hashes",
    "output_hashes",
    "manifest_hash",
    "public_safe",
}
HASH_RECORD_FIELDS = {"path", "sha256"}
EXTERNAL_VALIDATION_FIELDS = {
    "status",
    "validator_name",
    "validator_organization",
    "scope",
    "completed_at_utc",
    "report_path",
    "report_sha256",
}
RESULT_FIELDS = {
    "summary",
    "primary_delta",
    "secondary_metrics",
    "negative_results",
    "failure_notes",
}
CLAIM_BOUNDARY_FIELDS = {"proves", "does_not_prove", "safe_public_sentence"}
PILOT_DECISION_FIELDS = {"status", "next_gate", "owner"}
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
RUN_TYPES = {
    "measured",
    "replay",
    "synthetic",
    "bench",
    "modeled",
    "estimated",
    "conceptual",
}
PILOT_STATUSES = {"promote", "rerun", "external_review", "hold", "reject"}
EXTERNAL_VALIDATION_STATUSES = {"not_established", "established"}
EVIDENCE_RUN_COMPATIBILITY = {
    "measured": {"measured", "bench"},
    "replay": {"replay"},
    "synthetic": {"synthetic", "bench"},
    "modeled": {"modeled"},
    "estimated": {"estimated"},
    "conceptual": {"conceptual"},
    "externally_validated": {"measured", "replay", "synthetic", "bench"},
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
    "world best",
    "best in the world",
    "number one",
    "institutional grade",
    "government grade",
    "nobel tier",
    "trillion dollar valuation",
    "proven alpha",
    "guaranteed alpha",
    "guaranteed return on investment",
}
NON_EXTERNAL_BOUNDARY_TERMS = (
    "external validation",
    "field validation",
    "field performance",
    "operational performance",
)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-fA-F]{7,64}$")
UNKNOWN_COMMIT_RE = re.compile(
    r"^unknown(?:[-:][A-Za-z0-9][A-Za-z0-9._:-]{0,127})?$"
)
CAPSULE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,127}$")
WINDOWS_DRIVE_RE = re.compile(r"^[A-Za-z]:")
WINDOWS_RESERVED_NAMES = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{index}" for index in range(1, 10)),
    *(f"lpt{index}" for index in range(1, 10)),
}
CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
FORMAT_CONTROL_RE = re.compile(
    "[\u061c\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff]"
)
CLAIM_SEPARATOR_RE = re.compile(r"[^a-z0-9]+")


class CapsuleError(ValueError):
    """Raised when a capsule fails a public-safety or integrity gate."""


class LoadedCapsule(NamedTuple):
    """Parsed capsule plus custody metadata for the exact source bytes."""

    data: dict[str, Any]
    file_sha256: str
    byte_count: int


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


def _reject_nonstandard_number(value: str) -> None:
    raise CapsuleError(f"non-standard JSON number is not allowed: {value}")


def _stat_signature(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
    )


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def load_capsule_document(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_CAPSULE_BYTES,
) -> LoadedCapsule:
    """Load one stable regular file and bind its exact bytes to a digest."""

    try:
        path_before = path.lstat()
        if not stat.S_ISREG(path_before.st_mode):
            raise CapsuleError("capsule must be a regular file, not a link")
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_before.st_mode):
                raise CapsuleError("capsule must be a regular file")
            if opened_before.st_size > max_bytes:
                raise CapsuleError(
                    f"capsule exceeds maximum size of {max_bytes} bytes"
                )
            if _stat_signature(path_before) != _stat_signature(opened_before):
                raise CapsuleError("capsule changed before reading")
            raw = handle.read(max_bytes + 1)
            opened_after = os.fstat(handle.fileno())
        path_after = path.lstat()
    except CapsuleError:
        raise
    except OSError as exc:
        raise CapsuleError(f"cannot read capsule: {exc}") from exc

    if len(raw) > max_bytes:
        raise CapsuleError(f"capsule exceeds maximum size of {max_bytes} bytes")
    signatures = {
        _stat_signature(path_before),
        _stat_signature(opened_before),
        _stat_signature(opened_after),
        _stat_signature(path_after),
    }
    changed_ctime = (
        path_before.st_ctime_ns != path_after.st_ctime_ns
        or opened_before.st_ctime_ns != opened_after.st_ctime_ns
    )
    if len(signatures) != 1 or changed_ctime or len(raw) != opened_after.st_size:
        raise CapsuleError("capsule changed while reading")

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CapsuleError("capsule must be valid UTF-8") from exc
    try:
        capsule = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonstandard_number,
        )
    except CapsuleError:
        raise
    except json.JSONDecodeError as exc:
        raise CapsuleError(f"invalid JSON: {exc}") from exc
    except (RecursionError, ValueError) as exc:
        raise CapsuleError(f"unsafe JSON structure: {exc}") from exc
    if not isinstance(capsule, dict):
        raise CapsuleError("capsule root must be a JSON object")
    return LoadedCapsule(
        data=capsule,
        file_sha256=hashlib.sha256(raw).hexdigest(),
        byte_count=len(raw),
    )


def load_capsule(
    path: Path,
    *,
    max_bytes: int = DEFAULT_MAX_CAPSULE_BYTES,
) -> dict[str, Any]:
    """Compatibility wrapper for callers that only need the parsed object."""

    return load_capsule_document(path, max_bytes=max_bytes).data


def _require_exact_fields(
    value: dict[str, Any],
    expected: set[str],
    context: str,
) -> None:
    non_string = [repr(key) for key in value if not isinstance(key, str)]
    if non_string:
        raise CapsuleError(
            f"{context} contains non-string field name(s): {', '.join(non_string)}"
        )
    missing = sorted(expected - value.keys())
    if missing:
        raise CapsuleError(f"missing {context} fields: {', '.join(missing)}")
    unknown = sorted(value.keys() - expected)
    if unknown:
        raise CapsuleError(f"unknown {context} fields: {', '.join(unknown)}")


def _require_mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise CapsuleError(f"{key} must be an object")
    return value


def _validate_text(value: str, context: str) -> str:
    if value != value.strip():
        raise CapsuleError(f"{context} must not contain surrounding whitespace")
    if len(value) > MAX_TEXT_CHARACTERS:
        raise CapsuleError(
            f"{context} exceeds the {MAX_TEXT_CHARACTERS} character safety limit"
        )
    if CONTROL_CHAR_RE.search(value):
        raise CapsuleError(f"{context} contains a control character")
    if FORMAT_CONTROL_RE.search(value):
        raise CapsuleError(f"{context} contains a hidden format character")
    return value


def _require_nonempty_string(
    parent: dict[str, Any],
    key: str,
    context: str,
) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise CapsuleError(f"{context}.{key} must be a non-empty string")
    return _validate_text(value, f"{context}.{key}")


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
    if len(value) > MAX_LIST_ITEMS:
        raise CapsuleError(
            f"{context}.{key} exceeds the {MAX_LIST_ITEMS} item safety limit"
        )
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
        normalized = _validate_text(value, f"{context}.{key}[{index}]")
        dedupe_key = normalized.casefold()
        if dedupe_key in seen:
            raise CapsuleError(
                f"{context}.{key} contains a duplicate entry: {normalized}"
            )
        seen.add(dedupe_key)
        output.append(normalized)
    return output


def _normalize_claim_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return CLAIM_SEPARATOR_RE.sub(" ", normalized).strip()


def _reject_forbidden_claims(values: list[str]) -> None:
    normalized_phrases = {
        _normalize_claim_text(phrase): phrase
        for phrase in FORBIDDEN_PROMOTION_PHRASES
    }
    forbidden_hits = sorted({
        original
        for value in values
        for normalized_phrase, original in normalized_phrases.items()
        if normalized_phrase in _normalize_claim_text(value)
    })
    if forbidden_hits:
        raise CapsuleError(
            f"forbidden promotion phrase(s): {', '.join(forbidden_hits)}"
        )


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
    if unicodedata.normalize("NFC", raw_path) != raw_path:
        raise CapsuleError(
            f"manifest path must use canonical Unicode normalization: {raw_path}"
        )
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
    for part in pure.parts:
        if ":" in part:
            raise CapsuleError(
                f"manifest path must not contain a colon: {raw_path}"
            )
        if part.endswith((" ", ".")):
            raise CapsuleError(
                "manifest path segments must not end in a space or dot: "
                f"{raw_path}"
            )
        device_name = part.split(".", 1)[0].casefold()
        if device_name in WINDOWS_RESERVED_NAMES:
            raise CapsuleError(
                f"manifest path uses a reserved device name: {raw_path}"
            )
    normalized = pure.as_posix()
    if normalized != raw_path:
        raise CapsuleError(f"manifest path is not canonical: {raw_path}")
    return normalized


def _safe_path(root: Path, raw_path: str) -> tuple[str, Path]:
    canonical = _canonical_manifest_path(raw_path)
    candidate_unresolved = root / Path(*PurePosixPath(canonical).parts)
    cursor = root
    for part in PurePosixPath(canonical).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise CapsuleError(f"manifest path must not traverse a symlink: {raw_path}")
    candidate = candidate_unresolved.resolve()
    if candidate != root and root not in candidate.parents:
        raise CapsuleError(f"manifest path escapes root: {raw_path}")
    return canonical, candidate


def _sha256(path: Path, *, max_bytes: int) -> tuple[str, int, tuple[int, int]]:
    try:
        path_before = path.lstat()
        if not stat.S_ISREG(path_before.st_mode):
            raise CapsuleError(
                f"manifest target is not a regular file: {path}"
            )
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
        path_after = path.lstat()
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
    changed_ctime = (
        path_before.st_ctime_ns != path_after.st_ctime_ns
        or opened_before.st_ctime_ns != opened_after.st_ctime_ns
    )
    if len(signatures) != 1 or changed_ctime or total != opened_after.st_size:
        raise CapsuleError(f"manifest file changed while hashing: {path}")
    return digest.hexdigest(), total, (opened_after.st_dev, opened_after.st_ino)


def _validate_hash_records(
    records: list[Any],
    root: Path,
    label: str,
    *,
    seen_paths: set[str],
    seen_targets: set[Path],
    seen_file_ids: set[tuple[int, int]],
    max_artifact_bytes: int,
    max_total_artifact_bytes: int,
    previously_verified_bytes: int,
) -> tuple[list[dict[str, str]], int]:
    verified_records: list[dict[str, str]] = []
    verified_bytes = 0
    for index, record in enumerate(records):
        context = f"manifest.{label}[{index}]"
        if not isinstance(record, dict):
            raise CapsuleError(f"{context} must be an object")
        _require_exact_fields(record, HASH_RECORD_FIELDS, context)
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
        actual, byte_count, file_id = _sha256(
            path,
            max_bytes=max_artifact_bytes,
        )
        if file_id in seen_file_ids:
            raise CapsuleError(
                f"multiple manifest paths reference the same file identity: {canonical}"
            )
        seen_file_ids.add(file_id)
        if actual != expected:
            raise CapsuleError(
                f"hash mismatch for {canonical}: expected {expected}, got {actual}"
            )
        next_total = previously_verified_bytes + verified_bytes + byte_count
        if next_total > max_total_artifact_bytes:
            raise CapsuleError(
                "manifest artifacts exceed the aggregate maximum size of "
                f"{max_total_artifact_bytes} bytes"
            )
        verified_bytes += byte_count
        verified_records.append({"path": canonical, "sha256": actual})
    return verified_records, verified_bytes


def validate_capsule(
    capsule: dict[str, Any],
    root: Path,
    *,
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES,
    max_total_artifact_bytes: int = DEFAULT_MAX_TOTAL_ARTIFACT_BYTES,
    capsule_file_sha256: str | None = None,
    capsule_file_bytes: int | None = None,
) -> dict[str, Any]:
    if max_artifact_bytes < 1:
        raise CapsuleError("max_artifact_bytes must be positive")
    if max_total_artifact_bytes < 1:
        raise CapsuleError("max_total_artifact_bytes must be positive")
    if (capsule_file_sha256 is None) != (capsule_file_bytes is None):
        raise CapsuleError(
            "capsule_file_sha256 and capsule_file_bytes must be provided together"
        )
    if capsule_file_sha256 is not None and not SHA256_RE.fullmatch(
        capsule_file_sha256
    ):
        raise CapsuleError("capsule_file_sha256 is not a SHA-256 hex digest")
    if capsule_file_bytes is not None and (
        isinstance(capsule_file_bytes, bool)
        or not isinstance(capsule_file_bytes, int)
        or capsule_file_bytes < 1
    ):
        raise CapsuleError("capsule_file_bytes must be a positive integer")

    try:
        root_resolved = root.resolve(strict=True)
    except OSError as exc:
        raise CapsuleError(f"cannot resolve repository root: {exc}") from exc
    if not root_resolved.is_dir():
        raise CapsuleError("repository root must be a directory")

    _require_exact_fields(capsule, TOP_LEVEL_FIELDS, "top-level")
    schema_version = _require_nonempty_string(
        capsule,
        "schema_version",
        "capsule",
    )
    if schema_version != CAPSULE_SCHEMA_VERSION:
        raise CapsuleError(
            "capsule.schema_version must be "
            f"{CAPSULE_SCHEMA_VERSION!r}; received {schema_version!r}"
        )

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
    _require_exact_fields(source, SOURCE_FIELDS, "source")
    source_name = _require_nonempty_string(source, "name", "source")
    _require_enum(source, "type", "source", SOURCE_TYPES)
    rights_status = _require_enum(
        source,
        "rights_status",
        "source",
        RIGHTS_STATUSES,
    )
    source_window = _require_nonempty_string(
        source,
        "row_count_or_window",
        "source",
    )
    if rights_status == "unknown":
        raise CapsuleError(
            "source.rights_status must be resolved before public verification"
        )

    baseline = _require_mapping(capsule, "baseline")
    _require_exact_fields(baseline, BASELINE_FIELDS, "baseline")
    baseline_name = _require_nonempty_string(baseline, "name", "baseline")
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
    _require_exact_fields(metric, LOCKED_METRIC_FIELDS, "locked_metric")
    metric_name = _require_nonempty_string(metric, "name", "locked_metric")
    metric_definition = _require_nonempty_string(
        metric,
        "definition",
        "locked_metric",
    )
    if metric.get("locked_before_run") is not True:
        raise CapsuleError("locked_metric.locked_before_run must be true")

    run = _require_mapping(capsule, "run")
    _require_exact_fields(run, RUN_FIELDS, "run")
    run_id = _require_nonempty_string(run, "run_id", "run")
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
        UNKNOWN_COMMIT_RE.fullmatch(code_commit)
        or GIT_SHA_RE.fullmatch(code_commit)
    ):
        raise CapsuleError(
            "run.code_commit must be a 7-64 character Git SHA or an exact "
            "unknown[-reason] value"
        )
    dependency_lock = _require_nonempty_string(run, "dependency_lock", "run")
    seed_or_window = _require_nonempty_string(run, "seed_or_window", "run")
    compatible = EVIDENCE_RUN_COMPATIBILITY.get(evidence_type)
    if compatible is not None and run_type not in compatible:
        allowed = ", ".join(sorted(compatible))
        raise CapsuleError(
            f"run.run_type {run_type!r} is incompatible with evidence_type "
            f"{evidence_type!r}; expected {allowed}"
        )

    manifest = _require_mapping(capsule, "manifest")
    _require_exact_fields(manifest, MANIFEST_FIELDS, "manifest")
    manifest_format = _require_nonempty_string(
        manifest,
        "manifest_format",
        "manifest",
    )
    if manifest_format != MANIFEST_FORMAT:
        raise CapsuleError(
            f"manifest.manifest_format must be {MANIFEST_FORMAT!r}"
        )
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
    seen_file_ids: set[tuple[int, int]] = set()
    verified_inputs, input_bytes = _validate_hash_records(
        input_records,
        root_resolved,
        "input_hashes",
        seen_paths=seen_paths,
        seen_targets=seen_targets,
        seen_file_ids=seen_file_ids,
        max_artifact_bytes=max_artifact_bytes,
        max_total_artifact_bytes=max_total_artifact_bytes,
        previously_verified_bytes=0,
    )
    verified_outputs, output_bytes = _validate_hash_records(
        output_records,
        root_resolved,
        "output_hashes",
        seen_paths=seen_paths,
        seen_targets=seen_targets,
        seen_file_ids=seen_file_ids,
        max_artifact_bytes=max_artifact_bytes,
        max_total_artifact_bytes=max_total_artifact_bytes,
        previously_verified_bytes=input_bytes,
    )
    expected_manifest_hash = _require_sha256(
        manifest,
        "manifest_hash",
        "manifest",
    )
    manifest_payload = {
        "manifest_format": manifest_format,
        "input_hashes": verified_inputs,
        "output_hashes": verified_outputs,
    }
    actual_manifest_hash = hashlib.sha256(
        _canonical_json_bytes(manifest_payload)
    ).hexdigest()
    if actual_manifest_hash != expected_manifest_hash:
        raise CapsuleError(
            f"manifest hash mismatch: expected {expected_manifest_hash}, "
            f"got {actual_manifest_hash}"
        )

    external = _require_mapping(capsule, "external_validation")
    _require_exact_fields(
        external,
        EXTERNAL_VALIDATION_FIELDS,
        "external_validation",
    )
    external_status = _require_enum(
        external,
        "status",
        "external_validation",
        EXTERNAL_VALIDATION_STATUSES,
    )
    external_claim_text: list[str] = []
    external_report_manifest_bound = False
    if evidence_type == "externally_validated":
        if external_status != "established":
            raise CapsuleError(
                "externally_validated evidence requires "
                "external_validation.status=established"
            )
        validator_name = _require_nonempty_string(
            external,
            "validator_name",
            "external_validation",
        )
        validator_organization = _require_nonempty_string(
            external,
            "validator_organization",
            "external_validation",
        )
        validation_scope = _require_nonempty_string(
            external,
            "scope",
            "external_validation",
        )
        completed_at = _require_nonempty_string(
            external,
            "completed_at_utc",
            "external_validation",
        )
        _parse_utc_timestamp(
            completed_at,
            "external_validation.completed_at_utc",
        )
        report_path = _require_nonempty_string(
            external,
            "report_path",
            "external_validation",
        )
        report_path = _canonical_manifest_path(report_path)
        report_sha256 = _require_sha256(
            external,
            "report_sha256",
            "external_validation",
        )
        manifest_records = verified_inputs + verified_outputs
        if not any(
            record["path"] == report_path
            and record["sha256"] == report_sha256
            for record in manifest_records
        ):
            raise CapsuleError(
                "external validation report path and digest must match a "
                "verified manifest record"
            )
        external_report_manifest_bound = True
        external_claim_text.extend(
            (validator_name, validator_organization, validation_scope)
        )
    else:
        if external_status != "not_established":
            raise CapsuleError(
                "non-external evidence must use "
                "external_validation.status=not_established"
            )
        nullable_fields = EXTERNAL_VALIDATION_FIELDS - {"status"}
        populated = sorted(
            key for key in nullable_fields if external.get(key) is not None
        )
        if populated:
            raise CapsuleError(
                "non-external evidence must leave external validation detail "
                f"fields null: {', '.join(populated)}"
            )

    result = _require_mapping(capsule, "result")
    _require_exact_fields(result, RESULT_FIELDS, "result")
    summary = _require_nonempty_string(result, "summary", "result")
    primary_delta = _require_nonempty_string(
        result,
        "primary_delta",
        "result",
    )
    secondary_metrics = _require_string_list(
        result,
        "secondary_metrics",
        "result",
    )
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
    _require_exact_fields(boundary, CLAIM_BOUNDARY_FIELDS, "claim_boundary")
    proves = _require_string_list(
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

    decision = _require_mapping(capsule, "pilot_decision")
    _require_exact_fields(decision, PILOT_DECISION_FIELDS, "pilot_decision")
    status = _require_enum(
        decision,
        "status",
        "pilot_decision",
        PILOT_STATUSES,
    )
    next_gate = _require_nonempty_string(
        decision,
        "next_gate",
        "pilot_decision",
    )
    _require_nonempty_string(decision, "owner", "pilot_decision")

    _reject_forbidden_claims(
        [
            title,
            source_name,
            source_window,
            baseline_name,
            metric_name,
            metric_definition,
            run_id,
            dependency_lock,
            seed_or_window,
            summary,
            primary_delta,
            *secondary_metrics,
            *proves,
            safe_sentence,
            next_gate,
            *external_claim_text,
        ]
    )

    canonical_capsule_bytes = _canonical_json_bytes(capsule)
    canonical_capsule_sha256 = hashlib.sha256(
        canonical_capsule_bytes
    ).hexdigest()

    return {
        "valid": True,
        "receipt_schema": RECEIPT_SCHEMA,
        "verifier_version": VERIFIER_VERSION,
        "verification_scope": "capsule-schema-and-custody",
        "capsule_schema_version": schema_version,
        "capsule_id": capsule_id,
        "capsule_file_custody_complete": capsule_file_sha256 is not None,
        "capsule_file_sha256": capsule_file_sha256,
        "capsule_file_bytes": capsule_file_bytes,
        "capsule_canonical_sha256": canonical_capsule_sha256,
        "capsule_canonical_bytes": len(canonical_capsule_bytes),
        "declared_evidence_type": evidence_type,
        "run_type": run_type,
        "run_timestamp_utc": run_timestamp.isoformat().replace(
            "+00:00",
            "Z",
        ),
        "verified_hash_records": record_count,
        "verified_bytes": input_bytes + output_bytes,
        "manifest_format": manifest_format,
        "manifest_hash": actual_manifest_hash,
        "declared_external_validation_status": external_status,
        "external_report_manifest_bound": external_report_manifest_bound,
        "external_validator_identity_evaluated": False,
        "external_validator_independence_evaluated": False,
        "external_validation_conclusion_evaluated": False,
        "pilot_decision": status,
        "release_authorization_evaluated": False,
        "human_unlock_required": True,
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
    parser.add_argument(
        "--max-total-artifact-bytes",
        type=_positive_int,
        default=DEFAULT_MAX_TOTAL_ARTIFACT_BYTES,
        help=(
            "Maximum aggregate size of all referenced artifacts "
            f"(default: {DEFAULT_MAX_TOTAL_ARTIFACT_BYTES})"
        ),
    )
    args = parser.parse_args(argv)

    try:
        document = load_capsule_document(
            args.capsule,
            max_bytes=args.max_capsule_bytes,
        )
        result = validate_capsule(
            document.data,
            args.root,
            max_artifact_bytes=args.max_artifact_bytes,
            max_total_artifact_bytes=args.max_total_artifact_bytes,
            capsule_file_sha256=document.file_sha256,
            capsule_file_bytes=document.byte_count,
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
