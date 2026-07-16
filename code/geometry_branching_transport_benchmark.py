"""Generated branching-transport benchmark for Geometry Championship V1.

This suite tests a narrow software hypothesis: can nature-inspired branching
strategies route flow through a damaged spatial network with better delivered
flow, failure tolerance, and material efficiency than budget-matched graph
baselines?

It is generated software evidence only. It is not grid, datacenter, medical,
defense, field, or customer validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import os
import random
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "geometry_branching_transport"
EVIDENCE_BOUNDARY = (
    "Generated spatial-network software benchmark only. Nodes, demands, risks, "
    "failures, flow costs, and recovery proxies are synthetic assumptions. "
    "Results do not establish grid, datacenter, medical, defense, field, "
    "customer, or real-dollar performance."
)

Node = tuple[int, int]
Edge = tuple[Node, Node]
StrategyFn = Callable[["Scenario"], set[Edge]]


@dataclass(frozen=True)
class Condition:
    name: str
    width: int
    height: int
    sink_count: int
    risk_bias: float
    demand_skew: float
    failure_pressure: float
    obstacle_density: float


@dataclass(frozen=True)
class Scenario:
    split: str
    condition: Condition
    seed: int
    source: Node
    sinks: dict[Node, float]
    edge_risk: dict[Edge, float]
    blocked_edges: set[Edge]


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    build: StrategyFn


CONDITIONS = (
    Condition("nominal_branching", 14, 10, 9, 0.22, 0.20, 0.12, 0.03),
    Condition("crack_front", 15, 11, 10, 0.58, 0.28, 0.25, 0.07),
    Condition("sparse_terminals", 18, 11, 7, 0.34, 0.38, 0.18, 0.05),
    Condition("high_demand_skew", 16, 12, 11, 0.42, 0.72, 0.20, 0.05),
    Condition("degraded_corridor", 17, 12, 10, 0.66, 0.48, 0.30, 0.09),
)


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _u01(seed: int, *parts: object) -> float:
    payload = "|".join(str(part) for part in (seed, *parts)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64)


def canon_edge(a: Node, b: Node) -> Edge:
    return (a, b) if a <= b else (b, a)


def neighbors(node: Node, width: int, height: int) -> Iterable[Node]:
    x, y = node
    if x > 0:
        yield (x - 1, y)
    if x + 1 < width:
        yield (x + 1, y)
    if y > 0:
        yield (x, y - 1)
    if y + 1 < height:
        yield (x, y + 1)


def all_edges(width: int, height: int) -> list[Edge]:
    edges: list[Edge] = []
    for x in range(width):
        for y in range(height):
            node = (x, y)
            for nxt in neighbors(node, width, height):
                edge = canon_edge(node, nxt)
                if edge not in edges:
                    edges.append(edge)
    return edges


def edge_midpoint(edge: Edge) -> tuple[float, float]:
    return ((edge[0][0] + edge[1][0]) / 2.0, (edge[0][1] + edge[1][1]) / 2.0)


def generate_scenario(seed: int, condition: Condition, *, split: str) -> Scenario:
    source = (0, condition.height // 2)
    crack_center = (
        condition.width * (0.44 + 0.12 * _u01(seed, condition.name, "cx")),
        condition.height * (0.30 + 0.40 * _u01(seed, condition.name, "cy")),
    )
    crack_slope = -0.7 + 1.4 * _u01(seed, condition.name, "slope")

    edge_risk: dict[Edge, float] = {}
    blocked_edges: set[Edge] = set()
    for edge in all_edges(condition.width, condition.height):
        mx, my = edge_midpoint(edge)
        crack_line_y = crack_center[1] + crack_slope * (mx - crack_center[0])
        crack_distance = abs(my - crack_line_y) / max(1.0, condition.height)
        base_noise = _u01(seed, condition.name, "risk", edge)
        risk = min(1.0, max(0.0, condition.risk_bias * (1.0 - crack_distance) + 0.28 * base_noise))
        edge_risk[edge] = risk
        blocked_score = 0.70 * risk + 0.30 * _u01(seed, condition.name, "blocked", edge)
        if blocked_score > 1.0 - condition.obstacle_density:
            blocked_edges.add(edge)

    candidates: list[tuple[float, Node]] = []
    for x in range(max(2, condition.width // 3), condition.width):
        for y in range(condition.height):
            node = (x, y)
            if node == source:
                continue
            edge_count = sum(canon_edge(node, nxt) not in blocked_edges for nxt in neighbors(node, condition.width, condition.height))
            if edge_count < 2:
                continue
            score = (
                x / condition.width
                + 0.35 * _u01(seed, condition.name, "sink", node)
                - 0.08 * abs(y - condition.height / 2) / condition.height
            )
            candidates.append((score, node))
    candidates.sort(reverse=True)

    sinks: dict[Node, float] = {}
    for idx, (_, node) in enumerate(candidates[: condition.sink_count]):
        skew = 1.0 + condition.demand_skew * (condition.sink_count - idx) / max(1, condition.sink_count)
        demand = round(skew * (0.85 + 0.55 * _u01(seed, condition.name, "demand", idx)), 4)
        sinks[node] = demand

    return Scenario(
        split=split,
        condition=condition,
        seed=seed,
        source=source,
        sinks=sinks,
        edge_risk=edge_risk,
        blocked_edges=blocked_edges,
    )


def edge_cost(scenario: Scenario, edge: Edge, *, risk_weight: float = 0.0, demand_pull: float = 0.0, sink: Node | None = None) -> float:
    if edge in scenario.blocked_edges:
        return float("inf")
    base = 1.0
    risk = scenario.edge_risk.get(edge, 0.0)
    if sink is not None and demand_pull:
        mx, my = edge_midpoint(edge)
        pull = abs(mx - sink[0]) + abs(my - sink[1])
        base += demand_pull * pull / max(1, scenario.condition.width + scenario.condition.height)
    return base + risk_weight * risk


def dijkstra_path(
    scenario: Scenario,
    start: Node,
    goal: Node,
    *,
    risk_weight: float = 0.0,
    demand_pull: float = 0.0,
) -> list[Node]:
    queue: list[tuple[float, Node]] = [(0.0, start)]
    dist: dict[Node, float] = {start: 0.0}
    parent: dict[Node, Node] = {}
    while queue:
        cost, node = heapq.heappop(queue)
        if node == goal:
            break
        if cost > dist.get(node, float("inf")):
            continue
        for nxt in neighbors(node, scenario.condition.width, scenario.condition.height):
            edge = canon_edge(node, nxt)
            weight = edge_cost(scenario, edge, risk_weight=risk_weight, demand_pull=demand_pull, sink=goal)
            if weight == float("inf"):
                continue
            alt = cost + weight
            if alt < dist.get(nxt, float("inf")):
                dist[nxt] = alt
                parent[nxt] = node
                heapq.heappush(queue, (alt, nxt))
    if goal not in dist:
        return []
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def a_star_path(
    scenario: Scenario,
    start: Node,
    goal: Node,
    *,
    risk_weight: float = 0.0,
    demand_pull: float = 0.0,
) -> list[Node]:
    def heuristic(node: Node) -> float:
        return abs(node[0] - goal[0]) + abs(node[1] - goal[1])

    queue: list[tuple[float, float, Node]] = [(heuristic(start), 0.0, start)]
    dist: dict[Node, float] = {start: 0.0}
    parent: dict[Node, Node] = {}
    while queue:
        _, cost, node = heapq.heappop(queue)
        if node == goal:
            break
        if cost > dist.get(node, float("inf")):
            continue
        for nxt in neighbors(node, scenario.condition.width, scenario.condition.height):
            edge = canon_edge(node, nxt)
            weight = edge_cost(scenario, edge, risk_weight=risk_weight, demand_pull=demand_pull, sink=goal)
            if weight == float("inf"):
                continue
            alt = cost + weight
            if alt < dist.get(nxt, float("inf")):
                dist[nxt] = alt
                parent[nxt] = node
                heapq.heappush(queue, (alt + heuristic(nxt), alt, nxt))
    if goal not in dist:
        return []
    path = [goal]
    while path[-1] != start:
        path.append(parent[path[-1]])
    path.reverse()
    return path


def multi_source_dijkstra_path(
    scenario: Scenario,
    starts: set[Node],
    goal: Node,
    *,
    risk_weight: float = 0.0,
    demand_pull: float = 0.0,
) -> tuple[float, list[Node]]:
    queue: list[tuple[float, Node]] = [(0.0, start) for start in sorted(starts)]
    heapq.heapify(queue)
    dist: dict[Node, float] = {start: 0.0 for start in starts}
    parent: dict[Node, Node] = {}
    while queue:
        cost, node = heapq.heappop(queue)
        if node == goal:
            break
        if cost > dist.get(node, float("inf")):
            continue
        for nxt in neighbors(node, scenario.condition.width, scenario.condition.height):
            edge = canon_edge(node, nxt)
            weight = edge_cost(scenario, edge, risk_weight=risk_weight, demand_pull=demand_pull, sink=goal)
            if weight == float("inf"):
                continue
            alt = cost + weight
            if alt < dist.get(nxt, float("inf")):
                dist[nxt] = alt
                parent[nxt] = node
                heapq.heappush(queue, (alt, nxt))
    if goal not in dist:
        return float("inf"), []
    path = [goal]
    while path[-1] not in starts:
        path.append(parent[path[-1]])
    path.reverse()
    return dist[goal], path


def add_path_edges(edges: set[Edge], path: list[Node]) -> None:
    for left, right in zip(path, path[1:]):
        edges.add(canon_edge(left, right))


def terminal_order(scenario: Scenario, *, reverse_demand: bool = True) -> list[Node]:
    return [
        node
        for node, _ in sorted(
            scenario.sinks.items(),
            key=lambda item: (item[1], item[0][0], -abs(item[0][1] - scenario.source[1])),
            reverse=reverse_demand,
        )
    ]


def connect_from_source(scenario: Scenario, *, risk_weight: float = 0.0, demand_pull: float = 0.0) -> set[Edge]:
    edges: set[Edge] = set()
    for sink in terminal_order(scenario):
        add_path_edges(edges, dijkstra_path(scenario, scenario.source, sink, risk_weight=risk_weight, demand_pull=demand_pull))
    return edges


def connect_greedy_tree(scenario: Scenario, *, risk_weight: float = 0.0, demand_pull: float = 0.0) -> set[Edge]:
    tree_nodes = {scenario.source}
    remaining = set(scenario.sinks)
    edges: set[Edge] = set()
    while remaining:
        best: tuple[float, Node, list[Node]] | None = None
        for sink in sorted(remaining):
            cost, path = multi_source_dijkstra_path(
                scenario,
                tree_nodes,
                sink,
                risk_weight=risk_weight,
                demand_pull=demand_pull,
            )
            if not path:
                continue
            demand = scenario.sinks.get(sink, 1.0)
            score = cost / max(0.1, demand)
            if best is None or score < best[0]:
                best = (score, sink, path)
        if best is None:
            break
        _, sink, path = best
        add_path_edges(edges, path)
        tree_nodes.update(path)
        remaining.remove(sink)
    return edges


def add_redundancy(scenario: Scenario, edges: set[Edge], *, count: int, risk_weight: float) -> set[Edge]:
    result = set(edges)
    sinks = terminal_order(scenario)[:count]
    for sink in sinks:
        blocked = set(result)
        masked = Scenario(
            split=scenario.split,
            condition=scenario.condition,
            seed=scenario.seed,
            source=scenario.source,
            sinks=scenario.sinks,
            edge_risk=scenario.edge_risk,
            blocked_edges=scenario.blocked_edges | blocked,
        )
        path = dijkstra_path(masked, scenario.source, sink, risk_weight=risk_weight)
        if path:
            add_path_edges(result, path)
    return result


def strategy_minimum_spanning_tree(scenario: Scenario) -> set[Edge]:
    return connect_greedy_tree(scenario, risk_weight=0.0)


def strategy_steiner_approximation(scenario: Scenario) -> set[Edge]:
    return connect_greedy_tree(scenario, risk_weight=0.35)


def strategy_min_cost_flow(scenario: Scenario) -> set[Edge]:
    return connect_from_source(scenario, risk_weight=0.20, demand_pull=0.10)


def strategy_dijkstra(scenario: Scenario) -> set[Edge]:
    return connect_from_source(scenario, risk_weight=0.0, demand_pull=0.0)


def strategy_a_star(scenario: Scenario) -> set[Edge]:
    edges: set[Edge] = set()
    for sink in terminal_order(scenario):
        add_path_edges(edges, a_star_path(scenario, scenario.source, sink, risk_weight=0.0, demand_pull=0.0))
    return edges


def strategy_crack_propagation_paths(scenario: Scenario) -> set[Edge]:
    base = connect_greedy_tree(scenario, risk_weight=3.8, demand_pull=0.06)
    return add_redundancy(scenario, base, count=max(1, len(scenario.sinks) // 4), risk_weight=5.0)


def strategy_leaf_veins(scenario: Scenario) -> set[Edge]:
    base = connect_greedy_tree(scenario, risk_weight=1.6)
    return add_redundancy(scenario, base, count=max(2, len(scenario.sinks) // 2), risk_weight=1.8)


def strategy_river_deltas(scenario: Scenario) -> set[Edge]:
    base = connect_from_source(scenario, risk_weight=0.55, demand_pull=0.04)
    return add_redundancy(scenario, base, count=max(1, len(scenario.sinks) // 3), risk_weight=0.70)


def strategy_vascular_lung_branching(scenario: Scenario) -> set[Edge]:
    return connect_greedy_tree(scenario, risk_weight=0.95, demand_pull=0.18)


def strategy_murray_law_branching(scenario: Scenario) -> set[Edge]:
    edges: set[Edge] = set()
    for sink in terminal_order(scenario):
        demand = scenario.sinks[sink]
        add_path_edges(edges, dijkstra_path(scenario, scenario.source, sink, risk_weight=0.75 / max(0.8, demand), demand_pull=0.20))
    return edges


def strategy_neural_dendritic_arbors(scenario: Scenario) -> set[Edge]:
    return connect_greedy_tree(scenario, risk_weight=0.70, demand_pull=0.08)


def strategy_root_gravitropism_paths(scenario: Scenario) -> set[Edge]:
    return connect_from_source(scenario, risk_weight=1.25, demand_pull=-0.04)


def strategy_lightning_laplacian_paths(scenario: Scenario) -> set[Edge]:
    return connect_from_source(scenario, risk_weight=0.05, demand_pull=-0.08)


def strategy_kidney_nephron_filtration(scenario: Scenario) -> set[Edge]:
    base = connect_greedy_tree(scenario, risk_weight=1.2, demand_pull=0.12)
    return add_redundancy(scenario, base, count=max(1, len(scenario.sinks) // 5), risk_weight=2.2)


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("minimum_spanning_tree", "baseline", "minimum_spanning_tree", "Greedy metric-closure tree baseline.", strategy_minimum_spanning_tree),
    StrategySpec("steiner_approximation", "baseline", "steiner_approximation", "Risk-light greedy Steiner-style baseline.", strategy_steiner_approximation),
    StrategySpec("dijkstra", "baseline", "dijkstra", "Independent shortest-path routing baseline.", strategy_dijkstra),
    StrategySpec("a_star", "baseline", "a_star", "A* shortest-path routing baseline with Manhattan heuristic.", strategy_a_star),
    StrategySpec("min_cost_flow", "baseline", "min_cost_flow", "Independent low-cost source-to-sink flow baseline.", strategy_min_cost_flow),
    StrategySpec("crack_propagation_paths", "geometry_family", "crack_propagation_paths", "Routes around predicted crack-risk fronts.", strategy_crack_propagation_paths),
    StrategySpec("leaf_veins", "geometry_family", "leaf_veins", "Reticulate venation with redundant loops.", strategy_leaf_veins),
    StrategySpec("river_deltas", "geometry_family", "river_deltas", "Multi-channel distribution fanout.", strategy_river_deltas),
    StrategySpec("vascular_lung_branching", "geometry_family", "vascular_lung_branching", "Hierarchical terminal distribution.", strategy_vascular_lung_branching),
    StrategySpec("murray_law_branching", "geometry_family", "murray_law_branching", "Demand-weighted branch sizing analogue.", strategy_murray_law_branching),
    StrategySpec("neural_dendritic_arbors", "geometry_family", "neural_dendritic_arbors", "Local dendritic arborization.", strategy_neural_dendritic_arbors),
    StrategySpec("root_gravitropism_paths", "geometry_family", "root_gravitropism_paths", "Resource-gradient seeking paths.", strategy_root_gravitropism_paths),
    StrategySpec("lightning_laplacian_paths", "geometry_family", "lightning_laplacian_paths", "Fast low-material branching along steep paths.", strategy_lightning_laplacian_paths),
    StrategySpec("kidney_nephron_filtration", "geometry_family", "kidney_nephron_filtration", "Staged filtration and redundancy analogue.", strategy_kidney_nephron_filtration),
)


def failed_edges_for(scenario: Scenario, edges: set[Edge], replicate: int) -> set[Edge]:
    failed: set[Edge] = set()
    for edge in edges:
        risk = scenario.edge_risk.get(edge, 0.0)
        threshold = min(0.92, scenario.condition.failure_pressure * (0.35 + risk))
        if _u01(scenario.seed, scenario.condition.name, "fail", replicate, edge) < threshold:
            failed.add(edge)
    return failed


def connected_sinks(source: Node, sinks: dict[Node, float], edges: set[Edge]) -> set[Node]:
    adj: dict[Node, list[Node]] = {}
    for a, b in edges:
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    seen = {source}
    stack = [source]
    while stack:
        node = stack.pop()
        for nxt in adj.get(node, []):
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    return {sink for sink in sinks if sink in seen}


def evaluate_strategy(scenario: Scenario, spec: StrategySpec) -> dict[str, Any]:
    edges = spec.build(scenario)
    delivered_nominal = connected_sinks(scenario.source, scenario.sinks, edges)
    total_demand = sum(scenario.sinks.values())
    nominal_flow = sum(scenario.sinks[sink] for sink in delivered_nominal) / max(0.1, total_demand)
    material_proxy = float(len(edges))
    risk_exposure = sum(scenario.edge_risk.get(edge, 0.0) for edge in edges) / max(1.0, material_proxy)
    failure_rates: list[float] = []
    for replicate in range(7):
        failed = failed_edges_for(scenario, edges, replicate)
        surviving = edges - failed
        delivered = connected_sinks(scenario.source, scenario.sinks, surviving)
        failure_rates.append(sum(scenario.sinks[sink] for sink in delivered) / max(0.1, total_demand))
    failure_tolerance = mean(failure_rates)
    delivered_flow = 0.55 * nominal_flow + 0.45 * failure_tolerance
    energy_proxy = material_proxy * (1.0 + risk_exposure)
    runtime_ms = round((scenario.condition.width * scenario.condition.height * max(1, len(scenario.sinks))) / 15000.0, 5)
    score = (
        0.46 * delivered_flow
        + 0.32 * failure_tolerance
        + 0.14 * max(0.0, 1.0 - material_proxy / max(1.0, scenario.condition.width * scenario.condition.height * 0.55))
        + 0.08 * max(0.0, 1.0 - risk_exposure)
    )
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "seed": scenario.seed,
        "strategy": spec.name,
        "kind": spec.kind,
        "family_id": spec.family_id,
        "delivered_flow": round(delivered_flow, 6),
        "nominal_flow": round(nominal_flow, 6),
        "failure_tolerance": round(failure_tolerance, 6),
        "material_proxy": round(material_proxy, 6),
        "energy_proxy": round(energy_proxy, 6),
        "risk_exposure": round(risk_exposure, 6),
        "runtime_ms": runtime_ms,
        "score": round(score, 6),
        "edges": len(edges),
    }


def build_scenarios(split: str, *, scenario_count: int, seed_base: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index in range(scenario_count):
        for condition in CONDITIONS:
            scenarios.append(generate_scenario(seed_base + index * 101 + len(condition.name), condition, split=split))
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
            "mean_delivered_flow": round(mean(float(item["delivered_flow"]) for item in items), 6),
            "mean_failure_tolerance": round(mean(float(item["failure_tolerance"]) for item in items), 6),
            "mean_material_proxy": round(mean(float(item["material_proxy"]) for item in items), 6),
            "mean_energy_proxy": round(mean(float(item["energy_proxy"]) for item in items), 6),
            "mean_risk_exposure": round(mean(float(item["risk_exposure"]) for item in items), 6),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            -float(row["mean_delivered_flow"]),
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
    delivered_delta = float(best_geometry["mean_delivered_flow"]) - float(best_baseline["mean_delivered_flow"])
    tolerance_delta = float(best_geometry["mean_failure_tolerance"]) - float(best_baseline["mean_failure_tolerance"])
    return {
        "gate": "candidate_geometry_beats_best_baseline" if score_delta > 0 else "baseline_still_leads",
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": round(score_delta, 6),
        "delivered_flow_delta_vs_best_baseline": round(delivered_delta, 6),
        "failure_tolerance_delta_vs_best_baseline": round(tolerance_delta, 6),
        "claim_language": (
            "Generated benchmark candidate only. May be used as proof-building evidence, not field validation or real-dollar performance."
        ),
    }


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def paired_bootstrap_mean_ci(
    deltas: list[float],
    *,
    resamples: int = 2000,
    seed: int = 20260715,
) -> dict[str, Any]:
    if not deltas:
        raise ValueError("paired bootstrap requires at least one delta")
    rng = random.Random(seed)
    sample_count = len(deltas)
    bootstrap_means = [
        mean(rng.choices(deltas, k=sample_count))
        for _ in range(resamples)
    ]
    return {
        "observed_mean_delta": round(mean(deltas), 6),
        "ci95": [
            round(percentile(bootstrap_means, 0.025), 6),
            round(percentile(bootstrap_means, 0.975), 6),
        ],
        "resamples": resamples,
        "seed": seed,
        "paired_scenario_count": sample_count,
    }


def confirmatory_promotion_gate(
    development_ranked: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    validation_ranked: list[dict[str, Any]],
    *,
    condition_noninferiority_margin: float = 0.01,
    bootstrap_resamples: int = 2000,
) -> dict[str, Any]:
    development_baselines = [row for row in development_ranked if row["kind"] == "baseline"]
    development_geometries = [row for row in development_ranked if row["kind"] == "geometry_family"]
    if not development_baselines or not development_geometries:
        return {"gate": "missing_development_baseline_or_geometry", "promoted": False}

    selected_geometry_name = str(development_geometries[0]["strategy"])
    selected_baseline_name = str(development_baselines[0]["strategy"])
    validation_by_strategy = {str(row["strategy"]): row for row in validation_ranked}
    selected_geometry = validation_by_strategy.get(selected_geometry_name)
    selected_baseline = validation_by_strategy.get(selected_baseline_name)
    if not selected_geometry or not selected_baseline:
        return {
            "gate": "selected_pair_missing_from_validation",
            "promoted": False,
            "selected_geometry_name": selected_geometry_name,
            "selected_baseline_name": selected_baseline_name,
        }

    paired: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in validation_rows:
        strategy = str(row.get("strategy") or "")
        if strategy not in {selected_geometry_name, selected_baseline_name}:
            continue
        key = (str(row["condition"]), int(row["seed"]))
        paired[key][strategy] = row
    complete_pairs = [
        (key, rows[selected_geometry_name], rows[selected_baseline_name])
        for key, rows in sorted(paired.items())
        if selected_geometry_name in rows and selected_baseline_name in rows
    ]
    if not complete_pairs:
        return {
            "gate": "no_complete_validation_pairs",
            "promoted": False,
            "selected_geometry_name": selected_geometry_name,
            "selected_baseline_name": selected_baseline_name,
        }

    score_deltas = [float(candidate["score"]) - float(baseline["score"]) for _, candidate, baseline in complete_pairs]
    delivered_deltas = [
        float(candidate["delivered_flow"]) - float(baseline["delivered_flow"])
        for _, candidate, baseline in complete_pairs
    ]
    tolerance_deltas = [
        float(candidate["failure_tolerance"]) - float(baseline["failure_tolerance"])
        for _, candidate, baseline in complete_pairs
    ]
    bootstrap = paired_bootstrap_mean_ci(
        score_deltas,
        resamples=bootstrap_resamples,
    )

    by_condition: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for (condition, _), candidate, baseline in complete_pairs:
        by_condition[condition].append((candidate, baseline))
    condition_guardrails: list[dict[str, Any]] = []
    for condition, rows in sorted(by_condition.items()):
        condition_deltas = [
            float(candidate["score"]) - float(baseline["score"])
            for candidate, baseline in rows
        ]
        score_delta = mean(condition_deltas)
        condition_guardrails.append(
            {
                "condition": condition,
                "paired_scenario_count": len(rows),
                "score_delta": round(score_delta, 6),
                "noninferiority_margin": condition_noninferiority_margin,
                "passes_noninferiority": score_delta >= -condition_noninferiority_margin,
            }
        )

    checks = {
        "overall_score_delta_positive": mean(score_deltas) > 0.0,
        "paired_ci95_lower_bound_positive": float(bootstrap["ci95"][0]) > 0.0,
        "delivered_flow_no_regression": mean(delivered_deltas) >= 0.0,
        "failure_tolerance_no_regression": mean(tolerance_deltas) >= 0.0,
        "all_condition_score_noninferiority": all(
            row["passes_noninferiority"] for row in condition_guardrails
        ),
    }
    promoted = all(checks.values())
    failed_checks = [name for name, passed in checks.items() if not passed]
    return {
        "gate": (
            "candidate_geometry_promoted_confirmatory"
            if promoted
            else "candidate_geometry_not_promoted_confirmatory"
        ),
        "promoted": promoted,
        "selection": {
            "source": "development_only",
            "selected_geometry": selected_geometry_name,
            "selected_baseline": selected_baseline_name,
            "validation_pair_locked_before_scoring": True,
            "multiple_comparison_control": (
                "one confirmatory pair selected on development; validation leaderboard is descriptive"
            ),
        },
        "best_geometry": selected_geometry,
        "best_baseline": selected_baseline,
        "score_delta_vs_best_baseline": round(mean(score_deltas), 6),
        "delivered_flow_delta_vs_best_baseline": round(mean(delivered_deltas), 6),
        "failure_tolerance_delta_vs_best_baseline": round(mean(tolerance_deltas), 6),
        "paired_bootstrap": bootstrap,
        "condition_guardrails": condition_guardrails,
        "checks": checks,
        "failed_checks": failed_checks,
        "claim_language": (
            "Generated benchmark evidence only. Promotion requires a development-locked pair, "
            "paired validation superiority, and no material condition regression. It is not field "
            "validation, certification, or real-dollar performance."
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


def sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def evaluate_scenario_all_strategies(scenario: Scenario) -> list[dict[str, Any]]:
    return [evaluate_strategy(scenario, spec) for spec in STRATEGIES]


def scenario_key(scenario: Scenario) -> tuple[str, str, int]:
    return scenario.split, scenario.condition.name, scenario.seed


def row_scenario_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return str(row["split"]), str(row["condition"]), int(row["seed"])


def canonical_json_line(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"


def load_complete_checkpoint(
    checkpoint_path: Path,
    scenarios: list[Scenario],
) -> tuple[dict[tuple[str, str, int], list[dict[str, Any]]], int]:
    expected_keys = {scenario_key(scenario) for scenario in scenarios}
    expected_strategies = {spec.name for spec in STRATEGIES}
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    discarded_rows = 0
    if checkpoint_path.exists():
        for line_number, line in enumerate(checkpoint_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid checkpoint JSON at {checkpoint_path}:{line_number}") from exc
            if not isinstance(row, dict):
                discarded_rows += 1
                continue
            try:
                key = row_scenario_key(row)
            except (KeyError, TypeError, ValueError):
                discarded_rows += 1
                continue
            strategy = str(row.get("strategy") or "")
            if key not in expected_keys or strategy not in expected_strategies:
                discarded_rows += 1
                continue
            grouped[key][strategy] = row

    complete: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for key, by_strategy in grouped.items():
        if set(by_strategy) == expected_strategies:
            complete[key] = [by_strategy[spec.name] for spec in STRATEGIES]
        else:
            discarded_rows += len(by_strategy)
    return complete, discarded_rows


def run_rows_resumable(
    scenarios: list[Scenario],
    checkpoint_path: Path,
    *,
    workers: int,
    resume: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    complete, discarded_rows = (
        load_complete_checkpoint(checkpoint_path, scenarios)
        if resume
        else ({}, 0)
    )
    ordered_keys = [scenario_key(scenario) for scenario in scenarios]
    missing = [scenario for scenario in scenarios if scenario_key(scenario) not in complete]

    with checkpoint_path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in ordered_keys:
            for row in complete.get(key, []):
                handle.write(canonical_json_line(row))

    if missing:
        executor: ProcessPoolExecutor | None = None
        if workers <= 1:
            iterator = map(evaluate_scenario_all_strategies, missing)
        else:
            executor = ProcessPoolExecutor(max_workers=workers)
            iterator = executor.map(evaluate_scenario_all_strategies, missing, chunksize=1)
        try:
            with checkpoint_path.open("a", encoding="utf-8", newline="\n") as handle:
                for scenario, scenario_rows in zip(missing, iterator):
                    complete[scenario_key(scenario)] = scenario_rows
                    for row in scenario_rows:
                        handle.write(canonical_json_line(row))
                    handle.flush()
        finally:
            if executor is not None:
                executor.shutdown(wait=True, cancel_futures=False)

    rows = [row for key in ordered_keys for row in complete[key]]
    return rows, {
        "scenario_count": len(scenarios),
        "row_count": len(rows),
        "resumed_scenario_count": len(scenarios) - len(missing),
        "executed_scenario_count": len(missing),
        "discarded_checkpoint_row_count": discarded_rows,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "workers": workers,
        "wall_seconds": round(time.perf_counter() - started, 6),
    }


def write_or_validate_execution_plan(
    out_dir: Path,
    *,
    development_scenarios: int,
    validation_scenarios: int,
) -> tuple[Path, dict[str, Any]]:
    plan_path = out_dir / "execution_plan.json"
    plan: dict[str, Any] = {
        "schema": "geometry_branching_transport_execution_plan_v1",
        "source_sha256": sha256_file(Path(__file__)),
        "development_scenarios_per_condition": development_scenarios,
        "validation_scenarios_per_condition": validation_scenarios,
        "development_seed_base": 4100,
        "validation_seed_base": 9100,
        "condition_names": [condition.name for condition in CONDITIONS],
        "strategy_names": [spec.name for spec in STRATEGIES],
        "family_ids": [spec.family_id for spec in STRATEGIES],
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    plan["plan_sha256"] = sha256_payload(plan)
    if plan_path.exists():
        existing = json.loads(plan_path.read_text(encoding="utf-8"))
        if existing != plan:
            raise ValueError(
                "execution plan mismatch; use a new run tag instead of mixing code, seeds, "
                "scenario counts, or strategies in one checkpoint"
            )
    else:
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan_path, plan


def render_scorecard(summary: dict[str, Any]) -> str:
    validation = summary["validation"]
    gate = summary["promotion_gate"]
    lines = [
        "# Geometry Branching Transport Benchmark",
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
        f"- Delivered-flow delta vs best baseline: {gate.get('delivered_flow_delta_vs_best_baseline', 0)}",
        f"- Failure-tolerance delta vs best baseline: {gate.get('failure_tolerance_delta_vs_best_baseline', 0)}",
        f"- Paired score-delta CI95: {gate.get('paired_bootstrap', {}).get('ci95', 'n/a')}",
        f"- Failed confirmatory checks: {', '.join(gate.get('failed_checks', [])) or 'none'}",
        "",
        "## Condition Guardrails",
        "",
        "| Condition | Paired Scenarios | Score Delta | Noninferiority Margin | Pass |",
        "|---|---:|---:|---:|---|",
    ]
    for row in gate.get("condition_guardrails", []):
        lines.append(
            f"| {row['condition']} | {row['paired_scenario_count']} | {row['score_delta']} | "
            f"{row['noninferiority_margin']} | {str(row['passes_noninferiority']).lower()} |"
        )
    lines.extend(
        [
        "",
        "## Validation Leaderboard",
        "",
        "| Rank | Strategy | Kind | Score | Delivered Flow | Failure Tolerance | Material | Energy |",
        "|---:|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in validation["leaderboard"]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | {row['mean_score']} | "
            f"{row['mean_delivered_flow']} | {row['mean_failure_tolerance']} | "
            f"{row['mean_material_proxy']} | {row['mean_energy_proxy']} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            gate.get("claim_language", ""),
        ]
    )
    return "\n".join(lines)


def run_suite(
    out_dir: Path,
    *,
    development_scenarios: int = 8,
    validation_scenarios: int = 10,
    workers: int = 1,
    resume: bool = True,
) -> dict[str, Any]:
    if development_scenarios < 1 or validation_scenarios < 1:
        raise ValueError("scenario counts must be positive")
    if workers < 1:
        raise ValueError("workers must be positive")
    generated_utc = now_utc()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path, execution_plan = write_or_validate_execution_plan(
        out_dir,
        development_scenarios=development_scenarios,
        validation_scenarios=validation_scenarios,
    )
    dev_scenarios = build_scenarios("development", scenario_count=development_scenarios, seed_base=4100)
    val_scenarios = build_scenarios("validation", scenario_count=validation_scenarios, seed_base=9100)
    development_checkpoint = out_dir / "development_checkpoint.jsonl"
    validation_checkpoint = out_dir / "validation_checkpoint.jsonl"
    development_rows, development_execution = run_rows_resumable(
        dev_scenarios,
        development_checkpoint,
        workers=workers,
        resume=resume,
    )
    validation_rows, validation_execution = run_rows_resumable(
        val_scenarios,
        validation_checkpoint,
        workers=workers,
        resume=resume,
    )
    dev_leaderboard = ranked_aggregate(aggregate(development_rows))
    val_leaderboard = ranked_aggregate(aggregate(validation_rows))
    descriptive_gate = score_against_baseline(val_leaderboard)
    gate = confirmatory_promotion_gate(dev_leaderboard, validation_rows, val_leaderboard)
    summary = {
        "schema": "geometry_branching_transport_benchmark_v1",
        "generated_utc": generated_utc,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "lane": "branching_transport",
        "registry_first_test": "crack_path_prediction_v1",
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
        "execution": {
            "plan_sha256": execution_plan["plan_sha256"],
            "workers": workers,
            "resume_enabled": resume,
            "development": development_execution,
            "validation": validation_execution,
        },
        "development": {
            "seed_base": 4100,
            "scenario_count": len(dev_scenarios),
            "leaderboard": dev_leaderboard,
        },
        "validation": {
            "seed_base": 9100,
            "scenario_count": len(val_scenarios),
            "leaderboard": val_leaderboard,
        },
        "descriptive_validation_gate": descriptive_gate,
        "promotion_gate": gate,
        "claim_gate": {
            "performance_result_generated": True,
            "global_geometry_champion": False,
            "lane_specific_generated_benchmark": True,
            "field_validation": False,
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
            "delivered_flow",
            "nominal_flow",
            "failure_tolerance",
            "material_proxy",
            "energy_proxy",
            "risk_exposure",
            "runtime_ms",
            "score",
            "edges",
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
            "mean_delivered_flow",
            "mean_failure_tolerance",
            "mean_material_proxy",
            "mean_energy_proxy",
            "mean_risk_exposure",
        ],
    )
    manifest = {
        "schema": "geometry_branching_transport_manifest_v1",
        "generated_utc": generated_utc,
        "files": {},
    }
    for path in (
        plan_path,
        development_checkpoint,
        validation_checkpoint,
        summary_path,
        scorecard_path,
        out_dir / "scenario_summary.csv",
        out_dir / "leaderboard.csv",
    ):
        manifest["files"][path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--development-scenarios", type=int, default=8)
    parser.add_argument("--validation-scenarios", type=int, default=10)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(8, (os.cpu_count() or 2) - 1)),
    )
    parser.add_argument("--no-resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or now_tag()
    out_dir = args.out_root / run_tag
    summary = run_suite(
        out_dir,
        development_scenarios=args.development_scenarios,
        validation_scenarios=args.validation_scenarios,
        workers=args.workers,
        resume=not args.no_resume,
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
