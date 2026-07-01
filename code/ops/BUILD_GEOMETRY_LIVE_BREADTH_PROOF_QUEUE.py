from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
FRONTIER_JSON = OUT_OPS / "geometry_proof_frontier_board_latest.json"
LIVE_VALUE_METER_JSON = OUT_OPS / "live_proof_value_meter_latest.json"
LIVE_BREADTH_PANEL_JSON = OUT_OPS / "live_breadth_value_panel_latest.json"
DOLLAR_GATE_JSON = OUT_OPS / "dollar_claim_gate_latest.json"
ROLLING_GATE_JSON = OUT_OPS / "rolling_champion_gate_latest.json"

OUT_JSON = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_live_breadth_proof_queue.json"
OUT_MD = DOCS / "GEOMETRY_LIVE_BREADTH_PROOF_QUEUE_2026-06-22.md"


LANE_PROFILES: dict[str, dict[str, Any]] = {
    "mission_network_routing": {
        "impact_score": 92,
        "grant_fit_score": 90,
        "proof_asset": "Mission routing and degraded-network proof card",
        "live_sources": ["EIA", "NREL", "NOAA_NCEI", "USGS_WATER", "CENSUS"],
        "target_assets": [
            "public/authorized network-topology windows",
            "edge-failure and congestion snapshots",
            "mission route constraints and delivery-cost windows",
        ],
        "next_adapter": "Freeze route graphs, inject edge failures, then run Dijkstra, A*, min-cost-flow, and candidate geometry on identical windows.",
        "grant_story": "Defense, disaster logistics, grid restoration, and degraded communications.",
    },
    "field_guided_control": {
        "impact_score": 94,
        "grant_fit_score": 88,
        "proof_asset": "Field-guided defense and infrastructure control proof card",
        "live_sources": ["NOAA_NCEI", "USGS_WATER", "EIA", "NREL", "EPA_AQS"],
        "target_assets": [
            "vector-field or environmental forcing windows",
            "moving-target or corridor constraints",
            "energy/control-effort traces",
        ],
        "next_adapter": "Convert live environmental/forcing windows into field maps and compare Euclidean potential fields, MPC, and geometry candidates.",
        "grant_story": "Maritime, autonomous sensing, resilience, energy, and environmental response.",
    },
    "packing_topology": {
        "impact_score": 80,
        "grant_fit_score": 72,
        "proof_asset": "Hardware layout, sensor packing, and resilient topology proof card",
        "live_sources": ["NREL", "EIA", "NOAA_NCEI"],
        "target_assets": [
            "sensor/node placement maps",
            "public facility/load layout proxies",
            "failure-tolerance and material-proxy windows",
        ],
        "next_adapter": "Freeze layout scenarios and compare square, triangular, random, optimized, and bio-topology candidates.",
        "grant_story": "Hardware prototyping, sensor layout, resilient edge infrastructure, and packaging.",
    },
    "multi_agent_coordination": {
        "impact_score": 82,
        "grant_fit_score": 86,
        "proof_asset": "Multi-agent formation and swarm coordination proof card",
        "live_sources": ["NOAA_NCEI", "EIA", "NREL"],
        "target_assets": [
            "multi-agent task windows",
            "collision and formation-error traces",
            "energy or message-budget constraints",
        ],
        "next_adapter": "Freeze agent-mission windows and compare independent shortest path, consensus, MPC, and bio-coordination candidates.",
        "grant_story": "Autonomous defense systems, distributed sensors, and robotics.",
    },
    "branching_transport": {
        "impact_score": 98,
        "grant_fit_score": 95,
        "proof_asset": "Critical-infrastructure branching transport proof card",
        "live_sources": ["EIA", "NREL", "USGS_WATER", "NOAA_NCEI", "FEDWIRE_OPS", "ISO_NE", "HHS_FEED"],
        "target_assets": [
            "grid/load or supply-chain flow windows",
            "public outage/disruption proxies",
            "constrained-flow networks with failure/dropout manifests",
        ],
        "next_adapter": "Convert live load/disruption windows into constrained flow networks and compare MST, Steiner, min-cost-flow, and branching candidates.",
        "grant_story": "Critical infrastructure, power, logistics, healthcare cold chain, and failure localization.",
    },
    "thermal_ventilation": {
        "impact_score": 96,
        "grant_fit_score": 90,
        "proof_asset": "Datacenter cooling and thermal recovery proof card",
        "live_sources": ["EIA", "NREL", "NOAA_NCEI", "EPA_AQS", "ISO_NE"],
        "target_assets": [
            "load and ambient-temperature windows",
            "thermal recovery and pressure-drop proxies",
            "datacenter/HVAC scenario manifests",
        ],
        "next_adapter": "Map frozen load and ambient-temperature windows into thermal-grid replay, then compare straight duct, conventional HVAC, CFD reference, and thermal geometry candidates.",
        "grant_story": "DOE, datacenter uptime, energy efficiency, cooling, and resilience.",
    },
    "resource_aware_scheduling": {
        "impact_score": 78,
        "grant_fit_score": 78,
        "proof_asset": "Bounded wake and resource scheduling proof card",
        "live_sources": ["EIA", "NREL", "KRAKEN", "FRED", "BLS"],
        "target_assets": [
            "task-arrival and resource-price windows",
            "deadline and energy-budget traces",
            "wake/sleep decision manifests",
        ],
        "next_adapter": "Freeze task windows and compare always-on, fixed-sleep, EDF, threshold wake, and bio-scheduler candidates.",
        "grant_story": "Edge compute, low-power sensing, energy-aware AI, and resilient operations.",
    },
    "time_series_model_routing": {
        "impact_score": 88,
        "grant_fit_score": 84,
        "proof_asset": "Live-breadth forecasting and regime-drift proof card",
        "live_sources": [
            "EIA",
            "NREL",
            "FRED",
            "BEA",
            "BLS",
            "KRAKEN",
            "FINNHUB",
            "ALPHAVANTAGE",
            "TWELVE_DATA",
            "MASSIVE",
        ],
        "target_assets": [
            "walk-forward time-series windows",
            "leakage-control declarations",
            "persistence, seasonal naive, ridge, and MLP budget-matched baselines",
        ],
        "next_adapter": "Freeze walk-forward splits and compare baseline forecasters against each flowform feature family.",
        "grant_story": "Forecasting, anomaly detection, regime drift, live-breadth proof, and operations intelligence.",
    },
    "stability_diagnostic": {
        "impact_score": 72,
        "grant_fit_score": 82,
        "proof_asset": "Stability diagnostic and reviewer trust gate",
        "live_sources": ["EIA", "NREL", "FRED", "BEA", "KRAKEN", "NOAA_NCEI"],
        "target_assets": [
            "frozen replay windows from any promoted lane",
            "perturbation, conditioning, and sensitivity manifests",
            "negative controls and uncertainty intervals",
        ],
        "next_adapter": "Apply diagnostics to already-frozen lane outputs before any live/dollar promotion.",
        "grant_story": "Reviewer trust, robustness, reproducibility, and failure-mode discipline.",
    },
    "optimal_curve_transport": {
        "impact_score": 84,
        "grant_fit_score": 72,
        "proof_asset": "Brachistochrone and optimal-transport benchmark card",
        "live_sources": ["EIA", "NREL", "NOAA_NCEI", "USGS_WATER"],
        "target_assets": [
            "frozen public path-planning maps",
            "layout/cabling/thermal path scenarios",
            "curvature, obstacle, drag, and runtime constraints",
        ],
        "next_adapter": "Freeze obstacle/path windows, run straight-line, spline, RRT*, minimum-jerk, and brachistochrone candidates on identical constraints.",
        "grant_story": "Fast visual/math proof, route optimization, cabling/layout, thermal paths, and constrained movement.",
    },
    "wave_resonance_timing": {
        "impact_score": 86,
        "grant_fit_score": 92,
        "proof_asset": "Harmonic timing and oscillatory-system proof card",
        "live_sources": ["EIA", "NREL", "FRED", "BEA", "KRAKEN", "FINNHUB", "ALPHAVANTAGE", "TWELVE_DATA"],
        "target_assets": [
            "EIA/NREL load or grid-stability proxy windows",
            "phase-window synthetic controls",
            "Kraken/Finnhub public time-series as paper stress controls only",
        ],
        "next_adapter": "Convert frozen oscillatory windows into phase-error tasks and compare FFT, Kalman, ARIMA, PLL, and oscillator-coupling candidates.",
        "grant_story": "Harmonic/backprop thesis, PLL-like stability, grid timing, signal drift, and oscillatory systems.",
    },
    "market_signal_geometry": {
        "impact_score": 62,
        "grant_fit_score": 55,
        "proof_asset": "Market geometry paper-lab proof card",
        "live_sources": ["KRAKEN", "FINNHUB", "ALPHAVANTAGE", "TWELVE_DATA", "MASSIVE", "ALPACA_PAPER", "POLYGON"],
        "target_assets": [
            "read-only or paper market windows",
            "walk-forward splits with fee/slippage assumptions",
            "risk, drawdown, and abstention manifests",
        ],
        "next_adapter": "Freeze paper/read-only market windows and compare buy-hold, moving-average, volatility target, ridge, and geometry features.",
        "grant_story": "Paper-only calibration lane; useful for timing/stress evidence but not a grant or profit claim by itself.",
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


def money(value: float | int | None) -> str:
    numeric = float(value or 0)
    if abs(numeric) >= 1_000_000_000:
        return f"${numeric / 1_000_000_000:.2f}B"
    if abs(numeric) >= 1_000_000:
        return f"${numeric / 1_000_000:.2f}M"
    if abs(numeric) >= 1_000:
        return f"${numeric / 1_000:.2f}K"
    return f"${numeric:.2f}"


def log_value_score(value: float) -> float:
    if value <= 0:
        return 0.0
    return max(0.0, min(100.0, (math.log10(value + 1) - 4.0) * 22.0))


def source_rows(live_panel: dict[str, Any], dollar_gate: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}

    def add(row: dict[str, Any], status_hint: str = "") -> None:
        source = str(row.get("source", "") or row.get("provider", "")).upper()
        if not source:
            return
        existing = rows.get(source, {})
        primary_live = bool(row.get("primary_live_evidence", False) or row.get("measured_source", False))
        existing["source"] = source
        existing["sector"] = row.get("sector", existing.get("sector", ""))
        existing["primary_live_evidence"] = bool(existing.get("primary_live_evidence", False) or primary_live)
        existing["claim_band"] = row.get("claim_band", existing.get("claim_band", ""))
        existing["status"] = row.get("status", existing.get("status", status_hint))
        existing["annual_value_usd"] = max(
            float(existing.get("annual_value_usd", 0) or 0),
            float(row.get("estimated_annual_value_usd", 0) or 0),
        )
        existing["hourly_value_usd"] = max(
            float(existing.get("hourly_value_usd", 0) or 0),
            float(row.get("estimated_hourly_value_usd", 0) or 0),
        )
        existing["missing_for_stronger_claim"] = row.get(
            "missing_for_stronger_claim", existing.get("missing_for_stronger_claim", [])
        )
        rows[source] = existing

    for row in live_panel.get("source_rows", []):
        if isinstance(row, dict):
            add(row, "live_breadth_panel")
    for row in dollar_gate.get("estimated_value_lanes", []):
        if isinstance(row, dict):
            add(row, "estimated_value_signal")
    for row in dollar_gate.get("context_only_or_blocked_lanes", []):
        if isinstance(row, dict):
            add(row, "blocked_context_only")
    return rows


def frontier_indexes(frontier: dict[str, Any]) -> dict[str, Any]:
    generated = {
        str(row.get("best_geometry_family_id") or row.get("best_geometry")): row
        for row in frontier.get("generated_benchmark_frontier", [])
        if isinstance(row, dict)
    }
    proof_value = {
        str(row.get("candidate_champion_id")): row
        for row in frontier.get("proof_value_frontier", [])
        if isinstance(row, dict)
    }
    lane_generated = {
        str(row.get("lane")): row
        for row in frontier.get("generated_benchmark_frontier", [])
        if isinstance(row, dict)
    }
    lane_proof = {
        str(row.get("lane")): row
        for row in frontier.get("proof_value_frontier", [])
        if isinstance(row, dict)
    }
    return {
        "generated": generated,
        "proof_value": proof_value,
        "lane_generated": lane_generated,
        "lane_proof": lane_proof,
    }


def rolling_gate_indexes(rolling_gate: dict[str, Any]) -> dict[str, Any]:
    """Index the strict rolling champion gate by family and entity.

    This gate is intentionally stricter than the proof queue. A family can be a
    high-priority work order without being a repeat champion. Keeping the rolling
    status explicit prevents one-run wins from becoming sales or grant claims.
    """

    board = rolling_gate.get("promotion_board", [])
    by_family: dict[str, dict[str, Any]] = {}
    by_entity: dict[str, dict[str, Any]] = {}
    triple_source_candidates: list[dict[str, Any]] = []
    triple_source_rolling_champions: list[dict[str, Any]] = []
    rolling_champions: list[dict[str, Any]] = []
    single_run_candidates: list[dict[str, Any]] = []
    if not isinstance(board, list):
        board = []
    for row in board:
        if not isinstance(row, dict):
            continue
        family_id = str(row.get("family_id", "") or "")
        entity_id = str(row.get("entity_id", "") or "")
        if family_id:
            by_family[family_id] = row
        if entity_id:
            by_entity[entity_id] = row
        status = str(row.get("status", ""))
        if status == "rolling_champion":
            rolling_champions.append(row)
            if int(row.get("source_count") or 0) >= 3:
                triple_source_rolling_champions.append(row)
        elif status == "triple_source_candidate":
            triple_source_candidates.append(row)
        elif status == "single_run_candidate":
            single_run_candidates.append(row)
    return {
        "by_family": by_family,
        "by_entity": by_entity,
        "rolling_champions": rolling_champions,
        "triple_source_rolling_champions": triple_source_rolling_champions,
        "triple_source_candidates": triple_source_candidates,
        "single_run_candidates": single_run_candidates,
        "summary": rolling_gate.get("summary", {}),
        "boundary": rolling_gate.get("evidence_boundary", ""),
    }


def rolling_status_bonus(status: str) -> float:
    return {
        "rolling_champion": 36.0,
        "triple_source_candidate": 24.0,
        "single_run_candidate": 10.0,
        "not_promoted": -2.0,
    }.get(status, 0.0)


def readiness_score(family: dict[str, Any]) -> float:
    status = str(family.get("status", "unknown"))
    score_by_status = {
        "benchmark_design_ready": 55,
        "diagnostic_specification": 45,
        "legacy_transform_only": 35,
        "legacy_analogue_only": 30,
    }
    score = float(score_by_status.get(status, 35))
    for key, weight in [
        ("natural_logic", 10),
        ("benchmark_hypothesis", 10),
        ("first_test", 7),
        ("promotion_metric", 7),
        ("failure_mode", 4),
    ]:
        if family.get(key):
            score += weight
    if family.get("competitor") is False:
        score -= 10
    if "negative" in str(family.get("located_result", "")).lower():
        score -= 8
    return round(max(0.0, min(100.0, score)), 3)


def live_fit(profile: dict[str, Any], sources: dict[str, dict[str, Any]]) -> dict[str, Any]:
    wanted = [str(source).upper() for source in profile.get("live_sources", [])]
    live = [source for source in wanted if sources.get(source, {}).get("primary_live_evidence")]
    context = [source for source in wanted if source in sources and source not in live]
    safe_value = sum(float(sources[source].get("annual_value_usd", 0) or 0) for source in live)
    blocked_value = sum(float(sources[source].get("annual_value_usd", 0) or 0) for source in context)
    score = 24 + (len(live) * 9) + (len(context) * 3) + min(18, math.log10(safe_value + 1) * 2 if safe_value else 0)
    return {
        "target_sources": wanted,
        "live_measured_sources": live,
        "context_only_sources": context,
        "safe_annual_value_surface_usd": round(safe_value, 2),
        "blocked_context_annual_value_surface_usd": round(blocked_value, 2),
        "live_source_fit_score": round(max(0.0, min(100.0, score)), 3),
    }


def family_queue_rows(
    registry: dict[str, Any],
    frontier: dict[str, Any],
    value_meter: dict[str, Any],
    live_panel: dict[str, Any],
    dollar_gate: dict[str, Any],
    rolling_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    families = registry.get("families", []) if isinstance(registry.get("families"), list) else []
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    sources = source_rows(live_panel, dollar_gate)
    indexes = frontier_indexes(frontier)
    rolling_indexes = rolling_gate_indexes(rolling_gate)
    live_backed_generated = int(frontier.get("promotion_gate", {}).get("live_breadth_backed_generated_lanes", 0) or 0)

    rows: list[dict[str, Any]] = []
    for family in families:
        if not isinstance(family, dict):
            continue
        family_id = str(family.get("id", ""))
        lane = str(family.get("lane", ""))
        profile = LANE_PROFILES.get(lane, {})
        lane_meta = lanes.get(lane, {}) if isinstance(lanes.get(lane), dict) else {}
        generated_hit = indexes["generated"].get(family_id)
        proof_hit = indexes["proof_value"].get(family_id)
        rolling_hit = rolling_indexes["by_family"].get(family_id, {})
        lane_generated = indexes["lane_generated"].get(lane, {})
        lane_proof = indexes["lane_proof"].get(lane, {})
        ready = readiness_score(family)
        fit = live_fit(profile, sources)
        value_score = log_value_score(fit["safe_annual_value_surface_usd"])
        blocked_value_score = log_value_score(fit["blocked_context_annual_value_surface_usd"])
        generated_bonus = 22.0 if generated_hit else 0.0
        proof_bonus = 18.0 if proof_hit else 0.0
        lane_generated_bonus = 8.0 if lane_generated else 0.0
        lane_proof_bonus = 6.0 if lane_proof else 0.0
        rolling_status = str(rolling_hit.get("status", "not_in_rolling_gate") or "not_in_rolling_gate")
        rolling_bonus = rolling_status_bonus(rolling_status)
        safety_penalty = 8.0 if lane == "market_signal_geometry" else 0.0
        score = (
            ready * 0.20
            + fit["live_source_fit_score"] * 0.24
            + float(profile.get("impact_score", 50)) * 0.17
            + float(profile.get("grant_fit_score", 50)) * 0.16
            + value_score * 0.10
            + blocked_value_score * 0.03
            + generated_bonus
            + proof_bonus
            + lane_generated_bonus
            + lane_proof_bonus
            + rolling_bonus
            - safety_penalty
        )
        market_boundary = lane == "market_signal_geometry"
        ready_for_live = bool(generated_hit and live_backed_generated > 0 and False)
        if generated_hit:
            evidence_status = "generated_software_benchmark_only_needs_live_replay"
        elif proof_hit:
            evidence_status = "proof_value_candidate_not_performance_claim"
        elif fit["live_measured_sources"]:
            evidence_status = "live_breadth_source_available_needs_lane_replay"
        else:
            evidence_status = "registry_ready_needs_live_adapter"
        if rolling_status == "rolling_champion":
            evidence_status = "repeat_rolling_champion_claim_still_needs_field_validation"
        elif rolling_status == "triple_source_candidate":
            evidence_status = "triple_source_live_candidate_needs_repeat_run"
        elif rolling_status == "single_run_candidate":
            evidence_status = "single_run_candidate_needs_more_sources_or_repeat"
        claim_boundary = (
            "Paper/read-only market calibration only; not trading profit, investment advice, live execution performance, or a grant value claim."
            if market_boundary
            else "Ranking shows proof-build priority only. It is not a live geometry win, field validation, realized savings, or government/customer ROI until the lane passes frozen live replay and claim gates."
        )
        row = {
            "family_id": family_id,
            "label": family.get("label", family_id),
            "lane": lane,
            "status": family.get("status", "unknown"),
            "readiness_score": ready,
            "impact_score": float(profile.get("impact_score", 50)),
            "grant_fit_score": float(profile.get("grant_fit_score", 50)),
            "live_source_fit_score": fit["live_source_fit_score"],
            "safe_annual_value_surface_usd": fit["safe_annual_value_surface_usd"],
            "blocked_context_annual_value_surface_usd": fit["blocked_context_annual_value_surface_usd"],
            "value_score": round(value_score, 3),
            "priority_score": round(max(0.0, min(100.0, score)), 3),
            "baselines": lane_meta.get("baselines", []),
            "metrics": lane_meta.get("metrics", []),
            "natural_logic": family.get("natural_logic", ""),
            "benchmark_hypothesis": family.get("benchmark_hypothesis", ""),
            "first_test": family.get("first_test", ""),
            "promotion_metric": family.get("promotion_metric", ""),
            "failure_mode": family.get("failure_mode", ""),
            "proof_asset": profile.get("proof_asset", ""),
            "target_assets": profile.get("target_assets", []),
            "target_live_sources": fit["target_sources"],
            "live_measured_sources": fit["live_measured_sources"],
            "context_only_sources": fit["context_only_sources"],
            "next_adapter": profile.get("next_adapter", ""),
            "grant_story": profile.get("grant_story", ""),
            "is_generated_lane_champion": bool(generated_hit),
            "is_proof_value_champion": bool(proof_hit),
            "rolling_gate_status": rolling_status,
            "rolling_gate_repeat_live_win_count": int(rolling_hit.get("repeat_live_win_count", 0) or 0),
            "rolling_gate_distinct_run_hash_count": int(rolling_hit.get("distinct_run_hash_count", 0) or 0),
            "rolling_gate_source_count": int(rolling_hit.get("source_count", 0) or 0),
            "rolling_gate_latest_score_delta_vs_named_baseline": rolling_hit.get("latest_score_delta_vs_named_baseline"),
            "rolling_gate_claim_language": rolling_hit.get("claim_language", ""),
            "generated_delta_vs_best_baseline": generated_hit.get("score_delta_vs_best_baseline") if generated_hit else None,
            "proof_priority_score": proof_hit.get("proof_priority_score") if proof_hit else None,
            "evidence_status": evidence_status,
            "ready_for_live_geometry_claim": ready_for_live,
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "market_safety": "paper_only_no_profit_claim" if market_boundary else "not_market_lane",
            "claim_boundary": claim_boundary,
        }
        rows.append(row)

    rows.sort(key=lambda item: (-float(item["priority_score"]), str(item["lane"]), str(item["family_id"])))
    for rank, row in enumerate(rows, start=1):
        row["overall_rank"] = rank
    return rows


def lane_leaderboard(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    leaders: dict[str, dict[str, Any]] = {}
    for row in rows:
        lane = str(row["lane"])
        if lane not in leaders or float(row["priority_score"]) > float(leaders[lane]["priority_score"]):
            leaders[lane] = row
    result = []
    for lane, row in leaders.items():
        result.append(
            {
                "lane": lane,
                "leader_family_id": row["family_id"],
                "leader_label": row["label"],
                "priority_score": row["priority_score"],
                "safe_annual_value_surface_usd": row["safe_annual_value_surface_usd"],
                "blocked_context_annual_value_surface_usd": row["blocked_context_annual_value_surface_usd"],
                "live_measured_sources": row["live_measured_sources"],
                "target_assets": row["target_assets"],
                "claim_boundary": row["claim_boundary"],
            }
        )
    result.sort(key=lambda item: (-float(item["priority_score"]), str(item["lane"])))
    for rank, row in enumerate(result, start=1):
        row["lane_rank"] = rank
    return result


def select_first(rows: list[dict[str, Any]], predicate) -> dict[str, Any]:
    for row in rows:
        if predicate(row):
            return row
    return rows[0] if rows else {}


def top_next_runs(rows: list[dict[str, Any]], frontier: dict[str, Any]) -> list[dict[str, Any]]:
    generated = frontier.get("champion_board", {}).get("generated_benchmark_champion", {})
    generated_family = generated.get("family", "") if isinstance(generated, dict) else ""
    by_id = {row["family_id"]: row for row in rows}
    rolling_picks = [
        row
        for row in rows
        if row.get("rolling_gate_status") in {"rolling_champion", "triple_source_candidate", "single_run_candidate"}
    ]
    rolling_picks.sort(
        key=lambda row: (
            {"rolling_champion": 0, "triple_source_candidate": 1, "single_run_candidate": 2}.get(
                str(row.get("rolling_gate_status", "")),
                9,
            ),
            -float(row.get("priority_score", 0) or 0),
        )
    )
    picks = [
        by_id.get(generated_family),
        *rolling_picks[:4],
        select_first(rows, lambda row: row["lane"] == "wave_resonance_timing" and row["family_id"] == "kuramoto_phase_coupling"),
        select_first(rows, lambda row: row["lane"] == "thermal_ventilation"),
        select_first(rows, lambda row: row["lane"] == "branching_transport" and row["family_id"] == "crack_propagation_paths"),
        select_first(rows, lambda row: row["lane"] == "time_series_model_routing"),
        select_first(rows, lambda row: row["lane"] == "market_signal_geometry"),
    ]
    seen = set()
    run_rows = []
    for pick in picks:
        if not pick or pick["family_id"] in seen:
            continue
        seen.add(pick["family_id"])
        run_rows.append(
            {
                "run_rank": len(run_rows) + 1,
                "family_id": pick["family_id"],
                "lane": pick["lane"],
                "run_name": f"{pick['lane']}::{pick['family_id']}::live_breadth_replay_v1",
                "why_now": (
                    "Strict rolling gate says this is the strongest candidate class to repeat next."
                    if pick.get("rolling_gate_status") in {"rolling_champion", "triple_source_candidate", "single_run_candidate"}
                    else "Generated champion needs live-breadth promotion."
                    if pick["is_generated_lane_champion"]
                    else "High proof/value fit and live sources are available for adapter work."
                ),
                "rolling_gate_status": pick.get("rolling_gate_status", "not_in_rolling_gate"),
                "rolling_gate_repeat_live_win_count": pick.get("rolling_gate_repeat_live_win_count", 0),
                "target_live_sources": pick["target_live_sources"],
                "live_measured_sources": pick["live_measured_sources"],
                "baselines": pick["baselines"],
                "metrics": pick["metrics"],
                "first_test": pick["first_test"],
                "next_adapter": pick["next_adapter"],
                "claim_gate": {
                    "ready_for_live_geometry_claim": False,
                    "ready_for_real_dollar_claim": False,
                    "kraken_live_execution_allowed": False,
                    "boundary": pick["claim_boundary"],
                },
            }
        )
    return run_rows


def build_queue() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    frontier = read_json(FRONTIER_JSON)
    value_meter = read_json(LIVE_VALUE_METER_JSON)
    live_panel = read_json(LIVE_BREADTH_PANEL_JSON)
    dollar_gate = read_json(DOLLAR_GATE_JSON)
    rolling_gate = read_json(ROLLING_GATE_JSON)
    rows = family_queue_rows(registry, frontier, value_meter, live_panel, dollar_gate, rolling_gate)
    leaders = lane_leaderboard(rows)
    rolling_indexes = rolling_gate_indexes(rolling_gate)
    live_value_gate = value_meter.get("value_gate", {}) if isinstance(value_meter.get("value_gate"), dict) else {}
    champion_board = frontier.get("champion_board", {}) if isinstance(frontier.get("champion_board"), dict) else {}
    generated_champion = champion_board.get("generated_benchmark_champion", {}) if isinstance(champion_board.get("generated_benchmark_champion"), dict) else {}
    proof_champion = champion_board.get("proof_value_champion", {}) if isinstance(champion_board.get("proof_value_champion"), dict) else {}
    fastest_adapter = select_first(rows, lambda row: bool(row["live_measured_sources"]) and row["lane"] != "market_signal_geometry")
    highest_blocked = max(rows, key=lambda row: float(row["blocked_context_annual_value_surface_usd"] or 0), default={})
    market_paper = select_first(rows, lambda row: row["lane"] == "market_signal_geometry")
    rolling_champion = rolling_indexes["rolling_champions"][0] if rolling_indexes["rolling_champions"] else {}
    queue = {
        "generated_utc": now_utc(),
        "schema": "geometry_live_breadth_proof_queue_v1",
        "purpose": "Rank every registered geometry family against live-breadth availability, proof value, grant fit, and safe claim gates.",
        "registry_health": {
            "family_count": len(registry.get("families", []) if isinstance(registry.get("families"), list) else []),
            "lane_count": len(registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}),
            "minimum_family_count": registry.get("minimum_family_count", 75),
            "core_rule": registry.get("core_rule", ""),
            "evidence_boundary": registry.get("evidence_boundary", ""),
        },
        "valuation_posture": {
            "safe_estimated_annual_value_usd": live_value_gate.get("allowed_estimated_annual_value_usd", 0),
            "safe_estimated_hourly_value_usd": live_value_gate.get("allowed_estimated_hourly_value_usd", 0),
            "blocked_context_only_annual_value_usd": live_value_gate.get("blocked_context_only_annual_value_usd", 0),
            "ready_for_real_dollar_claim": False,
            "boundary": "This is a proof-build and estimated-value surface, not company valuation, realized savings, revenue, or award certainty.",
        },
        "champions": {
            "generated_champion": {
                "family_id": generated_champion.get("family", ""),
                "lane": generated_champion.get("lane", ""),
                "status": generated_champion.get("status", "generated_lane_champion_not_live_claim"),
            },
            "proof_value_champion": {
                "family_id": proof_champion.get("family", ""),
                "lane": proof_champion.get("lane", ""),
                "status": proof_champion.get("status", "highest_funding_and_proof_priority_not_performance_winner"),
            },
            "fastest_live_breadth_adapter": {
                "family_id": fastest_adapter.get("family_id", ""),
                "lane": fastest_adapter.get("lane", ""),
                "live_measured_sources": fastest_adapter.get("live_measured_sources", []),
                "priority_score": fastest_adapter.get("priority_score", 0),
                "status": "best_next_adapter_candidate_not_live_geometry_claim",
            },
            "highest_blocked_context_value_target": {
                "family_id": highest_blocked.get("family_id", ""),
                "lane": highest_blocked.get("lane", ""),
                "blocked_context_annual_value_surface_usd": highest_blocked.get("blocked_context_annual_value_surface_usd", 0),
                "status": "large_context_target_needs_live_measured_source_before_claim",
            },
            "market_paper_champion": {
                "family_id": market_paper.get("family_id", ""),
                "lane": market_paper.get("lane", ""),
                "status": "paper_only_no_profit_claim",
            },
            "strict_rolling_champion": {
                "family_id": rolling_champion.get("family_id", ""),
                "lane": rolling_champion.get("lane", ""),
                "status": "rolling_champion_not_field_validated" if rolling_champion else "none",
                "repeat_live_win_count": rolling_champion.get("repeat_live_win_count", 0),
            },
            "rolling_champions": [
                {
                    "family_id": row.get("family_id", ""),
                    "lane": row.get("lane", ""),
                    "status": "rolling_champion_not_field_validated",
                    "repeat_live_win_count": row.get("repeat_live_win_count", 0),
                    "source_count": row.get("source_count", 0),
                }
                for row in rolling_indexes["rolling_champions"]
            ],
            "triple_source_rolling_champions": [
                {
                    "family_id": row.get("family_id", ""),
                    "lane": row.get("lane", ""),
                    "status": "triple_source_rolling_champion_not_field_validated",
                    "source_count": row.get("source_count", 0),
                    "repeat_live_win_count": row.get("repeat_live_win_count", 0),
                }
                for row in rolling_indexes["triple_source_rolling_champions"]
            ],
            "triple_source_candidates": [
                {
                    "family_id": row.get("family_id", ""),
                    "lane": row.get("lane", ""),
                    "source_count": row.get("source_count", 0),
                    "repeat_live_win_count": row.get("repeat_live_win_count", 0),
                }
                for row in rolling_indexes["triple_source_candidates"]
            ],
            "boundary": "Champion categories are separated; generated, live-adapter, proof-value, blocked-context, and market-paper titles are not interchangeable.",
        },
        "promotion_gate": {
            "ready_for_live_geometry_claim": any(row["ready_for_live_geometry_claim"] for row in rows),
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "families_ranked": len(rows),
            "live_geometry_winners": 0,
            "strict_rolling_champion_count": len(rolling_indexes["rolling_champions"]),
            "triple_source_rolling_champion_count": len(rolling_indexes["triple_source_rolling_champions"]),
            "triple_source_candidate_count": len(rolling_indexes["triple_source_candidates"]),
            "single_run_candidate_count": len(rolling_indexes["single_run_candidates"]),
            "rolling_gate_boundary": rolling_indexes["boundary"],
            "requirements": [
                "lane-specific live/public source windows",
                "frozen raw input manifest and SHA-256",
                "identical baselines on the same frozen windows",
                "holdout or walk-forward split",
                "uncertainty or paired comparison",
                "claim language bounded by the dollar and field-validation gates",
            ],
        },
        "lane_leaderboard": leaders,
        "top_next_runs": top_next_runs(rows, frontier),
        "family_queue": rows,
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_frontier": str(FRONTIER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_proof_value_meter": str(LIVE_VALUE_METER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_breadth_value_panel": str(LIVE_BREADTH_PANEL_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dollar_claim_gate": str(DOLLAR_GATE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "rolling_champion_gate": str(ROLLING_GATE_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    return queue


def render_markdown(queue: dict[str, Any]) -> str:
    posture = queue["valuation_posture"]
    champions = queue["champions"]
    lines = [
        "# Geometry Live-Breadth Proof Queue",
        "",
        f"Generated UTC: `{queue['generated_utc']}`",
        "",
        "## Why This Matters",
        "",
        "This board turns the geometry registry into a proof factory: every family is ranked by readiness, live-source fit, grant relevance, value surface, and claim safety.",
        "",
        "## Value Posture",
        "",
        f"- Safe estimated annual value surface: `{money(posture['safe_estimated_annual_value_usd'])}`",
        f"- Safe estimated hourly value surface: `{money(posture['safe_estimated_hourly_value_usd'])}`",
        f"- Blocked context-only annual surface: `{money(posture['blocked_context_only_annual_value_usd'])}`",
        f"- Ready for real-dollar claim: `{str(posture['ready_for_real_dollar_claim']).lower()}`",
        f"- Boundary: {posture['boundary']}",
        "",
        "## Champion Map",
        "",
        f"- Generated champion: `{champions['generated_champion']['family_id']}` on `{champions['generated_champion']['lane']}`",
        f"- Proof-value champion: `{champions['proof_value_champion']['family_id']}` on `{champions['proof_value_champion']['lane']}`",
        f"- Fastest live-breadth adapter: `{champions['fastest_live_breadth_adapter']['family_id']}` on `{champions['fastest_live_breadth_adapter']['lane']}`",
        f"- Highest blocked context target: `{champions['highest_blocked_context_value_target']['family_id']}` on `{champions['highest_blocked_context_value_target']['lane']}`",
        f"- Market paper champion: `{champions['market_paper_champion']['family_id']}`",
        f"- Strict rolling champion: `{champions['strict_rolling_champion']['family_id'] or 'none'}` on `{champions['strict_rolling_champion']['lane'] or 'none'}`",
        f"- Triple-source rolling champions: `{len(champions['triple_source_rolling_champions'])}`",
        f"- Triple-source candidates: `{len(champions['triple_source_candidates'])}`",
        f"- Boundary: {champions['boundary']}",
        "",
        "## Strict Rolling Gate",
        "",
        f"- Rolling champions: `{queue['promotion_gate']['strict_rolling_champion_count']}`",
        f"- Triple-source rolling champions: `{queue['promotion_gate']['triple_source_rolling_champion_count']}`",
        f"- Triple-source candidates: `{queue['promotion_gate']['triple_source_candidate_count']}`",
        f"- Single-run candidates: `{queue['promotion_gate']['single_run_candidate_count']}`",
        f"- Boundary: {queue['promotion_gate']['rolling_gate_boundary']}",
        "",
        "## Lane Leaders",
        "",
    ]
    for row in queue["lane_leaderboard"]:
        lines.append(
            f"- {row['lane_rank']}. `{row['lane']}` -> `{row['leader_family_id']}` "
            f"(score {row['priority_score']}, safe {money(row['safe_annual_value_surface_usd'])}, live sources {', '.join(row['live_measured_sources']) or 'none'})"
        )
    lines.extend(["", "## Top Next Runs", ""])
    for row in queue["top_next_runs"]:
        lines.append(
            f"- {row['run_rank']}. `{row['run_name']}`: {row['why_now']} "
            f"Rolling gate: `{row['rolling_gate_status']}`. "
            f"Baselines: {', '.join(row['baselines'])}. Metrics: {', '.join(row['metrics'])}."
        )
    lines.extend(["", "## Top 20 Family Queue", ""])
    for row in queue["family_queue"][:20]:
        lines.append(
            f"- {row['overall_rank']}. `{row['family_id']}` / `{row['lane']}`: "
            f"score {row['priority_score']} | status `{row['evidence_status']}` | rolling `{row['rolling_gate_status']}` | live `{', '.join(row['live_measured_sources']) or 'none'}`"
        )
    gate = queue["promotion_gate"]
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            f"- Families ranked: `{gate['families_ranked']}`",
            f"- Ready for live geometry claim: `{str(gate['ready_for_live_geometry_claim']).lower()}`",
            f"- Ready for real-dollar claim: `{str(gate['ready_for_real_dollar_claim']).lower()}`",
            f"- Kraken live execution allowed: `{str(gate['kraken_live_execution_allowed']).lower()}`",
            "- Requirements:",
        ]
    )
    lines.extend(f"  - {item}" for item in gate["requirements"])
    return "\n".join(lines)


def main() -> int:
    queue = build_queue()
    write_json(OUT_JSON, queue)
    write_json(DASHBOARD_JSON, queue)
    write_text(OUT_MD, render_markdown(queue))
    print(
        json.dumps(
            {
                "schema": queue["schema"],
                "families_ranked": queue["promotion_gate"]["families_ranked"],
                "generated_champion": queue["champions"]["generated_champion"]["family_id"],
                "fastest_live_adapter": queue["champions"]["fastest_live_breadth_adapter"]["family_id"],
                "safe_estimated_annual_value_usd": queue["valuation_posture"]["safe_estimated_annual_value_usd"],
                "ready_for_live_geometry_claim": queue["promotion_gate"]["ready_for_live_geometry_claim"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
