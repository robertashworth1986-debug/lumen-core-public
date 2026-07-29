from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = (
    ROOT / "config" / "market_signal_source_native_benchmark_protocol_v1.json"
)
OUT_JSON = (
    ROOT / "out" / "ops" / "market_signal_source_native_benchmark_latest.json"
)
DASHBOARD_JSON = (
    ROOT / "dashboard" / "data" / "market_signal_source_native_benchmark.json"
)
MANIFEST_JSON = (
    ROOT
    / "out"
    / "ops"
    / "market_signal_source_native_benchmark_manifest_latest.json"
)
DOC_PATH = (
    ROOT / "docs" / "MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK_2026-07-29.md"
)

EXPECTED_CANDIDATE_IDS = (
    "beast_strategy_trend",
    "beast_strategy_mean_revert",
    "beast_strategy_breakout",
    "beast_strategy_regime_switch",
)
EXPECTED_BASELINE_IDS = (
    "buy_and_hold",
    "moving_average_cross",
    "ridge_return_baseline",
    "volatility_targeting",
)
EXPECTED_SOURCES = ("KRAKEN_PUBLIC", "TWELVE_DATA", "ALPHAVANTAGE")

BOUNDARY = (
    "Exploratory retrospective paper/replay only. This sidecar does not establish "
    "alpha, edge, profit, value, field performance, prospective validity, "
    "execution quality, or live-trading authority. No external action is allowed."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=True)
        + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def as_float(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected numeric value, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"Expected finite numeric value, got {value!r}")
    return result


def rounded(value: float, digits: int = 12) -> float:
    if not math.isfinite(value):
        return 0.0
    return round(float(value), digits)


def sample_std(values: list[float]) -> float:
    return stdev(values) if len(values) >= 2 else 0.0


def trailing_mean(values: list[float]) -> float:
    return mean(values) if values else 0.0


def sign_position(
    value: float,
    long_position: float = 1.0,
    short_position: float = -1.0,
    neutral_position: float = 0.0,
) -> float:
    if value > 0.0:
        return long_position
    if value < 0.0:
        return short_position
    return neutral_position


def solve_linear_system(matrix: list[list[float]], target: list[float]) -> list[float]:
    size = len(target)
    augmented = [
        [float(matrix[row][column]) for column in range(size)]
        + [float(target[row])]
        for row in range(size)
    ]
    for column in range(size):
        pivot = max(
            range(column, size),
            key=lambda row: abs(augmented[row][column]),
        )
        if abs(augmented[pivot][column]) < 1e-15:
            raise ValueError("Singular ridge system")
        augmented[column], augmented[pivot] = (
            augmented[pivot],
            augmented[column],
        )
        divisor = augmented[column][column]
        augmented[column] = [value / divisor for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                augmented[row][index] - factor * augmented[column][index]
                for index in range(size + 1)
            ]
    return [augmented[row][-1] for row in range(size)]


def ridge_prediction(
    returns: list[float],
    evaluation_index: int,
    parameters: dict[str, Any],
) -> float:
    lag_count = int(parameters["return_lags"])
    training_window = int(parameters["training_window"])
    minimum_samples = int(parameters["minimum_training_samples"])
    ridge_lambda = as_float(parameters["ridge_lambda"])
    start = max(lag_count, evaluation_index - training_window)
    training_indices = list(range(start, evaluation_index))
    if len(training_indices) < minimum_samples:
        return 0.0

    feature_count = lag_count + 1
    xtx = [[0.0] * feature_count for _ in range(feature_count)]
    xty = [0.0] * feature_count
    for target_index in training_indices:
        features = [1.0] + [
            returns[target_index - lag] for lag in range(1, lag_count + 1)
        ]
        target = returns[target_index]
        for row in range(feature_count):
            xty[row] += features[row] * target
            for column in range(feature_count):
                xtx[row][column] += features[row] * features[column]
    for index in range(1, feature_count):
        xtx[index][index] += ridge_lambda

    coefficients = solve_linear_system(xtx, xty)
    current_features = [1.0] + [
        returns[evaluation_index - lag]
        for lag in range(1, lag_count + 1)
    ]
    return sum(
        coefficient * feature
        for coefficient, feature in zip(coefficients, current_features)
    )


