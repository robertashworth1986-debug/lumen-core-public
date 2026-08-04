"""Deterministic confirmatory analysis for source-native forecast settlements.

The module is intentionally pure: it accepts already verified settlement
records, verified independent-anchor coverage, and a self-bound V3 protocol.
It performs no file, network, or ledger writes. Invalid or incomplete inputs
produce a machine-readable non-promoting report.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import numpy as np


SOURCE_ARMS = ("FRED", "TWELVE_DATA")
BOOTSTRAP_REPLICATIONS = 20_000
BOOTSTRAP_SEED = 2_026_072_901
SIGNIFICANCE_LEVEL = 0.05
EFFECT_FLOOR_RMAE = 0.95
CELL_RMAE_LIMIT = 1.05
P95_ERROR_RATIO_LIMIT = 1.10
DENOMINATOR_EPSILON = 1e-12
PERIOD_IDS = ("V3_CONFIRMATORY_P1", "V3_REPLICATION_P2")
SOURCE_BOOTSTRAP = {
    "FRED": {
        "cluster_grain": "calendar_month",
        "block_length": 6,
        "minimum_clusters": 60,
    },
    "TWELVE_DATA": {
        "cluster_grain": "exchange_week_monday",
        "block_length": 8,
        "minimum_clusters": 104,
    },
}


class ConfirmatoryInputError(ValueError):
    """Raised internally when a frozen input contract is not satisfied."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def protocol_payload_sha256(protocol: dict[str, Any]) -> str:
    payload = copy.deepcopy(protocol)
    payload.pop("protocol_payload_sha256", None)
    return canonical_sha256(payload)


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return value == value.lower()


def _as_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ConfirmatoryInputError(f"{field}_must_be_utc_text")
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ConfirmatoryInputError(f"{field}_invalid_utc_text") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ConfirmatoryInputError(f"{field}_must_be_utc")
    return parsed.astimezone(timezone.utc)


