from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config"
OUT_OPS = ROOT / "out" / "ops"
DOCS = ROOT / "docs"
DASHBOARD_DATA = ROOT / "dashboard" / "data"

REGISTRY_JSON = CONFIG / "geometry_championship_v1_registry.json"
CHAMPION_JSON = OUT_OPS / "geometry_champion_of_champions_latest.json"
PROOF_QUEUE_JSON = OUT_OPS / "geometry_live_breadth_proof_queue_latest.json"
FRONTIER_JSON = OUT_OPS / "geometry_proof_frontier_board_latest.json"

OUT_JSON = OUT_OPS / "geometry_synthetic_live_coverage_audit_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_synthetic_live_coverage_audit.json"
OUT_MD = DOCS / "GEOMETRY_SYNTHETIC_LIVE_COVERAGE_AUDIT_2026-06-23.md"


REQUESTED_CANDIDATE_UNIVERSE = [
    "Dijkstra shortest path",
    "A* / weighted A*",
    "bidirectional A*",
    "k-shortest paths",
    "min-cost flow",
    "max-flow/min-cut",
    "Steiner tree approximation",
    "minimum spanning tree",
    "traveling-salesman heuristics",
    "vehicle-routing heuristics",
    "RRT/RRT*",
    "probabilistic roadmaps",
    "contraction hierarchies",
    "landmark routing",
    "hierarchical pathfinding",
    "dynamic replanning / D* Lite",
    "mycelium/fungus networks",
    "slime mold / Physarum routing",
    "ant colony optimization",
    "bee foraging / waggle routing",
    "bird flocking / V-formation",
    "fish schooling",
    "wolf-pack pursuit paths",
    "predator-prey pursuit/evasion",
    "river deltas",
    "leaf veins",
    "vascular/lung branching",
    "root growth networks",
    "termite mound ventilation paths",
    "coral branching",
    "lightning/Lichtenberg paths",
    "neural dendrite branching",
    "hibernation/bounded wake routing",
    "pheromone evaporation trails",
    "magnetic field lines",
    "electric field lines",
    "potential fields",
    "harmonic potential fields",
    "toroidal fields",
    "vortex fields",
    "spiral attractor fields",
    "Halbach-array field shaping",
    "gradient-flow paths",
    "Laplacian smoothing paths",
    "heat-diffusion routing",
    "wavefront propagation",
    "eikonal equation paths",
    "geodesic distance fields",
    "signed-distance-field routing",
    "Euclidean geodesics",
    "non-Euclidean geodesics",
    "hyperbolic routing",
    "spherical routing",
    "manifold geodesics",
    "Ricci-flow-inspired paths",
    "Voronoi routing",
    "Delaunay triangulation paths",
    "medial-axis paths",
    "convex-hull routing",
    "alpha-shape routing",
    "hexagonal / honeycomb packing",
    "Flower of Life / hex packing",
    "lattice paths: square, triangular, hex",
    "fractal paths",
    "Hilbert curves",
    "Peano curves",
    "Z-order/Morton curves",
    "space-filling curves",
    "logarithmic spirals",
    "Fibonacci/golden spirals",
    "Lissajous paths",
    "catenary curves",
    "brachistochrone paths",
    "cycloid paths",
    "laminar-flow paths",
    "turbulent mixing paths",
    "vortex shedding paths",
    "convection-cell paths",
    "pressure-gradient routing",
    "Navier-Stokes-inspired flow fields",
    "streamline routing",
    "river-basin flow accumulation",
    "watershed routing",
    "drainage network routing",
    "capillary flow paths",
    "porous-media flow",
    "hydraulic resistance minimization",
    "consensus control",
    "boids/flocking",
    "formation control",
    "leader-follower paths",
    "auction-based routing",
    "market-based task routing",
    "stigmergic routing",
    "decentralized belief propagation",
    "quorum routing",
    "gossip routing",
    "Byzantine-resilient routing",
    "role-coherence routing",
    "sparse peer task markets",
    "reputation-weighted routing",
    "local repair / re-auction routing",
    "redundant k-path routing",
    "disjoint-path routing",
    "risk-aware routing",
    "stealth routing",
    "deception-aware routing",
    "moving-target routing",
    "resilient mesh routing",
    "failure-tolerant routing",
    "jamming-aware routing",
    "collusion-aware routing",
    "anomaly-aware rerouting",
    "bounded-trust propagation",
    "quarantine/isolation routing",
    "mixture-of-experts routing",
    "router-transformer gating",
    "token routing",
    "sparse attention paths",
    "memory-retrieval routing",
    "tool-call routing",
    "agent handoff paths",
    "context-window path optimization",
    "DAG workflow routing",
    "queueing-network routing",
    "latency/cost-aware API routing",
    "GPU job scheduling paths",
    "energy-aware compute routing",
    "LumenCore hybrid: reputation + source-quality + local repair + geometric prior",
]


