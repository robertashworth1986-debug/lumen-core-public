from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, pstdev
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

MATRIX_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"
QUEUE_JSON = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"
OUT_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "top_geometry_live_replay_results.json"
OUT_MD = DOCS / "TOP_GEOMETRY_LIVE_REPLAY_RESULTS_2026-06-24.md"

LANE_MODULES = {
    "optimal_curve_transport": ROOT / "code" / "geometry_optimal_curve_transport_benchmark.py",
    "wave_resonance_timing": ROOT / "code" / "geometry_wave_resonance_timing_benchmark.py",
    "branching_transport": ROOT / "code" / "geometry_branching_transport_benchmark.py",
    "thermal_ventilation": ROOT / "code" / "geometry_thermal_ventilation_benchmark.py",
}

EVIDENCE_BOUNDARY = (
    "Live-context replay only. Frozen measured source snapshots are used to derive deterministic "
    "scenario stress parameters for existing software benchmarks. This is stronger than synthetic-only "
    "benchmarking, but it is not field validation, not realized savings, not a real-dollar claim, "
    "not grant award certainty, and not permission for live trading."
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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_module(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def numeric_values(value: Any) -> list[float]:
    found: list[float] = []
    if isinstance(value, bool):
        return found
    if isinstance(value, (int, float)) and math.isfinite(float(value)):
        return [float(value)]
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text and not any(ch in text for ch in ("-", ":", "/")):
            try:
                number = float(text)
            except ValueError:
                return found
            if math.isfinite(number):
                return [number]
        return found
    if isinstance(value, list):
        for item in value:
            found.extend(numeric_values(item))
        return found
    if isinstance(value, dict):
        for item in value.values():
            found.extend(numeric_values(item))
    return found


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def source_seed(source: dict[str, Any], fallback: str) -> int:
    raw = str(source.get("snapshot_sha256") or fallback or source.get("source") or "live")
    return int(hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12], 16) % 900_000 + 10_000


def load_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    rel = source.get("snapshot_json", "")
    if not rel:
        return {}
    path = ROOT / str(rel)
    return read_json(path)


def snapshot_profile(source: dict[str, Any]) -> dict[str, Any]:
    snapshot = load_snapshot(source)
    values = numeric_values(snapshot.get("rows", []))
    rows = snapshot.get("rows", []) if isinstance(snapshot.get("rows"), list) else []
    if not values:
        values = [float(source.get("rows", 0) or 0)]
    avg = mean(values)
    spread = pstdev(values) if len(values) > 1 else 0.0
    span = max(values) - min(values) if values else 0.0
    cv = spread / max(abs(avg), 1.0)
    diffs = [abs(b - a) for a, b in zip(values, values[1:])]
    shock = max(diffs) / max(abs(avg), 1.0) if diffs else 0.0
    trend = (values[-1] - values[0]) / max(abs(avg), 1.0) if len(values) > 1 else 0.0
    source_name = str(source.get("source", snapshot.get("source", "UNKNOWN"))).upper()
    sha = str(source.get("snapshot_sha256") or snapshot.get("sha256") or "")
    profile = {
        "source": source_name,
        "snapshot_json": source.get("snapshot_json", ""),
        "snapshot_sha256": sha,
        "row_count": int(source.get("rows", snapshot.get("row_count", len(rows))) or 0),
        "numeric_count": len(values),
        "mean": round(avg, 6),
        "stddev": round(spread, 6),
        "span": round(span, 6),
        "coefficient_of_variation": round(cv, 6),
        "shock_index": round(shock, 6),
        "trend_index": round(trend, 6),
        "stress_index": round(clamp(0.45 * cv + 0.35 * shock + 0.20 * abs(trend), 0.0, 1.0), 6),
        "seed": source_seed(source, sha),
    }
    return profile


def combined_profile(profiles: list[dict[str, Any]]) -> dict[str, Any]:
    if not profiles:
        return {
            "source_count": 0,
            "row_count": 0,
            "numeric_count": 0,
            "stress_index": 0.0,
            "coefficient_of_variation": 0.0,
            "shock_index": 0.0,
            "trend_index": 0.0,
            "seed": 10101,
        }
    text = json.dumps(profiles, sort_keys=True)
    return {
        "source_count": len(profiles),
        "row_count": sum(int(item.get("row_count", 0) or 0) for item in profiles),
        "numeric_count": sum(int(item.get("numeric_count", 0) or 0) for item in profiles),
        "stress_index": round(mean(float(item.get("stress_index", 0.0) or 0.0) for item in profiles), 6),
        "coefficient_of_variation": round(mean(float(item.get("coefficient_of_variation", 0.0) or 0.0) for item in profiles), 6),
        "shock_index": round(mean(float(item.get("shock_index", 0.0) or 0.0) for item in profiles), 6),
        "trend_index": round(mean(float(item.get("trend_index", 0.0) or 0.0) for item in profiles), 6),
        "seed": int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:10], 16) % 900_000 + 20_000,
    }


