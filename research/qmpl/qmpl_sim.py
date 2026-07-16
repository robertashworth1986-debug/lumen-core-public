#!/usr/bin/env python3
"""
Public-safe QuantaMechoPhaseLocking (QMPL) validation harness.

This implements standard, generic second-order coupled-oscillator and formation
transition baselines. It does not implement proprietary adaptive weighting,
private shape-selection logic, flight control, targeting, or operational drone
autonomy.

Outputs are simulation evidence only.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


TAU = 2.0 * math.pi


def wrap_angle(x: np.ndarray) -> np.ndarray:
    return (x + math.pi) % TAU - math.pi


def quantize_angle(x: np.ndarray, bins: Optional[int]) -> np.ndarray:
    wrapped = wrap_angle(x)
    if bins is None or bins <= 0:
        return wrapped
    step = TAU / float(bins)
    return np.round(wrapped / step) * step


def sha256_file(path: Optional[Path]) -> Optional[str]:
    if path is None or not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class RunSpec:
    agent_count: int
    coupling_gain: float
    phase_bins: Optional[int]
    packet_loss: float
    sensor_noise: float
    latency_steps: int
    frequency_spread: float
    damping: float
    inertia: float
    seed: int
    duration_s: float
    dt_s: float
    disturbance_time_s: float
    disturbance_phase_rad: float


def _fixed_latency_observation(
    history: Sequence[np.ndarray],
    latency_steps: int,
) -> np.ndarray:
    if latency_steps <= 0 or len(history) <= latency_steps:
        return history[-1]
    return history[-1 - latency_steps]


def simulate_phase_lock(spec: RunSpec) -> Dict[str, Any]:
    rng = np.random.default_rng(spec.seed)
    n = spec.agent_count
    steps = int(round(spec.duration_s / spec.dt_s))

    theta = rng.uniform(-math.pi, math.pi, size=n)
    velocity = rng.normal(0.0, 0.12, size=n)
    natural_velocity = rng.normal(0.0, spec.frequency_spread, size=n)
    natural_velocity -= natural_velocity.mean()

    theta_history: List[np.ndarray] = [theta.copy()]
    coherence_history = np.zeros(steps, dtype=float)
    freq_std_history = np.zeros(steps, dtype=float)
    control_energy = 0.0
    disturbance_step = int(round(spec.disturbance_time_s / spec.dt_s))
    disturbance_applied = False

    lock_threshold_r = 0.90
    lock_threshold_freq_std = 0.05
    lock_hold_steps = max(2, int(round(1.0 / spec.dt_s)))
    first_lock_time: Optional[float] = None
    recovery_time: Optional[float] = None
    pre_disturbance_locked = False

    for step in range(steps):
        t = step * spec.dt_s

        if step == disturbance_step:
            theta[: max(1, n // 2)] = wrap_angle(
                theta[: max(1, n // 2)] + spec.disturbance_phase_rad
            )
            disturbance_applied = True

        observed = _fixed_latency_observation(theta_history, spec.latency_steps).copy()
        if spec.sensor_noise > 0.0:
            observed += rng.normal(0.0, spec.sensor_noise, size=n)

        delta = observed[None, :] - theta[:, None]
        delta = quantize_angle(delta, spec.phase_bins)

        if spec.packet_loss > 0.0:
            message_mask = rng.random((n, n)) >= spec.packet_loss
            np.fill_diagonal(message_mask, False)
        else:
            message_mask = np.ones((n, n), dtype=bool)
            np.fill_diagonal(message_mask, False)

        neighbor_counts = np.maximum(message_mask.sum(axis=1), 1)
        coupling = spec.coupling_gain * (
            (np.sin(delta) * message_mask).sum(axis=1) / neighbor_counts
        )

        acceleration = (
            spec.damping * (natural_velocity - velocity) + coupling
        ) / spec.inertia
        velocity = velocity + acceleration * spec.dt_s
        theta = wrap_angle(theta + velocity * spec.dt_s)

        theta_history.append(theta.copy())
        max_history = max(2, spec.latency_steps + 2)
        if len(theta_history) > max_history:
            theta_history.pop(0)

        coherence = abs(np.mean(np.exp(1j * theta)))
        freq_std = float(np.std(velocity))
        coherence_history[step] = coherence
        freq_std_history[step] = freq_std
        control_energy += float(np.mean(coupling ** 2)) * spec.dt_s

        if (
            step >= lock_hold_steps
            and np.all(coherence_history[step - lock_hold_steps + 1 : step + 1] >= lock_threshold_r)
            and np.all(freq_std_history[step - lock_hold_steps + 1 : step + 1] <= lock_threshold_freq_std)
        ):
            candidate_time = t - (lock_hold_steps - 1) * spec.dt_s
            if first_lock_time is None and step < disturbance_step:
                first_lock_time = max(0.0, candidate_time)
                pre_disturbance_locked = True
            if disturbance_applied and recovery_time is None and step > disturbance_step:
                recovery_time = max(0.0, candidate_time - spec.disturbance_time_s)

    final_window = max(1, int(round(3.0 / spec.dt_s)))
    final_coherence = float(np.mean(coherence_history[-final_window:]))
    final_freq_std = float(np.mean(freq_std_history[-final_window:]))
    worst_post_disturbance_coherence = float(
        np.min(coherence_history[disturbance_step:])
    ) if disturbance_step < steps else float("nan")

    if spec.phase_bins is None:
        bits_per_phase = 32
        phase_mode = "continuous"
    else:
        bits_per_phase = max(1, int(math.ceil(math.log2(max(2, spec.phase_bins)))))
        phase_mode = str(spec.phase_bins)

    update_rate_hz = 1.0 / spec.dt_s
    estimated_bytes_per_agent_s = (
        max(1, n - 1) * bits_per_phase / 8.0 * update_rate_hz * (1.0 - spec.packet_loss)
    )

    passed = bool(final_coherence >= 0.90 and final_freq_std <= 0.05)

    return {
        "system": "second_order_phase_network",
        "agent_count": n,
        "coupling_gain": spec.coupling_gain,
        "phase_bins": phase_mode,
        "packet_loss": spec.packet_loss,
        "sensor_noise": spec.sensor_noise,
        "latency_steps": spec.latency_steps,
        "frequency_spread": spec.frequency_spread,
        "damping": spec.damping,
        "inertia": spec.inertia,
        "seed": spec.seed,
        "duration_s": spec.duration_s,
        "dt_s": spec.dt_s,
        "disturbance_time_s": spec.disturbance_time_s,
        "disturbance_phase_rad": spec.disturbance_phase_rad,
        "final_coherence": final_coherence,
        "final_frequency_std": final_freq_std,
        "time_to_lock_s": first_lock_time,
        "recovery_time_s": recovery_time,
        "pre_disturbance_locked": pre_disturbance_locked,
        "worst_post_disturbance_coherence": worst_post_disturbance_coherence,
        "control_energy_proxy": control_energy,
        "estimated_bytes_per_agent_s": estimated_bytes_per_agent_s,
        "pass": passed,
    }


def target_shape(name: str, n: int, spacing: float = 1.0) -> np.ndarray:
    name = name.lower()
    if name == "line":
        x = (np.arange(n) - (n - 1) / 2.0) * spacing
        return np.column_stack([x, np.zeros(n)])
    if name == "ring":
        angles = np.linspace(0.0, TAU, n, endpoint=False)
        radius = max(spacing, n * spacing / TAU)
        return np.column_stack([radius * np.cos(angles), radius * np.sin(angles)])
    if name == "v":
        points = np.zeros((n, 2), dtype=float)
        for i in range(n):
            side = -1.0 if i % 2 == 0 else 1.0
            rank = (i + 1) // 2
            points[i] = [rank * spacing, side * rank * spacing * 0.65]
        points -= points.mean(axis=0)
        return points
    if name == "echelon":
        k = np.arange(n) - (n - 1) / 2.0
        return np.column_stack([k * spacing, k * spacing * 0.55])
    raise ValueError(f"Unsupported shape: {name}")


def simulate_formation_transition(
    n: int,
    start_shape: str,
    end_shape: str,
    seed: int,
    duration_s: float = 20.0,
    dt_s: float = 0.02,
    spacing: float = 1.0,
    position_gain: float = 1.8,
    damping: float = 1.2,
    separation_radius: float = 0.55,
    separation_gain: float = 0.35,
) -> Dict[str, Any]:
    """
    Generic 2D kinematic formation transition baseline.

    This is not an aerodynamic or flight-control model. It only measures
    convergence, path length, control effort, and separation behavior.
    """
    rng = np.random.default_rng(seed)
    target0 = target_shape(start_shape, n, spacing)
    target1 = target_shape(end_shape, n, spacing)
    position = target0 + rng.normal(0.0, 0.08, size=(n, 2))
    velocity = np.zeros((n, 2), dtype=float)
    steps = int(round(duration_s / dt_s))
    path_length = np.zeros(n, dtype=float)
    control_energy = 0.0
    min_separation = float("inf")
    convergence_time: Optional[float] = None
    threshold = 0.12
    hold_steps = max(2, int(round(0.8 / dt_s)))
    recent_errors: List[float] = []

    for step in range(steps):
        delta = position[:, None, :] - position[None, :, :]
        distance = np.linalg.norm(delta, axis=2) + np.eye(n)
        separation = np.zeros_like(position)
        close = (distance < separation_radius) & (~np.eye(n, dtype=bool))
        for i in range(n):
            if np.any(close[i]):
                vectors = delta[i, close[i]]
                dist = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-9
                separation[i] = np.sum(vectors / dist * (separation_radius - dist), axis=0)

        control = (
            position_gain * (target1 - position)
            - damping * velocity
            + separation_gain * separation
        )
        velocity += control * dt_s
        previous = position.copy()
        position += velocity * dt_s
        path_length += np.linalg.norm(position - previous, axis=1)
        control_energy += float(np.mean(np.sum(control ** 2, axis=1))) * dt_s

        pairwise = np.linalg.norm(
            position[:, None, :] - position[None, :, :], axis=2
        )
        np.fill_diagonal(pairwise, np.inf)
        min_separation = min(min_separation, float(np.min(pairwise)))

        rms_error = float(np.sqrt(np.mean(np.sum((target1 - position) ** 2, axis=1))))
        recent_errors.append(rms_error)
        if len(recent_errors) > hold_steps:
            recent_errors.pop(0)
        if convergence_time is None and len(recent_errors) == hold_steps and max(recent_errors) <= threshold:
            convergence_time = max(0.0, step * dt_s - (hold_steps - 1) * dt_s)

    final_rms_error = float(
        np.sqrt(np.mean(np.sum((target1 - position) ** 2, axis=1)))
    )
    passed = bool(final_rms_error <= threshold and min_separation >= 0.30)

    return {
        "system": "generic_2d_formation_transition",
        "agent_count": n,
        "start_shape": start_shape,
        "end_shape": end_shape,
        "seed": seed,
        "duration_s": duration_s,
        "dt_s": dt_s,
        "final_rms_error": final_rms_error,
        "transition_time_s": convergence_time,
        "min_separation": min_separation,
        "mean_path_length": float(np.mean(path_length)),
        "control_energy_proxy": control_energy,
        "pass": passed,
        "claim_boundary": (
            "Generic 2D kinematic convergence only; not aerodynamic efficiency, "
            "flight safety, certification, or operational swarm capability."
        ),
    }


def expand_specs(config: Dict[str, Any]) -> Iterable[RunSpec]:
    sweep = config["phase_sweep"]
    for n in sweep["agent_counts"]:
        for coupling in sweep["coupling_gains"]:
            for bins in sweep["phase_bins"]:
                bins_value = None if bins in (None, "continuous") else int(bins)
                for loss in sweep["packet_losses"]:
                    for noise in sweep["sensor_noises"]:
                        for latency in sweep["latency_steps"]:
                            for seed in sweep["seeds"]:
                                yield RunSpec(
                                    agent_count=int(n),
                                    coupling_gain=float(coupling),
                                    phase_bins=bins_value,
                                    packet_loss=float(loss),
                                    sensor_noise=float(noise),
                                    latency_steps=int(latency),
                                    frequency_spread=float(sweep["frequency_spread"]),
                                    damping=float(sweep["damping"]),
                                    inertia=float(sweep["inertia"]),
                                    seed=int(seed),
                                    duration_s=float(sweep["duration_s"]),
                                    dt_s=float(sweep["dt_s"]),
                                    disturbance_time_s=float(sweep["disturbance_time_s"]),
                                    disturbance_phase_rad=float(sweep["disturbance_phase_rad"]),
                                )


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    fields = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def summarize_phase(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {}
    passing = [r for r in rows if r["pass"]]
    best = max(
        rows,
        key=lambda r: (
            r["final_coherence"],
            -r["final_frequency_std"],
            -r["estimated_bytes_per_agent_s"],
        ),
    )
    return {
        "run_count": len(rows),
        "pass_count": len(passing),
        "pass_rate": len(passing) / len(rows),
        "mean_final_coherence": float(np.mean([r["final_coherence"] for r in rows])),
        "median_final_coherence": float(np.median([r["final_coherence"] for r in rows])),
        "mean_final_frequency_std": float(np.mean([r["final_frequency_std"] for r in rows])),
        "best_run": best,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--constants", type=Path)
    parser.add_argument("--lexicon", type=Path)
    args = parser.parse_args()

    config = json.loads(args.config.read_text(encoding="utf-8"))
    args.output.mkdir(parents=True, exist_ok=True)

    phase_rows: List[Dict[str, Any]] = []
    for spec in expand_specs(config):
        phase_rows.append(simulate_phase_lock(spec))

    formation_rows: List[Dict[str, Any]] = []
    formation = config.get("formation_sweep", {})
    if formation.get("enabled", True):
        for n in formation["agent_counts"]:
            for start in formation["start_shapes"]:
                for end in formation["end_shapes"]:
                    if start == end:
                        continue
                    for seed in formation["seeds"]:
                        formation_rows.append(
                            simulate_formation_transition(
                                n=int(n),
                                start_shape=str(start),
                                end_shape=str(end),
                                seed=int(seed),
                                duration_s=float(formation["duration_s"]),
                                dt_s=float(formation["dt_s"]),
                                spacing=float(formation["spacing"]),
                            )
                        )

    write_csv(args.output / "phase_sweep_results.csv", phase_rows)
    write_csv(args.output / "formation_transition_results.csv", formation_rows)

    source_path = Path(__file__).resolve()
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "claim_level": "simulation-only, public-safe baseline",
        "phase_summary": summarize_phase(phase_rows),
        "formation_summary": {
            "run_count": len(formation_rows),
            "pass_count": sum(1 for r in formation_rows if r["pass"]),
            "pass_rate": (
                sum(1 for r in formation_rows if r["pass"]) / len(formation_rows)
                if formation_rows else None
            ),
        },
        "claim_boundary": [
            "No external validation.",
            "No aerodynamic-efficiency claim.",
            "No flight certification or operational capability claim.",
            "No proprietary adaptive controller or private shape-selection logic included.",
        ],
    }
    (args.output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )

    manifest = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "config_path": str(args.config.resolve()),
        "config_sha256": sha256_file(args.config),
        "source_path": str(source_path),
        "source_sha256": sha256_file(source_path),
        "constants_path": str(args.constants.resolve()) if args.constants else None,
        "constants_sha256": sha256_file(args.constants),
        "lexicon_path": str(args.lexicon.resolve()) if args.lexicon else None,
        "lexicon_sha256": sha256_file(args.lexicon),
        "outputs": {},
    }
    for output_file in sorted(args.output.iterdir()):
        if output_file.is_file() and output_file.name != "manifest.json":
            manifest["outputs"][output_file.name] = sha256_file(output_file)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
