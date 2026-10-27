from __future__ import annotations

import csv
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OPS_OUT = ROOT / "out" / "ops"

LIVE_BREADTH_PANEL = OPS_OUT / "live_breadth_value_panel_latest.json"
INFRA_FROZEN_DELTAS = ROOT / "out" / "infra_frozen_deltas.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def reject_duplicate_members(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON member: {key}")
        result[key] = value
    return result


def reject_nonfinite_constant(value: str) -> Any:
    raise ValueError(f"Nonfinite JSON number: {value}")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=reject_duplicate_members, parse_constant=reject_nonfinite_constant)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        row = json.loads(raw, object_pairs_hook=reject_duplicate_members, parse_constant=reject_nonfinite_constant)
        if not isinstance(row, dict):
            raise ValueError("Frozen delta rows must be JSON objects")
        rows.append(row)
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\n") + "\n", encoding="utf-8")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


MODEL_BOUNDARY = (
    "Unvalidated model context only. A source registry flag, source hash or frozen metric delta "
    "does not establish equivalent service, causal savings, overhead, annual persistence or buyer acceptance. "
    "Scenario sums assume 8,760 constant hours and unverified additivity; they are not measured savings."
)


def as_float(value: Any, default: float | None = None) -> float | None:
    if value is None or isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


def as_bool(value: Any) -> bool:
    return value is True


def complete_sum(rows: list[dict[str, Any]], key: str) -> float | None:
    values = [as_float(row.get(key)) for row in rows]
    if not values or any(value is None for value in values):
        return None
    try:
        return as_float(math.fsum(values))
    except OverflowError:
        return None


def display_number(value: Any) -> str:
    number = as_float(value)
    return "UNKNOWN" if number is None else f"{number:,.2f}"


def selection_timestamp(value: Any) -> datetime:
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Frozen row needs a valid generated_utc timestamp") from exc
    if timestamp.tzinfo is None:
        raise ValueError("Frozen row generated_utc must contain a timezone")
    return timestamp.astimezone(timezone.utc)


def pick_latest_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest_map: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        source = str(row.get("source") or "").strip()
        if not source:
            continue
        key = tuple(str(row.get(name) or "").strip().casefold() for name in ("source", "sector", "constraint"))
        timestamp = selection_timestamp(row.get("generated_utc"))
        current = latest_map.get(key)
        if current is None or timestamp > selection_timestamp(current.get("generated_utc")):
            latest_map[key] = row
        elif timestamp == selection_timestamp(current.get("generated_utc")) and row != current:
            raise ValueError("Conflicting frozen rows share an identity and timestamp")
    return list(latest_map.values())


