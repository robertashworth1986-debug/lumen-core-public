#!/usr/bin/env python3
"""Build synthetic public-safe V3 custody fixtures for offline verification."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = (
    ROOT
    / "tests"
    / "fixtures"
    / "eia_v3_custody_watchdog"
    / "valid_accumulating_spec.json"
)
DEFAULT_POLICY = (
    ROOT / "config" / "eia_grid_hourly_hybrid_confirmation_custody_watchdog_v1.json"
)
ZERO_HASH = "0" * 64
SCENARIOS = {
    "valid",
    "broken_chain",
    "before_first_allowed",
    "duplicate_period",
    "duplicate_settlement_period",
    "missing_target_period",
    "missing_authority",
    "invalid_lead",
    "actual_present_at_seal",
    "backfill",
    "count_mismatch",
    "parent_binding_mismatch",
    "score_leakage",
    "automatic_promotion",
}


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
    ).hexdigest()


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_period(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%dT%H").replace(tzinfo=timezone.utc)


def period_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H")


def utc_text(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def identity(policy: dict[str, Any]) -> dict[str, str]:
    frozen = policy["frozen_source"]
    contract = policy["protocol_contract"]
    return {
        "protocol_id": contract["protocol_id"],
        "protocol_sha256": frozen["artifacts"]["protocol"]["sha256"],
        "runtime_sha256": frozen["artifacts"]["runtime"]["sha256"],
        "frozen_source_commit": frozen["commit"],
        "parent_v2_protocol_id": contract["parent_v2_protocol_id"],
        "parent_v2_protocol_sha256": frozen["artifacts"]["parent_v2_protocol"][
            "sha256"
        ],
        "parent_v2_protocol_commit": contract["parent_v2_protocol_commit"],
    }


def complete_utc_days(targets: set[str]) -> int:
    by_day: dict[str, set[int]] = {}
    for target in targets:
        by_day.setdefault(target[:10], set()).add(int(target[-2:]))
    return sum(1 for hours in by_day.values() if hours == set(range(24)))


def readiness(
    settlement_count: int, complete_days: int, policy: dict[str, Any]
) -> dict[str, bool]:
    contract = policy["protocol_contract"]
    hour_168 = settlement_count >= contract["operational_shakeout_common_hours"]
    hour_720 = settlement_count >= contract["preliminary_common_hours"]
    hour_2160 = settlement_count >= contract["confirmatory_common_hours"]
    day_90 = complete_days >= contract["minimum_complete_utc_days"]
    return {
        "operational_shakeout_168_hours": hour_168,
        "preliminary_720_hours": hour_720,
        "confirmatory_2160_hours": hour_2160,
        "minimum_90_complete_utc_days": day_90,
        "confirmatory_sample_ready": hour_2160 and day_90,
    }


def chain_records(records: list[dict[str, Any]], *, broken: bool = False) -> None:
    previous = ZERO_HASH
    for index, record in enumerate(records):
        record.pop("record_sha256", None)
        record["prior_record_chain_sha256"] = (
            "f" * 64 if broken and index == 1 else previous
        )
        record["record_sha256"] = canonical_sha256(record)
        previous = record["record_sha256"]


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
            for value in values
        ),
        encoding="utf-8",
        newline="\n",
    )


def build_fixture(
    output_dir: Path,
    spec: dict[str, Any],
    policy: dict[str, Any],
    *,
    scenario: str = "valid",
) -> Path:
    if scenario not in SCENARIOS:
        raise ValueError(f"unknown fixture scenario: {scenario}")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("fixture output directory must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = policy["protocol_contract"]
    input_contract = policy["input_contract"]
    authorities = list(contract["balancing_authorities"])
    frozen_identity = identity(policy)
    first = parse_period(spec["first_target_period_end_utc"])
    if scenario == "before_first_allowed":
        first -= timedelta(hours=1)
    prediction_count = int(spec["prediction_panel_count"])
    settlement_count = int(spec["settlement_panel_count"])
    lead_seconds = int(spec["seal_lead_seconds"])
    if prediction_count < 1 or settlement_count < 0 or settlement_count > prediction_count:
        raise ValueError("fixture counts are invalid")

    predictions: list[dict[str, Any]] = []
    for index in range(prediction_count):
        target = first + timedelta(hours=index)
        if scenario == "duplicate_period" and index == 1:
            target = first
        if scenario == "missing_target_period" and index >= 1:
            target += timedelta(hours=1)
        record_lead = 3000 if scenario == "invalid_lead" and index == 0 else lead_seconds
        interval_start = target - timedelta(hours=1)
        sealed = interval_start - timedelta(seconds=record_lead)
        record_authorities = authorities
        if scenario == "missing_authority" and index == 0:
            record_authorities = authorities[:-1]
        actual_present = scenario == "actual_present_at_seal" and index == 0
        parent_record_hash = hashlib.sha256(
            f"parent-v2-prediction-{index}".encode("utf-8")
        ).hexdigest()
        predictions.append(
            {
                "schema": input_contract["prediction_schema"],
                **frozen_identity,
                "target_period_end_utc": period_text(target),
                "target_interval_start_utc": utc_text(interval_start),
                "sealed_utc": utc_text(sealed),
                "seal_lead_seconds": record_lead,
                "authority_count": len(record_authorities),
                "authorities": list(record_authorities),
                "authority_rows": [
                    {
                        "respondent": authority,
                        "target_actual_present_at_seal": actual_present,
                    }
                    for authority in record_authorities
                ],
                "target_actual_present_at_seal": actual_present,
                "backfilled": scenario == "backfill" and index == 0,
                "scores_suppressed": True,
                "automatic_promotion_allowed": False,
                "parent_v2_prediction_panel_record_sha256": parent_record_hash,
                "parent_v2_prediction_chain_terminal_observed": hashlib.sha256(
                    f"parent-v2-prediction-terminal-{index}".encode("utf-8")
                ).hexdigest(),
            }
        )
    chain_records(predictions, broken=scenario == "broken_chain")

    settlements: list[dict[str, Any]] = []
    for index in range(settlement_count):
        prediction = predictions[index]
        target = parse_period(prediction["target_period_end_utc"])
        settlements.append(
            {
                "schema": input_contract["settlement_schema"],
                **frozen_identity,
                "target_period_end_utc": prediction["target_period_end_utc"],
                "settled_utc": utc_text(target + timedelta(minutes=15)),
                "authority_count": 8,
                "authorities": authorities,
                "authority_rows": [
                    {"respondent": authority} for authority in authorities
                ],
                "scores_suppressed": True,
                "automatic_promotion_allowed": False,
                "v3_prediction_panel_record_sha256": prediction["record_sha256"],
                "parent_v2_prediction_panel_record_sha256": prediction[
                    "parent_v2_prediction_panel_record_sha256"
                ]
                if scenario != "parent_binding_mismatch" or index != 0
                else hashlib.sha256(b"mismatched-parent-v2-prediction").hexdigest(),
                "parent_v2_settlement_panel_record_sha256": hashlib.sha256(
                    f"parent-v2-settlement-{index}".encode("utf-8")
                ).hexdigest(),
                "parent_v2_settlement_chain_terminal_observed": hashlib.sha256(
                    f"parent-v2-settlement-terminal-{index}".encode("utf-8")
                ).hexdigest(),
            }
        )
    chain_records(settlements)
    if scenario == "duplicate_settlement_period" and len(settlements) > 1:
        settlements[1]["target_period_end_utc"] = settlements[0][
            "target_period_end_utc"
        ]
        chain_records(settlements)

    prediction_terminal = predictions[-1]["record_sha256"] if predictions else ZERO_HASH
    settlement_terminal = settlements[-1]["record_sha256"] if settlements else ZERO_HASH
    settlement_targets = {row["target_period_end_utc"] for row in settlements}
    complete_days = complete_utc_days(settlement_targets)
    unsettled_count = prediction_count - settlement_count
    status = {
        "schema": input_contract["status_schema"],
        **frozen_identity,
        "generated_utc": spec["generated_utc"],
        "prediction_panel_count": prediction_count,
        "settlement_panel_count": settlement_count,
        "complete_utc_day_count": complete_days,
        "unsettled_panel_count": unsettled_count,
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_terminal_sha256": settlement_terminal,
        "sample_readiness": readiness(settlement_count, complete_days, policy),
        "scores_suppressed": True,
        "performance_evaluated": False,
        "automatic_promotion_allowed": False,
    }
    if scenario == "count_mismatch":
        status["prediction_panel_count"] += 1
    if scenario == "score_leakage":
        status["model_score"] = 0.5
    if scenario == "automatic_promotion":
        status["automatic_promotion_allowed"] = True
    status_sha256 = canonical_sha256(status)
    operational = {
        "schema": input_contract["operational_receipt_schema"],
        **frozen_identity,
        "run_utc": spec["generated_utc"],
        "prediction_panel_count": prediction_count,
        "settlement_panel_count": settlement_count,
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_terminal_sha256": settlement_terminal,
        "complete_utc_day_count": complete_days,
        "unsettled_panel_count": unsettled_count,
        "status_sha256": status_sha256,
        "scores_suppressed": True,
        "performance_evaluated": False,
        "automatic_promotion_allowed": False,
    }

    prediction_path = output_dir / "prediction_custody_panels.jsonl"
    settlement_path = output_dir / "settlement_custody_panels.jsonl"
    status_path = output_dir / "status.json"
    operational_path = output_dir / "operational_receipt.json"
    write_jsonl(prediction_path, predictions)
    write_jsonl(settlement_path, settlements)
    write_json(status_path, status)
    write_json(operational_path, operational)
    descriptors = {
        path.name: {"bytes": path.stat().st_size, "sha256": file_sha256(path)}
        for path in (
            operational_path,
            prediction_path,
            settlement_path,
            status_path,
        )
    }
    manifest = {
        "schema": input_contract["snapshot_schema"],
        "snapshot_kind": spec["snapshot_kind"],
        "generated_utc": spec["generated_utc"],
        "frozen_source": {
            "repository": policy["frozen_source"]["repository"],
            **frozen_identity,
        },
        "files": descriptors,
        "prediction_panel_count": prediction_count,
        "settlement_panel_count": settlement_count,
        "complete_utc_day_count": complete_days,
        "unsettled_panel_count": unsettled_count,
        "prediction_terminal_sha256": prediction_terminal,
        "settlement_terminal_sha256": settlement_terminal,
        "status_sha256": status_sha256,
        "scores_suppressed": True,
        "performance_evaluated": False,
        "automatic_promotion_allowed": False,
    }
    write_json(output_dir / "manifest.json", manifest)
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), default="valid")
    args = parser.parse_args()
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    policy = json.loads(args.policy.read_text(encoding="utf-8"))
    build_fixture(args.output_dir, spec, policy, scenario=args.scenario)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
