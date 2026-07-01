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
GEOMETRY_ROOT = ROOT / "out" / "geometry_championship_v1"
BRANCHING_TRANSPORT_LATEST = ROOT / "out" / "geometry_branching_transport" / "latest.json"
THERMAL_VENTILATION_LATEST = ROOT / "out" / "geometry_thermal_ventilation" / "latest.json"
OPTIMAL_CURVE_LATEST = ROOT / "out" / "geometry_optimal_curve_transport" / "latest.json"
WAVE_RESONANCE_LATEST = ROOT / "out" / "geometry_wave_resonance_timing" / "latest.json"

GEOMETRY_RUNNER_SCRIPTS: dict[str, str] = {
    "branching_transport": "code/geometry_branching_transport_benchmark.py",
    "thermal_ventilation": "code/geometry_thermal_ventilation_benchmark.py",
    "optimal_curve_transport": "code/geometry_optimal_curve_transport_benchmark.py",
    "wave_resonance_timing": "code/geometry_wave_resonance_timing_benchmark.py",
    "time_series_model_routing": "code/ops/BUILD_LIVE_BREADTH_REPLAY_BRIDGE.py",
}

TOP_LIVE_REPLAY_WIRING_LANES = (
    "optimal_curve_transport",
    "wave_resonance_timing",
    "branching_transport",
    "thermal_ventilation",
    "time_series_model_routing",
)

REGISTRY = CONFIG / "geometry_championship_v1_registry.json"
DOLLAR_CLAIM_GATE = OUT_OPS / "dollar_claim_gate_latest.json"
LIVE_BREADTH_KEY_GATE = OUT_OPS / "live_breadth_key_gate_latest.json"
LIVE_BREADTH_REPLAY_BRIDGE = OUT_OPS / "live_breadth_replay_bridge_latest.json"
LIVE_BREADTH_PROVENANCE_ANNEX = OUT_OPS / "grant_live_breadth_provenance_annex_latest.json"

OUT_JSON = OUT_OPS / "geometry_championship_bridge_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_championship_bridge.json"
OUT_MD = DOCS / "GEOMETRY_CHAMPIONSHIP_BRIDGE_2026-06-21.md"


