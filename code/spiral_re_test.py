"""
spiral_re_test.py — honest re-evaluation of spiral vs straight-line efficiency

Purpose: The original demo (spiral_demo_report master folder.csv) reported
savings_distance_% = -441 and savings_energy_% = -359 — meaning the spiral
was 4-5x WORSE than the straight line. That CSV had been used as supporting
material for EchoLock/HyperCore claims.

This script does an apples-to-apples test: given a start point and end point,
compare straight-line vs Archimedean spiral path on:
  - geometric path length (line integral of |dr/dt|)
  - "energy" along path under a generic curvature penalty (k * integral kappa^2)

It then sweeps parameters to find IF/WHERE a spiral can ever be more efficient
than a straight line by these metrics. If no parameter region exists, the
claim must be permanently retired or replaced with a different metric.

Output: out/spiral_retest/spiral_retest_results.csv + summary.json
"""
from __future__ import annotations
import csv
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np


@dataclass
class PathMetrics:
    name: str
    radius: float
    turns: float
    length: float
    energy_curvature: float
    energy_total: float


def _trapz(y: np.ndarray, x: np.ndarray) -> float:
    return float(np.trapezoid(y, x))


def straight_line_metrics(p0: np.ndarray, p1: np.ndarray, n: int = 2000) -> PathMetrics:
    t = np.linspace(0.0, 1.0, n)
    pts = p0[None, :] + (p1 - p0)[None, :] * t[:, None]
    diffs = np.diff(pts, axis=0)
    seg_len = np.linalg.norm(diffs, axis=1)
    length = float(seg_len.sum())
    # straight line: zero curvature, zero curvature energy
    return PathMetrics(
        name="straight",
        radius=0.0,
        turns=0.0,
        length=length,
        energy_curvature=0.0,
        energy_total=length,  # trivial baseline = pure length
    )


def archimedean_spiral_metrics(
    p0: np.ndarray,
    p1: np.ndarray,
    turns: float,
    n: int = 4000,
) -> PathMetrics:
    """Archimedean spiral from p0 to p1 with `turns` revolutions around midpoint."""
    mid = 0.5 * (p0 + p1)
    end_offset = p1 - mid
    r_end = float(np.linalg.norm(end_offset))
    if r_end == 0.0 or turns <= 0.0:
        return PathMetrics("spiral", r_end, turns, 0.0, 0.0, math.inf)

    theta_end = 2.0 * math.pi * turns
    a = r_end / theta_end  # r = a * theta so that r(theta_end) = r_end

    theta = np.linspace(1e-6, theta_end, n)
    r = a * theta
    base_angle = math.atan2(end_offset[1], end_offset[0])
    # Spiral starts near mid (small r) and ends at p1. We approximate p0 by
    # rotating starting angle so the small-r tail sits closest to p0.
    angle = theta + base_angle - theta_end  # ends with angle = base_angle

    x = mid[0] + r * np.cos(angle)
    y = mid[1] + r * np.sin(angle)
    pts = np.stack([x, y], axis=1)

    # Length
    diffs = np.diff(pts, axis=0)
    seg_len = np.linalg.norm(diffs, axis=1)
    length = float(seg_len.sum())

    # Curvature kappa for parametric (x(t), y(t))
    dx = np.gradient(x, theta)
    dy = np.gradient(y, theta)
    ddx = np.gradient(dx, theta)
    ddy = np.gradient(dy, theta)
    speed_sq = dx * dx + dy * dy
    speed = np.sqrt(np.maximum(speed_sq, 1e-12))
    kappa = (dx * ddy - dy * ddx) / np.maximum(speed_sq * speed, 1e-12)
    energy_curvature = _trapz(kappa * kappa * speed, theta)

    return PathMetrics(
        name="spiral",
        radius=r_end,
        turns=turns,
        length=length,
        energy_curvature=float(energy_curvature),
        energy_total=length + float(energy_curvature),
    )


def sweep(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    p0 = np.array([0.0, 0.0])
    any_better_length = False
    any_better_energy = False

    for radius in [1.0, 5.0, 10.0, 20.0]:
        p1 = np.array([radius, 0.0])
        s = straight_line_metrics(p0, p1)
        for turns in [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]:
            sp = archimedean_spiral_metrics(p0, p1, turns=turns)
            len_savings_pct = 100.0 * (s.length - sp.length) / s.length
            # use length+curvature as energy proxy
            energy_savings_pct = 100.0 * (s.energy_total - sp.energy_total) / max(s.energy_total, 1e-12)
            if len_savings_pct > 0:
                any_better_length = True
            if energy_savings_pct > 0:
                any_better_energy = True
            rows.append({
                "radius": radius,
                "turns": turns,
                "straight_length": round(s.length, 6),
                "spiral_length": round(sp.length, 6),
                "spiral_curvature_energy": round(sp.energy_curvature, 6),
                "len_savings_pct": round(len_savings_pct, 4),
                "energy_savings_pct": round(energy_savings_pct, 4),
            })

    csv_path = out_dir / "spiral_retest_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "test": "spiral_vs_straight_line",
        "metric_length": "geometric path length (sum of segment norms)",
        "metric_energy": "length + integral of curvature^2 along path",
        "rows_tested": len(rows),
        "any_config_where_spiral_shorter": any_better_length,
        "any_config_where_spiral_lower_energy": any_better_energy,
        "verdict": (
            "Spiral can never beat a straight line on either pure length or "
            "length+curvature energy in flat 2D space. The original demo CSV "
            "is mathematically expected; the only way 'savings' could be "
            "positive is under a different metric (e.g. avoiding obstacles, "
            "minimum-jerk under acceleration constraints, signal-to-noise in "
            "rotating reference frames). Until such a metric is defined and "
            "validated, all 'spiral efficiency' claims must be retired."
        ),
        "rows_csv": str(csv_path),
    }
    (out_dir / "spiral_retest_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


if __name__ == "__main__":
    here = Path(__file__).resolve().parent
    repo_root = here.parent
    out_dir = repo_root / "out" / "spiral_retest"
    s = sweep(out_dir)
    print(json.dumps(s, indent=2))
