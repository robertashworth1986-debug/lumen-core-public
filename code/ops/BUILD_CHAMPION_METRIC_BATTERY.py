from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_OPS = ROOT / "out" / "ops"
DASHBOARD_DATA = ROOT / "dashboard" / "data"
DOCS = ROOT / "docs"

GAUNTLET_JSON = OUT_OPS / "champion_metric_gauntlet_latest.json"
STRESS_JSON = OUT_OPS / "champion_stress_test_matrix_latest.json"
PHASE_JSON = OUT_OPS / "champion_phase_proxy_diagnostics_latest.json"
SOURCE_JSON = OUT_OPS / "live_source_measurement_maximizer_latest.json"
DOMAIN_JSON = OUT_OPS / "live_domain_deployment_feed_latest.json"
DOLLAR_GATE_JSON = DASHBOARD_DATA / "dollar_claim_gate.json"

OUT_JSON = OUT_OPS / "champion_metric_battery_latest.json"
DASHBOARD_JSON = DASHBOARD_DATA / "champion_metric_battery.json"
OUT_MD = DOCS / "CHAMPION_METRIC_BATTERY_2026-07-01.md"

BOUNDARY = (
    "Champion metric battery only. This artifact consolidates internal replay evidence, live-source breadth, "
    "phase proxy diagnostics, hosted hash verification, and remaining blockers. It does not prove field "
    "validation, realized savings, fixed frozen-delta pricing, medical efficacy, grant award certainty, or live "
    "trading performance."
)


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


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


