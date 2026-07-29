from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
LIVE_MEASURED_ROOT = ROOT / "data" / "live_measured"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
FRONTIER_JSON = OUT_OPS / "geometry_proof_frontier_board_latest.json"
BRIDGE_JSON = OUT_OPS / "geometry_championship_bridge_latest.json"
LIVE_SOURCE_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
DOLLAR_GATE_JSON = OUT_OPS / "dollar_claim_gate_latest.json"
PROTOCOL_FIELD_JSON = OUT_OPS / "full_geometry_protocol_field_latest.json"

OUT_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_live_wiring_matrix.json"
OUT_MD = DOCS / "GEOMETRY_LIVE_WIRING_MATRIX_2026-06-22.md"


LANE_SOURCE_PLAN: dict[str, dict[str, Any]] = {
    "mission_network_routing": {
        "sources": ["GRANTS_GOV", "SAM_GOV", "NOAA_NCEI", "USGS_WATER", "WEBHOOK"],
        "critical_sources": ["GRANTS_GOV"],
        "first_live_replay": "degraded-network routing windows from grant/opportunity, weather, water, and event-ingress signals",
        "highest_impact_use": "mission routing, degraded infrastructure, grant/opportunity triage",
    },
    "field_guided_control": {
        "sources": [
            "NWS_PUBLIC",
            "OPEN_METEO_PUBLIC",
            "NOAA_NCEI",
            "NASA",
            "USGS_WATER",
            "KRAKEN_PUBLIC",
        ],
        "critical_sources": ["NWS_PUBLIC", "OPEN_METEO_PUBLIC"],
        "first_live_replay": "field drift and corridor-control replay using weather, hydrology, and public time-series stress controls",
        "highest_impact_use": "defense, maritime, environmental, and sensor-control routing",
    },
    "packing_topology": {
        "sources": ["CENSUS", "NREL", "GRANTS_GOV", "BEA"],
        "critical_sources": ["CENSUS", "BEA"],
        "first_live_replay": "regional demand and layout-density replay for sensor, hardware, and infrastructure placement",
        "highest_impact_use": "hardware layout, sensor packing, public infrastructure siting",
    },
    "multi_agent_coordination": {
        "sources": [
            "NWS_PUBLIC",
            "OPEN_METEO_PUBLIC",
            "NOAA_NCEI",
            "GRANTS_GOV",
            "KRAKEN_PUBLIC",
            "WEBHOOK",
        ],
        "critical_sources": ["NWS_PUBLIC", "OPEN_METEO_PUBLIC"],
        "first_live_replay": "multi-agent coordination replay under weather/event disruption and public time-series stress",
        "highest_impact_use": "swarm coordination, task allocation, review-burden reduction",
    },
    "branching_transport": {
        "sources": [
            "EIA",
            "NWS_PUBLIC",
            "OPEN_METEO_PUBLIC",
            "NREL",
            "NOAA_NCEI",
            "USGS_WATER",
            "WEBHOOK",
        ],
        "critical_sources": ["EIA", "NWS_PUBLIC", "OPEN_METEO_PUBLIC"],
        "first_live_replay": "critical-flow and failure-propagation replay using EIA load, weather, hydrology, and event signals",
        "highest_impact_use": "grid resilience, datacenter flow, outage detection, logistics, cold-chain routing",
    },
    "thermal_ventilation": {
        "sources": [
            "EIA",
            "NWS_PUBLIC",
            "OPEN_METEO_PUBLIC",
            "NOAA_NCEI",
            "NREL",
        ],
        "critical_sources": ["EIA", "NWS_PUBLIC", "OPEN_METEO_PUBLIC"],
        "first_live_replay": "load-plus-ambient thermal replay comparing plume/cellular ventilation against straight-duct baselines",
        "highest_impact_use": "datacenter cooling, HVAC energy recovery, thermal resilience",
    },
    "resource_aware_scheduling": {
        "sources": ["GRANTS_GOV", "BLS", "FRED", "BEA", "WEBHOOK"],
        "critical_sources": ["GRANTS_GOV"],
        "first_live_replay": "bounded wake/scheduling replay using macro pressure and internal event cadence",
        "highest_impact_use": "compute scheduling, automation throttling, low-power operations",
    },
    "time_series_model_routing": {
        "sources": [
            "EIA_GRID_VALIDATION",
            "EIA",
            "FRED",
            "BEA",
            "BLS",
            "CENSUS",
            "NOAA_NCEI",
            "KRAKEN_PUBLIC",
            "FINNHUB",
            "TWELVE_DATA",
            "ALPHAVANTAGE",
            "MASSIVE",
        ],
        "critical_sources": ["EIA_GRID_VALIDATION", "FRED", "BLS"],
        "first_live_replay": "walk-forward forecasting and regime-drift replay across macro, weather, and market proxies",
        "highest_impact_use": "live-breadth forecasting, regime detection, proof-card calibration",
    },
    "stability_diagnostic": {
        "sources": ["FRED", "BEA", "BLS", "NOAA_NCEI", "EIA", "KRAKEN_PUBLIC", "WEBHOOK"],
        "critical_sources": ["FRED", "NOAA_NCEI", "WEBHOOK"],
        "first_live_replay": "Frobenius, perturbation, and drift diagnostics over measured source snapshots",
        "highest_impact_use": "reviewer trust, drift detection, claim-boundary enforcement",
    },
    "optimal_curve_transport": {
        "sources": ["KRAKEN_PUBLIC", "COINGECKO_PUBLIC", "FRED", "GRANTS_GOV", "EIA"],
        "critical_sources": ["KRAKEN_PUBLIC", "FRED"],
        "first_live_replay": "frozen path-window replay using public time series as constraints, not as trading signals",
        "highest_impact_use": "path planning, cabling/layout, thermal route optimization, visual proof card",
    },
    "wave_resonance_timing": {
        "sources": [
            "EIA_GRID_VALIDATION",
            "EIA",
            "FRED",
            "KRAKEN_PUBLIC",
            "NOAA_NCEI",
            "NASA",
        ],
        "critical_sources": ["EIA_GRID_VALIDATION", "FRED", "NOAA_NCEI"],
        "first_live_replay": "oscillatory-window replay comparing Kuramoto, PLL, Kalman, FFT, and ARIMA under identical frozen windows",
        "highest_impact_use": "harmonic AI thesis, PLL/grid timing, oscillatory anomaly detection",
    },
    "market_signal_geometry": {
        "sources": [
            "KRAKEN_PUBLIC",
            "KRAKEN",
            "FINNHUB",
            "TWELVE_DATA",
            "ALPHAVANTAGE",
            "MASSIVE",
            "COINGECKO_PUBLIC",
            "BINANCE_PUBLIC",
        ],
        "critical_sources": ["KRAKEN_PUBLIC", "KRAKEN"],
        "first_live_replay": "paper-only walk-forward replay with fees, slippage, drawdown, and abstention controls",
        "highest_impact_use": "paper lab calibration, not autonomous live trading",
    },
}

TIME_SERIES_BASELINES = [
    "naive_last",
    "drift",
    "moving_average",
    "exponential_smoothing",
    "linear_trend",
    "seasonal_naive_source_period",
    "damped_holt_ets",
    "autoregressive_ridge_source_lag",
]

