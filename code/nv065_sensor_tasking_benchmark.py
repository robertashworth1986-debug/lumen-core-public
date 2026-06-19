"""Synthetic adaptive sensor-management benchmark for Navy NV065.

The benchmark uses generated tracks and sensor-resource models to test a
narrow software hypothesis: can a marginal-contribution tasking policy release
low-value sensor updates from well-characterized tracks and reallocate them to
tracks with higher expected fire-control-quality benefit?

It is not SSDS, radar, fire-control, classified, operational, or field
evidence.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "nv065_sensor_tasking"
FCQ_THRESHOLD = 1.0
EVIDENCE_BOUNDARY = (
    "Generated software benchmark only. Tracks, sensors, covariance, hostility "
    "changes, sensor feedback, and tasking costs are synthetic. Results do not "
    "establish SSDS integration, fire-control performance, sensor physics, "
    "classified-environment performance, cybersecurity, adversarial robustness, "
    "or field readiness."
)


@dataclass(frozen=True)
class Sensor:
    name: str
    capacity: int
    precision: float
    scan_cost: float
    suitability: dict[str, float]


@dataclass(frozen=True)
class TrackSpec:
    track_id: str
    arrival: int
    target_type: str
    initial_hostility: int
    maneuver: float
    clutter: float
    initial_covariance: float
    hostility_shift: int | None = None
    shifted_hostility: int = 3


@dataclass
class TrackState:
    spec: TrackSpec
    hostility: int
    covariance: float
    last_fcq_time: int | None = None
    first_fcq_after_shift: int | None = None


@dataclass(frozen=True)
class Condition:
    name: str
    initial_tracks: int
    arrival_rate: float
    shift_probability: float
    clutter_multiplier: float = 1.0
    maneuver_multiplier: float = 1.0
    capacity_factor: float = 1.0
    sensor_quality: dict[str, float] | None = None


@dataclass(frozen=True)
class PolicyParams:
    name: str
    release_threshold: float
    critical_boost: float
    stale_boost: float
    release_penalty: float
    degradation_weight: float


SENSORS = (
    Sensor(
        "SPS-48",
        capacity=8,
        precision=0.16,
        scan_cost=1.0,
        suitability={"air": 1.0, "missile": 0.72, "surface": 0.34},
    ),
    Sensor(
        "SPQ-9B",
        capacity=7,
        precision=0.18,
        scan_cost=1.0,
        suitability={"surface": 1.0, "missile": 0.70, "air": 0.56},
    ),
    Sensor(
        "MK-9",
        capacity=3,
        precision=0.36,
        scan_cost=1.8,
        suitability={"missile": 1.0, "air": 0.70, "surface": 0.45},
    ),
    Sensor(
        "SPY-6(V)3",
        capacity=9,
        precision=0.24,
        scan_cost=1.4,
        suitability={"air": 1.0, "missile": 0.95, "surface": 0.72},
    ),
)

CONDITIONS = (
    Condition("nominal", initial_tracks=24, arrival_rate=0.14, shift_probability=0.010),
    Condition(
        "dense_raid",
        initial_tracks=58,
        arrival_rate=0.42,
        shift_probability=0.020,
        clutter_multiplier=1.22,
        capacity_factor=0.82,
    ),
    Condition(
        "sensor_degradation",
        initial_tracks=32,
        arrival_rate=0.20,
        shift_probability=0.016,
        sensor_quality={"SPY-6(V)3": 0.56, "SPQ-9B": 0.78},
    ),
    Condition(
        "hostility_shift",
        initial_tracks=34,
        arrival_rate=0.22,
        shift_probability=0.045,
        maneuver_multiplier=1.25,
    ),
    Condition(
        "combined_stress",
        initial_tracks=64,
        arrival_rate=0.48,
        shift_probability=0.042,
        clutter_multiplier=1.35,
        maneuver_multiplier=1.32,
        capacity_factor=0.74,
        sensor_quality={"SPY-6(V)3": 0.62, "SPQ-9B": 0.74, "SPS-48": 0.82},
    ),
)

POLICY_CANDIDATES = (
    PolicyParams("balanced_release", 0.030, 1.15, 0.50, 0.65, 1.0),
    PolicyParams("critical_release", 0.040, 1.70, 0.35, 0.80, 1.0),
    PolicyParams("fast_shift_release", 0.026, 1.45, 0.90, 0.55, 1.0),
    PolicyParams("conservative_release", 0.055, 1.20, 0.25, 1.10, 1.0),
)


def sensor_quality(condition: Condition, sensor: Sensor) -> float:
    if not condition.sensor_quality:
        return 1.0
    return float(condition.sensor_quality.get(sensor.name, 1.0))


def generate_tracks(
    *,
    seed: int,
    condition: Condition,
    horizon: int,
) -> list[TrackSpec]:
    rng = np.random.default_rng(seed)
    specs: list[TrackSpec] = []

    def add_track(arrival: int, index: int) -> None:
        target_type = str(rng.choice(["air", "surface", "missile"], p=[0.48, 0.34, 0.18]))
        initial_hostility = int(rng.choice([0, 1, 2], p=[0.46, 0.38, 0.16]))
        maneuver_base = {
            "surface": 0.65,
            "air": 0.95,
            "missile": 1.35,
        }[target_type]
        maneuver = float(
            maneuver_base
            * condition.maneuver_multiplier
            * rng.uniform(0.75, 1.35)
        )
        clutter = float(condition.clutter_multiplier * rng.uniform(0.75, 1.45))
        initial_covariance = float(rng.uniform(1.6, 4.8) * (1.0 + 0.20 * maneuver))
        shift: int | None = None
        if rng.random() < condition.shift_probability * max(8, horizon - arrival):
            shift = int(rng.integers(arrival + 8, max(arrival + 9, horizon)))
        specs.append(
            TrackSpec(
                track_id=f"T{index:05d}",
                arrival=arrival,
                target_type=target_type,
                initial_hostility=initial_hostility,
                maneuver=maneuver,
                clutter=clutter,
                initial_covariance=initial_covariance,
                hostility_shift=shift,
            )
        )

    for idx in range(condition.initial_tracks):
        add_track(0, idx)
    next_idx = condition.initial_tracks
    for timestamp in range(1, horizon):
        for _ in range(int(rng.poisson(condition.arrival_rate))):
            add_track(timestamp, next_idx)
            next_idx += 1
    return specs


def _process_growth(state: TrackState) -> float:
    hostility_growth = 1.0 + 0.12 * max(0, state.hostility - 1)
    return 0.035 * state.spec.maneuver * state.spec.clutter * hostility_growth


def _target_weight(state: TrackState) -> float:
    return 1.0 + 0.70 * state.hostility + (0.35 if state.spec.target_type == "missile" else 0.0)


def expected_contribution(
    *,
    sensor: Sensor,
    state: TrackState,
    condition: Condition,
    policy: str,
    params: PolicyParams | None,
    timestamp: int,
    predicted_covariance: float | None = None,
) -> float:
    cov = float(state.covariance if predicted_covariance is None else predicted_covariance)
    suitability = sensor.suitability.get(state.spec.target_type, 0.0)
    quality = sensor_quality(condition, sensor)
    base = sensor.precision * suitability * quality
    covariance_need = min(2.4, max(0.10, cov / FCQ_THRESHOLD))
    marginal = base * covariance_need / (1.0 + 0.38 * max(0.0, FCQ_THRESHOLD - cov))
    if policy == "adaptive_sensor_manager" and params is not None:
        recently_shifted = (
            state.spec.hostility_shift is not None
            and 0 <= timestamp - state.spec.hostility_shift <= 8
        )
        critical = max(0, state.hostility - 1)
        stale = 0.0
        if state.last_fcq_time is None:
            stale = 1.0
        elif timestamp - state.last_fcq_time > 6:
            stale = min(1.0, (timestamp - state.last_fcq_time) / 18.0)
        marginal *= 1.0 + params.critical_boost * critical + params.stale_boost * stale
        if recently_shifted:
            marginal *= 1.45
        if quality < 1.0:
            marginal *= quality ** params.degradation_weight
        recently_confirmed = (
            state.last_fcq_time is not None
            and timestamp - state.last_fcq_time <= 4
        )
        if cov <= FCQ_THRESHOLD * 0.75 and recently_confirmed:
            marginal *= 0.22
        if cov <= FCQ_THRESHOLD and marginal < params.release_threshold * (1.0 + critical):
            marginal *= 1.0 - params.release_penalty
    else:
        marginal *= _target_weight(state)
    return max(0.0, marginal)


def apply_sensor_update(
    *,
    sensor: Sensor,
    state: TrackState,
    condition: Condition,
) -> float:
    suitability = sensor.suitability.get(state.spec.target_type, 0.0)
    quality = sensor_quality(condition, sensor)
    raw_reduction = sensor.precision * suitability * quality
    reduction_fraction = min(0.62, max(0.015, raw_reduction))
    before = state.covariance
    state.covariance = max(0.18, state.covariance * (1.0 - reduction_fraction))
    return before - state.covariance


def _sensor_capacity(sensor: Sensor, condition: Condition) -> int:
    return max(1, int(round(sensor.capacity * condition.capacity_factor)))


def _active_states(specs: list[TrackSpec], states: dict[str, TrackState], timestamp: int) -> list[TrackState]:
    for spec in specs:
        if spec.arrival == timestamp and spec.track_id not in states:
            states[spec.track_id] = TrackState(
                spec=spec,
                hostility=spec.initial_hostility,
                covariance=spec.initial_covariance,
            )
    active = list(states.values())
    for state in active:
        if state.spec.hostility_shift is not None and timestamp >= state.spec.hostility_shift:
            state.hostility = max(state.hostility, state.spec.shifted_hostility)
    return active


def allocate_tasks(
    *,
    active: list[TrackState],
    condition: Condition,
    policy: str,
    params: PolicyParams | None,
    timestamp: int,
) -> list[tuple[Sensor, TrackState, float]]:
    assignments: list[tuple[Sensor, TrackState, float]] = []
    if policy == "fixed_priority":
        for sensor in SENSORS:
            ranked = sorted(
                active,
                key=lambda state: (
                    state.hostility,
                    sensor.suitability.get(state.spec.target_type, 0.0),
                    state.covariance,
                    -state.spec.arrival,
                ),
                reverse=True,
            )
            for state in ranked[: _sensor_capacity(sensor, condition)]:
                contribution = expected_contribution(
                    sensor=sensor,
                    state=state,
                    condition=condition,
                    policy=policy,
                    params=None,
                    timestamp=timestamp,
                )
                assignments.append((sensor, state, contribution))
        return assignments

    if policy == "greedy_uncertainty":
        for sensor in SENSORS:
            candidates = [
                (
                    expected_contribution(
                        sensor=sensor,
                        state=state,
                        condition=condition,
                        policy=policy,
                        params=None,
                        timestamp=timestamp,
                    )
                    + 0.35 * state.covariance,
                    state,
                )
                for state in active
                if sensor.suitability.get(state.spec.target_type, 0.0) > 0.0
            ]
            candidates.sort(key=lambda item: item[0], reverse=True)
            for score, state in candidates[: _sensor_capacity(sensor, condition)]:
                assignments.append((sensor, state, score))
        return assignments

    if policy != "adaptive_sensor_manager" or params is None:
        raise ValueError(f"unknown policy {policy!r}")

    predicted_cov = {state.spec.track_id: state.covariance for state in active}
    for sensor in SENSORS:
        for _ in range(_sensor_capacity(sensor, condition)):
            best: tuple[float, TrackState] | None = None
            for state in active:
                if sensor.suitability.get(state.spec.target_type, 0.0) <= 0.0:
                    continue
                contribution = expected_contribution(
                    sensor=sensor,
                    state=state,
                    condition=condition,
                    policy=policy,
                    params=params,
                    timestamp=timestamp,
                    predicted_covariance=predicted_cov[state.spec.track_id],
                )
                critical = state.hostility >= 2
                recently_confirmed = (
                    state.last_fcq_time is not None
                    and timestamp - state.last_fcq_time <= 4
                )
                well_covered = (
                    predicted_cov[state.spec.track_id] <= FCQ_THRESHOLD * 0.75
                    and recently_confirmed
                )
                release_gate = params.release_threshold * (1.0 + 0.35 * state.hostility)
                if contribution < release_gate and (not critical or well_covered):
                    continue
                score = contribution / sensor.scan_cost
                if best is None or score > best[0]:
                    best = (score, state)
            if best is None:
                break
            score, state = best
            assignments.append((sensor, state, score))
            pseudo_reduction = min(0.55, sensor.precision * sensor_quality(condition, sensor))
            predicted_cov[state.spec.track_id] = max(
                0.18,
                predicted_cov[state.spec.track_id] * (1.0 - pseudo_reduction),
            )
    return assignments


def simulate_policy(
    specs: list[TrackSpec],
    *,
    condition: Condition,
    policy: str,
    params: PolicyParams | None = None,
    horizon: int = 150,
) -> dict[str, Any]:
    states: dict[str, TrackState] = {}
    critical_observations = 0
    critical_fcq = 0
    high_observations = 0
    high_fcq = 0
    assignment_count = 0
    low_value_assignments = 0
    total_cov_critical = 0.0
    critical_track_ids: set[str] = set()

    for timestamp in range(horizon):
        active = _active_states(specs, states, timestamp)
        for state in active:
            state.covariance = min(9.5, state.covariance + _process_growth(state))
        assignments = allocate_tasks(
            active=active,
            condition=condition,
            policy=policy,
            params=params,
            timestamp=timestamp,
        )
        for sensor, state, estimated in assignments:
            actual = apply_sensor_update(sensor=sensor, state=state, condition=condition)
            assignment_count += 1
            if actual < 0.025 or (state.covariance <= FCQ_THRESHOLD * 0.80 and estimated < 0.07):
                low_value_assignments += 1

        for state in active:
            if state.covariance <= FCQ_THRESHOLD:
                state.last_fcq_time = timestamp
                if (
                    state.spec.hostility_shift is not None
                    and timestamp >= state.spec.hostility_shift
                    and state.first_fcq_after_shift is None
                ):
                    state.first_fcq_after_shift = timestamp
            if state.hostility >= 2:
                critical_track_ids.add(state.spec.track_id)
                critical_observations += 1
                total_cov_critical += state.covariance
                if state.covariance <= FCQ_THRESHOLD:
                    critical_fcq += 1
            if state.hostility >= 3:
                high_observations += 1
                if state.covariance <= FCQ_THRESHOLD:
                    high_fcq += 1

    delays = []
    missed_shift_count = 0
    for state in states.values():
        if state.spec.hostility_shift is None or state.spec.hostility_shift >= horizon:
            continue
        if state.first_fcq_after_shift is None:
            missed_shift_count += 1
            delays.append(horizon - state.spec.hostility_shift)
        else:
            delays.append(state.first_fcq_after_shift - state.spec.hostility_shift)

    return {
        "policy": policy,
        "critical_fcq_rate": critical_fcq / critical_observations if critical_observations else 0.0,
        "high_hostility_fcq_rate": high_fcq / high_observations if high_observations else 0.0,
        "mean_critical_covariance": (
            total_cov_critical / critical_observations if critical_observations else 0.0
        ),
        "low_value_task_fraction": (
            low_value_assignments / assignment_count if assignment_count else 0.0
        ),
        "assignments_per_step": assignment_count / horizon,
        "median_shift_response_delay": float(median(delays)) if delays else 0.0,
        "missed_shift_count": missed_shift_count,
        "critical_track_count": len(critical_track_ids),
        "track_count": len(states),
    }


def _bootstrap_interval(deltas: list[float], *, seed: int = 88_111, samples: int = 800) -> list[float]:
    if not deltas:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    values = np.array(deltas, dtype=float)
    means = []
    for _ in range(samples):
        draw = rng.choice(values, size=len(values), replace=True)
        means.append(float(np.mean(draw)))
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def _paired_summary(
    rows: list[dict[str, Any]],
    *,
    baseline: str,
    key: str,
    higher_is_better: bool,
) -> dict[str, Any]:
    deltas = [
        float(row[f"adaptive_sensor_manager_{key}"]) - float(row[f"{baseline}_{key}"])
        for row in rows
    ]
    favorable = [delta >= 0 if higher_is_better else delta <= 0 for delta in deltas]
    return {
        "mean_delta": float(np.mean(deltas)) if deltas else 0.0,
        "bootstrap_95pct_interval": _bootstrap_interval(deltas),
        "scenario_count": len(deltas),
        "favorable_scenario_fraction": sum(favorable) / len(favorable) if favorable else 0.0,
    }


def evaluate_condition(
    condition: Condition,
    *,
    validation_seeds: Iterable[int],
    params: PolicyParams,
    horizon: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    policy_metrics: dict[str, list[dict[str, Any]]] = {
        "fixed_priority": [],
        "greedy_uncertainty": [],
        "adaptive_sensor_manager": [],
    }
    for seed in validation_seeds:
        specs = generate_tracks(seed=seed, condition=condition, horizon=horizon)
        row: dict[str, Any] = {"condition": condition.name, "seed": seed}
        for policy in policy_metrics:
            metrics = simulate_policy(
                specs,
                condition=condition,
                policy=policy,
                params=params if policy == "adaptive_sensor_manager" else None,
                horizon=horizon,
            )
            policy_metrics[policy].append(metrics)
            for key, value in metrics.items():
                if key == "policy":
                    continue
                row[f"{policy}_{key}"] = value
        rows.append(row)

    aggregate: dict[str, Any] = {}
    metric_keys = [
        "critical_fcq_rate",
        "high_hostility_fcq_rate",
        "mean_critical_covariance",
        "low_value_task_fraction",
        "assignments_per_step",
        "median_shift_response_delay",
        "missed_shift_count",
        "critical_track_count",
        "track_count",
    ]
    for policy, metrics in policy_metrics.items():
        aggregate[policy] = {
            key: float(np.mean([row[key] for row in metrics]))
            for key in metric_keys
        }
    for baseline in ("fixed_priority", "greedy_uncertainty"):
        aggregate[f"adaptive_vs_{baseline}"] = {
            "critical_fcq_rate": _paired_summary(
                rows,
                baseline=baseline,
                key="critical_fcq_rate",
                higher_is_better=True,
            ),
            "high_hostility_fcq_rate": _paired_summary(
                rows,
                baseline=baseline,
                key="high_hostility_fcq_rate",
                higher_is_better=True,
            ),
            "mean_critical_covariance": _paired_summary(
                rows,
                baseline=baseline,
                key="mean_critical_covariance",
                higher_is_better=False,
            ),
            "low_value_task_fraction": _paired_summary(
                rows,
                baseline=baseline,
                key="low_value_task_fraction",
                higher_is_better=False,
            ),
            "assignments_per_step": _paired_summary(
                rows,
                baseline=baseline,
                key="assignments_per_step",
                higher_is_better=False,
            ),
            "median_shift_response_delay": _paired_summary(
                rows,
                baseline=baseline,
                key="median_shift_response_delay",
                higher_is_better=False,
            ),
        }
    return aggregate, rows


def select_policy(
    *,
    development_seeds: Iterable[int],
    horizon: int,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    selected: PolicyParams | None = None
    best_score = -1e9
    dev_conditions = [CONDITIONS[0], CONDITIONS[1], CONDITIONS[3]]
    for params in POLICY_CANDIDATES:
        rows: list[dict[str, Any]] = []
        for condition in dev_conditions:
            _, condition_rows = evaluate_condition(
                condition,
                validation_seeds=development_seeds,
                params=params,
                horizon=horizon,
            )
            rows.extend(condition_rows)
        fcq_delta = np.mean(
            [
                row["adaptive_sensor_manager_critical_fcq_rate"]
                - row["greedy_uncertainty_critical_fcq_rate"]
                for row in rows
            ]
        )
        waste_delta = np.mean(
            [
                row["adaptive_sensor_manager_low_value_task_fraction"]
                - row["greedy_uncertainty_low_value_task_fraction"]
                for row in rows
            ]
        )
        delay_delta = np.mean(
            [
                row["adaptive_sensor_manager_median_shift_response_delay"]
                - row["greedy_uncertainty_median_shift_response_delay"]
                for row in rows
            ]
        )
        score = float(fcq_delta - 0.35 * waste_delta - 0.010 * delay_delta)
        record = {
            "name": params.name,
            "critical_fcq_delta_vs_greedy": float(fcq_delta),
            "low_value_task_fraction_delta_vs_greedy": float(waste_delta),
            "median_shift_response_delay_delta_vs_greedy": float(delay_delta),
            "selection_score": score,
        }
        candidates.append(record)
        if score > best_score:
            best_score = score
            selected = params
    assert selected is not None
    return {
        "selected": selected,
        "candidates": candidates,
        "selection_rule": (
            "maximize development critical-FCQ delta versus greedy uncertainty, "
            "penalizing low-value tasking and hostility-shift response delay"
        ),
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_suite(
    *,
    out_dir: Path,
    development_scenarios: int = 12,
    validation_scenarios: int = 24,
    development_seed_base: int = 3_100_000,
    validation_seed_base: int = 3_900_000,
    horizon: int = 150,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    development_seeds = [
        development_seed_base + index * 10_007
        for index in range(development_scenarios)
    ]
    validation_seeds = [
        validation_seed_base + index * 10_007
        for index in range(validation_scenarios)
    ]
    selection = select_policy(development_seeds=development_seeds, horizon=horizon)
    selected: PolicyParams = selection["selected"]

    condition_results: dict[str, Any] = {}
    scenario_rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        aggregate, rows = evaluate_condition(
            condition,
            validation_seeds=validation_seeds,
            params=selected,
            horizon=horizon,
        )
        condition_results[condition.name] = {
            "configuration": {
                "initial_tracks": condition.initial_tracks,
                "arrival_rate": condition.arrival_rate,
                "shift_probability": condition.shift_probability,
                "clutter_multiplier": condition.clutter_multiplier,
                "maneuver_multiplier": condition.maneuver_multiplier,
                "capacity_factor": condition.capacity_factor,
                "sensor_quality": condition.sensor_quality or {},
            },
            "metrics": aggregate,
        }
        scenario_rows.extend(rows)

    summary = {
        "schema": "nv065_adaptive_sensor_tasking_benchmark_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "development": {
            "scenario_count": development_scenarios,
            "seed_base": development_seed_base,
            "conditions": ["nominal", "dense_raid", "hostility_shift"],
            "selected_policy": selected.__dict__,
            "candidate_results": selection["candidates"],
            "selection_rule": selection["selection_rule"],
        },
        "validation": {
            "scenarios_per_condition": validation_scenarios,
            "seed_base": validation_seed_base,
            "horizon": horizon,
            "fcq_threshold": FCQ_THRESHOLD,
            "conditions": condition_results,
        },
        "limitations": [
            "No SSDS, Aegis, Navy sensor, fire-control, or operational data.",
            "No electromagnetic propagation, radar waveform, covariance filter, or classified model.",
            "No real-time implementation, cybersecurity assessment, or integration test.",
            "Sensor names are topic-aligned archetypes; parameters are generated assumptions.",
            "The benchmark tests tasking allocation behavior, not fire-control readiness.",
        ],
    }

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    csv_path = out_dir / "scenario_summary.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scenario_rows[0]))
        writer.writeheader()
        writer.writerows(scenario_rows)

    lines = [
        "# NV065 Adaptive Sensor-Tasking Scorecard",
        "",
        f"Evidence boundary: {EVIDENCE_BOUNDARY}",
        "",
        "## Development Gate",
        "",
        f"- Development scenarios: {development_scenarios}",
        f"- Selected policy: {selected.name}",
        "- Development conditions: nominal, dense raid, hostility shift.",
        "- Baselines: fixed priority and greedy uncertainty tasking.",
        "",
        "## Frozen Validation",
        "",
        "| Condition | Greedy critical FCQ | ASM critical FCQ | Critical FCQ delta [95% CI] | Sensor-task delta | Low-value fraction delta | Shift-delay delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metrics = condition_results[condition.name]["metrics"]
        greedy = metrics["greedy_uncertainty"]
        asm = metrics["adaptive_sensor_manager"]
        delta = metrics["adaptive_vs_greedy_uncertainty"]
        fcq = delta["critical_fcq_rate"]
        interval = fcq["bootstrap_95pct_interval"]
        task_delta = delta["assignments_per_step"]["mean_delta"]
        waste_delta = delta["low_value_task_fraction"]["mean_delta"]
        delay_delta = delta["median_shift_response_delay"]["mean_delta"]
        lines.append(
            "| "
            f"{condition.name} | "
            f"{greedy['critical_fcq_rate']:.3f} | "
            f"{asm['critical_fcq_rate']:.3f} | "
            f"{fcq['mean_delta']:+.3f} [{interval[0]:+.3f}, {interval[1]:+.3f}] | "
            f"{task_delta:+.2f} | "
            f"{waste_delta:+.3f} | "
            f"{delay_delta:+.2f} |"
        )
    lines.extend(
        [
            "",
            "Negative sensor-task and shift-delay deltas favor the adaptive "
            "sensor manager. Low-value fraction is a diagnostic and may worsen "
            "when fewer total updates are concentrated on already-controlled "
            "critical tracks. All comparisons use identical generated tracks "
            "per paired seed.",
            "",
            "## Interpretation",
            "",
            "The benchmark tests a narrow allocation hypothesis: marginal "
            "contribution estimates can release generated sensor resources from "
            "well-characterized tracks and reallocate them to tracks with greater "
            "expected fire-control-quality benefit. Stress conditions are "
            "generated feasibility checks, not operating envelopes. Any condition "
            "with weak or negative critical-FCQ delta remains a preserved failure "
            "region for the proposal.",
            "",
        ]
    )
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text("\n".join(lines), encoding="utf-8")

    files = {}
    for path in (summary_path, csv_path, scorecard_path):
        files[path.name] = {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
    manifest_path = out_dir / "manifest.sha256.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema": "nv065_sensor_tasking_manifest_v1",
                "generated_utc": summary["generated_utc"],
                "files": files,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--development-scenarios", type=int, default=12)
    parser.add_argument("--validation-scenarios", type=int, default=24)
    parser.add_argument("--development-seed-base", type=int, default=3_100_000)
    parser.add_argument("--validation-seed-base", type=int, default=3_900_000)
    parser.add_argument("--horizon", type=int, default=150)
    args = parser.parse_args()
    summary = run_suite(
        out_dir=args.out,
        development_scenarios=max(3, args.development_scenarios),
        validation_scenarios=max(3, args.validation_scenarios),
        development_seed_base=args.development_seed_base,
        validation_seed_base=args.validation_seed_base,
        horizon=max(80, args.horizon),
    )
    print(
        json.dumps(
            {
                "selected_policy": summary["development"]["selected_policy"]["name"],
                "conditions": {
                    name: result["metrics"]["adaptive_vs_greedy_uncertainty"][
                        "critical_fcq_rate"
                    ]
                    for name, result in summary["validation"]["conditions"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
