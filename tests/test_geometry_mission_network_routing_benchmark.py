from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from geometry_mission_network_routing_benchmark import (  # noqa: E402
    CONDITIONS,
    DEVELOPMENT_SEED_BASE,
    EVIDENCE_BOUNDARY,
    STRATEGIES,
    VALIDATION_SEED_BASE,
    evaluate_strategy,
    generate_scenario,
    run_suite,
)


EXPECTED_BASELINES = {
    "dijkstra",
    "a_star",
    "min_cost_flow",
    "k_shortest_redundancy",
}
EXPECTED_FAMILIES = {
    "ant_trails",
    "bee_foraging_paths",
    "slime_mold_routing",
    "mycelium_network",
}


def test_scenario_and_strategy_metrics_are_deterministically_reproducible():
    condition = CONDITIONS[2]
    left = generate_scenario(77123, condition, split="validation")
    right = generate_scenario(77123, condition, split="validation")

    assert left == right
    assert left.split == "validation"
    assert left.failed_edges
    assert left.pre_demands == right.pre_demands
    assert left.post_demands == right.post_demands

    ant = next(spec for spec in STRATEGIES if spec.family_id == "ant_trails")
    left_result = evaluate_strategy(left, ant, measure_runtime=False)
    right_result = evaluate_strategy(right, ant, measure_runtime=False)
    assert left_result == right_result
    assert set(
        (
            "delivery_rate",
            "path_cost_per_delivery",
            "recovery_steps",
            "maximum_edge_load",
            "messages",
            "runtime_ms",
        )
    ).issubset(left_result)


def test_literal_strategy_registry_contains_all_four_baselines_and_families():
    baselines = {spec.family_id for spec in STRATEGIES if spec.kind == "baseline"}
    families = {
        spec.family_id for spec in STRATEGIES if spec.kind == "geometry_family"
    }

    assert baselines == EXPECTED_BASELINES
    assert families == EXPECTED_FAMILIES
    assert len(STRATEGIES) == 8


def test_shared_protocol_field_ast_discovers_all_four_geometry_families():
    script = ROOT / "code" / "ops" / "BUILD_FULL_GEOMETRY_PROTOCOL_FIELD.py"
    spec = importlib.util.spec_from_file_location("full_geometry_protocol_field", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    discovered = module.module_geometry_families(
        ROOT / "code" / "geometry_mission_network_routing_benchmark.py"
    )

    assert discovered == EXPECTED_FAMILIES


def test_suite_freezes_split_blocks_claims_and_retains_losses(tmp_path):
    out = tmp_path / "run"
    summary = run_suite(out, development_scenarios=1, validation_scenarios=1)

    assert summary["schema"] == "geometry_mission_network_routing_benchmark_v1"
    assert summary["lane"] == "mission_network_routing"
    assert summary["evidence_boundary"] == EVIDENCE_BOUNDARY
    assert summary["ranking_scope"] == "mission_network_routing_only"
    assert summary["cross_lane_ranking_performed"] is False
    assert summary["development"]["seed_base"] == DEVELOPMENT_SEED_BASE
    assert summary["validation"]["seed_base"] == VALIDATION_SEED_BASE
    assert DEVELOPMENT_SEED_BASE != VALIDATION_SEED_BASE
    assert summary["development"]["scenario_count"] == len(CONDITIONS)
    assert summary["validation"]["scenario_count"] == len(CONDITIONS)
    assert summary["protocol"]["baseline_ids"] == [
        "dijkstra",
        "a_star",
        "min_cost_flow",
        "k_shortest_redundancy",
    ]
    assert set(summary["protocol"]["geometry_family_ids"]) == EXPECTED_FAMILIES
    assert summary["promotion_gate"]["selection"]["source"] == "development_only"
    assert summary["promotion_gate"]["selection"][
        "validation_pair_locked_before_scoring"
    ] is True

    gate = summary["claim_gate"]
    for field in (
        "source_conditioned_evidence",
        "live_breadth_evidence",
        "live_validation",
        "field_validation",
        "external_validation",
        "customer_validation",
        "government_approval",
        "universal_superiority",
        "cross_lane_champion",
        "trading_alpha",
        "real_dollar_claim",
    ):
        assert gate[field] is False

    negatives = summary["negative_result_retention"]
    assert negatives["retained"] is True
    assert negatives["loss_count"] == len(negatives["losses"])
    assert negatives["loss_count"] > 0
    assert all(row["retained"] is True for row in negatives["losses"])

    runtime = summary["runtime_receipts"]
    assert runtime["timer"] == "time.perf_counter_ns"
    assert runtime["measured"] is True
    assert runtime["excluded_from_score"] is True
    assert runtime["evaluation_count"] == len(CONDITIONS) * len(STRATEGIES) * 2
    assert {row["strategy"] for row in runtime["by_strategy"]} == {
        spec.name for spec in STRATEGIES
    }

    manifest = json.loads(
        (out / "manifest.sha256.json").read_text(encoding="utf-8")
    )
    assert set(manifest["files"]) == {"summary.json", "SCORECARD.md"}
    for name, metadata in manifest["files"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == metadata[
            "sha256"
        ]


def test_deterministic_result_hash_ignores_wall_clock_and_runtime_noise(tmp_path):
    left = run_suite(
        tmp_path / "left",
        development_scenarios=1,
        validation_scenarios=1,
    )
    right = run_suite(
        tmp_path / "right",
        development_scenarios=1,
        validation_scenarios=1,
    )

    assert left["generated_utc"] != right["generated_utc"]
    assert left["deterministic_result_sha256"] == right[
        "deterministic_result_sha256"
    ]
    assert left["protocol"]["protocol_sha256"] == right["protocol"]["protocol_sha256"]