def _finite_float(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfirmatoryInputError(f"{field}_must_be_numeric") from exc
    if not math.isfinite(result):
        raise ConfirmatoryInputError(f"{field}_must_be_finite")
    return result


def _exact_number(value: Any, expected: float, field: str) -> None:
    number = _finite_float(value, field)
    if not math.isclose(number, expected, rel_tol=0.0, abs_tol=1e-15):
        raise ConfirmatoryInputError(f"{field}_must_equal_{expected}")


def validate_protocol(protocol: dict[str, Any]) -> list[str]:
    """Return all detectable V3 protocol violations in deterministic order."""

    errors: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    if not isinstance(protocol, dict):
        return ["protocol_must_be_object"]
    require(
        protocol.get("schema") == "time_series_source_native_prospective_protocol.v3",
        "protocol_schema_not_v3",
    )
    require(bool(protocol.get("protocol_id")), "protocol_id_missing")
    supplied_hash = protocol.get("protocol_payload_sha256")
    require(_is_sha256(supplied_hash), "protocol_payload_sha256_invalid")
    if _is_sha256(supplied_hash):
        require(
            supplied_hash == protocol_payload_sha256(protocol),
            "protocol_payload_sha256_mismatch",
        )

    try:
        _as_utc(protocol.get("freeze", {}).get("freeze_utc"), "freeze_utc")
    except ConfirmatoryInputError as exc:
        errors.append(str(exc))

    candidate_id = protocol.get("candidate", {}).get("registered_family_id")
    require(isinstance(candidate_id, str) and bool(candidate_id), "candidate_id_missing")
    baselines = protocol.get("registered_baselines")
    require(isinstance(baselines, list), "registered_baselines_must_be_list")
    if isinstance(baselines, list):
        require(len(baselines) == 8, "registered_baselines_must_contain_8")
        require(len(set(baselines)) == len(baselines), "registered_baselines_not_unique")
        require(
            all(isinstance(item, str) and item for item in baselines),
            "registered_baseline_id_invalid",
        )
        require(candidate_id not in baselines, "candidate_must_not_be_baseline")

    require(
        protocol.get("ledger_contract", {}).get("settlement_schema")
        == "time_series_source_native_settlement.v3",
        "settlement_schema_not_bound",
    )

    registered_sources: dict[str, Any] = {}
    for source in protocol.get("sources", []) if isinstance(protocol.get("sources"), list) else []:
        if not isinstance(source, dict) or source.get("source") not in SOURCE_ARMS:
            errors.append("registered_source_invalid")
            continue
        source_id = source["source"]
        if source_id in registered_sources:
            errors.append(f"registered_source_duplicate:{source_id}")
            continue
        registered_sources[source_id] = source
        series_rows = source.get("series")
        if not isinstance(series_rows, list) or not series_rows:
            errors.append(f"registered_series_missing:{source_id}")
            continue
        seen_series: set[str] = set()
        for series in series_rows:
            if not isinstance(series, dict) or not isinstance(series.get("series_id"), str):
                errors.append(f"registered_series_invalid:{source_id}")
                continue
            series_id = series["series_id"]
            if series_id in seen_series:
                errors.append(f"registered_series_duplicate:{source_id}:{series_id}")
            seen_series.add(series_id)
            horizons = series.get("horizons")
            if (
                not isinstance(horizons, list)
                or not horizons
                or any(not isinstance(h, int) or isinstance(h, bool) or h <= 0 for h in horizons)
                or len(set(horizons)) != len(horizons)
            ):
                errors.append(f"registered_horizons_invalid:{source_id}:{series_id}")
    require(set(registered_sources) == set(SOURCE_ARMS), "source_arms_must_be_fred_and_twelve_data")

    analysis = protocol.get("analysis_contract", {})
    require(analysis.get("source_arms") == list(SOURCE_ARMS), "source_arm_order_changed")
    require(analysis.get("contrast_count") == 16, "contrast_count_must_equal_16")
    require(analysis.get("cell_definition") == "source-series-horizon", "cell_definition_changed")
    require(
        analysis.get("cell_weighting") == "equal_mean_log_rmae",
        "cell_weighting_changed",
    )
    require(
        analysis.get("bootstrap_replications") == BOOTSTRAP_REPLICATIONS,
        "bootstrap_replications_must_equal_20000",
    )
    require(analysis.get("bootstrap_seed") == BOOTSTRAP_SEED, "bootstrap_seed_changed")
    require(analysis.get("quantile_method") == "linear", "quantile_method_changed")
    try:
        _exact_number(analysis.get("familywise_error_rate"), SIGNIFICANCE_LEVEL, "familywise_error_rate")
    except ConfirmatoryInputError as exc:
        errors.append(str(exc))
    bootstrap_by_source = analysis.get("bootstrap_by_source", {})
    for source_id in SOURCE_ARMS:
        require(
            bootstrap_by_source.get(source_id) == SOURCE_BOOTSTRAP[source_id],
            f"bootstrap_contract_changed:{source_id}",
        )

    decision = protocol.get("decision_rule", {})
    for key, expected in (
        ("effect_floor_max_rmae", EFFECT_FLOOR_RMAE),
        ("cell_rmae_max", CELL_RMAE_LIMIT),
        ("p95_error_ratio_max", P95_ERROR_RATIO_LIMIT),
        ("upper_confidence_level", 0.95),
    ):
        try:
            _exact_number(decision.get(key), expected, key)
        except ConfirmatoryInputError as exc:
            errors.append(str(exc))
    require(
        decision.get("require_all_contrasts_each_arm") is True,
        "all_contrasts_requirement_missing",
    )
    require(
        decision.get("require_independent_replication_period") is True,
        "replication_requirement_missing",
    )

    periods = protocol.get("period_contract", {})
    first = periods.get("first_confirmatory_period", {})
    second = periods.get("independent_replication_period", {})
    require(first.get("period_id") == PERIOD_IDS[0], "first_period_id_changed")
    require(second.get("period_id") == PERIOD_IDS[1], "replication_period_id_changed")
    try:
        first_start = date.fromisoformat(first.get("target_period_start_inclusive", ""))
        first_end = date.fromisoformat(first.get("target_period_end_inclusive", ""))
        second_start = date.fromisoformat(second.get("target_period_start_inclusive", ""))
        second_end = date.fromisoformat(second.get("target_period_end_inclusive", ""))
        require(first_start <= first_end, "first_period_order_invalid")
        require(second_start == first_end + timedelta(days=1), "periods_not_contiguous")
        require(second_start <= second_end, "replication_period_order_invalid")
    except (TypeError, ValueError):
        errors.append("period_date_contract_invalid")
    require(periods.get("replication_reuses_first_period_rows") is False, "shared_targets_must_be_disallowed")
    return errors


def _registered_cells(protocol: dict[str, Any]) -> dict[str, tuple[tuple[str, int], ...]]:
    result: dict[str, tuple[tuple[str, int], ...]] = {}
    sources = {row["source"]: row for row in protocol["sources"]}
    for source_id in SOURCE_ARMS:
        cells = [
            (series["series_id"], int(horizon))
            for series in sources[source_id]["series"]
            for horizon in series["horizons"]
        ]
        result[source_id] = tuple(sorted(cells, key=lambda item: (item[0], item[1])))
    return result


def _period_date_bounds(
    protocol: dict[str, Any], period_id: str
) -> tuple[date, date]:
    key = (
        "first_confirmatory_period"
        if period_id == PERIOD_IDS[0]
        else "independent_replication_period"
    )
    period = protocol["period_contract"][key]
    if period.get("period_id") != period_id:
        raise ConfirmatoryInputError(f"period_id_mismatch:{period_id}")
    try:
        start = date.fromisoformat(period["target_period_start_inclusive"])
        end = date.fromisoformat(period["target_period_end_inclusive"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfirmatoryInputError(f"period_boundary_invalid:{period_id}") from exc
    if end < start:
        raise ConfirmatoryInputError(f"period_boundary_order_invalid:{period_id}")
    return start, end


def _normalize_settlement(record: dict[str, Any], protocol: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ConfirmatoryInputError("settlement_must_be_object")
    if record.get("schema") != protocol["ledger_contract"]["settlement_schema"]:
        raise ConfirmatoryInputError("settlement_schema_not_accepted")
    if record.get("protocol_id") != protocol["protocol_id"]:
        raise ConfirmatoryInputError("settlement_protocol_id_mismatch")
    if record.get("protocol_payload_sha256") != protocol["protocol_payload_sha256"]:
        raise ConfirmatoryInputError("settlement_protocol_payload_sha256_mismatch")
    if not _is_sha256(record.get("record_sha256")):
        raise ConfirmatoryInputError("settlement_record_sha256_invalid")
    if not _is_sha256(record.get("prediction_record_sha256")):
        raise ConfirmatoryInputError("prediction_record_sha256_invalid")
    verification = record.get("verification")
    required_verification = (
        "chain_record_verified",
        "prediction_reference_verified",
        "protocol_binding_verified",
    )
    if not isinstance(verification, dict) or any(
        verification.get(field) is not True for field in required_verification
    ):
        raise ConfirmatoryInputError("settlement_verification_incomplete")
    release_proof = record.get("release_order_proof")
    if not isinstance(release_proof, dict) or release_proof.get("passed") is not True:
        raise ConfirmatoryInputError("release_order_not_verified")
    source = record.get("source")
    if source not in SOURCE_ARMS:
        raise ConfirmatoryInputError("settlement_source_invalid")
    series_id = record.get("series_id")
    horizon = record.get("horizon")
    if not isinstance(series_id, str) or not series_id:
        raise ConfirmatoryInputError("settlement_series_id_invalid")
    if not isinstance(horizon, int) or isinstance(horizon, bool) or horizon <= 0:
        raise ConfirmatoryInputError("settlement_horizon_invalid")
    try:
        target_date = date.fromisoformat(str(record.get("target_period")))
    except ValueError as exc:
        raise ConfirmatoryInputError("settlement_target_period_invalid") from exc
    observed_at = _as_utc(record.get("actual_observed_at_utc"), "actual_observed_at_utc")
    actual = _finite_float(record.get("actual"), "settlement_actual")
    metrics = record.get("strategy_metrics")
    if not isinstance(metrics, dict):
        raise ConfirmatoryInputError("strategy_metrics_missing")
    strategy_ids = [
        protocol["candidate"]["registered_family_id"],
        *protocol["registered_baselines"],
    ]
    normalized_metrics: dict[str, dict[str, float]] = {}
    if set(metrics) != set(strategy_ids):
        raise ConfirmatoryInputError("strategy_metric_ids_not_exact")
    for strategy_id in strategy_ids:
        metric = metrics[strategy_id]
        if not isinstance(metric, dict):
            raise ConfirmatoryInputError(f"strategy_metric_invalid:{strategy_id}")
        prediction = _finite_float(metric.get("prediction"), f"prediction:{strategy_id}")
        error = _finite_float(metric.get("absolute_error"), f"absolute_error:{strategy_id}")
        if error < 0.0:
            raise ConfirmatoryInputError(f"absolute_error_negative:{strategy_id}")
        recomputed = abs(actual - prediction)
        if not math.isclose(error, recomputed, rel_tol=0.0, abs_tol=1e-8):
            raise ConfirmatoryInputError(f"absolute_error_mismatch:{strategy_id}")
        normalized_metrics[strategy_id] = {
            "prediction": prediction,
            "absolute_error": error,
        }
    normalized = dict(record)
    normalized["target_date"] = target_date
    normalized["observed_at"] = observed_at
    if source == "FRED":
        target_release_boundary = _as_utc(
            release_proof.get("conservative_release_boundary_utc"),
            "conservative_release_boundary_utc",
        )
    else:
        exchange_timezone = str(release_proof.get("exchange_timezone", ""))
        if exchange_timezone != "America/New_York":
            raise ConfirmatoryInputError("twelve_data_exchange_timezone_invalid")
        target_release_boundary = datetime.combine(
            target_date,
            datetime.min.time(),
            tzinfo=ZoneInfo(exchange_timezone),
        ).astimezone(timezone.utc)
    normalized["target_release_boundary"] = target_release_boundary
    normalized["strategy_metrics"] = normalized_metrics
    return normalized


def _period_anchor_map(
    anchor_coverage: dict[str, Any],
    period_id: str,
    rows: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], set[str]]:
    if not rows:
        return {}, set()
    period_entries = anchor_coverage.get("periods")
    if not isinstance(period_entries, list):
        raise ConfirmatoryInputError("anchor_periods_must_be_list")
    matches = [item for item in period_entries if isinstance(item, dict) and item.get("period_id") == period_id]
    if len(matches) != 1:
        raise ConfirmatoryInputError(f"anchor_period_entry_count_invalid:{period_id}")
    anchors = matches[0].get("anchors")
    if not isinstance(anchors, list) or not anchors:
        raise ConfirmatoryInputError(f"verified_anchor_missing:{period_id}")
    prediction_to_anchor: dict[str, dict[str, Any]] = {}
    receipts: set[str] = set()
    for index, anchor in enumerate(anchors):
        if not isinstance(anchor, dict):
            raise ConfirmatoryInputError(f"anchor_invalid:{period_id}:{index}")
        receipt = anchor.get("anchor_receipt_sha256")
        subject = anchor.get("anchor_subject_sha256")
        if not _is_sha256(receipt) or not _is_sha256(subject):
            raise ConfirmatoryInputError(f"anchor_hash_invalid:{period_id}:{index}")
        if anchor.get("verified") is not True or anchor.get("independent") is not True:
            raise ConfirmatoryInputError(f"anchor_not_independently_verified:{period_id}:{index}")
        anchored_at = _as_utc(anchor.get("anchored_at_utc"), f"anchored_at_utc:{period_id}:{index}")
        covered = anchor.get("covered_prediction_record_sha256")
        if not isinstance(covered, list) or not covered:
            raise ConfirmatoryInputError(f"anchor_coverage_empty:{period_id}:{index}")
        receipts.add(receipt)
        for prediction_hash in covered:
            if not _is_sha256(prediction_hash):
                raise ConfirmatoryInputError(f"covered_prediction_hash_invalid:{period_id}:{index}")
            if prediction_hash in prediction_to_anchor:
                raise ConfirmatoryInputError(f"prediction_covered_by_multiple_anchors:{period_id}")
            prediction_to_anchor[prediction_hash] = {
                "receipt": receipt,
                "subject": subject,
                "anchored_at": anchored_at,
            }
    for row in rows:
        prediction_hash = row["prediction_record_sha256"]
        anchor = prediction_to_anchor.get(prediction_hash)
        if anchor is None:
            raise ConfirmatoryInputError(f"prediction_not_anchor_covered:{period_id}")
        if anchor["anchored_at"] >= row["target_release_boundary"]:
            raise ConfirmatoryInputError(f"anchor_does_not_precede_target:{period_id}")
    return prediction_to_anchor, receipts


def split_nonoverlapping_replication_periods(
    settlements: Iterable[dict[str, Any]],
    anchor_coverage: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    """Validate and split two frozen periods with no target or anchor reuse."""

    protocol_errors = validate_protocol(protocol)
    if protocol_errors:
        raise ConfirmatoryInputError(";".join(protocol_errors))
    if not isinstance(anchor_coverage, dict):
        raise ConfirmatoryInputError("anchor_coverage_must_be_object")
    if anchor_coverage.get("schema") != "time_series_source_native_anchor_coverage.v3":
        raise ConfirmatoryInputError("anchor_coverage_schema_not_v3")
    if anchor_coverage.get("verification_complete") is not True:
        raise ConfirmatoryInputError("anchor_coverage_not_verified")
    if anchor_coverage.get("protocol_id") != protocol["protocol_id"]:
        raise ConfirmatoryInputError("anchor_coverage_protocol_id_mismatch")
    if anchor_coverage.get("protocol_payload_sha256") != protocol["protocol_payload_sha256"]:
        raise ConfirmatoryInputError("anchor_coverage_protocol_hash_mismatch")

    normalized = [_normalize_settlement(row, protocol) for row in settlements]
    record_hashes = [row["record_sha256"] for row in normalized]
    if len(record_hashes) != len(set(record_hashes)):
        raise ConfirmatoryInputError("duplicate_settlement_record")
    cell_targets = [
        (row["source"], row["series_id"], row["horizon"], row["target_period"])
        for row in normalized
    ]
    if len(cell_targets) != len(set(cell_targets)):
        raise ConfirmatoryInputError("duplicate_cell_target")

    periods: dict[str, list[dict[str, Any]]] = {period_id: [] for period_id in PERIOD_IDS}
    bounds = {
        period_id: _period_date_bounds(protocol, period_id) for period_id in PERIOD_IDS
    }
    for row in normalized:
        matches = [
            period_id
            for period_id, (start, end) in bounds.items()
            if start <= row["target_date"] <= end
        ]
        if len(matches) != 1:
            raise ConfirmatoryInputError("settlement_outside_frozen_period_boundaries")
        period_id = matches[0]
        if row.get("period_id") != period_id:
            raise ConfirmatoryInputError("settlement_period_id_mismatch")
        periods[period_id].append(row)

    first_map, first_receipts = _period_anchor_map(
        anchor_coverage,
        PERIOD_IDS[0],
        periods[PERIOD_IDS[0]],
    )
    del first_map
    second_map, second_receipts = _period_anchor_map(
        anchor_coverage,
        PERIOD_IDS[1],
        periods[PERIOD_IDS[1]],
    )
    del second_map
    if first_receipts & second_receipts:
        raise ConfirmatoryInputError("replication_must_use_separate_anchor_receipts")

    first_targets = {
        (row["source"], row["series_id"], row["target_period"])
        for row in periods[PERIOD_IDS[0]]
    }
    second_targets = {
        (row["source"], row["series_id"], row["target_period"])
        for row in periods[PERIOD_IDS[1]]
    }
    if first_targets & second_targets:
        raise ConfirmatoryInputError("replication_periods_share_targets")
    for rows in periods.values():
        rows.sort(
            key=lambda row: (
                row["source"],
                row["series_id"],
                row["horizon"],
                row["target_period"],
                row["record_sha256"],
            )
        )
    return periods


def holm_adjust(p_values: Iterable[float]) -> list[float]:
    """Return Holm adjusted p-values while preserving the supplied order."""

    values = [_finite_float(value, "p_value") for value in p_values]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ConfirmatoryInputError("p_value_out_of_range")
    count = len(values)
    ranked = sorted(range(count), key=lambda index: (values[index], index))
    adjusted = [1.0] * count
    running = 0.0
    for rank, index in enumerate(ranked):
        candidate = min(1.0, (count - rank) * values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def _cluster_key(source: str, target_date: date) -> str:
    if source == "FRED":
        return f"{target_date.year:04d}-{target_date.month:02d}"
    monday = target_date - timedelta(days=target_date.weekday())
    return monday.isoformat()


def _circular_moving_block_plan(
    rng: np.random.Generator,
    cluster_count: int,
    block_length: int,
    replications: int,
) -> np.ndarray:
    block_count = math.ceil(cluster_count / block_length)
    starts = rng.integers(0, cluster_count, size=(replications, block_count), endpoint=False)
    offsets = np.arange(block_length, dtype=np.int64)
    plan = (starts[:, :, None] + offsets[None, None, :]) % cluster_count
    return plan.reshape(replications, -1)[:, :cluster_count]


def _plan_weights(plan: np.ndarray, cluster_count: int) -> np.ndarray:
    weights = np.zeros((plan.shape[0], cluster_count), dtype=np.int16)
    for index, row in enumerate(plan):
        weights[index] = np.bincount(row, minlength=cluster_count)
    return weights


def _arm_analysis(
    source: str,
    rows: list[dict[str, Any]],
    registered_cells: tuple[tuple[str, int], ...],
    candidate_id: str,
    baselines: list[str],
    rng: np.random.Generator,
    replications: int,
) -> dict[str, Any]:
    arm_rows = [row for row in rows if row["source"] == source]
    present_cells = {(row["series_id"], row["horizon"]) for row in arm_rows}
    missing_cells = [
        {"series_id": series_id, "horizon": horizon}
        for series_id, horizon in registered_cells
        if (series_id, horizon) not in present_cells
    ]
    unexpected_cells = sorted(present_cells - set(registered_cells))
    clusters = sorted({_cluster_key(source, row["target_date"]) for row in arm_rows})
    bootstrap_contract = SOURCE_BOOTSTRAP[source]
    sample_gate_passed = len(clusters) >= bootstrap_contract["minimum_clusters"]
    plan_hash: str | None = None
    weights: np.ndarray | None = None
    cluster_index = {cluster: index for index, cluster in enumerate(clusters)}
    if clusters:
        plan = _circular_moving_block_plan(
            rng,
            len(clusters),
            bootstrap_contract["block_length"],
            replications,
        )
        plan_hash = hashlib.sha256(plan.astype("<i8", copy=False).tobytes()).hexdigest()
        weights = _plan_weights(plan, len(clusters))

    cells: dict[tuple[str, int], list[dict[str, Any]]] = {
        cell: [] for cell in registered_cells
    }
    for row in arm_rows:
        cell = (row["series_id"], row["horizon"])
        if cell in cells:
            cells[cell].append(row)

    contrasts: list[dict[str, Any]] = []
    for baseline in baselines:
        contrast: dict[str, Any] = {
            "source": source,
            "baseline_id": baseline,
            "registered_cell_count": len(registered_cells),
            "complete_cell_count": 0,
            "cell_metrics": [],
            "theta_log_rmae": None,
            "geometric_mean_rmae": None,
            "p95_error_ratio": None,
            "unadjusted_p_value": None,
            "holm_adjusted_p_value": None,
            "upper_95_confidence_theta": None,
            "bootstrap_plan_sha256": plan_hash,
            "effect_floor_passed": False,
            "cell_limit_passed": False,
            "p95_limit_passed": False,
            "upper_confidence_passed": False,
            "sample_gate_passed": sample_gate_passed,
            "valid": False,
            "errors": [],
        }
        if missing_cells or unexpected_cells:
            contrast["errors"].append("registered_cells_incomplete")
            contrasts.append(contrast)
            continue
        log_ratios: list[float] = []
        pooled_candidate_errors: list[float] = []
        pooled_baseline_errors: list[float] = []
        cell_summaries: list[dict[str, Any]] = []
        invalid_denominator = False
        for cell in registered_cells:
            cell_rows = cells[cell]
            candidate_errors = np.asarray(
                [row["strategy_metrics"][candidate_id]["absolute_error"] for row in cell_rows],
                dtype=np.float64,
            )
            baseline_errors = np.asarray(
                [row["strategy_metrics"][baseline]["absolute_error"] for row in cell_rows],
                dtype=np.float64,
            )
            candidate_mae = float(np.mean(candidate_errors))
            baseline_mae = float(np.mean(baseline_errors))
            if baseline_mae <= DENOMINATOR_EPSILON:
                invalid_denominator = True
                contrast["errors"].append(
                    f"baseline_mae_denominator_invalid:{cell[0]}:{cell[1]}"
                )
                continue
            ratio = candidate_mae / baseline_mae
            if ratio <= 0.0 or not math.isfinite(ratio):
                contrast["errors"].append(f"cell_rmae_invalid:{cell[0]}:{cell[1]}")
                invalid_denominator = True
                continue
            log_ratios.append(math.log(ratio))
            pooled_candidate_errors.extend(candidate_errors.tolist())
            pooled_baseline_errors.extend(baseline_errors.tolist())
            cell_summaries.append(
                {
                    "series_id": cell[0],
                    "horizon": cell[1],
                    "target_count": len(cell_rows),
                    "candidate_mae": candidate_mae,
                    "baseline_mae": baseline_mae,
                    "rmae": ratio,
                }
            )
        contrast["cell_metrics"] = cell_summaries
        contrast["complete_cell_count"] = len(cell_summaries)
        if invalid_denominator or len(cell_summaries) != len(registered_cells):
            contrasts.append(contrast)
            continue
        baseline_p95 = float(
            np.quantile(np.asarray(pooled_baseline_errors), 0.95, method="linear")
        )
        if baseline_p95 <= DENOMINATOR_EPSILON:
            contrast["errors"].append("baseline_p95_denominator_invalid")
            contrasts.append(contrast)
            continue
        candidate_p95 = float(
            np.quantile(np.asarray(pooled_candidate_errors), 0.95, method="linear")
        )
        p95_ratio = candidate_p95 / baseline_p95
        theta_hat = float(np.mean(np.asarray(log_ratios, dtype=np.float64)))
        contrast["theta_log_rmae"] = theta_hat
        contrast["geometric_mean_rmae"] = math.exp(theta_hat)
        contrast["p95_error_ratio"] = p95_ratio
        contrast["effect_floor_passed"] = theta_hat < math.log(EFFECT_FLOOR_RMAE)
        contrast["cell_limit_passed"] = all(
            item["rmae"] <= CELL_RMAE_LIMIT for item in cell_summaries
        )
        contrast["p95_limit_passed"] = p95_ratio <= P95_ERROR_RATIO_LIMIT
        if not sample_gate_passed:
            contrast["errors"].append("minimum_source_cluster_count_not_met")
            contrasts.append(contrast)
            continue
        if weights is None:
            contrast["errors"].append("bootstrap_plan_unavailable")
            contrasts.append(contrast)
            continue

        theta_boot = np.zeros(replications, dtype=np.float64)
        bootstrap_valid = np.ones(replications, dtype=bool)
        for cell in registered_cells:
            candidate_sum = np.zeros(len(clusters), dtype=np.float64)
            baseline_sum = np.zeros(len(clusters), dtype=np.float64)
            observation_count = np.zeros(len(clusters), dtype=np.float64)
            for row in cells[cell]:
                index = cluster_index[_cluster_key(source, row["target_date"])]
                candidate_sum[index] += row["strategy_metrics"][candidate_id]["absolute_error"]
                baseline_sum[index] += row["strategy_metrics"][baseline]["absolute_error"]
                observation_count[index] += 1.0
            resampled_counts = weights @ observation_count
            resampled_candidate = weights @ candidate_sum
            resampled_baseline = weights @ baseline_sum
            valid = (resampled_counts > 0.0) & (
                resampled_baseline / np.maximum(resampled_counts, 1.0)
                > DENOMINATOR_EPSILON
            )
            bootstrap_valid &= valid
            safe_counts = np.where(resampled_counts > 0.0, resampled_counts, 1.0)
            candidate_mae = resampled_candidate / safe_counts
            baseline_mae = resampled_baseline / safe_counts
            safe_baseline = np.where(
                baseline_mae > DENOMINATOR_EPSILON, baseline_mae, 1.0
            )
            ratio = candidate_mae / safe_baseline
            valid &= np.isfinite(ratio) & (ratio > 0.0)
            bootstrap_valid &= valid
            theta_boot += np.log(np.where(valid, ratio, 1.0))
        if not bool(np.all(bootstrap_valid)):
            contrast["errors"].append("bootstrap_replication_invalid")
            contrasts.append(contrast)
            continue
        theta_boot /= float(len(registered_cells))
        delta_boot = theta_boot - theta_hat
        boundary_distance = theta_hat - math.log(EFFECT_FLOOR_RMAE)
        p_value = (1.0 + float(np.count_nonzero(delta_boot <= boundary_distance))) / (
            replications + 1.0
        )
        upper = theta_hat - float(np.quantile(delta_boot, 0.05, method="linear"))
        contrast["unadjusted_p_value"] = p_value
        contrast["upper_95_confidence_theta"] = upper
        contrast["upper_confidence_passed"] = upper < math.log(EFFECT_FLOOR_RMAE)
        contrast["valid"] = True
        contrasts.append(contrast)

    return {
        "source": source,
        "cluster_grain": bootstrap_contract["cluster_grain"],
        "block_length": bootstrap_contract["block_length"],
        "minimum_cluster_count": bootstrap_contract["minimum_clusters"],
        "observed_cluster_count": len(clusters),
        "sample_gate_passed": sample_gate_passed,
        "registered_cells": [
            {"series_id": series_id, "horizon": horizon}
            for series_id, horizon in registered_cells
        ],
        "missing_cells": missing_cells,
        "unexpected_cells": [
            {"series_id": series_id, "horizon": horizon}
            for series_id, horizon in unexpected_cells
        ],
        "bootstrap_plan_sha256": plan_hash,
        "contrasts": contrasts,
    }


def _period_analysis(
    period_id: str,
    rows: list[dict[str, Any]],
    protocol: dict[str, Any],
    rng: np.random.Generator,
    replications: int,
) -> dict[str, Any]:
    cells = _registered_cells(protocol)
    candidate_id = protocol["candidate"]["registered_family_id"]
    baselines = list(protocol["registered_baselines"])
    arms = [
        _arm_analysis(
            source,
            rows,
            cells[source],
            candidate_id,
            baselines,
            rng,
            replications,
        )
        for source in SOURCE_ARMS
    ]
    contrasts = [
        contrast
        for arm in arms
        for contrast in arm["contrasts"]
    ]
    correction_inputs = [
        contrast["unadjusted_p_value"]
        if contrast["valid"] and contrast["unadjusted_p_value"] is not None
        else 1.0
        for contrast in contrasts
    ]
    adjusted = holm_adjust(correction_inputs)
    for contrast, adjusted_value in zip(contrasts, adjusted):
        contrast["holm_adjusted_p_value"] = adjusted_value
        contrast["all_decision_gates_passed"] = bool(
            contrast["valid"]
            and contrast["sample_gate_passed"]
            and adjusted_value <= SIGNIFICANCE_LEVEL
            and contrast["effect_floor_passed"]
            and contrast["cell_limit_passed"]
            and contrast["p95_limit_passed"]
            and contrast["upper_confidence_passed"]
        )
    for arm in arms:
        arm["all_eight_contrasts_passed"] = len(arm["contrasts"]) == 8 and all(
            contrast["all_decision_gates_passed"] for contrast in arm["contrasts"]
        )
    has_invalid = any(
        contrast["errors"]
        and any("denominator_invalid" in error or "bootstrap_replication_invalid" in error for error in contrast["errors"])
        for contrast in contrasts
    )
    has_incomplete = any(
        arm["missing_cells"] or arm["unexpected_cells"] or not arm["sample_gate_passed"]
        for arm in arms
    )
    supported = all(arm["all_eight_contrasts_passed"] for arm in arms)
    if supported:
        decision = "PERIOD_CRITERIA_SATISFIED"
    elif has_invalid:
        decision = "INVALID"
    elif has_incomplete:
        decision = "INCONCLUSIVE"
    else:
        decision = "PERIOD_CRITERIA_NOT_SATISFIED"
    return {
        "period_id": period_id,
        "settlement_count": len(rows),
        "bootstrap_replications_executed": replications,
        "contrast_order": [
            {"source": source, "baseline_id": baseline}
            for source in SOURCE_ARMS
            for baseline in baselines
        ],
        "arms": arms,
        "decision": decision,
        "period_criteria_satisfied": supported,
    }


def _invalid_report(protocol: Any, errors: list[str]) -> dict[str, Any]:
    return {
        "schema": "time_series_source_native_confirmatory_report.v3",
        "protocol_id": protocol.get("protocol_id") if isinstance(protocol, dict) else None,
        "protocol_payload_sha256": (
            protocol.get("protocol_payload_sha256") if isinstance(protocol, dict) else None
        ),
        "decision": "INVALID",
        "promotion_supported": False,
        "bounded_forecasting_claim_supported": False,
        "claim_text": "No bounded prospective forecasting-accuracy claim is supported.",
        "errors": errors,
        "periods": [],
        "scope_limits": [
            "No economic outcome is established.",
            "No field deployment result is established.",
            "No universal superiority claim is supported.",
        ],
    }


def analyze_confirmatory(
    settlements: Iterable[dict[str, Any]],
    anchor_coverage: dict[str, Any],
    protocol: dict[str, Any],
    *,
    _test_bootstrap_replications: int | None = None,
) -> dict[str, Any]:
    """Run the frozen two-period V3 analysis and return a claim-safe report.

    ``_test_bootstrap_replications`` is the only supported runtime reduction.
    It does not relax the required production protocol value of 20,000 and is
    visibly marked in the report. Production callers must leave it unset.
    """

    protocol_errors = validate_protocol(protocol)
    if protocol_errors:
        return _invalid_report(protocol, protocol_errors)
    try:
        analysis_as_of = _as_utc(
            anchor_coverage.get("analysis_as_of_utc")
            if isinstance(anchor_coverage, dict)
            else None,
            "analysis_as_of_utc",
        )
    except ConfirmatoryInputError as exc:
        return _invalid_report(protocol, [str(exc)])
    first_end = _period_date_bounds(protocol, PERIOD_IDS[0])[1]
    second_end = _period_date_bounds(protocol, PERIOD_IDS[1])[1]
    if analysis_as_of.date() <= first_end:
        return {
            "schema": "time_series_source_native_confirmatory_report.v3",
            "protocol_id": protocol["protocol_id"],
            "protocol_payload_sha256": protocol["protocol_payload_sha256"],
            "analysis_as_of_utc": analysis_as_of.isoformat().replace("+00:00", "Z"),
            "decision": "INCONCLUSIVE_FIRST_PERIOD_OPEN",
            "promotion_supported": False,
            "bounded_forecasting_claim_supported": False,
            "claim_text": "No bounded prospective forecasting-accuracy claim is supported.",
            "errors": [],
            "periods": [],
            "scope_limits": [
                "The first frozen confirmatory period is still open.",
                "No economic outcome is established.",
                "No field deployment result is established.",
                "No universal superiority claim is supported.",
            ],
        }
    replications = BOOTSTRAP_REPLICATIONS
    test_override_used = _test_bootstrap_replications is not None
    if test_override_used:
        if (
            not isinstance(_test_bootstrap_replications, int)
            or isinstance(_test_bootstrap_replications, bool)
            or _test_bootstrap_replications <= 0
            or _test_bootstrap_replications > BOOTSTRAP_REPLICATIONS
        ):
            return _invalid_report(protocol, ["test_bootstrap_replications_invalid"])
        replications = _test_bootstrap_replications
    try:
        rows = list(settlements)
        periods = split_nonoverlapping_replication_periods(rows, anchor_coverage, protocol)
    except ConfirmatoryInputError as exc:
        return _invalid_report(protocol, str(exc).split(";"))

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    first = _period_analysis(
        PERIOD_IDS[0], periods[PERIOD_IDS[0]], protocol, rng, replications
    )
    reports = [first]
    replication_boundary_present = analysis_as_of.date() > second_end
    second: dict[str, Any] | None = None
    if replication_boundary_present:
        second = _period_analysis(
            PERIOD_IDS[1], periods[PERIOD_IDS[1]], protocol, rng, replications
        )
        reports.append(second)

    boundary_consistent = first["period_criteria_satisfied"]
    if not boundary_consistent:
        decision = (
            "INVALID"
            if first["decision"] == "INVALID"
            else first["decision"]
        )
        promotion = False
    elif second is None:
        decision = "INCONCLUSIVE_REPLICATION_REQUIRED"
        promotion = False
    elif second["period_criteria_satisfied"]:
        decision = "PROMOTION_SUPPORTED"
        promotion = True
    elif second["decision"] == "INVALID":
        decision = "INVALID"
        promotion = False
    elif second["decision"] == "INCONCLUSIVE":
        decision = "INCONCLUSIVE"
        promotion = False
    else:
        decision = "REPLICATION_CRITERIA_NOT_SATISFIED"
        promotion = False

    claim_text = (
        "The registered candidate satisfied the frozen forecasting-accuracy criteria "
        "in two nonoverlapping independently anchored periods for only the named "
        "sources, series, horizons, baselines, and cutoffs."
        if promotion
        else "No bounded prospective forecasting-accuracy claim is supported."
    )
    return {
        "schema": "time_series_source_native_confirmatory_report.v3",
        "protocol_id": protocol["protocol_id"],
        "protocol_payload_sha256": protocol["protocol_payload_sha256"],
        "candidate_id": protocol["candidate"]["registered_family_id"],
        "source_order": list(SOURCE_ARMS),
        "baseline_order": list(protocol["registered_baselines"]),
        "bootstrap_seed": BOOTSTRAP_SEED,
        "production_bootstrap_replications_required": BOOTSTRAP_REPLICATIONS,
        "bootstrap_replications_executed": replications,
        "test_only_replication_override_used": test_override_used,
        "first_period_boundary_consistent": boundary_consistent,
        "decision": decision,
        "promotion_supported": promotion,
        "bounded_forecasting_claim_supported": promotion,
        "claim_text": claim_text,
        "errors": [],
        "periods": reports,
        "scope_limits": [
            "No economic outcome is established.",
            "No field deployment result is established.",
            "No universal superiority claim is supported.",
        ],
    }


__all__ = [
    "BOOTSTRAP_REPLICATIONS",
    "BOOTSTRAP_SEED",
    "ConfirmatoryInputError",
    "analyze_confirmatory",
    "canonical_sha256",
    "holm_adjust",
    "protocol_payload_sha256",
    "split_nonoverlapping_replication_periods",
    "validate_protocol",
]
