"""Preliminary synthetic benchmark for a DICE TA1/TA2 research concept.

This is a lightweight discrete-event model, not an LLM-agent evaluation and
not evidence of operational DoD performance. It compares:

1. A centralized assignment baseline with periodic global status collection.
2. A sparse peer-auction mesh with local reputation and role-coherence repair.

The benchmark is intentionally reproducible and writes its evidence boundary
into every machine-readable result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "dice_preliminary"
EVIDENCE_BOUNDARY = (
    "Synthetic discrete-event software benchmark only. Agents are stochastic "
    "task executors, not language models. Results do not establish DICE program "
    "metric attainment, operational DoD performance, or adversarial security."
)


@dataclass
class TrialResult:
    architecture: str
    seed: int
    agents: int
    tasks: int
    compromised_fraction: float
    failed_fraction: float
    mission_success_rate: float
    messages: int
    messages_per_completed_task: float
    recovery_messages: int
    role_coherence_rate: float
    false_commitments: int


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _agent_population(rng: random.Random, agents: int, roles: int) -> list[dict[str, Any]]:
    population = []
    for agent_id in range(agents):
        role = agent_id % roles
        population.append(
            {
                "id": agent_id,
                "role": role,
                "skill": 0.62 + 0.34 * rng.random(),
                "reputation": 1.0,
                "coherent": True,
                "failed": False,
                "compromised": False,
                "failures": 0,
            }
        )
    rng.shuffle(population)
    return population


def _apply_perturbation(
    rng: random.Random,
    population: list[dict[str, Any]],
    failed_fraction: float,
    compromised_fraction: float,
) -> None:
    ids = list(range(len(population)))
    rng.shuffle(ids)
    failed_count = round(len(population) * failed_fraction)
    compromised_count = round(len(population) * compromised_fraction)
    for idx in ids[:failed_count]:
        population[idx]["failed"] = True
    for idx in ids[failed_count : failed_count + compromised_count]:
        population[idx]["compromised"] = True


def _task_roles(rng: random.Random, tasks: int, roles: int) -> list[int]:
    task_roles = [idx % roles for idx in range(tasks)]
    rng.shuffle(task_roles)
    return task_roles


def _attempt(
    rng: random.Random,
    agent: dict[str, Any],
    role: int,
    coherence_penalty: float,
) -> tuple[bool, bool]:
    if agent["failed"]:
        return False, False
    role_match = agent["role"] == role
    probability = float(agent["skill"])
    if not role_match:
        probability *= 0.42
    if not agent["coherent"]:
        probability *= coherence_penalty
    false_commitment = False
    if agent["compromised"]:
        false_commitment = rng.random() < 0.70
        probability *= 0.18
    return rng.random() < probability, false_commitment


def _maybe_drift(rng: random.Random, agent: dict[str, Any], drift_probability: float) -> None:
    if not agent["failed"] and rng.random() < drift_probability:
        agent["coherent"] = False


def run_centralized(
    seed: int,
    agents: int,
    tasks: int,
    roles: int,
    failed_fraction: float,
    compromised_fraction: float,
) -> TrialResult:
    rng = random.Random(seed)
    population = _agent_population(rng, agents, roles)
    task_roles = _task_roles(rng, tasks, roles)
    _apply_perturbation(rng, population, failed_fraction, compromised_fraction)
    by_role: dict[int, list[dict[str, Any]]] = {role: [] for role in range(roles)}
    for agent in population:
        by_role[agent["role"]].append(agent)
    for role_pool in by_role.values():
        role_pool.sort(key=lambda agent: (-float(agent["skill"]), agent["id"]))

    messages = agents  # initial global status collection
    recovery_messages = agents  # global rescan after the perturbation
    completed = 0
    false_commitments = 0
    coherent_observations = 0
    observations = 0

    for task_index, role in enumerate(task_roles):
        if task_index and task_index % max(1, agents // 2) == 0:
            messages += agents
        candidates = []
        for agent in by_role[role]:
            if not agent["failed"] and agent["failures"] < 3:
                candidates.append(agent)
                if len(candidates) == 4:
                    break
        success = False
        for agent in candidates:
            messages += 2  # dispatch plus result
            if task_index < max(1, tasks // 5):
                recovery_messages += 2
            observations += 1
            coherent_observations += int(bool(agent["coherent"]))
            task_success, false_commitment = _attempt(rng, agent, role, 0.48)
            false_commitments += int(false_commitment)
            _maybe_drift(rng, agent, 0.018)
            if task_success:
                completed += 1
                success = True
                break
            agent["failures"] += 1
        if not success:
            continue

    coherence_rate = coherent_observations / observations if observations else 0.0
    return TrialResult(
        architecture="centralized_baseline",
        seed=seed,
        agents=agents,
        tasks=tasks,
        compromised_fraction=compromised_fraction,
        failed_fraction=failed_fraction,
        mission_success_rate=completed / tasks,
        messages=messages,
        messages_per_completed_task=messages / max(1, completed),
        recovery_messages=recovery_messages,
        role_coherence_rate=coherence_rate,
        false_commitments=false_commitments,
    )


def run_peer_mesh(
    seed: int,
    agents: int,
    tasks: int,
    roles: int,
    failed_fraction: float,
    compromised_fraction: float,
    neighborhood: int = 8,
) -> TrialResult:
    rng = random.Random(seed)
    population = _agent_population(rng, agents, roles)
    task_roles = _task_roles(rng, tasks, roles)
    _apply_perturbation(rng, population, failed_fraction, compromised_fraction)

    by_role: dict[int, list[dict[str, Any]]] = {role: [] for role in range(roles)}
    for agent in population:
        by_role[agent["role"]].append(agent)

    # One local capability advertisement per agent initializes bounded peer
    # caches. Each task then uses one neighborhood announcement; candidates
    # are ranked from cached capability/reputation and contacted in order.
    messages = agents
    recovery_messages = 0
    completed = 0
    false_commitments = 0
    coherent_observations = 0
    observations = 0

    for task_index, role in enumerate(task_roles):
        role_pool = by_role[role]
        start = (seed + task_index * 17) % len(role_pool)
        candidates = [
            role_pool[(start + offset) % len(role_pool)]
            for offset in range(min(neighborhood, len(role_pool)))
        ]
        messages += 1  # neighborhood task announcement
        if task_index < max(1, tasks // 5):
            recovery_messages += 1

        ranked = sorted(
            candidates,
            key=lambda agent: (
                -(
                    float(agent["skill"])
                    * float(agent["reputation"])
                    * (1.0 if agent["coherent"] else 0.55)
                ),
                agent["id"],
            ),
        )

        for agent in ranked:
            if not agent["coherent"]:
                messages += 1
                if task_index < max(1, tasks // 5):
                    recovery_messages += 1
                if rng.random() < 0.88:
                    agent["coherent"] = True

            messages += 1
            if task_index < max(1, tasks // 5):
                recovery_messages += 1
            observations += 1
            coherent_observations += int(bool(agent["coherent"]))
            task_success, false_commitment = _attempt(rng, agent, role, 0.72)
            false_commitments += int(false_commitment)
            _maybe_drift(rng, agent, 0.018)

            if task_success:
                completed += 1
                agent["reputation"] = min(1.0, agent["reputation"] + 0.025)
                break

            penalty = 0.38 if false_commitment else 0.16
            agent["reputation"] = max(0.05, agent["reputation"] - penalty)
            messages += 2  # local challenge and re-auction notice
            if task_index < max(1, tasks // 5):
                recovery_messages += 2

    coherence_rate = coherent_observations / observations if observations else 0.0
    return TrialResult(
        architecture="peer_auction_with_local_control",
        seed=seed,
        agents=agents,
        tasks=tasks,
        compromised_fraction=compromised_fraction,
        failed_fraction=failed_fraction,
        mission_success_rate=completed / tasks,
        messages=messages,
        messages_per_completed_task=messages / max(1, completed),
        recovery_messages=recovery_messages,
        role_coherence_rate=coherence_rate,
        false_commitments=false_commitments,
    )


def _aggregate(rows: list[TrialResult]) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[TrialResult]] = {}
    for row in rows:
        grouped.setdefault(row.architecture, []).append(row)

    output: dict[str, dict[str, float]] = {}
    for architecture, trials in grouped.items():
        output[architecture] = {
            "trials": float(len(trials)),
            "mission_success_rate_mean": mean(x.mission_success_rate for x in trials),
            "mission_success_rate_min": min(x.mission_success_rate for x in trials),
            "messages_mean": mean(x.messages for x in trials),
            "messages_per_completed_task_mean": mean(
                x.messages_per_completed_task for x in trials
            ),
            "recovery_messages_median": median(x.recovery_messages for x in trials),
            "role_coherence_rate_mean": mean(x.role_coherence_rate for x in trials),
            "false_commitments_mean": mean(x.false_commitments for x in trials),
        }
    return output


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _paired_statistics(rows: list[TrialResult], bootstrap_samples: int = 2000) -> dict[str, Any]:
    by_seed: dict[int, dict[str, TrialResult]] = {}
    for row in rows:
        by_seed.setdefault(row.seed, {})[row.architecture] = row

    paired = [
        pair
        for _, pair in sorted(by_seed.items())
        if {"centralized_baseline", "peer_auction_with_local_control"} <= set(pair)
    ]
    metrics = {
        "mission_success_rate_points": [
            100.0
            * (
                pair["peer_auction_with_local_control"].mission_success_rate
                - pair["centralized_baseline"].mission_success_rate
            )
            for pair in paired
        ],
        "message_reduction_pct": [
            100.0
            * (
                1.0
                - pair["peer_auction_with_local_control"].messages
                / max(1, pair["centralized_baseline"].messages)
            )
            for pair in paired
        ],
        "recovery_message_reduction_pct": [
            100.0
            * (
                1.0
                - pair["peer_auction_with_local_control"].recovery_messages
                / max(1, pair["centralized_baseline"].recovery_messages)
            )
            for pair in paired
        ],
        "role_coherence_rate_points": [
            100.0
            * (
                pair["peer_auction_with_local_control"].role_coherence_rate
                - pair["centralized_baseline"].role_coherence_rate
            )
            for pair in paired
        ],
    }

    rng = random.Random(91_173)
    output: dict[str, Any] = {"paired_trials": len(paired)}
    for name, values in metrics.items():
        boot_means = []
        for _ in range(bootstrap_samples):
            sample = [values[rng.randrange(len(values))] for _ in values]
            boot_means.append(mean(sample))
        output[name] = {
            "mean": mean(values),
            "median": median(values),
            "bootstrap_95_ci": [
                _percentile(boot_means, 0.025),
                _percentile(boot_means, 0.975),
            ],
        }
    return output


def run_benchmark(
    out_dir: Path,
    seeds: int = 30,
    agents: int = 500,
    tasks: int = 1200,
    roles: int = 12,
    failed_fraction: float = 0.10,
    compromised_fraction: float = 0.05,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[TrialResult] = []
    for offset in range(seeds):
        seed = 726_000 + offset
        rows.append(
            run_centralized(
                seed,
                agents,
                tasks,
                roles,
                failed_fraction,
                compromised_fraction,
            )
        )
        rows.append(
            run_peer_mesh(
                seed,
                agents,
                tasks,
                roles,
                failed_fraction,
                compromised_fraction,
            )
        )

    aggregate = _aggregate(rows)
    paired_statistics = _paired_statistics(rows)
    centralized = aggregate["centralized_baseline"]
    peer = aggregate["peer_auction_with_local_control"]
    result = {
        "schema": "dice_preliminary_synthetic_benchmark_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "configuration": {
            "seeds": seeds,
            "agents": agents,
            "tasks": tasks,
            "roles": roles,
            "failed_fraction": failed_fraction,
            "compromised_fraction": compromised_fraction,
            "peer_neighborhood": 8,
        },
        "aggregate": aggregate,
        "paired_statistics": paired_statistics,
        "paired_deltas": {
            "mission_success_rate_points": 100.0
            * (
                peer["mission_success_rate_mean"]
                - centralized["mission_success_rate_mean"]
            ),
            "message_reduction_pct": 100.0
            * (
                1.0
                - peer["messages_mean"] / max(1.0, centralized["messages_mean"])
            ),
            "recovery_message_reduction_pct": 100.0
            * (
                1.0
                - peer["recovery_messages_median"]
                / max(1.0, centralized["recovery_messages_median"])
            ),
            "role_coherence_rate_points": 100.0
            * (
                peer["role_coherence_rate_mean"]
                - centralized["role_coherence_rate_mean"]
            ),
        },
        "platform": platform.platform(),
        "python": platform.python_version(),
        "git_commit": _git_commit(),
    }

    trial_path = out_dir / "trials.csv"
    with trial_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(row) for row in rows)

    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(
        "\n".join(
            [
                "# DICE Preliminary Synthetic Scorecard",
                "",
                f"Evidence boundary: {EVIDENCE_BOUNDARY}",
                "",
                "## Configuration",
                "",
                f"- Paired seeds: {seeds}",
                f"- Agents per trial: {agents}",
                f"- Tasks per trial: {tasks}",
                f"- Distinct roles: {roles}",
                f"- Failed agents: {failed_fraction:.1%}",
                f"- Compromised agents: {compromised_fraction:.1%}",
                "",
                "## Mean Results",
                "",
                (
                    "- Centralized mission success: "
                    f"{centralized['mission_success_rate_mean']:.3f}"
                ),
                (
                    "- Peer mesh mission success: "
                    f"{peer['mission_success_rate_mean']:.3f}"
                ),
                (
                    "- Mission-success delta: "
                    f"{paired_statistics['mission_success_rate_points']['mean']:+.2f} points "
                    f"(95% bootstrap CI "
                    f"{paired_statistics['mission_success_rate_points']['bootstrap_95_ci'][0]:+.2f} "
                    f"to {paired_statistics['mission_success_rate_points']['bootstrap_95_ci'][1]:+.2f})"
                ),
                (
                    "- Message reduction: "
                    f"{paired_statistics['message_reduction_pct']['mean']:.1f}% "
                    f"(95% bootstrap CI "
                    f"{paired_statistics['message_reduction_pct']['bootstrap_95_ci'][0]:.1f}% "
                    f"to {paired_statistics['message_reduction_pct']['bootstrap_95_ci'][1]:.1f}%)"
                ),
                (
                    "- Recovery-message reduction: "
                    f"{paired_statistics['recovery_message_reduction_pct']['mean']:.1f}% "
                    f"(95% bootstrap CI "
                    f"{paired_statistics['recovery_message_reduction_pct']['bootstrap_95_ci'][0]:.1f}% "
                    f"to {paired_statistics['recovery_message_reduction_pct']['bootstrap_95_ci'][1]:.1f}%)"
                ),
                (
                    "- Role-coherence delta: "
                    f"{paired_statistics['role_coherence_rate_points']['mean']:+.2f} points "
                    f"(95% bootstrap CI "
                    f"{paired_statistics['role_coherence_rate_points']['bootstrap_95_ci'][0]:+.2f} "
                    f"to {paired_statistics['role_coherence_rate_points']['bootstrap_95_ci'][1]:+.2f})"
                ),
                "",
                "## Interpretation",
                "",
                (
                    "This run is feasibility evidence for the measurement harness and "
                    "research hypothesis only. A conforming DICE evaluation still needs "
                    "heterogeneous agentic AI systems, a TA3-compatible adaptor, stronger "
                    "baselines, preregistered adversarial tests, and independent evaluation."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )

    manifest = {
        "schema": "dice_preliminary_manifest_v1",
        "generated_utc": result["generated_utc"],
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (trial_path, summary_path, scorecard_path)
        },
    }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seeds", type=int, default=30)
    parser.add_argument("--agents", type=int, default=500)
    parser.add_argument("--tasks", type=int, default=1200)
    args = parser.parse_args()
    result = run_benchmark(
        out_dir=args.out,
        seeds=max(1, args.seeds),
        agents=max(24, args.agents),
        tasks=max(24, args.tasks),
    )
    print(json.dumps(result["paired_deltas"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
