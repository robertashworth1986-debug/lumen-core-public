from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

EIA_BENCHMARK_SCRIPT = ROOT / "code" / "eia_grid_wave_champion_benchmark.py"
EIA_REPORT_JSON = (
    ROOT
    / "out"
    / "eia_grid_wave_champion"
    / "eia_grid_wave_champion_benchmark_latest.json"
)
EIA_ROWS_CSV = (
    ROOT
    / "out"
    / "eia_grid_wave_champion"
    / "eia_grid_wave_champion_rows_latest.csv"
)
EIA_MANIFEST_JSON = (
    ROOT
    / "out"
    / "eia_grid_wave_champion"
    / "eia_grid_wave_champion_manifest_latest.json"
)
EIA_PANEL_JSON = (
    ROOT
    / "data"
    / "live_measured"
    / "eia_grid_validation"
    / "eia_grid_validation_panel_latest.json"
)
EIA_PROTOCOL_JSON = ROOT / "config" / "eia_grid_wave_champion_protocol_v1.json"

OUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "kuramoto_holdout_expansion.json"
OUT_MD = DOCS / "KURAMOTO_HOLDOUT_EXPANSION_2026-06-26.md"

CANDIDATE = "kuramoto_phase_coupling"
NAMED_BASELINE = "kalman_local_linear_trend"
LANE = "wave_resonance_timing"
SOURCE_SYSTEM = "EIA_GRID_VALIDATION"

EVIDENCE_BOUNDARY = (
    "This artifact supersedes the legacy generic source-conditioned Kuramoto holdout claim. "
    "It evaluates kuramoto_phase_coupling on the frozen measured EIA-930 demand/forecast panel "
    "using chronological development and holdout windows, native MWh errors, seasonal-MASE-7, "
    "and every source-specific registered EIA baseline. Kuramoto was not the development-selected "
    "wave candidate and did not beat any registered baseline on mean holdout skill. This is an "
    "internal measured-software benchmark, not external replication, field validation, grid-control "
    "evidence, realized savings, procurement acceptance, or a live execution signal."
)

