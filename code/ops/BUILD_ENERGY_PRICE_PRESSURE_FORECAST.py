from __future__ import annotations

import csv
import hashlib
import json
import math
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
LIVE = DATA / "live_measured"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

GRID_HOURLY_CSV = DATA / "930-data-export (2).csv"
REGION_CHANGE_CSV = DATA / "930-data-export (1).csv"
NUCLEAR_OUTAGE_CSV = DATA / "Daily_U.S._nuclear_capacity_outage.csv"
FUEL_PRICE_CSV = DATA / "MER_T09_04.csv"
FRED_DGS10_CSV = DATA / "fred_DGS10.csv"
FRED_UNRATE_CSV = DATA / "fred_UNRATE.csv"
FRED_CPI_CSV = DATA / "fred_CPIAUCSL.csv"
LIVE_EIA_JSON = LIVE / "eia" / "eia_latest.json"
LIVE_FRED_JSON = LIVE / "fred" / "fred_latest.json"
LIVE_NOAA_JSON = LIVE / "noaa_ncei" / "noaa_ncei_latest.json"
GEOMETRY_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"

OUT_JSON = OUT_OPS / "energy_price_pressure_forecast_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "energy_price_pressure_forecast.json"
OUT_MD = DOCS / "ENERGY_PRICE_PRESSURE_FORECAST_2026-06-25.md"

