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

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
GEOMETRY_BRIDGE_JSON = OUT_OPS / "geometry_championship_bridge_latest.json"
DICE_LIVE_REPLAY_JSON = OUT_OPS / "dice_live_breadth_replay_latest.json"
HARBOR_AIS_INJECTION_JSON = OUT_OPS / "harbor_ais_injection_benchmark_latest.json"
LIVE_BREADTH_REPLAY_BRIDGE_JSON = OUT_OPS / "live_breadth_replay_bridge_latest.json"

OUT_JSON = OUT_OPS / "geometry_proof_frontier_board_latest.json"
OUT_MD = DOCS / "GEOMETRY_PROOF_FRONTIER_BOARD_2026-06-22.md"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_proof_frontier_board.json"


LANE_WIRING = {
    "optimal_curve_transport": {
        "proof_asset": "Brachistochrone optimal-curve proof card",
        "target_assets": [
            "frozen public path-planning maps",
            "layout/cabling/thermal path scenarios",
            "curvature, obstacle, drag, and runtime constraints",
        ],
        "first_adapter": "Freeze obstacle/path windows, run straight-line, spline, RRT*, minimum-jerk, and brachistochrone candidates on identical constraints.",
        "live_asset_fit_score": 70,
        "grant_fit_score": 72,
        "why": "It is the strongest generated lane delta and the easiest visual/math story to explain quickly.",
    },
    "wave_resonance_timing": {
        "proof_asset": "Harmonic timing and oscillatory-system proof card",
        "target_assets": [
            "EIA load or grid-stability proxy windows",
            "phase-window synthetic controls",
            "Kraken public time-series as stress controls only",
        ],
        "first_adapter": "Convert frozen oscillatory windows into phase-error tasks and compare FFT, Kalman, ARIMA, PLL, and Kuramoto candidates.",
        "live_asset_fit_score": 80,
        "grant_fit_score": 92,
        "why": "This is the cleanest lane for the harmonic/backprop thesis on oscillatory systems.",
    },
    "thermal_ventilation": {
        "proof_asset": "Datacenter cooling and thermal recovery proof card",
        "target_assets": [
            "EIA load windows",
            "NOAA ambient weather windows",
            "public datacenter cooling/load proxies if available",
        ],
        "first_adapter": "Map frozen load and ambient-temperature windows into thermal-grid replay, then compare straight duct, conventional HVAC, CFD reference, and thermal plume candidates.",
        "live_asset_fit_score": 75,
        "grant_fit_score": 90,
        "why": "Cooling, recovery time, pressure, and energy metrics translate cleanly into DOE/critical-infrastructure value language.",
    },
    "branching_transport": {
        "proof_asset": "Critical-infrastructure branching transport proof card",
        "target_assets": [
            "EIA grid/load windows",
            "NREL energy context",
            "NOAA disruption context",
            "public outage or proxy feeds",
        ],
        "first_adapter": "Convert live load/disruption windows into constrained flow networks and compare MST, Steiner, min-cost-flow, and branching candidates.",
        "live_asset_fit_score": 90,
        "grant_fit_score": 95,
        "why": "It has the strongest funding fit, but the current generated lane delta is still small and needs a stronger live-backed result.",
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


def registry_health(registry: dict[str, Any]) -> dict[str, Any]:
    families = registry.get("families", []) if isinstance(registry.get("families"), list) else []
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    status_counts: dict[str, int] = {}
    lane_counts: dict[str, int] = {}
    for row in families:
        if not isinstance(row, dict):
            continue
        status = str(row.get("status", "unknown"))
        lane = str(row.get("lane", "unknown"))
        status_counts[status] = status_counts.get(status, 0) + 1
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
    return {
        "schema": registry.get("schema", ""),
        "version": registry.get("version", 0),
        "core_rule": registry.get("core_rule", ""),
        "family_count": len(families),
        "lane_count": len(lanes),
        "natural_logic_family_count": sum(1 for row in families if isinstance(row, dict) and row.get("natural_logic")),
        "benchmark_hypothesis_family_count": sum(1 for row in families if isinstance(row, dict) and row.get("benchmark_hypothesis")),
        "status_counts": status_counts,
        "lane_counts": lane_counts,
        "cross_lane_ranking_allowed": bool(registry.get("cross_lane_ranking_allowed", False)),
        "boundary": registry.get("evidence_boundary", ""),
    }


def generated_frontier(bridge: dict[str, Any]) -> list[dict[str, Any]]:
    generated = bridge.get("generated_lane_benchmarks", [])
    if not isinstance(generated, list):
        return []
    max_delta = max([float(row.get("score_delta_vs_best_baseline", 0) or 0) for row in generated if isinstance(row, dict)] or [1.0])
    rows: list[dict[str, Any]] = []
    lane_rows = {
        str(row.get("lane")): row
        for row in bridge.get("lane_champion_rankings", [])
        if isinstance(row, dict) and row.get("lane")
    }
    for row in generated:
        if not isinstance(row, dict):
            continue
        lane = str(row.get("lane", ""))
        wiring = LANE_WIRING.get(lane, {})
        lane_rank = lane_rows.get(lane, {})
        delta = float(row.get("score_delta_vs_best_baseline", 0) or 0)
        delta_score = (delta / max_delta) * 100 if max_delta else 0
        impact_score = float(lane_rank.get("impact_score", 0) or 0)
        live_fit = float(wiring.get("live_asset_fit_score", 50) or 50)
        grant_fit = float(wiring.get("grant_fit_score", 50) or 50)
        frontier_score = round((delta_score * 0.40) + (impact_score * 0.30) + (live_fit * 0.20) + (grant_fit * 0.10), 3)
        rows.append(
            {
                "lane": lane,
                "best_geometry": row.get("best_geometry", ""),
                "best_geometry_family_id": row.get("best_geometry_family_id", ""),
                "best_baseline": row.get("best_baseline", ""),
                "generated_champion_rank": row.get("generated_champion_rank"),
                "validation_scenario_count": row.get("validation_scenario_count", 0),
                "score_delta_vs_best_baseline": delta,
                "impact_score": impact_score,
                "live_asset_fit_score": live_fit,
                "grant_fit_score": grant_fit,
                "frontier_score": frontier_score,
                "proof_asset": wiring.get("proof_asset", ""),
                "target_assets": wiring.get("target_assets", []),
                "first_adapter": wiring.get("first_adapter", ""),
                "why": wiring.get("why", ""),
                "ready_for_live_claim": False,
                "ready_for_real_dollar_claim": False,
                "kraken_live_execution_allowed": False,
                "evidence_status": "generated_software_benchmark_only",
            }
        )
    rows.sort(key=lambda item: (-float(item["frontier_score"]), str(item["lane"])))
    for index, row in enumerate(rows, start=1):
        row["live_wiring_rank"] = index
    return rows


def proof_value_frontier(bridge: dict[str, Any]) -> list[dict[str, Any]]:
    rows = bridge.get("lane_champion_rankings", [])
    if not isinstance(rows, list):
        return []
    cleaned: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cleaned.append(
            {
                "rank": row.get("proof_priority_rank"),
                "lane": row.get("lane", ""),
                "candidate_champion_id": row.get("candidate_champion_id", ""),
                "candidate_champion_label": row.get("candidate_champion_label", ""),
                "readiness_score": row.get("readiness_score", 0),
                "impact_score": row.get("impact_score", 0),
                "proof_priority_score": row.get("proof_priority_score", 0),
                "proof_asset": row.get("proof_asset", ""),
                "first_test": row.get("first_test", ""),
                "promotion_metric": row.get("promotion_metric", ""),
                "evidence_status": row.get("evidence_status", "candidate_champion_only_not_performance_claim"),
            }
        )
    cleaned.sort(key=lambda item: (int(item["rank"] or 9999), str(item["lane"])))
    return cleaned


def live_proof_champions(dice: dict[str, Any], harbor: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dice_sources = dice.get("source_manifest", {}).get("sources", [])
    paired = dice.get("paired_metrics", {}) if isinstance(dice.get("paired_metrics"), dict) else {}
    if isinstance(dice_sources, list) and dice_sources:
        rows.append(
            {
                "rank": 1,
                "name": "DICE live-breadth replay",
                "proof_type": "frozen_live_pulled_replay",
                "source_count": len(dice_sources),
                "scenario_count": dice.get("configuration", {}).get("scenario_count"),
                "primary_delta": paired.get("safe_completion_rate", {}).get("mean_delta"),
                "supporting_delta": paired.get("constraint_violation_rate", {}).get("mean_delta"),
                "claim_status": "proposal_specific_live_replay_not_field_validation",
                "ready_for_submit": bool(dice.get("claim_gate", {}).get("ready_for_submit", False)),
            }
        )
    result = harbor.get("controlled_injection_benchmark", {})
    if isinstance(result, dict) and result:
        rows.append(
            {
                "rank": len(rows) + 1,
                "name": "HarborSentinel public AIS controlled-injection",
                "proof_type": "public_heldout_data_controlled_injection",
                "source_count": 1,
                "scenario_count": result.get("total_injected_segments", 0),
                "primary_delta": result.get("recall_lift_vs_speed_only", 0),
                "supporting_delta": result.get("motion_consistency_recall", 0),
                "claim_status": "public_data_detector_vs_baseline_not_field_validation",
                "ready_for_submit": False,
            }
        )
    return rows


def available_live_assets(replay_bridge: dict[str, Any]) -> list[dict[str, Any]]:
    rollup = replay_bridge.get("live_breadth_rollup", {}) if isinstance(replay_bridge.get("live_breadth_rollup"), dict) else {}
    providers = rollup.get("providers", []) if isinstance(rollup.get("providers"), list) else []
    rows = []
    for provider in providers:
        if not isinstance(provider, dict):
            continue
        rows.append(
            {
                "provider": provider.get("provider", ""),
                "sector": provider.get("sector", ""),
                "rows": int(provider.get("rows", 0) or 0),
                "measured": bool(provider.get("measured", False)),
                "probe_ok": bool(provider.get("probe_ok", False)),
                "status": provider.get("status", ""),
            }
        )
    rows.sort(key=lambda item: (-int(item["rows"]), str(item["provider"])))
    return rows[:12]


def champion_board(bridge: dict[str, Any], live_champions: list[dict[str, Any]], wiring: list[dict[str, Any]]) -> dict[str, Any]:
    generated = bridge.get("generated_champion_of_champions", {})
    proof = bridge.get("proof_build_champion", {})
    raw = bridge.get("raw_readiness_champion", {})
    return {
        "generated_benchmark_champion": {
            "lane": generated.get("lane", "") if isinstance(generated, dict) else "",
            "family": generated.get("best_geometry", "") if isinstance(generated, dict) else "",
            "score_delta_vs_best_baseline": generated.get("score_delta_vs_best_baseline", 0) if isinstance(generated, dict) else 0,
            "status": "generated_lane_champion_not_live_claim",
        },
        "proof_value_champion": {
            "lane": proof.get("lane", "") if isinstance(proof, dict) else "",
            "family": proof.get("candidate_champion_id", "") if isinstance(proof, dict) else "",
            "proof_priority_score": proof.get("proof_priority_score", 0) if isinstance(proof, dict) else 0,
            "status": "highest_funding_and_proof_priority_not_performance_winner",
        },
        "raw_readiness_champion": {
            "lane": raw.get("lane", "") if isinstance(raw, dict) else "",
            "family": raw.get("id", "") if isinstance(raw, dict) else "",
            "readiness_score": raw.get("readiness_score", 0) if isinstance(raw, dict) else 0,
            "status": "registry_readiness_champion_not_performance_winner",
        },
        "live_proof_champion": live_champions[0] if live_champions else None,
        "recommended_next_live_wiring": wiring[0] if wiring else None,
        "boundary": "Champion titles are separated so generated software wins, proof-value priorities, and live-proof evidence are never conflated.",
    }


def build_board() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    bridge = read_json(GEOMETRY_BRIDGE_JSON)
    dice = read_json(DICE_LIVE_REPLAY_JSON)
    harbor = read_json(HARBOR_AIS_INJECTION_JSON)
    replay_bridge = read_json(LIVE_BREADTH_REPLAY_BRIDGE_JSON)

    generated = generated_frontier(bridge)
    proof = proof_value_frontier(bridge)
    live = live_proof_champions(dice, harbor)
    assets = available_live_assets(replay_bridge)
    champions = champion_board(bridge, live, generated)

    return {
        "generated_utc": now_utc(),
        "schema": "geometry_proof_frontier_board_v1",
        "purpose": "Rank geometry champions, champion-of-champions, live proof, and next wiring targets without overclaiming.",
        "registry_health": registry_health(registry),
        "champion_board": champions,
        "generated_benchmark_frontier": generated,
        "proof_value_frontier": proof,
        "current_live_proof_champions": live,
        "available_live_assets": assets,
        "promotion_gate": {
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "live_breadth_backed_generated_lanes": bridge.get("summary", {}).get("live_breadth_backed_generated_lanes", 0),
            "synthetic_only_generated_lanes": bridge.get("summary", {}).get("synthetic_only_generated_lanes", 0),
            "requirements": [
                "lane-specific live/public data source",
                "frozen raw input manifest and SHA-256",
                "replay seed, time window, and leakage-control declaration",
                "identical baselines on the same frozen windows",
                "holdout or walk-forward result strong enough for reviewer re-run",
                "claim language approved by field/dollar/public-live gate",
            ],
        },
        "most_valuable_proof_now": [
            "DICE live-breadth replay is the strongest proposal-specific live proof, but it is not field validation or DICE metric attainment.",
            "HarborSentinel public AIS controlled-injection is the strongest public held-out detector-vs-baseline proof, but it is not Navy field validation.",
            "Brachistochrone_descent is the strongest generated geometry winner by score delta, but it is not live-breadth backed yet.",
            "Branching/crack-propagation remains the highest proof-value lane for critical-infrastructure funding, but needs stronger live-backed validation.",
        ],
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_bridge": str(GEOMETRY_BRIDGE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dice_live_breadth_replay": str(DICE_LIVE_REPLAY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "harbor_ais_injection_benchmark": str(HARBOR_AIS_INJECTION_JSON.relative_to(ROOT)).replace("\\", "/"),
            "live_breadth_replay_bridge": str(LIVE_BREADTH_REPLAY_BRIDGE_JSON.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def render_markdown(board: dict[str, Any]) -> str:
    health = board["registry_health"]
    champions = board["champion_board"]
    lines = [
        "# Geometry Proof Frontier Board",
        "",
        f"Generated UTC: `{board['generated_utc']}`",
        "",
        "## Registry Health",
        "",
        f"- Families: {health['family_count']}",
        f"- Lanes: {health['lane_count']}",
        f"- Natural-logic families: {health['natural_logic_family_count']}",
        f"- Benchmark-hypothesis families: {health['benchmark_hypothesis_family_count']}",
        f"- Cross-lane ranking allowed by registry: `{str(health['cross_lane_ranking_allowed']).lower()}`",
        f"- Core rule: {health['core_rule']}",
        f"- Boundary: {health['boundary']}",
        "",
        "## Champion-Of-Champions",
        "",
        f"- Generated benchmark champion: `{champions['generated_benchmark_champion']['family']}` on `{champions['generated_benchmark_champion']['lane']}`; delta {champions['generated_benchmark_champion']['score_delta_vs_best_baseline']}",
        f"- Proof-value champion: `{champions['proof_value_champion']['family']}` on `{champions['proof_value_champion']['lane']}`; score {champions['proof_value_champion']['proof_priority_score']}",
        f"- Raw readiness champion: `{champions['raw_readiness_champion']['family']}` on `{champions['raw_readiness_champion']['lane']}`",
        f"- Live-proof champion: `{champions['live_proof_champion']['name'] if champions['live_proof_champion'] else 'none'}`",
        f"- Recommended next live wiring: `{champions['recommended_next_live_wiring']['lane'] if champions['recommended_next_live_wiring'] else 'none'}`",
        f"- Boundary: {champions['boundary']}",
        "",
        "## Generated Benchmark Frontier",
        "",
    ]
    for row in board["generated_benchmark_frontier"]:
        lines.extend(
            [
                f"### {row['live_wiring_rank']}. {row['lane']}",
                "",
                f"- Winner: `{row['best_geometry']}` vs `{row['best_baseline']}`",
                f"- Generated delta: {row['score_delta_vs_best_baseline']}",
                f"- Frontier score: {row['frontier_score']}",
                f"- Proof asset: {row['proof_asset']}",
                f"- First adapter: {row['first_adapter']}",
                f"- Ready for live claim: `{str(row['ready_for_live_claim']).lower()}`",
                f"- Kraken live execution allowed: `{str(row['kraken_live_execution_allowed']).lower()}`",
                "",
            ]
        )
    lines.extend(["## Proof-Value Frontier", ""])
    for row in board["proof_value_frontier"][:12]:
        lines.append(
            f"- {row['rank']}. `{row['lane']}` / `{row['candidate_champion_id']}`: "
            f"score {row['proof_priority_score']} | first test `{row['first_test']}` | status `{row['evidence_status']}`"
        )
    lines.extend(["", "## Current Live Proof Champions", ""])
    for row in board["current_live_proof_champions"]:
        lines.append(
            f"- {row['rank']}. {row['name']}: {row['proof_type']} | sources {row['source_count']} | scenarios {row['scenario_count']} | status `{row['claim_status']}`"
        )
    lines.extend(["", "## Available Live Assets", ""])
    for row in board["available_live_assets"][:8]:
        lines.append(
            f"- `{row['provider']}` / {row['sector']}: rows {row['rows']} | measured `{str(row['measured']).lower()}` | status `{row['status']}`"
        )
    gate = board["promotion_gate"]
    lines.extend(
        [
            "",
            "## Promotion Gate",
            "",
            f"- Ready for live geometry claim: `{str(gate['ready_for_live_geometry_claim']).lower()}`",
            f"- Ready for real-dollar claim: `{str(gate['ready_for_real_dollar_claim']).lower()}`",
            f"- Kraken live execution allowed: `{str(gate['kraken_live_execution_allowed']).lower()}`",
            f"- Live-breadth-backed generated lanes: {gate['live_breadth_backed_generated_lanes']}",
            f"- Synthetic-only generated lanes: {gate['synthetic_only_generated_lanes']}",
            "- Requirements:",
        ]
    )
    lines.extend(f"  - {item}" for item in gate["requirements"])
    lines.extend(["", "## Most Valuable Proof Now", ""])
    lines.extend(f"- {item}" for item in board["most_valuable_proof_now"])
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    board = build_board()
    write_json(OUT_JSON, board)
    write_json(DASHBOARD_JSON, board)
    write_text(OUT_MD, render_markdown(board))
    print(
        json.dumps(
            {
                "schema": board["schema"],
                "family_count": board["registry_health"]["family_count"],
                "generated_champion": board["champion_board"]["generated_benchmark_champion"]["family"],
                "proof_value_champion": board["champion_board"]["proof_value_champion"]["family"],
                "next_live_wiring": board["champion_board"]["recommended_next_live_wiring"]["lane"]
                if board["champion_board"]["recommended_next_live_wiring"]
                else "",
                "ready_for_live_geometry_claim": board["promotion_gate"]["ready_for_live_geometry_claim"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