TIME_SERIES_BASELINE_PARAMETERS = {
    "EIA_GRID_VALIDATION": {
        "cadence": "daily",
        "seasonal_period": 7,
        "autoregressive_lag": 14,
    },
    "FRED": {
        "cadence": "mixed",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
        "series_overrides": {
            "CPIAUCSL": {
                "cadence": "monthly",
                "seasonal_period": 12,
                "autoregressive_lag": 12,
            },
            "UNRATE": {
                "cadence": "monthly",
                "seasonal_period": 12,
                "autoregressive_lag": 12,
            },
        },
    },
    "BLS": {
        "cadence": "monthly",
        "seasonal_period": 12,
        "autoregressive_lag": 12,
    },
    "KRAKEN_PUBLIC": {
        "cadence": "hourly",
        "seasonal_period": 24,
        "autoregressive_lag": 24,
    },
    "TWELVE_DATA": {
        "cadence": "business_daily",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
    },
    "ALPHAVANTAGE": {
        "cadence": "business_daily",
        "seasonal_period": 5,
        "autoregressive_lag": 5,
    },
}

EIA_GRID_WAVE_BASELINES = [
    "eia_day_ahead_forecast",
    "seasonal_naive_7",
    "naive_last",
    "kalman_local_linear_trend",
    "autoregressive_ridge_p14",
    "fft_extrapolation_top5",
]