def candidate_position(
    strategy_id: str,
    closes: list[float],
    returns: list[float],
    index: int,
    definitions: dict[str, dict[str, Any]],
) -> float:
    definition = definitions[strategy_id]
    parameters = definition["parameters"]
    if strategy_id == "beast_strategy_trend":
        fast = int(parameters["fast_return_lookback"])
        slow = int(parameters["slow_return_lookback"])
        fast_mean = trailing_mean(returns[index - fast : index])
        slow_mean = trailing_mean(returns[index - slow : index])
        return sign_position(
            fast_mean - slow_mean,
            as_float(parameters["long_position"]),
            as_float(parameters["short_position"]),
        )
    if strategy_id == "beast_strategy_mean_revert":
        lookback = int(parameters["reference_return_lookback"])
        reference = returns[index - lookback - 1 : index - 1]
        reference_std = sample_std(reference)
        zscore = (
            (returns[index - 1] - trailing_mean(reference)) / reference_std
            if reference_std > 0.0
            else 0.0
        )
        threshold = as_float(parameters["entry_zscore"])
        if zscore < -threshold:
            return as_float(parameters["long_position"])
        if zscore > threshold:
            return as_float(parameters["short_position"])
        return as_float(parameters["neutral_position"])
    if strategy_id == "beast_strategy_breakout":
        lookback = int(parameters["channel_lookback"])
        channel = closes[index - lookback - 1 : index - 1]
        observed = closes[index - 1]
        if observed > max(channel):
            return as_float(parameters["long_position"])
        if observed < min(channel):
            return as_float(parameters["short_position"])
        return as_float(parameters["neutral_position"])
    if strategy_id == "beast_strategy_regime_switch":
        fast = int(parameters["fast_volatility_lookback"])
        slow = int(parameters["slow_volatility_lookback"])
        fast_volatility = sample_std(returns[index - fast : index])
        slow_volatility = sample_std(returns[index - slow : index])
        selected = (
            str(parameters["trend_family_id"])
            if fast_volatility > slow_volatility
            else str(parameters["mean_revert_family_id"])
        )
        return candidate_position(
            selected, closes, returns, index, definitions
        )
    raise ValueError(f"Unsupported candidate strategy: {strategy_id}")


def baseline_position(
    strategy_id: str,
    closes: list[float],
    returns: list[float],
    index: int,
    definition: dict[str, Any],
    periods_per_year: int,
) -> float:
    parameters = definition["parameters"]
    if strategy_id == "buy_and_hold":
        return as_float(parameters["position"])
    if strategy_id == "moving_average_cross":
        fast = int(parameters["fast_close_lookback"])
        slow = int(parameters["slow_close_lookback"])
        fast_mean = trailing_mean(closes[index - fast : index])
        slow_mean = trailing_mean(closes[index - slow : index])
        return sign_position(
            fast_mean - slow_mean,
            as_float(parameters["long_position"]),
            as_float(parameters["short_position"]),
        )
    if strategy_id == "ridge_return_baseline":
        prediction = ridge_prediction(returns, index, parameters)
        return sign_position(
            prediction,
            as_float(parameters["long_position"]),
            as_float(parameters["short_position"]),
            as_float(parameters["neutral_position"]),
        )
    if strategy_id == "volatility_targeting":
        lookback = int(parameters["volatility_lookback"])
        realized_period_volatility = sample_std(
            returns[index - lookback : index]
        )
        minimum_volatility = as_float(parameters["minimum_volatility"])
        if realized_period_volatility <= minimum_volatility:
            return 0.0
        target_period_volatility = as_float(
            parameters["target_annual_volatility"]
        ) / math.sqrt(periods_per_year)
        return min(
            as_float(parameters["maximum_leverage"]),
            target_period_volatility / realized_period_volatility,
        )
    raise ValueError(f"Unsupported baseline strategy: {strategy_id}")


def maximum_drawdown(net_returns: list[float]) -> float:
    equity = 1.0
    peak = 1.0
    maximum = 0.0
    for value in net_returns:
        equity *= max(0.0, 1.0 + value)
        peak = max(peak, equity)
        drawdown = 0.0 if peak <= 0.0 else (peak - equity) / peak
        maximum = max(maximum, drawdown)
    return maximum


def cumulative_return(values: list[float]) -> float:
    equity = 1.0
    for value in values:
        equity *= max(0.0, 1.0 + value)
    return equity - 1.0


def strategy_metrics(
    positions: list[float],
    future_returns: list[float],
    cost_rate: float,
    initial_position: float,
) -> tuple[dict[str, Any], dict[str, str]]:
    if len(positions) != len(future_returns):
        raise ValueError("Positions and future returns are not aligned")
    previous_position = initial_position
    turnovers: list[float] = []
    costs: list[float] = []
    gross_returns: list[float] = []
    net_returns: list[float] = []
    for position, future_return in zip(positions, future_returns):
        turnover = abs(position - previous_position)
        cost = cost_rate * turnover
        gross_return = position * future_return
        net_return = gross_return - cost
        turnovers.append(turnover)
        costs.append(cost)
        gross_returns.append(gross_return)
        net_returns.append(net_return)
        previous_position = position

    volatility = sample_std(net_returns)
    score = mean(net_returns) / volatility if volatility > 0.0 else 0.0
    metrics = {
        "observation_count": len(net_returns),
        "gross_cumulative_paper_return": rounded(
            cumulative_return(gross_returns)
        ),
        "net_cumulative_paper_return": rounded(
            cumulative_return(net_returns)
        ),
        "mean_paper_net_return": rounded(
            mean(net_returns) if net_returns else 0.0
        ),
        "paper_net_return_standard_deviation": rounded(volatility),
        "risk_adjusted_score": rounded(score),
        "maximum_drawdown": rounded(maximum_drawdown(net_returns)),
        "total_turnover": rounded(sum(turnovers)),
        "mean_turnover": rounded(
            mean(turnovers) if turnovers else 0.0
        ),
        "total_assumed_cost": rounded(sum(costs)),
        "mean_assumed_cost": rounded(mean(costs) if costs else 0.0),
        "positive_net_return_rate": rounded(
            (
                sum(1 for value in net_returns if value > 0.0)
                / len(net_returns)
            )
            if net_returns
            else 0.0
        ),
    }
    hashes = {
        "position_sha256": stable_sha256(
            [rounded(value) for value in positions]
        ),
        "gross_paper_return_sha256": stable_sha256(
            [rounded(value) for value in gross_returns]
        ),
        "net_paper_return_sha256": stable_sha256(
            [rounded(value) for value in net_returns]
        ),
        "turnover_sha256": stable_sha256(
            [rounded(value) for value in turnovers]
        ),
        "cost_sha256": stable_sha256(
            [rounded(value) for value in costs]
        ),
    }
    return metrics, hashes


