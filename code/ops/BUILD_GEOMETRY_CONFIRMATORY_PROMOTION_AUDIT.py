from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_JSON = ROOT / "out" / "ops" / "geometry_confirmatory_promotion_audit_latest.json"

EVIDENCE_BOUNDARY = (
    "Internal confirmatory audit of generated software benchmarks. LumenGrade is an internal "
    "evidence-maturity label, not FAA, DoD, Air Force, laboratory, investor, or third-party "
    "certification. No result establishes airworthiness, operational safety, field validation, "
    "universal superiority, realized savings, or trading alpha."
)

LUMENGRADE_SCALE = {
    "LG0": "registered concept or specification only",
    "LG1": "implemented deterministic software test",
    "LG2": "frozen generated holdout with hashes and explicit baselines",
    "LG3": "preregistered public, representative, or partner-data validation",
    "LG4": "independent reproduction by an external runner",
    "LG5": "field validation or formal authority review; still not certification unless the authority says so",
}


@dataclass(frozen=True)
class MetricRule:
    field: str
    direction: str
    noninferiority_margin: float = 0.0


@dataclass(frozen=True)
class LaneSpec:
    lane: str
    run_dir: Path
    metric_rules: tuple[MetricRule, ...]
    condition_score_noninferiority_margin: float = 0.01


DEFAULT_LANES = (
    LaneSpec(
        "branching_transport",
        ROOT / "out" / "geometry_branching_transport" / "full_field_confirmatory_20260715",
        (
            MetricRule("delivered_flow", "higher"),
            MetricRule("failure_tolerance", "higher"),
        ),
    ),
    LaneSpec(
        "optimal_curve_transport",
        ROOT / "out" / "geometry_optimal_curve_transport" / "full_field_expanded_20260715",
        (
            MetricRule("travel_time", "lower"),
            MetricRule("path_energy_proxy", "lower"),
            MetricRule("constraint_violation_rate", "lower"),
            MetricRule("smoothness", "lower"),
        ),
    ),
    LaneSpec(
        "thermal_ventilation",
        ROOT / "out" / "geometry_thermal_ventilation" / "full_field_expanded_20260715",
        (
            MetricRule("temperature_uniformity", "higher"),
            MetricRule("hotspot_recovery", "higher"),
            MetricRule("pressure_drop", "lower"),
            MetricRule("energy_proxy", "lower"),
            MetricRule("recovery_time", "lower"),
        ),
    ),
    LaneSpec(
        "wave_resonance_timing",
        ROOT / "out" / "geometry_wave_resonance_timing" / "full_field_expanded_20260715",
        (
            MetricRule("phase_error", "lower"),
            MetricRule("noise_rejection", "higher", 0.01),
            MetricRule("forecast_error", "lower"),
            MetricRule("stability_margin", "higher"),
        ),
    ),
)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected object in {path}")
    return data


def load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def verify_manifest(run_dir: Path) -> dict[str, Any]:
    manifest_path = run_dir / "manifest.sha256.json"
    manifest = load_json(manifest_path)
    checked: list[dict[str, Any]] = []
    all_valid = True
    for name, metadata in sorted((manifest.get("files") or {}).items()):
        path = run_dir / name
        expected = str((metadata or {}).get("sha256") or "")
        actual = sha256_file(path) if path.exists() else None
        valid = bool(actual and actual == expected)
        all_valid = all_valid and valid
        checked.append(
            {
                "path": str(path),
                "exists": path.exists(),
                "expected_sha256": expected,
                "actual_sha256": actual,
                "valid": valid,
            }
        )
    return {
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "all_hashes_valid": all_valid,
        "files": checked,
    }


def paired_mean_ci95(deltas: list[float]) -> dict[str, Any]:
    if not deltas:
        raise ValueError("paired interval requires at least one delta")
    observed = mean(deltas)
    standard_error = stdev(deltas) / math.sqrt(len(deltas)) if len(deltas) > 1 else 0.0
    half_width = 1.959963984540054 * standard_error
    return {
        "method": "paired_normal_approximation",
        "paired_scenario_count": len(deltas),
        "observed_mean_delta": round(observed, 6),
        "standard_error": round(standard_error, 8),
        "ci95": [round(observed - half_width, 6), round(observed + half_width, 6)],
    }


def normalized_metric_delta(candidate: float, baseline: float, direction: str) -> float:
    if direction == "higher":
        return candidate - baseline
    if direction == "lower":
        return baseline - candidate
    raise ValueError(f"unsupported metric direction: {direction}")