# A measured snapshot is not automatically a scientifically compatible input.
# These rules state which sources can carry direct outcomes, which can only set
# synthetic stress conditions, and which remain context until richer fields exist.
LANE_SOURCE_COMPATIBILITY: dict[str, dict[str, Any]] = {
    "mission_network_routing": {
        "direct": {},
        "conditioned": {
            "GRANTS_GOV": {
                "minimum_rows": 24,
                "reason": (
                    "Opportunity metadata can define source-derived nodes and similarity links, "
                    "but topology, capacity, demand, congestion, failure, and recovery remain synthetic."
                ),
            },
        },
        "missing_direct_observations": [
            "observed network nodes and edges",
            "edge costs and capacities",
            "origin-destination demand",
            "congestion and failure events",
            "recovery outcomes",
        ],
    },
    "field_guided_control": {
        "direct": {},
        "conditioned": {
            "NWS_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can parameterize weather disturbances in a synthetic control replay.",
            },
            "OPEN_METEO_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can parameterize weather disturbances in a synthetic control replay.",
            },
        },
        "missing_direct_observations": [
            "vehicle or actuator state telemetry",
            "issued control actions",
            "obstacle and collision outcomes",
            "energy or control-effort outcomes",
        ],
    },
    "packing_topology": {
        "direct": {},
        "conditioned": {
            "CENSUS": {
                "minimum_rows": 24,
                "reason": "Regional density can condition synthetic placement demand when a sufficiently granular panel exists.",
            },
            "BEA": {
                "minimum_rows": 24,
                "reason": "Regional economic density can condition synthetic placement demand when a sufficiently granular panel exists.",
            },
        },
        "missing_direct_observations": [
            "candidate site coordinates and exclusion zones",
            "physical item dimensions",
            "connectivity requirements",
            "placement failures and measured material cost",
        ],
    },
    "multi_agent_coordination": {
        "direct": {},
        "conditioned": {
            "NWS_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can stress a synthetic coordination mission but do not supply agent outcomes.",
            },
            "OPEN_METEO_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can stress a synthetic coordination mission but do not supply agent outcomes.",
            },
        },
        "missing_direct_observations": [
            "per-agent trajectories and commands",
            "communication events",
            "collision and formation outcomes",
            "mission completion labels",
        ],
    },
    "branching_transport": {
        "direct": {},
        "conditioned": {
            "EIA": {
                "minimum_rows": 48,
                "reason": "Observed load can parameterize synthetic network demand but does not expose the transport graph.",
            },
            "NWS_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can parameterize synthetic disruption scenarios.",
            },
            "OPEN_METEO_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can parameterize synthetic disruption scenarios.",
            },
        },
        "missing_direct_observations": [
            "observed network topology",
            "edge capacities and flow",
            "component failure events",
            "restoration outcomes",
        ],
    },
    "thermal_ventilation": {
        "direct": {},
        "conditioned": {
            "EIA": {
                "minimum_rows": 48,
                "reason": "Observed load can parameterize synthetic heat demand but is not thermal-response telemetry.",
            },
            "NWS_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can supply ambient boundary conditions for a synthetic thermal replay.",
            },
            "OPEN_METEO_PUBLIC": {
                "minimum_rows": 24,
                "reason": "Observed forecasts can supply ambient boundary conditions for a synthetic thermal replay.",
            },
        },
        "missing_direct_observations": [
            "facility geometry and airflow topology",
            "inlet and outlet temperature telemetry",
            "pressure drop and fan power",
            "recovery-time outcomes",
        ],
    },
    "resource_aware_scheduling": {
        "direct": {},
        "conditioned": {
            "GRANTS_GOV": {
                "minimum_rows": 24,
                "reason": "Opportunity dates can define fixed deadlines, while task duration, compute cost, and completion remain synthetic.",
            },
        },
        "missing_direct_observations": [
            "task arrival and duration logs",
            "resource consumption",
            "wake latency",
            "deadline and completion outcomes",
        ],
    },
    "time_series_model_routing": {
        "direct": {
            "EIA_GRID_VALIDATION": {
                "minimum_rows": 365,
                "baselines": TIME_SERIES_BASELINES,
                "baseline_parameters": TIME_SERIES_BASELINE_PARAMETERS[
                    "EIA_GRID_VALIDATION"
                ],
                "measurement_shape": {
                    "group_fields": ["respondent", "type", "timezone"],
                    "time_key_fields": ["period"],
                    "value_field": "value",
                    "filters": {"type": ["D"]},
                    "minimum_series_length": 365,
                    "minimum_series_count": 4,
                    "minimum_valid_row_fraction": 0.99,
                },
                "reason": (
                    "Frozen EIA-930 actual-demand series support identical expanding-window "
                    "forecast comparisons after grouping by balancing authority and timezone."
                ),
            },
            "FRED": {
                "minimum_rows": 24,
                "baselines": TIME_SERIES_BASELINES,
                "baseline_parameters": TIME_SERIES_BASELINE_PARAMETERS["FRED"],
                "measurement_shape": {
                    "group_fields": ["series_id"],
                    "time_key_fields": ["date"],
                    "value_field": "value",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Observed economic series support identical expanding-window forecast comparisons.",
            },
            "BLS": {
                "minimum_rows": 24,
                "baselines": TIME_SERIES_BASELINES,
                "baseline_parameters": TIME_SERIES_BASELINE_PARAMETERS["BLS"],
                "measurement_shape": {
                    "group_fields": ["series_id"],
                    "time_key_fields": ["year", "period"],
                    "value_field": "value",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Observed labor series support identical expanding-window forecast comparisons.",
            },
            "KRAKEN_PUBLIC": {
                "minimum_rows": 24,
                "baselines": TIME_SERIES_BASELINES,
                "baseline_parameters": TIME_SERIES_BASELINE_PARAMETERS[
                    "KRAKEN_PUBLIC"
                ],
                "measurement_shape": {
                    "group_fields": ["pair"],
                    "time_key_fields": ["time"],
                    "value_field": "close",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Frozen public OHLC history supports paper-only expanding-window comparisons.",
            },
            "TWELVE_DATA": {
                "minimum_rows": 24,
                "baselines": TIME_SERIES_BASELINES,
                "baseline_parameters": TIME_SERIES_BASELINE_PARAMETERS[
                    "TWELVE_DATA"
                ],
                "measurement_shape": {
                    "group_fields": ["symbol"],
                    "time_key_fields": ["datetime"],
                    "value_field": "close",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Frozen public OHLC history supports expanding-window comparisons.",
            },
            "ALPHAVANTAGE": {
                "minimum_rows": 24,
                "baselines": TIME_SERIES_BASELINES,
                "baseline_parameters": TIME_SERIES_BASELINE_PARAMETERS[
                    "ALPHAVANTAGE"
                ],
                "measurement_shape": {
                    "group_fields": ["pair"],
                    "time_key_fields": ["date"],
                    "value_field": "4. close",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Frozen public FX history supports expanding-window comparisons.",
            },
        },
        "conditioned": {},
        "missing_direct_observations": [],
    },
    "stability_diagnostic": {
        "direct": {},
        "conditioned": {},
        "missing_direct_observations": [
            "lane-specific frozen perturbation-matrix adapter",
            "source-specific null model",
            "paired drift or stability outcome labels",
        ],
    },
    "optimal_curve_transport": {
        "direct": {},
        "conditioned": {},
        "missing_direct_observations": [
            "observed path geometry",
            "terrain or obstacle constraints",
            "travel time and energy outcomes",
            "constraint-violation labels",
        ],
    },
    "wave_resonance_timing": {
        "direct": {
            "EIA_GRID_VALIDATION": {
                "minimum_rows": 365,
                "baselines": EIA_GRID_WAVE_BASELINES,
                "measurement_shape": {
                    "group_fields": ["respondent", "type", "timezone"],
                    "time_key_fields": ["period"],
                    "value_field": "value",
                    "minimum_series_length": 365,
                    "minimum_series_count": 8,
                    "minimum_valid_row_fraction": 0.99,
                    "paired_series": {
                        "group_fields": ["respondent", "timezone"],
                        "type_field": "type",
                        "required_types": ["D", "DF"],
                        "minimum_common_periods": 365,
                        "minimum_pair_count": 4,
                    },
                },
                "reason": (
                    "Frozen EIA-930 actual demand and official day-ahead forecasts support "
                    "the protocol-locked wave benchmark against official and algorithmic baselines."
                ),
            },
        },
        "conditioned": {},
        "missing_direct_observations": [],
    },
    "market_signal_geometry": {
        "direct": {
            "KRAKEN_PUBLIC": {
                "minimum_rows": 24,
                "measurement_shape": {
                    "group_fields": ["pair"],
                    "time_key_fields": ["time"],
                    "value_field": "close",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Frozen OHLC history supports paper-only walk-forward comparisons with fees and slippage.",
            },
            "TWELVE_DATA": {
                "minimum_rows": 24,
                "measurement_shape": {
                    "group_fields": ["symbol"],
                    "time_key_fields": ["datetime"],
                    "value_field": "close",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Frozen OHLC history supports paper-only walk-forward comparisons with fees and slippage.",
            },
            "ALPHAVANTAGE": {
                "minimum_rows": 24,
                "measurement_shape": {
                    "group_fields": ["pair"],
                    "time_key_fields": ["date"],
                    "value_field": "4. close",
                    "minimum_series_length": 24,
                    "minimum_series_count": 1,
                    "minimum_valid_row_fraction": 0.95,
                },
                "reason": "Frozen market history supports paper-only walk-forward comparisons with fees and slippage.",
            },
        },
        "conditioned": {},
        "missing_direct_observations": [],
    },
}


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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_payload_hash(payload: dict[str, Any], field: str) -> bool:
    declared = str(payload.get(field, "")).strip()
    if not declared:
        return False
    unsigned = dict(payload)
    unsigned.pop(field, None)
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest() == declared


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def norm_source(value: Any) -> str:
    return str(value or "").strip().upper()


def registry_rows(registry: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    families = registry.get("families", []) if isinstance(registry.get("families"), list) else []
    return lanes, [row for row in families if isinstance(row, dict)]


def live_source_lookup(live: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = live.get("provider_rows", []) if isinstance(live.get("provider_rows"), list) else []
    return {norm_source(row.get("source")): row for row in rows if isinstance(row, dict) and row.get("source")}


def recent_measured_snapshot_row(source: str) -> dict[str, Any]:
    source_dir = LIVE_MEASURED_ROOT / norm_source(source).lower()
    if not source_dir.exists():
        return {}
    candidates = sorted(source_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for path in candidates:
        if path.name.endswith("_latest.json"):
            continue
        payload = read_json(path)
        rows = payload.get("rows", [])
        row_count = int(payload.get("row_count") or (len(rows) if isinstance(rows, list) else 0) or 0)
        if row_count <= 0:
            continue
        return {
            "source": norm_source(payload.get("source") or source),
            "sector": payload.get("sector", ""),
            "status": "MEASURED",
            "rows": row_count,
            "measured": True,
            "enabled": True,
            "http_status": payload.get("http_status", 200),
            "probe_note": f"recent_snapshot_fallback:{path.as_posix()}",
            "snapshot_json": str(path.relative_to(ROOT)).replace("\\", "/"),
            "snapshot_sha256": payload.get("sha256") or file_sha256(path),
            "recent_snapshot_fallback": True,
        }
    return {}


def with_recent_snapshot_fallbacks(lookup: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    out = dict(lookup)
    for source in set(out) | {norm_source(path.name) for path in LIVE_MEASURED_ROOT.glob("*") if path.is_dir()}:
        row = out.get(source, {})
        measured = bool(row.get("measured")) and str(row.get("status", "")).upper() == "MEASURED"
        if measured:
            continue
        fallback = recent_measured_snapshot_row(source)
        if fallback:
            fallback["latest_probe_status"] = row.get("status", "missing")
            fallback["latest_probe_note"] = row.get("probe_note", "")
            out[source] = fallback
    return out


def generated_champions(frontier: dict[str, Any], bridge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = frontier.get("generated_benchmark_frontier", [])
    if not isinstance(rows, list) or not rows:
        rows = bridge.get("generated_lane_benchmarks", [])
    out: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("lane"):
            out[str(row["lane"])] = row
    return out


def proof_champions(frontier: dict[str, Any], bridge: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = frontier.get("proof_value_frontier", [])
    if not isinstance(rows, list) or not rows:
        rows = bridge.get("lane_champion_rankings", [])
    out: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or not row.get("lane"):
            continue
        lane = str(row["lane"])
        if lane not in out:
            out[lane] = row
    return out


def allowed_estimated_sources(dollar_gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = dollar_gate.get("estimated_value_lanes", [])
    out: dict[str, dict[str, Any]] = {}
    for row in rows if isinstance(rows, list) else []:
        if isinstance(row, dict) and row.get("source"):
            out[norm_source(row["source"])] = row
    return out


def source_projection(source: str, lookup: dict[str, dict[str, Any]]) -> dict[str, Any]:
    row = lookup.get(norm_source(source), {})
    measured = bool(row.get("measured")) and str(row.get("status", "")).upper() == "MEASURED"
    enabled = bool(row.get("enabled"))
    return {
        "source": norm_source(source),
        "status": row.get("status", "MISSING_FROM_FRESH_MAXIMIZER"),
        "sector": row.get("sector", ""),
        "rows": int(row.get("rows", 0) or 0),
        "measured": measured,
        "enabled": enabled,
        "http_status": row.get("http_status"),
        "probe_note": row.get("probe_note", ""),
        "snapshot_json": row.get("snapshot_json", ""),
        "snapshot_sha256": row.get("snapshot_sha256", ""),
        "translated_annual_value_usd": float((row.get("translated_value") or {}).get("year", 0.0) or 0.0),
        "public_no_key_path": not bool(row.get("env_names")),
    }


@lru_cache(maxsize=128)
def snapshot_rows(relative_path: str) -> tuple[dict[str, Any], ...]:
    if not relative_path:
        return ()
    path = (ROOT / relative_path).resolve()
    root = ROOT.resolve()
    if path != root and root not in path.parents:
        return ()
    payload = read_json(path)
    rows = payload.get("rows", [])
    if not isinstance(rows, list):
        return ()
    return tuple(row for row in rows if isinstance(row, dict))


def finite_number(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return False
    return number == number and number not in {float("inf"), float("-inf")}


def field_present(row: dict[str, Any], field: str) -> bool:
    value = row.get(field)
    return value is not None and str(value).strip() != ""


def composite_key(row: dict[str, Any], fields: list[str]) -> tuple[str, ...]:
    return tuple(str(row.get(field, "")).strip() for field in fields)


def measurement_shape_profile(
    projection: dict[str, Any],
    rule: dict[str, Any],
    mode: str,
) -> dict[str, Any]:
    shape = rule.get("measurement_shape")
    required = mode == "direct_measured_replay"
    if not isinstance(shape, dict):
        return {
            "declared": False,
            "required": required,
            "pass": not required,
            "reason": (
                "Direct measured replay requires a declared source schema and "
                "minimum chronological series shape."
                if required
                else "No additional structural gate declared beyond measured row threshold."
            ),
        }

    rows = list(snapshot_rows(str(projection.get("snapshot_json", ""))))
    filters = shape.get("filters", {}) if isinstance(shape.get("filters"), dict) else {}
    filtered_rows = [
        row
        for row in rows
        if all(
            str(row.get(field, "")).strip() in {str(value) for value in allowed}
            for field, allowed in filters.items()
            if isinstance(allowed, list)
        )
    ]
    group_fields = [str(field) for field in shape.get("group_fields", [])]
    time_fields = [str(field) for field in shape.get("time_key_fields", [])]
    value_field = str(shape.get("value_field", ""))
    required_fields = group_fields + time_fields + ([value_field] if value_field else [])
    valid_rows = [
        row
        for row in filtered_rows
        if all(field_present(row, field) for field in required_fields)
        and finite_number(row.get(value_field))
    ]

    series_times: dict[tuple[str, ...], set[tuple[str, ...]]] = {}
    for row in valid_rows:
        group = composite_key(row, group_fields) if group_fields else ("source",)
        series_times.setdefault(group, set()).add(composite_key(row, time_fields))
    series_lengths = [len(values) for values in series_times.values()]
    minimum_series_length = int(shape.get("minimum_series_length", 1) or 1)
    minimum_series_count = int(shape.get("minimum_series_count", 1) or 1)
    qualifying_series_count = sum(
        1 for length in series_lengths if length >= minimum_series_length
    )
    minimum_valid_fraction = float(
        shape.get("minimum_valid_row_fraction", 1.0) or 1.0
    )
    valid_fraction = len(valid_rows) / max(len(filtered_rows), 1)

    paired = (
        shape.get("paired_series", {})
        if isinstance(shape.get("paired_series"), dict)
        else {}
    )
    paired_profile: dict[str, Any] = {
        "declared": bool(paired),
        "pass": True,
    }
    if paired:
        pair_group_fields = [str(field) for field in paired.get("group_fields", [])]
        type_field = str(paired.get("type_field", ""))
        required_types = [str(value) for value in paired.get("required_types", [])]
        minimum_common_periods = int(paired.get("minimum_common_periods", 1) or 1)
        minimum_pair_count = int(paired.get("minimum_pair_count", 1) or 1)
        pair_times: dict[
            tuple[str, ...], dict[str, set[tuple[str, ...]]]
        ] = {}
        for row in valid_rows:
            pair_key = (
                composite_key(row, pair_group_fields)
                if pair_group_fields
                else ("source",)
            )
            row_type = str(row.get(type_field, "")).strip()
            pair_times.setdefault(pair_key, {}).setdefault(row_type, set()).add(
                composite_key(row, time_fields)
            )
        common_counts: list[int] = []
        for type_map in pair_times.values():
            if not all(value in type_map for value in required_types):
                common_counts.append(0)
                continue
            common = set.intersection(
                *(type_map[value] for value in required_types)
            )
            common_counts.append(len(common))
        qualifying_pair_count = sum(
            1 for count in common_counts if count >= minimum_common_periods
        )
        paired_profile = {
            "declared": True,
            "required_types": required_types,
            "pair_count": len(pair_times),
            "qualifying_pair_count": qualifying_pair_count,
            "minimum_pair_count": minimum_pair_count,
            "minimum_common_periods": minimum_common_periods,
            "maximum_common_periods": max(common_counts, default=0),
            "pass": qualifying_pair_count >= minimum_pair_count,
        }

    shape_pass = bool(
        filtered_rows
        and valid_fraction >= minimum_valid_fraction
        and qualifying_series_count >= minimum_series_count
        and paired_profile["pass"]
    )
    return {
        "declared": True,
        "required": required,
        "pass": shape_pass,
        "snapshot_row_count": len(rows),
        "filtered_row_count": len(filtered_rows),
        "valid_row_count": len(valid_rows),
        "valid_row_fraction": round(valid_fraction, 6),
        "minimum_valid_row_fraction": minimum_valid_fraction,
        "group_fields": group_fields,
        "time_key_fields": time_fields,
        "value_field": value_field,
        "filters": filters,
        "series_count": len(series_times),
        "qualifying_series_count": qualifying_series_count,
        "minimum_series_count": minimum_series_count,
        "minimum_series_length": minimum_series_length,
        "longest_series_length": max(series_lengths, default=0),
        "distinct_time_count": len(
            {
                time_key
                for values in series_times.values()
                for time_key in values
            }
        ),
        "paired_series": paired_profile,
        "reason": (
            "Source has the declared chronological measurement shape."
            if shape_pass
            else "Source does not meet the declared chronological measurement shape."
        ),
    }


def source_compatibility_projection(
    projection: dict[str, Any],
    lane_spec: dict[str, Any],
    compatibility: dict[str, Any],
) -> dict[str, Any]:
    source = norm_source(projection.get("source"))
    direct = compatibility.get("direct", {})
    conditioned = compatibility.get("conditioned", {})
    if source in direct:
        mode = "direct_measured_replay"
        rule = direct[source]
    elif source in conditioned:
        mode = "source_conditioned_synthetic_stress"
        rule = conditioned[source]
    else:
        mode = "context_only"
        rule = {}

    minimum_rows = int(rule.get("minimum_rows", 0) or 0)
    row_threshold_met = int(projection.get("rows", 0) or 0) >= minimum_rows
    shape_profile = measurement_shape_profile(projection, rule, mode)
    measured_and_qualified = (
        bool(projection.get("measured"))
        and mode != "context_only"
        and row_threshold_met
        and bool(shape_profile.get("pass"))
    )
    baselines = (
        list(rule.get("baselines") or lane_spec.get("baselines", []))
        if mode != "context_only"
        else []
    )
    return {
        **projection,
        "compatibility_mode": mode,
        "compatibility_reason": rule.get(
            "reason",
            "No observed task outcome carried by this source for the lane's registered metrics.",
        ),
        "minimum_rows": minimum_rows,
        "row_threshold_met": row_threshold_met,
        "measurement_shape": shape_profile,
        "measured_and_qualified": measured_and_qualified,
        "source_specific_baselines": baselines,
        "source_specific_baseline_parameters": (
            dict(rule.get("baseline_parameters", {}))
            if mode != "context_only"
            and isinstance(rule.get("baseline_parameters"), dict)
            else {}
        ),
        "direct_performance_input_allowed": mode == "direct_measured_replay" and measured_and_qualified,
        "source_conditioning_only": (
            mode == "source_conditioned_synthetic_stress" and measured_and_qualified
        ),
    }


def fresh_vs_stale_conflicts(
    bridge: dict[str, Any],
    lookup: dict[str, dict[str, Any]],
    lane_sources: list[str],
) -> list[dict[str, Any]]:
    available = bridge.get("available_live_assets", [])
    stale_lookup = {
        norm_source(row.get("provider")): row
        for row in available
        if isinstance(row, dict) and row.get("provider")
    }
    conflicts = []
    for source in lane_sources:
        name = norm_source(source)
        fresh = lookup.get(name, {})
        stale = stale_lookup.get(name, {})
        if stale and bool(stale.get("measured")) and not bool(fresh.get("measured")):
            conflicts.append(
                {
                    "source": name,
                    "stale_status": stale.get("status", ""),
                    "stale_rows": int(stale.get("rows", 0) or 0),
                    "fresh_status": fresh.get("status", "MISSING_FROM_FRESH_MAXIMIZER"),
                    "fresh_rows": int(fresh.get("rows", 0) or 0),
                    "policy": "fresh live_source_measurement_maximizer status takes precedence",
                }
            )
    return conflicts


def lane_score(
    direct_sources: list[dict[str, Any]],
    conditioned_sources: list[dict[str, Any]],
    context_sources: list[dict[str, Any]],
    blocked_sources: list[dict[str, Any]],
    generated: dict[str, Any],
    proof: dict[str, Any],
    allowed_sources: list[dict[str, Any]],
) -> float:
    direct_count = len(direct_sources)
    conditioned_count = len(conditioned_sources)
    context_count = len(context_sources)
    hash_count = sum(
        1
        for row in direct_sources + conditioned_sources
        if row.get("snapshot_sha256")
    )
    blocked_count = len(blocked_sources)
    delta = float(generated.get("score_delta_vs_best_baseline", 0) or 0)
    proof_score = float(
        proof.get("proof_priority_score", proof.get("readiness_score", 0) or 0) or 0
    )
    allowed_count = len(allowed_sources)
    return round(
        direct_count * 16.0
        + conditioned_count * 7.0
        + context_count * 1.0
        + hash_count * 2.0
        + min(delta * 100.0, 25.0)
        + proof_score * 0.20
        + allowed_count * 2.0
        - blocked_count * 8.0,
        3,
    )


def lane_matrix_row(
    lane: str,
    lane_spec: dict[str, Any],
    families: list[dict[str, Any]],
    live_lookup: dict[str, dict[str, Any]],
    generated_by_lane: dict[str, dict[str, Any]],
    proof_by_lane: dict[str, dict[str, Any]],
    dollar_sources: dict[str, dict[str, Any]],
    bridge: dict[str, Any],
    protocol_lane: dict[str, Any],
) -> dict[str, Any]:
    plan = LANE_SOURCE_PLAN.get(lane, {"sources": [], "critical_sources": []})
    compatibility = LANE_SOURCE_COMPATIBILITY.get(
        lane,
        {"direct": {}, "conditioned": {}, "missing_direct_observations": []},
    )
    sources = [norm_source(item) for item in plan.get("sources", [])]
    critical = {norm_source(item) for item in plan.get("critical_sources", [])}
    projections = [
        source_compatibility_projection(
            source_projection(source, live_lookup),
            lane_spec,
            compatibility,
        )
        for source in sources
    ]
    measured = [row for row in projections if row["measured"]]
    blocked = [row for row in projections if not row["measured"]]
    direct_measured = [
        row
        for row in projections
        if row["compatibility_mode"] == "direct_measured_replay"
        and row["measured_and_qualified"]
    ]
    conditioned_measured = [
        row
        for row in projections
        if row["compatibility_mode"] == "source_conditioned_synthetic_stress"
        and row["measured_and_qualified"]
    ]
    context_measured = [
        row
        for row in projections
        if row["compatibility_mode"] == "context_only" and row["measured"]
    ]
    unqualified_compatible = [
        row
        for row in projections
        if row["compatibility_mode"] != "context_only"
        and row["measured"]
        and not row["measured_and_qualified"]
    ]
    public_paths = [row for row in projections if row["public_no_key_path"] and row["measured"]]
    lane_families = [row for row in families if str(row.get("lane", "")) == lane]
    generated = generated_by_lane.get(lane, {})
    proof = proof_by_lane.get(lane, {})
    allowed = [row for row in projections if row["source"] in dollar_sources and row["measured"]]
    critical_blockers = [row for row in blocked if row["source"] in critical]

    implementation_count = int(protocol_lane.get("implementation_present_count", 0) or 0)
    executed_count = int(protocol_lane.get("frozen_generated_executed_count", 0) or 0)
    source_replay_count = int(protocol_lane.get("source_conditioned_replay_count", 0) or 0)
    field_validated_count = int(protocol_lane.get("field_validated_count", 0) or 0)
    lane_ready_for_direct_replay = bool(direct_measured) and implementation_count > 0
    lane_ready_for_conditioned_simulation = (
        bool(conditioned_measured) and implementation_count > 0
    )
    lane_claim_blockers = [
        "no field validation or customer/government operational validation",
        "no paired uncertainty interval on the fresh live replay",
        "no multiple-comparison control across the full geometry family registry",
    ]
    if not direct_measured:
        lane_claim_blockers.insert(
            0,
            "no qualified task-compatible observed source is wired for direct measured replay",
        )
    if implementation_count == 0:
        lane_claim_blockers.insert(0, "no executable family implementation is registered for this lane")
    if conditioned_measured and not direct_measured:
        lane_claim_blockers.append(
            "measured sources can condition synthetic stress only; they do not carry direct lane outcomes"
        )
    if source_replay_count > 0 and not direct_measured:
        lane_claim_blockers.append(
            "existing source-conditioned replay receipt does not satisfy direct measured validation"
        )
    if source_replay_count == 0:
        lane_claim_blockers.insert(
            0, "no completed lane-specific source-conditioned replay receipt"
        )
    if critical_blockers:
        lane_claim_blockers.append("critical source blockers remain: " + ", ".join(row["source"] for row in critical_blockers))
    if lane == "market_signal_geometry":
        lane_claim_blockers.append("market lane is paper/replay only; no live trading or profit claim is authorized")

    return {
        "lane": lane,
        "family_count": len(lane_families),
        "implementation_present_count": implementation_count,
        "frozen_generated_executed_count": executed_count,
        "source_conditioned_replay_count": source_replay_count,
        "field_validated_count": field_validated_count,
        "baselines": lane_spec.get("baselines", []),
        "metrics": lane_spec.get("metrics", []),
        "highest_impact_use": plan.get("highest_impact_use", ""),
        "first_live_replay": plan.get("first_live_replay", ""),
        "source_plan": sources,
        "critical_sources": sorted(critical),
        "measured_sources": measured,
        "direct_measured_replay_sources": direct_measured,
        "source_conditioned_synthetic_stress_sources": conditioned_measured,
        "context_only_measured_sources": context_measured,
        "measured_but_below_compatibility_threshold": unqualified_compatible,
        "source_specific_baseline_matrix": projections,
        "missing_direct_observations": compatibility.get(
            "missing_direct_observations", []
        ),
        "blocked_sources": blocked,
        "public_no_key_measured_sources": public_paths,
        "fresh_vs_stale_conflicts": fresh_vs_stale_conflicts(bridge, live_lookup, sources),
        "generated_champion": {
            "family": generated.get("best_geometry", generated.get("best_geometry_family_id", "")),
            "baseline": generated.get("best_baseline", ""),
            "score_delta_vs_best_baseline": float(generated.get("score_delta_vs_best_baseline", 0) or 0),
            "evidence_status": generated.get("evidence_status", "not_yet_generated_for_lane"),
        },
        "proof_value_champion": {
            "family": proof.get("candidate_champion_id", proof.get("candidate_champion_label", "")),
            "label": proof.get("candidate_champion_label", ""),
            "proof_priority_score": float(proof.get("proof_priority_score", 0) or 0),
            "first_test": proof.get("first_test", ""),
            "promotion_metric": proof.get("promotion_metric", ""),
            "evidence_status": proof.get("evidence_status", "candidate_only_not_performance_claim"),
        },
        "estimated_value_signal_sources": [
            {
                "source": row["source"],
                "estimated_annual_value_usd": dollar_sources[row["source"]].get("estimated_annual_value_usd", 0.0),
                "claim_band": dollar_sources[row["source"]].get("claim_band", ""),
                "claimable": False,
                "role": "context_only_denominator_not_family_value",
            }
            for row in allowed
        ],
        "live_wiring_score": lane_score(
            direct_measured,
            conditioned_measured,
            context_measured,
            blocked,
            generated,
            proof,
            allowed,
        ),
        "lane_ready_for_direct_source_replay_build": lane_ready_for_direct_replay,
        "lane_ready_for_source_conditioned_simulation_build": (
            lane_ready_for_conditioned_simulation
        ),
        "lane_ready_for_live_replay_build": lane_ready_for_direct_replay,
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "kraken_live_execution_allowed": False,
        "claim_blockers": lane_claim_blockers,
        "safe_claim_language": (
            "Direct-source readiness requires a task-compatible observed outcome and an executable "
            "family implementation. Source-conditioned simulations remain synthetic. Neither is "
            "field validation, realized savings, award certainty, or a profit claim."
        ),
    }

def compact_source_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compacted = []
    for row in rows:
        compacted.append(
            {
                "source": row.get("source", ""),
                "status": row.get("status", ""),
                "rows": int(row.get("rows", 0) or 0),
                "sector": row.get("sector", ""),
                "snapshot_json": row.get("snapshot_json", ""),
                "snapshot_sha256": row.get("snapshot_sha256", ""),
                "translated_annual_value_usd": float(row.get("translated_annual_value_usd", 0.0) or 0.0),
                "compatibility_mode": row.get("compatibility_mode", "context_only"),
                "compatibility_reason": row.get("compatibility_reason", ""),
                "measured_and_qualified": bool(row.get("measured_and_qualified")),
                "direct_performance_input_allowed": bool(
                    row.get("direct_performance_input_allowed")
                ),
                "source_conditioning_only": bool(row.get("source_conditioning_only")),
                "measurement_shape": row.get("measurement_shape", {}),
                "source_specific_baselines": row.get("source_specific_baselines", []),
                "source_specific_baseline_parameters": row.get(
                    "source_specific_baseline_parameters", {}
                ),
            }
        )
    return compacted


def top_live_replay_source_map(
    bridge: dict[str, Any],
    matrix_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Map generated top geometry champions to fresh measured live-source paths.

    The bridge card says which geometry should be replayed next; the matrix row says
    whether the lane has current measured sources. Keeping them together prevents
    synthetic benchmark wins from being mistaken for live validation.
    """

    by_lane = {str(row.get("lane", "")): row for row in matrix_rows}
    cards = bridge.get("top_live_replay_wiring_cards", [])
    if not isinstance(cards, list):
        return []

    mapped: list[dict[str, Any]] = []
    for index, card in enumerate(cards, start=1):
        if not isinstance(card, dict):
            continue
        lane = str(card.get("lane", ""))
        matrix = by_lane.get(lane, {})
        measured = matrix.get("measured_sources", [])
        blocked = matrix.get("blocked_sources", [])
        critical = {norm_source(item) for item in matrix.get("critical_sources", [])}
        measured_rows = [row for row in measured if isinstance(row, dict)]
        blocked_rows = [row for row in blocked if isinstance(row, dict)]
        direct_rows = [
            row
            for row in matrix.get("direct_measured_replay_sources", [])
            if isinstance(row, dict)
        ]
        conditioned_rows = [
            row
            for row in matrix.get(
                "source_conditioned_synthetic_stress_sources", []
            )
            if isinstance(row, dict)
        ]
        context_rows = [
            row
            for row in matrix.get("context_only_measured_sources", [])
            if isinstance(row, dict)
        ]
        critical_measured = [row for row in measured_rows if norm_source(row.get("source")) in critical]
        critical_blocked = [row for row in blocked_rows if norm_source(row.get("source")) in critical]

        mapped.append(
            {
                "replay_rank": int(card.get("wiring_rank", index) or index),
                "lane": lane,
                "candidate_family_id": card.get("candidate_family_id", card.get("best_geometry", "")),
                "candidate_strategy": card.get("candidate_strategy", card.get("best_geometry", "")),
                "runner_script": card.get("runner_script", ""),
                "best_baseline": card.get("best_baseline", ""),
                "score_delta_vs_best_baseline": float(card.get("score_delta_vs_best_baseline", 0.0) or 0.0),
                "validation_scenario_count": int(card.get("validation_scenario_count", 0) or 0),
                "target_live_sources": [norm_source(item) for item in card.get("target_live_sources", [])],
                "fresh_measured_sources": compact_source_rows(measured_rows),
                "direct_measured_replay_sources": compact_source_rows(direct_rows),
                "source_conditioned_synthetic_stress_sources": compact_source_rows(
                    conditioned_rows
                ),
                "context_only_measured_sources": compact_source_rows(context_rows),
                "fresh_blocked_sources": compact_source_rows(blocked_rows),
                "critical_measured_sources": compact_source_rows(critical_measured),
                "critical_blocked_sources": compact_source_rows(critical_blocked),
                "source_snapshot_sha256_count": sum(1 for row in measured_rows if row.get("snapshot_sha256")),
                "lane_ready_for_direct_source_replay_build": bool(
                    matrix.get("lane_ready_for_direct_source_replay_build")
                ),
                "lane_ready_for_source_conditioned_simulation_build": bool(
                    matrix.get(
                        "lane_ready_for_source_conditioned_simulation_build"
                    )
                ),
                "lane_ready_for_live_replay_build": bool(
                    matrix.get("lane_ready_for_direct_source_replay_build")
                ),
                "ready_for_live_geometry_claim": False,
                "ready_for_real_dollar_claim": False,
                "kraken_live_execution_allowed": False,
                "next_adapter": matrix.get("first_live_replay", card.get("first_test", "")),
                "claim_boundary": (
                    "Top generated champion mapped by semantic source compatibility. Direct measured "
                    "replay and source-conditioned synthetic stress are separate gates; both require "
                    "uncertainty bounds and field validation before live or dollar claims."
                ),
            }
        )
    return sorted(mapped, key=lambda row: row["replay_rank"])

def build_matrix() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    frontier = read_json(FRONTIER_JSON)
    bridge = read_json(BRIDGE_JSON)
    live = read_json(LIVE_SOURCE_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)
    protocol_field = read_json(PROTOCOL_FIELD_JSON)
    if not verify_payload_hash(protocol_field, "board_sha256"):
        raise ValueError("full geometry protocol field self-hash is missing or invalid")

    lanes, families = registry_rows(registry)
    live_lookup = with_recent_snapshot_fallbacks(live_source_lookup(live))
    generated_by_lane = generated_champions(frontier, bridge)
    proof_by_lane = proof_champions(frontier, bridge)
    dollar_sources = allowed_estimated_sources(dollar_gate)
    protocol_by_lane = {
        str(row.get("lane")): row
        for row in protocol_field.get("lane_summary", [])
        if isinstance(row, dict) and row.get("lane")
    }

    matrix_rows = [
        lane_matrix_row(
            lane,
            lane_spec,
            families,
            live_lookup,
            generated_by_lane,
            proof_by_lane,
            dollar_sources,
            bridge,
            protocol_by_lane.get(lane, {}),
        )
        for lane, lane_spec in sorted(lanes.items())
    ]
    priority_queue = sorted(
        matrix_rows,
        key=lambda row: (-float(row["live_wiring_score"]), -len(row["measured_sources"]), row["lane"]),
    )
    for rank, row in enumerate(priority_queue, start=1):
        row["proof_build_priority_rank"] = rank

    top_replay_map = top_live_replay_source_map(bridge, matrix_rows)
    measured_names = sorted(
        source
        for source, row in live_lookup.items()
        if bool(row.get("measured")) and str(row.get("status", "")).upper() == "MEASURED"
    )
    failed_names = sorted(source for source, row in live_lookup.items() if source not in measured_names and row.get("enabled"))
    eia = live_lookup.get("EIA", {})
    total_measured_rows = sum(int(row.get("rows", 0) or 0) for source, row in live_lookup.items() if source in measured_names)

    return {
        "generated_utc": now_utc(),
        "schema": "geometry_live_wiring_matrix_v3",
        "purpose": (
            "Map every geometry lane and current champion to semantically compatible direct "
            "measured replay, source-conditioned synthetic stress, context-only sources, "
            "blocked paths, source-specific baselines, and conservative claim gates."
        ),
        "freshness_policy": "The latest live_source_measurement_maximizer output is authoritative over older bridge/live-breadth rollups.",
        "summary": {
            "lane_count": len(matrix_rows),
            "family_count": len(families),
            "implementation_present_count": int(
                protocol_field.get("summary", {}).get("implementation_present_count", 0)
            ),
            "frozen_generated_executed_count": int(
                protocol_field.get("summary", {}).get(
                    "frozen_generated_executed_count", 0
                )
            ),
            "source_conditioned_replay_count": int(
                protocol_field.get("summary", {}).get(
                    "source_conditioned_replay_count", 0
                )
            ),
            "field_validated_family_count": 0,
            "live_source_enabled_count": live.get("summary", {}).get("enabled_sources", 0),
            "live_source_measured_count": len(measured_names),
            "live_source_failed_or_thin_count": live.get("summary", {}).get("failed_or_thin_sources", 0),
            "total_measured_rows": total_measured_rows,
            "estimated_annual_value_surface_usd": 0.0,
            "claimable_annual_value_usd": 0.0,
            "context_only_estimated_annual_value_surface_usd": live.get(
                "summary", {}
            ).get("estimated_annual_value_surface_usd", 0.0),
            "economic_value_claim_allowed": False,
            "measured_source_names": measured_names,
            "failed_or_thin_source_names": failed_names,
            "eia_status": eia.get("status", "missing"),
            "eia_rows": int(eia.get("rows", 0) or 0),
            "lanes_ready_for_direct_source_replay_build": sum(
                1
                for row in matrix_rows
                if row["lane_ready_for_direct_source_replay_build"]
            ),
            "lanes_ready_for_source_conditioned_simulation_build": sum(
                1
                for row in matrix_rows
                if row["lane_ready_for_source_conditioned_simulation_build"]
            ),
            "lanes_ready_for_live_replay_build": sum(
                1
                for row in matrix_rows
                if row["lane_ready_for_direct_source_replay_build"]
            ),
            "qualified_direct_source_links": sum(
                len(row["direct_measured_replay_sources"]) for row in matrix_rows
            ),
            "qualified_conditioning_source_links": sum(
                len(row["source_conditioned_synthetic_stress_sources"])
                for row in matrix_rows
            ),
            "context_only_measured_source_links": sum(
                len(row["context_only_measured_sources"]) for row in matrix_rows
            ),
            "lanes_with_generated_champions": sum(1 for row in matrix_rows if row["generated_champion"]["family"]),
            "lanes_with_proof_champions": sum(1 for row in matrix_rows if row["proof_value_champion"]["family"]),
            "top_live_replay_source_map_count": len(top_replay_map),
            "top_live_replay_ready_count": sum(
                1
                for row in top_replay_map
                if row["lane_ready_for_direct_source_replay_build"]
            ),
            "top_source_conditioned_simulation_ready_count": sum(
                1
                for row in top_replay_map
                if row["lane_ready_for_source_conditioned_simulation_build"]
            ),
            "top_live_replay_measured_source_count": sum(len(row["fresh_measured_sources"]) for row in top_replay_map),
            "top_live_replay_snapshot_sha256_count": sum(row["source_snapshot_sha256_count"] for row in top_replay_map),
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "claim_boundary": (
                "Measured source availability alone is context, not task compatibility or family "
                "execution. Direct measured replay, source-conditioned synthetic stress, frozen "
                "generated execution, and field validation are separate gates. This matrix is not "
                "field validation, realized savings, award certainty, or trading profit."
            ),
        },
        "top_live_replay_source_map": top_replay_map,
        "priority_queue": priority_queue,
        "matrix": matrix_rows,
        "next_actions": [
            "Run direct measured comparisons first for time_series_model_routing and wave_resonance_timing using their source-specific baseline rosters.",
            "Treat branching_transport, thermal_ventilation, mission_network_routing, and multi_agent_coordination source links as synthetic stress conditioning until direct outcome telemetry exists.",
            "Do not use optimal_curve_transport source snapshots as performance inputs until observed paths, constraints, and outcomes are available.",
            "Build an EIA residual-matrix adapter before calling stability_diagnostic direct-replay ready.",
            "Fix NREL DNS/API reachability because it remains a key energy-lab blocker.",
            "Add SAM_GOV_API_KEY if contract-bid/opportunity wiring should become measured.",
            "Keep market_signal_geometry in paper/replay mode until a separate trading safety audit and explicit action-time approval exist.",
        ],
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "frontier_board": str(FRONTIER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_bridge": str(BRIDGE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_source_measurement_maximizer": str(LIVE_SOURCE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dollar_claim_gate": str(DOLLAR_GATE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "full_geometry_protocol_field": {
                "path": str(PROTOCOL_FIELD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "schema": protocol_field.get("schema"),
                "board_sha256": protocol_field.get("board_sha256"),
                "self_hash_valid": True,
            },
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Live Wiring Matrix",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Lanes: {summary['lane_count']}",
        f"- Families: {summary['family_count']}",
        f"- Implementations present: {summary['implementation_present_count']}",
        f"- Frozen generated executions: {summary['frozen_generated_executed_count']}",
        f"- Source-conditioned replay receipts: {summary['source_conditioned_replay_count']}",
        f"- Field-validated families: {summary['field_validated_family_count']}",
        f"- Fresh measured sources: {summary['live_source_measured_count']}",
        f"- Fresh failed/thin sources: {summary['live_source_failed_or_thin_count']}",
        f"- Total measured rows: {summary['total_measured_rows']}",
        f"- EIA status: `{summary['eia_status']}` with {summary['eia_rows']} rows",
        f"- Claimable annual value: ${summary['claimable_annual_value_usd']:,.2f}",
        f"- Context-only modeled source surface: ${summary['context_only_estimated_annual_value_surface_usd']:,.2f}",
        f"- Lanes ready for direct measured replay build: {summary['lanes_ready_for_direct_source_replay_build']}",
        f"- Lanes ready for source-conditioned synthetic stress build: {summary['lanes_ready_for_source_conditioned_simulation_build']}",
        f"- Qualified direct-source links: {summary['qualified_direct_source_links']}",
        f"- Qualified conditioning-source links: {summary['qualified_conditioning_source_links']}",
        f"- Context-only measured-source links: {summary['context_only_measured_source_links']}",
        f"- Top live replay source-map cards: {summary['top_live_replay_source_map_count']}",
        f"- Top replay cards ready for direct measured build: {summary['top_live_replay_ready_count']}",
        f"- Top replay cards ready for conditioned simulation: {summary['top_source_conditioned_simulation_ready_count']}",
        f"- Top replay measured source links: {summary['top_live_replay_measured_source_count']}",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Kraken live execution allowed: `{str(summary['kraken_live_execution_allowed']).lower()}`",
        f"- Boundary: {summary['claim_boundary']}",
        "",
        "## Top Live Replay Source Map",
        "",
        "| Rank | Lane | Candidate | Best Baseline | Direct | Conditioned | Context | Direct Ready |",
        "| ---: | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload.get("top_live_replay_source_map", []):
        direct = ", ".join(
            item["source"] for item in row["direct_measured_replay_sources"]
        ) or "none"
        conditioned = ", ".join(
            item["source"]
            for item in row["source_conditioned_synthetic_stress_sources"]
        ) or "none"
        context = ", ".join(
            item["source"] for item in row["context_only_measured_sources"]
        ) or "none"
        lines.append(
            "| {rank} | `{lane}` | `{candidate}` | `{baseline}` | {direct} | {conditioned} | {context} | `{ready}` |".format(
                rank=row["replay_rank"],
                lane=row["lane"],
                candidate=row["candidate_family_id"] or row["candidate_strategy"],
                baseline=row["best_baseline"],
                direct=direct,
                conditioned=conditioned,
                context=context,
                ready=str(
                    row["lane_ready_for_direct_source_replay_build"]
                ).lower(),
            )
        )
    lines.extend(
        [
            "",
            "Each row separates direct measured replay from source-conditioned synthetic stress. Neither is a live performance claim; promotion still requires a frozen lane replay, uncertainty bounds, and claim-gate approval.",
            "",
            "## Proof Build Priority Queue",
            "",
        ]
    )
    for row in payload["priority_queue"]:
        measured = ", ".join(item["source"] for item in row["measured_sources"]) or "none"
        blocked = ", ".join(item["source"] for item in row["blocked_sources"]) or "none"
        direct = ", ".join(
            item["source"] for item in row["direct_measured_replay_sources"]
        ) or "none"
        conditioned = ", ".join(
            item["source"]
            for item in row["source_conditioned_synthetic_stress_sources"]
        ) or "none"
        lines.extend(
            [
                f"### {row['proof_build_priority_rank']}. {row['lane']}",
                "",
                f"- Score: {row['live_wiring_score']}",
                f"- Measured sources: {measured}",
                f"- Direct measured replay sources: {direct}",
                f"- Source-conditioned synthetic stress sources: {conditioned}",
                f"- Blocked sources: {blocked}",
                f"- Generated champion: `{row['generated_champion']['family'] or 'none'}`",
                f"- Proof-value champion: `{row['proof_value_champion']['family'] or 'none'}`",
                f"- First live replay: {row['first_live_replay']}",
                f"- Safe claim: {row['safe_claim_language']}",
                "",
            ]
        )
    lines.extend(["## Blockers To Clear", ""])
    blockers = sorted(set(summary["failed_or_thin_source_names"]))
    for name in blockers:
        lines.append(f"- `{name}` remains failed/thin in the fresh maximizer run.")
    lines.extend(["", "## Next Actions", ""])
    lines.extend(f"- {item}" for item in payload["next_actions"])
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This matrix is a live-source wiring and replay-priority artifact. It is not field validation, not a realized-dollar proof, not an award-selection promise, and not permission for live trading.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    payload = build_matrix()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "lanes": payload["summary"]["lane_count"],
                "families": payload["summary"]["family_count"],
                "measured_sources": payload["summary"]["live_source_measured_count"],
                "eia_status": payload["summary"]["eia_status"],
                "eia_rows": payload["summary"]["eia_rows"],
                "ready_for_live_geometry_claim": payload["summary"]["ready_for_live_geometry_claim"],
                "top_priority_lane": payload["priority_queue"][0]["lane"] if payload["priority_queue"] else "",
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
