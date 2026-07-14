from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
LEXICON = ROOT / "config" / "quant_hub_lexicon_v1.json"
OUT_JSON = ROOT / "out" / "ops" / "quant_hub_reviewer_context_latest.json"
DASHBOARD_JSON = ROOT / "dashboard" / "data" / "quant_hub_reviewer_context.json"
OUT_MD = ROOT / "docs" / "QUANT_HUB_REVIEWER_CONTEXT_2026-07-13.md"

SOURCE_PATHS = {
    "prior_proof_vault": ROOT / "out" / "ops" / "external_proof_vault_manifest_latest.json",
    "estate_index": ROOT / "out" / "ops" / "lumencore_estate_master_index_latest.json",
    "live_source_measurement": ROOT / "out" / "ops" / "live_source_measurement_maximizer_latest.json",
    "locked_replay": ROOT / "out" / "ops" / "locked_source_baseline_replay_sweep_latest.json",
    "reviewer_gate": ROOT / "out" / "ops" / "funding_sprint_reviewer_gate_latest.json",
    "faa_sdr_10k": ROOT / "out" / "ops" / "faa_sdr_10k_benchmark_latest.json",
    "eia_prospective_router": ROOT
    / "out"
    / "eia_grid_prospective_hybrid_router"
    / "prospective_status_latest.json",
    "eia_residual_benchmark": ROOT
    / "out"
    / "eia_grid_residual_moe"
    / "eia_grid_residual_moe_benchmark_latest.json",
    "eia_residual_protocol": ROOT / "config" / "eia_grid_residual_moe_protocol_v1.json",
    "mda_feasibility_v1": ROOT
    / "out"
    / "mda_control_mapping_feasibility"
    / "mda_control_mapping_feasibility_latest.json",
    "mda_open_set_v2": ROOT
    / "out"
    / "mda_control_mapping_open_set_v2"
    / "mda_control_mapping_open_set_latest.json",
    "local_icloud_evidence_intake": ROOT
    / "out"
    / "ops"
    / "local_icloud_evidence_intake_latest.json",
    "local_system_health_history_audit": ROOT
    / "out"
    / "ops"
    / "local_system_health_history_audit_latest.json",
}

OPTIONAL_SOURCE_PATHS = {
    "private_universe_receipt": ROOT
    / "out"
    / "ops"
    / "lumencore_private_universe_receipt_latest.json",
}

PRIVATE_MARKERS = (
    "private_estate",
    "patent_19_281_546",
    "cp575notice",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json_snapshot_required(path: Path) -> tuple[dict[str, Any], bytes]:
    if not path.is_file():
        raise FileNotFoundError(f"required reviewer-context input is missing: {path}")
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"required reviewer-context input is not an object: {path}")
    return payload, raw


def read_json_required(path: Path) -> dict[str, Any]:
    payload, _ = read_json_snapshot_required(path)
    return payload


def require_dict(payload: dict[str, Any], key: str, source: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"{source}.{key} must be an object")
    return value


def require_value(payload: dict[str, Any], key: str, source: str) -> Any:
    if key not in payload:
        raise ValueError(f"{source}.{key} is required")
    return payload[key]


def require_list(payload: dict[str, Any], key: str, source: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"{source}.{key} must be an array")
    return value


def require_number(payload: dict[str, Any], key: str, source: str) -> float:
    value = require_value(payload, key, source)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{source}.{key} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{source}.{key} must be finite")
    return number


def require_integer(payload: dict[str, Any], key: str, source: str) -> int:
    number = require_number(payload, key, source)
    if not number.is_integer():
        raise ValueError(f"{source}.{key} must be an integer")
    return int(number)


def require_nonnegative_integer(payload: dict[str, Any], key: str, source: str) -> int:
    number = require_integer(payload, key, source)
    if number < 0:
        raise ValueError(f"{source}.{key} must be non-negative")
    return number


def require_boolean(payload: dict[str, Any], key: str, source: str) -> bool:
    value = require_value(payload, key, source)
    if not isinstance(value, bool):
        raise ValueError(f"{source}.{key} must be boolean")
    return value


def require_nonempty_string(payload: dict[str, Any], key: str, source: str) -> str:
    value = require_value(payload, key, source)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{source}.{key} must be a non-empty string")
    return value


def require_sha256(payload: dict[str, Any], key: str, source: str) -> str:
    value = require_nonempty_string(payload, key, source).casefold()
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError(f"{source}.{key} must be a lowercase SHA-256 digest")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_utf8_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def stable_json_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def repo_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def assert_public_safe(payload: Any, location: str = "root") -> None:
    if isinstance(payload, dict):
        for key, value in payload.items():
            assert_public_safe(value, f"{location}.{key}")
        return
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            assert_public_safe(value, f"{location}[{index}]")
        return
    if isinstance(payload, str):
        normalized = payload.casefold().replace("\\", "/")
        for marker in PRIVATE_MARKERS:
            if marker in normalized:
                raise ValueError(f"private marker {marker!r} found at {location}")


def source_snapshots(
    paths: dict[str, Path],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]], str]:
    payloads: dict[str, dict[str, Any]] = {}
    receipts = []
    for source_id, path in sorted(paths.items()):
        payload, raw = read_json_snapshot_required(path)
        payloads[source_id] = payload
        receipts.append(
            {
                "source_id": source_id,
                "path": repo_path(path),
                "bytes": len(raw),
                "sha256": sha256_bytes(raw),
            }
        )
    return payloads, receipts, canonical_sha256(receipts)


