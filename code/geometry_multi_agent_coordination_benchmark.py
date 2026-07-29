"""Synthetic multi-agent coordination benchmark for Geometry Championship V1.

This bounded sidecar evaluates four declared geometry families and three
registry baselines on identical generated moving-goal, obstacle, and
communication-limit scenarios. It uses frozen development and validation
splits and retains negative results.

The simulator is deliberately simplified. It is generated software evidence,
not source-conditioned, live, hardware, field, safety, certification,
government-approval, trading, universal-superiority, or real-dollar evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable

import numpy as np
import scipy
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cdist


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "geometry_multi_agent_coordination"
DEVELOPMENT_SEED_BASE = 23_000
VALIDATION_SEED_BASE = 47_000
AGENT_COUNT = 7
STEPS = 72
DT = 0.16
WORLD_WIDTH = 22.0
WORLD_HEIGHT = 14.0
LANE_METRICS = (
    "mission_completion_rate",
    "collision_rate",
    "formation_error",
    "messages",
    "runtime_ms",
)
EVIDENCE_BOUNDARY = (
    "Generated multi-agent coordination software benchmark only. Moving goals, "
    "obstacles, communication limits, dynamics, messages, collisions, formation "
    "error, and runtime are synthetic assumptions. Results are not "
    "source-conditioned, live, hardware, field, safety, certification, "
    "government-approval, trading, universal-superiority, or real-dollar evidence. "
    "Cross-lane ranking is forbidden."
)

Vector = np.ndarray
ControlFn = Callable[["ControlContext"], tuple[Vector, int, int]]


@dataclass(frozen=True)
class Condition:
    name: str
    obstacle_layout: str
    communication_radius: float
    communication_dropout: float
    goal_speed: float
    moving_hazard: bool
    failure_condition: str


@dataclass(frozen=True)
class Scenario:
    split: str
    condition: Condition
    seed: int
    initial_positions: tuple[tuple[float, float], ...]
    initial_velocities: tuple[tuple[float, float], ...]
    goal_initial: tuple[float, float]
    goal_velocity: tuple[float, float]
    obstacles: tuple[tuple[float, float, float, float, float], ...]
    steps: int
    dt: float
    speed_limit: float
    acceleration_limit: float
    agent_radius: float
    completion_radius: float


@dataclass(frozen=True)
class ControlContext:
    scenario: Scenario
    step: int
    positions: Vector
    velocities: Vector
    goal: Vector
    goal_velocity: Vector
    obstacle_states: Vector
    adjacency: Vector


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    simplification: str
    control: ControlFn


CONDITIONS = (
    Condition(
        "open_moving_goal",
        "sparse",
        8.0,
        0.00,
        0.16,
        False,
        "Long pursuit exposes slow convergence and formation lag.",
    ),
    Condition(
        "cluttered_corridor",
        "corridor",
        5.2,
        0.04,
        0.12,
        False,
        "Rigid formations can collide or stall in alternating narrow passages.",
    ),
    Condition(
        "communication_limited",
        "scattered",
        2.9,
        0.38,
        0.14,
        False,
        "Coordination can fragment when local links are sparse and dropped.",
    ),
    Condition(
        "moving_hazard",
        "moving_hazard",
        4.6,
        0.10,
        0.18,
        True,
        "Reactive swirls can trade directness for avoidance or destabilize.",
    ),
    Condition(
        "blocked_approach",
        "blocked_approach",
        4.0,
        0.16,
        0.20,
        False,
        "Encirclement and flocking can over-coordinate near blocked approach arcs.",
    ),
)

ALGORITHM_DEFINITIONS = {
    "independent_shortest_path": {
        "definition": (
            "Each agent independently tracks a fixed target-centered ring slot and "
            "uses a deterministic circular-obstacle detour vector."
        ),
        "simplification": (
            "Reactive Euclidean path control; it is not an exact graph shortest-path "
            "solver and has no inter-agent communication."
        ),
    },
    "consensus_control": {
        "definition": (
            "Goal tracking plus local position and velocity consensus over the "
            "current communication graph, with separation and obstacle repulsion."
        ),
        "simplification": (
            "Linear consensus gains are fixed; no delay model, estimator, or "
            "stability certificate is claimed."
        ),
    },
    "model_predictive_control": {
        "definition": (
            "Centralized Hungarian slot assignment followed by deterministic "
            "finite-horizon candidate-velocity evaluation and receding-horizon control."
        ),
        "simplification": (
            "Discrete velocity candidates approximate MPC; this is not a solved "
            "nonlinear constrained optimal-control problem."
        ),
    },
    "bird_v_formation_flocking": {
        "definition": (
            "Leader-relative V slots aligned to target motion, local velocity "
            "alignment, separation, and obstacle repulsion."
        ),
        "simplification": (
            "Wake sharing is represented by formation geometry only; no aerodynamic "
            "wake or energy model is simulated."
        ),
    },
    "boids_swarm_flocking": {
        "definition": (
            "Reynolds-style separation, alignment, and cohesion combined with "
            "moving-goal attraction and obstacle repulsion."
        ),
        "simplification": (
            "Fixed gains and radii replace learned or adaptive flocking behavior."
        ),
    },
    "fish_school_vortex": {
        "definition": (
            "Local schooling alignment and cohesion with tangential vortex avoidance "
            "around nearby obstacles and the moving hazard."
        ),
        "simplification": (
            "The vortex term is a planar control analogue, not fluid dynamics or "
            "biological schooling validation."
        ),
    },
    "wolf_pack_pursuit_paths": {
        "definition": (
            "Role-based target encirclement using Hungarian assignment to moving ring "
            "slots, pursuit pressure, local alignment, and separation."
        ),
        "simplification": (
            "Roles are reassigned centrally each step; no learned hunting policy or "
            "animal-behavior claim is made."
        ),
    },
}


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


def clip_rows(vectors: Vector, max_norm: float) -> Vector:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    scales = np.minimum(1.0, max_norm / np.maximum(norms, 1e-12))
    return vectors * scales


def unit_rows(vectors: Vector) -> Vector:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.maximum(norms, 1e-12)


def _round_points(points: Vector) -> tuple[tuple[float, float], ...]:
    return tuple((round(float(row[0]), 6), round(float(row[1]), 6)) for row in points)


def _layout_obstacles(
    condition: Condition,
    rng: np.random.Generator,
) -> tuple[tuple[float, float, float, float, float], ...]:
    if condition.obstacle_layout == "sparse":
        raw = [(10.5, 2.4, 0.8, 0.0, 0.0)]
    elif condition.obstacle_layout == "corridor":
        raw = [
            (7.8, 3.0, 1.25, 0.0, 0.0),
            (7.8, 10.7, 1.25, 0.0, 0.0),
            (11.0, 6.9, 1.35, 0.0, 0.0),
            (14.2, 3.3, 1.20, 0.0, 0.0),
            (14.2, 10.4, 1.20, 0.0, 0.0),
        ]
    elif condition.obstacle_layout == "scattered":
        raw = [
            (7.5, 4.0, 0.85, 0.0, 0.0),
            (10.2, 9.5, 0.95, 0.0, 0.0),
            (13.0, 5.8, 1.00, 0.0, 0.0),
        ]
    elif condition.obstacle_layout == "moving_hazard":
        raw = [
            (8.5, 3.8, 0.90, 0.0, 0.0),
            (11.2, 9.6, 0.95, 0.0, 0.0),
            (14.0, 6.6, 1.05, 0.0, 0.0),
            (12.0, 2.2, 0.72, 0.0, 0.46),
        ]
    elif condition.obstacle_layout == "blocked_approach":
        raw = [
            (13.8, 4.0, 1.00, 0.0, 0.0),
            (14.8, 6.5, 1.15, 0.0, 0.0),
            (13.8, 9.2, 1.00, 0.0, 0.0),
            (17.0, 3.4, 0.82, 0.0, 0.0),
            (17.2, 10.2, 0.82, 0.0, 0.0),
        ]
    else:
        raise ValueError(f"unknown obstacle layout: {condition.obstacle_layout}")
    obstacles: list[tuple[float, float, float, float, float]] = []
    for index, (x, y, radius, vx, vy) in enumerate(raw):
        jitter = rng.uniform(-0.14, 0.14, size=2)
        obstacles.append(
            (
                round(float(x + jitter[0]), 6),
                round(float(y + jitter[1]), 6),
                radius,
                vx,
                vy if index == len(raw) - 1 or not condition.moving_hazard else 0.0,
            )
        )
    return tuple(obstacles)


def generate_scenario(seed: int, condition: Condition, *, split: str) -> Scenario:
    rng = np.random.default_rng(seed)
    base_positions = np.asarray(
        [
            (2.0, 4.1),
            (2.0, 6.0),
            (2.0, 7.9),
            (3.5, 4.8),
            (3.5, 6.7),
            (4.9, 5.4),
            (4.9, 7.3),
        ],
        dtype=float,
    )
    positions = base_positions + rng.uniform(-0.10, 0.10, size=base_positions.shape)
    velocities = rng.uniform(-0.03, 0.03, size=base_positions.shape)
    goal_y = 6.8 + float(rng.uniform(-0.35, 0.35))
    heading = 0.45 + float(rng.uniform(-0.10, 0.10))
    goal_velocity = np.asarray(
        [
            condition.goal_speed * math.cos(heading),
            condition.goal_speed * math.sin(heading),
        ]
    )
    return Scenario(
        split=split,
        condition=condition,
        seed=seed,
        initial_positions=_round_points(positions),
        initial_velocities=_round_points(velocities),
        goal_initial=(round(17.4 + float(rng.uniform(-0.25, 0.25)), 6), round(goal_y, 6)),
        goal_velocity=(round(float(goal_velocity[0]), 6), round(float(goal_velocity[1]), 6)),
        obstacles=_layout_obstacles(condition, rng),
        steps=STEPS,
        dt=DT,
        speed_limit=1.65,
        acceleration_limit=2.35,
        agent_radius=0.28,
        completion_radius=3.1,
    )


def build_scenarios(split: str, *, scenario_count: int, seed_base: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index in range(scenario_count):
        for condition in CONDITIONS:
            seed = seed_base + index * 149 + len(condition.name)
            scenarios.append(generate_scenario(seed, condition, split=split))
    return scenarios


def ring_slots(goal: Vector, goal_velocity: Vector, *, radius: float = 1.35) -> Vector:
    heading = math.atan2(float(goal_velocity[1]), float(goal_velocity[0]))
    angles = heading + np.linspace(0.0, 2.0 * math.pi, AGENT_COUNT, endpoint=False)
    return goal + radius * np.column_stack((np.cos(angles), np.sin(angles)))


def v_slots(goal: Vector, goal_velocity: Vector) -> Vector:
    forward = goal_velocity.copy()
    if float(np.linalg.norm(forward)) < 1e-9:
        forward = np.asarray((1.0, 0.0))
    forward = forward / np.linalg.norm(forward)
    lateral = np.asarray((-forward[1], forward[0]))
    offsets = [(0.0, 0.0)]
    for rank in range(1, 4):
        offsets.append((-0.72 * rank, 0.68 * rank))
        offsets.append((-0.72 * rank, -0.68 * rank))
    return np.asarray(
        [goal - 0.65 * forward + back * forward + side * lateral for back, side in offsets]
    )


def local_graph(
    positions: Vector,
    communication_radius: float,
    *,
    seed: int,
    condition_name: str,
    step: int,
    dropout: float,
) -> Vector:
    distances = cdist(positions, positions)
    adjacency = (distances <= communication_radius) & (distances > 0.0)
    for left in range(len(positions)):
        for right in range(left + 1, len(positions)):
            if adjacency[left, right] and _u01(
                seed,
                condition_name,
                "link",
                step,
                left,
                right,
            ) < dropout:
                adjacency[left, right] = False
                adjacency[right, left] = False
    return adjacency


def obstacle_repulsion(positions: Vector, obstacle_states: Vector, *, margin: float = 1.55) -> Vector:
    forces = np.zeros_like(positions)
    for obstacle in obstacle_states:
        center = obstacle[:2]
        radius = float(obstacle[2])
        delta = positions - center
        distances = np.linalg.norm(delta, axis=1)
        active = distances < radius + margin
        safe = np.maximum(distances, 1e-6)
        strength = np.where(active, (radius + margin - distances) / margin, 0.0)
        forces += unit_rows(delta) * strength[:, None] * 2.4
        forces[~np.isfinite(forces)] = 0.0
        forces[distances < 1e-6] += np.asarray((2.4, 0.0))
    return forces


def agent_separation(positions: Vector, *, desired: float = 0.82) -> Vector:
    distances = cdist(positions, positions)
    forces = np.zeros_like(positions)
    for index in range(len(positions)):
        mask = (distances[index] > 0.0) & (distances[index] < desired)
        if np.any(mask):
            delta = positions[index] - positions[mask]
            scale = (desired - distances[index, mask]) / desired
            forces[index] = np.sum(unit_rows(delta) * scale[:, None], axis=0)
    return forces


def neighbor_terms(context: ControlContext) -> tuple[Vector, Vector, Vector]:
    cohesion = np.zeros_like(context.positions)
    alignment = np.zeros_like(context.positions)
    separation = agent_separation(context.positions)
    for index in range(len(context.positions)):
        neighbors = np.flatnonzero(context.adjacency[index])
        if len(neighbors):
            cohesion[index] = np.mean(context.positions[neighbors], axis=0) - context.positions[index]
            alignment[index] = np.mean(context.velocities[neighbors], axis=0) - context.velocities[index]
    return cohesion, alignment, separation


def target_acceleration(
    context: ControlContext,
    targets: Vector,
    *,
    attraction: float,
    damping: float,
) -> Vector:
    desired_velocity = unit_rows(targets - context.positions) * context.scenario.speed_limit
    return attraction * (desired_velocity - context.velocities) - damping * context.velocities


def control_independent_shortest_path(context: ControlContext) -> tuple[Vector, int, int]:
    targets = ring_slots(context.goal, context.goal_velocity)
    acceleration = target_acceleration(context, targets, attraction=1.15, damping=0.08)
    acceleration += 1.15 * obstacle_repulsion(context.positions, context.obstacle_states)
    return acceleration, 0, AGENT_COUNT


def control_consensus_control(context: ControlContext) -> tuple[Vector, int, int]:
    targets = ring_slots(context.goal, context.goal_velocity)
    cohesion, alignment, separation = neighbor_terms(context)
    acceleration = target_acceleration(context, targets, attraction=0.92, damping=0.06)
    acceleration += 0.34 * cohesion + 0.48 * alignment + 1.10 * separation
    acceleration += 1.05 * obstacle_repulsion(context.positions, context.obstacle_states)
    messages = int(np.count_nonzero(context.adjacency))
    return acceleration, messages, AGENT_COUNT + messages


def control_model_predictive_control(context: ControlContext) -> tuple[Vector, int, int]:
    slots = ring_slots(context.goal + 5.0 * context.scenario.dt * context.goal_velocity, context.goal_velocity)
    rows, cols = linear_sum_assignment(cdist(context.positions, slots))
    assigned = np.zeros_like(context.positions)
    assigned[rows] = slots[cols]
    candidate_angles = np.linspace(0.0, 2.0 * math.pi, 16, endpoint=False)
    candidate_velocities = context.scenario.speed_limit * np.column_stack(
        (np.cos(candidate_angles), np.sin(candidate_angles))
    )
    horizon = 5.0 * context.scenario.dt
    selected = np.zeros_like(context.velocities)
    evaluations = 0
    predicted_peers = context.positions + horizon * context.velocities
    for index in range(AGENT_COUNT):
        predicted = context.positions[index] + horizon * candidate_velocities
        costs = np.linalg.norm(predicted - assigned[index], axis=1)
        for obstacle in context.obstacle_states:
            clearance = np.linalg.norm(predicted - obstacle[:2], axis=1) - float(obstacle[2])
            costs += np.where(clearance < 1.15, (1.15 - clearance) * 5.0, 0.0)
        peer_distance = cdist(predicted, np.delete(predicted_peers, index, axis=0))
        costs += np.sum(np.where(peer_distance < 0.72, (0.72 - peer_distance) * 3.0, 0.0), axis=1)
        costs += 0.12 * np.linalg.norm(candidate_velocities - context.velocities[index], axis=1)
        selected[index] = candidate_velocities[int(np.argmin(costs))]
        evaluations += len(candidate_velocities)
    acceleration = 1.55 * (selected - context.velocities)
    messages = AGENT_COUNT * (AGENT_COUNT - 1)
    return acceleration, messages, evaluations


def control_bird_v_formation_flocking(context: ControlContext) -> tuple[Vector, int, int]:
    targets = v_slots(context.goal, context.goal_velocity)
    cohesion, alignment, separation = neighbor_terms(context)
    acceleration = target_acceleration(context, targets, attraction=1.04, damping=0.07)
    acceleration += 0.16 * cohesion + 0.56 * alignment + 1.26 * separation
    acceleration += 1.12 * obstacle_repulsion(context.positions, context.obstacle_states)
    messages = int(np.count_nonzero(context.adjacency))
    return acceleration, messages, AGENT_COUNT + messages


def control_boids_swarm_flocking(context: ControlContext) -> tuple[Vector, int, int]:
    cohesion, alignment, separation = neighbor_terms(context)
    goal_pull = unit_rows(context.goal[None, :] - context.positions) * context.scenario.speed_limit
    acceleration = 0.84 * (goal_pull - context.velocities)
    acceleration += 0.40 * cohesion + 0.66 * alignment + 1.52 * separation
    acceleration += 1.24 * obstacle_repulsion(context.positions, context.obstacle_states)
    messages = int(np.count_nonzero(context.adjacency))
    return acceleration, messages, AGENT_COUNT + messages


def control_fish_school_vortex(context: ControlContext) -> tuple[Vector, int, int]:
    cohesion, alignment, separation = neighbor_terms(context)
    goal_pull = unit_rows(context.goal[None, :] - context.positions) * context.scenario.speed_limit
    vortex = np.zeros_like(context.positions)
    for obstacle in context.obstacle_states:
        delta = context.positions - obstacle[:2]
        distances = np.linalg.norm(delta, axis=1)
        active = distances < float(obstacle[2]) + 2.45
        tangent = np.column_stack((-delta[:, 1], delta[:, 0]))
        tangent = unit_rows(tangent)
        strength = np.where(
            active,
            (float(obstacle[2]) + 2.45 - distances) / 2.45,
            0.0,
        )
        vortex += tangent * strength[:, None]
    acceleration = 0.76 * (goal_pull - context.velocities)
    acceleration += 0.34 * cohesion + 0.62 * alignment + 1.38 * separation
    acceleration += 1.35 * obstacle_repulsion(context.positions, context.obstacle_states)
    acceleration += 0.86 * vortex
    messages = int(np.count_nonzero(context.adjacency))
    return acceleration, messages, AGENT_COUNT + messages + len(context.obstacle_states)


def control_wolf_pack_pursuit_paths(context: ControlContext) -> tuple[Vector, int, int]:
    predicted_goal = context.goal + 3.0 * context.scenario.dt * context.goal_velocity
    slots = ring_slots(predicted_goal, context.goal_velocity, radius=1.55)
    rows, cols = linear_sum_assignment(cdist(context.positions, slots))
    assigned = np.zeros_like(context.positions)
    assigned[rows] = slots[cols]
    _, alignment, separation = neighbor_terms(context)
    acceleration = target_acceleration(context, assigned, attraction=1.20, damping=0.05)
    acceleration += 0.50 * alignment + 1.42 * separation
    acceleration += 1.10 * obstacle_repulsion(context.positions, context.obstacle_states)
    messages = int(np.count_nonzero(context.adjacency))
    return acceleration, messages, AGENT_COUNT * AGENT_COUNT + messages


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec(
        "independent_shortest_path",
        "baseline",
        "independent_shortest_path",
        "Independent moving-goal path control baseline.",
        str(ALGORITHM_DEFINITIONS["independent_shortest_path"]["simplification"]),
        control_independent_shortest_path,
    ),
    StrategySpec(
        "consensus_control",
        "baseline",
        "consensus_control",
        "Local graph consensus control baseline.",
        str(ALGORITHM_DEFINITIONS["consensus_control"]["simplification"]),
        control_consensus_control,
    ),
    StrategySpec(
        "model_predictive_control",
        "baseline",
        "model_predictive_control",
        "Finite-horizon receding-control baseline.",
        str(ALGORITHM_DEFINITIONS["model_predictive_control"]["simplification"]),
        control_model_predictive_control,
    ),
    StrategySpec(
        "bird_v_formation_flocking",
        "geometry_family",
        "bird_v_formation_flocking",
        "Leader-relative V-formation coordination analogue.",
        str(ALGORITHM_DEFINITIONS["bird_v_formation_flocking"]["simplification"]),
        control_bird_v_formation_flocking,
    ),
    StrategySpec(
        "boids_swarm_flocking",
        "geometry_family",
        "boids_swarm_flocking",
        "Separation-alignment-cohesion flocking analogue.",
        str(ALGORITHM_DEFINITIONS["boids_swarm_flocking"]["simplification"]),
        control_boids_swarm_flocking,
    ),
    StrategySpec(
        "fish_school_vortex",
        "geometry_family",
        "fish_school_vortex",
        "Schooling with tangential hazard-avoidance analogue.",
        str(ALGORITHM_DEFINITIONS["fish_school_vortex"]["simplification"]),
        control_fish_school_vortex,
    ),
    StrategySpec(
        "wolf_pack_pursuit_paths",
        "geometry_family",
        "wolf_pack_pursuit_paths",
        "Role-based pursuit and encirclement analogue.",
        str(ALGORITHM_DEFINITIONS["wolf_pack_pursuit_paths"]["simplification"]),
        control_wolf_pack_pursuit_paths,
    ),
)


def _advance_bounded(point: Vector, velocity: Vector, dt: float, margin: float) -> tuple[Vector, Vector]:
    updated = point + velocity * dt
    adjusted_velocity = velocity.copy()
    for axis, upper in ((0, WORLD_WIDTH), (1, WORLD_HEIGHT)):
        if updated[axis] < margin:
            updated[axis] = margin + (margin - updated[axis])
            adjusted_velocity[axis] = abs(adjusted_velocity[axis])
        elif updated[axis] > upper - margin:
            updated[axis] = upper - margin - (updated[axis] - (upper - margin))
            adjusted_velocity[axis] = -abs(adjusted_velocity[axis])
    return updated, adjusted_velocity


def _largest_component_fraction(adjacency: Vector) -> float:
    seen: set[int] = set()
    largest = 0
    for start in range(len(adjacency)):
        if start in seen:
            continue
        stack = [start]
        component: set[int] = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            seen.add(node)
            stack.extend(int(value) for value in np.flatnonzero(adjacency[node]))
        largest = max(largest, len(component))
    return largest / max(1, len(adjacency))


def _coordination_error(positions: Vector, goal: Vector, adjacency: Vector) -> float:
    centroid = np.mean(positions, axis=0)
    centroid_error = clamp(float(np.linalg.norm(centroid - goal)) / 8.0)
    spread = float(np.mean(np.linalg.norm(positions - centroid, axis=1)))
    spread_error = clamp(abs(spread - 1.35) / 2.7)
    connectivity_error = 1.0 - _largest_component_fraction(adjacency)
    distances = cdist(positions, positions)
    close_pairs = np.triu((distances > 0.0) & (distances < 0.72), k=1)
    pair_count = AGENT_COUNT * (AGENT_COUNT - 1) / 2
    separation_error = float(np.count_nonzero(close_pairs)) / pair_count
    return clamp(
        0.48 * centroid_error
        + 0.24 * spread_error
        + 0.18 * connectivity_error
        + 0.10 * separation_error
    )


def simulate_strategy(scenario: Scenario, spec: StrategySpec) -> dict[str, Any]:
    positions = np.asarray(scenario.initial_positions, dtype=float)
    velocities = np.asarray(scenario.initial_velocities, dtype=float)
    goal = np.asarray(scenario.goal_initial, dtype=float)
    goal_velocity = np.asarray(scenario.goal_velocity, dtype=float)
    obstacle_states = np.asarray(scenario.obstacles, dtype=float)
    total_messages = 0
    control_evaluations = 0
    collision_events = 0
    formation_errors: list[float] = []
    pair_opportunities = AGENT_COUNT * (AGENT_COUNT - 1) // 2
    collision_opportunities = scenario.steps * (
        pair_opportunities + AGENT_COUNT * len(obstacle_states)
    )
    started_ns = time.perf_counter_ns()

    for step in range(scenario.steps):
        adjacency = local_graph(
            positions,
            scenario.condition.communication_radius,
            seed=scenario.seed,
            condition_name=scenario.condition.name,
            step=step,
            dropout=scenario.condition.communication_dropout,
        )
        context = ControlContext(
            scenario=scenario,
            step=step,
            positions=positions.copy(),
            velocities=velocities.copy(),
            goal=goal.copy(),
            goal_velocity=goal_velocity.copy(),
            obstacle_states=obstacle_states.copy(),
            adjacency=adjacency.copy(),
        )
        acceleration, messages, evaluations = spec.control(context)
        acceleration = clip_rows(np.asarray(acceleration, dtype=float), scenario.acceleration_limit)
        velocities = clip_rows(velocities + acceleration * scenario.dt, scenario.speed_limit)
        positions = positions + velocities * scenario.dt
        for axis, upper in ((0, WORLD_WIDTH), (1, WORLD_HEIGHT)):
            below = positions[:, axis] < scenario.agent_radius
            above = positions[:, axis] > upper - scenario.agent_radius
            positions[below, axis] = scenario.agent_radius
            positions[above, axis] = upper - scenario.agent_radius
            velocities[below, axis] = np.abs(velocities[below, axis])
            velocities[above, axis] = -np.abs(velocities[above, axis])

        goal, goal_velocity = _advance_bounded(
            goal,
            goal_velocity,
            scenario.dt,
            margin=1.2,
        )
        for index in range(len(obstacle_states)):
            obstacle_states[index, :2], obstacle_states[index, 3:5] = _advance_bounded(
                obstacle_states[index, :2],
                obstacle_states[index, 3:5],
                scenario.dt,
                margin=float(obstacle_states[index, 2]) + 0.15,
            )

        agent_distances = cdist(positions, positions)
        agent_collisions = np.triu(
            (agent_distances > 0.0) & (agent_distances < 2.0 * scenario.agent_radius),
            k=1,
        )
        collision_events += int(np.count_nonzero(agent_collisions))
        for obstacle in obstacle_states:
            clearance = np.linalg.norm(positions - obstacle[:2], axis=1)
            collision_events += int(
                np.count_nonzero(clearance < float(obstacle[2]) + scenario.agent_radius)
            )
        if step >= scenario.steps // 2:
            formation_errors.append(_coordination_error(positions, goal, adjacency))
        total_messages += int(messages)
        control_evaluations += int(evaluations)

    finished_ns = time.perf_counter_ns()
    final_distances = np.linalg.norm(positions - goal, axis=1)
    arrival_fraction = float(np.mean(final_distances <= scenario.completion_radius))
    centroid_distance = float(np.linalg.norm(np.mean(positions, axis=0) - goal))
    collision_rate = collision_events / max(1, collision_opportunities)
    formation_error = mean(formation_errors)
    mission_complete = float(
        centroid_distance <= 2.65
        and arrival_fraction >= 5.0 / AGENT_COUNT
        and collision_rate <= 0.025
    )
    maximum_messages = scenario.steps * AGENT_COUNT * (AGENT_COUNT - 1)
    message_efficiency = clamp(1.0 - total_messages / max(1.0, maximum_messages))
    score = (
        0.36 * mission_complete
        + 0.20 * arrival_fraction
        + 0.20 * clamp(1.0 - collision_rate / 0.06)
        + 0.16 * clamp(1.0 - formation_error)
        + 0.08 * message_efficiency
    )
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "failure_condition": scenario.condition.failure_condition,
        "seed": scenario.seed,
        "strategy": spec.name,
        "kind": spec.kind,
        "family_id": spec.family_id,
        "mission_completion_rate": round(mission_complete, 6),
        "agent_arrival_fraction": round(arrival_fraction, 6),
        "collision_rate": round(collision_rate, 6),
        "formation_error": round(formation_error, 6),
        "messages": total_messages,
        "runtime_ms": round((finished_ns - started_ns) / 1_000_000.0, 6),
        "control_evaluations": control_evaluations,
        "score": round(score, 6),
        "final_centroid_goal_distance": round(centroid_distance, 6),
        "collision_events": collision_events,
        "collision_opportunities": collision_opportunities,
    }


def deterministic_projection(row: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in row.items() if key != "runtime_ms"}


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
            "mean_mission_completion_rate": round(
                mean(float(item["mission_completion_rate"]) for item in items),
                6,
            ),
            "mean_agent_arrival_fraction": round(
                mean(float(item["agent_arrival_fraction"]) for item in items),
                6,
            ),
            "mean_collision_rate": round(
                mean(float(item["collision_rate"]) for item in items),
                6,
            ),
            "mean_formation_error": round(
                mean(float(item["formation_error"]) for item in items),
                6,
            ),
            "mean_messages": round(mean(float(item["messages"]) for item in items), 6),
            "mean_runtime_ms": round(mean(float(item["runtime_ms"]) for item in items), 6),
            "mean_control_evaluations": round(
                mean(float(item["control_evaluations"]) for item in items),
                6,
            ),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            -float(row["mean_mission_completion_rate"]),
            float(row["mean_collision_rate"]),
            float(row["mean_formation_error"]),
            float(row["mean_messages"]),
            row["strategy"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("percentile requires at least one value")
    return float(np.quantile(np.asarray(values, dtype=float), quantile))


def paired_bootstrap_mean_ci(
    deltas: list[float],
    *,
    resamples: int = 1_000,
    seed: int = 20260729,
) -> dict[str, Any]:
    if not deltas:
        raise ValueError("paired bootstrap requires at least one delta")
    rng = np.random.default_rng(seed)
    values = np.asarray(deltas, dtype=float)
    indexes = rng.integers(0, len(values), size=(resamples, len(values)))
    means = np.mean(values[indexes], axis=1)
    return {
        "observed_mean_delta": round(float(np.mean(values)), 6),
        "ci95": [
            round(percentile(means.tolist(), 0.025), 6),
            round(percentile(means.tolist(), 0.975), 6),
        ],
        "resamples": resamples,
        "seed": seed,
        "paired_scenario_count": len(values),
    }


def _paired_rows(
    rows: list[dict[str, Any]],
    candidate_name: str,
    baseline_name: str,
) -> list[tuple[tuple[str, int], dict[str, Any], dict[str, Any]]]:
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if row["strategy"] not in {candidate_name, baseline_name}:
            continue
        key = (str(row["condition"]), int(row["seed"]))
        grouped[key][str(row["strategy"])] = row
    return [
        (key, by_strategy[candidate_name], by_strategy[baseline_name])
        for key, by_strategy in sorted(grouped.items())
        if candidate_name in by_strategy and baseline_name in by_strategy
    ]


def confirmatory_gate(
    development_ranked: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    validation_ranked: list[dict[str, Any]],
    *,
    bootstrap_resamples: int,
) -> dict[str, Any]:
    development_geometry = next(
        (row for row in development_ranked if row["kind"] == "geometry_family"),
        None,
    )
    development_baseline = next(
        (row for row in development_ranked if row["kind"] == "baseline"),
        None,
    )
    if not development_geometry or not development_baseline:
        return {"gate": "missing_development_pair", "promoted": False}
    candidate_name = str(development_geometry["strategy"])
    baseline_name = str(development_baseline["strategy"])
    validation_by_strategy = {
        str(row["strategy"]): row for row in validation_ranked
    }
    candidate = validation_by_strategy.get(candidate_name)
    baseline = validation_by_strategy.get(baseline_name)
    pairs = _paired_rows(validation_rows, candidate_name, baseline_name)
    if not candidate or not baseline or not pairs:
        return {
            "gate": "locked_pair_missing_from_validation",
            "promoted": False,
            "selection": {
                "selected_geometry": candidate_name,
                "selected_baseline": baseline_name,
            },
        }
    score_deltas = [
        float(candidate_row["score"]) - float(baseline_row["score"])
        for _, candidate_row, baseline_row in pairs
    ]
    completion_deltas = [
        float(candidate_row["mission_completion_rate"])
        - float(baseline_row["mission_completion_rate"])
        for _, candidate_row, baseline_row in pairs
    ]
    collision_deltas = [
        float(candidate_row["collision_rate"]) - float(baseline_row["collision_rate"])
        for _, candidate_row, baseline_row in pairs
    ]
    formation_deltas = [
        float(candidate_row["formation_error"]) - float(baseline_row["formation_error"])
        for _, candidate_row, baseline_row in pairs
    ]
    bootstrap = paired_bootstrap_mean_ci(
        score_deltas,
        resamples=bootstrap_resamples,
    )
    condition_guardrails: list[dict[str, Any]] = []
    for condition in sorted({key[0] for key, _, _ in pairs}):
        condition_pairs = [pair for pair in pairs if pair[0][0] == condition]
        delta = mean(
            float(candidate_row["score"]) - float(baseline_row["score"])
            for _, candidate_row, baseline_row in condition_pairs
        )
        condition_guardrails.append(
            {
                "condition": condition,
                "paired_scenario_count": len(condition_pairs),
                "score_delta": round(delta, 6),
                "noninferiority_margin": 0.03,
                "passes_noninferiority": delta >= -0.03,
            }
        )
    checks = {
        "overall_score_delta_positive": mean(score_deltas) > 0.0,
        "paired_ci95_lower_bound_positive": float(bootstrap["ci95"][0]) > 0.0,
        "mission_completion_noninferiority": mean(completion_deltas) >= 0.0,
        "collision_rate_noninferiority": mean(collision_deltas) <= 0.005,
        "formation_error_noninferiority": mean(formation_deltas) <= 0.03,
        "all_condition_score_noninferiority": all(
            row["passes_noninferiority"] for row in condition_guardrails
        ),
    }
    promoted = all(checks.values())
    return {
        "gate": (
            "candidate_geometry_promoted_internal_synthetic"
            if promoted
            else "candidate_geometry_not_promoted_internal_synthetic"
        ),
        "promoted": promoted,
        "selection": {
            "source": "development_only",
            "selected_geometry": candidate_name,
            "selected_baseline": baseline_name,
            "validation_pair_locked_before_scoring": True,
            "multiple_comparison_control": (
                "one geometry and one baseline selected on development; the full "
                "validation leaderboard remains descriptive"
            ),
        },
        "best_geometry": candidate,
        "best_baseline": baseline,
        "score_delta_vs_locked_baseline": round(mean(score_deltas), 6),
        "mission_completion_delta": round(mean(completion_deltas), 6),
        "collision_rate_delta": round(mean(collision_deltas), 6),
        "formation_error_delta": round(mean(formation_deltas), 6),
        "paired_bootstrap": bootstrap,
        "condition_guardrails": condition_guardrails,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "claim_language": (
            "At most an internally promoted synthetic lane candidate. It is not "
            "source-conditioned, live, hardware, field, certified, government-approved, "
            "universally superior, or associated with realized savings or revenue."
        ),
    }


def negative_result_retention(
    validation_rows: list[dict[str, Any]],
    validation_ranked: list[dict[str, Any]],
    locked_baseline: str,
) -> dict[str, Any]:
    by_strategy = {str(row["strategy"]): row for row in validation_ranked}
    baseline = by_strategy[locked_baseline]
    overall_losses = [
        {
            "family_id": row["family_id"],
            "mean_score": row["mean_score"],
            "baseline": locked_baseline,
            "baseline_mean_score": baseline["mean_score"],
            "score_delta": round(
                float(row["mean_score"]) - float(baseline["mean_score"]),
                6,
            ),
        }
        for row in validation_ranked
        if row["kind"] == "geometry_family"
        and float(row["mean_score"]) <= float(baseline["mean_score"])
    ]
    condition_losses: list[dict[str, Any]] = []
    for spec in STRATEGIES:
        if spec.kind != "geometry_family":
            continue
        pairs = _paired_rows(validation_rows, spec.name, locked_baseline)
        for condition in sorted({key[0] for key, _, _ in pairs}):
            selected = [pair for pair in pairs if pair[0][0] == condition]
            delta = mean(
                float(candidate["score"]) - float(baseline_row["score"])
                for _, candidate, baseline_row in selected
            )
            if delta <= 0.0:
                condition_losses.append(
                    {
                        "family_id": spec.family_id,
                        "condition": condition,
                        "baseline": locked_baseline,
                        "paired_scenario_count": len(selected),
                        "mean_score_delta": round(delta, 6),
                        "retained": True,
                    }
                )
    return {
        "retained": True,
        "all_validation_rows_retained": True,
        "validation_row_count": len(validation_rows),
        "overall_geometry_losses_vs_locked_baseline": overall_losses,
        "condition_losses_vs_locked_baseline": condition_losses,
        "loss_count": len(overall_losses) + len(condition_losses),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def scenario_receipt(scenario: Scenario) -> dict[str, Any]:
    payload = {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "seed": scenario.seed,
        "initial_positions": scenario.initial_positions,
        "initial_velocities": scenario.initial_velocities,
        "goal_initial": scenario.goal_initial,
        "goal_velocity": scenario.goal_velocity,
        "obstacles": scenario.obstacles,
        "steps": scenario.steps,
        "dt": scenario.dt,
    }
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "seed": scenario.seed,
        "sha256": sha256_payload(payload),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def render_scorecard(summary: dict[str, Any]) -> str:
    gate = summary["promotion_gate"]
    negative = summary["negative_results"]
    lines = [
        "# Geometry Multi-Agent Coordination Benchmark",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Evidence Boundary",
        "",
        summary["evidence_boundary"],
        "",
        "## Protocol",
        "",
        f"- Development scenarios: `{summary['development']['scenario_count']}`",
        f"- Validation scenarios: `{summary['validation']['scenario_count']}`",
        f"- Development seed base: `{summary['development']['seed_base']}`",
        f"- Validation seed base: `{summary['validation']['seed_base']}`",
        f"- Split overlap: `{str(summary['protocol']['split_overlap']).lower()}`",
        f"- Protocol SHA-256: `{summary['protocol']['protocol_sha256']}`",
        "- Runtime is retained as a machine-dependent receipt and does not decide promotion.",
        "",
        "## Current Result",
        "",
        f"- Development-locked geometry: `{gate.get('selection', {}).get('selected_geometry', 'n/a')}`",
        f"- Development-locked baseline: `{gate.get('selection', {}).get('selected_baseline', 'n/a')}`",
        f"- Gate: `{gate.get('gate', 'n/a')}`",
        f"- Internally promoted synthetic candidate: `{str(gate.get('promoted', False)).lower()}`",
        f"- Score delta: `{gate.get('score_delta_vs_locked_baseline', 'n/a')}`",
        f"- Paired CI95: `{gate.get('paired_bootstrap', {}).get('ci95', 'n/a')}`",
        f"- Failed checks: `{', '.join(gate.get('failed_checks', [])) or 'none'}`",
        "",
        "## Negative Results Retained",
        "",
        f"- Loss records retained: `{negative['loss_count']}`",
        f"- All validation rows retained: `{str(negative['all_validation_rows_retained']).lower()}`",
        "",
        "| Family | Condition | Baseline | Mean Score Delta |",
        "|---|---|---|---:|",
    ]
    for row in negative["condition_losses_vs_locked_baseline"]:
        lines.append(
            f"| {row['family_id']} | {row['condition']} | {row['baseline']} | "
            f"{row['mean_score_delta']} |"
        )
    lines.extend(
        [
            "",
            "## Validation Leaderboard",
            "",
            "| Rank | Strategy | Kind | Score | Completion | Collision | Formation Error | Messages | Runtime ms |",
            "|---:|---|---|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in summary["validation"]["leaderboard"]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | "
            f"{row['mean_score']} | {row['mean_mission_completion_rate']} | "
            f"{row['mean_collision_rate']} | {row['mean_formation_error']} | "
            f"{row['mean_messages']} | {row['mean_runtime_ms']} |"
        )
    lines.extend(["", "## Algorithm Definitions And Simplifications", ""])
    for name, definition in summary["algorithm_definitions"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                str(definition["definition"]),
                "",
                f"Simplification: {definition['simplification']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Claim Boundary",
            "",
            gate.get("claim_language", EVIDENCE_BOUNDARY),
            "",
            "No cross-lane ranking was performed.",
        ]
    )
    return "\n".join(lines)


def run_suite(
    out_dir: Path,
    *,
    development_scenarios: int = 4,
    validation_scenarios: int = 6,
    bootstrap_resamples: int = 1_000,
) -> dict[str, Any]:
    if development_scenarios < 1 or validation_scenarios < 1:
        raise ValueError("scenario counts must be positive")
    if bootstrap_resamples < 100:
        raise ValueError("bootstrap_resamples must be at least 100")
    generated_utc = now_utc()
    out_dir.mkdir(parents=True, exist_ok=True)
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
    development_seeds = {scenario.seed for scenario in development}
    validation_seeds = {scenario.seed for scenario in validation}
    if development_seeds & validation_seeds:
        raise ValueError("development and validation seeds overlap")

    development_started = time.perf_counter()
    development_rows = [
        simulate_strategy(scenario, spec)
        for scenario in development
        for spec in STRATEGIES
    ]
    development_wall_seconds = time.perf_counter() - development_started
    validation_started = time.perf_counter()
    validation_rows = [
        simulate_strategy(scenario, spec)
        for scenario in validation
        for spec in STRATEGIES
    ]
    validation_wall_seconds = time.perf_counter() - validation_started

    development_leaderboard = ranked_aggregate(aggregate(development_rows))
    validation_leaderboard = ranked_aggregate(aggregate(validation_rows))
    gate = confirmatory_gate(
        development_leaderboard,
        validation_rows,
        validation_leaderboard,
        bootstrap_resamples=bootstrap_resamples,
    )
    locked_baseline = str(gate.get("selection", {}).get("selected_baseline") or "")
    if not locked_baseline:
        raise ValueError("confirmatory gate did not select a baseline")
    negative_results = negative_result_retention(
        validation_rows,
        validation_leaderboard,
        locked_baseline,
    )
    protocol = {
        "schema": "geometry_multi_agent_coordination_protocol_v1",
        "source_sha256": sha256_file(Path(__file__)),
        "frozen_before_validation": True,
        "development_seed_base": DEVELOPMENT_SEED_BASE,
        "validation_seed_base": VALIDATION_SEED_BASE,
        "split_overlap": False,
        "development_scenarios_per_condition": development_scenarios,
        "validation_scenarios_per_condition": validation_scenarios,
        "condition_names": [condition.name for condition in CONDITIONS],
        "strategy_names": [spec.name for spec in STRATEGIES],
        "lane_metrics": list(LANE_METRICS),
        "agent_count": AGENT_COUNT,
        "steps": STEPS,
        "dt": DT,
        "no_cross_lane_ranking": True,
        "runtime_used_for_promotion": False,
        "source_conditioned": False,
    }
    protocol["protocol_sha256"] = sha256_payload(protocol)
    summary = {
        "schema": "geometry_multi_agent_coordination_benchmark_v1",
        "generated_utc": generated_utc,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "lane": "multi_agent_coordination",
        "registry_first_tests": [
            "multi_agent_wake_sharing_v1",
            "boids_coordination_v1",
            "schooling_evasion_v1",
            "encirclement_capture_v1",
        ],
        "lane_metrics": list(LANE_METRICS),
        "libraries": {
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "established_primitives": [
                "scipy.optimize.linear_sum_assignment",
                "scipy.spatial.distance.cdist",
                "linear consensus control",
                "finite-horizon receding control",
                "separation alignment cohesion",
            ],
        },
        "algorithm_definitions": ALGORITHM_DEFINITIONS,
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
        "conditions": [
            {
                "name": condition.name,
                "obstacle_layout": condition.obstacle_layout,
                "communication_radius": condition.communication_radius,
                "communication_dropout": condition.communication_dropout,
                "goal_speed": condition.goal_speed,
                "moving_hazard": condition.moving_hazard,
                "failure_condition": condition.failure_condition,
            }
            for condition in CONDITIONS
        ],
        "protocol": protocol,
        "scenario_receipts": {
            "development": [scenario_receipt(scenario) for scenario in development],
            "validation": [scenario_receipt(scenario) for scenario in validation],
        },
        "execution": {
            "development": {
                "wall_seconds": round(development_wall_seconds, 6),
                "row_count": len(development_rows),
            },
            "validation": {
                "wall_seconds": round(validation_wall_seconds, 6),
                "row_count": len(validation_rows),
            },
            "runtime_receipt_boundary": (
                "Observed on this machine and retained for audit; not deterministic and "
                "not used for promotion."
            ),
        },
        "development": {
            "seed_base": DEVELOPMENT_SEED_BASE,
            "scenario_count": len(development),
            "seed_count": len(development_seeds),
            "leaderboard": development_leaderboard,
        },
        "validation": {
            "seed_base": VALIDATION_SEED_BASE,
            "scenario_count": len(validation),
            "seed_count": len(validation_seeds),
            "leaderboard": validation_leaderboard,
        },
        "promotion_gate": gate,
        "negative_results": negative_results,
        "claim_gate": {
            "lane_specific_generated_benchmark": True,
            "synthetic_only": True,
            "cross_lane_ranking": False,
            "source_conditioned_evidence": False,
            "live_evidence": False,
            "hardware_validation": False,
            "field_validation": False,
            "safety_certification": False,
            "government_approval": False,
            "universal_superiority": False,
            "trading_signal": False,
            "real_dollar_claim": False,
        },
    }

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
    scenario_path = out_dir / "scenario_summary.csv"
    write_csv(
        scenario_path,
        validation_rows,
        [
            "split",
            "condition",
            "failure_condition",
            "seed",
            "strategy",
            "kind",
            "family_id",
            "mission_completion_rate",
            "agent_arrival_fraction",
            "collision_rate",
            "formation_error",
            "messages",
            "runtime_ms",
            "control_evaluations",
            "score",
            "final_centroid_goal_distance",
            "collision_events",
            "collision_opportunities",
        ],
    )
    leaderboard_path = out_dir / "leaderboard.csv"
    write_csv(
        leaderboard_path,
        validation_leaderboard,
        [
            "rank",
            "strategy",
            "kind",
            "family_id",
            "scenario_count",
            "mean_score",
            "median_score",
            "mean_mission_completion_rate",
            "mean_agent_arrival_fraction",
            "mean_collision_rate",
            "mean_formation_error",
            "mean_messages",
            "mean_runtime_ms",
            "mean_control_evaluations",
        ],
    )
    manifest = {
        "schema": "geometry_multi_agent_coordination_manifest_v1",
        "generated_utc": generated_utc,
        "protocol_sha256": protocol["protocol_sha256"],
        "files": {},
    }
    for path in (summary_path, scorecard_path, scenario_path, leaderboard_path):
        manifest["files"][path.name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
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
    parser.add_argument("--development-scenarios", type=int, default=4)
    parser.add_argument("--validation-scenarios", type=int, default=6)
    parser.add_argument("--bootstrap-resamples", type=int, default=1_000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or now_tag()
    out_dir = args.out_root / run_tag
    summary = run_suite(
        out_dir,
        development_scenarios=args.development_scenarios,
        validation_scenarios=args.validation_scenarios,
        bootstrap_resamples=args.bootstrap_resamples,
    )
    latest = args.out_root / "latest.json"
    latest.parent.mkdir(parents=True, exist_ok=True)
    latest_payload = {
        "run_dir": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
        **summary,
    }
    latest.write_text(
        json.dumps(latest_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_dir": latest_payload["run_dir"],
                "selected_geometry": summary["promotion_gate"]["selection"][
                    "selected_geometry"
                ],
                "selected_baseline": summary["promotion_gate"]["selection"][
                    "selected_baseline"
                ],
                "gate": summary["promotion_gate"]["gate"],
                "score_delta": summary["promotion_gate"].get(
                    "score_delta_vs_locked_baseline"
                ),
                "retained_loss_count": summary["negative_results"]["loss_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