EVIDENCE_BOUNDARY = (
    "This is a live measured energy price-pressure proxy, not an actual wholesale power price "
    "forecast and not a real-dollar savings claim. It uses EIA grid demand/generation, EIA "
    "day-ahead demand snapshot rows, nuclear outage stress, FRED macro series, and current "
    "geometry replay evidence. To unlock real price and dollar claims, connect ISO/RTO LMP "
    "or other auditable electricity price settlement data and run walk-forward validation."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_payload(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_mean(values: list[float], default: float = 0.0) -> float:
    good = [float(v) for v in values if math.isfinite(float(v))]
    return mean(good) if good else default


def safe_std(values: list[float], default: float = 1.0) -> float:
    good = [float(v) for v in values if math.isfinite(float(v))]
    if len(good) < 2:
        return default
    return max(pstdev(good), 1e-9)


def parse_grid_timestamp(value: str) -> datetime | None:
    text = value.strip()
    text = text.replace("a.m.", "AM").replace("p.m.", "PM")
    text = text.replace("a.m", "AM").replace("p.m", "PM")
    text = text.replace(" EST", "").replace(" EDT", "")
    for fmt in ("%m/%d/%Y %I %p", "%m/%d/%Y %I:%M %p"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def read_csv_dicts(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
        reader = csv.DictReader(handle)
        return [dict(row) for row in reader]


def load_hourly_grid_rows(path: Path = GRID_HOURLY_CSV) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv_dicts(path):
        stamp = parse_grid_timestamp(row.get("Timestamp (Hour Ending)", ""))
        demand = parse_float(row.get("Demand (MWh)"))
        forecast = parse_float(row.get("Demand Forecast (MWh)"))
        generation = parse_float(row.get("Net Generation (MWh)"))
        interchange = parse_float(row.get("Total Interchange (MWh)"))
        if stamp is None or demand is None:
            continue
        rows.append(
            {
                "region": row.get("Region Code", ""),
                "timestamp": stamp,
                "hour": stamp.hour,
                "demand_mwh": demand,
                "demand_forecast_mwh": forecast,
                "net_generation_mwh": generation,
                "total_interchange_mwh": interchange,
                "forecast_error_mwh": demand - forecast if forecast is not None else None,
                "generation_gap_mwh": demand - generation if generation is not None else None,
            }
        )
    return sorted(rows, key=lambda item: item["timestamp"])

def public_grid_row(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    if isinstance(out.get("timestamp"), datetime):
        out["timestamp"] = out["timestamp"].isoformat()
    return out


def load_region_shock(path: Path = REGION_CHANGE_CSV) -> dict[str, Any]:
    values: list[float] = []
    rows: list[dict[str, Any]] = []
    for row in read_csv_dicts(path):
        pct = parse_float(row.get("Percent Change from Prior Hour"))
        demand = parse_float(row.get("Selected Hour Demand (MWh)"))
        prior = parse_float(row.get("Prior Hour Demand (MWh)"))
        if pct is None:
            continue
        values.append(pct)
        rows.append(
            {
                "region": row.get("Region Code", ""),
                "region_type": row.get("Region Type", ""),
                "selected_demand_mwh": demand,
                "prior_demand_mwh": prior,
                "percent_change": pct,
            }
        )
    abs_values = [abs(value) for value in values]
    top = sorted(rows, key=lambda item: abs(float(item["percent_change"])), reverse=True)[:8]
    return {
        "row_count": len(rows),
        "mean_abs_percent_change": round(safe_mean(abs_values), 6),
        "max_abs_percent_change": round(max(abs_values) if abs_values else 0.0, 6),
        "shock_index": round(clamp(safe_mean(abs_values) / 20.0, 0.0, 1.0), 6),
        "top_regions": top,
    }


def load_nuclear_outage(path: Path = NUCLEAR_OUTAGE_CSV) -> dict[str, Any]:
    if not path.exists():
        return {"row_count": 0, "latest_2026_gw": 0.0, "stress_index": 0.0}
    lines = path.read_text(encoding="utf-8-sig", errors="ignore").splitlines()
    header_index = next((idx for idx, line in enumerate(lines) if line.startswith("Day,")), -1)
    if header_index < 0:
        return {"row_count": 0, "latest_2026_gw": 0.0, "stress_index": 0.0}
    reader = csv.DictReader(lines[header_index:])
    parsed: list[dict[str, Any]] = []
    for row in reader:
        day_text = row.get("Day", "")
        try:
            day = datetime.strptime(day_text, "%m/%d/%Y")
        except ValueError:
            continue
        value_2026 = parse_float(row.get("2026 gigawatts (GW)"))
        low = parse_float(row.get("2021-2025 Range Low  gigawatts (GW)"))
        high = parse_float(row.get("2021-2025 Range High  gigawatts (GW)"))
        if value_2026 is None:
            continue
        parsed.append({"day": day, "gw_2026": value_2026, "low": low, "high": high})
    if not parsed:
        return {"row_count": 0, "latest_2026_gw": 0.0, "stress_index": 0.0}
    latest = sorted(parsed, key=lambda item: item["day"])[-1]
    high = float(latest.get("high") or max(item["gw_2026"] for item in parsed) or 1.0)
    stress = clamp(float(latest["gw_2026"]) / max(high, 1e-9), 0.0, 1.5)
    return {
        "row_count": len(parsed),
        "latest_day": latest["day"].date().isoformat(),
        "latest_2026_gw": round(float(latest["gw_2026"]), 6),
        "latest_range_high_gw": round(high, 6),
        "mean_2026_gw": round(safe_mean([float(item["gw_2026"]) for item in parsed]), 6),
        "stress_index": round(clamp(stress, 0.0, 1.0), 6),
    }


def load_simple_series(path: Path) -> dict[str, Any]:
    rows = read_csv_dicts(path)
    values: list[tuple[str, float]] = []
    for row in rows:
        value = parse_float(row.get("value") or row.get("Value"))
        date = row.get("date") or row.get("YYYYMM") or ""
        if value is not None and date:
            values.append((str(date), value))
    if not values:
        return {"row_count": 0, "latest_value": None, "change_30": None, "change_365": None}
    latest = values[-1][1]
    change_30 = latest - values[-31][1] if len(values) > 31 else None
    change_365 = latest - values[-366][1] if len(values) > 366 else None
    return {
        "row_count": len(values),
        "latest_date": values[-1][0],
        "latest_value": round(latest, 6),
        "change_30": round(change_30, 6) if change_30 is not None else None,
        "change_365": round(change_365, 6) if change_365 is not None else None,
    }


def load_fuel_price(path: Path = FUEL_PRICE_CSV) -> dict[str, Any]:
    rows = read_csv_dicts(path)
    values: list[tuple[str, float, str]] = []
    for row in rows:
        value = parse_float(row.get("Value"))
        period = row.get("YYYYMM", "")
        description = row.get("Description", "")
        if value is None or not period:
            continue
        values.append((period, value, description))
    values.sort(key=lambda item: item[0])
    if not values:
        return {"row_count": 0, "latest_value": None, "stress_index": 0.0}
    latest = values[-1]
    recent = [value for _, value, _ in values[-24:]]
    baseline = safe_mean(recent, latest[1])
    stress = clamp((latest[1] - baseline) / max(baseline, 1e-9) * 4.0 + 0.5, 0.0, 1.0)
    return {
        "row_count": len(values),
        "latest_period": latest[0],
        "latest_value": round(latest[1], 6),
        "latest_description": latest[2],
        "recent_mean": round(baseline, 6),
        "stress_index": round(stress, 6),
        "boundary": "Retail fuel macro proxy only, not wholesale electricity price.",
    }


def load_live_snapshot_profile(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    rows = payload.get("rows", [])
    numeric: list[float] = []
    if isinstance(rows, list):
        for row in rows:
            if isinstance(row, dict):
                for value in row.values():
                    parsed = parse_float(value)
                    if parsed is not None:
                        numeric.append(parsed)
    sha = str(payload.get("sha256") or sha256_payload(payload) if payload else "")
    return {
        "path": str(path.relative_to(ROOT)) if path.exists() else str(path),
        "source": payload.get("source", path.parent.name.upper()) if payload else path.parent.name.upper(),
        "row_count": int(payload.get("row_count", len(rows)) or 0) if payload else 0,
        "numeric_count": len(numeric),
        "mean_numeric_value": round(safe_mean(numeric), 6) if numeric else None,
        "coefficient_of_variation": round(safe_std(numeric, 0.0) / max(abs(safe_mean(numeric)), 1.0), 6) if numeric else 0.0,
        "sha256": sha,
    }


def mae(errors: list[float]) -> float:
    return safe_mean([abs(error) for error in errors])


def rmse(errors: list[float]) -> float:
    if not errors:
        return 0.0
    return math.sqrt(safe_mean([error * error for error in errors]))


def walk_forward_backtest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if len(rows) < 8:
        return {"row_count": len(rows), "usable": False, "reason": "Too few hourly rows."}

    persistence_errors: list[float] = []
    eia_forecast_errors: list[float] = []
    phase_locked_errors: list[float] = []
    residuals_by_hour: dict[int, list[float]] = defaultdict(list)
    all_residuals: list[float] = []
    recent_demand_deltas: list[float] = []

    previous = rows[0]
    first_residual = previous.get("forecast_error_mwh")
    if first_residual is not None:
        residuals_by_hour[int(previous["hour"])].append(float(first_residual))
        all_residuals.append(float(first_residual))

    for row in rows[1:]:
        actual = float(row["demand_mwh"])
        forecast = row.get("demand_forecast_mwh")
        if forecast is None:
            forecast = float(previous["demand_mwh"])

        previous_actual = float(previous["demand_mwh"])
        demand_delta = previous_actual - float(rows[max(0, rows.index(previous) - 1)]["demand_mwh"]) if rows.index(previous) > 0 else 0.0
        recent_demand_deltas.append(demand_delta)
        if len(recent_demand_deltas) > 6:
            recent_demand_deltas.pop(0)

        hour = int(row["hour"])
        same_hour_residuals = residuals_by_hour[hour][-5:]
        residual_anchor = safe_mean(same_hour_residuals, safe_mean(all_residuals[-24:], 0.0))
        velocity_anchor = safe_mean(recent_demand_deltas[-3:], 0.0)
        phase_locked_pred = float(forecast) + 0.75 * residual_anchor + 0.15 * velocity_anchor

        persistence_errors.append(actual - previous_actual)
        eia_forecast_errors.append(actual - float(forecast))
        phase_locked_errors.append(actual - phase_locked_pred)

        residual = actual - float(forecast)
        residuals_by_hour[hour].append(residual)
        all_residuals.append(residual)
        previous = row

    persistence_mae = mae(persistence_errors)
    eia_mae = mae(eia_forecast_errors)
    phase_mae = mae(phase_locked_errors)
    avg_demand = safe_mean([float(row["demand_mwh"]) for row in rows], 1.0)
    best_named_baseline = min(
        [("persistence", persistence_mae), ("eia_day_ahead_forecast", eia_mae)],
        key=lambda item: item[1],
    )
    improvement_vs_best = (
        (best_named_baseline[1] - phase_mae) / best_named_baseline[1] * 100.0
        if best_named_baseline[1] > 0
        else 0.0
    )
    return {
        "row_count": len(rows),
        "usable": True,
        "models": {
            "persistence": {
                "mae_mwh": round(persistence_mae, 6),
                "rmse_mwh": round(rmse(persistence_errors), 6),
                "mae_percent_of_avg_demand": round(persistence_mae / avg_demand * 100.0, 6),
            },
            "eia_day_ahead_forecast": {
                "mae_mwh": round(eia_mae, 6),
                "rmse_mwh": round(rmse(eia_forecast_errors), 6),
                "mae_percent_of_avg_demand": round(eia_mae / avg_demand * 100.0, 6),
            },
            "phase_locked_residual_corrector": {
                "mae_mwh": round(phase_mae, 6),
                "rmse_mwh": round(rmse(phase_locked_errors), 6),
                "mae_percent_of_avg_demand": round(phase_mae / avg_demand * 100.0, 6),
            },
        },
        "best_named_baseline": best_named_baseline[0],
        "phase_locked_improvement_vs_best_named_baseline_pct": round(improvement_vs_best, 6),
        "phase_locked_beats_best_named_baseline": improvement_vs_best > 0.0,
        "claim_language": "Walk-forward demand/pressure proxy only; not actual LMP, not realized revenue.",
    }


def geometry_context() -> dict[str, Any]:
    replay = read_json(GEOMETRY_REPLAY_JSON)
    cards = replay.get("replay_cards", []) if isinstance(replay.get("replay_cards"), list) else []
    selected = []
    for card in cards:
        if not isinstance(card, dict):
            continue
        if card.get("lane") in {"wave_resonance_timing", "thermal_ventilation", "time_series_model_routing"}:
            selected.append(
                {
                    "lane": card.get("lane", ""),
                    "candidate_family_id": card.get("candidate_family_id", ""),
                    "best_baseline_family_id": card.get("best_baseline_family_id", ""),
                    "candidate_beats_named_baseline": bool(card.get("candidate_beats_named_baseline")),
                    "candidate_score_delta_vs_named_baseline": card.get("candidate_score_delta_vs_named_baseline"),
                    "ready_for_live_geometry_claim": bool(card.get("ready_for_live_geometry_claim")),
                    "ready_for_real_dollar_claim": bool(card.get("ready_for_real_dollar_claim")),
                }
            )
    return {
        "summary": replay.get("summary", {}),
        "selected_replay_cards": selected,
        "source_file": str(GEOMETRY_REPLAY_JSON.relative_to(ROOT)),
    }


def pressure_band(score: float) -> str:
    if score >= 80:
        return "critical"
    if score >= 65:
        return "high"
    if score >= 50:
        return "elevated"
    return "normal"


def build_forecast_rows(
    rows: list[dict[str, Any]],
    backtest: dict[str, Any],
    region_shock: dict[str, Any],
    nuclear: dict[str, Any],
    fuel: dict[str, Any],
) -> list[dict[str, Any]]:
    if not rows:
        return []
    demand_values = [float(row["demand_mwh"]) for row in rows]
    demand_mean = safe_mean(demand_values, 1.0)
    demand_std = safe_std(demand_values, 1.0)
    recent_24 = demand_values[-24:] if len(demand_values) >= 24 else demand_values
    recent_mean = safe_mean(recent_24, demand_mean)
    recent_deltas = [b - a for a, b in zip(demand_values, demand_values[1:])]
    velocity = safe_mean(recent_deltas[-6:], 0.0)
    by_hour: dict[int, list[float]] = defaultdict(list)
    gap_values: list[float] = []
    for row in rows:
        by_hour[int(row["hour"])].append(float(row["demand_mwh"]))
        gap = row.get("generation_gap_mwh")
        if gap is not None:
            gap_values.append(float(gap))
    last = rows[-1]
    last_time = last["timestamp"]
    latest_gap = float(last.get("generation_gap_mwh") or safe_mean(gap_values, 0.0))
    normalized_gap = abs(latest_gap) / max(float(last["demand_mwh"]), 1.0)
    model_error = 0.0
    try:
        model_error = float(backtest["models"]["phase_locked_residual_corrector"]["mae_percent_of_avg_demand"]) / 100.0
    except Exception:
        model_error = 0.0
    regional = float(region_shock.get("shock_index", 0.0) or 0.0)
    outage = float(nuclear.get("stress_index", 0.0) or 0.0)
    fuel_stress = float(fuel.get("stress_index", 0.0) or 0.0)

    forecasts: list[dict[str, Any]] = []
    for hour_ahead in range(1, 25):
        target = last_time + timedelta(hours=hour_ahead)
        same_hour = by_hour.get(target.hour, [])
        seasonal = safe_mean(same_hour, recent_mean)
        trend = velocity * min(hour_ahead, 6) * 0.18
        predicted = 0.62 * seasonal + 0.38 * recent_mean + trend
        demand_z = (predicted - demand_mean) / demand_std
        score = 50.0
        score += 8.5 * demand_z
        score += 100.0 * normalized_gap
        score += 11.0 * regional
        score += 8.0 * outage
        score += 5.0 * fuel_stress
        score += 60.0 * model_error
        score = clamp(score, 0.0, 100.0)
        forecasts.append(
            {
                "horizon_hour": hour_ahead,
                "timestamp_estimated": target.isoformat(),
                "predicted_demand_mwh": round(predicted, 6),
                "seasonal_hour_mean_mwh": round(seasonal, 6),
                "recent_24h_mean_mwh": round(recent_mean, 6),
                "latest_generation_gap_mwh": round(latest_gap, 6),
                "price_pressure_score_0_100": round(score, 6),
                "price_pressure_band": pressure_band(score),
            }
        )
    return forecasts


def build_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    backtest = payload["backtest"]
    lines = [
        "# Energy Price-Pressure Forecast Evidence",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Boundary",
        "",
        EVIDENCE_BOUNDARY,
        "",
        "## Summary",
        "",
        f"- Hourly grid rows: {summary['hourly_grid_rows']}",
        f"- Forecast rows generated: {summary['forecast_rows']}",
        f"- Price-pressure max band: {summary['max_pressure_band']}",
        f"- Phase-locked model beats best named baseline: {summary['phase_locked_beats_best_named_baseline']}",
        f"- Improvement vs best named baseline: {summary['phase_locked_improvement_vs_best_named_baseline_pct']}%",
        f"- Actual electricity price series connected: {summary['actual_electricity_price_series_connected']}",
        f"- Ready for real dollar claim: {summary['ready_for_real_dollar_claim']}",
        "",
        "## Walk-Forward Demand Proxy Backtest",
        "",
        "| Model | MAE MWh | RMSE MWh | MAE % avg demand |",
        "|---|---:|---:|---:|",
    ]
    for name, row in backtest.get("models", {}).items():
        lines.append(
            f"| {name} | {row['mae_mwh']} | {row['rmse_mwh']} | {row['mae_percent_of_avg_demand']} |"
        )
    lines.extend(["", "## Next Forecast Windows", "", "| Hour | Pressure | Band | Predicted Demand MWh |", "|---:|---:|---|---:|"])
    for row in payload.get("forecast_rows", [])[:8]:
        lines.append(
            f"| {row['horizon_hour']} | {row['price_pressure_score_0_100']} | "
            f"{row['price_pressure_band']} | {row['predicted_demand_mwh']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Gate",
            "",
            "- Use now: measured live-breadth energy pressure proxy, dashboard signal, grant evidence artifact.",
            "- Do not claim yet: realized savings, field validation, actual LMP price forecast, live trading alpha, or guaranteed award outcome.",
            "- Unlock next: connect ISO/RTO LMP settlement data and run the same walk-forward harness against actual prices.",
        ]
    )
    return "\n".join(lines)


def build_payload() -> dict[str, Any]:
    hourly_rows = load_hourly_grid_rows()
    region_shock = load_region_shock()
    nuclear = load_nuclear_outage()
    fuel = load_fuel_price()
    fred = {
        "dgs10": load_simple_series(FRED_DGS10_CSV),
        "unrate": load_simple_series(FRED_UNRATE_CSV),
        "cpi": load_simple_series(FRED_CPI_CSV),
    }
    live_snapshots = {
        "eia": load_live_snapshot_profile(LIVE_EIA_JSON),
        "fred": load_live_snapshot_profile(LIVE_FRED_JSON),
        "noaa_ncei": load_live_snapshot_profile(LIVE_NOAA_JSON),
    }
    backtest = walk_forward_backtest(hourly_rows)
    forecast_rows = build_forecast_rows(hourly_rows, backtest, region_shock, nuclear, fuel)
    bands = [row["price_pressure_band"] for row in forecast_rows]
    max_score = max([float(row["price_pressure_score_0_100"]) for row in forecast_rows], default=0.0)
    geometry = geometry_context()

    payload: dict[str, Any] = {
        "schema": "energy_price_pressure_forecast.v1",
        "generated_utc": now_utc(),
        "purpose": "Reviewer-safe live energy pressure prediction evidence bridge.",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "hourly_grid_csv": str(GRID_HOURLY_CSV.relative_to(ROOT)),
            "region_change_csv": str(REGION_CHANGE_CSV.relative_to(ROOT)),
            "nuclear_outage_csv": str(NUCLEAR_OUTAGE_CSV.relative_to(ROOT)),
            "fuel_price_csv": str(FUEL_PRICE_CSV.relative_to(ROOT)),
            "fred_dgs10_csv": str(FRED_DGS10_CSV.relative_to(ROOT)),
            "fred_unrate_csv": str(FRED_UNRATE_CSV.relative_to(ROOT)),
            "fred_cpi_csv": str(FRED_CPI_CSV.relative_to(ROOT)),
            "live_eia_json": str(LIVE_EIA_JSON.relative_to(ROOT)),
            "live_fred_json": str(LIVE_FRED_JSON.relative_to(ROOT)),
            "live_noaa_json": str(LIVE_NOAA_JSON.relative_to(ROOT)),
        },
        "summary": {
            "hourly_grid_rows": len(hourly_rows),
            "forecast_rows": len(forecast_rows),
            "max_pressure_score_0_100": round(max_score, 6),
            "max_pressure_band": pressure_band(max_score) if forecast_rows else "missing",
            "phase_locked_beats_best_named_baseline": bool(backtest.get("phase_locked_beats_best_named_baseline")),
            "phase_locked_improvement_vs_best_named_baseline_pct": backtest.get(
                "phase_locked_improvement_vs_best_named_baseline_pct", 0.0
            ),
            "actual_electricity_price_series_connected": False,
            "ready_for_price_pressure_claim": bool(hourly_rows and forecast_rows),
            "ready_for_real_dollar_claim": False,
            "ready_for_field_validation_claim": False,
            "kraken_live_execution_allowed": False,
        },
        "latest_grid_state": public_grid_row(hourly_rows[-1]) if hourly_rows else {},
        "backtest": backtest,
        "region_shock": region_shock,
        "nuclear_outage": nuclear,
        "fuel_macro_proxy": fuel,
        "fred_macro": fred,
        "live_snapshot_profiles": live_snapshots,
        "geometry_context": geometry,
        "forecast_rows": forecast_rows,
        "claim_gate": {
            "can_say": [
                "The system runs a measured energy price-pressure proxy over EIA grid rows.",
                "The system performs walk-forward demand/pressure error checks against named baselines.",
                "The output is reproducible, timestamped, and hashable.",
            ],
            "cannot_say_yet": [
                "Actual wholesale electricity prices were predicted.",
                "Real customer savings were achieved.",
                "The system is field validated.",
                "The system is cleared for live trading or automated energy market execution.",
            ],
            "next_feed_to_unlock_dollar_claims": "ISO/RTO LMP or settlement price history with auditable timestamps.",
        },
    }
    payload["sha256"] = sha256_payload({key: value for key, value in payload.items() if key != "sha256"})
    return payload


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, build_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(json.dumps(payload["summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
