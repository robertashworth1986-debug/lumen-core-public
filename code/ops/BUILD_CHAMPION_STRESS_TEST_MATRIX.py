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

OUT_JSON = OUT_OPS / "champion_stress_test_matrix_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_stress_test_matrix.json"
DOC_MD = DOCS / "CHAMPION_STRESS_TEST_MATRIX.md"

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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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


def route_status(row: dict[str, Any]) -> str:
    mode = str(row.get("evidence_mode") or "")
    if mode == "direct_measured_replay":
        return "DIRECT_MEASURED_NONPROMOTION"
    if mode == "source_conditioned_synthetic_stress":
        return "CONDITIONED_SYNTHETIC_RESEARCH_LEAD"
    return "NO_COMPATIBLE_REPLAY"


def build_route_matrix(ready_replay: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_value in as_list(ready_replay.get("ready_source_replay_results")):
        row = as_dict(row_value)
        comparisons = as_list(row.get("baseline_comparisons"))
        rows.append(
            {
                "lane": row.get("lane"),
                "evidence_mode": row.get("evidence_mode"),
                "status": route_status(row),
                "registered_candidate_family": row.get("registered_candidate_family"),
                "evaluated_candidate_family": row.get("candidate_family"),
                "registered_baseline_count": as_int(row.get("registered_baseline_count")),
                "baseline_mean_win_count": as_int(row.get("registered_baseline_mean_win_count")),
                "global_holm_positive_count": as_int(
                    row.get("registered_baseline_global_holm_positive_count")
                ),
                "performance_rows_evaluated": as_int(row.get("performance_rows_evaluated")),
                "candidate_beats_all_registered_baselines_mean": bool(
                    row.get("candidate_beats_all_registered_baselines_mean")
                ),
                "candidate_beats_all_registered_baselines_after_global_holm": bool(
                    row.get("candidate_beats_all_registered_baselines_after_global_holm")
                ),
                "baseline_comparisons": [
                    {
                        "baseline_family_id": item.get("baseline_family_id"),
                        "candidate_beats_baseline_mean": bool(
                            item.get("candidate_beats_baseline_mean")
                        ),
                        "statistically_positive_after_global_holm": bool(
                            item.get("statistically_positive_after_global_holm")
                        ),
                    }
                    for item in comparisons
                    if isinstance(item, dict)
                ],
                "claim_boundary": (
                    "Direct measured routes can report the measured nonpromotion result only."
                    if row.get("evidence_mode") == "direct_measured_replay"
                    else (
                        "Conditioned synthetic routes are research leads only and are not measured "
                        "performance evidence."
                        if row.get("evidence_mode") == "source_conditioned_synthetic_stress"
                        else "No performance conclusion is available without a compatible replay input."
                    )
                ),
            }
        )
    return rows


def metric_gate(
    name: str,
    passed: bool,
    actual: Any,
    threshold: str,
    blocker: bool,
    interpretation: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else ("BLOCKED" if blocker else "NONPROMOTION"),
        "passed": passed,
        "actual": actual,
        "threshold": threshold,
        "blocker": blocker,
        "interpretation": interpretation,
    }


def build_payload(inputs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    inputs = inputs or load_inputs()
    for name, input_payload in inputs.items():
        require_schema(name, input_payload)

    gauntlet_summary = as_dict(inputs["gauntlet"].get("summary"))
    sweep_summary = as_dict(inputs["locked_sweep"].get("summary"))
    ready_summary = as_dict(inputs["ready_replay"].get("summary"))
    kuramoto_summary = as_dict(inputs["kuramoto"].get("summary"))
    route_matrix = build_route_matrix(inputs["ready_replay"])

    holdout_count = as_int(kuramoto_summary.get("holdout_count"))
    wins_vs_kalman = as_int(kuramoto_summary.get("wins_vs_kalman"))
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

    gates = [
        metric_gate(
            "development_selection",
            candidate_selected,
            candidate_selected,
            "candidate must be frozen on development data",
            True,
            "Kuramoto was not development-selected; Lissajous was selected.",
        ),
        metric_gate(
            "paired_named_baseline_result",
            wins_vs_kalman > holdout_count / 2 and mean_skill_delta > 0,
            {
                "wins": wins_vs_kalman,
                "paired_days": holdout_count,
                "mean_skill_delta": mean_skill_delta,
            },
            "majority paired-day wins and positive mean skill",
            False,
            "Kuramoto loses the named-baseline gate on both win rate and mean skill.",
        ),
        metric_gate(
            "all_registered_source_baselines",
            baseline_passes == baseline_count and baseline_count > 0,
            f"{baseline_passes}/{baseline_count}",
            "all registered source-specific baselines pass",
            True,
            "No registered EIA baseline clears its complete promotion gate.",
        ),
        metric_gate(
            "global_holm_promotion",
            global_holm_positives == comparisons and comparisons > 0,
            f"{global_holm_positives}/{comparisons}",
            "all required comparisons positive after global Holm correction",
            True,
            "There are no globally Holm-positive comparisons.",
        ),
        metric_gate(
            "direct_measured_route_coverage",
            direct_routes == 2,
            direct_routes,
            "2 compatibility-qualified direct measured routes",
            False,
            "This is benchmark coverage, not proof of performance superiority.",
        ),
        metric_gate(
            "conditioned_synthetic_separation",
            conditioned_routes == 2 and conditioned_named_wins == 1,
            {
                "conditioned_routes": conditioned_routes,
                "named_baseline_mean_wins": conditioned_named_wins,
            },
            "conditioned results remain labeled research-only",
            False,
            "Thermal and branching can remain research leads only.",
        ),
        metric_gate(
            "compatibility_hygiene",
            legacy_rows_excluded == 358 and numeric_fallbacks == 0,
            {
                "legacy_rows_excluded": legacy_rows_excluded,
                "numeric_fallbacks": numeric_fallbacks,
            },
            "exclude incompatible legacy rows and use no numeric fallback profiles",
            False,
            "The v2 compatibility boundary is enforced.",
        ),
        metric_gate(
            "external_validation",
            bool(gauntlet_summary.get("field_validation_claim_allowed")),
            bool(gauntlet_summary.get("field_validation_claim_allowed")),
            "independent owner-approved validation complete",
            True,
            "No field-validation or realized-savings claim is allowed.",
        ),
    ]

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_stress_test_matrix_v2",
        "purpose": (
            "Stress-test the current canonical evidence without converting inventory, conditioned "
            "simulation, or negative measured results into champion claims."
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
            "paired_day_wins_vs_named_baseline": wins_vs_kalman,
            "paired_day_count": holdout_count,
            "paired_day_win_rate": round(wins_vs_kalman / holdout_count, 6)
            if holdout_count
            else 0.0,
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
            "source_inventory_measured_provider_count": as_int(
                gauntlet_summary.get("broader_measured_provider_count")
            ),
            "source_inventory_is_performance_evidence": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                f"No internal performance champion is present. Kuramoto was not development-selected "
                f"and won {wins_vs_kalman}/{holdout_count} paired measured days against "
                f"{kuramoto_summary.get('named_baseline')} with mean skill delta "
                f"{mean_skill_delta:.6f}. It cleared {baseline_passes}/{baseline_count} registered "
                f"baselines, and the complete sweep produced {global_holm_positives}/{comparisons} "
                "globally Holm-positive comparisons."
            ),
        },
        "metric_stress_tests": gates,
        "route_matrix": route_matrix,
        "conditioned_research_leads": [
            {
                "lane": row["lane"],
                "candidate_family": row["evaluated_candidate_family"],
                "status": "RESEARCH_ONLY",
                "performance_claim_allowed": False,
            }
            for row in route_matrix
            if row["evidence_mode"] == "source_conditioned_synthetic_stress"
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
    payload["stress_matrix_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Champion Stress Test Matrix",
        "",
        "## Truth Line",
        "",
        summary.get("plain_english_answer", ""),
        "",
        "## Canonical Result",
        "",
        f"- Internal performance champion: `{str(summary.get('internal_performance_champion')).lower()}`",
        f"- Audited candidate: `{summary.get('audited_candidate_family')}`",
        f"- Development-selected candidate: `{summary.get('development_selected_candidate')}`",
        f"- Kuramoto protocol-selected: `{str(summary.get('candidate_was_protocol_selected')).lower()}`",
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
        "",
        "## Evidence Modes",
        "",
        "| Lane | Mode | Status | Baselines | Mean wins | Global Holm positives | Rows |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row_value in as_list(payload.get("route_matrix")):
        row = as_dict(row_value)
        lines.append(
            f"| `{row.get('lane')}` | `{row.get('evidence_mode')}` | `{row.get('status')}` | "
            f"{row.get('registered_baseline_count')} | {row.get('baseline_mean_win_count')} | "
            f"{row.get('global_holm_positive_count')} | {row.get('performance_rows_evaluated')} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Direct measured routes support measured nonpromotion reporting only.",
            "- Thermal and branching conditioned simulations are research leads only.",
            "- Source breadth is inventory, not performance evidence.",
            "- Field validation, realized savings, and autonomous execution remain disallowed.",
            "",
            f"Stress matrix SHA-256: `{payload.get('stress_matrix_sha256')}`",
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
                "stress_matrix_sha256": payload["stress_matrix_sha256"],
                "outputs": [str(OUT_JSON), str(DASHBOARD_JSON), str(DOC_MD)],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