def build_top_lanes(source_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    lanes: list[dict[str, Any]] = []
    for row in source_rows:
        source = str(row.get("source") or "").strip()
        if not source:
            continue
        baseline = as_float(row.get("baseline_loss_rate_usd_per_hour"))
        gain = as_float(row.get("optimization_gain_pct"))
        modeled = as_float(baseline * gain / 100) if baseline is not None and baseline >= 0 and gain is not None else None
        annual = as_float(modeled * 8760) if modeled is not None else None
        issues = list(row.get("input_issues") or [])
        if modeled is None or annual is None:
            issues.append("missing_invalid_or_overflowing_signed_model")
        if gain is not None and gain > 100:
            issues.append("gain_exceeds_100_pct_loss_reduction_bound")
        reported = as_float(row.get("reported_estimated_hourly_value_usd", row.get("estimated_hourly_value_usd")))
        if reported is not None and modeled is not None and not math.isclose(reported, modeled, rel_tol=1e-9, abs_tol=1e-9):
            issues.append("reported_value_conflicts_with_signed_model")
        lane = {
            "source": source,
            "sector": str(row.get("sector") or "").strip(),
            "constraint": str(row.get("constraint") or "").strip() or "default",
            "generated_utc": str(row.get("generated_utc") or "").strip(),
            "optimization_gain_pct": gain,
            "baseline_loss_rate_usd_per_hour": baseline,
            "estimated_hourly_value_usd": None,
            "estimated_daily_value_usd": None,
            "estimated_annual_value_usd": None,
            "reported_estimated_hourly_value_usd": reported,
            "reported_estimated_annual_value_usd": as_float(row.get("reported_estimated_annual_value_usd", row.get("estimated_annual_value_usd"))),
            "modeled_hourly_value_usd": modeled,
            "modeled_daily_value_usd": as_float(modeled * 24) if modeled is not None else None,
            "modeled_annual_value_usd": annual,
            "trust_tier": str(row.get("trust_tier") or "").strip(),
            "enabled_source": as_bool(row.get("enabled_source")),
            "measured_source": as_bool(row.get("measured_source")),
            "primary_live_evidence": False,
            "effect_validated": False,
            "reported_primary_live_evidence": as_bool(row.get("primary_live_evidence")),
            "premium_tier": "unvalidated_model_context",
            "input_issues": sorted(set(issues)),
            "evidence_status": "INVALID_INPUT_REVIEW" if issues else "UNVALIDATED_MODEL_INPUT",
            "model_boundary": MODEL_BOUNDARY,
        }
        lanes.append(lane)
    lanes.sort(key=lambda row: (row["modeled_hourly_value_usd"] is not None, row["modeled_hourly_value_usd"] or 0), reverse=True)
    return lanes


def build_markdown(payload: dict[str, Any]) -> str:
    headline = payload["headline"]
    lines = ["# Multi Asset Frozen Delta Pack", "", f"Generated UTC: {payload.get('generated_utc', '')}", "",
             "Accepted annual savings: **UNKNOWN**. No economic or operational promotion is authorized.", "", MODEL_BOUNDARY, "",
             f"- Lanes retained: {headline['lane_count']}",
             f"- Invalid model inputs: {headline['invalid_input_count']}",
             f"- Arithmetic modeled annual sum: {display_number(headline['modeled_annual_value_usd'])} USD", "",
             "## Model context (not measured savings)", "",
             "| Source | Sector | Signed metric gain % | Modeled hourly USD | Modeled annual USD | Status |",
             "|---|---|---:|---:|---:|---|"]
    for row in payload["top_lanes"]:
        lines.append(f"| {row['source']} | {row['sector']} | {display_number(row['optimization_gain_pct'])} | {display_number(row['modeled_hourly_value_usd'])} | {display_number(row['modeled_annual_value_usd'])} | {row['evidence_status']} |")
    return "\n".join(lines) + "\n"


def build_payload(panel: dict[str, Any], frozen_rows: list[dict[str, Any]]) -> dict[str, Any]:
    panel_rows = panel.get("source_rows") if isinstance(panel.get("source_rows"), list) else []
    latest_rows = pick_latest_rows([row for row in panel_rows if isinstance(row, dict)])
    lanes = build_top_lanes(latest_rows)
    latest_frozen = pick_latest_rows(frozen_rows)
    return {
        "generated_utc": now_iso(), "run_tag": now_tag(), "scope": "multi_asset_frozen_delta_pack",
        "inputs": {
            "live_breadth_value_panel_latest_json": str(LIVE_BREADTH_PANEL),
            "infra_frozen_deltas_jsonl": str(INFRA_FROZEN_DELTAS),
            "panel_source_rows": len(panel_rows), "panel_latest_rows": len(latest_rows),
            "infra_frozen_rows_raw": len(frozen_rows), "infra_frozen_rows_latest": len(latest_frozen),
        },
        "headline": {
            "lane_count": len(lanes), "enabled_source_count": sum(row["enabled_source"] for row in lanes),
            "measured_source_count": sum(row["measured_source"] for row in lanes),
            "measurement_basis": "REGISTRY_REPORTED_INTAKE_ONLY",
            "estimated_hourly_value_usd": None, "estimated_annual_value_usd": None,
            "ten_k_plus_lane_count": None, "top_lane_hourly_value_usd": None,
            "modeled_hourly_value_usd": complete_sum(lanes, "modeled_hourly_value_usd"),
            "modeled_annual_value_usd": complete_sum(lanes, "modeled_annual_value_usd"),
            "invalid_input_count": sum(bool(row["input_issues"]) for row in lanes),
            "top_lane_source": lanes[0]["source"] if lanes else "",
            "top_lane_sector": lanes[0]["sector"] if lanes else "",
        },
        "claim_gate": {
            "public_economic_value_claim_allowed": False, "field_performance_validated": False,
            "trading_profit_proven": False, "accepted_annual_savings_usd": None, "boundary": MODEL_BOUNDARY,
        },
        "top_lanes": lanes,
    }


def main() -> int:
    panel = load_json(LIVE_BREADTH_PANEL, {})
    if not isinstance(panel, dict):
        raise SystemExit(f"Invalid panel payload: {LIVE_BREADTH_PANEL}")

    frozen_rows = load_jsonl(INFRA_FROZEN_DELTAS)
    payload = build_payload(panel, frozen_rows)
    run_tag = payload["run_tag"]
    top_lanes = payload["top_lanes"]

    json_tagged = OPS_OUT / f"multi_asset_frozen_delta_pack_{run_tag}.json"
    json_latest = OPS_OUT / "multi_asset_frozen_delta_pack_latest.json"
    md_tagged = OPS_OUT / f"multi_asset_frozen_delta_pack_{run_tag}.md"
    md_latest = OPS_OUT / "multi_asset_frozen_delta_pack_latest.md"
    csv_tagged = OPS_OUT / f"multi_asset_frozen_delta_pack_{run_tag}.csv"
    csv_latest = OPS_OUT / "multi_asset_frozen_delta_pack_latest.csv"

    write_json(json_tagged, payload)
    write_json(json_latest, payload)

    md_text = build_markdown(payload)
    write_text(md_tagged, md_text)
    write_text(md_latest, md_text)

    csv_rows: list[dict[str, Any]] = []
    for row in top_lanes:
        csv_rows.append(
            {
                "source": row.get("source", ""),
                "sector": row.get("sector", ""),
                "constraint": row.get("constraint", ""),
                "estimated_hourly_value_usd": row.get("estimated_hourly_value_usd"),
                "estimated_annual_value_usd": row.get("estimated_annual_value_usd"),
                "modeled_hourly_value_usd": row.get("modeled_hourly_value_usd"),
                "modeled_annual_value_usd": row.get("modeled_annual_value_usd"),
                "evidence_status": row.get("evidence_status"),
                "model_boundary": MODEL_BOUNDARY,
                "optimization_gain_pct": row.get("optimization_gain_pct", 0.0),
                "premium_tier": row.get("premium_tier", ""),
                "enabled_source": row.get("enabled_source", False),
                "measured_source": row.get("measured_source", False),
            }
        )

    write_csv(
        csv_tagged,
        csv_rows,
        [
            "source",
            "sector",
            "constraint",
            "estimated_hourly_value_usd",
            "estimated_annual_value_usd",
            "modeled_hourly_value_usd",
            "modeled_annual_value_usd",
            "evidence_status",
            "model_boundary",
            "optimization_gain_pct",
            "premium_tier",
            "enabled_source",
            "measured_source",
        ],
    )
    write_csv(
        csv_latest,
        csv_rows,
        [
            "source",
            "sector",
            "constraint",
            "estimated_hourly_value_usd",
            "estimated_annual_value_usd",
            "modeled_hourly_value_usd",
            "modeled_annual_value_usd",
            "evidence_status",
            "model_boundary",
            "optimization_gain_pct",
            "premium_tier",
            "enabled_source",
            "measured_source",
        ],
    )

    print("BUILD_MULTI_ASSET_FROZEN_DELTA_PACK")
    print(f"json_latest={json_latest}")
    print(f"md_latest={md_latest}")
    print(f"csv_latest={csv_latest}")
    print(f"lanes={len(top_lanes)}")
    print("accepted_annual_savings_usd=UNKNOWN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
