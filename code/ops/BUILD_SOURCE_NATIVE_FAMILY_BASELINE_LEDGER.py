from __future__ import annotations

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

REGISTRY_JSON = ROOT / "config" / "geometry_championship_v1_registry.json"
PROTOCOL_FIELD_JSON = OUT_OPS / "full_geometry_protocol_field_latest.json"
WIRING_MATRIX_JSON = OUT_OPS / "geometry_live_wiring_matrix_latest.json"
TOP_REPLAY_JSON = OUT_OPS / "top_geometry_live_replay_results_latest.json"
TOP_REPLAY_BUILDER = OUT_OPS.parent.parent / "code" / "ops" / "BUILD_TOP_GEOMETRY_LIVE_REPLAY_RESULTS.py"
MARKET_SIGNAL_BENCHMARK_BUILDER = (
    ROOT / "code" / "ops" / "BUILD_MARKET_SIGNAL_SOURCE_NATIVE_BENCHMARK.py"
)
MARKET_SIGNAL_BENCHMARK_JSON = (
    OUT_OPS / "market_signal_source_native_benchmark_latest.json"
)

OUT_JSON = OUT_OPS / "source_native_family_baseline_ledger_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "source_native_family_baseline_ledger.json"
OUT_MD = DOCS / "SOURCE_NATIVE_FAMILY_BASELINE_LEDGER.md"