def exact_two_sided_sign_test(deltas: list[float]) -> float:
    wins = sum(1 for value in deltas if value > 0.0)
    losses = sum(1 for value in deltas if value < 0.0)
    non_ties = wins + losses
    if non_ties == 0:
        return 1.0
    tail = min(wins, losses)
    probability = sum(
        math.comb(non_ties, count) for count in range(tail + 1)
    ) / (2**non_ties)
    return min(1.0, 2.0 * probability)


def apply_global_holm(
    comparisons: list[dict[str, Any]], alpha: float
) -> None:
    ordered = sorted(
        enumerate(comparisons),
        key=lambda item: (
            as_float(item[1]["raw_cluster_sign_test_p_value"]),
            str(item[1]["candidate_family_id"]),
            str(item[1]["source"]),
            str(item[1]["baseline_id"]),
        ),
    )
    comparison_count = len(ordered)
    running_max = 0.0
    for rank, (original_index, comparison) in enumerate(ordered, start=1):
        adjusted = min(
            1.0,
            (comparison_count - rank + 1)
            * as_float(comparison["raw_cluster_sign_test_p_value"]),
        )
        running_max = max(running_max, adjusted)
        comparisons[original_index]["global_holm_adjusted_p_value"] = rounded(
            running_max
        )
        comparisons[original_index][
            "statistically_positive_after_global_holm"
        ] = bool(
            as_float(comparison["mean_risk_adjusted_score_delta"]) > 0.0
            and running_max < alpha
        )


def verify_embedded_snapshot_hash(snapshot: dict[str, Any]) -> str:
    observed = str(snapshot.get("sha256", ""))
    without_hash = {
        key: value for key, value in snapshot.items() if key != "sha256"
    }
    computed = stable_sha256(without_hash)
    if observed != computed:
        raise ValueError(
            "Snapshot embedded SHA-256 does not match canonical content"
        )
    return computed


def registered_snapshot_map(
    wiring_matrix: dict[str, Any],
) -> dict[str, tuple[str, str]]:
    market_lane = next(
        (
            row
            for row in wiring_matrix.get("matrix", [])
            if isinstance(row, dict)
            and row.get("lane") == "market_signal_geometry"
        ),
        None,
    )
    if market_lane is None:
        raise ValueError("Market-signal lane missing from source wiring matrix")

    found: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for source_row in market_lane.get("direct_measured_replay_sources", []):
        if not isinstance(source_row, dict):
            continue
        source = str(source_row.get("source", "")).upper()
        path = str(source_row.get("snapshot_json", ""))
        digest = str(source_row.get("snapshot_sha256", ""))
        baselines = tuple(source_row.get("source_specific_baselines", []))
        if set(baselines) != set(EXPECTED_BASELINE_IDS):
            raise ValueError(
                f"Source-specific baseline set differs for {source}"
            )
        if (
            source_row.get("measured_and_qualified") is not True
            or source_row.get("direct_performance_input_allowed") is not True
        ):
            raise ValueError(
                f"Direct market source is not qualified for replay: {source}"
            )
        if source and path and digest:
            found[source].add((path, digest))
    result: dict[str, tuple[str, str]] = {}
    for source in EXPECTED_SOURCES:
        references = found.get(source, set())
        if len(references) != 1:
            raise ValueError(
                f"Expected one registered snapshot for {source}, found "
                f"{len(references)}"
            )
        result[source] = next(iter(references))
    return result


