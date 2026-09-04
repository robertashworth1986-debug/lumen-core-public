#!/usr/bin/env python3
"""Frozen manufacturing-tolerance uncertainty sweep for flexible traces.

Purely computational screening. Results are not experimental validation and do
not establish qualification for any military, aerospace, medical, or safety-
critical use.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "experiments" / "flexible_electronics" / "phase1_trace_reliability_config.json"
OUT = ROOT / "out" / "flexible-electronics-phase1"
SEED = 26090401
DRAWS = 1000


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def geom_length_factor(name: str) -> float:
    # Frozen factors from the nominal path family; this sweep tests process
    # tolerances rather than re-optimizing geometry after seeing outcomes.
    return {
        "straight": 1.00,
        "sinusoid": 1.57,
        "serpentine": 1.92,
        "chirped_sinusoid": 1.63,
    }[name]


def run():
    cfg = json.loads(CFG.read_text())
    rng = random.Random(SEED)
    a = cfg["acceptance"]
    e = cfg["environment"]
    trace = cfg["trace"]
    width_m_nom = trace["width_mm"] * 1e-3
    thick_m_nom = trace["thickness_um"] * 1e-6
    base_length_m = cfg["footprint_mm"]["width"] * 1e-3

    rows = []
    for material in cfg["materials"]:
        for geom in cfg["geometries"]:
            accepted = 0
            scores = []
            temps = []
            resistances = []
            failures = {"geometry_or_process": 0, "thermal": 0}
            for _ in range(DRAWS):
                # Conservative, bounded process variation assumptions for
                # screening only; replace with measured process distributions.
                width_m = width_m_nom * clamp(rng.gauss(1.0, 0.06), 0.75, 1.25)
                thick_m = thick_m_nom * clamp(rng.gauss(1.0, 0.10), 0.60, 1.40)
                rho = material["resistivity_ohm_m"] * clamp(rng.gauss(1.0, 0.12), 0.65, 1.60)
                thermal_r = e["lumped_thermal_resistance_c_per_w"] * clamp(rng.gauss(1.0, 0.15), 0.50, 1.70)
                length_m = base_length_m * geom_length_factor(geom) * clamp(rng.gauss(1.0, 0.015), 0.95, 1.05)
                resistance = rho * length_m / (width_m * thick_m)
                power = e["current_a"] ** 2 * resistance
                temp_c = e["ambient_c"] + power * thermal_r
                process_ok = width_m >= a["min_trace_width_mm"] * 1e-3 and thick_m >= a["min_trace_thickness_um"] * 1e-6
                thermal_ok = temp_c <= min(a["max_estimated_temp_c"], material["max_operating_c"])
                if not process_ok:
                    failures["geometry_or_process"] += 1
                if not thermal_ok:
                    failures["thermal"] += 1
                ok = process_ok and thermal_ok
                accepted += int(ok)
                score = resistance / a["reference_resistance_ohm"] + max(0.0, temp_c - e["ambient_c"]) / 75.0
                scores.append(score)
                temps.append(temp_c)
                resistances.append(resistance)

            def pct(values, q):
                s = sorted(values)
                idx = int(round((len(s) - 1) * q))
                return s[idx]

            rows.append({
                "material": material["name"],
                "geometry": geom,
                "draws": DRAWS,
                "seed": SEED,
                "acceptance_rate": accepted / DRAWS,
                "resistance_p50_ohm": pct(resistances, 0.50),
                "resistance_p95_ohm": pct(resistances, 0.95),
                "temp_p50_c": pct(temps, 0.50),
                "temp_p95_c": pct(temps, 0.95),
                "score_p50": pct(scores, 0.50),
                "score_p95": pct(scores, 0.95),
                "process_failures": failures["geometry_or_process"],
                "thermal_failures": failures["thermal"],
            })
    return rows


def write(rows):
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "manufacturing_uncertainty_sweep.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    best = max(rows, key=lambda r: (r["acceptance_rate"], -r["score_p95"]))
    summary = {
        "schema_version": "1.0",
        "draws_per_candidate": DRAWS,
        "seed": SEED,
        "candidate_count": len(rows),
        "best_screening_candidate": best,
        "claim_boundary": "computational_tolerance_screen_only",
        "experimentally_validated": False,
        "process_distributions_measured": False,
        "limitations": [
            "Tolerance distributions are assumed, not measured from a printing process.",
            "Electrical and thermal models are lumped analytic proxies.",
            "Use only to prioritize physical coupons and calibration experiments."
        ],
    }
    (OUT / "uncertainty_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    manifest = {
        "manufacturing_uncertainty_sweep.csv": hashlib.sha256(path.read_bytes()).hexdigest(),
        "uncertainty_summary.json": hashlib.sha256((OUT / "uncertainty_summary.json").read_bytes()).hexdigest(),
    }
    (OUT / "uncertainty_sha256.json").write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    rows = run()
    write(rows)
    print(json.dumps({"status": "ok", "candidates": len(rows), "draws_per_candidate": DRAWS, "seed": SEED}))
