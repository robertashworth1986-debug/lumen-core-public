#!/usr/bin/env python3
"""Deterministic, non-actuating incumbent-versus-candidate shadow replay.

The runner reads frozen local JSON inputs, evaluates one locked MAE contract,
falls back exactly to the incumbent on explicit abstention, and emits a
hash-verifiable receipt. It has no network, credential, subprocess, trading,
dispatch, or production-write capability.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROTOCOL_SCHEMA = "lumencore_buyer_owned_shadow_replay_v1"
CASES_SCHEMA = "lumencore_buyer_owned_shadow_cases_v1"
PREDICTIONS_SCHEMA = "lumencore_buyer_owned_shadow_predictions_v1"
RECEIPT_SCHEMA = "lumencore_buyer_owned_shadow_receipt_v1"
VERSION = "1.0.0"
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_ROWS = 100_000

PROTOCOL_KEYS = {
    "schema",
    "version",
    "run_label",
    "mode",
    "decision_owner",
    "primary_metric",
    "metric_direction",
    "execution_boundary",
    "acceptance",
    "economic_conversion",
    "claim_boundary",
}
BOUNDARY_KEYS = {
    "production_write_access",
    "actuation_allowed",
    "production_credentials_allowed",
    "recommendations_require_human_approval",
    "incumbent_fallback_required",
}
ACCEPTANCE_KEYS = {
    "minimum_eligible_rows",
    "minimum_candidate_coverage",
    "minimum_relative_improvement",
    "maximum_worst_row_error_increase",
}
CASE_KEYS = {
    "row_id",
    "event_time_utc",
    "actual_available_at_utc",
    "incumbent_version",
    "incumbent_output",
    "outcome",
}
PREDICTION_KEYS = {
    "row_id",
    "prediction_time_utc",
    "candidate_version",
    "candidate_output",
    "confidence",
    "abstain",
    "reason",
}
STANDARD_CLAIM_BOUNDARY = [
    "This receipt is an offline replay or read-only shadow result, not field or external validation.",
    "Forecast or model skill is not a savings, ROI, revenue, or production-performance claim.",
    "The receipt recommends a bounded decision; it does not authorize deployment or control.",
]


class ShadowReplayError(ValueError):
    """Raised when a frozen input or non-actuation gate fails closed."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ShadowReplayError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ShadowReplayError(f"non-finite JSON number is forbidden: {value}")


