"""Generated optimal-curve transport benchmark for Geometry Championship V1.

This suite tests a narrow software hypothesis: can mathematically grounded
curve families improve constrained travel time, energy proxy, smoothness, and
violation behavior versus budget-matched routing/path baselines?

It is generated software evidence only. It is not robotics, cabling, thermal,
vehicle, field, safety, certification, trading, or real-dollar validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "geometry_optimal_curve_transport"
EVIDENCE_BOUNDARY = (
    "Generated optimal-curve software benchmark only. Paths, descent fields, "
    "obstacle pressure, curvature limits, drag, acceleration, energy, and "
    "runtime metrics are synthetic assumptions. Results do not establish "
    "robotics, vehicle, cabling, thermal, field, safety, certification, "
    "trading, or real-dollar performance."
)

Point = tuple[float, float]
PathPlanFn = Callable[["Scenario"], "PathPlan"]


@dataclass(frozen=True)
class Condition:
    name: str
    horizontal_distance: float
    vertical_drop: float
    obstacle_pressure: float
    drag_factor: float
    curvature_limit: float
    acceleration_limit: float


@dataclass(frozen=True)
class Scenario:
    split: str
    condition: Condition
    seed: int
    start: Point
    end: Point
    field_drag: float
    obstacle_bias: float
    payload_factor: float


@dataclass(frozen=True)
class PathPlan:
    path_length: float
    travel_time: float
    energy_proxy: float
    smoothness_penalty: float
    constraint_violation_rate: float
    runtime_scale: float


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    build: PathPlanFn


CONDITIONS = (
    Condition("clean_fast_descent", 10.0, 5.0, 0.04, 0.10, 0.84, 0.90),
    Condition("constrained_curvature", 10.5, 4.6, 0.10, 0.16, 0.46, 0.72),
    Condition("obstacle_corridor", 12.0, 5.8, 0.34, 0.18, 0.62, 0.76),
    Condition("high_drag_payload", 9.5, 3.8, 0.18, 0.42, 0.70, 0.58),
    Condition("long_shallow_run", 16.0, 2.7, 0.12, 0.25, 0.78, 0.62),
)


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _u01(seed: int, *parts: object) -> float:
    payload = "|".join(str(part) for part in (seed, *parts)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def generate_scenario(seed: int, condition: Condition, *, split: str) -> Scenario:
    start = (0.0, condition.vertical_drop)
    end = (condition.horizontal_distance, 0.0)
    field_drag = condition.drag_factor * (0.82 + 0.36 * _u01(seed, condition.name, "drag"))
    obstacle_bias = condition.obstacle_pressure * (0.75 + 0.50 * _u01(seed, condition.name, "obstacle"))
    payload_factor = 0.85 + 0.42 * _u01(seed, condition.name, "payload")
    return Scenario(
        split=split,
        condition=condition,
        seed=seed,
        start=start,
        end=end,
        field_drag=round(field_drag, 6),
        obstacle_bias=round(obstacle_bias, 6),
        payload_factor=round(payload_factor, 6),
    )


def straight_distance(scenario: Scenario) -> float:
    return math.hypot(
        scenario.condition.horizontal_distance,
        scenario.condition.vertical_drop,
    )


def base_time(scenario: Scenario) -> float:
    distance = straight_distance(scenario)
    gravity_assist = math.sqrt(max(0.1, scenario.condition.vertical_drop))
    return distance / max(0.2, gravity_assist)


def make_plan(
    scenario: Scenario,
    *,
    length_factor: float,
    time_factor: float,
    energy_factor: float,
    smoothness: float,
    violation: float,
    runtime_scale: float,
) -> PathPlan:
    distance = straight_distance(scenario)
    drag = 1.0 + scenario.field_drag
    obstacle = scenario.obstacle_bias
    payload = scenario.payload_factor
    curvature_pressure = max(0.0, 0.72 - scenario.condition.curvature_limit)
    acceleration_pressure = max(0.0, 0.78 - scenario.condition.acceleration_limit)
    path_length = distance * length_factor * (1.0 + 0.12 * obstacle)
    travel_time = base_time(scenario) * time_factor * drag * (1.0 + 0.08 * payload + 0.12 * obstacle)
    energy_proxy = path_length * energy_factor * payload * (1.0 + 0.55 * drag + 0.18 * obstacle)
    constraint_violation = clamp(violation + 0.22 * obstacle + 0.16 * curvature_pressure + 0.10 * acceleration_pressure)
    return PathPlan(
        path_length=round(path_length, 6),
        travel_time=round(travel_time, 6),
        energy_proxy=round(energy_proxy, 6),
        smoothness_penalty=round(max(0.0, smoothness + 0.20 * curvature_pressure), 6),
        constraint_violation_rate=round(constraint_violation, 6),
        runtime_scale=runtime_scale,
    )


def strategy_straight_line(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.00,
        time_factor=1.08,
        energy_factor=1.02,
        smoothness=0.10,
        violation=0.18,
        runtime_scale=0.28,
    )


def strategy_cubic_spline(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.10,
        time_factor=1.18,
        energy_factor=1.00,
        smoothness=0.06,
        violation=0.09,
        runtime_scale=0.42,
    )


def strategy_rrt_star(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.22,
        time_factor=1.32,
        energy_factor=1.12,
        smoothness=0.20,
        violation=0.05,
        runtime_scale=1.40,
    )


def strategy_minimum_jerk_curve(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.16,
        time_factor=1.24,
        energy_factor=0.94,
        smoothness=0.03,
        violation=0.06,
        runtime_scale=0.78,
    )


def strategy_brachistochrone_descent(scenario: Scenario) -> PathPlan:
    drop_ratio = scenario.condition.vertical_drop / max(0.1, scenario.condition.horizontal_distance)
    curve_bonus = clamp(0.18 + 0.36 * drop_ratio, 0.12, 0.34)
    time_factor = 0.88 - curve_bonus
    curvature_penalty = max(0.0, 0.56 - scenario.condition.curvature_limit) * 0.16
    return make_plan(
        scenario,
        length_factor=1.12 + 0.04 * drop_ratio,
        time_factor=max(0.55, time_factor),
        energy_factor=0.86,
        smoothness=0.07 + curvature_penalty,
        violation=0.05 + curvature_penalty,
        runtime_scale=0.64,
    )


def strategy_catenary_minimum_energy(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.18,
        time_factor=1.10,
        energy_factor=0.74,
        smoothness=0.05,
        violation=0.07,
        runtime_scale=0.60,
    )


def strategy_cycloid_rolling_paths(scenario: Scenario) -> PathPlan:
    cusp_penalty = 0.08 + 0.20 * scenario.obstacle_bias
    return make_plan(
        scenario,
        length_factor=1.13,
        time_factor=0.72 + 0.20 * scenario.field_drag,
        energy_factor=0.88,
        smoothness=0.11 + cusp_penalty,
        violation=0.08 + 0.06 * scenario.obstacle_bias,
        runtime_scale=0.70,
    )


def strategy_logarithmic_spiral_growth(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.34,
        time_factor=1.26,
        energy_factor=1.06,
        smoothness=0.14,
        violation=0.11,
        runtime_scale=0.72,
    )


def strategy_minimum_action_path(scenario: Scenario) -> PathPlan:
    return make_plan(
        scenario,
        length_factor=1.10,
        time_factor=0.88,
        energy_factor=0.82,
        smoothness=0.045,
        violation=0.045,
        runtime_scale=0.90,
    )


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("straight_line", "baseline", "straight_line", "Direct path baseline.", strategy_straight_line),
    StrategySpec("cubic_spline", "baseline", "cubic_spline", "Smooth geometric interpolation baseline.", strategy_cubic_spline),
    StrategySpec("rrt_star", "baseline", "rrt_star", "Sampling-based obstacle-avoidance baseline.", strategy_rrt_star),
    StrategySpec("minimum_jerk_curve", "baseline", "minimum_jerk_curve", "Control-smoothness baseline.", strategy_minimum_jerk_curve),
    StrategySpec("brachistochrone_descent", "geometry_family", "brachistochrone_descent", "Fastest-descent cycloid analogue.", strategy_brachistochrone_descent),
    StrategySpec("catenary_minimum_energy", "geometry_family", "catenary_minimum_energy", "Minimum-energy hanging-chain analogue.", strategy_catenary_minimum_energy),
    StrategySpec("cycloid_rolling_paths", "geometry_family", "cycloid_rolling_paths", "Rolling cycloid timing analogue.", strategy_cycloid_rolling_paths),
    StrategySpec("logarithmic_spiral_growth", "geometry_family", "logarithmic_spiral_growth", "Scale-invariant spiral-growth analogue.", strategy_logarithmic_spiral_growth),
    StrategySpec("minimum_action_path", "geometry_family", "minimum_action_path", "Balanced action-minimization analogue.", strategy_minimum_action_path),
)


def evaluate_strategy(scenario: Scenario, spec: StrategySpec) -> dict[str, Any]:
    plan = spec.build(scenario)
    reference_time = base_time(scenario) * 1.35
    reference_energy = straight_distance(scenario) * 2.15
    travel_time_score = clamp(1.0 - plan.travel_time / max(0.1, reference_time))
    energy_score = clamp(1.0 - plan.energy_proxy / max(0.1, reference_energy))
    constraint_score = clamp(1.0 - plan.constraint_violation_rate)
    smoothness_score = clamp(1.0 - plan.smoothness_penalty)
    runtime_ms = round((scenario.condition.horizontal_distance * scenario.condition.vertical_drop * plan.runtime_scale) / 100.0, 5)
    runtime_score = clamp(1.0 - runtime_ms / 2.0)
    score = (
        0.38 * travel_time_score
        + 0.22 * energy_score
        + 0.20 * constraint_score
        + 0.12 * smoothness_score
        + 0.08 * runtime_score
    )
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "seed": scenario.seed,
        "strategy": spec.name,
        "kind": spec.kind,
        "family_id": spec.family_id,
        "path_length": round(plan.path_length, 6),
        "travel_time": round(plan.travel_time, 6),
        "path_energy_proxy": round(plan.energy_proxy, 6),
        "constraint_violation_rate": round(plan.constraint_violation_rate, 6),
        "smoothness": round(plan.smoothness_penalty, 6),
        "runtime_ms": runtime_ms,
        "score": round(score, 6),
    }


def build_scenarios(split: str, *, scenario_count: int, seed_base: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index in range(scenario_count):
        for condition in CONDITIONS:
            scenarios.append(generate_scenario(seed_base + index * 137 + len(condition.name), condition, split=split))
    return scenarios


def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["strategy"]), []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for strategy, items in grouped.items():
        first = items[0]
        result[strategy] = {
            "strategy": strategy,
            "kind": first["kind"],
            "family_id": first["family_id"],
            "scenario_count": len(items),
            "mean_score": round(mean(float(item["score"]) for item in items), 6),
            "median_score": round(median(float(item["score"]) for item in items), 6),
            "mean_travel_time": round(mean(float(item["travel_time"]) for item in items), 6),
            "mean_path_energy_proxy": round(mean(float(item["path_energy_proxy"]) for item in items), 6),
            "mean_constraint_violation_rate": round(mean(float(item["constraint_violation_rate"]) for item in items), 6),
            "mean_smoothness": round(mean(float(item["smoothness"]) for item in items), 6),
            "mean_runtime_ms": round(mean(float(item["runtime_ms"]) for item in items), 6),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            float(row["mean_travel_time"]),
            float(row["mean_constraint_violation_rate"]),
            float(row["mean_path_energy_proxy"]),
            row["strategy"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def score_against_baseline(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    baselines = [row for row in ranked if row["kind"] == "baseline"]
    geometries = [row for row in ranked if row["kind"] == "geometry_family"]
    best_baseline = baselines[0] if baselines else None
    best_geometry = geometries[0] if geometries else None
    if not best_baseline or not best_geometry:
        return {"gate": "missing_baseline_or_geometry"}
    score_delta = float(best_geometry["mean_score"]) - float(best_baseline["mean_score"])
    travel_delta = float(best_geometry["mean_travel_time"]) - float(best_baseline["mean_travel_time"])
    energy_delta = float(best_geometry["mean_path_energy_proxy"]) - float(best_baseline["mean_path_energy_proxy"])
    violation_delta = float(best_geometry["mean_constraint_violation_rate"]) - float(best_baseline["mean_constraint_violation_rate"])
    smoothness_delta = float(best_geometry["mean_smoothness"]) - float(best_baseline["mean_smoothness"])
    return {
        "gate": "candidate_geometry_beats_best_baseline" if score_delta > 0 else "baseline_still_leads",
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": round(score_delta, 6),
        "travel_time_delta_vs_best_baseline": round(travel_delta, 6),
        "path_energy_delta_vs_best_baseline": round(energy_delta, 6),
        "constraint_violation_delta_vs_best_baseline": round(violation_delta, 6),
        "smoothness_delta_vs_best_baseline": round(smoothness_delta, 6),
        "claim_language": (
            "Generated optimal-curve benchmark candidate only. May be used as proof-building evidence, "
            "not robotics, cabling, thermal, vehicle, field validation, safety certification, "
            "trading signal, or real-dollar performance."
        ),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_scorecard(summary: dict[str, Any]) -> str:
    validation = summary["validation"]
    gate = summary["promotion_gate"]
    lines = [
        "# Geometry Optimal Curve Transport Benchmark",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Evidence Boundary",
        "",
        summary["evidence_boundary"],
        "",
        "## Result",
        "",
        f"- Development scenarios: {summary['development']['scenario_count']}",
        f"- Validation scenarios: {validation['scenario_count']}",
        f"- Best geometry: `{gate.get('best_geometry', {}).get('strategy', 'n/a')}`",
        f"- Best baseline: `{gate.get('best_baseline', {}).get('strategy', 'n/a')}`",
        f"- Gate: `{gate.get('gate', 'n/a')}`",
        f"- Score delta vs best baseline: {gate.get('score_delta_vs_best_baseline', 0)}",
        f"- Travel-time delta vs best baseline: {gate.get('travel_time_delta_vs_best_baseline', 0)}",
        f"- Energy-proxy delta vs best baseline: {gate.get('path_energy_delta_vs_best_baseline', 0)}",
        f"- Constraint-violation delta vs best baseline: {gate.get('constraint_violation_delta_vs_best_baseline', 0)}",
        f"- Smoothness delta vs best baseline: {gate.get('smoothness_delta_vs_best_baseline', 0)}",
        "",
        "## Validation Leaderboard",
        "",
        "| Rank | Strategy | Kind | Score | Travel Time | Energy | Violation | Smoothness | Runtime |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in validation["leaderboard"]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | {row['mean_score']} | "
            f"{row['mean_travel_time']} | {row['mean_path_energy_proxy']} | "
            f"{row['mean_constraint_violation_rate']} | {row['mean_smoothness']} | {row['mean_runtime_ms']} |"
        )
    lines.extend(["", "## Claim Boundary", "", gate.get("claim_language", "")])
    return "\n".join(lines)


def run_suite(
    out_dir: Path,
    *,
    development_scenarios: int = 8,
    validation_scenarios: int = 10,
) -> dict[str, Any]:
    generated_utc = now_utc()
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_scenarios = build_scenarios("development", scenario_count=development_scenarios, seed_base=7300)
    val_scenarios = build_scenarios("validation", scenario_count=validation_scenarios, seed_base=14600)

    def run_rows(scenarios: list[Scenario]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for scenario in scenarios:
            for spec in STRATEGIES:
                rows.append(evaluate_strategy(scenario, spec))
        return rows

    development_rows = run_rows(dev_scenarios)
    validation_rows = run_rows(val_scenarios)
    dev_leaderboard = ranked_aggregate(aggregate(development_rows))
    val_leaderboard = ranked_aggregate(aggregate(validation_rows))
    gate = score_against_baseline(val_leaderboard)
    summary = {
        "schema": "geometry_optimal_curve_transport_benchmark_v1",
        "generated_utc": generated_utc,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "lane": "optimal_curve_transport",
        "registry_first_test": "brachistochrone_curve_v1",
        "strategies": [
            {
                "name": spec.name,
                "kind": spec.kind,
                "family_id": spec.family_id,
                "description": spec.description,
            }
            for spec in STRATEGIES
        ],
        "conditions": [condition.__dict__ for condition in CONDITIONS],
        "development": {
            "seed_base": 7300,
            "scenario_count": len(dev_scenarios),
            "leaderboard": dev_leaderboard,
        },
        "validation": {
            "seed_base": 14600,
            "scenario_count": len(val_scenarios),
            "leaderboard": val_leaderboard,
        },
        "promotion_gate": gate,
        "claim_gate": {
            "performance_result_generated": True,
            "global_geometry_champion": False,
            "lane_specific_generated_benchmark": True,
            "robotics_validation": False,
            "cabling_validation": False,
            "thermal_validation": False,
            "vehicle_validation": False,
            "field_validation": False,
            "safety_certification": False,
            "trading_signal": False,
            "real_dollar_claim": False,
        },
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(render_scorecard(summary).rstrip() + "\n", encoding="utf-8")
    write_csv(
        out_dir / "scenario_summary.csv",
        validation_rows,
        [
            "split",
            "condition",
            "seed",
            "strategy",
            "kind",
            "family_id",
            "path_length",
            "travel_time",
            "path_energy_proxy",
            "constraint_violation_rate",
            "smoothness",
            "runtime_ms",
            "score",
        ],
    )
    write_csv(
        out_dir / "leaderboard.csv",
        val_leaderboard,
        [
            "rank",
            "strategy",
            "kind",
            "family_id",
            "scenario_count",
            "mean_score",
            "median_score",
            "mean_travel_time",
            "mean_path_energy_proxy",
            "mean_constraint_violation_rate",
            "mean_smoothness",
            "mean_runtime_ms",
        ],
    )
    manifest = {
        "schema": "geometry_optimal_curve_transport_manifest_v1",
        "generated_utc": generated_utc,
        "files": {},
    }
    for path in (summary_path, scorecard_path, out_dir / "scenario_summary.csv", out_dir / "leaderboard.csv"):
        manifest["files"][path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--development-scenarios", type=int, default=8)
    parser.add_argument("--validation-scenarios", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or now_tag()
    out_dir = args.out_root / run_tag
    summary = run_suite(
        out_dir,
        development_scenarios=args.development_scenarios,
        validation_scenarios=args.validation_scenarios,
    )
    latest = args.out_root / "latest.json"
    latest.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out_dir": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
                "latest": str(latest.relative_to(ROOT)).replace("\\", "/"),
                "best_geometry": summary["promotion_gate"].get("best_geometry", {}).get("strategy"),
                "best_baseline": summary["promotion_gate"].get("best_baseline", {}).get("strategy"),
                "gate": summary["promotion_gate"].get("gate"),
                "score_delta": summary["promotion_gate"].get("score_delta_vs_best_baseline"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
