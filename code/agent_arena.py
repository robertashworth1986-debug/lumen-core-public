"""LumenCore Agent Arena V5: deterministic adversarial multi-agent validation.

This module is a bounded proof-to-pilot sub-harness. Agents can propose controls,
but they cannot alter the locked scenario, baseline, selection rule, holdout split,
referee physics, score function, custody chain, or evidence boundary.

Evidence produced by the reference arena is synthetic/replay software evidence.
It is not field validation, certification, customer-savings proof, or endorsement.
"""
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import platform
import random
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any, Mapping, Protocol, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "agent_arena_v5.json"
DEFAULT_OUT = ROOT / "out" / "agent_arena"
SCHEMA = "lumencore.agent_arena.v5"
MANIFEST_SCHEMA = "lumencore.agent_arena.manifest.v3"
RECEIPT_SCHEMA = "lumencore.agent_arena.execution_receipt.v2"
EVIDENCE_BOUNDARY = (
    "Synthetic/replay software evidence only. The Arena evaluates bounded agent "
    "proposals inside a deterministic abstract infrastructure model under predeclared "
    "selection, holdout, scoring, adversarial, and custody rules. It can establish "
    "software behavior, replay reproducibility, provenance, and performance inside "
    "the declared model only; it does not establish field performance, production "
    "safety, customer savings, external validation, certification, agency endorsement, "
    "or universal superiority."
)
CONTROLS = ("routing", "cooling", "redundancy", "reserve")
CONSTRAINTS = (
    "service_rate_min",
    "latency_index_max",
    "energy_index_max",
    "thermal_index_max",
    "resilience_index_min",
)
WEIGHTS = (
    "service_rate",
    "resilience_index",
    "latency_index",
    "energy_index",
    "thermal_index",
    "violation_penalty",
)
REQUIRED_STAGES = {"v2", "v3", "v4", "v5"}


class ProposalProvider(Protocol):
    def __call__(
        self,
        role: str,
        observation: Mapping[str, Any],
        bounds: Mapping[str, tuple[float, float]],
    ) -> Mapping[str, float]: ...


@dataclass(frozen=True)
class ControlPlan:
    routing: float = 1.0
    cooling: float = 0.20
    redundancy: float = 1.0
    reserve: float = 0.10


@dataclass(frozen=True)
class FloorSpec:
    floor_id: str
    label: str
    demand: float
    capacity_loss: float
    ambient_heat: float
    failure_rate: float
    telemetry_noise: float
    attack_mode: str
    attack_strength: float
    compromised_roles: tuple[str, ...]
    dropout_roles: tuple[str, ...]
    holdout: bool = False


@dataclass(frozen=True)
class Metrics:
    service_rate: float
    latency_index: float
    energy_index: float
    thermal_index: float
    resilience_index: float
    violations: int
    score: float


