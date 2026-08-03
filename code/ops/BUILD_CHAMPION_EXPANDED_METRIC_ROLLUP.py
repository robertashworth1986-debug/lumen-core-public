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

OUT_JSON = OUT_OPS / "champion_expanded_metric_rollup_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_expanded_metric_rollup.json"
DOC_MD = DOCS / "CHAMPION_EXPANDED_METRIC_ROLLUP.md"

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


def lane_status(evidence_mode: str, global_holm_positive_count: int) -> str:
    if evidence_mode == "direct_measured_replay":
        return (
            "DIRECT_MEASURED_PROMOTED"
            if global_holm_positive_count > 0
            else "DIRECT_MEASURED_NONPROMOTION"
        )
    if evidence_mode == "source_conditioned_synthetic_stress":
        return "CONDITIONED_SYNTHETIC_RESEARCH_LEAD"
    return "NO_COMPATIBLE_REPLAY"


def build_lane_scoreboard(ready_replay: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row_value in as_list(ready_replay.get("ready_source_replay_results")):
        row = as_dict(row_value)
        evidence_mode = str(row.get("evidence_mode") or "")
        global_holm_positive_count = as_int(
            row.get("registered_baseline_global_holm_positive_count")
        )
        registered_baseline_count = as_int(row.get("registered_baseline_count"))
        mean_win_count = as_int(row.get("registered_baseline_mean_win_count"))
        if evidence_mode == "direct_measured_replay":
            claim_gate = (
                "Measured nonpromotion result only; promotion requires every registered source-specific "
                "baseline to pass the global correction."
            )
        elif evidence_mode == "source_conditioned_synthetic_stress":
            claim_gate = (
                "Research lead only; conditioned synthetic stress is not measured performance evidence."
            )
        else:
            claim_gate = "No performance claim without a compatible source-native replay."
        rows.append(
            {
                "lane": row.get("lane"),
                "evidence_mode": evidence_mode,
                "status": lane_status(evidence_mode, global_holm_positive_count),
                "registered_candidate_family": row.get("registered_candidate_family"),
                "evaluated_candidate_family": row.get("candidate_family"),
                "registered_baseline_count": registered_baseline_count,
                "baseline_mean_win_count": mean_win_count,
                "global_holm_positive_count": global_holm_positive_count,
                "all_registered_baseline_mean_gate_passed": bool(
                    row.get("candidate_beats_all_registered_baselines_mean")
                ),
                "all_registered_baseline_global_holm_gate_passed": bool(
                    row.get("candidate_beats_all_registered_baselines_after_global_holm")
                ),
                "paired_unit_count": as_int(row.get("paired_unit_count")),
                "performance_rows_evaluated": as_int(row.get("performance_rows_evaluated")),
                "direct_replay_sources": [
                    str(item) for item in as_list(row.get("direct_replay_sources"))
                ],
                "conditioned_stress_sources": [
                    str(item) for item in as_list(row.get("conditioned_stress_sources"))
                ],
                "claim_gate": claim_gate,
            }
        )
    return rows


def build_payload(inputs: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    inputs = inputs or load_inputs()
    for name, input_payload in inputs.items():
        require_schema(name, input_payload)

    gauntlet_summary = as_dict(inputs["gauntlet"].get("summary"))
    sweep_summary = as_dict(inputs["locked_sweep"].get("summary"))
    ready_summary = as_dict(inputs["ready_replay"].get("summary"))
    kuramoto_summary = as_dict(inputs["kuramoto"].get("summary"))
    lane_scoreboard = build_lane_scoreboard(inputs["ready_replay"])

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

    direct_rows = [
        row for row in lane_scoreboard if row["evidence_mode"] == "direct_measured_replay"
    ]
    conditioned_rows = [
        row
        for row in lane_scoreboard
        if row["evidence_mode"] == "source_conditioned_synthetic_stress"
    ]
    no_input_rows = [
        row for row in lane_scoreboard if row["evidence_mode"] == "no_compatible_replay_input"
    ]

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_expanded_metric_rollup_v2",
        "purpose": (
            "Roll up the canonical v2 benchmark evidence while preserving task compatibility, "
            "multiplicity correction, and measured-versus-conditioned boundaries."
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
            "route_count": direct_routes + conditioned_routes,
            "direct_measured_route_count": direct_routes,
            "conditioned_synthetic_route_count": conditioned_routes,
            "no_compatible_replay_input_count": len(no_input_rows),
            "baseline_comparison_count": comparisons,
            "global_holm_positive_count": global_holm_positives,
            "conditioned_named_baseline_mean_win_count": conditioned_named_wins,
            "performance_rows_reviewed": performance_rows,
            "direct_measured_rows_reviewed": sum(
                row["performance_rows_evaluated"] for row in direct_rows
            ),
            "conditioned_synthetic_rows_reviewed": sum(
                row["performance_rows_evaluated"] for row in conditioned_rows
            ),
            "legacy_rows_excluded": legacy_rows_excluded,
            "numeric_fallback_count": numeric_fallbacks,
            "source_inventory_measured_provider_count": as_int(
                gauntlet_summary.get("broader_measured_provider_count")
            ),
            "source_inventory_enabled_provider_count": as_int(
                gauntlet_summary.get("broader_enabled_provider_count")
            ),
            "source_inventory_is_performance_evidence": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "plain_english_answer": (
                f"No internal performance champion exists. Kuramoto was not development-selected and "
                f"won {holdout_wins}/{holdout_count} paired measured days against "
                f"{kuramoto_summary.get('named_baseline')} with mean skill delta "
                f"{mean_skill_delta:.6f}. Across {direct_routes} direct measured and "
                f"{conditioned_routes} conditioned synthetic routes, the current "
                f"{comparisons} comparisons contain {global_holm_positives} global Holm positives."
            ),
        },
        "lane_scoreboard": lane_scoreboard,
        "conditioned_research_leads": [
            {
                "lane": row["lane"],
                "family": row["evaluated_candidate_family"],
                "status": "RESEARCH_ONLY",
                "baseline_mean_win_count": row["baseline_mean_win_count"],
                "global_holm_positive_count": row["global_holm_positive_count"],
                "performance_claim_allowed": False,
            }
            for row in conditioned_rows
        ],
        "source_inventory": {
            "measured_provider_count": as_int(
                gauntlet_summary.get("broader_measured_provider_count")
            ),
            "enabled_provider_count": as_int(
                gauntlet_summary.get("broader_enabled_provider_count")
            ),
            "classification": "RESEARCH_INVENTORY_ONLY",
            "performance_claim_allowed": False,
        },
        "claim_state": {
            "measured_nonpromotion_result_claim_allowed": True,
            "internal_performance_champion_claim_allowed": False,
            "conditioned_synthetic_performance_claim_allowed": False,
            "source_inventory_performance_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "realized_savings_claim_allowed": False,
        },
        "next_actions": [
            "Preserve the Lissajous development selection in the EIA wave protocol.",
            "Treat the Kuramoto result as a measured negative post-selection audit.",
            "Redesign candidates using development data only before opening a new holdout.",
            "Build source-native measured tasks for thermal and branching research leads.",
            "Commission an independent protocol and evidence review before performance claims.",
        ],
        "inputs": {
            "champion_metric_gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)),
            "locked_source_baseline_replay_sweep": str(
                LOCKED_SWEEP_JSON.relative_to(ROOT)
            ),
            "geometry_ready_source_replay": str(READY_REPLAY_JSON.relative_to(ROOT)),
            "kuramoto_holdout_expansion": str(KURAMOTO_JSON.relative_to(ROOT)),
        },
    }
    payload["rollup_sha256"] = canonical_sha256(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Champion Expanded Metric Rollup",
        "",
        "## Truth Line",
        "",
        summary.get("plain_english_answer", ""),
        "",
        "## Canonical Counts",
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
        f"- Direct measured routes: `{summary.get('direct_measured_route_count')}`",
        f"- Conditioned synthetic routes: `{summary.get('conditioned_synthetic_route_count')}`",
        (
            f"- Global Holm positives: `{summary.get('global_holm_positive_count')}/"
            f"{summary.get('baseline_comparison_count')}`"
        ),
        f"- Conditioned named-baseline mean wins: `{summary.get('conditioned_named_baseline_mean_win_count')}`",
        f"- Performance rows reviewed: `{summary.get('performance_rows_reviewed')}`",
        f"- Legacy rows excluded: `{summary.get('legacy_rows_excluded')}`",
        f"- Numeric fallbacks: `{summary.get('numeric_fallback_count')}`",
        f"- Field-validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary.get('real_dollar_savings_claim_allowed')).lower()}`",
        "",
        "## Lane Scoreboard",
        "",
        "| Lane | Mode | Status | Candidate | Baselines | Mean wins | Global Holm positives | Rows |",
        "|---|---|---|---|---:|---:|---:|---:|",
    ]
    for row_value in as_list(payload.get("lane_scoreboard")):
        row = as_dict(row_value)
        lines.append(
            f"| `{row.get('lane')}` | `{row.get('evidence_mode')}` | `{row.get('status')}` | "
            f"`{row.get('evaluated_candidate_family')}` | {row.get('registered_baseline_count')} | "
            f"{row.get('baseline_mean_win_count')} | {row.get('global_holm_positive_count')} | "
            f"{row.get('performance_rows_evaluated')} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- Direct measured routes currently record nonpromotion results.",
            "- Thermal and branching conditioned simulations are research leads only.",
            "- Source breadth is inventory, not performance evidence.",
            "- No field-validation, realized-savings, or autonomous-execution claim is allowed.",
            "",
            f"Rollup SHA-256: `{payload.get('rollup_sha256')}`",
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
                "rollup_sha256": payload["rollup_sha256"],
                "outputs": [str(OUT_JSON), str(DASHBOARD_JSON), str(DOC_MD)],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
