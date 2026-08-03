from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

HOLDOUT_JSON = OUT_OPS / "kuramoto_holdout_expansion_latest.json"
STRESS_JSON = OUT_OPS / "champion_stress_test_matrix_latest.json"

OUT_JSON = OUT_OPS / "champion_phase_proxy_diagnostics_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_phase_proxy_diagnostics.json"
OUT_MD = DOCS / "CHAMPION_PHASE_PROXY_DIAGNOSTICS_2026-07-01.md"

MAX_NUMERIC_PER_HOLDOUT = 4096

CANONICAL_SOURCE_INVENTORY = {
    "measured_source_count": 24,
    "measured_row_count": 17081,
    "inventory_is_performance_evidence": False,
}

BOUNDARY = (
    "These are file-level numeric-sequence diagnostic proxies for a negative measured Kuramoto reference. "
    "They are not phase measurements, model-residual diagnostics, candidate-selection evidence, performance "
    "promotion evidence, hardware PLL measurements, field validation, realized savings, or proof of live "
    "trading edge. The 24-source / 17,081-row register is source inventory only."
)


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
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip("\r\n") + "\n", encoding="utf-8")


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isfinite(number):
        return number
    return None


def stable_sha256(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def read_numeric_values(path_text: str, limit: int = MAX_NUMERIC_PER_HOLDOUT) -> list[float]:
    path = Path(path_text)
    if not path.exists() or not path.is_file():
        return []
    values: list[float] = []
    suffix = path.suffix.lower()
    try:
        if suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", errors="ignore", newline="") as handle:
                reader = csv.reader(handle)
                for row in reader:
                    for cell in row:
                        number = safe_float(str(cell).replace(",", "").strip())
                        if number is not None:
                            values.append(number)
                            if len(values) >= limit:
                                return values
        else:
            text = path.read_text(encoding="utf-8", errors="ignore")
            token = []
            for char in text:
                if char.isdigit() or char in ".-+eE":
                    token.append(char)
                elif token:
                    number = safe_float("".join(token))
                    if number is not None:
                        values.append(number)
                        if len(values) >= limit:
                            return values
                    token = []
            if token:
                number = safe_float("".join(token))
                if number is not None:
                    values.append(number)
    except OSError:
        return []
    return values


def mean(values: list[float]) -> float:
    return round(statistics.mean(values), 6) if values else 0.0


def stdev(values: list[float]) -> float:
    return round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0


def lag1_autocorrelation(values: list[float]) -> float:
    if len(values) < 3:
        return 0.0
    left = values[:-1]
    right = values[1:]
    mean_left = statistics.mean(left)
    mean_right = statistics.mean(right)
    num = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right))
    den_left = math.sqrt(sum((a - mean_left) ** 2 for a in left))
    den_right = math.sqrt(sum((b - mean_right) ** 2 for b in right))
    den = den_left * den_right
    return round(num / den, 6) if den else 0.0


def circular_mean_resultant(phases: list[float]) -> float:
    if not phases:
        return 0.0
    c = sum(math.cos(x) for x in phases) / len(phases)
    s = sum(math.sin(x) for x in phases) / len(phases)
    return round(math.sqrt(c * c + s * s), 6)


