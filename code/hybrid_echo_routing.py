#!/usr/bin/env python3
"""LumenCore Hybrid Echo Routing lineage simulator.

Simulation-first research harness. It does not control physical infrastructure.
It compares static geometry, adaptive control, and hybrid candidates under the
same deterministic disturbance schedule and emits a hash-addressed lineage.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from hashlib import sha256
import argparse, json, math, random
from pathlib import Path
from typing import Iterable

GEOMETRIES = ("straight", "spiral", "helix", "branching", "gyroid", "phyllotactic")

@dataclass(frozen=True)
class Candidate:
    geometry: str
    phase_gain: float
    damping: float
    reroute_gain: float
    thermal_gain: float
    generation: int = 0
    parent_id: str | None = None

    @property
    def candidate_id(self) -> str:
        raw = json.dumps(asdict(self), sort_keys=True).encode()
        return sha256(raw).hexdigest()[:16]

@dataclass(frozen=True)
class Metrics:
    transmission_efficiency: float
    peak_load: float
    thermal_concentration: float
    recovery_time: float
    instability_rate: float
    control_cost: float
    score: float

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def geometry_profile(name: str) -> tuple[float, float, float]:
    profiles = {
        "straight": (0.82, 1.00, 0.95),
        "spiral": (0.91, 0.84, 0.80),
        "helix": (0.89, 0.86, 0.82),
        "branching": (0.88, 0.78, 0.76),
        "gyroid": (0.93, 0.73, 0.70),
        "phyllotactic": (0.92, 0.75, 0.72),
    }
    return profiles[name]

def evaluate(c: Candidate, seed: int, steps: int = 240) -> Metrics:
    rng = random.Random(seed)
    base_eff, load_shape, thermal_shape = geometry_profile(c.geometry)
    delivered = peak = thermal_sum = recovery = unstable = 0.0
    for t in range(steps):
        disturbance = 0.55 + 0.45 * math.sin(t / 17.0) + rng.uniform(-0.20, 0.20)
        demand = clamp(0.75 + disturbance, 0.15, 1.75)
        phase_match = 1.0 - abs(math.sin((t + 1) * 0.11 * c.phase_gain)) * 0.10
        adaptive_relief = clamp(c.reroute_gain * max(0.0, demand - 1.0), 0.0, 0.45)
        damping_relief = clamp(c.damping * abs(disturbance) * 0.18, 0.0, 0.35)
        thermal_relief = clamp(c.thermal_gain * demand * 0.12, 0.0, 0.30)
        load = demand * load_shape * (1.0 - adaptive_relief) * (1.0 - damping_relief)
        temperature = demand * thermal_shape * (1.0 - thermal_relief)
        efficiency = clamp(base_eff * phase_match + adaptive_relief * 0.12 - c.reroute_gain * 0.015, 0, 1)
        delivered += efficiency
        peak = max(peak, load)
        thermal_sum += temperature
        unstable += 1.0 if load > 1.30 or temperature > 1.25 else 0.0
        recovery += max(0.0, load - 0.90)
    eff = delivered / steps
    thermal = thermal_sum / steps
    instability = unstable / steps
    recovery_time = recovery / steps
    control_cost = 0.02 * (c.phase_gain + c.damping + c.reroute_gain + c.thermal_gain)
    score = 100*eff - 18*peak - 15*thermal - 30*instability - 8*recovery_time - 20*control_cost
    return Metrics(eff, peak, thermal, recovery_time, instability, control_cost, score)

def aggregate(c: Candidate, seeds: Iterable[int]) -> Metrics:
    rows = [evaluate(c, s) for s in seeds]
    n = len(rows)
    vals = {k: sum(getattr(r, k) for r in rows)/n for k in asdict(rows[0])}
    return Metrics(**vals)

def mutate(parent: Candidate, rng: random.Random, generation: int) -> Candidate:
    geometry = parent.geometry if rng.random() > 0.18 else rng.choice(GEOMETRIES)
    return Candidate(
        geometry=geometry,
        phase_gain=clamp(parent.phase_gain + rng.gauss(0, 0.18), 0.0, 2.0),
        damping=clamp(parent.damping + rng.gauss(0, 0.15), 0.0, 1.5),
        reroute_gain=clamp(parent.reroute_gain + rng.gauss(0, 0.14), 0.0, 1.5),
        thermal_gain=clamp(parent.thermal_gain + rng.gauss(0, 0.14), 0.0, 1.5),
        generation=generation,
        parent_id=parent.candidate_id,
    )

def evolve(seed: int = 1986, generations: int = 24, population: int = 36) -> dict:
    rng = random.Random(seed)
    train_seeds = [seed + i * 101 for i in range(8)]
    validation_seeds = [seed + 10_000 + i * 137 for i in range(8)]
    ancestor = Candidate("straight", 0.0, 0.0, 0.0, 0.0)
    pop = [ancestor] + [Candidate(rng.choice(GEOMETRIES), rng.random(), rng.random(), rng.random(), rng.random()) for _ in range(population - 1)]
    lineage = []
    for generation in range(generations + 1):
        ranked = sorted(((aggregate(c, train_seeds).score, c) for c in pop), reverse=True, key=lambda x: x[0])
        best = ranked[0][1]
        lineage.append({
            "generation": generation,
            "candidate": asdict(best),
            "candidate_id": best.candidate_id,
            "train_metrics": asdict(aggregate(best, train_seeds)),
            "validation_metrics": asdict(aggregate(best, validation_seeds)),
        })
        elite = [c for _, c in ranked[:max(3, population // 6)]]
        pop = elite[:]
        while len(pop) < population:
            pop.append(mutate(rng.choice(elite), rng, generation + 1))
    baseline = aggregate(ancestor, validation_seeds)
    champion = Candidate(**lineage[-1]["candidate"])
    result = {
        "schema": "lumencore.hybrid_echo_lineage.v1",
        "run_type": "synthetic",
        "seed": seed,
        "locked_objective": "maximize bounded composite score with efficiency, load, thermal, instability, recovery, and control-cost terms",
        "baseline": {"candidate": asdict(ancestor), "metrics": asdict(baseline)},
        "champion": {"candidate": asdict(champion), "candidate_id": champion.candidate_id, "metrics": asdict(aggregate(champion, validation_seeds))},
        "lineage": lineage,
        "claim_boundary": "Synthetic comparison only; not field validation, certified savings, or autonomous infrastructure control.",
    }
    payload = json.dumps(result, sort_keys=True, separators=(",", ":")).encode()
    result["manifest_sha256"] = sha256(payload).hexdigest()
    return result

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--seed", type=int, default=1986)
    p.add_argument("--generations", type=int, default=24)
    p.add_argument("--population", type=int, default=36)
    p.add_argument("--output", type=Path, default=Path("artifacts/hybrid_echo_lineage.json"))
    args = p.parse_args()
    result = evolve(args.seed, args.generations, args.population)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": result["manifest_sha256"], "champion": result["champion"]}, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
