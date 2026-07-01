from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

from geometry_branching_transport_benchmark import (  # noqa: E402
    Condition,
    STRATEGIES,
    aggregate,
    evaluate_strategy,
    generate_scenario,
    ranked_aggregate,
    score_against_baseline,
)


OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

LIVE_BREADTH = OUT_OPS / "live_breadth_value_panel_latest.json"
GEOMETRY_QUEUE = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"
LOCAL_INTAKE = OUT_OPS / "local_icloud_evidence_intake_latest.json"

RUN_ROOT = OUT_OPS / "branching_live_breadth_replay"
OUT_JSON = OUT_OPS / "branching_live_breadth_replay_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "branching_live_breadth_replay.json"
OUT_MD = DOCS / "BRANCHING_LIVE_BREADTH_REPLAY_2026-06-22.md"

TARGET_FAMILY = "crack_propagation_paths"
TARGET_LANE = "branching_transport"
EVIDENCE_BOUNDARY = (
    "Live-breadth-derived proxy replay. Live/source rows are used to derive "
    "deterministic constrained-flow scenario parameters, then the existing "
    "branching benchmark compares baselines and geometry families on the same "
    "frozen scenarios. This is not raw operational topology, field validation, "
    "realized savings, customer ROI, government savings, or trading performance."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def read_json(path: Path) -> dict[str, Any]:
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
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_int(*parts: object) -> int:
    digest = hashlib.blake2b("|".join(str(part) for part in parts).encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(digest, "big")


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def compact_source_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(row.get("source") or ""),
        "sector": str(row.get("sector") or ""),
        "constraint": str(row.get("constraint") or "default"),
        "evidence_source": str(row.get("evidence_source") or ""),
        "provenance": str(row.get("provenance") or ""),
        "primary_live_evidence": bool(row.get("primary_live_evidence")),
        "baseline_loss_rate_usd_per_hour": round(as_float(row.get("baseline_loss_rate_usd_per_hour")), 4),
        "optimization_gain_pct": round(as_float(row.get("optimization_gain_pct")), 4),
        "estimated_hourly_value_usd": round(as_float(row.get("estimated_hourly_value_usd")), 4),
        "estimated_annual_value_usd": round(as_float(row.get("estimated_annual_value_usd")), 4),
        "generated_utc": str(row.get("generated_utc") or ""),
    }


def branching_work_order(queue: dict[str, Any]) -> dict[str, Any]:
    for item in queue.get("top_next_runs", []):
        if isinstance(item, dict) and item.get("lane") == TARGET_LANE and item.get("family_id") == TARGET_FAMILY:
            return item
    return {
        "family_id": TARGET_FAMILY,
        "lane": TARGET_LANE,
        "target_live_sources": ["EIA", "NREL", "USGS_WATER", "NOAA_NCEI", "FEDWIRE_OPS", "ISO_NE", "HHS_FEED"],
        "live_measured_sources": ["EIA", "NREL"],
        "baselines": ["minimum_spanning_tree", "steiner_approximation", "min_cost_flow"],
        "metrics": ["delivered_flow", "energy_proxy", "material_proxy", "failure_tolerance", "runtime_ms"],
    }


def source_rows_for_replay(live_breadth: dict[str, Any], work_order: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    rows = [row for row in live_breadth.get("source_rows", []) if isinstance(row, dict)]
    target_sources = {str(source) for source in work_order.get("target_live_sources", [])}
    live_rows = [
        compact_source_row(row)
        for row in rows
        if bool(row.get("primary_live_evidence")) and str(row.get("source") or "") in target_sources
    ]
    context_rows = [
        compact_source_row(row)
        for row in rows
        if not bool(row.get("primary_live_evidence")) and str(row.get("source") or "") in target_sources
    ]
    return {"live_rows": live_rows, "context_rows": context_rows, "all_rows": [compact_source_row(row) for row in rows]}


def derive_condition(row: dict[str, Any], *, split: str, fold: int) -> Condition:
    seed = stable_int(row["source"], row["sector"], row["constraint"], split, fold)
    baseline = max(1.0, as_float(row.get("baseline_loss_rate_usd_per_hour")))
    annual = max(1.0, as_float(row.get("estimated_annual_value_usd")))
    gain = max(0.0, as_float(row.get("optimization_gain_pct")))
    width = 13 + seed % 6 + min(4, int(annual // 10_000_000))
    height = 9 + (seed // 7) % 5 + min(3, int(baseline // 100_000))
    sink_count = 6 + (seed // 11) % 6 + min(3, int(gain // 2))
    risk_bias = min(0.82, max(0.18, 0.24 + gain / 10.0 + ((seed % 17) / 200.0)))
    demand_skew = min(0.85, max(0.16, 0.18 + (baseline / 500_000.0) + ((seed % 13) / 100.0)))
    failure_pressure = min(0.48, max(0.08, 0.10 + gain / 18.0 + ((seed % 9) / 160.0)))
    obstacle_density = min(0.12, max(0.025, 0.035 + gain / 120.0 + ((seed % 5) / 250.0)))
    name = f"{row['source'].lower()}_{row['sector'].lower()}_{split}_f{fold}"
    return Condition(name, int(width), int(height), int(sink_count), risk_bias, demand_skew, failure_pressure, obstacle_density)


def build_replay_scenarios(rows: list[dict[str, Any]], *, split: str, fold_count: int, seed_offset: int) -> list[Any]:
    scenarios = []
    for row_index, row in enumerate(rows):
        for fold in range(fold_count):
            condition = derive_condition(row, split=split, fold=fold)
            seed = stable_int(row["source"], row["sector"], row["constraint"], split, fold, seed_offset, row_index) % 2_000_000_000
            scenarios.append(generate_scenario(seed, condition, split=split))
    return scenarios


def evaluate_scenarios(scenarios: list[Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        for spec in STRATEGIES:
            rows.append(evaluate_strategy(scenario, spec))
    leaderboard = ranked_aggregate(aggregate(rows))
    gate = score_against_baseline(leaderboard)
    return rows, leaderboard, gate


def source_manifest(rows: list[dict[str, Any]]) -> dict[str, Any]:
    serial = json.dumps(rows, sort_keys=True, separators=(",", ":"))
    return {
        "row_count": len(rows),
        "source_count": len({row["source"] for row in rows}),
        "sources": sorted({row["source"] for row in rows}),
        "sectors": sorted({row["sector"] for row in rows}),
        "sha256": sha256_text(serial),
    }


def scenario_manifest(scenarios: list[Any]) -> dict[str, Any]:
    rows = [
        {
            "split": scenario.split,
            "condition": scenario.condition.__dict__,
            "seed": scenario.seed,
            "sink_count": len(scenario.sinks),
            "blocked_edges": len(scenario.blocked_edges),
        }
        for scenario in scenarios
    ]
    return {"scenario_count": len(scenarios), "sha256": sha256_text(json.dumps(rows, sort_keys=True)), "rows": rows}


def intake_bridge_summary(intake: dict[str, Any]) -> dict[str, Any]:
    bridge = intake.get("valuation_bridge", {}) if isinstance(intake.get("valuation_bridge"), dict) else {}
    return {
        "available": bool(intake),
        "candidate_count": int(bridge.get("candidate_count") or 0),
        "top_candidates": bridge.get("top_candidates", [])[:8] if isinstance(bridge.get("top_candidates"), list) else [],
        "boundary": "Historical evidence roots broaden target discovery, but each file remains metadata until source, hash, and replay gates pass.",
    }


def promotion_gate(live_rows: list[dict[str, Any]], context_rows: list[dict[str, Any]], validation_gate: dict[str, Any]) -> dict[str, Any]:
    score_delta = as_float(validation_gate.get("score_delta_vs_best_baseline"))
    live_source_count = len({row["source"] for row in live_rows})
    enough_sources = live_source_count >= 3
    enough_rows = len(live_rows) >= 5
    candidate_beats = validation_gate.get("gate") == "candidate_geometry_beats_best_baseline" and score_delta > 0.0
    return {
        "bounded_live_breadth_replay_complete": True,
        "candidate_geometry_beats_best_baseline": bool(candidate_beats),
        "ready_for_live_geometry_claim": bool(candidate_beats and enough_sources and enough_rows),
        "ready_for_real_dollar_claim": False,
        "field_validation": False,
        "grant_or_portal_submit_proof": False,
        "live_measured_source_count": live_source_count,
        "live_measured_row_count": len(live_rows),
        "context_only_row_count": len(context_rows),
        "requirements_missing": [
            requirement
            for requirement, missing in [
                ("minimum three representative live/authorized source families", not enough_sources),
                ("minimum five independent live measured source rows", not enough_rows),
                ("raw operational topology or source-specific flow windows", True),
                ("holdout uncertainty or paired confidence interval", True),
                ("independent field/pilot validation", True),
                ("buyer or agency mission-owner confirmation of loss metric", True),
            ]
            if missing
        ],
        "boundary": EVIDENCE_BOUNDARY,
    }


def money(value: Any) -> str:
    return f"${as_float(value):,.2f}"


def render_markdown(payload: dict[str, Any]) -> str:
    source = payload["source_summary"]
    gate = payload["promotion_gate"]
    validation = payload["validation_replay"]
    context = payload["context_only_replay"]
    lines = [
        "# Branching Live-Breadth Replay",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Boundary",
        "",
        payload["evidence_boundary"],
        "",
        "## Result",
        "",
        f"- Family: `{payload['family_id']}`",
        f"- Lane: `{payload['lane']}`",
        f"- Live measured sources: {', '.join(source['live_source_manifest']['sources']) or 'none'}",
        f"- Live measured annual value surface: {money(source['live_measured_estimated_annual_value_usd'])}",
        f"- Context-only annual value surface: {money(source['context_only_estimated_annual_value_usd'])}",
        f"- Validation gate: `{validation['gate'].get('gate')}`",
        f"- Best geometry: `{validation['gate'].get('best_geometry', {}).get('strategy', 'n/a')}`",
        f"- Best baseline: `{validation['gate'].get('best_baseline', {}).get('strategy', 'n/a')}`",
        f"- Score delta vs best baseline: `{validation['gate'].get('score_delta_vs_best_baseline', 0)}`",
        f"- Ready for live geometry claim: `{str(gate['ready_for_live_geometry_claim']).lower()}`",
        f"- Ready for real-dollar claim: `{str(gate['ready_for_real_dollar_claim']).lower()}`",
        "",
        "## Validation Leaderboard",
        "",
        "| Rank | Strategy | Kind | Score | Delivered | Failure Tolerance | Energy |",
        "|---:|---|---|---:|---:|---:|---:|",
    ]
    for row in validation["leaderboard"][:12]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | {row['mean_score']} | "
            f"{row['mean_delivered_flow']} | {row['mean_failure_tolerance']} | {row['mean_energy_proxy']} |"
        )
    lines.extend(["", "## Context-Only Replay", ""])
    lines.append(
        "Context rows are run only as blocked target discovery. They can show where value may exist, "
        "but cannot be promoted to live or dollar claims until the sources become measured/authorized."
    )
    lines.append(f"- Context scenario count: `{context['scenario_manifest']['scenario_count']}`")
    lines.append(f"- Context gate: `{context['gate'].get('gate', 'not_run')}`")
    lines.extend(["", "## Missing Before Strong Claims", ""])
    for item in gate["requirements_missing"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Historical Valuation Bridge", ""])
    lines.append(f"- Intake candidate artifacts: `{payload['historical_valuation_bridge']['candidate_count']}`")
    lines.append(f"- Boundary: {payload['historical_valuation_bridge']['boundary']}")
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def write_run_artifacts(run_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    summary_path = run_dir / "summary.json"
    readme_path = run_dir / "README.md"
    write_json(summary_path, payload)
    write_text(readme_path, render_markdown(payload))
    fieldnames = [
        "rank",
        "strategy",
        "kind",
        "family_id",
        "scenario_count",
        "mean_score",
        "median_score",
        "mean_delivered_flow",
        "mean_failure_tolerance",
        "mean_material_proxy",
        "mean_energy_proxy",
        "mean_risk_exposure",
    ]
    write_csv(run_dir / "development_leaderboard.csv", payload["development_replay"]["leaderboard"], fieldnames)
    write_csv(run_dir / "validation_leaderboard.csv", payload["validation_replay"]["leaderboard"], fieldnames)
    write_csv(run_dir / "context_leaderboard.csv", payload["context_only_replay"]["leaderboard"], fieldnames)
    manifest = {
        "schema": "branching_live_breadth_replay_manifest_v1",
        "generated_utc": payload["generated_utc"],
        "files": {},
    }
    for path in [
        summary_path,
        readme_path,
        run_dir / "development_leaderboard.csv",
        run_dir / "validation_leaderboard.csv",
        run_dir / "context_leaderboard.csv",
    ]:
        manifest["files"][path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    manifest_path = run_dir / "manifest.sha256.json"
    write_json(manifest_path, manifest)
    return manifest


def build_payload(run_tag: str | None = None) -> dict[str, Any]:
    generated_utc = now_utc()
    live_breadth = read_json(LIVE_BREADTH)
    queue = read_json(GEOMETRY_QUEUE)
    intake = read_json(LOCAL_INTAKE)
    work_order = branching_work_order(queue)
    rows = source_rows_for_replay(live_breadth, work_order)
    live_rows = rows["live_rows"]
    context_rows = rows["context_rows"]

    development_scenarios = build_replay_scenarios(live_rows, split="development", fold_count=3, seed_offset=7100)
    validation_scenarios = build_replay_scenarios(live_rows, split="validation", fold_count=5, seed_offset=9700)
    context_scenarios = build_replay_scenarios(context_rows, split="context_only_blocked", fold_count=2, seed_offset=13100)

    _, development_leaderboard, development_gate = evaluate_scenarios(development_scenarios)
    _, validation_leaderboard, validation_gate = evaluate_scenarios(validation_scenarios)
    _, context_leaderboard, context_gate = evaluate_scenarios(context_scenarios)

    live_annual = sum(as_float(row.get("estimated_annual_value_usd")) for row in live_rows)
    live_hourly = sum(as_float(row.get("estimated_hourly_value_usd")) for row in live_rows)
    context_annual = sum(as_float(row.get("estimated_annual_value_usd")) for row in context_rows)
    context_hourly = sum(as_float(row.get("estimated_hourly_value_usd")) for row in context_rows)
    payload = {
        "schema": "branching_live_breadth_replay_v1",
        "generated_utc": generated_utc,
        "run_tag": run_tag or now_tag(),
        "family_id": TARGET_FAMILY,
        "lane": TARGET_LANE,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "work_order": work_order,
        "source_summary": {
            "live_source_manifest": source_manifest(live_rows),
            "context_source_manifest": source_manifest(context_rows),
            "all_source_manifest": source_manifest(rows["all_rows"]),
            "live_measured_estimated_hourly_value_usd": round(live_hourly, 2),
            "live_measured_estimated_annual_value_usd": round(live_annual, 2),
            "context_only_estimated_hourly_value_usd": round(context_hourly, 2),
            "context_only_estimated_annual_value_usd": round(context_annual, 2),
        },
        "development_replay": {
            "scenario_manifest": scenario_manifest(development_scenarios),
            "leaderboard": development_leaderboard,
            "gate": development_gate,
        },
        "validation_replay": {
            "scenario_manifest": scenario_manifest(validation_scenarios),
            "leaderboard": validation_leaderboard,
            "gate": validation_gate,
        },
        "context_only_replay": {
            "scenario_manifest": scenario_manifest(context_scenarios),
            "leaderboard": context_leaderboard,
            "gate": context_gate,
            "claim_status": "blocked_target_discovery_only",
        },
        "promotion_gate": promotion_gate(live_rows, context_rows, validation_gate),
        "historical_valuation_bridge": intake_bridge_summary(intake),
        "inputs": {
            "live_breadth": rel(LIVE_BREADTH),
            "geometry_queue": rel(GEOMETRY_QUEUE),
            "local_intake": rel(LOCAL_INTAKE),
        },
    }
    return payload


def write_outputs(payload: dict[str, Any]) -> dict[str, Any]:
    run_dir = RUN_ROOT / payload["run_tag"]
    manifest = write_run_artifacts(run_dir, payload)
    payload = {**payload, "run_dir": rel(run_dir), "artifact_manifest": manifest}
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


def main() -> int:
    payload = write_outputs(build_payload())
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "run_dir": payload["run_dir"],
                "live_sources": payload["source_summary"]["live_source_manifest"]["sources"],
                "validation_gate": payload["validation_replay"]["gate"].get("gate"),
                "ready_for_live_geometry_claim": payload["promotion_gate"]["ready_for_live_geometry_claim"],
                "ready_for_real_dollar_claim": payload["promotion_gate"]["ready_for_real_dollar_claim"],
                "json": rel(OUT_JSON),
                "dashboard_json": rel(DASHBOARD_JSON),
                "markdown": rel(OUT_MD),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
