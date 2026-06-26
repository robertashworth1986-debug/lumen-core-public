from __future__ import annotations

import json
import hashlib
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
ROLLING_GATE_JSON = OUT_OPS / "rolling_champion_gate_latest.json"
UNCERTAINTY_JSON = OUT_OPS / "geometry_repeat_uncertainty_report_latest.json"
PROOF_TO_PILOT_JSON = OUT_OPS / "proof_to_pilot_control_room_latest.json"
TRUTH_SWEEP_JSON = OUT_OPS / "field_money_truth_sweep_latest.json"
CLAIM_MAP_JSON = OUT_OPS / "claim_strength_value_unlock_map_latest.json"
KURAMOTO_HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"

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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def rows_from(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = payload.get(key, [])
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def rolling_by_family(rolling: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {norm_id(row.get("family_id")): row for row in rows_from(rolling, "promotion_board") if row.get("family_id")}


def uncertainty_by_family(uncertainty: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {norm_id(row.get("family_id")): row for row in rows_from(uncertainty, "analyses") if row.get("family_id")}


def proof_cards_by_family(proof_to_pilot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {norm_id(row.get("family_id")): row for row in rows_from(proof_to_pilot, "top_cards") if row.get("family_id")}


def summary_dict(payload: dict[str, Any]) -> dict[str, Any]:
    summary = payload.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def gates_dict(payload: dict[str, Any]) -> dict[str, Any]:
    gates = payload.get("gates", {})
    return gates if isinstance(gates, dict) else {}


def registry_families(registry: dict[str, Any]) -> list[dict[str, Any]]:
    rows = registry.get("families", [])
    return [row for row in rows if isinstance(row, dict)]


def registry_lanes(registry: dict[str, Any]) -> dict[str, Any]:
    lanes = registry.get("lanes", {})
    return lanes if isinstance(lanes, dict) else {}


BENCHMARK_SPEC_FIELDS = (
    "natural_logic",
    "benchmark_hypothesis",
    "first_test",
    "promotion_metric",
    "failure_mode",
)


def benchmark_spec_missing_fields(row: dict[str, Any]) -> list[str]:
    return [field for field in BENCHMARK_SPEC_FIELDS if not norm_id(row.get(field))]


def benchmark_spec_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    missing = [
        {
            "family": norm_id(row.get("family") or row.get("id")),
            "lane": norm_id(row.get("lane")),
            "missing_fields": benchmark_spec_missing_fields(row),
        }
        for row in rows
        if benchmark_spec_missing_fields(row)
    ]
    return {
        "specified_count": max(len(rows) - len(missing), 0),
        "missing_count": len(missing),
        "missing": missing,
    }


def apply_registry_spec_overlay(rows: list[dict[str, Any]], registry: dict[str, Any]) -> list[dict[str, Any]]:
    registry_by_family = {norm_id(row.get("id")): row for row in registry_families(registry) if row.get("id")}
    overlaid = []
    for row in rows:
        family_id = norm_id(row.get("family"))
        registry_row = registry_by_family.get(family_id, {})
        merged = dict(row)
        for field in BENCHMARK_SPEC_FIELDS:
            if not norm_id(merged.get(field)) and norm_id(registry_row.get(field)):
                merged[field] = registry_row.get(field, "")
        if not norm_id(merged.get("label")) and norm_id(registry_row.get("label")):
            merged["label"] = registry_row.get("label", family_id)
        if not norm_id(merged.get("lane")) and norm_id(registry_row.get("lane")):
            merged["lane"] = registry_row.get("lane", "")
        overlaid.append(merged)
    return overlaid


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


def overlay_claim_stage(rolling_status: str, uncertainty: dict[str, Any], live_sources: list[Any]) -> str:
    if rolling_status == "rolling_champion":
        return "rolling_champion_not_field_validated"
    if bool(uncertainty.get("robust_repeat_uncertainty_gate_passed")):
        return "robust_repeat_window_candidate_not_field_validated"
    if bool(uncertainty.get("repeat_candidate_gate_passed")):
        return "repeat_window_candidate_not_field_validated"
    if rolling_status in {"triple_source_candidate", "single_run_candidate"}:
        return "live_replay_candidate_needs_repeat"
    if live_sources:
        return "live_replay_ready_not_field_validated"
    return "registry_design_only"


def overlay_evidence_status(rolling_status: str, uncertainty: dict[str, Any], fallback: str) -> str:
    if rolling_status == "rolling_champion":
        return "rolling_champion_repeat_live_context_not_field_validated"
    if bool(uncertainty.get("robust_repeat_uncertainty_gate_passed")):
        return "robust_repeat_window_candidate_not_field_validated"
    if rolling_status == "triple_source_candidate":
        return "triple_source_live_candidate_needs_repeat_run"
    if rolling_status == "single_run_candidate":
        return "single_run_candidate_needs_more_sources_or_repeat"
    if bool(uncertainty.get("repeat_candidate_gate_passed")):
        return "repeat_window_candidate_not_field_validated"
    return fallback or "registry_candidate_not_validated"


def overlay_asset_score(row: dict[str, Any], rolling: dict[str, Any], uncertainty: dict[str, Any], proof_card: dict[str, Any]) -> float:
    score = safe_float(row.get("priority_score"))
    rolling_status = norm_id(rolling.get("status") or row.get("rolling_gate_status"))
    source_count = safe_int(rolling.get("source_count"), len(row.get("live_measured_sources", []) or []))
    delta = safe_float(rolling.get("latest_score_delta_vs_named_baseline"))
    if rolling_status == "rolling_champion":
        score += 70.0
    elif rolling_status == "triple_source_candidate":
        score += 35.0
    elif rolling_status == "single_run_candidate":
        score += 12.0
    if bool(uncertainty.get("robust_repeat_uncertainty_gate_passed")):
        score += 60.0
    elif bool(uncertainty.get("repeat_candidate_gate_passed")):
        score += 25.0
    if proof_card:
        score += 20.0
    score += min(source_count * 3.0, 30.0)
    if delta > 0:
        score += min(delta * 100.0, 25.0)
    if row.get("lane") == "market_signal_geometry":
        score -= 20.0
    return round(score, 3)


def family_rankings_from_queue(
    queue: dict[str, Any],
    rolling: dict[str, Any] | None = None,
    uncertainty: dict[str, Any] | None = None,
    proof_to_pilot: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    queue_rows = queue.get("family_queue", [])
    if not isinstance(queue_rows, list) or not queue_rows:
        return []
    rolling_map = rolling_by_family(rolling or {})
    uncertainty_map = uncertainty_by_family(uncertainty or {})
    proof_map = proof_cards_by_family(proof_to_pilot or {})
    rows = []
    for row in queue_rows:
        if not isinstance(row, dict):
            continue
        family_id = norm_id(row.get("family_id"))
        rolling_row = rolling_map.get(family_id, {})
        uncertainty_row = uncertainty_map.get(family_id, {})
        proof_card = proof_map.get(family_id, {})
        rolling_status = norm_id(rolling_row.get("status") or row.get("rolling_gate_status") or "not_in_rolling_gate")
        live_sources = row.get("live_measured_sources", []) or []
        rows.append(
            {
                "family": family_id,
                "label": row.get("label", family_id),
                "lane": row.get("lane", ""),
                "status": row.get("status", ""),
                "asset_score": overlay_asset_score(row, rolling_row, uncertainty_row, proof_card),
                "evidence_status": overlay_evidence_status(
                    rolling_status,
                    uncertainty_row,
                    row.get("evidence_status", "registry_candidate_not_validated"),
                ),
                "rolling_gate_status": rolling_status,
                "rolling_gate_repeat_live_win_count": safe_int(
                    rolling_row.get("repeat_live_win_count"),
                    safe_int(row.get("rolling_gate_repeat_live_win_count")),
                ),
                "rolling_gate_distinct_run_hash_count": safe_int(
                    rolling_row.get("distinct_run_hash_count"),
                    safe_int(row.get("rolling_gate_distinct_run_hash_count")),
                ),
                "rolling_latest_score_delta_vs_named_baseline": rolling_row.get("latest_score_delta_vs_named_baseline"),
                "rolling_source_count": safe_int(rolling_row.get("source_count"), len(live_sources)),
                "rolling_sources": rolling_row.get("sources", []),
                "claim_stage": overlay_claim_stage(rolling_status, uncertainty_row, live_sources),
                "natural_logic": row.get("natural_logic", ""),
                "benchmark_hypothesis": row.get("benchmark_hypothesis", ""),
                "first_test": row.get("first_test", ""),
                "promotion_metric": row.get("promotion_metric", ""),
                "failure_mode": row.get("failure_mode", ""),
                "lane_operational_proof_score": safe_float(row.get("priority_score")),
                "lane_measured_source_count": len(live_sources),
                "lane_blocked_sources": row.get("context_only_sources", []),
                "uncertainty_stage": uncertainty_row.get("evidence_stage", ""),
                "robust_repeat_uncertainty_gate_passed": bool(
                    uncertainty_row.get("robust_repeat_uncertainty_gate_passed")
                ),
                "repeat_candidate_gate_passed": bool(uncertainty_row.get("repeat_candidate_gate_passed")),
                "uncertainty_lower_95_delta": (
                    uncertainty_row.get("delta_stats", {}).get("normal_t_lower_95_delta")
                    if isinstance(uncertainty_row.get("delta_stats"), dict)
                    else None
                ),
                "uncertainty_sign_test_p": uncertainty_row.get("one_sided_sign_test_p_value"),
                "uncertainty_windows": uncertainty_row.get("window_count"),
                "uncertainty_wins": uncertainty_row.get("win_count"),
                "paid_pilot_ready": bool(proof_card),
                "pilot_name": proof_card.get("pilot_name", ""),
                "manual_outreach_allowed": bool(proof_card.get("claim_gate", {}).get("manual_outreach_allowed"))
                if isinstance(proof_card.get("claim_gate"), dict)
                else False,
                "unlock_conditions": proof_card.get("unlock_conditions", []),
                "ready_for_field_validation_claim": False,
                "ready_for_real_dollar_claim": False,
                "kraken_live_execution_allowed": False,
            }
        )
    ranked = sorted(rows, key=lambda item: (-float(item["asset_score"]), item["lane"], item["family"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked


def kuramoto_holdout_summary(holdout: dict[str, Any]) -> dict[str, Any]:
    summary = summary_dict(holdout)
    results = rows_from(holdout, "holdout_results")
    candidate = norm_id(summary.get("candidate")) or (
        norm_id(results[0].get("candidate_family")) if results else "kuramoto_phase_coupling"
    )
    named_baseline = norm_id(summary.get("named_baseline")) or "kalman_filter"
    holdout_count = safe_int(summary.get("holdout_count"), len(results))
    wins_vs_kalman = safe_int(
        summary.get("wins_vs_kalman"),
        len([row for row in results if bool(row.get("candidate_beats_kalman"))]),
    )
    wins_vs_best = safe_int(
        summary.get("wins_vs_best_baseline"),
        len([row for row in results if bool(row.get("candidate_beats_best_baseline"))]),
    )
    estimated_rows = safe_int(
        summary.get("estimated_rows_replayed"),
        sum(safe_int(row.get("estimated_rows")) for row in results),
    )
    numeric_samples = safe_int(
        summary.get("numeric_samples_read"),
        sum(safe_int(row.get("numeric_samples")) for row in results),
    )
    source_systems = summary.get("source_systems", [])
    if not isinstance(source_systems, list) or not source_systems:
        source_systems = sorted({norm_id(row.get("source_system")) for row in results if row.get("source_system")})
    source_systems = [norm_id(item) for item in source_systems if norm_id(item)]
    source_system_count = safe_int(summary.get("source_system_count"), len(source_systems))
    mean_delta = safe_float(summary.get("mean_delta_vs_kalman"))
    if not mean_delta and results:
        deltas = [safe_float(row.get("delta_vs_kalman")) for row in results]
        mean_delta = sum(deltas) / len(deltas)
    win_rate = safe_float(summary.get("win_rate_vs_kalman"))
    if not win_rate and holdout_count:
        win_rate = wins_vs_kalman / holdout_count
    passes_internal_gate = bool(summary.get("passes_internal_20_holdout_gate")) or (
        holdout_count >= 20 and wins_vs_kalman == holdout_count
    )
    ready_for_field_replay_request = bool(summary.get("ready_for_buyer_authorized_field_replay_request")) or (
        passes_internal_gate and holdout_count >= 20
    )
    return {
        "candidate": candidate,
        "named_baseline": named_baseline,
        "holdout_count": holdout_count,
        "wins_vs_kalman": wins_vs_kalman,
        "wins_vs_best_baseline": wins_vs_best,
        "losses_or_ties_vs_kalman": safe_int(
            summary.get("losses_or_ties_vs_kalman"),
            max(holdout_count - wins_vs_kalman, 0),
        ),
        "win_rate_vs_kalman": round(win_rate, 6),
        "mean_delta_vs_kalman": round(mean_delta, 6),
        "min_delta_vs_kalman": safe_float(summary.get("min_delta_vs_kalman")),
        "max_delta_vs_kalman": safe_float(summary.get("max_delta_vs_kalman")),
        "estimated_rows_replayed": estimated_rows,
        "numeric_samples_read": numeric_samples,
        "source_system_count": source_system_count,
        "source_systems": source_systems,
        "wilson_95_win_rate_lower": safe_float(summary.get("wilson_95_win_rate_lower")),
        "wilson_95_win_rate_upper": safe_float(summary.get("wilson_95_win_rate_upper")),
        "one_sided_sign_test_p_value": summary.get("one_sided_sign_test_p_value"),
        "holdout_chain_sha256": norm_id(summary.get("holdout_chain_sha256")),
        "passes_internal_20_holdout_gate": passes_internal_gate,
        "ready_for_buyer_authorized_field_replay_request": ready_for_field_replay_request,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "claim_boundary": (
            "Internal source-conditioned holdout replay; ready to request buyer-authorized field replay, "
            "but not field validation, realized savings, fixed-dollar delta value, or live execution evidence."
        ),
    }


def kuramoto_holdout_score_boost(summary: dict[str, Any]) -> float:
    if not summary.get("ready_for_buyer_authorized_field_replay_request"):
        return 0.0
    return round(
        35.0
        + (15.0 if summary.get("passes_internal_20_holdout_gate") else 0.0)
        + min(safe_int(summary.get("wins_vs_kalman")) * 0.5, 12.0)
        + min(safe_int(summary.get("source_system_count")) * 2.0, 8.0)
        + min(safe_float(summary.get("mean_delta_vs_kalman")) * 100.0, 15.0)
        + min(safe_int(summary.get("estimated_rows_replayed")) / 500000.0, 8.0),
        3,
    )


def apply_kuramoto_holdout_overlay(
    family_rows: list[dict[str, Any]],
    holdout: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    holdout_summary = kuramoto_holdout_summary(holdout)
    candidate = norm_id(holdout_summary.get("candidate"))
    if not candidate or not holdout_summary.get("ready_for_buyer_authorized_field_replay_request"):
        return family_rows, holdout_summary

    boost = kuramoto_holdout_score_boost(holdout_summary)
    rows = []
    for row in family_rows:
        updated = dict(row)
        if norm_id(updated.get("family")) == candidate:
            updated["asset_score"] = round(safe_float(updated.get("asset_score")) + boost, 3)
            updated["evidence_status"] = "expanded_source_conditioned_holdout_winner_not_field_validated"
            updated["claim_stage"] = "buyer_authorized_field_replay_request_ready_not_field_validated"
            updated["holdout_gate_status"] = "internal_20_holdout_gate_passed"
            updated["ready_for_buyer_authorized_field_replay_request"] = True
            updated["kuramoto_holdout_evidence"] = holdout_summary
            updated["ready_for_field_validation_claim"] = False
            updated["ready_for_real_dollar_claim"] = False
            updated["kraken_live_execution_allowed"] = False
            unlock_conditions = (
                list(updated.get("unlock_conditions", []))
                if isinstance(updated.get("unlock_conditions"), list)
                else []
            )
            needed = "buyer-authorized field replay using pre-registered holdout windows and accepted economics"
            if needed not in unlock_conditions:
                unlock_conditions.append(needed)
            updated["unlock_conditions"] = unlock_conditions
        rows.append(updated)

    ranked = sorted(rows, key=lambda item: (-float(item["asset_score"]), item["lane"], item["family"]))
    for rank, row in enumerate(ranked, start=1):
        row["rank"] = rank
    return ranked, holdout_summary


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
    robust = [row for row in families if row.get("robust_repeat_uncertainty_gate_passed")]
    paid_pilot = [row for row in families if row.get("paid_pilot_ready")]
    field_replay_request = [row for row in families if row.get("ready_for_buyer_authorized_field_replay_request")]
    harmonic = [row for row in lanes if row["lane"] == "wave_resonance_timing"]
    market = [row for row in lanes if row["lane"] == "market_signal_geometry"]
    return {
        "operational_proof_priority": lanes[0] if lanes else {},
        "top_family_asset": families[0] if families else {},
        "generated_benchmark_delta_champion": generated[0] if generated else {},
        "proof_value_champion": proof[0] if proof else by_family_status.get("proof_value_champion_not_performance_claim", {}),
        "strict_rolling_champion": rolling[0] if rolling else {},
        "robust_repeat_candidate": robust[0] if robust else {},
        "buyer_authorized_field_replay_request_candidate": field_replay_request[0] if field_replay_request else {},
        "paid_pilot_scoping_candidate": paid_pilot[0] if paid_pilot else {},
        "strict_triple_source_candidate": triple_source[0] if triple_source else {},
        "strict_single_run_candidate": single_run[0] if single_run else {},
        "harmonic_phase_lock_candidate": harmonic[0] if harmonic else {},
        "market_lane_status": market[0] if market else {},
    }


def strongest_rolling_proxy(rolling: dict[str, Any], family_id: str) -> dict[str, Any]:
    for row in rows_from(rolling, "promotion_board"):
        if norm_id(row.get("family_id")) == family_id:
            return row
    return {}


def champion_of_champions_section(
    families: list[dict[str, Any]],
    rolling: dict[str, Any],
    truth: dict[str, Any],
) -> dict[str, Any]:
    by_family = {row["family"]: row for row in families}
    rolling_rows = [row for row in families if row.get("rolling_gate_status") == "rolling_champion"]
    robust_rows = [row for row in rolling_rows if row.get("robust_repeat_uncertainty_gate_passed")]
    field_replay_rows = [row for row in families if row.get("ready_for_buyer_authorized_field_replay_request")]
    strongest_current = (
        field_replay_rows[0]
        if field_replay_rows
        else (robust_rows[0] if robust_rows else (rolling_rows[0] if rolling_rows else (families[0] if families else {})))
    )
    return {
        "strongest_current": strongest_current,
        "best_buyer_pilot_card": by_family.get("brachistochrone_descent", {}),
        "best_harmonic_candidate": by_family.get("kuramoto_phase_coupling", {}),
        "best_thermal_candidate": by_family.get("thermal_plume_convection", {}),
        "best_branching_next_candidate": by_family.get("leaf_veins", by_family.get("crack_propagation_paths", {})),
        "strongest_money_proxy": strongest_rolling_proxy(rolling, "phase_locked_residual_corrector"),
        "safe_estimated_value_signal": {
            "hourly_usd": summary_dict(truth).get("safe_estimated_hourly_value_usd", 0),
            "annual_usd": summary_dict(truth).get("safe_estimated_annual_value_usd", 0),
            "language": "Estimated under assumptions only; not field validation, revenue, ROI, or realized savings.",
        },
        "blocked_context_value_surface": {
            "annual_usd": summary_dict(truth).get("blocked_context_annual_value_usd", 0),
            "language": "Context-only opportunity surface; blocked from dollar claims until field validation and accepted economics exist.",
        },
    }


def current_truth_gates(truth: dict[str, Any]) -> dict[str, Any]:
    gates = gates_dict(truth)
    return {
        "live_data_available_for_benchmarking": bool(gates.get("live_data_available_for_benchmarking")),
        "rolling_champion_present": bool(gates.get("rolling_champion_present")),
        "bounded_estimated_value_claim_allowed": bool(gates.get("bounded_estimated_value_claim_allowed")),
        "paid_pilot_scoping_allowed": bool(gates.get("paid_pilot_scoping_allowed")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "vps_domain_live_dashboard_routed": bool(gates.get("vps_domain_live_dashboard_routed")),
        "all_registered_families_live_benchmarked": bool(gates.get("all_registered_families_live_benchmarked")),
        "all_families_have_benchmark_specs": bool(gates.get("all_families_have_benchmark_specs")),
        "glyph_or_external_vault_routed": bool(gates.get("glyph_or_external_vault_routed")),
        "triple_dataset_frozen_assets_present": bool(gates.get("triple_dataset_frozen_assets_present")),
    }


def build_board() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    matrix = read_json(MATRIX_JSON)
    frontier = read_json(FRONTIER_JSON)
    gate = read_json(REVIEWER_GATE_JSON)
    queue = read_json(QUEUE_JSON)
    rolling = read_json(ROLLING_GATE_JSON)
    uncertainty = read_json(UNCERTAINTY_JSON)
    proof_to_pilot = read_json(PROOF_TO_PILOT_JSON)
    truth = read_json(TRUTH_SWEEP_JSON)
    claim_map = read_json(CLAIM_MAP_JSON)
    kuramoto_holdout = read_json(KURAMOTO_HOLDOUT_JSON)

    lane_rows = lane_rankings(matrix)
    family_rows = family_rankings_from_queue(queue, rolling, uncertainty, proof_to_pilot) or family_rankings(registry, matrix)
    family_rows, kuramoto_summary = apply_kuramoto_holdout_overlay(family_rows, kuramoto_holdout)
    family_rows = apply_registry_spec_overlay(family_rows, registry)
    spec_summary = benchmark_spec_summary(family_rows)
    blocked = reviewer_blocked_sources(gate)
    summary_matrix = matrix.get("summary", {}) if isinstance(matrix.get("summary"), dict) else {}
    truth_summary = summary_dict(truth)
    rolling_summary = summary_dict(rolling)
    truth_gates = current_truth_gates(truth)
    registry_cross_lane = bool(registry.get("cross_lane_ranking_allowed"))

    payload = {
        "generated_utc": now_utc(),
        "schema": "geometry_champion_of_champions_v1",
        "purpose": "Rank geometry lanes and families for the next proof-building sprint using the latest live truth gates without treating cross-lane rankings as field validation.",
        "global_performance_champion_allowed": False,
        "cross_lane_ranking_policy": "Cross-lane ranking is allowed only as an operational proof-build priority, not as a scientific global winner claim.",
        "registry_cross_lane_ranking_allowed": registry_cross_lane,
        "summary": {
            "lane_count": truth_summary.get("registered_lane_count", len(registry_lanes(registry))),
            "family_count": truth_summary.get("registered_family_count", len(registry_families(registry))),
            "ranked_lane_count": len(lane_rows),
            "ranked_family_count": len(family_rows),
            "live_measured_sources": truth_summary.get("measured_sources", summary_matrix.get("live_source_measured_count", 0)),
            "live_total_measured_rows": truth_summary.get("total_measured_rows", summary_matrix.get("total_measured_rows", 0)),
            "adapter_replay_count": truth_summary.get("adapter_replay_count", 0),
            "candidate_beats_named_baseline_count": truth_summary.get("candidate_beats_named_baseline_count", 0),
            "reviewer_packet_ready": bool(gate.get("ready_for_reviewer_packet")),
            "ready_for_field_validation_claim": False,
            "ready_for_real_dollar_claim": False,
            "kraken_live_execution_allowed": False,
            "bounded_estimated_value_claim_allowed": truth_gates["bounded_estimated_value_claim_allowed"],
            "paid_pilot_scoping_allowed": truth_gates["paid_pilot_scoping_allowed"],
            "safe_estimated_hourly_value_usd": truth_summary.get("safe_estimated_hourly_value_usd", 0),
            "safe_estimated_annual_value_usd": truth_summary.get("safe_estimated_annual_value_usd", 0),
            "blocked_context_annual_value_usd": truth_summary.get("blocked_context_annual_value_usd", 0),
            "vault_packet_ready": bool(truth_summary.get("vault_packet_ready")),
            "vault_packet_dir": truth_summary.get("vault_packet_dir", ""),
            "vault_hashes_verified": bool(truth_summary.get("vault_hashes_verified")),
            "benchmark_specified_family_count": spec_summary["specified_count"],
            "benchmark_specified_family_gap_count": spec_summary["missing_count"],
            "benchmark_specified_family_missing": spec_summary["missing"],
            "blocked_or_thin_sources": blocked,
            "strict_rolling_champion_count": rolling_summary.get(
                "rolling_champion_count",
                truth_summary.get("rolling_champion_count", 0),
            ),
            "robust_repeat_candidate_count": truth_summary.get("robust_repeat_candidate_count", 0),
            "triple_source_candidate_count": rolling_summary.get(
                "triple_source_candidate_count",
                truth_summary.get("triple_source_candidate_count", 0),
            ),
            "single_run_candidate_count": rolling_summary.get(
                "single_run_candidate_count",
                truth_summary.get("single_run_candidate_count", 0),
            ),
            "kuramoto_holdout_count": kuramoto_summary.get("holdout_count", 0),
            "kuramoto_holdout_wins_vs_kalman": kuramoto_summary.get("wins_vs_kalman", 0),
            "kuramoto_holdout_mean_delta_vs_kalman": kuramoto_summary.get("mean_delta_vs_kalman", 0),
            "kuramoto_holdout_estimated_rows_replayed": kuramoto_summary.get("estimated_rows_replayed", 0),
            "kuramoto_holdout_source_system_count": kuramoto_summary.get("source_system_count", 0),
            "kuramoto_holdout_chain_sha256": kuramoto_summary.get("holdout_chain_sha256", ""),
            "kuramoto_ready_for_buyer_authorized_field_replay_request": bool(
                kuramoto_summary.get("ready_for_buyer_authorized_field_replay_request")
            ),
            "claim_boundary": (
                "This board ranks what to validate next. It does not establish field validation, "
                "real-dollar savings, trading profit, universal superiority, or award certainty."
            ),
        },
        "current_truth_gates": truth_gates,
        "champion_of_champions": champion_of_champions_section(family_rows, rolling, truth),
        "category_champions": category_champions(lane_rows, family_rows),
        "lane_rankings": lane_rows,
        "family_asset_rankings": family_rows,
        "external_rolling_candidates": rows_from(rolling, "promotion_board"),
        "top_assets_to_build_now": [
            {
                "asset": "Brachistochrone constrained-routing proof card",
                "lane": "optimal_curve_transport",
                "why": "It is the only current robust repeat-window candidate and the strongest buyer-authorized pilot target.",
                "claim_limit": "Repeat live-context candidate; not field validation or realized savings.",
            },
            {
                "asset": "Harmonic phase-lock proof card",
                "lane": "wave_resonance_timing",
                "why": "Kuramoto/PLL/Kalman comparisons are the clearest way to test the harmonic thesis on oscillatory systems; the current expansion has 24 internal source-conditioned holdout wins versus Kalman.",
                "claim_limit": "Ready to request buyer-authorized field replay; not field validation, realized savings, or fixed-dollar delta value.",
            },
            {
                "asset": "Energy price pressure money-proxy replay",
                "lane": "energy_price_pressure_proxy",
                "why": "It has the largest current named-baseline delta, but it is still a proxy and needs buyer or agency economics before money claims.",
                "claim_limit": "Bounded estimated value only; not realized savings.",
            },
            {
                "asset": "Critical-infrastructure branching transport proof card",
                "lane": "branching_transport",
                "why": "Leaf-vein and crack/branching logic maps directly to resilience, outage localization, flow, and avoided-loss language.",
                "claim_limit": "Candidate only until repeat windows and uncertainty pass.",
            },
            {
                "asset": "Thermal ventilation and datacenter cooling proof card",
                "lane": "thermal_ventilation",
                "why": "It is a rolling champion but has too few source types for robust promotion; it is the clearest hardware-energy wedge once source depth improves.",
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
        "required_next_wiring": [
            "Route dashboard/data/geometry_champion_of_champions.json and field_money_truth_sweep.json to the live VPS/domain and verify hosted hashes.",
            "Route kuramoto_holdout_expansion_latest.json into dashboard/data and the buyer field-replay request packet.",
            "Convert brachistochrone_descent and kuramoto_phase_coupling proof cards into grant appendices with the same claim gates.",
            "Keep all registered family benchmark specs complete as the registry expands; do not let the spec count drift below the ranked family count.",
            "Build adapters for high-value unbenchmarked families before claiming broad family coverage.",
            "Acquire buyer or agency authorized field data before any field-validation or real-dollar savings claim.",
        ],
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_live_wiring_matrix": str(MATRIX_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_proof_frontier_board": str(FRONTIER_JSON.relative_to(ROOT)).replace("\\", "/"),
            "reviewer_evidence_gate": str(REVIEWER_GATE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_live_breadth_proof_queue": str(QUEUE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "rolling_champion_gate": str(ROLLING_GATE_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_repeat_uncertainty_report": str(UNCERTAINTY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "proof_to_pilot_control_room": str(PROOF_TO_PILOT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "field_money_truth_sweep": str(TRUTH_SWEEP_JSON.relative_to(ROOT)).replace("\\", "/"),
            "claim_strength_value_unlock_map": str(CLAIM_MAP_JSON.relative_to(ROOT)).replace("\\", "/"),
            "kuramoto_holdout_expansion": str(KURAMOTO_HOLDOUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "frontier_schema": frontier.get("schema", ""),
            "claim_map_schema": claim_map.get("schema", ""),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace("\\", "/"),
            "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
        },
    }
    payload["board_sha256"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    champions = payload["category_champions"]
    truth_gates = payload.get("current_truth_gates", {})
    coc = payload.get("champion_of_champions", {})
    strongest = coc.get("strongest_current", {}) if isinstance(coc, dict) else {}
    money_proxy = coc.get("strongest_money_proxy", {}) if isinstance(coc, dict) else {}
    lines = [
        "# Geometry Champion Of Champions",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Board SHA-256: `{payload.get('board_sha256', '')}`",
        "",
        "## Boundary",
        "",
        summary["claim_boundary"],
        "",
        "## Summary",
        "",
        f"- Families ranked: {summary['ranked_family_count']} / {summary['family_count']}",
        f"- Benchmark-specified families: {summary['benchmark_specified_family_count']} / {summary['ranked_family_count']}",
        f"- Benchmark spec gaps: {summary['benchmark_specified_family_gap_count']}",
        f"- Lanes ranked: {summary['ranked_lane_count']} / {summary['lane_count']}",
        f"- Live measured sources: {summary['live_measured_sources']}",
        f"- Live measured rows: {summary['live_total_measured_rows']}",
        f"- Live adapter replays: {summary['adapter_replay_count']}",
        f"- Candidate beats named baseline count: {summary['candidate_beats_named_baseline_count']}",
        f"- Reviewer packet ready: `{str(summary['reviewer_packet_ready']).lower()}`",
        f"- Ready for field-validation claim: `{str(summary['ready_for_field_validation_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Kraken live execution allowed: `{str(summary['kraken_live_execution_allowed']).lower()}`",
        f"- Bounded estimated value claim allowed: `{str(summary['bounded_estimated_value_claim_allowed']).lower()}`",
        f"- Paid pilot scoping allowed: `{str(summary['paid_pilot_scoping_allowed']).lower()}`",
        f"- Safe estimated value signal: `${summary['safe_estimated_hourly_value_usd']:,.0f}/hour`, `${summary['safe_estimated_annual_value_usd']:,.0f}/year` under assumptions",
        f"- Blocked context-only value surface: `${summary['blocked_context_annual_value_usd']:,.0f}/year`",
        f"- Vault packet ready: `{str(summary['vault_packet_ready']).lower()}`",
        f"- Vault hashes verified: `{str(summary['vault_hashes_verified']).lower()}`",
        f"- Strict rolling champions: `{summary['strict_rolling_champion_count']}`",
        f"- Robust repeat candidates: `{summary['robust_repeat_candidate_count']}`",
        f"- Triple-source candidates: `{summary['triple_source_candidate_count']}`",
        f"- Single-run candidates: `{summary['single_run_candidate_count']}`",
        f"- Kuramoto holdout wins vs Kalman: `{summary.get('kuramoto_holdout_wins_vs_kalman', 0)} / {summary.get('kuramoto_holdout_count', 0)}`",
        f"- Kuramoto holdout mean delta vs Kalman: `{summary.get('kuramoto_holdout_mean_delta_vs_kalman', 0)}`",
        f"- Kuramoto holdout estimated rows replayed: `{summary.get('kuramoto_holdout_estimated_rows_replayed', 0)}`",
        f"- Kuramoto field-replay request ready: `{str(summary.get('kuramoto_ready_for_buyer_authorized_field_replay_request', False)).lower()}`",
        "",
        "## Current Truth Gates",
        "",
    ]
    for key, value in truth_gates.items():
        lines.append(f"- {key}: `{str(value).lower()}`")
    lines.extend(
        [
            "",
            "## Strongest Current Read",
            "",
            f"- Strongest current candidate: `{strongest.get('family', '')}` ({strongest.get('lane', '')})",
            f"- Evidence status: `{strongest.get('evidence_status', '')}`",
            f"- Claim stage: `{strongest.get('claim_stage', '')}`",
            f"- Robust repeat gate: `{str(strongest.get('robust_repeat_uncertainty_gate_passed', False)).lower()}`",
            f"- Paid pilot ready: `{str(strongest.get('paid_pilot_ready', False)).lower()}`",
            f"- Strongest money proxy: `{money_proxy.get('family_id', '')}` ({money_proxy.get('lane', '')}) delta `{money_proxy.get('latest_score_delta_vs_named_baseline', '')}`",
            "",
        ]
    )
    kuramoto = coc.get("best_harmonic_candidate", {}) if isinstance(coc, dict) else {}
    kuramoto_evidence = kuramoto.get("kuramoto_holdout_evidence", {}) if isinstance(kuramoto, dict) else {}
    if isinstance(kuramoto_evidence, dict) and kuramoto_evidence:
        lines.extend(
            [
                "## Kuramoto Holdout Read",
                "",
                f"- Candidate: `{kuramoto_evidence.get('candidate', '')}`",
                f"- Baseline: `{kuramoto_evidence.get('named_baseline', '')}`",
                f"- Holdout wins: `{kuramoto_evidence.get('wins_vs_kalman', 0)} / {kuramoto_evidence.get('holdout_count', 0)}`",
                f"- Mean delta vs baseline: `{kuramoto_evidence.get('mean_delta_vs_kalman', 0)}`",
                f"- Estimated rows replayed: `{kuramoto_evidence.get('estimated_rows_replayed', 0)}`",
                f"- Source systems: `{kuramoto_evidence.get('source_system_count', 0)}`",
                f"- Chain SHA-256: `{kuramoto_evidence.get('holdout_chain_sha256', '')}`",
                f"- Boundary: {kuramoto_evidence.get('claim_boundary', '')}",
                "",
            ]
        )
    lines.extend(
        [
        "## Category Champions",
        "",
        ]
    )
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
    lines.extend(["", "## Required Next Wiring", ""])
    lines.extend(f"- {item}" for item in payload["required_next_wiring"])
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
