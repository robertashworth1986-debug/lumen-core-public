from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DATA = ROOT / "dashboard" / "data"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"

LOCKED_SWEEP = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
REGISTRY = ROOT / "config" / "geometry_championship_v1_registry.json"
OUT_JSON = OUT_OPS / "baseline_gauntlet_coverage_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "baseline_gauntlet_coverage.json"
OUT_MD = DOCS / "BASELINE_GAUNTLET_COVERAGE_2026-07-03.md"


REQUESTED_BASELINES: list[dict[str, Any]] = [
    {"id": "persistence", "label": "Persistence / last-value forecast", "packages": []},
    {"id": "rolling_mean", "label": "Rolling mean", "packages": []},
    {"id": "ewma", "label": "Exponential smoothing / EWMA", "packages": []},
    {"id": "arima", "label": "ARIMA or SARIMAX", "packages": ["statsmodels"]},
    {"id": "seasonal_naive", "label": "Seasonal naive", "packages": []},
    {"id": "holt_winters_ets", "label": "Holt-Winters / ETS", "packages": ["statsmodels"]},
    {"id": "kalman_filter", "label": "Kalman filter", "packages": []},
    {"id": "extended_kalman_filter", "label": "Extended Kalman filter", "packages": ["filterpy"]},
    {"id": "unscented_kalman_filter", "label": "Unscented Kalman filter", "packages": ["filterpy"]},
    {"id": "particle_filter", "label": "Particle filter", "packages": []},
    {"id": "gaussian_process_regression", "label": "Gaussian process regression", "packages": ["sklearn"]},
    {"id": "xgboost", "label": "Gradient boosting: XGBoost", "packages": ["xgboost"]},
    {"id": "lightgbm", "label": "Gradient boosting: LightGBM", "packages": ["lightgbm"]},
    {"id": "random_forest_regression", "label": "Random forest regression", "packages": ["sklearn"]},
    {"id": "lstm", "label": "LSTM forecast", "packages": ["tensorflow"]},
    {"id": "tcn", "label": "TCN forecast", "packages": ["tensorflow"]},
    {"id": "small_transformer_forecast", "label": "Small transformer forecast", "packages": ["tensorflow"]},
    {"id": "model_predictive_control", "label": "Model predictive control baseline", "packages": ["scipy"]},
    {"id": "dijkstra", "label": "Dijkstra routing baseline", "packages": ["networkx"]},
    {"id": "a_star", "label": "A* routing baseline", "packages": ["networkx"]},
    {"id": "min_cost_flow", "label": "Min-cost flow routing baseline", "packages": ["networkx"]},
    {"id": "dc_power_flow", "label": "DC power-flow baseline", "packages": ["scipy"]},
    {"id": "opf", "label": "OPF baseline", "packages": ["scipy"]},
    {"id": "ieee_39_bus", "label": "IEEE 39-bus grid benchmark case", "packages": []},
    {"id": "ieee_118_bus", "label": "IEEE 118-bus grid benchmark case", "packages": []},
    {"id": "ieee_300_bus", "label": "IEEE 300-bus grid benchmark case", "packages": []},
    {"id": "kuramoto_order_parameter", "label": "Kuramoto order parameter", "packages": ["numpy"]},
    {"id": "kuramoto_critical_coupling", "label": "Kuramoto critical coupling threshold", "packages": ["numpy"]},
    {"id": "kuramoto_phase_bound_stress", "label": "Kuramoto phase-bound stress tests", "packages": ["numpy"]},
]