def _load_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise ShadowReplayError(f"cannot read {path}: {exc}") from exc
    if len(raw) > MAX_INPUT_BYTES:
        raise ShadowReplayError(f"{path} exceeds {MAX_INPUT_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except UnicodeDecodeError as exc:
        raise ShadowReplayError(f"{path} must be UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ShadowReplayError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ShadowReplayError(f"{path} root must be an object")
    return value


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    if set(value) != expected:
        missing = sorted(expected - set(value))
        extra = sorted(set(value) - expected)
        raise ShadowReplayError(
            f"{context} keys mismatch; missing={missing}, extra={extra}"
        )


def _string(value: dict[str, Any], key: str, context: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip():
        raise ShadowReplayError(f"{context}.{key} must be a non-empty string")
    return item.strip()


def _number(
    value: dict[str, Any],
    key: str,
    context: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, (int, float)):
        raise ShadowReplayError(f"{context}.{key} must be numeric")
    result = float(item)
    if not math.isfinite(result):
        raise ShadowReplayError(f"{context}.{key} must be finite")
    if minimum is not None and result < minimum:
        raise ShadowReplayError(f"{context}.{key} must be at least {minimum}")
    if maximum is not None and result > maximum:
        raise ShadowReplayError(f"{context}.{key} must not exceed {maximum}")
    return result


def _integer(
    value: dict[str, Any], key: str, context: str, *, minimum: int, maximum: int
) -> int:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, int):
        raise ShadowReplayError(f"{context}.{key} must be an integer")
    if not minimum <= item <= maximum:
        raise ShadowReplayError(
            f"{context}.{key} must be between {minimum} and {maximum}"
        )
    return item


def _utc_timestamp(value: dict[str, Any], key: str, context: str) -> datetime:
    text = _string(value, key, context)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ShadowReplayError(f"{context}.{key} must be ISO-8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ShadowReplayError(f"{context}.{key} must be UTC")
    return parsed


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _validate_protocol(value: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(value, PROTOCOL_KEYS, "protocol")
    if value.get("schema") != PROTOCOL_SCHEMA or value.get("version") != VERSION:
        raise ShadowReplayError("unsupported protocol schema or version")
    run_label = _string(value, "run_label", "protocol")
    mode = _string(value, "mode", "protocol")
    if mode not in {"offline_replay", "read_only_shadow"}:
        raise ShadowReplayError("protocol.mode must be offline_replay or read_only_shadow")
    decision_owner = _string(value, "decision_owner", "protocol")
    if value.get("primary_metric") != "mae":
        raise ShadowReplayError("protocol.primary_metric must be mae")
    if value.get("metric_direction") != "lower_is_better":
        raise ShadowReplayError("protocol.metric_direction must be lower_is_better")

    boundary = value.get("execution_boundary")
    if not isinstance(boundary, dict):
        raise ShadowReplayError("protocol.execution_boundary must be an object")
    _exact_keys(boundary, BOUNDARY_KEYS, "protocol.execution_boundary")
    for key in (
        "production_write_access",
        "actuation_allowed",
        "production_credentials_allowed",
    ):
        if boundary.get(key) is not False:
            raise ShadowReplayError(f"protocol.execution_boundary.{key} must be false")
    for key in (
        "recommendations_require_human_approval",
        "incumbent_fallback_required",
    ):
        if boundary.get(key) is not True:
            raise ShadowReplayError(f"protocol.execution_boundary.{key} must be true")

    acceptance = value.get("acceptance")
    if not isinstance(acceptance, dict):
        raise ShadowReplayError("protocol.acceptance must be an object")
    _exact_keys(acceptance, ACCEPTANCE_KEYS, "protocol.acceptance")
    minimum_rows = _integer(
        acceptance,
        "minimum_eligible_rows",
        "protocol.acceptance",
        minimum=1,
        maximum=MAX_ROWS,
    )
    minimum_coverage = _number(
        acceptance,
        "minimum_candidate_coverage",
        "protocol.acceptance",
        minimum=0.0,
        maximum=1.0,
    )
    minimum_improvement = _number(
        acceptance,
        "minimum_relative_improvement",
        "protocol.acceptance",
        minimum=0.0,
        maximum=1.0,
    )
    maximum_regression = _number(
        acceptance,
        "maximum_worst_row_error_increase",
        "protocol.acceptance",
        minimum=0.0,
    )

    economic = value.get("economic_conversion")
    if not isinstance(economic, dict) or set(economic) != {"enabled"}:
        raise ShadowReplayError(
            "protocol.economic_conversion must contain only enabled"
        )
    if economic.get("enabled") is not False:
        raise ShadowReplayError(
            "economic conversion is forbidden in the technical shadow runner"
        )

    raw_claims = value.get("claim_boundary")
    if not isinstance(raw_claims, list) or not raw_claims:
        raise ShadowReplayError("protocol.claim_boundary must be a non-empty array")
    claims: list[str] = []
    for index, claim in enumerate(raw_claims):
        if not isinstance(claim, str) or not claim.strip():
            raise ShadowReplayError(
                f"protocol.claim_boundary[{index}] must be a non-empty string"
            )
        claims.append(claim.strip())

    return {
        "run_label": run_label,
        "mode": mode,
        "decision_owner": decision_owner,
        "primary_metric": "mae",
        "metric_direction": "lower_is_better",
        "execution_boundary": boundary,
        "acceptance": {
            "minimum_eligible_rows": minimum_rows,
            "minimum_candidate_coverage": minimum_coverage,
            "minimum_relative_improvement": minimum_improvement,
            "maximum_worst_row_error_increase": maximum_regression,
        },
        "claim_boundary": claims,
    }


def _validate_cases(value: dict[str, Any]) -> list[dict[str, Any]]:
    _exact_keys(value, {"schema", "version", "rows"}, "cases")
    if value.get("schema") != CASES_SCHEMA or value.get("version") != VERSION:
        raise ShadowReplayError("unsupported cases schema or version")
    rows = value.get("rows")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS:
        raise ShadowReplayError(f"cases.rows must contain 1 to {MAX_ROWS} rows")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(rows):
        context = f"cases.rows[{index}]"
        if not isinstance(raw, dict):
            raise ShadowReplayError(f"{context} must be an object")
        _exact_keys(raw, CASE_KEYS, context)
        row_id = _string(raw, "row_id", context)
        if row_id in seen:
            raise ShadowReplayError(f"duplicate cases row_id: {row_id}")
        seen.add(row_id)
        event_time = _utc_timestamp(raw, "event_time_utc", context)
        actual_time = _utc_timestamp(raw, "actual_available_at_utc", context)
        if actual_time <= event_time:
            raise ShadowReplayError(
                f"{context}.actual_available_at_utc must follow event_time_utc"
            )
        normalized.append(
            {
                "row_id": row_id,
                "event_time_utc": raw["event_time_utc"],
                "event_time": event_time,
                "actual_available_at_utc": raw["actual_available_at_utc"],
                "actual_time": actual_time,
                "incumbent_version": _string(raw, "incumbent_version", context),
                "incumbent_output": _number(raw, "incumbent_output", context),
                "outcome": _number(raw, "outcome", context),
            }
        )
    return sorted(normalized, key=lambda row: (row["event_time"], row["row_id"]))


def _validate_predictions(
    value: dict[str, Any], cases: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    _exact_keys(value, {"schema", "version", "rows"}, "predictions")
    if value.get("schema") != PREDICTIONS_SCHEMA or value.get("version") != VERSION:
        raise ShadowReplayError("unsupported predictions schema or version")
    rows = value.get("rows")
    if not isinstance(rows, list):
        raise ShadowReplayError("predictions.rows must be an array")
    case_map = {row["row_id"]: row for row in cases}
    result: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(rows):
        context = f"predictions.rows[{index}]"
        if not isinstance(raw, dict):
            raise ShadowReplayError(f"{context} must be an object")
        _exact_keys(raw, PREDICTION_KEYS, context)
        row_id = _string(raw, "row_id", context)
        if row_id not in case_map:
            raise ShadowReplayError(f"prediction row_id not in cases: {row_id}")
        if row_id in result:
            raise ShadowReplayError(f"duplicate prediction row_id: {row_id}")
        prediction_time = _utc_timestamp(raw, "prediction_time_utc", context)
        case = case_map[row_id]
        if prediction_time < case["event_time"]:
            raise ShadowReplayError(f"{context} precedes the case event")
        if prediction_time >= case["actual_time"]:
            raise ShadowReplayError(
                f"{context} was not sealed before the outcome became available"
            )
        abstain = raw.get("abstain")
        if not isinstance(abstain, bool):
            raise ShadowReplayError(f"{context}.abstain must be boolean")
        candidate_output = raw.get("candidate_output")
        if abstain:
            if candidate_output is not None:
                raise ShadowReplayError(
                    f"{context}.candidate_output must be null on abstention"
                )
            normalized_output = None
        else:
            normalized_output = _number(raw, "candidate_output", context)
        result[row_id] = {
            "row_id": row_id,
            "prediction_time_utc": raw["prediction_time_utc"],
            "candidate_version": _string(raw, "candidate_version", context),
            "candidate_output": normalized_output,
            "confidence": _number(
                raw, "confidence", context, minimum=0.0, maximum=1.0
            ),
            "abstain": abstain,
            "reason": _string(raw, "reason", context),
        }
    missing = sorted(set(case_map) - set(result))
    if missing:
        raise ShadowReplayError(f"missing prediction row_id(s): {missing[:10]}")
    return result


def evaluate_shadow_replay(
    protocol_path: Path, cases_path: Path, predictions_path: Path
) -> dict[str, Any]:
    paths = {
        "protocol": protocol_path.resolve(),
        "cases": cases_path.resolve(),
        "predictions": predictions_path.resolve(),
    }
    if len(set(paths.values())) != 3:
        raise ShadowReplayError("protocol, cases, and predictions must be distinct files")
    before = {name: _sha256_file(path) for name, path in paths.items()}
    protocol = _validate_protocol(_load_object(paths["protocol"]))
    cases = _validate_cases(_load_object(paths["cases"]))
    predictions = _validate_predictions(_load_object(paths["predictions"]), cases)

    per_row: list[dict[str, Any]] = []
    incumbent_errors: list[float] = []
    effective_errors: list[float] = []
    non_abstain = 0
    for case in cases:
        prediction = predictions[case["row_id"]]
        use_candidate = not prediction["abstain"]
        if use_candidate:
            non_abstain += 1
            effective_output = float(prediction["candidate_output"])
            selected_source = "candidate"
        else:
            effective_output = case["incumbent_output"]
            selected_source = "incumbent_fallback"
        incumbent_error = abs(case["incumbent_output"] - case["outcome"])
        effective_error = abs(effective_output - case["outcome"])
        incumbent_errors.append(incumbent_error)
        effective_errors.append(effective_error)
        per_row.append(
            {
                "row_id": case["row_id"],
                "event_time_utc": case["event_time_utc"],
                "actual_available_at_utc": case["actual_available_at_utc"],
                "incumbent_version": case["incumbent_version"],
                "candidate_version": prediction["candidate_version"],
                "incumbent_output": case["incumbent_output"],
                "candidate_output": prediction["candidate_output"],
                "effective_output": effective_output,
                "outcome": case["outcome"],
                "selected_source": selected_source,
                "abstain": prediction["abstain"],
                "reason": prediction["reason"],
                "incumbent_absolute_error": incumbent_error,
                "effective_absolute_error": effective_error,
                "error_increase": effective_error - incumbent_error,
            }
        )

    count = len(cases)
    incumbent_mae = math.fsum(incumbent_errors) / count
    effective_mae = math.fsum(effective_errors) / count
    if incumbent_mae == 0.0:
        relative_improvement = 0.0 if effective_mae == 0.0 else -1.0
    else:
        relative_improvement = (incumbent_mae - effective_mae) / incumbent_mae
    coverage = non_abstain / count
    worst_increase = max(
        row["error_increase"] for row in per_row
    )
    acceptance = protocol["acceptance"]
    gates = {
        "minimum_eligible_rows": count >= acceptance["minimum_eligible_rows"],
        "minimum_candidate_coverage": coverage
        >= acceptance["minimum_candidate_coverage"],
        "minimum_relative_improvement": relative_improvement
        >= acceptance["minimum_relative_improvement"],
        "maximum_worst_row_error_increase": worst_increase
        <= acceptance["maximum_worst_row_error_increase"],
        "sealed_before_outcome": True,
        "non_actuating_boundary": True,
    }
    all_gates_pass = all(gates.values())
    if all_gates_pass:
        recommended_decision = "promote"
    elif effective_mae > incumbent_mae:
        recommended_decision = "reject"
    else:
        recommended_decision = "hold"

    negative_register: list[dict[str, Any]] = [
        {"type": "gate_failure", "gate": key}
        for key, passed in gates.items()
        if not passed
    ]
    negative_register.extend(
        {
            "type": "row_regression",
            "row_id": row["row_id"],
            "error_increase": row["error_increase"],
        }
        for row in per_row
        if row["error_increase"] > 0.0
    )

    after = {name: _sha256_file(path) for name, path in paths.items()}
    if before != after:
        raise ShadowReplayError("frozen input changed during evaluation")
    input_manifest = {
        name: {
            "sha256": before[name],
            "bytes": paths[name].stat().st_size,
            "logical_role": name,
        }
        for name in sorted(paths)
    }
    run_id = hashlib.sha256(
        _canonical_json(
            {
                "run_label": protocol["run_label"],
                "inputs": input_manifest,
            }
        )
    ).hexdigest()
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "version": VERSION,
        "status": "complete",
        "run_id": run_id,
        "contract": protocol,
        "input_manifest": input_manifest,
        "counts": {
            "eligible_rows": count,
            "candidate_rows": non_abstain,
            "abstentions": count - non_abstain,
        },
        "metrics": {
            "incumbent_mae": incumbent_mae,
            "candidate_effective_mae": effective_mae,
            "candidate_coverage": coverage,
            "relative_improvement": relative_improvement,
            "worst_row_error_increase": worst_increase,
        },
        "gates": gates,
        "all_gates_pass": all_gates_pass,
        "recommended_decision": recommended_decision,
        "human_approval_required": True,
        "production_change_authorized": False,
        "economic_conversion_enabled": False,
        "negative_result_register": negative_register,
        "rows": per_row,
        "claim_boundary": protocol["claim_boundary"] + STANDARD_CLAIM_BOUNDARY,
    }
    receipt["receipt_sha256"] = hashlib.sha256(_canonical_json(receipt)).hexdigest()
    return receipt


def write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    resolved = path.resolve()
    if not resolved.parent.is_dir():
        raise ShadowReplayError("output parent directory must already exist")
    payload = json.dumps(
        receipt, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False
    ) + "\n"
    temporary = resolved.with_name(f".{resolved.name}.tmp")
    try:
        temporary.write_text(payload, encoding="utf-8")
        os.replace(temporary, resolved)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", required=True, type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--predictions", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    inputs = {args.protocol.resolve(), args.cases.resolve(), args.predictions.resolve()}
    if args.output.resolve() in inputs:
        print("shadow replay failed: output must not overwrite a frozen input", file=sys.stderr)
        return 2
    try:
        receipt = evaluate_shadow_replay(
            args.protocol, args.cases, args.predictions
        )
        write_receipt(args.output, receipt)
    except (OSError, ShadowReplayError) as exc:
        print(f"shadow replay failed: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "all_gates_pass": receipt["all_gates_pass"],
                "recommended_decision": receipt["recommended_decision"],
                "receipt_sha256": receipt["receipt_sha256"],
                "run_id": receipt["run_id"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
