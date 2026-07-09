from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "artifacts"
ART.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 4444
random.seed(RANDOM_SEED)

CLAIM_BOUNDARY = (
    "Simulation-only synthetic benchmark. Not flight control, not aircraft certification, "
    "not airworthiness evidence, not propulsion design, not drone swarm control."
)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def honeycomb_cells(rings: int = 7) -> list[dict]:
    cells = []
    idx = 0
    for q in range(-rings, rings + 1):
        for r in range(-rings, rings + 1):
            s = -q - r
            ring = max(abs(q), abs(r), abs(s))
            if ring <= rings:
                x = math.sqrt(3) * q + (math.sqrt(3) / 2.0) * r
                y = 1.5 * r
                radius = math.sqrt(x*x + y*y)
                angle = math.atan2(y, x)
                cells.append({
                    "id": idx,
                    "q": q,
                    "r": r,
                    "s": s,
                    "ring": ring,
                    "x": x,
                    "y": y,
                    "radius": radius,
                    "angle": angle
                })
                idx += 1
    return cells

def route_points(kind: str, n: int = 500) -> list[tuple[float, float]]:
    pts = []
    if kind == "straight_grid":
        for i in range(n):
            t = (i / max(1, n - 1)) * 2.0 - 1.0
            pts.append((t * 12.0, 0.0))
    elif kind == "random_walk":
        x, y = 0.0, 0.0
        for _ in range(n):
            x += random.uniform(-0.45, 0.45)
            y += random.uniform(-0.45, 0.45)
            pts.append((x, y))
    elif kind == "uniform_ring":
        for i in range(n):
            theta = (2.0 * math.pi * i) / n
            pts.append((8.0 * math.cos(theta), 8.0 * math.sin(theta)))
    elif kind == "lumajet_champion_flowform":
        phi = 0.61803398875
        for i in range(n):
            t = i / max(1, n - 1)
            theta = t * 9.0 * math.pi
            radius = 0.15 + 0.42 * theta
            phase = 0.24 * math.sin(theta * phi)
            pts.append(((radius + phase) * math.cos(theta), (radius - phase) * math.sin(theta)))
    else:
        raise ValueError(kind)
    return pts

def nearest_distance(x: float, y: float, pts: list[tuple[float, float]]) -> float:
    best = 10**9
    for px, py in pts[::3]:
        d = math.sqrt((x - px)**2 + (y - py)**2)
        if d < best:
            best = d
    return best

def score_pattern(kind: str, cells: list[dict]) -> dict:
    pts = route_points(kind)
    distances = []
    thermal_proxy = []
    coverage = []
    for c in cells:
        d = nearest_distance(c["x"], c["y"], pts)
        distances.append(d)
        cov = 1.0 / (1.0 + d)
        coverage.append(cov)
        center_pressure = 1.0 / (1.0 + c["ring"])
        relief = 0.42 * cov
        thermal_proxy.append(max(0.0, center_pressure - relief + 0.03))

    mean_dist = statistics.mean(distances)
    mean_cov = statistics.mean(coverage)
    thermal_mean = statistics.mean(thermal_proxy)
    thermal_std = statistics.pstdev(thermal_proxy)
    balance = 1.0 / (1.0 + thermal_std)
    routing_efficiency = 1.0 / (1.0 + mean_dist)
    composite = (0.40 * mean_cov) + (0.30 * balance) + (0.20 * routing_efficiency) + (0.10 * (1.0 / (1.0 + thermal_mean)))

    return {
        "pattern": kind,
        "cell_count": len(cells),
        "mean_route_distance": round(mean_dist, 6),
        "mean_coverage": round(mean_cov, 6),
        "thermal_mean_proxy": round(thermal_mean, 6),
        "thermal_std_proxy": round(thermal_std, 6),
        "thermal_balance_score": round(balance, 6),
        "routing_efficiency_score": round(routing_efficiency, 6),
        "composite_simulation_score": round(composite, 6),
        "claim_boundary": CLAIM_BOUNDARY
    }

def main() -> int:
    cells = honeycomb_cells()
    patterns = [
        "straight_grid",
        "random_walk",
        "uniform_ring",
        "lumajet_champion_flowform"
    ]
    rows = [score_pattern(p, cells) for p in patterns]
    rows_sorted = sorted(rows, key=lambda r: r["composite_simulation_score"], reverse=True)
    best = rows_sorted[0]
    champion = next(r for r in rows if r["pattern"] == "lumajet_champion_flowform")
    best_baseline = max((r for r in rows if r["pattern"] != "lumajet_champion_flowform"), key=lambda r: r["composite_simulation_score"])

    lift = champion["composite_simulation_score"] - best_baseline["composite_simulation_score"]
    lift_pct = 100.0 * lift / max(1e-9, best_baseline["composite_simulation_score"])

    csv_path = ART / "lumajet_baseline_scores.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for row in rows_sorted:
            w.writerow(row)

    payload = {
        "generated_utc": now_iso(),
        "project": "LumaJet",
        "scope": "synthetic_aerospace_baseline_comparison",
        "claim_boundary": CLAIM_BOUNDARY,
        "patterns_tested": patterns,
        "best_pattern": best["pattern"],
        "champion_pattern": champion,
        "best_non_lumajet_baseline": best_baseline,
        "champion_lift_vs_best_baseline_points": round(lift, 6),
        "champion_lift_vs_best_baseline_pct": round(lift_pct, 3),
        "interpretation": (
            "If lift is positive, LumaJet champion flowform beat the simple synthetic baselines "
            "inside this toy simulation only. It does not prove aircraft performance."
        ),
        "all_results": rows_sorted
    }

    json_path = ART / "lumajet_baseline_results.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    md_path = ART / "LUMAJET_BASELINE_REPORT.md"
    lines = [
        "# LumaJet Baseline Report",
        "",
        f"Generated UTC: {payload['generated_utc']}",
        "",
        "## Claim Boundary",
        "",
        CLAIM_BOUNDARY,
        "",
        "## Result",
        "",
        f"- Best pattern: {best['pattern']}",
        f"- Champion pattern score: {champion['composite_simulation_score']}",
        f"- Best non-LumaJet baseline: {best_baseline['pattern']} score={best_baseline['composite_simulation_score']}",
        f"- Champion lift vs best baseline: {payload['champion_lift_vs_best_baseline_points']} points",
        f"- Champion lift vs best baseline: {payload['champion_lift_vs_best_baseline_pct']}%",
        "",
        "## Interpretation",
        "",
        payload["interpretation"],
        "",
        "## Scores",
        ""
    ]
    for row in rows_sorted:
        lines.append(f"- {row['pattern']}: composite={row['composite_simulation_score']}, coverage={row['mean_coverage']}, thermal_balance={row['thermal_balance_score']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    manifest = ART / "manifest.sha256.json"
    manifest_payload = {
        "generated_utc": now_iso(),
        "files": {
            csv_path.name: {"sha256": sha256_file(csv_path)},
            json_path.name: {"sha256": sha256_file(json_path)},
            md_path.name: {"sha256": sha256_file(md_path)}
        },
        "claim_boundary": CLAIM_BOUNDARY
    }
    manifest.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    print("LUMAJET_BASELINE_DONE")
    print(f"best_pattern={best['pattern']}")
    print(f"champion_lift_pct={payload['champion_lift_vs_best_baseline_pct']}")
    print(f"report={md_path}")
    print(f"json={json_path}")
    print(f"manifest={manifest}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