REQUEST_ALIASES = {
    "dijkstra shortest path": ["dijkstra"],
    "a weighted a": ["a_star"],
    "k shortest paths": ["k_shortest_redundancy"],
    "min cost flow": ["min_cost_flow"],
    "steiner tree approximation": ["steiner_approximation"],
    "minimum spanning tree": ["minimum_spanning_tree"],
    "mycelium fungus networks": ["mycelium_network"],
    "slime mold physarum routing": ["slime_mold_routing"],
    "ant colony optimization": ["ant_trails"],
    "bee foraging waggle routing": ["bee_foraging_paths"],
    "bird flocking v formation": ["bird_v_formation_flocking", "boids_swarm_flocking"],
    "fish schooling": ["fish_school_vortex"],
    "wolf pack pursuit paths": ["wolf_pack_pursuit_paths"],
    "river deltas": ["river_deltas"],
    "leaf veins": ["leaf_veins"],
    "vascular lung branching": ["vascular_lung_branching"],
    "root growth networks": ["root_gravitropism_paths"],
    "termite mound ventilation paths": ["termite_mound_ventilation"],
    "coral branching": ["coral_growth_fronts"],
    "lightning lichtenberg paths": ["lightning_laplacian_paths"],
    "neural dendrite branching": ["neural_dendritic_arbors"],
    "hibernation bounded wake routing": ["hibernation_bounded_wake_logic"],
    "magnetic field lines": ["magnetic_field_geometry"],
    "toroidal fields": ["toroidal_fields"],
    "halbach array field shaping": ["halbach_arrays"],
    "spiral attractor fields": ["logarithmic_spiral_growth", "archimedean_spiral_scan"],
    "non euclidean geodesics": ["non_euclidean_geodesics"],
    "manifold geodesics": ["non_euclidean_geodesics"],
    "voronoi routing": ["voronoi_cellular_partition"],
    "delaunay triangulation paths": ["delaunay_triangulation_paths"],
    "hexagonal honeycomb packing": ["flower_of_life_hexagonal_packing"],
    "flower of life hex packing": ["flower_of_life_hexagonal_packing"],
    "fractal paths": ["fractal_brownian_surface"],
    "hilbert curves": ["hilbert_space_filling_curve"],
    "peano curves": ["peano_space_filling_curve"],
    "z order morton curves": ["morton_z_order_curve"],
    "space filling curves": ["hilbert_space_filling_curve", "peano_space_filling_curve", "morton_z_order_curve"],
    "logarithmic spirals": ["logarithmic_spiral_growth"],
    "fibonacci golden spirals": ["fibonacci_phyllotaxis", "logarithmic_spiral_growth"],
    "lissajous paths": ["lissajous_phase_paths"],
    "catenary curves": ["catenary_minimum_energy"],
    "brachistochrone paths": ["brachistochrone_descent"],
    "cycloid paths": ["cycloid_rolling_paths"],
    "convection cell paths": ["rayleigh_benard_cells"],
    "streamline routing": ["ocean_current_streamlines", "atmospheric_jet_stream_paths"],
    "river basin flow accumulation": ["river_deltas"],
    "watershed routing": ["river_deltas"],
    "drainage network routing": ["river_deltas"],
    "boids flocking": ["boids_swarm_flocking", "bird_v_formation_flocking"],
    "consensus control": ["consensus_control"],
    "formation control": ["bird_v_formation_flocking", "boids_swarm_flocking"],
    "market based task routing": ["market_signal_geometry"],
    "anomaly aware rerouting": ["markov_blanket_boundaries", "regime_transition_manifold"],
    "bounded trust propagation": ["markov_blanket_boundaries"],
    "quarantine isolation routing": ["markov_blanket_boundaries"],
    "latency cost aware api routing": ["minimum_action_path"],
    "energy aware compute routing": ["cicada_prime_cycles", "minimum_action_path"],
    "lumencore hybrid reputation source quality local repair geometric prior": ["hybrid_flowforms"],
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def slug(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def compact_slug(value: Any) -> str:
    return slug(value).replace(" ", "_")


def registry_baselines(registry: dict[str, Any]) -> set[str]:
    baselines: set[str] = set()
    lanes = registry.get("lanes", {})
    if not isinstance(lanes, dict):
        return baselines
    for lane in lanes.values():
        if isinstance(lane, dict):
            for baseline in lane.get("baselines", []):
                baselines.add(compact_slug(baseline))
    return baselines


def synthetic_stage(row: dict[str, Any]) -> str:
    evidence = str(row.get("evidence_status", ""))
    first_test = str(row.get("first_test", "")).strip()
    if "generated" in evidence:
        return "synthetic_benchmark_result_present"
    if evidence == "proof_value_champion_not_performance_claim":
        return "proof_priority_candidate_needs_live_replay"
    if first_test:
        return "test_spec_ready_no_result"
    return "registered_but_test_spec_missing"


def live_stage(row: dict[str, Any]) -> str:
    measured_sources = int(row.get("lane_measured_source_count", 0) or 0)
    if row.get("ready_for_field_validation_claim") is True:
        return "field_validated"
    if measured_sources > 0:
        return "live_sources_wired_for_replay_not_live_win"
    return "not_live_wired"


def claimable_stage(row: dict[str, Any]) -> str:
    if row.get("ready_for_field_validation_claim") is True:
        return "field_validation_claim_allowed"
    evidence = str(row.get("evidence_status", ""))
    if "generated" in evidence:
        return "controlled_synthetic_result_only"
    if evidence == "proof_value_champion_not_performance_claim":
        return "proof_priority_only"
    return "research_candidate_only"


def family_index(families: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in families:
        fid = str(row.get("family", "")).strip()
        if fid:
            index[fid] = row
    return index


def fuzzy_family_match(request: str, families: list[dict[str, Any]]) -> list[str]:
    req = slug(request)
    if not req:
        return []
    matches = []
    for row in families:
        haystack = " ".join(
            [
                slug(row.get("family")),
                slug(row.get("label")),
                slug(row.get("natural_logic")),
                slug(row.get("benchmark_hypothesis")),
            ]
        )
        req_tokens = [token for token in req.split() if len(token) >= 4]
        if req_tokens and all(token in haystack for token in req_tokens[:3]):
            fid = str(row.get("family", "")).strip()
            if fid:
                matches.append(fid)
    return matches[:3]


def classify_requested_universe(
    families: list[dict[str, Any]], baselines: set[str]
) -> list[dict[str, Any]]:
    by_family = family_index(families)
    rows: list[dict[str, Any]] = []
    for request in REQUESTED_CANDIDATE_UNIVERSE:
        normalized = slug(request)
        alias_ids = REQUEST_ALIASES.get(normalized, [])
        matched_families = [fid for fid in alias_ids if fid in by_family]
        matched_baselines = [bid for bid in alias_ids if bid in baselines]
        if not matched_families and compact_slug(request) in baselines:
            matched_baselines.append(compact_slug(request))
        if not matched_families and not matched_baselines:
            matched_families = fuzzy_family_match(request, families)
        if matched_families:
            stage = "covered_by_registry_family"
        elif matched_baselines:
            stage = "covered_as_baseline"
        else:
            stage = "not_yet_in_registry"
        rows.append(
            {
                "requested_candidate": request,
                "coverage_stage": stage,
                "matched_families": matched_families,
                "matched_baselines": matched_baselines,
                "claim_note": "Coverage here means registered or baseline-tracked, not proven performance.",
            }
        )
    return rows


def build_audit() -> dict[str, Any]:
    registry = read_json(REGISTRY_JSON)
    champion = read_json(CHAMPION_JSON)
    proof_queue = read_json(PROOF_QUEUE_JSON)
    frontier = read_json(FRONTIER_JSON)

    families = [
        row for row in champion.get("family_asset_rankings", []) if isinstance(row, dict)
    ]
    lanes = [row for row in champion.get("lane_rankings", []) if isinstance(row, dict)]
    baselines = registry_baselines(registry)

    family_rows = []
    for row in families:
        family_rows.append(
            {
                "rank": row.get("rank"),
                "family": row.get("family"),
                "label": row.get("label"),
                "lane": row.get("lane"),
                "asset_score": row.get("asset_score"),
                "status": row.get("status"),
                "evidence_status": row.get("evidence_status"),
                "synthetic_stage": synthetic_stage(row),
                "live_stage": live_stage(row),
                "claimable_stage": claimable_stage(row),
                "first_test": row.get("first_test"),
                "promotion_metric": row.get("promotion_metric"),
                "lane_measured_source_count": row.get("lane_measured_source_count", 0),
                "lane_blocked_sources": row.get("lane_blocked_sources", []),
                "ready_for_field_validation_claim": bool(
                    row.get("ready_for_field_validation_claim", False)
                ),
            }
        )

    synthetic_counts = Counter(row["synthetic_stage"] for row in family_rows)
    live_counts = Counter(row["live_stage"] for row in family_rows)
    claim_counts = Counter(row["claimable_stage"] for row in family_rows)
    evidence_counts = Counter(row["evidence_status"] for row in family_rows)
    status_counts = Counter(row["status"] for row in family_rows)

    requested_rows = classify_requested_universe(families, baselines)
    request_counts = Counter(row["coverage_stage"] for row in requested_rows)

    next_synthetic = [
        row
        for row in family_rows
        if row["synthetic_stage"] in {"test_spec_ready_no_result", "registered_but_test_spec_missing"}
    ][:20]
    next_live = [
        row
        for row in family_rows
        if row["synthetic_stage"] in {
            "synthetic_benchmark_result_present",
            "proof_priority_candidate_needs_live_replay",
        }
    ][:20]
    missing_registry = [
        row for row in requested_rows if row["coverage_stage"] == "not_yet_in_registry"
    ][:25]

    payload = {
        "generated_utc": now_utc(),
        "schema": "geometry_synthetic_live_coverage_audit_v1",
        "purpose": "Keep synthetic discovery, live replay, and field validation separated while auditing coverage of the requested route/path geometry universe.",
        "policy": {
            "rule": "Synthetic discovers. Live proves. Field validation wins awards.",
            "synthetic_use": "Controlled benchmarks, failure cases, cheap ranking, and candidate discovery.",
            "live_use": "Frozen live/public data replay with baselines, hashes, timestamps, and uncertainty.",
            "field_validation_use": "External partner, agency, or independent validation before real-dollar or operational-performance claims.",
            "claim_boundary": "This audit does not create field validation, realized savings, trading profit, award certainty, or universal superiority claims.",
        },
        "summary": {
            "registered_family_count": len(family_rows),
            "lane_count": len(lanes),
            "requested_candidate_count": len(REQUESTED_CANDIDATE_UNIVERSE),
            "requested_candidates_covered_by_registry_family": request_counts.get(
                "covered_by_registry_family", 0
            ),
            "requested_candidates_covered_as_baseline": request_counts.get(
                "covered_as_baseline", 0
            ),
            "requested_candidates_not_yet_in_registry": request_counts.get(
                "not_yet_in_registry", 0
            ),
            "synthetic_benchmark_result_count": synthetic_counts.get(
                "synthetic_benchmark_result_present", 0
            ),
            "proof_priority_candidate_count": synthetic_counts.get(
                "proof_priority_candidate_needs_live_replay", 0
            ),
            "test_spec_ready_no_result_count": synthetic_counts.get(
                "test_spec_ready_no_result", 0
            ),
            "registered_but_test_spec_missing_count": synthetic_counts.get(
                "registered_but_test_spec_missing", 0
            ),
            "live_sources_wired_for_replay_count": live_counts.get(
                "live_sources_wired_for_replay_not_live_win", 0
            ),
            "field_validated_family_count": live_counts.get("field_validated", 0),
            "claimable_family_count": claim_counts.get(
                "field_validation_claim_allowed", 0
            ),
            "registry_candidate_not_validated_count": evidence_counts.get(
                "registry_candidate_not_validated", 0
            ),
            "safe_answer_to_have_we_tested_all": "No. The registered universe is ranked and mostly test-spec-ready, but only a small subset has generated benchmark evidence and none are field validated.",
        },
        "status_counts": dict(status_counts),
        "evidence_counts": dict(evidence_counts),
        "synthetic_stage_counts": dict(synthetic_counts),
        "live_stage_counts": dict(live_counts),
        "claimable_stage_counts": dict(claim_counts),
        "requested_universe_coverage_counts": dict(request_counts),
        "current_champions": {
            "from_champion_board": champion.get("category_champions", {}),
            "from_proof_queue": proof_queue.get("champions", {}),
            "from_frontier": frontier.get("champion_board", {}),
        },
        "top_next_live_replay_queue": next_live,
        "top_next_synthetic_benchmark_queue": next_synthetic,
        "requested_candidates_missing_from_registry": missing_registry,
        "requested_universe_coverage": requested_rows,
        "family_coverage": family_rows,
        "outputs": {
            "json": str(OUT_JSON.relative_to(ROOT)),
            "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)),
            "markdown": str(OUT_MD.relative_to(ROOT)),
        },
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    policy = payload["policy"]
    lines = [
        "# Geometry Synthetic/Live Coverage Audit",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        "## Policy",
        "",
        f"**{policy['rule']}**",
        "",
        f"- Synthetic: {policy['synthetic_use']}",
        f"- Live: {policy['live_use']}",
        f"- Field validation: {policy['field_validation_use']}",
        "",
        "## Current Truth",
        "",
        f"- Registered families ranked: `{summary['registered_family_count']}`",
        f"- Lanes ranked: `{summary['lane_count']}`",
        f"- Synthetic benchmark-result families: `{summary['synthetic_benchmark_result_count']}`",
        f"- Proof-priority candidate families: `{summary['proof_priority_candidate_count']}`",
        f"- Test-spec-ready but no result yet: `{summary['test_spec_ready_no_result_count']}`",
        f"- Registered but missing a first test: `{summary['registered_but_test_spec_missing_count']}`",
        f"- Live-source-wired for replay: `{summary['live_sources_wired_for_replay_count']}`",
        f"- Field-validated families: `{summary['field_validated_family_count']}`",
        "",
        "## Answer",
        "",
        summary["safe_answer_to_have_we_tested_all"],
        "",
        "## Requested Universe Coverage",
        "",
        f"- Requested candidates tracked in this audit: `{summary['requested_candidate_count']}`",
        f"- Covered by registry family: `{summary['requested_candidates_covered_by_registry_family']}`",
        f"- Covered as baseline: `{summary['requested_candidates_covered_as_baseline']}`",
        f"- Not yet in registry: `{summary['requested_candidates_not_yet_in_registry']}`",
        "",
        "## Top Next Live Replay Queue",
        "",
    ]
    for row in payload["top_next_live_replay_queue"][:10]:
        lines.append(
            f"- `{row['family']}` ({row['lane']}): {row['synthetic_stage']} -> {row['live_stage']}; metric `{row.get('promotion_metric') or 'TBD'}`"
        )
    lines.extend(["", "## Top Next Synthetic Benchmark Queue", ""])
    for row in payload["top_next_synthetic_benchmark_queue"][:10]:
        lines.append(
            f"- `{row['family']}` ({row['lane']}): {row['synthetic_stage']}; first test `{row.get('first_test') or 'NEEDS_TEST_SPEC'}`"
        )
    if payload["requested_candidates_missing_from_registry"]:
        lines.extend(["", "## Missing From Registry", ""])
        for row in payload["requested_candidates_missing_from_registry"][:15]:
            lines.append(f"- {row['requested_candidate']}")
    lines.extend(
        [
            "",
            "## Do Not Overclaim",
            "",
            policy["claim_boundary"],
        ]
    )
    return "\n".join(lines)


def main() -> dict[str, Any]:
    payload = build_audit()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    return payload


if __name__ == "__main__":
    result = main()
    print(json.dumps(result["summary"], indent=2))