def scenario_profiles_for_card(card: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    profiles = [snapshot_profile(row) for row in card.get("fresh_measured_sources", []) if isinstance(row, dict)]
    return profiles, combined_profile(profiles)


def condition_name(prefix: str, source: str, index: int) -> str:
    clean = "".join(ch.lower() if ch.isalnum() else "_" for ch in source).strip("_") or "source"
    return f"live_{prefix}_{index}_{clean}"[:64]


def run_optimal(module: Any, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles, start=1):
        stress = float(profile["stress_index"])
        cv = float(profile["coefficient_of_variation"])
        shock = float(profile["shock_index"])
        trend = abs(float(profile["trend_index"]))
        condition = module.Condition(
            condition_name("optimal", profile["source"], index),
            8.0 + 10.0 * clamp(cv + 0.2 * index, 0.0, 1.0),
            2.2 + 5.8 * clamp(stress + trend, 0.0, 1.0),
            clamp(0.04 + 0.42 * stress + 0.08 * shock, 0.02, 0.55),
            clamp(0.08 + 0.55 * cv + 0.10 * shock, 0.04, 0.70),
            clamp(0.86 - 0.48 * stress, 0.34, 0.90),
            clamp(0.88 - 0.42 * shock, 0.38, 0.92),
        )
        scenario = module.generate_scenario(int(profile["seed"]), condition, split="live_context")
        for spec in module.STRATEGIES:
            row = module.evaluate_strategy(scenario, spec)
            row["source"] = profile["source"]
            rows.append(row)
    return rows


def run_wave(module: Any, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles, start=1):
        stress = float(profile["stress_index"])
        cv = float(profile["coefficient_of_variation"])
        shock = float(profile["shock_index"])
        trend = abs(float(profile["trend_index"]))
        count = int(profile.get("numeric_count", 0) or 0)
        condition = module.Condition(
            condition_name("wave", profile["source"], index),
            max(128, min(512, 160 + count * 8)),
            clamp(0.055 + 0.18 * ((profile["seed"] % 97) / 97.0), 0.04, 0.24),
            clamp(0.012 + 0.12 * stress + 0.08 * trend, 0.005, 0.18),
            clamp(0.08 + 0.48 * cv, 0.04, 0.48),
            clamp(0.01 + 0.22 * shock, 0.0, 0.24),
            clamp(0.02 + 0.45 * shock + 0.08 * stress, 0.0, 0.55),
            max(1, min(5, 1 + int((profile["seed"] % 5)))),
        )
        scenario = module.generate_scenario(int(profile["seed"]), condition, split="live_context")
        for spec in module.STRATEGIES:
            row = module.evaluate_strategy(scenario, spec)
            row["source"] = profile["source"]
            rows.append(row)
    return rows


def run_branching(module: Any, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles, start=1):
        stress = float(profile["stress_index"])
        cv = float(profile["coefficient_of_variation"])
        shock = float(profile["shock_index"])
        condition = module.Condition(
            condition_name("branch", profile["source"], index),
            13 + int((profile["seed"] % 6)),
            9 + int((profile["seed"] % 5)),
            7 + int((profile["seed"] % 5)),
            clamp(0.20 + 0.55 * stress, 0.10, 0.82),
            clamp(0.18 + 0.65 * cv, 0.08, 0.88),
            clamp(0.10 + 0.38 * shock + 0.16 * stress, 0.04, 0.48),
            clamp(0.03 + 0.12 * shock, 0.01, 0.18),
        )
        scenario = module.generate_scenario(int(profile["seed"]), condition, split="live_context")
        for spec in module.STRATEGIES:
            row = module.evaluate_strategy(scenario, spec)
            row["source"] = profile["source"]
            rows.append(row)
    return rows


def run_thermal(module: Any, profiles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index, profile in enumerate(profiles, start=1):
        stress = float(profile["stress_index"])
        cv = float(profile["coefficient_of_variation"])
        shock = float(profile["shock_index"])
        trend = float(profile["trend_index"])
        condition = module.Condition(
            condition_name("thermal", profile["source"], index),
            15 + int((profile["seed"] % 5)),
            10 + int((profile["seed"] % 4)),
            5 + int((profile["seed"] % 5)),
            clamp(0.22 + 0.62 * stress + 0.12 * cv, 0.10, 0.90),
            clamp(trend, -0.45, 0.45),
            clamp(0.05 + 0.44 * shock + 0.18 * stress, 0.02, 0.55),
            clamp(0.03 + 0.12 * cv + 0.08 * shock, 0.01, 0.20),
        )
        scenario = module.generate_scenario(int(profile["seed"]), condition, split="live_context")
        for spec in module.STRATEGIES:
            row = module.evaluate_strategy(scenario, spec)
            row["source"] = profile["source"]
            rows.append(row)
    return rows


def run_lane_adapter(lane: str, profiles: list[dict[str, Any]]) -> dict[str, Any]:
    module_path = LANE_MODULES.get(lane)
    if not module_path or not module_path.exists():
        return {"adapter_status": "source_context_only_no_lane_adapter", "rows": [], "leaderboard": [], "promotion_gate": {}}
    module = load_module(module_path)
    if lane == "optimal_curve_transport":
        rows = run_optimal(module, profiles)
    elif lane == "wave_resonance_timing":
        rows = run_wave(module, profiles)
    elif lane == "branching_transport":
        rows = run_branching(module, profiles)
    elif lane == "thermal_ventilation":
        rows = run_thermal(module, profiles)
    else:
        rows = []
    leaderboard = module.ranked_aggregate(module.aggregate(rows)) if rows else []
    gate = module.score_against_baseline(leaderboard) if leaderboard else {}
    return {"adapter_status": "live_context_replay_ran", "rows": rows, "leaderboard": leaderboard, "promotion_gate": gate}


def find_leaderboard_row(leaderboard: list[dict[str, Any]], name: str) -> dict[str, Any]:
    for row in leaderboard:
        if row.get("family_id") == name or row.get("strategy") == name:
            return row
    return {}


def score_value(row: dict[str, Any]) -> float:
    return float(row.get("mean_score", row.get("score", 0.0)) or 0.0)


def queue_indexes(queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    family_index = {
        str(row.get("family_id", "")): row
        for row in queue.get("family_queue", [])
        if isinstance(row, dict) and row.get("family_id")
    }
    run_index = {
        str(row.get("family_id", "")): row
        for row in queue.get("top_next_runs", [])
        if isinstance(row, dict) and row.get("family_id")
    }
    return {"family": family_index, "run": run_index}


def replay_card(card: dict[str, Any], indexes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    profiles, profile_summary = scenario_profiles_for_card(card)
    lane = str(card.get("lane", ""))
    candidate = str(card.get("candidate_family_id") or card.get("candidate_strategy") or "")
    named_baseline = str(card.get("best_baseline") or "")
    family_queue = indexes["family"].get(candidate, {})
    next_run = indexes["run"].get(candidate, {})
    adapter = run_lane_adapter(lane, profiles)
    leaderboard = adapter.get("leaderboard", [])
    candidate_row = find_leaderboard_row(leaderboard, candidate)
    named_baseline_row = find_leaderboard_row(leaderboard, named_baseline)
    best_geometry = adapter.get("promotion_gate", {}).get("best_geometry", {}) if isinstance(adapter.get("promotion_gate"), dict) else {}
    best_baseline = adapter.get("promotion_gate", {}).get("best_baseline", {}) if isinstance(adapter.get("promotion_gate"), dict) else {}
    delta = None
    if candidate_row and named_baseline_row:
        delta = round(score_value(candidate_row) - score_value(named_baseline_row), 6)
    candidate_beats_named = bool(delta is not None and delta > 0)
    return {
        "replay_rank": card.get("replay_rank"),
        "lane": lane,
        "candidate_family_id": candidate,
        "named_baseline": named_baseline,
        "adapter_status": adapter["adapter_status"],
        "live_context_profile": profile_summary,
        "source_profiles": profiles,
        "leaderboard": leaderboard,
        "promotion_gate": adapter.get("promotion_gate", {}),
        "candidate_row": candidate_row,
        "named_baseline_row": named_baseline_row,
        "candidate_score_delta_vs_named_baseline": delta,
        "candidate_beats_named_baseline": candidate_beats_named,
        "best_geometry_family_id": best_geometry.get("family_id", best_geometry.get("strategy", "")),
        "best_baseline_family_id": best_baseline.get("family_id", best_baseline.get("strategy", "")),
        "live_context_rows_evaluated": len(adapter.get("rows", [])),
        "queue_rank": family_queue.get("rank"),
        "top_next_run_rank": next_run.get("run_rank"),
        "proof_asset": family_queue.get("proof_asset", ""),
        "evidence_status": family_queue.get("evidence_status", "source_context_only_no_queue_hit"),
        "claim_stage": family_queue.get("claim_stage", "source_context_only_no_queue_hit"),
        "rolling_gate_status": family_queue.get("rolling_gate_status", "not_in_rolling_gate"),
        "rolling_gate_repeat_live_win_count": int(family_queue.get("rolling_gate_repeat_live_win_count", 0) or 0),
        "rolling_gate_distinct_run_hash_count": int(family_queue.get("rolling_gate_distinct_run_hash_count", 0) or 0),
        "rolling_gate_source_count": int(family_queue.get("rolling_gate_source_count", 0) or 0),
        "target_live_sources": family_queue.get("target_live_sources", []),
        "target_assets": family_queue.get("target_assets", []),
        "next_adapter": next_run.get("run_name", family_queue.get("next_adapter", "")),
        "ready_for_live_geometry_claim": False,
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "kraken_live_execution_allowed": False,
        "claim_boundary": EVIDENCE_BOUNDARY,
    }


def build_results() -> dict[str, Any]:
    matrix = read_json(MATRIX_JSON)
    queue = read_json(QUEUE_JSON)
    indexes = queue_indexes(queue)
    cards = matrix.get("top_live_replay_source_map", []) if isinstance(matrix.get("top_live_replay_source_map"), list) else []
    replay_cards = [replay_card(card, indexes) for card in cards if isinstance(card, dict)]
    source_hashes = sorted(
        {
            profile.get("snapshot_sha256", "")
            for card in replay_cards
            for profile in card.get("source_profiles", [])
            if profile.get("snapshot_sha256")
        }
    )
    queue_gate = queue.get("promotion_gate", {}) if isinstance(queue.get("promotion_gate"), dict) else {}
    return {
        "generated_utc": now_utc(),
        "schema": "top_geometry_live_replay_results_v1",
        "purpose": "Run top geometry champion cards against deterministic live-context scenarios derived from frozen measured source snapshots.",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "summary": {
            "replay_card_count": len(replay_cards),
            "adapter_replay_count": sum(1 for card in replay_cards if card["adapter_status"] == "live_context_replay_ran"),
            "source_context_only_count": sum(1 for card in replay_cards if card["adapter_status"] != "live_context_replay_ran"),
            "candidate_beats_named_baseline_count": sum(1 for card in replay_cards if card["candidate_beats_named_baseline"]),
            "total_live_context_rows_evaluated": sum(int(card.get("live_context_rows_evaluated", 0) or 0) for card in replay_cards),
            "unique_snapshot_sha256_count": len(source_hashes),
            "snapshot_chain_sha256": sha256_text("\n".join(source_hashes)),
            "strict_rolling_champion_count": int(queue_gate.get("strict_rolling_champion_count", 0) or 0),
            "triple_source_candidate_replay_count": sum(
                1 for card in replay_cards if card.get("rolling_gate_status") == "triple_source_candidate"
            ),
            "single_run_candidate_replay_count": sum(
                1 for card in replay_cards if card.get("rolling_gate_status") == "single_run_candidate"
            ),
            "ready_for_live_geometry_claim": False,
            "ready_for_real_dollar_claim": False,
            "field_validation": False,
            "kraken_live_execution_allowed": False,
            "claim_boundary": EVIDENCE_BOUNDARY,
        },
        "replay_cards": replay_cards,
        "inputs": {
            "geometry_live_wiring_matrix": str(MATRIX_JSON.relative_to(ROOT)).replace("\\", "/"),
            "geometry_live_breadth_proof_queue": str(QUEUE_JSON.relative_to(ROOT)).replace("\\", "/"),
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
        "# Top Geometry Live Replay Results",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Summary",
        "",
        f"- Replay cards: {summary['replay_card_count']}",
        f"- Adapter replays run: {summary['adapter_replay_count']}",
        f"- Source-context-only cards: {summary['source_context_only_count']}",
        f"- Candidate beats named baseline count: {summary['candidate_beats_named_baseline_count']}",
        f"- Live-context rows evaluated: {summary['total_live_context_rows_evaluated']}",
        f"- Unique snapshot hashes: {summary['unique_snapshot_sha256_count']}",
        f"- Snapshot chain SHA-256: `{summary['snapshot_chain_sha256']}`",
        f"- Strict rolling champions: `{summary['strict_rolling_champion_count']}`",
        f"- Triple-source candidate replays: `{summary['triple_source_candidate_replay_count']}`",
        f"- Single-run candidate replays: `{summary['single_run_candidate_replay_count']}`",
        f"- Ready for live geometry claim: `{str(summary['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(summary['ready_for_real_dollar_claim']).lower()}`",
        "",
        "## Replay Cards",
        "",
        "| Rank | Lane | Candidate | Named Baseline | Adapter | Candidate Delta | Best Geometry | Rolling Gate | Evidence | Status |",
        "| ---: | --- | --- | --- | --- | ---: | --- | --- | --- | --- |",
    ]
    for card in payload["replay_cards"]:
        delta = card["candidate_score_delta_vs_named_baseline"]
        delta_text = "n/a" if delta is None else str(delta)
        lines.append(
            f"| {card['replay_rank']} | `{card['lane']}` | `{card['candidate_family_id']}` | "
            f"`{card['named_baseline']}` | `{card['adapter_status']}` | {delta_text} | "
            f"`{card['best_geometry_family_id'] or 'n/a'}` | `{card['rolling_gate_status']}` | "
            f"`{card['evidence_status']}` | `{str(card['candidate_beats_named_baseline']).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            payload["evidence_boundary"],
            "",
            "## Next Gate",
            "",
            "Promote no card to live geometry or dollar claims until the replay is repeated on larger frozen windows, uncertainty intervals are reported, multiple-comparison control is applied across the registry, and a real operational/field validation source is attached.",
        ]
    )
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    payload = build_results()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "replay_cards": payload["summary"]["replay_card_count"],
                "adapter_replays": payload["summary"]["adapter_replay_count"],
                "candidate_beats_named_baseline_count": payload["summary"]["candidate_beats_named_baseline_count"],
                "live_context_rows_evaluated": payload["summary"]["total_live_context_rows_evaluated"],
                "ready_for_live_geometry_claim": payload["summary"]["ready_for_live_geometry_claim"],
                "json": payload["outputs"]["json"],
                "markdown": payload["outputs"]["markdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
