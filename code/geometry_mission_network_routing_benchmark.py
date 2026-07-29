"""Generated mission-network-routing benchmark for Geometry Championship V1.

This suite tests a narrow software hypothesis: can four declared
nature-inspired routing heuristics improve delivery, cost, recovery, and load
behavior under generated congestion shifts and edge failures versus four
registry-named graph baselines?

The graph primitives and baselines use NetworkX. The natural-family algorithms
are explicit, bounded software analogues, not biological simulations. This is
generated software evidence only. It is not live-breadth, source-conditioned,
field, customer, government-approval, universal-superiority, trading, or
real-dollar evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import islice
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable, Iterable

import networkx as nx
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "geometry_mission_network_routing"
EVIDENCE_BOUNDARY = (
    "Generated mission-network-routing software benchmark only. Graph topology, "
    "positions, demand, congestion, capacities, failures, recovery, messages, "
    "and costs are deterministic synthetic assumptions. This lane is separate "
    "from the live-breadth source registry and does not establish source-conditioned, "
    "live, field, customer, government-approval, universal-superiority, trading, "
    "or real-dollar performance. Cross-lane ranking is forbidden."
)

Edge = tuple[int, int]
RoutingFn = Callable[["Scenario", bool], "RoutingPlan"]


@dataclass(frozen=True)
class Condition:
    name: str
    node_count: int
    target_count: int
    edge_multiplier: float
    failure_rate: float
    congestion_pressure: float
    demand_max: int
    failure_mode: str
    bandwidth_limit: int


@dataclass(frozen=True)
class EdgeSpec:
    u: int
    v: int
    distance: float
    capacity: int
    pre_weight: float
    post_weight: float
    failure_risk: float


@dataclass(frozen=True)
class Scenario:
    split: str
    condition: Condition
    seed: int
    source: int
    targets: tuple[int, ...]
    pre_demands: tuple[tuple[int, int], ...]
    post_demands: tuple[tuple[int, int], ...]
    positions: tuple[tuple[int, float, float], ...]
    edges: tuple[EdgeSpec, ...]
    failed_edges: tuple[Edge, ...]


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    simplification: str
    build: RoutingFn


@dataclass
class RoutingPlan:
    edge_flow: dict[Edge, float]
    deliveries: dict[int, float]
    messages: int
    search_steps: int
    details: dict[str, Any]


CONDITIONS = (
    Condition(
        "nominal_sparse_failures",
        24,
        4,
        2.05,
        0.03,
        0.12,
        3,
        "random_dropout",
        4200,
    ),
    Condition(
        "dynamic_congestion_shift",
        28,
        5,
        2.15,
        0.05,
        0.82,
        4,
        "regime_shift",
        5200,
    ),
    Condition(
        "random_edge_dropout",
        30,
        5,
        2.00,
        0.17,
        0.32,
        4,
        "random_dropout",
        5600,
    ),
    Condition(
        "correlated_corridor_failure",
        32,
        6,
        2.20,
        0.15,
        0.52,
        4,
        "corridor_failure",
        6200,
    ),
    Condition(
        "hub_loss_bandwidth_limit",
        34,
        6,
        2.10,
        0.19,
        0.66,
        5,
        "hub_failure",
        6400,
    ),
)

DEVELOPMENT_SEED_BASE = 4300
VALIDATION_SEED_BASE = 14300
ALGORITHM_BUDGETS = {
    "capacity_allocation_quantum": 1.0,
    "k_shortest_candidate_paths": 4,
    "ant_iterations": 6,
    "ants_per_target_per_iteration": 5,
    "ant_walk_step_multiplier": 2,
    "bee_scout_paths_per_target": 4,
    "bee_recruited_paths_per_target": 2,
    "slime_mold_iterations_per_target": 7,
    "mycelium_diverse_paths_per_target": 3,
    "paired_bootstrap_resamples": 2000,
    "condition_noninferiority_margin": 0.02,
}


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_edge(u: int, v: int) -> Edge:
    return (u, v) if u < v else (v, u)


def _digest(seed: int, *parts: object) -> bytes:
    payload = "|".join(str(part) for part in (seed, *parts)).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).digest()


def _u01(seed: int, *parts: object) -> float:
    return int.from_bytes(_digest(seed, *parts)[:8], "big") / float(2**64)


def stable_seed(seed: int, *parts: object) -> int:
    return int.from_bytes(_digest(seed, *parts), "big")


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _positions(seed: int, node_count: int) -> dict[int, tuple[float, float]]:
    positions = {0: (0.02, 0.50)}
    for node in range(1, node_count):
        x = 0.08 + 0.88 * _u01(seed, "position", node, "x")
        y = 0.05 + 0.90 * _u01(seed, "position", node, "y")
        positions[node] = (round(x, 6), round(y, 6))
    return positions


def _euclidean(left: tuple[float, float], right: tuple[float, float]) -> float:
    return math.hypot(left[0] - right[0], left[1] - right[1])


def _base_edges(
    seed: int,
    positions: dict[int, tuple[float, float]],
    edge_multiplier: float,
) -> list[Edge]:
    complete = nx.Graph()
    complete.add_nodes_from(sorted(positions))
    candidates: list[tuple[float, int, int]] = []
    for u in sorted(positions):
        for v in range(u + 1, len(positions)):
            distance = _euclidean(positions[u], positions[v])
            complete.add_edge(u, v, weight=distance)
            tie_break = 0.000001 * _u01(seed, "edge_tie", u, v)
            candidates.append((distance + tie_break, u, v))
    tree = nx.minimum_spanning_tree(complete, weight="weight", algorithm="kruskal")
    selected = {canonical_edge(int(u), int(v)) for u, v in tree.edges()}
    target_edge_count = max(
        len(selected),
        min(len(candidates), int(round(len(positions) * edge_multiplier))),
    )
    for _, u, v in sorted(candidates):
        selected.add(canonical_edge(u, v))
        if len(selected) >= target_edge_count:
            break
    return sorted(selected)


def _targets(
    seed: int,
    positions: dict[int, tuple[float, float]],
    target_count: int,
) -> tuple[int, ...]:
    ranked = sorted(
        (node for node in positions if node != 0),
        key=lambda node: (
            -(positions[node][0] + 0.18 * _u01(seed, "target", node)),
            node,
        ),
    )
    return tuple(sorted(ranked[:target_count]))


def _select_failed_edges(
    seed: int,
    condition: Condition,
    positions: dict[int, tuple[float, float]],
    edge_rows: list[EdgeSpec],
) -> tuple[Edge, ...]:
    target_count = max(1, int(round(len(edge_rows) * condition.failure_rate)))
    scored: list[tuple[float, Edge]] = []
    if condition.failure_mode == "hub_failure":
        probe = nx.Graph()
        probe.add_nodes_from(sorted(positions))
        probe.add_edges_from((row.u, row.v) for row in edge_rows)
        candidates = [node for node in probe if node != 0]
        centrality = nx.betweenness_centrality(probe, normalized=True)
        hub = max(candidates, key=lambda node: (centrality[node], probe.degree[node], -node))
        for row in edge_rows:
            incident = 1.0 if hub in (row.u, row.v) else 0.0
            score = 2.0 * incident + row.failure_risk + 0.1 * _u01(seed, "hub_fail", row.u, row.v)
            scored.append((score, canonical_edge(row.u, row.v)))
    elif condition.failure_mode == "corridor_failure":
        corridor_x = 0.48 + 0.08 * _u01(seed, "corridor_x")
        for row in edge_rows:
            left = positions[row.u][0] - corridor_x
            right = positions[row.v][0] - corridor_x
            crosses = 1.0 if left == 0.0 or right == 0.0 or left * right < 0.0 else 0.0
            midpoint = (positions[row.u][0] + positions[row.v][0]) / 2.0
            proximity = max(0.0, 1.0 - abs(midpoint - corridor_x) / 0.22)
            score = 1.4 * crosses + 0.7 * proximity + row.failure_risk
            scored.append((score, canonical_edge(row.u, row.v)))
    else:
        for row in edge_rows:
            score = row.failure_risk + 0.55 * _u01(seed, "random_fail", row.u, row.v)
            scored.append((score, canonical_edge(row.u, row.v)))
    ranked = [edge for _, edge in sorted(scored, reverse=True)]
    return tuple(sorted(ranked[:target_count]))


def generate_scenario(seed: int, condition: Condition, *, split: str) -> Scenario:
    positions = _positions(seed, condition.node_count)
    edge_keys = _base_edges(seed, positions, condition.edge_multiplier)
    targets = _targets(seed, positions, condition.target_count)
    edge_rows: list[EdgeSpec] = []
    corridor_y = 0.25 + 0.50 * _u01(seed, condition.name, "congestion_corridor_y")
    for u, v in edge_keys:
        distance = _euclidean(positions[u], positions[v])
        roughness = 0.88 + 0.32 * _u01(seed, condition.name, "roughness", u, v)
        base_weight = max(0.01, distance * 100.0 * roughness)
        capacity = 2 + int(7 * _u01(seed, condition.name, "capacity", u, v))
        failure_risk = 0.15 + 0.75 * _u01(seed, condition.name, "risk", u, v)
        midpoint_y = (positions[u][1] + positions[v][1]) / 2.0
        corridor_proximity = max(0.0, 1.0 - abs(midpoint_y - corridor_y) / 0.24)
        pre_congestion = 1.0 + 0.18 * _u01(seed, condition.name, "pre_congestion", u, v)
        shift = condition.congestion_pressure * (
            0.25
            + 1.15 * corridor_proximity
            + 0.45 * _u01(seed, condition.name, "post_congestion", u, v)
        )
        if condition.failure_mode == "regime_shift":
            shift *= 1.45
        edge_rows.append(
            EdgeSpec(
                u=u,
                v=v,
                distance=round(distance, 8),
                capacity=capacity,
                pre_weight=round(base_weight * pre_congestion, 6),
                post_weight=round(base_weight * (1.0 + shift), 6),
                failure_risk=round(failure_risk, 6),
            )
        )

    pre_demands: list[tuple[int, int]] = []
    post_demands: list[tuple[int, int]] = []
    for target in targets:
        pre = 1 + int(condition.demand_max * _u01(seed, condition.name, "pre_demand", target))
        if condition.name in {"dynamic_congestion_shift", "hub_loss_bandwidth_limit"}:
            post = 1 + int(condition.demand_max * _u01(seed, condition.name, "post_demand", target))
        else:
            post = pre
        pre_demands.append((target, pre))
        post_demands.append((target, post))

    failed_edges = _select_failed_edges(seed, condition, positions, edge_rows)
    return Scenario(
        split=split,
        condition=condition,
        seed=seed,
        source=0,
        targets=targets,
        pre_demands=tuple(sorted(pre_demands)),
        post_demands=tuple(sorted(post_demands)),
        positions=tuple((node, *positions[node]) for node in sorted(positions)),
        edges=tuple(edge_rows),
        failed_edges=failed_edges,
    )


def scenario_graph(scenario: Scenario, *, post_change: bool) -> nx.Graph:
    graph = nx.Graph()
    for node, x, y in scenario.positions:
        graph.add_node(node, pos=(x, y))
    failed = set(scenario.failed_edges) if post_change else set()
    for row in scenario.edges:
        edge = canonical_edge(row.u, row.v)
        if edge in failed:
            continue
        graph.add_edge(
            row.u,
            row.v,
            weight=row.post_weight if post_change else row.pre_weight,
            capacity=row.capacity,
            failure_risk=row.failure_risk,
            distance=row.distance,
        )
    return graph


def demands_for(scenario: Scenario, *, post_change: bool) -> dict[int, int]:
    return dict(scenario.post_demands if post_change else scenario.pre_demands)


def path_cost(graph: nx.Graph, path: list[int]) -> float:
    return sum(float(graph[u][v]["weight"]) for u, v in zip(path, path[1:]))


def path_edges(path: list[int]) -> list[Edge]:
    return [canonical_edge(u, v) for u, v in zip(path, path[1:])]


def _allocate_candidate_paths(
    graph: nx.Graph,
    demands: dict[int, int],
    candidates: dict[int, list[list[int]]],
    *,
    messages: int,
    search_steps: int,
    details: dict[str, Any],
) -> RoutingPlan:
    edge_flow: dict[Edge, float] = defaultdict(float)
    deliveries = {target: 0.0 for target in demands}
    target_order = sorted(demands, key=lambda target: (-demands[target], target))
    quantum = float(ALGORITHM_BUDGETS["capacity_allocation_quantum"])
    for target in target_order:
        remaining = float(demands[target])
        unique_paths: list[list[int]] = []
        seen: set[tuple[int, ...]] = set()
        for path in candidates.get(target, []):
            signature = tuple(path)
            if len(path) < 2 or signature in seen:
                continue
            seen.add(signature)
            unique_paths.append(path)
        while remaining > 1e-9 and unique_paths:
            ranked: list[tuple[float, tuple[int, ...], list[int], float]] = []
            for path in unique_paths:
                edges = path_edges(path)
                residual = min(
                    float(graph[u][v]["capacity"]) - edge_flow[canonical_edge(u, v)]
                    for u, v in zip(path, path[1:])
                )
                if residual <= 1e-9:
                    continue
                load_penalty = mean(
                    edge_flow[canonical_edge(u, v)] / max(1.0, float(graph[u][v]["capacity"]))
                    for u, v in zip(path, path[1:])
                )
                ranked.append(
                    (
                        path_cost(graph, path) * (1.0 + 0.65 * load_penalty),
                        tuple(path),
                        path,
                        residual,
                    )
                )
            if not ranked:
                break
            _, _, selected, residual = min(ranked)
            amount = min(quantum, remaining, residual)
            for edge in path_edges(selected):
                edge_flow[edge] += amount
            deliveries[target] += amount
            remaining -= amount
    return RoutingPlan(
        edge_flow=dict(edge_flow),
        deliveries=deliveries,
        messages=messages,
        search_steps=search_steps,
        details=details,
    )


def _single_shortest_paths(
    graph: nx.Graph,
    source: int,
    targets: Iterable[int],
    *,
    astar: bool,
) -> tuple[dict[int, list[list[int]]], int]:
    positions = nx.get_node_attributes(graph, "pos")
    minimum_cost_per_distance = min(
        float(data["weight"]) / max(1e-9, float(data["distance"]))
        for _, _, data in graph.edges(data=True)
    )
    candidates: dict[int, list[list[int]]] = {}
    messages = 0
    for target in sorted(targets):
        try:
            if astar:
                heuristic = (
                    lambda left, right: _euclidean(positions[left], positions[right])
                    * minimum_cost_per_distance
                )
                path = nx.astar_path(graph, source, target, heuristic=heuristic, weight="weight")
            else:
                path = nx.dijkstra_path(graph, source, target, weight="weight")
            candidates[target] = [list(path)]
        except nx.NetworkXNoPath:
            candidates[target] = []
        messages += graph.number_of_edges()
    return candidates, messages


def strategy_dijkstra(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    candidates, messages = _single_shortest_paths(
        graph,
        scenario.source,
        demands,
        astar=False,
    )
    return _allocate_candidate_paths(
        graph,
        demands,
        candidates,
        messages=messages,
        search_steps=len(demands),
        details={"primitive": "networkx.dijkstra_path", "independent_target_paths": True},
    )


def strategy_a_star(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    candidates, messages = _single_shortest_paths(
        graph,
        scenario.source,
        demands,
        astar=True,
    )
    return _allocate_candidate_paths(
        graph,
        demands,
        candidates,
        messages=messages,
        search_steps=len(demands),
        details={
            "primitive": "networkx.astar_path",
            "heuristic": "euclidean_position_times_graph_minimum_cost_per_distance",
            "heuristic_admissible_by_construction": True,
            "independent_target_paths": True,
        },
    )


def strategy_min_cost_flow(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    directed = nx.DiGraph()
    directed.add_nodes_from(graph.nodes())
    for u, v, data in graph.edges(data=True):
        capacity = int(data["capacity"])
        weight = max(1, int(round(float(data["weight"]) * 1000.0)))
        directed.add_edge(u, v, capacity=capacity, weight=weight)
        directed.add_edge(v, u, capacity=capacity, weight=weight)
    sink = "__mission_sink__"
    directed.add_node(sink)
    for target, demand in sorted(demands.items()):
        directed.add_edge(target, sink, capacity=int(demand), weight=0)
    deliveries = {target: 0.0 for target in demands}
    edge_flow: dict[Edge, float] = defaultdict(float)
    try:
        flow = nx.max_flow_min_cost(
            directed,
            scenario.source,
            sink,
            capacity="capacity",
            weight="weight",
        )
        for target in demands:
            deliveries[target] = float(flow.get(target, {}).get(sink, 0.0))
        for u, outgoing in flow.items():
            if u == sink:
                continue
            for v, amount in outgoing.items():
                if v == sink or amount <= 0:
                    continue
                edge_flow[canonical_edge(int(u), int(v))] += float(amount)
    except (nx.NetworkXError, nx.NetworkXUnfeasible):
        pass
    return RoutingPlan(
        edge_flow=dict(edge_flow),
        deliveries=deliveries,
        messages=directed.number_of_edges() + directed.number_of_nodes(),
        search_steps=1,
        details={
            "primitive": "networkx.max_flow_min_cost",
            "simplification": "undirected links represented by symmetric directed capacity arcs",
        },
    )


def _k_shortest_candidates(
    graph: nx.Graph,
    source: int,
    targets: Iterable[int],
    *,
    count: int,
) -> tuple[dict[int, list[list[int]]], int]:
    candidates: dict[int, list[list[int]]] = {}
    messages = 0
    for target in sorted(targets):
        try:
            paths = [
                list(path)
                for path in islice(
                    nx.shortest_simple_paths(graph, source, target, weight="weight"),
                    count,
                )
            ]
        except nx.NetworkXNoPath:
            paths = []
        candidates[target] = paths
        messages += graph.number_of_edges() * max(1, len(paths))
    return candidates, messages


def strategy_k_shortest_redundancy(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    count = int(ALGORITHM_BUDGETS["k_shortest_candidate_paths"])
    candidates, messages = _k_shortest_candidates(
        graph,
        scenario.source,
        demands,
        count=count,
    )
    return _allocate_candidate_paths(
        graph,
        demands,
        candidates,
        messages=messages,
        search_steps=len(demands) * count,
        details={
            "primitive": "networkx.shortest_simple_paths",
            "candidate_paths_per_target": count,
            "allocation": "unit demand assigned by incremental cost and residual capacity",
        },
    )


def _ant_walk(
    graph: nx.Graph,
    source: int,
    target: int,
    pheromone: dict[Edge, float],
    rng: random.Random,
    *,
    max_steps: int,
) -> tuple[list[int], int]:
    path = [source]
    visited = {source}
    messages = 0
    while path[-1] != target and len(path) <= max_steps:
        node = path[-1]
        neighbors = [candidate for candidate in sorted(graph.neighbors(node)) if candidate not in visited]
        messages += len(neighbors)
        if not neighbors:
            return [], messages
        weights: list[float] = []
        for candidate in neighbors:
            edge = canonical_edge(node, candidate)
            cost = float(graph[node][candidate]["weight"])
            capacity = float(graph[node][candidate]["capacity"])
            desirability = (
                max(1e-6, pheromone.get(edge, 1.0)) ** 1.15
                * (1.0 / max(1e-6, cost)) ** 1.65
                * math.sqrt(capacity)
            )
            weights.append(desirability)
        selected = rng.choices(neighbors, weights=weights, k=1)[0]
        path.append(selected)
        visited.add(selected)
    return (path if path[-1] == target else []), messages


def strategy_ant_trails(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    iterations = int(ALGORITHM_BUDGETS["ant_iterations"])
    ants_per_target = int(ALGORITHM_BUDGETS["ants_per_target_per_iteration"])
    max_steps = int(ALGORITHM_BUDGETS["ant_walk_step_multiplier"]) * graph.number_of_nodes()
    pheromone = {canonical_edge(u, v): 1.0 for u, v in graph.edges()}
    discovered: dict[int, list[list[int]]] = defaultdict(list)
    messages = 0
    rng = random.Random(
        stable_seed(
            scenario.seed,
            scenario.condition.name,
            "ant_trails",
            "post" if post_change else "pre",
        )
    )
    for _ in range(iterations):
        successful: list[list[int]] = []
        for target in sorted(demands):
            for _ant in range(ants_per_target):
                path, walk_messages = _ant_walk(
                    graph,
                    scenario.source,
                    target,
                    pheromone,
                    rng,
                    max_steps=max_steps,
                )
                messages += walk_messages
                if path:
                    successful.append(path)
                    discovered[target].append(path)
        for edge in list(pheromone):
            pheromone[edge] *= 0.72
        for path in successful:
            deposit = 1.0 / max(1e-6, path_cost(graph, path))
            for edge in path_edges(path):
                pheromone[edge] = pheromone.get(edge, 0.0) + 28.0 * deposit

    candidates: dict[int, list[list[int]]] = {}
    for target in sorted(demands):
        unique = {tuple(path): path for path in discovered.get(target, [])}
        ranked = sorted(unique.values(), key=lambda path: (path_cost(graph, path), tuple(path)))
        if nx.has_path(graph, scenario.source, target):
            learned = nx.shortest_path(
                graph,
                scenario.source,
                target,
                weight=lambda u, v, data: float(data["weight"])
                / max(0.05, pheromone.get(canonical_edge(u, v), 1.0)),
            )
            ranked.append(list(learned))
        candidates[target] = ranked[:3]
    return _allocate_candidate_paths(
        graph,
        demands,
        candidates,
        messages=messages,
        search_steps=iterations,
        details={
            "analogue": "pheromone reinforcement with evaporation",
            "iterations": iterations,
            "ants_per_target_per_iteration": ants_per_target,
            "simplification": "self-avoiding stochastic walks followed by learned-cost path extraction",
        },
    )


def strategy_bee_foraging_paths(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    scout_count = int(ALGORITHM_BUDGETS["bee_scout_paths_per_target"])
    recruit_count = int(ALGORITHM_BUDGETS["bee_recruited_paths_per_target"])
    scouts, messages = _k_shortest_candidates(
        graph,
        scenario.source,
        demands,
        count=scout_count,
    )
    recruited: dict[int, list[list[int]]] = {}
    for target, paths in scouts.items():
        ranked: list[tuple[float, tuple[int, ...], list[int]]] = []
        for path in paths:
            bottleneck = min(float(graph[u][v]["capacity"]) for u, v in zip(path, path[1:]))
            noise = 0.97 + 0.06 * _u01(
                scenario.seed,
                scenario.condition.name,
                "bee_reward",
                post_change,
                target,
                tuple(path),
            )
            reward = noise * bottleneck * max(1, demands[target]) / max(1e-6, path_cost(graph, path))
            ranked.append((-reward, tuple(path), path))
            messages += len(path) + min(scenario.condition.bandwidth_limit, len(path) * 2)
        recruited[target] = [path for _, _, path in sorted(ranked)[:recruit_count]]
    return _allocate_candidate_paths(
        graph,
        demands,
        recruited,
        messages=messages,
        search_steps=len(demands) * (scout_count + 1),
        details={
            "analogue": "scout exploration plus waggle-style recruitment",
            "scout_paths_per_target": scout_count,
            "recruited_paths_per_target": recruit_count,
            "simplification": "bounded k-shortest scouts ranked by noisy capacity-adjusted reward",
        },
    )


def _slime_mold_path(
    graph: nx.Graph,
    source: int,
    target: int,
    *,
    iterations: int,
) -> tuple[list[int], int]:
    if not nx.has_path(graph, source, target):
        return [], 0
    nodes = sorted(nx.node_connected_component(graph, source))
    if target not in nodes:
        return [], 0
    index = {node: idx for idx, node in enumerate(nodes)}
    conductance = {canonical_edge(u, v): 1.0 for u, v in graph.subgraph(nodes).edges()}
    messages = 0
    for _ in range(iterations):
        laplacian = np.zeros((len(nodes), len(nodes)), dtype=float)
        for u, v, data in graph.subgraph(nodes).edges(data=True):
            edge = canonical_edge(u, v)
            coefficient = conductance[edge] / max(1e-9, float(data["weight"]))
            i = index[u]
            j = index[v]
            laplacian[i, i] += coefficient
            laplacian[j, j] += coefficient
            laplacian[i, j] -= coefficient
            laplacian[j, i] -= coefficient
        injection = np.zeros(len(nodes), dtype=float)
        injection[index[source]] = 1.0
        injection[index[target]] = -1.0
        anchor = index[target]
        keep = [idx for idx in range(len(nodes)) if idx != anchor]
        reduced = laplacian[np.ix_(keep, keep)]
        rhs = injection[keep]
        try:
            solved = np.linalg.solve(reduced, rhs)
        except np.linalg.LinAlgError:
            solved = np.linalg.lstsq(reduced, rhs, rcond=None)[0]
        pressure = np.zeros(len(nodes), dtype=float)
        pressure[keep] = solved
        updated: dict[Edge, float] = {}
        for u, v, data in graph.subgraph(nodes).edges(data=True):
            edge = canonical_edge(u, v)
            flux = conductance[edge] / max(1e-9, float(data["weight"])) * (
                pressure[index[u]] - pressure[index[v]]
            )
            updated[edge] = max(0.02, 0.76 * conductance[edge] + 0.24 * abs(float(flux)))
            messages += 1
        conductance = updated
    path = nx.shortest_path(
        graph,
        source,
        target,
        weight=lambda u, v, data: float(data["weight"])
        / max(0.02, conductance.get(canonical_edge(u, v), 0.02)),
    )
    return list(path), messages


def strategy_slime_mold_routing(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    iterations = int(ALGORITHM_BUDGETS["slime_mold_iterations_per_target"])
    candidates: dict[int, list[list[int]]] = {}
    messages = 0
    for target in sorted(demands):
        path, target_messages = _slime_mold_path(
            graph,
            scenario.source,
            target,
            iterations=iterations,
        )
        candidates[target] = [path] if path else []
        messages += target_messages
    return _allocate_candidate_paths(
        graph,
        demands,
        candidates,
        messages=messages,
        search_steps=iterations,
        details={
            "analogue": "Physarum-style conductance adaptation",
            "iterations_per_target": iterations,
            "primitive": "NumPy grounded Laplacian pressure solve plus NetworkX path extraction",
            "simplification": "single-commodity target solves; no biological growth or continuous-time claim",
        },
    )


def strategy_mycelium_network(scenario: Scenario, post_change: bool) -> RoutingPlan:
    graph = scenario_graph(scenario, post_change=post_change)
    demands = demands_for(scenario, post_change=post_change)
    path_budget = int(ALGORITHM_BUDGETS["mycelium_diverse_paths_per_target"])
    reuse: dict[Edge, int] = defaultdict(int)
    candidates: dict[int, list[list[int]]] = defaultdict(list)
    messages = 0
    for target in sorted(demands, key=lambda item: (-demands[item], item)):
        for _ in range(path_budget):
            try:
                path = nx.shortest_path(
                    graph,
                    scenario.source,
                    target,
                    weight=lambda u, v, data: float(data["weight"])
                    * (
                        1.0
                        + 0.85 * reuse[canonical_edge(u, v)]
                        + 0.35 * float(data["failure_risk"])
                    ),
                )
            except nx.NetworkXNoPath:
                break
            candidates[target].append(list(path))
            for edge in path_edges(path):
                reuse[edge] += 1
            messages += graph.number_of_edges()
    return _allocate_candidate_paths(
        graph,
        demands,
        dict(candidates),
        messages=messages,
        search_steps=len(demands) * path_budget,
        details={
            "analogue": "redundant nutrient-seeking network with local risk avoidance",
            "diverse_paths_per_target": path_budget,
            "simplification": "sequential overlap-penalized shortest paths with split load allocation",
            "known_failure_mode": "may overbuild paths and message load when failures are rare",
        },
    )


# Literal StrategySpec calls preserve AST discovery by BUILD_FULL_GEOMETRY_PROTOCOL_FIELD.
STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec(
        "dijkstra",
        "baseline",
        "dijkstra",
        "Independent weighted shortest paths recomputed after the change.",
        "NetworkX dijkstra_path per target; unit-capacity-aware allocation is sequential.",
        strategy_dijkstra,
    ),
    StrategySpec(
        "a_star",
        "baseline",
        "a_star",
        "Independent A* paths with a Euclidean positional heuristic.",
        "NetworkX astar_path per target with a graph-derived admissible Euclidean lower bound.",
        strategy_a_star,
    ),
    StrategySpec(
        "min_cost_flow",
        "baseline",
        "min_cost_flow",
        "Network-wide maximum flow with minimum integerized routing cost.",
        "NetworkX max_flow_min_cost on symmetric directed arcs; target demands terminate at a super-sink.",
        strategy_min_cost_flow,
    ),
    StrategySpec(
        "k_shortest_redundancy",
        "baseline",
        "k_shortest_redundancy",
        "Up to four weighted simple paths per target with residual-capacity allocation.",
        "NetworkX shortest_simple_paths; this is a bounded redundancy baseline, not exhaustive routing.",
        strategy_k_shortest_redundancy,
    ),
    StrategySpec(
        "ant_trails",
        "geometry_family",
        "ant_trails",
        "Pheromone reinforcement and evaporation under a fixed ant-walk budget.",
        "Self-avoiding synthetic walkers; no biological fidelity or convergence guarantee.",
        strategy_ant_trails,
    ),
    StrategySpec(
        "bee_foraging_paths",
        "geometry_family",
        "bee_foraging_paths",
        "Scout paths recruited by capacity-adjusted, deterministically jittered reward.",
        "Bounded k-shortest scouts stand in for exploration and waggle communication.",
        strategy_bee_foraging_paths,
    ),
    StrategySpec(
        "slime_mold_routing",
        "geometry_family",
        "slime_mold_routing",
        "Physarum-style conductance updates followed by learned-cost path extraction.",
        "Discrete single-target Laplacian solves; not a continuous biological simulation.",
        strategy_slime_mold_routing,
    ),
    StrategySpec(
        "mycelium_network",
        "geometry_family",
        "mycelium_network",
        "Risk-aware diverse paths with overlap penalties and split load.",
        "Sequential NetworkX paths approximate local repair and load sharing; overbuild is retained.",
        strategy_mycelium_network,
    ),
)


def _cost_scale(graph: nx.Graph, source: int, targets: Iterable[int]) -> float:
    costs: list[float] = []
    for target in targets:
        try:
            costs.append(float(nx.shortest_path_length(graph, source, target, weight="weight")))
        except nx.NetworkXNoPath:
            continue
    return max(1.0, mean(costs) if costs else 100.0)


def evaluate_strategy(
    scenario: Scenario,
    spec: StrategySpec,
    *,
    measure_runtime: bool = True,
) -> dict[str, Any]:
    started = time.perf_counter_ns()
    initial = spec.build(scenario, False)
    recovered = spec.build(scenario, True)
    elapsed_ms = (time.perf_counter_ns() - started) / 1_000_000.0 if measure_runtime else 0.0
    graph = scenario_graph(scenario, post_change=True)
    demands = demands_for(scenario, post_change=True)
    total_demand = float(sum(demands.values()))
    delivered = sum(min(float(demands[target]), recovered.deliveries.get(target, 0.0)) for target in demands)
    delivery_rate = delivered / max(1.0, total_demand)
    routed_cost = 0.0
    maximum_edge_load = 0.0
    for edge, flow in recovered.edge_flow.items():
        u, v = edge
        if not graph.has_edge(u, v):
            continue
        routed_cost += flow * float(graph[u][v]["weight"])
        maximum_edge_load = max(
            maximum_edge_load,
            flow / max(1.0, float(graph[u][v]["capacity"])),
        )
    cost_scale = _cost_scale(graph, scenario.source, demands)
    unmet_rate = 1.0 - delivery_rate
    path_cost_per_delivery = routed_cost / max(1.0, delivered) + unmet_rate * cost_scale * 3.0
    failed_initial_edges = len(set(initial.edge_flow) & set(scenario.failed_edges))
    changed_edges = len(set(initial.edge_flow) ^ set(recovered.edge_flow))
    recovery_steps = recovered.search_steps + failed_initial_edges + changed_edges
    messages = initial.messages + recovered.messages
    cost_score = 1.0 / (1.0 + path_cost_per_delivery / cost_scale)
    recovery_score = 1.0 / (
        1.0 + recovery_steps / max(1.0, len(demands) * 4.0)
    )
    load_score = 1.0 / (1.0 + maximum_edge_load)
    message_score = 1.0 / (
        1.0 + messages / max(1.0, graph.number_of_edges() * max(1, len(demands)) * 6.0)
    )
    score = (
        0.52 * delivery_rate
        + 0.22 * cost_score
        + 0.11 * recovery_score
        + 0.09 * load_score
        + 0.06 * message_score
    )
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "failure_mode": scenario.condition.failure_mode,
        "seed": scenario.seed,
        "strategy": spec.name,
        "kind": spec.kind,
        "family_id": spec.family_id,
        "delivery_rate": round(delivery_rate, 6),
        "path_cost_per_delivery": round(path_cost_per_delivery, 6),
        "recovery_steps": int(recovery_steps),
        "maximum_edge_load": round(maximum_edge_load, 6),
        "messages": int(messages),
        "runtime_ms": round(elapsed_ms, 6),
        "runtime_receipt": {
            "timer": "time.perf_counter_ns",
            "measured": measure_runtime,
            "excluded_from_score": True,
        },
        "score": round(score, 6),
        "delivered_units": round(delivered, 6),
        "demand_units": round(total_demand, 6),
        "failed_initial_route_edge_count": failed_initial_edges,
        "changed_route_edge_count": changed_edges,
        "algorithm_details": recovered.details,
    }


def build_scenarios(split: str, *, scenario_count: int, seed_base: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index in range(scenario_count):
        for condition in CONDITIONS:
            seed = seed_base + index * 149 + len(condition.name)
            scenarios.append(generate_scenario(seed, condition, split=split))
    return scenarios


def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["strategy"])].append(row)
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
            "mean_delivery_rate": round(mean(float(item["delivery_rate"]) for item in items), 6),
            "mean_path_cost_per_delivery": round(
                mean(float(item["path_cost_per_delivery"]) for item in items),
                6,
            ),
            "mean_recovery_steps": round(mean(float(item["recovery_steps"]) for item in items), 6),
            "mean_maximum_edge_load": round(
                mean(float(item["maximum_edge_load"]) for item in items),
                6,
            ),
            "mean_messages": round(mean(float(item["messages"]) for item in items), 6),
            "mean_runtime_ms": round(mean(float(item["runtime_ms"]) for item in items), 6),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            -float(row["mean_delivery_rate"]),
            float(row["mean_path_cost_per_delivery"]),
            float(row["mean_recovery_steps"]),
            str(row["strategy"]),
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def aggregate_by_condition(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["condition"]), str(row["strategy"]))].append(row)
    output: list[dict[str, Any]] = []
    for (condition, strategy), items in sorted(grouped.items()):
        summary = aggregate(items)[strategy]
        output.append({"condition": condition, **summary})
    return output


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires values")
    return float(np.quantile(np.asarray(values, dtype=float), quantile, method="linear"))


def paired_bootstrap_mean_ci(
    deltas: list[float],
    *,
    resamples: int = 2000,
    seed: int = 20260729,
) -> dict[str, Any]:
    if not deltas:
        raise ValueError("paired bootstrap requires values")
    values = np.asarray(deltas, dtype=float)
    rng = np.random.default_rng(seed)
    indices = rng.integers(0, len(values), size=(resamples, len(values)))
    bootstrap_means = values[indices].mean(axis=1)
    return {
        "observed_mean_delta": round(float(values.mean()), 6),
        "ci95": [
            round(percentile(bootstrap_means.tolist(), 0.025), 6),
            round(percentile(bootstrap_means.tolist(), 0.975), 6),
        ],
        "resamples": resamples,
        "seed": seed,
        "paired_scenario_count": len(deltas),
    }


def confirmatory_promotion_gate(
    development_ranked: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    validation_ranked: list[dict[str, Any]],
) -> dict[str, Any]:
    development_geometries = [row for row in development_ranked if row["kind"] == "geometry_family"]
    development_baselines = [row for row in development_ranked if row["kind"] == "baseline"]
    if not development_geometries or not development_baselines:
        return {"gate": "missing_development_pair", "promoted": False}
    selected_geometry_name = str(development_geometries[0]["strategy"])
    selected_baseline_name = str(development_baselines[0]["strategy"])
    validation_by_strategy = {str(row["strategy"]): row for row in validation_ranked}
    selected_geometry = validation_by_strategy[selected_geometry_name]
    selected_baseline = validation_by_strategy[selected_baseline_name]

    paired: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in validation_rows:
        strategy = str(row["strategy"])
        if strategy in {selected_geometry_name, selected_baseline_name}:
            paired[(str(row["condition"]), int(row["seed"]))][strategy] = row
    complete = [
        (key, rows[selected_geometry_name], rows[selected_baseline_name])
        for key, rows in sorted(paired.items())
        if selected_geometry_name in rows and selected_baseline_name in rows
    ]
    score_deltas = [
        float(candidate["score"]) - float(baseline["score"])
        for _, candidate, baseline in complete
    ]
    delivery_deltas = [
        float(candidate["delivery_rate"]) - float(baseline["delivery_rate"])
        for _, candidate, baseline in complete
    ]
    cost_deltas = [
        float(candidate["path_cost_per_delivery"]) - float(baseline["path_cost_per_delivery"])
        for _, candidate, baseline in complete
    ]
    bootstrap = paired_bootstrap_mean_ci(
        score_deltas,
        resamples=int(ALGORITHM_BUDGETS["paired_bootstrap_resamples"]),
    )
    by_condition: dict[str, list[float]] = defaultdict(list)
    for (condition, _), candidate, baseline in complete:
        by_condition[condition].append(float(candidate["score"]) - float(baseline["score"]))
    condition_guardrails = [
        {
            "condition": condition,
            "paired_scenario_count": len(deltas),
            "score_delta": round(mean(deltas), 6),
            "noninferiority_margin": ALGORITHM_BUDGETS["condition_noninferiority_margin"],
            "passes_noninferiority": mean(deltas)
            >= -float(ALGORITHM_BUDGETS["condition_noninferiority_margin"]),
        }
        for condition, deltas in sorted(by_condition.items())
    ]
    checks = {
        "overall_score_delta_positive": mean(score_deltas) > 0.0,
        "paired_ci95_lower_bound_positive": float(bootstrap["ci95"][0]) > 0.0,
        "delivery_rate_no_regression": mean(delivery_deltas) >= 0.0,
        "path_cost_no_material_regression": mean(cost_deltas)
        <= 0.05 * max(1.0, float(selected_baseline["mean_path_cost_per_delivery"])),
        "all_condition_score_noninferiority": all(
            row["passes_noninferiority"] for row in condition_guardrails
        ),
    }
    promoted = all(checks.values())
    return {
        "gate": (
            "candidate_geometry_promoted_internal_confirmatory"
            if promoted
            else "candidate_geometry_not_promoted_internal_confirmatory"
        ),
        "promoted": promoted,
        "selection": {
            "source": "development_only",
            "selected_geometry": selected_geometry_name,
            "selected_baseline": selected_baseline_name,
            "validation_pair_locked_before_scoring": True,
            "multiple_comparison_control": (
                "one geometry and one baseline selected on development; all other "
                "validation comparisons are descriptive and losses are retained"
            ),
        },
        "best_geometry": selected_geometry,
        "best_baseline": selected_baseline,
        "score_delta_vs_locked_baseline": round(mean(score_deltas), 6),
        "delivery_rate_delta_vs_locked_baseline": round(mean(delivery_deltas), 6),
        "path_cost_delta_vs_locked_baseline": round(mean(cost_deltas), 6),
        "paired_bootstrap": bootstrap,
        "condition_guardrails": condition_guardrails,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "claim_language": (
            "Internal generated-lane result only. A passing internal confirmatory gate "
            "would still not establish live, source-conditioned, field, government-approved, "
            "universal, trading, or real-dollar performance."
        ),
    }


def retain_negative_results(
    validation_ranked: list[dict[str, Any]],
    condition_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baselines = [row for row in validation_ranked if row["kind"] == "baseline"]
    geometries = [row for row in validation_ranked if row["kind"] == "geometry_family"]
    losses: list[dict[str, Any]] = []
    for geometry in geometries:
        for baseline in baselines:
            delta = float(geometry["mean_score"]) - float(baseline["mean_score"])
            if delta <= 0.0:
                losses.append(
                    {
                        "scope": "validation_aggregate",
                        "geometry_family": geometry["family_id"],
                        "baseline": baseline["family_id"],
                        "score_delta": round(delta, 6),
                        "retained": True,
                    }
                )
    condition_map = {
        (str(row["condition"]), str(row["strategy"])): row
        for row in condition_rows
    }
    for geometry in geometries:
        for baseline in baselines:
            for condition in sorted({row["condition"] for row in condition_rows}):
                candidate = condition_map[(str(condition), str(geometry["strategy"]))]
                reference = condition_map[(str(condition), str(baseline["strategy"]))]
                delta = float(candidate["mean_score"]) - float(reference["mean_score"])
                if delta <= 0.0:
                    losses.append(
                        {
                            "scope": "named_failure_condition",
                            "condition": condition,
                            "geometry_family": geometry["family_id"],
                            "baseline": baseline["family_id"],
                            "score_delta": round(delta, 6),
                            "retained": True,
                        }
                    )
    return {
        "retention_policy": "all nonpositive geometry-versus-baseline score deltas are retained",
        "retained": True,
        "loss_count": len(losses),
        "losses": losses,
    }


def deterministic_result_view(summary: dict[str, Any]) -> dict[str, Any]:
    def without_runtime(value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: without_runtime(item)
                for key, item in value.items()
                if key not in {"runtime_ms", "mean_runtime_ms", "runtime_receipt"}
            }
        if isinstance(value, list):
            return [without_runtime(item) for item in value]
        return value

    return {
        "schema": summary["schema"],
        "lane": summary["lane"],
        "evidence_boundary": summary["evidence_boundary"],
        "protocol": summary["protocol"],
        "development": {
            "seed_base": summary["development"]["seed_base"],
            "scenario_count": summary["development"]["scenario_count"],
            "leaderboard": without_runtime(summary["development"]["leaderboard"]),
        },
        "validation": {
            "seed_base": summary["validation"]["seed_base"],
            "scenario_count": summary["validation"]["scenario_count"],
            "leaderboard": without_runtime(summary["validation"]["leaderboard"]),
            "condition_leaderboards": without_runtime(
                summary["validation"]["condition_leaderboards"]
            ),
        },
        "promotion_gate": without_runtime(summary["promotion_gate"]),
        "negative_result_retention": summary["negative_result_retention"],
        "claim_gate": summary["claim_gate"],
    }


def render_scorecard(summary: dict[str, Any]) -> str:
    gate = summary["promotion_gate"]
    lines = [
        "# Geometry Mission Network Routing Benchmark",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Evidence Boundary",
        "",
        summary["evidence_boundary"],
        "",
        "## Frozen Protocol",
        "",
        f"- Protocol SHA-256: `{summary['protocol']['protocol_sha256']}`",
        f"- Development seed base: `{summary['development']['seed_base']}`",
        f"- Validation seed base: `{summary['validation']['seed_base']}`",
        f"- Named failure conditions: {', '.join(row['name'] for row in summary['conditions'])}",
        "- Ranking scope: `mission_network_routing` only",
        "- Cross-lane ranking performed: `false`",
        "",
        "## Current Outcome",
        "",
        f"- Status: `{summary['status']}`",
        f"- Development-locked geometry: `{gate['selection']['selected_geometry']}`",
        f"- Development-locked baseline: `{gate['selection']['selected_baseline']}`",
        f"- Confirmatory gate: `{gate['gate']}`",
        f"- Score delta: `{gate['score_delta_vs_locked_baseline']}`",
        f"- Paired CI95: `{gate['paired_bootstrap']['ci95']}`",
        f"- Retained losses: `{summary['negative_result_retention']['loss_count']}`",
        "",
        "## Validation Leaderboard",
        "",
        "| Rank | Strategy | Kind | Score | Delivery | Cost/Delivery | Recovery Steps | Max Edge Load | Messages | Runtime ms |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in summary["validation"]["leaderboard"]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | {row['mean_score']} | "
            f"{row['mean_delivery_rate']} | {row['mean_path_cost_per_delivery']} | "
            f"{row['mean_recovery_steps']} | {row['mean_maximum_edge_load']} | "
            f"{row['mean_messages']} | {row['mean_runtime_ms']} |"
        )
    lines.extend(
        [
            "",
            "## Algorithm Boundaries",
            "",
        ]
    )
    for row in summary["strategies"]:
        lines.append(
            f"- `{row['family_id']}`: {row['simplification']}"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            gate["claim_language"],
            "",
            "Runtime is measured with `time.perf_counter_ns` and excluded from the score. "
            "All deterministic routing metrics are covered by the deterministic result hash.",
        ]
    )
    return "\n".join(lines)


def run_suite(
    out_dir: Path,
    *,
    development_scenarios: int = 5,
    validation_scenarios: int = 7,
) -> dict[str, Any]:
    if development_scenarios < 1 or validation_scenarios < 1:
        raise ValueError("scenario counts must be positive")
    generated_utc = now_utc()
    started = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    protocol = {
        "schema": "geometry_mission_network_routing_protocol_v1",
        "source_sha256": sha256_file(Path(__file__)),
        "development_scenarios_per_condition": development_scenarios,
        "validation_scenarios_per_condition": validation_scenarios,
        "development_seed_base": DEVELOPMENT_SEED_BASE,
        "validation_seed_base": VALIDATION_SEED_BASE,
        "condition_names": [condition.name for condition in CONDITIONS],
        "baseline_ids": [spec.family_id for spec in STRATEGIES if spec.kind == "baseline"],
        "geometry_family_ids": [
            spec.family_id for spec in STRATEGIES if spec.kind == "geometry_family"
        ],
        "lane_metrics": [
            "delivery_rate",
            "path_cost_per_delivery",
            "recovery_steps",
            "maximum_edge_load",
            "messages",
            "runtime_ms",
        ],
        "metric_definitions": {
            "delivery_rate": (
                "post-change delivered demand units divided by post-change requested demand units"
            ),
            "path_cost_per_delivery": (
                "post-change flow-weighted edge cost divided by delivered units plus a "
                "three-times shortest-path-scale penalty for the unmet-demand fraction"
            ),
            "recovery_steps": (
                "declared post-change search rounds plus failed initial route edges plus "
                "the symmetric difference between initial and recovered flow-edge sets"
            ),
            "maximum_edge_load": (
                "maximum post-change routed flow divided by declared edge capacity"
            ),
            "messages": (
                "deterministic algorithm primitive-operation proxy reported without clipping"
            ),
            "runtime_ms": (
                "measured wall runtime for initial and recovered plans using perf_counter_ns; "
                "reported as a receipt and excluded from the score"
            ),
        },
        "score_contract": {
            "delivery_rate_weight": 0.52,
            "normalized_path_cost_weight": 0.22,
            "normalized_recovery_weight": 0.11,
            "normalized_edge_load_weight": 0.09,
            "normalized_messages_weight": 0.06,
            "runtime_weight": 0.0,
        },
        "algorithm_budgets": ALGORITHM_BUDGETS,
        "runtime_scored": False,
        "cross_lane_ranking_allowed": False,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    protocol["protocol_sha256"] = sha256_payload(protocol)
    development = build_scenarios(
        "development",
        scenario_count=development_scenarios,
        seed_base=DEVELOPMENT_SEED_BASE,
    )
    validation = build_scenarios(
        "validation",
        scenario_count=validation_scenarios,
        seed_base=VALIDATION_SEED_BASE,
    )
    development_rows = [
        evaluate_strategy(scenario, spec)
        for scenario in development
        for spec in STRATEGIES
    ]
    validation_rows = [
        evaluate_strategy(scenario, spec)
        for scenario in validation
        for spec in STRATEGIES
    ]
    development_ranked = ranked_aggregate(aggregate(development_rows))
    validation_ranked = ranked_aggregate(aggregate(validation_rows))
    condition_rows = aggregate_by_condition(validation_rows)
    gate = confirmatory_promotion_gate(
        development_ranked,
        validation_rows,
        validation_ranked,
    )
    negatives = retain_negative_results(validation_ranked, condition_rows)
    runtime_rows = development_rows + validation_rows
    runtime_by_strategy: list[dict[str, Any]] = []
    for spec in STRATEGIES:
        values = [
            float(row["runtime_ms"])
            for row in runtime_rows
            if row["strategy"] == spec.name
        ]
        runtime_by_strategy.append(
            {
                "strategy": spec.name,
                "measurement_count": len(values),
                "mean_runtime_ms": round(mean(values), 6),
                "median_runtime_ms": round(median(values), 6),
                "maximum_runtime_ms": round(max(values), 6),
            }
        )
    summary: dict[str, Any] = {
        "schema": "geometry_mission_network_routing_benchmark_v1",
        "generated_utc": generated_utc,
        "status": (
            "INTERNAL_SYNTHETIC_CONFIRMATORY_PASS_NO_EXTERNAL_CLAIM"
            if gate["promoted"]
            else "INTERNAL_SYNTHETIC_CONFIRMATORY_NONPROMOTION"
        ),
        "lane": "mission_network_routing",
        "ranking_scope": "mission_network_routing_only",
        "cross_lane_ranking_performed": False,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "protocol": protocol,
        "strategies": [
            {
                "name": spec.name,
                "kind": spec.kind,
                "family_id": spec.family_id,
                "description": spec.description,
                "simplification": spec.simplification,
            }
            for spec in STRATEGIES
        ],
        "conditions": [condition.__dict__ for condition in CONDITIONS],
        "development": {
            "seed_base": DEVELOPMENT_SEED_BASE,
            "scenario_count": len(development),
            "leaderboard": development_ranked,
        },
        "validation": {
            "seed_base": VALIDATION_SEED_BASE,
            "scenario_count": len(validation),
            "leaderboard": validation_ranked,
            "condition_leaderboards": condition_rows,
        },
        "promotion_gate": gate,
        "negative_result_retention": negatives,
        "runtime_receipts": {
            "timer": "time.perf_counter_ns",
            "measured": True,
            "excluded_from_score": True,
            "evaluation_count": len(runtime_rows),
            "suite_wall_seconds": round(time.perf_counter() - started, 6),
            "by_strategy": runtime_by_strategy,
        },
        "claim_gate": {
            "performance_result_generated": True,
            "lane_specific_generated_benchmark": True,
            "source_conditioned_evidence": False,
            "live_breadth_evidence": False,
            "live_validation": False,
            "field_validation": False,
            "external_validation": False,
            "customer_validation": False,
            "government_approval": False,
            "universal_superiority": False,
            "cross_lane_champion": False,
            "trading_alpha": False,
            "real_dollar_claim": False,
        },
    }
    summary["deterministic_result_sha256"] = sha256_payload(
        deterministic_result_view(summary)
    )
    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(
        render_scorecard(summary).rstrip() + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "geometry_mission_network_routing_manifest_v1",
        "generated_utc": generated_utc,
        "protocol_sha256": protocol["protocol_sha256"],
        "deterministic_result_sha256": summary["deterministic_result_sha256"],
        "files": {
            "summary.json": {
                "sha256": sha256_file(summary_path),
                "bytes": summary_path.stat().st_size,
            },
            "SCORECARD.md": {
                "sha256": sha256_file(scorecard_path),
                "bytes": scorecard_path.stat().st_size,
            },
        },
    }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--development-scenarios", type=int, default=5)
    parser.add_argument("--validation-scenarios", type=int, default=7)
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
    latest.write_text(
        json.dumps({"run_dir": str(out_dir), **summary}, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
                "status": summary["status"],
                "selected_geometry": summary["promotion_gate"]["selection"][
                    "selected_geometry"
                ],
                "selected_baseline": summary["promotion_gate"]["selection"][
                    "selected_baseline"
                ],
                "gate": summary["promotion_gate"]["gate"],
                "score_delta": summary["promotion_gate"][
                    "score_delta_vs_locked_baseline"
                ],
                "retained_loss_count": summary["negative_result_retention"][
                    "loss_count"
                ],
                "deterministic_result_sha256": summary[
                    "deterministic_result_sha256"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