def phase_proxy(values: list[float]) -> dict[str, Any]:
    if len(values) < 8:
        return {
            "numeric_count": len(values),
            "enough_numeric_data": False,
            "non_degenerate_numeric_data": False,
            "degenerate_reason": "too_few_numeric_values",
            "phase_slip_proxy_count": 0,
            "phase_coherence_proxy": 0.0,
            "circular_phase_error_proxy": 0.0,
            "amplitude_cv_proxy": 0.0,
            "residual_lag1_autocorrelation_proxy": 0.0,
            "spectral_concentration_proxy": 0.0,
        }

    finite_values = [x for x in values if math.isfinite(x)]
    unique_values = len({round(x, 12) for x in finite_values})
    centered_mean = statistics.mean(finite_values)
    centered_raw = [x - centered_mean for x in finite_values]
    raw_stddev = statistics.pstdev(finite_values) if len(finite_values) > 1 else 0.0
    non_degenerate = unique_values >= 3 and raw_stddev > 1e-12
    scale = max(max(abs(x) for x in centered_raw), 1.0)
    centered = [x / scale for x in centered_raw]
    normalized = [x / scale for x in finite_values]
    diffs = [b - a for a, b in zip(normalized[:-1], normalized[1:])]
    phases = [math.atan2(delta, centered[i]) for i, delta in enumerate(diffs)]
    phase_jumps = [abs(math.atan2(math.sin(b - a), math.cos(b - a))) for a, b in zip(phases[:-1], phases[1:])]
    phase_slips = sum(1 for jump in phase_jumps if jump > math.pi * 0.75)
    phase_coherence = circular_mean_resultant(phases)
    circular_error = round(1.0 - phase_coherence, 6)

    abs_values = [abs(x) for x in normalized]
    amp_mean = statistics.mean(abs_values)
    amplitude_cv = round(statistics.pstdev(abs_values) / amp_mean, 6) if amp_mean else 0.0
    residual_auto = lag1_autocorrelation(diffs)

    # A small DFT sample is enough for a deterministic concentration proxy without adding dependencies.
    n = min(len(centered), 512)
    sample = centered[:n]
    energies: list[float] = []
    for k in range(1, min(32, n // 2) + 1):
        real = 0.0
        imag = 0.0
        for i, value in enumerate(sample):
            angle = -2.0 * math.pi * k * i / n
            real += value * math.cos(angle)
            imag += value * math.sin(angle)
        energies.append(real * real + imag * imag)
    total_energy = sum(energies)
    spectral_concentration = round(max(energies) / total_energy, 6) if total_energy else 0.0

    return {
        "numeric_count": len(values),
        "enough_numeric_data": True,
        "non_degenerate_numeric_data": non_degenerate,
        "degenerate_reason": "" if non_degenerate else "flat_or_low_variance_series",
        "unique_numeric_value_count": unique_values,
        "phase_slip_proxy_count": phase_slips,
        "phase_slip_proxy_rate": round(phase_slips / max(1, len(phase_jumps)), 6),
        "phase_coherence_proxy": phase_coherence,
        "circular_phase_error_proxy": circular_error,
        "amplitude_cv_proxy": amplitude_cv,
        "residual_lag1_autocorrelation_proxy": residual_auto,
        "spectral_concentration_proxy": spectral_concentration,
        "normalization_scale": round(scale, 6),
        "mean": mean(finite_values),
        "raw_stddev": round(raw_stddev, 12),
        "stddev": stdev(normalized),
    }


def build_payload() -> dict[str, Any]:
    holdout = read_json(HOLDOUT_JSON)
    stress = read_json(STRESS_JSON)
    holdout_summary = as_dict(holdout.get("summary"))
    stress_summary = as_dict(stress.get("summary"))
    rows = [as_dict(row) for row in as_list(holdout.get("holdout_results"))]
    diagnostics: list[dict[str, Any]] = []

    for row in rows:
        path = str(row.get("source_path") or "")
        values = read_numeric_values(path)
        metrics = phase_proxy(values)
        diagnostics.append(
            {
                "source_system": row.get("source_system"),
                "source_path": path,
                "source_sha256_prefix": str(row.get("source_sha256") or "")[:16],
                "holdout_sha256": row.get("holdout_sha256"),
                "candidate_family": row.get("candidate_family"),
                "named_baseline": row.get("baseline") or row.get("named_baseline"),
                "delta_vs_named_baseline": row.get("mean_skill_delta") or row.get("delta_vs_kalman"),
                "candidate_rank": row.get("candidate_rank") or holdout_summary.get("candidate_holdout_rank"),
                "diagnostic_role": "file_level_numeric_sequence_proxy_only",
                "metrics": metrics,
            }
        )

    usable = [row for row in diagnostics if as_dict(row.get("metrics")).get("enough_numeric_data")]
    non_degenerate_usable = [
        row for row in usable if as_dict(row.get("metrics")).get("non_degenerate_numeric_data")
    ]
    coherence_values = [float(as_dict(row.get("metrics")).get("phase_coherence_proxy") or 0.0) for row in usable]
    slip_rates = [float(as_dict(row.get("metrics")).get("phase_slip_proxy_rate") or 0.0) for row in usable]
    circular_errors = [float(as_dict(row.get("metrics")).get("circular_phase_error_proxy") or 0.0) for row in usable]
    spectral = [float(as_dict(row.get("metrics")).get("spectral_concentration_proxy") or 0.0) for row in usable]
    residual_auto = [
        abs(float(as_dict(row.get("metrics")).get("residual_lag1_autocorrelation_proxy") or 0.0)) for row in usable
    ]

    source_groups: dict[str, list[dict[str, Any]]] = {}
    for row in diagnostics:
        source_groups.setdefault(str(row.get("source_system") or "unknown"), []).append(row)

    source_summary = []
    for source, group in sorted(source_groups.items()):
        group_metrics = [as_dict(row.get("metrics")) for row in group if as_dict(row.get("metrics")).get("enough_numeric_data")]
        non_degenerate_metrics = [
            metric for metric in group_metrics if metric.get("non_degenerate_numeric_data")
        ]
        source_summary.append(
            {
                "source_system": source,
                "holdout_count": len(group),
                "usable_numeric_holdouts": len(group_metrics),
                "non_degenerate_numeric_holdouts": len(non_degenerate_metrics),
                "degenerate_numeric_holdouts": len(group_metrics) - len(non_degenerate_metrics),
                "mean_phase_coherence_proxy": mean(
                    [float(metric.get("phase_coherence_proxy") or 0.0) for metric in non_degenerate_metrics]
                ),
                "mean_phase_slip_proxy_rate": mean(
                    [float(metric.get("phase_slip_proxy_rate") or 0.0) for metric in non_degenerate_metrics]
                ),
                "mean_spectral_concentration_proxy": mean(
                    [float(metric.get("spectral_concentration_proxy") or 0.0) for metric in non_degenerate_metrics]
                ),
                "mean_abs_residual_lag1_autocorrelation_proxy": mean(
                    [
                        abs(float(metric.get("residual_lag1_autocorrelation_proxy") or 0.0))
                        for metric in non_degenerate_metrics
                    ]
                ),
            }
        )

    canonical_contract = {
        "internal_performance_champion": False,
        "direct_measured_route_count": int(stress_summary.get("direct_measured_route_count") or 0),
        "conditioned_synthetic_route_count": int(stress_summary.get("conditioned_synthetic_route_count") or 0),
        "baseline_comparison_count": int(stress_summary.get("baseline_comparison_count") or 0),
        "performance_rows_reviewed": int(stress_summary.get("performance_rows_reviewed") or 0),
        "direct_all_baseline_globally_holm_positive_promotion_count": int(
            stress_summary.get("global_holm_positive_count") or 0
        ),
        "source_inventory": dict(CANONICAL_SOURCE_INVENTORY),
    }
    canonical_contract_matches = (
        stress_summary.get("internal_performance_champion") is False
        and canonical_contract["direct_measured_route_count"] == 2
        and canonical_contract["conditioned_synthetic_route_count"] == 2
        and canonical_contract["baseline_comparison_count"] == 22
        and canonical_contract["performance_rows_reviewed"] == 32608
        and canonical_contract["direct_all_baseline_globally_holm_positive_promotion_count"] == 0
        and holdout_summary.get("candidate") == "kuramoto_phase_coupling"
        and holdout_summary.get("candidate_was_protocol_selected") is False
        and int(holdout_summary.get("wins_vs_kalman") or 0) == 482
        and int(holdout_summary.get("holdout_count") or 0) == 1525
        and round(float(holdout_summary.get("mean_delta_vs_kalman") or 0.0), 6) == -0.508191
    )
    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_phase_proxy_diagnostics_v2",
        "purpose": (
            "Report bounded file-level numeric-sequence proxies for diagnostic review without inferring a "
            "performance champion, phase lock, promotion, field result, or economic result."
        ),
        "boundary": BOUNDARY,
        "canonical_evidence_contract": canonical_contract,
        "summary": {
            "internal_performance_champion": False,
            "champion_family": None,
            "audited_reference_candidate": holdout_summary.get("candidate") or "kuramoto_phase_coupling",
            "reference_candidate_status": "negative_measured_reference_not_selected_not_promoted",
            "development_selected_candidate": (
                holdout_summary.get("development_selected_candidate")
                or stress_summary.get("development_selected_candidate")
                or "lissajous_phase_paths"
            ),
            "candidate_was_development_selected": False,
            "named_baseline": holdout_summary.get("named_baseline") or "kalman_local_linear_trend",
            "kuramoto_wins_vs_named_baseline": int(holdout_summary.get("wins_vs_kalman") or 0),
            "kuramoto_paired_holdout_count": int(holdout_summary.get("holdout_count") or 0),
            "kuramoto_mean_delta_vs_named_baseline": round(
                float(holdout_summary.get("mean_delta_vs_kalman") or 0.0), 6
            ),
            "direct_measured_route_count": canonical_contract["direct_measured_route_count"],
            "conditioned_synthetic_route_count": canonical_contract["conditioned_synthetic_route_count"],
            "baseline_comparison_count": canonical_contract["baseline_comparison_count"],
            "performance_rows_reviewed": canonical_contract["performance_rows_reviewed"],
            "direct_all_baseline_globally_holm_positive_promotion_count": canonical_contract[
                "direct_all_baseline_globally_holm_positive_promotion_count"
            ],
            "source_inventory_measured_source_count": CANONICAL_SOURCE_INVENTORY["measured_source_count"],
            "source_inventory_measured_row_count": CANONICAL_SOURCE_INVENTORY["measured_row_count"],
            "source_inventory_is_performance_evidence": False,
            "canonical_evidence_contract_matches_inputs": canonical_contract_matches,
            "holdout_count": len(rows),
            "usable_numeric_holdout_count": len(usable),
            "non_degenerate_numeric_holdout_count": len(non_degenerate_usable),
            "degenerate_numeric_holdout_count": len(usable) - len(non_degenerate_usable),
            "source_system_count": len(source_groups),
            "mean_phase_coherence_proxy": mean(coherence_values),
            "mean_circular_phase_error_proxy": mean(circular_errors),
            "mean_phase_slip_proxy_rate": mean(slip_rates),
            "mean_spectral_concentration_proxy": mean(spectral),
            "mean_abs_residual_lag1_autocorrelation_proxy": mean(residual_auto),
            "live_domain_hash_verified": bool(stress_summary.get("live_domain_hash_verified")),
            "descriptive_file_proxy_reporting_allowed": canonical_contract_matches and bool(
                non_degenerate_usable
            ),
            "phase_measurement_claim_allowed": False,
            "model_residual_diagnostic_claim_allowed": False,
            "performance_promotion_claim_allowed": False,
            "degenerate_series_excluded_from_source_means": True,
            "hardware_phase_lock_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "plain_english_answer": (
                "No performance champion is present. Kuramoto was not development-selected and is retained only "
                "as a negative measured reference: 482/1525 paired wins against kalman_local_linear_trend with "
                f"mean delta -0.508191. The broader replay contains "
                f"{canonical_contract['direct_measured_route_count']} direct measured routes, "
                f"{canonical_contract['conditioned_synthetic_route_count']} conditioned-synthetic routes, "
                f"{canonical_contract['baseline_comparison_count']} comparisons, "
                f"{canonical_contract['performance_rows_reviewed']:,} performance rows, and "
                f"{canonical_contract['direct_all_baseline_globally_holm_positive_promotion_count']} direct "
                "all-baseline globally Holm-positive promotions. These file-level proxies are descriptive data "
                f"diagnostics only; the {CANONICAL_SOURCE_INVENTORY['measured_source_count']}-source / "
                f"{CANONICAL_SOURCE_INVENTORY['measured_row_count']:,}-row register is inventory, not "
                "performance evidence."
            ),
        },
        "claim_controls": {
            "allowed_now": [
                "file-level numeric-sequence proxy diagnostics",
                "negative measured Kuramoto reference reporting",
                "nonpromotion evidence-contract reporting",
            ],
            "not_allowed_yet": [
                "performance champion",
                "phase measurement",
                "model-residual diagnostic",
                "candidate promotion",
                "hardware PLL phase-lock validation",
                "field validated",
                "realized savings",
                "medical or nervous-system claims",
                "live trading edge",
            ],
        },
        "source_summary": source_summary,
        "holdout_phase_diagnostics": diagnostics,
    }
    payload["phase_proxy_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "source_summary": payload["source_summary"],
            "holdout_phase_diagnostics": payload["holdout_phase_diagnostics"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Phase Proxy Diagnostic Nonpromotion Report",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Phase proxy SHA-256: `{payload.get('phase_proxy_sha256')}`",
        "",
        "## Truth Line",
        "",
        str(summary.get("plain_english_answer") or ""),
        "",
        "## Summary",
        "",
        f"- Internal performance champion: `{str(summary.get('internal_performance_champion')).lower()}`",
        f"- Champion family: `{summary.get('champion_family') or 'none'}`",
        f"- Audited reference candidate: `{summary.get('audited_reference_candidate')}`",
        f"- Reference candidate status: `{summary.get('reference_candidate_status')}`",
        f"- Development-selected candidate: `{summary.get('development_selected_candidate')}`",
        f"- Kuramoto paired wins: `{summary.get('kuramoto_wins_vs_named_baseline')}/{summary.get('kuramoto_paired_holdout_count')}`",
        f"- Kuramoto mean delta vs named baseline: `{summary.get('kuramoto_mean_delta_vs_named_baseline')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Direct measured routes: `{summary.get('direct_measured_route_count')}`",
        f"- Conditioned-synthetic routes: `{summary.get('conditioned_synthetic_route_count')}`",
        f"- Baseline comparisons: `{summary.get('baseline_comparison_count')}`",
        f"- Performance rows reviewed: `{summary.get('performance_rows_reviewed')}`",
        f"- Direct all-baseline globally Holm-positive promotions: `{summary.get('direct_all_baseline_globally_holm_positive_promotion_count')}`",
        f"- Source inventory: `{summary.get('source_inventory_measured_source_count')}` measured sources / `{summary.get('source_inventory_measured_row_count')}` rows",
        f"- Source inventory is performance evidence: `{str(summary.get('source_inventory_is_performance_evidence')).lower()}`",
        f"- Usable numeric holdouts: `{summary.get('usable_numeric_holdout_count')}/{summary.get('holdout_count')}`",
        f"- Non-degenerate numeric holdouts: `{summary.get('non_degenerate_numeric_holdout_count')}`",
        f"- Degenerate numeric holdouts excluded from source means: `{summary.get('degenerate_numeric_holdout_count')}`",
        f"- Mean phase coherence proxy: `{summary.get('mean_phase_coherence_proxy')}`",
        f"- Mean circular phase error proxy: `{summary.get('mean_circular_phase_error_proxy')}`",
        f"- Mean phase slip proxy rate: `{summary.get('mean_phase_slip_proxy_rate')}`",
        f"- Mean spectral concentration proxy: `{summary.get('mean_spectral_concentration_proxy')}`",
        f"- Mean absolute residual lag-1 autocorrelation proxy: `{summary.get('mean_abs_residual_lag1_autocorrelation_proxy')}`",
        f"- Phase measurement claim allowed: `{str(summary.get('phase_measurement_claim_allowed')).lower()}`",
        f"- Performance promotion claim allowed: `{str(summary.get('performance_promotion_claim_allowed')).lower()}`",
        f"- Hardware phase-lock claim allowed: `{str(summary.get('hardware_phase_lock_claim_allowed')).lower()}`",
        "",
        "## Source Summary",
        "",
        "| Source | Holdouts | Usable | Non-Degenerate | Degenerate | Phase Coherence | Slip Rate | Spectral Concentration | Abs Residual Lag1 |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in as_list(payload.get("source_summary")):
        source = as_dict(row)
        lines.append(
            "| "
            f"`{source.get('source_system')}` | "
            f"{source.get('holdout_count')} | "
            f"{source.get('usable_numeric_holdouts')} | "
            f"{source.get('non_degenerate_numeric_holdouts')} | "
            f"{source.get('degenerate_numeric_holdouts')} | "
            f"{source.get('mean_phase_coherence_proxy')} | "
            f"{source.get('mean_phase_slip_proxy_rate')} | "
            f"{source.get('mean_spectral_concentration_proxy')} | "
            f"{source.get('mean_abs_residual_lag1_autocorrelation_proxy')} |"
        )
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            str(payload.get("boundary") or ""),
        ]
    )
    return "\n".join(lines)


def write_outputs(
    payload: dict[str, Any],
    out_json: Path = OUT_JSON,
    dashboard_json: Path = DASHBOARD_JSON,
    out_md: Path = OUT_MD,
) -> None:
    write_json(out_json, payload)
    write_json(dashboard_json, payload)
    write_text(out_md, render_markdown(payload))


def main() -> int:
    payload = build_payload()
    write_outputs(payload)
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["plain_english_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
