from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "config" / "noahs_proof_chain_v1.json"
ZERO_HASH = "0" * 64
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
REQUIRED_LINK_IDS = (
    "public_front_door",
    "publication_custody",
    "current_source_breadth",
    "baseline_custody_completeness",
    "champion_metric_custody",
    "current_row_seal",
    "preregistered_sample_gates",
    "reproducibility",
    "immutable_release_manifest",
    "independent_validation",
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def sorted_json_sha256(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def normalized_bytes(data: bytes, mode: str) -> bytes:
    if mode == "raw":
        return data
    if mode == "utf8_lf":
        return data.replace(b"\r\n", b"\n")
    raise ValueError(f"unsupported hash mode: {mode}")


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_PATTERN.fullmatch(value.lower()) is not None


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def get_field(payload: Any, field: str) -> Any:
    current = payload
    for part in field.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(field)
        current = current[part]
    return current


def make_blocker(
    code: str,
    message: str,
    *,
    path: str | None = None,
    rule_id: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {"code": code, "message": message}
    if path is not None:
        row["path"] = path
    if rule_id is not None:
        row["rule_id"] = rule_id
    return row


class ArtifactStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self._cache: dict[str, dict[str, Any]] = {}

    def resolve(self, relative_path: str) -> Path:
        normalized = str(relative_path).replace("\\", "/")
        pure = PurePosixPath(normalized)
        if (
            pure.is_absolute()
            or not pure.parts
            or ".." in pure.parts
            or ":" in pure.parts[0]
        ):
            raise ValueError(f"path is not repository-relative: {relative_path}")
        current = self.root
        for part in pure.parts:
            current = current / part
            if current.exists() and current.is_symlink():
                raise ValueError(f"symlink evidence path is not allowed: {relative_path}")
        try:
            current.resolve(strict=False).relative_to(self.root)
        except ValueError as exc:
            raise ValueError(f"path escapes repository root: {relative_path}") from exc
        return current

    def snapshot(self, relative_path: str) -> dict[str, Any]:
        key = str(relative_path).replace("\\", "/")
        if key in self._cache:
            return self._cache[key]
        try:
            path = self.resolve(key)
        except ValueError as exc:
            row = {
                "path": key,
                "exists": False,
                "path_error": str(exc),
                "data": None,
            }
            self._cache[key] = row
            return row
        if not path.is_file():
            row = {"path": key, "exists": False, "path_error": None, "data": None}
            self._cache[key] = row
            return row
        before = path.stat()
        data = path.read_bytes()
        after = path.stat()
        changed_during_read = (
            before.st_size != after.st_size
            or before.st_mtime_ns != after.st_mtime_ns
            or len(data) != after.st_size
        )
        row = {
            "path": key,
            "exists": True,
            "path_error": None,
            "data": data,
            "bytes": len(data),
            "modified_utc": datetime.fromtimestamp(
                after.st_mtime, tz=timezone.utc
            ).isoformat(),
            "changed_during_read": changed_during_read,
        }
        self._cache[key] = row
        return row

    def data(self, relative_path: str, mode: str = "raw") -> bytes:
        snapshot = self.snapshot(relative_path)
        if not snapshot["exists"] or snapshot["data"] is None:
            raise FileNotFoundError(relative_path)
        return normalized_bytes(snapshot["data"], mode)

    def sha256(self, relative_path: str, mode: str = "raw") -> str:
        return hashlib.sha256(self.data(relative_path, mode)).hexdigest()

    def byte_count(self, relative_path: str, mode: str = "raw") -> int:
        return len(self.data(relative_path, mode))

    def json(self, relative_path: str) -> dict[str, Any]:
        payload = json.loads(self.data(relative_path).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"expected JSON object: {relative_path}")
        return payload


def validate_config(config: dict[str, Any]) -> dict[str, Any]:
    links = config.get("links")
    link_ids = [
        row.get("id") for row in links if isinstance(row, dict)
    ] if isinstance(links, list) else []
    policies = config.get("policies") if isinstance(config.get("policies"), dict) else {}
    boundaries = (
        config.get("no_claim_boundaries")
        if isinstance(config.get("no_claim_boundaries"), dict)
        else {}
    )
    claim_flags = [
        key for key in boundaries if key.endswith("_claim_allowed")
    ]
    checks = {
        "schema_valid": config.get("schema") == "noahs_proof_chain_config.v1",
        "architecture_name_valid": config.get("architecture_name") == "NOAHS",
        "links_exact_and_ordered": tuple(link_ids) == REQUIRED_LINK_IDS,
        "link_ids_unique": len(link_ids) == len(set(link_ids)),
        "all_links_required": bool(links)
        and all(row.get("required") is True for row in links if isinstance(row, dict)),
        "all_links_have_boundaries": bool(links)
        and all(
            isinstance(row.get("claim_boundary"), str)
            and bool(row["claim_boundary"].strip())
            for row in links
            if isinstance(row, dict)
        ),
        "network_disabled": policies.get("allow_network_access") is False,
        "mutation_disabled": policies.get("allow_file_mutation") is False,
        "external_action_disabled": policies.get("allow_external_action") is False,
        "symlink_following_disabled": policies.get("allow_symlink_following") is False,
        "performance_inference_disabled": policies.get(
            "infer_performance_from_internal_receipts"
        )
        is False,
        "all_claim_flags_closed": bool(claim_flags)
        and all(boundaries.get(key) is False for key in claim_flags),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "link_ids": link_ids,
    }


def inspect_artifact(
    store: ArtifactStore,
    spec: dict[str, Any],
    *,
    observed_utc: datetime,
) -> dict[str, Any]:
    relative_path = str(spec["path"])
    snapshot = store.snapshot(relative_path)
    blockers: list[dict[str, Any]] = []
    row: dict[str, Any] = {
        "id": spec.get("id"),
        "path": relative_path,
        "exists": bool(snapshot.get("exists")),
        "required": spec.get("required", True),
        "blockers": blockers,
    }
    if snapshot.get("path_error"):
        blockers.append(
            make_blocker(
                "UNSAFE_EVIDENCE_PATH",
                str(snapshot["path_error"]),
                path=relative_path,
            )
        )
        return row
    if not snapshot.get("exists"):
        if spec.get("required", True):
            blockers.append(
                make_blocker(
                    "MISSING_ARTIFACT",
                    "Required evidence artifact is missing.",
                    path=relative_path,
                )
            )
        return row

    mode = str(spec.get("hash_mode", "raw"))
    row.update(
        {
            "bytes": snapshot["bytes"],
            "modified_utc": snapshot["modified_utc"],
            "hash_mode": mode,
            "sha256": store.sha256(relative_path, mode),
        }
    )
    if snapshot.get("changed_during_read"):
        blockers.append(
            make_blocker(
                "ARTIFACT_CHANGED_DURING_READ",
                "Artifact changed while the gate was reading it.",
                path=relative_path,
            )
        )
    minimum = int(spec.get("min_bytes", 0))
    if snapshot["bytes"] == 0 and minimum > 0:
        blockers.append(
            make_blocker(
                "ZERO_BYTE_ARTIFACT",
                "Required evidence artifact is zero bytes.",
                path=relative_path,
            )
        )
    elif snapshot["bytes"] < minimum:
        blockers.append(
            make_blocker(
                "ARTIFACT_TOO_SMALL",
                f"Artifact has {snapshot['bytes']} bytes; minimum is {minimum}.",
                path=relative_path,
            )
        )

    expected_sha = spec.get("expected_sha256")
    if expected_sha is not None and row["sha256"] != str(expected_sha).lower():
        blockers.append(
            make_blocker(
                "PINNED_HASH_MISMATCH",
                "Artifact does not match its pinned SHA-256.",
                path=relative_path,
            )
        )

    payload: dict[str, Any] | None = None
    if relative_path.lower().endswith(".json") and snapshot["bytes"] > 0:
        try:
            payload = store.json(relative_path)
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            blockers.append(
                make_blocker(
                    "INVALID_JSON_ARTIFACT",
                    f"Evidence JSON could not be parsed: {exc}",
                    path=relative_path,
                )
            )

    max_age_hours = spec.get("max_age_hours")
    if max_age_hours is not None:
        evidence_time: datetime | None = None
        timestamp_source = "file_mtime"
        timestamp_fields = spec.get("timestamp_fields", [])
        if timestamp_fields:
            timestamp_source = ""
            if payload is not None:
                for field in timestamp_fields:
                    try:
                        candidate = parse_utc(get_field(payload, str(field)))
                    except KeyError:
                        candidate = None
                    if candidate is not None:
                        evidence_time = candidate
                        timestamp_source = str(field)
                        break
        else:
            evidence_time = parse_utc(snapshot["modified_utc"])
        if evidence_time is None:
            blockers.append(
                make_blocker(
                    "MISSING_EVIDENCE_TIMESTAMP",
                    "Freshness is required but no valid evidence timestamp was found.",
                    path=relative_path,
                )
            )
        else:
            age_hours = (observed_utc - evidence_time).total_seconds() / 3600
            row["evidence_timestamp_utc"] = evidence_time.isoformat()
            row["timestamp_source"] = timestamp_source
            row["age_hours"] = round(age_hours, 6)
            row["max_age_hours"] = max_age_hours
            if age_hours < -0.25:
                blockers.append(
                    make_blocker(
                        "FUTURE_EVIDENCE_TIMESTAMP",
                        "Evidence timestamp is materially later than the gate clock.",
                        path=relative_path,
                    )
                )
            elif age_hours > float(max_age_hours):
                blockers.append(
                    make_blocker(
                        "STALE_ARTIFACT",
                        f"Artifact age is {age_hours:.2f} hours; maximum is {max_age_hours}.",
                        path=relative_path,
                    )
                )
    return row


def check_json_fields(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    path = str(rule["artifact"])
    blockers: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []
    try:
        payload = store.json(path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "JSON_RULE_SOURCE_INVALID",
                f"JSON rule source is unavailable: {exc}",
                path=path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "results": [], "blockers": blockers}

    mismatch_code = str(rule.get("mismatch_code", "JSON_FIELD_MISMATCH"))
    for requirement in rule.get("requirements", []):
        field = str(requirement["field"])
        operator = str(requirement["operator"])
        try:
            observed = get_field(payload, field)
        except KeyError:
            observed = None
            passed = False
        else:
            expected = requirement.get("expected")
            if operator == "equals":
                passed = observed == expected
            elif operator == "is_true":
                passed = observed is True
            elif operator == "is_false":
                passed = observed is False
            elif operator == "nonempty":
                passed = observed not in (None, "", [], {})
            elif operator == "valid_sha256":
                passed = is_sha256(observed)
            else:
                raise ValueError(f"unsupported JSON field operator: {operator}")
        results.append({"field": field, "operator": operator, "passed": passed})
        if not passed:
            blockers.append(
                make_blocker(
                    mismatch_code,
                    f"Required JSON field condition failed: {field} {operator}.",
                    path=path,
                    rule_id=rule_id,
                )
            )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "results": results,
        "blockers": blockers,
    }


def check_manifest_entries(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    manifest_path = str(rule["artifact"])
    blockers: list[dict[str, Any]] = []
    mismatch_rows: list[dict[str, Any]] = []
    try:
        manifest = store.json(manifest_path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "MANIFEST_INVALID",
                f"Manifest could not be read: {exc}",
                path=manifest_path,
                rule_id=rule_id,
            )
        )
        return {
            "id": rule_id,
            "type": rule["type"],
            "passed": False,
            "entry_count": 0,
            "matched_count": 0,
            "mismatches": mismatch_rows,
            "blockers": blockers,
        }

    entries: list[dict[str, Any]] = []
    for field in rule.get("array_fields", []):
        try:
            values = get_field(manifest, str(field))
        except KeyError:
            values = None
        if not isinstance(values, list):
            blockers.append(
                make_blocker(
                    "MANIFEST_ARRAY_MISSING",
                    f"Manifest array is missing or invalid: {field}.",
                    path=manifest_path,
                    rule_id=rule_id,
                )
            )
            continue
        entries.extend(row for row in values if isinstance(row, dict))

    required_field = rule.get("required_field")
    if required_field is not None:
        required_value = rule.get("required_value")
        entries = [
            row for row in entries if row.get(str(required_field)) == required_value
        ]
    minimum = int(rule.get("min_entries", 1))
    if len(entries) < minimum:
        blockers.append(
            make_blocker(
                "MANIFEST_ENTRY_COUNT_LOW",
                f"Manifest exposes {len(entries)} entries; minimum is {minimum}.",
                path=manifest_path,
                rule_id=rule_id,
            )
        )

    path_field = str(rule["path_field"])
    sha_field = str(rule["sha256_field"])
    bytes_field = rule.get("bytes_field")
    mode_field = rule.get("hash_mode_field")
    drift_code = str(rule.get("drift_code", "MANIFEST_HASH_MISMATCH"))
    matched = 0
    for entry in entries:
        relative_path = entry.get(path_field)
        expected_sha = entry.get(sha_field)
        mode = str(entry.get(str(mode_field), "raw")) if mode_field else "raw"
        reason: str | None = None
        current_sha: str | None = None
        current_bytes: int | None = None
        if not isinstance(relative_path, str) or not relative_path:
            reason = "missing_path"
        elif not is_sha256(expected_sha):
            reason = "invalid_declared_sha256"
        else:
            snapshot = store.snapshot(relative_path)
            if not snapshot.get("exists"):
                reason = "missing_file"
            elif snapshot.get("bytes") == 0:
                reason = "zero_byte_file"
            else:
                try:
                    current_sha = store.sha256(relative_path, mode)
                    current_bytes = store.byte_count(relative_path, mode)
                except (UnicodeError, ValueError) as exc:
                    reason = f"hash_error:{exc}"
                if reason is None and current_sha != str(expected_sha).lower():
                    reason = "sha256_mismatch"
                if (
                    reason is None
                    and bytes_field is not None
                    and isinstance(entry.get(str(bytes_field)), int)
                    and current_bytes != entry[str(bytes_field)]
                ):
                    reason = "byte_count_mismatch"
        if reason is None:
            matched += 1
            continue
        mismatch = {
            "path": relative_path,
            "reason": reason,
            "expected_sha256": expected_sha,
            "current_sha256": current_sha,
        }
        mismatch_rows.append(mismatch)
        blockers.append(
            make_blocker(
                drift_code,
                f"Manifested artifact failed custody check: {reason}.",
                path=str(relative_path or manifest_path),
                rule_id=rule_id,
            )
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "entry_count": len(entries),
        "matched_count": matched,
        "mismatches": mismatch_rows,
        "blockers": blockers,
    }


def check_source_registry(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    path = str(rule["artifact"])
    blockers: list[dict[str, Any]] = []
    try:
        payload = store.json(path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "SOURCE_REGISTRY_INVALID",
                f"Source registry is unavailable: {exc}",
                path=path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}
    rows = payload.get("rows")
    if not isinstance(rows, list):
        rows = []
        blockers.append(
            make_blocker(
                "SOURCE_REGISTRY_INVALID",
                "Source registry rows are missing.",
                path=path,
                rule_id=rule_id,
            )
        )

    sources: set[str] = set()
    enabled_count = 0
    measured_count = 0
    measured_rows = 0
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            blockers.append(
                make_blocker(
                    "SOURCE_REGISTRY_INCONSISTENT",
                    f"Source row {index} is not an object.",
                    path=path,
                    rule_id=rule_id,
                )
            )
            continue
        source = str(row.get("source") or "").strip()
        if not source or source in sources:
            blockers.append(
                make_blocker(
                    "SOURCE_REGISTRY_INCONSISTENT",
                    f"Source row {index} has a missing or duplicate source id.",
                    path=path,
                    rule_id=rule_id,
                )
            )
        sources.add(source)
        enabled = row.get("enabled") is True
        measured = row.get("measured") is True
        status_measured = row.get("status") == "MEASURED"
        row_count = row.get("rows")
        if enabled:
            enabled_count += 1
        if measured:
            measured_count += 1
            if isinstance(row_count, int) and not isinstance(row_count, bool):
                measured_rows += row_count
        if measured != status_measured:
            blockers.append(
                make_blocker(
                    "SOURCE_REGISTRY_INCONSISTENT",
                    f"Measured flag and status disagree for {source or index}.",
                    path=path,
                    rule_id=rule_id,
                )
            )
        if measured and (
            row.get("probe_ok") is not True
            or not isinstance(row_count, int)
            or isinstance(row_count, bool)
            or row_count <= 0
        ):
            blockers.append(
                make_blocker(
                    "SOURCE_REGISTRY_INCONSISTENT",
                    f"Measured source lacks a successful nonzero probe: {source or index}.",
                    path=path,
                    rule_id=rule_id,
                )
            )

    coverage = measured_count / enabled_count if enabled_count else 0.0
    thresholds = (
        ("enabled", enabled_count, int(rule.get("min_enabled_sources", 1))),
        ("measured", measured_count, int(rule.get("min_measured_sources", 1))),
        ("measured rows", measured_rows, int(rule.get("min_measured_rows", 1))),
    )
    for label, observed, minimum in thresholds:
        if observed < minimum:
            blockers.append(
                make_blocker(
                    "SOURCE_BREADTH_BELOW_MINIMUM",
                    f"Current {label} count is {observed}; minimum is {minimum}.",
                    path=path,
                    rule_id=rule_id,
                )
            )
    minimum_coverage = float(rule.get("min_measured_coverage", 0.0))
    if coverage < minimum_coverage:
        blockers.append(
            make_blocker(
                "SOURCE_BREADTH_BELOW_MINIMUM",
                f"Measured coverage is {coverage:.4f}; minimum is {minimum_coverage:.4f}.",
                path=path,
                rule_id=rule_id,
            )
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "enabled_source_count": enabled_count,
        "measured_source_count": measured_count,
        "measured_row_count": measured_rows,
        "measured_coverage": round(coverage, 6),
        "blockers": blockers,
    }


def check_measurement_snapshot_seals(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    path = str(rule["artifact"])
    blockers: list[dict[str, Any]] = []
    try:
        payload = store.json(path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "CURRENT_ROW_ARTIFACT_INVALID",
                f"Measurement artifact is unavailable: {exc}",
                path=path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}
    provider_rows = payload.get("provider_rows")
    summary = payload.get("summary")
    if not isinstance(provider_rows, list) or not isinstance(summary, dict):
        blockers.append(
            make_blocker(
                "CURRENT_ROW_ARTIFACT_INVALID",
                "Measurement provider rows or summary are missing.",
                path=path,
                rule_id=rule_id,
            )
        )
        provider_rows = []
        summary = {}

    measured = [
        row
        for row in provider_rows
        if isinstance(row, dict)
        and row.get("measured") is True
        and row.get("status") == "MEASURED"
    ]
    measured_rows = sum(
        row["rows"]
        for row in measured
        if isinstance(row.get("rows"), int) and not isinstance(row.get("rows"), bool)
    )
    summary_count = summary.get("measured_sources")
    summary_rows = summary.get("total_measured_rows")
    if summary_count != len(measured) or summary_rows != measured_rows:
        blockers.append(
            make_blocker(
                "CURRENT_ROW_SUMMARY_INCONSISTENT",
                "Summary measured-source or row totals disagree with current provider rows.",
                path=path,
                rule_id=rule_id,
            )
        )

    verified = 0
    for row in measured:
        source = str(row.get("source") or "")
        snapshot_path = row.get("snapshot_json")
        declared_sha = row.get("snapshot_sha256")
        reason: str | None = None
        if not isinstance(snapshot_path, str) or not snapshot_path:
            reason = "missing_snapshot_path"
        elif not is_sha256(declared_sha):
            reason = "invalid_snapshot_sha256"
        else:
            try:
                snapshot = store.json(snapshot_path)
            except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError):
                reason = "snapshot_unreadable"
            else:
                embedded_sha = snapshot.get("sha256")
                unsigned = {
                    key: value for key, value in snapshot.items() if key != "sha256"
                }
                if embedded_sha != declared_sha:
                    reason = "registry_snapshot_hash_disagreement"
                elif canonical_sha256(unsigned) != declared_sha:
                    reason = "snapshot_embedded_hash_invalid"
                elif snapshot.get("source") != source:
                    reason = "snapshot_source_disagreement"
                elif snapshot.get("row_count") != row.get("rows"):
                    reason = "snapshot_row_count_disagreement"
        if reason is None:
            verified += 1
        else:
            blockers.append(
                make_blocker(
                    "CURRENT_ROW_SEAL_INVALID",
                    f"Measured source {source or '<unknown>'} failed snapshot seal: {reason}.",
                    path=str(snapshot_path or path),
                    rule_id=rule_id,
                )
            )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "provider_row_count": len(provider_rows),
        "measured_source_count": len(measured),
        "measured_row_count": measured_rows,
        "verified_snapshot_count": verified,
        "blockers": blockers,
    }


def check_baseline_completeness(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    coverage_path = str(rule["coverage_artifact"])
    replay_path = str(rule["replay_artifact"])
    blockers: list[dict[str, Any]] = []
    try:
        payload = store.json(coverage_path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "BASELINE_COVERAGE_INVALID",
                f"Baseline coverage artifact is unavailable: {exc}",
                path=coverage_path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}

    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    baseline_rows = payload.get("baseline_rows")
    package_status = payload.get("package_status")
    if not isinstance(baseline_rows, list):
        baseline_rows = []
    declared_sha = summary.get("baseline_gauntlet_sha256")
    unhashed_summary = dict(summary)
    unhashed_summary.pop("baseline_gauntlet_sha256", None)
    computed_sha = canonical_sha256(
        {
            "summary": unhashed_summary,
            "baseline_rows": baseline_rows,
            "package_status": package_status,
        }
    )
    if declared_sha != computed_sha:
        blockers.append(
            make_blocker(
                "BASELINE_EMBEDDED_HASH_INVALID",
                "Baseline gauntlet embedded SHA-256 does not verify.",
                path=coverage_path,
                rule_id=rule_id,
            )
        )

    requested = summary.get("requested_baselines")
    executed = summary.get("executed_in_locked_replay")
    implementation_needed = summary.get("implementation_needed")
    registered_not_executed = summary.get("registered_not_adapter_executed")
    proxy_only = summary.get("replay_proxy_ready_from_metric_audit")
    complete = (
        isinstance(requested, int)
        and requested == len(baseline_rows)
        and executed == requested
        and implementation_needed == 0
        and registered_not_executed == 0
        and proxy_only == 0
    )
    if not complete:
        blockers.append(
            make_blocker(
                "BASELINE_INCOMPLETE",
                "The declared named-baseline set is not fully executed in the locked replay.",
                path=coverage_path,
                rule_id=rule_id,
            )
        )
    replay_snapshot = store.snapshot(replay_path)
    if not replay_snapshot.get("exists") or replay_snapshot.get("bytes", 0) == 0:
        blockers.append(
            make_blocker(
                "BASELINE_REPLAY_BODY_UNAVAILABLE",
                "The locked source baseline replay body is missing or zero bytes.",
                path=replay_path,
                rule_id=rule_id,
            )
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "requested_baseline_count": requested,
        "executed_baseline_count": executed,
        "implementation_needed_count": implementation_needed,
        "registered_not_executed_count": registered_not_executed,
        "proxy_only_count": proxy_only,
        "embedded_hash_valid": declared_sha == computed_sha,
        "blockers": blockers,
    }


def check_champion_custody(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    holdout_path = str(rule["holdout_artifact"])
    audit_path = str(rule["audit_artifact"])
    blockers: list[dict[str, Any]] = []
    try:
        holdout = store.json(holdout_path)
        audit = store.json(audit_path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "CHAMPION_CUSTODY_INVALID",
                f"Champion custody artifact is unavailable: {exc}",
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}

    summary = holdout.get("summary") if isinstance(holdout.get("summary"), dict) else {}
    results = holdout.get("holdout_results")
    if not isinstance(results, list):
        results = []
    unhashed_summary = dict(summary)
    declared_holdout_sha = unhashed_summary.pop("holdout_chain_sha256", None)
    result_seals = []
    for row in results:
        if not isinstance(row, dict):
            continue
        result_seals.append(
            {
                "rank": row.get("rank"),
                "source_path": row.get("source_path"),
                "source_sha256": row.get("source_sha256"),
                "delta_vs_kalman": row.get("delta_vs_kalman"),
                "holdout_sha256": row.get("holdout_sha256"),
            }
        )
    computed_holdout_sha = sorted_json_sha256(
        {"summary": unhashed_summary, "results": result_seals}
    )
    if declared_holdout_sha != computed_holdout_sha:
        blockers.append(
            make_blocker(
                "CHAMPION_HOLDOUT_HASH_INVALID",
                "Champion holdout chain SHA-256 does not verify.",
                path=holdout_path,
                rule_id=rule_id,
            )
        )
    if (
        not results
        or summary.get("holdout_count") != len(results)
        or not str(summary.get("named_baseline") or "").strip()
    ):
        blockers.append(
            make_blocker(
                "CHAMPION_CUSTODY_INCONSISTENT",
                "Champion holdout count or named baseline is missing or inconsistent.",
                path=holdout_path,
                rule_id=rule_id,
            )
        )
    for row in results:
        if not isinstance(row, dict) or not all(
            is_sha256(row.get(field))
            for field in ("source_sha256", "holdout_sha256")
        ):
            blockers.append(
                make_blocker(
                    "CHAMPION_CUSTODY_INCONSISTENT",
                    "A champion holdout row lacks a valid source or holdout SHA-256.",
                    path=holdout_path,
                    rule_id=rule_id,
                )
            )
            break

    claim_gates = (
        holdout.get("claim_gates")
        if isinstance(holdout.get("claim_gates"), dict)
        else {}
    )
    prohibited_true = [
        key
        for key, value in claim_gates.items()
        if key.endswith("_allowed") and value is not False
    ]
    if prohibited_true:
        blockers.append(
            make_blocker(
                "CHAMPION_CLAIM_BOUNDARY_OPEN",
                "One or more high-risk champion claim gates are not explicitly false.",
                path=holdout_path,
                rule_id=rule_id,
            )
        )

    audit_summary = (
        audit.get("summary") if isinstance(audit.get("summary"), dict) else {}
    )
    audit_rows = audit.get("accepted_metric_rows")
    audit_controls = audit.get("claim_controls")
    declared_audit_sha = audit.get("audit_sha256")
    computed_audit_sha = canonical_sha256(
        {
            "summary": audit_summary,
            "accepted_metric_rows": audit_rows,
            "claim_controls": audit_controls,
        }
    )
    if declared_audit_sha != computed_audit_sha:
        blockers.append(
            make_blocker(
                "CHAMPION_AUDIT_HASH_INVALID",
                "Accepted-metric audit SHA-256 does not verify.",
                path=audit_path,
                rule_id=rule_id,
            )
        )
    if (
        audit_summary.get("champion_family") != summary.get("candidate")
        or audit_summary.get("named_baseline") != summary.get("named_baseline")
        or audit_summary.get("field_validation_claim_allowed") is not False
        or audit_summary.get("real_dollar_savings_claim_allowed") is not False
    ):
        blockers.append(
            make_blocker(
                "CHAMPION_AUDIT_INCONSISTENT",
                "Accepted-metric audit disagrees with the holdout identity or claim boundary.",
                path=audit_path,
                rule_id=rule_id,
            )
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "holdout_count": len(results),
        "named_baseline_present": bool(summary.get("named_baseline")),
        "holdout_chain_valid": declared_holdout_sha == computed_holdout_sha,
        "metric_audit_valid": declared_audit_sha == computed_audit_sha,
        "claim_gates_closed": not prohibited_true,
        "blockers": blockers,
    }


def verify_jsonl_chain(
    store: ArtifactStore,
    path: str,
    *,
    expected_protocol_sha256: str | None = None,
    expected_protocol_commit: str | None = None,
    require_protocol_fields: bool = False,
) -> dict[str, Any]:
    blockers: list[dict[str, Any]] = []
    previous = ZERO_HASH
    count = 0
    try:
        text = store.data(path).decode("utf-8")
    except (FileNotFoundError, UnicodeError) as exc:
        blockers.append(
            make_blocker(
                "CHAIN_UNREADABLE",
                f"Append-only chain could not be read: {exc}",
                path=path,
            )
        )
        return {
            "path": path,
            "record_count": 0,
            "terminal_chain_sha256": previous,
            "passed": False,
            "blockers": blockers,
        }
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            blockers.append(
                make_blocker(
                    "CHAIN_JSON_INVALID",
                    f"Chain record {line_number} is invalid JSON.",
                    path=path,
                )
            )
            break
        if not isinstance(record, dict):
            blockers.append(
                make_blocker(
                    "CHAIN_RECORD_INVALID",
                    f"Chain record {line_number} is not an object.",
                    path=path,
                )
            )
            break
        observed = record.get("record_sha256")
        unsigned = {
            key: value for key, value in record.items() if key != "record_sha256"
        }
        if record.get("prior_record_chain_sha256") != previous:
            blockers.append(
                make_blocker(
                    "CHAIN_PRIOR_HASH_MISMATCH",
                    f"Chain record {line_number} has a broken prior hash.",
                    path=path,
                )
            )
            break
        if observed != canonical_sha256(unsigned):
            blockers.append(
                make_blocker(
                    "CHAIN_RECORD_HASH_MISMATCH",
                    f"Chain record {line_number} SHA-256 does not verify.",
                    path=path,
                )
            )
            break
        observed_protocol_sha = record.get("protocol_sha256")
        if expected_protocol_sha256 is not None and (
            (require_protocol_fields and observed_protocol_sha != expected_protocol_sha256)
            or (
                observed_protocol_sha is not None
                and observed_protocol_sha != expected_protocol_sha256
            )
        ):
            blockers.append(
                make_blocker(
                    "CHAIN_PROTOCOL_MISMATCH",
                    f"Chain record {line_number} references a different protocol hash.",
                    path=path,
                )
            )
            break
        observed_protocol_commit = record.get("protocol_commit")
        if expected_protocol_commit is not None and (
            (
                require_protocol_fields
                and observed_protocol_commit != expected_protocol_commit
            )
            or (
                observed_protocol_commit is not None
                and observed_protocol_commit != expected_protocol_commit
            )
        ):
            blockers.append(
                make_blocker(
                    "CHAIN_PROTOCOL_MISMATCH",
                    f"Chain record {line_number} references a different protocol commit.",
                    path=path,
                )
            )
            break
        count += 1
        previous = str(observed)
    if count == 0 and not blockers:
        blockers.append(
            make_blocker(
                "CHAIN_EMPTY",
                "Append-only chain has no records.",
                path=path,
            )
        )
    return {
        "path": path,
        "record_count": count,
        "terminal_chain_sha256": previous,
        "passed": not blockers,
        "blockers": blockers,
    }


def check_preregistered_lanes(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    blockers: list[dict[str, Any]] = []
    lane_rows: list[dict[str, Any]] = []
    for lane in rule.get("lanes", []):
        lane_id = str(lane["id"])
        status_path = str(lane["status_path"])
        protocol_path = str(lane["protocol_path"])
        expected_sha = str(lane["protocol_sha256"])
        expected_commit = str(lane["protocol_commit"])
        lane_blockers: list[dict[str, Any]] = []
        try:
            status = store.json(status_path)
        except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            lane_blockers.append(
                make_blocker(
                    "PREREGISTERED_STATUS_INVALID",
                    f"Lane status is unavailable: {exc}",
                    path=status_path,
                    rule_id=rule_id,
                )
            )
            status = {}
        try:
            current_protocol_sha = store.sha256(protocol_path, "utf8_lf")
        except (FileNotFoundError, ValueError):
            current_protocol_sha = None
        if current_protocol_sha != expected_sha:
            lane_blockers.append(
                make_blocker(
                    "PREREGISTERED_PROTOCOL_DRIFT",
                    f"Frozen protocol hash changed for lane {lane_id}.",
                    path=protocol_path,
                    rule_id=rule_id,
                )
            )
        if (
            status.get("protocol_sha256") != expected_sha
            or status.get("protocol_commit") != expected_commit
        ):
            lane_blockers.append(
                make_blocker(
                    "PREREGISTERED_STATUS_PROTOCOL_MISMATCH",
                    f"Status does not reference the frozen protocol for lane {lane_id}.",
                    path=status_path,
                    rule_id=rule_id,
                )
            )
        gate_name = str(lane["required_sample_gate"])
        sample_gates = (
            status.get("sample_gates")
            if isinstance(status.get("sample_gates"), dict)
            else {}
        )
        if sample_gates.get(gate_name) is not True:
            lane_blockers.append(
                make_blocker(
                    "SAMPLE_GATE_CLOSED",
                    f"Lane {lane_id} has not cleared the preregistered {gate_name} sample gate.",
                    path=status_path,
                    rule_id=rule_id,
                )
            )

        chain_rows: list[dict[str, Any]] = []
        for chain in lane.get("chains", []):
            chain_row = verify_jsonl_chain(
                store,
                str(chain["path"]),
                expected_protocol_sha256=expected_sha,
                expected_protocol_commit=expected_commit,
                require_protocol_fields=chain.get("require_protocol_fields") is True,
            )
            chain_rows.append(chain_row)
            lane_blockers.extend(chain_row["blockers"])
            count_field = chain.get("status_count_field")
            if count_field is not None and status.get(str(count_field)) != chain_row["record_count"]:
                lane_blockers.append(
                    make_blocker(
                        "CHAIN_STATUS_COUNT_MISMATCH",
                        f"Lane {lane_id} status count disagrees with chain {chain['id']}.",
                        path=str(chain["path"]),
                        rule_id=rule_id,
                    )
                )
            terminal_field = chain.get("status_terminal_field")
            if (
                terminal_field is not None
                and status.get(str(terminal_field))
                != chain_row["terminal_chain_sha256"]
            ):
                lane_blockers.append(
                    make_blocker(
                        "CHAIN_STATUS_TERMINAL_MISMATCH",
                        f"Lane {lane_id} status terminal hash disagrees with chain {chain['id']}.",
                        path=str(chain["path"]),
                        rule_id=rule_id,
                    )
                )

        for check in lane.get("panel_multiplier_checks", []):
            panels = status.get(str(check["panel_count_field"]))
            expanded = status.get(str(check["expanded_count_field"]))
            multiplier = int(check["multiplier"])
            if not isinstance(panels, int) or expanded != panels * multiplier:
                lane_blockers.append(
                    make_blocker(
                        "PANEL_COUNT_INCONSISTENT",
                        f"Lane {lane_id} expanded authority count is inconsistent.",
                        path=status_path,
                        rule_id=rule_id,
                    )
                )
        blockers.extend(lane_blockers)
        lane_rows.append(
            {
                "id": lane_id,
                "passed": not lane_blockers,
                "required_sample_gate": gate_name,
                "sample_gate_ready": sample_gates.get(gate_name) is True,
                "chains": [
                    {
                        key: value
                        for key, value in row.items()
                        if key != "blockers"
                    }
                    for row in chain_rows
                ],
                "blockers": lane_blockers,
            }
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "lanes": lane_rows,
        "blockers": blockers,
    }


def check_self_hash(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    path = str(rule["artifact"])
    hash_field = str(rule["hash_field"])
    blockers: list[dict[str, Any]] = []
    try:
        payload = store.json(path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "SELF_HASH_SOURCE_INVALID",
                f"Self-hashed artifact is unavailable: {exc}",
                path=path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}
    declared = payload.get(hash_field)
    unhashed = {key: value for key, value in payload.items() if key != hash_field}
    computed = canonical_sha256(unhashed)
    if declared != computed:
        blockers.append(
            make_blocker(
                "SELF_HASH_INVALID",
                f"Declared {hash_field} does not verify.",
                path=path,
                rule_id=rule_id,
            )
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "declared_sha256": declared,
        "computed_sha256": computed,
        "blockers": blockers,
    }


def git_state(root: Path) -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        ).stdout.strip()
        status_lines = subprocess.run(
            ["git", "status", "--porcelain=v1"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.splitlines()
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "head": None,
            "branch": None,
            "dirty_entry_count": None,
            "error": str(exc),
        }
    return {
        "available": True,
        "head": head,
        "branch": branch,
        "dirty_entry_count": len(status_lines),
        "error": None,
    }


def check_reproducibility_current(
    store: ArtifactStore,
    rule: dict[str, Any],
    *,
    root: Path,
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    path = str(rule["artifact"])
    blockers: list[dict[str, Any]] = []
    try:
        payload = store.json(path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "REPRODUCIBILITY_CAPSULE_INVALID",
                f"Reproducibility capsule is unavailable: {exc}",
                path=path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}
    state = git_state(root)
    capsule_git = payload.get("git") if isinstance(payload.get("git"), dict) else {}
    if (
        not state["available"]
        or capsule_git.get("commit") != state["head"]
        or capsule_git.get("branch") != state["branch"]
    ):
        blockers.append(
            make_blocker(
                "REPRODUCIBILITY_NOT_CURRENT",
                "Capsule branch or commit does not match the current repository state.",
                path=path,
                rule_id=rule_id,
            )
        )
    for field in rule.get("required_true_fields", []):
        try:
            value = get_field(payload, str(field))
        except KeyError:
            value = None
        if value is not True:
            blockers.append(
                make_blocker(
                    "REPRODUCIBILITY_GATE_OPEN",
                    f"Required reproducibility field is not true: {field}.",
                    path=path,
                    rule_id=rule_id,
                )
            )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "current_git": state,
        "capsule_git": {
            "branch": capsule_git.get("branch"),
            "commit": capsule_git.get("commit"),
        },
        "blockers": blockers,
    }


def check_git_clean(root: Path, rule: dict[str, Any]) -> dict[str, Any]:
    rule_id = str(rule["id"])
    state = git_state(root)
    blockers: list[dict[str, Any]] = []
    if not state["available"]:
        blockers.append(
            make_blocker(
                "GIT_STATE_UNAVAILABLE",
                "Repository state could not be read.",
                rule_id=rule_id,
            )
        )
    elif state["dirty_entry_count"] != 0:
        blockers.append(
            make_blocker(
                "GIT_DIRTY",
                f"Immutable release requires a clean worktree; {state['dirty_entry_count']} entries are dirty.",
                rule_id=rule_id,
            )
        )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "git": state,
        "blockers": blockers,
    }


def check_independent_validation(
    store: ArtifactStore, rule: dict[str, Any]
) -> dict[str, Any]:
    rule_id = str(rule["id"])
    path = str(rule["artifact"])
    blockers: list[dict[str, Any]] = []
    completed_fields: list[str] = []
    try:
        payload = store.json(path)
    except (FileNotFoundError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        blockers.append(
            make_blocker(
                "INDEPENDENT_PACKET_INVALID",
                f"Independent-validation packet is unavailable: {exc}",
                path=path,
                rule_id=rule_id,
            )
        )
        return {"id": rule_id, "type": rule["type"], "passed": False, "blockers": blockers}
    for field in rule.get("required_true_fields", []):
        try:
            value = get_field(payload, str(field))
        except KeyError:
            value = None
        if value is True:
            completed_fields.append(str(field))
        else:
            blockers.append(
                make_blocker(
                    "INDEPENDENT_VALIDATION_MISSING",
                    f"Required independent-validation field is not true: {field}.",
                    path=path,
                    rule_id=rule_id,
                )
            )
    return {
        "id": rule_id,
        "type": rule["type"],
        "passed": not blockers,
        "completed_fields": completed_fields,
        "required_field_count": len(rule.get("required_true_fields", [])),
        "blockers": blockers,
    }


def evaluate_rule(
    store: ArtifactStore,
    rule: dict[str, Any],
    *,
    root: Path,
) -> dict[str, Any]:
    rule_type = str(rule["type"])
    if rule_type == "json_fields":
        return check_json_fields(store, rule)
    if rule_type == "manifest_entries":
        return check_manifest_entries(store, rule)
    if rule_type == "source_registry":
        return check_source_registry(store, rule)
    if rule_type == "measurement_snapshot_seals":
        return check_measurement_snapshot_seals(store, rule)
    if rule_type == "baseline_completeness":
        return check_baseline_completeness(store, rule)
    if rule_type == "champion_custody":
        return check_champion_custody(store, rule)
    if rule_type == "preregistered_lanes":
        return check_preregistered_lanes(store, rule)
    if rule_type == "self_hash":
        return check_self_hash(store, rule)
    if rule_type == "reproducibility_current":
        return check_reproducibility_current(store, rule, root=root)
    if rule_type == "git_clean":
        return check_git_clean(root, rule)
    if rule_type == "independent_validation":
        return check_independent_validation(store, rule)
    raise ValueError(f"unsupported NOAHS rule type: {rule_type}")


def build_gate(
    *,
    root: Path = ROOT,
    config_path: Path | None = None,
    observed_utc: datetime | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    config_path = (config_path or root / "config" / "noahs_proof_chain_v1.json").resolve()
    try:
        config_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("NOAHS config must remain inside the repository root") from exc
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("NOAHS config must be a JSON object")
    validation = validate_config(config)
    if not validation["passed"]:
        failed = [key for key, value in validation["checks"].items() if not value]
        raise ValueError(f"NOAHS config failed closed: {failed}")

    observed = (observed_utc or now_utc()).astimezone(timezone.utc)
    store = ArtifactStore(root)
    link_rows: list[dict[str, Any]] = []
    all_blockers: list[dict[str, Any]] = []
    for link in config["links"]:
        artifacts = [
            inspect_artifact(store, spec, observed_utc=observed)
            for spec in link.get("artifacts", [])
        ]
        checks = [
            evaluate_rule(store, rule, root=root)
            for rule in link.get("rules", [])
        ]
        link_blockers: list[dict[str, Any]] = []
        for artifact in artifacts:
            link_blockers.extend(artifact["blockers"])
        for check in checks:
            link_blockers.extend(check["blockers"])
        for blocker in link_blockers:
            blocker["link_id"] = link["id"]
        all_blockers.extend(link_blockers)
        link_rows.append(
            {
                "id": link["id"],
                "label": link["label"],
                "required": link["required"],
                "state": "PASS" if not link_blockers else "BLOCKED",
                "claim_boundary": link["claim_boundary"],
                "artifacts": [
                    {
                        key: value
                        for key, value in row.items()
                        if key != "blockers"
                    }
                    for row in artifacts
                ],
                "checks": [
                    {
                        key: value
                        for key, value in row.items()
                        if key != "blockers"
                    }
                    for row in checks
                ],
                "blockers": link_blockers,
            }
        )

    passed_count = sum(1 for row in link_rows if row["state"] == "PASS")
    blocked_count = len(link_rows) - passed_count
    config_relative = config_path.relative_to(root).as_posix()
    config_sha = hashlib.sha256(config_path.read_bytes()).hexdigest()
    payload: dict[str, Any] = {
        "schema": "noahs_proof_chain_gate.v1",
        "architecture_name": "NOAHS",
        "generated_utc": observed.isoformat(),
        "overall_state": "PASS" if blocked_count == 0 else "BLOCKED",
        "reviewer_release_ready": blocked_count == 0,
        "summary": {
            "link_count": len(link_rows),
            "passed_link_count": passed_count,
            "blocked_link_count": blocked_count,
            "blocker_count": len(all_blockers),
        },
        "config": {
            "path": config_relative,
            "bytes": config_path.stat().st_size,
            "sha256": config_sha,
            "validation": validation,
        },
        "controls": {
            "network_access_performed": False,
            "files_written": False,
            "external_action_performed": False,
            "performance_inference_performed": False,
            "symlinks_followed": False,
        },
        "no_claim_boundaries": deepcopy(config["no_claim_boundaries"]),
        "links": link_rows,
        "blockers": all_blockers,
    }
    payload["gate_sha256"] = canonical_sha256(payload)
    return payload


def render_summary(payload: dict[str, Any]) -> str:
    lines = [
        f"NOAHS {payload['overall_state']}",
        (
            f"links={payload['summary']['link_count']} "
            f"passed={payload['summary']['passed_link_count']} "
            f"blocked={payload['summary']['blocked_link_count']} "
            f"blockers={payload['summary']['blocker_count']}"
        ),
    ]
    for link in payload["links"]:
        lines.append(
            f"{link['state']}: {link['id']} ({len(link['blockers'])} blockers)"
        )
        for blocker in link["blockers"]:
            path = f" [{blocker['path']}]" if blocker.get("path") else ""
            lines.append(f"  - {blocker['code']}{path}: {blocker['message']}")
    lines.append(f"gate_sha256={payload['gate_sha256']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the read-only, fail-closed NOAHS proof-chain gate."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Repository root. Defaults to the current LumenCore stack root.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Repository-local NOAHS config path.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "summary"),
        default="json",
        help="Select machine-readable JSON or a concise blocker summary.",
    )
    parser.add_argument(
        "--allow-blocked",
        action="store_true",
        help="Return zero for read-only diagnostics even when the gate is blocked.",
    )
    args = parser.parse_args()

    root = args.root.resolve()
    config_path = args.config
    if config_path is not None and not config_path.is_absolute():
        config_path = root / config_path
    payload = build_gate(root=root, config_path=config_path)
    if args.format == "summary":
        print(render_summary(payload))
    else:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    if payload["overall_state"] == "PASS" or args.allow_blocked:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