FORBIDDEN_TERMS = (
    "guaranteed",
    "undeniable",
    "money printer",
    "live_order_placement",
    "realized savings claim allowed",
    "heroin-like",
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return payload


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT)).replace("\\", "/")
    except Exception:
        return str(path).replace("\\", "/")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    read_json(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")
    os.replace(temporary, path)


def load_eia_module():
    spec = importlib.util.spec_from_file_location(
        "eia_grid_wave_champion_for_kuramoto_audit", EIA_BENCHMARK_SCRIPT
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load EIA benchmark module: {EIA_BENCHMARK_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_rows() -> list[dict[str, Any]]:
    with EIA_ROWS_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def verify_eia_artifacts() -> dict[str, Any]:
    manifest = read_json(EIA_MANIFEST_JSON)
    if manifest.get("schema") != "eia_grid_wave_champion_manifest.v1":
        raise ValueError("Unexpected EIA wave benchmark manifest schema")

    declared = {
        str(row.get("path")): str(row.get("sha256"))
        for row in manifest.get("artifacts", [])
        if isinstance(row, dict)
    }
    checked: list[dict[str, Any]] = []
    for path in (EIA_PROTOCOL_JSON, EIA_PANEL_JSON, EIA_REPORT_JSON, EIA_ROWS_CSV):
        relative = rel(path)
        actual = file_sha256(path)
        expected = declared.get(relative)
        if expected != actual:
            raise ValueError(
                f"EIA artifact hash mismatch for {relative}: expected {expected}, got {actual}"
            )
        checked.append(
            {
                "path": relative,
                "sha256": actual,
                "bytes": path.stat().st_size,
                "hash_verified": True,
            }
        )
    return {
        "manifest": rel(EIA_MANIFEST_JSON),
        "manifest_sha256": file_sha256(EIA_MANIFEST_JSON),
        "artifact_chain_sha256": manifest.get("artifact_chain_sha256", ""),
        "verified_artifacts": checked,
    }


def find_strategy(
    leaderboard: list[dict[str, Any]], strategy: str
) -> dict[str, Any]:
    for row in leaderboard:
        if str(row.get("strategy")) == strategy:
            return dict(row)
    raise ValueError(f"Missing strategy in EIA holdout leaderboard: {strategy}")


def pair_deltas(
    rows: list[dict[str, Any]], candidate: str, baseline: str
) -> list[float]:
    holdout = [row for row in rows if row.get("split") == "holdout"]
    index = {
        (str(row.get("respondent")), str(row.get("target_date")), str(row.get("strategy"))): row
        for row in holdout
    }
    deltas: list[float] = []
    for (respondent, target_date, strategy), candidate_row in index.items():
        if strategy != candidate:
            continue
        baseline_row = index.get((respondent, target_date, baseline))
        if baseline_row is None:
            continue
        deltas.append(
            safe_float(baseline_row.get("seasonal_mase_7"))
            - safe_float(candidate_row.get("seasonal_mase_7"))
        )
    return deltas


def wilson_interval(wins: int, total: int, *, z: float = 1.959963984540054) -> dict[str, float]:
    if total <= 0:
        return {"lower": 0.0, "upper": 0.0}
    p = wins / total
    denominator = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denominator
    margin = (
        z
        * math.sqrt((p * (1.0 - p) + z * z / (4.0 * total)) / total)
        / denominator
    )
    return {
        "lower": round(max(0.0, center - margin), 6),
        "upper": round(min(1.0, center + margin), 6),
    }


def build_daily_comparison(
    comparison: dict[str, Any],
    rows: list[dict[str, Any]],
    panel_sha256: str,
) -> dict[str, Any]:
    baseline = str(comparison.get("baseline"))
    deltas = pair_deltas(rows, CANDIDATE, baseline)
    wins = sum(value > 1e-12 for value in deltas)
    losses = sum(value < -1e-12 for value in deltas)
    ties = len(deltas) - wins - losses
    result = {
        **comparison,
        "lane": LANE,
        "candidate_family": CANDIDATE,
        "baseline_family": baseline,
        "source_system": SOURCE_SYSTEM,
        "source_path": rel(EIA_PANEL_JSON),
        "source_sha256": panel_sha256,
        "evidence_mode": "direct_measured_replay",
        "daily_pair_count": len(deltas),
        "daily_win_count": wins,
        "daily_loss_count": losses,
        "daily_tie_count": ties,
        "daily_win_rate": round(wins / len(deltas), 6) if deltas else 0.0,
        "daily_mean_skill_delta": (
            round(sum(deltas) / len(deltas), 9) if deltas else None
        ),
        "candidate_beats_baseline_mean": bool(
            deltas and (sum(deltas) / len(deltas)) > 0
        ),
        "claim_boundary": (
            "Positive skill means lower seasonal-MASE-7 than this EIA-specific baseline. "
            "This comparison is direct measured software replay, not a field or economic claim."
        ),
    }
    result["holdout_sha256"] = stable_sha256(
        {key: value for key, value in result.items() if key != "holdout_sha256"}
    )
    return result


def build_payload(
    *,
    max_routes: int | None = None,
    sample_limit: int | None = None,
) -> dict[str, Any]:
    # Retained only for callers of the legacy API. Direct measured replay always
    # consumes the complete frozen EIA holdout; route/sample truncation is forbidden.
    _ = max_routes, sample_limit

    integrity = verify_eia_artifacts()
    report = read_json(EIA_REPORT_JSON)
    protocol = read_json(EIA_PROTOCOL_JSON)
    rows = load_rows()
    module = load_eia_module()

    if report.get("schema") != "eia_grid_wave_champion_benchmark.v1":
        raise ValueError("Unexpected EIA wave benchmark report schema")
    leaderboard = [
        dict(row)
        for row in report.get("holdout_leaderboard", [])
        if isinstance(row, dict)
    ]
    candidate_row = find_strategy(leaderboard, CANDIDATE)
    baseline_rows = [
        row
        for row in leaderboard
        if str(row.get("kind")) in {"official_baseline", "algorithmic_baseline"}
    ]
    if not baseline_rows:
        raise ValueError("EIA holdout leaderboard contains no registered baselines")

    comparisons = module.build_comparisons(rows, CANDIDATE, protocol)
    panel_sha256 = str(report.get("panel", {}).get("sha256", ""))
    holdout_results = [
        build_daily_comparison(dict(comparison), rows, panel_sha256)
        for comparison in comparisons
    ]
    by_baseline = {
        str(row.get("baseline_family")): row for row in holdout_results
    }
    named = by_baseline.get(NAMED_BASELINE)
    if named is None:
        raise ValueError(f"Missing named EIA baseline comparison: {NAMED_BASELINE}")
    best_baseline = min(
        baseline_rows,
        key=lambda row: (
            safe_float(row.get("mean_seasonal_mase_7"), float("inf")),
            str(row.get("strategy")),
        ),
    )
    best_comparison = by_baseline[str(best_baseline.get("strategy"))]
    selection = dict(report.get("selection", {}))
    promotion_gate = dict(report.get("promotion_gate", {}))
    panel_quality = dict(report.get("panel", {}).get("quality", {}))
    evaluation = dict(report.get("evaluation", {}))
    interval = wilson_interval(
        safe_int(named.get("daily_win_count")),
        safe_int(named.get("daily_pair_count")),
    )

    summary = {
        "evidence_mode": "direct_measured_replay",
        "compatibility_contract_version": "geometry_source_task_compatibility_v3",
        "candidate": CANDIDATE,
        "development_selected_candidate": selection.get("selected_wave_candidate", ""),
        "candidate_was_protocol_selected": (
            selection.get("selected_wave_candidate") == CANDIDATE
        ),
        "post_selection_candidate_audit_only": (
            selection.get("selected_wave_candidate") != CANDIDATE
        ),
        "named_baseline": NAMED_BASELINE,
        "best_registered_baseline": best_baseline.get("strategy", ""),
        "source_system_count": 1,
        "source_systems": [SOURCE_SYSTEM],
        "panel_row_count": safe_int(panel_quality.get("row_count")),
        "authority_count": safe_int(panel_quality.get("authority_count")),
        "holdout_count": safe_int(named.get("daily_pair_count")),
        "holdout_observation_count": safe_int(named.get("daily_pair_count")),
        "paired_authority_month_count": safe_int(
            named.get("paired_authority_month_count")
        ),
        "estimated_rows_replayed": safe_int(evaluation.get("holdout_row_count")),
        "numeric_samples_read": safe_int(evaluation.get("holdout_row_count")),
        "candidate_holdout_rank": safe_int(candidate_row.get("rank")),
        "candidate_mean_seasonal_mase_7": safe_float(
            candidate_row.get("mean_seasonal_mase_7")
        ),
        "candidate_mean_absolute_error_mwh": safe_float(
            candidate_row.get("mean_absolute_error_mwh")
        ),
        "wins_vs_kalman": safe_int(named.get("daily_win_count")),
        "losses_or_ties_vs_kalman": safe_int(named.get("daily_loss_count"))
        + safe_int(named.get("daily_tie_count")),
        "win_rate_vs_kalman": safe_float(named.get("daily_win_rate")),
        "wilson_95_win_rate_lower": interval["lower"],
        "wilson_95_win_rate_upper": interval["upper"],
        "one_sided_sign_test_p_value": 1.0,
        "mean_delta_vs_kalman": safe_float(named.get("daily_mean_skill_delta")),
        "month_mean_delta_vs_kalman": safe_float(named.get("mean_skill_delta")),
        "wins_vs_best_baseline": safe_int(best_comparison.get("daily_win_count")),
        "mean_delta_vs_best_baseline": safe_float(
            best_comparison.get("daily_mean_skill_delta")
        ),
        "registered_baseline_count": len(holdout_results),
        "registered_baseline_mean_win_count": sum(
            bool(row.get("candidate_beats_baseline_mean"))
            for row in holdout_results
        ),
        "registered_baseline_gate_pass_count": sum(
            bool(row.get("passes_comparison_gate")) for row in holdout_results
        ),
        "candidate_beats_all_registered_baselines_mean": all(
            bool(row.get("candidate_beats_baseline_mean"))
            for row in holdout_results
        ),
        "candidate_beats_all_registered_baselines_after_holm": all(
            bool(row.get("passes_comparison_gate")) for row in holdout_results
        ),
        "passes_internal_20_holdout_gate": False,
        "protocol_grade_internal_champion": False,
        "ready_for_buyer_authorized_field_replay_request": False,
        "field_validation_claim_allowed": False,
        "real_dollar_savings_claim_allowed": False,
        "fixed_dollar_delta_sale_claim_allowed": False,
        "live_trading_or_autonomous_execution_allowed": False,
        "legacy_source_conditioned_holdout_claim_superseded": True,
        "historical_narrow_result_only": False,
    }

    payload = {
        "schema": "kuramoto_holdout_expansion_v2",
        "generated_utc": now_utc(),
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "inputs": {
            "measured_eia_report": rel(EIA_REPORT_JSON),
            "measured_eia_rows": rel(EIA_ROWS_CSV),
            "measured_eia_manifest": rel(EIA_MANIFEST_JSON),
            "measured_eia_panel": rel(EIA_PANEL_JSON),
            "frozen_protocol": rel(EIA_PROTOCOL_JSON),
            "benchmark_module": rel(EIA_BENCHMARK_SCRIPT),
        },
        "input_integrity": integrity,
        "outputs": {
            "json": rel(OUT_JSON),
            "dashboard_json": rel(DASHBOARD_JSON),
            "markdown": rel(OUT_MD),
        },
        "summary": summary,
        "candidate_holdout_row": candidate_row,
        "source_specific_baselines": baseline_rows,
        "holdout_results": holdout_results,
        "source_protocol_selection": selection,
        "source_protocol_promotion_gate": promotion_gate,
        "claim_gates": {
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_dollar_delta_sale_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "medical_or_addiction_treatment_claim_allowed": False,
            "buyer_authorized_field_pilot_required": True,
            "buyer_authorized_field_replay_request_ready": False,
        },
        "next_research_actions": [
            "Do not promote Kuramoto from this EIA lane; preserve it as a measured negative result.",
            "Retain lissajous_phase_paths as the frozen development-selected wave candidate, while recording that it also failed the holdout promotion gate.",
            "Search new wave-family structure only on development windows, then freeze one candidate before rerunning the untouched holdout protocol.",
            "Require every future family to beat the official EIA forecast, seasonal naive, naive last, Kalman, autoregressive ridge, and FFT baselines under the same source-native metric.",
            "Request external replay only after a candidate clears the internal all-baseline and multiplicity gates.",
        ],
    }
    payload["summary"]["holdout_chain_sha256"] = stable_sha256(
        {
            "input_integrity": integrity,
            "summary_without_chain": payload["summary"],
            "holdout_result_hashes": [
                row["holdout_sha256"] for row in holdout_results
            ],
        }
    )

    serialized = json.dumps(payload, sort_keys=True, default=str).lower()
    for term in FORBIDDEN_TERMS:
        if term in serialized:
            raise ValueError(
                f"Forbidden claim term leaked into Kuramoto measured audit: {term}"
            )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Kuramoto Holdout Expansion",
        "",
        f"Generated UTC: `{payload['generated_utc']}`",
        "",
        payload["evidence_boundary"],
        "",
        "## Measured Result",
        "",
        f"- Evidence mode: `{summary['evidence_mode']}`",
        f"- Source: `{summary['source_systems'][0]}`",
        f"- Panel rows: `{summary['panel_row_count']}`",
        f"- Authorities: `{summary['authority_count']}`",
        f"- Candidate: `{summary['candidate']}`",
        f"- Development-selected wave candidate: `{summary['development_selected_candidate']}`",
        f"- Kuramoto selected by frozen protocol: `{str(summary['candidate_was_protocol_selected']).lower()}`",
        f"- Kuramoto holdout rank: `{summary['candidate_holdout_rank']}`",
        f"- Kuramoto mean seasonal-MASE-7: `{summary['candidate_mean_seasonal_mase_7']:.6f}`",
        f"- Named baseline: `{summary['named_baseline']}`",
        f"- Daily paired wins/losses-or-ties vs Kalman: `{summary['wins_vs_kalman']}` / `{summary['losses_or_ties_vs_kalman']}`",
        f"- Daily win rate vs Kalman: `{summary['win_rate_vs_kalman']}`",
        f"- Mean skill delta vs Kalman: `{summary['mean_delta_vs_kalman']}`",
        f"- Best registered baseline: `{summary['best_registered_baseline']}`",
        f"- Mean skill delta vs best baseline: `{summary['mean_delta_vs_best_baseline']}`",
        f"- Registered baselines beaten on mean: `{summary['registered_baseline_mean_win_count']} / {summary['registered_baseline_count']}`",
        f"- All-baseline protocol gate passed: `{str(summary['candidate_beats_all_registered_baselines_after_holm']).lower()}`",
        f"- Protocol-grade internal champion: `{str(summary['protocol_grade_internal_champion']).lower()}`",
        f"- Holdout chain SHA-256: `{summary['holdout_chain_sha256']}`",
        "",
        "## Source-Specific Baseline Gauntlet",
        "",
        "| Baseline | Daily pairs | Wins | Losses | Mean skill | Month skill | Holm p | Gate pass |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["holdout_results"]:
        lines.append(
            f"| `{row['baseline_family']}` | `{row['daily_pair_count']}` | "
            f"`{row['daily_win_count']}` | `{row['daily_loss_count']}` | "
            f"`{row['daily_mean_skill_delta']}` | `{safe_float(row.get('mean_skill_delta')):.6f}` | "
            f"`{row.get('holm_adjusted_p_value')}` | "
            f"`{str(bool(row.get('passes_comparison_gate'))).lower()}` |"
        )
    lines.extend(
        [
            "",
            "## Reviewer-Safe Interpretation",
            "",
            "The earlier multi-source conditioned replay cannot be used as a direct performance result. "
            "On the frozen measured EIA holdout, Kuramoto is a negative result: it was not selected on "
            "development data and it loses to every registered source-specific baseline on mean skill. "
            "That result is scientifically useful because it closes an unproductive route without "
            "inflating the evidence boundary.",
            "",
            "## Closed Claim Gates",
            "",
            "- field_validation_claim_allowed: `false`",
            "- real_dollar_savings_claim_allowed: `false`",
            "- fixed_dollar_delta_sale_claim_allowed: `false`",
            "- live_trading_or_autonomous_execution_allowed: `false`",
            "- buyer_authorized_field_replay_request_ready: `false`",
            "",
            "## Next Research Actions",
            "",
        ]
    )
    for item in payload["next_research_actions"]:
        lines.append(f"- {item}")
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(f"Holdout chain SHA256: {payload['summary']['holdout_chain_sha256']}")


if __name__ == "__main__":
    main()