BOUNDARY = (
    "This ledger separates executable direct measured comparisons from "
    "source-conditioned synthetic stress, generated benchmarks, and context-only "
    "inventory. Individual baseline wins are exploratory research leads unless the "
    "same predeclared candidate beats every source-native baseline after the global "
    "multiple-comparison correction on a prospectively protected holdout. No current "
    "card passes that gate. Nothing here establishes field validation, realized "
    "savings, enterprise value, trading edge, or live-execution authority."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def ranked_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        family_id = str(row.get("family_id") or row.get("strategy") or "")
        if family_id:
            grouped.setdefault(family_id, []).append(row)
    leaderboard: list[dict[str, Any]] = []
    for family_id, family_rows in grouped.items():
        first = family_rows[0]
        scores = [as_float(row.get("score")) for row in family_rows]
        leaderboard.append(
            {
                "family_id": family_id,
                "strategy": family_id,
                "kind": str(first.get("kind", "")),
                "mean_score": mean(scores) if scores else 0.0,
                "median_score": median(scores) if scores else 0.0,
                "scenario_count": len(family_rows),
            }
        )
    leaderboard.sort(
        key=lambda row: (-as_float(row.get("mean_score")), row["family_id"])
    )
    for rank, row in enumerate(leaderboard, start=1):
        row["rank"] = rank
    return leaderboard


def execute_direct_cards(
    matrix: dict[str, Any], top_replay_module: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cards: list[dict[str, Any]] = []
    adapter_receipts: list[dict[str, Any]] = []
    for lane_row in as_list(matrix.get("matrix")):
        if not isinstance(lane_row, dict):
            continue
        lane = str(lane_row.get("lane", ""))
        source_refs = [
            row
            for row in as_list(lane_row.get("direct_measured_replay_sources"))
            if isinstance(row, dict)
        ]
        if not source_refs:
            continue
        adapter = top_replay_module.run_lane_adapter(
            lane,
            [],
            source_refs,
            evidence_mode="direct_measured_replay",
        )
        adapter_rows = [
            row
            for row in as_list(adapter.get("rows"))
            if isinstance(row, dict)
        ]
        selected_candidate = str(
            as_dict(adapter.get("ingestion_summary")).get(
                "development_selected_candidate", ""
            )
        )
        adapter_receipts.append(
            {
                "lane": lane,
                "adapter_status": adapter.get("adapter_status", ""),
                "direct_source_count": len(source_refs),
                "evaluation_row_count": len(adapter_rows),
                "evaluated_candidate_count": len(
                    {
                        str(row.get("family_id", ""))
                        for row in adapter_rows
                        if row.get("kind") == "geometry_family"
                    }
                ),
                "development_selected_candidate": selected_candidate,
                "ingestion_summary": adapter.get("ingestion_summary", {}),
            }
        )
        if not adapter_rows:
            continue

        for source_ref in source_refs:
            source = str(source_ref.get("source", "")).upper()
            source_rows = [
                row
                for row in adapter_rows
                if str(row.get("source", "")).upper() == source
            ]
            if not source_rows:
                continue
            leaderboard = ranked_rows(source_rows)
            candidates = [
                str(row.get("family_id", ""))
                for row in leaderboard
                if row.get("kind") == "geometry_family"
            ]
            for candidate in candidates:
                comparisons = top_replay_module.all_baseline_comparisons(
                    source_rows, leaderboard, candidate, lane
                )
                prospectively_protected = bool(
                    lane == "wave_resonance_timing"
                    and candidate
                    and candidate == selected_candidate
                )
                cards.append(
                    {
                        "lane": lane,
                        "source": source,
                        "source_snapshot_json": source_ref.get(
                            "snapshot_json", ""
                        ),
                        "source_snapshot_sha256": source_ref.get(
                            "snapshot_sha256", ""
                        ),
                        "candidate_family_id": candidate,
                        "candidate_role": (
                            "development_selected_confirmatory_candidate"
                            if prospectively_protected
                            else "exploratory_direct_measured_candidate"
                        ),
                        "prospectively_protected_candidate": (
                            prospectively_protected
                        ),
                        "baseline_comparisons": comparisons,
                        "source_specific_baseline_count": len(comparisons),
                        "evaluation_row_count": len(source_rows),
                        "public_performance_claim_allowed": False,
                        "field_validation_claim_allowed": False,
                        "real_dollar_savings_claim_allowed": False,
                        "live_execution_allowed": False,
                    }
                )

    top_replay_module.apply_global_baseline_holm(cards)
    for card in cards:
        gauntlet = as_dict(card.get("baseline_gauntlet"))
        gauntlet["scope"] = (
            "Holm correction across every candidate-source-baseline comparison "
            "in this exhaustive direct-source ledger."
        )
        full_gate = bool(
            card.get("prospectively_protected_candidate")
            and gauntlet.get(
                "candidate_beats_all_registered_baselines_after_global_holm"
            )
        )
        card["internal_source_native_promotion_gate_passed"] = full_gate
        card["public_performance_claim_allowed"] = False
        card["claim_stage"] = (
            "internal_source_native_gate_passed_external_validation_pending"
            if full_gate
            else "direct_measured_nonpromotion_or_exploratory_result"
        )
    return cards, adapter_receipts


def validate_market_signal_benchmark(payload: dict[str, Any]) -> None:
    implementation = as_dict(payload.get("implementation_summary"))
    negative = as_dict(payload.get("negative_result_summary"))
    claim_controls = as_dict(payload.get("claim_controls"))
    if (
        payload.get("schema") != "market_signal_source_native_benchmark_v1"
        or payload.get("protocol_id")
        != "LUMENCORE_MARKET_SIGNAL_SOURCE_NATIVE_20260729_V1"
        or payload.get("status")
        != "EXPLORATORY_RETROSPECTIVE_NEGATIVE_OR_INSUFFICIENT_EVIDENCE"
        or payload.get("external_actions") != []
        or not claim_controls
        or any(bool(value) for value in claim_controls.values())
    ):
        raise ValueError("Market-signal benchmark does not fail closed")
    expected_counts = {
        "registered_candidate_count": 4,
        "implemented_candidate_count": 4,
        "missing_candidate_implementation_count": 0,
        "registered_baseline_count": 4,
        "implemented_baseline_count": 4,
        "missing_baseline_implementation_count": 0,
        "source_count": 3,
        "source_series_count": 3,
        "strategy_source_series_result_count": 24,
    }
    if any(
        as_int(implementation.get(key), -1) != expected
        for key, expected in expected_counts.items()
    ):
        raise ValueError("Market-signal implementation counts are unexpected")
    if (
        as_int(negative.get("candidate_source_baseline_comparison_count"))
        != 48
        or as_int(negative.get("global_holm_positive_count")) != 0
        or as_int(negative.get("inference_insufficient_comparison_count"))
        != 48
        or as_int(
            negative.get(
                "candidate_beats_every_source_baseline_after_global_holm_count"
            )
        )
        != 0
        or negative.get("candidate_passes") != []
    ):
        raise ValueError("Market-signal negative-result gate changed")


def market_signal_cards(
    payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], set[str]]:
    validate_market_signal_benchmark(payload)
    implementation = as_dict(payload["implementation_summary"])
    candidate_ids = {
        str(value) for value in as_list(implementation.get("candidate_ids"))
    }
    baseline_ids = [
        str(value) for value in as_list(implementation.get("baseline_ids"))
    ]
    source_inputs = {
        str(row.get("source", "")).upper(): row
        for row in as_list(as_dict(payload.get("inputs")).get("source_snapshots"))
        if isinstance(row, dict)
    }
    series_by_source: dict[str, list[dict[str, Any]]] = {}
    for row in as_list(payload.get("series_results")):
        if isinstance(row, dict):
            series_by_source.setdefault(
                str(row.get("source", "")).upper(), []
            ).append(row)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for comparison in as_list(payload.get("comparisons")):
        if not isinstance(comparison, dict):
            continue
        key = (
            str(comparison.get("candidate_family_id", "")),
            str(comparison.get("source", "")).upper(),
        )
        grouped.setdefault(key, []).append(comparison)

    cards: list[dict[str, Any]] = []
    for (candidate_id, source), rows in sorted(grouped.items()):
        if candidate_id not in candidate_ids or source not in source_inputs:
            raise ValueError("Unexpected market-signal comparison identity")
        by_baseline = {
            str(row.get("baseline_id", "")): row for row in rows
        }
        if set(by_baseline) != set(baseline_ids):
            raise ValueError(
                f"Incomplete source-specific baseline set for "
                f"{candidate_id}/{source}"
            )
        comparisons: list[dict[str, Any]] = []
        for rank, baseline_id in enumerate(baseline_ids, start=1):
            row = by_baseline[baseline_id]
            inference_sufficient = bool(row.get("inference_sufficient"))
            comparisons.append(
                {
                    "baseline_family_id": baseline_id,
                    "baseline_rank": rank,
                    "candidate_score_delta": row.get(
                        "mean_risk_adjusted_score_delta"
                    ),
                    "candidate_beats_baseline_mean": bool(
                        row.get("candidate_beats_baseline_mean")
                    ),
                    "source_protocol_global_holm_adjusted_p_value": row.get(
                        "global_holm_adjusted_p_value"
                    ),
                    "global_holm_adjusted_p_value": None,
                    "statistically_positive_after_global_holm": False,
                    "paired_inference": {
                        "paired_unit_count": as_int(
                            row.get("source_series_cluster_count")
                        ),
                        "minimum_paired_unit_count": as_int(
                            row.get(
                                "minimum_clusters_for_interpretable_inference"
                            )
                        ),
                        "inference_sufficient": inference_sufficient,
                        "insufficiency_reason": row.get(
                            "insufficiency_reason", ""
                        ),
                        "independence_mode": "source_series_cluster",
                        "inference_scope": (
                            "One cluster per distinct source series; time "
                            "observations are not independent inferential units."
                        ),
                        "raw_two_sided_sign_test_p_value": row.get(
                            "raw_cluster_sign_test_p_value"
                        ),
                        "source_protocol_holm_adjusted_p_value": row.get(
                            "global_holm_adjusted_p_value"
                        ),
                    },
                }
            )
        source_series = series_by_source.get(source, [])
        source_input = source_inputs[source]
        cards.append(
            {
                "lane": "market_signal_geometry",
                "source": source,
                "source_snapshot_json": source_input.get("path", ""),
                "source_snapshot_sha256": source_input.get(
                    "registered_wiring_matrix_sha256", ""
                ),
                "candidate_family_id": candidate_id,
                "candidate_role": (
                    "exploratory_retrospective_market_signal_candidate"
                ),
                "prospectively_protected_candidate": False,
                "baseline_comparisons": comparisons,
                "source_specific_baseline_count": len(comparisons),
                "source_series_count": len(source_series),
                "evaluation_row_count": sum(
                    as_int(row.get("evaluation_observation_count"))
                    for row in source_series
                ),
                "market_signal_protocol_id": payload.get("protocol_id"),
                "market_signal_benchmark_payload_sha256": payload.get(
                    "payload_sha256"
                ),
                "inference_sufficient_comparison_count": sum(
                    1
                    for comparison in comparisons
                    if as_dict(comparison.get("paired_inference")).get(
                        "inference_sufficient"
                    )
                ),
                "public_performance_claim_allowed": False,
                "field_validation_claim_allowed": False,
                "real_dollar_savings_claim_allowed": False,
                "live_execution_allowed": False,
                "internal_source_native_promotion_gate_passed": False,
                "claim_stage": (
                    "direct_measured_inferentially_insufficient_no_promotion"
                ),
            }
        )

    adapter_receipt = {
        "lane": "market_signal_geometry",
        "adapter_status": "market_signal_source_native_sidecar_ran",
        "direct_source_count": len(source_inputs),
        "evaluation_row_count": sum(
            as_int(row.get("evaluation_observation_count"))
            for rows in series_by_source.values()
            for row in rows
        ),
        "evaluated_candidate_count": len(candidate_ids),
        "development_selected_candidate": "",
        "ingestion_summary": {
            "protocol_id": payload.get("protocol_id"),
            "source_series_count": implementation.get("source_series_count"),
            "comparison_count": as_dict(
                payload.get("negative_result_summary")
            ).get("candidate_source_baseline_comparison_count"),
            "inference_insufficient_comparison_count": as_dict(
                payload.get("negative_result_summary")
            ).get("inference_insufficient_comparison_count"),
            "global_holm_positive_count": 0,
            "promotion_allowed": False,
        },
    }
    return cards, adapter_receipt, candidate_ids


def apply_combined_global_holm(cards: list[dict[str, Any]]) -> None:
    indexed: list[tuple[float, str, str, str, dict[str, Any]]] = []
    for card in cards:
        for comparison in as_list(card.get("baseline_comparisons")):
            if not isinstance(comparison, dict):
                continue
            inference = as_dict(comparison.get("paired_inference"))
            indexed.append(
                (
                    as_float(
                        inference.get("raw_two_sided_sign_test_p_value"),
                        1.0,
                    ),
                    str(card.get("lane", "")),
                    str(card.get("source", "")),
                    (
                        f"{card.get('candidate_family_id', '')}::"
                        f"{comparison.get('baseline_family_id', '')}"
                    ),
                    comparison,
                )
            )
    indexed.sort(key=lambda row: row[:4])
    running_max = 0.0
    comparison_count = len(indexed)
    for rank, (raw_p, _, _, _, comparison) in enumerate(indexed, start=1):
        adjusted = min(1.0, (comparison_count - rank + 1) * raw_p)
        running_max = max(running_max, adjusted)
        inference = as_dict(comparison.get("paired_inference"))
        inference_sufficient = bool(
            inference.get("inference_sufficient", True)
        )
        positive = bool(
            inference_sufficient
            and comparison.get("candidate_beats_baseline_mean")
            and running_max < 0.05
        )
        comparison["global_holm_adjusted_p_value"] = round(
            running_max, 12
        )
        comparison["statistically_positive_after_global_holm"] = positive
        inference["ledger_global_holm_adjusted_p_value"] = round(
            running_max, 12
        )
        inference["ledger_global_holm_positive"] = positive
        comparison["paired_inference"] = inference

    for card in cards:
        comparisons = [
            row
            for row in as_list(card.get("baseline_comparisons"))
            if isinstance(row, dict)
        ]
        card["baseline_gauntlet"] = {
            "registered_baseline_count": len(comparisons),
            "mean_score_win_count": sum(
                1
                for row in comparisons
                if row.get("candidate_beats_baseline_mean")
            ),
            "global_holm_positive_count": sum(
                1
                for row in comparisons
                if row.get(
                    "statistically_positive_after_global_holm"
                )
            ),
            "candidate_beats_all_registered_baselines_mean": bool(
                comparisons
                and all(
                    row.get("candidate_beats_baseline_mean")
                    for row in comparisons
                )
            ),
            "candidate_beats_all_registered_baselines_after_global_holm": (
                bool(
                    comparisons
                    and all(
                        row.get(
                            "statistically_positive_after_global_holm"
                        )
                        for row in comparisons
                    )
                )
            ),
            "scope": (
                "Holm correction across every candidate-source-baseline "
                "comparison in this exhaustive direct-source ledger."
            ),
            "external_approval_claim": False,
        }
        full_gate = bool(
            card.get("prospectively_protected_candidate")
            and card["baseline_gauntlet"][
                "candidate_beats_all_registered_baselines_after_global_holm"
            ]
        )
        card["internal_source_native_promotion_gate_passed"] = full_gate
        card["public_performance_claim_allowed"] = False
        card["claim_stage"] = (
            "internal_source_native_gate_passed_external_validation_pending"
            if full_gate
            else "direct_measured_nonpromotion_or_exploratory_result"
        )


def route_status(
    family: dict[str, Any],
    source: str,
    baseline: str,
    card_index: dict[tuple[str, str, str], dict[str, Any]],
) -> tuple[str, dict[str, Any]]:
    family_id = str(family.get("family_id", ""))
    lane = str(family.get("lane", ""))
    card = card_index.get((lane, source, family_id), {})
    comparison = next(
        (
            row
            for row in as_list(card.get("baseline_comparisons"))
            if isinstance(row, dict)
            and str(row.get("baseline_family_id", "")) == baseline
        ),
        {},
    )
    if comparison:
        status = (
            "confirmatory_protocol_comparison_executed"
            if card.get("prospectively_protected_candidate")
            else "exploratory_direct_measured_comparison_executed"
        )
        return status, comparison
    if bool(family.get("implementation_present")):
        return "blocked_direct_adapter_missing_family", {}
    return "blocked_family_implementation_missing", {}


def next_action(
    family: dict[str, Any],
    direct_sources: list[dict[str, Any]],
    executed_route_count: int,
    blocked_adapter_route_count: int,
) -> str:
    if executed_route_count:
        if family.get("family_id") == "lissajous_phase_paths":
            return (
                "Preserve the negative confirmatory result. Freeze a new "
                "development-selected candidate and prospective holdout before "
                "another promotion attempt."
            )
        return (
            "Treat subset wins as hypothesis generation only. Diagnose the "
            "baselines that still win, then freeze a prospective source-native "
            "protocol before changing the candidate."
        )
    if blocked_adapter_route_count:
        return (
            "Implement the family in the existing direct-source adapter, add "
            "leakage tests, and freeze candidate identity before scoring."
        )
    if direct_sources:
        return (
            "Implement the registered family and its source-native metric adapter "
            "before inspecting candidate performance."
        )
    if family.get("source_conditioned_replay"):
        return (
            "Retain as conditioned-synthetic evidence only and obtain a source "
            "that carries the observed task outcome before direct comparison."
        )
    if family.get("frozen_generated_benchmark_executed"):
        return (
            "Keep the generated benchmark as software evidence and acquire a "
            "task-compatible measured source before any performance claim."
        )
    return (
        "Implement the family and pre-register its lane-native source, baselines, "
        "metrics, chronology, and failure conditions."
    )


def build_family_and_route_ledgers(
    protocol_field: dict[str, Any],
    matrix: dict[str, Any],
    cards: list[dict[str, Any]],
    implementation_overrides: set[str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    implementation_overrides = implementation_overrides or set()
    lane_index = {
        str(row.get("lane", "")): row
        for row in as_list(matrix.get("matrix"))
        if isinstance(row, dict) and row.get("lane")
    }
    card_index = {
        (
            str(card.get("lane", "")),
            str(card.get("source", "")).upper(),
            str(card.get("candidate_family_id", "")),
        ): card
        for card in cards
    }
    routes: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    for family in as_list(protocol_field.get("families")):
        if not isinstance(family, dict):
            continue
        family = dict(family)
        family_id = str(family.get("family_id", ""))
        if family_id in implementation_overrides:
            family["implementation_present"] = True
        lane = str(family.get("lane", ""))
        lane_row = as_dict(lane_index.get(lane))
        direct_sources = [
            row
            for row in as_list(lane_row.get("direct_measured_replay_sources"))
            if isinstance(row, dict)
        ]
        conditioned_sources = [
            row
            for row in as_list(
                lane_row.get(
                    "source_conditioned_synthetic_stress_sources"
                )
            )
            if isinstance(row, dict)
        ]
        family_routes: list[dict[str, Any]] = []
        for source_ref in direct_sources:
            source = str(source_ref.get("source", "")).upper()
            for baseline in as_list(
                source_ref.get("source_specific_baselines")
            ):
                baseline_id = str(baseline)
                status, comparison = route_status(
                    family, source, baseline_id, card_index
                )
                route = {
                    "lane": lane,
                    "family_id": family_id,
                    "source": source,
                    "source_rows": as_int(source_ref.get("rows")),
                    "source_snapshot_json": source_ref.get(
                        "snapshot_json", ""
                    ),
                    "source_snapshot_sha256": source_ref.get(
                        "snapshot_sha256", ""
                    ),
                    "baseline_id": baseline_id,
                    "status": status,
                    "candidate_implementation_present": bool(
                        family.get("implementation_present")
                    ),
                    "candidate_score_delta": comparison.get(
                        "candidate_score_delta"
                    ),
                    "candidate_beats_baseline_mean": bool(
                        comparison.get("candidate_beats_baseline_mean")
                    ),
                    "global_holm_adjusted_p_value": comparison.get(
                        "global_holm_adjusted_p_value"
                    ),
                    "statistically_positive_after_global_holm": bool(
                        comparison.get(
                            "statistically_positive_after_global_holm"
                        )
                    ),
                    "candidate_beats_every_source_baseline": bool(
                        as_dict(
                            card_index.get((lane, source, family_id), {})
                        )
                        .get("baseline_gauntlet", {})
                        .get(
                            "candidate_beats_all_registered_baselines_after_global_holm",
                            False,
                        )
                    ),
                    "public_performance_claim_allowed": False,
                    "real_dollar_savings_claim_allowed": False,
                }
                route["route_sha256"] = stable_sha256(route)
                routes.append(route)
                family_routes.append(route)

        executed = sum(
            1 for row in family_routes if row["status"].endswith("_executed")
        )
        confirmatory = sum(
            1
            for row in family_routes
            if row["status"]
            == "confirmatory_protocol_comparison_executed"
        )
        exploratory = sum(
            1
            for row in family_routes
            if row["status"]
            == "exploratory_direct_measured_comparison_executed"
        )
        blocked_adapter = sum(
            1
            for row in family_routes
            if row["status"] == "blocked_direct_adapter_missing_family"
        )
        blocked_implementation = sum(
            1
            for row in family_routes
            if row["status"] == "blocked_family_implementation_missing"
        )
        positive_subset = sum(
            1
            for row in family_routes
            if row["statistically_positive_after_global_holm"]
        )
        families.append(
            {
                "family_id": family_id,
                "label": family.get("label", family_id),
                "lane": lane,
                "registry_status": family.get("registry_status", ""),
                "disposition": family.get("disposition", ""),
                "implementation_present": bool(
                    family.get("implementation_present")
                ),
                "frozen_generated_benchmark_executed": bool(
                    family.get("frozen_generated_benchmark_executed")
                ),
                "source_conditioned_replay": family.get(
                    "source_conditioned_replay"
                ),
                "direct_source_count": len(direct_sources),
                "conditioned_source_count": len(conditioned_sources),
                "direct_source_baseline_route_count": len(family_routes),
                "executed_direct_route_count": executed,
                "confirmatory_direct_route_count": confirmatory,
                "exploratory_direct_route_count": exploratory,
                "blocked_adapter_route_count": blocked_adapter,
                "blocked_implementation_route_count": (
                    blocked_implementation
                ),
                "globally_corrected_subset_win_count": positive_subset,
                "beats_every_source_native_baseline_count": sum(
                    1
                    for source in {
                        row["source"] for row in family_routes
                    }
                    if as_dict(card_index.get((lane, source, family_id), {}))
                    .get("baseline_gauntlet", {})
                    .get(
                        "candidate_beats_all_registered_baselines_after_global_holm",
                        False,
                    )
                ),
                "public_performance_claim_allowed": False,
                "field_validation_claim_allowed": False,
                "real_dollar_savings_claim_allowed": False,
                "next_action": next_action(
                    family, direct_sources, executed, blocked_adapter
                ),
            }
        )
    families.sort(key=lambda row: (row["lane"], row["family_id"]))
    routes.sort(
        key=lambda row: (
            row["lane"],
            row["source"],
            row["family_id"],
            row["baseline_id"],
        )
    )
    return families, routes


def build_source_coverage_matrix(
    matrix: dict[str, Any],
    families: list[dict[str, Any]],
    routes: list[dict[str, Any]],
    cards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    coverage: list[dict[str, Any]] = []
    for lane_row in as_list(matrix.get("matrix")):
        if not isinstance(lane_row, dict):
            continue
        lane = str(lane_row.get("lane", ""))
        lane_families = [
            row for row in families if str(row.get("lane", "")) == lane
        ]
        for source_ref in as_list(
            lane_row.get("direct_measured_replay_sources")
        ):
            if not isinstance(source_ref, dict):
                continue
            source = str(source_ref.get("source", "")).upper()
            baseline_ids = [
                str(value)
                for value in as_list(
                    source_ref.get("source_specific_baselines")
                )
            ]
            source_routes = [
                row
                for row in routes
                if row.get("lane") == lane and row.get("source") == source
            ]
            source_cards = [
                row
                for row in cards
                if row.get("lane") == lane and row.get("source") == source
            ]
            comparisons = [
                comparison
                for card in source_cards
                for comparison in as_list(card.get("baseline_comparisons"))
                if isinstance(comparison, dict)
            ]
            executed_route_count = sum(
                1
                for row in source_routes
                if str(row.get("status", "")).endswith("_executed")
            )
            executed_family_ids = sorted(
                {
                    str(card.get("candidate_family_id", ""))
                    for card in source_cards
                    if card.get("candidate_family_id")
                }
            )
            coverage_status = (
                "EXECUTED_FULL_REGISTERED_FAMILY_COVERAGE"
                if lane_families
                and len(executed_family_ids) == len(lane_families)
                else (
                    "EXECUTED_PARTIAL_REGISTERED_FAMILY_COVERAGE"
                    if executed_route_count
                    else "BLOCKED_NO_EXECUTED_FAMILY_ADAPTER"
                )
            )
            row = {
                "lane": lane,
                "source": source,
                "source_rows": as_int(source_ref.get("rows")),
                "source_snapshot_json": source_ref.get("snapshot_json", ""),
                "source_snapshot_sha256": source_ref.get(
                    "snapshot_sha256", ""
                ),
                "source_native_baseline_ids": baseline_ids,
                "source_native_baseline_count": len(baseline_ids),
                "registered_lane_family_count": len(lane_families),
                "implemented_lane_family_count": sum(
                    1
                    for family in lane_families
                    if family.get("implementation_present")
                ),
                "executed_candidate_family_ids": executed_family_ids,
                "executed_candidate_family_count": len(executed_family_ids),
                "eligible_candidate_source_baseline_route_count": len(
                    source_routes
                ),
                "executed_candidate_source_baseline_route_count": (
                    executed_route_count
                ),
                "blocked_family_implementation_route_count": sum(
                    1
                    for route in source_routes
                    if route.get("status")
                    == "blocked_family_implementation_missing"
                ),
                "blocked_direct_adapter_route_count": sum(
                    1
                    for route in source_routes
                    if route.get("status")
                    == "blocked_direct_adapter_missing_family"
                ),
                "inference_sufficient_comparison_count": sum(
                    1
                    for comparison in comparisons
                    if as_dict(comparison.get("paired_inference")).get(
                        "inference_sufficient", True
                    )
                ),
                "inference_insufficient_comparison_count": sum(
                    1
                    for comparison in comparisons
                    if not as_dict(comparison.get("paired_inference")).get(
                        "inference_sufficient", True
                    )
                ),
                "candidate_beats_every_baseline_on_mean_count": sum(
                    1
                    for card in source_cards
                    if as_dict(card.get("baseline_gauntlet")).get(
                        "candidate_beats_all_registered_baselines_mean"
                    )
                ),
                "candidate_beats_every_baseline_after_global_holm_count": sum(
                    1
                    for card in source_cards
                    if as_dict(card.get("baseline_gauntlet")).get(
                        "candidate_beats_all_registered_baselines_after_global_holm"
                    )
                ),
                "prospectively_protected_candidate_count": sum(
                    1
                    for card in source_cards
                    if card.get("prospectively_protected_candidate")
                ),
                "internal_promotion_gate_pass_count": sum(
                    1
                    for card in source_cards
                    if card.get(
                        "internal_source_native_promotion_gate_passed"
                    )
                ),
                "coverage_status": coverage_status,
                "cross_source_baseline_substitution_allowed": False,
                "cross_lane_ranking_allowed": False,
                "public_performance_claim_allowed": False,
                "real_dollar_savings_claim_allowed": False,
            }
            row["source_baseline_contract_sha256"] = stable_sha256(
                {
                    "lane": lane,
                    "source": source,
                    "source_snapshot_sha256": row[
                        "source_snapshot_sha256"
                    ],
                    "source_native_baseline_ids": baseline_ids,
                }
            )
            coverage.append(row)
    coverage.sort(key=lambda row: (row["lane"], row["source"]))
    return coverage


def build_adapter_expansion_queue(
    families: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    queued: list[dict[str, Any]] = []
    for family in families:
        if (
            family.get("direct_source_count", 0) <= 0
            or family.get("implementation_present")
        ):
            continue
        registry_status = str(family.get("registry_status", ""))
        if registry_status == "benchmark_design_ready":
            priority_tier = 1
            evidence_role = "development_only_benchmark_candidate"
        elif registry_status == "legacy_transform_only":
            priority_tier = 3
            evidence_role = "exploratory_legacy_transform_control"
        else:
            priority_tier = 2
            evidence_role = "development_only_research_candidate"
        queued.append(
            {
                "lane": family.get("lane", ""),
                "family_id": family.get("family_id", ""),
                "label": family.get("label", ""),
                "registry_status": registry_status,
                "disposition": family.get("disposition", ""),
                "priority_tier": priority_tier,
                "evidence_role": evidence_role,
                "direct_source_count": family.get("direct_source_count", 0),
                "potential_source_baseline_route_count": family.get(
                    "direct_source_baseline_route_count", 0
                ),
                "required_adapter_tests": [
                    "deterministic_replay",
                    "chronology_and_no_future_data",
                    "matched_compute_budget",
                    "source_native_metric_and_units",
                    "missing_data_and_abstention",
                    "no_holdout_selected_candidate",
                ],
                "development_sweep_allowed": True,
                "holdout_selection_allowed": False,
                "confirmatory_claim_allowed_after_development_sweep": False,
                "public_performance_claim_allowed": False,
                "next_action": (
                    "Implement in the existing lane adapter, run only on the "
                    "development partition, and freeze one challenger before a "
                    "new prospective or untouched holdout evaluation."
                ),
            }
        )
    queued.sort(
        key=lambda row: (
            as_int(row.get("priority_tier"), 99),
            -as_int(row.get("potential_source_baseline_route_count")),
            str(row.get("lane", "")),
            str(row.get("family_id", "")),
        )
    )
    for rank, row in enumerate(queued, start=1):
        row["rank"] = rank
    return queued


def build_payload(generated_utc: str | None = None) -> dict[str, Any]:
    generated = generated_utc or now_utc()
    registry = read_json(REGISTRY_JSON)
    protocol_field = read_json(PROTOCOL_FIELD_JSON)
    matrix = read_json(WIRING_MATRIX_JSON)
    top_replay = read_json(TOP_REPLAY_JSON)
    top_module = load_module(
        TOP_REPLAY_BUILDER, "source_native_top_replay_module"
    )
    market_module = load_module(
        MARKET_SIGNAL_BENCHMARK_BUILDER,
        "market_signal_source_native_benchmark_module",
    )

    cards, adapter_receipts = execute_direct_cards(matrix, top_module)
    market_payload = market_module.build_payload(generated)
    market_cards, market_receipt, implementation_overrides = (
        market_signal_cards(market_payload)
    )
    cards.extend(market_cards)
    adapter_receipts.append(market_receipt)
    apply_combined_global_holm(cards)
    families, routes = build_family_and_route_ledgers(
        protocol_field,
        matrix,
        cards,
        implementation_overrides=implementation_overrides,
    )
    source_coverage = build_source_coverage_matrix(
        matrix, families, routes, cards
    )
    adapter_expansion_queue = build_adapter_expansion_queue(families)
    positive_comparisons = [
        {
            "lane": card["lane"],
            "source": card["source"],
            "candidate_family_id": card["candidate_family_id"],
            "baseline_family_id": comparison["baseline_family_id"],
            "candidate_score_delta": comparison["candidate_score_delta"],
            "global_holm_adjusted_p_value": comparison[
                "global_holm_adjusted_p_value"
            ],
            "claim_stage": "subset_research_lead_not_full_gauntlet_pass",
        }
        for card in cards
        for comparison in as_list(card.get("baseline_comparisons"))
        if isinstance(comparison, dict)
        and comparison.get("statistically_positive_after_global_holm")
    ]
    direct_source_lanes = [
        row
        for row in as_list(matrix.get("matrix"))
        if isinstance(row, dict)
        and as_list(row.get("direct_measured_replay_sources"))
    ]
    summary = {
        "registered_family_count": len(families),
        "implementation_present_count": sum(
            1 for row in families if row["implementation_present"]
        ),
        "implementation_required_count": sum(
            1 for row in families if not row["implementation_present"]
        ),
        "lane_count": len(
            {
                str(row.get("lane", ""))
                for row in as_list(protocol_field.get("lane_summary"))
                if isinstance(row, dict)
            }
        ),
        "lane_with_qualified_direct_source_count": len(
            direct_source_lanes
        ),
        "lane_with_executable_direct_adapter_count": sum(
            1
            for row in adapter_receipts
            if str(row.get("adapter_status", "")).endswith("_ran")
        ),
        "qualified_direct_source_link_count": sum(
            len(as_list(row.get("direct_measured_replay_sources")))
            for row in direct_source_lanes
        ),
        "family_in_direct_source_lane_count": sum(
            1 for row in families if row["direct_source_count"] > 0
        ),
        "implemented_family_in_direct_source_lane_count": sum(
            1
            for row in families
            if row["direct_source_count"] > 0
            and row["implementation_present"]
        ),
        "direct_candidate_source_card_count": len(cards),
        "direct_candidate_family_count": len(
            {row["candidate_family_id"] for row in cards}
        ),
        "direct_source_baseline_route_count": len(routes),
        "executed_direct_source_baseline_comparison_count": sum(
            1 for row in routes if row["status"].endswith("_executed")
        ),
        "confirmatory_protocol_comparison_count": sum(
            1
            for row in routes
            if row["status"]
            == "confirmatory_protocol_comparison_executed"
        ),
        "exploratory_direct_comparison_count": sum(
            1
            for row in routes
            if row["status"]
            == "exploratory_direct_measured_comparison_executed"
        ),
        "blocked_direct_adapter_route_count": sum(
            1
            for row in routes
            if row["status"] == "blocked_direct_adapter_missing_family"
        ),
        "blocked_implementation_route_count": sum(
            1
            for row in routes
            if row["status"] == "blocked_family_implementation_missing"
        ),
        "source_coverage_card_count": len(source_coverage),
        "direct_lane_missing_family_implementation_count": len(
            adapter_expansion_queue
        ),
        "benchmark_design_ready_adapter_backlog_count": sum(
            1
            for row in adapter_expansion_queue
            if row["registry_status"] == "benchmark_design_ready"
        ),
        "legacy_transform_exploratory_backlog_count": sum(
            1
            for row in adapter_expansion_queue
            if row["registry_status"] == "legacy_transform_only"
        ),
        "individual_comparison_global_holm_positive_count": len(
            positive_comparisons
        ),
        "candidate_source_beats_every_baseline_mean_count": sum(
            1
            for row in cards
            if as_dict(row.get("baseline_gauntlet")).get(
                "candidate_beats_all_registered_baselines_mean"
            )
        ),
        "candidate_source_beats_every_baseline_global_holm_count": sum(
            1
            for row in cards
            if as_dict(row.get("baseline_gauntlet")).get(
                "candidate_beats_all_registered_baselines_after_global_holm"
            )
        ),
        "internal_source_native_promotion_gate_pass_count": sum(
            1
            for row in cards
            if row["internal_source_native_promotion_gate_passed"]
        ),
        "market_signal_candidate_count": as_int(
            as_dict(market_payload.get("implementation_summary")).get(
                "implemented_candidate_count"
            )
        ),
        "market_signal_source_count": as_int(
            as_dict(market_payload.get("implementation_summary")).get(
                "source_count"
            )
        ),
        "market_signal_comparison_count": as_int(
            as_dict(market_payload.get("negative_result_summary")).get(
                "candidate_source_baseline_comparison_count"
            )
        ),
        "market_signal_descriptive_mean_win_count": as_int(
            as_dict(market_payload.get("negative_result_summary")).get(
                "comparison_mean_win_count"
            )
        ),
        "market_signal_inference_insufficient_count": as_int(
            as_dict(market_payload.get("negative_result_summary")).get(
                "inference_insufficient_comparison_count"
            )
        ),
        "market_signal_global_holm_positive_count": as_int(
            as_dict(market_payload.get("negative_result_summary")).get(
                "global_holm_positive_count"
            )
        ),
        "market_signal_promoted_candidate_count": as_int(
            as_dict(market_payload.get("negative_result_summary")).get(
                "candidate_beats_every_source_baseline_after_global_holm_count"
            )
        ),
        "public_performance_claim_allowed": False,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "claim_boundary": BOUNDARY,
    }
    payload = {
        "schema": "source_native_family_baseline_ledger_v1",
        "generated_utc": generated,
        "purpose": (
            "Enumerate every registered family against each currently qualified "
            "direct source and that source's registered baselines, execute every "
            "available adapter, and expose blockers without cross-task ranking."
        ),
        "boundary": BOUNDARY,
        "direct_answer": {
            "can_run_every_family_now": False,
            "why_not": (
                f"{summary['implementation_required_count']} of "
                f"{summary['registered_family_count']} registered families lack "
                "implementations, and only "
                f"{summary['lane_with_executable_direct_adapter_count']} lanes "
                "currently have executable direct measured adapters."
            ),
            "what_ran_now": (
                f"{summary['executed_direct_source_baseline_comparison_count']} "
                "candidate-source-baseline comparisons across "
                f"{summary['direct_candidate_source_card_count']} candidate/source "
                "cards."
            ),
            "what_won": (
                f"{summary['individual_comparison_global_holm_positive_count']} "
                "individual subset comparisons survived global correction, but "
                f"{summary['candidate_source_beats_every_baseline_global_holm_count']} "
                "candidate/source cards beat every registered baseline."
            ),
            "current_alpha_or_champion": "none",
            "what_next": (
                f"Implement the {len(adapter_expansion_queue)} missing families "
                "that are compatible with qualified direct-source lanes as "
                "development-only adapters, then freeze a small challenger set "
                "before any untouched or prospective scoring."
            ),
        },
        "registry_separation": {
            "family_registry": str(REGISTRY_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "source_and_baseline_contract_registry": str(
                WIRING_MATRIX_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "live_breadth_inventory_role": (
                "Source discovery, custody, freshness, task compatibility, and "
                "qualification only."
            ),
            "source_native_benchmark_role": (
                "Candidate scoring only after a qualified source is paired with "
                "that source's predeclared lane-native baselines and metric."
            ),
            "live_breadth_inventory_is_performance_evidence": False,
            "inventory_row_count_is_benchmark_sample_size": False,
            "cross_source_baseline_substitution_allowed": False,
            "cross_lane_ranking_allowed": False,
        },
        "summary": summary,
        "positive_subset_research_leads": positive_comparisons,
        "retired_retrospective_findings": [
            {
                "source": "FRED",
                "candidate_family_id": "fractal_brownian_surface",
                "former_baseline_family_ids": [
                    "exponential_smoothing",
                    "moving_average",
                ],
                "disposition": (
                    "retired_after_source_series_cluster_inference_and_stale_"
                    "acquisition_audit"
                ),
                "promotion_claim_allowed": False,
            },
            {
                "source": "TWELVE_DATA",
                "candidate_family_id": "fractal_brownian_surface",
                "former_baseline_family_ids": ["moving_average"],
                "disposition": (
                    "retired_after_source_series_cluster_inference"
                ),
                "promotion_claim_allowed": False,
            },
        ],
        "candidate_source_cards": cards,
        "adapter_receipts": adapter_receipts,
        "family_ledger": families,
        "source_baseline_route_ledger": routes,
        "source_coverage_matrix": source_coverage,
        "adapter_expansion_queue": adapter_expansion_queue,
        "prospective_priorities": [
            {
                "rank": 1,
                "lane": "time_series_model_routing",
                "source": "FRED",
                "family_id": "fractal_brownian_surface",
                "reason": (
                    "The candidate trails stronger source-native baselines, and "
                    "the former subset positives disappear when overlapping "
                    "origins and horizons are clustered by source series. Rebuild "
                    "the latest-data custody chain and freeze a prospective "
                    "challenger before any retest."
                ),
                "promotion_claim_allowed": False,
            },
            {
                "rank": 2,
                "lane": "time_series_model_routing",
                "source": "TWELVE_DATA",
                "family_id": "fractal_brownian_surface",
                "reason": (
                    "The former moving-average subset result does not survive "
                    "source-series cluster inference, and the eight-baseline "
                    "gauntlet fails. Keep it as retired hypothesis-generation "
                    "history only."
                ),
                "promotion_claim_allowed": False,
            },
            {
                "rank": 3,
                "lane": "market_signal_geometry",
                "source": "KRAKEN_PUBLIC,TWELVE_DATA,ALPHAVANTAGE",
                "family_id": "preselect_one_after_development_only",
                "reason": (
                    "Three qualified direct OHLC sources and four registered "
                    "baselines now cover four fixed candidate implementations. "
                    "All 48 comparisons remain inferentially insufficient because "
                    "each source currently contributes only one source-series "
                    "cluster. Expand independent clusters under a frozen protocol "
                    "and keep the lane paper/replay-only."
                ),
                "promotion_claim_allowed": False,
            },
        ],
        "claim_controls": {
            "cross_lane_ranking_allowed": False,
            "subset_win_is_champion": False,
            "conditioned_synthetic_is_direct_measured": False,
            "inventory_rows_are_performance_evidence": False,
            "hash_identity_is_model_skill": False,
            "public_performance_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_execution_allowed": False,
        },
        "inputs": {
            "registry": str(REGISTRY_JSON.relative_to(ROOT)).replace("\\", "/"),
            "protocol_field": str(
                PROTOCOL_FIELD_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "wiring_matrix": str(
                WIRING_MATRIX_JSON.relative_to(ROOT)
            ).replace("\\", "/"),
            "top_replay_context": str(TOP_REPLAY_JSON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "registry_schema": registry.get("schema", ""),
            "protocol_field_schema": protocol_field.get("schema", ""),
            "wiring_matrix_schema": matrix.get("schema", ""),
            "top_replay_schema": top_replay.get("schema", ""),
            "market_signal_benchmark": {
                "path": str(
                    MARKET_SIGNAL_BENCHMARK_JSON.relative_to(ROOT)
                ).replace("\\", "/"),
                "schema": market_payload.get("schema", ""),
                "protocol_id": market_payload.get("protocol_id", ""),
                "payload_sha256": market_payload.get("payload_sha256", ""),
                "status": market_payload.get("status", ""),
                "built_in_memory_from_current_inputs": True,
            },
        },
    }
    payload["ledger_sha256"] = stable_sha256(
        {
            "summary": summary,
            "positive_subset_research_leads": positive_comparisons,
            "candidate_source_cards": cards,
            "family_ledger": families,
            "source_baseline_route_ledger": routes,
            "source_coverage_matrix": source_coverage,
            "adapter_expansion_queue": adapter_expansion_queue,
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Source-Native Family Baseline Ledger",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Ledger SHA-256: `{payload['ledger_sha256']}`",
        "",
        "## Direct Answer",
        "",
        f"- Can run every family now: `{str(payload['direct_answer']['can_run_every_family_now']).lower()}`",
        f"- Why not: {payload['direct_answer']['why_not']}",
        f"- What ran: {payload['direct_answer']['what_ran_now']}",
        f"- What won: {payload['direct_answer']['what_won']}",
        f"- What next: {payload['direct_answer']['what_next']}",
        "- Current alpha or champion: `none`",
        "",
        "## Registry Separation",
        "",
        (
            "The live-breadth registry and the source-native benchmark ledger "
            "are not the same thing. Live breadth qualifies source custody, "
            "freshness, and task compatibility. This ledger scores a candidate "
            "only after that source is paired with its predeclared native "
            "baselines and metric."
        ),
        "- Live-breadth inventory rows are performance evidence: `false`",
        "- Cross-source baseline substitution allowed: `false`",
        "- Cross-lane ranking allowed: `false`",
        "",
        "## Current Coverage",
        "",
        f"- Registered families: `{summary['registered_family_count']}`",
        f"- Implemented families: `{summary['implementation_present_count']}`",
        f"- Missing implementations: `{summary['implementation_required_count']}`",
        f"- Qualified direct-source links: `{summary['qualified_direct_source_link_count']}`",
        f"- Executable direct adapters: `{summary['lane_with_executable_direct_adapter_count']}`",
        f"- Candidate/source cards: `{summary['direct_candidate_source_card_count']}`",
        f"- Source-baseline routes: `{summary['direct_source_baseline_route_count']}`",
        f"- Executed comparisons: `{summary['executed_direct_source_baseline_comparison_count']}`",
        f"- Globally corrected individual subset wins: `{summary['individual_comparison_global_holm_positive_count']}`",
        f"- Full source-native gauntlet passes: `{summary['candidate_source_beats_every_baseline_global_holm_count']}`",
        f"- Direct-lane adapter backlog: `{summary['direct_lane_missing_family_implementation_count']}`",
        "",
        "## Per-Source Native Baseline Coverage",
        "",
        "| Lane | Source | Native Baselines | Families Run / Registered | Routes Run / Eligible | Mean All-Baseline Leads | Holm All-Baseline Passes | Status |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["source_coverage_matrix"]:
        lines.append(
            f"| `{row['lane']}` | `{row['source']}` | "
            f"{row['source_native_baseline_count']} | "
            f"{row['executed_candidate_family_count']} / "
            f"{row['registered_lane_family_count']} | "
            f"{row['executed_candidate_source_baseline_route_count']} / "
            f"{row['eligible_candidate_source_baseline_route_count']} | "
            f"{row['candidate_beats_every_baseline_on_mean_count']} | "
            f"{row['candidate_beats_every_baseline_after_global_holm_count']} | "
            f"`{row['coverage_status']}` |"
        )
    lines.extend(
        [
        "",
        "## Claim Boundary",
        "",
        payload["boundary"],
        "",
        "## Positive Subset Research Leads",
        "",
        "| Source | Candidate | Baseline | Score Delta | Global Holm p |",
        "| --- | --- | --- | ---: | ---: |",
        ]
    )
    for row in payload["positive_subset_research_leads"]:
        lines.append(
            f"| `{row['source']}` | `{row['candidate_family_id']}` | "
            f"`{row['baseline_family_id']}` | "
            f"{as_float(row['candidate_score_delta']):.6f} | "
            f"{as_float(row['global_holm_adjusted_p_value']):.8f} |"
        )
    lines.extend(
        [
            "",
            "Every lead above fails the full source-native baseline gauntlet and "
            "is not a champion, alpha claim, field result, or dollar claim.",
            "",
            "## Prospective Priorities",
            "",
        ]
    )
    for row in payload["prospective_priorities"]:
        lines.append(
            f"- `{row['rank']}` `{row['lane']}` / `{row['source']}` / "
            f"`{row['family_id']}`: {row['reason']}"
        )
    lines.extend(
        [
            "",
            "## Family Execution Ledger",
            "",
            "| Lane | Family | Implemented | Routes Run | Subset Wins | Full Passes | Next Action |",
            "| --- | --- | :---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["family_ledger"]:
        lines.append(
            f"| `{row['lane']}` | `{row['family_id']}` | "
            f"{str(row['implementation_present']).lower()} | "
            f"{row['executed_direct_route_count']} | "
            f"{row['globally_corrected_subset_win_count']} | "
            f"{row['beats_every_source_native_baseline_count']} | "
            f"{row['next_action']} |"
        )
    return "\n".join(lines).rstrip() + "\n"


def write_outputs(payload: dict[str, Any]) -> None:
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "json": str(OUT_JSON.relative_to(ROOT)).replace("\\", "/"),
                "dashboard_json": str(DASHBOARD_JSON.relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "markdown": str(OUT_MD.relative_to(ROOT)).replace("\\", "/"),
                "registered_families": payload["summary"][
                    "registered_family_count"
                ],
                "executed_comparisons": payload["summary"][
                    "executed_direct_source_baseline_comparison_count"
                ],
                "global_subset_wins": payload["summary"][
                    "individual_comparison_global_holm_positive_count"
                ],
                "full_gauntlet_passes": payload["summary"][
                    "candidate_source_beats_every_baseline_global_holm_count"
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