ALIASES: dict[str, tuple[str, ...]] = {
    "persistence": ("persistence",),
    "rolling_mean": ("rolling_mean",),
    "ewma": ("ewma",),
    "arima": ("arima", "sarimax"),
    "seasonal_naive": ("seasonal_naive",),
    "holt_winters_ets": ("holt_winters_ets", "holt_winters", "ets"),
    "kalman_filter": ("kalman_filter", "scalar_kalman_filter"),
    "extended_kalman_filter": ("extended_kalman_filter", "ekf"),
    "unscented_kalman_filter": ("unscented_kalman_filter", "ukf"),
    "particle_filter": ("particle_filter",),
    "gaussian_process_regression": ("gaussian_process_regression", "gaussian_process", "gpr"),
    "xgboost": ("xgboost", "xgb"),
    "lightgbm": ("lightgbm", "lgbm"),
    "random_forest_regression": ("random_forest_regression", "random_forest"),
    "lstm": ("lstm",),
    "tcn": ("tcn",),
    "small_transformer_forecast": ("small_transformer_forecast", "transformer_forecast"),
    "model_predictive_control": ("model_predictive_control",),
    "dijkstra": ("dijkstra",),
    "a_star": ("a_star", "astar", "a*"),
    "min_cost_flow": ("min_cost_flow",),
    "dc_power_flow": ("dc_power_flow", "dc_power"),
    "opf": ("opf", "optimal_power_flow"),
    "ieee_39_bus": ("ieee_39_bus", "ieee_39"),
    "ieee_118_bus": ("ieee_118_bus", "ieee_118"),
    "ieee_300_bus": ("ieee_300_bus", "ieee_300"),
    "kuramoto_order_parameter": ("kuramoto_order_parameter",),
    "kuramoto_critical_coupling": ("kuramoto_critical_coupling",),
    "kuramoto_phase_bound_stress": ("kuramoto_phase_bound_stress", "phase_bound_stress"),
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


def stable_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def collect_locked_baselines(sweep: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for route in sweep.get("route_results", []) or []:
        if not isinstance(route, dict):
            continue
        comparisons = route.get("comparisons") or []
        if not isinstance(comparisons, list):
            continue
        for comparison in comparisons:
            if not isinstance(comparison, dict):
                continue
            key = str(comparison.get("baseline_family") or "").strip()
            if not key:
                continue
            item = out.setdefault(
                key,
                {
                    "baseline": key,
                    "lanes": set(),
                    "baseline_comparison_count": 0,
                    "candidate_win_count": 0,
                    "estimated_rows": 0,
                    "numeric_samples": 0,
                },
            )
            item["lanes"].add(str(route.get("lane", "")))
            item["baseline_comparison_count"] += 1
            item["candidate_win_count"] += 1 if comparison.get("candidate_beats_baseline") else 0
            item["estimated_rows"] += int(route.get("estimated_rows") or 0)
            item["numeric_samples"] += int(route.get("numeric_samples") or 0)
    for item in out.values():
        item["lanes"] = sorted(item["lanes"])
    return out


def collect_registry_baselines(registry: dict[str, Any]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    lanes = registry.get("lanes", {})
    if not isinstance(lanes, dict):
        return out
    for lane_name, lane in lanes.items():
        if not isinstance(lane, dict):
            continue
        for baseline in lane.get("baselines", []) or []:
            out.setdefault(str(baseline), []).append(str(lane_name))
    return {key: sorted(set(value)) for key, value in out.items()}


def match_aliases(target_id: str, haystack: dict[str, Any] | dict[str, list[str]]) -> list[str]:
    aliases = ALIASES.get(target_id, (target_id,))
    return [alias for alias in aliases if alias in haystack]


def build_payload() -> dict[str, Any]:
    sweep = read_json(LOCKED_SWEEP)
    registry = read_json(REGISTRY)
    locked = collect_locked_baselines(sweep)
    registered = collect_registry_baselines(registry)
    packages = sorted({pkg for row in REQUESTED_BASELINES for pkg in row["packages"]})
    package_status = {pkg: module_available(pkg) for pkg in packages}

    rows: list[dict[str, Any]] = []
    for request in REQUESTED_BASELINES:
        target_id = request["id"]
        locked_keys = match_aliases(target_id, locked)
        registered_keys = match_aliases(target_id, registered)
        required_packages = request["packages"]
        missing_packages = [pkg for pkg in required_packages if not package_status.get(pkg, False)]
        if locked_keys:
            status = "EXECUTED_IN_LOCKED_REPLAY"
        elif registered_keys:
            status = "REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED"
        elif missing_packages:
            status = "BLOCKED_BY_MISSING_PACKAGE_OR_DATASET"
        else:
            status = "IMPLEMENTATION_NEEDED"
        locked_infos = [locked[key] for key in locked_keys if key in locked]
        lanes = sorted({lane for item in locked_infos for lane in item.get("lanes", [])})
        rows.append(
            {
                "id": target_id,
                "label": request["label"],
                "status": status,
                "matched_locked_baseline": locked_keys[0] if locked_keys else None,
                "matched_locked_baselines": locked_keys,
                "matched_registry_baseline": registered_keys[0] if registered_keys else None,
                "matched_registry_baselines": registered_keys,
                "lanes_executed": lanes,
                "baseline_comparison_count": sum(int(item.get("baseline_comparison_count") or 0) for item in locked_infos),
                "candidate_win_count": sum(int(item.get("candidate_win_count") or 0) for item in locked_infos),
                "estimated_rows_replayed": sum(int(item.get("estimated_rows") or 0) for item in locked_infos),
                "numeric_samples": sum(int(item.get("numeric_samples") or 0) for item in locked_infos),
                "required_packages": required_packages,
                "missing_packages": missing_packages,
            }
        )

    summary = {
        "requested_baselines": len(rows),
        "executed_in_locked_replay": sum(1 for row in rows if row["status"] == "EXECUTED_IN_LOCKED_REPLAY"),
        "registered_not_adapter_executed": sum(
            1 for row in rows if row["status"] == "REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED"
        ),
        "blocked_by_missing_package_or_dataset": sum(
            1 for row in rows if row["status"] == "BLOCKED_BY_MISSING_PACKAGE_OR_DATASET"
        ),
        "implementation_needed": sum(1 for row in rows if row["status"] == "IMPLEMENTATION_NEEDED"),
        "locked_replay_baseline_comparisons": int(sweep.get("summary", {}).get("baseline_comparison_count") or 0),
        "locked_replay_candidate_wins": int(sweep.get("summary", {}).get("candidate_win_count") or 0),
        "locked_replay_estimated_rows": int(sweep.get("summary", {}).get("estimated_rows_replayed") or 0),
        "locked_replay_numeric_samples": int(sweep.get("summary", {}).get("numeric_samples_read") or 0),
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "attribution_scope": (
            "Per-baseline comparisons and candidate wins are counted from route-level comparison rows. "
            "Rows replayed are per-baseline exposure counts and should not be summed as unique global rows."
        ),
    }
    payload = {
        "schema": "baseline_gauntlet_coverage_v1",
        "generated_utc": now_utc(),
        "boundary": (
            "Baseline coverage audit only. EXECUTED means present in the locked source-conditioned replay feed. "
            "REGISTERED means named in the benchmark registry but not run by the current adapter. Per-baseline "
            "comparison and win counts come from route-level comparison rows where available. Missing advanced "
            "adapters or IEEE cases must be added before those baselines can be claimed as tested. This is not "
            "field validation or realized savings."
        ),
        "inputs": {
            "locked_sweep": str(LOCKED_SWEEP.relative_to(ROOT)).replace("\\", "/"),
            "registry": str(REGISTRY.relative_to(ROOT)).replace("\\", "/"),
        },
        "summary": summary,
        "package_status": package_status,
        "executed_baseline_ids": [row["id"] for row in rows if row["status"] == "EXECUTED_IN_LOCKED_REPLAY"],
        "registered_not_executed_ids": [
            row["id"] for row in rows if row["status"] == "REGISTERED_BASELINE_NOT_ADAPTER_EXECUTED"
        ],
        "implementation_needed_ids": [row["id"] for row in rows if row["status"] == "IMPLEMENTATION_NEEDED"],
        "baseline_rows": rows,
    }
    payload["summary"]["baseline_gauntlet_sha256"] = stable_sha256(
        {"summary": payload["summary"], "baseline_rows": payload["baseline_rows"], "package_status": package_status}
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Baseline Gauntlet Coverage",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["boundary"],
        "",
        "## Summary",
        "",
        f"- Requested baselines: `{summary['requested_baselines']}`",
        f"- Executed in locked replay: `{summary['executed_in_locked_replay']}`",
        f"- Registered but not adapter-executed: `{summary['registered_not_adapter_executed']}`",
        f"- Blocked by missing package/dataset: `{summary['blocked_by_missing_package_or_dataset']}`",
        f"- Implementation needed: `{summary['implementation_needed']}`",
        f"- Locked replay comparisons: `{summary['locked_replay_baseline_comparisons']}`",
        f"- Locked replay candidate wins: `{summary['locked_replay_candidate_wins']}`",
        f"- Locked replay estimated rows: `{summary['locked_replay_estimated_rows']}`",
        f"- Locked replay numeric samples: `{summary['locked_replay_numeric_samples']}`",
        f"- Attribution scope: {summary['attribution_scope']}",
        f"- SHA-256: `{summary['baseline_gauntlet_sha256']}`",
        "",
        "## Package Status",
        "",
    ]
    for pkg, ok in payload["package_status"].items():
        lines.append(f"- `{pkg}`: `{'available' if ok else 'missing'}`")
    lines.extend(
        [
            "",
            "## Requested Baselines",
            "",
            "| Baseline | Status | Matched Replay Baselines | Route Comparisons | Candidate Wins | Row Exposure | Lanes | Missing Packages |",
            "| --- | --- | --- | ---: | ---: | ---: | --- | --- |",
        ]
    )
    for row in payload["baseline_rows"]:
        missing = ", ".join(row["missing_packages"]) if row["missing_packages"] else ""
        matched = ", ".join(row.get("matched_locked_baselines") or row.get("matched_registry_baselines") or [])
        lanes = ", ".join(row.get("lanes_executed") or [])
        lines.append(
            f"| {row['label']} | `{row['status']}` | `{matched}` | `{row['baseline_comparison_count']}` | "
            f"`{row['candidate_win_count']}` | `{row['estimated_rows_replayed']}` | `{lanes}` | `{missing}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- Executed locked replay coverage now includes classical forecast baselines, ETS/Holt-Winters, ARIMA, scalar/standard Kalman plus EKF/UKF/particle filters, Gaussian process, random forest, XGBoost, LightGBM, and min-cost-flow routing.",
            "- MPC, Dijkstra, and A* are registered in the geometry registry but are not executed by this locked replay adapter yet.",
            "- LSTM/TCN/small-transformer forecasts, DC power-flow/OPF, IEEE 39/118/300 bus cases, and explicit Kuramoto order/coupling/phase-bound metrics still need adapters or accepted benchmark files.",
            "- This strengthens the technical validation story, but it still does not authorize field-validation, realized-savings, trading-profit, safety, medical, or certification claims.",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(render_markdown(payload).rstrip("\r\n") + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
