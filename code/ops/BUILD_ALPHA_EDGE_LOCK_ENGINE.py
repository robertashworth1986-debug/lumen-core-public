from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "out" / "ops" / "alpha_edge_lock"

SECTOR_MATRIX_PATH = ROOT / "out" / "sector_value_matrix.json"
BENCHMARK_BEATER_PATH = ROOT / "out" / "execution" / "benchmark_beater.json"
TOP_SYSTEM_STRATEGY_BASELINE_PATH = ROOT / "out" / "execution" / "top_system_strategy_baseline.json"
KRAKEN_GAUNTLET_PATH = ROOT / "out" / "ops" / "kraken_institutional_alpha_gauntlet_latest.json"
SYMBOL_TIMING_EDGE_PATH = ROOT / "out" / "ops" / "symbol_timing_edge_latest.json"
KURAMOTO_CROSS_SECTOR_PATH = ROOT / "out" / "ops" / "kuramoto_cross_sector_benchmark_latest.json"
BRANCHING_LIVE_BREADTH_PATH = ROOT / "out" / "ops" / "branching_live_breadth_replay_latest.json"
GEOMETRY_CONFIRMATORY_PATH = ROOT / "out" / "ops" / "geometry_confirmatory_promotion_audit_latest.json"

HEARTBEAT_LATEST_PATH = OUT_DIR / "alpha_edge_lock_engine_heartbeat_latest.json"

STATUS_NO_PROVEN_ALPHA = "NO_PROVEN_ALPHA_EDGE"

STRICT_ALPHA_GATE_KEYS = (
    "truly_unseen_forward_holdout",
    "realistic_costs_and_slippage",
    "positive_excess_return",
    "risk_adjusted_metric",
    "sufficient_trades_and_history",
    "multiple_testing_correction",
    "capacity_and_liquidity",
    "reproducible_code_and_data_hash",
    "independent_or_prospective_replication",
)