@dataclass(frozen=True)
class FloorResult:
    architecture: str
    profile: str
    seed: int
    floor_id: str
    attack_mode: str
    holdout: bool
    plan: ControlPlan
    metrics: Metrics


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: Any, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _git_state() -> tuple[str, str]:
    """Return the committed source identity and reject dirty executions.

    A HEAD hash is meaningful custody only when the working tree and index match
    that commit. Ignored output files are intentionally excluded by Git.
    """
    try:
        status = subprocess.check_output(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        if status:
            raise ValueError("arena execution requires a clean Git worktree")
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        tree = subprocess.check_output(
            ["git", "rev-parse", "HEAD^{tree}"],
            cwd=ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        return commit, tree
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("arena execution requires an identifiable Git commit") from exc


def _engine_sha256() -> str:
    return sha256_file(Path(__file__))


def _validate_exact_keys(mapping: Mapping[str, Any], expected: Sequence[str], name: str) -> None:
    if set(mapping) != set(expected):
        raise ValueError(f"{name} lock mismatch")


def _validate_config(cfg: dict[str, Any]) -> dict[str, Any]:
    if cfg.get("schema") != SCHEMA:
        raise ValueError("unexpected scenario schema")
    if cfg.get("evidence_boundary") != EVIDENCE_BOUNDARY:
        raise ValueError("evidence boundary mismatch")
    if set(cfg.get("capability_stages", {})) != REQUIRED_STAGES:
        raise ValueError("capability stage lock mismatch")
    _validate_exact_keys(cfg.get("control_bounds", {}), CONTROLS, "control bounds")
    for name, pair in cfg["control_bounds"].items():
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"invalid bounds for {name}")
        low, high = map(float, pair)
        if not math.isfinite(low) or not math.isfinite(high) or low > high:
            raise ValueError(f"invalid bounds for {name}")
    _validate_exact_keys(cfg.get("constraints", {}), CONSTRAINTS, "constraint")
    _validate_exact_keys(cfg.get("score_weights", {}), WEIGHTS, "score-weight")
    for name, raw in cfg["constraints"].items():
        value = _finite(raw, f"constraints.{name}")
        if value < 0.0 or (name.endswith("_min") and value > 1.0):
            raise ValueError(f"invalid constraint: {name}")
    for name, raw in cfg["score_weights"].items():
        if _finite(raw, f"score_weights.{name}") < 0.0:
            raise ValueError(f"score weight must be nonnegative: {name}")
    _validate_exact_keys(cfg.get("baseline_plan", {}), CONTROLS, "baseline plan")
    roles = cfg.get("agent_roles", [])
    if len(roles) < 5 or len(set(roles)) != len(roles):
        raise ValueError("agent roles must be unique and contain at least five entries")
    selection_seeds = cfg.get("selection_seeds", [])
    holdout_seeds = cfg.get("holdout_seeds", [])
    if not selection_seeds or not holdout_seeds:
        raise ValueError("selection and holdout seeds are required")
    if any(not isinstance(x, int) for x in selection_seeds + holdout_seeds):
        raise ValueError("all seeds must be integers")
    if len(set(selection_seeds + holdout_seeds)) != len(selection_seeds) + len(holdout_seeds):
        raise ValueError("selection and holdout seeds must be unique and disjoint")
    floors = cfg.get("floors", [])
    ids = [str(x["floor_id"]) for x in floors]
    if len(floors) < 4 or len(ids) != len(set(ids)):
        raise ValueError("floors must be unique and contain at least four entries")
    if not any(bool(x.get("holdout")) for x in floors):
        raise ValueError("at least one holdout floor is required")
    if not any(not bool(x.get("holdout")) for x in floors):
        raise ValueError("at least one selection floor is required")
    profiles = cfg.get("candidate_profiles", {})
    if len(profiles) < 3:
        raise ValueError("at least three candidate profiles are required")
    for profile_name, profile in profiles.items():
        required = {
            "trim_threshold",
            "deviation_sensitivity",
            "safety_margin",
            "reserve_bias",
            "red_team",
        }
        if set(profile) != required:
            raise ValueError(f"candidate profile lock mismatch: {profile_name}")
        for key in required - {"red_team"}:
            _finite(profile[key], f"candidate_profiles.{profile_name}.{key}")
        if not isinstance(profile["red_team"], bool):
            raise ValueError(f"candidate_profiles.{profile_name}.red_team must be boolean")
    selection = cfg.get("champion_selection", {})
    if set(selection) != {"mean_score_weight", "cvar10_weight", "violation_weight"}:
        raise ValueError("champion selection lock mismatch")
    oracle_grid = cfg.get("oracle_grid", {})
    _validate_exact_keys(oracle_grid, CONTROLS, "oracle grid")
    for name, points in oracle_grid.items():
        if not isinstance(points, int) or not 2 <= points <= 12:
            raise ValueError(f"oracle_grid.{name} must be an integer in [2, 12]")
    statistics = cfg.get("statistics", {})
    if set(statistics) != {"bootstrap_samples", "confidence", "bootstrap_seed"}:
        raise ValueError("statistics lock mismatch")
    if int(statistics["bootstrap_samples"]) < 200:
        raise ValueError("bootstrap_samples must be at least 200")
    confidence = float(statistics["confidence"])
    if not 0.80 <= confidence < 1.0:
        raise ValueError("confidence must be in [0.80, 1.0)")
    provider = cfg.get("provider_descriptor", {})
    if not isinstance(provider, dict) or not provider.get("provider_id"):
        raise ValueError("provider descriptor must include provider_id")
    gate = cfg.get("acceptance_gate", {})
    if set(gate) != {"min_score_mean", "max_constraint_violations_total"}:
        raise ValueError("acceptance gate lock mismatch")
    _finite(gate["min_score_mean"], "acceptance_gate.min_score_mean")
    if not isinstance(gate["max_constraint_violations_total"], int) or gate["max_constraint_violations_total"] < 0:
        raise ValueError("acceptance_gate.max_constraint_violations_total must be a nonnegative integer")
    allowed_attacks = {
        "none",
        "underreport_demand",
        "hide_capacity_loss",
        "heat_blindness",
        "hide_failures",
        "byzantine_controls",
        "mixed_cascade",
    }
    role_set = set(roles)
    for index, floor in enumerate(floors):
        if not isinstance(floor.get("holdout"), bool):
            raise ValueError(f"floors[{index}].holdout must be boolean")
        attack = floor.get("attack_mode", "none")
        if attack not in allowed_attacks:
            raise ValueError(f"floors[{index}].attack_mode is not declared")
        strength = _finite(floor.get("attack_strength", 0.0), f"floors[{index}].attack_strength")
        if not 0.0 <= strength <= 0.95:
            raise ValueError(f"floors[{index}].attack_strength must be in [0, 0.95]")
        compromised = floor.get("compromised_roles", [])
        dropped = floor.get("dropout_roles", [])
        if len(compromised) != len(set(compromised)) or len(dropped) != len(set(dropped)):
            raise ValueError(f"floors[{index}] role lists must be unique")
        if not set(compromised).issubset(role_set) or not set(dropped).issubset(role_set):
            raise ValueError(f"floors[{index}] references an undeclared role")
        if set(compromised) & set(dropped):
            raise ValueError(f"floors[{index}] cannot compromise and drop the same role")
    return cfg


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return _validate_config(json.loads(path.read_text(encoding="utf-8")))


def _bounds(cfg: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    return {k: (float(v[0]), float(v[1])) for k, v in cfg["control_bounds"].items()}


def _floor_from_config(x: Mapping[str, Any]) -> FloorSpec:
    return FloorSpec(
        floor_id=str(x["floor_id"]),
        label=str(x["label"]),
        demand=_finite(x["demand"], "demand"),
        capacity_loss=_finite(x["capacity_loss"], "capacity_loss"),
        ambient_heat=_finite(x["ambient_heat"], "ambient_heat"),
        failure_rate=_finite(x["failure_rate"], "failure_rate"),
        telemetry_noise=_finite(x["telemetry_noise"], "telemetry_noise"),
        attack_mode=str(x.get("attack_mode", "none")),
        attack_strength=_finite(x.get("attack_strength", 0.0), "attack_strength"),
        compromised_roles=tuple(str(r) for r in x.get("compromised_roles", [])),
        dropout_roles=tuple(str(r) for r in x.get("dropout_roles", [])),
        holdout=bool(x.get("holdout")),
    )


def _plan(values: Mapping[str, Any], bounds: Mapping[str, tuple[float, float]]) -> ControlPlan:
    unknown = set(values) - set(CONTROLS)
    if unknown:
        raise ValueError(f"plan contains undeclared controls: {sorted(unknown)}")
    base = asdict(ControlPlan())
    for name in CONTROLS:
        low, high = bounds[name]
        base[name] = clamp(_finite(values.get(name, base[name]), name), low, high)
    return ControlPlan(**base)


def baseline_plan(cfg: Mapping[str, Any]) -> ControlPlan:
    return _plan(cfg["baseline_plan"], _bounds(cfg))


def _role_seed(seed: int, floor_id: str, role: str) -> int:
    digest = sha256_text(f"{seed}|{floor_id}|{role}")
    return int(digest[:16], 16)


def observe_floor(floor: FloorSpec, seed: int, role: str) -> dict[str, Any]:
    rng = random.Random(_role_seed(seed, floor.floor_id, role))
    n = floor.telemetry_noise

    def sensed(value: float) -> float:
        return value * (1.0 + rng.uniform(-n, n))

    observation = {
        "demand": sensed(floor.demand),
        "capacity_loss": clamp(sensed(floor.capacity_loss), 0.0, 0.95),
        "ambient_heat": max(0.0, sensed(floor.ambient_heat)),
        "failure_rate": clamp(sensed(floor.failure_rate), 0.0, 0.95),
        "telemetry_noise": n,
    }
    if role not in floor.compromised_roles:
        return observation
    strength = floor.attack_strength
    if floor.attack_mode in {"underreport_demand", "mixed_cascade"}:
        observation["demand"] *= 1.0 - strength
    if floor.attack_mode in {"hide_capacity_loss", "mixed_cascade"}:
        observation["capacity_loss"] *= 1.0 - strength
    if floor.attack_mode in {"heat_blindness", "mixed_cascade"}:
        observation["ambient_heat"] *= 1.0 - strength
    if floor.attack_mode in {"hide_failures", "mixed_cascade"}:
        observation["failure_rate"] *= 1.0 - strength
    return observation


def deterministic_provider(
    role: str,
    observation: Mapping[str, Any],
    bounds: Mapping[str, tuple[float, float]],
) -> Mapping[str, float]:
    demand = float(observation["demand"])
    loss = float(observation["capacity_loss"])
    heat = float(observation["ambient_heat"])
    failure = float(observation["failure_rate"])
    noise = float(observation["telemetry_noise"])
    pressure = max(0.0, demand / 100.0 - 0.70)
    table = {
        "router": {"routing": 1.0 + 1.15 * pressure + 0.85 * loss},
        "thermal": {"cooling": 0.18 + 0.75 * pressure + 1.00 * heat},
        "resilience": {
            "redundancy": 1.0 + 7.5 * failure + 1.9 * loss,
            "reserve": 0.10 + 2.8 * failure + 0.80 * loss,
        },
        "efficiency": {
            "routing": 1.0 + 0.58 * pressure,
            "cooling": 0.14 + 0.42 * pressure + 0.60 * heat,
            "reserve": 0.08 + 0.38 * pressure,
        },
        "telemetry_skeptic": {
            "cooling": 0.18 + 1.25 * noise,
            "reserve": 0.10 + 1.75 * noise,
            "redundancy": 1.0 + 3.2 * noise,
        },
        "anomaly_hunter": {
            "routing": 1.0 + 0.75 * pressure + 0.45 * loss,
            "reserve": 0.11 + 1.30 * noise + 1.20 * failure,
        },
        "planner": {
            "routing": 1.0 + 0.80 * pressure + 0.45 * loss,
            "cooling": 0.16 + 0.50 * pressure + 0.70 * heat,
            "redundancy": 1.0 + 4.0 * failure + 1.1 * loss,
            "reserve": 0.10 + 1.5 * failure + 0.45 * loss + 0.5 * noise,
        },
    }
    if role not in table:
        raise ValueError(f"unknown role: {role}")
    return table[role]


def sanitize_proposal(
    proposal: Mapping[str, Any],
    bounds: Mapping[str, tuple[float, float]],
) -> dict[str, float]:
    unknown = set(proposal) - set(bounds)
    if unknown:
        raise ValueError(f"proposal contains undeclared controls: {sorted(unknown)}")
    out: dict[str, float] = {}
    for name, raw in proposal.items():
        low, high = bounds[name]
        out[name] = clamp(_finite(raw, f"proposal.{name}"), low, high)
    return out


def _corrupt_proposal(
    proposal: Mapping[str, float],
    floor: FloorSpec,
    role: str,
    bounds: Mapping[str, tuple[float, float]],
) -> dict[str, float]:
    result = dict(proposal)
    if role not in floor.compromised_roles:
        return result
    if floor.attack_mode not in {"byzantine_controls", "mixed_cascade"}:
        return result
    strength = floor.attack_strength
    for name, value in list(result.items()):
        low, _ = bounds[name]
        result[name] = low + (value - low) * (1.0 - strength)
    return result


def _weighted_median(values: list[tuple[float, float]]) -> float:
    ordered = sorted(values, key=lambda item: item[0])
    total = sum(max(0.0, weight) for _, weight in ordered)
    if total <= 0:
        return median(value for value, _ in ordered)
    threshold = total / 2.0
    running = 0.0
    for value, weight in ordered:
        running += max(0.0, weight)
        if running >= threshold:
            return value
    return ordered[-1][0]


def _proposal_trust(
    proposals: Mapping[str, Mapping[str, float]],
    bounds: Mapping[str, tuple[float, float]],
    sensitivity: float,
) -> dict[str, float]:
    medians: dict[str, float] = {}
    for control in CONTROLS:
        xs = [p[control] for p in proposals.values() if control in p]
        if xs:
            medians[control] = median(xs)
    trust: dict[str, float] = {}
    for role, proposal in proposals.items():
        deviations: list[float] = []
        for control, value in proposal.items():
            low, high = bounds[control]
            span = max(high - low, 1e-9)
            deviations.append(abs(value - medians[control]) / span)
        disagreement = mean(deviations) if deviations else 0.0
        trust[role] = clamp(1.0 - sensitivity * disagreement, 0.0, 1.0)
    return trust


def synthesize_plan(
    proposals: Mapping[str, Mapping[str, float]],
    bounds: Mapping[str, tuple[float, float]],
    profile: Mapping[str, Any],
) -> tuple[ControlPlan, dict[str, float], list[str]]:
    trust = _proposal_trust(
        proposals,
        bounds,
        float(profile["deviation_sensitivity"]),
    )
    threshold = float(profile["trim_threshold"])
    accepted = [role for role, value in trust.items() if value >= threshold]
    if not accepted:
        accepted = sorted(trust, key=lambda role: (-trust[role], role))[:1]
    values: dict[str, float] = {}
    defaults = asdict(ControlPlan())
    for control in CONTROLS:
        candidates = [
            (proposals[role][control], trust[role])
            for role in accepted
            if control in proposals[role]
        ]
        values[control] = _weighted_median(candidates) if candidates else defaults[control]
    safety = float(profile["safety_margin"])
    reserve_bias = float(profile["reserve_bias"])
    values["routing"] += safety * 0.55
    values["cooling"] += safety * 0.65
    values["redundancy"] += safety * 1.8
    values["reserve"] += safety + reserve_bias
    return _plan(values, bounds), trust, sorted(accepted)


def _robust_observation(observations: Mapping[str, Mapping[str, Any]]) -> dict[str, float]:
    return {
        key: median(float(obs[key]) for obs in observations.values())
        for key in ("demand", "capacity_loss", "ambient_heat", "failure_rate", "telemetry_noise")
    }


def red_team_challenge(
    plan: ControlPlan,
    observations: Mapping[str, Mapping[str, Any]],
    bounds: Mapping[str, tuple[float, float]],
    enabled: bool,
) -> tuple[ControlPlan, list[str]]:
    if not enabled:
        return plan, []
    o = _robust_observation(observations)
    values = asdict(plan)
    findings: list[str] = []
    if o["demand"] > 92 and plan.routing < 1.22:
        findings.append("routing_underprovisioned_for_robust_demand")
        values["routing"] = 1.22
    if o["ambient_heat"] > 0.10 and plan.cooling < 0.31:
        findings.append("cooling_underprovisioned_for_robust_heat")
        values["cooling"] = 0.31
    if o["failure_rate"] + o["capacity_loss"] > 0.12 and plan.redundancy < 1.45:
        findings.append("redundancy_underprovisioned_for_robust_faults")
        values["redundancy"] = 1.45
    if o["telemetry_noise"] > 0.08 and plan.reserve < 0.19:
        findings.append("reserve_underprovisioned_for_telemetry_uncertainty")
        values["reserve"] = 0.19
    return _plan(values, bounds), findings


def evaluate_plan(
    floor: FloorSpec,
    plan: ControlPlan,
    constraints: Mapping[str, float],
    weights: Mapping[str, float],
) -> Metrics:
    capacity = (
        100.0
        * max(0.05, 1.0 - floor.capacity_loss)
        * (1.0 + 0.30 * (plan.routing - 1.0))
        * (1.0 + 0.10 * max(0.0, plan.redundancy - 1.0))
        * (1.0 + 0.16 * plan.reserve)
    )
    ratio = floor.demand / max(capacity, 1e-9)
    service = clamp(capacity / max(floor.demand, 1e-9), 0.0, 1.0)
    latency = max(0.0, ratio * ratio / max(plan.routing, 0.1))
    energy = max(
        0.0,
        (floor.demand / 100.0)
        * (
            1.0
            + 0.07 * max(0.0, plan.routing - 1.0)
            + 0.11 * max(0.0, plan.redundancy - 1.0)
            + 0.34 * plan.cooling
            + 0.08 * plan.reserve
        ),
    )
    thermal = max(
        0.0,
        (floor.demand / 100.0) * (1.0 + floor.ambient_heat)
        - 0.80 * plan.cooling
        + 0.05 * max(0.0, plan.redundancy - 1.0),
    )
    resilience = clamp(
        1.0
        - 1.55 * floor.failure_rate / max(plan.redundancy, 1.0)
        - 0.28 * floor.capacity_loss
        + 0.22 * plan.reserve
        + 0.035 * max(0.0, plan.redundancy - 1.0),
        0.0,
        1.0,
    )
    violations = int(
        sum(
            (
                service < float(constraints["service_rate_min"]),
                latency > float(constraints["latency_index_max"]),
                energy > float(constraints["energy_index_max"]),
                thermal > float(constraints["thermal_index_max"]),
                resilience < float(constraints["resilience_index_min"]),
            )
        )
    )
    score = (
        float(weights["service_rate"]) * service
        + float(weights["resilience_index"]) * resilience
        - float(weights["latency_index"]) * latency
        - float(weights["energy_index"]) * energy
        - float(weights["thermal_index"]) * thermal
        - float(weights["violation_penalty"]) * violations
    )
    return Metrics(service, latency, energy, thermal, resilience, violations, score)


def run_floor(
    floor: FloorSpec,
    seed: int,
    cfg: Mapping[str, Any],
    profile_name: str,
    provider: ProposalProvider = deterministic_provider,
) -> tuple[FloorResult, dict[str, Any]]:
    bounds = _bounds(cfg)
    profile = cfg["candidate_profiles"][profile_name]
    roles = list(cfg["agent_roles"])
    observations: dict[str, dict[str, Any]] = {}
    proposals: dict[str, dict[str, float]] = {}
    dropped: list[str] = []
    for role in roles:
        if role in floor.dropout_roles:
            dropped.append(role)
            continue
        observation = observe_floor(floor, seed, role)
        observations[role] = observation
        proposal = sanitize_proposal(provider(role, observation, bounds), bounds)
        proposals[role] = _corrupt_proposal(proposal, floor, role, bounds)
    if not proposals:
        raise ValueError("all agent roles were dropped")
    synthesized, trust, accepted = synthesize_plan(proposals, bounds, profile)
    candidate, findings = red_team_challenge(
        synthesized,
        observations,
        bounds,
        bool(profile["red_team"]),
    )
    result = FloorResult(
        architecture="agent_candidate",
        profile=profile_name,
        seed=seed,
        floor_id=floor.floor_id,
        attack_mode=floor.attack_mode,
        holdout=floor.holdout,
        plan=candidate,
        metrics=evaluate_plan(floor, candidate, cfg["constraints"], cfg["score_weights"]),
    )
    trace = {
        "profile": profile_name,
        "observations": observations,
        "dropped_roles": dropped,
        "proposals": proposals,
        "trust_scores": trust,
        "accepted_roles": accepted,
        "synthesized_plan": asdict(synthesized),
        "red_team_findings": findings,
        "final_candidate_plan": asdict(candidate),
        "referee_ground_truth": asdict(floor),
    }
    return result, trace


def baseline_result(floor: FloorSpec, seed: int, cfg: Mapping[str, Any]) -> FloorResult:
    plan = baseline_plan(cfg)
    return FloorResult(
        architecture="locked_baseline",
        profile="locked_baseline",
        seed=seed,
        floor_id=floor.floor_id,
        attack_mode=floor.attack_mode,
        holdout=floor.holdout,
        plan=plan,
        metrics=evaluate_plan(floor, plan, cfg["constraints"], cfg["score_weights"]),
    )


def _grid_axis(low: float, high: float, points: int) -> list[float]:
    if points == 2:
        return [low, high]
    step = (high - low) / (points - 1)
    return [low + step * index for index in range(points)]


def oracle_result(
    floor: FloorSpec,
    seed: int,
    cfg: Mapping[str, Any],
) -> FloorResult:
    """Return the referee-only best plan found on the predeclared finite grid."""
    bounds = _bounds(cfg)
    grid = cfg["oracle_grid"]
    axes = {name: _grid_axis(*bounds[name], int(grid[name])) for name in CONTROLS}
    best_plan: ControlPlan | None = None
    best_metrics: Metrics | None = None
    for routing in axes["routing"]:
        for cooling in axes["cooling"]:
            for redundancy in axes["redundancy"]:
                for reserve in axes["reserve"]:
                    plan = ControlPlan(routing, cooling, redundancy, reserve)
                    metrics = evaluate_plan(floor, plan, cfg["constraints"], cfg["score_weights"])
                    if best_metrics is None or (metrics.score, -metrics.violations, -metrics.energy_index) > (best_metrics.score, -best_metrics.violations, -best_metrics.energy_index):
                        best_plan, best_metrics = plan, metrics
    assert best_plan is not None and best_metrics is not None
    return FloorResult(
        architecture="referee_grid_reference",
        profile="referee_grid_reference",
        seed=seed,
        floor_id=floor.floor_id,
        attack_mode=floor.attack_mode,
        holdout=floor.holdout,
        plan=best_plan,
        metrics=best_metrics,
    )


def _result(result: FloorResult) -> dict[str, Any]:
    return {
        "architecture": result.architecture,
        "profile": result.profile,
        "seed": result.seed,
        "floor_id": result.floor_id,
        "attack_mode": result.attack_mode,
        "holdout": result.holdout,
        "plan": asdict(result.plan),
        "metrics": asdict(result.metrics),
    }


def _percentile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction


def _cvar(
    values: Sequence[float],
    tail_probability: float = 0.10,
    *,
    upper: bool = False,
) -> float:
    ordered = sorted(float(v) for v in values)
    if not ordered:
        return 0.0
    count = max(1, math.ceil(len(ordered) * tail_probability))
    return mean(ordered[-count:] if upper else ordered[:count])


def _profile_selection_summary(rows: Sequence[FloorResult], cfg: Mapping[str, Any]) -> dict[str, Any]:
    by_profile: dict[str, list[FloorResult]] = {}
    for row in rows:
        by_profile.setdefault(row.profile, []).append(row)
    rule = cfg["champion_selection"]
    summary: dict[str, Any] = {}
    for profile, trials in sorted(by_profile.items()):
        scores = [trial.metrics.score for trial in trials]
        violation_rate = mean(trial.metrics.violations for trial in trials)
        objective = (
            float(rule["mean_score_weight"]) * mean(scores)
            + float(rule["cvar10_weight"]) * _cvar(scores, 0.10)
            - float(rule["violation_weight"]) * violation_rate
        )
        summary[profile] = {
            "trials": len(trials),
            "score_mean": mean(scores),
            "score_stdev": pstdev(scores) if len(scores) > 1 else 0.0,
            "score_p10": _percentile(scores, 0.10),
            "score_cvar10": _cvar(scores, 0.10),
            "violations_per_trial": violation_rate,
            "selection_objective": objective,
        }
    return summary


def select_champion(rows: Sequence[FloorResult], cfg: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
    summary = _profile_selection_summary(rows, cfg)
    champion = sorted(
        summary,
        key=lambda profile: (-float(summary[profile]["selection_objective"]), profile),
    )[0]
    return champion, summary


def _aggregate(rows: Sequence[FloorResult]) -> dict[str, Any]:
    grouped: dict[str, list[FloorResult]] = {}
    for row in rows:
        grouped.setdefault(row.profile, []).append(row)
    out: dict[str, Any] = {}
    for profile, trials in sorted(grouped.items()):
        scores = [r.metrics.score for r in trials]
        out[profile] = {
            "trials": len(trials),
            "score_mean": mean(scores),
            "score_p10": _percentile(scores, 0.10),
            "score_cvar10": _cvar(scores, 0.10),
            "service_rate_mean": mean(r.metrics.service_rate for r in trials),
            "latency_index_mean": mean(r.metrics.latency_index for r in trials),
            "energy_index_mean": mean(r.metrics.energy_index for r in trials),
            "thermal_index_mean": mean(r.metrics.thermal_index for r in trials),
            "resilience_index_mean": mean(r.metrics.resilience_index for r in trials),
            "constraint_violations_total": sum(r.metrics.violations for r in trials),
        }
    return out


def _paired_rows(
    baseline: Sequence[FloorResult],
    candidate: Sequence[FloorResult],
) -> list[tuple[FloorResult, FloorResult]]:
    by_key = {(r.seed, r.floor_id): r for r in baseline}
    pairs: list[tuple[FloorResult, FloorResult]] = []
    for cand in candidate:
        key = (cand.seed, cand.floor_id)
        if key in by_key:
            pairs.append((by_key[key], cand))
    return sorted(pairs, key=lambda pair: (pair[0].seed, pair[0].floor_id))


def _bootstrap_ci(
    values: Sequence[float],
    samples: int,
    confidence: float,
    seed: int,
) -> list[float]:
    if not values:
        return [0.0, 0.0]
    rng = random.Random(seed)
    boot_means: list[float] = []
    for _ in range(samples):
        boot_means.append(mean(values[rng.randrange(len(values))] for _ in values))
    alpha = (1.0 - confidence) / 2.0
    return [_percentile(boot_means, alpha), _percentile(boot_means, 1.0 - alpha)]


def paired_statistics(
    baseline: Sequence[FloorResult],
    candidate: Sequence[FloorResult],
    cfg: Mapping[str, Any],
) -> dict[str, Any]:
    pairs = _paired_rows(baseline, candidate)
    stats_cfg = cfg["statistics"]
    samples = int(stats_cfg["bootstrap_samples"])
    confidence = float(stats_cfg["confidence"])
    base_seed = int(stats_cfg["bootstrap_seed"])
    metrics: dict[str, tuple[list[float], bool]] = {
        "score_delta": ([c.metrics.score - b.metrics.score for b, c in pairs], False),
        "service_rate_delta_points": ([100.0 * (c.metrics.service_rate - b.metrics.service_rate) for b, c in pairs], False),
        "resilience_delta_points": ([100.0 * (c.metrics.resilience_index - b.metrics.resilience_index) for b, c in pairs], False),
        "energy_delta": ([c.metrics.energy_index - b.metrics.energy_index for b, c in pairs], True),
        "latency_delta": ([c.metrics.latency_index - b.metrics.latency_index for b, c in pairs], True),
        "violation_delta": ([float(c.metrics.violations - b.metrics.violations) for b, c in pairs], True),
    }
    output: dict[str, Any] = {
        "paired_trials": len(pairs),
        "confidence": confidence,
        "bootstrap_samples": samples,
        "candidate_score_win_rate": mean(float(c.metrics.score > b.metrics.score) for b, c in pairs) if pairs else 0.0,
        "candidate_no_worse_violation_rate": mean(float(c.metrics.violations <= b.metrics.violations) for b, c in pairs) if pairs else 0.0,
    }
    floor_ids = sorted({candidate.floor_id for _, candidate in pairs})
    for index, (name, (values, upper_is_adverse)) in enumerate(metrics.items()):
        by_floor = {
            floor_id: [
                value
                for value, (_, candidate) in zip(values, pairs)
                if candidate.floor_id == floor_id
            ]
            for floor_id in floor_ids
        }
        floor_cluster_means = [mean(by_floor[floor_id]) for floor_id in floor_ids]
        output[name] = {
            "mean": mean(values) if values else 0.0,
            "median": median(values) if values else 0.0,
            "adverse_tail": "upper" if upper_is_adverse else "lower",
            "adverse_tail_cvar10": _cvar(values, 0.10, upper=upper_is_adverse),
            "floor_cluster_bootstrap_ci": _bootstrap_ci(
                floor_cluster_means,
                samples,
                confidence,
                base_seed + index * 97,
            ),
        }
    return output


def grid_reference_statistics(
    candidate: Sequence[FloorResult],
    reference: Sequence[FloorResult],
) -> dict[str, Any]:
    pairs = _paired_rows(candidate, reference)
    deltas = [r.metrics.score - c.metrics.score for c, r in pairs]
    return {
        "paired_trials": len(pairs),
        "reference_minus_candidate_score_mean": mean(deltas) if deltas else 0.0,
        "reference_minus_candidate_score_median": median(deltas) if deltas else 0.0,
        "reference_minus_candidate_score_max": max(deltas) if deltas else 0.0,
        "candidate_fraction_within_5_score_points": mean(float(delta <= 5.0) for delta in deltas) if deltas else 0.0,
    }


def _attack_breakdown(
    baseline: Sequence[FloorResult],
    candidate: Sequence[FloorResult],
) -> dict[str, Any]:
    pairs = _paired_rows(baseline, candidate)
    grouped: dict[str, list[tuple[FloorResult, FloorResult]]] = {}
    for pair in pairs:
        grouped.setdefault(pair[0].attack_mode, []).append(pair)
    out: dict[str, Any] = {}
    for attack, group in sorted(grouped.items()):
        out[attack] = {
            "pairs": len(group),
            "score_delta_mean": mean(c.metrics.score - b.metrics.score for b, c in group),
            "violation_delta_mean": mean(c.metrics.violations - b.metrics.violations for b, c in group),
            "candidate_score_win_rate": mean(float(c.metrics.score > b.metrics.score) for b, c in group),
        }
    return out


def _write_event(handle, event: Mapping[str, Any], previous: str) -> tuple[str, str]:
    body = dict(event)
    body["previous_event_sha256"] = previous
    event_hash = sha256_text(canonical_json(body))
    body["event_sha256"] = event_hash
    handle.write(canonical_json(body) + "\n")
    return event_hash, event_hash


def merkle_root(event_hashes: Sequence[str]) -> str:
    if not event_hashes:
        return sha256_text("")
    layer = [str(value) for value in event_hashes]
    while len(layer) > 1:
        if len(layer) % 2:
            layer.append(layer[-1])
        layer = [sha256_text(layer[i] + layer[i + 1]) for i in range(0, len(layer), 2)]
    return layer[0]


def _provider_implementation_sha256(provider: ProposalProvider) -> str:
    """Bind the executing callable, not just its human-written descriptor."""
    target: Any = provider
    if not inspect.isfunction(target) and not inspect.ismethod(target):
        target = getattr(target, "__call__", None)
    if target is None:
        raise ValueError("provider implementation is not inspectable")
    try:
        source = inspect.getsource(target)
    except (OSError, TypeError) as exc:
        raise ValueError("provider implementation source is not inspectable") from exc
    identity = {
        "module": getattr(target, "__module__", None),
        "qualname": getattr(target, "__qualname__", None),
        "source": source,
    }
    return sha256_text(canonical_json(identity))


def _bound_provider_descriptor(
    descriptor: Mapping[str, Any],
    provider: ProposalProvider,
) -> dict[str, Any]:
    bound = dict(descriptor)
    actual = _provider_implementation_sha256(provider)
    declared = bound.get("implementation_sha256")
    if declared is not None and declared != actual:
        raise ValueError("provider implementation hash does not match descriptor")
    bound["implementation_sha256"] = actual
    return bound


def _provider_descriptor_hash(descriptor: Mapping[str, Any]) -> str:
    return sha256_text(canonical_json(descriptor))


def _scorecard(summary: Mapping[str, Any]) -> str:
    holdout = summary["holdout_statistics"]
    score = holdout["score_delta"]
    violations = holdout["violation_delta"]
    candidate = summary["holdout_aggregate"][summary["champion_profile"]]
    gate = summary["acceptance_gate"]
    return "\n".join(
        [
            "# LumenCore Agent Arena V5 — Synthetic Scorecard",
            "",
            f"**Evidence boundary:** {summary['evidence_boundary']}",
            "",
            f"- Scenario lock SHA-256: `{summary['scenario_sha256']}`",
            f"- Engine SHA-256: `{summary['engine_sha256']}`",
            f"- Provider descriptor SHA-256: `{summary['provider_descriptor_sha256']}`",
            f"- Provider implementation SHA-256: `{summary['provider_descriptor']['implementation_sha256']}`",
            f"- Git tree: `{summary['git_tree']}`",
            f"- Event-chain root SHA-256: `{summary['event_chain_root_sha256']}`",
            f"- Event Merkle root SHA-256: `{summary['event_merkle_root_sha256']}`",
            f"- Selected champion: `{summary['champion_profile']}`",
            f"- Holdout paired trials: {holdout['paired_trials']}",
            "",
            "## Holdout result",
            "",
            f"- Absolute gate: **{gate['status']}**",
            f"- Candidate mean score: {candidate['score_mean']:.6f} (required >= {gate['required']['min_score_mean']:.6f})",
            f"- Candidate constraint violations: {candidate['constraint_violations_total']} (required <= {gate['required']['max_constraint_violations_total']})",
            f"- Mean score delta: {score['mean']:.6f}",
            f"- Score-delta floor-cluster bootstrap CI: [{score['floor_cluster_bootstrap_ci'][0]:.6f}, {score['floor_cluster_bootstrap_ci'][1]:.6f}]",
            f"- Candidate score win rate: {100.0 * holdout['candidate_score_win_rate']:.2f}%",
            f"- Mean violation delta: {violations['mean']:.6f}",
            f"- Candidate no-worse violation rate: {100.0 * holdout['candidate_no_worse_violation_rate']:.2f}%",
            f"- Mean referee-grid-minus-candidate score: {summary['grid_reference_comparison']['reference_minus_candidate_score_mean']:.6f}",
            f"- Trust-assurance status: {summary['trust_assurance']['status']}",
            "",
            "## V2 → V5 capability chain",
            "",
            "- V2: role-specific corrupted telemetry, role dropout, Byzantine control corruption, trust-weighted synthesis, deterministic red-team gate.",
            "- V3: multiple predeclared candidate profiles compete only on non-holdout floors; the champion is locked before holdout execution.",
            "- V4: floor-cluster bootstrap intervals, direction-aware adverse-tail metrics, win rates, and attack-mode breakdowns.",
            "- V5: engine/provider implementation hashes, clean-tree custody, event hash chain, event Merkle root, manifest verification, and an unsigned internally consistent receipt.",
            "",
            "Completion is not acceptance. A positive relative delta does not override a failed absolute gate or establish Byzantine tolerance. The unsigned receipt requires an independently pinned digest or signature for authenticity. Promotion requires qualified non-author execution or a buyer-approved dataset/simulator and accepted baseline under the same prelocked rules.",
            "",
        ]
    )


def _execution_receipt_body(
    summary: Mapping[str, Any],
    manifest_sha256: str,
    generated_utc: str,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "generated_utc": generated_utc,
        "git_commit": summary["git_commit"],
        "git_tree": summary["git_tree"],
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "scenario_sha256": summary["scenario_sha256"],
        "engine_sha256": summary["engine_sha256"],
        "provider_descriptor_sha256": summary["provider_descriptor_sha256"],
        "event_chain_root_sha256": summary["event_chain_root_sha256"],
        "event_merkle_root_sha256": summary["event_merkle_root_sha256"],
        "manifest_sha256": manifest_sha256,
        "champion_profile": summary["champion_profile"],
        "evaluation_status": summary["acceptance_gate"]["status"],
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "authentication": "UNSIGNED_REQUIRES_EXTERNAL_PIN_OR_SIGNATURE",
    }


def run_arena(
    out_dir: Path = DEFAULT_OUT,
    config_path: Path = DEFAULT_CONFIG,
    provider: ProposalProvider = deterministic_provider,
    generated_utc: str | None = None,
    provider_descriptor: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    git_commit, git_tree = _git_state()
    raw = config_path.read_bytes()
    cfg = _validate_config(json.loads(raw.decode("utf-8")))
    if out_dir.exists() and any(out_dir.iterdir()):
        raise ValueError("arena output directory must be absent or empty")
    out_dir.mkdir(parents=True, exist_ok=True)
    generated_utc = generated_utc or datetime.now(timezone.utc).isoformat()
    scenario_sha = hashlib.sha256(raw).hexdigest()
    (out_dir / "scenario.lock.json").write_bytes(raw)
    floors = [_floor_from_config(x) for x in cfg["floors"]]
    selection_floors = [floor for floor in floors if not floor.holdout]
    holdout_floors = [floor for floor in floors if floor.holdout]
    descriptor = _bound_provider_descriptor(
        provider_descriptor or cfg["provider_descriptor"],
        provider,
    )
    descriptor_hash = _provider_descriptor_hash(descriptor)
    event_path = out_dir / "events.jsonl"
    root = "0" * 64
    event_hashes: list[str] = []
    selection_rows: list[FloorResult] = []
    holdout_candidate_rows: list[FloorResult] = []
    holdout_baseline_rows: list[FloorResult] = []
    holdout_oracle_rows: list[FloorResult] = []
    trust_audit: list[dict[str, Any]] = []
    with event_path.open("w", encoding="utf-8", newline="\n") as handle:
        root, event_hash = _write_event(
            handle,
            {
                "event_type": "arena_start",
                "schema": SCHEMA,
                "evidence_boundary": EVIDENCE_BOUNDARY,
                "scenario_sha256": scenario_sha,
                "engine_sha256": _engine_sha256(),
                "git_commit": git_commit,
                "git_tree": git_tree,
                "provider_descriptor_sha256": descriptor_hash,
                "selection_seeds": cfg["selection_seeds"],
                "holdout_seeds": cfg["holdout_seeds"],
                "selection_floor_ids": [floor.floor_id for floor in selection_floors],
                "holdout_floor_ids": [floor.floor_id for floor in holdout_floors],
            },
            root,
        )
        event_hashes.append(event_hash)
        for profile_name in sorted(cfg["candidate_profiles"]):
            for seed in cfg["selection_seeds"]:
                for floor in selection_floors:
                    candidate, trace = run_floor(floor, seed, cfg, profile_name, provider)
                    selection_rows.append(candidate)
                    root, event_hash = _write_event(
                        handle,
                        {
                            "event_type": "selection_floor_referee_decision",
                            "profile": profile_name,
                            "seed": seed,
                            "floor_id": floor.floor_id,
                            "attack_mode": floor.attack_mode,
                            "trace": trace,
                            "candidate": _result(candidate),
                        },
                        root,
                    )
                    event_hashes.append(event_hash)
        champion, selection_summary = select_champion(selection_rows, cfg)
        root, event_hash = _write_event(
            handle,
            {
                "event_type": "champion_selected",
                "champion_profile": champion,
                "selection_summary": selection_summary,
                "selection_rule": cfg["champion_selection"],
                "holdout_results_observed": False,
            },
            root,
        )
        event_hashes.append(event_hash)
        for seed in cfg["holdout_seeds"]:
            for floor in holdout_floors:
                baseline = baseline_result(floor, seed, cfg)
                candidate, trace = run_floor(floor, seed, cfg, champion, provider)
                oracle = oracle_result(floor, seed, cfg)
                holdout_baseline_rows.append(baseline)
                holdout_oracle_rows.append(oracle)
                holdout_candidate_rows.append(candidate)
                accepted = set(trace["accepted_roles"])
                compromised = set(floor.compromised_roles)
                trust_audit.append(
                    {
                        "seed": seed,
                        "floor_id": floor.floor_id,
                        "accepted_roles": sorted(accepted),
                        "accepted_compromised_roles": sorted(accepted & compromised),
                        "only_compromised_roles_accepted": bool(accepted) and accepted <= compromised,
                    }
                )
                root, event_hash = _write_event(
                    handle,
                    {
                        "event_type": "holdout_floor_referee_decision",
                        "champion_profile": champion,
                        "seed": seed,
                        "floor_id": floor.floor_id,
                        "attack_mode": floor.attack_mode,
                        "trace": trace,
                        "baseline": _result(baseline),
                        "candidate": _result(candidate),
                        "referee_grid_reference": _result(oracle),
                    },
                    root,
                )
                event_hashes.append(event_hash)
        root, event_hash = _write_event(
            handle,
            {
                "event_type": "arena_complete",
                "selection_rows": len(selection_rows),
                "holdout_pairs": len(holdout_candidate_rows),
                "champion_profile": champion,
            },
            root,
        )
        event_hashes.append(event_hash)
    merkle = merkle_root(event_hashes)
    holdout_stats = paired_statistics(holdout_baseline_rows, holdout_candidate_rows, cfg)
    candidate_aggregate = _aggregate(holdout_candidate_rows)[champion]
    gate_required = cfg["acceptance_gate"]
    gate_checks = {
        "score_mean": candidate_aggregate["score_mean"] >= float(gate_required["min_score_mean"]),
        "constraint_violations_total": candidate_aggregate["constraint_violations_total"] <= int(gate_required["max_constraint_violations_total"]),
    }
    acceptance_gate = {
        "status": "PASS" if all(gate_checks.values()) else "FAIL",
        "required": gate_required,
        "checks": gate_checks,
    }
    trust_assurance = {
        "status": "NOT_DEMONSTRATED" if any(row["accepted_compromised_roles"] for row in trust_audit) else "NO_COMPROMISED_ROLE_ACCEPTED_IN_LOCKED_RUN",
        "holdout_trials": len(trust_audit),
        "trials_accepting_compromised_roles": sum(bool(row["accepted_compromised_roles"]) for row in trust_audit),
        "trials_accepting_only_compromised_roles": sum(row["only_compromised_roles_accepted"] for row in trust_audit),
        "audit": trust_audit,
    }
    summary = {
        "schema": SCHEMA,
        "generated_utc": generated_utc,
        "execution_environment": {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
        },
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "git_commit": git_commit,
        "git_tree": git_tree,
        "engine_sha256": _engine_sha256(),
        "scenario_sha256": scenario_sha,
        "provider_descriptor": descriptor,
        "provider_descriptor_sha256": descriptor_hash,
        "event_chain_root_sha256": root,
        "event_merkle_root_sha256": merkle,
        "champion_profile": champion,
        "selection_summary": selection_summary,
        "holdout_aggregate": {
            "locked_baseline": _aggregate(holdout_baseline_rows)["locked_baseline"],
            champion: candidate_aggregate,
            "referee_grid_reference": _aggregate(holdout_oracle_rows)["referee_grid_reference"],
        },
        "holdout_statistics": holdout_stats,
        "grid_reference_comparison": grid_reference_statistics(holdout_candidate_rows, holdout_oracle_rows),
        "acceptance_gate": acceptance_gate,
        "trust_assurance": trust_assurance,
        "holdout_attack_breakdown": _attack_breakdown(holdout_baseline_rows, holdout_candidate_rows),
        "configuration": {
            "capability_stages": cfg["capability_stages"],
            "selection_seeds": cfg["selection_seeds"],
            "holdout_seeds": cfg["holdout_seeds"],
            "selection_floor_ids": [floor.floor_id for floor in selection_floors],
            "holdout_floor_ids": [floor.floor_id for floor in holdout_floors],
            "agent_roles": cfg["agent_roles"],
            "candidate_profiles": cfg["candidate_profiles"],
            "baseline_plan": asdict(baseline_plan(cfg)),
            "control_bounds": cfg["control_bounds"],
            "constraints": cfg["constraints"],
            "score_weights": cfg["score_weights"],
            "champion_selection": cfg["champion_selection"],
            "oracle_grid": cfg["oracle_grid"],
            "statistics": cfg["statistics"],
            "acceptance_gate": cfg["acceptance_gate"],
        },
        "claim_boundary": cfg["claim_boundary"],
        "next_validation_gate": cfg["next_validation_gate"],
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(_scorecard(summary), encoding="utf-8")
    files = ["scenario.lock.json", "events.jsonl", "summary.json", "SCORECARD.md"]
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "scenario_sha256": scenario_sha,
        "engine_sha256": summary["engine_sha256"],
        "git_commit": git_commit,
        "git_tree": git_tree,
        "provider_descriptor_sha256": descriptor_hash,
        "event_chain_root_sha256": root,
        "event_merkle_root_sha256": merkle,
        "files": {
            name: {
                "bytes": (out_dir / name).stat().st_size,
                "sha256": sha256_file(out_dir / name),
            }
            for name in files
        },
    }
    manifest_path = out_dir / "manifest.sha256.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt_body = _execution_receipt_body(summary, sha256_file(manifest_path), generated_utc)
    receipt = dict(receipt_body)
    receipt["receipt_sha256"] = sha256_text(canonical_json(receipt_body))
    (out_dir / "execution_receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def verify_bundle(out_dir: Path) -> dict[str, Any]:
    current_commit, current_tree = _git_state()
    manifest_path = out_dir / "manifest.sha256.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != MANIFEST_SCHEMA:
        raise ValueError("manifest schema mismatch")
    if manifest.get("evidence_boundary") != EVIDENCE_BOUNDARY:
        raise ValueError("manifest evidence boundary mismatch")
    if manifest.get("engine_sha256") != _engine_sha256():
        raise ValueError("verifier engine does not match bundle engine")
    if manifest.get("git_commit") != current_commit or manifest.get("git_tree") != current_tree:
        raise ValueError("verifier Git source does not match bundle source")
    expected = {"scenario.lock.json", "events.jsonl", "summary.json", "SCORECARD.md"}
    if set(manifest.get("files", {})) != expected:
        raise ValueError("manifest file set mismatch")
    for name, metadata in manifest["files"].items():
        path = out_dir / name
        if not path.is_file():
            raise ValueError(f"missing artifact: {name}")
        if path.stat().st_size != int(metadata["bytes"]):
            raise ValueError(f"byte-count mismatch: {name}")
        if sha256_file(path) != metadata["sha256"]:
            raise ValueError(f"sha256 mismatch: {name}")
    lock_path = out_dir / "scenario.lock.json"
    cfg = load_config(lock_path)
    scenario_sha = sha256_file(lock_path)
    if scenario_sha != manifest.get("scenario_sha256"):
        raise ValueError("scenario hash mismatch")
    previous = "0" * 64
    first: dict[str, Any] | None = None
    last: dict[str, Any] | None = None
    event_hashes: list[str] = []
    count = 0
    for count, line in enumerate((out_dir / "events.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        event = json.loads(line)
        first = first or dict(event)
        last = dict(event)
        if event.get("previous_event_sha256") != previous:
            raise ValueError(f"event predecessor mismatch at line {count}")
        claimed = event.pop("event_sha256")
        if claimed != sha256_text(canonical_json(event)):
            raise ValueError(f"event hash mismatch at line {count}")
        previous = claimed
        event_hashes.append(claimed)
    if not first or first.get("event_type") != "arena_start":
        raise ValueError("arena_start mismatch")
    if first.get("scenario_sha256") != scenario_sha:
        raise ValueError("arena_start scenario mismatch")
    if first.get("engine_sha256") != manifest.get("engine_sha256"):
        raise ValueError("arena_start engine mismatch")
    if first.get("git_commit") != manifest.get("git_commit") or first.get("git_tree") != manifest.get("git_tree"):
        raise ValueError("arena_start Git source mismatch")
    if not last or last.get("event_type") != "arena_complete":
        raise ValueError("arena_complete mismatch")
    if previous != manifest.get("event_chain_root_sha256"):
        raise ValueError("event chain root mismatch")
    calculated_merkle = merkle_root(event_hashes)
    if calculated_merkle != manifest.get("event_merkle_root_sha256"):
        raise ValueError("event merkle root mismatch")
    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    for key, expected_value in {
        "scenario_sha256": scenario_sha,
        "engine_sha256": manifest["engine_sha256"],
        "git_commit": manifest["git_commit"],
        "git_tree": manifest["git_tree"],
        "provider_descriptor_sha256": manifest["provider_descriptor_sha256"],
        "event_chain_root_sha256": previous,
        "event_merkle_root_sha256": calculated_merkle,
    }.items():
        if summary.get(key) != expected_value:
            raise ValueError(f"summary custody mismatch: {key}")
    expected_count = (
        len(cfg["candidate_profiles"]) * len(cfg["selection_seeds"]) * len([x for x in cfg["floors"] if not x.get("holdout")])
        + len(cfg["holdout_seeds"]) * len([x for x in cfg["floors"] if x.get("holdout")])
        + 3
    )
    if count != expected_count:
        raise ValueError("event count mismatch")
    receipt_path = out_dir / "execution_receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("receipt schema mismatch")
    claimed_receipt_hash = receipt.pop("receipt_sha256", None)
    if claimed_receipt_hash != sha256_text(canonical_json(receipt)):
        raise ValueError("execution receipt hash mismatch")
    if receipt.get("manifest_sha256") != sha256_file(manifest_path):
        raise ValueError("execution receipt manifest mismatch")
    receipt_expectations = {
        "generated_utc": summary["generated_utc"],
        "git_commit": summary["git_commit"],
        "git_tree": summary["git_tree"],
        "python_version": summary["execution_environment"]["python_version"],
        "platform": summary["execution_environment"]["platform"],
        "scenario_sha256": summary["scenario_sha256"],
        "engine_sha256": summary["engine_sha256"],
        "provider_descriptor_sha256": summary["provider_descriptor_sha256"],
        "event_chain_root_sha256": summary["event_chain_root_sha256"],
        "event_merkle_root_sha256": summary["event_merkle_root_sha256"],
        "champion_profile": summary["champion_profile"],
        "evaluation_status": summary["acceptance_gate"]["status"],
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "authentication": "UNSIGNED_REQUIRES_EXTERNAL_PIN_OR_SIGNATURE",
    }
    for key, expected_value in receipt_expectations.items():
        if receipt.get(key) != expected_value:
            raise ValueError(f"execution receipt custody mismatch: {key}")
    return {
        "status": "INTEGRITY_VERIFIED_UNSIGNED",
        "event_lines": count,
        "event_chain_root_sha256": previous,
        "event_merkle_root_sha256": calculated_merkle,
        "manifest_sha256": sha256_file(manifest_path),
        "execution_receipt_sha256": claimed_receipt_hash,
        "champion_profile": summary["champion_profile"],
        "evaluation_status": summary["acceptance_gate"]["status"],
        "authentication": "UNSIGNED_REQUIRES_EXTERNAL_PIN_OR_SIGNATURE",
        "files_verified": sorted(manifest["files"]),
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    run_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    if args.command == "run":
        summary = run_arena(args.out, args.config)
        print(
            json.dumps(
                {
                    "status": "COMPLETE",
                    "evaluation_status": summary["acceptance_gate"]["status"],
                    "out": str(args.out),
                    "champion_profile": summary["champion_profile"],
                    "event_chain_root_sha256": summary["event_chain_root_sha256"],
                    "event_merkle_root_sha256": summary["event_merkle_root_sha256"],
                    "evidence_boundary": EVIDENCE_BOUNDARY,
                },
                sort_keys=True,
            )
        )
    else:
        print(json.dumps(verify_bundle(args.out), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
