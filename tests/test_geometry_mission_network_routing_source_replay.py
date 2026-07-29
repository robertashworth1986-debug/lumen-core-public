from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "code"))

from geometry_mission_network_routing_source_replay import (  # noqa: E402
    BASELINE_IDS,
    BENCHMARK_PATH,
    EVIDENCE_BOUNDARY,
    FAMILY_IDS,
    SOURCE_PATH,
    run_replay,
)


@pytest.fixture(scope="module")
def replay(tmp_path_factory):
    return run_replay(
        tmp_path_factory.mktemp("mission-routing-source-replay") / "run",
        development_scenarios=2,
        validation_scenarios=3,
    )


def test_source_and_benchmark_receipts_bind_exact_files(replay):
    protocol = replay["protocol"]
    source = protocol["source_receipt"]
    benchmark = protocol["benchmark_receipt"]

    assert source["path"] == "data/live_measured/grants_gov/grants_gov_latest.json"
    assert source["sha256"] == hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest()
    assert source["bytes"] == SOURCE_PATH.stat().st_size
    assert source["valid_public_row_count"] > 0
    assert benchmark["path"] == "code/geometry_mission_network_routing_benchmark.py"
    assert benchmark["sha256"] == hashlib.sha256(
        BENCHMARK_PATH.read_bytes()
    ).hexdigest()
    assert benchmark["bytes"] == BENCHMARK_PATH.stat().st_size
    assert protocol["network_fetch_performed"] is False


def test_development_and_validation_opportunity_ids_do_not_overlap(replay):
    development_ids = set(replay["development"]["opportunity_ids"])
    validation_ids = set(replay["validation"]["opportunity_ids"])

    assert development_ids
    assert validation_ids
    assert development_ids.isdisjoint(validation_ids)
    assert replay["selection_lock"]["source"] == "development_only"
    assert replay["selection_lock"]["locked_before_validation_comparison"] is True


def test_all_strategies_share_scenarios_and_each_family_has_route_result(replay):
    assert replay["protocol"]["baseline_ids"] == list(BASELINE_IDS)
    assert replay["protocol"]["geometry_family_ids"] == list(FAMILY_IDS)
    assert replay["protocol"]["same_scenarios_for_every_strategy"] is True

    leaderboard_ids = {
        row["family_id"] for row in replay["validation"]["leaderboard"]
    }
    assert leaderboard_ids == set(BASELINE_IDS) | set(FAMILY_IDS)
    routes = replay["route_results"]
    assert {row["family_id"] for row in routes} == set(FAMILY_IDS)
    assert all(
        len(row["validation_scenario_results"])
        == replay["validation"]["scenario_count"]
        for row in routes
    )
    assert all(
        {comparison["baseline"] for comparison in row["comparisons"]}
        == set(BASELINE_IDS)
        for row in routes
    )


def test_deterministic_result_hash_excludes_wall_clock_and_output_location(tmp_path):
    left = run_replay(
        tmp_path / "left",
        development_scenarios=1,
        validation_scenarios=2,
    )
    right = run_replay(
        tmp_path / "right",
        development_scenarios=1,
        validation_scenarios=2,
    )

    assert left["generated_utc"] != right["generated_utc"]
    assert left["deterministic_result_sha256"] == right[
        "deterministic_result_sha256"
    ]
    assert left["protocol"]["protocol_sha256"] == right["protocol"]["protocol_sha256"]
    assert [row["route_sha256"] for row in left["route_results"]] == [
        row["route_sha256"] for row in right["route_results"]
    ]