def validate_protocol(
    protocol: dict[str, Any],
    registry: dict[str, Any],
    wiring_matrix: dict[str, Any],
) -> None:
    if (
        protocol.get("schema")
        != "market_signal_source_native_benchmark_protocol_v1"
    ):
        raise ValueError("Unexpected protocol schema")
    candidate_ids = tuple(
        str(row.get("family_id", ""))
        for row in protocol.get("candidates", [])
        if isinstance(row, dict)
    )
    baseline_ids = tuple(
        str(row.get("baseline_id", ""))
        for row in protocol.get("baselines", [])
        if isinstance(row, dict)
    )
    source_ids = tuple(
        str(row.get("source", "")).upper()
        for row in protocol.get("sources", [])
        if isinstance(row, dict)
    )
    if candidate_ids != EXPECTED_CANDIDATE_IDS:
        raise ValueError("Candidate set or ordering differs from protocol v1")
    if baseline_ids != EXPECTED_BASELINE_IDS:
        raise ValueError("Baseline set or ordering differs from protocol v1")
    if source_ids != EXPECTED_SOURCES:
        raise ValueError("Source set or ordering differs from protocol v1")
    if not protocol.get("evaluation", {}).get(
        "no_parameter_tuning_on_evaluation"
    ):
        raise ValueError("Evaluation tuning must be disabled")
    if any(bool(value) for value in protocol.get("claim_controls", {}).values()):
        raise ValueError("Every external/performance claim control must fail closed")

    family_rows = {
        str(row.get("id", "")): row
        for row in registry.get("families", [])
        if isinstance(row, dict)
    }
    for candidate_id in candidate_ids:
        row = family_rows.get(candidate_id)
        if not row or row.get("lane") != "market_signal_geometry":
            raise ValueError(
                f"Candidate is not registered in market_signal_geometry: "
                f"{candidate_id}"
            )
    registered_baselines = tuple(
        registry.get("lanes", {})
        .get("market_signal_geometry", {})
        .get("baselines", [])
    )
    if set(baseline_ids) != set(registered_baselines):
        raise ValueError("Protocol baselines differ from the registry lane")

    registered = registered_snapshot_map(wiring_matrix)
    for source_row in protocol["sources"]:
        source = str(source_row["source"]).upper()
        expected = (
            str(source_row["snapshot_path"]),
            str(source_row["snapshot_embedded_sha256"]),
        )
        if registered[source] != expected:
            raise ValueError(
                f"Protocol snapshot differs from source wiring matrix: {source}"
            )


def extract_series(
    snapshot: dict[str, Any], source_definition: dict[str, Any]
) -> list[dict[str, Any]]:
    series_field = str(source_definition["series_field"])
    timestamp_field = str(source_definition["timestamp_field"])
    close_field = str(source_definition["close_field"])
    grouped: dict[str, dict[str, float]] = defaultdict(dict)
    input_row_counts: dict[str, int] = defaultdict(int)
    for row in snapshot.get("rows", []):
        if not isinstance(row, dict):
            continue
        series_id = str(row.get(series_field, "")).strip()
        timestamp = str(row.get(timestamp_field, "")).strip()
        if not series_id or not timestamp:
            continue
        input_row_counts[series_id] += 1
        close = as_float(row.get(close_field))
        if close <= 0.0:
            raise ValueError(
                f"Non-positive close in {source_definition['source']} "
                f"{series_id} at {timestamp}"
            )
        if timestamp in grouped[series_id]:
            raise ValueError(
                f"Duplicate timestamp in {source_definition['source']} "
                f"{series_id}: {timestamp}"
            )
        grouped[series_id][timestamp] = close

    extracted: list[dict[str, Any]] = []
    for series_id in sorted(grouped):
        ordered = sorted(grouped[series_id].items(), key=lambda item: item[0])
        extracted.append(
            {
                "series_id": series_id,
                "input_row_count": input_row_counts[series_id],
                "timestamps": [timestamp for timestamp, _ in ordered],
                "closes": [close for _, close in ordered],
            }
        )
    if not extracted:
        raise ValueError(
            f"No usable series in snapshot: {source_definition['source']}"
        )
    return extracted


