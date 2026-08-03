from __future__ import annotations

import hashlib
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
PROTOCOL_FIELD_JSON = OUT_OPS / "full_geometry_protocol_field_latest.json"
LIVE_WIRING_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"

OUT_JSON = OUT_OPS / "geometry_synthetic_live_coverage_audit_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "geometry_synthetic_live_coverage_audit.json"
OUT_MD = DOCS / "GEOMETRY_SYNTHETIC_LIVE_COVERAGE_AUDIT_2026-06-23.md"

NATURAL_FORM_SENTINEL_FAMILIES = [
    "mycelium_network",
    "slime_mold_routing",
    "ant_trails",
    "bee_foraging_paths",
    "bird_v_formation_flocking",
    "boids_swarm_flocking",
    "wolf_pack_pursuit_paths",
]


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


def verify_payload_hash(payload: dict[str, Any], field: str) -> bool:
    declared = str(payload.get(field, "")).strip()
    if not declared:
        return False
    unsigned = dict(payload)
    unsigned.pop(field, None)
    encoded = json.dumps(unsigned, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest() == declared


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
    if row.get("frozen_generated_benchmark_executed") is True:
        return "synthetic_benchmark_result_present"
    if row.get("implementation_present") is True:
        return "implementation_present_no_frozen_result"
    evidence = str(row.get("evidence_status", ""))
    first_test = str(row.get("first_test", "")).strip()
    if evidence == "proof_value_champion_not_performance_claim":
        return "proof_priority_candidate_needs_live_replay"
    if first_test:
        return "test_spec_ready_no_result"
    return "registered_but_test_spec_missing"


def live_stage(row: dict[str, Any]) -> str:
    measured_sources = int(row.get("lane_measured_source_count", 0) or 0)
    if row.get("field_validated") is True:
        return "field_validated"
    if row.get("source_conditioned_replay"):
        return "source_conditioned_replay_present"
    if measured_sources > 0:
        return "measured_source_available_not_replayed"
    return "not_live_wired"


def claimable_stage(row: dict[str, Any]) -> str:
    if row.get("field_validated") is True:
        return "field_validation_claim_allowed"
    confirmatory = row.get("confirmatory_audit")
    if isinstance(confirmatory, dict):
        if confirmatory.get("confirmatory_pass") is True:
            return "internal_confirmatory_pass_not_field_validated"
        if confirmatory.get("development_preselected") is True:
            return "confirmatory_nonpromotion"
        return "descriptive_only_not_promoted"
    if row.get("source_conditioned_replay"):
        return "source_conditioned_replay_not_field_validated"
    if row.get("frozen_generated_benchmark_executed") is True:
        return "controlled_synthetic_result_only"
    evidence = str(row.get("evidence_status", ""))
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
    protocol_field = read_json(PROTOCOL_FIELD_JSON)
    live_wiring = read_json(LIVE_WIRING_JSON)
    if not verify_payload_hash(protocol_field, "board_sha256"):
        raise ValueError("full geometry protocol field self-hash is missing or invalid")
    if live_wiring.get("schema") != "geometry_live_wiring_matrix_v3":
        raise ValueError("semantic geometry live-wiring matrix v3 is required")
    wiring_summary = (
        live_wiring.get("summary", {})
        if isinstance(live_wiring.get("summary"), dict)
        else {}
    )

    champion_families = [
        row for row in champion.get("family_asset_rankings", []) if isinstance(row, dict)
    ]
    lanes = [row for row in champion.get("lane_rankings", []) if isinstance(row, dict)]
    baselines = registry_baselines(registry)
    registry_families = [
        row for row in registry.get("families", []) if isinstance(row, dict) and row.get("id")
    ]
    protocol_families = [
        row
        for row in protocol_field.get("families", [])
        if isinstance(row, dict) and row.get("family_id")
    ]
    champion_by_id = {
        str(row.get("family")): row for row in champion_families if row.get("family")
    }
    proof_family_by_id = {
        str(row.get("family_id")): row
        for row in proof_queue.get("family_queue", [])
        if isinstance(row, dict) and row.get("family_id")
    }
    protocol_by_id = {
        str(row.get("family_id")): row for row in protocol_families if row.get("family_id")
    }
    lane_specs = registry.get("lanes", {}) if isinstance(registry.get("lanes"), dict) else {}
    registry_ids = {str(row["id"]) for row in registry_families}
    if set(protocol_by_id) != registry_ids:
        raise ValueError("protocol field does not account for the current geometry registry")

    family_rows: list[dict[str, Any]] = []
    for registry_row in registry_families:
        family_id = str(registry_row["id"])
        asset_row = champion_by_id.get(family_id, {})
        proof_row = proof_family_by_id.get(family_id, {})
        protocol_row = protocol_by_id[family_id]
        lane_id = str(registry_row.get("lane", ""))
        lane_spec = lane_specs.get(lane_id, {})
        if not isinstance(lane_spec, dict):
            lane_spec = {}
        merged: dict[str, Any] = {
            "rank": asset_row.get("rank"),
            "family": family_id,
            "label": registry_row.get("label"),
            "lane": lane_id,
            "asset_score": asset_row.get("asset_score"),
            "status": registry_row.get("status"),
            "evidence_status": asset_row.get("evidence_status"),
            "natural_logic": registry_row.get("natural_logic"),
            "benchmark_hypothesis": registry_row.get("benchmark_hypothesis"),
            "first_test": registry_row.get("first_test"),
            "promotion_metric": registry_row.get("promotion_metric"),
            "failure_mode": registry_row.get("failure_mode"),
            "implementation_present": bool(protocol_row.get("implementation_present")),
            "frozen_generated_benchmark_executed": bool(
                protocol_row.get("frozen_generated_benchmark_executed")
            ),
            "source_conditioned_replay": protocol_row.get("source_conditioned_replay"),
            "confirmatory_audit": protocol_row.get("confirmatory_audit"),
            "disposition": protocol_row.get("disposition"),
            "external_validation": bool(protocol_row.get("external_validation")),
            "field_validated": bool(protocol_row.get("field_validated")),
            "lane_measured_source_count": asset_row.get("lane_measured_source_count", 0),
            "lane_blocked_sources": asset_row.get("lane_blocked_sources", []),
            "named_baselines": list(lane_spec.get("baselines", [])),
            "lane_metrics": list(lane_spec.get("metrics", [])),
            "candidate_measured_source_contexts": list(
                proof_row.get("live_measured_sources", [])
            ),
            "candidate_context_only_sources": list(
                proof_row.get("context_only_sources", [])
            ),
            "next_source_adapter": proof_row.get("next_adapter", ""),
            "ready_for_field_validation_claim": False,
        }
        merged["synthetic_stage"] = synthetic_stage(merged)
        merged["live_stage"] = live_stage(merged)
        merged["claimable_stage"] = claimable_stage(merged)
        family_rows.append(merged)

    synthetic_counts = Counter(row["synthetic_stage"] for row in family_rows)
    live_counts = Counter(row["live_stage"] for row in family_rows)
    claim_counts = Counter(row["claimable_stage"] for row in family_rows)
    evidence_counts = Counter(row["evidence_status"] for row in family_rows)
    status_counts = Counter(row["status"] for row in family_rows)

    requested_rows = classify_requested_universe(family_rows, baselines)
    request_counts = Counter(row["coverage_stage"] for row in requested_rows)

    next_synthetic = sorted(
        [
            row
            for row in family_rows
            if row["synthetic_stage"]
            in {
                "implementation_present_no_frozen_result",
                "test_spec_ready_no_result",
                "registered_but_test_spec_missing",
            }
        ],
        key=lambda row: (
            not bool(row.get("natural_logic")),
            -(float(row.get("asset_score") or 0.0)),
            str(row["family"]),
        ),
    )[:20]
    next_live = [
        row
        for row in family_rows
        if row["frozen_generated_benchmark_executed"] is True
    ][:20]
    natural_form_queue = sorted(
        [
            row
            for row in family_rows
            if row.get("natural_logic") and row["implementation_present"] is False
        ],
        key=lambda row: (
            {"mission_network_routing": 0, "multi_agent_coordination": 1}.get(
                str(row["lane"]), 2
            ),
            -(float(row.get("asset_score") or 0.0)),
            str(row["family"]),
        ),
    )
    family_rows_by_id = {str(row["family"]): row for row in family_rows}
    natural_form_sentinels = [
        family_rows_by_id[family_id]
        for family_id in NATURAL_FORM_SENTINEL_FAMILIES
        if family_id in family_rows_by_id
    ]
    family_source_baseline_protocols = [
        {
            "family": row["family"],
            "lane": row["lane"],
            "implementation_present": row["implementation_present"],
            "frozen_generated_benchmark_executed": row[
                "frozen_generated_benchmark_executed"
            ],
            "source_conditioned_replay_present": bool(row["source_conditioned_replay"]),
            "field_validated": row["field_validated"],
            "candidate_measured_source_contexts": row[
                "candidate_measured_source_contexts"
            ],
            "candidate_context_only_sources": row["candidate_context_only_sources"],
            "named_baselines": row["named_baselines"],
            "metrics": row["lane_metrics"],
            "first_test": row["first_test"],
            "next_adapter": row["next_source_adapter"],
            "protocol_status": (
                "FIELD_VALIDATED"
                if row["field_validated"]
                else "SOURCE_CONDITIONED_REPLAY_PRESENT"
                if row["source_conditioned_replay"]
                else "SYNTHETIC_EXECUTED_NEEDS_SOURCE_ADAPTER"
                if row["frozen_generated_benchmark_executed"]
                else "IMPLEMENTED_NEEDS_FROZEN_EXECUTION"
                if row["implementation_present"]
                else "IMPLEMENTATION_REQUIRED"
            ),
            "claim_note": (
                "Measured source contexts are candidate inputs only. Each source requires a "
                "frozen, family-compatible adapter and identical named-baseline evaluation."
            ),
        }
        for row in family_rows
    ]
    missing_registry = [
        row for row in requested_rows if row["coverage_stage"] == "not_yet_in_registry"
    ][:25]

    payload = {
        "generated_utc": now_utc(),
        "schema": "geometry_synthetic_live_coverage_audit_v3",
        "purpose": "Keep synthetic discovery, live replay, and field validation separated while auditing coverage of the requested route/path geometry universe.",
        "policy": {
            "rule": (
                "Synthetic discovers. Direct measured replay tests. "
                "Field validation proves operational value."
            ),
            "synthetic_use": "Controlled benchmarks, failure cases, cheap ranking, and candidate discovery.",
            "live_use": (
                "Frozen measured data replay with matched baselines, hashes, timestamps, "
                "holdouts, and uncertainty; still not field validation."
            ),
            "field_validation_use": "External partner, agency, or independent validation before real-dollar or operational-performance claims.",
            "claim_boundary": "This audit does not create field validation, realized savings, trading profit, award certainty, or universal superiority claims.",
            "source_context_rule": (
                "Measured-source availability, direct task compatibility, source-conditioned "
                "synthetic stress, family execution, and field validation are separate gates."
            ),
            "comparison_rule": (
                "Only lane-compatible families and named baselines may share a frozen source "
                "adapter, constraints, seeds, metrics, holdout, and multiple-comparison gate."
            ),
        },
        "summary": {
            "registered_family_count": len(family_rows),
            "lane_count": int(
                protocol_field.get("summary", {}).get("registered_lane_count", len(lanes))
            ),
            "implementation_present_count": sum(
                row["implementation_present"] for row in family_rows
            ),
            "implementation_required_count": sum(
                not row["implementation_present"] for row in family_rows
            ),
            "frozen_generated_executed_count": sum(
                row["frozen_generated_benchmark_executed"] for row in family_rows
            ),
            "source_conditioned_replay_count": sum(
                bool(row["source_conditioned_replay"]) for row in family_rows
            ),
            "confirmatory_audited_count": sum(
                isinstance(row["confirmatory_audit"], dict) for row in family_rows
            ),
            "development_preselected_count": sum(
                bool((row["confirmatory_audit"] or {}).get("development_preselected"))
                for row in family_rows
            ),
            "internal_confirmatory_pass_count": sum(
                bool((row["confirmatory_audit"] or {}).get("confirmatory_pass"))
                for row in family_rows
            ),
            "confirmatory_nonpromotion_count": sum(
                (row["confirmatory_audit"] or {}).get("decision")
                == "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"
                for row in family_rows
            ),
            "natural_logic_registered_count": sum(
                bool(row.get("natural_logic")) for row in family_rows
            ),
            "natural_logic_implemented_count": sum(
                bool(row.get("natural_logic")) and row["implementation_present"]
                for row in family_rows
            ),
            "natural_logic_executed_count": sum(
                bool(row.get("natural_logic"))
                and row["frozen_generated_benchmark_executed"]
                for row in family_rows
            ),
            "natural_logic_implementation_required_count": len(natural_form_queue),
            "source_specific_baseline_protocol_count": len(
                family_source_baseline_protocols
            ),
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
            "live_replay_result_count": live_counts.get(
                "source_conditioned_replay_present", 0
            ),
            "source_conditioned_replay_receipt_family_count": live_counts.get(
                "source_conditioned_replay_present", 0
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
            "live_sources_wired_for_replay_count": int(
                wiring_summary.get("qualified_direct_source_links", 0) or 0
            ),
            "qualified_direct_source_link_count": int(
                wiring_summary.get("qualified_direct_source_links", 0) or 0
            ),
            "qualified_conditioning_source_link_count": int(
                wiring_summary.get("qualified_conditioning_source_links", 0) or 0
            ),
            "context_only_measured_source_link_count": int(
                wiring_summary.get("context_only_measured_source_links", 0) or 0
            ),
            "direct_source_replay_build_ready_lane_count": int(
                wiring_summary.get(
                    "lanes_ready_for_direct_source_replay_build", 0
                )
                or 0
            ),
            "source_conditioned_simulation_build_ready_lane_count": int(
                wiring_summary.get(
                    "lanes_ready_for_source_conditioned_simulation_build", 0
                )
                or 0
            ),
            "live_source_context_available_not_replayed_count": live_counts.get(
                "measured_source_available_not_replayed", 0
            ),
            "field_validated_family_count": live_counts.get("field_validated", 0),
            "claimable_family_count": claim_counts.get(
                "field_validation_claim_allowed", 0
            ),
            "registry_candidate_not_validated_count": evidence_counts.get(
                "registry_candidate_not_validated", 0
            ),
            "safe_answer_to_have_we_tested_all": (
                f"No. {len(family_rows)} families are registered, "
                f"{sum(row['implementation_present'] for row in family_rows)} have implementations, "
                f"{sum(row['frozen_generated_benchmark_executed'] for row in family_rows)} have "
                "current frozen generated-benchmark execution, "
                f"{sum(bool((row['confirmatory_audit'] or {}).get('development_preselected')) for row in family_rows)} "
                "were development-preselected, "
                f"{sum(bool((row['confirmatory_audit'] or {}).get('confirmatory_pass')) for row in family_rows)} "
                "passed internal confirmatory gates, "
                f"{sum((row['confirmatory_audit'] or {}).get('decision') == 'NOT_PROMOTED_CONFIRMATORY_GATE_FAILED' for row in family_rows)} "
                "were retained as confirmatory non-promotions, and "
                f"{sum(row['field_validated'] for row in family_rows)} are field validated. "
                "Registry or source coverage must not be described as testing."
            ),
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
        "protocol_field_receipt": {
            "path": str(PROTOCOL_FIELD_JSON.relative_to(ROOT)),
            "schema": protocol_field.get("schema"),
            "board_sha256": protocol_field.get("board_sha256"),
            "self_hash_valid": True,
        },
        "semantic_live_wiring_receipt": {
            "path": str(LIVE_WIRING_JSON.relative_to(ROOT)),
            "schema": live_wiring.get("schema"),
            "generated_utc": live_wiring.get("generated_utc"),
        },
        "natural_form_sentinel_coverage": natural_form_sentinels,
        "natural_form_tournament_queue": natural_form_queue,
        "family_source_baseline_protocols": family_source_baseline_protocols,
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
        f"- Source context: {policy['source_context_rule']}",
        f"- Comparison: {policy['comparison_rule']}",
        "",
        "## Current Truth",
        "",
        f"- Registered families accounted for: `{summary['registered_family_count']}`",
        f"- Registered lanes: `{summary['lane_count']}`",
        f"- Implementations present: `{summary['implementation_present_count']}`",
        f"- Implementations still required: `{summary['implementation_required_count']}`",
        f"- Current frozen generated-benchmark executions: `{summary['frozen_generated_executed_count']}`",
        f"- Source-conditioned replay receipts: `{summary['source_conditioned_replay_receipt_family_count']}` families",
        f"- Qualified direct-source links: `{summary['qualified_direct_source_link_count']}`",
        f"- Qualified conditioning-source links: `{summary['qualified_conditioning_source_link_count']}`",
        f"- Context-only measured-source links: `{summary['context_only_measured_source_link_count']}`",
        f"- Direct-source replay build-ready lanes: `{summary['direct_source_replay_build_ready_lane_count']}`",
        f"- Source-conditioned simulation build-ready lanes: `{summary['source_conditioned_simulation_build_ready_lane_count']}`",
        f"- Development-preselected candidates: `{summary['development_preselected_count']}`",
        f"- Internal confirmatory passes: `{summary['internal_confirmatory_pass_count']}`",
        f"- Confirmatory non-promotions retained: `{summary['confirmatory_nonpromotion_count']}`",
        f"- Proof-priority candidate families: `{summary['proof_priority_candidate_count']}`",
        f"- Test-spec-ready but no result yet: `{summary['test_spec_ready_no_result_count']}`",
        f"- Registered but missing a first test: `{summary['registered_but_test_spec_missing_count']}`",
        f"- Field-validated families: `{summary['field_validated_family_count']}`",
        f"- Natural-logic families registered / implemented / executed: `{summary['natural_logic_registered_count']}` / `{summary['natural_logic_implemented_count']}` / `{summary['natural_logic_executed_count']}`",
        f"- Family/source/baseline protocol cards: `{summary['source_specific_baseline_protocol_count']}`",
        "",
        "## Answer",
        "",
        summary["safe_answer_to_have_we_tested_all"],
        "",
        "## Natural-Form Sentinels",
        "",
    ]
    for row in payload["natural_form_sentinel_coverage"]:
        lines.append(
            f"- `{row['family']}` ({row['lane']}): implementation "
            f"`{str(row['implementation_present']).lower()}`, frozen execution "
            f"`{str(row['frozen_generated_benchmark_executed']).lower()}`, "
            f"stage `{row['synthetic_stage']}`."
        )
    lines.extend(
        [
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
    )
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

