"""Deterministic adversarial multi-agent harness for LumenCore proof-to-pilot.

Synthetic/replay evidence only. The referee, scoring, constraints, baseline,
scenario lock, and evidence ledger remain outside agent control.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Protocol

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config" / "agent_arena_v1.json"
DEFAULT_OUT = ROOT / "out" / "agent_arena"
SCHEMA = "lumencore.agent_arena.v1"
EVIDENCE_BOUNDARY = (
    "Synthetic/replay software evidence only. The Arena evaluates agent proposals "
    "inside a deterministic abstract infrastructure model with predeclared rules. "
    "It does not establish field performance, production safety, customer savings, "
    "external validation, certification, or universal superiority."
)
CONTROLS = ("routing", "cooling", "redundancy", "reserve")
CONSTRAINTS = (
    "service_rate_min", "latency_index_max", "energy_index_max",
    "thermal_index_max", "resilience_index_min",
)
WEIGHTS = (
    "service_rate", "resilience_index", "latency_index", "energy_index",
    "thermal_index", "violation_penalty",
)


class ProposalProvider(Protocol):
    def __call__(self, role: str, observation: Mapping[str, Any],
                 bounds: Mapping[str, tuple[float, float]]) -> Mapping[str, float]: ...


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
    seed: int
    floor_id: str
    holdout: bool
    plan: ControlPlan
    metrics: Metrics


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _finite(value: Any, name: str) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "unknown"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if cfg.get("schema") != SCHEMA:
        raise ValueError("unexpected scenario schema")
    if cfg.get("evidence_boundary") != EVIDENCE_BOUNDARY:
        raise ValueError("evidence boundary mismatch")
    if set(cfg.get("control_bounds", {})) != set(CONTROLS):
        raise ValueError("control bounds mismatch")
    for name, pair in cfg["control_bounds"].items():
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError(f"invalid bounds for {name}")
        low, high = map(float, pair)
        if not low <= high:
            raise ValueError(f"reversed bounds for {name}")
    floors = cfg.get("floors", [])
    ids = [str(x["floor_id"]) for x in floors]
    if len(floors) < 2 or len(ids) != len(set(ids)):
        raise ValueError("floors must be unique and contain at least two entries")
    if sum(bool(x.get("holdout")) for x in floors) != 1:
        raise ValueError("exactly one holdout floor is required")
    seeds = cfg.get("seeds", [])
    if not seeds or any(not isinstance(x, int) for x in seeds) or len(seeds) != len(set(seeds)):
        raise ValueError("seeds must be unique integers")
    if set(cfg.get("constraints", {})) != set(CONSTRAINTS):
        raise ValueError("constraint lock mismatch")
    if set(cfg.get("score_weights", {})) != set(WEIGHTS):
        raise ValueError("score-weight lock mismatch")
    if not cfg.get("agent_roles"):
        raise ValueError("at least one agent role is required")
    return cfg


def _bounds(cfg: Mapping[str, Any]) -> dict[str, tuple[float, float]]:
    return {k: (float(v[0]), float(v[1])) for k, v in cfg["control_bounds"].items()}


def _floor_from_config(x: Mapping[str, Any]) -> FloorSpec:
    return FloorSpec(
        floor_id=str(x["floor_id"]), label=str(x["label"]),
        demand=_finite(x["demand"], "demand"),
        capacity_loss=_finite(x["capacity_loss"], "capacity_loss"),
        ambient_heat=_finite(x["ambient_heat"], "ambient_heat"),
        failure_rate=_finite(x["failure_rate"], "failure_rate"),
        telemetry_noise=_finite(x["telemetry_noise"], "telemetry_noise"),
        holdout=bool(x.get("holdout")),
    )


def _plan(values: Mapping[str, Any], bounds: Mapping[str, tuple[float, float]]) -> ControlPlan:
    base = asdict(ControlPlan())
    for name in CONTROLS:
        low, high = bounds[name]
        base[name] = clamp(_finite(values.get(name, base[name]), name), low, high)
    return ControlPlan(**base)


def baseline_plan(cfg: Mapping[str, Any]) -> ControlPlan:
    return _plan(cfg["baseline_plan"], _bounds(cfg))


def observe_floor(floor: FloorSpec, seed: int) -> dict[str, Any]:
    rng = random.Random((seed * 1_000_003) ^ int(sha256_text(floor.floor_id)[:12], 16))
    n = floor.telemetry_noise
    sensed = lambda v: v * (1 + rng.uniform(-n, n))
    return {
        "floor_id": floor.floor_id, "label": floor.label, "holdout": floor.holdout,
        "seed": seed, "demand": sensed(floor.demand),
        "capacity_loss": clamp(sensed(floor.capacity_loss), 0, .95),
        "ambient_heat": max(0.0, sensed(floor.ambient_heat)),
        "failure_rate": clamp(sensed(floor.failure_rate), 0, .95),
        "telemetry_noise": n,
    }


def deterministic_provider(role: str, o: Mapping[str, Any],
                           bounds: Mapping[str, tuple[float, float]]) -> Mapping[str, float]:
    demand, loss, heat = float(o["demand"]), float(o["capacity_loss"]), float(o["ambient_heat"])
    failure, noise = float(o["failure_rate"]), float(o["telemetry_noise"])
    pressure = max(0.0, demand / 100.0 - .72)
    table = {
        "router": {"routing": 1 + 1.10 * pressure + .80 * loss},
        "thermal": {"cooling": .18 + .75 * pressure + .95 * heat},
        "resilience": {"redundancy": 1 + 7 * failure + 1.8 * loss,
                       "reserve": .10 + 2.6 * failure + .75 * loss},
        "efficiency": {"routing": 1 + .60 * pressure,
                       "cooling": .15 + .45 * pressure + .65 * heat,
                       "reserve": .08 + .40 * pressure},
        "telemetry_skeptic": {"cooling": .18 + 1.2 * noise,
                              "reserve": .10 + 1.6 * noise,
                              "redundancy": 1 + 3 * noise},
    }
    if role not in table:
        raise ValueError(f"unknown role: {role}")
    return table[role]


def sanitize_proposal(p: Mapping[str, Any], bounds: Mapping[str, tuple[float, float]]) -> dict[str, float]:
    unknown = set(p) - set(bounds)
    if unknown:
        raise ValueError(f"proposal contains undeclared controls: {sorted(unknown)}")
    out = {}
    for name, raw in p.items():
        low, high = bounds[name]
        out[name] = clamp(_finite(raw, f"proposal.{name}"), low, high)
    return out


def synthesize_plan(proposals: list[Mapping[str, float]],
                    bounds: Mapping[str, tuple[float, float]]) -> ControlPlan:
    values = {}
    defaults = asdict(ControlPlan())
    for name in CONTROLS:
        xs = sorted(float(p[name]) for p in proposals if name in p) or [defaults[name]]
        n = len(xs)
        median = xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2
        values[name] = median
    return _plan(values, bounds)


def red_team_challenge(plan: ControlPlan, o: Mapping[str, Any],
                       bounds: Mapping[str, tuple[float, float]]) -> tuple[ControlPlan, list[str]]:
    x, findings = asdict(plan), []
    if float(o["demand"]) > 92 and plan.routing < 1.20:
        findings.append("routing_underprovisioned_for_observed_demand"); x["routing"] = 1.20
    if float(o["ambient_heat"]) > .10 and plan.cooling < .30:
        findings.append("cooling_underprovisioned_for_observed_heat"); x["cooling"] = .30
    if float(o["failure_rate"]) + float(o["capacity_loss"]) > .12 and plan.redundancy < 1.40:
        findings.append("redundancy_underprovisioned_for_observed_faults"); x["redundancy"] = 1.40
    if float(o["telemetry_noise"]) > .08 and plan.reserve < .18:
        findings.append("reserve_underprovisioned_for_telemetry_uncertainty"); x["reserve"] = .18
    return _plan(x, bounds), findings


def evaluate_plan(f: FloorSpec, p: ControlPlan, c: Mapping[str, float], w: Mapping[str, float]) -> Metrics:
    capacity = (100 * max(.05, 1 - f.capacity_loss) * (1 + .30 * (p.routing - 1))
                * (1 + .10 * max(0, p.redundancy - 1)) * (1 + .16 * p.reserve))
    ratio = f.demand / max(capacity, 1e-9)
    service = clamp(capacity / max(f.demand, 1e-9), 0, 1)
    latency = max(0.0, ratio * ratio / max(p.routing, .1))
    energy = max(0.0, (f.demand / 100) * (1 + .07 * max(0, p.routing - 1)
                 + .11 * max(0, p.redundancy - 1) + .34 * p.cooling + .08 * p.reserve))
    thermal = max(0.0, (f.demand / 100) * (1 + f.ambient_heat) - .80 * p.cooling
                  + .05 * max(0, p.redundancy - 1))
    resilience = clamp(1 - 1.55 * f.failure_rate / max(p.redundancy, 1)
                       - .28 * f.capacity_loss + .22 * p.reserve
                       + .035 * max(0, p.redundancy - 1), 0, 1)
    violations = int(sum((
        service < float(c["service_rate_min"]), latency > float(c["latency_index_max"]),
        energy > float(c["energy_index_max"]), thermal > float(c["thermal_index_max"]),
        resilience < float(c["resilience_index_min"]),
    )))
    score = (float(w["service_rate"]) * service + float(w["resilience_index"]) * resilience
             - float(w["latency_index"]) * latency - float(w["energy_index"]) * energy
             - float(w["thermal_index"]) * thermal - float(w["violation_penalty"]) * violations)
    return Metrics(service, latency, energy, thermal, resilience, violations, score)


def run_floor(floor: FloorSpec, seed: int, cfg: Mapping[str, Any],
              provider: ProposalProvider = deterministic_provider):
    bounds, o = _bounds(cfg), observe_floor(floor, seed)
    roles = list(cfg["agent_roles"])
    proposals = [sanitize_proposal(provider(role, o, bounds), bounds) for role in roles]
    synthesized = synthesize_plan(proposals, bounds)
    candidate, findings = red_team_challenge(synthesized, o, bounds)
    baseline = baseline_plan(cfg)
    c, w = cfg["constraints"], cfg["score_weights"]
    b = FloorResult("locked_baseline", seed, floor.floor_id, floor.holdout,
                    baseline, evaluate_plan(floor, baseline, c, w))
    a = FloorResult("specialist_team_with_red_team", seed, floor.floor_id, floor.holdout,
                    candidate, evaluate_plan(floor, candidate, c, w))
    trace = {"observation": o, "roles": roles, "proposals": proposals,
             "synthesized_plan": asdict(synthesized), "red_team_findings": findings,
             "final_candidate_plan": asdict(candidate), "referee_ground_truth": asdict(floor)}
    return b, a, trace


def _result(r: FloorResult) -> dict[str, Any]:
    return {"architecture": r.architecture, "seed": r.seed, "floor_id": r.floor_id,
            "holdout": r.holdout, "plan": asdict(r.plan), "metrics": asdict(r.metrics)}


def _aggregate(rows: list[FloorResult]) -> dict[str, Any]:
    out = {}
    for arch in sorted({r.architecture for r in rows}):
        xs, hs = [r for r in rows if r.architecture == arch], [r for r in rows if r.architecture == arch and r.holdout]
        out[arch] = {
            "trials": len(xs), "score_mean": mean(r.metrics.score for r in xs),
            "service_rate_mean": mean(r.metrics.service_rate for r in xs),
            "latency_index_mean": mean(r.metrics.latency_index for r in xs),
            "energy_index_mean": mean(r.metrics.energy_index for r in xs),
            "thermal_index_mean": mean(r.metrics.thermal_index for r in xs),
            "resilience_index_mean": mean(r.metrics.resilience_index for r in xs),
            "constraint_violations_total": sum(r.metrics.violations for r in xs),
            "holdout_score_mean": mean(r.metrics.score for r in hs),
            "holdout_constraint_violations_total": sum(r.metrics.violations for r in hs),
        }
    return out


def _paired(rows: list[FloorResult]) -> dict[str, float]:
    by = {}
    for r in rows: by.setdefault((r.seed, r.floor_id), {})[r.architecture] = r
    pairs = [p for p in by.values() if {"locked_baseline", "specialist_team_with_red_team"} <= set(p)]
    return {
        "paired_trials": float(len(pairs)),
        "score_delta_mean": mean(p["specialist_team_with_red_team"].metrics.score - p["locked_baseline"].metrics.score for p in pairs),
        "service_rate_delta_points_mean": 100 * mean(p["specialist_team_with_red_team"].metrics.service_rate - p["locked_baseline"].metrics.service_rate for p in pairs),
        "violation_delta_mean": mean(p["specialist_team_with_red_team"].metrics.violations - p["locked_baseline"].metrics.violations for p in pairs),
    }


def _write_event(handle, event: Mapping[str, Any], previous: str) -> str:
    body = dict(event); body["previous_event_sha256"] = previous
    event_hash = sha256_text(canonical_json(body)); body["event_sha256"] = event_hash
    handle.write(canonical_json(body) + "\n")
    return event_hash


def _scorecard(s: Mapping[str, Any]) -> str:
    a, d = s["aggregate"], s["paired_deltas"]
    return "\n".join([
        "# LumenCore Agent Arena — Synthetic Scorecard", "",
        f"**Evidence boundary:** {s['evidence_boundary']}", "",
        f"- Scenario lock SHA-256: `{s['scenario_sha256']}`",
        f"- Event-chain root SHA-256: `{s['event_chain_root_sha256']}`",
        f"- Paired trials: {int(d['paired_trials'])}", "",
        "## Locked baseline", "",
        f"- Mean score: {a['locked_baseline']['score_mean']:.6f}",
        f"- Total constraint violations: {a['locked_baseline']['constraint_violations_total']}", "",
        "## Specialist team + red team", "",
        f"- Mean score: {a['specialist_team_with_red_team']['score_mean']:.6f}",
        f"- Total constraint violations: {a['specialist_team_with_red_team']['constraint_violations_total']}", "",
        "## Paired synthetic deltas", "",
        f"- Mean score delta: {d['score_delta_mean']:.6f}",
        f"- Mean service-rate delta: {d['service_rate_delta_points_mean']:.6f} percentage points",
        f"- Mean violation delta: {d['violation_delta_mean']:.6f}", "",
        "A positive delta means only that the reference policy scored higher inside the locked abstract model. The next promotion gate is qualified non-author execution against a buyer-approved dataset, baseline, metric, threshold, and failure rule.", "",
    ])


def run_arena(out_dir: Path = DEFAULT_OUT, config_path: Path = DEFAULT_CONFIG,
              provider: ProposalProvider = deterministic_provider, generated_utc: str | None = None) -> dict[str, Any]:
    cfg = load_config(config_path); out_dir.mkdir(parents=True, exist_ok=True)
    raw = config_path.read_bytes(); scenario_sha = hashlib.sha256(raw).hexdigest()
    (out_dir / "scenario.lock.json").write_bytes(raw)
    floors, rows = [_floor_from_config(x) for x in cfg["floors"]], []
    event_path, root = out_dir / "events.jsonl", "0" * 64
    with event_path.open("w", encoding="utf-8", newline="\n") as h:
        root = _write_event(h, {"event_type": "arena_start", "schema": SCHEMA,
            "evidence_boundary": EVIDENCE_BOUNDARY, "scenario_sha256": scenario_sha,
            "seeds": cfg["seeds"]}, root)
        for seed in cfg["seeds"]:
            for floor in floors:
                b, a, trace = run_floor(floor, seed, cfg, provider); rows += [b, a]
                root = _write_event(h, {"event_type": "floor_referee_decision", "seed": seed,
                    "floor_id": floor.floor_id, "holdout": floor.holdout, "trace": trace,
                    "baseline": _result(b), "candidate": _result(a)}, root)
        root = _write_event(h, {"event_type": "arena_complete", "result_rows": len(rows)}, root)
    summary = {
        "schema": SCHEMA, "generated_utc": generated_utc or datetime.now(timezone.utc).isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY, "git_commit": _git_commit(),
        "scenario_sha256": scenario_sha, "event_chain_root_sha256": root,
        "configuration": {"seeds": cfg["seeds"], "floors": [asdict(x) for x in floors],
            "agent_roles": cfg["agent_roles"], "baseline_plan": asdict(baseline_plan(cfg)),
            "control_bounds": cfg["control_bounds"], "constraints": cfg["constraints"],
            "score_weights": cfg["score_weights"]},
        "aggregate": _aggregate(rows), "paired_deltas": _paired(rows),
        "claim_boundary": cfg["claim_boundary"], "next_validation_gate": cfg["next_validation_gate"],
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out_dir / "SCORECARD.md").write_text(_scorecard(summary), encoding="utf-8")
    files = ["scenario.lock.json", "events.jsonl", "summary.json", "SCORECARD.md"]
    manifest = {"schema": "lumencore.agent_arena.manifest.v1", "evidence_boundary": EVIDENCE_BOUNDARY,
        "event_chain_root_sha256": root, "files": {n: {"bytes": (out_dir/n).stat().st_size,
        "sha256": sha256_file(out_dir/n)} for n in files}}
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def verify_bundle(out_dir: Path) -> dict[str, Any]:
    mp = out_dir / "manifest.sha256.json"; m = json.loads(mp.read_text(encoding="utf-8"))
    if m.get("schema") != "lumencore.agent_arena.manifest.v1" or m.get("evidence_boundary") != EVIDENCE_BOUNDARY:
        raise ValueError("manifest identity mismatch")
    expected = {"scenario.lock.json", "events.jsonl", "summary.json", "SCORECARD.md"}
    if set(m.get("files", {})) != expected: raise ValueError("manifest file set mismatch")
    for name, meta in m["files"].items():
        p = out_dir / name
        if not p.is_file(): raise ValueError(f"missing artifact: {name}")
        if p.stat().st_size != int(meta["bytes"]): raise ValueError(f"byte-count mismatch: {name}")
        if sha256_file(p) != meta["sha256"]: raise ValueError(f"sha256 mismatch: {name}")
    lock = out_dir / "scenario.lock.json"; cfg = load_config(lock); scenario_sha = sha256_file(lock)
    previous, first, last, count = "0" * 64, None, None, 0
    for count, line in enumerate((out_dir/"events.jsonl").read_text(encoding="utf-8").splitlines(), 1):
        event = json.loads(line); first = first or dict(event); last = dict(event)
        if event.get("previous_event_sha256") != previous: raise ValueError(f"event predecessor mismatch at line {count}")
        claimed = event.pop("event_sha256")
        if claimed != sha256_text(canonical_json(event)): raise ValueError(f"event hash mismatch at line {count}")
        previous = claimed
    if not first or first.get("event_type") != "arena_start" or first.get("scenario_sha256") != scenario_sha:
        raise ValueError("arena_start mismatch")
    if not last or last.get("event_type") != "arena_complete": raise ValueError("arena_complete mismatch")
    if previous != m["event_chain_root_sha256"]: raise ValueError("event chain root mismatch")
    s = json.loads((out_dir/"summary.json").read_text(encoding="utf-8"))
    if s.get("event_chain_root_sha256") != previous or s.get("scenario_sha256") != scenario_sha:
        raise ValueError("summary custody mismatch")
    if count != len(cfg["seeds"]) * len(cfg["floors"]) + 2: raise ValueError("event count mismatch")
    return {"status": "VERIFIED", "event_lines": count, "event_chain_root_sha256": previous,
            "manifest_sha256": sha256_file(mp), "files_verified": sorted(m["files"]),
            "evidence_boundary": EVIDENCE_BOUNDARY}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run"); run.add_argument("--config", type=Path, default=DEFAULT_CONFIG); run.add_argument("--out", type=Path, default=DEFAULT_OUT)
    verify = sub.add_parser("verify"); verify.add_argument("--out", type=Path, default=DEFAULT_OUT)
    a = p.parse_args(argv)
    if a.command == "run":
        s = run_arena(a.out, a.config); print(json.dumps({"status": "COMPLETE", "out": str(a.out),
            "event_chain_root_sha256": s["event_chain_root_sha256"], "evidence_boundary": EVIDENCE_BOUNDARY}, sort_keys=True))
    else: print(json.dumps(verify_bundle(a.out), sort_keys=True))
    return 0


if __name__ == "__main__": raise SystemExit(main())
