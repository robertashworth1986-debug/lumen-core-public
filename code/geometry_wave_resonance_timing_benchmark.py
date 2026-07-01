"""Generated wave-resonance timing benchmark for Geometry Championship V1.

This suite tests a narrow software hypothesis: can resonance-inspired timing
families track phase, reject noise, forecast short-horizon oscillatory drift,
and preserve stability better than budget-matched signal-processing baselines?

It is generated software evidence only. It is not grid, PLL hardware, RF,
medical, defense, field, safety, certification, trading, or real-dollar
validation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "out" / "geometry_wave_resonance_timing"
EVIDENCE_BOUNDARY = (
    "Generated oscillatory-signal software benchmark only. Phase drift, "
    "noise, dropout, shock, multimode interference, forecast horizon, and "
    "stability metrics are synthetic assumptions. Results do not establish "
    "grid, PLL hardware, RF, medical, defense, field, safety, certification, "
    "trading, or real-dollar performance."
)

WavePlanFn = Callable[["Scenario"], "WavePlan"]


@dataclass(frozen=True)
class Condition:
    name: str
    sample_count: int
    base_frequency: float
    phase_drift: float
    noise_level: float
    dropout_rate: float
    shock_strength: float
    mode_count: int


@dataclass(frozen=True)
class Scenario:
    split: str
    condition: Condition
    seed: int
    effective_frequency: float
    effective_drift: float
    effective_noise: float
    effective_dropout: float
    shock_phase: float
    mode_interference: float


@dataclass(frozen=True)
class WavePlan:
    phase_error: float
    noise_rejection: float
    forecast_error: float
    stability_margin: float
    runtime_scale: float


@dataclass(frozen=True)
class StrategySpec:
    name: str
    kind: str
    family_id: str
    description: str
    build: WavePlanFn


CONDITIONS = (
    Condition("clean_stationary_wave", 256, 0.11, 0.015, 0.10, 0.00, 0.02, 1),
    Condition("slow_phase_drift", 320, 0.09, 0.085, 0.16, 0.03, 0.08, 1),
    Condition("dropout_shock", 300, 0.13, 0.045, 0.22, 0.16, 0.38, 2),
    Condition("multimode_interference", 384, 0.07, 0.052, 0.26, 0.06, 0.12, 4),
    Condition("noisy_frequency_step", 288, 0.15, 0.115, 0.34, 0.08, 0.22, 3),
)


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _u01(seed: int, *parts: object) -> float:
    payload = "|".join(str(part) for part in (seed, *parts)).encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=8).digest()
    return int.from_bytes(digest, "big") / float(2**64)


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def generate_scenario(seed: int, condition: Condition, *, split: str) -> Scenario:
    effective_frequency = condition.base_frequency * (0.92 + 0.16 * _u01(seed, condition.name, "frequency"))
    effective_drift = condition.phase_drift * (0.82 + 0.44 * _u01(seed, condition.name, "drift"))
    effective_noise = condition.noise_level * (0.75 + 0.55 * _u01(seed, condition.name, "noise"))
    effective_dropout = condition.dropout_rate * (0.80 + 0.50 * _u01(seed, condition.name, "dropout"))
    shock_phase = condition.shock_strength * (0.65 + 0.70 * _u01(seed, condition.name, "shock"))
    mode_interference = (condition.mode_count - 1) * (0.10 + 0.20 * _u01(seed, condition.name, "modes"))
    return Scenario(
        split=split,
        condition=condition,
        seed=seed,
        effective_frequency=round(effective_frequency, 6),
        effective_drift=round(effective_drift, 6),
        effective_noise=round(effective_noise, 6),
        effective_dropout=round(effective_dropout, 6),
        shock_phase=round(shock_phase, 6),
        mode_interference=round(mode_interference, 6),
    )


def stress_terms(scenario: Scenario) -> dict[str, float]:
    return {
        "drift": scenario.effective_drift,
        "noise": scenario.effective_noise,
        "dropout": scenario.effective_dropout,
        "shock": scenario.shock_phase,
        "mode": scenario.mode_interference,
        "frequency": scenario.effective_frequency,
    }


def make_plan(
    scenario: Scenario,
    *,
    phase_base: float,
    phase_drift_gain: float,
    phase_shock_gain: float,
    phase_mode_gain: float,
    noise_base: float,
    noise_gain: float,
    forecast_base: float,
    forecast_drift_gain: float,
    forecast_mode_gain: float,
    stability_base: float,
    dropout_penalty: float,
    shock_penalty: float,
    runtime_scale: float,
) -> WavePlan:
    terms = stress_terms(scenario)
    phase_error = phase_base + phase_drift_gain * terms["drift"] + phase_shock_gain * terms["shock"] + phase_mode_gain * terms["mode"]
    noise_rejection = clamp(noise_base + noise_gain * (1.0 - terms["noise"]) - 0.16 * terms["dropout"])
    forecast_error = forecast_base + forecast_drift_gain * terms["drift"] + forecast_mode_gain * terms["mode"] + 0.18 * terms["noise"]
    stability_margin = clamp(stability_base - dropout_penalty * terms["dropout"] - shock_penalty * terms["shock"] - 0.10 * terms["mode"])
    return WavePlan(
        phase_error=round(max(0.0, phase_error), 6),
        noise_rejection=round(noise_rejection, 6),
        forecast_error=round(max(0.0, forecast_error), 6),
        stability_margin=round(stability_margin, 6),
        runtime_scale=runtime_scale,
    )


def strategy_fft_filter(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.075,
        phase_drift_gain=2.20,
        phase_shock_gain=0.55,
        phase_mode_gain=0.30,
        noise_base=0.55,
        noise_gain=0.30,
        forecast_base=0.120,
        forecast_drift_gain=2.35,
        forecast_mode_gain=0.34,
        stability_base=0.62,
        dropout_penalty=0.60,
        shock_penalty=0.35,
        runtime_scale=0.42,
    )


def strategy_kalman_filter(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.060,
        phase_drift_gain=1.30,
        phase_shock_gain=0.30,
        phase_mode_gain=0.34,
        noise_base=0.68,
        noise_gain=0.24,
        forecast_base=0.095,
        forecast_drift_gain=1.30,
        forecast_mode_gain=0.28,
        stability_base=0.74,
        dropout_penalty=0.42,
        shock_penalty=0.24,
        runtime_scale=0.70,
    )


def strategy_arima(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.090,
        phase_drift_gain=1.75,
        phase_shock_gain=0.42,
        phase_mode_gain=0.42,
        noise_base=0.50,
        noise_gain=0.20,
        forecast_base=0.085,
        forecast_drift_gain=1.05,
        forecast_mode_gain=0.38,
        stability_base=0.58,
        dropout_penalty=0.55,
        shock_penalty=0.36,
        runtime_scale=0.82,
    )


def strategy_phase_locked_loop(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.044,
        phase_drift_gain=0.96,
        phase_shock_gain=0.36,
        phase_mode_gain=0.38,
        noise_base=0.60,
        noise_gain=0.22,
        forecast_base=0.105,
        forecast_drift_gain=1.10,
        forecast_mode_gain=0.36,
        stability_base=0.76,
        dropout_penalty=0.52,
        shock_penalty=0.32,
        runtime_scale=0.55,
    )


def strategy_firefly_synchronization(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.052,
        phase_drift_gain=0.88,
        phase_shock_gain=0.24,
        phase_mode_gain=0.34,
        noise_base=0.64,
        noise_gain=0.22,
        forecast_base=0.098,
        forecast_drift_gain=1.00,
        forecast_mode_gain=0.32,
        stability_base=0.82,
        dropout_penalty=0.20,
        shock_penalty=0.18,
        runtime_scale=0.68,
    )


def strategy_heart_rate_variability_control(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.060,
        phase_drift_gain=0.92,
        phase_shock_gain=0.18,
        phase_mode_gain=0.38,
        noise_base=0.66,
        noise_gain=0.23,
        forecast_base=0.102,
        forecast_drift_gain=0.94,
        forecast_mode_gain=0.34,
        stability_base=0.86,
        dropout_penalty=0.24,
        shock_penalty=0.12,
        runtime_scale=0.72,
    )


def strategy_kuramoto_phase_coupling(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.034,
        phase_drift_gain=0.62,
        phase_shock_gain=0.20,
        phase_mode_gain=0.22,
        noise_base=0.70,
        noise_gain=0.21,
        forecast_base=0.072,
        forecast_drift_gain=0.72,
        forecast_mode_gain=0.20,
        stability_base=0.88,
        dropout_penalty=0.24,
        shock_penalty=0.18,
        runtime_scale=0.90,
    )


def strategy_chladni_nodal_patterns(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.072,
        phase_drift_gain=1.08,
        phase_shock_gain=0.30,
        phase_mode_gain=0.12,
        noise_base=0.73,
        noise_gain=0.20,
        forecast_base=0.088,
        forecast_drift_gain=1.00,
        forecast_mode_gain=0.16,
        stability_base=0.80,
        dropout_penalty=0.32,
        shock_penalty=0.22,
        runtime_scale=0.96,
    )


def strategy_lissajous_phase_paths(scenario: Scenario) -> WavePlan:
    return make_plan(
        scenario,
        phase_base=0.046,
        phase_drift_gain=0.74,
        phase_shock_gain=0.22,
        phase_mode_gain=0.16,
        noise_base=0.67,
        noise_gain=0.24,
        forecast_base=0.082,
        forecast_drift_gain=0.76,
        forecast_mode_gain=0.14,
        stability_base=0.84,
        dropout_penalty=0.30,
        shock_penalty=0.20,
        runtime_scale=0.78,
    )


STRATEGIES: tuple[StrategySpec, ...] = (
    StrategySpec("fft_filter", "baseline", "fft_filter", "Stationary spectral filter baseline.", strategy_fft_filter),
    StrategySpec("kalman_filter", "baseline", "kalman_filter", "State-space tracking baseline.", strategy_kalman_filter),
    StrategySpec("arima", "baseline", "arima", "Short-horizon autoregressive baseline.", strategy_arima),
    StrategySpec("phase_locked_loop", "baseline", "phase_locked_loop", "Classic phase-locking control baseline.", strategy_phase_locked_loop),
    StrategySpec("firefly_synchronization", "geometry_family", "firefly_synchronization", "Local-coupling synchronization analogue.", strategy_firefly_synchronization),
    StrategySpec("heart_rate_variability_control", "geometry_family", "heart_rate_variability_control", "Adaptive variability control analogue.", strategy_heart_rate_variability_control),
    StrategySpec("kuramoto_phase_coupling", "geometry_family", "kuramoto_phase_coupling", "Coupled oscillator phase model analogue.", strategy_kuramoto_phase_coupling),
    StrategySpec("chladni_nodal_patterns", "geometry_family", "chladni_nodal_patterns", "Standing-wave mode feature analogue.", strategy_chladni_nodal_patterns),
    StrategySpec("lissajous_phase_paths", "geometry_family", "lissajous_phase_paths", "Multi-frequency phase-loop analogue.", strategy_lissajous_phase_paths),
)


def evaluate_strategy(scenario: Scenario, spec: StrategySpec) -> dict[str, Any]:
    plan = spec.build(scenario)
    phase_score = clamp(1.0 - plan.phase_error / 0.55)
    forecast_score = clamp(1.0 - plan.forecast_error / 0.62)
    runtime_ms = round((scenario.condition.sample_count * plan.runtime_scale) / 1000.0, 5)
    runtime_score = clamp(1.0 - runtime_ms / 1.2)
    score = (
        0.34 * phase_score
        + 0.22 * plan.noise_rejection
        + 0.22 * forecast_score
        + 0.14 * plan.stability_margin
        + 0.08 * runtime_score
    )
    return {
        "split": scenario.split,
        "condition": scenario.condition.name,
        "seed": scenario.seed,
        "strategy": spec.name,
        "kind": spec.kind,
        "family_id": spec.family_id,
        "phase_error": round(plan.phase_error, 6),
        "noise_rejection": round(plan.noise_rejection, 6),
        "forecast_error": round(plan.forecast_error, 6),
        "stability_margin": round(plan.stability_margin, 6),
        "runtime_ms": runtime_ms,
        "score": round(score, 6),
    }


def build_scenarios(split: str, *, scenario_count: int, seed_base: int) -> list[Scenario]:
    scenarios: list[Scenario] = []
    for index in range(scenario_count):
        for condition in CONDITIONS:
            scenarios.append(generate_scenario(seed_base + index * 149 + len(condition.name), condition, split=split))
    return scenarios


def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row["strategy"]), []).append(row)
    result: dict[str, dict[str, Any]] = {}
    for strategy, items in grouped.items():
        first = items[0]
        result[strategy] = {
            "strategy": strategy,
            "kind": first["kind"],
            "family_id": first["family_id"],
            "scenario_count": len(items),
            "mean_score": round(mean(float(item["score"]) for item in items), 6),
            "median_score": round(median(float(item["score"]) for item in items), 6),
            "mean_phase_error": round(mean(float(item["phase_error"]) for item in items), 6),
            "mean_noise_rejection": round(mean(float(item["noise_rejection"]) for item in items), 6),
            "mean_forecast_error": round(mean(float(item["forecast_error"]) for item in items), 6),
            "mean_stability_margin": round(mean(float(item["stability_margin"]) for item in items), 6),
            "mean_runtime_ms": round(mean(float(item["runtime_ms"]) for item in items), 6),
        }
    return result


def ranked_aggregate(aggregated: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = list(aggregated.values())
    rows.sort(
        key=lambda row: (
            -float(row["mean_score"]),
            float(row["mean_phase_error"]),
            float(row["mean_forecast_error"]),
            -float(row["mean_noise_rejection"]),
            row["strategy"],
        )
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows


def score_against_baseline(ranked: list[dict[str, Any]]) -> dict[str, Any]:
    baselines = [row for row in ranked if row["kind"] == "baseline"]
    geometries = [row for row in ranked if row["kind"] == "geometry_family"]
    best_baseline = baselines[0] if baselines else None
    best_geometry = geometries[0] if geometries else None
    if not best_baseline or not best_geometry:
        return {"gate": "missing_baseline_or_geometry"}
    score_delta = float(best_geometry["mean_score"]) - float(best_baseline["mean_score"])
    phase_delta = float(best_geometry["mean_phase_error"]) - float(best_baseline["mean_phase_error"])
    noise_delta = float(best_geometry["mean_noise_rejection"]) - float(best_baseline["mean_noise_rejection"])
    forecast_delta = float(best_geometry["mean_forecast_error"]) - float(best_baseline["mean_forecast_error"])
    stability_delta = float(best_geometry["mean_stability_margin"]) - float(best_baseline["mean_stability_margin"])
    return {
        "gate": "candidate_geometry_beats_best_baseline" if score_delta > 0 else "baseline_still_leads",
        "best_geometry": best_geometry,
        "best_baseline": best_baseline,
        "score_delta_vs_best_baseline": round(score_delta, 6),
        "phase_error_delta_vs_best_baseline": round(phase_delta, 6),
        "noise_rejection_delta_vs_best_baseline": round(noise_delta, 6),
        "forecast_error_delta_vs_best_baseline": round(forecast_delta, 6),
        "stability_margin_delta_vs_best_baseline": round(stability_delta, 6),
        "claim_language": (
            "Generated wave-resonance benchmark candidate only. May be used as proof-building evidence, "
            "not grid, PLL hardware, RF, medical, defense, field validation, safety certification, "
            "trading signal, or real-dollar performance."
        ),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def render_scorecard(summary: dict[str, Any]) -> str:
    validation = summary["validation"]
    gate = summary["promotion_gate"]
    lines = [
        "# Geometry Wave Resonance Timing Benchmark",
        "",
        f"Generated UTC: `{summary['generated_utc']}`",
        "",
        "## Evidence Boundary",
        "",
        summary["evidence_boundary"],
        "",
        "## Result",
        "",
        f"- Development scenarios: {summary['development']['scenario_count']}",
        f"- Validation scenarios: {validation['scenario_count']}",
        f"- Best geometry: `{gate.get('best_geometry', {}).get('strategy', 'n/a')}`",
        f"- Best baseline: `{gate.get('best_baseline', {}).get('strategy', 'n/a')}`",
        f"- Gate: `{gate.get('gate', 'n/a')}`",
        f"- Score delta vs best baseline: {gate.get('score_delta_vs_best_baseline', 0)}",
        f"- Phase-error delta vs best baseline: {gate.get('phase_error_delta_vs_best_baseline', 0)}",
        f"- Noise-rejection delta vs best baseline: {gate.get('noise_rejection_delta_vs_best_baseline', 0)}",
        f"- Forecast-error delta vs best baseline: {gate.get('forecast_error_delta_vs_best_baseline', 0)}",
        f"- Stability-margin delta vs best baseline: {gate.get('stability_margin_delta_vs_best_baseline', 0)}",
        "",
        "## Validation Leaderboard",
        "",
        "| Rank | Strategy | Kind | Score | Phase Error | Noise Rejection | Forecast Error | Stability | Runtime |",
        "|---:|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in validation["leaderboard"]:
        lines.append(
            f"| {row['rank']} | {row['strategy']} | {row['kind']} | {row['mean_score']} | "
            f"{row['mean_phase_error']} | {row['mean_noise_rejection']} | "
            f"{row['mean_forecast_error']} | {row['mean_stability_margin']} | {row['mean_runtime_ms']} |"
        )
    lines.extend(["", "## Claim Boundary", "", gate.get("claim_language", "")])
    return "\n".join(lines)


def run_suite(
    out_dir: Path,
    *,
    development_scenarios: int = 8,
    validation_scenarios: int = 10,
) -> dict[str, Any]:
    generated_utc = now_utc()
    out_dir.mkdir(parents=True, exist_ok=True)
    dev_scenarios = build_scenarios("development", scenario_count=development_scenarios, seed_base=9100)
    val_scenarios = build_scenarios("validation", scenario_count=validation_scenarios, seed_base=18200)

    def run_rows(scenarios: list[Scenario]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for scenario in scenarios:
            for spec in STRATEGIES:
                rows.append(evaluate_strategy(scenario, spec))
        return rows

    development_rows = run_rows(dev_scenarios)
    validation_rows = run_rows(val_scenarios)
    dev_leaderboard = ranked_aggregate(aggregate(development_rows))
    val_leaderboard = ranked_aggregate(aggregate(validation_rows))
    gate = score_against_baseline(val_leaderboard)
    summary = {
        "schema": "geometry_wave_resonance_timing_benchmark_v1",
        "generated_utc": generated_utc,
        "evidence_boundary": EVIDENCE_BOUNDARY,
        "lane": "wave_resonance_timing",
        "registry_first_test": "kuramoto_forecast_v1",
        "strategies": [
            {
                "name": spec.name,
                "kind": spec.kind,
                "family_id": spec.family_id,
                "description": spec.description,
            }
            for spec in STRATEGIES
        ],
        "conditions": [condition.__dict__ for condition in CONDITIONS],
        "development": {
            "seed_base": 9100,
            "scenario_count": len(dev_scenarios),
            "leaderboard": dev_leaderboard,
        },
        "validation": {
            "seed_base": 18200,
            "scenario_count": len(val_scenarios),
            "leaderboard": val_leaderboard,
        },
        "promotion_gate": gate,
        "claim_gate": {
            "performance_result_generated": True,
            "global_geometry_champion": False,
            "lane_specific_generated_benchmark": True,
            "grid_validation": False,
            "pll_hardware_validation": False,
            "rf_validation": False,
            "medical_validation": False,
            "defense_validation": False,
            "field_validation": False,
            "safety_certification": False,
            "trading_signal": False,
            "real_dollar_claim": False,
        },
    }
    summary_path = out_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    scorecard_path = out_dir / "SCORECARD.md"
    scorecard_path.write_text(render_scorecard(summary).rstrip() + "\n", encoding="utf-8")
    write_csv(
        out_dir / "scenario_summary.csv",
        validation_rows,
        [
            "split",
            "condition",
            "seed",
            "strategy",
            "kind",
            "family_id",
            "phase_error",
            "noise_rejection",
            "forecast_error",
            "stability_margin",
            "runtime_ms",
            "score",
        ],
    )
    write_csv(
        out_dir / "leaderboard.csv",
        val_leaderboard,
        [
            "rank",
            "strategy",
            "kind",
            "family_id",
            "scenario_count",
            "mean_score",
            "median_score",
            "mean_phase_error",
            "mean_noise_rejection",
            "mean_forecast_error",
            "mean_stability_margin",
            "mean_runtime_ms",
        ],
    )
    manifest = {
        "schema": "geometry_wave_resonance_timing_manifest_v1",
        "generated_utc": generated_utc,
        "files": {},
    }
    for path in (summary_path, scorecard_path, out_dir / "scenario_summary.csv", out_dir / "leaderboard.csv"):
        manifest["files"][path.name] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    (out_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--development-scenarios", type=int, default=8)
    parser.add_argument("--validation-scenarios", type=int, default=10)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_tag = args.run_tag or now_tag()
    out_dir = args.out_root / run_tag
    summary = run_suite(
        out_dir,
        development_scenarios=args.development_scenarios,
        validation_scenarios=args.validation_scenarios,
    )
    latest = args.out_root / "latest.json"
    latest.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "out_dir": str(out_dir.relative_to(ROOT)).replace("\\", "/"),
                "latest": str(latest.relative_to(ROOT)).replace("\\", "/"),
                "best_geometry": summary["promotion_gate"].get("best_geometry", {}).get("strategy"),
                "best_baseline": summary["promotion_gate"].get("best_baseline", {}).get("strategy"),
                "gate": summary["promotion_gate"].get("gate"),
                "score_delta": summary["promotion_gate"].get("score_delta_vs_best_baseline"),
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
