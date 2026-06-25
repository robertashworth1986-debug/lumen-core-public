from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
QUEUE_JSON = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
ASSET_WIRING_JSON = OUT_OPS / "geometry_asset_wiring_board_latest.json"
PROOF_CARD_PACK_JSON = OUT_OPS / "geometry_proof_card_pack_latest.json"

OUT_JSON = OUT_OPS / "geometry_champion_asset_map_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_champion_asset_map.json"
OUT_MD = DOCS / "GEOMETRY_CHAMPION_ASSET_MAP_2026-06-25.md"

BOUNDARY = (
    "Champion asset mapping ranks research, live-context evidence, dashboard wiring, grant fit, and buyer-pilot "
    "readiness. It is not field validation, not realized savings, not a company valuation, not trading advice, "
    "and not a real-dollar claim."
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


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def index_by(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {str(row.get(key, "")): row for row in rows if isinstance(row, dict) and row.get(key)}


def registry_summary(registry: dict[str, Any]) -> dict[str, Any]:
    families = [row for row in as_list(registry.get("families")) if isinstance(row, dict)]
    lanes = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    status_counts = Counter(str(row.get("status", "unknown")) for row in families)
    lane_counts = Counter(str(row.get("lane", "unknown")) for row in families)
    natural_path_count = sum(1 for row in families if str(row.get("natural_logic", "")).strip())
    benchmark_ready_count = sum(1 for row in families if row.get("status") == "benchmark_design_ready")
    missing_natural_logic = [str(row.get("id", "")) for row in families if not str(row.get("natural_logic", "")).strip()]
    return {
        "family_count": len(families),
        "lane_count": len(lanes),
        "natural_path_family_count": natural_path_count,
        "benchmark_design_ready_count": benchmark_ready_count,
        "minimum_natural_path_target": 50,
        "natural_path_target_met": natural_path_count >= 50,
        "status_counts": dict(sorted(status_counts.items())),
        "lane_counts": dict(sorted(lane_counts.items())),
        "missing_natural_logic": missing_natural_logic,
        "core_rule": registry.get("core_rule", ""),
        "evidence_boundary": registry.get("evidence_boundary", ""),
    }


def completeness_score(family: dict[str, Any]) -> float:
    score = 0.0
    score += 4.0 if family.get("natural_logic") else 0.0
    score += 4.0 if family.get("benchmark_hypothesis") else 0.0
    score += 3.0 if family.get("first_test") else 0.0
    score += 3.0 if family.get("promotion_metric") else 0.0
    score += 2.0 if family.get("failure_mode") else 0.0
    return score


def wiring_stage_score(row: dict[str, Any]) -> float:
    tier = str(row.get("readiness_tier", ""))
    score = 0.0
    if "triple_source" in tier:
        score += 38.0
    if "single_run" in tier:
        score += 18.0
    if "proof_value" in tier:
        score += 20.0
    if "did_not_beat" in tier:
        score -= 10.0
    validation = row.get("validation_run", {}) if isinstance(row.get("validation_run"), dict) else {}
    if validation.get("candidate_beats_named_baseline") is True:
        score += 18.0
    if validation.get("candidate_beats_named_baseline") is False:
        score -= 8.0
    score += min(float(row.get("live_source_count", 0) or 0) * 2.0, 12.0)
    score += min(len(as_list(row.get("dashboard_targets"))) * 0.7, 7.0)
    score += min(len(as_list(row.get("grant_targets"))) * 1.1, 7.0)
    return score


def claim_stage(row: dict[str, Any] | None, queue_row: dict[str, Any] | None) -> str:
    tier = str((row or {}).get("readiness_tier", ""))
    rolling = str((queue_row or {}).get("rolling_gate_status", ""))
    if "triple_source" in tier or rolling == "triple_source_candidate":
        return "repeat_live_candidate_not_field_validated"
    if "single_run" in tier or rolling == "single_run_candidate":
        return "single_run_candidate_needs_repeat_or_more_sources"
    if "proof_value" in tier or (queue_row or {}).get("is_proof_value_champion"):
        return "high_value_adapter_target_not_live_winner"
    if "did_not_beat" in tier:
        return "negative_evidence_reroute"
    return "registry_ranked_needs_live_replay"


def asset_stage(row: dict[str, Any] | None, queue_row: dict[str, Any] | None) -> str:
    stage = claim_stage(row, queue_row)
    if stage == "repeat_live_candidate_not_field_validated":
        return "closest_to_defensible_repeat_proof"
    if stage == "single_run_candidate_needs_repeat_or_more_sources":
        return "needs_repeat_or_more_sources"
    if stage == "high_value_adapter_target_not_live_winner":
        return "high_value_next_adapter"
    if stage == "negative_evidence_reroute":
        return "negative_result_use_for_reroute"
    return "longer_horizon_registry_candidate"


def score_asset(
    family: dict[str, Any],
    queue_row: dict[str, Any] | None,
    champion_row: dict[str, Any] | None,
    wiring_row: dict[str, Any] | None,
) -> float:
    score = completeness_score(family)
    status = str(family.get("status", ""))
    if status == "benchmark_design_ready":
        score += 7.0
    if status.startswith("legacy"):
        score -= 10.0
    if status == "diagnostic_specification":
        score += 2.0

    if queue_row:
        score += float(queue_row.get("priority_score", 0.0) or 0.0) * 0.44
        score += min(float(queue_row.get("safe_annual_value_surface_usd", 0.0) or 0.0) / 1_000_000.0, 18.0)
        if queue_row.get("is_generated_lane_champion"):
            score += 12.0
        if queue_row.get("is_proof_value_champion"):
            score += 16.0
        if queue_row.get("rolling_gate_status") == "triple_source_candidate":
            score += 24.0
        if queue_row.get("rolling_gate_status") == "single_run_candidate":
            score += 10.0

    if champion_row:
        score += float(champion_row.get("asset_score", 0.0) or 0.0) * 0.18
        if champion_row.get("rolling_gate_status") == "triple_source_candidate":
            score += 15.0
        if champion_row.get("rolling_gate_status") == "single_run_candidate":
            score += 6.0

    if wiring_row:
        score += wiring_stage_score(wiring_row)

    lane = str(family.get("lane", ""))
    if lane == "market_signal_geometry":
        score -= 12.0
    return round(score, 3)


def build_asset_rows(
    registry: dict[str, Any],
    queue: dict[str, Any],
    champion: dict[str, Any],
    asset_wiring: dict[str, Any],
) -> list[dict[str, Any]]:
    families = [row for row in as_list(registry.get("families")) if isinstance(row, dict)]
    queue_by_id = index_by([row for row in as_list(queue.get("family_queue")) if isinstance(row, dict)], "family_id")
    champion_by_id = index_by([row for row in as_list(champion.get("family_asset_rankings")) if isinstance(row, dict)], "family")
    wiring_by_id = index_by([row for row in as_list(asset_wiring.get("wiring_rows")) if isinstance(row, dict)], "family_id")

    rows: list[dict[str, Any]] = []
    for family in families:
        family_id = str(family.get("id", ""))
        q = queue_by_id.get(family_id)
        c = champion_by_id.get(family_id)
        w = wiring_by_id.get(family_id)
        score = score_asset(family, q, c, w)
        row = {
            "family_id": family_id,
            "label": family.get("label", family_id),
            "lane": family.get("lane", ""),
            "status": family.get("status", ""),
            "natural_logic": family.get("natural_logic", ""),
            "benchmark_hypothesis": family.get("benchmark_hypothesis", ""),
            "first_test": family.get("first_test", ""),
            "promotion_metric": family.get("promotion_metric", ""),
            "failure_mode": family.get("failure_mode", ""),
            "asset_score": score,
            "asset_stage": asset_stage(w, q),
            "claim_stage": claim_stage(w, q),
            "queue_priority_score": (q or {}).get("priority_score", 0.0),
            "champion_asset_score": (c or {}).get("asset_score", 0.0),
            "wiring_readiness_tier": (w or {}).get("readiness_tier", ""),
            "rolling_gate_status": (w or q or {}).get("rolling_gate_status", "not_in_rolling_gate"),
            "candidate_beats_named_baseline": ((w or {}).get("validation_run", {}) or {}).get(
                "candidate_beats_named_baseline"
            ),
            "live_source_count": (w or q or {}).get("live_source_count", (q or {}).get("rolling_gate_source_count", 0)),
            "safe_annual_value_surface_usd": (q or {}).get("safe_annual_value_surface_usd", 0.0),
            "blocked_context_annual_value_surface_usd": (q or {}).get("blocked_context_annual_value_surface_usd", 0.0),
            "dashboard_targets": (w or {}).get("dashboard_targets", []),
            "grant_targets": (w or {}).get("grant_targets", []),
            "buyer_segments": (w or {}).get("buyer_segments", []),
            "next_adapter": (q or {}).get("next_adapter", ""),
            "next_validation_steps": ((w or {}).get("validation_run", {}) or {}).get(
                "next_steps", as_list((q or {}).get("next_validation_steps"))
            ),
            "claim_gate": {
                "ready_for_live_geometry_claim": False,
                "ready_for_real_dollar_claim": False,
                "field_validation": False,
                "kraken_live_execution_allowed": False,
            },
            "claim_boundary": BOUNDARY,
        }
        row["row_sha256"] = stable_sha256(row)
        rows.append(row)

    ranked = sorted(rows, key=lambda item: (-float(item["asset_score"]), item["lane"], item["family_id"]))
    for rank, row in enumerate(ranked, start=1):
        row["asset_rank"] = rank
    return ranked


def nearest_valuable_proofs(rows: list[dict[str, Any]]) -> dict[str, Any]:
    repeat_candidates = [
        row
        for row in rows
        if row["asset_stage"] == "closest_to_defensible_repeat_proof"
    ]
    single_run = [row for row in rows if row["asset_stage"] == "needs_repeat_or_more_sources"]
    adapters = [row for row in rows if row["asset_stage"] == "high_value_next_adapter"]
    negative = [row for row in rows if row["asset_stage"] == "negative_result_use_for_reroute"]
    blocked_value = sorted(
        rows,
        key=lambda item: float(item.get("blocked_context_annual_value_surface_usd", 0.0) or 0.0),
        reverse=True,
    )
    safe_value = sorted(
        rows,
        key=lambda item: float(item.get("safe_annual_value_surface_usd", 0.0) or 0.0),
        reverse=True,
    )
    return {
        "closest_repeat_candidates": trim_assets(repeat_candidates, 6),
        "single_run_candidates": trim_assets(single_run, 6),
        "highest_value_adapter_targets": trim_assets(adapters, 8),
        "negative_evidence_reroutes": trim_assets(negative, 6),
        "largest_blocked_context_targets": trim_assets(blocked_value, 8),
        "largest_safe_value_surfaces": trim_assets(safe_value, 8),
    }


def trim_assets(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    trimmed = []
    for row in rows[:limit]:
        trimmed.append(
            {
                "asset_rank": row.get("asset_rank"),
                "family_id": row.get("family_id"),
                "label": row.get("label"),
                "lane": row.get("lane"),
                "asset_score": row.get("asset_score"),
                "asset_stage": row.get("asset_stage"),
                "claim_stage": row.get("claim_stage"),
                "rolling_gate_status": row.get("rolling_gate_status"),
                "safe_annual_value_surface_usd": row.get("safe_annual_value_surface_usd"),
                "blocked_context_annual_value_surface_usd": row.get("blocked_context_annual_value_surface_usd"),
                "next_adapter": row.get("next_adapter"),
            }
        )
    return trimmed


def validation_sequence(asset_wiring: dict[str, Any], queue: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for item in as_list(asset_wiring.get("top_next_actions")):
        if not isinstance(item, dict):
            continue
        actions.append(
            {
                "priority": int(item.get("priority", len(actions) + 1) or len(actions) + 1),
                "family_id": item.get("family_id", ""),
                "action": item.get("action", ""),
                "reason": item.get("reason", ""),
                "source": "asset_wiring_board",
            }
        )
    offset = len(actions)
    for item in as_list(queue.get("top_next_runs"))[:8]:
        if not isinstance(item, dict):
            continue
        family_id = str(item.get("family_id", ""))
        if any(action["family_id"] == family_id for action in actions):
            continue
        actions.append(
            {
                "priority": offset + int(item.get("run_rank", len(actions) + 1) or len(actions) + 1),
                "family_id": family_id,
                "action": item.get("run_name", ""),
                "reason": item.get("why_now", ""),
                "source": "geometry_live_breadth_proof_queue",
            }
        )
    ordered = sorted(actions, key=lambda item: item["priority"])[:12]
    for priority, item in enumerate(ordered, start=1):
        item["priority"] = priority
    return ordered


def build_payload() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    queue = read_json(QUEUE_JSON)
    champion = read_json(CHAMPION_JSON)
    asset_wiring = read_json(ASSET_WIRING_JSON)
    proof_pack = read_json(PROOF_CARD_PACK_JSON)

    assets = build_asset_rows(registry, queue, champion, asset_wiring)
    reg_summary = registry_summary(registry)
    stage_counts = Counter(row["asset_stage"] for row in assets)
    gates = {
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "kraken_live_execution_allowed": False,
        "mass_email_allowed": False,
    }
    summary = {
        "family_count": reg_summary["family_count"],
        "lane_count": reg_summary["lane_count"],
        "ranked_asset_count": len(assets),
        "natural_path_family_count": reg_summary["natural_path_family_count"],
        "natural_path_target_met": reg_summary["natural_path_target_met"],
        "benchmark_design_ready_count": reg_summary["benchmark_design_ready_count"],
        "closest_repeat_candidate_count": stage_counts.get("closest_to_defensible_repeat_proof", 0),
        "single_run_candidate_count": stage_counts.get("needs_repeat_or_more_sources", 0),
        "high_value_adapter_target_count": stage_counts.get("high_value_next_adapter", 0),
        "negative_reroute_count": stage_counts.get("negative_result_use_for_reroute", 0),
        "longer_horizon_candidate_count": stage_counts.get("longer_horizon_registry_candidate", 0),
        "strict_rolling_champion_count": queue.get("promotion_gate", {}).get("strict_rolling_champion_count", 0),
        "triple_source_candidate_count": queue.get("promotion_gate", {}).get("triple_source_candidate_count", 0),
        "proof_card_count": proof_pack.get("summary", {}).get("proof_card_count", 0),
        "asset_chain_sha256": stable_sha256(assets),
        **gates,
    }

    return {
        "schema": "geometry_champion_asset_map_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)),
            "geometry_live_breadth_proof_queue": str(QUEUE_JSON.relative_to(ROOT)),
            "geometry_champion_of_champions": str(CHAMPION_JSON.relative_to(ROOT)),
            "geometry_asset_wiring_board": str(ASSET_WIRING_JSON.relative_to(ROOT)),
            "geometry_proof_card_pack": str(PROOF_CARD_PACK_JSON.relative_to(ROOT)),
        },
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
        "summary": summary,
        "registry_summary": reg_summary,
        "nearest_valuable_proofs": nearest_valuable_proofs(assets),
        "top_validation_sequence": validation_sequence(asset_wiring, queue),
        "top_assets": trim_assets(assets, 25),
        "ranked_assets": assets,
        "claim_controls": {
            "allowed": [
                "ranked research asset",
                "repeat-live candidate when the row says repeat candidate",
                "buyer pilot/review target",
                "grant evidence appendix candidate",
            ],
            "blocked": [
                "field validated",
                "realized savings",
                "guaranteed award",
                "guaranteed profit",
                "fixed-dollar packet value as fact",
                "live trading permission",
            ],
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    reg = payload["registry_summary"]
    nearest = payload["nearest_valuable_proofs"]
    lines = [
        "# Geometry Champion Asset Map",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Registry Health",
        "",
        f"- Families ranked: `{summary['ranked_asset_count']}` / `{summary['family_count']}`",
        f"- Lanes: `{summary['lane_count']}`",
        f"- Families with natural logic: `{summary['natural_path_family_count']}`",
        f"- Natural path target met: `{str(summary['natural_path_target_met']).lower()}`",
        f"- Benchmark-design-ready families: `{summary['benchmark_design_ready_count']}`",
        f"- Missing natural logic: {', '.join(reg['missing_natural_logic']) if reg['missing_natural_logic'] else 'none'}",
        "",
        "## Claim Gates",
        "",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        f"- Field validation: `{str(summary['field_validation']).lower()}`",
        f"- Kraken live execution allowed: `{str(summary['kraken_live_execution_allowed']).lower()}`",
        f"- Mass email allowed: `{str(summary['mass_email_allowed']).lower()}`",
        f"- Asset chain SHA-256: `{summary['asset_chain_sha256']}`",
        "",
        "## Nearest Valuable Proof",
        "",
        "Closest repeat candidates:",
    ]
    for row in nearest["closest_repeat_candidates"]:
        lines.append(
            f"- `{row['family_id']}` ({row['lane']}) score `{row['asset_score']}`: repeat live-context proof candidate, not field validation."
        )
    lines.append("")
    lines.append("Highest-value next adapters:")
    for row in nearest["highest_value_adapter_targets"][:5]:
        lines.append(
            f"- `{row['family_id']}` ({row['lane']}) score `{row['asset_score']}`: {row['asset_stage']}."
        )
    lines.extend(["", "## Top Validation Sequence", ""])
    for action in payload["top_validation_sequence"]:
        lines.append(
            f"{action['priority']}. `{action['family_id']}` - {action['action']} ({action['source']})"
        )
    lines.extend(
        [
            "",
            "## Top Assets",
            "",
            "| Rank | Family | Lane | Stage | Score | Claim Stage |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["top_assets"][:20]:
        lines.append(
            f"| {row['asset_rank']} | `{row['family_id']}` | `{row['lane']}` | `{row['asset_stage']}` | `{row['asset_score']}` | `{row['claim_stage']}` |"
        )
    lines.extend(
        [
            "",
            "## Controls",
            "",
            "- Use this map to decide the next experiment, dashboard wiring, grant annex, or paid pilot target.",
            "- Do not use it to claim field validation, realized savings, guaranteed awards, guaranteed profit, or a fixed-dollar packet value.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


if __name__ == "__main__":
    main()
