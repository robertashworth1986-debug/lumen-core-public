"""Bounded Grants.gov source-derived simulation for mission-routing research.

This module constructs deterministic opportunity-similarity graphs from the
local public Grants.gov snapshot and evaluates them with the existing mission
routing benchmark strategies and evaluator. It does not infer opportunity
relevance, applicant eligibility, award probability, submission routing, field
performance, government approval, or economic value. Grants.gov does not supply
observed network topology, capacity, congestion, demand, or failure labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

from geometry_mission_network_routing_benchmark import (
    EdgeSpec,
    Scenario,
    STRATEGIES,
    Condition,
    aggregate,
    aggregate_by_condition,
    evaluate_strategy,
    ranked_aggregate,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "live_measured" / "grants_gov" / "grants_gov_latest.json"
BENCHMARK_PATH = ROOT / "code" / "geometry_mission_network_routing_benchmark.py"
DEFAULT_OUT = ROOT / "out" / "geometry_mission_network_routing_source_replay"

SCHEMA = "geometry_mission_network_routing_source_replay_v1"
DEVELOPMENT_SCENARIO_COUNT = 6
VALIDATION_SCENARIO_COUNT = 8
OPPORTUNITIES_PER_SCENARIO = 12
TARGETS_PER_SCENARIO = 4

BASELINE_IDS = (
    "dijkstra",
    "a_star",
    "min_cost_flow",
    "k_shortest_redundancy",
)
FAMILY_IDS = (
    "ant_trails",
    "bee_foraging_paths",
    "slime_mold_routing",
    "mycelium_network",
)

EVIDENCE_BOUNDARY = (
    "Source-derived synthetic opportunity-network simulation using public rows from "
    "one local Grants.gov snapshot. Opportunity metadata defines nodes and similarity "
    "weights; deterministic synthetic rules assign positions, capacities, demands, "
    "congestion, and bounded edge failures because the source contains none of those "
    "observed routing labels. This is not source-conditioned mission-routing performance, "
    "not a determination of relevance or eligibility, not an estimate of award probability "
    "or economic value, not actual submission routing, and not field, customer, government, "
    "or external validation."
)

TOKEN_RE = re.compile(r"[a-z0-9]+")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def stable_sha256(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def read_source(path: Path = SOURCE_PATH) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Grants.gov snapshot must be a JSON object")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        raise ValueError("Grants.gov snapshot rows must be a list")

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        opportunity_id = str(raw.get("id") or "").strip()
        title = str(raw.get("title") or "").strip()
        if not opportunity_id or not title or opportunity_id in seen:
            continue
        seen.add(opportunity_id)
        rows.append(
            {
                "id": opportunity_id,
                "number": str(raw.get("number") or "").strip(),
                "title": title,
                "agencyCode": str(raw.get("agencyCode") or "").strip(),
                "agency": str(raw.get("agency") or "").strip(),
                "openDate": str(raw.get("openDate") or "").strip(),
                "closeDate": str(raw.get("closeDate") or "").strip(),
                "oppStatus": str(raw.get("oppStatus") or "").strip(),
                "docType": str(raw.get("docType") or "").strip(),
                "cfdaList": sorted(
                    {
                        str(item).strip()
                        for item in (raw.get("cfdaList") or [])
                        if str(item).strip()
                    }
                ),
            }
        )
    if len(rows) < OPPORTUNITIES_PER_SCENARIO * 2:
        raise ValueError("not enough valid public opportunity rows for disjoint replay splits")
    return payload, rows


def token_set(*values: Any) -> set[str]:
    return {
        token
        for value in values
        for token in TOKEN_RE.findall(str(value).lower())
        if len(token) > 1
    }


def jaccard(left: set[str], right: set[str]) -> float:
    union = left | right
    return len(left & right) / len(union) if union else 0.0


def opportunity_features(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": token_set(row["title"]),
        "agency": token_set(row["agencyCode"], row["agency"]),
        "cfda": set(row["cfdaList"]),
        "document": token_set(row["docType"], row["oppStatus"]),
    }


def opportunity_similarity(
    left: dict[str, Any],
    right: dict[str, Any],
    features: dict[str, dict[str, Any]],
) -> float:
    left_features = features[left["id"]]
    right_features = features[right["id"]]
    score = (
        0.45 * jaccard(left_features["title"], right_features["title"])
        + 0.25 * jaccard(left_features["agency"], right_features["agency"])
        + 0.20 * jaccard(left_features["cfda"], right_features["cfda"])
        + 0.10 * jaccard(left_features["document"], right_features["document"])
    )
    return min(1.0, max(0.0, score))


def stable_unit(*parts: Any) -> float:
    digest = hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:8], "big") / float(2**64 - 1)


def split_opportunities(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            stable_sha256({"split_lock": "grants_gov_v1", "id": row["id"]}),
            row["id"],
        ),
    )
    midpoint = len(ordered) // 2
    return ordered[:midpoint], ordered[midpoint:]


def select_scenario_rows(
    pool: list[dict[str, Any]],
    *,
    split: str,
    scenario_index: int,
) -> list[dict[str, Any]]:
    return sorted(
        pool,
        key=lambda row: (
            stable_sha256(
                {
                    "scenario_membership": "grants_gov_v1",
                    "split": split,
                    "scenario_index": scenario_index,
                    "id": row["id"],
                }
            ),
            row["id"],
        ),
    )[:OPPORTUNITIES_PER_SCENARIO]


def build_source_scenario(
    rows: list[dict[str, Any]],
    *,
    split: str,
    scenario_index: int,
) -> tuple[Scenario, dict[str, Any]]:
    ordered = sorted(
        rows,
        key=lambda row: (
            stable_sha256(
                {
                    "node_order": "grants_gov_v1",
                    "split": split,
                    "scenario_index": scenario_index,
                    "id": row["id"],
                }
            ),
            row["id"],
        ),
    )
    features = {row["id"]: opportunity_features(row) for row in ordered}
    node_rows = {index: row for index, row in enumerate(ordered)}
    positions = {
        node: (
            round(stable_unit("x", row["id"]), 8),
            round(stable_unit("y", row["id"]), 8),
        )
        for node, row in node_rows.items()
    }

    similarities: dict[tuple[int, int], float] = {}
    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            similarities[(left, right)] = opportunity_similarity(
                node_rows[left],
                node_rows[right],
                features,
            )

    selected_edges: set[tuple[int, int]] = {
        (node, node + 1) for node in range(len(ordered) - 1)
    }
    for node in range(len(ordered)):
        neighbours = sorted(
            (
                (similarities[(min(node, other), max(node, other))], other)
                for other in range(len(ordered))
                if other != node
            ),
            key=lambda item: (-item[0], item[1]),
        )
        for _, other in neighbours[:3]:
            selected_edges.add((min(node, other), max(node, other)))

    failure_mode = (
        "opportunity_similarity_bridge_dropout"
        if scenario_index % 2 == 0
        else "opportunity_agency_cluster_congestion"
    )
    edge_specs: list[EdgeSpec] = []
    for left, right in sorted(selected_edges):
        similarity = similarities[(left, right)]
        distance = 1.0 + 9.0 * (1.0 - similarity)
        capacity = 2 + int(math.floor(4.0 * similarity)) + int(
            stable_unit("capacity", ordered[left]["id"], ordered[right]["id"]) > 0.72
        )
        failure_risk = min(
            0.98,
            0.15
            + 0.58 * (1.0 - similarity)
            + 0.20
            * stable_unit("failure", ordered[left]["id"], ordered[right]["id"]),
        )
        pre_weight = distance * (
            1.0
            + 0.08
            * stable_unit("pre", ordered[left]["id"], ordered[right]["id"])
        )
        congestion = (
            0.20
            + 0.85
            * stable_unit(
                "post",
                split,
                scenario_index,
                ordered[left]["id"],
                ordered[right]["id"],
            )
        )
        if failure_mode == "opportunity_agency_cluster_congestion":
            same_agency = (
                ordered[left]["agencyCode"]
                and ordered[left]["agencyCode"] == ordered[right]["agencyCode"]
            )
            congestion += 0.45 if same_agency else 0.0
        edge_specs.append(
            EdgeSpec(
                u=left,
                v=right,
                distance=round(distance, 8),
                capacity=capacity,
                pre_weight=round(pre_weight, 8),
                post_weight=round(pre_weight * (1.0 + congestion), 8),
                failure_risk=round(failure_risk, 8),
            )
        )

    non_chain_edges = [
        edge
        for edge in edge_specs
        if abs(edge.u - edge.v) != 1
    ]
    failure_candidates = sorted(
        non_chain_edges,
        key=lambda edge: (
            -edge.failure_risk,
            edge.u,
            edge.v,
        ),
    )
    failed_edges = tuple(
        (edge.u, edge.v)
        for edge in failure_candidates[: 1 + int(scenario_index % 3 == 2)]
    )

    source = 0
    target_candidates = sorted(
        range(1, len(ordered)),
        key=lambda node: (
            -similarities[(0, node)],
            node,
        ),
    )
    targets = tuple(sorted(target_candidates[:TARGETS_PER_SCENARIO]))
    pre_demands: list[tuple[int, int]] = []
    post_demands: list[tuple[int, int]] = []
    for target in targets:
        row = node_rows[target]
        base = 1 + int(stable_unit("demand", row["id"]) * 3.0)
        pressure = int(
            stable_unit("post_demand", split, scenario_index, row["id"]) > 0.48
        )
        pre_demands.append((target, base))
        post_demands.append((target, base + pressure))

    seed = int(
        stable_sha256(
            {
                "split": split,
                "scenario_index": scenario_index,
                "opportunity_ids": [row["id"] for row in ordered],
            }
        )[:8],
        16,
    )
    condition = Condition(
        name=failure_mode,
        node_count=len(ordered),
        target_count=len(targets),
        edge_multiplier=round(len(edge_specs) / len(ordered), 6),
        failure_rate=round(len(failed_edges) / max(1, len(edge_specs)), 6),
        congestion_pressure=0.65 if scenario_index % 2 else 0.45,
        demand_max=max(value for _, value in post_demands),
        failure_mode=failure_mode,
        bandwidth_limit=3200,
    )
    scenario = Scenario(
        split=split,
        condition=condition,
        seed=seed,
        source=source,
        targets=targets,
        pre_demands=tuple(pre_demands),
        post_demands=tuple(post_demands),
        positions=tuple(
            (node, positions[node][0], positions[node][1])
            for node in sorted(positions)
        ),
        edges=tuple(edge_specs),
        failed_edges=failed_edges,
    )
    receipt = {
        "scenario_id": stable_sha256(
            {
                "split": split,
                "scenario_index": scenario_index,
                "seed": seed,
                "opportunity_ids": [row["id"] for row in ordered],
            }
        )[:20],
        "split": split,
        "scenario_index": scenario_index,
        "seed": seed,
        "condition": failure_mode,
        "opportunity_ids": [row["id"] for row in ordered],
        "source_opportunity_id": ordered[source]["id"],
        "target_opportunity_ids": [ordered[target]["id"] for target in targets],
        "node_count": len(ordered),
        "edge_count": len(edge_specs),
        "failed_edge_count": len(failed_edges),
        "construction": (
            "public opportunity metadata weighted similarity graph; chain connectivity "
            "plus three nearest-similarity neighbours per node"
        ),
    }
    receipt["scenario_sha256"] = stable_sha256(receipt)
    return scenario, receipt


def build_split_scenarios(
    pool: list[dict[str, Any]],
    *,
    split: str,
    scenario_count: int,
) -> tuple[list[Scenario], list[dict[str, Any]]]:
    scenarios: list[Scenario] = []
    receipts: list[dict[str, Any]] = []
    for index in range(scenario_count):
        selected = select_scenario_rows(pool, split=split, scenario_index=index)
        scenario, receipt = build_source_scenario(
            selected,
            split=split,
            scenario_index=index,
        )
        scenarios.append(scenario)
        receipts.append(receipt)
    return scenarios, receipts


def evaluate_scenarios(
    scenarios: list[Scenario],
    receipts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    receipt_by_seed = {int(row["seed"]): row for row in receipts}
    rows: list[dict[str, Any]] = []
    for scenario in scenarios:
        receipt = receipt_by_seed[scenario.seed]
        for strategy in STRATEGIES:
            result = evaluate_strategy(
                scenario,
                strategy,
                measure_runtime=False,
            )
            result["scenario_id"] = receipt["scenario_id"]
            result["opportunity_id_count"] = len(receipt["opportunity_ids"])
            rows.append(result)
    return rows


def paired_rows(
    rows: Iterable[dict[str, Any]],
    candidate: str,
    baseline: str,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    grouped: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        strategy = str(row["strategy"])
        if strategy in {candidate, baseline}:
            grouped[str(row["scenario_id"])][strategy] = row
    return [
        (pair[candidate], pair[baseline])
        for _, pair in sorted(grouped.items())
        if candidate in pair and baseline in pair
    ]


def compare_pair(
    rows: list[dict[str, Any]],
    candidate: str,
    baseline: str,
) -> dict[str, Any]:
    pairs = paired_rows(rows, candidate, baseline)
    deltas = [
        float(candidate_row["score"]) - float(baseline_row["score"])
        for candidate_row, baseline_row in pairs
    ]
    return {
        "candidate_family": candidate,
        "baseline": baseline,
        "paired_scenario_count": len(pairs),
        "mean_score_delta": round(mean(deltas), 6) if deltas else None,
        "candidate_win_count": sum(delta > 0.0 for delta in deltas),
        "candidate_loss_count": sum(delta < 0.0 for delta in deltas),
        "tie_count": sum(delta == 0.0 for delta in deltas),
    }


def retain_losses(
    validation_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    losses: list[dict[str, Any]] = []
    for family in FAMILY_IDS:
        for baseline in BASELINE_IDS:
            for candidate_row, baseline_row in paired_rows(
                validation_rows,
                family,
                baseline,
            ):
                delta = float(candidate_row["score"]) - float(baseline_row["score"])
                if delta <= 0.0:
                    losses.append(
                        {
                            "scenario_id": candidate_row["scenario_id"],
                            "condition": candidate_row["condition"],
                            "family_id": family,
                            "baseline": baseline,
                            "score_delta": round(delta, 6),
                            "outcome": "tie" if delta == 0.0 else "loss",
                            "retained": True,
                        }
                    )
    return sorted(
        losses,
        key=lambda row: (
            row["family_id"],
            row["baseline"],
            row["scenario_id"],
        ),
    )


def retain_condition_failures(
    validation_rows: list[dict[str, Any]],
    locked_baseline: str,
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for family in FAMILY_IDS:
        for candidate_row, baseline_row in paired_rows(
            validation_rows,
            family,
            locked_baseline,
        ):
            reasons: list[str] = []
            delta = float(candidate_row["score"]) - float(baseline_row["score"])
            if delta <= 0.0:
                reasons.append("nonpositive_score_delta_vs_locked_baseline")
            if float(candidate_row["delivery_rate"]) < 1.0:
                reasons.append("incomplete_delivery")
            if int(candidate_row["failed_initial_route_edge_count"]) > 0:
                reasons.append("initial_route_used_failed_edge")
            if reasons:
                failures.append(
                    {
                        "scenario_id": candidate_row["scenario_id"],
                        "condition": candidate_row["condition"],
                        "family_id": family,
                        "locked_baseline": locked_baseline,
                        "score_delta": round(delta, 6),
                        "reasons": reasons,
                        "retained": True,
                    }
                )
    return sorted(
        failures,
        key=lambda row: (row["family_id"], row["scenario_id"]),
    )


def row_without_algorithm_details(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key not in {"algorithm_details", "runtime_ms", "runtime_receipt"}
    }


def build_route_results(
    development_ranked: list[dict[str, Any]],
    validation_ranked: list[dict[str, Any]],
    validation_rows: list[dict[str, Any]],
    losses: list[dict[str, Any]],
    condition_failures: list[dict[str, Any]],
    *,
    selected_family: str,
    locked_baseline: str,
    source_receipt: dict[str, Any],
) -> list[dict[str, Any]]:
    development_by_id = {row["family_id"]: row for row in development_ranked}
    validation_by_id = {row["family_id"]: row for row in validation_ranked}
    route_results: list[dict[str, Any]] = []
    for family in FAMILY_IDS:
        route = {
            "lane": "mission_network_routing",
            "family_id": family,
            "kind": "geometry_family",
            "selected_on_development": family == selected_family,
            "locked_baseline": locked_baseline,
            "source_path": source_receipt["path"],
            "source_sha256": source_receipt["sha256"],
            "development_row": development_by_id[family],
            "validation_row": validation_by_id[family],
            "comparisons": [
                compare_pair(validation_rows, family, baseline)
                for baseline in BASELINE_IDS
            ],
            "validation_scenario_results": [
                row_without_algorithm_details(row)
                for row in validation_rows
                if row["family_id"] == family
            ],
            "retained_losses": [
                row for row in losses if row["family_id"] == family
            ],
            "retained_condition_failures": [
                row for row in condition_failures if row["family_id"] == family
            ],
            "claim_gates": fail_closed_claim_gates(),
            "evidence_boundary": EVIDENCE_BOUNDARY,
        }
        route["route_sha256"] = stable_sha256(route)
        route_results.append(route)
    return route_results


def fail_closed_claim_gates() -> dict[str, bool]:
    return {
        "relevance_claim_allowed": False,
        "eligibility_claim_allowed": False,
        "award_probability_claim_allowed": False,
        "actual_submission_routing_allowed": False,
        "field_validation_claim_allowed": False,
        "external_validation_claim_allowed": False,
        "customer_validation_claim_allowed": False,
        "government_approval_claim_allowed": False,
        "government_adoption_claim_allowed": False,
        "source_conditioned_performance_claim_allowed": False,
        "dollar_value_claim_allowed": False,
        "savings_claim_allowed": False,
        "trading_claim_allowed": False,
        "universal_superiority_claim_allowed": False,
        "cross_lane_champion_claim_allowed": False,
        "autonomous_action_allowed": False,
    }


def deterministic_result_view(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if key not in {"generated_utc", "deterministic_result_sha256", "output_receipts"}
    }


def build_payload(
    *,
    source_path: Path = SOURCE_PATH,
    development_scenarios: int = DEVELOPMENT_SCENARIO_COUNT,
    validation_scenarios: int = VALIDATION_SCENARIO_COUNT,
) -> dict[str, Any]:
    if development_scenarios < 1 or validation_scenarios < 1:
        raise ValueError("development and validation scenario counts must be positive")
    source_payload, rows = read_source(source_path)
    development_pool, validation_pool = split_opportunities(rows)
    development, development_receipts = build_split_scenarios(
        development_pool,
        split="development",
        scenario_count=development_scenarios,
    )
    validation, validation_receipts = build_split_scenarios(
        validation_pool,
        split="validation",
        scenario_count=validation_scenarios,
    )

    development_rows = evaluate_scenarios(development, development_receipts)
    validation_rows = evaluate_scenarios(validation, validation_receipts)
    development_ranked = ranked_aggregate(aggregate(development_rows))
    validation_ranked = ranked_aggregate(aggregate(validation_rows))
    development_families = [
        row for row in development_ranked if row["kind"] == "geometry_family"
    ]
    development_baselines = [
        row for row in development_ranked if row["kind"] == "baseline"
    ]
    selected_family = str(development_families[0]["family_id"])
    locked_baseline = str(development_baselines[0]["family_id"])

    source_receipt = {
        "path": relative(source_path),
        "sha256": sha256_file(source_path),
        "bytes": source_path.stat().st_size,
        "declared_snapshot_sha256": str(source_payload.get("sha256") or ""),
        "declared_row_count": int(source_payload.get("row_count") or 0),
        "valid_public_row_count": len(rows),
    }
    benchmark_receipt = {
        "path": relative(BENCHMARK_PATH),
        "sha256": sha256_file(BENCHMARK_PATH),
        "bytes": BENCHMARK_PATH.stat().st_size,
    }
    protocol = {
        "schema": "geometry_mission_network_routing_source_replay_protocol_v1",
        "source_receipt": source_receipt,
        "benchmark_receipt": benchmark_receipt,
        "source_row_fields": [
            "id",
            "number",
            "title",
            "agencyCode",
            "agency",
            "openDate",
            "closeDate",
            "oppStatus",
            "docType",
            "cfdaList",
        ],
        "split_contract": (
            "one frozen SHA-256 ordering partitions valid opportunity IDs into "
            "disjoint development and validation pools before scenario construction"
        ),
        "selection_contract": (
            "best nature family and best named baseline are selected from development "
            "aggregate scores before validation results are compared"
        ),
        "scenario_contract": (
            "twelve public opportunity rows per graph; weighted metadata similarity; "
            "chain connectivity plus three nearest-similarity neighbours; deterministic "
            "synthetic positions, congestion, demands, capacities, and one or two "
            "non-chain edge failures; these quantities are not observed Grants.gov fields"
        ),
        "baseline_ids": list(BASELINE_IDS),
        "geometry_family_ids": list(FAMILY_IDS),
        "same_scenarios_for_every_strategy": True,
        "runtime_scored": False,
        "network_fetch_performed": False,
        "evidence_boundary": EVIDENCE_BOUNDARY,
    }
    protocol["protocol_sha256"] = stable_sha256(protocol)

    losses = retain_losses(validation_rows)
    condition_failures = retain_condition_failures(
        validation_rows,
        locked_baseline,
    )
    route_results = build_route_results(
        development_ranked,
        validation_ranked,
        validation_rows,
        losses,
        condition_failures,
        selected_family=selected_family,
        locked_baseline=locked_baseline,
        source_receipt=source_receipt,
    )
    development_ids = sorted(
        {
            opportunity_id
            for receipt in development_receipts
            for opportunity_id in receipt["opportunity_ids"]
        }
    )
    validation_ids = sorted(
        {
            opportunity_id
            for receipt in validation_receipts
            for opportunity_id in receipt["opportunity_ids"]
        }
    )
    locked_comparison = compare_pair(
        validation_rows,
        selected_family,
        locked_baseline,
    )
    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_utc": now_utc(),
        "status": "SOURCE_DERIVED_OPPORTUNITY_NETWORK_SIMULATION_COMPLETE",
        "lane": "mission_network_routing",
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "protocol": protocol,
        "source_derived_opportunity_network_simulation_completed": True,
        "development": {
            "scenario_count": len(development),
            "opportunity_ids": development_ids,
            "scenario_receipts": development_receipts,
            "leaderboard": development_ranked,
        },
        "validation": {
            "scenario_count": len(validation),
            "opportunity_ids": validation_ids,
            "scenario_receipts": validation_receipts,
            "leaderboard": validation_ranked,
            "condition_leaderboards": aggregate_by_condition(validation_rows),
            "baseline_results": [
                row_without_algorithm_details(row)
                for row in validation_rows
                if row["kind"] == "baseline"
            ],
        },
        "selection_lock": {
            "source": "development_only",
            "selected_family": selected_family,
            "locked_baseline": locked_baseline,
            "locked_before_validation_comparison": True,
            "validation_pair": locked_comparison,
            "field_promotion_allowed": False,
        },
        "route_results": route_results,
        "negative_result_retention": {
            "policy": (
                "every nonpositive family-versus-baseline validation scenario "
                "comparison is retained"
            ),
            "loss_count": len(losses),
            "losses": losses,
            "retained": True,
        },
        "condition_failure_retention": {
            "policy": (
                "every family validation scenario with nonpositive locked-baseline "
                "delta, incomplete delivery, or initial use of a failed edge is retained"
            ),
            "failure_count": len(condition_failures),
            "failures": condition_failures,
            "retained": True,
        },
        "claim_gates": fail_closed_claim_gates(),
    }
    if set(development_ids) & set(validation_ids):
        raise AssertionError("development and validation opportunity IDs overlap")
    payload["deterministic_result_sha256"] = stable_sha256(
        deterministic_result_view(payload)
    )
    return payload


def write_outputs(payload: dict[str, Any], out_dir: Path = DEFAULT_OUT) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = out_dir / "latest.json"
    latest.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {
        "schema": "geometry_mission_network_routing_source_replay_manifest_v1",
        "generated_utc": payload["generated_utc"],
        "protocol_sha256": payload["protocol"]["protocol_sha256"],
        "deterministic_result_sha256": payload["deterministic_result_sha256"],
        "files": {
            "latest.json": {
                "sha256": sha256_file(latest),
                "bytes": latest.stat().st_size,
            }
        },
    }
    (out_dir / "manifest.sha256.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def run_replay(
    out_dir: Path = DEFAULT_OUT,
    *,
    source_path: Path = SOURCE_PATH,
    development_scenarios: int = DEVELOPMENT_SCENARIO_COUNT,
    validation_scenarios: int = VALIDATION_SCENARIO_COUNT,
) -> dict[str, Any]:
    payload = build_payload(
        source_path=source_path,
        development_scenarios=development_scenarios,
        validation_scenarios=validation_scenarios,
    )
    write_outputs(payload, out_dir)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--source", type=Path, default=SOURCE_PATH)
    parser.add_argument(
        "--development-scenarios",
        type=int,
        default=DEVELOPMENT_SCENARIO_COUNT,
    )
    parser.add_argument(
        "--validation-scenarios",
        type=int,
        default=VALIDATION_SCENARIO_COUNT,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = run_replay(
        args.out,
        source_path=args.source,
        development_scenarios=args.development_scenarios,
        validation_scenarios=args.validation_scenarios,
    )
    print(
        json.dumps(
            {
                "status": payload["status"],
                "selected_family": payload["selection_lock"]["selected_family"],
                "locked_baseline": payload["selection_lock"]["locked_baseline"],
                "validation_mean_score_delta": payload["selection_lock"][
                    "validation_pair"
                ]["mean_score_delta"],
                "loss_count": payload["negative_result_retention"]["loss_count"],
                "condition_failure_count": payload["condition_failure_retention"][
                    "failure_count"
                ],
                "deterministic_result_sha256": payload[
                    "deterministic_result_sha256"
                ],
                "output": relative(args.out / "latest.json"),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
