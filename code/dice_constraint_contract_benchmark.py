"""Constraint-carrying commitment benchmark for a DARPA DICE concept.

This generated discrete-event suite tests a narrow TA1/TA2 coupling idea:
task bids carry locally verifiable role, evidence-lineage, expiration, and
finite coherence-horizon fields. The suite does not use language models and
does not establish DICE metric attainment or adversarial security.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "dice_constraint_contract"
EVIDENCE_BOUNDARY = (
    "Generated discrete-event software benchmark only. Agents are stochastic "
    "executors, not language models. Contract fields and attacks are modeled "
    "assumptions. Results do not establish DICE metric attainment, semantic "
    "correctness, operational defense performance, or adversarial security."
)


@dataclass(frozen=True)
class AgentSpec:
    agent_id: int
    role: int
    skill: float
    coherence_horizon: int
    strategy: int
    failed: bool
    compromised: bool
    attack_mode: str


@dataclass(frozen=True)
class TaskSpec:
    task_id: int
    role: int
    required_horizon: int
    evidence_epoch: int
    risk_tier: int


@dataclass(frozen=True)
class Condition:
    name: str
    failed_fraction: float
    compromised_fraction: float
    collusive_fraction: float
    monitor_noise: float
    stale_evidence_fraction: float


@dataclass(frozen=True)
class TrialResult:
    condition: str
    architecture: str
    seed: int
    agents: int
    tasks: int
    margin: int
    safe_completion_rate: float
    raw_completion_rate: float
    constraint_violation_rate: float
    compromised_assignment_rate: float
    messages_per_safe_completion: float
    messages: int
    contract_fields_transmitted: int
    false_rejection_rate: float
    strategy_entropy: float
    unavailable_task_rate: float


CONDITIONS = (
    Condition("benign", 0.05, 0.00, 0.00, 0.02, 0.02),
    Condition("independent_compromise_10pct", 0.05, 0.10, 0.00, 0.04, 0.05),
    Condition("collusion_10pct", 0.05, 0.10, 0.75, 0.04, 0.05),
    Condition("monitor_shift", 0.05, 0.10, 0.35, 0.22, 0.08),
    Condition("high_collusion_25pct", 0.05, 0.25, 0.90, 0.06, 0.10),
)


def _u01(seed: int, *parts: object) -> float:
    payload = "|".join(str(part) for part in (seed, *parts)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64)


def _choice_index(seed: int, size: int, *parts: object) -> int:
    if size <= 0:
        raise ValueError("size must be positive")
    return min(size - 1, int(_u01(seed, *parts) * size))


def generate_trial(
    *,
    seed: int,
    agents: int,
    tasks: int,
    roles: int,
    condition: Condition,
) -> tuple[list[AgentSpec], list[TaskSpec]]:
    failed_count = round(agents * condition.failed_fraction)
    compromised_count = round(agents * condition.compromised_fraction)
    ordering = sorted(range(agents), key=lambda idx: _u01(seed, "state", idx))
    failed = set(ordering[:failed_count])
    compromised = set(ordering[failed_count : failed_count + compromised_count])

    population = []
    for agent_id in range(agents):
        attack_roll = _u01(seed, "attack", agent_id)
        if agent_id not in compromised:
            attack_mode = "honest"
        elif attack_roll < condition.collusive_fraction:
            attack_mode = "consistent_collusion"
        elif attack_roll < condition.collusive_fraction + 0.55 * (
            1.0 - condition.collusive_fraction
        ):
            attack_mode = "malformed_contract"
        else:
            attack_mode = "stale_lineage"
        population.append(
            AgentSpec(
                agent_id=agent_id,
                role=agent_id % roles,
                skill=0.60 + 0.36 * _u01(seed, "skill", agent_id),
                coherence_horizon=4
                + _choice_index(seed, 13, "horizon", agent_id),
                strategy=agent_id % 8,
                failed=agent_id in failed,
                compromised=agent_id in compromised,
                attack_mode=attack_mode,
            )
        )

    task_specs = []
    balanced_roles = [task_id % roles for task_id in range(tasks)]
    task_order = sorted(
        range(tasks),
        key=lambda task_id: _u01(seed, "task-order", task_id),
    )
    role_order = [balanced_roles[task_id] for task_id in task_order]
    for task_id in range(tasks):
        risk_roll = _u01(seed, "risk", task_id)
        risk_tier = 3 if risk_roll < 0.15 else 2 if risk_roll < 0.48 else 1
        required_horizon = 3 + _choice_index(seed, 12, "required", task_id)
        task_specs.append(
            TaskSpec(
                task_id=task_id,
                role=role_order[task_id],
                required_horizon=required_horizon,
                evidence_epoch=task_id // max(1, agents // 3),
                risk_tier=risk_tier,
            )
        )
    return population, task_specs


def _reported_horizon(
    agent: AgentSpec,
    task: TaskSpec,
    *,
    seed: int,
    monitor_noise: float,
) -> int:
    if agent.attack_mode == "consistent_collusion":
        return max(agent.coherence_horizon, task.required_horizon + 2)
    noise_roll = _u01(seed, "monitor-noise", task.task_id, agent.agent_id)
    if noise_roll < monitor_noise / 2.0:
        return max(1, agent.coherence_horizon - 3)
    if noise_roll < monitor_noise:
        return agent.coherence_horizon + 3
    return agent.coherence_horizon


def _contract_check(
    agent: AgentSpec,
    task: TaskSpec,
    *,
    seed: int,
    margin: int,
    monitor_noise: float,
    stale_evidence_fraction: float,
) -> tuple[bool, bool]:
    """Return (accepted, false_rejection_of_honest_eligible_agent)."""
    true_eligible = (
        not agent.failed
        and not agent.compromised
        and agent.role == task.role
        and agent.coherence_horizon >= task.required_horizon
    )
    if agent.failed:
        return False, False
    if agent.attack_mode == "malformed_contract":
        return False, False
    if agent.attack_mode == "stale_lineage":
        return False, False
    if (
        agent.attack_mode == "honest"
        and _u01(seed, "stale", task.task_id, agent.agent_id)
        < stale_evidence_fraction
    ):
        return False, true_eligible
    reported_horizon = _reported_horizon(
        agent,
        task,
        seed=seed,
        monitor_noise=monitor_noise,
    )
    accepted = (
        agent.role == task.role
        and reported_horizon >= task.required_horizon + margin
    )
    return accepted, bool(true_eligible and not accepted)


def _attempt(
    agent: AgentSpec,
    task: TaskSpec,
    *,
    seed: int,
    attempt_index: int,
) -> tuple[bool, bool]:
    if agent.failed:
        return False, False
    horizon_ok = agent.coherence_horizon >= task.required_horizon
    probability = agent.skill * (1.0 if horizon_ok else 0.43)
    if agent.compromised:
        probability *= 0.24
    raw_success = (
        _u01(seed, "success", task.task_id, agent.agent_id, attempt_index)
        < probability
    )
    violation_probability = 0.015 * task.risk_tier
    if not horizon_ok:
        violation_probability += 0.48
    if agent.compromised:
        violation_probability += (
            0.58 if agent.attack_mode == "consistent_collusion" else 0.42
        )
    violation = raw_success and (
        _u01(seed, "violation", task.task_id, agent.agent_id, attempt_index)
        < min(0.98, violation_probability)
    )
    return raw_success, violation


def _strategy_entropy(counts: dict[int, int]) -> float:
    total = sum(counts.values())
    if total <= 0:
        return 0.0
    entropy = -sum(
        (count / total) * math.log(count / total)
        for count in counts.values()
        if count > 0
    )
    return entropy / math.log(8.0)


def run_protocol(
    *,
    seed: int,
    population: list[AgentSpec],
    tasks: list[TaskSpec],
    condition: Condition,
    architecture: str,
    margin: int,
    neighborhood: int = 10,
) -> TrialResult:
    if architecture not in {"peer_reputation", "constraint_contract"}:
        raise ValueError(f"unsupported architecture: {architecture}")
    by_role: dict[int, list[AgentSpec]] = {}
    for agent in population:
        by_role.setdefault(agent.role, []).append(agent)
    reputation = {agent.agent_id: 1.0 for agent in population}
    messages = len(population)
    contract_fields = 0
    safe_completed = 0
    raw_completed = 0
    violations = 0
    compromised_assignments = 0
    false_rejections = 0
    honest_eligible_bids = 0
    unavailable_tasks = 0
    strategy_counts: dict[int, int] = {}

    for task in tasks:
        role_pool = by_role[task.role]
        start = _choice_index(seed, len(role_pool), "start", task.task_id)
        candidates = [
            role_pool[(start + offset) % len(role_pool)]
            for offset in range(min(neighborhood, len(role_pool)))
        ]
        messages += 1  # task announcement
        ranked = sorted(
            candidates,
            key=lambda agent: (
                -(agent.skill * reputation[agent.agent_id]),
                agent.agent_id,
            ),
        )
        accepted: list[AgentSpec] = []
        for agent in ranked:
            messages += 1  # bid; contract fields are piggybacked when enabled
            if architecture == "constraint_contract":
                contract_fields += 6
                if (
                    not agent.failed
                    and not agent.compromised
                    and agent.coherence_horizon >= task.required_horizon
                ):
                    honest_eligible_bids += 1
                contract_ok, false_rejection = _contract_check(
                    agent,
                    task,
                    seed=seed,
                    margin=margin,
                    monitor_noise=condition.monitor_noise,
                    stale_evidence_fraction=condition.stale_evidence_fraction,
                )
                false_rejections += int(false_rejection)
                if not contract_ok:
                    continue
            elif agent.failed:
                continue
            accepted.append(agent)

        if not accepted:
            unavailable_tasks += 1
            messages += 1  # local no-bid/decomposition notice
            continue

        task_finished = False
        for attempt_index, agent in enumerate(accepted):
            messages += 2  # commitment and execution result
            raw_success, violation = _attempt(
                agent,
                task,
                seed=seed,
                attempt_index=attempt_index,
            )
            if raw_success:
                raw_completed += 1
                compromised_assignments += int(agent.compromised)
                if violation:
                    violations += 1
                else:
                    safe_completed += 1
                    strategy_counts[agent.strategy] = (
                        strategy_counts.get(agent.strategy, 0) + 1
                    )
                reputation[agent.agent_id] = min(
                    1.0,
                    reputation[agent.agent_id] + (0.02 if not violation else 0.0),
                )
                task_finished = True
                break
            reputation[agent.agent_id] = max(
                0.05,
                reputation[agent.agent_id] - (0.34 if agent.compromised else 0.14),
            )
            messages += 2  # same challenge and re-auction cost for both methods
        if not task_finished:
            continue

    return TrialResult(
        condition=condition.name,
        architecture=architecture,
        seed=seed,
        agents=len(population),
        tasks=len(tasks),
        margin=margin,
        safe_completion_rate=safe_completed / len(tasks),
        raw_completion_rate=raw_completed / len(tasks),
        constraint_violation_rate=violations / max(1, raw_completed),
        compromised_assignment_rate=compromised_assignments
        / max(1, raw_completed),
        messages_per_safe_completion=messages / max(1, safe_completed),
        messages=messages,
        contract_fields_transmitted=contract_fields,
        false_rejection_rate=false_rejections / max(1, honest_eligible_bids),
        strategy_entropy=_strategy_entropy(strategy_counts),
        unavailable_task_rate=unavailable_tasks / len(tasks),
    )


def _objective(result: TrialResult) -> float:
    return (
        1.00 * result.safe_completion_rate
        - 0.90 * result.constraint_violation_rate
        - 0.20 * result.false_rejection_rate
        + 0.08 * result.strategy_entropy
        - 0.002 * result.messages_per_safe_completion
    )


def select_margin(
    *,
    seed_base: int,
    scenarios: int,
    agents: int,
    tasks: int,
    roles: int,
) -> dict[str, Any]:
    development_conditions = CONDITIONS[:2]
    candidates = []
    for margin in (0, 1, 2):
        objectives = []
        for condition_index, condition in enumerate(development_conditions):
            for scenario in range(scenarios):
                seed = seed_base + condition_index * 1_000_000 + scenario * 10_007
                population, task_specs = generate_trial(
                    seed=seed,
                    agents=agents,
                    tasks=tasks,
                    roles=roles,
                    condition=condition,
                )
                result = run_protocol(
                    seed=seed,
                    population=population,
                    tasks=task_specs,
                    condition=condition,
                    architecture="constraint_contract",
                    margin=margin,
                )
                objectives.append(_objective(result))
        candidates.append(
            {
                "margin": margin,
                "mean_objective": mean(objectives),
                "minimum_objective": min(objectives),
            }
        )
    selected = max(
        candidates,
        key=lambda row: (
            row["mean_objective"],
            row["minimum_objective"],
            -row["margin"],
        ),
    )
    return {
        "selected_margin": selected["margin"],
        "candidate_results": candidates,
        "selection_rule": (
            "maximize mean development objective across benign and independent "
            "10% compromise; objective rewards safe completion and strategy "
            "entropy while penalizing violations, false rejection, and messages"
        ),
    }


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _paired_summary(
    rows: list[TrialResult],
    *,
    metric: str,
    higher_is_better: bool,
) -> dict[str, Any]:
    by_seed: dict[int, dict[str, TrialResult]] = {}
    for row in rows:
        by_seed.setdefault(row.seed, {})[row.architecture] = row
    deltas = [
        getattr(pair["constraint_contract"], metric)
        - getattr(pair["peer_reputation"], metric)
        for _, pair in sorted(by_seed.items())
    ]
    rng = random.Random(8_117 + sum(ord(char) for char in metric))
    boot_means = []
    for _ in range(10_000):
        boot_means.append(mean(deltas[rng.randrange(len(deltas))] for _ in deltas))
    favorable = [delta > 0 if higher_is_better else delta < 0 for delta in deltas]
    return {
        "mean_delta": mean(deltas),
        "bootstrap_95pct_interval": [
            _percentile(boot_means, 0.025),
            _percentile(boot_means, 0.975),
        ],
        "favorable_scenario_fraction": mean(float(value) for value in favorable),
        "zero_delta_scenario_fraction": mean(float(value == 0) for value in deltas),
        "scenario_count": len(deltas),
    }


def _aggregate(rows: list[TrialResult]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    metrics = (
        "safe_completion_rate",
        "raw_completion_rate",
        "constraint_violation_rate",
        "compromised_assignment_rate",
        "messages_per_safe_completion",
        "false_rejection_rate",
        "strategy_entropy",
        "unavailable_task_rate",
    )
    for architecture in ("peer_reputation", "constraint_contract"):
        subset = [row for row in rows if row.architecture == architecture]
        output[architecture] = {
            metric: mean(getattr(row, metric) for row in subset)
            for metric in metrics
        }
    output["paired"] = {
        "safe_completion_rate": _paired_summary(
            rows,
            metric="safe_completion_rate",
            higher_is_better=True,
        ),
        "constraint_violation_rate": _paired_summary(
            rows,
            metric="constraint_violation_rate",
            higher_is_better=False,
        ),
        "compromised_assignment_rate": _paired_summary(
            rows,
            metric="compromised_assignment_rate",
            higher_is_better=False,
        ),
        "messages_per_safe_completion": _paired_summary(
            rows,
            metric="messages_per_safe_completion",
            higher_is_better=False,
        ),
        "strategy_entropy": _paired_summary(
            rows,
            metric="strategy_entropy",
            higher_is_better=True,
        ),
    }
    return output


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
    validation_scenarios: int = 30,
    agents: int = 500,
    tasks: int = 1200,
    roles: int = 12,
    development_seed_base: int = 3_100_000,
    validation_seed_base: int = 3_900_000,
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    selection = select_margin(
        seed_base=development_seed_base,
        scenarios=development_scenarios,
        agents=agents,
        tasks=tasks,
        roles=roles,
    )
    margin = int(selection["selected_margin"])
    all_rows: list[TrialResult] = []
    condition_results: dict[str, Any] = {}
    for condition_index, condition in enumerate(CONDITIONS):
        rows: list[TrialResult] = []
        for scenario in range(validation_scenarios):
            seed = (
                validation_seed_base
                + condition_index * 1_000_000
                + scenario * 10_007
            )
            population, task_specs = generate_trial(
                seed=seed,
                agents=agents,
                tasks=tasks,
                roles=roles,
                condition=condition,
            )
            for architecture in ("peer_reputation", "constraint_contract"):
                rows.append(
                    run_protocol(
                        seed=seed,
                        population=population,
                        tasks=task_specs,
                        condition=condition,
                        architecture=architecture,
                        margin=margin,
                    )
                )
        all_rows.extend(rows)
        condition_results[condition.name] = {
            "configuration": asdict(condition),
            "metrics": _aggregate(rows),
        }

    summary = {
        "schema": "dice_constraint_contract_generated_benchmark_v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "development": {
            "scenarios_per_condition": development_scenarios,
            "seed_base": development_seed_base,
            "conditions": [condition.name for condition in CONDITIONS[:2]],
            **selection,
        },
        "validation": {
            "scenarios_per_condition": validation_scenarios,
            "seed_base": validation_seed_base,
            "agents": agents,
            "tasks": tasks,
            "roles": roles,
            "conditions": condition_results,
        },
        "platform": platform.platform(),
        "python": platform.python_version(),
        "limitations": [
            "No language-model inference, tools, memory systems, or TA3 adaptor.",
            "Role, horizon, evidence, attack, and monitor behavior are generated assumptions.",
            "A locally consistent forged contract can pass deterministic field checks.",
            "Message sizes and cryptographic computation costs are not measured.",
            "Strategy entropy is a generated proxy, not cognitive-agility evidence.",
        ],
    }

    trial_path = out_dir / "trials.csv"
    with trial_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(all_rows[0])))
        writer.writeheader()
        writer.writerows(asdict(row) for row in all_rows)
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# DICE Constraint-Carrying Commitment Scorecard",
        "",
        f"Evidence boundary: {EVIDENCE_BOUNDARY}",
        "",
        "## Development Gate",
        "",
        f"- Frozen coherence-horizon margin: {margin}",
        f"- Development scenarios per condition: {development_scenarios}",
        "- Development conditions: benign and independent 10% compromise.",
        "",
        "## Disjoint Validation",
        "",
        "| Condition | Peer safe completion | Contract safe completion | Safe-completion delta [95% CI] | Violation delta | Message-cost delta | False rejection |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for condition in CONDITIONS:
        metrics = condition_results[condition.name]["metrics"]
        baseline = metrics["peer_reputation"]
        contract = metrics["constraint_contract"]
        paired = metrics["paired"]
        safe = paired["safe_completion_rate"]
        safe_ci = safe["bootstrap_95pct_interval"]
        lines.append(
            f"| {condition.name} | "
            f"{baseline['safe_completion_rate']:.3f} | "
            f"{contract['safe_completion_rate']:.3f} | "
            f"{safe['mean_delta']:+.3f} "
            f"[{safe_ci[0]:+.3f}, {safe_ci[1]:+.3f}] | "
            f"{paired['constraint_violation_rate']['mean_delta']:+.3f} | "
            f"{paired['messages_per_safe_completion']['mean_delta']:+.2f} | "
            f"{contract['false_rejection_rate']:.3f} |"
        )
    lines.extend(
        [
            "",
            "Negative violation and message-cost deltas favor the contract method. "
            "False rejection is measured only for generated honest agents whose true "
            "horizon satisfies the task.",
            "",
            "## Interpretation",
            "",
            "The contract carries six modeled fields in each existing bid message; the "
            "field count is reported separately and is not a byte or latency claim. "
            "Deterministic checks reject malformed or stale contracts, but locally "
            "consistent collusive forgeries can pass. High-collusion and monitor-shift "
            "conditions therefore test a known boundary rather than assume certificates "
            "solve semantic deception.",
            "",
        ]
    )
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text("\n".join(lines), encoding="utf-8")

    manifest = {
        "schema": "dice_constraint_contract_manifest_v1",
        "generated_utc": summary["generated_utc"],
        "files": {
            path.name: {"bytes": path.stat().st_size, "sha256": _sha256(path)}
            for path in (trial_path, summary_path, scorecard_path)
        },
    }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--development-scenarios", type=int, default=12)
    parser.add_argument("--validation-scenarios", type=int, default=30)
    parser.add_argument("--agents", type=int, default=500)
    parser.add_argument("--tasks", type=int, default=1200)
    args = parser.parse_args()
    summary = run_suite(
        out_dir=args.out,
        development_scenarios=max(3, args.development_scenarios),
        validation_scenarios=max(3, args.validation_scenarios),
        agents=max(60, args.agents),
        tasks=max(120, args.tasks),
    )
    print(
        json.dumps(
            {
                "selected_margin": summary["development"]["selected_margin"],
                "conditions": {
                    name: value["metrics"]["paired"]["safe_completion_rate"]
                    for name, value in summary["validation"]["conditions"].items()
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
