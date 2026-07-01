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

BOUNDARY = (
    "Replay phase-proxy diagnostics for the current internal champion. These metrics are computed "
    "from source-conditioned holdout data and are useful for mechanism triage. They are not hardware "
    "PLL measurements, not field validation, not realized savings, and not proof of live trading edge."
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
            "phase_slip_proxy_count": 0,
            "phase_coherence_proxy": 0.0,
            "circular_phase_error_proxy": 0.0,
            "amplitude_cv_proxy": 0.0,
            "residual_lag1_autocorrelation_proxy": 0.0,
            "spectral_concentration_proxy": 0.0,
        }

    finite_values = [x for x in values if math.isfinite(x)]
    centered_mean = statistics.mean(finite_values)
    centered_raw = [x - centered_mean for x in finite_values]
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
        "phase_slip_proxy_count": phase_slips,
        "phase_slip_proxy_rate": round(phase_slips / max(1, len(phase_jumps)), 6),
        "phase_coherence_proxy": phase_coherence,
        "circular_phase_error_proxy": circular_error,
        "amplitude_cv_proxy": amplitude_cv,
        "residual_lag1_autocorrelation_proxy": residual_auto,
        "spectral_concentration_proxy": spectral_concentration,
        "normalization_scale": round(scale, 6),
        "mean": mean(finite_values),
        "stddev": stdev(normalized),
    }


def build_payload() -> dict[str, Any]:
    holdout = read_json(HOLDOUT_JSON)
    stress = read_json(STRESS_JSON)
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
                "named_baseline": row.get("named_baseline"),
                "delta_vs_named_baseline": row.get("delta_vs_kalman"),
                "candidate_rank": row.get("candidate_rank"),
                "metrics": metrics,
            }
        )

    usable = [row for row in diagnostics if as_dict(row.get("metrics")).get("enough_numeric_data")]
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
        source_summary.append(
            {
                "source_system": source,
                "holdout_count": len(group),
                "usable_numeric_holdouts": len(group_metrics),
                "mean_phase_coherence_proxy": mean(
                    [float(metric.get("phase_coherence_proxy") or 0.0) for metric in group_metrics]
                ),
                "mean_phase_slip_proxy_rate": mean(
                    [float(metric.get("phase_slip_proxy_rate") or 0.0) for metric in group_metrics]
                ),
                "mean_spectral_concentration_proxy": mean(
                    [float(metric.get("spectral_concentration_proxy") or 0.0) for metric in group_metrics]
                ),
                "mean_abs_residual_lag1_autocorrelation_proxy": mean(
                    [abs(float(metric.get("residual_lag1_autocorrelation_proxy") or 0.0)) for metric in group_metrics]
                ),
            }
        )

    stress_summary = as_dict(stress.get("summary"))
    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_phase_proxy_diagnostics_v1",
        "purpose": "Add direct replay-data phase/coherence/residual proxy diagnostics for the current champion.",
        "boundary": BOUNDARY,
        "summary": {
            "champion_family": as_dict(holdout.get("summary")).get("candidate") or "kuramoto_phase_coupling",
            "named_baseline": as_dict(holdout.get("summary")).get("named_baseline") or "kalman_filter",
            "holdout_count": len(rows),
            "usable_numeric_holdout_count": len(usable),
            "source_system_count": len(source_groups),
            "mean_phase_coherence_proxy": mean(coherence_values),
            "mean_circular_phase_error_proxy": mean(circular_errors),
            "mean_phase_slip_proxy_rate": mean(slip_rates),
            "mean_spectral_concentration_proxy": mean(spectral),
            "mean_abs_residual_lag1_autocorrelation_proxy": mean(residual_auto),
            "live_domain_hash_verified": bool(stress_summary.get("live_domain_hash_verified")),
            "phase_proxy_claim_allowed": len(usable) >= 20,
            "hardware_phase_lock_claim_allowed": False,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "plain_english_answer": (
                "The champion now has replay-data phase proxy diagnostics across the current holdout set. "
                "These metrics support mechanism triage for the wave-resonance lane, but they do not prove "
                "hardware PLL behavior or external field validation."
            ),
        },
        "claim_controls": {
            "allowed_now": [
                "replay-data phase proxy diagnostics",
                "source-conditioned mechanism triage",
                "internal phase/coherence/residual proxy evidence",
            ],
            "not_allowed_yet": [
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
        "# Champion Phase Proxy Diagnostics",
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
        f"- Champion: `{summary.get('champion_family')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Usable numeric holdouts: `{summary.get('usable_numeric_holdout_count')}/{summary.get('holdout_count')}`",
        f"- Mean phase coherence proxy: `{summary.get('mean_phase_coherence_proxy')}`",
        f"- Mean circular phase error proxy: `{summary.get('mean_circular_phase_error_proxy')}`",
        f"- Mean phase slip proxy rate: `{summary.get('mean_phase_slip_proxy_rate')}`",
        f"- Mean spectral concentration proxy: `{summary.get('mean_spectral_concentration_proxy')}`",
        f"- Mean absolute residual lag-1 autocorrelation proxy: `{summary.get('mean_abs_residual_lag1_autocorrelation_proxy')}`",
        f"- Hardware phase-lock claim allowed: `{str(summary.get('hardware_phase_lock_claim_allowed')).lower()}`",
        "",
        "## Source Summary",
        "",
        "| Source | Holdouts | Usable | Phase Coherence | Slip Rate | Spectral Concentration | Abs Residual Lag1 |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in as_list(payload.get("source_summary")):
        source = as_dict(row)
        lines.append(
            "| "
            f"`{source.get('source_system')}` | "
            f"{source.get('holdout_count')} | "
            f"{source.get('usable_numeric_holdouts')} | "
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


def main() -> int:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")
    print(payload["summary"]["plain_english_answer"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
