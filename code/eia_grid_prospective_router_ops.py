"""Operate and audit the preregistered EIA prospective hybrid router."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = ROOT / "code" / "eia_grid_prospective_hybrid_router.py"
OUT_DIR = ROOT / "out" / "eia_grid_prospective_hybrid_router"
RUN_RECEIPTS_PATH = OUT_DIR / "operational_runs.jsonl"
STATUS_PATH = OUT_DIR / "prospective_status_latest.json"
LOCK_PATH = OUT_DIR / ".prospective_cycle.lock"


def load_core():
    spec = importlib.util.spec_from_file_location("eia_grid_prospective_core", CORE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load router core from {CORE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


core = load_core()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@contextmanager
def cycle_lock(path: Path = LOCK_PATH) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise RuntimeError(f"prospective router cycle already locked: {path}") from exc
    try:
        lock_payload = {"pid": os.getpid(), "created_utc": now_utc()}
        os.write(descriptor, json.dumps(lock_payload, sort_keys=True).encode("utf-8"))
        os.close(descriptor)
        descriptor = -1
        yield
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        path.unlink(missing_ok=True)


def chain_snapshot(path: Path) -> dict[str, Any]:
    records, terminal = core.load_chain(path)
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "record_count": len(records),
        "terminal_sha256": terminal,
        "records": records,
    }


def validate_cross_chain(
    predictions: list[dict[str, Any]], settlements: list[dict[str, Any]]
) -> None:
    prediction_keys = [(row["respondent"], row["target_date"]) for row in predictions]
    if len(prediction_keys) != len(set(prediction_keys)):
        raise ValueError("duplicate respondent-target prediction detected")
    prediction_hashes = {row["record_sha256"] for row in predictions}
    settlement_keys = [
        (row["respondent"], row["target_date"], row["prediction_record_sha256"])
        for row in settlements
    ]
    if len(settlement_keys) != len(set(settlement_keys)):
        raise ValueError("duplicate settlement detected")
    missing = [row for row in settlements if row["prediction_record_sha256"] not in prediction_hashes]
    if missing:
        raise ValueError("settlement references a prediction outside the verified chain")


def build_status(
    protocol: dict[str, Any],
    predictions: list[dict[str, Any]],
    settlements: list[dict[str, Any]],
) -> dict[str, Any]:
    authorities = list(protocol["balancing_authorities"])
    prediction_counts = {
        authority: sum(row["respondent"] == authority for row in predictions)
        for authority in authorities
    }
    settlement_counts = {
        authority: sum(row["respondent"] == authority for row in settlements)
        for authority in authorities
    }
    settled_dates = {
        authority: {
            row["target_date"] for row in settlements if row["respondent"] == authority
        }
        for authority in authorities
    }
    common_dates = sorted(set.intersection(*(settled_dates[key] for key in authorities))) if authorities else []

    router_scores = [float(row["router_seasonal_mase_7"]) for row in settlements]
    route_hits = [bool(row["route_hit"]) for row in settlements]
    regrets = [float(row["router_regret_to_oracle"]) for row in settlements]
    specialists = list(protocol["comparators"]["predeclared_fixed_specialists"])
    specialist_scores = {
        specialist: [
            float(row["specialist_metrics"][specialist]["seasonal_mase_7"])
            for row in settlements
            if specialist in row["specialist_metrics"]
        ]
        for specialist in specialists
    }
    specialist_means = {
        specialist: (mean(values) if values else None)
        for specialist, values in specialist_scores.items()
    }
    scored_fixed = {
        specialist: score for specialist, score in specialist_means.items() if score is not None
    }
    best_fixed = min(scored_fixed, key=lambda key: (scored_fixed[key], key)) if scored_fixed else None
    windows = protocol["prospective_window"]
    common_count = len(common_dates)

    if not predictions:
        state = "WAITING_FOR_FIRST_ELIGIBLE_FORECAST"
    elif not settlements:
        state = "SEALED_AWAITING_ACTUALS"
    else:
        state = "PROSPECTIVE_COLLECTION_ACTIVE"

    return {
        "schema": "eia_grid_prospective_router_status.v1",
        "generated_utc": now_utc(),
        "state": state,
        "protocol_sha256": core.file_sha256(core.PROTOCOL_PATH),
        "protocol_commit": core.protocol_commit(),
        "first_allowed_target_date": windows["first_allowed_target_date"],
        "prediction_count": len(predictions),
        "settlement_count": len(settlements),
        "prediction_count_by_authority": prediction_counts,
        "settlement_count_by_authority": settlement_counts,
        "common_settled_day_count": common_count,
        "first_common_settled_date": common_dates[0] if common_dates else None,
        "latest_common_settled_date": common_dates[-1] if common_dates else None,
        "sample_gates": {
            "preliminary_30_days_ready": common_count
            >= int(windows["preliminary_gate_common_days_per_authority"]),
            "confirmatory_90_days_ready": common_count
            >= int(windows["confirmatory_gate_common_days_per_authority"]),
            "durability_180_days_ready": common_count
            >= int(windows["durability_gate_common_days_per_authority"]),
            "note": "Sample readiness does not mean a scientific promotion gate passed.",
        },
        "router_mean_seasonal_mase_7": mean(router_scores) if router_scores else None,
        "fixed_specialist_mean_seasonal_mase_7": specialist_means,
        "current_best_fixed_specialist": best_fixed,
        "current_best_fixed_mean_seasonal_mase_7": scored_fixed.get(best_fixed)
        if best_fixed
        else None,
        "router_skill_vs_current_best_fixed": (
            scored_fixed[best_fixed] - mean(router_scores)
            if best_fixed and router_scores
            else None
        ),
        "route_hit_rate": mean(route_hits) if route_hits else None,
        "mean_regret_to_oracle": mean(regrets) if regrets else None,
        "promotion_evaluation_complete": False,
        "claim_boundary": protocol["claim_boundary"],
    }


def append_operational_receipt(
    payload: dict[str, Any], path: Path = RUN_RECEIPTS_PATH
) -> dict[str, Any]:
    _, previous = core.load_chain(path)
    return core.append_chain_record(path, payload, previous)


def run_cycle(timeout: int = 60, dry_run: bool = False) -> dict[str, Any]:
    with cycle_lock():
        protocol = core.load_protocol()
        before_predictions = chain_snapshot(core.PREDICTIONS_PATH)
        before_settlements = chain_snapshot(core.SETTLEMENTS_PATH)
        validate_cross_chain(before_predictions["records"], before_settlements["records"])

        seal_result = core.seal_latest(protocol, timeout=timeout, dry_run=dry_run)
        settlement_result = core.settle(protocol, timeout=timeout, dry_run=dry_run)

        after_predictions = chain_snapshot(core.PREDICTIONS_PATH)
        after_settlements = chain_snapshot(core.SETTLEMENTS_PATH)
        validate_cross_chain(after_predictions["records"], after_settlements["records"])
        status = build_status(protocol, after_predictions["records"], after_settlements["records"])

        receipt_payload = {
            "schema": "eia_grid_prospective_router_operational_run.v1",
            "run_utc": now_utc(),
            "dry_run": dry_run,
            "protocol_sha256": status["protocol_sha256"],
            "protocol_commit": status["protocol_commit"],
            "before": {
                "prediction_count": before_predictions["record_count"],
                "prediction_terminal_sha256": before_predictions["terminal_sha256"],
                "settlement_count": before_settlements["record_count"],
                "settlement_terminal_sha256": before_settlements["terminal_sha256"],
            },
            "seal_result_sha256": core.canonical_sha256(seal_result),
            "seal_record_count": int(seal_result.get("sealed_record_count", 0)),
            "seal_skipped": seal_result.get("skipped", {}),
            "source_panel_row_count": seal_result.get("source_panel_row_count"),
            "source_panel_row_chain_sha256": seal_result.get(
                "source_panel_row_chain_sha256"
            ),
            "settlement_result_sha256": core.canonical_sha256(settlement_result),
            "settled_record_count": int(settlement_result.get("settled_record_count", 0)),
            "after": {
                "prediction_count": after_predictions["record_count"],
                "prediction_terminal_sha256": after_predictions["terminal_sha256"],
                "settlement_count": after_settlements["record_count"],
                "settlement_terminal_sha256": after_settlements["terminal_sha256"],
            },
            "status_sha256": core.canonical_sha256(status),
            "claim_boundary": protocol["claim_boundary"],
        }

        operational_receipt = None
        if not dry_run:
            operational_receipt = append_operational_receipt(receipt_payload)
            status["operational_receipt_sha256"] = operational_receipt["record_sha256"]
            write_json(STATUS_PATH, status)

        return {
            "schema": "eia_grid_prospective_router_cycle.v1",
            "dry_run": dry_run,
            "seal": seal_result,
            "settle": settlement_result,
            "status": status,
            "operational_receipt": operational_receipt,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run_cycle(timeout=args.timeout, dry_run=args.dry_run)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
