from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import shutil
import subprocess
import tempfile
import time
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROTOCOL = ROOT / "config" / "local_compute_work_provenance_protocol_v1.json"

PROTOCOL_SCHEMA = "local_compute_work_provenance_protocol.v1"
WORK_SCHEMA = "local_compute_work_provenance_work_measurement.v1"
RECEIPT_SCHEMA = "local_compute_work_provenance_receipt.v1"
PACKET_MANIFEST_SCHEMA = "local_compute_work_provenance_packet_manifest.v1"
LATEST_POINTER_SCHEMA = "local_compute_work_provenance_latest_pointer.v1"
QUALITY_LEVELS = frozenset({"VALID", "DEGRADED", "INVALID"})

MAX_TASK_DURATION_MS = 7 * 24 * 60 * 60 * 1000
MAX_GOAL_DURATION_SECONDS = 365 * 24 * 60 * 60
UNATTRIBUTED_MODEL = "__UNATTRIBUTED__"
AMBIGUOUS_MODEL = "__AMBIGUOUS__"
RESERVED_MODEL_LABELS = frozenset({UNATTRIBUTED_MODEL, AMBIGUOUS_MODEL})
UTC_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)
ROUNDING_POLICY = {
    "duration_ms_normalization": "ROUND_HALF_UP to nearest integer microsecond",
    "elapsed_seconds": "ROUND_HALF_UP to 0.001 seconds",
    "duration_labels": "ROUND_HALF_UP to nearest whole second",
}

DEPENDENCY_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "env",
    "env311",
    "node_modules",
    "site-packages",
    "venv",
}
KEY_QUANTLAB_ARTIFACTS = (
    "README.md",
    "BUILD_SUMMARY.txt",
    "current/hashes/MANIFEST.json",
    "current/reports/leaderboard.csv",
    "current/reports/v3_family_leaderboard.csv",
    "current/reports/v4_family_leaderboard.csv",
    "current/reports/v44_core_metrics.csv",
    "current/evidence/champion_freeze.json",
    "current/evidence/v3_champion_of_champions_freeze.json",
    "current/evidence/v4_champion_freeze.json",
)
KEY_STACK_ARTIFACTS = (
    "docs/PUBLIC_SAFE_MODEL_AND_GEOMETRY_EVIDENCE_LEDGER_2026-07-13.md",
    "docs/QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md",
    "out/master_universe_v2/20260613T021546Z/UNDENIABLE_SCORECARD_V2.md",
)


