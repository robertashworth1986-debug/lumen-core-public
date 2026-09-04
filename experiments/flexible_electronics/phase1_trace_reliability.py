#!/usr/bin/env python3
"""Bounded simulation study for additively manufactured flexible conductors.

This is a feasibility / ranking model only. It does not claim MIL-STD compliance,
physical validation, RF qualification, or experimental validation.

The study compares candidate 2-D trace paths under frozen footprint, material,
and operating assumptions. Outputs retain all candidates, including failures.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "experiments" / "flexible_electronics" / "phase1_trace_reliability_config.json"
OUT_DIR = ROOT / "out" / "flexible-electronics-phase1"


@dataclass(frozen=True)
class Material:
    name: str
    resistivity_ohm_m: float
    tempco_per_c: float
    max_operating_c: float
    fatigue_exponent: float


@dataclass(frozen=True)
class CandidateResult:
    material: str
    geometry: str
    bend_radius_mm: float
    stretch_pct: float
    path_length_mm: float
    resistance_ohm_25c: float
    resistance_ohm_hot: float
    power_w: float
    estimated_temp_c: float
    max_curvature_1_per_mm: float
    strain_proxy_pct: float
    fatigue_damage_proxy: float
    footprint_efficiency: float
    manufacturability_pass: bool
    thermal_pass: bool
    strain_pass: bool
    primary_score: float
    accepted: bool
    failure_reasons: str


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def linspace(a: float, b: float, n: int) -> List[float]:
    if n <= 1:
        return [a]
    return [a + (b - a) * i / (n - 1) for i in range(n)]


def polyline_length(points: Iterable[Tuple[float, float]]) -> float:
    pts = list(points)
    return sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:]))


def max_discrete_curvature(points: List[Tuple[float, float]]) -> float:
    curvatures = []
    for a, b, c in zip(points, points[1:], points[2:]):
        ab = math.hypot(b[0] - a[0], b[1] - a[1])
        bc = math.hypot(c[0] - b[0], c[1] - b[1])
        ac = math.hypot(c[0] - a[0], c[1] - a[1])
        if min(ab, bc, ac) <= 1e-12:
            continue
        area2 = abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]))
        kappa = 2.0 * area2 / (ab * bc * ac)
        curvatures.append(kappa)
    return max(curvatures, default=0.0)


def geometry_points(name: str, width_mm: float, height_mm: float, samples: int = 401) -> List[Tuple[float, float]]:
    xs = linspace(0.0, width_mm, samples)
    if name == "straight":
        return [(x, height_mm / 2.0) for x in xs]
    if name == "sinusoid":
        amp = 0.30 * height_mm
        cycles = 3.0
        return [(x, height_mm / 2.0 + amp * math.sin(2.0 * math.pi * cycles * x / width_mm)) for x in xs]
    if name == "serpentine":
        amp = 0.34 * height_mm
        cycles = 4.0
        return [(x, height_mm / 2.0 + amp * math.tanh(3.0 * math.sin(2.0 * math.pi * cycles * x / width_mm))) for x in xs]
    if name == "chirped_sinusoid":
        amp = 0.28 * height_mm
        pts = []
        for x in xs:
            u = x / width_mm
            phase = 2.0 * math.pi * (2.0 * u + 2.0 * u * u)
            pts.append((x, height_mm / 2.0 + amp * math.sin(phase)))
        return pts
    raise ValueError(f"unknown geometry: {name}")


def strain_proxy(trace_kappa_per_mm: float, bend_radius_mm: float, substrate_thickness_mm: float,
                 conductor_thickness_mm: float, stretch_pct: float, tortuosity: float) -> float:
    # Substrate bending strain plus path-curvature concentration and reduced axial
    # strain due to geometric slack. This is explicitly a proxy, not an FEA result.
    neutral_offset_mm = 0.5 * (substrate_thickness_mm + conductor_thickness_mm)
    bend = neutral_offset_mm / bend_radius_mm
    curvature_penalty = min(0.02, trace_kappa_per_mm * conductor_thickness_mm * 0.25)
    axial = (stretch_pct / 100.0) / max(tortuosity, 1.0)
    return 100.0 * (bend + curvature_penalty + axial)


def run() -> List[CandidateResult]:
    cfg = load_config()
    footprint = cfg["footprint_mm"]
    trace = cfg["trace"]
    env = cfg["environment"]
    criteria = cfg["acceptance"]
    thermal_r = env["lumped_thermal_resistance_c_per_w"]
    ambient = env["ambient_c"]
    current = env["current_a"]

    materials = [Material(**m) for m in cfg["materials"]]
    results: List[CandidateResult] = []

    for material in materials:
        for geom in cfg["geometries"]:
            pts = geometry_points(geom, footprint["width"], footprint["height"])
            length_mm = polyline_length(pts)
            direct_mm = footprint["width"]
            tortuosity = length_mm / direct_mm
            kappa = max_discrete_curvature(pts)
            cross_section_m2 = (trace["width_mm"] * 1e-3) * (trace["thickness_um"] * 1e-6)
            r25 = material.resistivity_ohm_m * (length_mm * 1e-3) / cross_section_m2

            for bend_radius in cfg["bend_radius_mm"]:
                for stretch_pct in cfg["stretch_pct"]:
                    # one-pass thermal estimate with material TCR
                    p25 = current * current * r25
                    t_est = ambient + p25 * thermal_r
                    rhot = r25 * (1.0 + material.tempco_per_c * max(0.0, t_est - 25.0))
                    power = current * current * rhot
                    t_est = ambient + power * thermal_r

                    strain = strain_proxy(
                        kappa, bend_radius, trace["substrate_thickness_mm"],
                        trace["thickness_um"] / 1000.0, stretch_pct, tortuosity
                    )
                    damage = (max(strain, 1e-9) / criteria["max_strain_proxy_pct"]) ** material.fatigue_exponent
                    footprint_eff = direct_mm / max(length_mm, 1e-9)

                    manufacturable = (
                        trace["width_mm"] >= criteria["min_trace_width_mm"]
                        and trace["thickness_um"] >= criteria["min_trace_thickness_um"]
                        and tortuosity <= criteria["max_tortuosity"]
                    )
                    thermal_pass = t_est <= min(criteria["max_estimated_temp_c"], material.max_operating_c)
                    strain_pass = strain <= criteria["max_strain_proxy_pct"]

                    # Primary metric: lower is better. It penalizes resistance,
                    # thermal rise, and strain damage; failed constraints cannot win.
                    norm_r = rhot / criteria["reference_resistance_ohm"]
                    norm_temp = max(0.0, t_est - ambient) / max(1.0, criteria["max_estimated_temp_c"] - ambient)
                    primary = 0.45 * norm_r + 0.20 * norm_temp + 0.35 * damage
                    reasons = []
                    if not manufacturable:
                        reasons.append("manufacturability")
                    if not thermal_pass:
                        reasons.append("thermal")
                    if not strain_pass:
                        reasons.append("strain")
                    accepted = manufacturable and thermal_pass and strain_pass
                    if not accepted:
                        primary += 1000.0

                    results.append(CandidateResult(
                        material=material.name,
                        geometry=geom,
                        bend_radius_mm=bend_radius,
                        stretch_pct=stretch_pct,
                        path_length_mm=length_mm,
                        resistance_ohm_25c=r25,
                        resistance_ohm_hot=rhot,
                        power_w=power,
                        estimated_temp_c=t_est,
                        max_curvature_1_per_mm=kappa,
                        strain_proxy_pct=strain,
                        fatigue_damage_proxy=damage,
                        footprint_efficiency=footprint_eff,
                        manufacturability_pass=manufacturable,
                        thermal_pass=thermal_pass,
                        strain_pass=strain_pass,
                        primary_score=primary,
                        accepted=accepted,
                        failure_reasons=";".join(reasons),
                    ))
    return results


def write_outputs(results: List[CandidateResult]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows = [asdict(r) for r in results]
    csv_path = OUT_DIR / "trace_reliability_matrix.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    accepted = [r for r in results if r.accepted]
    champion = min(accepted, key=lambda r: r.primary_score) if accepted else None
    baseline = [r for r in results if r.geometry == "straight"]
    summary = {
        "schema_version": "1.0",
        "claim_level": "physics_informed_proxy_only",
        "experimentally_validated": False,
        "mil_std_qualified": False,
        "rf_mcm_qualified": False,
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "candidate_count": len(results),
        "accepted_count": len(accepted),
        "rejected_count": len(results) - len(accepted),
        "negative_results_retained": True,
        "straight_baseline_count": len(baseline),
        "best_accepted_candidate": asdict(champion) if champion else None,
        "limitations": [
            "Analytic proxy model only; no FEA, RF simulation, fabrication, instrumentation, or environmental testing.",
            "Material values are frozen engineering assumptions for ranking, not lot-specific characterization.",
            "No MIL-STD compliance or reliability qualification is inferred from these outputs.",
            "Physical Phase I work must replace proxy strain/thermal models with calibrated simulation and measured coupons."
        ],
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    manifest = {}
    for p in sorted(OUT_DIR.glob("*")):
        if p.is_file() and p.name != "sha256_manifest.json":
            manifest[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
    (OUT_DIR / "sha256_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    output = run()
    write_outputs(output)
    print(json.dumps({
        "status": "ok",
        "rows": len(output),
        "accepted": sum(1 for r in output if r.accepted),
        "out_dir": str(OUT_DIR),
    }))
