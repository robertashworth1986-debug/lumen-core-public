"""Frozen v3 convex hybrid over verified atomic hourly v2 prediction panels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config" / "eia_grid_hourly_hybrid_confirmation_protocol_v3.json"
OUT_DIR = ROOT / "out" / "eia_grid_hourly_hybrid_confirmation_v3"
PREDICTIONS_PATH = OUT_DIR / "sealed_prediction_panels.jsonl"
SETTLEMENTS_PATH = OUT_DIR / "settlement_panels.jsonl"
RUN_RECEIPTS_PATH = OUT_DIR / "operational_runs.jsonl"
STATUS_PATH = OUT_DIR / "prospective_status_latest.json"
LATEST_CYCLE_PATH = OUT_DIR / "latest_cycle.json"
LOCK_PATH = OUT_DIR / ".hourly_hybrid_confirmation_cycle.lock"
ZERO_HASH = "0" * 64


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git_commit_for_path(path: Path) -> str | None:
    try:
        relative = path.resolve().relative_to(ROOT.resolve())
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", str(relative)],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    return result.stdout.strip() or None


def repository_head() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None


def root_path(relative: str) -> Path:
    candidate = (ROOT / relative).resolve()
    candidate.relative_to(ROOT.resolve())
    return candidate


def parse_period(period: str) -> datetime:
    return datetime.strptime(period, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)


def target_interval_start_utc(period: str) -> datetime:
    return parse_period(period) - timedelta(hours=1)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return parsed.astimezone(timezone.utc)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def load_protocol(path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != "eia_grid_hourly_hybrid_confirmation_protocol.v3":
        raise ValueError("unexpected hourly hybrid confirmation protocol schema")
    if payload.get("version") != 3:
        raise ValueError("hourly hybrid confirmation must remain version 3")
    if payload.get("automatic_promotion_allowed") is not False:
        raise ValueError("automatic promotion must remain disabled")
    window = payload["prospective_window"]
    if window.get("backfilled_predictions_allowed") is not False:
        raise ValueError("backfilled predictions must remain disabled")
    if int(window["minimum_seal_lead_seconds"]) < 3600:
        raise ValueError("the v3 minimum seal lead may not be weakened below one hour")
    if int(window["maximum_seal_lead_seconds"]) <= int(
        window["minimum_seal_lead_seconds"]
    ):
        raise ValueError("the v3 issuance window is invalid")
    parse_period(window["first_allowed_period_end_utc"])
    authorities = payload["balancing_authorities"]
    if len(authorities) != 8 or len(set(authorities)) != 8:
        raise ValueError("v3 requires exactly eight unique balancing authorities")
    candidate = payload["candidate"]
    if candidate.get("id") != "constrained_historical_inverse_square_blend_v3":
        raise ValueError("unexpected v3 candidate")
    constraints = candidate["constraints"]
    required_false = (
        "prospective_weight_updates_allowed",
        "dynamic_regime_switching_allowed",
        "post_target_override_allowed",
    )
    if any(constraints.get(key) is not False for key in required_false):
        raise ValueError("v3 dynamic behavior must remain disabled")
    succession = payload["succession"]
    if succession.get("v4_start_allowed_now") is not False:
        raise ValueError("v4 must remain deferred until the v3 window closes")
    if succession.get("v5_start_allowed_now") is not False:
        raise ValueError("v5 must remain deferred to independent replication")
    return payload


def verify_frozen_inputs(protocol: dict[str, Any]) -> dict[str, str]:
    parent_protocol = root_path(protocol["parent_v2"]["protocol_path"])
    design_artifact = root_path(protocol["historical_design"]["artifact_path"])
    observed_parent = file_sha256(parent_protocol)
    observed_design = file_sha256(design_artifact)
    if observed_parent != protocol["parent_v2"]["protocol_sha256"]:
        raise ValueError("v2 protocol hash does not match the v3 freeze")
    if observed_design != protocol["historical_design"]["artifact_sha256"]:
        raise ValueError("v2 design artifact hash does not match the v3 freeze")
    return {
        "parent_v2_protocol_sha256": observed_parent,
        "historical_design_artifact_sha256": observed_design,
        "v3_protocol_sha256": file_sha256(PROTOCOL_PATH),
        "v3_runtime_sha256": file_sha256(Path(__file__).resolve()),
    }


def load_chain(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.exists():
        return [], ZERO_HASH
    records: list[dict[str, Any]] = []
    previous = ZERO_HASH
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            observed = record.get("record_sha256")
            unsigned = {key: value for key, value in record.items() if key != "record_sha256"}
            if record.get("prior_record_chain_sha256") != previous:
                raise ValueError(f"broken prior hash at {path.name}:{line_number}")
            if observed != canonical_sha256(unsigned):
                raise ValueError(f"record hash mismatch at {path.name}:{line_number}")
            records.append(record)
            previous = str(observed)
    return records, previous


def append_chain_record(path: Path, record: dict[str, Any], previous: str) -> dict[str, Any]:
    output = dict(record)
    output["prior_record_chain_sha256"] = previous
    output["record_sha256"] = canonical_sha256(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n")
    return output


def load_design_metrics(protocol: dict[str, Any]) -> dict[str, dict[str, float]]:
    path = root_path(protocol["historical_design"]["artifact_path"])
    payload = json.loads(path.read_text(encoding="utf-8"))
    inputs = set(protocol["candidate"]["input_candidates"])
    output: dict[str, dict[str, float]] = {}
    for row in payload.get("authority_metrics", []):
        authority = str(row.get("respondent"))
        if authority not in protocol["balancing_authorities"]:
            continue
        source = row.get("candidate_metrics", {})
        values: dict[str, float] = {}
        for candidate in inputs:
            value = float(source[candidate]["mean_scaled_absolute_error"])
            if not math.isfinite(value) or value <= 0.0:
                raise ValueError(f"invalid design MASE for {authority}/{candidate}")
            values[candidate] = value
        output[authority] = values
    if set(output) != set(protocol["balancing_authorities"]):
        raise ValueError("design artifact does not cover every v3 authority")
    return output


def inverse_square_weights(
    authority: str,
    protocol: dict[str, Any],
    design_metrics: dict[str, dict[str, float]],
) -> dict[str, float]:
    candidates = protocol["candidate"]["input_candidates"]
    raw = {candidate: 1.0 / design_metrics[authority][candidate] ** 2 for candidate in candidates}
    total = sum(raw.values())
    if not math.isfinite(total) or total <= 0.0:
        raise ValueError("invalid v3 weight total")
    weights = {candidate: raw[candidate] / total for candidate in candidates}
    if any(value < 0.0 or not math.isfinite(value) for value in weights.values()):
        raise ValueError("v3 weights must be finite and nonnegative")
    if not math.isclose(sum(weights.values()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError("v3 weights must sum to one")
    return weights


def validate_parent_panel(panel: dict[str, Any], protocol: dict[str, Any]) -> None:
    if panel.get("schema") != "eia_grid_all_authority_direct_hourly_prediction_panel.v2":
        raise ValueError("unexpected v2 prediction panel schema")
    parent = protocol["parent_v2"]
    if panel.get("protocol_sha256") != parent["protocol_sha256"]:
        raise ValueError("v2 prediction panel protocol hash mismatch")
    if panel.get("protocol_commit") != parent["protocol_commit"]:
        raise ValueError("v2 prediction panel protocol commit mismatch")
    if panel.get("backfilled") is not False:
        raise ValueError("v2 prediction panel is marked as backfilled")
    if panel.get("target_actual_present_at_seal") is not False:
        raise ValueError("v2 panel had a target actual at seal")
    if panel.get("target_official_forecast_used") is not False:
        raise ValueError("v2 panel unexpectedly used a target official forecast")
    authorities = list(panel.get("authorities", []))
    if authorities != protocol["balancing_authorities"]:
        raise ValueError("v2 prediction panel authority order is incomplete or changed")
    rows = panel.get("authority_predictions", [])
    if len(rows) != 8 or [row.get("respondent") for row in rows] != authorities:
        raise ValueError("v2 prediction panel is not an atomic eight-authority panel")
    target = str(panel["target_period_end_utc"])
    parent_sealed = parse_timestamp(str(panel["sealed_utc"]))
    if parent_sealed >= target_interval_start_utc(target):
        raise ValueError("v2 panel was not sealed before the target interval")
    required = set(protocol["candidate"]["input_candidates"])
    for row in rows:
        values = row.get("candidate_predictions_mwh", {})
        if not required.issubset(values):
            raise ValueError("v2 authority row is missing a declared v3 input candidate")
        if row.get("target_actual_present_at_seal") is not False:
            raise ValueError("v2 authority row had a target actual at seal")
        scale = float(row["error_scale_mwh"])
        if not math.isfinite(scale) or scale <= 0.0:
            raise ValueError("v2 authority error scale must be positive and finite")


def compute_v3_panel(
    parent_panel: dict[str, Any],
    protocol: dict[str, Any],
    design_metrics: dict[str, dict[str, float]],
) -> list[dict[str, Any]]:
    validate_parent_panel(parent_panel, protocol)
    output: list[dict[str, Any]] = []
    inputs = protocol["candidate"]["input_candidates"]
    for row in parent_panel["authority_predictions"]:
        authority = str(row["respondent"])
        values = {candidate: float(row["candidate_predictions_mwh"][candidate]) for candidate in inputs}
        if any(not math.isfinite(value) or value < 0.0 for value in values.values()):
            raise ValueError("v2 candidate forecast must be finite and nonnegative")
        weights = inverse_square_weights(authority, protocol, design_metrics)
        forecast = sum(weights[candidate] * values[candidate] for candidate in inputs)
        lower = min(values.values())
        upper = max(values.values())
        if not math.isfinite(forecast) or forecast < lower - 1e-9 or forecast > upper + 1e-9:
            raise ValueError("v3 convex forecast fell outside its input envelope")
        output.append(
            {
                "respondent": authority,
                "respondent_name": row.get("respondent_name") or authority,
                "input_candidate_predictions_mwh": values,
                "input_candidate_predictions_sha256": canonical_sha256(values),
                "weights": weights,
                "weights_sha256": canonical_sha256(weights),
                "v3_prediction_mwh": forecast,
                "parent_v2_selected_candidate": row["selected_candidate"],
                "parent_v2_router_prediction_mwh": float(row["router_prediction_mwh"]),
                "error_scale_mwh": float(row["error_scale_mwh"]),
                "level_scale_mwh": float(row["level_scale_mwh"]),
                "target_actual_present_at_seal": False,
            }
        )
    return output


def eligible_parent_panels(
    parent_panels: list[dict[str, Any]],
    existing_panels: list[dict[str, Any]],
    protocol: dict[str, Any],
    sealed_at: datetime,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    existing_parent_hashes = {
        row["parent_v2_prediction_panel_record_sha256"] for row in existing_panels
    }
    first_allowed = protocol["prospective_window"]["first_allowed_period_end_utc"]
    minimum_lead = float(protocol["prospective_window"]["minimum_seal_lead_seconds"])
    maximum_lead = float(protocol["prospective_window"]["maximum_seal_lead_seconds"])
    selected: list[dict[str, Any]] = []
    skipped: dict[str, int] = {}
    seen_targets: dict[str, str] = {}
    for panel in parent_panels:
        validate_parent_panel(panel, protocol)
        target = str(panel["target_period_end_utc"])
        prior = seen_targets.get(target)
        if prior and prior != panel["record_sha256"]:
            raise ValueError(f"v2 chain contains replacement panels for {target}")
        seen_targets[target] = panel["record_sha256"]
        if panel["record_sha256"] in existing_parent_hashes:
            skipped["already_sealed"] = skipped.get("already_sealed", 0) + 1
            continue
        if target < first_allowed:
            skipped["before_v3_window"] = skipped.get("before_v3_window", 0) + 1
            continue
        lead = (target_interval_start_utc(target) - sealed_at).total_seconds()
        if lead < minimum_lead:
            skipped["below_frozen_minimum_lead"] = skipped.get(
                "below_frozen_minimum_lead", 0
            ) + 1
            continue
        if lead > maximum_lead:
            skipped["above_frozen_maximum_lead"] = skipped.get(
                "above_frozen_maximum_lead", 0
            ) + 1
            continue
        selected.append(panel)
    selected.sort(key=lambda row: row["target_period_end_utc"])
    return selected, skipped


def seal_from_parent(
    protocol: dict[str, Any],
    parent_panels: list[dict[str, Any]],
    parent_terminal: str,
    sealed_at: datetime,
    dry_run: bool,
    prediction_path: Path = PREDICTIONS_PATH,
) -> dict[str, Any]:
    existing, previous = load_chain(prediction_path)
    eligible, skipped = eligible_parent_panels(
        parent_panels, existing, protocol, sealed_at
    )
    design_metrics = load_design_metrics(protocol)
    frozen_inputs = verify_frozen_inputs(protocol)
    output: list[dict[str, Any]] = []
    for parent_panel in eligible:
        target = str(parent_panel["target_period_end_utc"])
        authority_predictions = compute_v3_panel(parent_panel, protocol, design_metrics)
        record = {
            "schema": "eia_grid_hourly_hybrid_confirmation_prediction_panel.v3",
            "protocol_id": protocol["protocol_id"],
            "protocol_sha256": frozen_inputs["v3_protocol_sha256"],
            "protocol_commit": git_commit_for_path(PROTOCOL_PATH),
            "runtime_sha256": frozen_inputs["v3_runtime_sha256"],
            "runtime_commit": repository_head(),
            "historical_design_artifact_sha256": frozen_inputs[
                "historical_design_artifact_sha256"
            ],
            "parent_v2_protocol_sha256": frozen_inputs["parent_v2_protocol_sha256"],
            "parent_v2_prediction_panel_record_sha256": parent_panel["record_sha256"],
            "parent_v2_prediction_chain_terminal_observed": parent_terminal,
            "parent_v2_sealed_utc": parent_panel["sealed_utc"],
            "parent_v2_source_panel_row_chain_sha256": parent_panel[
                "source_panel_row_chain_sha256"
            ],
            "parent_v2_source_receipt_sha256": parent_panel["source_receipt_sha256"],
            "target_period_end_utc": target,
            "target_interval_start_utc": target_interval_start_utc(target).isoformat(),
            "sealed_utc": sealed_at.isoformat(),
            "seal_lead_seconds": (
                target_interval_start_utc(target) - sealed_at
            ).total_seconds(),
            "authority_count": len(authority_predictions),
            "authorities": list(protocol["balancing_authorities"]),
            "authority_predictions": authority_predictions,
            "target_actual_present_at_seal": False,
            "backfilled": False,
            "scores_suppressed_before_confirmatory_window_close": True,
            "automatic_promotion_allowed": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        if dry_run:
            sealed = dict(record)
            sealed["prior_record_chain_sha256"] = previous
            sealed["record_sha256"] = canonical_sha256(sealed)
        else:
            sealed = append_chain_record(prediction_path, record, previous)
        previous = sealed["record_sha256"]
        output.append(sealed)
    return {
        "schema": "eia_grid_hourly_hybrid_confirmation_seal_run.v3",
        "run_utc": sealed_at.isoformat(),
        "dry_run": dry_run,
        "verified_parent_v2_panel_count": len(parent_panels),
        "prior_v3_panel_count": len(existing),
        "eligible_parent_v2_panel_count": len(eligible),
        "sealed_panel_count": len(output),
        "sealed_panels": output,
        "skipped": skipped,
    }


def validate_parent_settlement(
    settlement: dict[str, Any], protocol: dict[str, Any]
) -> None:
    if settlement.get("schema") != "eia_grid_all_authority_direct_hourly_settlement_panel.v2":
        raise ValueError("unexpected v2 settlement panel schema")
    if settlement.get("protocol_sha256") != protocol["parent_v2"]["protocol_sha256"]:
        raise ValueError("v2 settlement protocol hash mismatch")
    if settlement.get("protocol_commit") != protocol["parent_v2"]["protocol_commit"]:
        raise ValueError("v2 settlement protocol commit mismatch")
    rows = settlement.get("authority_metrics", [])
    if len(rows) != 8 or [row.get("respondent") for row in rows] != protocol[
        "balancing_authorities"
    ]:
        raise ValueError("v2 settlement is not a complete eight-authority panel")


def settle_from_parent(
    protocol: dict[str, Any],
    parent_settlements: list[dict[str, Any]],
    parent_terminal: str,
    dry_run: bool,
    prediction_path: Path = PREDICTIONS_PATH,
    settlement_path: Path = SETTLEMENTS_PATH,
) -> dict[str, Any]:
    predictions, _ = load_chain(prediction_path)
    existing, previous = load_chain(settlement_path)
    existing_prediction_hashes = {
        row["v3_prediction_panel_record_sha256"] for row in existing
    }
    by_parent_prediction: dict[str, dict[str, Any]] = {}
    for settlement in parent_settlements:
        validate_parent_settlement(settlement, protocol)
        parent_hash = str(settlement["prediction_panel_record_sha256"])
        if parent_hash in by_parent_prediction:
            raise ValueError("v2 settlement chain contains a duplicate prediction reference")
        by_parent_prediction[parent_hash] = settlement
    output: list[dict[str, Any]] = []
    for prediction in predictions:
        if prediction["record_sha256"] in existing_prediction_hashes:
            continue
        parent_hash = prediction["parent_v2_prediction_panel_record_sha256"]
        parent_settlement = by_parent_prediction.get(parent_hash)
        if parent_settlement is None:
            continue
        if parent_settlement["target_period_end_utc"] != prediction["target_period_end_utc"]:
            raise ValueError("v2 settlement target does not match v3 prediction")
        settlement_by_authority = {
            row["respondent"]: row for row in parent_settlement["authority_metrics"]
        }
        authority_metrics: list[dict[str, Any]] = []
        for forecast in prediction["authority_predictions"]:
            authority = forecast["respondent"]
            actual = float(settlement_by_authority[authority]["actual_mwh"])
            scale = float(forecast["error_scale_mwh"])
            v3_absolute = abs(actual - float(forecast["v3_prediction_mwh"]))
            comparator_metrics: dict[str, dict[str, float]] = {}
            for candidate, value in forecast["input_candidate_predictions_mwh"].items():
                absolute = abs(actual - float(value))
                comparator_metrics[candidate] = {
                    "absolute_error_mwh": absolute,
                    "scaled_absolute_error": absolute / scale,
                }
            parent_absolute = abs(
                actual - float(forecast["parent_v2_router_prediction_mwh"])
            )
            authority_metrics.append(
                {
                    "respondent": authority,
                    "actual_mwh": actual,
                    "error_scale_mwh": scale,
                    "v3_prediction_mwh": float(forecast["v3_prediction_mwh"]),
                    "v3_absolute_error_mwh": v3_absolute,
                    "v3_scaled_absolute_error": v3_absolute / scale,
                    "parent_v2_router_scaled_absolute_error": parent_absolute / scale,
                    "comparator_metrics": comparator_metrics,
                }
            )
        record = {
            "schema": "eia_grid_hourly_hybrid_confirmation_settlement_panel.v3",
            "settled_utc": now_utc().isoformat(),
            "target_period_end_utc": prediction["target_period_end_utc"],
            "authority_count": len(authority_metrics),
            "authorities": list(protocol["balancing_authorities"]),
            "authority_metrics": authority_metrics,
            "v3_prediction_panel_record_sha256": prediction["record_sha256"],
            "parent_v2_prediction_panel_record_sha256": parent_hash,
            "parent_v2_settlement_panel_record_sha256": parent_settlement[
                "record_sha256"
            ],
            "parent_v2_settlement_chain_terminal_observed": parent_terminal,
            "scores_suppressed_before_confirmatory_window_close": True,
            "automatic_promotion_allowed": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        if dry_run:
            settled = dict(record)
            settled["prior_record_chain_sha256"] = previous
            settled["record_sha256"] = canonical_sha256(settled)
        else:
            settled = append_chain_record(settlement_path, record, previous)
        previous = settled["record_sha256"]
        output.append(settled)
    return {
        "schema": "eia_grid_hourly_hybrid_confirmation_settlement_run.v3",
        "run_utc": now_utc().isoformat(),
        "dry_run": dry_run,
        "v3_prediction_panel_count": len(predictions),
        "prior_v3_settlement_panel_count": len(existing),
        "settled_panel_count": len(output),
        "settled_panels": output,
    }


def complete_utc_days(settlements: list[dict[str, Any]]) -> list[str]:
    by_day: dict[str, set[str]] = {}
    for row in settlements:
        period = str(row["target_period_end_utc"])
        by_day.setdefault(period[:10], set()).add(period)
    return sorted(day for day, periods in by_day.items() if len(periods) == 24)


def build_status(
    protocol: dict[str, Any],
    parent_prediction_count: int,
    parent_settlement_count: int,
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
    prediction_terminal: str,
    settlement_terminal: str,
) -> dict[str, Any]:
    settled_count = len(settlements)
    complete_days = complete_utc_days(settlements)
    window = protocol["prospective_window"]
    shakeout_ready = settled_count >= int(window["operational_shakeout_common_hours"])
    preliminary_ready = settled_count >= int(window["preliminary_common_hours"])
    confirmatory_sample_ready = (
        settled_count >= int(window["confirmatory_common_hours"])
        and len(complete_days) >= int(window["minimum_complete_utc_days"])
    )
    return {
        "schema": "eia_grid_hourly_hybrid_confirmation_status.v3",
        "generated_utc": now_utc().isoformat(),
        "state": (
            "WAITING_FOR_FIRST_ELIGIBLE_V2_PANEL"
            if not predictions
            else "V3_PANELS_AWAITING_ACTUALS"
            if not settlements
            else "V3_PROSPECTIVE_COLLECTION_ACTIVE"
        ),
        "protocol_id": protocol["protocol_id"],
        "protocol_sha256": file_sha256(PROTOCOL_PATH),
        "protocol_commit": git_commit_for_path(PROTOCOL_PATH),
        "runtime_sha256": file_sha256(Path(__file__).resolve()),
        "runtime_commit": repository_head(),
        "parent_v2_prediction_panel_count": parent_prediction_count,
        "parent_v2_settlement_panel_count": parent_settlement_count,
        "v3_prediction_panel_count": len(predictions),
        "v3_settlement_panel_count": settled_count,
        "v3_sealed_authority_prediction_count": len(predictions) * 8,
        "v3_settled_authority_prediction_count": settled_count * 8,
        "v3_prediction_terminal_sha256": prediction_terminal,
        "v3_settlement_terminal_sha256": settlement_terminal,
        "first_v3_settled_period": (
            settlements[0]["target_period_end_utc"] if settlements else None
        ),
        "latest_v3_settled_period": (
            settlements[-1]["target_period_end_utc"] if settlements else None
        ),
        "complete_utc_day_count": len(complete_days),
        "first_complete_utc_day": complete_days[0] if complete_days else None,
        "latest_complete_utc_day": complete_days[-1] if complete_days else None,
        "sample_gates": {
            "operational_shakeout_ready": shakeout_ready,
            "preliminary_sample_ready": preliminary_ready,
            "confirmatory_sample_ready": confirmatory_sample_ready,
            "note": "Sample readiness is not a performance or promotion decision.",
        },
        "performance": {
            "scores_suppressed": not confirmatory_sample_ready,
            "reason": (
                "FROZEN_CONFIRMATORY_WINDOW_OPEN"
                if not confirmatory_sample_ready
                else "READY_FOR_SEPARATE_FROZEN_CONFIRMATORY_ANALYSIS"
            ),
            "aggregate_metrics": None,
            "promotion_evaluation_complete": False,
            "automatic_promotion_allowed": False,
        },
        "succession": {
            "v2": "ACTIVE_PRESERVED_PARENT",
            "v3": "ACTIVE_FROZEN_PROSPECTIVE_CONFIRMATION",
            "v4": "DEFERRED_UNTIL_DISJOINT_TEMPORAL_REPLICATION",
            "v5": "DEFERRED_UNTIL_NAMED_INDEPENDENT_EVALUATOR",
        },
        "claim_boundary": protocol["claim_boundary"],
    }


@contextmanager
def cycle_lock(path: Path = LOCK_PATH) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"hourly hybrid confirmation cycle already locked: {path}") from exc
    try:
        os.write(
            descriptor,
            json.dumps({"pid": os.getpid(), "created_utc": now_utc().isoformat()}).encode(
                "utf-8"
            ),
        )
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def verify_references(
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
    parent_predictions: list[dict[str, Any]],
    parent_settlements: list[dict[str, Any]],
) -> None:
    parent_prediction_hashes = {row["record_sha256"] for row in parent_predictions}
    parent_settlement_hashes = {row["record_sha256"] for row in parent_settlements}
    prediction_hashes = {row["record_sha256"] for row in predictions}
    if any(
        row["parent_v2_prediction_panel_record_sha256"] not in parent_prediction_hashes
        for row in predictions
    ):
        raise ValueError("v3 prediction references a panel outside the verified v2 chain")
    if any(
        row["v3_prediction_panel_record_sha256"] not in prediction_hashes
        for row in settlements
    ):
        raise ValueError("v3 settlement references a prediction outside the v3 chain")
    if any(
        row["parent_v2_settlement_panel_record_sha256"] not in parent_settlement_hashes
        for row in settlements
    ):
        raise ValueError("v3 settlement references a panel outside the verified v2 chain")


def run_cycle(dry_run: bool = False, sealed_at: datetime | None = None) -> dict[str, Any]:
    with cycle_lock():
        protocol = load_protocol()
        frozen_inputs = verify_frozen_inputs(protocol)
        parent_predictions, parent_prediction_terminal = load_chain(
            root_path(protocol["parent_v2"]["prediction_panel_chain_path"])
        )
        parent_settlements, parent_settlement_terminal = load_chain(
            root_path(protocol["parent_v2"]["settlement_panel_chain_path"])
        )
        seal = seal_from_parent(
            protocol,
            parent_predictions,
            parent_prediction_terminal,
            sealed_at or now_utc(),
            dry_run,
        )
        settle = settle_from_parent(
            protocol,
            parent_settlements,
            parent_settlement_terminal,
            dry_run,
        )
        predictions, prediction_terminal = load_chain(PREDICTIONS_PATH)
        settlements, settlement_terminal = load_chain(SETTLEMENTS_PATH)
        verify_references(
            predictions, settlements, parent_predictions, parent_settlements
        )
        status = build_status(
            protocol,
            len(parent_predictions),
            len(parent_settlements),
            predictions,
            settlements,
            prediction_terminal,
            settlement_terminal,
        )
        receipt = {
            "schema": "eia_grid_hourly_hybrid_confirmation_operational_run.v3",
            "run_utc": now_utc().isoformat(),
            "dry_run": dry_run,
            "frozen_inputs": frozen_inputs,
            "protocol_commit": status["protocol_commit"],
            "runtime_commit": status["runtime_commit"],
            "parent_v2_prediction_panel_count": len(parent_predictions),
            "parent_v2_prediction_terminal_sha256": parent_prediction_terminal,
            "parent_v2_settlement_panel_count": len(parent_settlements),
            "parent_v2_settlement_terminal_sha256": parent_settlement_terminal,
            "sealed_v3_panel_count": seal["sealed_panel_count"],
            "settled_v3_panel_count": settle["settled_panel_count"],
            "v3_prediction_panel_count": len(predictions),
            "v3_prediction_terminal_sha256": prediction_terminal,
            "v3_settlement_panel_count": len(settlements),
            "v3_settlement_terminal_sha256": settlement_terminal,
            "status_sha256": canonical_sha256(status),
            "automatic_promotion_allowed": False,
            "claim_boundary": protocol["claim_boundary"],
        }
        operational = None
        if not dry_run:
            _, previous = load_chain(RUN_RECEIPTS_PATH)
            operational = append_chain_record(RUN_RECEIPTS_PATH, receipt, previous)
            status["operational_receipt_sha256"] = operational["record_sha256"]
            write_json_atomic(STATUS_PATH, status)
        result = {
            "schema": "eia_grid_hourly_hybrid_confirmation_cycle.v3",
            "dry_run": dry_run,
            "seal": seal,
            "settle": settle,
            "status": status,
            "operational_receipt": operational,
        }
        if not dry_run:
            write_json_atomic(LATEST_CYCLE_PATH, result)
        return result


def check_state() -> dict[str, Any]:
    protocol = load_protocol()
    frozen_inputs = verify_frozen_inputs(protocol)
    parent_predictions, parent_prediction_terminal = load_chain(
        root_path(protocol["parent_v2"]["prediction_panel_chain_path"])
    )
    parent_settlements, parent_settlement_terminal = load_chain(
        root_path(protocol["parent_v2"]["settlement_panel_chain_path"])
    )
    predictions, prediction_terminal = load_chain(PREDICTIONS_PATH)
    settlements, settlement_terminal = load_chain(SETTLEMENTS_PATH)
    verify_references(predictions, settlements, parent_predictions, parent_settlements)
    return {
        "schema": "eia_grid_hourly_hybrid_confirmation_check.v3",
        "checked_utc": now_utc().isoformat(),
        "ok": True,
        "frozen_inputs": frozen_inputs,
        "parent_v2_prediction_panel_count": len(parent_predictions),
        "parent_v2_prediction_terminal_sha256": parent_prediction_terminal,
        "parent_v2_settlement_panel_count": len(parent_settlements),
        "parent_v2_settlement_terminal_sha256": parent_settlement_terminal,
        "v3_prediction_panel_count": len(predictions),
        "v3_prediction_terminal_sha256": prediction_terminal,
        "v3_settlement_panel_count": len(settlements),
        "v3_settlement_terminal_sha256": settlement_terminal,
        "status": build_status(
            protocol,
            len(parent_predictions),
            len(parent_settlements),
            predictions,
            settlements,
            prediction_terminal,
            settlement_terminal,
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = check_state() if args.check else run_cycle(dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
