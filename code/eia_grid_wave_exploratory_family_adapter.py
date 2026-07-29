"""Retrospective exploratory family adapters for the frozen EIA wave panel.

This module may append fixed, clearly labeled exploratory candidates to the
source-native ledger. It must not modify the frozen champion protocol, select a
new confirmatory candidate, or turn the already-observed holdout into
prospective evidence.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from datetime import date, timedelta
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT / "config" / "eia_grid_wave_exploratory_family_adapter_v1.json"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_wave_exploratory_family_adapter.v1":
        raise ValueError("unexpected EIA exploratory family adapter schema")
    if payload.get("status") != "retrospective_exploratory_only":
        raise ValueError("EIA exploratory family adapter must remain retrospective")
    contract = payload.get("evaluation_contract", {})
    controls = payload.get("claim_controls", {})
    if (
        contract.get("prospectively_protected") is not False
        or contract.get("promotion_eligible") is not False
        or any(
            controls.get(field) is not False
            for field in (
                "public_performance_claim_allowed",
                "field_validation_claim_allowed",
                "realized_savings_claim_allowed",
                "trading_or_control_execution_allowed",
            )
        )
    ):
        raise ValueError("EIA exploratory adapter claim controls must fail closed")
    return payload


def robust_center_scale(values: np.ndarray) -> tuple[float, float]:
    center = float(np.median(values))
    mad = float(np.median(np.abs(values - center)))
    scale = max(1.4826 * mad, float(np.std(values)), 1e-9)
    return center, scale


def forecast_heart_rate_variability_control(
    history: list[float],
    eia_module: Any,
    parameters: dict[str, Any],
) -> float:
    """Return a history-only adaptive correction to the frozen harmonic model."""

    periods = tuple(float(value) for value in parameters["harmonic_periods_days"])
    ridge = float(parameters["harmonic_ridge"])
    weekly_lag = int(parameters["weekly_lag_days"])
    recent_window = int(parameters["recent_innovation_window"])
    long_window = int(parameters["long_innovation_window"])
    correction_gain = float(parameters["correction_gain"])
    maximum_scales = float(parameters["maximum_correction_robust_scales"])

    base = float(eia_module.forecast_harmonic(history, periods, ridge))
    values = np.asarray(history, dtype=float)
    if values.size <= weekly_lag + recent_window:
        return base

    innovations = values[weekly_lag:] - values[:-weekly_lag]
    long_values = innovations[-long_window:]
    recent_values = innovations[-recent_window:]
    long_center, long_scale = robust_center_scale(long_values)
    recent_center, recent_scale = robust_center_scale(recent_values)
    variability_ratio = recent_scale / max(long_scale, 1e-9)
    adaptive_gain = correction_gain / max(1.0, variability_ratio)
    correction = adaptive_gain * (recent_center - long_center)
    correction_limit = maximum_scales * long_scale
    correction = float(np.clip(correction, -correction_limit, correction_limit))
    return base + correction


def evaluate(
    panel: dict[str, Any],
    protocol: dict[str, Any],
    eia_module: Any,
    policy: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    policy = policy or load_policy()
    source_protocol = policy["source_protocol"]
    actual_protocol_sha256 = file_sha256(eia_module.PROTOCOL_PATH)
    if actual_protocol_sha256 != source_protocol["sha256"]:
        raise ValueError("frozen EIA protocol hash does not match exploratory policy")
    if protocol.get("protocol_id") != source_protocol["protocol_id"]:
        raise ValueError("frozen EIA protocol id does not match exploratory policy")

    candidate = policy["candidate"]
    candidate_id = str(candidate["id"])
    frozen_ids = {
        str(row.get("id", ""))
        for row in protocol.get("wave_candidates", [])
        if isinstance(row, dict)
    }
    if candidate_id in frozen_ids:
        raise ValueError("exploratory candidate must not alter the frozen roster")

    parameters = candidate["parameters"]
    maximum_history = int(protocol["execution_controls"]["maximum_history_days"])
    minimum_history = int(protocol["split"]["minimum_history_days"])
    series = eia_module.panel_series(panel, protocol)
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []

    for respondent, bundle in series.items():
        actual: dict[str, float] = bundle["actual"]
        official: dict[str, float] = bundle["official"]
        actual_dates = sorted(actual)
        for target in sorted(set(actual) & set(official)):
            split_name = eia_module.target_split(target, protocol)
            if split_name is None:
                continue
            target_date = date.fromisoformat(target)
            previous = (target_date - timedelta(days=1)).isoformat()
            seasonal = (target_date - timedelta(days=7)).isoformat()
            if previous not in actual or seasonal not in actual:
                skipped.append(
                    {
                        "respondent": respondent,
                        "target": target,
                        "reason": "history_gap",
                    }
                )
                continue
            history_dates = [value for value in actual_dates if value < target]
            if len(history_dates) < minimum_history:
                skipped.append(
                    {
                        "respondent": respondent,
                        "target": target,
                        "reason": "insufficient_history",
                    }
                )
                continue
            history_dates = history_dates[-maximum_history:]
            history = [actual[value] for value in history_dates]
            start = time.perf_counter()
            try:
                predicted = float(
                    forecast_heart_rate_variability_control(
                        history, eia_module, parameters
                    )
                )
            except (
                KeyError,
                TypeError,
                ValueError,
                np.linalg.LinAlgError,
                FloatingPointError,
                OverflowError,
            ):
                skipped.append(
                    {
                        "respondent": respondent,
                        "target": target,
                        "reason": "strategy_failure",
                    }
                )
                continue
            runtime_ms = (time.perf_counter() - start) * 1000.0
            if not math.isfinite(predicted):
                skipped.append(
                    {
                        "respondent": respondent,
                        "target": target,
                        "reason": "nonfinite_prediction",
                    }
                )
                continue

            target_value = actual[target]
            last_value = actual[previous]
            absolute_error = abs(target_value - predicted)
            scale = eia_module.seasonal_mase_scale(history)
            rows.append(
                {
                    "split": split_name,
                    "respondent": respondent,
                    "respondent_name": bundle["authority"]["name"],
                    "timezone": bundle["authority"]["timezone"],
                    "target_date": target,
                    "calendar_month": target[:7],
                    "strategy": candidate_id,
                    "kind": "exploratory_geometry_family",
                    "actual_mwh": target_value,
                    "predicted_mwh": predicted,
                    "absolute_error_mwh": absolute_error,
                    "absolute_percentage_error": absolute_error
                    / max(abs(target_value), 1e-9),
                    "seasonal_mase_7": absolute_error / scale,
                    "directional_accuracy": float(
                        eia_module.direction(predicted - last_value)
                        == eia_module.direction(target_value - last_value)
                    ),
                    "runtime_ms": runtime_ms,
                    "protocol_role": "retrospective_exploratory_only",
                    "prospectively_protected": False,
                    "promotion_eligible": False,
                }
            )

    summary = {
        "adapter_id": policy["adapter_id"],
        "adapter_policy_path": str(POLICY_PATH.relative_to(ROOT)).replace("\\", "/"),
        "adapter_policy_sha256": file_sha256(POLICY_PATH),
        "source_protocol_sha256": actual_protocol_sha256,
        "candidate_id": candidate_id,
        "candidate_count": 1,
        "evaluation_row_count": len(rows),
        "development_row_count": sum(
            1 for row in rows if row["split"] == "development"
        ),
        "holdout_row_count": sum(1 for row in rows if row["split"] == "holdout"),
        "authority_count": len({row["respondent"] for row in rows}),
        "skipped_target_count": len(skipped),
        "history_only": True,
        "holdout_previously_observed": True,
        "prospectively_protected": False,
        "promotion_eligible": False,
        "public_performance_claim_allowed": False,
    }
    return rows, summary