def strategy_definitions(
    protocol: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    candidates = {
        str(row["family_id"]): row for row in protocol["candidates"]
    }
    baselines = {
        str(row["baseline_id"]): row for row in protocol["baselines"]
    }
    return candidates, baselines


def evaluate_series(
    source_definition: dict[str, Any],
    series: dict[str, Any],
    protocol: dict[str, Any],
) -> dict[str, Any]:
    closes = [as_float(value) for value in series["closes"]]
    timestamps = [str(value) for value in series["timestamps"]]
    returns = [0.0] + [
        closes[index] / closes[index - 1] - 1.0
        for index in range(1, len(closes))
    ]
    warmup = int(protocol["evaluation"]["warmup_observations"])
    if len(closes) <= warmup:
        raise ValueError(
            f"Insufficient rows for {source_definition['source']} "
            f"{series['series_id']}: {len(closes)} <= {warmup}"
        )
    evaluation_indices = list(range(warmup, len(closes)))
    evaluation_timestamps = [timestamps[index] for index in evaluation_indices]
    future_returns = [returns[index] for index in evaluation_indices]
    future_return_hash = stable_sha256(
        [rounded(value) for value in future_returns]
    )
    timestamp_hash = stable_sha256(evaluation_timestamps)
    candidate_definitions, baseline_definitions = strategy_definitions(protocol)
    cost_bps = as_float(source_definition["cost_bps_per_unit_turnover"])
    cost_rate = cost_bps / 10000.0
    initial_position = as_float(protocol["evaluation"]["initial_position"])
    periods_per_year = int(source_definition["periods_per_year"])

    strategy_rows: list[dict[str, Any]] = []
    for strategy_id in EXPECTED_CANDIDATE_IDS + EXPECTED_BASELINE_IDS:
        if strategy_id in candidate_definitions:
            role = "candidate"
            definition = candidate_definitions[strategy_id]
            position_function: Callable[[int], float] = lambda index, sid=strategy_id: candidate_position(
                sid,
                closes,
                returns,
                index,
                candidate_definitions,
            )
        else:
            role = "baseline"
            definition = baseline_definitions[strategy_id]
            position_function = lambda index, sid=strategy_id, row=definition: baseline_position(
                sid,
                closes,
                returns,
                index,
                row,
                periods_per_year,
            )
        positions = [
            max(-1.0, min(1.0, as_float(position_function(index))))
            for index in evaluation_indices
        ]
        metrics, hashes = strategy_metrics(
            positions,
            future_returns,
            cost_rate,
            initial_position,
        )
        strategy_rows.append(
            {
                "strategy_id": strategy_id,
                "role": role,
                "implementation_id": definition["implementation_id"],
                "parameters": definition["parameters"],
                "cost_bps_per_unit_turnover": cost_bps,
                "future_return_sha256": future_return_hash,
                "evaluation_timestamp_sha256": timestamp_hash,
                "metrics": metrics,
                "sequence_hashes": hashes,
                "claim_allowed": false_claim_controls(),
            }
        )

    return {
        "source": str(source_definition["source"]),
        "series_id": str(series["series_id"]),
        "input_row_count": int(series["input_row_count"]),
        "usable_price_observation_count": len(closes),
        "evaluation_observation_count": len(evaluation_indices),
        "evaluation_start_timestamp": evaluation_timestamps[0],
        "evaluation_end_timestamp": evaluation_timestamps[-1],
        "future_return_sha256": future_return_hash,
        "evaluation_timestamp_sha256": timestamp_hash,
        "cost_bps_per_unit_turnover": cost_bps,
        "cost_note": str(source_definition["cost_note"]),
        "strategy_results": strategy_rows,
    }


def false_claim_controls() -> dict[str, bool]:
    return {
        "alpha_claim_allowed": False,
        "edge_claim_allowed": False,
        "profit_claim_allowed": False,
        "field_performance_claim_allowed": False,
        "live_trading_allowed": False,
        "external_action_allowed": False,
    }


def build_comparisons(
    series_results: list[dict[str, Any]],
    protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in series_results:
        grouped[str(row["source"])].append(row)
    comparisons: list[dict[str, Any]] = []
    minimum_clusters = int(
        protocol["inference"]["minimum_clusters_for_interpretable_inference"]
    )
    for source in EXPECTED_SOURCES:
        source_series = grouped[source]
        for candidate_id in EXPECTED_CANDIDATE_IDS:
            for baseline_id in EXPECTED_BASELINE_IDS:
                cluster_rows: list[dict[str, Any]] = []
                for series_row in source_series:
                    strategies = {
                        row["strategy_id"]: row
                        for row in series_row["strategy_results"]
                    }
                    candidate_score = as_float(
                        strategies[candidate_id]["metrics"][
                            "risk_adjusted_score"
                        ]
                    )
                    baseline_score = as_float(
                        strategies[baseline_id]["metrics"][
                            "risk_adjusted_score"
                        ]
                    )
                    cluster_rows.append(
                        {
                            "cluster_id": (
                                f"{source}::{series_row['series_id']}"
                            ),
                            "candidate_risk_adjusted_score": candidate_score,
                            "baseline_risk_adjusted_score": baseline_score,
                            "risk_adjusted_score_delta": rounded(
                                candidate_score - baseline_score
                            ),
                            "shared_future_return_sha256": series_row[
                                "future_return_sha256"
                            ],
                            "observation_count": series_row[
                                "evaluation_observation_count"
                            ],
                        }
                    )
                deltas = [
                    as_float(row["risk_adjusted_score_delta"])
                    for row in cluster_rows
                ]
                cluster_count = len(cluster_rows)
                raw_p_value = (
                    exact_two_sided_sign_test(deltas)
                    if cluster_count >= minimum_clusters
                    else 1.0
                )
                comparisons.append(
                    {
                        "candidate_family_id": candidate_id,
                        "source": source,
                        "baseline_id": baseline_id,
                        "paired_unit": "source_series",
                        "source_series_cluster_count": cluster_count,
                        "minimum_clusters_for_interpretable_inference": (
                            minimum_clusters
                        ),
                        "inference_sufficient": (
                            cluster_count >= minimum_clusters
                        ),
                        "insufficiency_reason": (
                            ""
                            if cluster_count >= minimum_clusters
                            else (
                                f"{cluster_count} source-series cluster(s); "
                                f"protocol requires {minimum_clusters}"
                            )
                        ),
                        "cluster_rows": cluster_rows,
                        "mean_risk_adjusted_score_delta": rounded(
                            mean(deltas) if deltas else 0.0
                        ),
                        "candidate_beats_baseline_mean": bool(
                            deltas and mean(deltas) > 0.0
                        ),
                        "raw_cluster_sign_test_p_value": rounded(raw_p_value),
                        "global_holm_adjusted_p_value": None,
                        "statistically_positive_after_global_holm": False,
                    }
                )
    apply_global_holm(
        comparisons,
        as_float(protocol["inference"]["familywise_alpha"]),
    )
    return comparisons


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    protocol = read_json(PROTOCOL_PATH)
    wiring_matrix_path = ROOT / protocol["inputs"]["source_wiring_matrix"]
    registry_path = ROOT / protocol["inputs"]["family_registry"]
    wiring_matrix = read_json(wiring_matrix_path)
    registry = read_json(registry_path)
    validate_protocol(protocol, registry, wiring_matrix)

    candidate_definitions, baseline_definitions = strategy_definitions(protocol)
    registered_references = registered_snapshot_map(wiring_matrix)
    source_inputs: list[dict[str, Any]] = []
    series_results: list[dict[str, Any]] = []
    for source_definition in protocol["sources"]:
        source = str(source_definition["source"]).upper()
        snapshot_path = ROOT / str(source_definition["snapshot_path"])
        snapshot = read_json(snapshot_path)
        computed_embedded_hash = verify_embedded_snapshot_hash(snapshot)
        expected_path, expected_hash = registered_references[source]
        if str(source_definition["snapshot_path"]) != expected_path:
            raise ValueError(f"Snapshot path drift for {source}")
        if computed_embedded_hash != expected_hash:
            raise ValueError(f"Snapshot content drift for {source}")
        if str(snapshot.get("source", "")).upper() != source:
            raise ValueError(f"Snapshot source label drift for {source}")
        extracted = extract_series(snapshot, source_definition)
        source_inputs.append(
            {
                "source": source,
                "path": str(source_definition["snapshot_path"]),
                "file_sha256": file_sha256(snapshot_path),
                "embedded_canonical_sha256": computed_embedded_hash,
                "registered_wiring_matrix_sha256": expected_hash,
                "embedded_hash_verified": True,
                "registered_reference_verified": True,
                "snapshot_row_count": int(snapshot.get("row_count", 0)),
                "series_count": len(extracted),
                "series_ids": [row["series_id"] for row in extracted],
            }
        )
        for series in extracted:
            series_results.append(
                evaluate_series(source_definition, series, protocol)
            )

    comparisons = build_comparisons(series_results, protocol)
    alpha = as_float(protocol["inference"]["familywise_alpha"])
    global_positive = [
        row
        for row in comparisons
        if row["statistically_positive_after_global_holm"]
    ]
    candidate_passes = []
    for candidate_id in EXPECTED_CANDIDATE_IDS:
        candidate_rows = [
            row
            for row in comparisons
            if row["candidate_family_id"] == candidate_id
        ]
        if candidate_rows and all(
            row["statistically_positive_after_global_holm"]
            for row in candidate_rows
        ):
            candidate_passes.append(candidate_id)

    payload: dict[str, Any] = {
        "schema": "market_signal_source_native_benchmark_v1",
        "protocol_id": protocol["protocol_id"],
        "generated_utc": generated_utc or now_utc(),
        "mode": protocol["mode"],
        "status": (
            "EXPLORATORY_RETROSPECTIVE_NEGATIVE_OR_INSUFFICIENT_EVIDENCE"
        ),
        "boundary": BOUNDARY,
        "claim_controls": protocol["claim_controls"],
        "inputs": {
            "protocol": {
                "path": str(PROTOCOL_PATH.relative_to(ROOT)).replace("\\", "/"),
                "file_sha256": file_sha256(PROTOCOL_PATH),
                "canonical_sha256": stable_sha256(protocol),
            },
            "source_wiring_matrix": {
                "path": str(wiring_matrix_path.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "file_sha256": file_sha256(wiring_matrix_path),
                "schema": str(wiring_matrix.get("schema", "")),
                "matrix_sha256": stable_sha256(wiring_matrix),
            },
            "family_registry": {
                "path": str(registry_path.relative_to(ROOT)).replace("\\", "/"),
                "file_sha256": file_sha256(registry_path),
                "canonical_sha256": stable_sha256(registry),
            },
            "source_snapshots": source_inputs,
        },
        "protocol_summary": {
            "warmup_observations": int(
                protocol["evaluation"]["warmup_observations"]
            ),
            "no_parameter_tuning_on_evaluation": True,
            "signal_timing": protocol["evaluation"]["signal_timing"],
            "future_return_definition": protocol["evaluation"][
                "future_return_definition"
            ],
            "risk_adjusted_score_definition": protocol["evaluation"][
                "risk_adjusted_score_definition"
            ],
            "inference": protocol["inference"],
        },
        "implementation_summary": {
            "registered_candidate_count": len(EXPECTED_CANDIDATE_IDS),
            "implemented_candidate_count": len(candidate_definitions),
            "missing_candidate_implementation_count": (
                len(EXPECTED_CANDIDATE_IDS) - len(candidate_definitions)
            ),
            "registered_baseline_count": len(EXPECTED_BASELINE_IDS),
            "implemented_baseline_count": len(baseline_definitions),
            "missing_baseline_implementation_count": (
                len(EXPECTED_BASELINE_IDS) - len(baseline_definitions)
            ),
            "candidate_ids": list(EXPECTED_CANDIDATE_IDS),
            "baseline_ids": list(EXPECTED_BASELINE_IDS),
            "source_count": len(source_inputs),
            "source_series_count": len(series_results),
            "strategy_source_series_result_count": sum(
                len(row["strategy_results"]) for row in series_results
            ),
        },
        "series_results": series_results,
        "comparisons": comparisons,
        "negative_result_summary": {
            "candidate_source_baseline_comparison_count": len(comparisons),
            "comparison_mean_win_count": sum(
                1
                for row in comparisons
                if row["candidate_beats_baseline_mean"]
            ),
            "global_holm_positive_count": len(global_positive),
            "global_holm_nonpositive_count": (
                len(comparisons) - len(global_positive)
            ),
            "inference_insufficient_comparison_count": sum(
                1 for row in comparisons if not row["inference_sufficient"]
            ),
            "candidate_beats_every_source_baseline_after_global_holm_count": (
                len(candidate_passes)
            ),
            "candidate_passes": candidate_passes,
            "familywise_alpha": alpha,
            "conclusion": (
                "No candidate is promoted. Current snapshots contain one "
                "series per source, so every candidate-source-baseline "
                "comparison is inferentially insufficient under the "
                "predeclared source-series cluster rule."
            ),
        },
        "external_actions": [],
    }
    payload["payload_sha256"] = stable_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    implementation = payload["implementation_summary"]
    negative = payload["negative_result_summary"]
    lines = [
        "# Market-Signal Source-Native Benchmark",
        "",
        f"Protocol: `{payload['protocol_id']}`",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Status: `{payload['status']}`",
        f"Output payload SHA-256: `{payload['payload_sha256']}`",
        "",
        "## Decision",
        "",
        "**No candidate is promoted.**",
        "",
        payload["boundary"],
        "",
        "## Fixed Scope",
        "",
        f"- Registered candidates: `{implementation['registered_candidate_count']}`",
        f"- Implemented candidates: `{implementation['implemented_candidate_count']}`",
        f"- Missing candidate implementations: `{implementation['missing_candidate_implementation_count']}`",
        f"- Registered baselines: `{implementation['registered_baseline_count']}`",
        f"- Implemented baselines: `{implementation['implemented_baseline_count']}`",
        f"- Sources: `{implementation['source_count']}`",
        f"- Source series: `{implementation['source_series_count']}`",
        f"- Strategy/source-series results: `{implementation['strategy_source_series_result_count']}`",
        f"- Candidate/source/baseline comparisons: `{negative['candidate_source_baseline_comparison_count']}`",
        f"- Globally Holm-positive comparisons: `{negative['global_holm_positive_count']}`",
        f"- Candidates passing every source-native baseline: `{negative['candidate_beats_every_source_baseline_after_global_holm_count']}`",
        "",
        "No parameter was selected or tuned on the evaluation observations. "
        "Every position applied to `return[t]` uses only information available "
        "through `t-1`.",
        "",
        "## Input Custody",
        "",
        "| Source | Registered snapshot | Rows | Series | Embedded SHA-256 verified |",
        "|---|---|---:|---:|---|",
    ]
    for row in payload["inputs"]["source_snapshots"]:
        lines.append(
            f"| {row['source']} | `{row['path']}` | "
            f"{row['snapshot_row_count']} | {row['series_count']} | "
            f"`{str(row['embedded_hash_verified']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "The builder independently recomputes each snapshot's canonical "
            "embedded hash and requires an exact match to the snapshot reference "
            "in the qualified source wiring matrix.",
            "",
            "## Implementations",
            "",
            "| Role | Registered ID | Fixed implementation |",
            "|---|---|---|",
        ]
    )
    for series_row in payload["series_results"][:1]:
        for strategy in series_row["strategy_results"]:
            lines.append(
                f"| {strategy['role']} | `{strategy['strategy_id']}` | "
                f"`{strategy['implementation_id']}` |"
            )
    lines.extend(
        [
            "",
            "## Per-Source and Per-Series Results",
            "",
            "| Source | Series | Strategy | Role | Obs | Cost bps | Turnover | Assumed cost | Max drawdown | Risk-adjusted score | Net paper return |",
            "|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for series_row in payload["series_results"]:
        for strategy in series_row["strategy_results"]:
            metrics = strategy["metrics"]
            lines.append(
                f"| {series_row['source']} | `{series_row['series_id']}` | "
                f"`{strategy['strategy_id']}` | {strategy['role']} | "
                f"{metrics['observation_count']} | "
                f"{strategy['cost_bps_per_unit_turnover']:.2f} | "
                f"{metrics['total_turnover']:.6f} | "
                f"{metrics['total_assumed_cost']:.6f} | "
                f"{metrics['maximum_drawdown']:.6f} | "
                f"{metrics['risk_adjusted_score']:.6f} | "
                f"{metrics['net_cumulative_paper_return']:.6f} |"
            )
    lines.extend(
        [
            "",
            "These are bounded retrospective paper/replay measurements, not "
            "realized or expected trading outcomes.",
            "",
            "## Clustered Inference and Global Correction",
            "",
            f"- Paired unit: `{payload['protocol_summary']['inference']['paired_unit']}`",
            f"- Test: `{payload['protocol_summary']['inference']['test']}`",
            f"- Multiple-comparison control: `{payload['protocol_summary']['inference']['global_multiple_comparison_control']}`",
            f"- Familywise alpha: `{negative['familywise_alpha']}`",
            f"- Inferentially insufficient comparisons: `{negative['inference_insufficient_comparison_count']}`",
            f"- Global Holm positives: `{negative['global_holm_positive_count']}`",
            "",
            negative["conclusion"],
            "",
            "Time observations inside one source series are deliberately not "
            "counted as independent inferential units. The three current sources "
            "each contain only one series, so raw p-values are forced to `1.0` "
            "under the predeclared single-cluster rule.",
            "",
            "## Limitations",
            "",
            "- The snapshots are retrospective and were not prospectively protected for this sidecar.",
            "- There is one series per source, below the five-cluster inferential minimum.",
            "- Costs are fixed research proxies, not executable venue quotes.",
            "- Funding, borrow, latency, queue position, spread variation, taxes, rollover, and market impact are not fully modeled.",
            "- Candidate inclusion comes from the existing registry and is not evidence of merit.",
            "- A mean score difference is descriptive only; no comparison survives the global promotion gate.",
            "",
            "## Claim Controls",
            "",
            "- Alpha claim allowed: `false`",
            "- Edge claim allowed: `false`",
            "- Profit claim allowed: `false`",
            "- Value claim allowed: `false`",
            "- Field-performance claim allowed: `false`",
            "- Prospective-validation claim allowed: `false`",
            "- Live trading allowed: `false`",
            "- External action allowed: `false`",
            "",
            "## Reproduction",
            "",
            "```powershell",
            "python code/ops/BUILD_MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK.py "
            f"--generated-utc {payload['generated_utc']}",
            "python -m pytest -q tests/test_market_signal_source_native_benchmark.py",
            "```",
        ]
    )
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any],
    out_json: Path = OUT_JSON,
    manifest_json: Path = MANIFEST_JSON,
    doc_path: Path = DOC_PATH,
    dashboard_json: Path | None = None,
) -> dict[str, Any]:
    rendered = render_markdown(payload)
    write_json(out_json, payload)
    if dashboard_json is not None:
        write_json(dashboard_json, payload)
    write_text(doc_path, rendered)
    manifest: dict[str, Any] = {
        "schema": "market_signal_source_native_benchmark_manifest_v1",
        "protocol_id": payload["protocol_id"],
        "generated_utc": payload["generated_utc"],
        "status": payload["status"],
        "output": {
            "path": str(out_json.relative_to(ROOT)).replace("\\", "/")
            if out_json.is_relative_to(ROOT)
            else str(out_json),
            "file_sha256": file_sha256(out_json),
            "payload_sha256": payload["payload_sha256"],
        },
        "public_feed": (
            {
                "path": str(dashboard_json.relative_to(ROOT)).replace("\\", "/")
                if dashboard_json.is_relative_to(ROOT)
                else str(dashboard_json),
                "file_sha256": file_sha256(dashboard_json),
                "payload_sha256": payload["payload_sha256"],
                "public_performance_claim_allowed": False,
            }
            if dashboard_json is not None
            else None
        ),
        "documentation": {
            "path": str(doc_path.relative_to(ROOT)).replace("\\", "/")
            if doc_path.is_relative_to(ROOT)
            else str(doc_path),
            "file_sha256": file_sha256(doc_path),
        },
        "input_hashes": payload["inputs"],
        "claim_controls": payload["claim_controls"],
        "external_actions": [],
    }
    manifest["manifest_sha256"] = stable_sha256(manifest)
    write_json(manifest_json, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the bounded paper/replay market-signal source-native sidecar."
        )
    )
    parser.add_argument(
        "--generated-utc",
        default=None,
        help="Fixed UTC timestamp for deterministic reproduction.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Build and validate in memory without writing outputs.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args.generated_utc)
    if not args.check:
        manifest = write_outputs(payload, dashboard_json=DASHBOARD_JSON)
    else:
        manifest = {"manifest_sha256": "not_written_check_mode"}
    print(
        json.dumps(
            {
                "status": payload["status"],
                "payload_sha256": payload["payload_sha256"],
                "manifest_sha256": manifest["manifest_sha256"],
                "candidate_count": payload["implementation_summary"][
                    "implemented_candidate_count"
                ],
                "baseline_count": payload["implementation_summary"][
                    "implemented_baseline_count"
                ],
                "source_series_count": payload["implementation_summary"][
                    "source_series_count"
                ],
                "comparison_count": payload["negative_result_summary"][
                    "candidate_source_baseline_comparison_count"
                ],
                "global_holm_positive_count": payload[
                    "negative_result_summary"
                ]["global_holm_positive_count"],
                "external_action_count": len(payload["external_actions"]),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