def build_family_comparison(
    rows: list[dict[str, Any]],
    *,
    family_id: str,
    baseline_id: str,
    development_selected_family: str,
    metric_rules: tuple[MetricRule, ...],
    condition_score_noninferiority_margin: float,
) -> dict[str, Any]:
    paired: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        strategy = str(row.get("strategy") or "")
        if strategy not in {family_id, baseline_id}:
            continue
        key = (str(row["condition"]), int(row["seed"]))
        paired[key][strategy] = row
    complete = [
        (key, values[family_id], values[baseline_id])
        for key, values in sorted(paired.items())
        if family_id in values and baseline_id in values
    ]
    if not complete:
        raise ValueError(f"no complete pairs for {family_id} vs {baseline_id}")

    score_deltas = [float(candidate["score"]) - float(baseline["score"]) for _, candidate, baseline in complete]
    interval = paired_mean_ci95(score_deltas)
    condition_groups: dict[str, list[float]] = defaultdict(list)
    for (condition, _), candidate, baseline in complete:
        condition_groups[condition].append(float(candidate["score"]) - float(baseline["score"]))
    condition_guardrails = [
        {
            "condition": condition,
            "paired_scenario_count": len(deltas),
            "score_delta": round(mean(deltas), 6),
            "noninferiority_margin": condition_score_noninferiority_margin,
            "passes_noninferiority": mean(deltas) >= -condition_score_noninferiority_margin,
        }
        for condition, deltas in sorted(condition_groups.items())
    ]

    metric_guardrails: list[dict[str, Any]] = []
    for rule in metric_rules:
        candidate_values = [float(candidate[rule.field]) for _, candidate, _ in complete]
        baseline_values = [float(baseline[rule.field]) for _, _, baseline in complete]
        candidate_mean = mean(candidate_values)
        baseline_mean = mean(baseline_values)
        normalized_delta = normalized_metric_delta(candidate_mean, baseline_mean, rule.direction)
        metric_guardrails.append(
            {
                "metric": rule.field,
                "direction": rule.direction,
                "candidate_mean": round(candidate_mean, 6),
                "baseline_mean": round(baseline_mean, 6),
                "raw_candidate_minus_baseline": round(candidate_mean - baseline_mean, 6),
                "normalized_improvement": round(normalized_delta, 6),
                "noninferiority_margin": rule.noninferiority_margin,
                "passes_noninferiority": normalized_delta >= -rule.noninferiority_margin,
            }
        )

    development_preselected = family_id == development_selected_family
    checks = {
        "development_preselected": development_preselected,
        "overall_score_delta_positive": float(interval["observed_mean_delta"]) > 0.0,
        "paired_ci95_lower_bound_positive": float(interval["ci95"][0]) > 0.0,
        "all_condition_score_noninferiority": all(
            row["passes_noninferiority"] for row in condition_guardrails
        ),
        "all_metric_noninferiority": all(
            row["passes_noninferiority"] for row in metric_guardrails
        ),
    }
    confirmatory_pass = all(checks.values())
    if not development_preselected:
        decision = "DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED"
    elif confirmatory_pass:
        decision = "INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED"
    else:
        decision = "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"
    return {
        "family_id": family_id,
        "baseline_id": baseline_id,
        "development_preselected": development_preselected,
        "paired_score_interval": interval,
        "condition_guardrails": condition_guardrails,
        "metric_guardrails": metric_guardrails,
        "checks": checks,
        "failed_checks": [name for name, passed in checks.items() if not passed],
        "decision": decision,
        "confirmatory_pass": confirmatory_pass,
    }


