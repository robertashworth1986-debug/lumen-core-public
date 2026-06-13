"""Synthetic organizational workflow benchmark for MissionWeave.

The benchmark uses generated cases and workers. It evaluates whether a frozen
evidence-aware routing policy improves bounded workflow metrics over fixed-role
and cross-trained FIFO policies. It is not DLA, personnel, causal, operational,
fairness, or productivity evidence.
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
from statistics import median
from typing import Any, Iterable

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "missionweave_validation"
EVIDENCE_BOUNDARY = (
    "Generated-workflow software benchmark only. Cases, workers, skills, "
    "deadlines, absences, and outages are synthetic. Results do not establish "
    "DLA readiness, workforce productivity, causal impact, fairness, privacy "
    "compliance, operational integration, or a 10x improvement."
)


@dataclass(frozen=True)
class Worker:
    worker_id: str
    primary_skill: str
    skills: dict[str, float]


@dataclass(frozen=True)
class CaseSpec:
    case_id: str
    arrival: int
    case_type: str
    criticality: int
    due: int
    efforts: tuple[float, float, float]

    @property
    def stages(self) -> tuple[str, str, str]:
        return ("intake", f"analysis_{self.case_type}", "review")


@dataclass
class CaseState:
    spec: CaseSpec
    stage_index: int = 0
    remaining: float = 0.0
    completed_at: int | None = None

    def __post_init__(self) -> None:
        if self.remaining <= 0.0:
            self.remaining = self.spec.efforts[0]

    @property
    def required_skill(self) -> str:
        return self.spec.stages[self.stage_index]


@dataclass(frozen=True)
class Condition:
    name: str
    arrival_rate: float
    absence_workers: tuple[str, ...] = ()
    absence_start: int = 70
    absence_end: int = 125
    outage_start: int = 85
    outage_end: int = 115
    outage_capacity: float = 1.0


@dataclass(frozen=True)
class PolicyWeights:
    name: str
    criticality: float
    urgency: float
    age: float
    skill: float
    bottleneck: float


WORKERS = (
    Worker(
        "W1",
        "intake",
        {"intake": 1.00, "analysis_a": 0.55},
    ),
    Worker(
        "W2",
        "intake",
        {"intake": 1.00, "analysis_b": 0.55},
    ),
    Worker(
        "W3",
        "analysis_a",
        {"analysis_a": 1.00, "analysis_b": 0.55, "intake": 0.60},
    ),
    Worker(
        "W4",
        "analysis_b",
        {"analysis_b": 1.00, "analysis_a": 0.55, "intake": 0.60},
    ),
    Worker(
        "W5",
        "review",
        {"review": 1.00, "analysis_a": 0.55},
    ),
    Worker(
        "W6",
        "review",
        {"review": 1.00, "analysis_b": 0.55},
    ),
    Worker(
        "W7",
        "analysis_a",
        {
            "intake": 0.80,
            "analysis_a": 0.80,
            "analysis_b": 0.80,
            "review": 0.60,
        },
    ),
)

WEIGHT_CANDIDATES = (
    PolicyWeights("balanced", 2.0, 3.0, 1.0, 1.0, 1.0),
    PolicyWeights("deadline", 1.5, 5.0, 0.5, 1.0, 1.0),
    PolicyWeights("critical", 5.0, 2.0, 1.0, 1.0, 0.5),
    PolicyWeights("flow", 1.0, 1.0, 4.0, 1.0, 2.0),
)

CONDITIONS = (
    Condition("nominal", 0.42),
    Condition("surge", 0.68),
    Condition("targeted_absence", 0.42, ("W3", "W5")),
    Condition("system_outage", 0.42, outage_capacity=0.45),
    Condition(
        "combined_stress",
        0.68,
        ("W3", "W5"),
        outage_capacity=0.45,
    ),
)


def generate_cases(
    *,
    seed: int,
    arrival_rate: float,
    horizon: int,
) -> list[CaseSpec]:
    rng = np.random.default_rng(seed)
    cases: list[CaseSpec] = []
    case_index = 0
    for timestamp in range(horizon):
        arrivals = int(rng.poisson(arrival_rate))
        for _ in range(arrivals):
            case_type = "a" if rng.random() < 0.54 else "b"
            criticality = int(rng.choice([1, 2, 3], p=[0.58, 0.30, 0.12]))
            effort = (
                float(rng.integers(1, 3)),
                float(rng.integers(3, 7)),
                float(rng.integers(2, 4)),
            )
            nominal_effort = sum(effort)
            due_window = int(
                max(
                    nominal_effort + 3,
                    rng.normal(
                        25.0 - 3.0 * (criticality - 1),
                        3.0,
                    ),
                )
            )
            cases.append(
                CaseSpec(
                    case_id=f"C{case_index:05d}",
                    arrival=timestamp,
                    case_type=case_type,
                    criticality=criticality,
                    due=timestamp + due_window,
                    efforts=effort,
                )
            )
            case_index += 1
    return cases


def _available_capacity(
    worker: Worker,
    condition: Condition,
    timestamp: int,
) -> float:
    if (
        worker.worker_id in condition.absence_workers
        and condition.absence_start <= timestamp < condition.absence_end
    ):
        return 0.0
    if condition.outage_start <= timestamp < condition.outage_end:
        return condition.outage_capacity
    return 1.0


def _remaining_work_estimate(state: CaseState) -> float:
    return state.remaining + sum(state.spec.efforts[state.stage_index + 1 :])


def _stage_counts(states: Iterable[CaseState]) -> dict[str, int]:
    counts = {"intake": 0, "analysis_a": 0, "analysis_b": 0, "review": 0}
    for state in states:
        if state.completed_at is None:
            counts[state.required_skill] += 1
    return counts


def _priority(
    *,
    policy: str,
    worker: Worker,
    state: CaseState,
    timestamp: int,
    weights: PolicyWeights | None,
    stage_counts: dict[str, int],
) -> tuple[float, ...]:
    skill = worker.skills.get(state.required_skill, 0.0)
    age = max(0, timestamp - state.spec.arrival)
    if policy in {"fixed_fifo", "cross_trained_fifo"}:
        return (
            float(age),
            float(state.spec.criticality),
            skill,
            -float(state.spec.arrival),
        )
    if weights is None:
        raise ValueError("MissionWeave policy requires frozen weights")
    slack = state.spec.due - timestamp - _remaining_work_estimate(state)
    urgency = max(0.0, -slack) + 1.0 / max(1.0, slack + 1.0)
    bottleneck = math.log1p(stage_counts[state.required_skill])
    score = (
        weights.criticality * state.spec.criticality
        + weights.urgency * urgency
        + weights.age * age / 25.0
        + weights.skill * skill
        + weights.bottleneck * bottleneck
    )
    return (
        score,
        float(state.spec.criticality),
        -float(state.spec.due),
        skill,
        -float(state.spec.arrival),
    )


def _eligible(
    *,
    policy: str,
    worker: Worker,
    state: CaseState,
) -> bool:
    skill = worker.skills.get(state.required_skill, 0.0)
    if policy == "fixed_fifo":
        return worker.primary_skill == state.required_skill and skill > 0.0
    return skill >= 0.50


def _gini(values: list[float]) -> float:
    clean = np.asarray([max(0.0, value) for value in values], dtype=float)
    if not clean.size or float(clean.sum()) == 0.0:
        return 0.0
    clean.sort()
    n = clean.size
    weighted = sum((index + 1) * value for index, value in enumerate(clean))
    return float((2.0 * weighted) / (n * clean.sum()) - (n + 1.0) / n)


def simulate_policy(
    cases: list[CaseSpec],
    *,
    condition: Condition,
    policy: str,
    weights: PolicyWeights | None = None,
    horizon: int = 180,
    drain_steps: int = 70,
) -> dict[str, Any]:
    states = {case.case_id: CaseState(case) for case in cases}
    arrivals: dict[int, list[CaseState]] = {}
    for state in states.values():
        arrivals.setdefault(state.spec.arrival, []).append(state)
    active: dict[str, CaseState] = {}
    workload = {worker.worker_id: 0.0 for worker in WORKERS}
    cross_trained_assignments = 0
    completed_during_horizon = 0

    for timestamp in range(horizon + drain_steps):
        for state in arrivals.get(timestamp, []):
            active[state.spec.case_id] = state
        stage_counts = _stage_counts(active.values())
        assigned: set[str] = set()
        for worker in WORKERS:
            capacity = _available_capacity(worker, condition, timestamp)
            if capacity <= 0.0:
                continue
            candidates = [
                state
                for state in active.values()
                if state.completed_at is None
                and state.spec.case_id not in assigned
                and _eligible(policy=policy, worker=worker, state=state)
            ]
            if not candidates:
                continue
            selected = max(
                candidates,
                key=lambda state: _priority(
                    policy=policy,
                    worker=worker,
                    state=state,
                    timestamp=timestamp,
                    weights=weights,
                    stage_counts=stage_counts,
                ),
            )
            assigned.add(selected.spec.case_id)
            skill = worker.skills[selected.required_skill]
            productive = capacity * skill
            workload[worker.worker_id] += capacity
            if worker.primary_skill != selected.required_skill:
                cross_trained_assignments += 1
            selected.remaining -= productive
            if selected.remaining <= 1e-12:
                if selected.stage_index == len(selected.spec.stages) - 1:
                    selected.completed_at = timestamp + 1
                    if selected.completed_at <= horizon:
                        completed_during_horizon += 1
                    active.pop(selected.spec.case_id)
                else:
                    selected.stage_index += 1
                    selected.remaining = selected.spec.efforts[
                        selected.stage_index
                    ]

    completed = [
        state for state in states.values() if state.completed_at is not None
    ]
    on_time = [
        state
        for state in completed
        if state.completed_at is not None
        and state.completed_at <= state.spec.due
    ]
    critical = [state for state in states.values() if state.spec.criticality == 3]
    critical_completed = [
        state for state in critical if state.completed_at is not None
    ]
    critical_on_time = [
        state
        for state in critical_completed
        if state.completed_at is not None
        and state.completed_at <= state.spec.due
    ]
    cycle_times = [
        int(state.completed_at - state.spec.arrival)
        for state in completed
        if state.completed_at is not None
    ]
    arrived_during_horizon = [
        state for state in states.values() if state.spec.arrival < horizon
    ]
    return {
        "policy": policy,
        "weights": weights.name if weights else None,
        "arrived_cases": len(arrived_during_horizon),
        "completed_cases": len(completed),
        "completed_during_horizon": completed_during_horizon,
        "completion_rate": (
            len(completed) / len(arrived_during_horizon)
            if arrived_during_horizon
            else 0.0
        ),
        "on_time_rate": len(on_time) / len(completed) if completed else 0.0,
        "critical_completion_rate": (
            len(critical_completed) / len(critical) if critical else 0.0
        ),
        "critical_on_time_rate": (
            len(critical_on_time) / len(critical_completed)
            if critical_completed
            else 0.0
        ),
        "median_cycle_time": float(median(cycle_times)) if cycle_times else None,
        "mean_cycle_time": (
            float(np.mean(cycle_times)) if cycle_times else None
        ),
        "backlog": len(arrived_during_horizon) - len(completed),
        "workload_gini": _gini(list(workload.values())),
        "cross_trained_assignments": cross_trained_assignments,
        "worker_load": workload,
    }


def _selection_objective(metrics: dict[str, Any]) -> float:
    cycle = metrics["mean_cycle_time"]
    return (
        0.45 * metrics["on_time_rate"]
        + 0.35 * metrics["critical_on_time_rate"]
        + 0.20 * metrics["completion_rate"]
        - 0.002 * (cycle if cycle is not None else 1000.0)
    )


def select_weights(
    *,
    development_seeds: list[int],
    horizon: int,
) -> dict[str, Any]:
    conditions = (CONDITIONS[0], CONDITIONS[1])
    candidate_rows: list[dict[str, Any]] = []
    for weights in WEIGHT_CANDIDATES:
        objectives = []
        for condition in conditions:
            for seed in development_seeds:
                cases = generate_cases(
                    seed=seed + _condition_offset(condition.name),
                    arrival_rate=condition.arrival_rate,
                    horizon=horizon,
                )
                metrics = simulate_policy(
                    cases,
                    condition=condition,
                    policy="missionweave",
                    weights=weights,
                    horizon=horizon,
                )
                objectives.append(_selection_objective(metrics))
        candidate_rows.append(
            {
                "name": weights.name,
                "mean_objective": float(np.mean(objectives)),
                "minimum_objective": float(np.min(objectives)),
            }
        )
    selected_row = max(
        candidate_rows,
        key=lambda row: (
            row["mean_objective"],
            row["minimum_objective"],
            row["name"],
        ),
    )
    selected = next(
        weights
        for weights in WEIGHT_CANDIDATES
        if weights.name == selected_row["name"]
    )
    return {
        "selected": selected,
        "candidates": candidate_rows,
        "selection_rule": (
            "maximize mean development objective across nominal and surge; "
            "objective combines on-time, critical on-time, completion, and "
            "mean cycle time"
        ),
    }


def _condition_offset(name: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(name))


def _mean(rows: list[dict[str, Any]], key: str) -> float:
    return float(np.mean([float(row[key]) for row in rows]))


def _paired_values(
    rows: list[dict[str, Any]],
    *,
    left_policy: str,
    right_policy: str,
    key: str,
) -> list[float]:
    by_seed = {(row["seed"], row["policy"]): row for row in rows}
    seeds = sorted({row["seed"] for row in rows})
    return [
        float(by_seed[(seed, left_policy)][key])
        - float(by_seed[(seed, right_policy)][key])
        for seed in seeds
    ]


def _paired_summary(
    rows: list[dict[str, Any]],
    *,
    key: str,
    higher_is_better: bool,
) -> dict[str, Any]:
    values = _paired_values(
        rows,
        left_policy="missionweave",
        right_policy="cross_trained_fifo",
        key=key,
    )
    array = np.asarray(values, dtype=float)
    rng = np.random.default_rng(
        7_000_000 + sum((index + 1) * ord(char) for index, char in enumerate(key))
    )
    bootstrap_means = rng.choice(
        array,
        size=(10_000, len(array)),
        replace=True,
    ).mean(axis=1)
    favorable = array > 0.0 if higher_is_better else array < 0.0
    return {
        "mean_delta": float(array.mean()),
        "bootstrap_95pct_interval": [
            float(np.quantile(bootstrap_means, 0.025)),
            float(np.quantile(bootstrap_means, 0.975)),
        ],
        "favorable_scenario_fraction": float(favorable.mean()),
        "zero_delta_scenario_fraction": float((array == 0.0).mean()),
        "scenario_count": len(values),
    }


def evaluate_condition(
    condition: Condition,
    *,
    validation_seeds: list[int],
    weights: PolicyWeights,
    horizon: int,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    scenario_rows: list[dict[str, Any]] = []
    policies = ("fixed_fifo", "cross_trained_fifo", "missionweave")
    for seed in validation_seeds:
        condition_seed = seed + _condition_offset(condition.name)
        cases = generate_cases(
            seed=condition_seed,
            arrival_rate=condition.arrival_rate,
            horizon=horizon,
        )
        for policy in policies:
            metrics = simulate_policy(
                cases,
                condition=condition,
                policy=policy,
                weights=weights if policy == "missionweave" else None,
                horizon=horizon,
            )
            scenario_rows.append(
                {
                    "condition": condition.name,
                    "seed": seed,
                    **{
                        key: value
                        for key, value in metrics.items()
                        if key != "worker_load"
                    },
                }
            )
    by_policy = {
        policy: [row for row in scenario_rows if row["policy"] == policy]
        for policy in policies
    }
    metric_keys = (
        "completion_rate",
        "on_time_rate",
        "critical_completion_rate",
        "critical_on_time_rate",
        "median_cycle_time",
        "mean_cycle_time",
        "backlog",
        "workload_gini",
        "cross_trained_assignments",
    )
    aggregate = {
        policy: {
            key: _mean(rows, key)
            for key in metric_keys
            if all(row[key] is not None for row in rows)
        }
        for policy, rows in by_policy.items()
    }
    paired = {
        "completion_rate": _paired_summary(
            scenario_rows,
            key="completion_rate",
            higher_is_better=True,
        ),
        "on_time_rate": _paired_summary(
            scenario_rows,
            key="on_time_rate",
            higher_is_better=True,
        ),
        "critical_on_time_rate": _paired_summary(
            scenario_rows,
            key="critical_on_time_rate",
            higher_is_better=True,
        ),
        "mean_cycle_time": _paired_summary(
            scenario_rows,
            key="mean_cycle_time",
            higher_is_better=False,
        ),
        "backlog": _paired_summary(
            scenario_rows,
            key="backlog",
            higher_is_better=False,
        ),
    }
    aggregate["missionweave_vs_cross_trained_fifo"] = paired
    return aggregate, scenario_rows


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_suite(
    *,
    out_dir: Path,
    development_scenarios: int = 16,
    validation_scenarios: int = 30,
    development_seed_base: int = 2_300_000,
    validation_seed_base: int = 2_900_000,
    horizon: int = 180,
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
    selection = select_weights(
        development_seeds=development_seeds,
        horizon=horizon,
    )
    selected: PolicyWeights = selection["selected"]

    condition_results: dict[str, Any] = {}
    scenario_rows: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        aggregate, rows = evaluate_condition(
            condition,
            validation_seeds=validation_seeds,
            weights=selected,
            horizon=horizon,
        )
        condition_results[condition.name] = {
            "configuration": {
                "arrival_rate": condition.arrival_rate,
                "absence_workers": list(condition.absence_workers),
                "absence_window": [
                    condition.absence_start,
                    condition.absence_end,
                ],
                "outage_window": [
                    condition.outage_start,
                    condition.outage_end,
                ],
                "outage_capacity": condition.outage_capacity,
            },
            "metrics": aggregate,
        }
        scenario_rows.extend(rows)

    summary = {
        "schema": "missionweave_generated_workflow_benchmark_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "development": {
            "scenario_count": development_scenarios,
            "seed_base": development_seed_base,
            "conditions": ["nominal", "surge"],
            "selected_weights": selected.__dict__,
            "candidate_results": selection["candidates"],
            "selection_rule": selection["selection_rule"],
        },
        "validation": {
            "scenarios_per_condition": validation_scenarios,
            "seed_base": validation_seed_base,
            "horizon": horizon,
            "drain_steps": 70,
            "conditions": condition_results,
        },
        "limitations": [
            "No DLA, personnel, timecard, workflow, or mission data.",
            "No causal identification of intervention effects.",
            "No validated fairness, privacy, records, or cybersecurity controls.",
            "No operator-in-the-loop or production integration evaluation.",
            "Policies use a small generated worker and skill model.",
            "The benchmark tests routing behavior, not a 10x productivity claim.",
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
        "# MissionWeave Generated-Workflow Scorecard",
        "",
        f"Evidence boundary: {EVIDENCE_BOUNDARY}",
        "",
        "## Development Gate",
        "",
        f"- Development scenarios: {development_scenarios}",
        f"- Selected policy weights: {selected.name}",
        "- Selection used nominal and surge development seeds only.",
        "",
        "## Frozen Validation",
        "",
        "| Condition | FIFO on-time | MissionWeave on-time | On-time delta [95% bootstrap interval] | Favorable seeds | Critical on-time delta | Mean cycle delta |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metrics = condition_results[condition.name]["metrics"]
        baseline = metrics["cross_trained_fifo"]
        missionweave = metrics["missionweave"]
        delta = metrics["missionweave_vs_cross_trained_fifo"]
        on_time = delta["on_time_rate"]
        interval = on_time["bootstrap_95pct_interval"]
        favorable_count = round(
            on_time["favorable_scenario_fraction"]
            * on_time["scenario_count"]
        )
        lines.append(
            "| "
            f"{condition.name} | "
            f"{baseline['on_time_rate']:.3f} | "
            f"{missionweave['on_time_rate']:.3f} | "
            f"{on_time['mean_delta']:+.3f} "
            f"[{interval[0]:+.3f}, {interval[1]:+.3f}] | "
            f"{favorable_count}/{on_time['scenario_count']} | "
            f"{delta['critical_on_time_rate']['mean_delta']:+.3f} | "
            f"{delta['mean_cycle_time']['mean_delta']:+.2f} |"
        )
    lines.extend(
        [
            "",
            "Negative cycle-time and backlog deltas favor MissionWeave. "
            "All comparisons use identical generated cases per paired seed.",
            "The JSON summary includes paired 95% bootstrap intervals and "
            "favorable-scenario fractions for every reported delta.",
            "A favorable-seed count below 30 means some generated scenarios "
            "performed worse even when the average interval excluded zero.",
            "",
            "## Interpretation",
            "",
            "The benchmark tests a bounded routing hypothesis under generated "
            "workflow demand, cross-training, absence, and system-capacity "
            "loss. It does not establish real organizational impact. Any "
            "condition with a negative on-time or critical-on-time delta is a "
            "preserved failure region and should constrain proposal claims.",
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
                "schema": "missionweave_manifest_v1",
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
    parser.add_argument("--development-scenarios", type=int, default=16)
    parser.add_argument("--validation-scenarios", type=int, default=30)
    parser.add_argument("--development-seed-base", type=int, default=2_300_000)
    parser.add_argument("--validation-seed-base", type=int, default=2_900_000)
    parser.add_argument("--horizon", type=int, default=180)
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
                "selected_weights": summary["development"][
                    "selected_weights"
                ]["name"],
                "conditions": {
                    name: result["metrics"][
                        "missionweave_vs_cross_trained_fifo"
                    ]["on_time_rate"]
                    for name, result in summary["validation"][
                        "conditions"
                    ].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