def stable_sha256(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def status_from_pass(passed: bool, blocked: bool = False) -> str:
    if passed:
        return "PASS"
    if blocked:
        return "BLOCKED_REQUIRES_EXTERNAL_INPUT"
    return "READY_TO_RUN_OR_EXPAND"


def category(
    category_id: str,
    label: str,
    status: str,
    evidence: dict[str, Any],
    metrics: list[str],
    next_action: str,
    claim_gate: str,
) -> dict[str, Any]:
    return {
        "category_id": category_id,
        "label": label,
        "status": status,
        "evidence": evidence,
        "metrics": metrics,
        "next_action": next_action,
        "claim_gate": claim_gate,
    }


def build_categories(inputs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    gauntlet = inputs["gauntlet"]
    stress = inputs["stress"]
    phase = inputs["phase"]
    sources = inputs["sources"]
    domain = inputs["domain"]
    dollar_gate = inputs["dollar_gate"]

    g_summary = as_dict(gauntlet.get("summary"))
    s_summary = as_dict(stress.get("summary"))
    p_summary = as_dict(phase.get("summary"))
    src_summary = as_dict(sources.get("summary"))
    domain_summary = as_dict(domain.get("summary"))
    dollar_summary = as_dict(dollar_gate.get("summary"))

    stress_gates = {str(row.get("name")): row for row in as_list(stress.get("metric_stress_tests")) if isinstance(row, dict)}
    gauntlet_gates = {str(row.get("name")): row for row in as_list(gauntlet.get("metric_gauntlet")) if isinstance(row, dict)}

    live_domain_ok = bool(
        s_summary.get("live_domain_hash_verified")
        or g_summary.get("live_domain_reviewer_ready")
        or domain_summary.get("live_domain_reviewer_ready")
    )
    field_allowed = bool(
        g_summary.get("field_validation_claim_allowed")
        or s_summary.get("field_validation_claim_allowed")
        or dollar_summary.get("field_validation_claim_allowed")
    )
    savings_allowed = bool(
        g_summary.get("real_dollar_savings_claim_allowed")
        or s_summary.get("real_dollar_savings_claim_allowed")
        or dollar_summary.get("real_dollar_savings_claim_allowed")
    )

    return [
        category(
            "source_conditioned_replay",
            "Source-conditioned replay versus named baseline",
            status_from_pass(bool(gauntlet_gates.get("baseline_win_count", {}).get("passed"))),
            {
                "champion_family": g_summary.get("champion_family"),
                "named_baseline": g_summary.get("named_baseline"),
                "holdout_wins": g_summary.get("holdout_wins"),
                "holdout_count": g_summary.get("holdout_count"),
                "mean_delta_vs_named_baseline": g_summary.get("mean_delta_vs_named_baseline"),
                "min_delta_vs_named_baseline": g_summary.get("min_delta_vs_named_baseline"),
            },
            ["holdout_win_rate", "mean_delta", "minimum_delta", "sign_test", "wilson_lower_bound"],
            "Keep frozen replay rows and rerun when new source systems are promoted.",
            "Allows internal champion language only.",
        ),
        category(
            "best_same_run_baseline",
            "Best same-run baseline pressure test",
            status_from_pass(bool(stress_gates.get("best_same_run_baseline_win_rate", {}).get("passed"))),
            {
                "wins_vs_best_same_run_baseline": s_summary.get("wins_vs_best_same_run_baseline"),
                "holdout_count": s_summary.get("holdout_count"),
                "mean_delta_vs_best_same_run_baseline": s_summary.get("mean_delta_vs_best_same_run_baseline"),
                "min_delta_vs_best_same_run_baseline": s_summary.get("min_delta_vs_best_same_run_baseline"),
            },
            ["best_baseline_win_rate", "best_baseline_margin", "rank_histogram"],
            "Add a leave-one-family-out control so no single baseline family is too easy.",
            "Supports stronger internal benchmark language, not field validation.",
        ),
        category(
            "phase_resonance_proxy",
            "Phase/coherence proxy diagnostics",
            status_from_pass(bool(s_summary.get("phase_proxy_diagnostics_ready"))),
            {
                "mean_phase_coherence_proxy": s_summary.get("mean_phase_coherence_proxy"),
                "mean_phase_slip_proxy_rate": s_summary.get("mean_phase_slip_proxy_rate"),
                "mean_spectral_concentration_proxy": s_summary.get("mean_spectral_concentration_proxy"),
                "phase_proxy_claim_allowed": p_summary.get("phase_proxy_claim_allowed"),
            },
            ["phase_coherence", "phase_slip_rate", "spectral_concentration", "circular_phase_error"],
            "Run the same proxy metrics on each newly promoted live-source lane.",
            "Allows replay-data phase-proxy language only; hardware PLL claims require instruments.",
        ),
        category(
            "live_source_breadth",
            "Live-source breadth and provider measurement",
            status_from_pass(as_int(src_summary.get("measured_source_count")) >= 18),
            {
                "enabled_sources": src_summary.get("enabled_source_count"),
                "measured_sources": src_summary.get("measured_source_count"),
                "failed_or_thin_sources": src_summary.get("failed_or_thin_source_count"),
                "total_measured_rows": src_summary.get("total_measured_rows"),
                "coverage_percent": src_summary.get("coverage_percent"),
            },
            ["provider_ping", "bounded_row_pull", "snapshot_hash", "coverage_percent"],
            "Fix or replace the remaining failed/thin sources: EPA AQS, NREL, odds, and restricted exchange feed.",
            "Live breadth is evidence inventory until promoted into locked benchmark replay.",
        ),
        category(
            "public_domain_hash_verification",
            "Hosted reviewer feed hash verification",
            status_from_pass(live_domain_ok),
            {
                "domain_deployment_state": domain_summary.get("domain_deployment_state")
                or as_dict(domain.get("summary")).get("domain_deployment_state"),
                "required_feed_count": domain_summary.get("required_feed_count"),
                "required_remote_hash_match_count": domain_summary.get("required_remote_hash_match_count"),
                "required_remote_stale_or_missing_count": domain_summary.get("required_remote_stale_or_missing_count"),
            },
            ["local_sha256", "remote_sha256", "required_feed_match_count", "stale_feed_count"],
            "Deploy this battery feed as an optional proof feed, then verify hosted hash parity.",
            "Allows public proof-feed deployment language.",
        ),
        category(
            "residual_calibration",
            "Residual, calibration, and error-distribution checks",
            "READY_TO_RUN_OR_EXPAND",
            {
                "current_gate": stress_gates.get("residual_autocorrelation_and_calibration", {}),
                "numeric_samples_read": s_summary.get("numeric_samples_read"),
            },
            ["residual_autocorrelation", "calibration_curve", "coverage_error", "error_tail_risk"],
            "Compute residual diagnostics per source system and fail closed on drift.",
            "Required before serious operational-performance language.",
        ),
        category(
            "source_generalization",
            "Source generalization and live-breadth promotion",
            "READY_TO_RUN_OR_EXPAND",
            {
                "champion_replay_source_systems": s_summary.get("source_systems"),
                "broader_measured_provider_count": g_summary.get("broader_measured_provider_count"),
                "manifest_unique_source_count": g_summary.get("manifest_unique_source_count"),
                "manifest_ready_for_benchmark_row_count": g_summary.get("manifest_ready_for_benchmark_row_count"),
            },
            ["leave_one_source_out", "source_group_holdout", "provider_promotion_rate", "schema_normalization_success"],
            "Promote one measured provider at a time into a locked source-conditioned replay.",
            "Blocks broad all-sector claims until promoted sources pass matched baselines.",
        ),
        category(
            "runtime_operational_budget",
            "Runtime, latency, and production-budget checks",
            "READY_TO_RUN_OR_EXPAND",
            {
                "current_gate": stress_gates.get("latency_runtime_budget", {}),
                "fallback_rate": s_summary.get("fallback_rate"),
            },
            ["p50_latency", "p95_latency", "memory_budget", "fallback_rate", "throughput"],
            "Run timed replays on the laptop and VPS with fixed budgets.",
            "Required before production readiness language.",
        ),
        category(
            "hardware_grid_rf_pll",
            "Grid/RF/PLL hardware validation",
            "BLOCKED_REQUIRES_INSTRUMENTED_DATA",
            {
                "grid_needed": "buyer/operator SCADA, PMU, outage, forecast, or dispatch holdout",
                "rf_needed": "recorded RF spectrum/IQ or lab instrument traces",
                "pll_needed": "jitter, phase-noise, lock-time, and bandwidth measurements",
            },
            ["PMU_replay", "RF_IQ_replay", "PLL_jitter", "phase_noise", "lock_time"],
            "Ask a lab or system owner for a held-out dataset and their acceptance metric.",
            "Blocks hardware field-validation language.",
        ),
        category(
            "economic_conversion",
            "Avoided-cost and dollar conversion",
            status_from_pass(savings_allowed, blocked=not savings_allowed),
            {
                "safe_estimated_hourly_value_usd": g_summary.get("safe_estimated_hourly_value_usd"),
                "safe_estimated_annual_value_usd": g_summary.get("safe_estimated_annual_value_usd"),
                "real_dollar_savings_claim_allowed": savings_allowed,
            },
            ["owner_cost_factor", "counterfactual_baseline", "acceptance_threshold", "avoided_cost_formula"],
            "Get an external owner to approve the baseline and cost conversion before naming realized savings.",
            "Blocks realized dollar savings and fixed frozen-delta pricing.",
        ),
        category(
            "buyer_authorized_field_replay",
            "Buyer-authorized field replay",
            status_from_pass(field_allowed, blocked=not field_allowed),
            {
                "buyer_authorized_field_replay_request_ready": g_summary.get(
                    "buyer_authorized_field_replay_request_ready"
                ),
                "field_validation_claim_allowed": field_allowed,
                "manual_paid_pilot_outreach_allowed": s_summary.get("manual_paid_pilot_outreach_allowed"),
            },
            ["pre_registered_holdout", "incumbent_baseline", "buyer_metric", "signed_result"],
            "Send the reviewer-safe outreach and ask for one 20-minute fit call.",
            "This is the unlock for field validation.",
        ),
        category(
            "all_family_live_championship",
            "All-family live championship",
            "BLOCKED_REQUIRES_FULL_REGISTRY_RUN",
            {
                "current_champion_family": g_summary.get("champion_family"),
                "current_registry_gate": stress_gates.get("all_registry_families_have_benchmark_specs", {}),
            },
            ["family_count_tested", "matched_budget", "negative_results_logged", "winner_by_lane"],
            "Run every registered family under matched budgets and publish the losers too.",
            "Blocks universal geometry superiority claims.",
        ),
    ]


def build_payload() -> dict[str, Any]:
    inputs = {
        "gauntlet": read_json(GAUNTLET_JSON),
        "stress": read_json(STRESS_JSON),
        "phase": read_json(PHASE_JSON),
        "sources": read_json(SOURCE_JSON),
        "domain": read_json(DOMAIN_JSON),
        "dollar_gate": read_json(DOLLAR_GATE_JSON),
    }
    categories = build_categories(inputs)
    pass_count = sum(1 for row in categories if row["status"] == "PASS")
    ready_count = sum(1 for row in categories if row["status"] == "READY_TO_RUN_OR_EXPAND")
    blocked_count = sum(1 for row in categories if row["status"].startswith("BLOCKED"))
    gauntlet_summary = as_dict(inputs["gauntlet"].get("summary"))
    stress_summary = as_dict(inputs["stress"].get("summary"))
    source_summary = as_dict(inputs["sources"].get("summary"))

    payload: dict[str, Any] = {
        "generated_utc": now_utc(),
        "schema": "champion_metric_battery_v1",
        "purpose": "One reviewer-safe board that shows every major champion test lane and blocker.",
        "boundary": BOUNDARY,
        "summary": {
            "evidence_stage": "internal_replay_metric_battery_not_field_validated",
            "champion_family": gauntlet_summary.get("champion_family") or stress_summary.get("champion_family"),
            "champion_label": gauntlet_summary.get("champion_label") or stress_summary.get("champion_label"),
            "named_baseline": gauntlet_summary.get("named_baseline") or stress_summary.get("named_baseline"),
            "holdout_wins": gauntlet_summary.get("holdout_wins") or stress_summary.get("wins_vs_named_baseline"),
            "holdout_count": gauntlet_summary.get("holdout_count") or stress_summary.get("holdout_count"),
            "estimated_rows_replayed": gauntlet_summary.get("estimated_rows_replayed")
            or stress_summary.get("estimated_rows_replayed"),
            "source_system_count": gauntlet_summary.get("source_system_count") or stress_summary.get("source_system_count"),
            "broader_measured_provider_count": source_summary.get("measured_source_count")
            or gauntlet_summary.get("broader_measured_provider_count"),
            "broader_enabled_provider_count": source_summary.get("enabled_source_count")
            or gauntlet_summary.get("broader_enabled_provider_count"),
            "total_measured_rows_latest_pull": source_summary.get("total_measured_rows"),
            "metric_category_count": len(categories),
            "metric_pass_count": pass_count,
            "metric_ready_to_run_count": ready_count,
            "metric_blocked_external_count": blocked_count,
            "field_validation_claim_allowed": False,
            "real_dollar_savings_claim_allowed": False,
            "fixed_frozen_delta_price_claim_allowed": False,
            "live_trading_or_autonomous_execution_allowed": False,
            "manual_paid_pilot_outreach_allowed": bool(stress_summary.get("manual_paid_pilot_outreach_allowed")),
            "plain_english_answer": (
                "The current platform is strongest as an internal, hash-verifiable replay and benchmark engine. "
                "It has a clear champion and growing live-source breadth, but the next money unlock is an external "
                "buyer-authorized replay with a locked baseline, not a premature realized-savings claim."
            ),
        },
        "claim_controls": {
            "allowed_now": [
                "internal champion",
                "source-conditioned replay winner",
                "public proof-feed deployment if hosted hashes match",
                "paid-pilot scoping candidate",
                "buyer-authorized field replay request",
            ],
            "not_allowed_yet": [
                "field validated",
                "realized savings",
                "fixed frozen-delta price",
                "grant award certainty",
                "autonomous live trading edge",
                "hardware PLL/RF/grid validation",
                "universal geometry superiority",
            ],
        },
        "metric_categories": categories,
        "best_next_source_families": [
            {
                "family": "ISO/RTO grid operations",
                "examples": ["PJM", "MISO", "ERCOT", "CAISO", "SPP", "NYISO", "ISO-NE", "BPA", "TVA"],
                "why": "Directly strengthens grid field-replay credibility and avoided-cost math.",
            },
            {
                "family": "utility outage and reliability",
                "examples": ["DOE OE-417", "utility outage maps", "EPRI or utility-held outage/event windows"],
                "why": "Turns abstract improvement into incident detection, response time, and avoided outage cost.",
            },
            {
                "family": "energy market and plant operations",
                "examples": ["EIA EBA", "EIA 860", "EIA 923", "nuclear outage daily status"],
                "why": "Connects forecasts, outages, generation mix, and operational pressure.",
            },
            {
                "family": "weather and environmental operations",
                "examples": ["NOAA", "NWS", "SWPC", "OpenAQ", "AirNow", "EPA AQS"],
                "why": "Adds exogenous drivers for load, outage, air-quality, and risk forecasts.",
            },
            {
                "family": "maritime and critical infrastructure movement",
                "examples": ["MarineCadastre AIS", "NOAA PORTS", "USCG public feeds"],
                "why": "Supports HarborSentinel/NV063 style validation lanes.",
            },
        ],
        "reviewer_safe_outreach_instruction": (
            "Do not claim realized savings. Ask for a paid or sponsored field replay using the buyer's held-out data, "
            "incumbent baseline, acceptance metric, and approved economic conversion."
        ),
        "source_artifacts": {
            "champion_metric_gauntlet": str(GAUNTLET_JSON.relative_to(ROOT)),
            "champion_stress_test_matrix": str(STRESS_JSON.relative_to(ROOT)),
            "champion_phase_proxy_diagnostics": str(PHASE_JSON.relative_to(ROOT)),
            "live_source_measurement_maximizer": str(SOURCE_JSON.relative_to(ROOT)),
            "live_domain_deployment_feed": str(DOMAIN_JSON.relative_to(ROOT)),
            "dollar_claim_gate": str(DOLLAR_GATE_JSON.relative_to(ROOT)),
        },
    }
    payload["metric_battery_sha256"] = stable_sha256(
        {
            "summary": payload["summary"],
            "metric_categories": payload["metric_categories"],
            "claim_controls": payload["claim_controls"],
        }
    )
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    summary = as_dict(payload.get("summary"))
    lines = [
        "# Champion Metric Battery",
        "",
        f"Generated UTC: `{payload.get('generated_utc')}`",
        f"Metric battery SHA-256: `{payload.get('metric_battery_sha256')}`",
        "",
        "## Plain English",
        "",
        str(summary.get("plain_english_answer") or ""),
        "",
        "## Current Champion",
        "",
        f"- Champion: `{summary.get('champion_family')}`",
        f"- Named baseline: `{summary.get('named_baseline')}`",
        f"- Holdout wins: `{summary.get('holdout_wins')}/{summary.get('holdout_count')}`",
        f"- Estimated rows replayed: `{summary.get('estimated_rows_replayed')}`",
        f"- Champion replay source systems: `{summary.get('source_system_count')}`",
        f"- Broader measured providers: `{summary.get('broader_measured_provider_count')}/"
        f"{summary.get('broader_enabled_provider_count')}`",
        f"- Latest bounded measured rows: `{summary.get('total_measured_rows_latest_pull')}`",
        "",
        "## Battery Status",
        "",
        f"- Metric categories: `{summary.get('metric_category_count')}`",
        f"- Passed: `{summary.get('metric_pass_count')}`",
        f"- Ready to run or expand: `{summary.get('metric_ready_to_run_count')}`",
        f"- Blocked by external input: `{summary.get('metric_blocked_external_count')}`",
        f"- Field-validation claim allowed: `{str(summary.get('field_validation_claim_allowed')).lower()}`",
        f"- Real-dollar savings claim allowed: `{str(summary.get('real_dollar_savings_claim_allowed')).lower()}`",
        "",
        "## Metric Categories",
        "",
    ]
    for row in as_list(payload.get("metric_categories")):
        if not isinstance(row, dict):
            continue
        lines.extend(
            [
                f"### {row.get('label')}",
                "",
                f"- Status: `{row.get('status')}`",
                f"- Metrics: `{', '.join(str(metric) for metric in as_list(row.get('metrics')))}`",
                f"- Next action: {row.get('next_action')}",
                f"- Claim gate: {row.get('claim_gate')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Best Next Source Families",
            "",
        ]
    )
    for row in as_list(payload.get("best_next_source_families")):
        if not isinstance(row, dict):
            continue
        lines.append(f"- `{row.get('family')}`: {row.get('why')}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            BOUNDARY,
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    payload = build_payload()
    write_json(OUT_JSON, payload)
    write_json(DASHBOARD_JSON, payload)
    write_text(OUT_MD, render_markdown(payload))
    print(f"Wrote {OUT_JSON}")
    print(f"Wrote {DASHBOARD_JSON}")
    print(f"Wrote {OUT_MD}")


if __name__ == "__main__":
    main()
