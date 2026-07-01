"""Generated thermal-ventilation benchmark for Geometry Championship V1.

This suite tests a narrow software hypothesis: can nature-inspired thermal
flowforms improve heat uniformity, recovery, and energy/pressure tradeoffs
versus simple budget-matched ventilation baselines?

It is generated software evidence only. It is not datacenter, HVAC, CFD,
field, customer, safety, certification, or real-dollar validation.
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
from statistics import mean, median, pstdev
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "geometry_thermal_ventilation"
EVIDENCE_BOUNDARY = (
    "Generated thermal-grid software benchmark only. Heat loads, obstructions, "
    "airflow proxies, cooling maps, pressure, energy, and recovery metrics are "
    "synthetic assumptions. Results do not establish datacenter, HVAC, CFD, "
    "field, customer, safety, certification, or real-dollar performance."
)

Cell = tuple[int, int]
ThermalPlanFn = Callable[["Scenario"], "ThermalPlan"]


@dataclass(frozen=True)
class Condition:
    name: str
    width: int
    height: int
    hotspot_count: int
    heat_skew: float
    external_gradient: float
    fan_degrade: float
    obstruction_density: float


@dataclass(frozen=True)
class Scenario:
    split: str
    condition: Condition
    seed: int
    heat_load: dict[Cell, float]
    blocked_cells: set[Cell]
    ambient_c: float


@dataclass(frozen=True)
class ThermalPlan:
    cooling: dict[Cell, float]
    pressure_drop: float
    energy_proxy: float
    recovery_lag: float
    runtime_scale: float


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    build: ThermalPlanFn


CONDITIONS = (
    Condition("nominal_rack_row", 16, 10, 5, 0.26, 0.10, 0.05, 0.03),
    Condition("hotspot_cluster", 18, 11, 8, 0.70, 0.18, 0.12, 0.05),
    Condition("reversed_external_gradient", 16, 12, 7, 0.44, -0.42, 0.18, 0.06),
    Condition("dense_rack_obstructions", 18, 12, 9, 0.56, 0.24, 0.22, 0.12),
    Condition("fan_degraded_recovery", 17, 11, 7, 0.48, 0.16, 0.42, 0.07),
)


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _u01(seed: int, *parts: object) -> float:
    payload = "|".join(str(part) for part in (seed, *parts)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64)


def cells(width: int, height: int) -> Iterable[Cell]:
    for x in range(width):
        for y in range(height):
            yield (x, y)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def dist(a: Cell, b: Cell) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def nearest_distance(cell: Cell, points: Iterable[Cell]) -> float:
    values = [dist(cell, point) for point in points]
    return min(values) if values else 999.0


def generate_scenario(seed: int, condition: Condition, *, split: str) -> Scenario:
    width, height = condition.width, condition.height
    ambient = 23.0 + 2.0 * _u01(seed, condition.name, "ambient")
    center = (width * (0.55 + 0.12 * _u01(seed, condition.name, "cx")), height * (0.35 + 0.30 * _u01(seed, condition.name, "cy")))

    candidates: list[tuple[float, Cell]] = []
    for cell in cells(width, height):
        x, y = cell
        rack_lane = 0.25 * (1.0 if x % 3 == 1 else 0.0)
        center_pull = 1.0 / (1.0 + math.hypot(x - center[0], y - center[1]))
        score = center_pull + rack_lane + 0.55 * _u01(seed, condition.name, "hotspot", cell)
        candidates.append((score, cell))
    candidates.sort(reverse=True)
    hotspots = [cell for _, cell in candidates[: condition.hotspot_count]]

    blocked: set[Cell] = set()
    for cell in cells(width, height):
        if cell in hotspots:
            continue
        obstruction_score = 0.65 * _u01(seed, condition.name, "block", cell) + 0.35 * (1.0 if cell[0] % 4 == 2 else 0.0)
        if obstruction_score > 1.0 - condition.obstruction_density:
            blocked.add(cell)

    heat: dict[Cell, float] = {}
    for cell in cells(width, height):
        x, y = cell
        gradient = condition.external_gradient * (x / max(1, width - 1) - 0.5)
        rack_load = 0.50 + 0.30 * (1.0 if x % 3 == 1 else 0.0) + 0.20 * _u01(seed, condition.name, "rack", cell)
        hotspot_load = 0.0
        for index, hotspot in enumerate(hotspots):
            amplitude = 1.10 + condition.heat_skew * (1.0 + index / max(1, len(hotspots)))
            hotspot_load += amplitude * math.exp(-(dist(cell, hotspot) ** 2) / 6.5)
        heat[cell] = round(max(0.05, rack_load + gradient + hotspot_load), 5)
    return Scenario(split=split, condition=condition, seed=seed, heat_load=heat, blocked_cells=blocked, ambient_c=round(ambient, 4))


def heat_norm(scenario: Scenario, cell: Cell) -> float:
    loads = scenario.heat_load.values()
    lo = min(loads)
    hi = max(loads)
    return (scenario.heat_load[cell] - lo) / max(0.001, hi - lo)


def top_hotspots(scenario: Scenario, count: int) -> list[Cell]:
    return [
        cell
        for cell, _ in sorted(
            scenario.heat_load.items(),
            key=lambda item: (item[1], item[0][0], item[0][1]),
            reverse=True,
        )[:count]
    ]


def obstruction_penalty(scenario: Scenario, cell: Cell) -> float:
    if cell in scenario.blocked_cells:
        return 0.45
    return 0.12 / (1.0 + nearest_distance(cell, scenario.blocked_cells))


def build_cooling_map(scenario: Scenario, fn: Callable[[Cell], float]) -> dict[Cell, float]:
    return {cell: round(max(0.0, fn(cell) * (1.0 - obstruction_penalty(scenario, cell))), 6) for cell in scenario.heat_load}


def strategy_straight_duct(scenario: Scenario) -> ThermalPlan:
    width, height = scenario.condition.width, scenario.condition.height
    mid = (height - 1) / 2.0

    def cool(cell: Cell) -> float:
        x, y = cell
        band = math.exp(-((y - mid) ** 2) / max(1.0, height * 0.55))
        inlet_decay = 1.0 - 0.42 * (x / max(1, width - 1))
        return 0.88 + 0.82 * band * inlet_decay

    return ThermalPlan(
        cooling=build_cooling_map(scenario, cool),
        pressure_drop=0.34 + 0.80 * scenario.condition.obstruction_density,
        energy_proxy=1.00 + 0.35 * scenario.condition.fan_degrade,
        recovery_lag=7.4 + 2.4 * scenario.condition.fan_degrade,
        runtime_scale=0.55,
    )


def strategy_conventional_hvac_network(scenario: Scenario) -> ThermalPlan:
    width, height = scenario.condition.width, scenario.condition.height
    vents = [(width // 4, 1), (width // 2, height - 2), (3 * width // 4, 1), (width - 2, height // 2)]

    def cool(cell: Cell) -> float:
        radial = sum(math.exp(-(dist(cell, vent) ** 2) / 16.0) for vent in vents)
        return 0.82 + 0.62 * radial + 0.18 * heat_norm(scenario, cell)

    return ThermalPlan(
        cooling=build_cooling_map(scenario, cool),
        pressure_drop=0.46 + 0.92 * scenario.condition.obstruction_density,
        energy_proxy=1.28 + 0.48 * scenario.condition.fan_degrade,
        recovery_lag=5.6 + 1.8 * scenario.condition.fan_degrade,
        runtime_scale=0.85,
    )


def strategy_cfd_reference(scenario: Scenario) -> ThermalPlan:
    width, height = scenario.condition.width, scenario.condition.height
    hotspots = top_hotspots(scenario, max(3, scenario.condition.hotspot_count // 2))

    def cool(cell: Cell) -> float:
        targeted = sum(math.exp(-(dist(cell, hotspot) ** 2) / 9.0) for hotspot in hotspots)
        boundary = 0.18 * (1.0 - abs(cell[1] - height / 2.0) / max(1.0, height / 2.0))
        return 1.00 + 0.42 * heat_norm(scenario, cell) + 0.30 * targeted + boundary

    return ThermalPlan(
        cooling=build_cooling_map(scenario, cool),
        pressure_drop=0.60 + 1.05 * scenario.condition.obstruction_density,
        energy_proxy=1.72 + 0.55 * scenario.condition.fan_degrade,
        recovery_lag=3.9 + 1.0 * scenario.condition.fan_degrade,
        runtime_scale=1.45,
    )


def strategy_rayleigh_benard_cells(scenario: Scenario) -> ThermalPlan:
    width, height = scenario.condition.width, scenario.condition.height
    phase = _u01(scenario.seed, scenario.condition.name, "benard_phase") * math.pi
    reversed_penalty = 0.12 if scenario.condition.external_gradient < -0.25 else 0.0

    def cool(cell: Cell) -> float:
        x, y = cell
        cell_roll = abs(math.sin((x + 1) * math.pi / 4.0 + phase) * math.sin((y + 1) * math.pi / 3.0))
        vertical_exchange = 1.0 - abs(y - height / 2.0) / max(1.0, height / 2.0)
        return 0.92 + 0.70 * cell_roll + 0.28 * vertical_exchange + 0.12 * heat_norm(scenario, cell) - reversed_penalty

    return ThermalPlan(
        cooling=build_cooling_map(scenario, cool),
        pressure_drop=0.30 + 0.70 * scenario.condition.obstruction_density,
        energy_proxy=0.94 + 0.22 * scenario.condition.fan_degrade,
        recovery_lag=4.8 + 1.5 * scenario.condition.fan_degrade + 1.0 * reversed_penalty,
        runtime_scale=0.80,
    )


def strategy_termite_mound_ventilation(scenario: Scenario) -> ThermalPlan:
    width, height = scenario.condition.width, scenario.condition.height
    chimneys = [(width // 3, 0), (2 * width // 3, 0), (width // 2, height - 1)]
    gradient_help = 0.16 if scenario.condition.external_gradient >= 0 else -0.22

    def cool(cell: Cell) -> float:
        x, y = cell
        chimney = sum(math.exp(-(dist(cell, vent) ** 2) / 12.0) for vent in chimneys)
        stack = y / max(1, height - 1)
        wall_breathing = 0.24 * (1.0 - min(x, width - 1 - x) / max(1.0, width / 2.0))
        return 0.78 + 0.42 * chimney + 0.36 * stack + wall_breathing + gradient_help

    return ThermalPlan(
        cooling=build_cooling_map(scenario, cool),
        pressure_drop=0.18 + 0.38 * scenario.condition.obstruction_density,
        energy_proxy=0.62 + 0.12 * scenario.condition.fan_degrade,
        recovery_lag=5.0 + 2.1 * scenario.condition.fan_degrade + (1.8 if scenario.condition.external_gradient < 0 else 0.0),
        runtime_scale=0.62,
    )


def strategy_thermal_plume_convection(scenario: Scenario) -> ThermalPlan:
    width, height = scenario.condition.width, scenario.condition.height
    hotspots = top_hotspots(scenario, max(4, scenario.condition.hotspot_count))

    def cool(cell: Cell) -> float:
        x, y = cell
        plume = 0.0
        for hot_x, hot_y in hotspots:
            vertical = max(0.0, (y - hot_y + 2.0) / max(2.0, height))
            lateral = math.exp(-((x - hot_x) ** 2) / 7.0)
            plume += vertical * lateral
        plume = min(2.2, plume)
        return 0.64 + 0.42 * heat_norm(scenario, cell) + 0.62 * plume

    return ThermalPlan(
        cooling=build_cooling_map(scenario, cool),
        pressure_drop=0.23 + 0.54 * scenario.condition.obstruction_density,
        energy_proxy=0.82 + 0.18 * scenario.condition.fan_degrade,
        recovery_lag=4.2 + 1.1 * scenario.condition.fan_degrade,
        runtime_scale=0.92,
    )


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("straight_duct", "baseline", "straight_duct", "Simple horizontal duct baseline.", strategy_straight_duct),
    StrategySpec("conventional_hvac_network", "baseline", "conventional_hvac_network", "Distributed supply/return baseline.", strategy_conventional_hvac_network),
    StrategySpec("cfd_reference", "baseline", "cfd_reference", "High-energy synthetic optimized-cooling reference.", strategy_cfd_reference),
    StrategySpec("rayleigh_benard_cells", "geometry_family", "rayleigh_benard_cells", "Cellular convection analogue.", strategy_rayleigh_benard_cells),
    StrategySpec("termite_mound_ventilation", "geometry_family", "termite_mound_ventilation", "Passive chimney and wall-breathing analogue.", strategy_termite_mound_ventilation),
    StrategySpec("thermal_plume_convection", "geometry_family", "thermal_plume_convection", "Hotspot-driven vertical plume analogue.", strategy_thermal_plume_convection),
)


def evaluate_strategy(scenario: Scenario, spec: StrategySpec) -> dict[str, Any]:
    plan = spec.build(scenario)
    temperatures: list[float] = []
    overheats: list[float] = []
    for cell, heat in scenario.heat_load.items():
        temp = scenario.ambient_c + 3.10 * heat - 2.15 * plan.cooling.get(cell, 0.0)
        temperatures.append(temp)
        overheats.append(max(0.0, temp - 30.0))

    temp_std = pstdev(temperatures)
    mean_overheat = mean(overheats)
    max_overheat = max(overheats)
    temperature_uniformity = clamp(1.0 - temp_std / 8.0)
    hotspot_recovery = clamp(1.0 - (0.70 * mean_overheat + 0.30 * max_overheat) / 10.0)
    pressure_drop = plan.pressure_drop * (1.0 + 0.90 * scenario.condition.fan_degrade)
    energy_proxy = plan.energy_proxy * (1.0 + 0.55 * scenario.condition.fan_degrade)
    recovery_time = plan.recovery_lag * (1.0 + 0.12 * mean_overheat)
    pressure_score = clamp(1.0 - pressure_drop / 1.35)
    energy_score = clamp(1.0 - energy_proxy / 2.20)
    recovery_score = clamp(1.0 - recovery_time / 10.5)
    runtime_ms = round((scenario.condition.width * scenario.condition.height * plan.runtime_scale) / 2000.0, 5)
    score = (
        0.34 * temperature_uniformity
        + 0.26 * hotspot_recovery
        + 0.18 * energy_score
        + 0.12 * pressure_score
        + 0.10 * recovery_score
    )
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "seed": scenario.seed,
        "strategy": spec.name,
        "kind": spec.kind,
        "family_id": spec.family_id,
        "temperature_uniformity": round(temperature_uniformity, 6),
        "hotspot_recovery": round(hotspot_recovery, 6),
        "pressure_drop": round(pressure_drop, 6),
        "energy_proxy": round(energy_proxy, 6),
        "recovery_time": round(recovery_time, 6),
        "runtime_ms": runtime_ms,
        "mean_temperature_c": round(mean(temperatures), 6),
        "max_temperature_c": round(max(temperatures), 6),
        "score": round(score, 6),
    }


def build_scenarios(split: str, *, scenario_count: int, seed_base: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index in range(scenario_count):
        for condition in CONDITIONS:
            scenarios.append(generate_scenario(seed_base + index * 131 + len(condition.name), condition, split=split))
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
            "mean_temperature_uniformity": round(mean(float(item["temperature_uniformity"]) for item in items), 6),
            "mean_hotspot_recovery": round(mean(float(item["hotspot_recovery"]) for item in items), 6),
            "mean_pressure_drop": round(mean(float(item["pressure_drop"]) for item in items), 6),
            "mean_energy_proxy": round(mean(float(item["energy_proxy"]) for item in items), 6),
            "mean_recovery_time": round(mean(float(item["recovery_time"]) for item in items), 6),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            -float(row["mean_temperature_uniformity"]),
            -float(row["mean_hotspot_recovery"]),
            float(row["mean_energy_proxy"]),
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
    uniformity_delta = float(best_geometry["mean_temperature_uniformity"]) - float(best_baseline["mean_temperature_uniformity"])
    recovery_delta = float(best_geometry["mean_hotspot_recovery"]) - float(best_baseline["mean_hotspot_recovery"])
    energy_delta = float(best_geometry["mean_energy_proxy"]) - float(best_baseline["mean_energy_proxy"])
    pressure_delta = float(best_geometry["mean_pressure_drop"]) - float(best_baseline["mean_pressure_drop"])
    return {
        "gate": "candidate_geometry_beats_best_baseline" if score_delta > 0 else "baseline_still_leads",
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": round(score_delta, 6),
        "temperature_uniformity_delta_vs_best_baseline": round(uniformity_delta, 6),
        "hotspot_recovery_delta_vs_best_baseline": round(recovery_delta, 6),
        "energy_proxy_delta_vs_best_baseline": round(energy_delta, 6),
        "pressure_drop_delta_vs_best_baseline": round(pressure_delta, 6),
        "claim_language": (
            "Generated thermal benchmark candidate only. May be used as proof-building evidence, "
            "not CFD, datacenter, HVAC, field validation, safety certification, or real-dollar performance."
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
        "# Geometry Thermal Ventilation Benchmark",
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
        f"- Temperature-uniformity delta vs best baseline: {gate.get('temperature_uniformity_delta_vs_best_baseline', 0)}",
        f"- Hotspot-recovery delta vs best baseline: {gate.get('hotspot_recovery_delta_vs_best_baseline', 0)}",
        f"- Energy-proxy delta vs best baseline: {gate.get('energy_proxy_delta_vs_best_baseline', 0)}",
        f"- Pressure-drop delta vs best baseline: {gate.get('pressure_drop_delta_vs_best_baseline', 0)}",
        "",
        "## Validation Leaderboard",
        "",
        "| Rank | Strategy | Kind | Score | Uniformity | Hotspot Recovery | Energy | Pressure | Recovery Time |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in validation["leaderboard"]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | {row['mean_score']} | "
            f"{row['mean_temperature_uniformity']} | {row['mean_hotspot_recovery']} | "
            f"{row['mean_energy_proxy']} | {row['mean_pressure_drop']} | {row['mean_recovery_time']} |"
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
    dev_scenarios = build_scenarios("development", scenario_count=development_scenarios, seed_base=5200)
    val_scenarios = build_scenarios("validation", scenario_count=validation_scenarios, seed_base=10400)

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
        "schema": "geometry_thermal_ventilation_benchmark_v1",
        "generated_utc": generated_utc,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "lane": "thermal_ventilation",
        "registry_first_test": "benard_cell_cooling_v1",
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
            "seed_base": 5200,
            "scenario_count": len(dev_scenarios),
            "leaderboard": dev_leaderboard,
        },
        "validation": {
            "seed_base": 10400,
            "scenario_count": len(val_scenarios),
            "leaderboard": val_leaderboard,
        },
        "promotion_gate": gate,
        "claim_gate": {
            "performance_result_generated": True,
            "global_geometry_champion": False,
            "lane_specific_generated_benchmark": True,
            "cfd_validation": False,
            "datacenter_validation": False,
            "field_validation": False,
            "safety_certification": False,
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
            "temperature_uniformity",
            "hotspot_recovery",
            "pressure_drop",
            "energy_proxy",
            "recovery_time",
            "runtime_ms",
            "mean_temperature_c",
            "max_temperature_c",
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
            "mean_temperature_uniformity",
            "mean_hotspot_recovery",
            "mean_pressure_drop",
            "mean_energy_proxy",
            "mean_recovery_time",
        ],
    )
    manifest = {
        "schema": "geometry_thermal_ventilation_manifest_v1",
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
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest.write_text(json.dumps({"run_dir": str(out_dir), **summary}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
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