def first_strategy(leaderboard: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    for row in leaderboard:
        if row.get("kind") == kind:
            return row
    raise ValueError(f"leaderboard has no {kind}")


def build_lane_audit(spec: LaneSpec) -> dict[str, Any]:
    summary_path = spec.run_dir / "summary.json"
    scenario_path = spec.run_dir / "scenario_summary.csv"
    summary = load_json(summary_path)
    rows = load_csv(scenario_path)
    development_leaderboard = list((summary.get("development") or {}).get("leaderboard") or [])
    selected_geometry = first_strategy(development_leaderboard, "geometry_family")
    selected_baseline = first_strategy(development_leaderboard, "baseline")
    geometry_families = [
        str(row["family_id"])
        for row in summary.get("strategies", [])
        if row.get("kind") == "geometry_family"
    ]
    comparisons = [
        build_family_comparison(
            rows,
            family_id=family_id,
            baseline_id=str(selected_baseline["strategy"]),
            development_selected_family=str(selected_geometry["strategy"]),
            metric_rules=spec.metric_rules,
            condition_score_noninferiority_margin=spec.condition_score_noninferiority_margin,
        )
        for family_id in geometry_families
    ]
    selected_comparison = next(row for row in comparisons if row["development_preselected"])
    manifest = verify_manifest(spec.run_dir)
    validation_scenario_count = int((summary.get("validation") or {}).get("scenario_count") or 0)
    lumengrade = "LG2" if manifest["all_hashes_valid"] and validation_scenario_count > 0 else "LG1"
    return {
        "lane": spec.lane,
        "run_dir": str(spec.run_dir),
        "summary_path": str(summary_path),
        "summary_sha256": sha256_file(summary_path),
        "scenario_path": str(scenario_path),
        "scenario_sha256": sha256_file(scenario_path),
        "validation_scenario_count": validation_scenario_count,
        "strategy_count": len(summary.get("strategies", [])),
        "geometry_family_count": len(geometry_families),
        "development_selected_geometry": selected_geometry["strategy"],
        "development_selected_baseline": selected_baseline["strategy"],
        "confirmatory_decision": selected_comparison["decision"],
        "confirmatory_pass": selected_comparison["confirmatory_pass"],
        "lumengrade": lumengrade,
        "lumengrade_external_certification": False,
        "family_comparisons": comparisons,
        "manifest_verification": manifest,
    }


def build_audit(lanes: tuple[LaneSpec, ...] = DEFAULT_LANES) -> dict[str, Any]:
    lane_audits = [build_lane_audit(spec) for spec in lanes]
    comparisons = [
        {"lane": lane["lane"], **comparison}
        for lane in lane_audits
        for comparison in lane["family_comparisons"]
    ]
    payload: dict[str, Any] = {
        "schema": "geometry_confirmatory_promotion_audit_v1",
        "generated_utc": now_utc().isoformat(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "lumengrade_scale": LUMENGRADE_SCALE,
        "summary": {
            "lane_count": len(lane_audits),
            "executed_geometry_family_count": len(comparisons),
            "development_preselected_family_count": sum(
                bool(row["development_preselected"]) for row in comparisons
            ),
            "internal_confirmatory_pass_count": sum(
                row["decision"] == "INTERNAL_CONFIRMATORY_PASS_NOT_FIELD_VALIDATED"
                for row in comparisons
            ),
            "confirmatory_nonpromotion_count": sum(
                row["decision"] == "NOT_PROMOTED_CONFIRMATORY_GATE_FAILED"
                for row in comparisons
            ),
            "descriptive_only_family_count": sum(
                row["decision"] == "DESCRIPTIVE_ONLY_NOT_DEVELOPMENT_PRESELECTED"
                for row in comparisons
            ),
            "all_manifests_valid": all(
                lane["manifest_verification"]["all_hashes_valid"] for lane in lane_audits
            ),
            "field_validation_claim_allowed": False,
            "certification_claim_allowed": False,
            "cross_lane_ranking_performed": False,
        },
        "lanes": lane_audits,
        "family_comparisons": comparisons,
        "claim_gate": {
            "internal_lumengrade_is_external_certification": False,
            "generated_holdout_is_field_validation": False,
            "cross_lane_champion_allowed": False,
            "only_development_preselected_family_is_confirmatory_eligible": True,
            "null_and_nonpromoted_results_retained": True,
        },
    }
    payload["audit_sha256"] = sha256_payload(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Geometry Confirmatory Promotion Audit",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        f"Audit SHA-256: `{payload['audit_sha256']}`",
        "",
        "## Boundary",
        "",
        payload["evidence_boundary"],
        "",
        "## Summary",
        "",
        f"- Executed geometry families audited: `{summary['executed_geometry_family_count']}`.",
        f"- Development-preselected confirmatory candidates: `{summary['development_preselected_family_count']}`.",
        f"- Internal confirmatory passes: `{summary['internal_confirmatory_pass_count']}`.",
        f"- Confirmatory non-promotions: `{summary['confirmatory_nonpromotion_count']}`.",
        f"- Descriptive-only family results: `{summary['descriptive_only_family_count']}`.",
        f"- All source manifests valid: `{str(summary['all_manifests_valid']).lower()}`.",
        "- LumenGrade is an internal evidence-maturity label and never an external certification.",
        "",
        "## Lane Decisions",
        "",
        "| Lane | Validation Scenarios | Selected Geometry | Selected Baseline | Decision | LumenGrade |",
        "| --- | ---: | --- | --- | --- | --- |",
    ]
    for lane in payload["lanes"]:
        lines.append(
            f"| `{lane['lane']}` | {lane['validation_scenario_count']} | "
            f"`{lane['development_selected_geometry']}` | `{lane['development_selected_baseline']}` | "
            f"`{lane['confirmatory_decision']}` | `{lane['lumengrade']}` |"
        )
    lines.extend(
        [
            "",
            "## Family Comparisons",
            "",
            "| Lane | Family | Baseline | Score Delta | CI95 | Minimum Condition Delta | Decision |",
            "| --- | --- | --- | ---: | --- | ---: | --- |",
        ]
    )
    for row in payload["family_comparisons"]:
        condition_min = min(
            float(item["score_delta"]) for item in row["condition_guardrails"]
        )
        interval = row["paired_score_interval"]
        lines.append(
            f"| `{row['lane']}` | `{row['family_id']}` | `{row['baseline_id']}` | "
            f"{interval['observed_mean_delta']} | `{interval['ci95']}` | {condition_min:.6f} | "
            f"`{row['decision']}` |"
        )
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], json_path: Path = DEFAULT_JSON) -> tuple[Path, Path]:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    date_tag = str(payload["generated_utc"])[:10]
    markdown_path = ROOT / "docs" / f"GEOMETRY_CONFIRMATORY_PROMOTION_AUDIT_{date_tag}.md"
    markdown_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, markdown_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_audit()
    json_path, markdown_path = write_outputs(payload, args.json_out)
    print(
        json.dumps(
            {
                "json": str(json_path),
                "markdown": str(markdown_path),
                "summary": payload["summary"],
                "audit_sha256": payload["audit_sha256"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
