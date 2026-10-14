"""Offline review of precomputed daily forecasts under a separately pinned protocol.

This versioned review path preserves the frozen EIA v1 code and results. It uses
calendar dates and declared publication times, requires complete paired records,
and reports descriptive differences without a statistical or production gate.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
from statistics import mean
import sys

MAX_FILE_BYTES = 16_777_216
MAX_ROWS = 100_000
MAX_TARGETS = 10_000
HISTORY_FIELDS = {"entity_id", "date", "actual_available_at_utc", "actual_mwh"}
PREDICTION_FIELDS = {"entity_id", "target_date", "issued_at_utc", "prediction_available_at_utc", "actual_available_at_utc", "strategy", "actual_mwh", "predicted_mwh"}
PROTOCOL_FIELDS = {
    "schema", "protocol_id", "evidence_type", "owner_acceptance_reference",
    "locked_at_utc", "grain", "time_zone", "unit", "entities", "window",
    "candidate_strategy", "baseline_strategies", "scope_match_declared",
    "baseline_scope_reference", "issue_rule", "history_contract", "metrics",
    "inference", "promotion",
}


@dataclass(frozen=True)
class Observation:
    value: float
    available_at: datetime


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError(f"nonfinite JSON value: {value}")


def _bytes(path: Path) -> bytes:
    with path.open("rb") as stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("input exceeds file-size budget")
    return raw


def _day(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("date must use YYYY-MM-DD")
    return parsed


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be an explicit UTC time ending in Z")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return parsed


def _number(value: str) -> float:
    result = float(value)
    if not math.isfinite(result) or result < 0:
        raise ValueError("demand and forecast values must be finite and nonnegative")
    return result


def _identifier(value) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,63}", value))


def _integer(value, lower, upper) -> bool:
    return type(value) is int and lower <= value <= upper


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def load_protocol(path: Path, protocol_sha256: str) -> tuple[dict, bytes]:
    raw = _bytes(path)
    if not isinstance(protocol_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", protocol_sha256) or hashlib.sha256(raw).hexdigest() != protocol_sha256:
        raise ValueError("protocol must match the separately supplied SHA-256")
    protocol = json.loads(raw, object_pairs_hook=_object, parse_constant=_nonfinite)
    if not isinstance(protocol, dict) or set(protocol) != PROTOCOL_FIELDS or protocol["schema"] != "forecast_evaluation_protocol.v2":
        raise ValueError("unexpected protocol schema or fields")
    if not _text(protocol["protocol_id"]) or protocol["evidence_type"] not in {"synthetic", "buyer_supplied"} or not _text(protocol["owner_acceptance_reference"]) or not _text(protocol["baseline_scope_reference"]):
        raise ValueError("protocol requires an evidence type and owner/scope references")
    if (protocol["grain"], protocol["time_zone"], protocol["unit"]) != ("entity_calendar_day", "UTC", "megawatthours"):
        raise ValueError("this review path supports UTC calendar days in megawatthours")
    if protocol["scope_match_declared"] is not True:
        raise ValueError("owner must declare a scope-matched baseline")
    entities, baselines = protocol["entities"], protocol["baseline_strategies"]
    for values, maximum in ((entities, 100), (baselines, 12)):
        if not isinstance(values, list) or not 1 <= len(values) <= maximum or not all(_identifier(value) for value in values) or len(set(values)) != len(values):
            raise ValueError("entity and baseline registries must be bounded, unique identifiers")
    if not _identifier(protocol["candidate_strategy"]) or protocol["candidate_strategy"] in baselines:
        raise ValueError("candidate must be a distinct named strategy")
    window = protocol["window"]
    if not isinstance(window, dict) or set(window) != {"start", "end"}:
        raise ValueError("protocol requires a scheduled target window")
    start, end = _day(window["start"]), _day(window["end"])
    if end < start or ((end - start).days + 1) * len(entities) > MAX_TARGETS:
        raise ValueError("target window is invalid or exceeds budget")
    issue = protocol["issue_rule"]
    if not isinstance(issue, dict) or set(issue) != {"day_offset", "time_utc"} or not _integer(issue["day_offset"], -30, 0) or not isinstance(issue["time_utc"], str) or not re.fullmatch(r"\d{2}:\d{2}:\d{2}", issue["time_utc"]):
        raise ValueError("invalid fixed issue rule")
    time.fromisoformat(issue["time_utc"])
    history = protocol["history_contract"]
    if not isinstance(history, dict) or set(history) != {"lag_offsets_days", "season_days", "lookback_days", "minimum_seasonal_pairs"}:
        raise ValueError("invalid calendar history contract")
    offsets = history["lag_offsets_days"]
    if not isinstance(offsets, list) or not offsets or not all(_integer(value, 1, 730) for value in offsets) or offsets != sorted(set(offsets)):
        raise ValueError("calendar lag offsets must be positive, ordered and unique")
    if history["season_days"] != 7 or type(history["season_days"]) is not int or not _integer(history["lookback_days"], max(offsets) + 7, 730) or not _integer(history["minimum_seasonal_pairs"], 1, history["lookback_days"] - 7):
        raise ValueError("invalid seven-calendar-day scale contract")
    if protocol["metrics"] != ["mae_mwh", "mean_seasonal_mase_7"] or protocol["inference"] != "descriptive_only_no_independence_claim" or protocol["promotion"] != "HUMAN_REVIEW_HOLD":
        raise ValueError("this version permits descriptive review and HOLD only")
    _utc(protocol["locked_at_utc"])
    return protocol, raw


def _csv_rows(raw: bytes, fields: set[str]) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8"), newline=""))
    rows = []
    try:
        if reader.fieldnames is None or len(reader.fieldnames) != len(fields) or set(reader.fieldnames) != fields:
            raise ValueError("CSV header must contain exactly the declared columns")
        for row in reader:
            if len(rows) >= MAX_ROWS or set(row) != fields or any(not isinstance(value, str) or not value.strip() for value in row.values()):
                raise ValueError("CSV has empty/malformed fields or exceeds the row budget")
            rows.append(row)
    except csv.Error as exc:
        raise ValueError("CSV parser rejected malformed input or an oversized field") from exc
    if not rows:
        raise ValueError("CSV input is empty")
    return rows


def load_history(raw: bytes, entities: list[str]) -> dict[tuple[str, date], Observation]:
    history = {}
    for row in _csv_rows(raw, HISTORY_FIELDS):
        entity, observed_day = row["entity_id"], _day(row["date"])
        key = entity, observed_day
        if entity not in entities or key in history:
            raise ValueError("history has an unknown entity or duplicate calendar identity")
        available = _utc(row["actual_available_at_utc"])
        if available < datetime.combine(observed_day + timedelta(days=1), time(), timezone.utc):
            raise ValueError("full-day actual availability precedes completion of its calendar day")
        history[key] = Observation(_number(row["actual_mwh"]), available)
    return history


def calendar_lags(history, entity: str, target: date, issued_at: datetime, offsets: list[int]) -> dict[int, float]:
    lags = {}
    for offset in offsets:
        observation = history.get((entity, target - timedelta(days=offset)))
        if observation is None or observation.available_at > issued_at:
            raise ValueError(f"required calendar lag {offset} is missing or unavailable at issue")
        lags[offset] = observation.value
    return lags


def calendar_seasonal_scale(history, entity: str, target: date, issued_at: datetime, lookback_days: int, min_pairs: int) -> dict:
    start = target - timedelta(days=lookback_days)
    available = {day: observation.value for (name, day), observation in history.items() if name == entity and start <= day < target and observation.available_at <= issued_at}
    differences = [abs(value - available[day - timedelta(days=7)]) for day, value in available.items() if day - timedelta(days=7) in available]
    if len(differences) < min_pairs:
        raise ValueError("insufficient as-of seven-calendar-day seasonal pairs")
    scale = mean(differences)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("seven-calendar-day seasonal scale must be finite and positive")
    return {"scale_mwh": scale, "pair_count": len(differences)}


def _scheduled(protocol: dict) -> set[tuple[str, date, datetime]]:
    start, end = _day(protocol["window"]["start"]), _day(protocol["window"]["end"])
    issue = protocol["issue_rule"]
    return {(entity, start + timedelta(days=offset), datetime.combine(start + timedelta(days=offset + issue["day_offset"]), time.fromisoformat(issue["time_utc"]), timezone.utc)) for entity in protocol["entities"] for offset in range((end - start).days + 1)}


def load_predictions(raw: bytes, protocol: dict, *, now: datetime) -> dict:
    strategies = [protocol["candidate_strategy"], *protocol["baseline_strategies"]]
    predictions = {strategy: {} for strategy in strategies}
    locked = _utc(protocol["locked_at_utc"])
    for row in _csv_rows(raw, PREDICTION_FIELDS):
        strategy = row["strategy"]
        if strategy not in predictions or row["entity_id"] not in protocol["entities"]:
            raise ValueError("prediction uses an undeclared strategy or entity")
        target, issued = _day(row["target_date"]), _utc(row["issued_at_utc"])
        identity = row["entity_id"], target, issued
        if identity in predictions[strategy]:
            raise ValueError("duplicate prediction identity")
        prediction_available, actual_available = _utc(row["prediction_available_at_utc"]), _utc(row["actual_available_at_utc"])
        if locked >= issued or prediction_available > issued or actual_available <= issued:
            raise ValueError("protocol/forecast/outcome timing does not precede or follow issue as required")
        if actual_available < datetime.combine(target + timedelta(days=1), time(), timezone.utc):
            raise ValueError("target actual availability precedes full-day completion")
        if protocol["evidence_type"] == "buyer_supplied" and (issued > now or actual_available > now):
            raise ValueError("buyer-supplied outcomes must be available by evaluation time")
        predictions[strategy][identity] = {"actual": _number(row["actual_mwh"]), "prediction": _number(row["predicted_mwh"]), "actual_available": actual_available}
    scheduled = _scheduled(protocol)
    for strategy, rows in predictions.items():
        if set(rows) != scheduled:
            raise ValueError(f"{strategy} does not contain exactly the complete scheduled identity set")
    candidate = predictions[protocol["candidate_strategy"]]
    for rows in predictions.values():
        if any(row["actual"] != candidate[key]["actual"] or row["actual_available"] != candidate[key]["actual_available"] for key, row in rows.items()):
            raise ValueError("paired strategy outcomes or availability timestamps disagree")
    return predictions


def evaluate_files(protocol_path: Path, predictions_path: Path, history_path: Path, protocol_sha256: str, *, now: datetime | None = None) -> dict:
    protocol, protocol_raw = load_protocol(protocol_path, protocol_sha256)
    predictions_raw, history_raw = _bytes(predictions_path), _bytes(history_path)
    evaluated_at = now or datetime.now(timezone.utc)
    if evaluated_at.tzinfo is None or evaluated_at.utcoffset() != timedelta(0):
        raise ValueError("evaluation time must be aware UTC")
    history = load_history(history_raw, protocol["entities"])
    predictions = load_predictions(predictions_raw, protocol, now=evaluated_at)
    identities = sorted(_scheduled(protocol))
    scores = {strategy: [] for strategy in predictions}
    diagnostics = []
    contract = protocol["history_contract"]
    for entity, target, issued in identities:
        calendar_lags(history, entity, target, issued, contract["lag_offsets_days"])
        scale = calendar_seasonal_scale(history, entity, target, issued, contract["lookback_days"], contract["minimum_seasonal_pairs"])
        diagnostics.append({"entity_id": entity, "target_date": target.isoformat(), "seasonal_scale_mwh": scale["scale_mwh"], "seasonal_pair_count": scale["pair_count"]})
        for strategy, rows in predictions.items():
            row = rows[entity, target, issued]
            historical_actual = history.get((entity, target))
            if historical_actual is not None and (historical_actual.value != row["actual"] or historical_actual.available_at != row["actual_available"]):
                raise ValueError("target outcome disagrees with the history source")
            error = abs(row["actual"] - row["prediction"])
            scores[strategy].append({"entity_id": entity, "absolute_error_mwh": error, "seasonal_mase_7": error / scale["scale_mwh"]})
    summary = {strategy: {"row_count": len(rows), "mae_mwh": mean(row["absolute_error_mwh"] for row in rows), "mean_seasonal_mase_7": mean(row["seasonal_mase_7"] for row in rows)} for strategy, rows in scores.items()}
    candidate = protocol["candidate_strategy"]
    comparisons = []
    for baseline in protocol["baseline_strategies"]:
        differences = [base["seasonal_mase_7"] - selected["seasonal_mase_7"] for base, selected in zip(scores[baseline], scores[candidate])]
        entity_differences = {entity: mean(delta for identity, delta in zip(identities, differences) if identity[0] == entity) for entity in protocol["entities"]}
        comparisons.append({"baseline": baseline, "paired_target_count": len(identities), "mean_skill_delta": mean(differences), "entity_mean_skill": entity_differences, "p_value": None, "confidence_interval": None, "interpretation": "Descriptive paired differences; entity and temporal dependence are not assumed absent."})
    report = {
        "schema": "forecast_evaluation_review.v2", "status": "HUMAN_REVIEW_HOLD",
        "protocol_id": protocol["protocol_id"], "evidence_type": protocol["evidence_type"],
        "evaluated_at_utc": evaluated_at.isoformat().replace("+00:00", "Z"),
        "identities": {"grain": protocol["grain"], "time_zone": protocol["time_zone"], "unit": protocol["unit"], "paired_target_count": len(identities), "entity_count": len(protocol["entities"]), "all_strategy_identity_sets_exact": True},
        "inputs": {"protocol": hashlib.sha256(protocol_raw).hexdigest(), "predictions": hashlib.sha256(predictions_raw).hexdigest(), "history": hashlib.sha256(history_raw).hexdigest()},
        "source_sha256": hashlib.sha256(_bytes(Path(__file__))).hexdigest(),
        "runtime": {"python": sys.version.split()[0], "matched_frozen_v1_runtime_claimed": False},
        "owner_acceptance_reference": protocol["owner_acceptance_reference"],
        "baseline_scope_reference": protocol["baseline_scope_reference"],
        "strategy_summary": summary, "baseline_comparisons": comparisons,
        "history_diagnostics": diagnostics,
        "promotion_gate_passed": False, "production_authorized": False, "external_validation_complete": False,
        "limitations": [
            "Owner acceptance, baseline scope and source publication times are supplied declarations requiring human reconciliation.",
            "As-of history checks do not prove that a precomputed candidate used only those features or that forecasts were actually issued at the declared time.",
            "No independence-based p-value, automatic promotion, operational effect, electricity savings or economic value is established.",
            "Synthetic fixture dates and values establish software behavior only; frozen EIA v1 results are unchanged.",
        ],
    }
    report["receipt_sha256"] = hashlib.sha256(json.dumps(report, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--protocol-sha256", required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        report = evaluate_files(args.protocol, args.predictions, args.history, args.protocol_sha256)
        rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            with args.json_out.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        print(rendered, end="")
        return 0
    except (OSError, ValueError, TypeError, KeyError, OverflowError, UnicodeError, RecursionError) as exc:
        print(json.dumps({"schema": "forecast_evaluation_review.v2", "status": "HUMAN_REVIEW_HOLD", "input_rejected": True, "error": str(exc), "promotion_gate_passed": False, "production_authorized": False}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
