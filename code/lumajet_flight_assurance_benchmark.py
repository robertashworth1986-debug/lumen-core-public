from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import json
import math
import os
import shutil
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, stdev
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROTOCOL = ROOT / "config" / "lumajet_flight_assurance_protocol_v1.json"
DEFAULT_OUT = ROOT / "out" / "lumajet_flight_assurance"

EVIDENCE_BOUNDARY = (
    "Generated offline software simulation only. No output is an actuator command. Results are "
    "not flight control, aircraft or propulsion design, airworthiness evidence, FAA or DoD "
    "approval, field validation, economic proof, or authorization for operational use."
)

MOVES = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (-1, 0),
    (1, 0),
    (-1, 1),
    (0, 1),
    (1, 1),
)


@dataclass(frozen=True)
class ScenarioSpec:
    split: str
    condition_index: int
    condition_name: str
    seed: int


@dataclass
class Environment:
    condition: str
    seed: int
    size: int
    start: tuple[int, int]
    goal: tuple[int, int]
    obstacles: np.ndarray
    clearance: np.ndarray
    wind_true: np.ndarray
    wind_observed: np.ndarray
    turbulence_true: np.ndarray
    turbulence_observed: np.ndarray
    energy_budget: float
    direct_distance: float
    spectral_receipt: dict[str, Any]


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def validate_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    if protocol.get("schema") not in {
        "lumajet_flight_assurance_protocol_v1",
        "lumajet_flight_assurance_protocol_v2",
    }:
        raise ValueError("unexpected LumaJet protocol schema")
    if protocol.get("operational_outputs_allowed") is not False:
        raise ValueError("operational outputs must be disabled")
    if protocol.get("actuator_commands_allowed") is not False:
        raise ValueError("actuator commands must be disabled")
    if (protocol.get("splits") or {}).get("holdout_used_for_selection") is not False:
        raise ValueError("holdout selection must be disabled")
    if int((protocol.get("grid") or {}).get("connectivity") or 0) != 8:
        raise ValueError("this protocol requires eight-connected planning")
    if (protocol.get("grid") or {}).get("diagonal_corner_cutting_allowed") is not False:
        raise ValueError("diagonal corner cutting must remain disabled")

    condition_names = [str(row.get("name") or "") for row in protocol.get("conditions", [])]
    if not condition_names or len(condition_names) != len(set(condition_names)):
        raise ValueError("condition names must be non-empty and unique")
    specialist_names = [str(row.get("name") or "") for row in protocol.get("specialists", [])]
    candidate_names = [str(row.get("name") or "") for row in protocol.get("hybrid_candidates", [])]
    all_names = specialist_names + candidate_names
    if not specialist_names or not candidate_names or len(all_names) != len(set(all_names)):
        raise ValueError("strategy names must be non-empty and unique")
    confirmatory = protocol.get("confirmatory_gate") or {}
    preselected_candidate = confirmatory.get("preselected_candidate")
    preselected_baseline = confirmatory.get("preselected_baseline")
    if bool(preselected_candidate) != bool(preselected_baseline):
        raise ValueError("confirmatory preselection requires both candidate and baseline")
    if preselected_candidate and str(preselected_candidate) not in candidate_names:
        raise ValueError("preselected candidate is not a registered hybrid candidate")
    if preselected_baseline and str(preselected_baseline) not in specialist_names:
        raise ValueError("preselected baseline is not a registered specialist")

    truth_weight_sum = sum(float(value) for value in protocol["truth_score_weights"].values())
    if not math.isclose(truth_weight_sum, 1.0, abs_tol=1e-9):
        raise ValueError("truth score weights must sum to one")
    for candidate in protocol["hybrid_candidates"]:
        candidate_sum = sum(float(value) for value in candidate["selection_weights"].values())
        if not math.isclose(candidate_sum, 1.0, abs_tol=1e-9):
            raise ValueError(f"selection weights must sum to one: {candidate['name']}")

    spectral = protocol["spectral_stress"]
    sample_rate = float(spectral["sample_rate_hz"])
    nyquist = sample_rate / 2.0
    guard_limit = nyquist * float(spectral["nyquist_guard_fraction"])
    frequencies = [float(value) for value in spectral["component_frequencies_hz"]]
    if not frequencies or min(frequencies) <= 0.0 or max(frequencies) > guard_limit:
        raise ValueError("spectral components violate the configured Nyquist guard")
    if float(spectral["amplitude_limit"]) <= 0.0:
        raise ValueError("spectral amplitude limit must be positive")

    return {
        "valid": True,
        "condition_count": len(condition_names),
        "strategy_count": len(all_names),
        "nyquist_hz": nyquist,
        "guard_limit_hz": guard_limit,
        "maximum_component_hz": max(frequencies),
        "all_components_below_guard": True,
        "actuator_commands_disabled": True,
        "holdout_selection_disabled": True,
    }


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def has_open_path(obstacles: np.ndarray, start: tuple[int, int], goal: tuple[int, int]) -> bool:
    size = int(obstacles.shape[0])
    pending = [start]
    seen = {start}
    while pending:
        x, y = pending.pop()
        if (x, y) == goal:
            return True
        for dx, dy in MOVES:
            nx, ny = x + dx, y + dy
            if not (0 <= nx < size and 0 <= ny < size) or obstacles[ny, nx]:
                continue
            if dx and dy and (obstacles[y, nx] or obstacles[ny, x]):
                continue
            point = (nx, ny)
            if point not in seen:
                seen.add(point)
                pending.append(point)
    return False


def carve_direct_corridor(
    obstacles: np.ndarray,
    start: tuple[int, int],
    goal: tuple[int, int],
) -> None:
    steps = max(abs(goal[0] - start[0]), abs(goal[1] - start[1])) + 1
    for index in range(steps):
        fraction = index / max(1, steps - 1)
        x = int(round(start[0] + fraction * (goal[0] - start[0])))
        y = int(round(start[1] + fraction * (goal[1] - start[1])))
        for oy in (-1, 0, 1):
            for ox in (-1, 0, 1):
                nx, ny = x + ox, y + oy
                if 0 <= nx < obstacles.shape[1] and 0 <= ny < obstacles.shape[0]:
                    obstacles[ny, nx] = False


