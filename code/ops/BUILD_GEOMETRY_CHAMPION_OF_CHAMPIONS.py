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
MATRIX_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"
FRONTIER_JSON = OUT_OPS / "geometry_proof_frontier_board_latest.json"
REVIEWER_GATE_JSON = OUT_OPS / "reviewer_evidence_gate_latest.json"
QUEUE_JSON = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"

OUT_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_champion_of_champions.json"
OUT_MD = DOCS / "GEOMETRY_CHAMPION_OF_CHAMPIONS_2026-06-23.md"


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


def norm_id(value: Any) -> str:
    return str(value or "").strip()


def norm_source(value: Any) -> str:
    return str(value or "").strip().upper()


def registry_families(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = registry.get("families", [])
    return [row for row in rows if isinstance(row, dict)]


def registry_lanes(registry: dict[str, Any]) -> dict[str, Any]:
    lanes = registry.get("lanes", {})
    return lanes if isinstance(lanes, dict) else {}


def matrix_rows(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = matrix.get("matrix", [])
    if not isinstance(rows, list) or not rows:
        rows = matrix.get("priority_queue", [])
    return [row for row in rows if isinstance(row, dict)]


def reviewer_blocked_sources(gate: dict[str, Any]) -> list[str]:
    quarantine = gate.get("quarantine", {})
    rows = quarantine.get("blocked_or_thin_sources", []) if isinstance(quarantine, dict) else []
    names = [norm_source(row.get("source")) for row in rows if isinstance(row, dict)]
    return [name for name in names if name]


def measured_source_count(row: dict[str, Any]) -> int:
    return len([item for item in row.get("measured_sources", []) if isinstance(item, dict)])


def measured_row_count(row: dict[str, Any]) -> int:
    total = 0
    for item in row.get("measured_sources", []):
        if isinstance(item, dict):
            total += int(item.get("rows", 0) or 0)
    return total


def hash_count(row: dict[str, Any]) -> int:
    return len(
        [
            item
            for item in row.get("measured_sources", [])
            if isinstance(item, dict) and item.get("snapshot_sha256")
        ]
    )


def blocked_source_names(row: dict[str, Any]) -> list[str]:
    return [
        norm_source(item.get("source"))
        for item in row.get("blocked_sources", [])
        if isinstance(item, dict) and item.get("source")
    ]


def critical_blocker_count(row: dict[str, Any]) -> int:
    critical = {norm_source(item) for item in row.get("critical_sources", [])}
    return len([name for name in blocked_source_names(row) if name in critical])


def generated_delta(row: dict[str, Any]) -> float:
    generated = row.get("generated_champion", {})
    if not isinstance(generated, dict):
        return 0.0
    return float(generated.get("score_delta_vs_best_baseline", 0.0) or 0.0)


def proof_score(row: dict[str, Any]) -> float:
    proof = row.get("proof_value_champion", {})
    if not isinstance(proof, dict):
        return 0.0
    return float(proof.get("proof_priority_score", 0.0) or 0.0)


def lane_operational_score(row: dict[str, Any]) -> float:
    live_wiring = float(row.get("live_wiring_score", 0.0) or 0.0)
    score = (
        live_wiring
        + proof_score(row) * 0.40
        + min(generated_delta(row) * 100.0, 25.0)
        + measured_source_count(row) * 2.0
        + hash_count(row) * 1.5
        - len(blocked_source_names(row)) * 4.0
        - critical_blocker_count(row) * 7.5
    )
    if row.get("lane") == "market_signal_geometry":
        score -= 35.0
    return round(score, 3)


def claim_stage(row: dict[str, Any]) -> str:
    if bool(row.get("ready_for_live_geometry_claim")):
        return "live_geometry_claim_ready"
    if bool(row.get("lane_ready_for_live_replay_build")):
        return "live_replay_ready_not_field_validated"
    return "registry_design_only"


def family_evidence_status(family_id: str, lane_row: dict[str, Any]) -> str:
    generated = lane_row.get("generated_champion", {})
    proof = lane_row.get("proof_value_champion", {})
    generated_family = norm_id(generated.get("family")) if isinstance(generated, dict) else ""
    proof_family = norm_id(proof.get("family")) if isinstance(proof, dict) else ""
    if family_id and family_id == generated_family and family_id == proof_family:
        return "generated_and_proof_candidate_not_field_validated"
    if family_id and family_id == generated_family:
        return "generated_benchmark_champion_not_live_claim"
    if family_id and family_id == proof_family:
        return "proof_value_champion_not_performance_claim"
    return "registry_candidate_not_validated"


def family_asset_score(family: dict[str, Any], lane_row: dict[str, Any]) -> float:
    family_id = norm_id(family.get("id"))
    status = norm_id(family.get("status"))
    score = lane_operational_score(lane_row) * 0.42
    score += 5.0 if status == "benchmark_design_ready" else 0.0
    score += 3.0 if family.get("natural_logic") else 0.0
    score += 3.0 if family.get("benchmark_hypothesis") else 0.0
    score += 2.0 if family.get("first_test") else 0.0
    score += 2.0 if family.get("promotion_metric") else 0.0
    evidence_status = family_evidence_status(family_id, lane_row)
    if evidence_status == "generated_and_proof_candidate_not_field_validated":
        score += 42.0
    elif evidence_status == "generated_benchmark_champion_not_live_claim":
        score += 34.0 + min(generated_delta(lane_row) * 100.0, 25.0)
    elif evidence_status == "proof_value_champion_not_performance_claim":
        score += 30.0 + proof_score(lane_row) * 0.10
    if status.startswith("legacy"):
        score -= 16.0
    if lane_row.get("lane") == "market_signal_geometry":
        score -= 20.0
    return round(score, 3)


def lane_rankings(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in matrix_rows(matrix):
        lane = norm_id(row.get("lane"))
        if not lane:
            continue
        rows.append(
            {
                "lane": lane,
                "operational_proof_score": lane_operational_score(row),
                "live_wiring_score": float(row.get("live_wiring_score", 0.0) or 0.0),
                "claim_stage": claim_stage(row),
                "measured_source_count": measured_source_count(row),
                "measured_row_count": measured_row_count(row),
                "hash_count": hash_count(row),
                "blocked_sources": blocked_source_names(row),
                "critical_blocker_count": critical_blocker_count(row),
                "generated_champion": row.get("generated_champion", {}),
                "proof_value_champion": row.get("proof_value_champion", {}),
                "highest_impact_use": row.get("highest_impact_use", ""),
                "first_live_replay": row.get("first_live_replay", ""),
                "safe_claim_language": row.get("safe_claim_language", ""),
                "ready_for_live_geometry_claim": bool(row.get("ready_for_live_geometry_claim")),
                "ready_for_real_dollar_claim": bool(row.get("ready_for_real_dollar_claim")),
                "kraken_live_execution_allowed": bool(row.get("kraken_live_execution_allowed")),
            }
        )
    ranked = sorted(rows, key=lambda item: (-item["operational_proof_score"], item["lane"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def family_rankings(registry: dict[str, Any], matrix: dict[str, Any]) -> list[dict[str, Any]]:
    by_lane = {norm_id(row.get("lane")): row for row in matrix_rows(matrix)}
    rows = []
    for family in registry_families(registry):
        lane = norm_id(family.get("lane"))
        lane_row = by_lane.get(lane, {})
        family_id = norm_id(family.get("id"))
        rows.append(
            {
                "family": family_id,
                "label": family.get("label", family_id),
                "lane": lane,
                "status": family.get("status", ""),
                "asset_score": family_asset_score(family, lane_row),
                "evidence_status": family_evidence_status(family_id, lane_row),
                "claim_stage": claim_stage(lane_row),
                "natural_logic": family.get("natural_logic", ""),
                "benchmark_hypothesis": family.get("benchmark_hypothesis", ""),
                "first_test": family.get("first_test", ""),
                "promotion_metric": family.get("promotion_metric", ""),
                "failure_mode": family.get("failure_mode", ""),
                "lane_operational_proof_score": lane_operational_score(lane_row),
                "lane_measured_source_count": measured_source_count(lane_row),
                "lane_blocked_sources": blocked_source_names(lane_row),
                "ready_for_field_validation_claim": False,
            }
        )
    ranked = sorted(rows, key=lambda item: (-item["asset_score"], item["lane"], item["family"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def family_rankings_from_queue(queue: dict[str, Any]) -> list[dict[str, Any]]:
    queue_rows = queue.get("family_queue", [])
    if not isinstance(queue_rows, list) or not queue_rows:
        return []
    rows = []
    for row in queue_rows:
        if not isinstance(row, dict):
            continue
        family_id = norm_id(row.get("family_id"))
        rows.append(
            {
                "family": family_id,
                "label": row.get("label", family_id),
                "lane": row.get("lane", ""),
                "status": row.get("status", ""),
                "asset_score": float(row.get("priority_score", 0.0) or 0.0),
                "evidence_status": row.get("evidence_status", "registry_candidate_not_validated"),
                "rolling_gate_status": row.get("rolling_gate_status", "not_in_rolling_gate"),
                "rolling_gate_repeat_live_win_count": int(row.get("rolling_gate_repeat_live_win_count", 0) or 0),
                "rolling_gate_distinct_run_hash_count": int(row.get("rolling_gate_distinct_run_hash_count", 0) or 0),
                "claim_stage": (
                    "live_replay_candidate_needs_repeat"
                    if row.get("rolling_gate_status") in {"triple_source_candidate", "single_run_candidate"}
                    else "live_replay_ready_not_field_validated"
                    if row.get("live_measured_sources")
                    else "registry_design_only"
                ),
                "natural_logic": row.get("natural_logic", ""),
                "benchmark_hypothesis": row.get("benchmark_hypothesis", ""),
                "first_test": row.get("first_test", ""),
                "promotion_metric": row.get("promotion_metric", ""),
                "failure_mode": row.get("failure_mode", ""),
                "lane_operational_proof_score": float(row.get("priority_score", 0.0) or 0.0),
                "lane_measured_source_count": len(row.get("live_measured_sources", []) or []),
                "lane_blocked_sources": row.get("context_only_sources", []),
                "ready_for_field_validation_claim": False,
                "ready_for_real_dollar_claim": False,
                "kraken_live_execution_allowed": False,
            }
        )
    ranked = sorted(rows, key=lambda item: (-float(item["asset_score"]), item["lane"], item["family"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def category_champions(lanes: list[dict[str, Any]], families: list[dict[str, Any]]) -> dict[str, Any]:
    by_family_status = {row["evidence_status"]: row for row in families}
    generated = [
        row for row in families if row["evidence_status"] == "generated_benchmark_champion_not_live_claim"
    ]
    proof = [
        row
        for row in families
        if row["evidence_status"] in {"proof_value_champion_not_performance_claim", "proof_value_candidate_not_performance_claim"}
    ]
    triple_source = [row for row in families if row.get("rolling_gate_status") == "triple_source_candidate"]
    single_run = [row for row in families if row.get("rolling_gate_status") == "single_run_candidate"]
    rolling = [row for row in families if row.get("rolling_gate_status") == "rolling_champion"]
    harmonic = [row for row in lanes if row["lane"] == "wave_resonance_timing"]
    market = [row for row in lanes if row["lane"] == "market_signal_geometry"]
    return {
        "operational_proof_priority": lanes[0] if lanes else {},
        "top_family_asset": families[0] if families else {},
        "generated_benchmark_delta_champion": generated[0] if generated else {},
        "proof_value_champion": proof[0] if proof else by_family_status.get("proof_value_champion_not_performance_claim", {}),
        "strict_rolling_champion": rolling[0] if rolling else {},
        "strict_triple_source_candidate": triple_source[0] if triple_source else {},
        "strict_single_run_candidate": single_run[0] if single_run else {},
        "harmonic_phase_lock_candidate": harmonic[0] if harmonic else {},
        "market_lane_status": market[0] if market else {},
    }


def build_board() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    matrix = read_json(MATRIX_JSON)
    frontier = read_json(FRONTIER_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    queue = read_json(QUEUE_JSON)

    lane_rows = lane_rankings(matrix)
    family_rows = family_rankings_from_queue(queue) or family_rankings(registry, matrix)
    blocked = reviewer_blocked_sources(gate)
    summary_matrix = matrix.get("summary", {}) if isinstance(matrix.get("summary"), dict) else {}
    registry_cross_lane = bool(registry.get("cross_lane_ranking_allowed"))

    return {
        "generated_utc": now_utc(),
        "schema": "geometry_champion_of_champions_v1",
        "purpose": "Rank geometry lanes and families for the next proof-building sprint without treating cross-lane rankings as field validation.",
        "global_performance_champion_allowed": False,
        "cross_lane_ranking_policy": "Cross-lane ranking is allowed only as an operational proof-build priority, not as a scientific global winner claim.",
        "registry_cross_lane_ranking_allowed": registry_cross_lane,
        "summary": {
            "lane_count": len(registry_lanes(registry)),
            "family_count": len(registry_families(registry)),
            "ranked_lane_count": len(lane_rows),
            "ranked_family_count": len(family_rows),
            "live_measured_sources": summary_matrix.get("live_source_measured_count", 0),
            "live_total_measured_rows": summary_matrix.get("total_measured_rows", 0),
            "reviewer_packet_ready": bool(gate.get("ready_for_reviewer_packet")),
            "ready_for_field_validation_claim": False,
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "blocked_or_thin_sources": blocked,
            "strict_rolling_champion_count": int(queue.get("promotion_gate", {}).get("strict_rolling_champion_count", 0) or 0)
            if isinstance(queue.get("promotion_gate"), dict)
            else 0,
            "triple_source_candidate_count": int(queue.get("promotion_gate", {}).get("triple_source_candidate_count", 0) or 0)
            if isinstance(queue.get("promotion_gate"), dict)
            else 0,
            "single_run_candidate_count": int(queue.get("promotion_gate", {}).get("single_run_candidate_count", 0) or 0)
            if isinstance(queue.get("promotion_gate"), dict)
            else 0,
            "claim_boundary": (
                "This board ranks what to validate next. It does not establish field validation, "
                "real-dollar savings, trading profit, universal superiority, or award certainty."
            ),
        },
        "category_champions": category_champions(lane_rows, family_rows),
        "lane_rankings": lane_rows,
        "family_asset_rankings": family_rows,
        "top_assets_to_build_now": [
            {
                "asset": "Live multi-source regime replay",
                "lane": "time_series_model_routing",
                "why": "It has the strongest fresh live-source wiring and the cleanest proof-chain leverage.",
                "claim_limit": "Replay priority, not field validation.",
            },
            {
                "asset": "Harmonic phase-lock proof card",
                "lane": "wave_resonance_timing",
                "why": "Kuramoto/PLL/Kalman comparisons are the clearest way to test the harmonic thesis on oscillatory systems.",
                "claim_limit": "Generated champion plus live wiring; needs frozen live replay and uncertainty intervals.",
            },
            {
                "asset": "Brachistochrone optimal-curve proof card",
                "lane": "optimal_curve_transport",
                "why": "It has the largest generated benchmark delta and a clean visual/math explanation.",
                "claim_limit": "Software benchmark only until tested on fresh frozen path windows.",
            },
            {
                "asset": "Critical-infrastructure branching transport proof card",
                "lane": "branching_transport",
                "why": "Crack/branching logic maps directly to resilience, outage localization, flow, and avoided-loss language.",
                "claim_limit": "Proof-value champion, not performance winner; NREL remains blocked.",
            },
            {
                "asset": "Thermal ventilation and datacenter cooling proof card",
                "lane": "thermal_ventilation",
                "why": "EIA plus NOAA makes this the clearest hardware-energy wedge once live replay is run.",
                "claim_limit": "Needs real or partner thermal baselines before dollar claims.",
            },
        ],
        "field_validation_requirements": [
            "Freeze a real input window from measured sources or a partner dataset.",
            "Define the incumbent baseline before scoring LumenCore or geometry candidates.",
            "Run identical inputs through baseline and candidate with hashes, failures, and runtime recorded.",
            "Report uncertainty intervals and multiple-comparison controls across tested families.",
            "Obtain a partner, agency, or independent reviewer confirmation before calling it field validation.",
        ],
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_live_wiring_matrix": str(MATRIX_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_proof_frontier_board": str(FRONTIER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "reviewer_evidence_gate": str(REVIEWER_GATE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_live_breadth_proof_queue": str(QUEUE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "frontier_schema": frontier.get("schema", ""),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    champions = payload["category_champions"]
    lines = [
        "# Geometry Champion Of Champions",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Families ranked: {summary['ranked_family_count']} / {summary['family_count']}",
        f"- Lanes ranked: {summary['ranked_lane_count']} / {summary['lane_count']}",
        f"- Live measured sources: {summary['live_measured_sources']}",
        f"- Live measured rows: {summary['live_total_measured_rows']}",
        f"- Reviewer packet ready: `{str(summary['reviewer_packet_ready']).lower()}`",
        f"- Ready for field-validation claim: `{str(summary['ready_for_field_validation_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Kraken live execution allowed: `{str(summary['kraken_live_execution_allowed']).lower()}`",
        f"- Strict rolling champions: `{summary['strict_rolling_champion_count']}`",
        f"- Triple-source candidates: `{summary['triple_source_candidate_count']}`",
        f"- Single-run candidates: `{summary['single_run_candidate_count']}`",
        "",
        "## Category Champions",
        "",
    ]
    for name, row in champions.items():
        if not isinstance(row, dict) or not row:
            continue
        label = row.get("label") or row.get("family") or row.get("lane") or "none"
        lane = row.get("lane", "")
        score = row.get("asset_score", row.get("operational_proof_score", ""))
        lines.append(f"- {name}: `{label}` ({lane}) score `{score}`")
    lines.extend(["", "## Lane Proof Priority", ""])
    for row in payload["lane_rankings"]:
        lines.extend(
            [
                f"### {row['rank']}. {row['lane']}",
                "",
                f"- Operational proof score: {row['operational_proof_score']}",
                f"- Claim stage: `{row['claim_stage']}`",
                f"- Measured sources: {row['measured_source_count']}",
                f"- Measured rows: {row['measured_row_count']}",
                f"- Blocked sources: {', '.join(row['blocked_sources']) or 'none'}",
                f"- Generated champion: `{row.get('generated_champion', {}).get('family', '') or 'none'}`",
                f"- Proof champion: `{row.get('proof_value_champion', {}).get('family', '') or 'none'}`",
                f"- First replay: {row['first_live_replay']}",
                "",
            ]
        )
    lines.extend(["## Top Family Assets", ""])
    for row in payload["family_asset_rankings"][:20]:
        lines.append(
            f"- {row['rank']}. `{row['family']}` ({row['lane']}): "
            f"{row['asset_score']} - {row['evidence_status']} - rolling `{row.get('rolling_gate_status', 'not_in_rolling_gate')}`"
        )
    lines.extend(["", "## Field Validation Requirements", ""])
    lines.extend(f"- {item}" for item in payload["field_validation_requirements"])
    lines.extend(["", "## Blocked Or Thin Sources", ""])
    for source in summary["blocked_or_thin_sources"]:
        lines.append(f"- `{source}`")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    payload = build_board()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "lanes_ranked": payload["summary"]["ranked_lane_count"],
                "families_ranked": payload["summary"]["ranked_family_count"],
                "top_lane": payload["lane_rankings"][0]["lane"] if payload["lane_rankings"] else "",
                "top_family": payload["family_asset_rankings"][0]["family"] if payload["family_asset_rankings"] else "",
                "ready_for_field_validation_claim": payload["summary"]["ready_for_field_validation_claim"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
