from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

FRONTIER_JSON = OUT_OPS / "geometry_live_systems_frontier_latest.json"
ACTION_LEDGER_JSON = OUT_OPS / "geometry_action_replay_ledger_latest.json"

OUT_JSON = OUT_OPS / "geometry_live_source_manifest_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_live_source_manifest.json"
OUT_MD = DOCS / "GEOMETRY_LIVE_SOURCE_MANIFEST_2026-06-26.md"

BOUNDARY = (
    "Geometry live source manifest only. It maps local/uploaded/live snapshot files to candidate benchmark lanes. "
    "A row in this manifest is not a validated result, not field validation, not a clinical claim, not a trading signal, "
    "and not a real-dollar savings claim."
)

LANE_PLANS = {
    "optimal_curve_transport": {
        "candidate": "brachistochrone_descent",
        "baseline": "minimum_jerk_curve",
        "runner": "python code\\geometry_optimal_curve_transport_benchmark.py",
        "metric": "travel_time_at_equal_constraints",
        "adapter_status": "runner_exists_needs_source_specific_adapter",
    },
    "wave_resonance_timing": {
        "candidate": "kuramoto_phase_coupling",
        "baseline": "kalman_filter",
        "runner": "python code\\geometry_wave_resonance_timing_benchmark.py",
        "metric": "phase_error_or_forecast_residual_under_equal_windows",
        "adapter_status": "runner_exists_needs_source_specific_adapter",
    },
    "thermal_ventilation": {
        "candidate": "thermal_plume_convection",
        "baseline": "straight_duct",
        "runner": "python code\\geometry_thermal_ventilation_benchmark.py",
        "metric": "temperature_uniformity_and_energy_proxy",
        "adapter_status": "runner_exists_needs_source_specific_adapter",
    },
    "branching_transport": {
        "candidate": "leaf_veins",
        "baseline": "minimum_spanning_tree",
        "runner": "python code\\geometry_branching_transport_benchmark.py",
        "metric": "delivered_flow_and_failure_tolerance",
        "adapter_status": "runner_exists_needs_source_specific_adapter",
    },
    "energy_price_pressure_proxy": {
        "candidate": "phase_locked_residual_corrector",
        "baseline": "best_named_forecast_baseline",
        "runner": "python code\\ops\\BUILD_ENERGY_PRICE_PRESSURE_FORECAST.py",
        "metric": "price_pressure_or_load_residual_delta",
        "adapter_status": "proxy_runner_exists_keep_separate_from_geometry_claims",
    },
    "field_guided_control": {
        "candidate": "atmospheric_jet_stream_paths",
        "baseline": "potential_field_baseline",
        "runner": "",
        "metric": "time_saved_with_risk_penalty",
        "adapter_status": "adapter_required",
    },
    "mission_network_routing": {
        "candidate": "slime_mold_routing",
        "baseline": "dijkstra_shortest_path",
        "runner": "",
        "metric": "delivery_rate_after_edge_dropout",
        "adapter_status": "adapter_required",
    },
    "market_signal_geometry": {
        "candidate": "fractal_brownian_surface",
        "baseline": "autoregressive_baseline",
        "runner": "",
        "metric": "heldout_residual_or_risk_adjusted_forecast_error",
        "adapter_status": "adapter_required_no_live_execution",
    },
    "resource_aware_scheduling": {
        "candidate": "cicada_prime_cycles",
        "baseline": "fifo_or_round_robin_scheduler",
        "runner": "",
        "metric": "deadline_hit_rate_under_resource_limits",
        "adapter_status": "adapter_required",
    },
    "multi_agent_coordination": {
        "candidate": "role_coherence_routing",
        "baseline": "centralized_dispatch_baseline",
        "runner": "",
        "metric": "task_success_under_stale_or_partial_context",
        "adapter_status": "adapter_required",
    },
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
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


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def source_rows(frontier: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in as_list(frontier.get("local_live_file_inventory_sample")):
        if isinstance(row, dict):
            rows.append({**row, "source_kind": "local_file_inventory"})
    for row in as_list(frontier.get("provider_snapshot_files")):
        if isinstance(row, dict):
            rows.append({**row, "source_kind": "provider_snapshot_file"})
    rows.sort(key=lambda item: (-int(item.get("estimated_rows") or 0), str(item.get("path", ""))))
    return rows


def replay_evidence_by_lane(ledger: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("lane", "")): row
        for row in as_list(ledger.get("replay_rows"))
        if isinstance(row, dict) and row.get("lane")
    }


def build_manifest_rows(frontier: dict[str, Any], ledger: dict[str, Any]) -> list[dict[str, Any]]:
    replay_by_lane = replay_evidence_by_lane(ledger)
    rows: list[dict[str, Any]] = []
    for source in source_rows(frontier):
        lanes = as_list(source.get("candidate_lanes"))
        if not lanes:
            rows.append(
                {
                    "source_path": source.get("path", ""),
                    "source_kind": source.get("source_kind", ""),
                    "system": source.get("system", "unclassified_measured_file"),
                    "estimated_rows": source.get("estimated_rows", 0),
                    "lane": "",
                    "candidate_family": "",
                    "baseline_family": "",
                    "metric": "",
                    "adapter_status": "unclassified_needs_manual_lane_mapping",
                    "safe_runner": "",
                    "current_replay_delta": None,
                    "ready_for_benchmark": False,
                    "ready_for_claim": False,
                    "claim_boundary": "Unclassified local file; cannot support a claim until mapped to a lane and replayed.",
                }
            )
            continue
        for lane in lanes:
            plan = LANE_PLANS.get(str(lane), {})
            replay = replay_by_lane.get(str(lane), {})
            rows.append(
                {
                    "source_path": source.get("path", ""),
                    "source_kind": source.get("source_kind", ""),
                    "system": source.get("system", ""),
                    "estimated_rows": source.get("estimated_rows", 0),
                    "lane": lane,
                    "candidate_family": plan.get("candidate", ""),
                    "baseline_family": plan.get("baseline", ""),
                    "metric": plan.get("metric", ""),
                    "adapter_status": plan.get("adapter_status", "adapter_required"),
                    "safe_runner": plan.get("runner", ""),
                    "current_replay_delta": replay.get("score_delta_vs_best_baseline"),
                    "ready_for_benchmark": bool(plan.get("runner")),
                    "ready_for_claim": False,
                    "claim_boundary": "Mapped source candidate only; replay and claim gates remain required before field or dollar language.",
                }
            )
    rows.sort(
        key=lambda item: (
            not bool(item["ready_for_benchmark"]),
            -int(item.get("estimated_rows") or 0),
            str(item.get("lane", "")),
            str(item.get("source_path", "")),
        )
    )
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
        row["row_sha256"] = stable_sha256(row)
    return rows


def lane_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        lane = str(row.get("lane") or "unclassified")
        item = grouped.setdefault(
            lane,
            {
                "lane": lane,
                "candidate_family": row.get("candidate_family", ""),
                "baseline_family": row.get("baseline_family", ""),
                "source_count": 0,
                "estimated_rows": 0,
                "ready_for_benchmark_count": 0,
                "top_source_paths": [],
            },
        )
        item["source_count"] += 1
        item["estimated_rows"] += int(row.get("estimated_rows") or 0)
        if row.get("ready_for_benchmark"):
            item["ready_for_benchmark_count"] += 1
        if len(item["top_source_paths"]) < 6:
            item["top_source_paths"].append(row.get("source_path", ""))
    out = list(grouped.values())
    out.sort(key=lambda item: (-int(item["ready_for_benchmark_count"]), -int(item["estimated_rows"]), item["lane"]))
    return out


def build_payload() -> dict[str, Any]:
    frontier = read_json(FRONTIER_JSON)
    ledger = read_json(ACTION_LEDGER_JSON)
    rows = build_manifest_rows(frontier, ledger)
    materialized_rows = rows[:500]
    ready = [row for row in rows if row.get("ready_for_benchmark")]
    unclassified = [row for row in rows if row.get("lane") == ""]
    unique_sources: dict[str, int] = {}
    for row in rows:
        source_path = str(row.get("source_path", ""))
        if not source_path:
            continue
        unique_sources[source_path] = max(unique_sources.get(source_path, 0), int(row.get("estimated_rows") or 0))
    summary = {
        "manifest_row_count": len(materialized_rows),
        "discovered_manifest_row_count": len(rows),
        "manifest_rows_truncated": len(materialized_rows) < len(rows),
        "manifest_rows_omitted_count": len(rows) - len(materialized_rows),
        "ready_for_benchmark_row_count": len(ready),
        "unclassified_row_count": len(unclassified),
        "lane_count": len({row.get("lane") for row in rows if row.get("lane")}),
        "unique_source_count": len(unique_sources),
        "unique_source_estimated_rows": sum(unique_sources.values()),
        "estimated_rows_mapped": sum(int(row.get("estimated_rows") or 0) for row in rows if row.get("lane")),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "medical_or_addiction_treatment_claim_allowed": False,
        "manifest_sha256": stable_sha256(materialized_rows),
        "discovered_row_set_sha256": stable_sha256(rows),
    }
    return {
        "schema": "geometry_live_source_manifest_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": BOUNDARY,
        "inputs": {"frontier": rel(FRONTIER_JSON), "action_replay_ledger": rel(ACTION_LEDGER_JSON)},
        "outputs": {"json": rel(OUT_JSON), "dashboard_json": rel(DASHBOARD_JSON), "markdown": rel(OUT_MD)},
        "summary": summary,
        "lane_summary": lane_summary(rows),
        "manifest_rows": materialized_rows,
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
        },
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Live Source Manifest",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Manifest rows: `{summary['manifest_row_count']}`",
        f"- Discovered source-lane routes: `{summary['discovered_manifest_row_count']}`",
        f"- Manifest rows truncated: `{str(summary['manifest_rows_truncated']).lower()}`",
        f"- Omitted source-lane routes: `{summary['manifest_rows_omitted_count']}`",
        f"- Ready-for-benchmark rows: `{summary['ready_for_benchmark_row_count']}`",
        f"- Unclassified rows: `{summary['unclassified_row_count']}`",
        f"- Mapped lanes: `{summary['lane_count']}`",
        f"- Unique source files: `{summary['unique_source_count']}`",
        f"- Unique source estimated rows: `{summary['unique_source_estimated_rows']}`",
        f"- Estimated mapped rows: `{summary['estimated_rows_mapped']}`",
        "- Note: mapped rows are source-lane routes and may count the same source once per benchmark lane.",
        f"- Field validation claim allowed: `{str(summary['field_validation_claim_allowed']).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary['real_dollar_savings_claim_allowed']).lower()}`",
        f"- Live trading/autonomous execution allowed: `{str(summary['live_trading_or_autonomous_execution_allowed']).lower()}`",
        f"- Medical/addiction-treatment claim allowed: `{str(summary['medical_or_addiction_treatment_claim_allowed']).lower()}`",
        f"- Manifest SHA-256: `{summary['manifest_sha256']}`",
        f"- Full discovered-row-set SHA-256: `{summary['discovered_row_set_sha256']}`",
        "",
        "## Lane Summary",
        "",
        "| Lane | Candidate | Baseline | Sources | Rows | Ready Rows |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in payload["lane_summary"][:14]:
        lines.append(
            f"| `{row['lane']}` | `{row['candidate_family']}` | `{row['baseline_family']}` | "
            f"`{row['source_count']}` | `{row['estimated_rows']}` | `{row['ready_for_benchmark_count']}` |"
        )

    lines.extend(
        [
            "",
            "## Top Manifest Rows",
            "",
            "| Rank | System | Lane | Candidate | Baseline | Rows |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["manifest_rows"][:24]:
        lines.append(
            f"| `{row['rank']}` | `{row['system']}` | `{row['lane']}` | `{row['candidate_family']}` | "
            f"`{row['baseline_family']}` | `{row['estimated_rows']}` |"
        )

    lines.extend(
        [
            "",
            "## Boundaries",
            "",
            "- This manifest is a benchmark routing map, not a result.",
            "- Unclassified rows must be manually mapped or archived before use.",
            "- Mapped rows still need frozen source manifests, identical-baseline replay, and claim-gate review.",
            "- No field, medical, live-trading, fixed-dollar, or realized-savings claim is allowed from this manifest alone.",
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
