#!/usr/bin/env python3
"""Verify a frozen EIA hourly reproduction packet and reviewer receipt offline."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from statistics import mean
from typing import Any


ZERO_HASH = "0" * 64
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
MANIFEST_NAME = "PACKET_MANIFEST.json"
RECEIPT_NAME = "REVIEWER_RECEIPT_TEMPLATE.json"
EVALUATOR_PROTOCOL_RELATIVE = Path(
    "config/eia_grid_hourly_external_evaluator_protocol_template_v1.json"
)
PROTOCOL_RELATIVE = Path(
    "config/eia_grid_prospective_hourly_router_protocol_v1.json"
)
SOURCE_CACHE_RELATIVE = Path(
    "runtime/source_panel_cache.json"
)
PREDICTIONS_RELATIVE = Path("runtime/sealed_predictions.jsonl")
SETTLEMENTS_RELATIVE = Path("runtime/settlements.jsonl")
OPERATIONS_RELATIVE = Path("runtime/operational_runs.jsonl")
STATUS_RELATIVE = Path("runtime/prospective_status_latest.json")
CYCLE_RELATIVE = Path("runtime/latest_cycle.json")
EXPECTED_MANIFEST_SCHEMA = "eia_grid_hourly_reproduction_packet_manifest.v1"
EXPECTED_RECEIPT_SCHEMA = "eia_grid_hourly_independent_reproduction_receipt.v1"
EXPECTED_EVALUATOR_PROTOCOL_SCHEMA = "eia_grid_hourly_external_evaluator_protocol.v1"

REVIEWER_FIELDS = (
    "name",
    "organization",
    "technical_role",
    "contact_channel",
    "conflict_of_interest_disclosure",
    "independence_basis",
    "independence_evidence_sha256",
)
REPRODUCTION_FIELDS = (
    "executed_utc",
    "decision",
    "environment_summary",
    "packet_rehashed",
    "packet_hashes_match",
    "source_cache_chain_verified",
    "prediction_chain_verified",
    "settlement_chain_verified",
    "operational_chain_verified",
    "settlement_metrics_recomputed",
    "authority_coverage_recomputed",
    "prediction_count",
    "settlement_count",
    "common_settled_hour_count",
    "zero_prospective_seal_authorities",
    "prediction_terminal_sha256",
    "settlement_terminal_sha256",
    "operational_terminal_sha256",
    "notes",
    "operator_filled_reviewer_fields",
)
SIGNATURE_FIELDS = (
    "method",
    "signed_payload_sha256",
    "detached_signature_artifact_sha256",
)
ALLOWED_DECISIONS = {
    "REPRODUCED_FROZEN_SNAPSHOT",
    "DID_NOT_REPRODUCE",
}
ALLOWED_SIGNATURE_METHODS = {
    "third_party_esign",
    "signed_pdf",
    "signed_email",
    "other_reviewer_controlled",
}
EVALUATOR_FIELDS = (
    "name",
    "organization",
    "technical_role",
    "contact_channel",
    "conflict_of_interest_disclosure",
    "independence_basis",
    "authority_to_accept_protocol",
    "independence_evidence_sha256",
)
EVALUATOR_DATA_FIELDS = (
    "publisher_or_owner",
    "dataset_description",
    "dataset_or_query_manifest_sha256",
    "custody_owner",
    "access_authority",
    "held_out_from_lumencore_before_freeze",
    "observation_availability_rule",
    "target_release_timing_rule",
    "evaluation_start_utc",
    "evaluation_end_utc",
    "registered_authorities",
    "authority_inclusion_rule",
    "missing_data_rule",
    "revision_policy",
)
EVALUATOR_TEST_FIELDS = (
    "candidate_definition",
    "incumbent_baseline_id",
    "incumbent_baseline_definition",
    "primary_metric",
    "metric_direction",
    "minimum_common_hours_per_authority",
    "minimum_effect_size",
    "bootstrap_replications",
    "bootstrap_seed",
    "secondary_metrics",
    "single_authority_regression_limit",
    "minimum_authority_mean_wins",
    "minimum_utc_day_win_rate",
)
EVALUATOR_FREEZE_FIELDS = (
    "accepted_utc",
    "accepted_protocol_payload_sha256",
    "signature_method",
    "signed_payload_sha256",
    "detached_signature_artifact_sha256",
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    )


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_text_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def require_nonnegative_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def require_finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    output = float(value)
    if not math.isfinite(output):
        raise ValueError(f"{label} must be finite")
    return output


def parse_aware_datetime(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{label} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{label} must be timezone-aware")
    return parsed


def parse_hour_ending(value: Any, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a UTC hour-ending string")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise ValueError(f"{label} must use YYYY-MM-DDTHH") from exc


def close(left: Any, right: Any, label: str, tolerance: float = 1e-9) -> None:
    observed = require_finite_number(left, f"{label}.observed")
    expected = require_finite_number(right, f"{label}.expected")
    if not math.isclose(observed, expected, rel_tol=0.0, abs_tol=tolerance):
        raise ValueError(f"{label} mismatch: observed={observed} expected={expected}")


def read_chain(path: Path) -> tuple[list[dict[str, Any]], str]:
    records: list[dict[str, Any]] = []
    previous = ZERO_HASH
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"non-object chain record at {path}:{line_number}")
            observed = value.get("record_sha256")
            require_sha256(observed, f"{path.name}:{line_number}.record_sha256")
            unsigned = dict(value)
            unsigned.pop("record_sha256", None)
            if value.get("prior_record_chain_sha256") != previous:
                raise ValueError(f"broken prior hash at {path}:{line_number}")
            if observed != canonical_sha256(unsigned):
                raise ValueError(f"record hash mismatch at {path}:{line_number}")
            records.append(value)
            previous = str(observed)
    return records, previous


def validate_source_cache(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("schema") != "eia_grid_hourly_source_cache.v1":
        raise ValueError("unexpected source-cache schema")
    rows = payload.get("rows")
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("source cache rows must be an array of objects")
    if require_nonnegative_int(payload.get("row_count"), "source.row_count") != len(rows):
        raise ValueError("source cache row count does not reconcile")
    if require_sha256(payload.get("row_chain_sha256"), "source.row_chain_sha256") != canonical_sha256(rows):
        raise ValueError("source cache row chain does not reconcile")
    identities: set[tuple[str, str, str]] = set()
    counts: dict[str, dict[str, int]] = {}
    for index, row in enumerate(rows):
        respondent = str(row.get("respondent") or "")
        period = str(row.get("period") or "")
        kind = str(row.get("type") or "")
        parse_hour_ending(period, f"source.rows[{index}].period")
        require_finite_number(row.get("value"), f"source.rows[{index}].value")
        identity = (respondent, period, kind)
        if identity in identities:
            raise ValueError(f"duplicate source row: {identity}")
        identities.add(identity)
        counts.setdefault(respondent, {}).setdefault(kind, 0)
        counts[respondent][kind] += 1
    return {
        "row_count": len(rows),
        "row_chain_sha256": payload["row_chain_sha256"],
        "rows_by_authority_and_type": {
            authority: dict(sorted(values.items()))
            for authority, values in sorted(counts.items())
        },
    }


def validate_predictions(
    records: list[dict[str, Any]],
    protocol: dict[str, Any],
    protocol_sha256: str,
) -> dict[str, Any]:
    authorities = list(protocol["balancing_authorities"])
    authority_set = set(authorities)
    candidate_ids = [row["id"] for row in protocol["candidates"]]
    route_map = protocol["router"]["route_map"]
    first_allowed = protocol["prospective_window"]["first_allowed_period_end_utc"]
    seen: set[tuple[str, str]] = set()
    counts = {authority: 0 for authority in authorities}
    periods = {authority: [] for authority in authorities}
    for index, record in enumerate(records):
        label = f"predictions[{index}]"
        if record.get("schema") != "eia_grid_prospective_hourly_router_prediction.v1":
            raise ValueError(f"{label} has unexpected schema")
        authority = record.get("respondent")
        target = record.get("target_period_end_utc")
        if authority not in authority_set:
            raise ValueError(f"{label} has undeclared authority")
        target_end = parse_hour_ending(target, f"{label}.target_period_end_utc")
        if str(target) < first_allowed:
            raise ValueError(f"{label} predates the frozen prospective window")
        identity = (str(authority), str(target))
        if identity in seen:
            raise ValueError(f"duplicate sealed prediction: {identity}")
        seen.add(identity)
        sealed = parse_aware_datetime(record.get("sealed_utc"), f"{label}.sealed_utc")
        interval_start = parse_aware_datetime(
            record.get("target_interval_start_utc"),
            f"{label}.target_interval_start_utc",
        )
        expected_start = target_end.replace(tzinfo=timezone.utc).timestamp() - 3600.0
        close(interval_start.timestamp(), expected_start, f"{label}.interval_start")
        if not sealed < interval_start:
            raise ValueError(f"{label} was not sealed before the target interval")
        close(
            record.get("seal_lead_seconds"),
            (interval_start - sealed).total_seconds(),
            f"{label}.seal_lead_seconds",
            tolerance=1e-6,
        )
        if record.get("backfilled") is not False:
            raise ValueError(f"{label} backfill flag must be false")
        if record.get("target_actual_present_at_seal") is not False:
            raise ValueError(f"{label} target actual was present at seal")
        if record.get("protocol_sha256") != protocol_sha256:
            raise ValueError(f"{label} protocol hash mismatch")
        commit = record.get("protocol_commit")
        if not isinstance(commit, str) or not COMMIT_PATTERN.fullmatch(commit):
            raise ValueError(f"{label} protocol commit is invalid")
        if record.get("selected_candidate") != route_map[authority]:
            raise ValueError(f"{label} violates the frozen route map")
        candidates = record.get("candidate_predictions_mwh")
        if not isinstance(candidates, dict) or sorted(candidates) != sorted(candidate_ids):
            raise ValueError(f"{label} candidate set does not match the protocol")
        for candidate, value in candidates.items():
            require_finite_number(value, f"{label}.candidate_predictions_mwh.{candidate}")
        selected = record["selected_candidate"]
        close(
            record.get("router_prediction_mwh"),
            candidates[selected],
            f"{label}.router_prediction_mwh",
            tolerance=1e-8,
        )
        if require_finite_number(record.get("scale_mwh"), f"{label}.scale_mwh") <= 0.0:
            raise ValueError(f"{label} scale must be positive")
        for key in (
            "source_receipt_sha256",
            "source_panel_row_chain_sha256",
            "feature_sha256",
            "training_rows_sha256",
        ):
            require_sha256(record.get(key), f"{label}.{key}")
        counts[str(authority)] += 1
        periods[str(authority)].append(str(target))
    return {
        "prediction_count": len(records),
        "prediction_counts_by_authority": counts,
        "first_prediction_period_by_authority": {
            authority: min(values) if values else None
            for authority, values in periods.items()
        },
        "latest_prediction_period_by_authority": {
            authority: max(values) if values else None
            for authority, values in periods.items()
        },
        "zero_prospective_seal_authorities": sorted(
            authority for authority, count in counts.items() if count == 0
        ),
    }


def validate_settlements(
    settlements: list[dict[str, Any]],
    predictions: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    prediction_by_hash = {row["record_sha256"]: row for row in predictions}
    if len(prediction_by_hash) != len(predictions):
        raise ValueError("prediction record hashes are not unique")
    candidate_ids = [row["id"] for row in protocol["candidates"]]
    counts = {authority: 0 for authority in protocol["balancing_authorities"]}
    periods = {authority: set() for authority in protocol["balancing_authorities"]}
    seen: set[tuple[str, str, str]] = set()
    for index, record in enumerate(settlements):
        label = f"settlements[{index}]"
        if record.get("schema") != "eia_grid_prospective_hourly_router_settlement.v1":
            raise ValueError(f"{label} has unexpected schema")
        prediction_hash = record.get("prediction_record_sha256")
        if prediction_hash not in prediction_by_hash:
            raise ValueError(f"{label} references a prediction outside the verified chain")
        prediction = prediction_by_hash[prediction_hash]
        authority = record.get("respondent")
        target = record.get("target_period_end_utc")
        if authority != prediction.get("respondent") or target != prediction.get(
            "target_period_end_utc"
        ):
            raise ValueError(f"{label} identity does not match its prediction")
        identity = (str(authority), str(target), str(prediction_hash))
        if identity in seen:
            raise ValueError(f"duplicate settlement: {identity}")
        seen.add(identity)
        parse_aware_datetime(record.get("settled_utc"), f"{label}.settled_utc")
        actual = require_finite_number(record.get("actual_mwh"), f"{label}.actual_mwh")
        scale = require_finite_number(prediction.get("scale_mwh"), f"{label}.scale_mwh")
        metrics = record.get("candidate_metrics")
        if not isinstance(metrics, dict) or sorted(metrics) != sorted(candidate_ids):
            raise ValueError(f"{label} candidate metric set does not match the protocol")
        expected_scaled: dict[str, float] = {}
        for candidate in candidate_ids:
            candidate_metrics = metrics.get(candidate)
            if not isinstance(candidate_metrics, dict):
                raise ValueError(f"{label}.{candidate} metrics must be an object")
            predicted = require_finite_number(
                prediction["candidate_predictions_mwh"][candidate],
                f"{label}.{candidate}.prediction",
            )
            absolute_error = abs(predicted - actual)
            scaled_error = absolute_error / scale
            close(
                candidate_metrics.get("absolute_error_mwh"),
                absolute_error,
                f"{label}.{candidate}.absolute_error_mwh",
                tolerance=1e-7,
            )
            close(
                candidate_metrics.get("scaled_absolute_error"),
                scaled_error,
                f"{label}.{candidate}.scaled_absolute_error",
                tolerance=1e-10,
            )
            expected_scaled[candidate] = scaled_error
        selected = prediction["selected_candidate"]
        if record.get("selected_candidate") != selected:
            raise ValueError(f"{label} selected candidate changed after seal")
        oracle = min(candidate_ids, key=lambda name: (expected_scaled[name], name))
        if record.get("oracle_candidate") != oracle:
            raise ValueError(f"{label} oracle candidate does not recompute")
        close(
            record.get("router_scaled_absolute_error"),
            expected_scaled[selected],
            f"{label}.router_scaled_absolute_error",
            tolerance=1e-10,
        )
        close(
            record.get("oracle_scaled_absolute_error"),
            expected_scaled[oracle],
            f"{label}.oracle_scaled_absolute_error",
            tolerance=1e-10,
        )
        close(
            record.get("router_regret_to_oracle"),
            expected_scaled[selected] - expected_scaled[oracle],
            f"{label}.router_regret_to_oracle",
            tolerance=1e-10,
        )
        if record.get("route_hit") is not (selected == oracle):
            raise ValueError(f"{label} route-hit flag does not recompute")
        counts[str(authority)] += 1
        periods[str(authority)].add(str(target))
    common = sorted(set.intersection(*(periods[key] for key in periods))) if periods else []
    return {
        "settlement_count": len(settlements),
        "settlement_counts_by_authority": counts,
        "common_settled_hour_count": len(common),
        "first_common_settled_period": common[0] if common else None,
        "latest_common_settled_period": common[-1] if common else None,
        "settlement_metrics_recomputed": True,
    }


def recompute_status(
    protocol: dict[str, Any],
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
    status: dict[str, Any],
    protocol_sha256: str,
) -> dict[str, Any]:
    if status.get("schema") != "eia_grid_prospective_hourly_router_status.v1":
        raise ValueError("unexpected status schema")
    if status.get("protocol_sha256") != protocol_sha256:
        raise ValueError("status protocol hash mismatch")
    candidates = [row["id"] for row in protocol["candidates"]]
    candidate_means = {
        candidate: (
            mean(
                float(row["candidate_metrics"][candidate]["scaled_absolute_error"])
                for row in settlements
            )
            if settlements
            else None
        )
        for candidate in candidates
    }
    available = {key: value for key, value in candidate_means.items() if value is not None}
    best_fixed = min(available, key=lambda key: (available[key], key)) if available else None
    router_mean = (
        mean(float(row["router_scaled_absolute_error"]) for row in settlements)
        if settlements
        else None
    )
    settled_periods = {
        authority: {
            row["target_period_end_utc"]
            for row in settlements
            if row["respondent"] == authority
        }
        for authority in protocol["balancing_authorities"]
    }
    common = sorted(set.intersection(*(settled_periods[key] for key in settled_periods)))
    if status.get("prediction_count") != len(predictions):
        raise ValueError("status prediction count does not reconcile")
    if status.get("settlement_count") != len(settlements):
        raise ValueError("status settlement count does not reconcile")
    if status.get("common_settled_hour_count") != len(common):
        raise ValueError("status common-hour count does not reconcile")
    if status.get("first_common_settled_period") != (common[0] if common else None):
        raise ValueError("status first common period does not reconcile")
    if status.get("latest_common_settled_period") != (common[-1] if common else None):
        raise ValueError("status latest common period does not reconcile")
    if status.get("current_best_fixed_candidate") != best_fixed:
        raise ValueError("status best fixed candidate does not recompute")
    observed_means = status.get("fixed_candidate_mean_scaled_absolute_error")
    if not isinstance(observed_means, dict) or sorted(observed_means) != sorted(candidates):
        raise ValueError("status fixed-candidate table is incomplete")
    for candidate in candidates:
        if candidate_means[candidate] is None:
            if observed_means[candidate] is not None:
                raise ValueError(f"status {candidate} mean should be null")
        else:
            close(
                observed_means[candidate],
                candidate_means[candidate],
                f"status.{candidate}.mean",
                tolerance=1e-12,
            )
    if router_mean is None:
        if status.get("router_mean_scaled_absolute_error") is not None:
            raise ValueError("status router mean should be null")
    else:
        close(
            status.get("router_mean_scaled_absolute_error"),
            router_mean,
            "status.router_mean_scaled_absolute_error",
            tolerance=1e-12,
        )
        close(
            status.get("router_skill_vs_current_best_fixed"),
            float(available[best_fixed]) - router_mean,
            "status.router_skill_vs_current_best_fixed",
            tolerance=1e-12,
        )
    windows = protocol["prospective_window"]
    gates = status.get("sample_gates")
    if not isinstance(gates, dict):
        raise ValueError("status sample gates are missing")
    gate_pairs = (
        ("preliminary_ready", "preliminary_gate_common_hours_per_authority"),
        ("confirmatory_ready", "confirmatory_gate_common_hours_per_authority"),
        ("durability_ready", "durability_gate_common_hours_per_authority"),
    )
    for gate, threshold in gate_pairs:
        expected = len(common) >= int(windows[threshold])
        if gates.get(gate) is not expected:
            raise ValueError(f"status {gate} does not reconcile")
    if status.get("promotion_evaluation_complete") is not False:
        raise ValueError("promotion evaluation must remain incomplete")
    return {
        "current_best_fixed_candidate": best_fixed,
        "router_mean_scaled_absolute_error": router_mean,
        "router_skill_vs_current_best_fixed": (
            float(available[best_fixed]) - router_mean
            if best_fixed is not None and router_mean is not None
            else None
        ),
        "sample_gates": {
            gate: bool(gates[gate]) for gate, _ in gate_pairs
        },
    }


def audit_snapshot(packet_root: Path) -> dict[str, Any]:
    protocol_path = packet_root / PROTOCOL_RELATIVE
    protocol = read_json(protocol_path)
    if protocol.get("schema") != "eia_grid_prospective_hourly_router_protocol.v1":
        raise ValueError("unexpected protocol schema")
    authorities = list(protocol.get("balancing_authorities") or [])
    if not authorities or len(authorities) != len(set(authorities)):
        raise ValueError("protocol authorities must be non-empty and unique")
    if sorted(authorities) != sorted((protocol.get("router") or {}).get("route_map") or {}):
        raise ValueError("protocol route map does not cover every authority")
    if protocol["router"].get("dynamic_override_allowed") is not False:
        raise ValueError("dynamic route overrides must remain disabled")
    if protocol["prospective_window"].get("backfilled_predictions_allowed") is not False:
        raise ValueError("backfilled predictions must remain disabled")
    protocol_hash = normalized_text_sha256(protocol_path)

    source = read_json(packet_root / SOURCE_CACHE_RELATIVE)
    source_summary = validate_source_cache(source)
    predictions, prediction_terminal = read_chain(packet_root / PREDICTIONS_RELATIVE)
    settlements, settlement_terminal = read_chain(packet_root / SETTLEMENTS_RELATIVE)
    operations, operational_terminal = read_chain(packet_root / OPERATIONS_RELATIVE)
    if not operations:
        raise ValueError("operational receipt chain is empty")
    prediction_summary = validate_predictions(predictions, protocol, protocol_hash)
    settlement_summary = validate_settlements(settlements, predictions, protocol)
    status = read_json(packet_root / STATUS_RELATIVE)
    status_summary = recompute_status(
        protocol,
        predictions,
        settlements,
        status,
        protocol_hash,
    )
    latest = operations[-1]
    if latest.get("schema") != "eia_grid_prospective_hourly_router_operational_run.v1":
        raise ValueError("unexpected operational receipt schema")
    expected_receipt_values = {
        "protocol_sha256": protocol_hash,
        "source_panel_row_count": source_summary["row_count"],
        "source_panel_row_chain_sha256": source_summary["row_chain_sha256"],
        "prediction_count": len(predictions),
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_count": len(settlements),
        "settlement_terminal_sha256": settlement_terminal,
    }
    for key, expected in expected_receipt_values.items():
        if latest.get(key) != expected:
            raise ValueError(f"latest operational receipt {key} does not reconcile")
    status_for_receipt = dict(status)
    if status_for_receipt.pop("operational_receipt_sha256", None) != latest["record_sha256"]:
        raise ValueError("status does not bind the latest operational receipt")
    if latest.get("status_sha256") != canonical_sha256(status_for_receipt):
        raise ValueError("latest operational receipt status hash does not reconcile")
    cycle = read_json(packet_root / CYCLE_RELATIVE)
    if cycle.get("schema") != "eia_grid_prospective_hourly_router_cycle.v1":
        raise ValueError("unexpected latest-cycle schema")
    if cycle.get("status") != status:
        raise ValueError("latest-cycle status does not match the status snapshot")
    if cycle.get("operational_receipt") != latest:
        raise ValueError("latest cycle does not contain the terminal operational receipt")

    coverage = {}
    source_counts = source_summary["rows_by_authority_and_type"]
    for authority in authorities:
        coverage[authority] = {
            "source_actual_row_count": int(source_counts.get(authority, {}).get("D", 0)),
            "source_forecast_row_count": int(source_counts.get(authority, {}).get("DF", 0)),
            "prediction_count": prediction_summary["prediction_counts_by_authority"][authority],
            "settlement_count": settlement_summary["settlement_counts_by_authority"][authority],
            "first_prediction_period": prediction_summary[
                "first_prediction_period_by_authority"
            ][authority],
            "latest_prediction_period": prediction_summary[
                "latest_prediction_period_by_authority"
            ][authority],
        }
    zero_seals = prediction_summary["zero_prospective_seal_authorities"]
    return {
        "schema": "eia_grid_hourly_reproduction_snapshot_audit.v1",
        "integrity_gate_passed": True,
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": protocol_hash,
        "protocol_commit": latest.get("protocol_commit"),
        "source_panel_row_count": source_summary["row_count"],
        "source_panel_row_chain_sha256": source_summary["row_chain_sha256"],
        "prediction_count": len(predictions),
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_count": len(settlements),
        "settlement_terminal_sha256": settlement_terminal,
        "operational_receipt_count": len(operations),
        "operational_terminal_sha256": operational_terminal,
        "common_settled_hour_count": settlement_summary[
            "common_settled_hour_count"
        ],
        "first_common_settled_period": settlement_summary[
            "first_common_settled_period"
        ],
        "latest_common_settled_period": settlement_summary[
            "latest_common_settled_period"
        ],
        "zero_prospective_seal_authorities": zero_seals,
        "all_protocol_authorities_have_prospective_seals": not zero_seals,
        "frozen_panel_feasibility_status": (
            "ALL_AUTHORITIES_HAVE_PROSPECTIVE_SEALS"
            if not zero_seals
            else "INCOMPLETE_AUTHORITY_PANEL_ZERO_PROSPECTIVE_SEALS"
        ),
        "authority_coverage": coverage,
        "settlement_metrics_recomputed": settlement_summary[
            "settlement_metrics_recomputed"
        ],
        "current_best_fixed_candidate": status_summary[
            "current_best_fixed_candidate"
        ],
        "router_mean_scaled_absolute_error": status_summary[
            "router_mean_scaled_absolute_error"
        ],
        "router_skill_vs_current_best_fixed": status_summary[
            "router_skill_vs_current_best_fixed"
        ],
        "sample_gates": status_summary["sample_gates"],
        "performance_promotion_allowed": False,
        "independent_reproduction_complete": False,
        "claim_boundary": protocol["claim_boundary"],
    }


def manifest_signing_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(manifest)
    payload["manifest_payload_sha256"] = None
    return payload


def manifest_payload_sha256(manifest: dict[str, Any]) -> str:
    return canonical_sha256(manifest_signing_payload(manifest))


def validate_relative_artifact_path(value: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"unsafe packet artifact path: {value}")
    return path


def verify_packet(packet_root: Path) -> dict[str, Any]:
    manifest_path = packet_root / MANIFEST_NAME
    manifest = read_json(manifest_path)
    if manifest.get("schema") != EXPECTED_MANIFEST_SCHEMA:
        raise ValueError("unexpected packet manifest schema")
    expected_payload_hash = require_sha256(
        manifest.get("manifest_payload_sha256"),
        "manifest.manifest_payload_sha256",
    )
    if expected_payload_hash != manifest_payload_sha256(manifest):
        raise ValueError("packet manifest payload hash mismatch")
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise ValueError("packet manifest artifacts must be non-empty")
    observed_paths: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            raise ValueError(f"manifest artifact {index} must be an object")
        relative = str(artifact.get("path") or "")
        validate_relative_artifact_path(relative)
        if relative in observed_paths:
            raise ValueError(f"duplicate packet artifact path: {relative}")
        observed_paths.add(relative)
        path = packet_root / Path(relative)
        if not path.is_file():
            raise ValueError(f"missing packet artifact: {relative}")
        if require_nonnegative_int(artifact.get("bytes"), f"artifact[{index}].bytes") != path.stat().st_size:
            raise ValueError(f"packet artifact byte count mismatch: {relative}")
        if require_sha256(artifact.get("sha256"), f"artifact[{index}].sha256") != file_sha256(path):
            raise ValueError(f"packet artifact hash mismatch: {relative}")
    snapshot = audit_snapshot(packet_root)
    if manifest.get("frozen_snapshot") != snapshot:
        raise ValueError("packet manifest frozen snapshot does not recompute")
    return {
        "schema": "eia_grid_hourly_reproduction_packet_verification.v1",
        "packet_integrity_passed": True,
        "packet_manifest_file_sha256": file_sha256(manifest_path),
        "packet_manifest_payload_sha256": expected_payload_hash,
        "artifact_count": len(artifacts),
        "snapshot": snapshot,
    }


def receipt_signing_payload(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(receipt)
    signature = payload.setdefault("signature", {})
    signature["signed_payload_sha256"] = None
    signature["detached_signature_artifact_sha256"] = None
    return payload


def receipt_signing_payload_sha256(receipt: dict[str, Any]) -> str:
    return canonical_sha256(receipt_signing_payload(receipt))


def validate_receipt(
    receipt: dict[str, Any],
    packet_report: dict[str, Any],
    *,
    expect_template: bool,
    independence_artifact: Path | None = None,
    signature_artifact: Path | None = None,
) -> dict[str, Any]:
    if receipt.get("schema") != EXPECTED_RECEIPT_SCHEMA:
        raise ValueError("unexpected independent reproduction receipt schema")
    frozen = receipt.get("frozen_packet")
    if not isinstance(frozen, dict):
        raise ValueError("receipt frozen_packet must be an object")
    expected_frozen = {
        "packet_manifest_file_sha256": packet_report[
            "packet_manifest_file_sha256"
        ],
        "packet_manifest_payload_sha256": packet_report[
            "packet_manifest_payload_sha256"
        ],
        "snapshot": packet_report["snapshot"],
    }
    if frozen != expected_frozen:
        raise ValueError("receipt frozen packet does not match the verified packet")
    if receipt.get("operator_may_fill_reviewer_fields") is not False:
        raise ValueError("operator substitution must be prohibited")
    if receipt.get("performance_promotion_allowed") is not False:
        raise ValueError("performance promotion must remain prohibited")
    reviewer = receipt.get("reviewer") or {}
    reproduction = receipt.get("reproduction") or {}
    signature = receipt.get("signature") or {}
    if expect_template:
        if any(reviewer.get(field) is not None for field in REVIEWER_FIELDS):
            raise ValueError("reviewer fields must be blank in the unsigned template")
        if any(reproduction.get(field) is not None for field in REPRODUCTION_FIELDS):
            raise ValueError("reproduction fields must be blank in the unsigned template")
        if any(signature.get(field) is not None for field in SIGNATURE_FIELDS):
            raise ValueError("signature fields must be blank in the unsigned template")
        return {
            "schema": "eia_grid_hourly_independent_reproduction_receipt_verification.v1",
            "receipt_integrity_passed": True,
            "status": "UNSIGNED_INDEPENDENT_REPRODUCTION_TEMPLATE_VALID",
            "independent_reproduction_complete": False,
            "performance_promotion_allowed": False,
        }

    text_fields = [field for field in REVIEWER_FIELDS if field != "independence_evidence_sha256"]
    if any(not isinstance(reviewer.get(field), str) or not reviewer[field].strip() for field in text_fields):
        raise ValueError("completed receipt reviewer identity fields are incomplete")
    independence_hash = require_sha256(
        reviewer.get("independence_evidence_sha256"),
        "reviewer.independence_evidence_sha256",
    )
    if not independence_artifact or not independence_artifact.is_file():
        raise ValueError("reviewer independence artifact is required")
    if file_sha256(independence_artifact) != independence_hash:
        raise ValueError("reviewer independence artifact hash mismatch")
    decision = reproduction.get("decision")
    if decision not in ALLOWED_DECISIONS:
        raise ValueError("completed receipt decision is invalid")
    parse_aware_datetime(reproduction.get("executed_utc"), "reproduction.executed_utc")
    if not isinstance(reproduction.get("environment_summary"), str) or not reproduction[
        "environment_summary"
    ].strip():
        raise ValueError("completed receipt environment summary is required")
    if reproduction.get("operator_filled_reviewer_fields") is not False:
        raise ValueError("operator-filled reviewer fields are prohibited")
    reproduced = decision == "REPRODUCED_FROZEN_SNAPSHOT"
    if reproduced:
        for field in (
            "packet_rehashed",
            "packet_hashes_match",
            "source_cache_chain_verified",
            "prediction_chain_verified",
            "settlement_chain_verified",
            "operational_chain_verified",
            "settlement_metrics_recomputed",
            "authority_coverage_recomputed",
        ):
            if reproduction.get(field) is not True:
                raise ValueError(f"reproduction.{field} must be true")
        snapshot = packet_report["snapshot"]
        exact_fields = (
            "prediction_count",
            "settlement_count",
            "common_settled_hour_count",
            "zero_prospective_seal_authorities",
            "prediction_terminal_sha256",
            "settlement_terminal_sha256",
            "operational_terminal_sha256",
        )
        for field in exact_fields:
            if reproduction.get(field) != snapshot[field]:
                raise ValueError(f"reproduction.{field} does not match the packet")
    elif not isinstance(reproduction.get("notes"), str) or not reproduction["notes"].strip():
        raise ValueError("a non-reproduction decision requires explanatory notes")
    if signature.get("method") not in ALLOWED_SIGNATURE_METHODS:
        raise ValueError("signature method is not allowed")
    signed_payload = require_sha256(
        signature.get("signed_payload_sha256"),
        "signature.signed_payload_sha256",
    )
    if signed_payload != receipt_signing_payload_sha256(receipt):
        raise ValueError("signed payload hash mismatch")
    signature_hash = require_sha256(
        signature.get("detached_signature_artifact_sha256"),
        "signature.detached_signature_artifact_sha256",
    )
    if not signature_artifact or not signature_artifact.is_file():
        raise ValueError("detached signature artifact is required")
    if file_sha256(signature_artifact) != signature_hash:
        raise ValueError("detached signature artifact hash mismatch")
    return {
        "schema": "eia_grid_hourly_independent_reproduction_receipt_verification.v1",
        "receipt_integrity_passed": True,
        "status": (
            "FROZEN_SNAPSHOT_INDEPENDENTLY_REPRODUCED"
            if reproduced
            else "INDEPENDENT_REPRODUCTION_DID_NOT_MATCH"
        ),
        "independent_reproduction_complete": reproduced,
        "performance_promotion_allowed": False,
    }


def validate_receipt_for_signing(
    receipt: dict[str, Any],
    packet_report: dict[str, Any],
    *,
    independence_artifact: Path | None,
) -> dict[str, Any]:
    """Validate reviewer-controlled content before emitting a signing digest."""
    signature = receipt.get("signature")
    if not isinstance(signature, dict):
        raise ValueError("receipt signature must be an object")
    for field in (
        "signed_payload_sha256",
        "detached_signature_artifact_sha256",
    ):
        if signature.get(field) is not None:
            raise ValueError(f"signature.{field} must be blank before signing")
    if not independence_artifact or not independence_artifact.is_file():
        raise ValueError("reviewer independence artifact is required before signing")

    signing_payload_sha256 = receipt_signing_payload_sha256(receipt)
    candidate = copy.deepcopy(receipt)
    candidate_signature = candidate["signature"]
    candidate_signature["signed_payload_sha256"] = signing_payload_sha256
    candidate_signature["detached_signature_artifact_sha256"] = file_sha256(
        independence_artifact
    )

    # Exercise the complete verifier on an isolated copy. The independence
    # artifact is used only as a private placeholder for the not-yet-created
    # signature artifact; no completed claim is returned from this preflight.
    validate_receipt(
        candidate,
        packet_report,
        expect_template=False,
        independence_artifact=independence_artifact,
        signature_artifact=independence_artifact,
    )
    return {
        "schema": "eia_grid_hourly_receipt_signing_preflight.v1",
        "status": "READY_FOR_REVIEWER_SIGNATURE",
        "signing_payload_sha256": signing_payload_sha256,
        "reviewer_content_validated": True,
        "independence_artifact_validated": True,
        "independent_reproduction_complete": False,
        "performance_promotion_allowed": False,
    }


def evaluator_protocol_signing_payload(protocol: dict[str, Any]) -> dict[str, Any]:
    payload = copy.deepcopy(protocol)
    freeze = payload.setdefault("freeze", {})
    freeze["accepted_protocol_payload_sha256"] = None
    freeze["signed_payload_sha256"] = None
    freeze["detached_signature_artifact_sha256"] = None
    return payload


def evaluator_protocol_signing_payload_sha256(protocol: dict[str, Any]) -> str:
    return canonical_sha256(evaluator_protocol_signing_payload(protocol))


def require_nonempty_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    return value.strip()


def validate_evaluator_guardrails(protocol: dict[str, Any]) -> None:
    predecessor = protocol.get("predecessor") or {}
    if predecessor.get("protocol_id") != "EIA_GRID_PROSPECTIVE_HOURLY_ROUTER_20260715":
        raise ValueError("evaluator protocol predecessor id mismatch")
    if predecessor.get("protocol_sha256") != "5398f17f57e02bdaadb1cef5b6dae20708146eaa0de534ebbe6ce36ab28952e5":
        raise ValueError("evaluator protocol predecessor hash mismatch")
    if predecessor.get("performance_promotion_allowed") is not False:
        raise ValueError("predecessor performance promotion must remain prohibited")
    data = protocol.get("data_contract") or {}
    test_plan = protocol.get("test_plan") or {}
    acceptance = protocol.get("acceptance_contract") or {}
    floors = protocol.get("scientific_floors") or {}
    fixed_pairs = {
        "data.backfill_allowed": data.get("backfill_allowed") is False,
        "test.route_change_prohibited": test_plan.get(
            "route_or_hyperparameter_change_after_freeze_allowed"
        )
        is False,
        "test.outcome_exclusion_prohibited": test_plan.get(
            "outcome_dependent_authority_exclusion_allowed"
        )
        is False,
        "test.negative_result_retained": test_plan.get(
            "negative_result_retention_required"
        )
        is True,
        "acceptance.all_checks_required": acceptance.get(
            "all_required_checks_must_pass"
        )
        is True,
        "acceptance.partial_pass_prohibited": acceptance.get(
            "partial_pass_allowed"
        )
        is False,
        "acceptance.economic_conversion_disabled": acceptance.get(
            "economic_conversion_enabled"
        )
        is False,
        "acceptance.field_claim_disabled": acceptance.get(
            "field_or_safety_claim_enabled"
        )
        is False,
        "acceptance.deployment_disabled": acceptance.get(
            "deployment_authorization_enabled"
        )
        is False,
        "operator_substitution_prohibited": protocol.get(
            "operator_may_fill_evaluator_fields"
        )
        is False,
        "premature_promotion_prohibited": protocol.get(
            "performance_promotion_before_completed_evaluation_allowed"
        )
        is False,
    }
    failed = sorted(key for key, passed in fixed_pairs.items() if not passed)
    if failed:
        raise ValueError(f"evaluator protocol guardrails failed: {failed}")
    required_floors = {
        "minimum_common_hours_per_authority": 720,
        "minimum_bootstrap_replications": 10000,
        "required_confidence_level": 0.95,
        "required_aggregation_unit": "balancing_authority_utc_day",
        "required_uncertainty_method": (
            "paired_moving_block_bootstrap_clustered_by_authority_utc_day"
        ),
        "required_multiple_comparison_correction": "holm",
    }
    if floors != required_floors:
        raise ValueError("evaluator scientific floors changed")
    fixed_test_values = {
        "aggregation_unit": floors["required_aggregation_unit"],
        "confidence_level": floors["required_confidence_level"],
        "uncertainty_method": floors["required_uncertainty_method"],
        "multiple_comparison_correction": floors[
            "required_multiple_comparison_correction"
        ],
        "tie_rule": "lexicographic_candidate_id",
    }
    for key, expected in fixed_test_values.items():
        if test_plan.get(key) != expected:
            raise ValueError(f"evaluator test-plan guardrail changed: {key}")


def validate_evaluator_protocol(
    protocol: dict[str, Any],
    *,
    expect_template: bool,
    independence_artifact: Path | None = None,
    signature_artifact: Path | None = None,
) -> dict[str, Any]:
    if protocol.get("schema") != EXPECTED_EVALUATOR_PROTOCOL_SCHEMA:
        raise ValueError("unexpected external evaluator protocol schema")
    if protocol.get("evidence_lane_id") != (
        "eia_grid_prospective_hourly_router_external_evaluation"
    ):
        raise ValueError("unexpected external evaluator evidence lane")
    validate_evaluator_guardrails(protocol)
    evaluator = protocol.get("evaluator") or {}
    data = protocol.get("data_contract") or {}
    test_plan = protocol.get("test_plan") or {}
    acceptance = protocol.get("acceptance_contract") or {}
    freeze = protocol.get("freeze") or {}
    if expect_template:
        if any(evaluator.get(field) is not None for field in EVALUATOR_FIELDS):
            raise ValueError("evaluator fields must be blank in the template")
        if any(data.get(field) is not None for field in EVALUATOR_DATA_FIELDS):
            raise ValueError("data-contract fields must be blank in the template")
        if any(test_plan.get(field) is not None for field in EVALUATOR_TEST_FIELDS):
            raise ValueError("test-plan fields must be blank in the template")
        if acceptance.get("technical_gate_expression") is not None:
            raise ValueError("technical gate must be blank in the template")
        if any(freeze.get(field) is not None for field in EVALUATOR_FREEZE_FIELDS):
            raise ValueError("freeze fields must be blank in the template")
        return {
            "schema": "eia_grid_hourly_external_evaluator_protocol_verification.v1",
            "protocol_integrity_passed": True,
            "status": "UNSIGNED_EXTERNAL_EVALUATOR_PROTOCOL_TEMPLATE_VALID",
            "evaluation_design_frozen": False,
            "performance_promotion_allowed": False,
        }

    evaluator_text_fields = [
        field for field in EVALUATOR_FIELDS if field != "independence_evidence_sha256"
    ]
    for field in evaluator_text_fields:
        require_nonempty_text(evaluator.get(field), f"evaluator.{field}")
    independence_hash = require_sha256(
        evaluator.get("independence_evidence_sha256"),
        "evaluator.independence_evidence_sha256",
    )
    if not independence_artifact or not independence_artifact.is_file():
        raise ValueError("evaluator independence artifact is required")
    if file_sha256(independence_artifact) != independence_hash:
        raise ValueError("evaluator independence artifact hash mismatch")
    for field in (
        "publisher_or_owner",
        "dataset_description",
        "custody_owner",
        "access_authority",
        "observation_availability_rule",
        "target_release_timing_rule",
        "authority_inclusion_rule",
        "missing_data_rule",
        "revision_policy",
    ):
        require_nonempty_text(data.get(field), f"data_contract.{field}")
    require_sha256(
        data.get("dataset_or_query_manifest_sha256"),
        "data_contract.dataset_or_query_manifest_sha256",
    )
    if data.get("held_out_from_lumencore_before_freeze") is not True:
        raise ValueError("evaluation data must be held out from LumenCore before freeze")
    start = parse_aware_datetime(
        data.get("evaluation_start_utc"), "data_contract.evaluation_start_utc"
    )
    end = parse_aware_datetime(
        data.get("evaluation_end_utc"), "data_contract.evaluation_end_utc"
    )
    if not start < end:
        raise ValueError("evaluation window end must follow its start")
    authorities = data.get("registered_authorities")
    if (
        not isinstance(authorities, list)
        or not authorities
        or any(not isinstance(value, str) or not value.strip() for value in authorities)
        or len(authorities) != len(set(authorities))
    ):
        raise ValueError("registered authorities must be a non-empty unique list")
    for field in (
        "candidate_definition",
        "incumbent_baseline_id",
        "incumbent_baseline_definition",
        "primary_metric",
    ):
        require_nonempty_text(test_plan.get(field), f"test_plan.{field}")
    if test_plan.get("metric_direction") not in {
        "lower_is_better",
        "higher_is_better",
    }:
        raise ValueError("metric direction is invalid")
    floors = protocol["scientific_floors"]
    minimum_hours = require_nonnegative_int(
        test_plan.get("minimum_common_hours_per_authority"),
        "test_plan.minimum_common_hours_per_authority",
    )
    if minimum_hours < floors["minimum_common_hours_per_authority"]:
        raise ValueError("common-hour sample floor is too small")
    minimum_effect = require_finite_number(
        test_plan.get("minimum_effect_size"), "test_plan.minimum_effect_size"
    )
    if minimum_effect <= 0.0:
        raise ValueError("minimum effect size must be positive")
    replications = require_nonnegative_int(
        test_plan.get("bootstrap_replications"),
        "test_plan.bootstrap_replications",
    )
    if replications < floors["minimum_bootstrap_replications"]:
        raise ValueError("bootstrap replication floor is too small")
    require_nonnegative_int(test_plan.get("bootstrap_seed"), "test_plan.bootstrap_seed")
    secondary = test_plan.get("secondary_metrics")
    if not isinstance(secondary, list) or any(
        not isinstance(value, str) or not value.strip() for value in secondary
    ):
        raise ValueError("secondary metrics must be a list of metric names")
    regression_limit = require_finite_number(
        test_plan.get("single_authority_regression_limit"),
        "test_plan.single_authority_regression_limit",
    )
    if regression_limit < 0.0:
        raise ValueError("single-authority regression limit cannot be negative")
    authority_wins = require_nonnegative_int(
        test_plan.get("minimum_authority_mean_wins"),
        "test_plan.minimum_authority_mean_wins",
    )
    if not 1 <= authority_wins <= len(authorities):
        raise ValueError("minimum authority wins is outside the registered panel")
    day_win_rate = require_finite_number(
        test_plan.get("minimum_utc_day_win_rate"),
        "test_plan.minimum_utc_day_win_rate",
    )
    if not 0.5 <= day_win_rate <= 1.0:
        raise ValueError("UTC-day win rate must be between 0.5 and 1.0")
    require_nonempty_text(
        acceptance.get("technical_gate_expression"),
        "acceptance_contract.technical_gate_expression",
    )
    parse_aware_datetime(freeze.get("accepted_utc"), "freeze.accepted_utc")
    if freeze.get("signature_method") not in ALLOWED_SIGNATURE_METHODS:
        raise ValueError("evaluator signature method is not allowed")
    expected_payload = evaluator_protocol_signing_payload_sha256(protocol)
    for field in ("accepted_protocol_payload_sha256", "signed_payload_sha256"):
        if require_sha256(freeze.get(field), f"freeze.{field}") != expected_payload:
            raise ValueError(f"freeze.{field} does not bind the accepted protocol")
    signature_hash = require_sha256(
        freeze.get("detached_signature_artifact_sha256"),
        "freeze.detached_signature_artifact_sha256",
    )
    if not signature_artifact or not signature_artifact.is_file():
        raise ValueError("evaluator detached signature artifact is required")
    if file_sha256(signature_artifact) != signature_hash:
        raise ValueError("evaluator detached signature artifact hash mismatch")
    return {
        "schema": "eia_grid_hourly_external_evaluator_protocol_verification.v1",
        "protocol_integrity_passed": True,
        "status": "EXTERNAL_EVALUATOR_PROTOCOL_ACCEPTED_AND_FROZEN",
        "evaluation_design_frozen": True,
        "performance_promotion_allowed": False,
    }


def validate_evaluator_protocol_for_signing(
    protocol: dict[str, Any],
    *,
    independence_artifact: Path | None,
) -> dict[str, Any]:
    """Validate evaluator-owned protocol content before emitting its digest."""
    freeze = protocol.get("freeze")
    if not isinstance(freeze, dict):
        raise ValueError("evaluator protocol freeze must be an object")
    for field in (
        "accepted_protocol_payload_sha256",
        "signed_payload_sha256",
        "detached_signature_artifact_sha256",
    ):
        if freeze.get(field) is not None:
            raise ValueError(f"freeze.{field} must be blank before signing")
    if not independence_artifact or not independence_artifact.is_file():
        raise ValueError("evaluator independence artifact is required before signing")

    signing_payload_sha256 = evaluator_protocol_signing_payload_sha256(protocol)
    candidate = copy.deepcopy(protocol)
    candidate_freeze = candidate["freeze"]
    candidate_freeze["accepted_protocol_payload_sha256"] = signing_payload_sha256
    candidate_freeze["signed_payload_sha256"] = signing_payload_sha256
    candidate_freeze["detached_signature_artifact_sha256"] = file_sha256(
        independence_artifact
    )

    validate_evaluator_protocol(
        candidate,
        expect_template=False,
        independence_artifact=independence_artifact,
        signature_artifact=independence_artifact,
    )
    return {
        "schema": "eia_grid_hourly_evaluator_protocol_signing_preflight.v1",
        "status": "READY_FOR_EVALUATOR_SIGNATURE",
        "signing_payload_sha256": signing_payload_sha256,
        "evaluator_content_validated": True,
        "independence_artifact_validated": True,
        "evaluation_design_frozen": False,
        "performance_promotion_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--expect-template", action="store_true")
    parser.add_argument("--evaluator-protocol", type=Path)
    parser.add_argument("--expect-evaluator-template", action="store_true")
    parser.add_argument("--independence-artifact", type=Path)
    parser.add_argument("--signature-artifact", type=Path)
    parser.add_argument("--print-signing-payload-sha256", action="store_true")
    args = parser.parse_args()
    try:
        packet_report = verify_packet(args.packet_dir.resolve())
        if args.receipt and args.evaluator_protocol:
            raise ValueError("validate a receipt or evaluator protocol per invocation")
        if args.evaluator_protocol:
            evaluator_protocol = read_json(args.evaluator_protocol.resolve())
            if args.print_signing_payload_sha256:
                preflight = validate_evaluator_protocol_for_signing(
                    evaluator_protocol,
                    independence_artifact=(
                        args.independence_artifact.resolve()
                        if args.independence_artifact
                        else None
                    ),
                )
                print(preflight["signing_payload_sha256"])
                return 0
            report = validate_evaluator_protocol(
                evaluator_protocol,
                expect_template=args.expect_evaluator_template,
                independence_artifact=(
                    args.independence_artifact.resolve()
                    if args.independence_artifact
                    else None
                ),
                signature_artifact=(
                    args.signature_artifact.resolve()
                    if args.signature_artifact
                    else None
                ),
            )
        elif args.receipt:
            receipt = read_json(args.receipt.resolve())
            if args.print_signing_payload_sha256:
                preflight = validate_receipt_for_signing(
                    receipt,
                    packet_report,
                    independence_artifact=(
                        args.independence_artifact.resolve()
                        if args.independence_artifact
                        else None
                    ),
                )
                print(preflight["signing_payload_sha256"])
                return 0
            report = validate_receipt(
                receipt,
                packet_report,
                expect_template=args.expect_template,
                independence_artifact=(
                    args.independence_artifact.resolve()
                    if args.independence_artifact
                    else None
                ),
                signature_artifact=(
                    args.signature_artifact.resolve()
                    if args.signature_artifact
                    else None
                ),
            )
        else:
            if args.print_signing_payload_sha256:
                raise ValueError(
                    "--print-signing-payload-sha256 requires --receipt or "
                    "--evaluator-protocol"
                )
            report = packet_report
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(
            json.dumps(
                {
                    "integrity_gate_passed": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