SECTOR_PROBLEM_MAP: dict[str, tuple[str, str]] = {
    "energy": (
        "Grid instability and outage cascades",
        "keep power systems stable before failures propagate",
    ),
    "energy_lab": (
        "Energy R&D blind spots",
        "accelerate high-impact infrastructure innovation decisions",
    ),
    "market_data": (
        "Information latency in markets",
        "reduce delayed decisions and hidden risk accumulation",
    ),
    "broker": (
        "Execution friction in financial rails",
        "lower slippage, missed opportunities, and operational drag",
    ),
    "crypto_exec": (
        "Volatile execution and settlement gaps",
        "improve reliability of digital-asset research operations",
    ),
    "weather": (
        "Extreme weather response lag",
        "trigger earlier resilience actions for vulnerable systems",
    ),
    "air_quality": (
        "Air-quality risk response delays",
        "protect health and productivity through earlier intervention",
    ),
    "rates": (
        "Interest-rate shock blindness",
        "preserve capital and planning stability under macro volatility",
    ),
    "macro": (
        "Macro regime transition risk",
        "adapt decisions before systemic drift becomes loss",
    ),
    "water": (
        "Water reliability and contamination risk",
        "detect and prioritize intervention windows earlier",
    ),
    "federal_data": (
        "Government data fragmentation",
        "convert fragmented telemetry into decision-grade evidence",
    ),
    "labor": (
        "Human time waste in repetitive operations",
        "free skilled time for high-value human judgment",
    ),
    "space": (
        "Space and satellite operation blind spots",
        "reduce downtime and mission risk through predictive alerts",
    ),
    "demographic": (
        "Population trend misalignment",
        "align planning with changing demand and risk footprints",
    ),
    "federal_contracts": (
        "Procurement cycle latency",
        "improve opportunity qualification and response speed",
    ),
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_tag() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except Exception:
        return path.name


def problem_for_sector(sector: str) -> tuple[str, str]:
    key = str(sector or "").strip().lower()
    if key in SECTOR_PROBLEM_MAP:
        return SECTOR_PROBLEM_MAP[key]
    return (
        f"Operational instability in {key or 'unknown'} systems",
        "improve resilience and decision speed through measured evidence",
    )


def build_business_problem_context(sector_matrix: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row
        for row in as_list(as_dict(sector_matrix).get("sector_value_matrix"))
        if isinstance(row, dict)
    ]
    if not rows:
        rows = [
            {
                "sector": "financial_market_research",
                "year": 0.0,
                "basis": "CURRENT_EVIDENCE",
                "problem_statement": (
                    "Unvalidated strategy selection under costs, limited history, and multiple testing"
                ),
                "mission_outcome": (
                    "separate research candidates from proven alpha before any capital decision"
                ),
            }
        ]
    rows.sort(
        key=lambda row: safe_float(row.get("year", row.get("annual_exposure_usd")), 0.0),
        reverse=True,
    )

    context: list[dict[str, Any]] = []
    for rank, row in enumerate(rows, start=1):
        sector = str(row.get("sector") or "unknown")
        default_problem, default_mission = problem_for_sector(sector)
        problem = str(row.get("problem_statement") or default_problem)
        mission = str(row.get("mission_outcome") or default_mission)
        annual_exposure = safe_float(row.get("year", row.get("annual_exposure_usd")), 0.0)
        context.append(
            {
                "rank": rank,
                "sector": sector,
                "problem_statement": problem,
                "mission_outcome": mission,
                "business_context_only": True,
                "annual_exposure_usd": round(max(0.0, annual_exposure), 2),
                "evidence_basis": str(row.get("basis") or "UNKNOWN").upper(),
                "validation_mode": "business_problem_context_only_not_alpha",
                "alpha_proven": False,
                # Legacy row keys are retained as explicit zeros. Exposure is never
                # transformed into an alpha, edge, confidence, or profit score.
                "alpha_lock_score": 0.0,
                "edge_lock_score": 0.0,
                "harmonic_alpha_edge_score": 0.0,
                "confidence_live_lock_pct": 0.0,
                "lock_grade": "UNPROVEN",
                "wealth_time_blend_score": 0.0,
                "modeled_annual_upside_usd": 0.0,
                "hourly_value_usd": 0.0,
                "modeled_time_saved_hours_per_week": 0.0,
                "fte_hours_equivalent": 0.0,
                "recommended_grants": [],
                "sim": {
                    "status": "not_run_opportunity_scores_are_not_alpha",
                    "alpha_hit_pct": 0.0,
                    "edge_hit_pct": 0.0,
                    "joint_hit_pct": 0.0,
                    "near_joint_hit_pct": 0.0,
                },
                "priority": "BUSINESS_CONTEXT_ONLY",
            }
        )
    return context


def extract_benchmark_beater(payload: dict[str, Any]) -> dict[str, Any]:
    headline = as_dict(payload.get("headline"))
    validation = as_dict(payload.get("validation"))
    return {
        "generated_utc": payload.get("generated_utc"),
        "overall_verdict": str(headline.get("overall_verdict") or "UNKNOWN"),
        "windows_beating": safe_int(headline.get("windows_beating")),
        "windows_total": safe_int(headline.get("windows_total")),
        "beat_rate_pct": safe_float(headline.get("beat_rate_pct")),
        "median_alpha_edge_pct": safe_float(headline.get("median_alpha_edge_pct")),
        "positive_sharpe_rate_pct": safe_float(headline.get("positive_sharpe_rate_pct")),
        "chronological_no_lookahead": bool(validation.get("chronological_no_lookahead")),
        "roundtrip_cost_bps": safe_float(validation.get("roundtrip_cost_bps")),
        "slippage_bps_per_side": safe_float(validation.get("slippage_bps_per_side")),
        "promotion_status": str(validation.get("promotion_status") or "UNKNOWN"),
        "claim": "Historical live-data benchmark result; current verdict is not a robust edge.",
    }


def extract_top_system_baseline(payload: dict[str, Any]) -> dict[str, Any]:
    baseline = as_dict(payload.get("baseline"))
    rows = [row for row in as_list(payload.get("top_strategies")) if isinstance(row, dict)]
    top = rows[0] if rows else {}
    source_path = Path(str(top.get("source_file") or "")) if top.get("source_file") else None
    source_hash = sha256_file(source_path) if source_path else None
    return {
        "generated_utc": payload.get("generated_utc"),
        "candidate": {
            "flow": top.get("flow", baseline.get("top_flow")),
            "strategy": top.get("strategy", baseline.get("top_strategy")),
            "algo": top.get("algo", baseline.get("top_algo")),
        },
        "test_sharpe": safe_float(top.get("test_sharpe", baseline.get("top_test_sharpe"))),
        "test_vs_baseline": safe_float(
            top.get("test_vs_baseline", baseline.get("top_test_vs_baseline"))
        ),
        "walk_forward_sharpe_mean": safe_float(baseline.get("top_wf_sharpe_mean")),
        "walk_forward_stability": safe_float(baseline.get("top_wf_stability")),
        "total_candidates_searched": safe_int(baseline.get("total_candidates")),
        "files_scanned": safe_int(baseline.get("files_scanned")),
        "source_data_sha256": source_hash,
        "claim": "Development-selected historical candidate; not prospective or independently replicated.",
    }


def extract_kraken_gauntlet(payload: dict[str, Any]) -> dict[str, Any]:
    summary = as_dict(payload.get("summary"))
    runtime = as_dict(payload.get("runtime_summary"))
    return {
        "generated_utc": payload.get("generated_utc"),
        "status": str(payload.get("status") or "UNKNOWN"),
        "gauntlet_row_count": safe_int(summary.get("gauntlet_row_count")),
        "institutional_research_candidate_count": safe_int(
            summary.get("institutional_research_candidate_count")
        ),
        "large_fund_ready_count": safe_int(summary.get("large_fund_ready_count")),
        "trusted_with_large_fund_now": bool(summary.get("trusted_with_large_fund_now")),
        "order_placement_allowed": bool(summary.get("order_placement_allowed")),
        "capital_movement_allowed": bool(summary.get("capital_movement_allowed")),
        "audit_posture": str(runtime.get("audit_posture") or "UNKNOWN"),
        "claim": "Paper-research gauntlet only; no performance or profit claim.",
    }


def extract_symbol_timing(payload: dict[str, Any]) -> dict[str, Any]:
    controls = as_dict(payload.get("controls"))
    production_gate = as_dict(payload.get("production_gate"))
    return {
        "generated_utc": payload.get("generated_utc"),
        "symbols_analyzed": safe_int(payload.get("symbols_analyzed")),
        "execution_authorized": bool(payload.get("execution_authorized")),
        "production_gate_status": str(production_gate.get("status") or "UNKNOWN"),
        "production_gate_reasons": [
            str(reason) for reason in as_list(production_gate.get("reasons"))
        ],
        "minimum_bars": safe_int(controls.get("min_bars")),
        "roundtrip_cost_bps": safe_float(controls.get("roundtrip_cost_bps")),
        "train_fraction": safe_float(controls.get("train_fraction")),
        "claim": "Shadow timing research; the production gate is authoritative.",
    }


def extract_kuramoto(payload: dict[str, Any]) -> dict[str, Any]:
    gates = as_dict(payload.get("gates"))
    return {
        "generated_utc": payload.get("generated_utc"),
        "status": str(payload.get("status") or "UNKNOWN"),
        "sector_gain_proven_count": safe_int(gates.get("sector_gain_proven_count")),
        "sector_count": safe_int(gates.get("sector_count")),
        "total_evaluation_origin_count": safe_int(gates.get("total_evaluation_origin_count")),
        "prospective_cross_sector_holdout_complete": bool(
            gates.get("prospective_cross_sector_holdout_complete")
        ),
        "external_cross_sector_replication_complete": bool(
            gates.get("external_cross_sector_replication_complete")
        ),
        "trading_execution_allowed": bool(gates.get("trading_execution_allowed")),
        "safest_next_action": payload.get("safest_next_action"),
        "claim": "Current cross-sector result is negative and cannot support trading alpha.",
    }


def extract_branching_replay(payload: dict[str, Any]) -> dict[str, Any]:
    promotion = as_dict(payload.get("promotion_gate"))
    validation = as_dict(as_dict(payload.get("validation_replay")).get("gate"))
    best_baseline = as_dict(validation.get("best_baseline"))
    best_geometry = as_dict(validation.get("best_geometry"))
    return {
        "generated_utc": payload.get("generated_utc"),
        "family_id": payload.get("family_id"),
        "validation_gate": str(validation.get("gate") or "UNKNOWN"),
        "best_baseline": best_baseline.get("family_id", best_baseline.get("strategy")),
        "best_geometry": best_geometry.get("family_id", best_geometry.get("strategy")),
        "score_delta_vs_best_baseline": safe_float(
            validation.get("score_delta_vs_best_baseline")
        ),
        "candidate_geometry_beats_best_baseline": bool(
            promotion.get("candidate_geometry_beats_best_baseline")
        ),
        "ready_for_live_geometry_claim": bool(promotion.get("ready_for_live_geometry_claim")),
        "ready_for_real_dollar_claim": bool(promotion.get("ready_for_real_dollar_claim")),
        "live_measured_row_count": safe_int(promotion.get("live_measured_row_count")),
        "requirements_missing": [
            str(reason) for reason in as_list(promotion.get("requirements_missing"))
        ],
        "claim": "Proxy replay retains a baseline-led result; no field or dollar claim.",
    }


def extract_brachistochrone_control(payload: dict[str, Any]) -> dict[str, Any]:
    comparisons = [
        row for row in as_list(payload.get("family_comparisons")) if isinstance(row, dict)
    ]
    comparison = next(
        (
            row
            for row in comparisons
            if str(row.get("family_id") or "") == "brachistochrone_descent"
            and str(row.get("baseline_id") or "") == "minimum_jerk_curve"
        ),
        {},
    )
    checks = as_dict(comparison.get("checks"))
    interval = as_dict(comparison.get("paired_score_interval"))
    smoothness = next(
        (
            row
            for row in as_list(comparison.get("metric_guardrails"))
            if isinstance(row, dict) and str(row.get("metric") or "") == "smoothness"
        ),
        {},
    )
    return {
        "generated_utc": payload.get("generated_utc"),
        "family_id": comparison.get("family_id"),
        "baseline_id": comparison.get("baseline_id"),
        "lane": comparison.get("lane"),
        "development_preselected": bool(comparison.get("development_preselected")),
        "confirmatory_pass": bool(comparison.get("confirmatory_pass")),
        "decision": str(comparison.get("decision") or "UNKNOWN"),
        "all_condition_guardrails_passed": bool(
            checks.get("all_condition_score_noninferiority")
        ),
        "observed_paired_aggregate_delta": safe_float(interval.get("observed_mean_delta")),
        "paired_ci95": [safe_float(value) for value in as_list(interval.get("ci95"))[:2]],
        "paired_synthetic_scenario_count": safe_int(interval.get("paired_scenario_count")),
        "smoothness_baseline": safe_float(smoothness.get("baseline_mean")),
        "smoothness_candidate": safe_float(smoothness.get("candidate_mean")),
        "smoothness_candidate_minus_baseline": safe_float(
            smoothness.get("raw_candidate_minus_baseline")
        ),
        "smoothness_passed": bool(smoothness.get("passes_noninferiority")),
        "failed_checks": [str(value) for value in as_list(comparison.get("failed_checks"))],
        "evidence_boundary": payload.get("evidence_boundary"),
        "claim": "Synthetic confirmatory control evidence only; HIL and physical validation are absent.",
    }


def artifact_receipt(
    source_id: str,
    path: Path,
    payload: dict[str, Any],
    normalized: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_id": source_id,
        "path": relative_path(path),
        "exists": path.exists(),
        "sha256": sha256_file(path),
        "generated_utc": payload.get("generated_utc"),
        "normalized_status": normalized.get("status")
        or normalized.get("overall_verdict")
        or normalized.get("production_gate_status")
        or normalized.get("decision")
        or normalized.get("validation_gate")
        or "CONTEXT_ONLY",
        "integrity_boundary": (
            "The hash identifies this local artifact. It is not independent validation, "
            "a data-lineage certificate, or proof of alpha."
        ),
    }


def iter_strict_receipts(payload: dict[str, Any]) -> list[dict[str, Any]]:
    value = payload.get("strict_alpha_gate_receipt")
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    return []


def evaluate_strict_alpha_gates(
    raw_sources: dict[str, dict[str, Any]],
    observed_support: dict[str, bool],
) -> dict[str, Any]:
    complete_receipts: list[dict[str, Any]] = []
    incomplete_receipts: list[dict[str, Any]] = []

    for source_id, payload in raw_sources.items():
        for receipt in iter_strict_receipts(payload):
            gates = as_dict(receipt.get("gates"))
            missing = [key for key in STRICT_ALPHA_GATE_KEYS if gates.get(key) is not True]
            candidate_id = str(receipt.get("candidate_id") or "").strip()
            status_ok = str(receipt.get("status") or "").upper() == "PASSED"
            receipt_summary = {
                "source_id": source_id,
                "candidate_id": candidate_id or None,
                "status": receipt.get("status"),
                "missing_or_failed_gates": missing,
            }
            if candidate_id and status_ok and not missing:
                complete_receipts.append(receipt_summary)
            else:
                incomplete_receipts.append(receipt_summary)

    current_alpha_proven = bool(complete_receipts)
    selected = complete_receipts[0] if complete_receipts else None
    gate_reasons = {
        "truly_unseen_forward_holdout": (
            "Chronological or generated holdouts are not a never-before-scored prospective receipt."
        ),
        "realistic_costs_and_slippage": (
            "Costs are modeled in source artifacts, but no single promoted candidate passes after "
            "venue-realistic fees, spread, impact, and slippage."
        ),
        "positive_excess_return": (
            "Positive exploratory deltas exist, but the benchmark-beater verdict is NO_ROBUST_EDGE "
            "and no prospective candidate has positive net excess return."
        ),
        "risk_adjusted_metric": (
            "Historical Sharpe values exist without a matching prospective, corrected promotion receipt."
        ),
        "sufficient_trades_and_history": (
            "The timing production gate reports insufficient history; no candidate supplies a sufficient "
            "trade count and regime span under one locked protocol."
        ),
        "multiple_testing_correction": (
            "The searched candidate families do not provide a candidate-level deflated Sharpe, SPA, "
            "reality-check, or equivalent multiplicity receipt."
        ),
        "capacity_and_liquidity": (
            "The Kraken gauntlet has zero large-fund-ready candidates and no validated impact/capacity curve."
        ),
        "reproducible_code_and_data_hash": (
            "Local artifact hashes exist, but no candidate bundle ties frozen strategy code, exact raw data, "
            "environment, and result hashes into one reproducible promotion receipt."
        ),
        "independent_or_prospective_replication": (
            "No independent evaluator or completed prospective replication receipt is present."
        ),
    }

    gates: dict[str, dict[str, Any]] = {}
    for key in STRICT_ALPHA_GATE_KEYS:
        passed = bool(selected) and current_alpha_proven
        gates[key] = {
            "passed": passed,
            "observed_support_only": bool(observed_support.get(key)),
            "reason": (
                "Passed in one complete strict-alpha receipt."
                if passed
                else gate_reasons[key]
            ),
        }

    return {
        "policy": (
            "Every gate must pass for the same preregistered candidate. Evidence cannot be pooled "
            "across unrelated artifacts, assets, simulations, or domains."
        ),
        "required_gate_count": len(STRICT_ALPHA_GATE_KEYS),
        "passed_gate_count": len(STRICT_ALPHA_GATE_KEYS) if current_alpha_proven else 0,
        "all_required_gates_passed": current_alpha_proven,
        "current_alpha_proven": current_alpha_proven,
        "proven_candidate_receipts": complete_receipts,
        "rejected_or_incomplete_receipts": incomplete_receipts,
        "gates": gates,
    }


def build_candidate_queue(
    benchmark: dict[str, Any],
    top_system: dict[str, Any],
    kraken: dict[str, Any],
    symbol_timing: dict[str, Any],
    brachistochrone: dict[str, Any],
) -> list[dict[str, Any]]:
    top_candidate = as_dict(top_system.get("candidate"))
    queue: list[dict[str, Any]] = [
        {
            "candidate_id": "geom_regime_switch_forward_net_alpha_v1",
            "domain": "financial_alpha_research",
            "classification": "preregistered_hypothesis_only",
            "current_status": "UNPROVEN_FORWARD_TEST_REQUIRED",
            "current_alpha_proven": False,
            "hypothesis": (
                "The locked geom_gaussian + regime_switch + confidence_weighted candidate will "
                "produce positive net excess return versus a preregistered passive baseline on a "
                "never-before-scored forward Kraken window after realistic fees, spread, impact, and slippage."
            ),
            "source_observations": {
                "flow": top_candidate.get("flow"),
                "strategy": top_candidate.get("strategy"),
                "algo": top_candidate.get("algo"),
                "historical_test_sharpe": top_system.get("test_sharpe"),
                "historical_test_vs_baseline": top_system.get("test_vs_baseline"),
                "historical_candidates_searched": top_system.get("total_candidates_searched"),
                "benchmark_beater_verdict": benchmark.get("overall_verdict"),
                "benchmark_beater_median_alpha_edge_pct": benchmark.get(
                    "median_alpha_edge_pct"
                ),
                "kraken_large_fund_ready_count": kraken.get("large_fund_ready_count"),
            },
            "preregistration": {
                "freeze_before_first_forward_bar": [
                    "candidate code and parameters",
                    "asset universe and passive baseline",
                    "forward start and end timestamps",
                    "fee, spread, slippage, and market-impact model",
                    "primary excess-return and risk-adjusted metrics",
                    "trade-count, history, liquidity, and capacity minima",
                    "multiplicity correction and rejection threshold",
                    "code, environment, and source-data hashes",
                ],
                "minimum_evidence": [
                    "at least 26 weeks of untouched forward history across multiple regimes",
                    "at least 100 completed round trips after all costs",
                    "positive net excess return with a positive risk-adjusted lower confidence bound",
                    "deflated Sharpe, Hansen SPA, White reality check, or equivalent correction",
                    "order-book-derived capacity and participation-rate limits",
                    "independent replay or prospective replication",
                ],
                "next_test": (
                    "Freeze one candidate and one baseline before the next forward window, collect "
                    "paper-only fills with venue-realistic costs, and publish the full null-inclusive result."
                ),
            },
            "live_trading_allowed": False,
            "capital_deployment_allowed": False,
            "public_performance_claim_allowed": False,
        },
        {
            "candidate_id": "symbol_timing_forward_window_v1",
            "domain": "financial_alpha_research",
            "classification": "preregistered_hypothesis_only",
            "current_status": "BLOCKED_INSUFFICIENT_HISTORY",
            "current_alpha_proven": False,
            "hypothesis": (
                "A training-only UTC timing-window selector will improve net forward excess return "
                "versus an all-hours entry schedule on an untouched holdout after the full cost model."
            ),
            "source_observations": {
                "symbols_analyzed": symbol_timing.get("symbols_analyzed"),
                "production_gate_status": symbol_timing.get("production_gate_status"),
                "production_gate_reasons": symbol_timing.get("production_gate_reasons"),
                "roundtrip_cost_bps": symbol_timing.get("roundtrip_cost_bps"),
                "execution_authorized": symbol_timing.get("execution_authorized"),
            },
            "preregistration": {
                "freeze_before_holdout": [
                    "eligible symbols and minimum-history rule",
                    "training-only window-selection rule",
                    "all-hours and passive baselines",
                    "untouched holdout dates",
                    "52 bps roundtrip floor plus measured spread and impact",
                    "symbol-hour multiplicity correction",
                    "minimum trades and liquidity thresholds",
                ],
                "minimum_evidence": [
                    "at least 26 weeks of hourly history before selection",
                    "a separately untouched forward holdout",
                    "positive net excess return and risk-adjusted metric after correction",
                    "capacity, liquidity, reproducibility, and independent replication receipts",
                ],
                "next_test": (
                    "Accumulate the missing history, freeze the selector without reading the holdout, "
                    "then run one paper-only forward evaluation across the locked symbol universe."
                ),
            },
            "live_trading_allowed": False,
            "capital_deployment_allowed": False,
            "public_performance_claim_allowed": False,
        },
        {
            "candidate_id": "brachistochrone_minimum_jerk_phase_locked_foc_hil_v1",
            "domain": "control_trajectory_engineering",
            "classification": "non_trading_control_candidate",
            "current_status": "NOT_PROMOTED_HIL_AND_PHYSICAL_VALIDATION_REQUIRED",
            "current_alpha_proven": False,
            "hypothesis": (
                "A brachistochrone_descent reference shaped by minimum-jerk smoothing and tracked "
                "through a phase-locked motor/FOC inner loop can retain the paired trajectory-score "
                "advantage while making smoothness noninferior to the minimum-jerk baseline."
            ),
            "source_observations": {
                "development_preselected": brachistochrone.get("development_preselected"),
                "synthetic_confirmatory_pass": brachistochrone.get("confirmatory_pass"),
                "paired_aggregate_delta": brachistochrone.get(
                    "observed_paired_aggregate_delta"
                ),
                "paired_ci95": brachistochrone.get("paired_ci95"),
                "paired_synthetic_scenario_count": brachistochrone.get(
                    "paired_synthetic_scenario_count"
                ),
                "all_condition_guardrails_passed": brachistochrone.get(
                    "all_condition_guardrails_passed"
                ),
                "smoothness_baseline": brachistochrone.get("smoothness_baseline"),
                "smoothness_candidate": brachistochrone.get("smoothness_candidate"),
                "smoothness_candidate_minus_baseline": brachistochrone.get(
                    "smoothness_candidate_minus_baseline"
                ),
                "promotion_failure": "smoothness_noninferiority_failed",
            },
            "preregistration": {
                "freeze_before_hil": [
                    "plant, inverter, motor, sensor, and load models",
                    "trajectory endpoints, limits, and minimum-jerk smoothing law",
                    "phase-lock and FOC gains, sample rate, saturation, and anti-windup",
                    "minimum-jerk and unsmoothed brachistochrone baselines",
                    "paired scenarios, seeds, metrics, margins, and safety aborts",
                    "controller code, HIL image, configuration, and data hashes",
                ],
                "primary_metrics": [
                    "travel_time",
                    "smoothness",
                    "tracking_error",
                    "energy_or_current_integral",
                    "constraint_violation_rate",
                    "overshoot_and_thermal_limits",
                ],
                "promotion_rule": (
                    "Require a positive paired aggregate lower confidence bound, smoothness "
                    "noninferiority to minimum jerk, every safety/condition guardrail, independent "
                    "HIL reproduction, and then a separately approved physical-rig validation."
                ),
                "next_test": (
                    "Implement the composite reference and inner loop in a non-energized simulator, "
                    "freeze it, run paired HIL trials against both baselines, and retain all null and "
                    "failed results before any physical-rig test."
                ),
            },
            "financial_alpha_candidate": False,
            "trading_relevance": "none",
            "live_trading_allowed": False,
            "capital_deployment_allowed": False,
            "public_performance_claim_allowed": False,
            "physical_control_deployment_allowed": False,
        },
    ]
    return queue[:3]


def build_payload(
    *,
    sector_matrix: dict[str, Any] | None = None,
    benchmark_beater: dict[str, Any] | None = None,
    top_system_strategy: dict[str, Any] | None = None,
    kraken_gauntlet: dict[str, Any] | None = None,
    symbol_timing: dict[str, Any] | None = None,
    kuramoto: dict[str, Any] | None = None,
    branching_replay: dict[str, Any] | None = None,
    geometry_confirmatory: dict[str, Any] | None = None,
    sim_runs: int = 5000,
    alpha_threshold: float = 78.0,
    edge_threshold: float = 72.0,
    top_n: int = 12,
) -> dict[str, Any]:
    sector_matrix = (
        load_json(SECTOR_MATRIX_PATH, {}) if sector_matrix is None else as_dict(sector_matrix)
    )
    benchmark_beater = (
        load_json(BENCHMARK_BEATER_PATH, {})
        if benchmark_beater is None
        else as_dict(benchmark_beater)
    )
    top_system_strategy = (
        load_json(TOP_SYSTEM_STRATEGY_BASELINE_PATH, {})
        if top_system_strategy is None
        else as_dict(top_system_strategy)
    )
    kraken_gauntlet = (
        load_json(KRAKEN_GAUNTLET_PATH, {})
        if kraken_gauntlet is None
        else as_dict(kraken_gauntlet)
    )
    symbol_timing = (
        load_json(SYMBOL_TIMING_EDGE_PATH, {})
        if symbol_timing is None
        else as_dict(symbol_timing)
    )
    kuramoto = (
        load_json(KURAMOTO_CROSS_SECTOR_PATH, {})
        if kuramoto is None
        else as_dict(kuramoto)
    )
    branching_replay = (
        load_json(BRANCHING_LIVE_BREADTH_PATH, {})
        if branching_replay is None
        else as_dict(branching_replay)
    )
    geometry_confirmatory = (
        load_json(GEOMETRY_CONFIRMATORY_PATH, {})
        if geometry_confirmatory is None
        else as_dict(geometry_confirmatory)
    )

    normalized = {
        "benchmark_beater": extract_benchmark_beater(benchmark_beater),
        "top_system_strategy_baseline": extract_top_system_baseline(top_system_strategy),
        "kraken_institutional_gauntlet": extract_kraken_gauntlet(kraken_gauntlet),
        "symbol_timing_production_gate": extract_symbol_timing(symbol_timing),
        "kuramoto_cross_sector_benchmark": extract_kuramoto(kuramoto),
        "branching_live_breadth_replay": extract_branching_replay(branching_replay),
        "brachistochrone_control_audit": extract_brachistochrone_control(
            geometry_confirmatory
        ),
    }

    raw_sources = {
        "benchmark_beater": benchmark_beater,
        "top_system_strategy_baseline": top_system_strategy,
        "kraken_institutional_gauntlet": kraken_gauntlet,
        "symbol_timing_production_gate": symbol_timing,
        "kuramoto_cross_sector_benchmark": kuramoto,
        "branching_live_breadth_replay": branching_replay,
        "brachistochrone_control_audit": geometry_confirmatory,
    }

    benchmark = normalized["benchmark_beater"]
    top_system = normalized["top_system_strategy_baseline"]
    kraken = normalized["kraken_institutional_gauntlet"]
    timing = normalized["symbol_timing_production_gate"]
    kuramoto_evidence = normalized["kuramoto_cross_sector_benchmark"]
    branching = normalized["branching_live_breadth_replay"]
    brachistochrone = normalized["brachistochrone_control_audit"]

    receipt_paths = {
        "benchmark_beater": BENCHMARK_BEATER_PATH,
        "top_system_strategy_baseline": TOP_SYSTEM_STRATEGY_BASELINE_PATH,
        "kraken_institutional_gauntlet": KRAKEN_GAUNTLET_PATH,
        "symbol_timing_production_gate": SYMBOL_TIMING_EDGE_PATH,
        "kuramoto_cross_sector_benchmark": KURAMOTO_CROSS_SECTOR_PATH,
        "branching_live_breadth_replay": BRANCHING_LIVE_BREADTH_PATH,
        "brachistochrone_control_audit": GEOMETRY_CONFIRMATORY_PATH,
    }
    receipts = [
        artifact_receipt(source_id, receipt_paths[source_id], raw_sources[source_id], value)
        for source_id, value in normalized.items()
    ]

    observed_support = {
        "truly_unseen_forward_holdout": False,
        "realistic_costs_and_slippage": (
            safe_float(benchmark.get("roundtrip_cost_bps")) > 0
            and safe_float(benchmark.get("slippage_bps_per_side")) > 0
            and safe_float(timing.get("roundtrip_cost_bps")) > 0
        ),
        "positive_excess_return": (
            safe_float(benchmark.get("median_alpha_edge_pct")) > 0
            or safe_float(top_system.get("test_vs_baseline")) > 0
        ),
        "risk_adjusted_metric": (
            safe_float(top_system.get("test_sharpe")) > 0
            or safe_float(benchmark.get("positive_sharpe_rate_pct")) > 0
        ),
        "sufficient_trades_and_history": False,
        "multiple_testing_correction": False,
        "capacity_and_liquidity": bool(kraken.get("trusted_with_large_fund_now")),
        "reproducible_code_and_data_hash": (
            all(isinstance(row.get("sha256"), str) and len(row["sha256"]) == 64 for row in receipts)
            and isinstance(top_system.get("source_data_sha256"), str)
            and len(str(top_system.get("source_data_sha256"))) == 64
        ),
        "independent_or_prospective_replication": (
            bool(kuramoto_evidence.get("prospective_cross_sector_holdout_complete"))
            and bool(kuramoto_evidence.get("external_cross_sector_replication_complete"))
        ),
    }
    alpha_assessment = evaluate_strict_alpha_gates(raw_sources, observed_support)
    current_alpha_proven = bool(alpha_assessment.get("current_alpha_proven"))

    problem_stack = build_business_problem_context(sector_matrix)
    candidate_queue = build_candidate_queue(
        benchmark=benchmark,
        top_system=top_system,
        kraken=kraken,
        symbol_timing=timing,
        brachistochrone=brachistochrone,
    )

    top_problem = problem_stack[0].get("problem_statement") if problem_stack else None
    top_sector = problem_stack[0].get("sector") if problem_stack else None
    proven_receipts = as_list(alpha_assessment.get("proven_candidate_receipts"))

    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "schema": "alpha_edge_lock_engine.v2",
        "scope": "alpha_edge_lock_engine",
        "status": "PROVEN_ALPHA_EDGE_RECEIPT_PRESENT" if current_alpha_proven else STATUS_NO_PROVEN_ALPHA,
        "claim_boundary": (
            "Opportunity exposure, modeled upside, internal scores, synthetic simulations, and research "
            "candidate ranks are not alpha. Alpha is proven only by one candidate passing every strict "
            "gate under one preregistered receipt. This artifact does not authorize trading, capital "
            "movement, physical control deployment, or profit claims."
        ),
        "config": {
            "sim_runs": max(100, int(sim_runs)),
            "alpha_threshold": float(alpha_threshold),
            "edge_threshold": float(edge_threshold),
            "legacy_cli_parameters_only": True,
            "legacy_parameter_note": (
                "sim-runs and score thresholds remain accepted for CLI compatibility but cannot create "
                "or promote alpha evidence."
            ),
            "candidate_queue_limit": 3,
            "strict_alpha_gate_count": len(STRICT_ALPHA_GATE_KEYS),
        },
        "summary": {
            # Legacy opportunities_api keys are retained with evidence-first semantics.
            "problem_count": len(problem_stack),
            "grade_a_locks": len(proven_receipts),
            "top_problem": top_problem,
            "top_sector": top_sector,
            "top_harmonic_alpha_edge_score": 0.0,
            "top_problem_context_only": True,
            "top_sector_context_only": True,
            "current_alpha_proven": current_alpha_proven,
            "proven_lock_count": len(proven_receipts),
            "candidate_hypothesis_count": len(candidate_queue),
            "financial_candidate_count": sum(
                1 for row in candidate_queue if row.get("domain") == "financial_alpha_research"
            ),
            "non_trading_control_candidate_count": sum(
                1
                for row in candidate_queue
                if row.get("classification") == "non_trading_control_candidate"
            ),
        },
        "strict_alpha_gate_assessment": alpha_assessment,
        "promotion_gates": {
            "current_alpha_proven": current_alpha_proven,
            "live_trading_allowed": False,
            "capital_deployment_allowed": False,
            "public_performance_claim_allowed": False,
            "profit_claim_allowed": False,
            "autonomous_execution_allowed": False,
            "physical_control_deployment_allowed": False,
            "reason": (
                "A complete alpha evidence receipt is absent, and deployment requires separate human, "
                "risk, legal, safety, and operational approvals even if research evidence later passes."
            ),
        },
        "live_posture": {
            "runtime_mode": "paper_research_only",
            "allow_live_orders": False,
            "controller_mode": "blocked",
            "capital_movement_allowed": False,
            "public_performance_claim_allowed": False,
            "policy": "evidence_first_no_live_or_capital_authorization",
        },
        "evidence_sources": normalized,
        "source_artifact_receipts": receipts,
        "negative_results_retained": {
            "benchmark_beater": benchmark.get("overall_verdict"),
            "kraken_institutional_research_candidate_count": kraken.get(
                "institutional_research_candidate_count"
            ),
            "symbol_timing_production_gate": timing.get("production_gate_status"),
            "kuramoto_sector_gains": (
                f"{safe_int(kuramoto_evidence.get('sector_gain_proven_count'))}/"
                f"{safe_int(kuramoto_evidence.get('sector_count'))}"
            ),
            "branching_validation_gate": branching.get("validation_gate"),
            "brachistochrone_confirmatory_pass": brachistochrone.get(
                "confirmatory_pass"
            ),
            "brachistochrone_smoothness_passed": brachistochrone.get(
                "smoothness_passed"
            ),
        },
        "preregistered_candidate_queue": candidate_queue,
        "not_queued_for_promotion": [
            {
                "candidate": "kuramoto_phase_coupling",
                "reason": (
                    f"Current result is {kuramoto_evidence.get('status')} with "
                    f"{safe_int(kuramoto_evidence.get('sector_gain_proven_count'))}/"
                    f"{safe_int(kuramoto_evidence.get('sector_count'))} proven sector gains."
                ),
            },
            {
                "candidate": "branching_live_breadth_geometry",
                "reason": (
                    f"Validation gate is {branching.get('validation_gate')}; "
                    "the best baseline still leads and field validation is absent."
                ),
            },
        ],
        "business_problem_context": problem_stack,
        # Legacy collection keys remain readable by existing downstream surfaces.
        "problem_stack": problem_stack,
        "top_problem_stack": problem_stack[: max(1, int(top_n))],
    }
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    strict = as_dict(payload.get("strict_alpha_gate_assessment"))
    promotion = as_dict(payload.get("promotion_gates"))

    lines = [
        "# Alpha and Edge Evidence Lock",
        "",
        f"Generated UTC: {payload.get('generated_utc', '')}",
        f"Status: `{payload.get('status', STATUS_NO_PROVEN_ALPHA)}`",
        f"Current alpha proven: `{str(bool(summary.get('current_alpha_proven'))).lower()}`",
        f"Proven locks: `{safe_int(summary.get('grade_a_locks'))}`",
        "",
        "## Claim Boundary",
        str(payload.get("claim_boundary") or ""),
        "",
        "## Strict Alpha Gates",
        (
            f"- passed: {safe_int(strict.get('passed_gate_count'))}/"
            f"{safe_int(strict.get('required_gate_count'))}"
        ),
    ]
    for gate_name, gate in as_dict(strict.get("gates")).items():
        gate = as_dict(gate)
        lines.append(
            f"- {gate_name}: `{str(bool(gate.get('passed'))).lower()}` - {gate.get('reason', '')}"
        )

    lines.extend(
        [
            "",
            "## Preregistered Candidate Queue",
        ]
    )
    for candidate in as_list(payload.get("preregistered_candidate_queue")):
        if not isinstance(candidate, dict):
            continue
        lines.append(
            f"- `{candidate.get('candidate_id')}` | {candidate.get('domain')} | "
            f"{candidate.get('current_status')}"
        )
        lines.append(f"  - hypothesis: {candidate.get('hypothesis')}")
        next_test = as_dict(candidate.get("preregistration")).get("next_test")
        lines.append(f"  - next test: {next_test}")

    lines.extend(
        [
            "",
            "## Business Problem Context",
            (
                f"- top_problem: {summary.get('top_problem')} "
                "(context only; not alpha)"
            ),
            (
                f"- top_sector: {summary.get('top_sector')} "
                "(context only; not alpha)"
            ),
            "",
            "## Deployment Posture",
            f"- live_trading_allowed: `{str(bool(promotion.get('live_trading_allowed'))).lower()}`",
            f"- capital_deployment_allowed: `{str(bool(promotion.get('capital_deployment_allowed'))).lower()}`",
            (
                "- public_performance_claim_allowed: "
                f"`{str(bool(promotion.get('public_performance_claim_allowed'))).lower()}`"
            ),
            f"- profit_claim_allowed: `{str(bool(promotion.get('profit_claim_allowed'))).lower()}`",
            (
                "- physical_control_deployment_allowed: "
                f"`{str(bool(promotion.get('physical_control_deployment_allowed'))).lower()}`"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_heartbeat(
    *,
    status: str,
    reason: str,
    run_tag: str,
    sim_runs: int,
    alpha_threshold: float,
    edge_threshold: float,
    summary: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_utc": now_iso(),
        "scope": "alpha_edge_lock_engine",
        "mode": "export",
        "status": str(status),
        "reason": str(reason),
        "run_tag": run_tag,
        "config": {
            "sim_runs": int(sim_runs),
            "alpha_threshold": float(alpha_threshold),
            "edge_threshold": float(edge_threshold),
            "legacy_cli_parameters_only": True,
        },
        "summary": summary if isinstance(summary, dict) else {},
        "artifacts": artifacts if isinstance(artifacts, dict) else {},
    }
    if error:
        payload["error"] = str(error)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat_ts_path = OUT_DIR / f"alpha_edge_lock_engine_heartbeat_{run_tag}.json"
    heartbeat_text = json.dumps(payload, indent=2)
    heartbeat_ts_path.write_text(heartbeat_text, encoding="utf-8")
    HEARTBEAT_LATEST_PATH.write_text(heartbeat_text, encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Build an evidence-first alpha and edge lock surface. Legacy score CLI arguments "
            "are accepted but cannot promote alpha."
        )
    )
    parser.add_argument("--sim-runs", type=int, default=5000, help="Legacy compatibility parameter")
    parser.add_argument(
        "--alpha-threshold", type=float, default=78.0, help="Legacy compatibility parameter"
    )
    parser.add_argument(
        "--edge-threshold", type=float, default=72.0, help="Legacy compatibility parameter"
    )
    parser.add_argument("--top-n", type=int, default=12, help="Top business-context records")
    args = parser.parse_args()

    sim_runs = max(100, int(args.sim_runs))
    alpha_threshold = float(args.alpha_threshold)
    edge_threshold = float(args.edge_threshold)
    tag = now_tag()

    write_heartbeat(
        status="running",
        reason="build_started",
        run_tag=tag,
        sim_runs=sim_runs,
        alpha_threshold=alpha_threshold,
        edge_threshold=edge_threshold,
    )

    try:
        payload = build_payload(
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
            top_n=max(1, int(args.top_n)),
        )

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        json_ts = OUT_DIR / f"alpha_edge_lock_engine_{tag}.json"
        md_ts = OUT_DIR / f"alpha_edge_lock_engine_{tag}.md"
        json_latest = OUT_DIR / "alpha_edge_lock_engine_latest.json"
        md_latest = OUT_DIR / "alpha_edge_lock_engine_latest.md"

        json_text = json.dumps(payload, indent=2)
        json_ts.write_text(json_text, encoding="utf-8")
        json_latest.write_text(json_text, encoding="utf-8")

        md_text = render_markdown(payload)
        md_ts.write_text(md_text, encoding="utf-8")
        md_latest.write_text(md_text, encoding="utf-8")

        write_heartbeat(
            status="ok",
            reason="build_complete",
            run_tag=tag,
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
            summary=payload.get("summary", {}),
            artifacts={
                "json_latest": str(json_latest),
                "json_timestamped": str(json_ts),
                "md_latest": str(md_latest),
                "md_timestamped": str(md_ts),
            },
        )

        print("BUILD_ALPHA_EDGE_LOCK_ENGINE")
        print(f"status={payload['status']}")
        print(f"current_alpha_proven={payload['summary']['current_alpha_proven']}")
        print(f"problems={payload['summary']['problem_count']}")
        print(f"grade_a_locks={payload['summary']['grade_a_locks']}")
        print(f"top_problem={payload['summary']['top_problem']}")
        print(f"json={json_latest}")
        print(f"md={md_latest}")
        return 0
    except Exception as exc:
        write_heartbeat(
            status="error",
            reason="build_failed",
            run_tag=tag,
            sim_runs=sim_runs,
            alpha_threshold=alpha_threshold,
            edge_threshold=edge_threshold,
            error=str(exc),
        )
        raise


if __name__ == "__main__":
    raise SystemExit(main())
