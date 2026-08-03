from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

GAUNTLET_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
LOCKED_SWEEP_JSON = DASHBOARD_DATA / "locked_source_baseline_replay_sweep.json"
READY_REPLAY_JSON = DASHBOARD_DATA / "geometry_ready_source_replay.json"
KURAMOTO_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"

OUT_JSON = OUT_OPS / "champion_metric_battery_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_metric_battery.json"
DOC_MD = DOCS / "CHAMPION_METRIC_BATTERY.md"

EXPECTED_SCHEMAS = {
    "gauntlet": "champion_metric_gauntlet_v2",
    "locked_sweep": "locked_source_baseline_replay_sweep_v2",
    "ready_replay": "geometry_ready_source_replay_v2",
    "kuramoto": "kuramoto_holdout_expansion_v2",
}


def now_utc() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_int(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def require_schema(name: str, payload: dict[str, Any]) -> None:
    expected = EXPECTED_SCHEMAS[name]
    actual = payload.get("schema")
    if actual != expected:
        raise ValueError(f"{name} schema must be {expected}; got {actual!r}")


def canonical_sha256(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_inputs() -> dict[str, dict[str, Any]]:
    inputs = {
        "gauntlet": read_json(GAUNTLET_JSON),
        "locked_sweep": read_json(LOCKED_SWEEP_JSON),
        "ready_replay": read_json(READY_REPLAY_JSON),
        "kuramoto": read_json(KURAMOTO_JSON),
    }
    for name, payload in inputs.items():
        require_schema(name, payload)
    return inputs


def category(
    category_id: str,
    label: str,
    status: str,
    evidence: dict[str, Any],
    interpretation: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "category_id": category_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "interpretation": interpretation,
        "next_action": next_action,
    }


def build_payload(inputs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    inputs = inputs or load_inputs()
    for name, input_payload in inputs.items():
        require_schema(name, input_payload)

    gauntlet_summary = as_dict(inputs["gauntlet"].get("summary"))
    sweep_summary = as_dict(inputs["locked_sweep"].get("summary"))
    ready_summary = as_dict(inputs["ready_replay"].get("summary"))
    kuramoto_summary = as_dict(inputs["kuramoto"].get("summary"))

    holdout_count = as_int(kuramoto_summary.get("holdout_count"))
    holdout_wins = as_int(kuramoto_summary.get("wins_vs_kalman"))
    mean_skill_delta = round(as_float(kuramoto_summary.get("mean_delta_vs_kalman")), 6)
    baseline_passes = as_int(kuramoto_summary.get("registered_baseline_gate_pass_count"))
    baseline_count = as_int(kuramoto_summary.get("registered_baseline_count"))
    direct_routes = as_int(ready_summary.get("direct_measured_replay_count"))
    conditioned_routes = as_int(ready_summary.get("source_conditioned_synthetic_stress_count"))
    comparisons = as_int(sweep_summary.get("baseline_comparison_count"))
    global_holm_positives = as_int(sweep_summary.get("global_holm_positive_count"))
    conditioned_named_wins = as_int(
        ready_summary.get("source_conditioned_named_baseline_mean_win_count")
    )
    performance_rows = as_int(ready_summary.get("performance_rows_reviewed"))
    legacy_rows_excluded = as_int(
        ready_summary.get("legacy_ready_for_benchmark_rows_excluded")
    )
    numeric_fallbacks = as_int(ready_summary.get("numeric_fallback_profile_count"))
    candidate_selected = bool(kuramoto_summary.get("candidate_was_protocol_selected"))
    internal_champion = bool(gauntlet_summary.get("internal_champion")) and bool(
        kuramoto_summary.get("protocol_grade_internal_champion")
    )

    categories = [
        category(
            "development_selection",
            "Frozen development selection",
            "BLOCKED",
            {
                "audited_candidate": kuramoto_summary.get("candidate"),
                "development_selected_candidate": kuramoto_summary.get(
                    "development_selected_candidate"
                ),
                "candidate_was_protocol_selected": candidate_selected,
            },
            "Kuramoto is a post-selection audit and cannot inherit the selected candidate's status.",
            "Keep candidate selection frozen before any future holdout is opened.",
        ),
        category(
            "direct_measured_named_baseline",
            "Direct measured named-baseline result",
            "MEASURED_NONPROMOTION",
            {
                "named_baseline": kuramoto_summary.get("named_baseline"),
                "paired_day_wins": holdout_wins,
                "paired_day_count": holdout_count,
                "mean_skill_delta": mean_skill_delta,
            },
            "The paired win rate is below one half and mean skill is negative.",
            "Report the negative result and redesign on development data only.",
        ),
        category(
            "source_specific_baseline_gauntlet",
            "All registered source-specific baselines",
            "BLOCKED",
            {
                "gate_pass_count": baseline_passes,
                "registered_baseline_count": baseline_count,
            },
            "No registered EIA baseline clears the complete candidate promotion gate.",
            "Require every source-native baseline gate to pass before promotion.",
        ),
        category(
            "global_holm_promotion",
            "Global multiplicity-corrected promotion",
            "BLOCKED",
            {
                "global_holm_positive_count": global_holm_positives,
                "baseline_comparison_count": comparisons,
            },
            "No comparison is positive after the global Holm correction.",
            "Freeze the family set and rerun the global correction on new held-out data.",
        ),
        category(
            "direct_measured_route_coverage",
            "Compatibility-qualified direct measured routes",
            "PASS_COVERAGE_ONLY",
            {
                "direct_measured_routes": direct_routes,
                "performance_rows_reviewed": performance_rows,
            },
            "Route and row depth describe benchmark coverage, not superiority.",
            "Add task-compatible measured sources without reusing holdouts for tuning.",
        ),
        category(
            "conditioned_synthetic_research",
            "Conditioned synthetic research leads",
            "RESEARCH_ONLY",
            {
                "conditioned_synthetic_routes": conditioned_routes,
                "conditioned_named_baseline_mean_win_count": conditioned_named_wins,
                "lead_lanes": ["thermal_ventilation", "branching_transport"],
            },
            "Thermal and branching can guide experiments but are not measured performance evidence.",
            "Create source-native measured tasks before considering either lane for promotion.",
        ),
        category(
            "compatibility_hygiene",
            "Compatibility and fallback hygiene",
            "PASS",
            {
                "legacy_rows_excluded": legacy_rows_excluded,
                "numeric_fallback_count": numeric_fallbacks,
            },
            "Incompatible legacy rows are excluded and numeric fallback profiles are absent.",
            "Preserve this fail-closed boundary in every downstream artifact.",
        ),
        category(
            "source_inventory",
            "Broader source inventory",
            "INVENTORY_ONLY",
            {
                "measured_provider_count": as_int(
                    gauntlet_summary.get("broader_measured_provider_count")
                ),
                "enabled_provider_count": as_int(
                    gauntlet_summary.get("broader_enabled_provider_count")
                ),
                "is_performance_evidence": False,
            },
            "Source breadth is research inventory, not performance evidence.",
            "Qualify each source against a task-specific adapter and baseline registry.",
        ),
        category(
            "external_validation",
            "Independent external validation",
            "BLOCKED_EXTERNAL",
            {
                "field_validation_claim_allowed": False,
                "independent_replication_complete": False,
            },
            "No independent owner-approved validation is complete.",
            "Use an outcome-independent evaluator and a preregistered acceptance protocol.",
        ),
        category(
            "economic_conversion",
            "Economic conversion",
            "BLOCKED_EXTERNAL",
            {
                "real_dollar_savings_claim_allowed": False,
                "safe_estimated_annual_value_usd": 0.0,
            },
            "No owner-approved cost model or realized-savings evidence exists.",
            "Price protocol and evidence-review work only; do not price unproven savings.",
        ),
    ]

    pass_count = sum(row["status"] in {"PASS", "PASS_COVERAGE_ONLY"} for row in categories)
    blocked_count = sum(row["status"].startswith("BLOCKED") for row in categories)
    research_only_count = sum(
        row["status"] in {"RESEARCH_ONLY", "INVENTORY_ONLY"} for row in categories
    )

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_metric_battery_v2",
        "purpose": (
            "Consolidate the canonical v2 evidence gates while keeping negative measured results, "
            "conditioned research leads, and source inventory semantically separate."
        ),
        "summary": {
            "internal_performance_champion": internal_champion,
            "champion_family": None,
            "audited_candidate_family": kuramoto_summary.get("candidate"),
            "development_selected_candidate": kuramoto_summary.get(
                "development_selected_candidate"
            ),
            "candidate_was_protocol_selected": candidate_selected,
            "named_baseline": kuramoto_summary.get("named_baseline"),
            "paired_day_wins_vs_named_baseline": holdout_wins,
            "paired_day_count": holdout_count,
            "mean_skill_delta_vs_named_baseline": mean_skill_delta,
            "registered_baseline_gate_pass_count": baseline_passes,
            "registered_baseline_count": baseline_count,
            "direct_measured_route_count": direct_routes,
            "conditioned_synthetic_route_count": conditioned_routes,
            "baseline_comparison_count": comparisons,
            "global_holm_positive_count": global_holm_positives,
            "conditioned_named_baseline_mean_win_count": conditioned_named_wins,
            "performance_rows_reviewed": performance_rows,
            "legacy_rows_excluded": legacy_rows_excluded,
            "numeric_fallback_count": numeric_fallbacks,
            "metric_category_count": len(categories),
            "metric_pass_count": pass_count,
            "metric_blocked_count": blocked_count,
            "metric_research_or_inventory_only_count": research_only_count,
            "source_inventory_is_performance_evidence": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                f"No internal performance champion exists. Kuramoto was not development-selected, "
                f"won {holdout_wins}/{holdout_count} paired days against "
                f"{kuramoto_summary.get('named_baseline')}, and recorded mean skill delta "
                f"{mean_skill_delta:.6f}. It cleared {baseline_passes}/{baseline_count} registered "
                f"baselines; the full {comparisons}-comparison sweep has "
                f"{global_holm_positives} global Holm positives."
            ),
        },
        "metric_categories": categories,
        "reviewer_safe_claims": [
            (
                f"Kuramoto produced a measured nonpromotion result of {holdout_wins}/{holdout_count} "
                f"paired-day wins and mean skill delta {mean_skill_delta:.6f} against "
                f"{kuramoto_summary.get('named_baseline')}."
            ),
            (
                f"The compatibility-qualified stack currently includes {direct_routes} direct measured "
                f"routes and {conditioned_routes} conditioned synthetic research routes."
            ),
            (
                f"The current artifacts review {performance_rows} performance rows, exclude "
                f"{legacy_rows_excluded} incompatible legacy rows, and use {numeric_fallbacks} numeric "
                "fallback profiles."
            ),
        ],
        "prohibited_claims": [
            "current internal performance champion",
            "performance superiority inferred from conditioned simulation",
            "field validation complete",
            "realized dollar savings",
            "source inventory proves performance",
        ],
        "best_next_work": [
            {
                "priority": 1,
                "work": "Independent protocol and evidence review",
                "why": "This can be sold truthfully without asserting performance or savings.",
            },
            {
                "priority": 2,
                "work": "Development-only candidate redesign",
                "why": "Kuramoto and Lissajous both fail the current direct measured EIA promotion gate.",
            },
            {
                "priority": 3,
                "work": "Measured adapters for thermal and branching tasks",
                "why": "Conditioned synthetic leads need source-native tasks and accepted baselines.",
            },
        ],
        "claim_state": {
            "measured_nonpromotion_result_claim_allowed": True,
            "internal_performance_champion_claim_allowed": False,
            "conditioned_synthetic_performance_claim_allowed": False,
            "source_inventory_performance_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
        },
        "inputs": {
            "champion_metric_gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)),
            "locked_source_baseline_replay_sweep": str(
                LOCKED_SWEEP_JSON.relative_to(ROOT)
            ),
            "geometry_ready_source_replay": str(READY_REPLAY_JSON.relative_to(ROOT)),
            "kuramoto_holdout_expansion": str(KURAMOTO_JSON.relative_to(ROOT)),
        },
    }
    payload["metric_battery_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Champion Metric Battery",
        "",
        "## Battery Status",
        "",
        summary.get("plain_english_answer", ""),
        "",
        f"- Internal performance champion: `{str(summary.get('internal_performance_champion')).lower()}`",
        f"- Audited candidate: `{summary.get('audited_candidate_family')}`",
        f"- Development-selected candidate: `{summary.get('development_selected_candidate')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        (
            f"- Paired-day wins: `{summary.get('paired_day_wins_vs_named_baseline')}/"
            f"{summary.get('paired_day_count')}`"
        ),
        f"- Mean skill delta: `{summary.get('mean_skill_delta_vs_named_baseline')}`",
        (
            f"- Registered baseline gates: `{summary.get('registered_baseline_gate_pass_count')}/"
            f"{summary.get('registered_baseline_count')}`"
        ),
        (
            f"- Global Holm positives: `{summary.get('global_holm_positive_count')}/"
            f"{summary.get('baseline_comparison_count')}`"
        ),
        f"- Performance rows reviewed: `{summary.get('performance_rows_reviewed')}`",
        f"- Legacy rows excluded: `{summary.get('legacy_rows_excluded')}`",
        f"- Numeric fallbacks: `{summary.get('numeric_fallback_count')}`",
        f"- Field-validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary.get('real_dollar_savings_claim_allowed')).lower()}`",
        "",
        "## Metric Categories",
        "",
        "| Category | Status | Interpretation |",
        "|---|---|---|",
    ]
    for row_value in payload.get("metric_categories", []):
        row = as_dict(row_value)
        lines.append(
            f"| `{row.get('category_id')}` | `{row.get('status')}` | "
            f"{row.get('interpretation')} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Thermal and branching conditioned simulations are research leads only.",
            "- Source breadth is inventory, not performance evidence.",
            "- The safe commercial scope is protocol and evidence review, not performance or savings.",
            "",
            f"Metric battery SHA-256: `{payload.get('metric_battery_sha256')}`",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    DOC_MD.parent.mkdir(parents=True, exist_ok=True)
    DOC_MD.write_text(render_markdown(payload), encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "internal_performance_champion": payload["summary"][
                    "internal_performance_champion"
                ],
                "metric_battery_sha256": payload["metric_battery_sha256"],
                "outputs": [str(OUT_JSON), str(DASHBOARD_JSON), str(DOC_MD)],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