def derive_hardware_design_prior_evidence(intake: dict[str, Any]) -> dict[str, Any]:
    source = "local_icloud_evidence_intake"
    if intake.get("schema") != "local_icloud_evidence_intake_v1":
        raise ValueError(f"{source}.schema is unexpected")

    summary = require_dict(intake, "summary", source)
    by_category = require_dict(summary, "by_category", f"{source}.summary")
    by_recommended_use = require_dict(
        summary,
        "by_recommended_use",
        f"{source}.summary",
    )
    record_count = require_nonnegative_integer(summary, "records", f"{source}.summary")
    geometry_hardware_candidates = require_nonnegative_integer(
        by_category,
        "geometry_hardware",
        f"{source}.summary.by_category",
    )
    design_prior_candidates = require_nonnegative_integer(
        by_recommended_use,
        "usable_as_concept_visual_or_design_prior_artifact_not_performance_proof",
        f"{source}.summary.by_recommended_use",
    )
    if geometry_hardware_candidates > record_count or design_prior_candidates > record_count:
        raise ValueError(f"{source}.summary aggregate counts exceed the record count")

    records = require_list(intake, "records", source)
    if len(records) != record_count:
        raise ValueError(f"{source}.summary.records does not match records length")
    geometry_records: list[dict[str, Any]] = []
    actual_design_prior_count = 0
    design_prior_label = (
        "usable_as_concept_visual_or_design_prior_artifact_not_performance_proof"
    )
    for index, value in enumerate(records):
        if not isinstance(value, dict):
            raise ValueError(f"{source}.records[{index}] must be an object")
        categories = require_list(value, "categories", f"{source}.records[{index}]")
        if value.get("recommended_use") == design_prior_label:
            actual_design_prior_count += 1
        if "geometry_hardware" in categories:
            geometry_records.append(value)
    if len(geometry_records) != geometry_hardware_candidates:
        raise ValueError(
            f"{source}.summary.by_category.geometry_hardware does not reconcile to records"
        )
    if actual_design_prior_count != design_prior_candidates:
        raise ValueError(
            f"{source}.summary.by_recommended_use design-prior count does not reconcile to records"
        )

    extension_counts: dict[str, int] = {}
    valid_sha256_values: set[str] = set()
    valid_sha256_record_count = 0
    stub_record_count = 0
    write_times: list[datetime] = []
    for index, record in enumerate(geometry_records):
        record_source = f"{source}.geometry_records[{index}]"
        extension = require_value(record, "extension", record_source)
        if not isinstance(extension, str):
            raise ValueError(f"{record_source}.extension must be a string")
        normalized_extension = extension.casefold()
        extension_counts[normalized_extension] = extension_counts.get(normalized_extension, 0) + 1

        byte_count = require_nonnegative_integer(record, "bytes", record_source)
        if byte_count < 100:
            stub_record_count += 1

        sha256 = record.get("sha256")
        if isinstance(sha256, str):
            normalized_sha256 = sha256.casefold()
            if len(normalized_sha256) == 64 and all(
                character in "0123456789abcdef" for character in normalized_sha256
            ):
                valid_sha256_record_count += 1
                valid_sha256_values.add(normalized_sha256)

        last_write = require_nonempty_string(record, "last_write_utc", record_source)
        try:
            parsed_last_write = datetime.fromisoformat(last_write.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError(f"{record_source}.last_write_utc must be ISO-8601") from exc
        if parsed_last_write.tzinfo is None:
            raise ValueError(f"{record_source}.last_write_utc must include a timezone")
        write_times.append(parsed_last_write.astimezone(timezone.utc))

    if not write_times and geometry_hardware_candidates:
        raise ValueError(f"{source} has geometry/hardware candidates without valid write times")

    claim_gate = require_dict(intake, "claim_gate", source)
    contains_secret_values = require_boolean(
        claim_gate,
        "contains_secret_values",
        f"{source}.claim_gate",
    )
    field_validation_proven = require_boolean(
        claim_gate,
        "field_validation_proven",
        f"{source}.claim_gate",
    )
    ready_for_portal_upload = require_boolean(
        claim_gate,
        "ready_for_portal_upload",
        f"{source}.claim_gate",
    )
    ready_for_submit = require_boolean(
        claim_gate,
        "ready_for_submit",
        f"{source}.claim_gate",
    )
    boundary = require_nonempty_string(claim_gate, "boundary", f"{source}.claim_gate")
    if "metadata intake only" not in boundary.casefold():
        raise ValueError(f"{source}.claim_gate.boundary does not preserve metadata-only scope")
    if contains_secret_values:
        raise ValueError(f"{source}.claim_gate reports secret values")
    if field_validation_proven or ready_for_portal_upload or ready_for_submit:
        raise ValueError(f"{source}.claim_gate exceeds the allowed design-prior evidence boundary")

    return {
        "intake_records": record_count,
        "geometry_hardware_candidates": geometry_hardware_candidates,
        "design_prior_candidates": design_prior_candidates,
        "distinct_valid_sha256_count": len(valid_sha256_values),
        "valid_sha256_record_count": valid_sha256_record_count,
        "extension_counts": dict(sorted(extension_counts.items())),
        "stl_record_count": extension_counts.get(".stl", 0),
        "pdf_record_count": extension_counts.get(".pdf", 0),
        "earliest_last_write_utc": min(write_times).isoformat() if write_times else None,
        "latest_last_write_utc": max(write_times).isoformat() if write_times else None,
        "stub_record_count_below_100_bytes": stub_record_count,
        "metadata_intake_only": "metadata intake only" in boundary.casefold(),
        "contains_secret_values": contains_secret_values,
        "field_validation_proven": field_validation_proven,
        "ready_for_portal_upload": ready_for_portal_upload,
        "ready_for_submit": ready_for_submit,
    }


def derive_local_system_health_history_evidence(audit: dict[str, Any]) -> dict[str, Any]:
    source = "local_system_health_history_audit"
    if audit.get("schema") != "luma.local_system_health_history_audit.v1":
        raise ValueError(f"{source}.schema is unexpected")
    if require_nonempty_string(audit, "mode", source) != "read_only_legacy_evidence_audit":
        raise ValueError(f"{source}.mode is unexpected")

    audit_receipt_sha256 = require_sha256(audit, "audit_receipt_sha256", source)
    receipt_body = {key: value for key, value in audit.items() if key != "audit_receipt_sha256"}
    if canonical_utf8_sha256(receipt_body) != audit_receipt_sha256:
        raise ValueError(f"{source}.audit_receipt_sha256 does not verify")

    source_manifest = require_dict(audit, "source_manifest", source)
    source_manifest_sha256 = require_sha256(audit, "source_manifest_sha256", source)
    if canonical_utf8_sha256(source_manifest) != source_manifest_sha256:
        raise ValueError(f"{source}.source_manifest_sha256 does not verify")

    summary = require_dict(audit, "summary", source)
    valid_snapshot_count = require_nonnegative_integer(
        summary,
        "valid_snapshot_count",
        f"{source}.summary",
    )
    active_utc_date_count = require_nonnegative_integer(
        summary,
        "active_utc_date_count",
        f"{source}.summary",
    )
    first_observed_utc = require_nonempty_string(
        summary,
        "first_observed_utc",
        f"{source}.summary",
    )
    last_observed_utc = require_nonempty_string(
        summary,
        "last_observed_utc",
        f"{source}.summary",
    )
    hour_bucket_coverage_pct = require_number(
        summary,
        "hour_bucket_coverage_pct",
        f"{source}.summary",
    )
    if not 0.0 <= hour_bucket_coverage_pct <= 100.0:
        raise ValueError(f"{source}.summary.hour_bucket_coverage_pct is outside 0..100")
    elapsed_days = require_number(summary, "elapsed_days", f"{source}.summary")
    if elapsed_days < 0.0:
        raise ValueError(f"{source}.summary.elapsed_days must be non-negative")

    integrity = require_dict(audit, "integrity", source)
    integrity_status = require_nonempty_string(integrity, "status", f"{source}.integrity")
    integrity_counts = require_dict(integrity, "counts", f"{source}.integrity")
    integrity_valid_snapshots = require_nonnegative_integer(
        integrity_counts,
        "valid_snapshots",
        f"{source}.integrity.counts",
    )
    complete_ledger_receipts = require_nonnegative_integer(
        integrity_counts,
        "complete_ledger_receipts",
        f"{source}.integrity.counts",
    )
    defect_count = require_nonnegative_integer(
        integrity_counts,
        "defect_count",
        f"{source}.integrity.counts",
    )
    if integrity_valid_snapshots != valid_snapshot_count:
        raise ValueError(f"{source} summary and integrity valid-snapshot counts disagree")

    trailing_windows = require_dict(audit, "trailing_windows", source)
    window_summaries: dict[str, dict[str, Any]] = {}
    for window_name in ("30", "90", "180"):
        window = require_dict(trailing_windows, window_name, f"{source}.trailing_windows")
        snapshot_count = require_nonnegative_integer(
            window,
            "snapshot_count",
            f"{source}.trailing_windows.{window_name}",
        )
        window_coverage = require_number(
            window,
            "hour_bucket_coverage_pct",
            f"{source}.trailing_windows.{window_name}",
        )
        if not 0.0 <= window_coverage <= 100.0:
            raise ValueError(
                f"{source}.trailing_windows.{window_name}.hour_bucket_coverage_pct is outside 0..100"
            )
        if require_boolean(
            window,
            "hardware_degradation_claim_allowed",
            f"{source}.trailing_windows.{window_name}",
        ):
            raise ValueError(f"{source} trailing window allows a hardware-degradation claim")

        cpu = require_dict(
            window,
            "cpu_point_samples",
            f"{source}.trailing_windows.{window_name}",
        )
        sample_seconds = require_number(
            cpu,
            "sample_seconds_each",
            f"{source}.trailing_windows.{window_name}.cpu_point_samples",
        )
        if sample_seconds != 1.0 or require_boolean(
            cpu,
            "sustained_utilization_claim_allowed",
            f"{source}.trailing_windows.{window_name}.cpu_point_samples",
        ):
            raise ValueError(f"{source} CPU point-sample boundary is unexpected")

        memory = require_dict(
            window,
            "memory_free",
            f"{source}.trailing_windows.{window_name}",
        )
        minimum_memory_free_pct = require_number(
            memory,
            "minimum_percent",
            f"{source}.trailing_windows.{window_name}.memory_free",
        )
        volume_free_space = require_dict(
            window,
            "volume_free_space",
            f"{source}.trailing_windows.{window_name}",
        )
        system_volume = require_dict(
            volume_free_space,
            "system_volume",
            f"{source}.trailing_windows.{window_name}.volume_free_space",
        )
        window_summaries[window_name] = {
            "snapshot_count": snapshot_count,
            "hour_bucket_coverage_pct": window_coverage,
            "cpu_sample_seconds_each": sample_seconds,
            "minimum_memory_free_pct": minimum_memory_free_pct,
            "system_volume_minimum_free_gb": require_number(
                system_volume,
                "minimum_free_gb",
                f"{source}.trailing_windows.{window_name}.volume_free_space.system_volume",
            ),
            "system_volume_delta_free_gb": require_number(
                system_volume,
                "delta_free_gb",
                f"{source}.trailing_windows.{window_name}.volume_free_space.system_volume",
            ),
        }

    claim_controls = require_dict(audit, "claim_controls", source)
    hardware_degradation_claim_allowed = require_boolean(
        claim_controls,
        "hardware_degradation_claim_allowed",
        f"{source}.claim_controls",
    )
    field_validation_claim_allowed = require_boolean(
        claim_controls,
        "field_validation_claim_allowed",
        f"{source}.claim_controls",
    )
    independent_validation_claim_allowed = require_boolean(
        claim_controls,
        "independent_validation_claim_allowed",
        f"{source}.claim_controls",
    )
    if (
        hardware_degradation_claim_allowed
        or field_validation_claim_allowed
        or independent_validation_claim_allowed
    ):
        raise ValueError(f"{source}.claim_controls exceeds the observational evidence boundary")

    return {
        "valid_snapshot_count": valid_snapshot_count,
        "active_utc_date_count": active_utc_date_count,
        "first_observed_utc": first_observed_utc,
        "last_observed_utc": last_observed_utc,
        "elapsed_days": elapsed_days,
        "hour_bucket_coverage_pct": hour_bucket_coverage_pct,
        "integrity_status": integrity_status,
        "complete_ledger_receipts": complete_ledger_receipts,
        "defect_count": defect_count,
        "trailing_windows": window_summaries,
        "cpu_measurement_mode": "sparse_one_second_point_samples",
        "hardware_degradation_claim_allowed": hardware_degradation_claim_allowed,
        "field_validation_claim_allowed": field_validation_claim_allowed,
        "independent_validation_claim_allowed": independent_validation_claim_allowed,
        "source_manifest_sha256": source_manifest_sha256,
        "audit_receipt_sha256": audit_receipt_sha256,
        "claim_boundary": require_nonempty_string(audit, "claim_boundary", source),
    }


def derive_private_universe_evidence(receipt: dict[str, Any]) -> dict[str, Any]:
    source = "private_universe_receipt"
    if receipt.get("schema") != "lumencore_private_universe_receipt_v1":
        raise ValueError(f"{source}.schema is unexpected")

    receipt_sha256 = require_sha256(receipt, "receipt_sha256", source)
    receipt_body = {key: value for key, value in receipt.items() if key != "receipt_sha256"}
    if stable_json_sha256(receipt_body) != receipt_sha256:
        raise ValueError(f"{source}.receipt_sha256 does not verify")

    status = require_nonempty_string(receipt, "status", source)
    generation_id = require_nonempty_string(receipt, "generation_id", source)
    generation_suffix = generation_id.removeprefix("generation_")
    if (
        not generation_id.startswith("generation_")
        or len(generation_suffix) != 32
        or any(character not in "0123456789abcdef" for character in generation_suffix)
    ):
        raise ValueError(f"{source}.generation_id is unexpected")

    transformation = require_dict(receipt, "transformation_identity", source)
    builder_sha256 = require_sha256(
        transformation,
        "builder_sha256",
        f"{source}.transformation_identity",
    )
    if require_nonempty_string(
        transformation,
        "parser_schema_version",
        f"{source}.transformation_identity",
    ) != "lumencore_private_universe_parser_v2":
        raise ValueError(f"{source}.transformation_identity parser schema is unexpected")
    sqlite_version = require_nonempty_string(
        transformation,
        "sqlite_version",
        f"{source}.transformation_identity",
    )
    if not require_boolean(
        transformation,
        "manifest_post_import_rehash_passed",
        f"{source}.transformation_identity",
    ):
        raise ValueError(f"{source}.transformation_identity manifest rehash did not pass")
    if require_nonempty_string(
        transformation,
        "generation_id",
        f"{source}.transformation_identity",
    ) != generation_id:
        raise ValueError(f"{source}.transformation_identity generation ID does not match")
    builder_git_commit = require_nonempty_string(
        transformation,
        "builder_git_commit",
        f"{source}.transformation_identity",
    )
    if builder_git_commit != "unavailable" and (
        len(builder_git_commit) != 40
        or any(character not in "0123456789abcdef" for character in builder_git_commit)
    ):
        raise ValueError(f"{source}.transformation_identity builder Git commit is invalid")
    builder_git_state = require_nonempty_string(
        transformation,
        "builder_git_state",
        f"{source}.transformation_identity",
    )
    if builder_git_state not in {
        "tracked_clean",
        "tracked_modified_dirty",
        "untracked_dirty",
        "unavailable_dirty_marker",
    }:
        raise ValueError(f"{source}.transformation_identity builder Git state is invalid")
    builder_git_dirty = require_boolean(
        transformation,
        "builder_git_dirty",
        f"{source}.transformation_identity",
    )
    builder_source_is_committed_snapshot = require_boolean(
        transformation,
        "builder_source_is_committed_snapshot",
        f"{source}.transformation_identity",
    )
    expected_committed_snapshot = builder_git_commit != "unavailable" and not builder_git_dirty
    if builder_source_is_committed_snapshot != expected_committed_snapshot:
        raise ValueError(f"{source}.transformation_identity Git snapshot flags do not reconcile")
    if (builder_git_state == "tracked_clean") == builder_git_dirty:
        raise ValueError(f"{source}.transformation_identity Git state and dirty flag disagree")
    sqlite_quick_check = require_nonempty_string(
        transformation,
        "sqlite_quick_check",
        f"{source}.transformation_identity",
    )
    staged_database_quick_check_passed = require_boolean(
        transformation,
        "staged_database_quick_check_passed",
        f"{source}.transformation_identity",
    )
    if sqlite_quick_check != "ok" or not staged_database_quick_check_passed:
        raise ValueError(f"{source}.transformation_identity SQLite quick_check did not pass")
    methodology = require_dict(receipt, "methodology", source)
    federation_mode = require_nonempty_string(
        methodology,
        "federation_mode",
        f"{source}.methodology",
    )
    freshness = require_nonempty_string(methodology, "freshness", f"{source}.methodology")
    if federation_mode != "zero_copy_manifest_federation" or freshness != "mixed_freshness":
        raise ValueError(f"{source}.methodology is outside the zero-copy mixed-freshness contract")

    false_methodology_fields = (
        "full_live_reconciliation",
        "manifest_referenced_file_bytes_read",
        "referenced_historical_asset_files_opened",
        "explicit_file_contents_parsed_or_extracted",
        "referenced_historical_asset_contents_parsed_or_extracted",
        "broad_roots_scanned",
        "archives_unpacked",
        "historical_hashes_reverified",
    )
    methodology_flags: dict[str, bool] = {}
    for field in false_methodology_fields:
        value = require_boolean(methodology, field, f"{source}.methodology")
        if value:
            raise ValueError(f"{source}.methodology.{field} exceeds the receipt boundary")
        methodology_flags[field] = value
    true_methodology_fields = (
        "source_manifest_files_read_and_parsed",
        "source_provenance_preserved",
        "manifest_initial_hash_stat_stable",
        "manifest_inputs_rehashed_after_import",
        "manifest_inputs_unchanged_after_import",
    )
    for field in true_methodology_fields:
        if not require_boolean(methodology, field, f"{source}.methodology"):
            raise ValueError(f"{source}.methodology.{field} must be true")
    manifest_input_count_reverified = require_nonnegative_integer(
        methodology,
        "manifest_input_count_reverified",
        f"{source}.methodology",
    )
    if require_nonempty_string(
        methodology,
        "effective_root_attribution",
        f"{source}.methodology",
    ) != "most_specific_declared_root":
        raise ValueError(f"{source}.methodology effective-root attribution is unexpected")
    lane_classification_method = require_nonempty_string(
        methodology,
        "lane_classification_method",
        f"{source}.methodology",
    )
    if lane_classification_method != "filename_extension_and_manifest_metadata_heuristics_only":
        raise ValueError(f"{source}.methodology candidate-lane classification is unexpected")
    lane_counts_are_content_validated = require_boolean(
        methodology,
        "lane_counts_are_content_validated",
        f"{source}.methodology",
    )
    if lane_counts_are_content_validated:
        raise ValueError(f"{source}.methodology candidate lane counts overstate validation")
    if require_nonempty_string(
        methodology,
        "sqlite_temp_store",
        f"{source}.methodology",
    ) != "memory_not_system_volume":
        raise ValueError(f"{source}.methodology SQLite temp-store scope is unexpected")
    if not require_boolean(
        methodology,
        "public_receipt_path_free",
        f"{source}.methodology",
    ):
        raise ValueError(f"{source}.methodology.public_receipt_path_free must be true")
    output_volume_preflight = require_dict(
        methodology,
        "output_volume_preflight",
        f"{source}.methodology",
    )
    if not require_boolean(
        output_volume_preflight,
        "gate_passed",
        f"{source}.methodology.output_volume_preflight",
    ):
        raise ValueError(f"{source}.methodology.output_volume_preflight gate must pass")
    minimum_free_percent = require_number(
        output_volume_preflight,
        "minimum_free_percent",
        f"{source}.methodology.output_volume_preflight",
    )
    observed_free_percent = require_number(
        output_volume_preflight,
        "observed_free_percent",
        f"{source}.methodology.output_volume_preflight",
    )
    if not 0.0 <= minimum_free_percent <= 100.0 or not 0.0 <= observed_free_percent <= 100.0:
        raise ValueError(f"{source}.methodology.output_volume_preflight percentages are invalid")
    observed_free_bytes = require_nonnegative_integer(
        output_volume_preflight,
        "observed_free_bytes",
        f"{source}.methodology.output_volume_preflight",
    )
    estimated_database_bytes = require_nonnegative_integer(
        output_volume_preflight,
        "estimated_database_bytes",
        f"{source}.methodology.output_volume_preflight",
    )
    absolute_reserve_bytes = require_nonnegative_integer(
        output_volume_preflight,
        "absolute_reserve_bytes",
        f"{source}.methodology.output_volume_preflight",
    )
    required_free_bytes = require_nonnegative_integer(
        output_volume_preflight,
        "required_free_bytes",
        f"{source}.methodology.output_volume_preflight",
    )
    if estimated_database_bytes <= 0 or absolute_reserve_bytes <= 0:
        raise ValueError(f"{source}.methodology output-volume estimate/reserve must be positive")
    if required_free_bytes != estimated_database_bytes + absolute_reserve_bytes:
        raise ValueError(f"{source}.methodology output-volume required bytes do not reconcile")
    if observed_free_bytes < required_free_bytes:
        raise ValueError(f"{source}.methodology output-volume absolute reserve did not pass")
    database_estimate_multiplier = require_number(
        output_volume_preflight,
        "database_estimate_multiplier",
        f"{source}.methodology.output_volume_preflight",
    )
    if database_estimate_multiplier <= 0:
        raise ValueError(f"{source}.methodology database estimate multiplier must be positive")
    if require_nonempty_string(
        output_volume_preflight,
        "database_estimate_basis",
        f"{source}.methodology.output_volume_preflight",
    ) != "aggregate_manifest_bytes_times_multiplier_with_minimum_floor":
        raise ValueError(f"{source}.methodology database estimate basis is unexpected")
    if not require_boolean(
        output_volume_preflight,
        "nearest_existing_ancestor_checked_before_output_creation",
        f"{source}.methodology.output_volume_preflight",
    ):
        raise ValueError(f"{source}.methodology output-volume ancestor preflight is missing")
    if not require_boolean(
        output_volume_preflight,
        "output_volume_only",
        f"{source}.methodology.output_volume_preflight",
    ) or require_boolean(
        output_volume_preflight,
        "input_volume_gate_required",
        f"{source}.methodology.output_volume_preflight",
    ):
        raise ValueError(f"{source}.methodology output-volume preflight scope is unexpected")
    if require_nonempty_string(
        output_volume_preflight,
        "input_scope",
        f"{source}.methodology.output_volume_preflight",
    ) != "manifest_only_plus_individually_authorized_explicit_files":
        raise ValueError(f"{source}.methodology output-volume input scope is unexpected")

    explicit_file_bytes_read_for_sha256 = require_boolean(
        methodology,
        "explicit_file_bytes_read_for_sha256",
        f"{source}.methodology",
    )
    explicit_user_supplied_files_hashed = require_boolean(
        methodology,
        "explicit_user_supplied_files_hashed",
        f"{source}.methodology",
    )

    summary = require_dict(receipt, "summary", source)
    summary_fields = (
        "source_manifest_count",
        "source_observation_count",
        "unique_asset_count",
        "duplicate_observation_count",
        "historical_content_sha256_observation_count",
        "historical_metadata_sha256_observation_count",
        "historical_content_sha256_conflict_asset_count",
        "explicit_file_count",
        "explicit_file_sha256_coverage_count",
        "root_alias_count",
        "root_registry_entry_count",
        "candidate_lane_count",
        "archive_reference_asset_count",
        "unmapped_observation_count",
        "reported_root_mismatch_observation_count",
    )
    normalized_summary = {
        field: require_nonnegative_integer(summary, field, f"{source}.summary")
        for field in summary_fields
    }
    expected_duplicate_count = max(
        0,
        normalized_summary["source_observation_count"]
        - normalized_summary["unique_asset_count"],
    )
    if normalized_summary["duplicate_observation_count"] != expected_duplicate_count:
        raise ValueError(f"{source}.summary.duplicate_observation_count does not reconcile")
    if (
        normalized_summary["explicit_file_sha256_coverage_count"]
        != normalized_summary["explicit_file_count"]
    ):
        raise ValueError(f"{source}.summary explicit-file hash coverage must equal file count")
    explicit_hashing_expected = bool(
        normalized_summary["explicit_file_count"]
        and normalized_summary["explicit_file_sha256_coverage_count"]
    )
    if explicit_file_bytes_read_for_sha256 != explicit_hashing_expected:
        raise ValueError(
            f"{source}.methodology.explicit_file_bytes_read_for_sha256 does not reconcile"
        )
    if explicit_user_supplied_files_hashed != explicit_hashing_expected:
        raise ValueError(
            f"{source}.methodology.explicit_user_supplied_files_hashed does not reconcile"
        )
    if manifest_input_count_reverified != normalized_summary["source_manifest_count"]:
        raise ValueError(f"{source}.methodology manifest rehash count does not reconcile")

    source_summary = require_list(receipt, "source_summary", source)
    if len(source_summary) != normalized_summary["source_manifest_count"]:
        raise ValueError(f"{source}.source_summary does not reconcile to source_manifest_count")
    for index, value in enumerate(source_summary):
        if not isinstance(value, dict):
            raise ValueError(f"{source}.source_summary[{index}] must be an object")
        row_source = f"{source}.source_summary[{index}]"
        require_nonempty_string(value, "source_kind", row_source)
        require_sha256(value, "source_sha256", row_source)
        require_nonnegative_integer(value, "source_bytes", row_source)
        require_nonnegative_integer(value, "manifest_row_count", row_source)
        require_nonnegative_integer(value, "observation_count", row_source)
        require_nonnegative_integer(value, "invalid_observation_count", row_source)
        if require_boolean(value, "manifest_referenced_file_bytes_read", row_source):
            raise ValueError(
                f"{row_source}.manifest_referenced_file_bytes_read exceeds the receipt boundary"
            )
        if require_boolean(value, "historical_hashes_reverified", row_source):
            raise ValueError(f"{row_source}.historical_hashes_reverified exceeds the receipt boundary")

    candidate_lane_counts_raw = require_dict(receipt, "candidate_lane_counts", source)
    candidate_lane_counts: dict[str, int] = {}
    for lane, count in sorted(candidate_lane_counts_raw.items()):
        if not isinstance(lane, str) or not lane:
            raise ValueError(f"{source}.candidate_lane_counts keys must be non-empty strings")
        candidate_lane_counts[lane] = require_nonnegative_integer(
            candidate_lane_counts_raw,
            lane,
            f"{source}.candidate_lane_counts",
        )
    if len(candidate_lane_counts) != normalized_summary["candidate_lane_count"]:
        raise ValueError(
            f"{source}.candidate_lane_counts does not reconcile to summary.candidate_lane_count"
        )

    root_summary = require_dict(receipt, "root_summary", source)
    coverage_is_current_live_truth = require_boolean(
        root_summary,
        "coverage_is_current_live_truth",
        f"{source}.root_summary",
    )
    if coverage_is_current_live_truth:
        raise ValueError(f"{source}.root_summary overstates live coverage")
    coverage_quality_counts = require_dict(
        root_summary,
        "coverage_quality_counts",
        f"{source}.root_summary",
    )
    registry_role_counts = require_dict(
        root_summary,
        "registry_role_counts",
        f"{source}.root_summary",
    )
    for count_source, values in {
        "coverage_quality_counts": coverage_quality_counts,
        "registry_role_counts": registry_role_counts,
    }.items():
        for key in values:
            require_nonnegative_integer(values, key, f"{source}.root_summary.{count_source}")

    claim_boundaries = require_dict(receipt, "claim_boundaries", source)
    boundary_fields = (
        "complete_universe_claim_allowed",
        "current_file_existence_claim_allowed",
        "content_ownership_claim_allowed",
        "field_validation_claim_allowed",
        "technical_readiness_claim_allowed",
        "valuation_claim_allowed",
    )
    for field in boundary_fields:
        if require_boolean(claim_boundaries, field, f"{source}.claim_boundaries"):
            raise ValueError(f"{source}.claim_boundaries.{field} exceeds the custody boundary")

    custody = require_dict(receipt, "private_index_custody", source)
    database_sha256 = require_sha256(custody, "database_sha256", f"{source}.private_index_custody")
    database_bytes = require_nonnegative_integer(
        custody,
        "database_bytes",
        f"{source}.private_index_custody",
    )
    if database_bytes <= 0:
        raise ValueError(f"{source}.private_index_custody.database_bytes must be positive")
    locator_alias = require_nonempty_string(
        custody,
        "locator_alias",
        f"{source}.private_index_custody",
    )
    if locator_alias != "private_proof_vault_estate_index_latest":
        raise ValueError(f"{source}.private_index_custody.locator_alias is unexpected")
    if require_nonempty_string(
        custody,
        "generation_id",
        f"{source}.private_index_custody",
    ) != generation_id:
        raise ValueError(f"{source}.private_index_custody generation ID does not match")
    if require_nonnegative_integer(
        custody,
        "publish_set_artifact_count",
        f"{source}.private_index_custody",
    ) != 4:
        raise ValueError(f"{source}.private_index_custody publish-set count is unexpected")
    if not require_boolean(
        custody,
        "atomic_per_artifact_replace",
        f"{source}.private_index_custody",
    ):
        raise ValueError(f"{source}.private_index_custody atomic replacement must be true")
    if not require_boolean(
        custody,
        "rollback_protected_publish_set",
        f"{source}.private_index_custody",
    ):
        raise ValueError(f"{source}.private_index_custody rollback protection must be true")
    if not require_boolean(
        custody,
        "staged_database_quick_check_passed",
        f"{source}.private_index_custody",
    ):
        raise ValueError(f"{source}.private_index_custody staged quick_check must pass")
    prior_database_present = require_boolean(
        custody,
        "prior_latest_database_present",
        f"{source}.private_index_custody",
    )
    prior_database_preserved = require_boolean(
        custody,
        "prior_latest_database_preserved",
        f"{source}.private_index_custody",
    )
    prior_database_sha256 = require_value(
        custody,
        "prior_latest_database_sha256",
        f"{source}.private_index_custody",
    )
    prior_database_bytes = require_nonnegative_integer(
        custody,
        "prior_latest_database_bytes",
        f"{source}.private_index_custody",
    )
    prior_private_receipt_preserved = require_boolean(
        custody,
        "prior_latest_private_receipt_preserved",
        f"{source}.private_index_custody",
    )
    prior_private_receipt_present = require_boolean(
        custody,
        "prior_latest_private_receipt_present",
        f"{source}.private_index_custody",
    )
    prior_private_receipt_sha256 = require_value(
        custody,
        "prior_latest_private_receipt_sha256",
        f"{source}.private_index_custody",
    )
    prior_private_receipt_bytes = require_nonnegative_integer(
        custody,
        "prior_latest_private_receipt_bytes",
        f"{source}.private_index_custody",
    )
    if prior_database_present:
        if not prior_database_preserved:
            raise ValueError(f"{source}.private_index_custody did not preserve the prior database")
        if not isinstance(prior_database_sha256, str):
            raise ValueError(f"{source}.private_index_custody prior database SHA-256 is invalid")
        require_sha256(
            {"sha256": prior_database_sha256},
            "sha256",
            f"{source}.private_index_custody.prior_latest_database",
        )
        if prior_database_bytes <= 0:
            raise ValueError(f"{source}.private_index_custody prior database bytes must be positive")
    elif prior_database_preserved or prior_database_sha256 != "" or prior_database_bytes != 0:
        raise ValueError(f"{source}.private_index_custody absent prior database fields are inconsistent")
    if prior_private_receipt_present:
        if not prior_private_receipt_preserved:
            raise ValueError(f"{source}.private_index_custody did not preserve the prior receipt")
        if not isinstance(prior_private_receipt_sha256, str):
            raise ValueError(f"{source}.private_index_custody prior receipt SHA-256 is invalid")
        require_sha256(
            {"sha256": prior_private_receipt_sha256},
            "sha256",
            f"{source}.private_index_custody.prior_latest_private_receipt",
        )
        if prior_private_receipt_bytes <= 0:
            raise ValueError(f"{source}.private_index_custody prior receipt bytes must be positive")
    elif (
        prior_private_receipt_preserved
        or prior_private_receipt_sha256 != ""
        or prior_private_receipt_bytes != 0
    ):
        raise ValueError(f"{source}.private_index_custody absent prior receipt fields are inconsistent")

    return {
        "status": status,
        "generation_id": generation_id,
        "federation_mode": federation_mode,
        "freshness": freshness,
        "fresh_full_scan_completed": False,
        **methodology_flags,
        "lane_classification_method": lane_classification_method,
        "lane_counts_are_content_validated": lane_counts_are_content_validated,
        "explicit_file_bytes_read_for_sha256": explicit_file_bytes_read_for_sha256,
        "explicit_user_supplied_files_hashed": explicit_user_supplied_files_hashed,
        "output_volume_preflight": {
            "gate_passed": True,
            "minimum_free_percent": minimum_free_percent,
            "observed_free_percent": observed_free_percent,
            "observed_free_bytes": observed_free_bytes,
            "estimated_database_bytes": estimated_database_bytes,
            "absolute_reserve_bytes": absolute_reserve_bytes,
            "required_free_bytes": required_free_bytes,
        },
        "transformation_identity": {
            "builder_sha256": builder_sha256,
            "sqlite_version": sqlite_version,
            "builder_git_commit": builder_git_commit,
            "builder_git_state": builder_git_state,
            "builder_git_dirty": builder_git_dirty,
            "builder_source_is_committed_snapshot": builder_source_is_committed_snapshot,
            "sqlite_quick_check": sqlite_quick_check,
            "staged_database_quick_check_passed": staged_database_quick_check_passed,
        },
        **normalized_summary,
        "candidate_lane_counts": candidate_lane_counts,
        "coverage_quality_counts": dict(sorted(coverage_quality_counts.items())),
        "registry_role_counts": dict(sorted(registry_role_counts.items())),
        "coverage_is_current_live_truth": coverage_is_current_live_truth,
        "private_index_custody": {
            "generation_id": generation_id,
            "database_sha256": database_sha256,
            "database_bytes": database_bytes,
            "locator_alias": locator_alias,
            "publish_set_artifact_count": 4,
            "atomic_per_artifact_replace": True,
            "rollback_protected_publish_set": True,
            "staged_database_quick_check_passed": True,
            "prior_latest_database_present": prior_database_present,
            "prior_latest_database_preserved": prior_database_preserved,
            "prior_latest_database_sha256": prior_database_sha256,
            "prior_latest_database_bytes": prior_database_bytes,
            "prior_latest_private_receipt_present": prior_private_receipt_present,
            "prior_latest_private_receipt_preserved": prior_private_receipt_preserved,
            "prior_latest_private_receipt_sha256": prior_private_receipt_sha256,
            "prior_latest_private_receipt_bytes": prior_private_receipt_bytes,
        },
        "receipt_sha256": receipt_sha256,
    }


def derive_eia_residual_evidence(
    benchmark: dict[str, Any],
    protocol: dict[str, Any],
    *,
    protocol_path: str,
    protocol_sha256: str,
) -> dict[str, Any]:
    if benchmark.get("schema") != "eia_grid_residual_moe_benchmark.v1":
        raise ValueError("eia_residual_benchmark.schema is unexpected")
    if protocol.get("schema") != "eia_grid_residual_moe_protocol.v1":
        raise ValueError("eia_residual_protocol.schema is unexpected")

    benchmark_protocol = require_dict(benchmark, "protocol", "eia_residual_benchmark")
    if require_value(benchmark_protocol, "path", "eia_residual_benchmark.protocol") != protocol_path:
        raise ValueError("eia_residual_benchmark protocol path does not match the required protocol source")
    if require_value(benchmark_protocol, "sha256", "eia_residual_benchmark.protocol") != protocol_sha256:
        raise ValueError("eia_residual_benchmark protocol hash does not match the required protocol snapshot")

    selection = require_dict(benchmark, "selection", "eia_residual_benchmark")
    selected_candidate = require_value(selection, "selected_candidate", "eia_residual_benchmark.selection")
    if not isinstance(selected_candidate, str) or not selected_candidate.strip():
        raise ValueError("eia_residual_benchmark.selection.selected_candidate must be a non-empty string")

    leaderboard = require_list(benchmark, "holdout_leaderboard", "eia_residual_benchmark")
    selected_rows = [
        row
        for row in leaderboard
        if isinstance(row, dict) and row.get("strategy") == selected_candidate
    ]
    if len(selected_rows) != 1:
        raise ValueError("eia_residual_benchmark holdout leaderboard must contain the selected candidate exactly once")
    selected_holdout = selected_rows[0]
    holdout_rows = require_integer(
        selected_holdout,
        "row_count",
        "eia_residual_benchmark.selected_holdout",
    )
    holdout_authorities = require_integer(
        selected_holdout,
        "authority_count",
        "eia_residual_benchmark.selected_holdout",
    )
    if holdout_rows <= 0 or holdout_authorities <= 0:
        raise ValueError("eia_residual_benchmark selected holdout counts must be positive")

    comparisons = require_list(benchmark, "baseline_comparisons", "eia_residual_benchmark")
    if not comparisons or not all(isinstance(row, dict) for row in comparisons):
        raise ValueError("eia_residual_benchmark.baseline_comparisons must contain objects")

    protocol_gate = require_dict(protocol, "promotion_gate", "eia_residual_protocol")
    holm_threshold = require_number(
        protocol_gate,
        "require_holm_adjusted_p_at_most",
        "eia_residual_protocol.promotion_gate",
    )
    if not 0.0 <= holm_threshold <= 1.0:
        raise ValueError("eia_residual_protocol Holm threshold must be between zero and one")

    authority_month_counts: set[int] = set()
    normalized_comparisons: list[dict[str, Any]] = []
    worst_authority: str | None = None
    worst_baseline: str | None = None
    worst_authority_mean_skill: float | None = None
    for index, comparison_value in enumerate(comparisons):
        comparison = comparison_value
        source = f"eia_residual_benchmark.baseline_comparisons[{index}]"
        baseline = require_value(comparison, "baseline", source)
        if not isinstance(baseline, str) or not baseline.strip():
            raise ValueError(f"{source}.baseline must be a non-empty string")
        paired_count = require_integer(comparison, "paired_authority_month_count", source)
        if paired_count <= 0:
            raise ValueError(f"{source}.paired_authority_month_count must be positive")
        authority_month_counts.add(paired_count)
        holm_p = require_number(comparison, "holm_adjusted_p_value", source)
        if not 0.0 <= holm_p <= 1.0:
            raise ValueError(f"{source}.holm_adjusted_p_value must be between zero and one")
        mean_skill_delta = require_number(comparison, "mean_skill_delta", source)
        interval = require_list(comparison, "cluster_bootstrap_mean_skill_ci95", source)
        if len(interval) != 2:
            raise ValueError(f"{source}.cluster_bootstrap_mean_skill_ci95 must contain two bounds")
        interval_bounds: list[float] = []
        for bound_index, bound in enumerate(interval):
            if isinstance(bound, bool) or not isinstance(bound, (int, float)):
                raise ValueError(
                    f"{source}.cluster_bootstrap_mean_skill_ci95[{bound_index}] must be numeric"
                )
            numeric_bound = float(bound)
            if not math.isfinite(numeric_bound):
                raise ValueError(
                    f"{source}.cluster_bootstrap_mean_skill_ci95[{bound_index}] must be finite"
                )
            interval_bounds.append(numeric_bound)
        if interval_bounds[0] > interval_bounds[1]:
            raise ValueError(f"{source}.cluster_bootstrap_mean_skill_ci95 bounds are reversed")
        authority_skills = require_dict(comparison, "authority_mean_skill", source)
        if not authority_skills:
            raise ValueError(f"{source}.authority_mean_skill must not be empty")
        for authority, value in authority_skills.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{source}.authority_mean_skill.{authority} must be numeric")
            skill = float(value)
            if not math.isfinite(skill):
                raise ValueError(f"{source}.authority_mean_skill.{authority} must be finite")
            if worst_authority_mean_skill is None or skill < worst_authority_mean_skill:
                worst_authority_mean_skill = skill
                worst_authority = str(authority)
                worst_baseline = baseline
        normalized_comparisons.append(
            {
                "baseline": baseline,
                "holm_adjusted_p_value": holm_p,
                "mean_skill_delta": mean_skill_delta,
                "cluster_bootstrap_mean_skill_ci95": interval_bounds,
            }
        )

    if len(authority_month_counts) != 1:
        raise ValueError("eia_residual_benchmark baseline comparisons must use one authority-month pair count")
    authority_month_pairs = next(iter(authority_month_counts))
    holm_positive_count = sum(
        row["holm_adjusted_p_value"] <= holm_threshold
        and row["mean_skill_delta"] > 0.0
        and row["cluster_bootstrap_mean_skill_ci95"][0] > 0.0
        for row in normalized_comparisons
    )
    holm_comparison_total = len(normalized_comparisons)

    coverage = require_dict(benchmark, "holdout_coverage", "eia_residual_benchmark")
    minimum_coverage_days = require_integer(
        coverage,
        "minimum_common_holdout_days",
        "eia_residual_benchmark.holdout_coverage",
    )
    coverage_target_days = require_integer(
        protocol_gate,
        "minimum_common_holdout_days_per_authority",
        "eia_residual_protocol.promotion_gate",
    )
    if minimum_coverage_days < 0 or coverage_target_days <= 0:
        raise ValueError("EIA residual coverage counts are invalid")

    promotion = require_dict(benchmark, "promotion_gate", "eia_residual_benchmark")
    coverage_pass = require_value(promotion, "coverage_pass", "eia_residual_benchmark.promotion_gate")
    comparisons_pass = require_value(
        promotion,
        "all_baseline_comparisons_pass",
        "eia_residual_benchmark.promotion_gate",
    )
    protocol_grade_champion = require_value(
        promotion,
        "protocol_grade_internal_champion",
        "eia_residual_benchmark.promotion_gate",
    )
    external_replication_complete = require_value(
        promotion,
        "external_replication_complete",
        "eia_residual_benchmark.promotion_gate",
    )
    field_validation_complete = require_value(
        promotion,
        "field_validation_complete",
        "eia_residual_benchmark.promotion_gate",
    )
    for key, value in {
        "coverage_pass": coverage_pass,
        "all_baseline_comparisons_pass": comparisons_pass,
        "protocol_grade_internal_champion": protocol_grade_champion,
        "external_replication_complete": external_replication_complete,
        "field_validation_complete": field_validation_complete,
    }.items():
        if not isinstance(value, bool):
            raise ValueError(f"eia_residual_benchmark.promotion_gate.{key} must be boolean")

    execution_controls = require_dict(protocol, "execution_controls", "eia_residual_protocol")
    dollar_conversion_allowed = require_value(
        execution_controls,
        "dollar_conversion_allowed",
        "eia_residual_protocol.execution_controls",
    )
    if not isinstance(dollar_conversion_allowed, bool):
        raise ValueError("eia_residual_protocol.execution_controls.dollar_conversion_allowed must be boolean")

    full_protocol_gate_closed = not protocol_grade_champion
    all_internal_comparisons_holm_positive = bool(
        holm_comparison_total and holm_positive_count == holm_comparison_total
    )
    if all_internal_comparisons_holm_positive and full_protocol_gate_closed:
        status = "all_internal_comparisons_holm_positive_full_protocol_gate_closed"
    elif protocol_grade_champion:
        status = "protocol_grade_internal_champion"
    else:
        status = "holm_or_composite_protocol_gate_not_passed"

    claim_boundary = require_value(benchmark, "claim_boundary", "eia_residual_benchmark")
    if not isinstance(claim_boundary, str) or not claim_boundary.strip():
        raise ValueError("eia_residual_benchmark.claim_boundary must be a non-empty string")

    return {
        "selected_candidate": selected_candidate,
        "holdout_rows": holdout_rows,
        "holdout_authorities": holdout_authorities,
        "authority_month_pairs": authority_month_pairs,
        "holm_positive_comparison_count": holm_positive_count,
        "holm_comparison_total": holm_comparison_total,
        "holm_result": f"{holm_positive_count}/{holm_comparison_total} Holm-positive internal comparisons",
        "holm_threshold": holm_threshold,
        "all_internal_comparisons_holm_positive": all_internal_comparisons_holm_positive,
        "minimum_coverage_days": minimum_coverage_days,
        "coverage_target_days": coverage_target_days,
        "coverage_result": (
            f"{minimum_coverage_days}/{coverage_target_days} minimum common days"
        ),
        "worst_authority": worst_authority,
        "worst_baseline": worst_baseline,
        "worst_authority_mean_skill": worst_authority_mean_skill,
        "coverage_pass": coverage_pass,
        "all_baseline_comparisons_pass": comparisons_pass,
        "protocol_grade_internal_champion": protocol_grade_champion,
        "full_protocol_gate": "CLOSED" if full_protocol_gate_closed else "OPEN",
        "external_replication_complete": external_replication_complete,
        "field_validation_complete": field_validation_complete,
        "dollar_conversion_allowed": dollar_conversion_allowed,
        "status": status,
        "claim_boundary": claim_boundary,
    }


def build_context() -> dict[str, Any]:
    available_optional_sources = {
        source_id: path
        for source_id, path in OPTIONAL_SOURCE_PATHS.items()
        if path.is_file()
    }
    snapshots, receipts, input_chain_sha256 = source_snapshots(
        {"lexicon": LEXICON, **SOURCE_PATHS, **available_optional_sources}
    )
    lexicon = snapshots["lexicon"]
    sources = {name: snapshots[name] for name in SOURCE_PATHS}
    receipt_by_source = {row["source_id"]: row for row in receipts}

    identity = require_dict(lexicon, "identity", "lexicon")
    maturity_policy = require_dict(lexicon, "level_policy", "lexicon")
    human_policy = require_dict(lexicon, "human_authority_policy", "lexicon")

    vault = sources["prior_proof_vault"]
    vault_summary = require_dict(vault, "summary", "prior_proof_vault")
    vault_copy = require_dict(vault, "copy_result", "prior_proof_vault")

    estate_summary = require_dict(sources["estate_index"], "summary", "estate_index")
    hardware_design_prior = derive_hardware_design_prior_evidence(
        sources["local_icloud_evidence_intake"]
    )
    health_history = derive_local_system_health_history_evidence(
        sources["local_system_health_history_audit"]
    )
    private_universe = (
        derive_private_universe_evidence(snapshots["private_universe_receipt"])
        if "private_universe_receipt" in snapshots
        else None
    )
    live_summary = require_dict(sources["live_source_measurement"], "summary", "live_source_measurement")
    replay = sources["locked_replay"]
    replay_summary = require_dict(replay, "summary", "locked_replay")
    replay_gates = require_dict(replay, "claim_gates", "locked_replay")
    reviewer = sources["reviewer_gate"]
    reviewer_summary = require_dict(reviewer, "summary", "reviewer_gate")
    faa = sources["faa_sdr_10k"]
    faa_execution = require_dict(faa, "execution", "faa_sdr_10k")
    faa_splits = require_dict(faa, "splits", "faa_sdr_10k")
    faa_gate = require_dict(faa, "promotion_gate", "faa_sdr_10k")
    faa_rolls = require_dict(faa, "rolls_royce_exploratory", "faa_sdr_10k")
    faa_leaderboard = require_value(faa, "holdout_leaderboard", "faa_sdr_10k")
    if not isinstance(faa_leaderboard, list):
        raise ValueError("faa_sdr_10k.holdout_leaderboard must be an array")
    faa_candidate = next((row for row in faa_leaderboard if row.get("candidate")), None)
    faa_baseline_name = str(require_value(faa, "strongest_approved_baseline", "faa_sdr_10k"))
    faa_baseline = next((row for row in faa_leaderboard if row.get("model") == faa_baseline_name), None)
    if not isinstance(faa_candidate, dict) or not isinstance(faa_baseline, dict):
        raise ValueError("faa_sdr_10k leaderboard must identify the candidate and strongest baseline")
    eia = sources["eia_prospective_router"]
    eia_gates = require_dict(eia, "sample_gates", "eia_prospective_router")
    eia_residual = derive_eia_residual_evidence(
        sources["eia_residual_benchmark"],
        sources["eia_residual_protocol"],
        protocol_path=receipt_by_source["eia_residual_protocol"]["path"],
        protocol_sha256=receipt_by_source["eia_residual_protocol"]["sha256"],
    )

    mda_v1 = sources["mda_feasibility_v1"]
    mda_v1_counts = require_dict(mda_v1, "fixture_counts", "mda_feasibility_v1")
    mda_v1_metrics = require_dict(mda_v1, "holdout_metrics", "mda_feasibility_v1")
    mda_v1_candidate = require_dict(
        mda_v1_metrics,
        "hybrid_static_then_lexical_v1",
        "mda_feasibility_v1.holdout_metrics",
    )
    mda_v1_gate = require_dict(mda_v1, "gate", "mda_feasibility_v1")

    mda_v2 = sources["mda_open_set_v2"]
    mda_v2_counts = require_dict(mda_v2, "fixture_counts", "mda_open_set_v2")
    mda_v2_metrics = require_dict(mda_v2, "holdout_metrics", "mda_open_set_v2")
    mda_v2_candidate = require_dict(
        mda_v2_metrics,
        "hybrid_static_then_open_set_lexical_v2",
        "mda_open_set_v2.holdout_metrics",
    )
    mda_v2_gate = require_dict(mda_v2, "gate", "mda_open_set_v2")

    prior_vault_verified = bool(vault_copy.get("all_copied_hashes_verified")) and (
        int(vault_copy.get("verified_count", -1)) == int(vault_summary.get("ready_count", -2))
    )

    proof_cards = [
        {
            "proof_id": "prooflock_prior_vault",
            "title": "Prior external proof-vault custody",
            "evidence_class": "provenance_and_custody",
            "attained_maturity_level": 3,
            "status": "verified" if prior_vault_verified else "not_verified",
            "facts": {
                "artifact_count": require_value(vault_summary, "artifact_count", "prior_proof_vault.summary"),
                "ready_count": require_value(vault_summary, "ready_count", "prior_proof_vault.summary"),
                "verified_count": require_value(vault_copy, "verified_count", "prior_proof_vault.copy_result"),
                "all_copied_hashes_verified": prior_vault_verified,
                "packet_name": Path(str(require_value(vault, "packet_dir", "prior_proof_vault"))).name,
                "manifest_source_sha256": receipt_by_source["prior_proof_vault"]["sha256"],
            },
            "claim_boundary": require_value(vault, "claim_boundary", "prior_proof_vault"),
        },
        {
            "proof_id": "estate_inventory",
            "title": "Public-safe estate inventory",
            "evidence_class": "asset_inventory",
            "attained_maturity_level": 1,
            "status": "indexed",
            "facts": {
                "managed_file_count": require_value(estate_summary, "managed_file_count", "estate_index.summary"),
                "managed_total_bytes": require_value(estate_summary, "managed_total_bytes", "estate_index.summary"),
                "inventory_chain_sha256": require_value(estate_summary, "inventory_chain_sha256", "estate_index.summary"),
                "secret_content_indexed": require_value(estate_summary, "secret_content_indexed", "estate_index.summary"),
                "sensitive_paths_redacted": require_value(
                    estate_summary,
                    "sensitive_paths_redacted_from_public_payload",
                    "estate_index.summary",
                ),
            },
            "claim_boundary": "An inventory proves discoverability and custody metadata, not scientific validity, ownership, novelty, or commercial value.",
        },
        {
            "proof_id": "hardware_3d_design_prior_custody",
            "title": "Hardware and 3D design-prior metadata custody",
            "evidence_class": "internal_metadata_custody",
            "attained_maturity_level": 1,
            "status": "candidate_design_priors_only",
            "facts": {
                **hardware_design_prior,
                "source_receipt_sha256": receipt_by_source[
                    "local_icloud_evidence_intake"
                ]["sha256"],
            },
            "claim_boundary": (
                "This internal metadata intake identifies design-prior candidates only. It proves "
                "no hardware build, field deployment, hardware degradation, performance result, "
                "or independent evaluation."
            ),
        },
        {
            "proof_id": "local_system_health_history_observation",
            "title": "Local system-health history custody audit",
            "evidence_class": "internal_observational_evidence",
            "attained_maturity_level": 2,
            "status": health_history["integrity_status"],
            "facts": {
                key: value
                for key, value in health_history.items()
                if key != "claim_boundary"
            }
            | {
                "source_receipt_sha256": receipt_by_source[
                    "local_system_health_history_audit"
                ]["sha256"]
            },
            "claim_boundary": (
                f"{health_history['claim_boundary']} No independent evaluator is named in "
                "this internal receipt."
            ),
        },
        {
            "proof_id": "live_source_measurement",
            "title": "Measured source breadth",
            "evidence_class": "fresh_source_measurement",
            "attained_maturity_level": 3,
            "status": "measured_with_thin_sources",
            "facts": {
                "enabled_sources": require_value(live_summary, "enabled_sources", "live_source_measurement.summary"),
                "measured_sources": require_value(live_summary, "measured_sources", "live_source_measurement.summary"),
                "failed_or_thin_sources": require_value(
                    live_summary,
                    "failed_or_thin_sources",
                    "live_source_measurement.summary",
                ),
                "total_measured_rows": require_value(
                    live_summary,
                    "total_measured_rows",
                    "live_source_measurement.summary",
                ),
                "coverage_pct": require_value(live_summary, "coverage_pct", "live_source_measurement.summary"),
            },
            "claim_boundary": require_value(live_summary, "claim_boundary", "live_source_measurement.summary"),
        },
        {
            "proof_id": "locked_source_baseline_replay",
            "title": "Locked source-conditioned baseline replay",
            "evidence_class": "source_conditioned_replay",
            "attained_maturity_level": 3,
            "status": "complete_with_wins_and_non_wins",
            "facts": {
                "adapter_backed_routes": require_value(replay_summary, "adapter_backed_routes", "locked_replay.summary"),
                "baseline_comparison_count": require_value(
                    replay_summary,
                    "baseline_comparison_count",
                    "locked_replay.summary",
                ),
                "candidate_win_count": require_value(replay_summary, "candidate_win_count", "locked_replay.summary"),
                "candidate_loss_or_tie_count": require_value(
                    replay_summary,
                    "candidate_loss_or_tie_count",
                    "locked_replay.summary",
                ),
                "estimated_rows_replayed": require_value(
                    replay_summary,
                    "estimated_rows_replayed",
                    "locked_replay.summary",
                ),
                "numeric_samples_read": require_value(
                    replay_summary,
                    "numeric_samples_read",
                    "locked_replay.summary",
                ),
                "energy_proxy_routes_replayed": require_value(
                    replay_summary,
                    "energy_proxy_routes_replayed",
                    "locked_replay.summary",
                ),
                "energy_proxy_unique_series_replays": require_value(
                    replay_summary,
                    "energy_proxy_unique_series_replays",
                    "locked_replay.summary",
                ),
                "replay_chain_sha256": require_value(replay_summary, "replay_chain_sha256", "locked_replay.summary"),
            },
            "claim_boundary": require_value(replay, "evidence_boundary", "locked_replay"),
        },
        {
            "proof_id": "eia_residual_holm_holdout",
            "title": "EIA residual hybrid frozen holdout",
            "evidence_class": "source_conditioned_frozen_holdout",
            "attained_maturity_level": 3,
            "status": eia_residual["status"],
            "facts": {
                "holm_result": eia_residual["holm_result"],
                "full_protocol_gate": eia_residual["full_protocol_gate"],
                "coverage_result": eia_residual["coverage_result"],
                "selected_candidate": eia_residual["selected_candidate"],
                "holdout_rows": eia_residual["holdout_rows"],
                "holdout_authorities": eia_residual["holdout_authorities"],
                "authority_month_pairs": eia_residual["authority_month_pairs"],
                "holm_positive_comparison_count": eia_residual["holm_positive_comparison_count"],
                "holm_comparison_total": eia_residual["holm_comparison_total"],
                "holm_threshold": eia_residual["holm_threshold"],
                "all_internal_comparisons_holm_positive": eia_residual[
                    "all_internal_comparisons_holm_positive"
                ],
                "minimum_coverage_days": eia_residual["minimum_coverage_days"],
                "coverage_target_days": eia_residual["coverage_target_days"],
                "worst_authority": eia_residual["worst_authority"],
                "worst_baseline": eia_residual["worst_baseline"],
                "worst_authority_mean_skill": eia_residual["worst_authority_mean_skill"],
                "coverage_pass": eia_residual["coverage_pass"],
                "all_baseline_comparisons_pass": eia_residual[
                    "all_baseline_comparisons_pass"
                ],
                "protocol_grade_internal_champion": eia_residual[
                    "protocol_grade_internal_champion"
                ],
                "external_replication_complete": eia_residual[
                    "external_replication_complete"
                ],
                "field_validation_complete": eia_residual["field_validation_complete"],
                "dollar_conversion_allowed": eia_residual["dollar_conversion_allowed"],
                "benchmark_source_sha256": receipt_by_source["eia_residual_benchmark"]["sha256"],
                "protocol_source_sha256": receipt_by_source["eia_residual_protocol"]["sha256"],
            },
            "claim_boundary": eia_residual["claim_boundary"],
        },
        {
            "proof_id": "eia_prospective_router",
            "title": "Frozen EIA prospective router",
            "evidence_class": "prospective_protocol",
            "attained_maturity_level": 1,
            "target_maturity_level": 4,
            "status": require_value(eia, "state", "eia_prospective_router"),
            "facts": {
                "first_allowed_target_date": require_value(
                    eia,
                    "first_allowed_target_date",
                    "eia_prospective_router",
                ),
                "prediction_count": require_value(eia, "prediction_count", "eia_prospective_router"),
                "settlement_count": require_value(eia, "settlement_count", "eia_prospective_router"),
                "promotion_evaluation_complete": require_value(
                    eia,
                    "promotion_evaluation_complete",
                    "eia_prospective_router",
                ),
                "preliminary_30_days_ready": require_value(
                    eia_gates,
                    "preliminary_30_days_ready",
                    "eia_prospective_router.sample_gates",
                ),
                "confirmatory_90_days_ready": require_value(
                    eia_gates,
                    "confirmatory_90_days_ready",
                    "eia_prospective_router.sample_gates",
                ),
                "durability_180_days_ready": require_value(
                    eia_gates,
                    "durability_180_days_ready",
                    "eia_prospective_router.sample_gates",
                ),
            },
            "claim_boundary": require_value(eia, "claim_boundary", "eia_prospective_router"),
        },
        {
            "proof_id": "mda_synthetic_feasibility_v1",
            "title": "MDA mapping synthetic feasibility v1",
            "evidence_class": "frozen_synthetic_benchmark",
            "attained_maturity_level": 2,
            "status": "gate_failed_preserved",
            "facts": {
                "fixture_count": require_value(mda_v1_counts, "total", "mda_feasibility_v1.fixture_counts"),
                "candidate_micro_f1": require_value(
                    mda_v1_candidate,
                    "micro_f1",
                    "mda_feasibility_v1.candidate",
                ),
                "candidate_unsupported_mapping_rate": require_value(
                    mda_v1_candidate,
                    "unsupported_mapping_rate",
                    "mda_feasibility_v1.candidate",
                ),
                "micro_f1_delta_over_best_baseline": require_value(
                    mda_v1_gate,
                    "micro_f1_delta_over_best_baseline",
                    "mda_feasibility_v1.gate",
                ),
                "gate_passed": require_value(mda_v1_gate, "passed", "mda_feasibility_v1.gate"),
            },
            "claim_boundary": require_value(mda_v1, "claim_boundary", "mda_feasibility_v1"),
        },
        {
            "proof_id": "mda_open_set_v2",
            "title": "MDA mapping independent open-set v2",
            "evidence_class": "frozen_synthetic_benchmark",
            "attained_maturity_level": 2,
            "status": "safer_unsupported_behavior_but_gate_failed",
            "facts": {
                "fixture_count": require_value(mda_v2_counts, "total", "mda_open_set_v2.fixture_counts"),
                "candidate_micro_f1": require_value(
                    mda_v2_candidate,
                    "micro_f1",
                    "mda_open_set_v2.candidate",
                ),
                "supported_coverage": require_value(
                    mda_v2_candidate,
                    "supported_coverage",
                    "mda_open_set_v2.candidate",
                ),
                "unsupported_mapping_rate": require_value(
                    mda_v2_candidate,
                    "unsupported_mapping_rate",
                    "mda_open_set_v2.candidate",
                ),
                "micro_f1_delta_over_best_baseline": require_value(
                    mda_v2_gate,
                    "micro_f1_delta_over_best_baseline",
                    "mda_open_set_v2.gate",
                ),
                "gate_passed": require_value(mda_v2_gate, "passed", "mda_open_set_v2.gate"),
            },
            "claim_boundary": require_value(mda_v2, "claim_boundary", "mda_open_set_v2"),
        },
        {
            "proof_id": "faa_sdr_frozen_10k",
            "title": "FAA SDR frozen 10,000-report triage benchmark",
            "evidence_class": "source_conditioned_frozen_holdout",
            "attained_maturity_level": 3,
            "status": "completed_candidate_not_promoted",
            "facts": {
                "holdout_rows": require_value(faa_splits, "holdout_rows", "faa_sdr_10k.splits"),
                "holdout_unique_keys": require_value(
                    faa_splits,
                    "holdout_unique_keys",
                    "faa_sdr_10k.splits",
                ),
                "development_key_overlap": int(
                    require_value(faa_splits, "base_holdout_key_overlap", "faa_sdr_10k.splits")
                )
                + int(require_value(faa_splits, "router_holdout_key_overlap", "faa_sdr_10k.splits")),
                "scenario_model_evaluations": require_value(
                    faa_execution,
                    "scenario_model_evaluations",
                    "faa_sdr_10k.execution",
                ),
                "candidate_macro_f1": require_value(faa_candidate, "macro_f1", "faa_sdr_10k.candidate"),
                "strongest_baseline": faa_baseline_name,
                "strongest_baseline_macro_f1": require_value(
                    faa_baseline,
                    "macro_f1",
                    "faa_sdr_10k.strongest_baseline",
                ),
                "multiplicity_adjusted_primary_improvement": require_value(
                    faa_gate,
                    "multiplicity_adjusted_primary_improvement",
                    "faa_sdr_10k.promotion_gate",
                ),
                "candidate_promoted": require_value(
                    faa_gate,
                    "candidate_promoted",
                    "faa_sdr_10k.promotion_gate",
                ),
                "rolls_royce_exploratory_rows": require_value(
                    faa_rolls,
                    "rows",
                    "faa_sdr_10k.rolls_royce_exploratory",
                ),
                "receipt_sha256": require_value(faa, "receipt_sha256", "faa_sdr_10k"),
            },
            "claim_boundary": require_value(faa, "claim_boundary", "faa_sdr_10k"),
        },
        {
            "proof_id": "funding_reviewer_gate",
            "title": "Funding-package language and secret scan",
            "evidence_class": "review_packaging_control",
            "attained_maturity_level": 1,
            "status": "clear" if bool(reviewer.get("reviewer_gate_clear")) else "blocked",
            "facts": {
                "reviewer_gate_clear": require_value(reviewer, "reviewer_gate_clear", "reviewer_gate"),
                "markdown_file_count": require_value(
                    reviewer_summary,
                    "markdown_file_count",
                    "reviewer_gate.summary",
                ),
                "unsafe_claim_count": require_value(
                    reviewer_summary,
                    "unsafe_claim_count",
                    "reviewer_gate.summary",
                ),
                "unsafe_secret_count": require_value(
                    reviewer_summary,
                    "unsafe_secret_count",
                    "reviewer_gate.summary",
                ),
            },
            "claim_boundary": "A clear packaging scan means the scanned text passed configured claim and secret rules. It is not scientific, legal, agency, security, or funding approval.",
        },
    ]

    if private_universe is not None:
        proof_cards.insert(
            2,
            {
                "proof_id": "private_universe_zero_copy_custody",
                "title": "Private-universe zero-copy candidate custody federation",
                "evidence_class": "internal_custody_evidence",
                "attained_maturity_level": 1,
                "status": private_universe["status"],
                "facts": {
                    **private_universe,
                    "source_receipt_sha256": receipt_by_source[
                        "private_universe_receipt"
                    ]["sha256"],
                },
                "claim_boundary": (
                    "This zero-copy federation of existing manifests is internal custody and "
                    "discovery metadata. Candidate lane counts are filename, extension, and manifest-"
                    "metadata heuristics only, not content-validated classifications. It is not a "
                    "fresh full scan or live reconciliation and proves no current file existence, "
                    "completeness, ownership, build, field or performance validation, technical "
                    "readiness, valuation, or independent evaluation."
                ),
            },
        )

    universe_supported_statement = (
        "The optional private-universe receipt federates existing manifests and represents no fresh "
        "full universe scan, manifest-referenced file byte read, broad-root scan, archive extraction, "
        "or live reconciliation; only individually authorized explicit files may be read for SHA-256, "
        "and candidate lane counts remain metadata heuristics rather than content validation. The "
        "receipt names no independent evaluator."
        if private_universe is not None
        else "No private-universe receipt has been generated, so this context represents no fresh full universe scan or live reconciliation."
    )

    claim_controls = {
        "currently_supported": [
            "The repository contains implemented and tested evidence-building infrastructure.",
            "The locked sweep is a source-conditioned replay with named baselines, wins, and non-wins.",
            "The MDA v1 and v2 synthetic promotion gates failed and the negative results are preserved.",
            "The frozen FAA SDR 10,000-report benchmark completed and did not promote the hybrid candidate.",
            (
                "The local metadata intake identifies hardware and 3D design-prior candidates; "
                "it establishes no hardware build, field deployment, hardware degradation, or "
                "performance result, and it names no independent evaluator."
            ),
            (
                "The local system-health history audit preserves sparse one-second point observations "
                "and custody defects across 30/90/180-day windows; it is not hardware-degradation "
                "proof and names no independent evaluator."
            ),
            universe_supported_statement,
            (
                f"The development-selected EIA residual hybrid has {eia_residual['holm_result']} "
                f"on its frozen internal holdout, but the full protocol gate is "
                f"{eia_residual['full_protocol_gate']}."
            ),
            "The EIA prospective protocol is frozen and operational but has not produced an eligible prediction or settlement in this snapshot.",
            "A prior external proof packet reports all copied artifact hashes verified.",
        ],
        "blocked_without_new_evidence": {
            "level_5_or_independent_validation": True,
            "field_validation": not bool(replay_gates.get("field_validation_claim_allowed")),
            "realized_or_fixed_dollar_savings": not bool(
                replay_gates.get("real_dollar_savings_claim_allowed")
                or replay_gates.get("fixed_dollar_delta_sale_claim_allowed")
            ),
            "production_readiness": True,
            "government_or_regulatory_approval": True,
            "universal_model_superiority": True,
            "profitable_live_trading": True,
            "patent_validity_scope_or_infringement": True,
        },
    }

    context = {
        "schema": "quant_hub_reviewer_context.v1",
        "generated_utc": now_utc(),
        "identity": identity,
        "mission": "Make LumenCore reviewable through bounded claims, reproducible measurements, preserved failures, and explicit human authority.",
        "current_evidence_posture": {
            "highest_repository_wide_supported_level": require_value(
                maturity_policy,
                "current_repository_wide_level",
                "lexicon.level_policy",
            ),
            "level_5_attained": require_value(maturity_policy, "level_5_attained", "lexicon.level_policy"),
            "level_5_gate": require_value(maturity_policy, "level_5_gate", "lexicon.level_policy"),
            "summary": (
                "Level 3 source-conditioned replay and frozen EIA holdout evidence are supported. "
                f"The EIA residual candidate has {eia_residual['holm_result']}, but its full "
                f"protocol gate is {eia_residual['full_protocol_gate']}. Level 4 prospective "
                "evidence is still waiting for eligible EIA forecasts and settlements. Level 5 "
                "independent external validation has not been attained."
            ),
        },
        "proof_cards": proof_cards,
        "optional_source_status": {
            "private_universe_receipt": (
                "available" if private_universe is not None else "not_generated"
            )
        },
        "claim_controls": claim_controls,
        "human_authority_policy": human_policy,
        "reviewer_decision_map": [
            {
                "decision": "Verify custody",
                "evidence": "Rehash the prior packet artifacts against its manifest and compare the source receipt in this context.",
                "remaining_gate": "Independent re-verification of the final packet after this context is staged.",
            },
            {
                "decision": "Assess quantitative evidence",
                "evidence": "Inspect the locked replay ledger, route-level baselines, wins, non-wins, and replay chain.",
                "remaining_gate": "Independent held-out data and an externally accepted metric.",
            },
            {
                "decision": "Assess falsification discipline",
                "evidence": "Review the preserved MDA v1 and v2 failed promotion gates and abstention behavior.",
                "remaining_gate": "An authoritative external corpus and independent evaluation owner.",
            },
            {
                "decision": "Assess prospective readiness",
                "evidence": (
                    "Inspect the frozen EIA residual holdout, its Holm-adjusted internal comparisons, "
                    "the closed composite gate, the prospective protocol, scheduler receipts, and "
                    "zero-count waiting state."
                ),
                "remaining_gate": (
                    f"Raise minimum common holdout coverage from {eia_residual['minimum_coverage_days']} "
                    f"to {eia_residual['coverage_target_days']} days without post-holdout tuning, "
                    "satisfy the authority robustness gate, then complete the 30-, 90-, and 180-day "
                    "prospective settlement gates."
                ),
            },
            {
                "decision": "Assess economic relevance",
                "evidence": "Use only technical deltas that an external owner accepts under a named operating metric.",
                "remaining_gate": "Buyer-owned assumptions, measurement period, counterfactual, and signed result receipt.",
            },
            {
                "decision": "Assess intellectual-property support",
                "evidence": "Counsel must use the official filed claims and specification plus dated, access-controlled evidence.",
                "remaining_gate": "Attorney-controlled claim chart; this public context contains no private patent-vault content.",
            },
        ],
        "next_validation_actions": [
            {
                "priority": 1,
                "action": "Keep the frozen EIA prospective router running without changing its promotion protocol.",
                "success_receipt": "Hashed predictions, settlements, and preregistered 30/90/180-day gate outputs.",
            },
            {
                "priority": 2,
                "action": "Secure one independent evaluator with held-out operational data and a pre-agreed metric.",
                "success_receipt": "Named evaluator, data boundary, protocol, acceptance metric, date, and signed or attributable result.",
            },
            {
                "priority": 3,
                "action": "Run MDA mapping only against an authoritative external corpus under a new preregistration.",
                "success_receipt": "Frozen external corpus hash, split, baselines, abstention policy, and independent score receipt.",
            },
            {
                "priority": 4,
                "action": "Translate technical deltas into economics only with a named buyer-side owner and bounded assumptions.",
                "success_receipt": "Accepted counterfactual, unit economics, sensitivity range, and no realized-savings language before measurement.",
            },
            {
                "priority": 5,
                "action": "Have patent counsel compare official filed claims with the filed specification and later dated concepts.",
                "success_receipt": "Counsel-controlled claim chart and a decision on amendment, continuation, continuation-in-part, or separate filing strategy.",
            },
        ],
        "patent_boundary": require_value(lexicon, "patent_boundary", "lexicon"),
        "public_private_boundary": require_value(lexicon, "public_private_boundary", "lexicon"),
        "known_limitations": [
            "Repeated route comparisons are not automatically statistically independent experiments.",
            "Source-conditioned replay does not equal a prospective field trial.",
            "A benchmark champion is conditional on its dataset, split, metric, baseline set, and run.",
            "Holm-positive internal comparisons do not override a failed coverage, authority-robustness, external-replication, field, or dollar gate.",
            "Estimated economic value surfaces are prioritization aids, not realized savings or valuation evidence.",
            "A clear reviewer-language scan does not imply scientific, legal, security, agency, or funding approval.",
            "Hardware and 3D design-prior metadata does not establish that a device was built, fielded, or performance-tested.",
            "Sparse one-second system-health point samples do not establish sustained utilization, hardware degradation, root cause, or prevented failure.",
        ],
        "reproducibility_entrypoints": [
            "code/ops/BUILD_QUANT_HUB_REVIEWER_CONTEXT.py",
            "code/ops/BUILD_LOCKED_SOURCE_BASELINE_REPLAY_SWEEP.py",
            "code/eia_grid_residual_moe_benchmark.py",
            "code/eia_grid_prospective_router_ops.py",
            "code/mda_control_mapping_feasibility.py",
            "code/mda_control_mapping_open_set_benchmark.py",
            "code/ops/STAGE_EXTERNAL_PROOF_VAULT.py",
            "tests/test_quant_hub_reviewer_context.py",
            "tests/test_locked_source_baseline_replay_sweep.py",
            "tests/test_eia_grid_residual_moe_benchmark.py",
            "tests/test_eia_grid_prospective_router_ops.py",
            "tests/test_mda_control_mapping_feasibility.py",
            "tests/test_mda_control_mapping_open_set_benchmark.py",
            "tests/test_external_proof_vault.py",
        ],
        "source_artifacts": receipts,
        "source_input_chain_sha256": input_chain_sha256,
        "outputs": {
            "machine_readable": repo_path(OUT_JSON),
            "dashboard_mirror": repo_path(DASHBOARD_JSON),
            "reviewer_markdown": repo_path(OUT_MD),
        },
    }
    assert_public_safe(context)
    return context


def render_markdown(context: dict[str, Any]) -> str:
    posture = require_dict(context, "current_evidence_posture", "context")
    lines = [
        "# Quant Hub Reviewer Context",
        "",
        f"Generated UTC: `{context['generated_utc']}`",
        "",
        "## Identity",
        "",
        f"- Repository: `{context['identity']['repository_display_name']}`",
        f"- Technical platform: `{context['identity']['technical_platform']}`",
        f"- Quantitative lane: `{context['identity']['quantitative_evidence_lane']}`",
        f"- Orchestration layer: `{context['identity']['orchestration_context_layer']}`",
        f"- Custody layer: `{context['identity']['proof_custody_layer']}`",
        f"- External gate: `{context['identity']['external_validation_gate']}`",
        "",
        "## Current Evidence Posture",
        "",
        f"- Highest repository-wide supported maturity: `Level {posture['highest_repository_wide_supported_level']}`",
        f"- Level 5 attained: `{str(posture['level_5_attained']).lower()}`",
        f"- Summary: {posture['summary']}",
        "",
        "Maturity is claim-specific. It is not a product-readiness, agency-approval, patent, security, or valuation grade.",
        "",
        "## Evidence Cards",
        "",
        "| Evidence | Class | Level | Status | Selected facts |",
        "|---|---|---:|---|---|",
    ]
    for card in context["proof_cards"]:
        selected = ", ".join(f"{key}={value}" for key, value in list(card["facts"].items())[:5])
        lines.append(
            f"| {card['title']} | `{card['evidence_class']}` | {card['attained_maturity_level']} | "
            f"`{card['status']}` | {selected} |"
        )

    lines.extend(
        [
            "",
            "## Supported Statements",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in context["claim_controls"]["currently_supported"])
    lines.extend(["", "## Blocked Claims", ""])
    for claim, blocked in context["claim_controls"]["blocked_without_new_evidence"].items():
        lines.append(f"- `{claim}`: `{'blocked' if blocked else 'not blocked'}`")

    lines.extend(["", "## Reviewer Decision Path", ""])
    for row in context["reviewer_decision_map"]:
        lines.append(f"### {row['decision']}")
        lines.append("")
        lines.append(f"Evidence: {row['evidence']}")
        lines.append("")
        lines.append(f"Remaining gate: {row['remaining_gate']}")
        lines.append("")

    lines.extend(["## Next Validation Actions", ""])
    for row in context["next_validation_actions"]:
        lines.append(f"{row['priority']}. {row['action']}")
        lines.append(f"   Required receipt: {row['success_receipt']}")

    lines.extend(
        [
            "",
            "## Human Authority",
            "",
        ]
    )
    for action, allowed in context["human_authority_policy"].items():
        lines.append(f"- `{action}`: `{str(allowed).lower()}`")

    lines.extend(
        [
            "",
            "## Patent And Privacy Boundary",
            "",
            context["patent_boundary"],
            "",
            context["public_private_boundary"],
            "",
            "## Source Chain",
            "",
            f"Input chain SHA-256: `{context['source_input_chain_sha256']}`",
            "",
        ]
    )
    for row in context["source_artifacts"]:
        lines.append(f"- `{row['path']}` | `{row['sha256']}` | `{row['bytes']}` bytes")
    return "\n".join(lines).rstrip() + "\n"


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_outputs(
    context: dict[str, Any],
    *,
    output_json: Path = OUT_JSON,
    dashboard_json: Path = DASHBOARD_JSON,
    output_markdown: Path = OUT_MD,
) -> None:
    assert_public_safe(context)
    write_json(output_json, context)
    write_json(dashboard_json, context)
    output_markdown.parent.mkdir(parents=True, exist_ok=True)
    output_markdown.write_text(render_markdown(context), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the public-safe Quant Hub reviewer context.")
    parser.add_argument("--check", action="store_true", help="Validate and print the context without writing outputs.")
    args = parser.parse_args()
    context = build_context()
    if not args.check:
        write_outputs(context)
    print(
        json.dumps(
            {
                "schema": context["schema"],
                "highest_supported_level": context["current_evidence_posture"][
                    "highest_repository_wide_supported_level"
                ],
                "level_5_attained": context["current_evidence_posture"]["level_5_attained"],
                "proof_card_count": len(context["proof_cards"]),
                "source_input_chain_sha256": context["source_input_chain_sha256"],
                "written": not args.check,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