def build_obstacles(
    size: int,
    start: tuple[int, int],
    goal: tuple[int, int],
    condition: dict[str, Any],
    rng: np.random.Generator,
) -> np.ndarray:
    obstacles = np.zeros((size, size), dtype=bool)
    if bool(condition.get("corridor")):
        for wall_index, wall_x in enumerate((size // 3, (2 * size) // 3)):
            gap_center = int(rng.integers(4, size - 4))
            if wall_index == 1:
                gap_center = size - 1 - gap_center
            obstacles[:, wall_x] = True
            obstacles[max(1, gap_center - 2) : min(size - 1, gap_center + 3), wall_x] = False
    for _ in range(int(condition.get("obstacle_count") or 0)):
        center_x = int(rng.integers(5, size - 5))
        center_y = int(rng.integers(3, size - 3))
        radius = float(rng.uniform(1.15, 2.15))
        yy, xx = np.mgrid[0:size, 0:size]
        obstacles |= (xx - center_x) ** 2 + (yy - center_y) ** 2 <= radius**2

    for point in (start, goal):
        x, y = point
        obstacles[max(0, y - 2) : min(size, y + 3), max(0, x - 2) : min(size, x + 3)] = False
    if not has_open_path(obstacles, start, goal):
        carve_direct_corridor(obstacles, start, goal)
    if not has_open_path(obstacles, start, goal):
        raise RuntimeError("deterministic obstacle repair failed")
    return obstacles


def bounded_spectral_field(
    shape: tuple[int, int],
    spectral: dict[str, Any],
    rng: np.random.Generator,
) -> tuple[np.ndarray, dict[str, Any]]:
    sample_rate = float(spectral["sample_rate_hz"])
    sample_count = int(spectral["sample_count"])
    frequencies = np.asarray(spectral["component_frequencies_hz"], dtype=float)
    phases = rng.uniform(0.0, 2.0 * math.pi, size=len(frequencies))
    samples = np.arange(sample_count, dtype=float) / sample_rate
    waveform = np.zeros(sample_count, dtype=float)
    for frequency, phase in zip(frequencies, phases):
        waveform += np.sin(2.0 * math.pi * frequency * samples + phase)
    waveform /= max(1.0, float(len(frequencies)))
    amplitude_limit = float(spectral["amplitude_limit"])
    waveform = np.clip(waveform * amplitude_limit, -amplitude_limit, amplitude_limit)
    positions = np.linspace(0, sample_count - 1, num=shape[0] * shape[1])
    field = np.interp(positions, np.arange(sample_count), waveform).reshape(shape)
    nyquist = sample_rate / 2.0
    guard_limit = nyquist * float(spectral["nyquist_guard_fraction"])
    return field, {
        "sample_rate_hz": sample_rate,
        "sample_count": sample_count,
        "component_frequencies_hz": frequencies.tolist(),
        "nyquist_hz": nyquist,
        "guard_limit_hz": guard_limit,
        "maximum_absolute_amplitude": round(float(np.max(np.abs(waveform))), 8),
        "amplitude_limit": amplitude_limit,
        "all_components_below_guard": bool(float(np.max(frequencies)) <= guard_limit),
        "amplitude_within_limit": bool(float(np.max(np.abs(waveform))) <= amplitude_limit + 1e-12),
    }


def generate_environment(
    spec: ScenarioSpec,
    protocol: dict[str, Any],
) -> Environment:
    condition = dict(protocol["conditions"][spec.condition_index])
    if condition["name"] != spec.condition_name:
        raise ValueError("scenario condition index/name mismatch")
    rng = np.random.default_rng(spec.seed)
    size = int(protocol["grid"]["size"])
    start = (1, int(size // 2 + rng.integers(-3, 4)))
    goal = (size - 2, int(size // 2 + rng.integers(-3, 4)))
    obstacles = build_obstacles(size, start, goal, condition, rng)
    clearance = distance_transform_edt(~obstacles)

    yy, xx = np.mgrid[0:size, 0:size]
    xn = xx / max(1.0, float(size - 1))
    yn = yy / max(1.0, float(size - 1))
    phase_a, phase_b = rng.uniform(0.0, 2.0 * math.pi, size=2)
    wind_scale = float(condition["wind_scale"])
    turbulence_scale = float(condition["turbulence_scale"])
    wind_x = wind_scale * (
        0.24 * np.sin(2.0 * math.pi * yn + phase_a)
        + 0.14 * np.cos(2.0 * math.pi * xn + phase_b)
    )
    wind_y = wind_scale * (
        0.22 * np.cos(2.0 * math.pi * xn + phase_a)
        - 0.12 * np.sin(2.0 * math.pi * yn + phase_b)
    )
    turbulence = turbulence_scale * (
        0.22
        + 0.38 * np.square(np.sin(2.0 * math.pi * xn + phase_a))
        + 0.40 * np.square(np.cos(2.0 * math.pi * yn + phase_b))
    )

    if spec.condition_name == "crosswind_shear":
        wind_y += wind_scale * (0.55 + 0.55 * (xn - 0.5))
    elif spec.condition_name == "bounded_gust_front":
        front = np.exp(-np.square((xn - 0.52) / 0.12))
        wind_x -= 0.62 * wind_scale * front
        wind_y += 0.35 * wind_scale * front * np.sin(4.0 * math.pi * yn + phase_b)
        turbulence += 0.72 * turbulence_scale * front
    elif spec.condition_name == "thermal_cell_field":
        for _ in range(3):
            center_x, center_y = rng.uniform(0.2, 0.8, size=2)
            dx = xn - center_x
            dy = yn - center_y
            radius_sq = np.square(dx) + np.square(dy)
            cell = np.exp(-radius_sq / 0.025)
            wind_x += -dy * cell * wind_scale * 2.2
            wind_y += dx * cell * wind_scale * 2.2
            turbulence += cell * turbulence_scale * 0.8

    wind_true = np.stack((wind_x, wind_y), axis=-1)
    turbulence_true = np.clip(turbulence, 0.0, 1.5)
    noise_scale = float(condition["sensor_noise_scale"])
    wind_observed = wind_true + rng.normal(0.0, noise_scale, size=wind_true.shape)
    turbulence_observed = np.clip(
        turbulence_true + rng.normal(0.0, noise_scale * 0.5, size=turbulence_true.shape),
        0.0,
        1.5,
    )
    spectral_receipt: dict[str, Any] = {
        "applied": False,
        "all_components_below_guard": True,
        "amplitude_within_limit": True,
    }
    if bool(condition.get("broadband_transient")):
        transient, spectral_receipt = bounded_spectral_field(
            (size, size), protocol["spectral_stress"], rng
        )
        wind_observed[..., 0] += transient
        wind_observed[..., 1] -= transient * 0.65
        turbulence_observed = np.clip(turbulence_observed + np.abs(transient), 0.0, 1.5)
        spectral_receipt["applied"] = True

    direct_distance = math.dist(start, goal)
    energy_budget = direct_distance * float(condition["energy_budget_multiplier"])
    return Environment(
        condition=spec.condition_name,
        seed=spec.seed,
        size=size,
        start=start,
        goal=goal,
        obstacles=obstacles,
        clearance=clearance,
        wind_true=wind_true,
        wind_observed=wind_observed,
        turbulence_true=turbulence_true,
        turbulence_observed=turbulence_observed,
        energy_budget=energy_budget,
        direct_distance=direct_distance,
        spectral_receipt=spectral_receipt,
    )


def environment_digest(environment: Environment) -> str:
    digest = hashlib.sha256()
    for array in (
        environment.obstacles,
        environment.wind_true,
        environment.wind_observed,
        environment.turbulence_true,
        environment.turbulence_observed,
    ):
        digest.update(np.ascontiguousarray(array).tobytes())
    digest.update(
        json.dumps(
            {
                "condition": environment.condition,
                "seed": environment.seed,
                "start": environment.start,
                "goal": environment.goal,
                "energy_budget": environment.energy_budget,
            },
            sort_keys=True,
        ).encode("utf-8")
    )
    return digest.hexdigest()


def edge_components(
    environment: Environment,
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    observed: bool,
) -> tuple[float, float, float, float]:
    sx, sy = start
    ex, ey = end
    dx, dy = ex - sx, ey - sy
    distance = math.hypot(dx, dy)
    direction_x, direction_y = dx / distance, dy / distance
    wind_field = environment.wind_observed if observed else environment.wind_true
    turbulence_field = (
        environment.turbulence_observed if observed else environment.turbulence_true
    )
    wind = 0.5 * (wind_field[sy, sx] + wind_field[ey, ex])
    turbulence = float(0.5 * (turbulence_field[sy, sx] + turbulence_field[ey, ex]))
    along = float(wind[0] * direction_x + wind[1] * direction_y)
    headwind = max(0.0, -along)
    tailwind = max(0.0, along)
    crosswind = abs(float(wind[0] * direction_y - wind[1] * direction_x))
    energy_factor = max(
        0.62,
        1.0 + 0.52 * headwind + 0.18 * crosswind + 0.28 * turbulence - 0.12 * tailwind,
    )
    energy = distance * energy_factor
    clearance = float(min(environment.clearance[sy, sx], environment.clearance[ey, ex]))
    risk = distance * (0.42 * turbulence + 0.18 * crosswind + 0.32 / (clearance + 0.5))
    clearance_cost = distance / (clearance + 0.25)
    return distance, energy, risk, clearance_cost


def iter_neighbors(
    environment: Environment,
    point: tuple[int, int],
) -> list[tuple[int, int]]:
    x, y = point
    neighbors: list[tuple[int, int]] = []
    for dx, dy in MOVES:
        nx, ny = x + dx, y + dy
        if not (0 <= nx < environment.size and 0 <= ny < environment.size):
            continue
        if environment.obstacles[ny, nx]:
            continue
        if dx and dy and (
            environment.obstacles[y, nx] or environment.obstacles[ny, x]
        ):
            continue
        neighbors.append((nx, ny))
    return neighbors


def reconstruct_path(
    parents: dict[tuple[int, int], tuple[int, int]],
    goal: tuple[int, int],
) -> list[tuple[int, int]]:
    path = [goal]
    while path[-1] in parents:
        path.append(parents[path[-1]])
    path.reverse()
    return path


def plan_specialist(
    environment: Environment,
    specialist: dict[str, Any],
) -> tuple[list[tuple[int, int]], int]:
    weights = {key: float(value) for key, value in specialist["weights"].items()}
    use_heuristic = bool(specialist.get("heuristic"))
    start, goal = environment.start, environment.goal
    queue: list[tuple[float, float, int, tuple[int, int]]] = [(0.0, 0.0, 0, start)]
    best_cost = {start: 0.0}
    parents: dict[tuple[int, int], tuple[int, int]] = {}
    sequence = 0
    expansions = 0
    heuristic_floor = weights["distance"] + 0.62 * weights["energy"]
    while queue:
        _, current_cost, _, current = heapq.heappop(queue)
        if current_cost != best_cost.get(current):
            continue
        expansions += 1
        if current == goal:
            return reconstruct_path(parents, goal), expansions
        for neighbor in iter_neighbors(environment, current):
            distance, energy, risk, clearance_cost = edge_components(
                environment, current, neighbor, observed=True
            )
            edge_cost = (
                weights["distance"] * distance
                + weights["energy"] * energy
                + weights["risk"] * risk
                + weights["clearance"] * clearance_cost
            )
            proposed = current_cost + edge_cost
            if proposed + 1e-12 >= best_cost.get(neighbor, math.inf):
                continue
            best_cost[neighbor] = proposed
            parents[neighbor] = current
            sequence += 1
            heuristic = (
                math.dist(neighbor, goal) * heuristic_floor if use_heuristic else 0.0
            )
            heapq.heappush(queue, (proposed + heuristic, proposed, sequence, neighbor))
    return [], expansions


def path_metrics(
    environment: Environment,
    path: list[tuple[int, int]],
    protocol: dict[str, Any],
    *,
    observed: bool,
) -> dict[str, Any]:
    endpoint_reached = bool(path and path[0] == environment.start and path[-1] == environment.goal)
    collision = any(
        not (0 <= x < environment.size and 0 <= y < environment.size)
        or bool(environment.obstacles[y, x])
        for x, y in path
    )
    total_distance = 0.0
    total_energy = 0.0
    total_risk = 0.0
    min_clearance = math.inf
    for start, end in zip(path, path[1:]):
        distance, energy, risk, _ = edge_components(
            environment, start, end, observed=observed
        )
        total_distance += distance
        total_energy += energy
        total_risk += risk
        min_clearance = min(
            min_clearance,
            float(environment.clearance[start[1], start[0]]),
            float(environment.clearance[end[1], end[0]]),
        )
    if not path:
        min_clearance = 0.0

    turn_total = 0.0
    for first, second, third in zip(path, path[1:], path[2:]):
        vector_a = (second[0] - first[0], second[1] - first[1])
        vector_b = (third[0] - second[0], third[1] - second[1])
        norm_a = math.hypot(*vector_a)
        norm_b = math.hypot(*vector_b)
        cosine = clamp(
            (vector_a[0] * vector_b[0] + vector_a[1] * vector_b[1])
            / max(1e-12, norm_a * norm_b),
            -1.0,
            1.0,
        )
        turn_total += math.acos(cosine)

    reserve_fraction = (
        (environment.energy_budget - total_energy) / environment.energy_budget
        if environment.energy_budget > 0.0
        else -math.inf
    )
    minimum_reserve = float(protocol["hard_safety_constraints"]["minimum_actual_reserve_fraction"])
    reserve_breach = reserve_fraction < minimum_reserve
    constraint_violation = collision or not endpoint_reached or reserve_breach
    distance_score = clamp(environment.direct_distance / max(total_distance, 1e-12))
    energy_score = clamp(environment.direct_distance / max(total_energy, 1e-12))
    risk_score = clamp(math.exp(-total_risk / max(total_distance, 1e-12)))
    smoothness_score = clamp(
        math.exp(-turn_total / max(math.pi, math.pi * max(1, len(path) - 2)))
    )
    clearance_score = clamp(min_clearance / 4.0)
    reserve_score = clamp((reserve_fraction - minimum_reserve) / 0.45)
    component_scores = {
        "distance": distance_score,
        "energy": energy_score,
        "risk": risk_score,
        "smoothness": smoothness_score,
        "clearance": clearance_score,
        "reserve": reserve_score,
    }
    truth_weights = protocol["truth_score_weights"]
    score = sum(float(truth_weights[key]) * value for key, value in component_scores.items())
    if constraint_violation:
        score = 0.0
    return {
        "endpoint_reached": endpoint_reached,
        "collision": collision,
        "reserve_breach": reserve_breach,
        "constraint_violation": constraint_violation,
        "path_node_count": len(path),
        "path_length": total_distance,
        "energy_used": total_energy,
        "risk_exposure": total_risk,
        "minimum_obstacle_clearance": min_clearance,
        "turn_angle_total": turn_total,
        "reserve_fraction": reserve_fraction,
        "distance_score": distance_score,
        "energy_score": energy_score,
        "risk_score": risk_score,
        "smoothness_score": smoothness_score,
        "clearance_score": clearance_score,
        "reserve_score": reserve_score,
        "score": score,
    }


def hybrid_selection_value(metrics: dict[str, Any], candidate: dict[str, Any]) -> float:
    weights = candidate["selection_weights"]
    return sum(float(weights[name]) * float(metrics[f"{name}_score"]) for name in weights)


def select_hybrid_specialist(
    specialist_results: dict[str, dict[str, Any]],
    candidate: dict[str, Any],
) -> str:
    minimum_reserve = float(candidate["minimum_predicted_reserve_fraction"])
    eligible = [
        name
        for name, result in specialist_results.items()
        if result["observed_metrics"]["endpoint_reached"]
        and not result["observed_metrics"]["collision"]
        and float(result["observed_metrics"]["reserve_fraction"]) >= minimum_reserve
    ]
    pool = eligible or list(specialist_results)
    selected = max(
        sorted(pool),
        key=lambda name: hybrid_selection_value(
            specialist_results[name]["observed_metrics"], candidate
        ),
    )
    guard_name = candidate.get("guard_against_specialist")
    if not guard_name:
        return selected
    guard_name = str(guard_name)
    if guard_name not in specialist_results:
        raise ValueError(f"unknown hybrid guard specialist: {guard_name}")
    if selected == guard_name:
        return selected

    selected_metrics = specialist_results[selected]["observed_metrics"]
    guard_metrics = specialist_results[guard_name]["observed_metrics"]
    selected_value = hybrid_selection_value(selected_metrics, candidate)
    guard_value = hybrid_selection_value(guard_metrics, candidate)
    minimum_gain = float(candidate.get("minimum_selection_gain") or 0.0)
    max_energy_regression = float(
        candidate.get("maximum_predicted_energy_regression_fraction") or 0.0
    )
    max_risk_regression = float(
        candidate.get("maximum_predicted_risk_regression_fraction") or 0.0
    )
    reserve_tolerance = float(candidate.get("predicted_reserve_regression_tolerance") or 0.0)
    guard_checks = (
        selected_value - guard_value >= minimum_gain,
        float(selected_metrics["energy_used"])
        <= float(guard_metrics["energy_used"]) * (1.0 + max_energy_regression),
        float(selected_metrics["risk_exposure"])
        <= float(guard_metrics["risk_exposure"]) * (1.0 + max_risk_regression),
        float(selected_metrics["reserve_fraction"])
        >= float(guard_metrics["reserve_fraction"]) - reserve_tolerance,
    )
    return selected if all(guard_checks) else guard_name


def rounded_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: round(value, 8) if isinstance(value, float) and math.isfinite(value) else value
        for key, value in row.items()
    }


def evaluate_scenario(
    spec: ScenarioSpec,
    protocol: dict[str, Any],
) -> list[dict[str, Any]]:
    environment = generate_environment(spec, protocol)
    environment_sha256 = environment_digest(environment)
    specialist_results: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for specialist in protocol["specialists"]:
        path, expansions = plan_specialist(environment, specialist)
        observed_metrics = path_metrics(environment, path, protocol, observed=True)
        truth_metrics = path_metrics(environment, path, protocol, observed=False)
        specialist_results[str(specialist["name"])] = {
            "path": path,
            "expansions": expansions,
            "observed_metrics": observed_metrics,
            "truth_metrics": truth_metrics,
        }
        rows.append(
            rounded_row(
                {
                    "split": spec.split,
                    "condition": spec.condition_name,
                    "seed": spec.seed,
                    "environment_sha256": environment_sha256,
                    "strategy": specialist["name"],
                    "kind": "baseline",
                    "family_id": specialist["name"],
                    "selected_specialist": specialist["name"],
                    "planner_expansions": expansions,
                    "predicted_reserve_fraction": observed_metrics["reserve_fraction"],
                    **truth_metrics,
                    "spectral_guard_pass": bool(
                        environment.spectral_receipt["all_components_below_guard"]
                        and environment.spectral_receipt["amplitude_within_limit"]
                    ),
                }
            )
        )

    total_expansions = sum(int(result["expansions"]) for result in specialist_results.values())
    for candidate in protocol["hybrid_candidates"]:
        selected = select_hybrid_specialist(specialist_results, candidate)
        selected_result = specialist_results[selected]
        truth_metrics = dict(selected_result["truth_metrics"])
        observed_metrics = selected_result["observed_metrics"]
        rows.append(
            rounded_row(
                {
                    "split": spec.split,
                    "condition": spec.condition_name,
                    "seed": spec.seed,
                    "environment_sha256": environment_sha256,
                    "strategy": candidate["name"],
                    "kind": "hybrid_candidate",
                    "family_id": candidate["family_id"],
                    "selected_specialist": selected,
                    "planner_expansions": total_expansions,
                    "predicted_reserve_fraction": observed_metrics["reserve_fraction"],
                    **truth_metrics,
                    "spectral_guard_pass": bool(
                        environment.spectral_receipt["all_components_below_guard"]
                        and environment.spectral_receipt["amplitude_within_limit"]
                    ),
                }
            )
        )
    return rows


def build_scenarios(
    protocol: dict[str, Any],
    split: str,
    scenarios_per_condition: int | None = None,
) -> list[ScenarioSpec]:
    split_spec = protocol["splits"][split]
    count = int(scenarios_per_condition or split_spec["scenarios_per_condition"])
    seed_base = int(split_spec["seed_base"])
    return [
        ScenarioSpec(
            split=split,
            condition_index=condition_index,
            condition_name=str(condition["name"]),
            seed=seed_base + condition_index * 100000 + index,
        )
        for condition_index, condition in enumerate(protocol["conditions"])
        for index in range(count)
    ]


def scenario_key(spec: ScenarioSpec) -> tuple[str, str, int]:
    return spec.split, spec.condition_name, spec.seed


def row_scenario_key(row: dict[str, Any]) -> tuple[str, str, int]:
    return str(row["split"]), str(row["condition"]), int(row["seed"])


def canonical_json_line(row: dict[str, Any]) -> str:
    return json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"


def load_complete_checkpoint(
    checkpoint_path: Path,
    scenarios: list[ScenarioSpec],
    strategy_names: list[str],
) -> tuple[dict[tuple[str, str, int], list[dict[str, Any]]], int]:
    expected_keys = {scenario_key(spec) for spec in scenarios}
    expected_strategies = set(strategy_names)
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    discarded = 0
    if checkpoint_path.exists():
        for line_number, line in enumerate(
            checkpoint_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid checkpoint JSON at {checkpoint_path}:{line_number}"
                ) from exc
            if not isinstance(row, dict):
                discarded += 1
                continue
            try:
                key = row_scenario_key(row)
            except (KeyError, TypeError, ValueError):
                discarded += 1
                continue
            strategy = str(row.get("strategy") or "")
            if key not in expected_keys or strategy not in expected_strategies:
                discarded += 1
                continue
            grouped[key][strategy] = row
    complete: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for key, rows in grouped.items():
        if set(rows) == expected_strategies:
            complete[key] = [rows[name] for name in strategy_names]
        else:
            discarded += len(rows)
    return complete, discarded


def evaluate_task(task: tuple[ScenarioSpec, dict[str, Any]]) -> list[dict[str, Any]]:
    return evaluate_scenario(task[0], task[1])


def run_rows_resumable(
    scenarios: list[ScenarioSpec],
    protocol: dict[str, Any],
    checkpoint_path: Path,
    *,
    workers: int,
    resume: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    started = time.perf_counter()
    strategy_names = [
        str(row["name"])
        for row in protocol["specialists"] + protocol["hybrid_candidates"]
    ]
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    complete, discarded = (
        load_complete_checkpoint(checkpoint_path, scenarios, strategy_names)
        if resume
        else ({}, 0)
    )
    ordered_keys = [scenario_key(spec) for spec in scenarios]
    missing = [spec for spec in scenarios if scenario_key(spec) not in complete]
    with checkpoint_path.open("w", encoding="utf-8", newline="\n") as handle:
        for key in ordered_keys:
            for row in complete.get(key, []):
                handle.write(canonical_json_line(row))

    if missing:
        tasks = [(spec, protocol) for spec in missing]
        executor: ProcessPoolExecutor | None = None
        if workers <= 1:
            iterator = map(evaluate_task, tasks)
        else:
            executor = ProcessPoolExecutor(max_workers=workers)
            iterator = executor.map(evaluate_task, tasks, chunksize=1)
        try:
            with checkpoint_path.open("a", encoding="utf-8", newline="\n") as handle:
                for spec, scenario_rows in zip(missing, iterator):
                    complete[scenario_key(spec)] = scenario_rows
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
        "discarded_checkpoint_row_count": discarded,
        "checkpoint_path": str(checkpoint_path),
        "checkpoint_sha256": sha256_file(checkpoint_path),
        "workers": workers,
        "wall_seconds": round(time.perf_counter() - started, 6),
    }


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["strategy"])].append(row)
    aggregate: list[dict[str, Any]] = []
    for strategy, items in grouped.items():
        selected_counts: dict[str, int] = defaultdict(int)
        for item in items:
            selected_counts[str(item["selected_specialist"])] += 1
        aggregate.append(
            {
                "strategy": strategy,
                "kind": items[0]["kind"],
                "family_id": items[0]["family_id"],
                "scenario_count": len(items),
                "mean_score": round(mean(float(row["score"]) for row in items), 8),
                "median_score": round(median(float(row["score"]) for row in items), 8),
                "mission_success_rate": round(
                    mean(not bool(row["constraint_violation"]) for row in items), 8
                ),
                "collision_rate": round(mean(bool(row["collision"]) for row in items), 8),
                "endpoint_failure_rate": round(
                    mean(not bool(row["endpoint_reached"]) for row in items), 8
                ),
                "reserve_breach_rate": round(
                    mean(bool(row["reserve_breach"]) for row in items), 8
                ),
                "mean_path_length": round(mean(float(row["path_length"]) for row in items), 8),
                "mean_energy_used": round(mean(float(row["energy_used"]) for row in items), 8),
                "mean_risk_exposure": round(
                    mean(float(row["risk_exposure"]) for row in items), 8
                ),
                "mean_reserve_fraction": round(
                    mean(float(row["reserve_fraction"]) for row in items), 8
                ),
                "mean_planner_expansions": round(
                    mean(float(row["planner_expansions"]) for row in items), 8
                ),
                "spectral_guard_pass_rate": round(
                    mean(bool(row["spectral_guard_pass"]) for row in items), 8
                ),
                "selected_specialist_counts": dict(sorted(selected_counts.items())),
            }
        )
    aggregate.sort(
        key=lambda row: (
            float(row["mission_success_rate"]),
            float(row["mean_score"]),
            -float(row["mean_planner_expansions"]),
        ),
        reverse=True,
    )
    for rank, row in enumerate(aggregate, start=1):
        row["rank"] = rank
    return aggregate


def paired_mean_ci95(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        raise ValueError("paired interval requires at least one delta")
    observed = mean(deltas)
    standard_error = stdev(deltas) / math.sqrt(len(deltas)) if len(deltas) > 1 else 0.0
    half_width = 1.959963984540054 * standard_error
    return {
        "method": "paired_normal_approximation",
        "paired_scenario_count": len(deltas),
        "observed_mean_delta": round(observed, 8),
        "standard_error": round(standard_error, 10),
        "ci95": [round(observed - half_width, 8), round(observed + half_width, 8)],
    }


def first_ranked_kind(leaderboard: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    for row in leaderboard:
        if row["kind"] == kind:
            return row
    raise ValueError(f"leaderboard contains no {kind}")


def build_promotion_gate(
    development_leaderboard: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    validation_leaderboard: list[dict[str, Any]],
    protocol: dict[str, Any],
    *,
    protocol_conformant: bool,
) -> dict[str, Any]:
    confirmatory = protocol["confirmatory_gate"]
    preselected_candidate = confirmatory.get("preselected_candidate")
    preselected_baseline = confirmatory.get("preselected_baseline")
    if preselected_candidate:
        development_by_strategy = {
            str(row["strategy"]): row for row in development_leaderboard
        }
        selected_candidate = development_by_strategy[str(preselected_candidate)]
        selected_baseline = development_by_strategy[str(preselected_baseline)]
        selection_source = str(
            confirmatory.get("pair_selection_source") or "prior_frozen_run"
        )
    else:
        selected_candidate = first_ranked_kind(development_leaderboard, "hybrid_candidate")
        selected_baseline = first_ranked_kind(development_leaderboard, "baseline")
        selection_source = "development_only"
    candidate_name = str(selected_candidate["strategy"])
    baseline_name = str(selected_baseline["strategy"])
    validation_by_strategy = {str(row["strategy"]): row for row in validation_leaderboard}
    candidate_aggregate = validation_by_strategy[candidate_name]
    baseline_aggregate = validation_by_strategy[baseline_name]

    paired: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in validation_rows:
        strategy = str(row["strategy"])
        if strategy in {candidate_name, baseline_name}:
            paired[(str(row["condition"]), int(row["seed"]))][strategy] = row
    complete = [
        (key, values[candidate_name], values[baseline_name])
        for key, values in sorted(paired.items())
        if candidate_name in values and baseline_name in values
    ]
    if not complete:
        raise ValueError("selected confirmatory pair has no complete validation scenarios")
    score_deltas = [float(candidate["score"]) - float(baseline["score"]) for _, candidate, baseline in complete]
    interval = paired_mean_ci95(score_deltas)
    by_condition: dict[str, list[float]] = defaultdict(list)
    for (condition, _), candidate, baseline in complete:
        by_condition[condition].append(float(candidate["score"]) - float(baseline["score"]))
    margin = float(protocol["confirmatory_gate"]["condition_score_noninferiority_margin"])
    condition_guardrails = [
        {
            "condition": condition,
            "paired_scenario_count": len(deltas),
            "score_delta": round(mean(deltas), 8),
            "noninferiority_margin": margin,
            "passes_noninferiority": mean(deltas) >= -margin,
        }
        for condition, deltas in sorted(by_condition.items())
    ]

    candidate_energy = float(candidate_aggregate["mean_energy_used"])
    baseline_energy = float(baseline_aggregate["mean_energy_used"])
    candidate_risk = float(candidate_aggregate["mean_risk_exposure"])
    baseline_risk = float(baseline_aggregate["mean_risk_exposure"])
    energy_regression_fraction = (candidate_energy - baseline_energy) / max(1e-12, baseline_energy)
    risk_regression_fraction = (candidate_risk - baseline_risk) / max(1e-12, baseline_risk)
    expansion_multiplier = float(candidate_aggregate["mean_planner_expansions"]) / max(
        1e-12, float(baseline_aggregate["mean_planner_expansions"])
    )
    hard = protocol["hard_safety_constraints"]
    spectral_valid = all(bool(row["spectral_guard_pass"]) for row in validation_rows)
    checks = {
        "protocol_conformant": protocol_conformant,
        "overall_score_delta_positive": float(interval["observed_mean_delta"]) > 0.0,
        "paired_ci95_lower_bound_positive": float(interval["ci95"][0]) > 0.0,
        "all_condition_score_noninferiority": all(
            row["passes_noninferiority"] for row in condition_guardrails
        ),
        "candidate_collision_rate_within_limit": float(candidate_aggregate["collision_rate"])
        <= float(hard["maximum_collision_rate"]),
        "candidate_endpoint_failure_rate_within_limit": float(
            candidate_aggregate["endpoint_failure_rate"]
        )
        <= float(hard["maximum_endpoint_failure_rate"]),
        "candidate_reserve_breach_rate_within_limit": float(
            candidate_aggregate["reserve_breach_rate"]
        )
        <= float(hard["maximum_candidate_reserve_breach_rate"]),
        "candidate_reserve_breach_not_worse_than_baseline": float(
            candidate_aggregate["reserve_breach_rate"]
        )
        <= float(baseline_aggregate["reserve_breach_rate"]),
        "mean_energy_noninferiority": energy_regression_fraction
        <= float(confirmatory["mean_energy_regression_margin_fraction"]),
        "mean_risk_noninferiority": risk_regression_fraction
        <= float(confirmatory["mean_risk_regression_margin_fraction"]),
        "bounded_compute_expansions": expansion_multiplier
        <= float(confirmatory["maximum_expansion_multiplier_vs_selected_baseline"]),
        "spectral_guard_valid": spectral_valid,
        "actuator_outputs_disabled": protocol.get("actuator_commands_allowed") is False,
    }
    promoted = all(checks.values())
    return {
        "gate": (
            "INTERNAL_GENERATED_ASSURANCE_PASS_NOT_AIRWORTHINESS"
            if promoted
            else "NOT_PROMOTED_ASSURANCE_GATE_FAILED"
        ),
        "promoted": promoted,
        "selection": {
            "source": selection_source,
            "selected_candidate": candidate_name,
            "selected_baseline": baseline_name,
            "validation_pair_locked_before_scoring": True,
            "holdout_used_for_selection": False,
            "preselected_before_current_validation": bool(preselected_candidate),
        },
        "candidate_validation_aggregate": candidate_aggregate,
        "baseline_validation_aggregate": baseline_aggregate,
        "paired_score_interval": interval,
        "condition_guardrails": condition_guardrails,
        "energy_regression_fraction": round(energy_regression_fraction, 8),
        "risk_regression_fraction": round(risk_regression_fraction, 8),
        "planner_expansion_multiplier": round(expansion_multiplier, 8),
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "claim_language": EVIDENCE_BOUNDARY,
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def render_scorecard(summary: dict[str, Any]) -> str:
    gate = summary["promotion_gate"]
    lines = [
        "# LumaJet Flight Energy and Safety-Assurance Benchmark",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        f"Evidence receipt SHA-256: `{summary['evidence_receipt_sha256']}`",
        "",
        "## Evidence Boundary",
        "",
        summary["evidence_boundary"],
        "",
        "## Confirmatory Decision",
        "",
        f"- Gate: `{gate['gate']}`",
        f"- Development-selected candidate: `{gate['selection']['selected_candidate']}`",
        f"- Development-selected baseline: `{gate['selection']['selected_baseline']}`",
        f"- Validation scenarios: `{summary['validation']['scenario_count']}`",
        f"- Score delta: `{gate['paired_score_interval']['observed_mean_delta']}`",
        f"- Paired CI95: `{gate['paired_score_interval']['ci95']}`",
        f"- Energy regression fraction: `{gate['energy_regression_fraction']}`",
        f"- Risk regression fraction: `{gate['risk_regression_fraction']}`",
        f"- Planner expansion multiplier: `{gate['planner_expansion_multiplier']}`",
        f"- Failed checks: `{', '.join(gate['failed_checks']) or 'none'}`",
        "",
        "## Condition Guardrails",
        "",
        "| Condition | Pairs | Score Delta | Margin | Pass |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for row in gate["condition_guardrails"]:
        lines.append(
            f"| `{row['condition']}` | {row['paired_scenario_count']} | "
            f"{row['score_delta']} | {row['noninferiority_margin']} | "
            f"{str(row['passes_noninferiority']).lower()} |"
        )
    lines.extend(
        [
            "",
            "## Validation Leaderboard",
            "",
            "| Rank | Strategy | Kind | Score | Success | Energy | Risk | Reserve Breach | Expansions |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in summary["validation"]["leaderboard"]:
        lines.append(
            f"| {row['rank']} | `{row['strategy']}` | `{row['kind']}` | "
            f"{row['mean_score']} | {row['mission_success_rate']} | {row['mean_energy_used']} | "
            f"{row['mean_risk_exposure']} | {row['reserve_breach_rate']} | "
            f"{row['mean_planner_expansions']} |"
        )
    lines.extend(
        [
            "",
            "## Assurance Boundary",
            "",
            "The FAA and NASA references in the protocol are process-orientation references. "
            "This artifact does not claim compliance with DO-178C, certification, airworthiness, "
            "flight safety, or external validation.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_or_validate_plan(
    out_dir: Path,
    protocol_path: Path,
    protocol: dict[str, Any],
    *,
    development_scenarios: int,
    validation_scenarios: int,
) -> tuple[Path, dict[str, Any], bool]:
    configured_development = int(protocol["splits"]["development"]["scenarios_per_condition"])
    configured_validation = int(protocol["splits"]["validation"]["scenarios_per_condition"])
    protocol_conformant = (
        development_scenarios == configured_development
        and validation_scenarios == configured_validation
    )
    plan: dict[str, Any] = {
        "schema": "lumajet_flight_assurance_execution_plan_v1",
        "protocol_path": str(protocol_path),
        "protocol_sha256": sha256_file(protocol_path),
        "source_path": str(Path(__file__).resolve()),
        "source_sha256": sha256_file(Path(__file__).resolve()),
        "development_scenarios_per_condition": development_scenarios,
        "validation_scenarios_per_condition": validation_scenarios,
        "condition_names": [row["name"] for row in protocol["conditions"]],
        "strategy_names": [
            row["name"] for row in protocol["specialists"] + protocol["hybrid_candidates"]
        ],
        "protocol_conformant": protocol_conformant,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    plan["plan_sha256"] = sha256_payload(plan)
    plan_path = out_dir / "execution_plan.json"
    if plan_path.exists():
        existing = load_json(plan_path)
        if existing != plan:
            raise ValueError(
                "execution plan mismatch; use a new run tag instead of mixing code, protocol, "
                "counts, or strategies in one checkpoint"
            )
    else:
        plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return plan_path, plan, protocol_conformant


def run_suite(
    protocol_path: Path,
    out_dir: Path,
    *,
    workers: int,
    resume: bool,
    development_scenarios: int | None = None,
    validation_scenarios: int | None = None,
) -> dict[str, Any]:
    protocol = load_json(protocol_path)
    protocol_validation = validate_protocol(protocol)
    development_count = int(
        development_scenarios
        or protocol["splits"]["development"]["scenarios_per_condition"]
    )
    validation_count = int(
        validation_scenarios
        or protocol["splits"]["validation"]["scenarios_per_condition"]
    )
    if workers < 1 or development_count < 1 or validation_count < 1:
        raise ValueError("workers and scenario counts must be positive")
    out_dir.mkdir(parents=True, exist_ok=True)
    protocol_snapshot = out_dir / "protocol_snapshot.json"
    source_snapshot = out_dir / "benchmark_source_snapshot.py"
    if protocol_snapshot.exists() and sha256_file(protocol_snapshot) != sha256_file(protocol_path):
        raise ValueError("protocol snapshot mismatch; use a new run tag")
    if source_snapshot.exists() and sha256_file(source_snapshot) != sha256_file(Path(__file__).resolve()):
        raise ValueError("source snapshot mismatch; use a new run tag")
    shutil.copyfile(protocol_path, protocol_snapshot)
    shutil.copyfile(Path(__file__).resolve(), source_snapshot)
    plan_path, execution_plan, protocol_conformant = write_or_validate_plan(
        out_dir,
        protocol_path,
        protocol,
        development_scenarios=development_count,
        validation_scenarios=validation_count,
    )

    development_specs = build_scenarios(protocol, "development", development_count)
    validation_specs = build_scenarios(protocol, "validation", validation_count)
    development_checkpoint = out_dir / "development_checkpoint.jsonl"
    validation_checkpoint = out_dir / "validation_checkpoint.jsonl"
    development_rows, development_execution = run_rows_resumable(
        development_specs,
        protocol,
        development_checkpoint,
        workers=workers,
        resume=resume,
    )
    validation_rows, validation_execution = run_rows_resumable(
        validation_specs,
        protocol,
        validation_checkpoint,
        workers=workers,
        resume=resume,
    )
    development_leaderboard = aggregate_rows(development_rows)
    validation_leaderboard = aggregate_rows(validation_rows)
    promotion_gate = build_promotion_gate(
        development_leaderboard,
        validation_rows,
        validation_leaderboard,
        protocol,
        protocol_conformant=protocol_conformant,
    )
    traceability = [
        {
            "requirement_id": "LJ-SA-001",
            "requirement": "No actuator or operational command output",
            "evidence": "protocol_snapshot.json and claim gate",
            "status": "PASS" if protocol.get("actuator_commands_allowed") is False else "FAIL",
        },
        {
            "requirement_id": "LJ-SA-002",
            "requirement": "Development-only pair selection with untouched validation seeds",
            "evidence": "execution_plan.json and promotion_gate.selection",
            "status": "PASS" if protocol_conformant else "FAIL",
        },
        {
            "requirement_id": "LJ-SA-003",
            "requirement": "Collision, endpoint, and reserve constraints are hard promotion vetoes",
            "evidence": "promotion_gate.checks",
            "status": "PASS",
        },
        {
            "requirement_id": "LJ-SA-004",
            "requirement": "Broadband transient remains bounded below the Nyquist guard",
            "evidence": "protocol_validation and spectral_guard_pass rows",
            "status": "PASS" if protocol_validation["all_components_below_guard"] else "FAIL",
        },
        {
            "requirement_id": "LJ-SA-005",
            "requirement": "Null and adverse results remain in checkpoints and scorecard",
            "evidence": "development_checkpoint.jsonl and validation_checkpoint.jsonl",
            "status": "PASS",
        },
    ]
    summary: dict[str, Any] = {
        "schema": "lumajet_flight_assurance_benchmark_v1",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "protocol": {
            "path": str(protocol_path),
            "snapshot_path": str(protocol_snapshot),
            "sha256": sha256_file(protocol_path),
            "validation": protocol_validation,
            "conformant_execution": protocol_conformant,
        },
        "execution": {
            "plan_sha256": execution_plan["plan_sha256"],
            "workers": workers,
            "resume_enabled": resume,
            "development": development_execution,
            "validation": validation_execution,
        },
        "development": {
            "scenario_count": len(development_specs),
            "scenarios_per_condition": development_count,
            "leaderboard": development_leaderboard,
        },
        "validation": {
            "scenario_count": len(validation_specs),
            "scenarios_per_condition": validation_count,
            "leaderboard": validation_leaderboard,
        },
        "promotion_gate": promotion_gate,
        "requirements_traceability": traceability,
        "claim_gate": {
            "generated_simulation_evidence": True,
            "internal_lumengrade": "LG2" if protocol_conformant else "LG1",
            "field_validation": False,
            "external_reproduction": False,
            "airworthiness": False,
            "faa_or_dod_approval": False,
            "operational_use_authorized": False,
            "economic_claim_allowed": False,
        },
    }
    summary["evidence_receipt_sha256"] = sha256_payload(summary)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(render_scorecard(summary), encoding="utf-8")
    scenario_path = out_dir / "scenario_summary.csv"
    leaderboard_path = out_dir / "leaderboard.csv"
    write_csv(
        scenario_path,
        validation_rows,
        [
            "split",
            "condition",
            "seed",
            "environment_sha256",
            "strategy",
            "kind",
            "family_id",
            "selected_specialist",
            "planner_expansions",
            "predicted_reserve_fraction",
            "endpoint_reached",
            "collision",
            "reserve_breach",
            "constraint_violation",
            "path_node_count",
            "path_length",
            "energy_used",
            "risk_exposure",
            "minimum_obstacle_clearance",
            "turn_angle_total",
            "reserve_fraction",
            "distance_score",
            "energy_score",
            "risk_score",
            "smoothness_score",
            "clearance_score",
            "reserve_score",
            "score",
            "spectral_guard_pass",
        ],
    )
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
            "mission_success_rate",
            "collision_rate",
            "endpoint_failure_rate",
            "reserve_breach_rate",
            "mean_path_length",
            "mean_energy_used",
            "mean_risk_exposure",
            "mean_reserve_fraction",
            "mean_planner_expansions",
            "spectral_guard_pass_rate",
            "selected_specialist_counts",
        ],
    )
    manifest = {
        "schema": "lumajet_flight_assurance_manifest_v1",
        "generated_utc": summary["generated_utc"],
        "evidence_receipt_sha256": summary["evidence_receipt_sha256"],
        "files": {},
    }
    for path in (
        protocol_snapshot,
        source_snapshot,
        plan_path,
        development_checkpoint,
        validation_checkpoint,
        summary_path,
        scorecard_path,
        scenario_path,
        leaderboard_path,
    ):
        manifest["files"][path.name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    manifest_path = out_dir / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, default=DEFAULT_PROTOCOL)
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--development-scenarios", type=int)
    parser.add_argument("--validation-scenarios", type=int)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(10, (os.cpu_count() or 2) - 1)),
    )
    parser.add_argument("--no-resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or now_tag()
    out_dir = args.out_root / run_tag
    summary = run_suite(
        args.protocol,
        out_dir,
        workers=args.workers,
        resume=not args.no_resume,
        development_scenarios=args.development_scenarios,
        validation_scenarios=args.validation_scenarios,
    )
    latest_path = args.out_root / "latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps({"run_dir": str(out_dir), **summary}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run_dir": str(out_dir),
                "validation_scenarios": summary["validation"]["scenario_count"],
                "gate": summary["promotion_gate"]["gate"],
                "selected_candidate": summary["promotion_gate"]["selection"]["selected_candidate"],
                "selected_baseline": summary["promotion_gate"]["selection"]["selected_baseline"],
                "score_delta": summary["promotion_gate"]["paired_score_interval"]["observed_mean_delta"],
                "failed_checks": summary["promotion_gate"]["failed_checks"],
                "evidence_receipt_sha256": summary["evidence_receipt_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