def test_all_nonpositive_losses_and_condition_failures_are_retained(replay):
    losses = replay["negative_result_retention"]
    failures = replay["condition_failure_retention"]

    assert losses["retained"] is True
    assert losses["loss_count"] == len(losses["losses"])
    assert losses["loss_count"] > 0
    assert all(row["score_delta"] <= 0.0 and row["retained"] for row in losses["losses"])
    assert failures["retained"] is True
    assert failures["failure_count"] == len(failures["failures"])
    assert failures["failure_count"] > 0
    assert all(row["reasons"] and row["retained"] for row in failures["failures"])

    route_loss_count = sum(
        len(row["retained_losses"]) for row in replay["route_results"]
    )
    route_failure_count = sum(
        len(row["retained_condition_failures"]) for row in replay["route_results"]
    )
    assert route_loss_count == losses["loss_count"]
    assert route_failure_count == failures["failure_count"]

    baseline_by_pair = {
        (row["scenario_id"], row["family_id"]): row
        for row in replay["validation"]["baseline_results"]
    }
    expected_losses = set()
    expected_failures = set()
    locked_baseline = replay["selection_lock"]["locked_baseline"]
    for route in replay["route_results"]:
        family = route["family_id"]
        for candidate in route["validation_scenario_results"]:
            scenario_id = candidate["scenario_id"]
            for baseline in BASELINE_IDS:
                reference = baseline_by_pair[(scenario_id, baseline)]
                delta = round(
                    float(candidate["score"]) - float(reference["score"]),
                    6,
                )
                if delta <= 0.0:
                    expected_losses.add((scenario_id, family, baseline, delta))
            locked = baseline_by_pair[(scenario_id, locked_baseline)]
            locked_delta = round(
                float(candidate["score"]) - float(locked["score"]),
                6,
            )
            reasons = []
            if locked_delta <= 0.0:
                reasons.append("nonpositive_score_delta_vs_locked_baseline")
            if float(candidate["delivery_rate"]) < 1.0:
                reasons.append("incomplete_delivery")
            if int(candidate["failed_initial_route_edge_count"]) > 0:
                reasons.append("initial_route_used_failed_edge")
            if reasons:
                expected_failures.add(
                    (scenario_id, family, locked_delta, tuple(reasons))
                )

    retained_losses = {
        (
            row["scenario_id"],
            row["family_id"],
            row["baseline"],
            row["score_delta"],
        )
        for row in losses["losses"]
    }
    retained_failures = {
        (
            row["scenario_id"],
            row["family_id"],
            row["score_delta"],
            tuple(row["reasons"]),
        )
        for row in failures["failures"]
    }
    assert retained_losses == expected_losses
    assert retained_failures == expected_failures


def test_evidence_boundary_and_every_external_claim_gate_fail_closed(replay):
    assert replay["evidence_boundary"] == EVIDENCE_BOUNDARY
    assert "not a determination of relevance or eligibility" in EVIDENCE_BOUNDARY
    assert "not an estimate of award probability or economic value" in EVIDENCE_BOUNDARY
    assert "not actual submission routing" in EVIDENCE_BOUNDARY
    assert replay["source_derived_opportunity_network_simulation_completed"] is True
    assert (
        replay["status"]
        == "SOURCE_DERIVED_OPPORTUNITY_NETWORK_SIMULATION_COMPLETE"
    )
    assert "not source-conditioned mission-routing performance" in EVIDENCE_BOUNDARY
    assert (
        replay["claim_gates"]["source_conditioned_performance_claim_allowed"]
        is False
    )
    assert replay["selection_lock"]["field_promotion_allowed"] is False
    assert replay["claim_gates"]
    assert all(value is False for value in replay["claim_gates"].values())
    assert all(
        all(value is False for value in route["claim_gates"].values())
        for route in replay["route_results"]
    )


def test_written_manifest_receipt_matches_latest_json(tmp_path):
    out = tmp_path / "written"
    payload = run_replay(
        out,
        development_scenarios=1,
        validation_scenarios=1,
    )
    latest = out / "latest.json"
    manifest = json.loads((out / "manifest.sha256.json").read_text(encoding="utf-8"))

    assert json.loads(latest.read_text(encoding="utf-8"))[
        "deterministic_result_sha256"
    ] == payload["deterministic_result_sha256"]
    assert manifest["deterministic_result_sha256"] == payload[
        "deterministic_result_sha256"
    ]
    assert manifest["files"]["latest.json"]["sha256"] == hashlib.sha256(
        latest.read_bytes()
    ).hexdigest()