LANE_PROOF_TARGETS: dict[str, dict[str, Any]] = {
    "branching_transport": {
        "impact_score": 98,
        "proof_asset": "Critical-infrastructure branching transport proof card",
        "funding_targets": ["DOE grid resilience", "DoD logistics/sensor mesh", "healthcare cold-chain"],
        "data_sources": ["EIA", "NREL", "NOAA", "public outage/proxy feeds"],
        "claim_lane": "critical_systems_estimated_value",
        "why": "Branching failures map cleanly to flow, delivery, resilience, and avoided-loss language.",
    },
    "thermal_ventilation": {
        "impact_score": 96,
        "proof_asset": "Datacenter cooling and uptime flowform proof card",
        "funding_targets": ["DOE datacenter energy", "critical infrastructure", "edge compute"],
        "data_sources": ["EIA", "NOAA weather", "public thermal/load proxies"],
        "claim_lane": "datacenter_cooling_uptime",
        "why": "Heat, pressure, and recovery-time deltas are easy for technical reviewers to value.",
    },
    "field_guided_control": {
        "impact_score": 94,
        "proof_asset": "Field-guided defense and maritime control proof card",
        "funding_targets": ["DoD sensor tasking", "maritime autonomy", "EMP/grid resilience"],
        "data_sources": ["NOAA AIS/weather", "NASA environment", "synthetic field stress tests"],
        "claim_lane": "defense_sensor_tasking",
        "why": "Field geometry can become routing, avoidance, and resilience evidence when paired with frozen baselines.",
    },
    "mission_network_routing": {
        "impact_score": 92,
        "proof_asset": "Mission routing and degraded-network proof card",
        "funding_targets": ["DICE", "DLA MissionWeave", "cyber/DLP routing"],
        "data_sources": ["public graph benchmarks", "event-stream replay", "grant live-breadth feeds"],
        "claim_lane": "mission_network_routing",
        "why": "Routing under dropout is a direct fit for adaptive orchestration claims.",
    },
    "time_series_model_routing": {
        "impact_score": 88,
        "proof_asset": "Live-breadth forecasting and regime-drift proof card",
        "funding_targets": ["grid forecasting", "market paper lab", "cyber anomaly triage"],
        "data_sources": ["FRED", "EIA", "NOAA", "Kraken public market data"],
        "claim_lane": "live_breadth_forecast",
        "why": "Time-series lanes convert live breadth into measurable forecast and abstention gates.",
    },
    "wave_resonance_timing": {
        "impact_score": 86,
        "proof_asset": "Oscillatory systems and harmonic timing proof card",
        "funding_targets": ["Harmonic AI", "grid stability", "sensor timing"],
        "data_sources": ["phase-signal controls", "grid frequency proxies", "synthetic oscillatory stress tests"],
        "claim_lane": "harmonic_resonance_learning",
        "why": "This is the cleanest home for harmonic/backprop comparison on oscillatory systems.",
    },
    "optimal_curve_transport": {
        "impact_score": 84,
        "proof_asset": "Brachistochrone and optimal transport benchmark card",
        "funding_targets": ["robotics", "routing", "thermal/cabling layout"],
        "data_sources": ["frozen path-planning scenarios", "public robotics/path datasets"],
        "claim_lane": "optimal_curve_transport",
        "why": "Brachistochrone-style tests are visually explainable and mathematically grounded.",
    },
    "multi_agent_coordination": {
        "impact_score": 82,
        "proof_asset": "Multi-agent formation and swarm coordination proof card",
        "funding_targets": ["DoD sensor swarms", "robotics", "search and rescue"],
        "data_sources": ["synthetic swarm controls", "public robotics scenarios"],
        "claim_lane": "multi_agent_coordination",
        "why": "Formation and collision metrics make the win/loss story concrete.",
    },
    "packing_topology": {
        "impact_score": 80,
        "proof_asset": "Packing, topology, and hardware layout proof card",
        "funding_targets": ["hardware layout", "thermal design", "sensor placement"],
        "data_sources": ["layout simulations", "manufacturing/thermal constraints"],
        "claim_lane": "packing_topology",
        "why": "Packing wins can support hardware/visual claims after mechanical validation.",
    },
    "resource_aware_scheduling": {
        "impact_score": 78,
        "proof_asset": "Bounded wake and resource scheduling proof card",
        "funding_targets": ["edge compute", "low-power sensors", "resilience scheduling"],
        "data_sources": ["event replay", "energy budget scenarios"],
        "claim_lane": "resource_aware_scheduling",
        "why": "Energy and deadline metrics are practical for agency reviewers.",
    },
    "stability_diagnostic": {
        "impact_score": 72,
        "proof_asset": "Stability diagnostic and reviewer trust gate",
        "funding_targets": ["all submissions", "model governance", "red-team review"],
        "data_sources": ["all frozen benchmark outputs"],
        "claim_lane": "diagnostic_only",
        "why": "Diagnostics do not win lanes, but they make every promoted claim harder to dismiss.",
    },
    "market_signal_geometry": {
        "impact_score": 62,
        "proof_asset": "Market geometry paper-lab proof card",
        "funding_targets": ["paper alpha lab", "risk calibration", "private R&D only"],
        "data_sources": ["Kraken public/read-only data", "Polygon/Massive", "Alpaca paper", "Twelve Data"],
        "claim_lane": "paper_market_lab",
        "why": "Markets are fast feedback for geometry, but live profit and order execution remain blocked.",
        "live_execution_allowed": False,
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def latest_geometry_summary() -> dict[str, Any]:
    if not GEOMETRY_ROOT.exists():
        return {}
    for run_dir in sorted(
        [path for path in GEOMETRY_ROOT.iterdir() if path.is_dir()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ):
        payload = read_json(run_dir / "summary.json")
        if payload:
            payload["_run_dir"] = str(run_dir)
            return payload
    return {}


def family_lookup(registry: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families = registry.get("families", [])
    if not isinstance(families, list):
        return {}
    return {str(row.get("id")): row for row in families if isinstance(row, dict) and row.get("id")}


def lane_config(registry: dict[str, Any], lane: str) -> dict[str, Any]:
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    value = lanes.get(lane, {})
    return value if isinstance(value, dict) else {}


def native_candidate_for_lane(readiness: dict[str, Any], lane: str) -> dict[str, Any] | None:
    rankings = readiness.get("candidate_rankings", [])
    if not isinstance(rankings, list):
        return None
    for row in rankings:
        if not isinstance(row, dict):
            continue
        if str(row.get("lane", "")) != lane:
            continue
        if str(row.get("id", "")).startswith("beast_"):
            continue
        return row
    return None


def lane_rankings(readiness: dict[str, Any], registry: dict[str, Any]) -> list[dict[str, Any]]:
    champions = readiness.get("lane_candidate_champions", {})
    if not isinstance(champions, dict):
        champions = {}
    families = family_lookup(registry)
    rows: list[dict[str, Any]] = []
    for lane, champion in champions.items():
        if not isinstance(champion, dict):
            continue
        lane_id = str(lane)
        if str(champion.get("id", "")).startswith("beast_"):
            champion = native_candidate_for_lane(readiness, lane_id) or champion
        target = LANE_PROOF_TARGETS.get(lane_id, {})
        family = families.get(str(champion.get("id")), {})
        config = lane_config(registry, lane_id)
        readiness_score = float(champion.get("readiness_score", 0) or 0)
        impact_score = float(target.get("impact_score", 50) or 50)
        proof_priority_score = round((readiness_score * 0.45) + (impact_score * 0.55), 2)
        rows.append(
            {
                "lane": lane,
                "candidate_champion_id": champion.get("id"),
                "candidate_champion_label": champion.get("label"),
                "readiness_rank": champion.get("rank"),
                "readiness_score": readiness_score,
                "impact_score": impact_score,
                "proof_priority_score": proof_priority_score,
                "status": champion.get("status"),
                "benchmark_hypothesis": champion.get("benchmark_hypothesis", ""),
                "natural_logic": family.get("natural_logic", ""),
                "first_test": champion.get("first_test", ""),
                "promotion_metric": family.get("promotion_metric", ""),
                "failure_mode": family.get("failure_mode", ""),
                "baselines": config.get("baselines", []),
                "metrics": config.get("metrics", []),
                "proof_asset": target.get("proof_asset", f"{lane} proof card"),
                "funding_targets": target.get("funding_targets", []),
                "data_sources": target.get("data_sources", []),
                "claim_lane": target.get("claim_lane", lane),
                "why": target.get("why", ""),
                "live_execution_allowed": bool(target.get("live_execution_allowed", False)),
                "evidence_status": "candidate_champion_only_not_performance_claim",
            }
        )
    rows.sort(key=lambda row: (-row["proof_priority_score"], row["lane"]))
    for index, row in enumerate(rows, start=1):
        row["proof_priority_rank"] = index
    return rows


def top_family_queue(readiness: dict[str, Any], registry: dict[str, Any], limit: int = 1000) -> list[dict[str, Any]]:
    rankings = readiness.get("candidate_rankings", [])
    if not isinstance(rankings, list):
        return []
    families = family_lookup(registry)
    rows: list[dict[str, Any]] = []
    for row in rankings[:limit]:
        if not isinstance(row, dict):
            continue
        family = families.get(str(row.get("id")), {})
        lane = str(row.get("lane", ""))
        target = LANE_PROOF_TARGETS.get(lane, {})
        rows.append(
            {
                "overall_readiness_rank": row.get("rank"),
                "family_id": row.get("id"),
                "label": row.get("label"),
                "lane": lane,
                "readiness_score": row.get("readiness_score", 0),
                "proof_asset": target.get("proof_asset", f"{lane} proof card"),
                "first_test": row.get("first_test", ""),
                "benchmark_hypothesis": row.get("benchmark_hypothesis", ""),
                "promotion_metric": family.get("promotion_metric", ""),
                "evidence_status": "benchmark_priority_not_proven_winner",
            }
        )
    return rows


def branching_transport_benchmark_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    gate = payload.get("promotion_gate", {}) if isinstance(payload.get("promotion_gate"), dict) else {}
    claim_gate = payload.get("claim_gate", {}) if isinstance(payload.get("claim_gate"), dict) else {}
    best_geometry = gate.get("best_geometry", {}) if isinstance(gate.get("best_geometry"), dict) else {}
    best_baseline = gate.get("best_baseline", {}) if isinstance(gate.get("best_baseline"), dict) else {}
    validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
    return {
        "schema": payload.get("schema", ""),
        "run_dir": payload.get("run_dir", ""),
        "generated_utc": payload.get("generated_utc", ""),
        "lane": payload.get("lane", "branching_transport"),
        "evidence_boundary": payload.get("evidence_boundary", ""),
        "validation_scenario_count": validation.get("scenario_count", 0),
        "gate": gate.get("gate", ""),
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": gate.get("score_delta_vs_best_baseline", 0),
        "delivered_flow_delta_vs_best_baseline": gate.get("delivered_flow_delta_vs_best_baseline", 0),
        "failure_tolerance_delta_vs_best_baseline": gate.get("failure_tolerance_delta_vs_best_baseline", 0),
        "claim_language": gate.get("claim_language", ""),
        "claim_gate": claim_gate,
        "global_geometry_champion": False,
        "live_execution_allowed": False,
    }


def thermal_ventilation_benchmark_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    gate = payload.get("promotion_gate", {}) if isinstance(payload.get("promotion_gate"), dict) else {}
    claim_gate = payload.get("claim_gate", {}) if isinstance(payload.get("claim_gate"), dict) else {}
    best_geometry = gate.get("best_geometry", {}) if isinstance(gate.get("best_geometry"), dict) else {}
    best_baseline = gate.get("best_baseline", {}) if isinstance(gate.get("best_baseline"), dict) else {}
    validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
    return {
        "schema": payload.get("schema", ""),
        "run_dir": payload.get("run_dir", ""),
        "generated_utc": payload.get("generated_utc", ""),
        "lane": payload.get("lane", "thermal_ventilation"),
        "evidence_boundary": payload.get("evidence_boundary", ""),
        "validation_scenario_count": validation.get("scenario_count", 0),
        "gate": gate.get("gate", ""),
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": gate.get("score_delta_vs_best_baseline", 0),
        "temperature_uniformity_delta_vs_best_baseline": gate.get("temperature_uniformity_delta_vs_best_baseline", 0),
        "hotspot_recovery_delta_vs_best_baseline": gate.get("hotspot_recovery_delta_vs_best_baseline", 0),
        "energy_proxy_delta_vs_best_baseline": gate.get("energy_proxy_delta_vs_best_baseline", 0),
        "pressure_drop_delta_vs_best_baseline": gate.get("pressure_drop_delta_vs_best_baseline", 0),
        "claim_language": gate.get("claim_language", ""),
        "claim_gate": claim_gate,
        "global_geometry_champion": False,
        "live_execution_allowed": False,
    }


def optimal_curve_transport_benchmark_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    gate = payload.get("promotion_gate", {}) if isinstance(payload.get("promotion_gate"), dict) else {}
    claim_gate = payload.get("claim_gate", {}) if isinstance(payload.get("claim_gate"), dict) else {}
    best_geometry = gate.get("best_geometry", {}) if isinstance(gate.get("best_geometry"), dict) else {}
    best_baseline = gate.get("best_baseline", {}) if isinstance(gate.get("best_baseline"), dict) else {}
    validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
    return {
        "schema": payload.get("schema", ""),
        "run_dir": payload.get("run_dir", ""),
        "generated_utc": payload.get("generated_utc", ""),
        "lane": payload.get("lane", "optimal_curve_transport"),
        "evidence_boundary": payload.get("evidence_boundary", ""),
        "validation_scenario_count": validation.get("scenario_count", 0),
        "gate": gate.get("gate", ""),
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": gate.get("score_delta_vs_best_baseline", 0),
        "travel_time_delta_vs_best_baseline": gate.get("travel_time_delta_vs_best_baseline", 0),
        "path_energy_delta_vs_best_baseline": gate.get("path_energy_delta_vs_best_baseline", 0),
        "constraint_violation_delta_vs_best_baseline": gate.get("constraint_violation_delta_vs_best_baseline", 0),
        "smoothness_delta_vs_best_baseline": gate.get("smoothness_delta_vs_best_baseline", 0),
        "claim_language": gate.get("claim_language", ""),
        "claim_gate": claim_gate,
        "global_geometry_champion": False,
        "live_execution_allowed": False,
    }


def wave_resonance_timing_benchmark_summary(payload: dict[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    gate = payload.get("promotion_gate", {}) if isinstance(payload.get("promotion_gate"), dict) else {}
    claim_gate = payload.get("claim_gate", {}) if isinstance(payload.get("claim_gate"), dict) else {}
    best_geometry = gate.get("best_geometry", {}) if isinstance(gate.get("best_geometry"), dict) else {}
    best_baseline = gate.get("best_baseline", {}) if isinstance(gate.get("best_baseline"), dict) else {}
    validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
    return {
        "schema": payload.get("schema", ""),
        "run_dir": payload.get("run_dir", ""),
        "generated_utc": payload.get("generated_utc", ""),
        "lane": payload.get("lane", "wave_resonance_timing"),
        "evidence_boundary": payload.get("evidence_boundary", ""),
        "validation_scenario_count": validation.get("scenario_count", 0),
        "gate": gate.get("gate", ""),
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": gate.get("score_delta_vs_best_baseline", 0),
        "phase_error_delta_vs_best_baseline": gate.get("phase_error_delta_vs_best_baseline", 0),
        "noise_rejection_delta_vs_best_baseline": gate.get("noise_rejection_delta_vs_best_baseline", 0),
        "forecast_error_delta_vs_best_baseline": gate.get("forecast_error_delta_vs_best_baseline", 0),
        "stability_margin_delta_vs_best_baseline": gate.get("stability_margin_delta_vs_best_baseline", 0),
        "claim_language": gate.get("claim_language", ""),
        "claim_gate": claim_gate,
        "global_geometry_champion": False,
        "live_execution_allowed": False,
    }


def generated_lane_benchmark_rankings(*benchmarks: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        if not benchmark:
            continue
        geometry = benchmark.get("best_geometry", {}) if isinstance(benchmark.get("best_geometry"), dict) else {}
        baseline = benchmark.get("best_baseline", {}) if isinstance(benchmark.get("best_baseline"), dict) else {}
        claim_gate = benchmark.get("claim_gate", {}) if isinstance(benchmark.get("claim_gate"), dict) else {}
        rows.append(
            {
                "lane": benchmark.get("lane", ""),
                "gate": benchmark.get("gate", ""),
                "best_geometry": geometry.get("strategy", ""),
                "best_geometry_family_id": geometry.get("family_id", ""),
                "best_baseline": baseline.get("strategy", ""),
                "validation_scenario_count": benchmark.get("validation_scenario_count", 0),
                "score_delta_vs_best_baseline": benchmark.get("score_delta_vs_best_baseline", 0),
                "claim_language": benchmark.get("claim_language", ""),
                "field_validation": bool(claim_gate.get("field_validation", False)),
                "real_dollar_claim": bool(claim_gate.get("real_dollar_claim", False)),
                "live_execution_allowed": bool(benchmark.get("live_execution_allowed", False)),
                "evidence_status": "generated_lane_benchmark_not_field_validation",
            }
        )
    rows.sort(
        key=lambda row: (
            row["gate"] != "candidate_geometry_beats_best_baseline",
            -float(row["score_delta_vs_best_baseline"] or 0),
            str(row["lane"]),
        )
    )
    for index, row in enumerate(rows, start=1):
        row["generated_champion_rank"] = index
    return rows


def live_breadth_promotion_gate(
    generated_benchmarks: list[dict[str, Any]],
    key_gate: dict[str, Any],
    replay_bridge: dict[str, Any],
    provenance_annex: dict[str, Any],
) -> dict[str, Any]:
    key_summary = key_gate.get("summary", {}) if isinstance(key_gate.get("summary"), dict) else {}
    replay_claim_gate = (
        replay_bridge.get("claim_gate", {}) if isinstance(replay_bridge.get("claim_gate"), dict) else {}
    )
    provenance_claim_gate = (
        provenance_annex.get("claim_gate", {})
        if isinstance(provenance_annex.get("claim_gate"), dict)
        else {}
    )
    provenance_state = (
        provenance_annex.get("live_breadth_state", {})
        if isinstance(provenance_annex.get("live_breadth_state"), dict)
        else {}
    )
    live_backed_lanes: list[str] = []
    generated_lanes = [str(row.get("lane", "")) for row in generated_benchmarks if row.get("lane")]
    synthetic_only_lanes = [lane for lane in generated_lanes if lane not in live_backed_lanes]

    return {
        "gate": "live_breadth_not_yet_mapped_to_geometry_lanes",
        "configured_providers": int(key_summary.get("configured_providers") or 0),
        "live_execution_allowed": bool(key_summary.get("live_execution_allowed", False)),
        "live_breadth_artifacts_present": bool(replay_bridge) and bool(provenance_annex),
        "primary_evidence_mode": str(provenance_state.get("primary_evidence_mode") or ""),
        "measured_sources": int(provenance_state.get("measured_sources") or 0),
        "enabled_sources": int(provenance_state.get("enabled_sources") or 0),
        "live_measured_source_row_count": int(provenance_state.get("live_measured_source_row_count") or 0),
        "generated_geometry_lanes": generated_lanes,
        "live_breadth_backed_lanes": live_backed_lanes,
        "synthetic_only_lanes": synthetic_only_lanes,
        "ready_for_public_live_claim": False,
        "ready_for_commit_push_as_live_benchmark": False,
        "replay_bridge_boundary": str(replay_claim_gate.get("boundary") or ""),
        "provenance_boundary": str(provenance_claim_gate.get("boundary") or ""),
        "promotion_requirements": [
            "lane-specific live data source",
            "frozen raw input manifest and SHA-256",
            "replay seed, time window, and leakage-control declaration",
            "identical baselines run on the same frozen live windows",
            "uncertainty or holdout result strong enough to survive reviewer re-run",
            "claim language approved by the dollar/field/public-live gate",
        ],
        "commit_push_boundary": (
            "Do not commit, push, or present generated geometry lanes as live benchmarks until "
            "each promoted lane has a lane-specific live data source, frozen input manifest, "
            "replay seed/window, leakage controls, and metric comparison against baselines."
        ),
    }


def top_live_replay_wiring_cards(
    generated_benchmarks: list[dict[str, Any]],
    lane_rows: list[dict[str, Any]],
    live_gate: dict[str, Any],
) -> list[dict[str, Any]]:
    generated_by_lane = {str(row.get("lane", "")): row for row in generated_benchmarks if row.get("lane")}
    lane_by_id = {str(row.get("lane", "")): row for row in lane_rows if row.get("lane")}
    synthetic_only = set(live_gate.get("synthetic_only_lanes", []))
    live_backed = set(live_gate.get("live_breadth_backed_lanes", []))
    requirements = list(live_gate.get("promotion_requirements", []))
    cards: list[dict[str, Any]] = []

    for rank, lane in enumerate(TOP_LIVE_REPLAY_WIRING_LANES, start=1):
        generated = generated_by_lane.get(lane, {})
        lane_row = lane_by_id.get(lane, {})
        target = LANE_PROOF_TARGETS.get(lane, {})
        candidate_family_id = generated.get("best_geometry_family_id") or lane_row.get("candidate_champion_id", "")
        candidate_strategy = generated.get("best_geometry") or lane_row.get("candidate_champion_label", "")
        if lane in live_backed:
            live_status = "live_breadth_backed_pending_claim_gate"
        elif lane in synthetic_only:
            live_status = "synthetic_benchmark_needs_lane_specific_live_mapping"
        else:
            live_status = "needs_live_adapter_and_lane_benchmark"
        cards.append(
            {
                "wiring_rank": rank,
                "lane": lane,
                "runner_script": GEOMETRY_RUNNER_SCRIPTS.get(lane, ""),
                "candidate_family_id": candidate_family_id,
                "candidate_strategy": candidate_strategy,
                "best_baseline": generated.get("best_baseline", ""),
                "score_delta_vs_best_baseline": generated.get("score_delta_vs_best_baseline", 0),
                "validation_scenario_count": generated.get("validation_scenario_count", 0),
                "baselines": lane_row.get("baselines", []),
                "metrics": lane_row.get("metrics", []),
                "target_live_sources": target.get("data_sources", []),
                "funding_targets": target.get("funding_targets", []),
                "proof_asset": target.get("proof_asset", f"{lane} proof card"),
                "first_test": lane_row.get("first_test", ""),
                "live_breadth_status": live_status,
                "blocked_by": requirements,
                "unlock_evidence": [
                    "frozen lane-specific live input manifest",
                    "SHA-256 hashes for raw inputs, config, code commit, and outputs",
                    "same-window baseline comparison",
                    "holdout or walk-forward uncertainty interval",
                    "reviewer-safe claim language approved by the live/dollar gate",
                ],
                "claim_gate": {
                    "ready_for_public_live_claim": False,
                    "ready_for_commit_push_as_live_benchmark": False,
                    "real_dollar_claim": False,
                    "live_execution_allowed": False,
                },
            }
        )
    return cards


def build_payload() -> dict[str, Any]:
    registry = read_json(REGISTRY)
    geometry = latest_geometry_summary()
    branching_benchmark = branching_transport_benchmark_summary(read_json(BRANCHING_TRANSPORT_LATEST))
    thermal_benchmark = thermal_ventilation_benchmark_summary(read_json(THERMAL_VENTILATION_LATEST))
    optimal_benchmark = optimal_curve_transport_benchmark_summary(read_json(OPTIMAL_CURVE_LATEST))
    wave_benchmark = wave_resonance_timing_benchmark_summary(read_json(WAVE_RESONANCE_LATEST))
    generated_benchmarks = generated_lane_benchmark_rankings(branching_benchmark, thermal_benchmark, optimal_benchmark, wave_benchmark)
    generated_champion = generated_benchmarks[0] if generated_benchmarks else None
    readiness = geometry.get("readiness", {}) if isinstance(geometry.get("readiness"), dict) else {}
    dollar_gate = read_json(DOLLAR_CLAIM_GATE)
    key_gate = read_json(LIVE_BREADTH_KEY_GATE)
    replay_bridge = read_json(LIVE_BREADTH_REPLAY_BRIDGE)
    provenance_annex = read_json(LIVE_BREADTH_PROVENANCE_ANNEX)
    live_gate = live_breadth_promotion_gate(generated_benchmarks, key_gate, replay_bridge, provenance_annex)
    lane_rows = lane_rankings(readiness, registry)
    family_queue = top_family_queue(readiness, registry)
    wiring_cards = top_live_replay_wiring_cards(generated_benchmarks, lane_rows, live_gate)
    proof_champion = lane_rows[0] if lane_rows else None
    raw_champion = readiness.get("champion_of_champions_candidate")
    key_summary = key_gate.get("summary", {}) if isinstance(key_gate.get("summary"), dict) else {}
    dollar_summary = dollar_gate.get("summary", {}) if isinstance(dollar_gate.get("summary"), dict) else {}

    return {
        "generated_utc": now_utc(),
        "schema": "geometry_championship_bridge_v1",
        "purpose": "Turn the geometry registry into a ranked proof-building queue without pretending candidates are proven winners.",
        "source_run_dir": geometry.get("_run_dir", ""),
        "evidence_boundary": geometry.get(
            "evidence_boundary",
            "Candidate champion only. No performance claim until lane-specific frozen validation passes.",
        ),
        "summary": {
            "family_count": readiness.get("family_count", 0),
            "lane_count": readiness.get("lane_count", 0),
            "natural_logic_family_count": sum(1 for row in registry.get("families", []) if isinstance(row, dict) and row.get("natural_logic")),
            "benchmark_hypothesis_family_count": sum(1 for row in registry.get("families", []) if isinstance(row, dict) and row.get("benchmark_hypothesis")),
            "performance_results_generated": bool(readiness.get("performance_results_generated", False)),
            "performance_champion": readiness.get("performance_champion"),
            "branching_transport_benchmark_generated": bool(branching_benchmark),
            "branching_transport_gate": branching_benchmark.get("gate", ""),
            "branching_transport_best_geometry": branching_benchmark.get("best_geometry", {}).get("strategy", "")
            if isinstance(branching_benchmark.get("best_geometry"), dict)
            else "",
            "branching_transport_best_baseline": branching_benchmark.get("best_baseline", {}).get("strategy", "")
            if isinstance(branching_benchmark.get("best_baseline"), dict)
            else "",
            "branching_transport_score_delta_vs_best_baseline": branching_benchmark.get("score_delta_vs_best_baseline", 0),
            "branching_transport_field_validation": False,
            "thermal_ventilation_benchmark_generated": bool(thermal_benchmark),
            "thermal_ventilation_gate": thermal_benchmark.get("gate", ""),
            "thermal_ventilation_best_geometry": thermal_benchmark.get("best_geometry", {}).get("strategy", "")
            if isinstance(thermal_benchmark.get("best_geometry"), dict)
            else "",
            "thermal_ventilation_best_baseline": thermal_benchmark.get("best_baseline", {}).get("strategy", "")
            if isinstance(thermal_benchmark.get("best_baseline"), dict)
            else "",
            "thermal_ventilation_score_delta_vs_best_baseline": thermal_benchmark.get("score_delta_vs_best_baseline", 0),
            "thermal_ventilation_field_validation": False,
            "optimal_curve_transport_benchmark_generated": bool(optimal_benchmark),
            "optimal_curve_transport_gate": optimal_benchmark.get("gate", ""),
            "optimal_curve_transport_best_geometry": optimal_benchmark.get("best_geometry", {}).get("strategy", "")
            if isinstance(optimal_benchmark.get("best_geometry"), dict)
            else "",
            "optimal_curve_transport_best_baseline": optimal_benchmark.get("best_baseline", {}).get("strategy", "")
            if isinstance(optimal_benchmark.get("best_baseline"), dict)
            else "",
            "optimal_curve_transport_score_delta_vs_best_baseline": optimal_benchmark.get("score_delta_vs_best_baseline", 0),
            "optimal_curve_transport_field_validation": False,
            "wave_resonance_timing_benchmark_generated": bool(wave_benchmark),
            "wave_resonance_timing_gate": wave_benchmark.get("gate", ""),
            "wave_resonance_timing_best_geometry": wave_benchmark.get("best_geometry", {}).get("strategy", "")
            if isinstance(wave_benchmark.get("best_geometry"), dict)
            else "",
            "wave_resonance_timing_best_baseline": wave_benchmark.get("best_baseline", {}).get("strategy", "")
            if isinstance(wave_benchmark.get("best_baseline"), dict)
            else "",
            "wave_resonance_timing_score_delta_vs_best_baseline": wave_benchmark.get("score_delta_vs_best_baseline", 0),
            "wave_resonance_timing_field_validation": False,
            "generated_lane_benchmark_count": len(generated_benchmarks),
            "generated_champion_lane": generated_champion.get("lane") if generated_champion else "",
            "generated_champion_family": generated_champion.get("best_geometry_family_id") if generated_champion else "",
            "generated_champion_strategy": generated_champion.get("best_geometry") if generated_champion else "",
            "generated_champion_score_delta_vs_best_baseline": generated_champion.get("score_delta_vs_best_baseline") if generated_champion else 0,
            "top_live_replay_wiring_card_count": len(wiring_cards),
            "claim_gate_passed": bool(readiness.get("claim_gate_passed", False)),
            "proof_champion_lane": proof_champion.get("lane") if proof_champion else "",
            "proof_champion_family": proof_champion.get("candidate_champion_id") if proof_champion else "",
            "raw_readiness_champion_family": raw_champion.get("id") if isinstance(raw_champion, dict) else "",
            "allowed_estimated_hourly_value_usd": dollar_summary.get("allowed_estimated_hourly_value_usd", 0),
            "allowed_estimated_annual_value_usd": dollar_summary.get("allowed_estimated_annual_value_usd", 0),
            "live_breadth_configured_providers": key_summary.get("configured_providers", 0),
            "live_breadth_backed_generated_lanes": len(live_gate["live_breadth_backed_lanes"]),
            "synthetic_only_generated_lanes": len(live_gate["synthetic_only_lanes"]),
            "ready_for_commit_push_as_live_benchmark": live_gate["ready_for_commit_push_as_live_benchmark"],
            "kraken_live_execution_allowed": False,
        },
        "proof_build_champion": proof_champion,
        "raw_readiness_champion": raw_champion if isinstance(raw_champion, dict) else None,
        "branching_transport_benchmark": branching_benchmark,
        "thermal_ventilation_benchmark": thermal_benchmark,
        "optimal_curve_transport_benchmark": optimal_benchmark,
        "wave_resonance_timing_benchmark": wave_benchmark,
        "generated_lane_benchmarks": generated_benchmarks,
        "generated_champion_of_champions": generated_champion,
        "live_breadth_promotion_gate": live_gate,
        "top_live_replay_wiring_cards": wiring_cards,
        "lane_champion_rankings": lane_rows,
        "top_family_benchmark_queue": family_queue,
        "champion_of_champions_policy": [
            "Raw readiness champion is the next technically prepared family by registry score.",
            "Proof-build champion is the best current funding/proof target after impact weighting.",
            "Neither is a performance winner until a frozen lane benchmark beats baselines with uncertainty bounds.",
            "Kraken/market geometry can rank as a paper-lab benchmark only; no live trades, order placement, withdrawals, or investment claims are authorized.",
        ],
        "asset_wiring": [
            "Select lane champion and freeze scenario/data source.",
            "Run budget-matched baselines listed in the registry lane.",
            "Run the candidate geometry under identical split, cost, and runtime constraints.",
            "Hash raw input, config, code commit, output metrics, and rendered scorecard.",
            "Promote only if validation beats baselines and the dollar/claim gate permits the language.",
            "Translate promoted deltas into grant, contract, pilot, or licensing proof cards.",
        ],
        "kraken_policy": {
            "signed_in_site_control": "not_authorized_for_trading",
            "allowed": ["read_only_public_market_data", "read_only_account_review_if_user_requests_specific_screen", "paper_replay", "validate_only_orders_without_submission"],
            "blocked": ["live_order_placement", "withdrawals", "margin_or_leverage_changes", "autonomous_trade_execution", "profit_claims"],
        },
        "inputs": {
            "registry": str(REGISTRY),
            "geometry_root": str(GEOMETRY_ROOT),
            "branching_transport_latest": str(BRANCHING_TRANSPORT_LATEST),
            "thermal_ventilation_latest": str(THERMAL_VENTILATION_LATEST),
            "optimal_curve_transport_latest": str(OPTIMAL_CURVE_LATEST),
            "wave_resonance_timing_latest": str(WAVE_RESONANCE_LATEST),
            "dollar_claim_gate": str(DOLLAR_CLAIM_GATE),
            "live_breadth_key_gate": str(LIVE_BREADTH_KEY_GATE),
            "live_breadth_replay_bridge": str(LIVE_BREADTH_REPLAY_BRIDGE),
            "live_breadth_provenance_annex": str(LIVE_BREADTH_PROVENANCE_ANNEX),
        },
    }


def money(value: Any) -> str:
    try:
        return f"${float(value):,.2f}"
    except Exception:
        return "$0.00"


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Championship Bridge",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## What This Is",
        "",
        (
            "This bridge ranks the current geometry registry into proof-building priorities. "
            "It does not claim that any geometry has won a live benchmark yet."
        ),
        "",
        "## Summary",
        "",
        f"- Families registered: {summary['family_count']}",
        f"- Families with natural logic: {summary['natural_logic_family_count']}",
        f"- Families with benchmark hypotheses: {summary['benchmark_hypothesis_family_count']}",
        f"- Lanes registered: {summary['lane_count']}",
        f"- Performance results generated: `{str(summary['performance_results_generated']).lower()}`",
        f"- Performance champion: `{summary['performance_champion']}`",
        f"- Branching benchmark generated: `{str(summary['branching_transport_benchmark_generated']).lower()}`",
        f"- Branching benchmark gate: `{summary['branching_transport_gate']}`",
        f"- Branching benchmark best geometry: `{summary['branching_transport_best_geometry']}`",
        f"- Branching benchmark best baseline: `{summary['branching_transport_best_baseline']}`",
        f"- Branching benchmark score delta: {summary['branching_transport_score_delta_vs_best_baseline']}",
        f"- Branching field validation: `{str(summary['branching_transport_field_validation']).lower()}`",
        f"- Thermal benchmark generated: `{str(summary['thermal_ventilation_benchmark_generated']).lower()}`",
        f"- Thermal benchmark gate: `{summary['thermal_ventilation_gate']}`",
        f"- Thermal benchmark best geometry: `{summary['thermal_ventilation_best_geometry']}`",
        f"- Thermal benchmark best baseline: `{summary['thermal_ventilation_best_baseline']}`",
        f"- Thermal benchmark score delta: {summary['thermal_ventilation_score_delta_vs_best_baseline']}",
        f"- Thermal field validation: `{str(summary['thermal_ventilation_field_validation']).lower()}`",
        f"- Optimal curve benchmark generated: `{str(summary['optimal_curve_transport_benchmark_generated']).lower()}`",
        f"- Optimal curve benchmark gate: `{summary['optimal_curve_transport_gate']}`",
        f"- Optimal curve benchmark best geometry: `{summary['optimal_curve_transport_best_geometry']}`",
        f"- Optimal curve benchmark best baseline: `{summary['optimal_curve_transport_best_baseline']}`",
        f"- Optimal curve benchmark score delta: {summary['optimal_curve_transport_score_delta_vs_best_baseline']}",
        f"- Optimal curve field validation: `{str(summary['optimal_curve_transport_field_validation']).lower()}`",
        f"- Wave resonance benchmark generated: `{str(summary['wave_resonance_timing_benchmark_generated']).lower()}`",
        f"- Wave resonance benchmark gate: `{summary['wave_resonance_timing_gate']}`",
        f"- Wave resonance benchmark best geometry: `{summary['wave_resonance_timing_best_geometry']}`",
        f"- Wave resonance benchmark best baseline: `{summary['wave_resonance_timing_best_baseline']}`",
        f"- Wave resonance benchmark score delta: {summary['wave_resonance_timing_score_delta_vs_best_baseline']}",
        f"- Wave resonance field validation: `{str(summary['wave_resonance_timing_field_validation']).lower()}`",
        f"- Generated champion lane: `{summary['generated_champion_lane']}`",
        f"- Generated champion strategy: `{summary['generated_champion_strategy']}`",
        f"- Live-breadth-backed generated lanes: {summary['live_breadth_backed_generated_lanes']}",
        f"- Synthetic-only generated lanes: {summary['synthetic_only_generated_lanes']}",
        f"- Ready to commit/push as live benchmark: `{str(summary['ready_for_commit_push_as_live_benchmark']).lower()}`",
        f"- Proof-build champion lane: `{summary['proof_champion_lane']}`",
        f"- Proof-build champion family: `{summary['proof_champion_family']}`",
        f"- Raw readiness champion family: `{summary['raw_readiness_champion_family']}`",
        f"- Claim-safe estimated value surface: {money(summary['allowed_estimated_hourly_value_usd'])}/hour; {money(summary['allowed_estimated_annual_value_usd'])}/year",
        f"- Kraken live execution allowed: `{str(summary['kraken_live_execution_allowed']).lower()}`",
        "- Boundary: Candidate champion only; no performance winner is claimed by this bridge.",
        "",
        "## Proof-Build Champion",
        "",
    ]
    champion = payload.get("proof_build_champion") or {}
    if champion:
        lines.extend(
            [
                f"- Lane: `{champion.get('lane')}`",
                f"- Candidate: `{champion.get('candidate_champion_label')}` (`{champion.get('candidate_champion_id')}`)",
                f"- Proof asset: {champion.get('proof_asset')}",
                f"- First test: `{champion.get('first_test')}`",
                f"- Baselines: {', '.join(champion.get('baselines', []))}",
                f"- Metrics: {', '.join(champion.get('metrics', []))}",
                f"- Boundary: {champion.get('evidence_status')}",
                "",
            ]
        )
    benchmark = payload.get("branching_transport_benchmark") or {}
    if benchmark:
        geometry = benchmark.get("best_geometry", {}) if isinstance(benchmark.get("best_geometry"), dict) else {}
        baseline = benchmark.get("best_baseline", {}) if isinstance(benchmark.get("best_baseline"), dict) else {}
        lines.extend(
            [
                "## Latest Branching Benchmark",
                "",
                f"- Run: `{benchmark.get('run_dir', '')}`",
                f"- Validation scenarios: {benchmark.get('validation_scenario_count', 0)}",
                f"- Best geometry: `{geometry.get('strategy', 'n/a')}`",
                f"- Best baseline: `{baseline.get('strategy', 'n/a')}`",
                f"- Gate: `{benchmark.get('gate', 'n/a')}`",
                f"- Score delta vs best baseline: {benchmark.get('score_delta_vs_best_baseline', 0)}",
                f"- Delivered-flow delta vs best baseline: {benchmark.get('delivered_flow_delta_vs_best_baseline', 0)}",
                f"- Failure-tolerance delta vs best baseline: {benchmark.get('failure_tolerance_delta_vs_best_baseline', 0)}",
                f"- Boundary: {benchmark.get('claim_language', '')}",
                "- Field/customer/real-dollar validation: `false`",
                "- Kraken/live execution authorization: `false`",
                "",
            ]
        )
    thermal = payload.get("thermal_ventilation_benchmark") or {}
    if thermal:
        geometry = thermal.get("best_geometry", {}) if isinstance(thermal.get("best_geometry"), dict) else {}
        baseline = thermal.get("best_baseline", {}) if isinstance(thermal.get("best_baseline"), dict) else {}
        claim_gate = thermal.get("claim_gate", {}) if isinstance(thermal.get("claim_gate"), dict) else {}
        lines.extend(
            [
                "## Latest Thermal Benchmark",
                "",
                f"- Run: `{thermal.get('run_dir', '')}`",
                f"- Validation scenarios: {thermal.get('validation_scenario_count', 0)}",
                f"- Best geometry: `{geometry.get('strategy', 'n/a')}`",
                f"- Best baseline: `{baseline.get('strategy', 'n/a')}`",
                f"- Gate: `{thermal.get('gate', 'n/a')}`",
                f"- Score delta vs best baseline: {thermal.get('score_delta_vs_best_baseline', 0)}",
                f"- Temperature-uniformity delta vs best baseline: {thermal.get('temperature_uniformity_delta_vs_best_baseline', 0)}",
                f"- Hotspot-recovery delta vs best baseline: {thermal.get('hotspot_recovery_delta_vs_best_baseline', 0)}",
                f"- Energy-proxy delta vs best baseline: {thermal.get('energy_proxy_delta_vs_best_baseline', 0)}",
                f"- Pressure-drop delta vs best baseline: {thermal.get('pressure_drop_delta_vs_best_baseline', 0)}",
                f"- Boundary: {thermal.get('claim_language', '')}",
                f"- CFD/datacenter/field/customer/real-dollar validation: `{str(bool(claim_gate.get('field_validation', False))).lower()}`",
                "- Kraken/live execution authorization: `false`",
                "",
            ]
        )
    optimal = payload.get("optimal_curve_transport_benchmark") or {}
    if optimal:
        geometry = optimal.get("best_geometry", {}) if isinstance(optimal.get("best_geometry"), dict) else {}
        baseline = optimal.get("best_baseline", {}) if isinstance(optimal.get("best_baseline"), dict) else {}
        claim_gate = optimal.get("claim_gate", {}) if isinstance(optimal.get("claim_gate"), dict) else {}
        lines.extend(
            [
                "## Latest Optimal Curve Benchmark",
                "",
                f"- Run: `{optimal.get('run_dir', '')}`",
                f"- Validation scenarios: {optimal.get('validation_scenario_count', 0)}",
                f"- Best geometry: `{geometry.get('strategy', 'n/a')}`",
                f"- Best baseline: `{baseline.get('strategy', 'n/a')}`",
                f"- Gate: `{optimal.get('gate', 'n/a')}`",
                f"- Score delta vs best baseline: {optimal.get('score_delta_vs_best_baseline', 0)}",
                f"- Travel-time delta vs best baseline: {optimal.get('travel_time_delta_vs_best_baseline', 0)}",
                f"- Energy-proxy delta vs best baseline: {optimal.get('path_energy_delta_vs_best_baseline', 0)}",
                f"- Constraint-violation delta vs best baseline: {optimal.get('constraint_violation_delta_vs_best_baseline', 0)}",
                f"- Smoothness delta vs best baseline: {optimal.get('smoothness_delta_vs_best_baseline', 0)}",
                f"- Boundary: {optimal.get('claim_language', '')}",
                f"- Robotics/cabling/field/trading/real-dollar validation: `{str(bool(claim_gate.get('field_validation', False))).lower()}`",
                "- Kraken/live execution authorization: `false`",
                "",
            ]
        )
    wave = payload.get("wave_resonance_timing_benchmark") or {}
    if wave:
        geometry = wave.get("best_geometry", {}) if isinstance(wave.get("best_geometry"), dict) else {}
        baseline = wave.get("best_baseline", {}) if isinstance(wave.get("best_baseline"), dict) else {}
        claim_gate = wave.get("claim_gate", {}) if isinstance(wave.get("claim_gate"), dict) else {}
        lines.extend(
            [
                "## Latest Wave Resonance Benchmark",
                "",
                f"- Run: `{wave.get('run_dir', '')}`",
                f"- Validation scenarios: {wave.get('validation_scenario_count', 0)}",
                f"- Best geometry: `{geometry.get('strategy', 'n/a')}`",
                f"- Best baseline: `{baseline.get('strategy', 'n/a')}`",
                f"- Gate: `{wave.get('gate', 'n/a')}`",
                f"- Score delta vs best baseline: {wave.get('score_delta_vs_best_baseline', 0)}",
                f"- Phase-error delta vs best baseline: {wave.get('phase_error_delta_vs_best_baseline', 0)}",
                f"- Noise-rejection delta vs best baseline: {wave.get('noise_rejection_delta_vs_best_baseline', 0)}",
                f"- Forecast-error delta vs best baseline: {wave.get('forecast_error_delta_vs_best_baseline', 0)}",
                f"- Stability-margin delta vs best baseline: {wave.get('stability_margin_delta_vs_best_baseline', 0)}",
                f"- Boundary: {wave.get('claim_language', '')}",
                f"- Grid/PLL/RF/medical/defense/field/trading/real-dollar validation: `{str(bool(claim_gate.get('field_validation', False))).lower()}`",
                "- Kraken/live execution authorization: `false`",
                "",
            ]
        )
    generated = payload.get("generated_lane_benchmarks") or []
    if generated:
        lines.extend(
            [
                "## Generated Champion-Of-Champions",
                "",
                "Generated-lane winner only. This is not a global, field, customer, safety, or real-dollar claim.",
                "",
                "| Rank | Lane | Winner | Baseline | Score Delta | Boundary |",
                "|---:|---|---|---|---:|---|",
            ]
        )
        for row in generated:
            lines.append(
                f"| {row.get('generated_champion_rank')} | {row.get('lane')} | `{row.get('best_geometry')}` | "
                f"`{row.get('best_baseline')}` | {row.get('score_delta_vs_best_baseline')} | {row.get('evidence_status')} |"
            )
        lines.append("")
    live_gate = payload.get("live_breadth_promotion_gate") or {}
    if live_gate:
        lines.extend(
            [
                "## Live Breadth Promotion Gate",
                "",
                f"- Gate: `{live_gate.get('gate', '')}`",
                f"- Live-breadth artifacts present: `{str(bool(live_gate.get('live_breadth_artifacts_present', False))).lower()}`",
                f"- Primary evidence mode: `{live_gate.get('primary_evidence_mode', '')}`",
                f"- Measured sources: {live_gate.get('measured_sources', 0)}/{live_gate.get('enabled_sources', 0)}",
                f"- Live-measured source rows: {live_gate.get('live_measured_source_row_count', 0)}",
                f"- Generated geometry lanes: {', '.join(live_gate.get('generated_geometry_lanes', []))}",
                f"- Live-breadth-backed lanes: {', '.join(live_gate.get('live_breadth_backed_lanes', [])) or 'none yet'}",
                f"- Synthetic-only lanes: {', '.join(live_gate.get('synthetic_only_lanes', [])) or 'none'}",
                f"- Ready for public live claim: `{str(bool(live_gate.get('ready_for_public_live_claim', False))).lower()}`",
                f"- Ready for commit/push as live benchmark: `{str(bool(live_gate.get('ready_for_commit_push_as_live_benchmark', False))).lower()}`",
                f"- Boundary: {live_gate.get('commit_push_boundary', '')}",
                "",
                "Promotion requirements:",
            ]
        )
        lines.extend(f"- {item}" for item in live_gate.get("promotion_requirements", []))
        lines.append("")
    wiring_cards = payload.get("top_live_replay_wiring_cards") or []
    if wiring_cards:
        lines.extend(
            [
                "## Top Live Replay Wiring Cards",
                "",
                "These are the first lanes to connect to live-breadth rows. They remain blocked from public live or dollar claims until the listed unlock evidence exists.",
                "",
                "| Rank | Lane | Candidate | Runner | Target Sources | Live Status |",
                "|---:|---|---|---|---|---|",
            ]
        )
        for card in wiring_cards:
            sources = ", ".join(card.get("target_live_sources", [])) or "needs source"
            lines.append(
                f"| {card.get('wiring_rank')} | {card.get('lane')} | `{card.get('candidate_family_id')}` | "
                f"`{card.get('runner_script')}` | {sources} | {card.get('live_breadth_status')} |"
            )
        lines.extend(["", "Unlock evidence required:"])
        for item in wiring_cards[0].get("unlock_evidence", []):
            lines.append(f"- {item}")
        lines.append("")
    lines.extend(
        [
            "## Lane Champion Rankings",
            "",
            "| Proof Rank | Lane | Candidate | Proof Asset | Score | First Test |",
            "|---:|---|---|---|---:|---|",
        ]
    )
    for row in payload["lane_champion_rankings"]:
        lines.append(
            f"| {row['proof_priority_rank']} | {row['lane']} | {row['candidate_champion_label']} | "
            f"{row['proof_asset']} | {row['proof_priority_score']} | `{row['first_test']}` |"
        )
    lines.extend(
        [
            "",
            "## Top Family Benchmark Queue",
            "",
            "| Readiness Rank | Family | Lane | First Test | Status |",
            "|---:|---|---|---|---|",
        ]
    )
    for row in payload["top_family_benchmark_queue"][:20]:
        lines.append(
            f"| {row['overall_readiness_rank']} | {row['label']} | {row['lane']} | "
            f"`{row['first_test']}` | {row['evidence_status']} |"
        )
    lines.extend(["", "## Champion Policy", ""])
    lines.extend(f"- {item}" for item in payload["champion_of_champions_policy"])
    lines.extend(["", "## Asset Wiring", ""])
    lines.extend(f"- {item}" for item in payload["asset_wiring"])
    return "\n".join(lines)


def write_outputs(payload: dict[str, Any]) -> None:
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    DASHBOARD_JSON.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT_MD.write_text(render_markdown(payload).rstrip() + "\n", encoding="utf-8")


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "proof_champion_lane": payload["summary"]["proof_champion_lane"],
                "proof_champion_family": payload["summary"]["proof_champion_family"],
                "kraken_live_execution_allowed": payload["summary"]["kraken_live_execution_allowed"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
