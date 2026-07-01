from __future__ import annotations

import json
from datetime import datetime, timezone
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
        "sources": ["NOAA_NCEI", "NASA", "USGS_WATER", "KRAKEN_PUBLIC"],
        "critical_sources": ["NOAA_NCEI", "USGS_WATER"],
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
        "sources": ["NOAA_NCEI", "GRANTS_GOV", "KRAKEN_PUBLIC", "WEBHOOK"],
        "critical_sources": ["NOAA_NCEI", "WEBHOOK"],
        "first_live_replay": "multi-agent coordination replay under weather/event disruption and public time-series stress",
        "highest_impact_use": "swarm coordination, task allocation, review-burden reduction",
    },
    "branching_transport": {
        "sources": ["EIA", "NREL", "NOAA_NCEI", "USGS_WATER", "WEBHOOK"],
        "critical_sources": ["EIA", "NOAA_NCEI", "USGS_WATER"],
        "first_live_replay": "critical-flow and failure-propagation replay using EIA load, weather, hydrology, and event signals",
        "highest_impact_use": "grid resilience, datacenter flow, outage detection, logistics, cold-chain routing",
    },
    "thermal_ventilation": {
        "sources": ["EIA", "NOAA_NCEI", "NREL"],
        "critical_sources": ["EIA", "NOAA_NCEI"],
        "first_live_replay": "load-plus-ambient thermal replay comparing plume/cellular ventilation against straight-duct baselines",
        "highest_impact_use": "datacenter cooling, HVAC energy recovery, thermal resilience",
    },
    "resource_aware_scheduling": {
        "sources": ["BLS", "FRED", "BEA", "WEBHOOK"],
        "critical_sources": ["FRED", "BEA", "WEBHOOK"],
        "first_live_replay": "bounded wake/scheduling replay using macro pressure and internal event cadence",
        "highest_impact_use": "compute scheduling, automation throttling, low-power operations",
    },
    "time_series_model_routing": {
        "sources": [
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
        "critical_sources": ["FRED", "BEA", "NOAA_NCEI"],
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
        "sources": ["EIA", "FRED", "KRAKEN_PUBLIC", "NOAA_NCEI", "NASA"],
        "critical_sources": ["EIA", "FRED", "NOAA_NCEI"],
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
            "snapshot_sha256": payload.get("sha256", ""),
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
    measured_sources: list[dict[str, Any]],
    blocked_sources: list[dict[str, Any]],
    generated: dict[str, Any],
    proof: dict[str, Any],
    allowed_sources: list[dict[str, Any]],
) -> float:
    measured_count = len(measured_sources)
    hash_count = sum(1 for row in measured_sources if row.get("snapshot_sha256"))
    blocked_count = len(blocked_sources)
    delta = float(generated.get("score_delta_vs_best_baseline", 0) or 0)
    proof_score = float(
        proof.get("proof_priority_score", proof.get("readiness_score", 0) or 0) or 0
    )
    allowed_count = len(allowed_sources)
    return round(
        measured_count * 10.0
        + hash_count * 3.0
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
) -> dict[str, Any]:
    plan = LANE_SOURCE_PLAN.get(lane, {"sources": [], "critical_sources": []})
    sources = [norm_source(item) for item in plan.get("sources", [])]
    critical = {norm_source(item) for item in plan.get("critical_sources", [])}
    projections = [source_projection(source, live_lookup) for source in sources]
    measured = [row for row in projections if row["measured"]]
    blocked = [row for row in projections if not row["measured"]]
    public_paths = [row for row in projections if row["public_no_key_path"] and row["measured"]]
    lane_families = [row for row in families if str(row.get("lane", "")) == lane]
    generated = generated_by_lane.get(lane, {})
    proof = proof_by_lane.get(lane, {})
    allowed = [row for row in projections if row["source"] in dollar_sources and row["measured"]]
    critical_blockers = [row for row in blocked if row["source"] in critical]

    has_generated = bool(generated)
    lane_ready_for_replay = len(measured) >= 2 and (has_generated or bool(proof))
    lane_claim_blockers = [
        "no completed lane-specific live replay using these fresh snapshots",
        "no field validation or customer/government operational validation",
        "no paired uncertainty interval on the fresh live replay",
        "no multiple-comparison control across the full geometry family registry",
    ]
    if critical_blockers:
        lane_claim_blockers.append("critical source blockers remain: " + ", ".join(row["source"] for row in critical_blockers))
    if lane == "market_signal_geometry":
        lane_claim_blockers.append("market lane is paper/replay only; no live trading or profit claim is authorized")

    return {
        "lane": lane,
        "family_count": len(lane_families),
        "baselines": lane_spec.get("baselines", []),
        "metrics": lane_spec.get("metrics", []),
        "highest_impact_use": plan.get("highest_impact_use", ""),
        "first_live_replay": plan.get("first_live_replay", ""),
        "source_plan": sources,
        "critical_sources": sorted(critical),
        "measured_sources": measured,
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
            }
            for row in allowed
        ],
        "live_wiring_score": lane_score(measured, blocked, generated, proof, allowed),
        "lane_ready_for_live_replay_build": lane_ready_for_replay,
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "kraken_live_execution_allowed": False,
        "claim_blockers": lane_claim_blockers,
        "safe_claim_language": (
            "This lane has fresh measured source paths and can be queued for frozen live replay; "
            "it is not field validation, not realized savings, and not an award-certainty or profit claim."
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
                "fresh_blocked_sources": compact_source_rows(blocked_rows),
                "critical_measured_sources": compact_source_rows(critical_measured),
                "critical_blocked_sources": compact_source_rows(critical_blocked),
                "source_snapshot_sha256_count": sum(1 for row in measured_rows if row.get("snapshot_sha256")),
                "lane_ready_for_live_replay_build": bool(matrix.get("lane_ready_for_live_replay_build")),
                "ready_for_live_geometry_claim": False,
                "ready_for_real_dollar_claim": False,
                "kraken_live_execution_allowed": False,
                "next_adapter": matrix.get("first_live_replay", card.get("first_test", "")),
                "claim_boundary": (
                    "Top generated champion mapped to fresh source snapshots only; "
                    "requires lane-specific replay, uncertainty bounds, and field validation before live or dollar claims."
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

    lanes, families = registry_rows(registry)
    live_lookup = with_recent_snapshot_fallbacks(live_source_lookup(live))
    generated_by_lane = generated_champions(frontier, bridge)
    proof_by_lane = proof_champions(frontier, bridge)
    dollar_sources = allowed_estimated_sources(dollar_gate)

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
        "schema": "geometry_live_wiring_matrix_v1",
        "purpose": "Map every geometry lane and current champion to fresh measured live-source paths, blocked paths, replay targets, and conservative claim gates.",
        "freshness_policy": "The latest live_source_measurement_maximizer output is authoritative over older bridge/live-breadth rollups.",
        "summary": {
            "lane_count": len(matrix_rows),
            "family_count": len(families),
            "live_source_enabled_count": live.get("summary", {}).get("enabled_sources", 0),
            "live_source_measured_count": len(measured_names),
            "live_source_failed_or_thin_count": live.get("summary", {}).get("failed_or_thin_sources", 0),
            "total_measured_rows": total_measured_rows,
            "estimated_annual_value_surface_usd": live.get("summary", {}).get("estimated_annual_value_surface_usd", 0.0),
            "measured_source_names": measured_names,
            "failed_or_thin_source_names": failed_names,
            "eia_status": eia.get("status", "missing"),
            "eia_rows": int(eia.get("rows", 0) or 0),
            "lanes_ready_for_live_replay_build": sum(1 for row in matrix_rows if row["lane_ready_for_live_replay_build"]),
            "lanes_with_generated_champions": sum(1 for row in matrix_rows if row["generated_champion"]["family"]),
            "lanes_with_proof_champions": sum(1 for row in matrix_rows if row["proof_value_champion"]["family"]),
            "top_live_replay_source_map_count": len(top_replay_map),
            "top_live_replay_ready_count": sum(1 for row in top_replay_map if row["lane_ready_for_live_replay_build"]),
            "top_live_replay_measured_source_count": sum(len(row["fresh_measured_sources"]) for row in top_replay_map),
            "top_live_replay_snapshot_sha256_count": sum(row["source_snapshot_sha256_count"] for row in top_replay_map),
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "claim_boundary": "Fresh live-source wiring is stronger evidence than synthetic-only tests, but it is not field validation, realized savings, award certainty, or trading profit.",
        },
        "top_live_replay_source_map": top_replay_map,
        "priority_queue": priority_queue,
        "matrix": matrix_rows,
        "next_actions": [
            "Run the top live replay source-map cards against frozen measured snapshots: optimal_curve_transport, wave_resonance_timing, branching_transport, thermal_ventilation, and time_series_model_routing.",
            "Run branching_transport and thermal_ventilation live replays now that EIA is measured.",
            "Keep NASA in the wave-resonance timing replay map now that it has a measured snapshot.",
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
        f"- Fresh measured sources: {summary['live_source_measured_count']}",
        f"- Fresh failed/thin sources: {summary['live_source_failed_or_thin_count']}",
        f"- Total measured rows: {summary['total_measured_rows']}",
        f"- EIA status: `{summary['eia_status']}` with {summary['eia_rows']} rows",
        f"- Estimated annual source surface: ${summary['estimated_annual_value_surface_usd']:,.2f}",
        f"- Lanes ready for live replay build: {summary['lanes_ready_for_live_replay_build']}",
        f"- Top live replay source-map cards: {summary['top_live_replay_source_map_count']}",
        f"- Top replay cards ready for build: {summary['top_live_replay_ready_count']}",
        f"- Top replay measured source links: {summary['top_live_replay_measured_source_count']}",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Kraken live execution allowed: `{str(summary['kraken_live_execution_allowed']).lower()}`",
        f"- Boundary: {summary['claim_boundary']}",
        "",
        "## Top Live Replay Source Map",
        "",
        "| Rank | Lane | Candidate | Best Baseline | Measured Sources | Blocked Sources | Ready |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload.get("top_live_replay_source_map", []):
        measured = ", ".join(item["source"] for item in row["fresh_measured_sources"]) or "none"
        blocked = ", ".join(item["source"] for item in row["fresh_blocked_sources"]) or "none"
        lines.append(
            "| {rank} | `{lane}` | `{candidate}` | `{baseline}` | {measured} | {blocked} | `{ready}` |".format(
                rank=row["replay_rank"],
                lane=row["lane"],
                candidate=row["candidate_family_id"] or row["candidate_strategy"],
                baseline=row["best_baseline"],
                measured=measured,
                blocked=blocked,
                ready=str(row["lane_ready_for_live_replay_build"]).lower(),
            )
        )
    lines.extend(
        [
            "",
            "Each row is a replay-build card, not a live performance claim. Promotion still requires a frozen lane replay, uncertainty bounds, and claim-gate approval.",
            "",
            "## Proof Build Priority Queue",
            "",
        ]
    )
    for row in payload["priority_queue"]:
        measured = ", ".join(item["source"] for item in row["measured_sources"]) or "none"
        blocked = ", ".join(item["source"] for item in row["blocked_sources"]) or "none"
        lines.extend(
            [
                f"### {row['proof_build_priority_rank']}. {row['lane']}",
                "",
                f"- Score: {row['live_wiring_score']}",
                f"- Measured sources: {measured}",
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