class SourceScanError(OSError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-finite JSON number: {value}")


def strict_json_loads(raw: str | bytes) -> Any:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return json.loads(raw, parse_constant=_reject_json_constant)


def parse_json_line(raw: bytes) -> dict[str, Any] | None:
    try:
        payload = strict_json_loads(raw)
    except (UnicodeDecodeError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _finite_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        return None
    try:
        parsed = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def duration_ms_to_microseconds(value: Any) -> int | None:
    parsed = _finite_decimal(value)
    if parsed is None or parsed < 0 or parsed > MAX_TASK_DURATION_MS:
        return None
    return int((parsed * 1000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def seconds_to_microseconds(value: Any, maximum_seconds: int | None = None) -> int | None:
    parsed = _finite_decimal(value)
    if parsed is None or parsed < 0:
        return None
    if maximum_seconds is not None and parsed > maximum_seconds:
        return None
    return int((parsed * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def rounded_seconds(microseconds: int) -> float:
    if isinstance(microseconds, bool) or not isinstance(microseconds, int) or microseconds < 0:
        raise ValueError("microseconds must be a non-negative integer")
    value = (Decimal(microseconds) / Decimal(1_000_000)).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP
    )
    return float(value)


def duration_label_microseconds(microseconds: int) -> str:
    if isinstance(microseconds, bool) or not isinstance(microseconds, int) or microseconds < 0:
        raise ValueError("microseconds must be a non-negative integer")
    whole = int(
        (Decimal(microseconds) / Decimal(1_000_000)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    )
    days, remainder = divmod(whole, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{days}d {hours:02d}h {minutes:02d}m {secs:02d}s"


def duration_label(seconds: float) -> str:
    microseconds = seconds_to_microseconds(seconds)
    if microseconds is None:
        raise ValueError("seconds must be finite and non-negative")
    return duration_label_microseconds(microseconds)


def _datetime_to_epoch_microseconds(value: datetime) -> int:
    normalized = value.astimezone(timezone.utc)
    delta = normalized - UTC_EPOCH
    return ((delta.days * 86400 + delta.seconds) * 1_000_000) + delta.microseconds


def parse_utc_instant_microseconds(value: Any) -> int | None:
    numeric = _finite_decimal(value)
    if numeric is not None:
        microseconds = int((numeric * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        try:
            UTC_EPOCH + timedelta(microseconds=microseconds)
        except (OverflowError, ValueError):
            return None
        return microseconds
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return _datetime_to_epoch_microseconds(parsed)
    except (OverflowError, ValueError):
        return None


def epoch_microseconds_to_utc(microseconds: int) -> str:
    value = UTC_EPOCH + timedelta(microseconds=microseconds)
    return value.isoformat(timespec="microseconds").replace("+00:00", "Z")


def event_epoch_seconds(payload: dict[str, Any], fallback_iso: str | None) -> float | None:
    for key in ("completed_at", "started_at"):
        if key in payload:
            value = parse_utc_instant_microseconds(payload[key])
            return None if value is None else value / 1_000_000
    value = parse_utc_instant_microseconds(fallback_iso)
    return None if value is None else value / 1_000_000


def _stat_signature(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)


def _same_source_snapshot(first: os.stat_result, second: os.stat_result) -> bool:
    return _stat_signature(first) == _stat_signature(second)


def _nonempty_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def scan_session_file(path: Path, sessions_root: Path) -> dict[str, Any]:
    if sessions_root.is_symlink():
        raise SourceScanError("ROOT_IS_SYMLINK")
    try:
        resolved_root = sessions_root.resolve(strict=True)
        initial = path.lstat()
    except OSError as exc:
        raise SourceScanError("SOURCE_STAT_ERROR") from exc
    if path.is_symlink():
        raise SourceScanError("SOURCE_IS_SYMLINK")
    try:
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(resolved_root)
    except (OSError, ValueError) as exc:
        raise SourceScanError("SOURCE_OUTSIDE_ROOT") from exc
    if not path.is_file():
        raise SourceScanError("SOURCE_NOT_REGULAR_FILE")

    model_contexts: dict[str, set[str]] = defaultdict(set)
    completed_seen: set[str] = set()
    start_event_ids: list[str] = []
    abort_event_ids: list[str] = []
    completions: list[dict[str, Any]] = []
    model_context_event_count = 0
    completion_event_count = 0
    task_aborted_event_count = 0
    context_compactions = 0
    parse_error_count = 0
    invalid_selected_event_count = 0
    rejected_completion_event_count = 0
    invalid_duration_count = 0
    invalid_completion_timestamp_count = 0
    late_model_context_count = 0

    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(resolved_path, flags)
        with os.fdopen(descriptor, "rb", buffering=1024 * 1024) as handle:
            opened = os.fstat(handle.fileno())
            if not _same_source_snapshot(initial, opened):
                raise SourceScanError("SOURCE_MUTATED_DURING_SCAN")
            for raw in handle:
                if not raw.strip():
                    continue
                row = parse_json_line(raw)
                if row is None:
                    parse_error_count += 1
                    continue
                row_type = row.get("type")
                if not isinstance(row_type, str) or row_type not in {"turn_context", "event_msg"}:
                    continue
                payload = row.get("payload")
                if not isinstance(payload, dict):
                    invalid_selected_event_count += 1
                    continue
                if row_type == "turn_context":
                    turn_id = _nonempty_string(payload.get("turn_id"))
                    model = _nonempty_string(payload.get("model"))
                    if turn_id is None or model is None or model in RESERVED_MODEL_LABELS:
                        invalid_selected_event_count += 1
                        continue
                    model_context_event_count += 1
                    if turn_id in completed_seen:
                        late_model_context_count += 1
                    else:
                        model_contexts[turn_id].add(model)
                    continue

                event_type = payload.get("type")
                if not isinstance(event_type, str):
                    invalid_selected_event_count += 1
                    continue
                if event_type == "context_compacted":
                    context_compactions += 1
                    continue
                if event_type not in {"task_started", "task_complete", "turn_aborted"}:
                    continue
                turn_id = _nonempty_string(payload.get("turn_id"))
                if event_type == "task_started":
                    if turn_id is None:
                        invalid_selected_event_count += 1
                    else:
                        start_event_ids.append(turn_id)
                    continue
                if event_type == "turn_aborted":
                    task_aborted_event_count += 1
                    if turn_id is None:
                        invalid_selected_event_count += 1
                    else:
                        abort_event_ids.append(turn_id)
                    continue

                completion_event_count += 1
                if turn_id is None:
                    invalid_selected_event_count += 1
                    rejected_completion_event_count += 1
                    continue
                duration_microseconds = duration_ms_to_microseconds(payload.get("duration_ms"))
                if duration_microseconds is None:
                    invalid_selected_event_count += 1
                    rejected_completion_event_count += 1
                    invalid_duration_count += 1
                    continue
                completion_value = payload.get("completed_at") if "completed_at" in payload else row.get("timestamp")
                completed_microseconds = parse_utc_instant_microseconds(completion_value)
                if completed_microseconds is None:
                    invalid_selected_event_count += 1
                    rejected_completion_event_count += 1
                    invalid_completion_timestamp_count += 1
                    continue
                candidates = model_contexts.get(turn_id, set())
                if len(candidates) == 1:
                    model = next(iter(candidates))
                elif len(candidates) > 1:
                    model = AMBIGUOUS_MODEL
                else:
                    model = UNATTRIBUTED_MODEL
                completions.append(
                    {
                        "turn_id": turn_id,
                        "model": model,
                        "duration_microseconds": duration_microseconds,
                        "started_epoch_microseconds": completed_microseconds - duration_microseconds,
                        "completed_epoch_microseconds": completed_microseconds,
                    }
                )
                completed_seen.add(turn_id)
            final_handle = os.fstat(handle.fileno())
    except SourceScanError:
        raise
    except OSError:
        raise

    try:
        final_path = path.lstat()
    except OSError as exc:
        raise SourceScanError("SOURCE_STAT_ERROR") from exc
    if path.is_symlink() or not _same_source_snapshot(initial, final_handle) or not _same_source_snapshot(initial, final_path):
        raise SourceScanError("SOURCE_MUTATED_DURING_SCAN")

    return {
        "parse_error_count": parse_error_count,
        "invalid_selected_event_count": invalid_selected_event_count,
        "rejected_completion_event_count": rejected_completion_event_count,
        "invalid_duration_count": invalid_duration_count,
        "invalid_completion_timestamp_count": invalid_completion_timestamp_count,
        "completion_event_count": completion_event_count,
        "task_aborted_event_count": task_aborted_event_count,
        "context_compaction_count": context_compactions,
        "model_context_event_count": model_context_event_count,
        "late_model_context_count": late_model_context_count,
        "_internal": {
            "model_contexts": {turn_id: frozenset(models) for turn_id, models in model_contexts.items()},
            "start_event_ids": tuple(start_event_ids),
            "abort_event_ids": tuple(abort_event_ids),
            "completions": tuple(completions),
        },
    }


def merge_interval_microseconds(intervals: Iterable[tuple[int, int]]) -> int:
    ordered: list[tuple[int, int]] = []
    for start, end in intervals:
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
            or end < start
        ):
            raise ValueError("intervals must be ordered integer-microsecond pairs")
        ordered.append((start, end))
    ordered.sort()
    if not ordered:
        return 0
    total = 0
    start, end = ordered[0]
    for next_start, next_end in ordered[1:]:
        if next_start <= end:
            end = max(end, next_end)
        else:
            total += end - start
            start, end = next_start, next_end
    return total + end - start


def merge_intervals(intervals: Iterable[tuple[float, float]]) -> float:
    normalized: list[tuple[int, int]] = []
    for start, end in intervals:
        start_decimal = _finite_decimal(start)
        end_decimal = _finite_decimal(end)
        if start_decimal is None or end_decimal is None:
            raise ValueError("interval endpoints must be finite numbers")
        start_us = int((start_decimal * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        end_us = int((end_decimal * 1_000_000).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        normalized.append((min(start_us, end_us), max(start_us, end_us)))
    return merge_interval_microseconds(normalized) / 1_000_000


def _sum_scan_counter(scans: list[dict[str, Any]], key: str) -> int:
    return sum(int(scan.get(key, 0)) for scan in scans)


def aggregate_session_scans(
    scans: list[dict[str, Any]],
    *,
    source_file_discovery_count: int | None = None,
    source_failure_reasons: dict[str, int] | Counter[str] | None = None,
) -> dict[str, Any]:
    failures = Counter(source_failure_reasons or {})
    discovery_count = len(scans) if source_file_discovery_count is None else source_file_discovery_count
    model_contexts: dict[str, set[str]] = defaultdict(set)
    start_event_ids: list[str] = []
    abort_event_ids: list[str] = []
    completion_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    # Read only from scan results. Callers may retain them for audit or retry.
    for scan in scans:
        internal = scan.get("_internal", {})
        for turn_id, models in internal.get("model_contexts", {}).items():
            model_contexts[turn_id].update(models)
        start_event_ids.extend(internal.get("start_event_ids", ()))
        abort_event_ids.extend(internal.get("abort_event_ids", ()))
        for completion in internal.get("completions", ()):
            completion_groups[completion["turn_id"]].append(completion)

    accepted: list[dict[str, Any]] = []
    duplicate_completion_count = 0
    conflicting_duplicate_task_count = 0
    ambiguous_model_completion_count = 0
    for records in completion_groups.values():
        duplicate_completion_count += max(0, len(records) - 1)
        interval_signatures = {
            (
                row["started_epoch_microseconds"],
                row["completed_epoch_microseconds"],
                row["duration_microseconds"],
            )
            for row in records
        }
        if len(interval_signatures) != 1:
            conflicting_duplicate_task_count += 1
            continue
        models = {row["model"] for row in records}
        model = next(iter(models)) if len(models) == 1 else AMBIGUOUS_MODEL
        if model == AMBIGUOUS_MODEL:
            ambiguous_model_completion_count += 1
        sample = records[0]
        accepted.append(
            {
                "model": model,
                "duration_microseconds": sample["duration_microseconds"],
                "started_epoch_microseconds": sample["started_epoch_microseconds"],
                "completed_epoch_microseconds": sample["completed_epoch_microseconds"],
            }
        )

    per_model_turns: Counter[str] = Counter()
    for models in model_contexts.values():
        label = next(iter(models)) if len(models) == 1 else AMBIGUOUS_MODEL
        per_model_turns[label] += 1

    per_model: dict[str, Any] = {}
    model_labels = set(per_model_turns) | {row["model"] for row in accepted}
    for model in sorted(model_labels):
        rows = [row for row in accepted if row["model"] == model]
        additive_us = sum(row["duration_microseconds"] for row in rows)
        union_us = merge_interval_microseconds(
            (row["started_epoch_microseconds"], row["completed_epoch_microseconds"]) for row in rows
        )
        if union_us > additive_us:
            raise AssertionError("calendar union cannot exceed additive elapsed time")
        per_model[model] = {
            "turn_context_count": per_model_turns[model],
            "completed_task_count": len(rows),
            "additive_task_elapsed_microseconds": additive_us,
            "additive_task_elapsed_seconds": rounded_seconds(additive_us),
            "additive_task_elapsed_label": duration_label_microseconds(additive_us),
            "calendar_union_elapsed_microseconds": union_us,
            "calendar_union_elapsed_seconds": rounded_seconds(union_us),
            "calendar_union_elapsed_label": duration_label_microseconds(union_us),
        }

    total_additive_us = sum(row["duration_microseconds"] for row in accepted)
    total_union_us = merge_interval_microseconds(
        (row["started_epoch_microseconds"], row["completed_epoch_microseconds"]) for row in accepted
    )
    if total_union_us > total_additive_us:
        raise AssertionError("calendar union cannot exceed additive elapsed time")

    valid_completion_ids = set(completion_groups)
    unique_starts = set(start_event_ids)
    unique_aborts = set(abort_event_ids)
    pending_ids = unique_starts - valid_completion_ids - unique_aborts
    unattributed_count = sum(1 for row in accepted if row["model"] == UNATTRIBUTED_MODEL)

    parse_error_count = _sum_scan_counter(scans, "parse_error_count")
    invalid_selected_event_count = _sum_scan_counter(scans, "invalid_selected_event_count")
    rejected_completion_event_count = _sum_scan_counter(scans, "rejected_completion_event_count")
    quality_reasons = set(failures)
    if parse_error_count:
        quality_reasons.add("JSON_PARSE_ERRORS")
    if invalid_selected_event_count:
        quality_reasons.add("INVALID_SELECTED_EVENTS")
    if rejected_completion_event_count:
        quality_reasons.add("REJECTED_COMPLETION_EVENTS")
    if duplicate_completion_count:
        quality_reasons.add("DUPLICATE_COMPLETIONS_DEDUPLICATED")
    if conflicting_duplicate_task_count:
        quality_reasons.add("CONFLICTING_DUPLICATE_COMPLETIONS_EXCLUDED")
    if ambiguous_model_completion_count:
        quality_reasons.add("AMBIGUOUS_MODEL_ATTRIBUTION")
    if unattributed_count:
        quality_reasons.add("UNATTRIBUTED_MODEL_COMPLETIONS")

    source_failure_count = sum(failures.values())
    if not scans and (discovery_count > 0 or source_failure_count > 0):
        quality = "INVALID"
    elif quality_reasons:
        quality = "DEGRADED"
    else:
        quality = "VALID"

    starts = [row["started_epoch_microseconds"] for row in accepted]
    completions = [row["completed_epoch_microseconds"] for row in accepted]
    return {
        "schema": WORK_SCHEMA,
        "quality": quality,
        "quality_reasons": sorted(quality_reasons),
        "rounding_policy": copy.deepcopy(ROUNDING_POLICY),
        "session_file_count": len(scans),
        "source_file_discovery_count": discovery_count,
        "source_file_failure_count": source_failure_count,
        "source_file_failure_reasons": [
            {"reason": reason, "count": failures[reason]} for reason in sorted(failures)
        ],
        "parse_error_count": parse_error_count,
        "invalid_selected_event_count": invalid_selected_event_count,
        "invalid_duration_count": _sum_scan_counter(scans, "invalid_duration_count"),
        "invalid_completion_timestamp_count": _sum_scan_counter(
            scans, "invalid_completion_timestamp_count"
        ),
        "task_started_event_count": len(start_event_ids),
        "task_started_count": len(unique_starts),
        "duplicate_task_start_count": len(start_event_ids) - len(unique_starts),
        "completion_event_count": _sum_scan_counter(scans, "completion_event_count"),
        "rejected_completion_event_count": rejected_completion_event_count,
        "duplicate_completion_count": duplicate_completion_count,
        "conflicting_duplicate_task_count": conflicting_duplicate_task_count,
        "completed_task_count": len(accepted),
        "pending_task_count": len(pending_ids),
        "task_aborted_event_count": _sum_scan_counter(scans, "task_aborted_event_count"),
        "task_aborted_count": len(unique_aborts),
        "context_compaction_count": _sum_scan_counter(scans, "context_compaction_count"),
        "turn_context_event_count": _sum_scan_counter(scans, "model_context_event_count"),
        "turn_context_count": len(model_contexts),
        "late_model_context_count": _sum_scan_counter(scans, "late_model_context_count"),
        "ambiguous_model_completion_count": ambiguous_model_completion_count,
        "unattributed_model_completion_count": unattributed_count,
        "measurement_interval_start_utc": epoch_microseconds_to_utc(min(starts)) if starts else None,
        "measurement_interval_end_utc": epoch_microseconds_to_utc(max(completions)) if completions else None,
        "additive_task_elapsed_microseconds": total_additive_us,
        "additive_task_elapsed_seconds": rounded_seconds(total_additive_us),
        "additive_task_elapsed_label": duration_label_microseconds(total_additive_us),
        "calendar_union_elapsed_microseconds": total_union_us,
        "calendar_union_elapsed_seconds": rounded_seconds(total_union_us),
        "calendar_union_elapsed_label": duration_label_microseconds(total_union_us),
        "per_model": per_model,
    }


def _invalid_root_measurement(reason: str) -> dict[str, Any]:
    payload = aggregate_session_scans([], source_file_discovery_count=0)
    payload["quality"] = "INVALID"
    payload["quality_reasons"] = [reason]
    return payload


def scan_sessions(sessions_root: Path, max_workers: int) -> dict[str, Any]:
    try:
        if sessions_root.is_symlink():
            return _invalid_root_measurement("ROOT_IS_SYMLINK")
        resolved_root = sessions_root.resolve(strict=True)
        if not resolved_root.is_dir():
            return _invalid_root_measurement("ROOT_NOT_DIRECTORY")
    except FileNotFoundError:
        return _invalid_root_measurement("ROOT_MISSING")
    except OSError:
        return _invalid_root_measurement("ROOT_VALIDATION_ERROR")

    files: list[Path] = []
    failures: Counter[str] = Counter()
    discovery_count = 0

    def on_walk_error(_: OSError) -> None:
        failures["SOURCE_DISCOVERY_ERROR"] += 1

    for directory, dirnames, filenames in os.walk(resolved_root, followlinks=False, onerror=on_walk_error):
        directory_path = Path(directory)
        kept_directories: list[str] = []
        for dirname in dirnames:
            candidate = directory_path / dirname
            if candidate.is_symlink():
                failures["SOURCE_SYMLINK_DIRECTORY_REJECTED"] += 1
            else:
                kept_directories.append(dirname)
        dirnames[:] = kept_directories
        for filename in filenames:
            if not filename.lower().endswith(".jsonl"):
                continue
            discovery_count += 1
            candidate = directory_path / filename
            if candidate.is_symlink():
                failures["SOURCE_SYMLINK_FILE_REJECTED"] += 1
                continue
            try:
                candidate.resolve(strict=True).relative_to(resolved_root)
            except (OSError, ValueError):
                failures["SOURCE_OUTSIDE_ROOT"] += 1
                continue
            files.append(candidate)

    scans: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, int(max_workers))) as executor:
        futures = {executor.submit(scan_session_file, path, resolved_root): path for path in sorted(files)}
        for future in as_completed(futures):
            try:
                scans.append(future.result())
            except SourceScanError as exc:
                failures[exc.code] += 1
            except OSError:
                failures["SOURCE_READ_ERROR"] += 1

    return aggregate_session_scans(
        scans,
        source_file_discovery_count=discovery_count,
        source_failure_reasons=failures,
    )


def optional_package_version(name: str) -> str | None:
    try:
        from importlib.metadata import version

        return version(name)
    except Exception:
        return None


def windows_cpu_name() -> str:
    if os.name != "nt":
        return platform.processor() or "unknown"
    try:
        import winreg

        key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            value, _ = winreg.QueryValueEx(key, "ProcessorNameString")
        return str(value).strip()
    except Exception:
        return platform.processor() or "unknown"


def nvidia_snapshot() -> list[dict[str, Any]]:
    executable = shutil.which("nvidia-smi")
    if not executable:
        return []
    query = "name,driver_version,memory.total,memory.free,compute_cap,pstate"
    result = subprocess.run(
        [executable, f"--query-gpu={query}", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines():
        values = [value.strip() for value in line.split(",")]
        if len(values) != 6:
            continue
        try:
            total_memory = int(float(values[2]))
            free_memory = int(float(values[3]))
        except (OverflowError, ValueError):
            continue
        rows.append(
            {
                "name": values[0],
                "driver_version": values[1],
                "memory_total_mib": total_memory,
                "memory_free_mib": free_memory,
                "compute_capability": values[4],
                "power_state": values[5],
            }
        )
    return rows


def cuda_smoke_test(matrix_n: int = 4096, iterations: int = 20) -> dict[str, Any]:
    try:
        import torch
    except Exception as exc:
        return {"attempted": False, "available": False, "reason": type(exc).__name__}
    if not torch.cuda.is_available():
        return {
            "attempted": False,
            "available": False,
            "torch_version": torch.__version__,
            "compiled_cuda": torch.version.cuda,
        }
    device = torch.device("cuda:0")
    torch.manual_seed(20260715)
    left = torch.randn((matrix_n, matrix_n), device=device, dtype=torch.float16)
    right = torch.randn((matrix_n, matrix_n), device=device, dtype=torch.float16)
    result = left @ right
    torch.cuda.synchronize()
    started = time.perf_counter()
    for _ in range(iterations):
        result = left @ right
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    operations = 2 * (matrix_n**3) * iterations
    properties = torch.cuda.get_device_properties(0)
    return {
        "attempted": True,
        "available": True,
        "torch_version": torch.__version__,
        "compiled_cuda": torch.version.cuda,
        "device_name": torch.cuda.get_device_name(0),
        "compute_capability": list(torch.cuda.get_device_capability(0)),
        "vram_bytes": properties.total_memory,
        "dtype": "float16",
        "matrix_n": matrix_n,
        "iterations": iterations,
        "elapsed_seconds": round(elapsed, 6),
        "estimated_tflops": round(operations / elapsed / 1e12, 6),
        "checksum_mean_fp32": float(result.float().mean().item()),
        "boundary": "local_engineering_smoke_test_not_vendor_or_scientific_benchmark",
    }


def collect_compute_snapshot(run_cuda_smoke: bool) -> dict[str, Any]:
    memory: dict[str, Any] = {}
    physical_cores: int | None = None
    try:
        import psutil

        vm = psutil.virtual_memory()
        memory = {"total_bytes": vm.total, "available_bytes": vm.available}
        physical_cores = psutil.cpu_count(logical=False)
    except Exception:
        pass
    torch_snapshot: dict[str, Any] = {}
    try:
        import torch

        torch_snapshot = {
            "version": torch.__version__,
            "compiled_cuda": torch.version.cuda,
            "cuda_available": torch.cuda.is_available(),
            "cuda_device_count": torch.cuda.device_count(),
        }
    except Exception:
        torch_snapshot = {"installed": False}
    return {
        "observed_utc": utc_now(),
        "cpu": {
            "name": windows_cpu_name(),
            "physical_cores": physical_cores,
            "logical_processors": os.cpu_count(),
        },
        "memory": memory,
        "nvidia_gpus": nvidia_snapshot(),
        "python_runtime": {
            "version": platform.python_version(),
            "implementation": platform.python_implementation(),
            "numpy": optional_package_version("numpy"),
            "scikit_learn": optional_package_version("scikit-learn"),
            "torch": optional_package_version("torch"),
            "transformers": optional_package_version("transformers"),
        },
        "torch_runtime": torch_snapshot,
        "cuda_smoke_test": cuda_smoke_test() if run_cuda_smoke else {"attempted": False},
    }


def artifact_receipt(path: Path, artifact_id: str) -> dict[str, Any]:
    if not path.is_file():
        return {"artifact_id": artifact_id, "present": False, "bytes": 0}
    return {"artifact_id": artifact_id, "present": True, "bytes": path.stat().st_size}


def count_tree(root: Path, exclude_dependencies: bool) -> dict[str, int]:
    files = 0
    size_bytes = 0
    if not root.is_dir():
        return {"file_count": 0, "size_bytes": 0}
    for directory, dirnames, filenames in os.walk(root):
        if exclude_dependencies:
            dirnames[:] = [name for name in dirnames if name.lower() not in DEPENDENCY_DIR_NAMES]
        for filename in filenames:
            path = Path(directory) / filename
            try:
                size_bytes += path.stat().st_size
                files += 1
            except OSError:
                continue
    return {"file_count": files, "size_bytes": size_bytes}


def collect_existing_assets(quant_lab_root: Path, premium_summary: Path, stack_root: Path) -> dict[str, Any]:
    quant_full = count_tree(quant_lab_root, exclude_dependencies=False)
    quant_research = count_tree(quant_lab_root, exclude_dependencies=True)
    quant_artifacts = [
        artifact_receipt(quant_lab_root / relative, f"quant_lab_artifact_{index:02d}")
        for index, relative in enumerate(KEY_QUANTLAB_ARTIFACTS, start=1)
    ]
    premium: dict[str, Any] = {"present": premium_summary.is_file()}
    if premium_summary.is_file():
        raw = strict_json_loads(premium_summary.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("premium summary must be a JSON object")
        premium.update(
            {
                "generated_utc": raw.get("generated_utc"),
                "total_sources": raw.get("total_sources"),
                "total_files_seen": raw.get("total_files_seen"),
                "total_files_copied": raw.get("total_files_copied"),
                "total_bytes_seen": raw.get("total_bytes_seen"),
                "latest_zip_count_from_proofs": raw.get("latest_zip_count_from_proofs"),
                "summary_bytes": premium_summary.stat().st_size,
            }
        )
    stack_artifacts = [
        artifact_receipt(stack_root / relative, f"stack_artifact_{index:02d}")
        for index, relative in enumerate(KEY_STACK_ARTIFACTS, start=1)
    ]
    return {
        "quant_lab": {
            "present": quant_lab_root.is_dir(),
            "all_files_including_dependencies": quant_full,
            "files_excluding_dependencies_and_caches": quant_research,
            "key_artifacts": quant_artifacts,
            "boundary": "file_count_is_not_simulation_or_independent_run_count",
        },
        "premium_mirror": premium,
        "canonical_evidence_references": stack_artifacts,
    }


def goal_snapshot(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.active_goal_seconds is None and args.active_goal_tokens is None:
        return None
    seconds = args.active_goal_seconds if args.active_goal_seconds is not None else 0
    elapsed_us = seconds_to_microseconds(seconds, MAX_GOAL_DURATION_SECONDS)
    if elapsed_us is None:
        raise ValueError("active goal duration must be finite, non-negative, and plausible")
    tokens = args.active_goal_tokens
    if tokens is not None and (isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0):
        raise ValueError("active goal token count must be a non-negative integer")
    created_utc = args.active_goal_created_utc
    if created_utc is not None:
        created_us = parse_utc_instant_microseconds(created_utc)
        if created_us is None:
            raise ValueError("active goal creation time must be timezone-aware")
        created_utc = epoch_microseconds_to_utc(created_us)
    return {
        "observed_utc": utc_now(),
        "model": args.active_goal_model or None,
        "time_used_microseconds": elapsed_us,
        "time_used_seconds": rounded_seconds(elapsed_us),
        "time_used_label": duration_label_microseconds(elapsed_us),
        "tokens_used": tokens,
        "created_utc": created_utc,
        "objective_text_included": False,
        "boundary": "goal_runtime_snapshot_not_added_to_completed_task_totals",
    }


def validate_protocol(protocol: dict[str, Any]) -> None:
    if not isinstance(protocol, dict):
        raise ValueError("protocol must be a JSON object")
    expected_scalars = {
        "schema": PROTOCOL_SCHEMA,
        "status": "frozen",
        "receipt_schema": RECEIPT_SCHEMA,
        "work_schema": WORK_SCHEMA,
        "packet_manifest_schema": PACKET_MANIFEST_SCHEMA,
    }
    for key, expected in expected_scalars.items():
        if protocol.get(key) != expected:
            raise ValueError(f"protocol invariant failed: {key}")
    work = protocol.get("work_measurement")
    if not isinstance(work, dict):
        raise ValueError("protocol invariant failed: work_measurement")
    duration_validation = work.get("duration_validation")
    if not isinstance(duration_validation, dict):
        raise ValueError("protocol invariant failed: duration_validation")
    if duration_validation.get("minimum_ms") != 0:
        raise ValueError("protocol invariant failed: minimum_ms")
    maximum = duration_validation.get("maximum_ms")
    if isinstance(maximum, bool) or maximum != MAX_TASK_DURATION_MS:
        raise ValueError("protocol invariant failed: maximum_ms")
    if duration_validation.get("boolean_allowed") is not False:
        raise ValueError("protocol invariant failed: boolean_allowed")
    if duration_validation.get("non_finite_allowed") is not False:
        raise ValueError("protocol invariant failed: non_finite_allowed")
    if work.get("rounding") != ROUNDING_POLICY:
        raise ValueError("protocol invariant failed: rounding")
    if work.get("interval_endpoint_timezone") != "UTC":
        raise ValueError("protocol invariant failed: interval_endpoint_timezone")
    if protocol.get("measurement_quality_levels") != ["VALID", "DEGRADED", "INVALID"]:
        raise ValueError("protocol invariant failed: measurement_quality_levels")
    privacy = protocol.get("privacy")
    if not isinstance(privacy, dict):
        raise ValueError("protocol invariant failed: privacy")
    false_privacy_invariants = (
        "message_content_read_for_measurement",
        "message_content_written_to_receipt",
        "prompt_content_written_to_receipt",
        "tool_output_content_written_to_receipt",
        "credentials_or_environment_values_written_to_receipt",
        "session_paths_written_to_receipt",
        "session_ids_written_to_receipt",
        "input_file_content_hashes_written_to_receipt",
        "stable_source_aliases_written_to_receipt",
    )
    for key in false_privacy_invariants:
        if privacy.get(key) is not False:
            raise ValueError(f"protocol invariant failed: privacy.{key}")
    if privacy.get("session_identity_mode") != "none":
        raise ValueError("protocol invariant failed: privacy.session_identity_mode")
    boundaries = protocol.get("claim_boundaries")
    if not isinstance(boundaries, list) or not boundaries or not all(
        isinstance(item, str) and item for item in boundaries
    ):
        raise ValueError("protocol invariant failed: claim_boundaries")


def _nonnegative_int(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"work invariant failed: {key}")
    return value


def validate_work_measurement(work: dict[str, Any]) -> None:
    if not isinstance(work, dict) or work.get("schema") != WORK_SCHEMA:
        raise ValueError("work invariant failed: schema")
    if work.get("quality") not in QUALITY_LEVELS:
        raise ValueError("work invariant failed: quality")
    if work.get("rounding_policy") != ROUNDING_POLICY:
        raise ValueError("work invariant failed: rounding_policy")
    quality_reasons = work.get("quality_reasons")
    if (
        not isinstance(quality_reasons, list)
        or quality_reasons != sorted(set(quality_reasons))
        or not all(isinstance(reason, str) and reason for reason in quality_reasons)
    ):
        raise ValueError("work invariant failed: quality_reasons")
    count_keys = (
        "session_file_count",
        "source_file_discovery_count",
        "source_file_failure_count",
        "parse_error_count",
        "invalid_selected_event_count",
        "invalid_duration_count",
        "invalid_completion_timestamp_count",
        "task_started_event_count",
        "task_started_count",
        "duplicate_task_start_count",
        "completion_event_count",
        "rejected_completion_event_count",
        "duplicate_completion_count",
        "conflicting_duplicate_task_count",
        "completed_task_count",
        "pending_task_count",
        "task_aborted_event_count",
        "task_aborted_count",
        "context_compaction_count",
        "turn_context_event_count",
        "turn_context_count",
        "late_model_context_count",
        "ambiguous_model_completion_count",
        "unattributed_model_completion_count",
    )
    for key in count_keys:
        _nonnegative_int(work, key)
    if work["session_file_count"] > work["source_file_discovery_count"]:
        raise ValueError("work invariant failed: scanned files exceed discovery")
    if work["task_started_count"] > work["task_started_event_count"]:
        raise ValueError("work invariant failed: unique starts exceed start events")
    if work["task_aborted_count"] > work["task_aborted_event_count"]:
        raise ValueError("work invariant failed: unique aborts exceed abort events")
    if work["completed_task_count"] > work["completion_event_count"]:
        raise ValueError("work invariant failed: completions exceed completion events")
    failure_reasons = work.get("source_file_failure_reasons")
    if not isinstance(failure_reasons, list):
        raise ValueError("work invariant failed: source_file_failure_reasons")
    failure_total = 0
    for row in failure_reasons:
        if not isinstance(row, dict) or not isinstance(row.get("reason"), str) or not row["reason"]:
            raise ValueError("work invariant failed: source failure reason")
        failure_total += _nonnegative_int(row, "count")
    if failure_total != work["source_file_failure_count"]:
        raise ValueError("work invariant failed: source failure total")
    additive = _nonnegative_int(work, "additive_task_elapsed_microseconds")
    union = _nonnegative_int(work, "calendar_union_elapsed_microseconds")
    if union > additive:
        raise ValueError("work invariant failed: union exceeds additive")
    if work.get("additive_task_elapsed_seconds") != rounded_seconds(additive):
        raise ValueError("work invariant failed: additive seconds rounding")
    if work.get("calendar_union_elapsed_seconds") != rounded_seconds(union):
        raise ValueError("work invariant failed: union seconds rounding")
    if work.get("additive_task_elapsed_label") != duration_label_microseconds(additive):
        raise ValueError("work invariant failed: additive label rounding")
    if work.get("calendar_union_elapsed_label") != duration_label_microseconds(union):
        raise ValueError("work invariant failed: union label rounding")
    interval_start = work.get("measurement_interval_start_utc")
    interval_end = work.get("measurement_interval_end_utc")
    if (interval_start is None) != (interval_end is None):
        raise ValueError("work invariant failed: measurement interval endpoints")
    if interval_start is not None:
        start_us = parse_utc_instant_microseconds(interval_start)
        end_us = parse_utc_instant_microseconds(interval_end)
        if start_us is None or end_us is None or end_us < start_us:
            raise ValueError("work invariant failed: measurement interval")
    completed = _nonnegative_int(work, "completed_task_count")
    per_model = work.get("per_model")
    if not isinstance(per_model, dict):
        raise ValueError("work invariant failed: per_model")
    model_completed = 0
    model_additive = 0
    for model, row in per_model.items():
        if not isinstance(model, str) or not model or not isinstance(row, dict):
            raise ValueError("work invariant failed: per_model entry")
        row_additive = _nonnegative_int(row, "additive_task_elapsed_microseconds")
        row_union = _nonnegative_int(row, "calendar_union_elapsed_microseconds")
        if row_union > row_additive:
            raise ValueError("work invariant failed: per-model union exceeds additive")
        if row.get("additive_task_elapsed_seconds") != rounded_seconds(row_additive):
            raise ValueError("work invariant failed: per-model additive seconds")
        if row.get("calendar_union_elapsed_seconds") != rounded_seconds(row_union):
            raise ValueError("work invariant failed: per-model union seconds")
        if row.get("additive_task_elapsed_label") != duration_label_microseconds(row_additive):
            raise ValueError("work invariant failed: per-model additive label")
        if row.get("calendar_union_elapsed_label") != duration_label_microseconds(row_union):
            raise ValueError("work invariant failed: per-model union label")
        _nonnegative_int(row, "turn_context_count")
        model_completed += _nonnegative_int(row, "completed_task_count")
        model_additive += row_additive
    if model_completed != completed or model_additive != additive:
        raise ValueError("work invariant failed: per-model totals")


def _assert_shareable_receipt_privacy(payload: Any) -> None:
    forbidden_keys = {
        "content_sha256_at_read",
        "source_alias_sha256",
        "output_alias_sha256",
        "session_path",
        "session_id",
        "summary_sha256",
    }
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in forbidden_keys or key == "sha256" or key.endswith("_sha256"):
                raise ValueError(f"shareable receipt contains forbidden field: {key}")
            _assert_shareable_receipt_privacy(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_shareable_receipt_privacy(value)


def build_payload(
    protocol: dict[str, Any],
    protocol_path: Path,
    work: dict[str, Any],
    compute: dict[str, Any],
    assets: dict[str, Any],
    goal: dict[str, Any] | None,
) -> dict[str, Any]:
    del protocol_path  # The receipt records protocol identity, never a local path or byte hash.
    validate_protocol(protocol)
    validate_work_measurement(work)
    status_by_quality = {
        "VALID": "MEASURED_VALID",
        "DEGRADED": "MEASURED_DEGRADED",
        "INVALID": "MEASUREMENT_INVALID",
    }
    payload = {
        "schema": RECEIPT_SCHEMA,
        "generated_utc": utc_now(),
        "status": status_by_quality[work["quality"]],
        "quality": work["quality"],
        "protocol": {
            "schema": protocol["schema"],
            "status": protocol["status"],
        },
        "work_provenance": copy.deepcopy(work),
        "active_goal_snapshot": copy.deepcopy(goal),
        "compute_snapshot": copy.deepcopy(compute),
        "existing_asset_snapshot": copy.deepcopy(assets),
        "privacy": copy.deepcopy(protocol["privacy"]),
        "claim_boundaries": copy.deepcopy(protocol["claim_boundaries"]),
    }
    _assert_shareable_receipt_privacy(payload)
    payload["receipt_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    work = payload["work_provenance"]
    compute = payload["compute_snapshot"]
    assets = payload["existing_asset_snapshot"]
    goal = payload.get("active_goal_snapshot") or {}
    lines = [
        "# Local Compute and Codex Work Provenance",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Status: `{payload['status']}`",
        f"Measurement quality: `{work['quality']}`",
        f"Receipt SHA-256: `{payload['receipt_sha256']}`",
        "",
        "## Work Measurement",
        "",
        f"- Session files scanned: `{work['session_file_count']}` of `{work['source_file_discovery_count']}` discovered",
        f"- Completed tasks: `{work['completed_task_count']}`",
        f"- Pending tasks: `{work['pending_task_count']}`",
        f"- Duplicate completions removed: `{work['duplicate_completion_count']}`",
        f"- Additive task elapsed: `{work['additive_task_elapsed_label']}`",
        f"- Calendar-union elapsed: `{work['calendar_union_elapsed_label']}`",
        f"- Context compactions observed: `{work['context_compaction_count']}`",
        f"- Quality reasons: `{', '.join(work['quality_reasons']) or 'none'}`",
    ]
    if goal:
        lines.extend(
            [
                f"- Current goal snapshot: `{goal['time_used_label']}` and `{goal.get('tokens_used')}` tokens",
                f"- Current goal model label: `{goal.get('model')}`",
            ]
        )
    lines.extend(["", "### Exact Model Labels", ""])
    for model, row in work["per_model"].items():
        lines.append(
            f"- `{model}`: {row['completed_task_count']} completed tasks; "
            f"additive `{row['additive_task_elapsed_label']}`; union `{row['calendar_union_elapsed_label']}`; "
            f"{row['turn_context_count']} turn contexts"
        )
    gpu = (compute.get("nvidia_gpus") or [{}])[0]
    smoke = compute.get("cuda_smoke_test") or {}
    lines.extend(
        [
            "",
            "## Compute Snapshot",
            "",
            f"- CPU: `{compute.get('cpu', {}).get('name')}`",
            f"- Logical processors: `{compute.get('cpu', {}).get('logical_processors')}`",
            f"- NVIDIA GPU: `{gpu.get('name')}` with `{gpu.get('memory_total_mib')}` MiB",
            f"- NVIDIA driver: `{gpu.get('driver_version')}`; compute capability `{gpu.get('compute_capability')}`",
            f"- PyTorch: `{compute.get('torch_runtime', {}).get('version')}`; CUDA available `{compute.get('torch_runtime', {}).get('cuda_available')}`",
            f"- Bounded CUDA smoke: attempted `{smoke.get('attempted')}`; estimated TFLOPS `{smoke.get('estimated_tflops')}`",
            "",
            "## Existing Assets",
            "",
            f"- QuantLab files including dependencies: `{assets['quant_lab']['all_files_including_dependencies']['file_count']}`",
            f"- QuantLab files excluding dependencies/caches: `{assets['quant_lab']['files_excluding_dependencies_and_caches']['file_count']}`",
            f"- Premium sources indexed: `{assets['premium_mirror'].get('total_sources')}`",
            f"- Premium files observed: `{assets['premium_mirror'].get('total_files_seen')}`",
            f"- Premium bytes observed: `{assets['premium_mirror'].get('total_bytes_seen')}`",
            "",
            "## Boundaries",
            "",
        ]
    )
    lines.extend(f"- {boundary}" for boundary in payload["claim_boundaries"])
    return "\n".join(lines) + "\n"


def _zip_info(name: str, generated_utc: str) -> zipfile.ZipInfo:
    instant = parse_utc_instant_microseconds(generated_utc)
    if instant is None:
        raise ValueError("packet generation time must be timezone-aware")
    value = UTC_EPOCH + timedelta(microseconds=instant)
    info = zipfile.ZipInfo(name, date_time=(value.year, value.month, value.day, value.hour, value.minute, value.second))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o644 << 16
    return info


def _publish_no_replace(temporary: Path, destination: Path) -> None:
    try:
        os.link(temporary, destination)
    except FileExistsError:
        raise FileExistsError(f"archive packet already exists: {destination.name}") from None
    except OSError as exc:
        raise OSError("filesystem cannot atomically publish a no-replace packet") from exc


def write_packet(payload: dict[str, Any], output_dirs: list[Path]) -> list[dict[str, Any]]:
    if not output_dirs:
        raise ValueError("at least one output directory is required")
    generated_us = parse_utc_instant_microseconds(payload.get("generated_utc"))
    if generated_us is None:
        raise ValueError("payload generated_utc must be timezone-aware")
    generated = UTC_EPOCH + timedelta(microseconds=generated_us)
    stamp = generated.strftime("%Y%m%dT%H%M%S%fZ")
    receipt_sha = payload.get("receipt_sha256")
    if not isinstance(receipt_sha, str) or len(receipt_sha) != 64:
        raise ValueError("payload receipt_sha256 is invalid")
    unsigned_payload = copy.deepcopy(payload)
    unsigned_payload.pop("receipt_sha256", None)
    _assert_shareable_receipt_privacy(unsigned_payload)
    if stable_sha256(unsigned_payload) != receipt_sha:
        raise ValueError("payload receipt_sha256 does not match payload content")

    json_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    markdown_bytes = render_markdown(payload).encode("utf-8")
    json_name = "local_compute_work_provenance.json"
    markdown_name = "local_compute_work_provenance.md"
    manifest = {
        "schema": PACKET_MANIFEST_SCHEMA,
        "generated_utc": payload["generated_utc"],
        "receipt_sha256": receipt_sha,
        "files": [
            {"name": json_name, "bytes": len(json_bytes), "sha256": hashlib.sha256(json_bytes).hexdigest()},
            {
                "name": markdown_name,
                "bytes": len(markdown_bytes),
                "sha256": hashlib.sha256(markdown_bytes).hexdigest(),
            },
        ],
    }
    manifest["manifest_sha256"] = stable_sha256(manifest)
    manifest_bytes = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    packet_name = f"local_compute_work_provenance_packet_{stamp}_{receipt_sha[:12]}.zip"

    normalized_output_dirs: list[Path] = []
    seen_output_dirs: set[Path] = set()
    for output_dir in output_dirs:
        output_dir.mkdir(parents=True, exist_ok=True)
        normalized = output_dir.resolve()
        if normalized in seen_output_dirs:
            raise ValueError("duplicate output directory")
        seen_output_dirs.add(normalized)
        destination = normalized / packet_name
        if destination.exists() or destination.is_symlink():
            raise FileExistsError(f"archive packet already exists: {packet_name}")
        normalized_output_dirs.append(normalized)

    outputs: list[dict[str, Any]] = []
    for output_dir in normalized_output_dirs:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{packet_name}.", suffix=".tmp", dir=output_dir
        )
        os.close(descriptor)
        temporary = Path(temporary_name)
        destination = output_dir / packet_name
        try:
            with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr(_zip_info(json_name, payload["generated_utc"]), json_bytes)
                archive.writestr(_zip_info(markdown_name, payload["generated_utc"]), markdown_bytes)
                archive.writestr(_zip_info("manifest.json", payload["generated_utc"]), manifest_bytes)
            with temporary.open("r+b") as handle:
                os.fsync(handle.fileno())
            _publish_no_replace(temporary, destination)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

        atomic_write(output_dir / "local_compute_work_provenance_latest.json", json_bytes)
        atomic_write(output_dir / "local_compute_work_provenance_latest.md", markdown_bytes)
        atomic_write(output_dir / "local_compute_work_provenance_manifest_latest.json", manifest_bytes)
        latest_pointer = {
            "schema": LATEST_POINTER_SCHEMA,
            "generated_utc": payload["generated_utc"],
            "packet_name": packet_name,
            "receipt_sha256": receipt_sha,
            "manifest_sha256": manifest["manifest_sha256"],
        }
        atomic_write(
            output_dir / "local_compute_work_provenance_latest_packet.json",
            json.dumps(latest_pointer, indent=2, sort_keys=True).encode("utf-8") + b"\n",
        )
        outputs.append(
            {
                "packet_name": packet_name,
                "receipt_sha256": receipt_sha,
                "manifest_sha256": manifest["manifest_sha256"],
            }
        )
    return outputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--sessions-root", type=Path, required=True)
    parser.add_argument("--quant-lab-root", type=Path, required=True)
    parser.add_argument("--premium-summary", type=Path, required=True)
    parser.add_argument("--stack-root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, action="append", required=True)
    parser.add_argument("--max-workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--run-cuda-smoke", action="store_true")
    parser.add_argument("--active-goal-seconds", type=float)
    parser.add_argument("--active-goal-tokens", type=int)
    parser.add_argument("--active-goal-model")
    parser.add_argument("--active-goal-created-utc")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    protocol = strict_json_loads(args.protocol.read_text(encoding="utf-8"))
    if not isinstance(protocol, dict):
        raise ValueError("protocol must be a JSON object")
    work = scan_sessions(args.sessions_root, args.max_workers)
    compute = collect_compute_snapshot(args.run_cuda_smoke)
    assets = collect_existing_assets(args.quant_lab_root, args.premium_summary, args.stack_root)
    payload = build_payload(protocol, args.protocol, work, compute, assets, goal_snapshot(args))
    outputs = write_packet(payload, args.output_dir)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "quality": payload["quality"],
                "receipt_sha256": payload["receipt_sha256"],
                "session_file_count": work["session_file_count"],
                "completed_task_count": work["completed_task_count"],
                "pending_task_count": work["pending_task_count"],
                "additive_task_elapsed_label": work["additive_task_elapsed_label"],
                "calendar_union_elapsed_label": work["calendar_union_elapsed_label"],
                "per_model": work["per_model"],
                "outputs": outputs,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
